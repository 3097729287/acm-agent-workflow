"""Personal-training tests use temporary tables, databases, clocks, and deterministic judges."""
import datetime as dt
import http.client
import json
from pathlib import Path
import random
import tempfile
import threading
import time
import unittest
from urllib.parse import quote

import backend
from training import TrainingService, ServiceError, UTC


class Clock:
    def __init__(self):
        self.value = dt.datetime(2026, 10, 8, 12, tzinfo=UTC)

    def __call__(self):
        return self.value

    def advance(self, **kwargs):
        self.value += dt.timedelta(**kwargs)


class Library:
    def __init__(self):
        self.rows = [{"id": f"fixture::{chr(65 + i)}", "contest": "fixture", "problem": chr(65 + i), "title": f"题目 {i}", "difficulty": 1000 + i * 150, "tags": [f"知识 {i % 3}"], "knowledge": f"知识 {i % 3}", "status": "独立AC", "date": "2020-01-01", "queue": "review", "platform": "测试"} for i in range(8)]

    def data(self):
        return {"rows": [dict(row) for row in self.rows]}


class Assets:
    def __init__(self, store):
        self.store = store

    def problem(self, identity):
        return {"id": identity, "title": identity, "markdown": "## 原题面\n输入两个整数，输出其和。", "url": "https://example.com/problem", "samples": [{"name": "样例 1", "input": "1 2\n", "output": "3\n"}], "limits": {"timeMs": 1000, "memoryMb": 128}, "judge": {"scope": "samples" if identity.endswith("H") else "local", "label": "测试校验", "cases": 2}, "statementAvailable": True, "referenceCode": "NEVER RETURN THIS"}

    def candidates(self, rows):
        return [dict(row, judgeScope=self.problem(row["id"])["judge"]["scope"]) for row in rows]


class Judge:
    def __init__(self):
        self.release = threading.Event()
        self.started = threading.Event()

    def execute(self, identity, code, mode="submit", input_text="", cancel=None):
        if code.startswith("BLOCK"):
            self.started.set()
            if not self.release.wait(3):
                return {"verdict": "ERROR", "scope": "local", "message": "测试任务超时"}
        verdict = "WA" if "WA" in code else "CE" if "CE" in code else "AC"
        scope = "samples" if identity.endswith("H") else "local"
        return {"verdict": verdict, "scope": scope, "timeMs": 12, "memoryKb": 1024, "passed": 2 if verdict == "AC" else 0, "total": 2, "output": input_text, "stderr": "", "message": "fixture"}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tb-personal-test-")
        self.root = Path(self.temp.name)
        self.library = Library()
        self.clock = Clock()
        self.judge = Judge()
        self.assets = Assets(self.library)
        self.db = self.root / "personal.sqlite3"
        self.service = TrainingService(self.library, self.db, self.assets, self.judge, self.clock, self.root / "backups")

    def tearDown(self):
        self.judge.release.set()
        self.service.close()
        self.temp.cleanup()

    def completed(self, identity="fixture::A", code="AC", **kwargs):
        response = self.service.submit(identity, code, **kwargs)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            result = self.service.submission(response["submission"]["id"])
            if result["submission"]["finishedAt"]:
                return result
            time.sleep(.01)
        self.fail("asynchronous judge did not complete")

    def contest(self, count=6, duration=120):
        plan = self.service.preview_contest({"count": count, "duration": duration, "min": 1000, "max": 2100})["plan"]
        return self.service.start_contest({"ids": [slot["id"] for slot in plan["slots"]], "duration": duration})["contest"]

    def test_initial_empty_no_migration_and_idempotent_start(self):
        self.assertEqual(self.service.workspace()["training"], [])
        self.assertEqual(self.service.workspace()["summary"]["accepted"], 0)
        for _ in range(3):
            self.service.start_training("fixture::A")
        row = self.service.workspace()["training"][0]
        self.assertFalse(row["accepted"])
        self.assertEqual(row["attempts"], 0)
        self.assertIsNone(row["queue"])
        self.assertEqual(self.library.rows[0]["status"], "独立AC")

    def test_open_draft_and_run_are_not_participation(self):
        problem = self.service.problem("fixture::A")
        self.assertNotIn("referenceCode", problem)
        self.service.save_draft("fixture::A", "AC")
        self.assertEqual(self.service.problem("fixture::A")["draft"], "AC")
        result = self.completed(code="AC", mode="run", input_text="1 2")
        self.assertEqual(result["submission"]["verdict"], "RUN_OK")
        self.assertEqual(self.service.workspace()["summary"]["total"], 0)
        self.assertEqual(self.service.workspace()["summary"]["attempts"], 0)
        self.assertEqual(len(self.service.submissions()["submissions"]), 1)

    def test_samples_never_local_acceptance(self):
        result = self.completed("fixture::H", "AC")
        self.assertEqual(result["submission"]["verdict"], "SAMPLE_PASS")
        row = result["workspace"]["training"][0]
        self.assertFalse(row["accepted"])
        self.assertEqual(row["queue"], "verify")
        self.assertEqual(result["workspace"]["summary"]["samplePassed"], 1)

    def test_acceptance_preserved_after_failure_and_attempts_count(self):
        self.completed()
        result = self.completed(code="WA")
        row = result["workspace"]["training"][0]
        self.assertTrue(row["accepted"])
        self.assertEqual(row["verdict"], "WA")
        self.assertEqual(row["queue"], "fill")
        self.assertEqual(row["attempts"], 2)
        self.assertEqual(result["workspace"]["summary"]["accepted"], 1)

    def test_solution_rewrite_and_independent_review_schedule(self):
        self.service.mark_solution_seen("fixture::A")
        self.assertEqual(self.service.workspace()["summary"]["total"], 0)
        self.service.start_training("fixture::A")
        self.service.mark_solution_seen("fixture::A")
        result = self.completed()
        self.assertEqual(result["workspace"]["training"][0]["queue"], "rewrite")
        self.clock.advance(days=1)
        result = self.completed()
        row = result["workspace"]["training"][0]
        self.assertEqual(row["reviewCount"], 1)
        self.assertIsNone(row["queue"])
        self.assertFalse(row["solutionSeen"])
        self.clock.advance(days=29)
        self.assertIsNone(self.service.workspace()["training"][0]["queue"])
        self.clock.advance(days=1)
        self.assertEqual(self.service.workspace()["training"][0]["queue"], "check")

    def test_first_acceptance_due_at_seven_days_not_before(self):
        self.completed()
        self.clock.advance(days=6, hours=23)
        self.assertEqual(self.service.workspace()["summary"]["due"], 0)
        self.clock.advance(hours=1)
        self.assertEqual(self.service.workspace()["training"][0]["queue"], "review")
        self.completed()
        self.completed()
        self.assertEqual(self.service.workspace()["training"][0]["reviewCount"], 1)

    def test_sets_have_no_duplicate_denominator_and_persist(self):
        self.service.start_training("fixture::A")
        for _ in range(2):
            self.service.start_practice_set("fixture")
        self.completed()
        workspace = self.service.workspace()
        self.assertEqual(workspace["summary"]["total"], 8)
        self.assertEqual(len(workspace["sets"]), 1)
        self.assertEqual(workspace["sets"][0]["accepted"], 1)
        self.service.close()
        self.service = TrainingService(self.library, self.db, self.assets, self.judge, self.clock, self.root / "backups")
        self.assertEqual(self.service.workspace()["summary"]["total"], 8)
        self.assertEqual(self.service.workspace()["summary"]["accepted"], 1)
        self.assertTrue(list((self.root / "backups").glob("*.bak")))

    def test_preview_reviewed_ascending_unique_and_no_activation(self):
        preview = self.service.preview_contest({"count": 6, "duration": 120})
        slots = preview["plan"]["slots"]
        self.assertEqual([slot["letter"] for slot in slots], list("ABCDEF"))
        frozen = self.service.previews[tuple(slot["id"] for slot in slots)]["slots"]
        self.assertEqual([slot["difficulty"] for slot in frozen], sorted(slot["difficulty"] for slot in frozen))
        self.assertTrue(all("difficulty" not in slot and "tags" not in slot for slot in slots))
        self.assertEqual(len({slot["id"] for slot in slots}), 6)
        self.assertEqual(self.service.workspace()["summary"]["total"], 0)
        with self.assertRaises(ServiceError):
            self.service.start_contest({"ids": ["fixture::A"], "duration": 120})
        with self.assertRaises(ServiceError):
            self.service.start_contest({"ids": [slot["id"] for slot in slots], "duration": 900})

    def test_contest_isolated_from_prior_ac_and_solution_is_locked(self):
        self.completed()
        contest = self.contest(count=8)
        self.assertEqual(contest["accepted"], 0)
        self.assertEqual(contest["slots"][0]["attempts"], 0)
        self.assertNotIn("difficulty", contest["slots"][0])
        self.assertNotIn("tags", contest["slots"][0])
        self.assertTrue(self.service.problem("fixture::A", contest["id"])["locked"])
        with self.assertRaises(ServiceError) as lock:
            self.service.assert_solution_unlocked("fixture::A")
        self.assertEqual(lock.exception.status, 403)
        with self.assertRaises(ServiceError):
            self.service.submit("fixture::A", "AC")
        result = self.completed(contest_id=contest["id"])
        self.assertEqual(result["workspace"]["activeContest"]["accepted"], 1)
        self.assertEqual(result["workspace"]["summary"]["accepted"], 1)

    def test_deadline_immutable_expiry_no_late_jobs_and_unsolved_due(self):
        contest = self.contest(duration=1)
        original_deadline = contest["deadline"]
        self.clock.advance(seconds=59)
        self.assertEqual(self.service.contest(contest["id"])["contest"]["deadline"], original_deadline)
        self.clock.advance(seconds=1)
        expired = self.service.contest(contest["id"])["contest"]
        self.assertEqual(expired["status"], "finished")
        self.assertEqual(expired["finishedAt"], original_deadline)
        with self.assertRaises(ServiceError):
            self.service.submit(expired["slots"][0]["id"], "AC", contest_id=contest["id"])
        with self.assertRaises(ServiceError):
            self.service.save_draft(expired["slots"][0]["id"], "new code", contest["id"])
        self.assertEqual(self.service.workspace()["summary"]["due"], 6)
        self.assertIn("difficulty", expired["slots"][0])
        self.service.assert_solution_unlocked(expired["slots"][0]["id"])

    def test_accepted_before_deadline_job_finishes_after_expiry(self):
        contest = self.contest(duration=1)
        identity = contest["slots"][0]["id"]
        submission = self.service.submit(identity, "BLOCK AC", contest_id=contest["id"])["submission"]
        self.assertTrue(self.judge.started.wait(1))
        self.clock.advance(minutes=2)
        self.assertEqual(self.service.contest(contest["id"])["contest"]["status"], "finished")
        self.judge.release.set()
        end = time.monotonic() + 3
        while not self.service.submission(submission["id"])["submission"]["finishedAt"] and time.monotonic() < end:
            time.sleep(.01)
        result = self.service.contest(contest["id"])["contest"]
        self.assertEqual(result["accepted"], 1)
        self.assertEqual(self.service.workspace()["summary"]["due"], 5)
        self.assertEqual(result["deadline"], contest["deadline"])

    def test_early_finish_is_idempotent_and_scoped_history_and_drafts(self):
        self.service.save_draft("fixture::A", "single draft")
        contest = self.contest(count=8)
        self.service.save_draft("fixture::A", "contest draft", contest["id"])
        self.completed(contest_id=contest["id"])
        self.completed("fixture::H", "AC", contest_id=contest["id"])
        finished = self.service.finish_contest(contest["id"])["contest"]
        self.assertEqual(finished["accepted"], 1)
        self.assertEqual(sum(slot["samplePassed"] for slot in finished["slots"]), 1)
        self.clock.advance(hours=2)
        self.assertEqual(self.service.finish_contest(contest["id"])["contest"]["finishedAt"], finished["finishedAt"])
        self.assertEqual(self.service.problem("fixture::A")["draft"], "single draft")
        self.assertEqual(self.service.problem("fixture::A", contest["id"])["draft"], "contest draft")
        self.assertEqual(len(self.service.submissions(contest_id=contest["id"])["submissions"]), 2)

    def test_old_code_history_cannot_bypass_running_mock_lock(self):
        old = self.completed()["submission"]
        self.service.save_draft("fixture::A", "old accepted solution")
        contest = self.contest(count=8)
        for read in (lambda: self.service.problem("fixture::A"), lambda: self.service.submissions("fixture::A"), lambda: self.service.submission(old["id"])):
            with self.assertRaises(ServiceError) as error:
                read()
            self.assertEqual(error.exception.status, 403)
        self.assertEqual(self.service.submissions()["submissions"], [])
        self.assertEqual(self.service.problem("fixture::A", contest["id"])["draft"], "")
        self.service.finish_contest(contest["id"])
        self.assertEqual(self.service.submission(old["id"])["submission"]["code"], "AC")

    def test_out_of_order_completion_replays_submission_time(self):
        first = self.service.submit("fixture::A", "BLOCK AC")["submission"]
        self.assertTrue(self.judge.started.wait(1))
        self.clock.advance(days=1)
        second = self.completed()["submission"]
        self.assertNotEqual(first["submittedAt"], second["submittedAt"])
        self.judge.release.set()
        end = time.monotonic() + 3
        while not self.service.submission(first["id"])["submission"]["finishedAt"] and time.monotonic() < end:
            time.sleep(.01)
        row = self.service.workspace()["training"][0]
        self.assertEqual(row["acceptedAt"], first["submittedAt"])
        self.assertEqual(row["reviewCount"], 1)
        self.assertEqual(row["lastSubmittedAt"], second["submittedAt"])

    def test_assets_loading_cannot_accept_a_job_after_deadline(self):
        contest = self.contest(duration=1)
        original = self.assets.problem
        def slow_lookup(identity):
            self.clock.advance(minutes=2)
            return original(identity)
        self.assets.problem = slow_lookup
        with self.assertRaises(ServiceError) as error:
            self.service.submit(contest["slots"][0]["id"], "AC", contest_id=contest["id"])
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.service.workspace()["summary"]["attempts"], 0)

    def test_solution_read_after_receipt_applies_to_future_submission(self):
        self.service.start_training("fixture::A")
        first = self.service.submit("fixture::A", "BLOCK AC")["submission"]
        self.assertTrue(self.judge.started.wait(1))
        self.clock.advance(seconds=1)
        self.service.mark_solution_seen("fixture::A")
        self.judge.release.set()
        end = time.monotonic() + 3
        while not self.service.submission(first["id"])["submission"]["finishedAt"] and time.monotonic() < end:
            time.sleep(.01)
        self.assertTrue(self.service.workspace()["training"][0]["solutionSeen"])
        self.clock.advance(seconds=1)
        row = self.completed()["workspace"]["training"][0]
        self.assertEqual(row["queue"], "rewrite")

    def test_restart_preserves_running_deadline_and_expired_history(self):
        contest = self.contest(duration=1)
        self.service.close()
        self.clock.advance(seconds=30)
        self.service = TrainingService(self.library, self.db, self.assets, self.judge, self.clock, self.root / "backups")
        restored = self.service.active_contest()
        self.assertEqual(restored["deadline"], contest["deadline"])
        self.assertEqual(restored["startedAt"], contest["startedAt"])
        self.clock.advance(seconds=30)
        self.assertIsNone(self.service.active_contest())
        self.assertEqual(self.service.workspace()["contests"][0]["finishedAt"], contest["deadline"])

    def test_pending_job_recovers_after_interrupted_process(self):
        self.service.start_training("fixture::A")
        with self.service._write() as connection:
            connection.execute("INSERT INTO submissions(id,problem_id,mode,code,submitted_at,verdict,scope) VALUES('recovered-job','fixture::A','submit','AC',?,'QUEUED','local')", (self.clock().isoformat().replace("+00:00", "Z"),))
        self.service.close()
        self.service = TrainingService(self.library, self.db, self.assets, self.judge, self.clock, self.root / "backups")
        end = time.monotonic() + 3
        while not self.service.submission("recovered-job")["submission"]["finishedAt"] and time.monotonic() < end:
            time.sleep(.01)
        workspace = self.service.submission("recovered-job")["workspace"]
        self.assertEqual(workspace["summary"]["accepted"], 1)
        self.assertEqual(workspace["summary"]["attempts"], 1)

    def test_preview_refresh_has_difficulty_strata_and_seeded_variation(self):
        self.library.rows = [dict(self.library.rows[0], id=f"fixture-{index}", difficulty=1000 + (index // 3) * 100, tags=[f"topic-{index % 5}"], platform=f"platform-{index % 3}") for index in range(33)]
        self.service.rng = random.Random(1234)
        plans = []
        for _ in range(5):
            slots = self.service.preview_contest({"count": 6, "min": 1000, "max": 2100})["plan"]["slots"]
            plans.append(tuple(slot["id"] for slot in slots))
            frozen = self.service.previews[tuple(slot["id"] for slot in slots)]["slots"]
            difficulties = [slot["difficulty"] for slot in frozen]
            self.assertEqual(difficulties, sorted(difficulties))
            self.assertEqual(len(set(difficulties)), 6)
            self.assertLessEqual(difficulties[0], 1200)
            self.assertGreaterEqual(difficulties[-1], 1900)
        self.assertGreater(len(set(plans)), 1)
        self.service.rng = random.Random(1234)
        repeated = self.service.preview_contest({"count": 6, "min": 1000, "max": 2100})["plan"]["slots"]
        self.assertEqual(tuple(slot["id"] for slot in repeated), plans[0])
        with self.assertRaises(ServiceError) as error:
            self.service.preview_contest({"count": 10, "min": 1000, "max": 1000})
        self.assertEqual(error.exception.status, 422)
        self.assertIn("3", error.exception.message)
        with self.assertRaises(ServiceError) as flat:
            self.service.preview_contest({"count": 3, "min": 1000, "max": 1100})
        self.assertEqual(flat.exception.status, 422)
        self.assertIn("2 档", flat.exception.message)

    def test_asset_wait_does_not_block_workspace_and_pending_is_visible(self):
        original = self.assets.problem
        entered, release = threading.Event(), threading.Event()
        def waiting(identity):
            entered.set()
            release.wait(2)
            return original(identity)
        self.assets.problem = waiting
        worker = threading.Thread(target=lambda: self.service.problem("fixture::A"))
        worker.start()
        self.assertTrue(entered.wait(1))
        started = time.monotonic()
        self.assertEqual(self.service.workspace()["summary"]["total"], 0)
        self.assertLess(time.monotonic() - started, .2)
        release.set()
        worker.join(2)
        self.assets.problem = original
        pending = self.service.submit("fixture::A", "BLOCK AC")["submission"]
        self.assertTrue(self.judge.started.wait(1))
        workspace = self.service.workspace()
        self.assertEqual(workspace["summary"]["pending"], 1)
        self.assertIn(workspace["training"][0]["verdict"], ("QUEUED", "RUNNING"))
        self.judge.release.set()
        end = time.monotonic() + 3
        while not self.service.submission(pending["id"])["submission"]["finishedAt"] and time.monotonic() < end:
            time.sleep(.01)
        self.assertEqual(self.service.workspace()["summary"]["pending"], 0)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tb-personal-http-")
        self.root = Path(self.temp.name)
        self.table = self.root / "TB.md"
        records = [f"| 周赛 164 | {chr(65+i)} | 原题 {i} | 模拟 | {1000+i*150} | 独立AC | 2020-01-01 |" for i in range(8)]
        self.original = ("\ufeff# 原表不能改\r\n| 场次 | 题号 | 题名 | 知识点 | 难度 | 状态 | 日期 |\r\n|---|---|---|---|---|---|---|\r\n" + "\r\n".join(records) + "\r\n").encode()
        self.table.write_bytes(self.original)
        self.clock = Clock()
        self.judge = Judge()
        self.server = backend.create_server(data_file=self.table, data_root=self.root, training_file=self.root / "personal.sqlite3", assets=Assets(None), judge=self.judge, clock=self.clock, backup_dir=self.root / "backups")
        self.server.store.solution = lambda identity: {"markdown": "## 思路\nSECRET SOLUTION", "url": "https://example.com", "title": identity}
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.token = self.server.store.token

    def tearDown(self):
        self.judge.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.assertEqual(self.table.read_bytes(), self.original)
        self.temp.cleanup()

    def request(self, method, path, body=None, token=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=4)
        headers = {"Content-Type": "application/json", "X-TB-Token": token if token is not None else self.token}
        connection.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=headers)
        response = connection.getresponse()
        result = json.loads(response.read())
        status = response.status
        connection.close()
        return status, result

    def test_http_contract_async_polling_empty_state_and_write_security(self):
        status, workspace = self.request("GET", "/api/workspace")
        self.assertEqual(status, 200)
        self.assertEqual(workspace["summary"]["total"], 0)
        self.assertEqual(self.request("POST", "/api/training/start", {"id": "周赛 164::A"}, token="wrong")[0], 403)
        self.assertEqual(self.request("POST", "/api/training/start", ["bad shape"])[0], 400)
        self.assertEqual(self.request("GET", "/api/problem?id=" + quote("周赛 164::A"))[0], 200)
        status, response = self.request("POST", "/api/submissions", {"id": "周赛 164::A", "code": "AC", "mode": "submit"})
        self.assertEqual(status, 200)
        submission_id = response["submission"]["id"]
        end = time.monotonic() + 3
        while time.monotonic() < end:
            status, result = self.request("GET", "/api/submission?id=" + submission_id)
            if result["submission"]["finishedAt"]:
                break
            time.sleep(.01)
        self.assertEqual(result["submission"]["verdict"], "AC")
        self.assertEqual(result["workspace"]["summary"]["accepted"], 1)
        self.assertEqual(self.request("GET", "/api/submissions?id=" + quote("周赛 164::A"))[1]["submissions"][0]["code"], "AC")

    def test_direct_solution_and_legacy_status_lock_and_contest_end(self):
        plan = self.request("POST", "/api/contests/preview", {"count": 6, "duration": 1})[1]["plan"]
        status, response = self.request("POST", "/api/contests/start", {"ids": [slot["id"] for slot in plan["slots"]], "duration": 1, "deadline": "2099-01-01T00:00:00Z"})
        self.assertEqual(status, 200)
        contest = response["contest"]
        identity = contest["slots"][0]["id"]
        self.assertEqual(self.request("GET", "/api/solution?id=" + quote(identity))[0], 403)
        self.assertEqual(self.request("POST", "/api/status", {"id": identity, "status": "巩固", "expected": {"status": "独立AC", "date": "2020-01-01"}})[0], 403)
        self.assertNotIn("difficulty", contest["slots"][0])
        self.clock.advance(minutes=1)
        status, ended = self.request("GET", "/api/contest?id=" + contest["id"])
        self.assertEqual(status, 200)
        self.assertEqual(ended["contest"]["status"], "finished")
        self.assertNotEqual(ended["contest"]["deadline"], "2099-01-01T00:00:00Z")
        self.assertEqual(self.request("POST", "/api/submissions", {"id": identity, "contestId": contest["id"], "code": "AC", "mode": "submit"})[0], 409)
        self.assertEqual(self.request("GET", "/api/solution?id=" + quote(identity))[0], 200)
        self.assertEqual(self.request("GET", "/api/workspace")[1]["summary"]["accepted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
