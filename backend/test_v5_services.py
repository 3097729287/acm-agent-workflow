"""v0.5 evidence, migration, task transactions and real shared-service protocol tests."""
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import unittest
from urllib.request import Request, urlopen

import test_training as fixtures
from training import TrainingService, ServiceError, UTC


class DailyMissionTests(unittest.TestCase):
    setUp = fixtures.ServiceTests.setUp
    tearDown = fixtures.ServiceTests.tearDown
    completed = fixtures.ServiceTests.completed

    def test_actual_unique_passes_only_and_atomic_idempotent_claim(self):
        self.completed(mode="run")
        self.completed("fixture::H")
        self.completed(code="WA")
        self.assertTrue(all(task["progress"] == 0 for task in self.service.daily_tasks()["tasks"]))
        with self.assertRaises(ServiceError): self.service.claim_daily_task("solve-1")
        self.completed()
        before = self.service.insights()["growth"]["xp"]
        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(lambda _: self.service.claim_daily_task("solve-1"), range(8)))
        self.assertEqual(sum(not result["alreadyClaimed"] for result in results), 1)
        self.assertEqual(self.service.insights()["growth"]["xp"], before + 25)
        self.service.close()
        self.service = TrainingService(self.library, self.db, self.assets, self.judge, self.clock, self.root / "backups")
        self.assertTrue(self.service.daily_tasks()["tasks"][0]["claimed"])
        self.assertEqual(self.service.insights()["growth"]["missionXp"], 25)

    def test_harder_tasks_award_more_and_same_problem_cannot_replay_next_day(self):
        self.library.rows[0]["difficulty"] = 2100
        self.completed()
        tasks = {task["id"]: task for task in self.service.daily_tasks()["tasks"]}
        self.assertLess(tasks["solve-1"]["xp"], tasks["hard-1500"]["xp"])
        self.assertLess(tasks["hard-1500"]["xp"], tasks["hard-1800"]["xp"])
        self.assertLess(tasks["hard-1800"]["xp"], tasks["hard-2100"]["xp"])
        for identity in ("solve-1", "hard-1500", "hard-1800", "hard-2100"):
            self.service.claim_daily_task(identity)
        self.assertEqual(self.service.insights()["growth"]["missionXp"], 435)
        self.clock.advance(days=1)
        self.completed(code="AC replay")
        self.assertTrue(all(task["progress"] == 0 for task in self.service.daily_tasks()["tasks"]))
        self.assertEqual(self.service.insights()["growth"]["missionXp"], 435)
        with self.assertRaises(ServiceError): self.service.claim_daily_task("solve-1", "2026-10-08")

    def test_aliases_removals_and_beijing_midnight(self):
        url = "https://codeforces.com/contest/123/problem/A"
        self.library.rows[0]["url"] = url
        self.library.rows[1]["url"] = "https://codeforces.com/problemset/problem/123/A"
        self.clock.value = dt.datetime(2026, 10, 8, 15, 59, tzinfo=UTC)
        self.completed()
        self.completed("fixture::B")
        self.service.remove_training("fixture::A")
        self.assertEqual(self.service.daily_tasks()["tasks"][1]["progress"], 1)
        self.assertEqual(len(self.service._ranking_events("fixture")), 1)
        self.clock.advance(minutes=2)
        self.assertEqual(self.service.daily_tasks()["date"], "2026-10-09")
        self.assertEqual(self.service.daily_tasks()["tasks"][0]["progress"], 0)

    def test_empty_mock_cannot_earn_xp_or_completed_achievement(self):
        plan = self.service.preview_contest({"count": 1})["plan"]
        contest = self.service.start_contest({"ids": [slot["id"] for slot in plan["slots"]], "duration": 120})["contest"]
        self.service.finish_contest(contest["id"])
        value = self.service.insights()
        self.assertEqual(value["growth"]["xp"], 0)
        self.assertFalse(next(item for item in value["achievements"] if item["id"] == "contest-1")["unlocked"])
        self.assertGreater(len(value["achievements"]), 15)

    def test_solution_before_joining_excludes_independent_credit(self):
        self.service.mark_solution_seen("fixture::A")
        self.assertEqual(self.service.workspace()["summary"]["total"], 0)
        self.completed()
        value = self.service.insights()
        self.assertEqual(value["assessment"]["evidenceCount"], 0)
        self.assertEqual(next(task for task in value["dailyTasks"]["tasks"] if task["id"] == "independent-2")["progress"], 0)

    def test_v4_sqlite_upgrade_preserves_all_original_values_and_running_deadline(self):
        self.completed(code="AC original code 你好")
        self.service.save_draft("fixture::A", "int main(){} // 原始草稿")
        plan = self.service.preview_contest({"count": 1, "min": 1150, "max": 1150})["plan"]
        contest = self.service.start_contest({"ids": [slot["id"] for slot in plan["slots"]], "duration": 120})["contest"]
        self.service.close()
        connection = sqlite3.connect(self.db)
        for table in ("daily_missions", "ranking_profile", "ranking_receipts"):
            connection.execute("DROP TABLE " + table)
        connection.execute("ALTER TABLE contests DROP COLUMN config")
        connection.commit()
        tables = ("training", "drafts", "submissions", "practice_sets", "contests")
        columns = {table: [row[1] for row in connection.execute("PRAGMA table_info(" + table + ")")] for table in tables}
        before = {table: connection.execute("SELECT " + ",".join(columns[table]) + " FROM " + table + " ORDER BY rowid").fetchall() for table in tables}
        connection.close()
        self.service = TrainingService(self.library, self.db, self.assets, self.judge, self.clock, self.root / "backups")
        for table in tables:
            after = [tuple(row) for row in self.service.connection.execute("SELECT " + ",".join(columns[table]) + " FROM " + table + " ORDER BY rowid")]
            self.assertEqual(after, before[table])
        self.assertEqual(self.service.active_contest()["deadline"], contest["deadline"])
        self.assertEqual(self.service.problem("fixture::A")["draft"], "int main(){} // 原始草稿")


class MockOptionsTests(unittest.TestCase):
    setUp = fixtures.ServiceTests.setUp
    tearDown = fixtures.ServiceTests.tearDown
    completed = fixtures.ServiceTests.completed

    def test_topic_plateau_and_blind_preview_freeze(self):
        for row in self.library.rows:
            row.update(tags=["排序"] if row["problem"] in "ABC" else ["BFS"], difficulty=1200)
        plan = self.service.preview_contest({"strategy": "topic", "tags": ["排序"], "count": 3, "min": 1200, "max": 1200, "platform": "测试", "reviewedOnly": True})["plan"]
        self.assertEqual(len(plan["slots"]), 3)
        self.assertTrue(all("tags" not in slot and "difficulty" not in slot for slot in plan["slots"]))
        body = {"ids": [slot["id"] for slot in plan["slots"]], "duration": plan["duration"], "previewId": plan["previewId"]}
        with self.assertRaises(ServiceError): self.service.start_contest({**body, "tags": ["BFS"]})
        with self.assertRaises(ServiceError): self.service.start_contest({**body, "topic": "BFS"})
        with self.assertRaises(ServiceError): self.service.start_contest({**body, "mode": "single"})
        with self.assertRaises(ServiceError): self.service.start_contest({**body, "count": 1})
        with self.assertRaises(ServiceError): self.service.start_contest({**body, "previewId": "stale"})
        contest = self.service.start_contest(body)["contest"]
        self.assertEqual(contest["strategy"], "topic")
        self.assertTrue(all("tags" not in slot for slot in contest["slots"]))
        finished = self.service.finish_contest(contest["id"])["contest"]
        self.assertTrue(all(slot["tags"] == ["排序"] and slot["difficulty"] == 1200 for slot in finished["slots"]))

    def test_solved_original_excluded_even_removed_alias_and_changes_reject_start(self):
        self.library.rows[0]["url"] = "https://codeforces.com/contest/123/problem/A"
        self.library.rows[1]["url"] = "https://codeforces.com/problemset/problem/123/A"
        self.completed(); self.service.remove_training("fixture::A")
        plan = self.service.preview_contest({"count": 3, "excludeSolved": True})["plan"]
        self.assertNotIn("fixture::A", [slot["id"] for slot in plan["slots"]])
        self.assertNotIn("fixture::B", [slot["id"] for slot in plan["slots"]])
        self.completed(plan["slots"][0]["id"])
        with self.assertRaises(ServiceError): self.service.start_contest({"ids": [slot["id"] for slot in plan["slots"]], "duration": 120, "previewId": plan["previewId"]})

    def test_strict_platform_tags_reviewed_filter_and_invalid_options(self):
        self.library.rows[0].update(platform="牛客", tags=["素数"])
        self.library.rows[7].update(platform="牛客", tags=["素数"])
        plan = self.service.preview_contest({"mode": "single", "count": 6, "platform": "nowcoder", "tags": ["素数"], "reviewedOnly": True})["plan"]
        self.assertEqual([slot["id"] for slot in plan["slots"]], ["fixture::A"])
        for body in ({"strategy": "topic", "tags": []}, {"excludeSolved": "yes"}, {"tags": "排序"}, {"strategy": "bad"}):
            with self.assertRaises(ServiceError): self.service.preview_contest(body)
        with self.assertRaises(ServiceError): self.service.preview_contest({"count": 2, "platform": "不存在"})


class IdentityAndClientTests(unittest.TestCase):
    setUp = fixtures.ServiceTests.setUp
    tearDown = fixtures.ServiceTests.tearDown
    completed = fixtures.ServiceTests.completed

    def test_uuid_private_token_persist_and_other_install_differs(self):
        profile = self.service.profile()
        self.assertFalse(profile["leaderboard"]["configured"])
        self.assertNotIn("auth_token", json.dumps(profile))
        identity = profile["profile"]["userId"]
        self.service.configure_profile({"nickname": "自己的昵称"})
        self.service.close()
        self.service = TrainingService(self.library, self.db, self.assets, self.judge, self.clock, self.root / "backups")
        self.assertEqual(self.service.profile()["profile"]["userId"], identity)
        self.assertEqual(self.service.profile()["profile"]["nickname"], "自己的昵称")
        other = TrainingService(self.library, self.root / "other.sqlite", self.assets, self.judge, self.clock, self.root / "backups")
        try: self.assertNotEqual(other.profile()["profile"]["userId"], identity)
        finally: other.close()
        for endpoint in ("http://remote.example.com", "https://user:secret@example.com", "https://example.com?key=secret", "ftp://example.com"):
            with self.assertRaises(ServiceError): self.service.configure_profile({"endpoint": endpoint})
        self.assertEqual(self.service.leaderboard.rankings()["entries"], [])

    def test_real_http_worker_and_sqlite_registration_metadata_only_and_auto_sync(self):
        script = Path(__file__).parent.parent / "server" / "leaderboard" / "tests" / "local-server.mjs"
        process = subprocess.Popen(["node", str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            line = process.stdout.readline()
            if not line: self.fail("Worker fixture did not start: " + process.stderr.read())
            endpoint = json.loads(line)["endpoint"]
            self.service.configure_profile({"nickname": "协议测试", "endpoint": endpoint})
            self.completed()
            self.completed("fixture::H")
            self.completed(mode="run")
            until = time.monotonic() + 15
            result = None
            while time.monotonic() < until:
                result = self.service.leaderboard.rankings("total")
                if result["status"] == "ready" and result.get("self", {}).get("count") == 1: break
                if result["status"] == "error": self.fail(result["error"])
                time.sleep(.02)
            self.assertEqual(result["self"]["count"], 1)
            self.assertEqual(result["self"]["nickname"], "协议测试")
            self.assertEqual(self.service._ranking_events(endpoint), [])
            self.service.configure_profile({"nickname": "新的昵称"})
            until = time.monotonic() + 10
            while time.monotonic() < until:
                result = self.service.leaderboard.rankings("total")
                if result["status"] == "ready" and result.get("self", {}).get("nickname") == "新的昵称": break
                time.sleep(.02)
            self.assertEqual(result["self"]["nickname"], "新的昵称")
            self.assertNotIn("code", json.dumps(self.service._ranking_events(endpoint)))
        finally:
            self.service.configure_profile({"endpoint": ""})
            process.terminate(); process.wait(timeout=10)
            process.stdout.close(); process.stderr.close()


class HTTPContractTests(unittest.TestCase):
    setUp = fixtures.HTTPTests.setUp
    tearDown = fixtures.HTTPTests.tearDown
    request = fixtures.HTTPTests.request

    def test_profile_claim_and_rank_endpoints_keep_local_write_token(self):
        status, value = self.request("GET", "/api/profile")
        self.assertEqual(status, 200)
        self.assertFalse(value["leaderboard"]["configured"])
        identity = value["profile"]["userId"]
        self.assertEqual(self.request("POST", "/api/profile", {"nickname": "HTTP 昵称"})[0], 200)
        self.assertEqual(self.request("GET", "/api/profile")[1]["profile"]["userId"], identity)
        self.assertEqual(self.request("GET", "/api/leaderboard?period=total")[1]["entries"], [])
        self.assertEqual(self.request("GET", "/api/leaderboard?period=bad")[0], 400)
        day = self.request("GET", "/api/daily-tasks")[1]["date"]
        self.assertEqual(self.request("POST", "/api/daily-tasks/claim", {"id": "solve-1", "date": day})[0], 409)
        self.assertEqual(self.request("POST", "/api/profile", {"nickname": "bad"}, token=False)[0], 403)

    def test_history_page_bounds_and_complete_total(self):
        service = self.server.training
        for index in range(7):
            value = service.submit("周赛 164::A", "AC " + str(index))["submission"]
            until = time.monotonic() + 4
            while not service.submission(value["id"])["submission"]["finishedAt"] and time.monotonic() < until:
                time.sleep(.01)
        first = self.request("GET", "/api/submissions?limit=3&offset=0")[1]
        second = self.request("GET", "/api/submissions?limit=3&offset=3")[1]
        last = self.request("GET", "/api/submissions?limit=3&offset=6")[1]
        self.assertEqual(first["total"], 7)
        self.assertTrue(first["hasMore"] and second["hasMore"])
        self.assertFalse(last["hasMore"])
        self.assertEqual(len({row["id"] for page in (first, second, last) for row in page["submissions"]}), 7)
        self.assertEqual(self.request("GET", "/api/submissions?limit=101")[0], 400)


if __name__ == "__main__": unittest.main()
