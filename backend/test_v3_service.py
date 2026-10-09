"""v3 service checks; every state write and submission is isolated in a temp folder."""
import datetime as dt
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import quote

import backend
from insights import canonical_url
from training import ServiceError
import test_training as fixtures


class RemovalInsightsTests(unittest.TestCase):
    setUp = fixtures.ServiceTests.setUp
    tearDown = fixtures.ServiceTests.tearDown
    completed = fixtures.ServiceTests.completed
    contest = fixtures.ServiceTests.contest

    def test_remove_retains_code_evidence_and_rejoin(self):
        self.service.save_draft("fixture::A", "my draft")
        result = self.completed()
        job_id = result["submission"]["id"]
        self.clock.advance(days=8)
        self.assertEqual(self.service.workspace()["summary"]["due"], 1)
        self.assertEqual(self.service.remove_training("fixture::A")["workspace"]["summary"]["total"], 0)
        self.assertEqual(self.service.workspace()["summary"]["due"], 0)
        self.assertEqual(self.service.submission(job_id)["submission"]["code"], "AC")
        self.assertEqual(self.service.problem("fixture::A")["draft"], "my draft")
        insight = self.service.insights()
        self.assertEqual(insight["summary"]["active"], 0)
        self.assertEqual(insight["summary"]["localAccepted"], 1)
        self.assertEqual(insight["activity"][0]["accepted"], 1)
        self.assertEqual(insight["knowledge"][0]["due"], 0)
        joined = self.service.start_training("fixture::A")["workspace"]
        self.assertTrue(joined["training"][0]["accepted"])
        self.assertEqual(joined["training"][0]["queue"], "review")

    def test_remove_last_set_member_and_rejoin_original_set(self):
        original = self.service.start_practice_set("fixture")["set"]
        self.completed()
        for identity in original["ids"]:
            self.service.remove_training(identity)
        self.assertEqual(self.service.workspace()["sets"], [])
        rejoined = self.service.start_practice_set("fixture")["set"]
        self.assertEqual(rejoined["id"], original["id"])
        self.assertEqual(rejoined["total"], 8)
        self.assertEqual(rejoined["accepted"], 1)

    def test_pending_and_running_mock_removal_rejected(self):
        self.service.submit("fixture::A", "BLOCK AC")
        self.assertTrue(self.judge.started.wait(2))
        with self.assertRaises(ServiceError) as error:
            self.service.remove_training("fixture::A")
        self.assertEqual(error.exception.status, 409)
        self.judge.release.set()
        contest = self.contest()
        with self.assertRaises(ServiceError) as error:
            self.service.remove_training(contest["slots"][0]["id"])
        self.assertEqual(error.exception.status, 409)

    def test_finished_genuine_submission_reactivates(self):
        self.completed()
        self.service.remove_training("fixture::A")
        self.completed(code="WA")
        self.assertTrue(self.service.workspace()["training"][0]["accepted"])
        self.assertEqual(self.service.workspace()["summary"]["total"], 1)

    def test_canonical_alias_cannot_bypass_mock_lock(self):
        self.library.rows[0]["url"] = "https://codeforces.com/contest/123/problem/A"
        contest = self.contest(count=1)
        original = contest["slots"][0]["id"]
        row = next(row for row in self.library.rows if row["id"] == original)
        row["url"] = "https://codeforces.com/contest/123/problem/A"
        self.library.rows.append(dict(row, id="remote:codeforces:123::A", url="https://codeforces.com/problemset/problem/123/A"))
        for operation in (lambda: self.service.assert_solution_unlocked("remote:codeforces:123::A"), lambda: self.service.problem("remote:codeforces:123::A")):
            with self.assertRaises(ServiceError) as error:
                operation()
            self.assertEqual(error.exception.status, 403)

    def test_archive_replaces_remote_identity_preserves_acceptance_and_code(self):
        self.library.rows[0].update(url="https://codeforces.com/contest/123/problem/A", source="remote")
        self.service.save_draft("fixture::A", "retained code")
        self.completed()
        archived = dict(self.library.rows[0], id="archive::A", source="archive")
        self.library.rows.append(archived)
        self.service.start_training("archive::A")
        workspace = self.service.workspace()
        self.assertEqual(workspace["summary"]["total"], 1)
        self.assertEqual(workspace["training"][0]["id"], "archive::A")
        self.assertTrue(workspace["training"][0]["accepted"])
        self.assertEqual(self.service.problem("archive::A")["draft"], "retained code")
        self.assertEqual(len(self.service.submissions("archive::A")["submissions"]), 1)
        self.service.mark_solution_seen("archive::A")
        self.completed("fixture::A", code="AC new")
        self.assertEqual(self.service.workspace()["training"][0]["queue"], "rewrite")
        self.service.remove_training("archive::A")
        self.assertEqual(self.service.workspace()["summary"]["total"], 0)
        self.assertEqual(self.service.insights()["summary"]["localAccepted"], 1)
        self.assertEqual(self.service.insights()["growth"]["xp"], 100)
        self.service.start_training("archive::A")
        self.assertEqual(self.service.workspace()["summary"]["accepted"], 1)

    def test_remove_persists_after_restart_and_old_schema_migrates(self):
        self.completed()
        self.service.remove_training("fixture::A")
        self.service.close()
        self.service = fixtures.TrainingService(self.library, self.db, self.assets, self.judge, self.clock, self.root / "backups")
        self.assertEqual(self.service.workspace()["summary"]["total"], 0)
        self.assertEqual(self.service.insights()["summary"]["localAccepted"], 1)
        self.service.start_training("fixture::A")
        self.service.close()
        import sqlite3
        connection = sqlite3.connect(self.db)
        connection.execute("ALTER TABLE training DROP COLUMN active")
        connection.execute("ALTER TABLE training DROP COLUMN removed_at")
        connection.commit()
        connection.close()
        self.service = fixtures.TrainingService(self.library, self.db, self.assets, self.judge, self.clock, self.root / "backups")
        self.assertEqual(self.service.workspace()["summary"]["accepted"], 1)
        self.assertEqual(len(self.service.submissions()["submissions"]), 1)

    def test_samples_runs_repeated_same_code_do_not_inflate_xp(self):
        self.completed(mode="run")
        self.completed("fixture::H")
        before = self.service.insights()
        self.assertEqual(before["growth"]["xp"], 0)
        self.assertEqual(before["summary"]["submissions"], 1)
        self.completed()
        self.completed()
        self.clock.advance(days=2)
        self.completed()
        after = self.service.insights()
        self.assertEqual(after["growth"]["xp"], 100)
        self.assertEqual(after["summary"]["localAccepted"], 1)
        self.assertEqual(after["summary"]["samplePassed"], 1)
        self.assertEqual(after["activity"][0]["accepted"], 1)
        self.assertEqual(after["assessment"]["rating"], None)

    def test_official_evidence_exact_match_only_no_unknown_tags(self):
        self.library.rows[0]["url"] = "https://codeforces.com/contest/123/problem/A"
        hub = {"accounts": [{"platform": "codeforces", "rating": 1555, "maxRating": 1600, "status": "ready", "solved": [{"url": "https://www.codeforces.com/problemset/problem/123/A?locale=en", "tags": ["INVENTED"], "acceptedAt": "2026-10-08T10:00:00Z"}, {"url": "https://codeforces.com/contest/999/problem/A", "tags": ["UNKNOWN"]}]}]}
        insights = self.service.insights(hub)
        self.assertEqual(insights["summary"]["officialSolved"], 1)
        self.assertEqual(insights["summary"]["active"], 0)
        self.assertEqual(insights["assessment"]["platforms"][0]["rating"], 1555)
        self.assertIsNone(insights["assessment"]["rating"])
        self.assertFalse(any(row["name"] in {"INVENTED", "UNKNOWN"} for row in insights["knowledge"]))
        self.assertEqual(sum(row["officialAccepted"] for row in insights["knowledge"]), 1)

    def test_review_xp_requires_24_hours_and_copied_code_is_not_independent(self):
        self.completed()
        self.clock.advance(hours=23)
        self.completed(code="AC second")
        self.assertEqual(self.service.insights()["growth"]["xp"], 100)
        self.clock.advance(hours=2)
        self.completed(code="AC third")
        self.completed(code="AC fourth")
        self.assertEqual(self.service.insights()["growth"]["xp"], 120)
        self.service.start_training("fixture::B")
        self.service.mark_solution_seen("fixture::B")
        self.completed("fixture::B", code="AC copied")
        self.clock.advance(days=2)
        self.completed("fixture::B", code="AC copied")
        self.assertEqual(self.service.insights()["assessment"]["evidenceCount"], 1)

    def test_independent_estimate_requires_five_excludes_solution_seen(self):
        for identity in ("fixture::A", "fixture::B", "fixture::C", "fixture::D"):
            self.completed(identity)
        self.service.start_training("fixture::E")
        self.service.mark_solution_seen("fixture::E")
        self.completed("fixture::E")
        self.assertIsNone(self.service.insights()["assessment"]["rating"])
        self.completed("fixture::F")
        assessment = self.service.insights()["assessment"]
        self.assertEqual(assessment["evidenceCount"], 5)
        self.assertEqual(assessment["rating"], 1300)


class HubFixture:
    def __init__(self, rows=None):
        self.library = rows or []
        self.closed = False
        self.hub = {"version": "0.3.0", "accounts": [], "settings": {"githubRepo": ""}, "notifications": [], "sync": {"busy": False}, "updates": {"configured": False}}

    def snapshot(self):
        return self.hub

    def configure(self, body):
        self.hub["settings"].update(body)
        return self.snapshot()

    def sync(self, body=None):
        return self.snapshot()

    def dismiss(self, identity):
        return self.snapshot()

    def rows(self):
        return list(self.library)

    def row(self, identity):
        row = next((row for row in self.library if row["id"] == identity), None)
        return {"场次": row["contest"], "题号": row["problem"], "题名": row["title"], "知识点": row["knowledge"], "难度": str(row["difficulty"]), "状态": "未做", "日期": "", "_remote": True, "_id": identity, "_url": row["url"], "_platform": row["platform"], "_series": row["series"]} if row else None

    def close(self):
        self.closed = True


class OverlayHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tb-v3-http-")
        self.root = Path(self.temp.name)
        self.table = self.root / "TB.md"
        self.original = "| 场次 | 题号 | 题名 | 知识点 | 难度 | 状态 | 日期 |\n|---|---|---|---|---|---|---|\n| ABC 478 | D | 原归档 | 排序 | 1100 | 独立AC | 2020-01-01 |\n".encode()
        self.table.write_bytes(self.original)
        self.remote = {"id": "remote:codeforces:123::A", "contest": "CF 123", "problem": "A", "title": "远程题目", "tags": ["排序"], "knowledge": "排序", "difficulty": 1300, "status": "未做", "date": "", "platform": "Codeforces", "series": "Div.4", "queue": None, "url": "https://codeforces.com/contest/123/problem/A", "source": "remote", "solutionAvailable": False, "solutionState": "missing"}
        self.integration = HubFixture([self.remote])
        self.server = backend.create_server(data_file=self.table, data_root=self.root, training_file=self.root / "personal.sqlite", integrations=self.integration, backup_dir=self.root / "backups")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.assertTrue(self.integration.closed)
        self.assertEqual(self.table.read_bytes(), self.original)
        self.temp.cleanup()

    def request(self, path, body=None, token=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-TB-Token"] = self.server.store.token
        connection.request("POST" if body is not None else "GET", path, json.dumps(body).encode() if body is not None else None, headers)
        response = connection.getresponse()
        value = json.loads(response.read())
        status = response.status
        connection.close()
        return status, value

    def test_overlay_fallback_and_missing_solution(self):
        status, data = self.request("/api/data")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["rows"]), 2)
        self.assertFalse(data["rows"][0]["solutionAvailable"])
        self.assertTrue(self.server.store.row(self.remote["id"])["_remote"])
        self.assertEqual(len(self.server.store.raw_rows()), 1)
        status, value = self.request("/api/solution?id=" + quote(self.remote["id"]))
        self.assertEqual((status, value["error"]), (404, "这道题尚未收录题解"))
        self.assertEqual(self.request("/api/training/start", {"id": self.remote["id"]})[0], 200)
        self.assertEqual(self.request("/api/training/remove", {"id": self.remote["id"]})[1]["workspace"]["summary"]["total"], 0)

    def test_hub_http_insights_token_and_official_native_bridge(self):
        self.assertEqual(self.request("/api/hub")[1]["version"], "0.3.0")
        self.assertEqual(self.request("/api/insights")[1]["summary"]["active"], 0)
        self.assertEqual(self.request("/api/hub/configure", {"githubRepo": "owner/repo"}, token=False)[0], 403)
        for endpoint, body in (("configure", {"githubRepo": "owner/repo"}), ("sync", {}), ("dismiss", {"id": "notice"})):
            self.assertEqual(self.request("/api/hub/" + endpoint, body)[0], 200)
        body = {"id": self.remote["id"], "code": "int main(){}"}
        self.assertEqual(self.request("/api/official/open", body)[0], 503)
        calls = []
        self.server.official_opener = lambda url, code, title: calls.append((url, code, title)) or {"sessionId": "native-1", "platform": "codeforces", "url": url, "status": "opened"}
        status, value = self.request("/api/official/open", body)
        self.assertEqual(status, 200)
        self.assertEqual(value["sessionId"], "native-1")
        self.assertEqual(calls[0][0], self.remote["url"])
        self.assertEqual(self.server.training.workspace()["summary"]["total"], 0)
        self.assertEqual(self.request("/api/official/open", dict(body, code="x" * 65537))[0], 400)
        self.server.training.assets = fixtures.Assets(self.server.store)
        plan = self.server.training.preview_contest({"count": 1, "min": 1300, "max": 1300})["plan"]
        self.server.training.start_contest({"ids": [row["id"] for row in plan["slots"]], "duration": 120})
        self.assertEqual(self.request("/api/official/open", body)[0], 403)
        self.assertEqual(len(calls), 1)

    def test_explicit_fixture_disables_network_constructor_unless_overridden(self):
        for override, expected in ((None, False), (True, True)):
            fixture = HubFixture()
            with patch("integrations.IntegrationService", return_value=fixture) as constructor:
                server = backend.create_server(data_file=self.table, data_root=self.root, training_file=self.root / f"fixture-{expected}.sqlite", integration_auto_start=override, backup_dir=self.root / "backups")
                self.assertEqual(constructor.call_args.kwargs["auto_start"], expected)
                server.server_close()

    def test_archive_metadata_cache_and_canonical_dedupe(self):
        _, source = backend.toolutil.contest_paths(str(self.root), "ABC", 478)
        source = Path(source)
        source.parent.mkdir(parents=True)
        content = "# ABC 478\nhttps://atcoder.jp/contests/abc478\n\n## 目录\n| 题号 | 题名 | 考点 | 难度 |\n|---|---|---|---|\n| D | 原归档 | 排序 | 1100 |\n\n## D. 原归档\n正文\n"
        source.write_text(content, encoding="utf-8")
        from archive_import import import_archive
        import_archive(self.server.store.library,self.root,self.table)
        archive = self.server.store.data()["rows"][0]
        self.assertTrue(archive["solutionAvailable"])
        self.integration.library.append(dict(self.remote, id="remote:atcoder:abc478::D", url="http://atcoder.jp/contests/abc478/tasks/abc478_d/?lang=en"))
        data = self.server.store.data()
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual(self.server.store.solution("remote:atcoder:abc478::D")["title"], "原归档")
        source.write_text(content.replace("| D | 原归档 | 排序 | 1100 |", "| C | 其他 | 排序 | 1100 |"), encoding="utf-8")
        self.assertTrue(self.server.store.data()["rows"][0]["solutionAvailable"], "Changing interchange Markdown does not mutate imported SQL content")

    def test_canonical_urls(self):
        self.assertEqual(canonical_url("https://codeforces.com/problemset/problem/123/A?locale=en"), canonical_url(self.remote["url"]))
        self.assertNotEqual(canonical_url(self.remote["url"]), canonical_url("https://codeforces.com/contest/123/problem/B"))


if __name__ == "__main__":
    unittest.main()
