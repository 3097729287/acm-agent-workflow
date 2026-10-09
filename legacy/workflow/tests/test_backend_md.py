"""Isolated HTTP and persistence checks. Never writes the user's TB table."""
import concurrent.futures
import datetime as dt
import http.client
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import quote

import backend


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tb-web-test-")
        self.root = Path(self.temp.name)
        self.table = self.root / "题解" / "TB.md"
        self.table.parent.mkdir()
        self.original = ("\ufeff# 我的 TB\r\n说明不许变\r\n\r\n"
                         "| 场次 | 题号 | 题名 | 知识点 | 难度 | 状态 | 日期 |\r\n"
                         "|---|---|---|---|---|---|---|\r\n"
                         "| 周赛 164 | D | 桃子\\|测试 | [前缀和 + 差分][主] + 排序 | 1500 | 未做 |  |\r\n"
                         "| ABC 478 | C | 中文题目 | 素数 | 1400 | 独立AC | 2020-01-01 |\n"
                         "| Div.2 1124 | B | 背包题 | 背包 DP | 1800 | 巩固 | 2020-01-01 |\r\n"
                         "| 周赛 164 | E | 重写题 | 树形 DP | 1700 | 待重写 |  |\r\n"
                         "| 周赛 164 | F | 补题 | DFS | 1800 | 不会 |  |\r\n"
                         "\r\n## 表外备注\r\n逐字保留 💡\r\n").encode("utf-8")
        self.table.write_bytes(self.original)
        self.dist = self.root / "dist"
        self.dist.mkdir()
        (self.dist / "index.html").write_text("<html>TB 中文</html>", encoding="utf-8")
        self.backups = []

        def backup(source, *args):
            destination = self.root / ("backup-%d.bak" % len(self.backups))
            shutil.copy2(source, destination)
            self.backups.append(destination)
            return str(destination)

        self.backup_patch = patch.object(backend.toolutil, "backup_to_repo", side_effect=backup)
        self.backup_patch.start()
        self.server = backend.create_server(data_file=self.table, data_root=self.root, dist_dir=self.dist,
                                             history_file=self.root / "history.jsonl")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.token = self.server.store.token

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.backup_patch.stop()
        self.temp.cleanup()

    def request(self, method="GET", path="/api/data", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        request_headers = {"Content-Type": "application/json", "X-TB-Token": self.token}
        request_headers.update(headers or {})
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        connection.request(method, path, body=payload, headers=request_headers)
        response = connection.getresponse()
        raw = response.read()
        content_type = response.getheader("Content-Type", "")
        result = json.loads(raw) if "application/json" in content_type else raw
        status = response.status
        connection.close()
        return status, result

    def update(self, status="独立AC", date=None, expected=None):
        body = {"id": "周赛 164::D", "status": status,
                "expected": expected or {"status": "未做", "date": ""}}
        if date is not None:
            body["date"] = date
        return self.request("POST", "/api/status", body)

    def test_chinese_rows_recursive_categories_and_queues(self):
        status, data = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(len(data["rows"]), 5)
        self.assertEqual(data["statuses"], ["未做", "不会", "待重写", "复现AC", "独立AC", "巩固"])
        self.assertEqual(data["rows"][0]["title"], "桃子|测试")
        self.assertEqual(data["rows"][0]["tags"], ["前缀和", "差分", "排序"])
        self.assertEqual([r["queue"] for r in data["rows"]], [None, "review", "check", "rewrite", "fill"])
        self.assertEqual([r["platform"] for r in data["rows"][:3]], ["牛客", "AtCoder", "Codeforces"])
        self.assertEqual(data["token"], self.token)
        math = next(category for category in data["categories"] if category["name"] == "数学")
        number_theory = next(category for category in math["children"] if category["name"] == "数论")
        self.assertIn("素数", number_theory["tags"])
        self.assertIn("素数", math["tags"])
        self.assertTrue(any(child["name"] == "素数" for child in number_theory["children"]))
        self.assertEqual(self.table.read_bytes(), self.original)

    def test_one_row_edit_preserves_every_other_byte_and_journals(self):
        status, result = self.update()
        self.assertEqual(status, 200, result)
        today = dt.date.today().isoformat()
        expected = self.original.replace(b"| 1500 | \xe6\x9c\xaa\xe5\x81\x9a |  |", ("| 1500 | 独立AC | " + today + " |").encode("utf-8"))
        self.assertEqual(self.table.read_bytes(), expected)
        self.assertEqual(self.backups[0].read_bytes(), self.original)
        entry = json.loads((self.root / "history.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(entry["before"], {"status": "未做", "date": ""})
        self.assertEqual(entry["after"], {"status": "独立AC", "date": today})
        self.assertEqual(result["row"]["date"], today)

    def test_conflict_refuses_stale_expected_without_backup(self):
        self.assertEqual(self.update()[0], 200)
        after = self.table.read_bytes()
        status, data = self.update("不会")
        self.assertEqual(status, 409, data)
        self.assertEqual(self.table.read_bytes(), after)
        self.assertEqual(len(self.backups), 1)

    def test_undo_explicit_empty_date_and_redo_preserve_dates(self):
        self.assertEqual(self.update(date="2026-01-23")[0], 200)
        status, result = self.update("未做", date="", expected={"status": "独立AC", "date": "2026-01-23"})
        self.assertEqual(status, 200, result)
        self.assertEqual(self.table.read_bytes(), self.original)
        self.assertEqual(self.update(date="2026-01-23")[0], 200)
        self.assertEqual(len((self.root / "history.jsonl").read_text(encoding="utf-8").splitlines()), 3)

    def test_external_change_between_backup_and_write_is_preserved(self):
        external = self.original.replace("中文题目".encode(), "外部更新".encode())

        def mutate_after_backup(source, *args):
            self.table.write_bytes(external)

        with patch.object(backend.toolutil, "backup_to_repo", side_effect=mutate_after_backup):
            status, result = self.update()
        self.assertEqual(status, 409, result)
        self.assertEqual(self.table.read_bytes(), external)

    def test_concurrent_edits_only_one_expected_version_commits(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            requests = [pool.submit(self.update, state) for state in ("不会", "复现AC")]
            self.assertEqual(sorted(request.result()[0] for request in requests), [200, 409])
        self.assertEqual(len(self.backups), 1)

    def test_invalid_status_date_and_missing_expected(self):
        for body in ({"id": "周赛 164::D", "status": "完成"},
                     {"id": "周赛 164::D", "status": "独立AC"},
                     {"id": "周赛 164::D", "status": "独立AC", "date": "2026-02-30", "expected": {"status": "未做", "date": ""}},
                     {"id": "周赛 164::D", "status": "独立AC", "date": "20260123", "expected": {"status": "未做", "date": ""}}):
            self.assertEqual(self.request("POST", "/api/status", body)[0], 400)
        self.assertEqual(self.table.read_bytes(), self.original)

    def test_token_origin_host_and_static_path_guards(self):
        body = {"id": "周赛 164::D", "status": "独立AC", "expected": {"status": "未做", "date": ""}}
        self.assertEqual(self.request("POST", "/api/status", body, {"X-TB-Token": "invalid"})[0], 403)
        self.assertEqual(self.request("POST", "/api/status", body, {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request(headers={"Host": "evil.example"})[0], 403)
        for path in ("/api/unknown", "/unknown", "/../backend.py", "/%2e%2e/backend.py", "/%5c..%5cbackend.py", "/api/data%00"):
            self.assertEqual(self.request(path=path)[0], 404, path)
        self.assertEqual(self.request(path="/")[0], 200)
        self.assertEqual(self.table.read_bytes(), self.original)

    def test_solution_extracts_only_selected_section_ignoring_code_headings(self):
        directory, solution_path = backend.toolutil.contest_paths(str(self.root), "周赛", 164)
        Path(directory).mkdir(parents=True)
        Path(solution_path).write_text(
            "# 周赛 164 题解\n> https://ac.nowcoder.com/acm/contest/141142\n\n"
            "## 目录\n| 题号 | 题名 | 考点 | 难度 |\n|---|---|---|---|\n"
            "| D | 桃子\\|测试 | 前缀和 | 1500 |\n| E | 重写题 | 树形 DP | 1700 |\n\n"
            "## D. 桃子|测试\n### 题意\n有 $n$ 个桃子。\n```text\n## E. 假标题\n```\n"
            "### 思路\n前缀和。\n## E. 重写题\n另一道题。\n", encoding="utf-8")
        status, data = self.request(path="/api/solution?id=" + quote("周赛 164::D"))
        self.assertEqual(status, 200, data)
        self.assertTrue(data["markdown"].startswith("## D. 桃子|测试"))
        self.assertIn("## E. 假标题", data["markdown"])
        self.assertNotIn("另一道题", data["markdown"])
        self.assertEqual(data["url"], "https://ac.nowcoder.com/acm/contest/141142/D")
        self.assertEqual(self.request(path="/api/solution?id=missing")[0], 404)

    def test_solution_handles_catalog_html_vs_heading_markdown(self):
        directory, solution_path = backend.toolutil.contest_paths(str(self.root), "周赛", 164)
        Path(directory).mkdir(parents=True)
        Path(solution_path).write_text(
            "# 周赛 164 题解\n> https://ac.nowcoder.com/acm/contest/141142\n\n"
            "## 目录\n| 题号 | 题名 | 考点 | 难度 |\n|---|---|---|---|\n"
            "| D | ABC&#124;AB&#124;A | 前缀和 | 1500 |\n\n"
            "## D. ABC\\|AB\\|A\n### 题意\n正文。\n## 实测记录\n记录。\n", encoding="utf-8")
        status, data = self.request(path="/api/solution?id=" + quote("周赛 164::D"))
        self.assertEqual(status, 200, data)
        self.assertIn("正文", data["markdown"])
        self.assertNotIn("实测记录", data["markdown"])

    def test_inbox_requires_choice_and_preserves_existing_state(self):
        inbox = self.table.parent / "_收件箱"
        inbox.mkdir()
        (inbox / "周赛164题解.md").write_text(
            "# 周赛 164 题解\n\n## 目录\n| 题号 | 题名 | 考点 | 难度 |\n|---|---|---|---|\n"
            "| D | 新题名 | 前缀和 | 1500 |\n| G | 新题 | 构造 | 1900 |\n\n## D. 新题名\n内容\n", encoding="utf-8")
        status, data = self.request(path="/api/inbox")
        self.assertEqual(status, 200, data)
        self.assertEqual(data["pending"], 2)
        self.assertEqual(len(data["conflicts"]), 1)
        status, result = self.request("POST", "/api/inbox", {"action": "import"})
        self.assertEqual(status, 200, result)
        self.assertTrue(result["needsChoice"])
        self.assertEqual(self.table.read_bytes(), self.original)
        status, result = self.request("POST", "/api/inbox", {"action": "overwrite"})
        self.assertEqual(status, 200, result)
        self.assertEqual(result["result"]["updated"], 1)
        self.assertEqual(result["result"]["added"], 1)
        rows = self.server.store.raw_rows()
        d = next(row for row in rows if row["题号"] == "D")
        self.assertEqual((d["状态"], d["日期"]), ("未做", ""))
        self.assertEqual(next(row for row in rows if row["题号"] == "G")["状态"], "未做")


if __name__ == "__main__":
    unittest.main(verbosity=2)
