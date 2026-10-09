"""Submission-derived personal training, isolated from the read-only TB archive."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import datetime as dt
import hashlib
import inspect
import json
import logging
from pathlib import Path
import secrets
import sqlite3
import threading
import uuid

UTC = dt.timezone.utc
FAILURES = {"WA", "TLE", "MLE", "RE", "CE", "OLE", "ERROR"}
VERDICTS = FAILURES | {"AC", "SAMPLE_PASS", "RUN_OK", "QUEUED", "RUNNING"}
MAX_CODE = 65_536


class ServiceError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def iso(value):
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class TrainingService:
    def __init__(self, store, db_path, assets=None, judge=None, clock=None, backup_dir=None, rng=None):
        self.store = store
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.clock = clock or (lambda: dt.datetime.now(UTC))
        self.rng = rng or secrets.SystemRandom()
        mirror = str(self.db_path.parent).replace(":", "").replace("\\", "_").replace("/", "_")
        self.backup_dir = Path(backup_dir) if backup_dir else Path(__import__("toolutil").BACKUP_ROOT) / mirror
        existed = self.db_path.exists()
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        if existed:
            self._backup()
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS training (
              id TEXT PRIMARY KEY, active_at TEXT NOT NULL, solution_pending INTEGER NOT NULL DEFAULT 0,
              rewrite_due INTEGER NOT NULL DEFAULT 0, accepted_at TEXT, last_local_at TEXT,
              last_review_at TEXT, review_count INTEGER NOT NULL DEFAULT 0, mock_due INTEGER NOT NULL DEFAULT 0,
              solution_seen_at TEXT, mock_due_at TEXT, mock_due_context TEXT);
            CREATE TABLE IF NOT EXISTS practice_sets (
              id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, ids TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS contests (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL,
              deadline TEXT NOT NULL, finished_at TEXT, duration INTEGER NOT NULL, slots TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS one_running_contest ON contests(status) WHERE status='running';
            CREATE TABLE IF NOT EXISTS drafts (
              problem_id TEXT NOT NULL, context TEXT NOT NULL, code TEXT NOT NULL, saved_at TEXT NOT NULL,
              PRIMARY KEY(problem_id,context));
            CREATE TABLE IF NOT EXISTS submissions (
              id TEXT PRIMARY KEY, problem_id TEXT NOT NULL, contest_id TEXT, mode TEXT NOT NULL,
              code TEXT NOT NULL, submitted_at TEXT NOT NULL, finished_at TEXT, verdict TEXT NOT NULL,
              scope TEXT NOT NULL, time_ms REAL, memory_kb REAL, passed INTEGER NOT NULL DEFAULT 0,
              total INTEGER NOT NULL DEFAULT 0, output TEXT NOT NULL DEFAULT '', stderr TEXT NOT NULL DEFAULT '',
              message TEXT NOT NULL DEFAULT '', custom_input TEXT NOT NULL DEFAULT '', solution_seen INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS submission_problem ON submissions(problem_id,submitted_at);
            CREATE INDEX IF NOT EXISTS submission_contest ON submissions(contest_id,submitted_at);
        """)
        for table, additions in (("training", {"solution_seen_at": "TEXT", "mock_due_at": "TEXT", "mock_due_context": "TEXT", "active": "INTEGER NOT NULL DEFAULT 1", "removed_at": "TEXT"}), ("submissions", {"solution_seen": "INTEGER NOT NULL DEFAULT 0", "sample_run": "INTEGER NOT NULL DEFAULT 0", "case_results": "TEXT NOT NULL DEFAULT '[]'"}), ("contests", {"config": "TEXT NOT NULL DEFAULT '{}'"})):
            columns = {record[1] for record in self.connection.execute(f"PRAGMA table_info({table})")}
            for column, definition in additions.items():
                if column not in columns:
                    self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS daily_missions (
              day TEXT NOT NULL, id TEXT NOT NULL, definition TEXT NOT NULL,
              claimed_at TEXT, awarded_xp INTEGER NOT NULL DEFAULT 0, evidence TEXT NOT NULL DEFAULT '[]',
              PRIMARY KEY(day,id));
            CREATE TABLE IF NOT EXISTS ranking_profile (
              singleton INTEGER PRIMARY KEY CHECK(singleton=1), user_id TEXT NOT NULL UNIQUE,
              nickname TEXT NOT NULL, auth_token TEXT NOT NULL, endpoint TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL, last_synced_at TEXT);
            CREATE TABLE IF NOT EXISTS ranking_receipts (
              endpoint TEXT NOT NULL, event_id TEXT NOT NULL, accepted_at TEXT NOT NULL,
              PRIMARY KEY(endpoint,event_id));
        """)
        from leaderboard import default_endpoint
        from persistence import load_document,save_document
        upgrade_marker=self.db_path.parent/'leaderboard-default-migration.json'
        if not load_document(upgrade_marker,False):
            with self.connection:
                self.connection.execute("UPDATE ranking_profile SET endpoint=? WHERE endpoint=''",(default_endpoint(),))
            save_document(upgrade_marker,True)
        if not self.connection.execute("SELECT 1 FROM ranking_profile WHERE singleton=1").fetchone():
            from leaderboard import default_endpoint
            with self._write() as connection:
                connection.execute("INSERT INTO ranking_profile(singleton,user_id,nickname,auth_token,endpoint,created_at) VALUES(1,?,?,?,?,?)",
                                   (str(uuid.uuid4()), "练习者", secrets.token_urlsafe(32), default_endpoint(), iso(self._now())))
        self.assets = assets
        self.judge = judge
        self.previews = {}
        self.previous_previews = {}
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tb-judge")
        self.closed = False
        self.cancellations = {}
        from leaderboard import LeaderboardClient
        self.leaderboard = LeaderboardClient(self)
        self.leaderboard.queue_sync()
        pending = self.connection.execute("SELECT id FROM submissions WHERE finished_at IS NULL").fetchall()
        for record in pending:
            self._enqueue(record["id"])

    def _now(self):
        value = self.clock()
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    def _backup(self):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        destination = self.backup_dir / f"{self.db_path.name}.{timestamp}.{uuid.uuid4().hex[:6]}.bak"
        backup = sqlite3.connect(destination)
        try:
            self.connection.backup(backup)
        finally:
            backup.close()

    @contextmanager
    def _write(self):
        with self.lock:
            self._backup()
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self.connection
                self.connection.execute("COMMIT")
            except BaseException:
                self.connection.execute("ROLLBACK")
                raise

    def _library(self):
        return self.store.data()["rows"]

    def _row(self, identity):
        if not isinstance(identity, str) or not identity or len(identity) > 512:
            raise ServiceError(400, "题目编号无效")
        rows = [row for row in self._library() if row["id"] == identity]
        if not rows and hasattr(self.store, "row"):
            try:
                raw = self.store.row(identity)
                rows = [self.store.encode_row(raw, self._now().date())]
                rows[0]["id"] = identity
            except Exception as error:
                if getattr(error, "status", None) != 404:
                    raise
        if len(rows) != 1:
            raise ServiceError(404 if not rows else 409, "没有找到唯一对应的题目，请刷新")
        return rows[0]

    def _asset_library(self):
        with self.lock:
            if self.assets is None:
                from assets import AssetLibrary
                self.assets = AssetLibrary(self.store)
            return self.assets

    def _judge(self):
        with self.lock:
            if self.judge is None:
                from judge import Judge
                self.judge = Judge(self._asset_library(), self.db_path.parent / "judge-work")
            return self.judge

    def _activate(self, connection, identity, timestamp):
        connection.execute("INSERT INTO training(id,active_at) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET active=1,removed_at=NULL", (identity, timestamp))
        self._recompute_progress(connection, identity)

    def _identity_map(self, library=None):
        from insights import canonical_url
        rows = list(library if library is not None else self._library())
        extensions = getattr(self.store, "extensions", None)
        if extensions is not None:
            rows += extensions.rows()
        known = {row["id"] for row in rows}
        if hasattr(self.store, "row"):
            for record in self.connection.execute("SELECT id FROM training"):
                if record["id"] not in known:
                    try:
                        raw = self.store.row(record["id"])
                        rows.append(self.store.encode_row(raw, self._now().date()))
                    except Exception as error:
                        if getattr(error, "status", None) != 404:
                            raise
        preferred = {}
        for row in rows:
            key = canonical_url(row.get("url"))
            if key and (key not in preferred or preferred[key].get("source") == "remote" and row.get("source") != "remote"):
                preferred[key] = row
        return {row["id"]: preferred[canonical_url(row.get("url"))]["id"] if canonical_url(row.get("url")) else row["id"] for row in rows}

    def _equivalent_ids(self, identity):
        aliases = self._identity_map()
        canonical = aliases.get(identity, identity)
        return sorted({identity} | {other for other, target in aliases.items() if target == canonical})

    def start_training(self, identity):
        with self.lock:
            self._row(identity)
            if not self.connection.execute("SELECT 1 FROM training WHERE id=? AND active=1", (identity,)).fetchone():
                with self._write() as connection:
                    self._activate(connection, identity, iso(self._now()))
            return {"workspace": self.workspace()}

    def remove_training(self, identity):
        with self.lock:
            self._row(identity)
            try:
                self.assert_solution_unlocked(identity)
            except ServiceError as error:
                if error.status != 403:
                    raise
                raise ServiceError(409, "这道题正在模拟赛中，交卷后才能取消训练") from error
            ids = self._equivalent_ids(identity)
            placeholders = ",".join("?" for _ in ids)
            if self.connection.execute(f"SELECT 1 FROM submissions WHERE problem_id IN ({placeholders}) AND finished_at IS NULL", ids).fetchone():
                raise ServiceError(409, "这道题还有评测任务，请等待结果后取消训练")
            if self.connection.execute(f"SELECT 1 FROM training WHERE id IN ({placeholders}) AND active=1", ids).fetchone():
                with self._write() as connection:
                    connection.execute(f"UPDATE training SET active=0,removed_at=? WHERE id IN ({placeholders})", [iso(self._now())] + ids)
            return {"workspace": self.workspace()}

    def insights(self, hub=None):
        from insights import build_insights
        with self.lock:
            workspace = self.workspace()
            records = [dict(record) for record in self.connection.execute("SELECT * FROM submissions WHERE mode='submit' AND finished_at IS NOT NULL ORDER BY submitted_at,rowid")]
            history = [dict(record) for record in self.connection.execute("SELECT * FROM training")]
            library = self._library()
            known = {row["id"] for row in library}
            for record in history:
                if record["id"] not in known:
                    try:
                        library.append(self._row(record["id"]))
                    except Exception as error:
                        if getattr(error, "status", None) != 404:
                            raise
            value = build_insights(library, records, history, workspace, hub or {}, self._now())
            tasks = self.daily_tasks()
            claimed = self.connection.execute("SELECT COALESCE(SUM(awarded_xp),0) AS xp,COUNT(*) AS count,MAX(claimed_at) AS latest FROM daily_missions WHERE claimed_at IS NOT NULL").fetchone()
            from progression import accepted_evidence, extra_achievements, qualified_contests
            evidence = accepted_evidence(library, records)
            completed = qualified_contests(workspace["contests"], records)
            claimed_dates = [item["claimed_at"] for item in self.connection.execute("SELECT claimed_at FROM daily_missions WHERE claimed_at IS NOT NULL ORDER BY claimed_at,rowid")]
            value["achievements"].extend(extra_achievements(evidence, records, completed, value["summary"]["longestStreak"], claimed_dates))
            xp = value["growth"]["xp"] + claimed["xp"]
            level = xp // 500 + 1
            names = ["初次启程", "持续练习", "稳步积累", "独立攻坚", "长期精进"]
            value["growth"].update(xp=xp, totalXp=xp, missionXp=claimed["xp"], level=level, levelName=names[min(level - 1, len(names) - 1)], currentLevelXp=xp % 500,
                                   nextMilestone=f"再积累 {500 - xp % 500} XP 升至 {level + 1} 级")
            value["dailyTasks"] = tasks
            value["profile"] = self.profile()["profile"]
            return value

    def _evidence(self):
        from progression import accepted_evidence
        rows = self._library()
        known = {row["id"] for row in rows}
        records = [dict(record) for record in self.connection.execute("SELECT * FROM submissions WHERE mode='submit' AND verdict='AC' AND scope='local' AND finished_at IS NOT NULL ORDER BY submitted_at,rowid")]
        for record in records:
            if record["problem_id"] not in known:
                try:
                    rows.append(self._row(record["problem_id"]))
                    known.add(record["problem_id"])
                except Exception as error:
                    if getattr(error, "status", None) != 404:
                        raise
        return accepted_evidence(rows, records)

    def daily_tasks(self):
        from progression import TASKS, SHANGHAI, task_progress
        with self.lock:
            day = self._now().astimezone(SHANGHAI).date().isoformat()
            if not self.connection.execute("SELECT 1 FROM daily_missions WHERE day=?", (day,)).fetchone():
                with self._write() as connection:
                    for task in TASKS:
                        connection.execute("INSERT OR IGNORE INTO daily_missions(day,id,definition) VALUES(?,?,?)", (day, task["id"], json.dumps(task, ensure_ascii=False)))
            evidence = self._evidence()
            tasks = []
            for record in self.connection.execute("SELECT * FROM daily_missions WHERE day=? ORDER BY rowid", (day,)):
                task = json.loads(record["definition"])
                progress, _ = task_progress(task, evidence, day)
                task.update(progress=progress, completed=progress >= task["target"], claimed=bool(record["claimed_at"]), claimedAt=record["claimed_at"])
                tasks.append(task)
            return {"date": day, "timezone": "Asia/Shanghai", "tasks": tasks, "claimable": sum(task["completed"] and not task["claimed"] for task in tasks),
                    "totalClaimedXp": sum(task["xp"] for task in tasks if task["claimed"]), "notice": "每日按北京时间刷新。只计当天首次本地审核通过；样例、运行及重复通过不计入。"}

    def claim_daily_task(self, identity, date=None):
        from progression import task_progress
        if not isinstance(identity, str) or not identity or len(identity) > 64:
            raise ServiceError(400, "每日任务编号无效")
        with self.lock:
            tasks = self.daily_tasks()
            if date is not None and date != tasks["date"]:
                raise ServiceError(409, "每日任务已刷新，请重新打开任务列表")
            record = self.connection.execute("SELECT * FROM daily_missions WHERE day=? AND id=?", (tasks["date"], identity)).fetchone()
            if not record:
                raise ServiceError(404, "没有找到这项每日任务")
            already = bool(record["claimed_at"])
            if not already:
                with self._write() as connection:
                    task = json.loads(record["definition"])
                    progress, evidence = task_progress(task, self._evidence(), tasks["date"])
                    if progress < task["target"]:
                        raise ServiceError(409, "这项任务尚未完成")
                    connection.execute("UPDATE daily_missions SET claimed_at=?,awarded_xp=?,evidence=? WHERE day=? AND id=? AND claimed_at IS NULL",
                                       (iso(self._now()), task["xp"], json.dumps(evidence), tasks["date"], identity))
            insights = self.insights()
            return {"dailyTasks": insights["dailyTasks"], "progression": insights["growth"], "achievements": insights["achievements"], "alreadyClaimed": already}

    def _ranking_profile(self):
        with self.lock:
            return dict(self.connection.execute("SELECT * FROM ranking_profile WHERE singleton=1").fetchone())

    def profile(self):
        record = self._ranking_profile()
        return {"profile": {"userId": record["user_id"], "nickname": record["nickname"], "displayName": record["nickname"] + " #" + record["user_id"], "createdAt": record["created_at"]},
                "leaderboard": self.leaderboard.snapshot()}

    def configure_profile(self, body):
        from leaderboard import validate_endpoint
        with self.lock:
            current = self._ranking_profile()
            nickname = body.get("nickname", current["nickname"])
            if not isinstance(nickname, str) or not 1 <= len(nickname.strip()) <= 32 or any(ord(char) < 32 or ord(char) == 127 for char in nickname):
                raise ServiceError(400, "昵称须为 1–32 个可显示字符")
            endpoint = validate_endpoint(body.get("endpoint", body.get("serverUrl", current["endpoint"])))
            with self._write() as connection:
                connection.execute("UPDATE ranking_profile SET nickname=?,endpoint=?,last_synced_at=CASE WHEN endpoint=? THEN last_synced_at ELSE NULL END WHERE singleton=1",
                                   (nickname.strip(), endpoint, endpoint))
        self.leaderboard.invalidate()
        return self.profile()

    def _ranking_events(self, endpoint):
        with self.lock:
            profile = self._ranking_profile()
            received = {record["event_id"]: record["accepted_at"] for record in self.connection.execute("SELECT event_id,accepted_at FROM ranking_receipts WHERE endpoint=?", (endpoint,))}
            events = []
            for item in self._evidence():
                identity = hashlib.sha256((profile["user_id"] + ":" + item["problemKey"]).encode()).hexdigest()
                if received.get(identity) == item["acceptedAt"]:
                    continue
                events.append({"eventId": identity, "problemKey": item["problemKey"], "acceptedAt": item["acceptedAt"], "difficulty": item["difficulty"], "scope": "local-reviewed"})
            return events

    def _ranking_receipts(self, endpoint, events):
        with self._write() as connection:
            for event in events:
                connection.execute("INSERT INTO ranking_receipts VALUES(?,?,?) ON CONFLICT(endpoint,event_id) DO UPDATE SET accepted_at=excluded.accepted_at", (endpoint, event["eventId"], event["acceptedAt"]))

    def _ranking_synced(self, endpoint):
        with self._write() as connection:
            connection.execute("UPDATE ranking_profile SET last_synced_at=? WHERE singleton=1 AND endpoint=?", (iso(self._now()), endpoint))

    def start_practice_set(self, contest_name):
        if not isinstance(contest_name, str) or not contest_name.strip():
            raise ServiceError(400, "请选择一场原比赛")
        with self.lock:
            rows = [row for row in self._library() if row["contest"] == contest_name]
            if not rows:
                raise ServiceError(404, "这场比赛没有收录题目")
            existing = self.connection.execute("SELECT id FROM practice_sets WHERE name=?", (contest_name,)).fetchone()
            if not existing:
                identity = "practice-" + hashlib.sha256(contest_name.encode()).hexdigest()[:20]
                timestamp = iso(self._now())
                ids = [row["id"] for row in rows]
                with self._write() as connection:
                    connection.execute("INSERT INTO practice_sets VALUES(?,?,?,?)", (identity, contest_name, json.dumps(ids, ensure_ascii=False), timestamp))
                    for problem_id in ids:
                        self._activate(connection, problem_id, timestamp)
            else:
                identity = existing["id"]
                timestamp = iso(self._now())
                ids = [row["id"] for row in rows]
                old_ids = json.loads(self.connection.execute("SELECT ids FROM practice_sets WHERE id=?", (identity,)).fetchone()[0])
                needs_rejoin = any(not self.connection.execute("SELECT 1 FROM training WHERE id=? AND active=1", (problem_id,)).fetchone() for problem_id in ids)
                if needs_rejoin or old_ids != ids:
                    with self._write() as connection:
                        connection.execute("UPDATE practice_sets SET ids=? WHERE id=?", (json.dumps(ids, ensure_ascii=False), identity))
                        for problem_id in ids:
                            self._activate(connection, problem_id, timestamp)
            workspace = self.workspace()
            return {"set": next(item for item in workspace["sets"] if item["id"] == identity), "workspace": workspace}

    def _expire(self):
        now = iso(self._now())
        expired = self.connection.execute("SELECT * FROM contests WHERE status='running' AND deadline<=?", (now,)).fetchall()
        if expired:
            with self._write() as connection:
                for contest in expired:
                    self._finish_record(connection, contest, contest["deadline"])

    def _finish_record(self, connection, contest, finished_at):
        connection.execute("UPDATE contests SET status='finished',finished_at=? WHERE id=? AND status='running'", (finished_at, contest["id"]))
        for slot in json.loads(contest["slots"]):
            solved = connection.execute("SELECT 1 FROM submissions WHERE contest_id=? AND problem_id=? AND mode='submit' AND verdict='AC' AND finished_at IS NOT NULL", (contest["id"], slot["id"])).fetchone()
            if not solved:
                connection.execute("UPDATE training SET mock_due=1,mock_due_at=?,mock_due_context=? WHERE id=?", (finished_at, contest["id"], slot["id"]))

    def _contest_record(self, identity):
        if not isinstance(identity, str) or not identity:
            raise ServiceError(400, "缺少模拟赛编号")
        record = self.connection.execute("SELECT * FROM contests WHERE id=?", (identity,)).fetchone()
        if not record:
            raise ServiceError(404, "没有找到这场模拟赛")
        return record

    def active_contest(self):
        with self.lock:
            self._expire()
            record = self.connection.execute("SELECT * FROM contests WHERE status='running'").fetchone()
            return self._contest(record) if record else None

    def assert_solution_unlocked(self, identity):
        with self.lock:
            self._expire()
            active = self.connection.execute("SELECT slots FROM contests WHERE status='running'").fetchone()
            if active and identity in self._locked_ids(active):
                raise ServiceError(403, "模拟赛进行中，这道题的题解已锁定。交卷后可以复盘。")

    def _locked_ids(self, active):
        """A remote/archive alias must not bypass the same original-question lock."""
        from insights import canonical_url
        slots = json.loads(active["slots"])
        locked = {slot["id"] for slot in slots}
        rows = self._library()
        extensions = getattr(self.store, "extensions", None)
        if extensions is not None:
            rows += extensions.rows()
        metadata = {row["id"]: row for row in rows}
        keys = set()
        for identity in locked:
            row = metadata.get(identity)
            if row is None:
                try:
                    row = self._row(identity)
                except Exception as error:
                    if getattr(error, "status", None) != 404:
                        raise
            key = canonical_url((row or {}).get("url"))
            if key:
                keys.add(key)
        locked.update(row["id"] for row in rows if canonical_url(row.get("url")) in keys)
        return locked

    def mark_solution_seen(self, identity):
        with self.lock:
            ids = self._equivalent_ids(identity)
            placeholders = ",".join("?" for _ in ids)
            record = self.connection.execute(f"SELECT solution_pending FROM training WHERE id IN ({placeholders})", ids).fetchone()
            if record:
                with self._write() as connection:
                    connection.execute(f"UPDATE training SET solution_pending=1,solution_seen_at=? WHERE id IN ({placeholders})", [iso(self._now())] + ids)
            else:
                # Reading a solution before joining still affects independence,
                # while an inactive history row does not enlarge personal training.
                self._row(identity)
                timestamp = iso(self._now())
                with self._write() as connection:
                    connection.execute("INSERT INTO training(id,active_at,active,solution_pending,solution_seen_at) VALUES(?,?,0,1,?)", (identity, timestamp, timestamp))

    def _context(self, identity, contest_id, writing=False):
        self._expire()
        if contest_id:
            contest = self._contest_record(contest_id)
            if not any(slot["id"] == identity for slot in json.loads(contest["slots"])):
                raise ServiceError(403, "这道题不属于该模拟赛")
            if writing and contest["status"] != "running":
                raise ServiceError(409, "模拟赛已经结束，不能继续提交或改写考场草稿")
            return contest
        if writing:
            self.assert_solution_unlocked(identity)
        return None

    def problem(self, identity, contest_id=None):
        with self.lock:
            row = self._row(identity)
            self._context(identity, contest_id)
            self._history_visible(identity, contest_id)
        try:
            raw = self._asset_library().problem(identity)
        except (ValueError, RuntimeError, OSError) as error:
            raise ServiceError(422, "题面资源暂时无法读取：" + str(error)) from error
        with self.lock:
            if self.closed:
                raise ServiceError(503, "服务正在关闭，请稍后重试")
            self._context(identity, contest_id)
            self._history_visible(identity, contest_id)
            allowed = {"id", "title", "markdown", "url", "samples", "limits", "judge", "statementAvailable"}
            problem = {key: raw[key] for key in allowed if key in raw}
            problem.setdefault("id", identity)
            problem.setdefault("title", row["title"])
            problem.setdefault("markdown", None)
            problem.setdefault("url", None)
            problem.setdefault("samples", [])
            problem.setdefault("limits", {"timeMs": 2000, "memoryMb": 256})
            problem.setdefault("judge", {"scope": "samples", "label": "样例校验", "cases": len(problem["samples"])})
            problem.setdefault("statementAvailable", bool(problem["markdown"]))
            try:
                self.assert_solution_unlocked(identity)
                problem["locked"] = False
            except ServiceError as error:
                if error.status != 403:
                    raise
                problem["locked"] = True
            context = contest_id or ""
            ids = self._equivalent_ids(identity)
            placeholders = ",".join("?" for _ in ids)
            draft = self.connection.execute(f"SELECT code FROM drafts WHERE problem_id IN ({placeholders}) AND context=? ORDER BY saved_at DESC LIMIT 1", ids + [context]).fetchone()
            problem["draft"] = draft["code"] if draft else ""
            problem["submissions"] = self.submissions(identity, contest_id, exact_context=True)["submissions"]
            if not problem["locked"]:
                from knowledge import enrich_row
                cache = getattr(self.store, "knowledge_analysis", None)
                analyzed = cache.enrich(row, statement=problem["markdown"]) if cache is not None else enrich_row(row, statement=problem["markdown"])
                problem.update({key: analyzed[key] for key in ("tags", "knowledge", "knowledgeAnalysis") if key in analyzed})
            return problem

    @staticmethod
    def _code(code):
        if not isinstance(code, str) or len(code.encode("utf-8")) > MAX_CODE:
            raise ServiceError(400, "代码必须是文本，且大小不超过 64 KB")
        return code

    def save_draft(self, identity, code, contest_id=None):
        self._code(code)
        with self.lock:
            self._row(identity)
            self._context(identity, contest_id, writing=True)
            context = contest_id or ""
            existing = self.connection.execute("SELECT code,saved_at FROM drafts WHERE problem_id=? AND context=?", (identity, context)).fetchone()
            if existing and existing["code"] == code:
                return {"savedAt": existing["saved_at"]}
            saved_at = iso(self._now())
            with self._write() as connection:
                connection.execute("INSERT INTO drafts VALUES(?,?,?,?) ON CONFLICT(problem_id,context) DO UPDATE SET code=excluded.code,saved_at=excluded.saved_at", (identity, context, code, saved_at))
            return {"savedAt": saved_at}

    def submit(self, identity, code, mode="submit", input_text="", contest_id=None, sample_run=None):
        self._code(code)
        if mode not in ("run", "submit"):
            raise ServiceError(400, "操作类型必须是 run 或 submit")
        if not isinstance(input_text, str) or len(input_text.encode("utf-8")) > MAX_CODE:
            raise ServiceError(400, "运行输入不能超过 64 KB")
        if sample_run is not None and not isinstance(sample_run, bool):
            raise ServiceError(400, "样例运行选项必须是布尔值")
        sample_run = mode == "run" and (not input_text if sample_run is None else sample_run)
        if not code.strip():
            raise ServiceError(400, "请先输入 C++ 代码")
        with self.lock:
            self._row(identity)
            self._context(identity, contest_id, writing=True)
            if self.closed:
                raise ServiceError(503, "判题服务正在关闭，请稍后重试")
            pending = self.connection.execute("SELECT COUNT(*) FROM submissions WHERE finished_at IS NULL").fetchone()[0]
            if pending >= 16:
                raise ServiceError(429, "待判题任务较多，请等待已有提交完成")
        metadata = self._asset_library().problem(identity)
        with self.lock:
            if self.closed:
                raise ServiceError(503, "判题服务正在关闭，请稍后重试")
            pending = self.connection.execute("SELECT COUNT(*) FROM submissions WHERE finished_at IS NULL").fetchone()[0]
            if pending >= 16:
                raise ServiceError(429, "待判题任务较多，请等待已有提交完成")
            scope = metadata.get("judge", {}).get("scope", "samples")
            if scope not in ("local", "samples"):
                scope = "samples"
            submission_id = "submission-" + uuid.uuid4().hex
            # Asset lookups may take time; check the immutable server deadline again at receipt.
            contest = self._context(identity, contest_id, writing=True)
            timestamp = iso(self._now())
            if contest and timestamp >= contest["deadline"]:
                self._expire()
                raise ServiceError(409, "模拟赛已经到时，不能再接收提交")
            ids = self._equivalent_ids(identity)
            placeholders = ",".join("?" for _ in ids)
            training = self.connection.execute(f"SELECT MAX(solution_pending) AS solution_pending FROM training WHERE id IN ({placeholders})", ids).fetchone()
            seen_solution = int(bool(training and training["solution_pending"]))
            with self._write() as connection:
                connection.execute("INSERT INTO submissions(id,problem_id,contest_id,mode,code,submitted_at,verdict,scope,custom_input,solution_seen,sample_run) VALUES(?,?,?,?,?,?,'QUEUED',?,?,?,?)", (submission_id, identity, contest_id or None, mode, code, timestamp, scope, input_text, seen_solution, int(sample_run)))
                if mode == "submit":
                    self._activate(connection, identity, timestamp)
            self._enqueue(submission_id)
            return {"submission": self._submission(self.connection.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone())}

    def _enqueue(self, identity):
        event = threading.Event()
        self.cancellations[identity] = event
        self.executor.submit(self._execute, identity, event)

    def _execute(self, identity, cancel):
        try:
            with self.lock:
                record = self.connection.execute("SELECT * FROM submissions WHERE id=?", (identity,)).fetchone()
                if record is None or record["finished_at"]:
                    return
                with self._write() as connection:
                    connection.execute("UPDATE submissions SET verdict='RUNNING' WHERE id=?", (identity,))
            try:
                execute = self._judge().execute
                options = {"mode": record["mode"], "input_text": record["custom_input"], "cancel": cancel}
                if "sample_run" in inspect.signature(execute).parameters:
                    options["sample_run"] = bool(record["sample_run"])
                result = execute(record["problem_id"], record["code"], **options)
            except Exception:
                logging.exception("TB judge execution failed")
                result = {"verdict": "ERROR", "scope": record["scope"], "message": "判题未完成，请检查本地编译器后重试"}
            if not isinstance(result, dict):
                result = {"verdict": "ERROR", "scope": record["scope"], "message": "判题结果格式无效"}
            verdict = result.get("verdict", "ERROR")
            scope = result.get("scope", record["scope"])
            if scope not in ("local", "samples"):
                scope = "samples"
            if verdict not in VERDICTS or verdict in ("QUEUED", "RUNNING"):
                verdict = "ERROR"
            if verdict == "AC" and (scope != "local" or record["mode"] == "run"):
                verdict = "RUN_OK" if record["mode"] == "run" and not record["sample_run"] else "SAMPLE_PASS"
            case_results = self._case_results(result.get("caseResults", []))
            finished = iso(self._now())
            with self.lock:
                with self._write() as connection:
                    connection.execute("UPDATE submissions SET finished_at=?,verdict=?,scope=?,time_ms=?,memory_kb=?,passed=?,total=?,output=?,stderr=?,message=?,case_results=? WHERE id=?", (finished, verdict, scope, result.get("timeMs"), result.get("memoryKb"), max(0, int(result.get("passed", 0))), max(0, int(result.get("total", 0))), str(result.get("output", ""))[:262144], str(result.get("stderr", ""))[:262144], str(result.get("message", ""))[:4000], json.dumps(case_results, ensure_ascii=False), identity))
                    if record["mode"] == "submit" and verdict == "AC":
                        self._recompute_progress(connection, record["problem_id"])
                self._expire()
            if record["mode"] == "submit" and verdict == "AC" and scope == "local":
                self.leaderboard.queue_sync()
        except Exception:
            logging.exception("TB submission persistence failed")
            # Persist an explicit terminal failure where possible; never leave a poller hanging.
            try:
                with self._write() as connection:
                    connection.execute("UPDATE submissions SET verdict='ERROR',finished_at=?,message=? WHERE id=? AND finished_at IS NULL", (iso(self._now()), "判题记录未能完整保存，请重试", identity))
            except Exception:
                logging.exception("TB could not persist terminal failure")
        finally:
            with self.lock:
                self.cancellations.pop(identity, None)

    def _recompute_progress(self, connection, identity):
        """Replay immutable received submissions, so asynchronous completion order is harmless."""
        ids = self._equivalent_ids(identity)
        placeholders = ",".join("?" for _ in ids)
        training_rows = connection.execute(f"SELECT * FROM training WHERE id IN ({placeholders})", ids).fetchall()
        accepted = connection.execute(f"SELECT * FROM submissions WHERE problem_id IN ({placeholders}) AND mode='submit' AND verdict='AC' AND finished_at IS NOT NULL ORDER BY submitted_at,rowid", ids).fetchall()
        if not training_rows or not accepted:
            return
        first, last = accepted[0], accepted[-1]
        cursor, review_at, reviews = first["submitted_at"], None, 0
        for submission in accepted[1:]:
            if not submission["solution_seen"] and (parse_time(submission["submitted_at"]) - parse_time(cursor)).total_seconds() >= 86400:
                reviews += 1
                cursor = review_at = submission["submitted_at"]
        for training in training_rows:
            pending = bool(training["solution_seen_at"] and training["solution_seen_at"] > last["submitted_at"])
            mock_due = training["mock_due"]
            if mock_due and any(submission["contest_id"] == training["mock_due_context"] or not training["mock_due_at"] or submission["submitted_at"] >= training["mock_due_at"] for submission in accepted):
                mock_due = 0
            connection.execute("UPDATE training SET accepted_at=?,last_local_at=?,last_review_at=?,review_count=?,rewrite_due=?,solution_pending=?,mock_due=? WHERE id=?", (first["submitted_at"], last["submitted_at"], review_at, reviews, last["solution_seen"], int(pending), mock_due, training["id"]))

    @staticmethod
    def _case_results(values):
        if not isinstance(values, list):
            return []
        results, budget = [], 262144
        for value in values[:100]:
            if not isinstance(value, dict):
                continue
            case = {"name": str(value.get("name", "测试"))[:100], "input": "", "expected": None, "actual": "", "verdict": value.get("verdict") if value.get("verdict") in VERDICTS else "ERROR", "timeMs": value.get("timeMs"), "exitCode": value.get("exitCode"), "message": str(value.get("message", ""))[:500]}
            for field in ("input", "expected", "actual"):
                if value.get(field) is None and field == "expected":
                    continue
                raw = str(value.get(field, "")).encode("utf-8")[:min(65536, max(0, budget))]
                case[field] = raw.decode("utf-8", "ignore")
                budget -= len(raw)
            results.append(case)
        return results

    @staticmethod
    def _submission(record):
        return {"id": record["id"], "problemId": record["problem_id"], "contestId": record["contest_id"], "mode": record["mode"], "verdict": record["verdict"], "scope": record["scope"], "code": record["code"], "submittedAt": record["submitted_at"], "finishedAt": record["finished_at"], "timeMs": record["time_ms"], "memoryKb": record["memory_kb"], "passed": record["passed"], "total": record["total"], "output": record["output"], "stderr": record["stderr"], "message": record["message"], "sampleRun": bool(record["sample_run"]), "caseResults": json.loads(record["case_results"])}

    def submission(self, identity):
        with self.lock:
            self._expire()
            record = self.connection.execute("SELECT * FROM submissions WHERE id=?", (identity,)).fetchone()
            if not record:
                raise ServiceError(404, "没有找到这次提交")
            self._history_visible(record["problem_id"], record["contest_id"])
            result = {"submission": self._submission(record)}
            if record["finished_at"]:
                result["workspace"] = self.workspace()
            return result

    def submissions(self, identity=None, contest_id=None, exact_context=False, limit=100, offset=0):
        try:
            limit, offset = int(limit), int(offset)
        except (ValueError, TypeError):
            raise ServiceError(400, "提交记录分页参数无效")
        if not 1 <= limit <= 100 or offset < 0:
            raise ServiceError(400, "每页提交记录须为 1–100 条，偏移量不能为负")
        with self.lock:
            self._expire()
            active = self.connection.execute("SELECT id,slots FROM contests WHERE status='running'").fetchone()
            locked = self._locked_ids(active) if active else set()
            if identity:
                self._history_visible(identity, contest_id)
            clauses, values = [], []
            if identity:
                ids = self._equivalent_ids(identity)
                clauses.append("problem_id IN (" + ",".join("?" for _ in ids) + ")")
                values.extend(ids)
            if contest_id:
                self._contest_record(contest_id)
                clauses.append("contest_id=?")
                values.append(contest_id)
            elif exact_context:
                clauses.append("contest_id IS NULL")
            if locked:
                clauses.append("(problem_id NOT IN (" + ",".join("?" for _ in locked) + ") OR contest_id=?)")
                values.extend(sorted(locked))
                values.append(active["id"])
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            total = self.connection.execute("SELECT COUNT(*) FROM submissions" + where, values).fetchone()[0]
            records = self.connection.execute("SELECT * FROM submissions" + where + " ORDER BY submitted_at DESC,rowid DESC LIMIT ? OFFSET ?", values + [limit, offset]).fetchall()
            return {"submissions": [self._submission(record) for record in records], "total": total, "offset": offset, "limit": limit, "hasMore": offset + len(records) < total}

    def _history_visible(self, identity, context):
        active = self.connection.execute("SELECT id,slots FROM contests WHERE status='running'").fetchone()
        if active and context != active["id"] and identity in self._locked_ids(active):
            raise ServiceError(403, "这道题正在模拟赛中，请从当前考场打开；旧草稿和提交记录赛后恢复。")

    def _contest_options(self, body):
        if not isinstance(body, dict):
            raise ServiceError(400, "模拟赛参数无效")
        strategy = body.get("strategy", body.get("mode", "comprehensive"))
        if strategy not in ("comprehensive", "topic", "single"):
            raise ServiceError(400, "训练方式须为综合、专项或单题")
        tags = body.get("tags", [])
        topic = body.get("topic")
        if topic is not None:
            if not isinstance(topic, str):
                raise ServiceError(400, "专项知识点无效")
            if topic.strip():
                tags = [topic.strip()] if not tags else tags
        if not isinstance(tags, list) or len(tags) > 20 or not all(isinstance(tag, str) and 0 < len(tag.strip()) <= 80 for tag in tags):
            raise ServiceError(400, "请选择有效的专项知识点")
        tags = sorted(set(tag.strip() for tag in tags))
        if strategy == "topic" and not tags:
            raise ServiceError(400, "专项训练须选择至少一个知识点")
        platform = body.get("platform", "") or ""
        if not isinstance(platform, str) or len(platform) > 80:
            raise ServiceError(400, "题目平台无效")
        switches = {}
        for key in ("excludeSolved", "reviewedOnly"):
            value = body.get(key, False)
            if not isinstance(value, bool):
                raise ServiceError(400, "模拟赛筛选选项须为布尔值")
            switches[key] = value
        return {"strategy": strategy, "tags": tags, "platform": platform.strip(), **switches}

    def _solved_problem_keys(self, rows):
        from insights import canonical_url
        accepted = {item["key"] for item in self._evidence()}
        extensions = getattr(self.store, "extensions", None)
        if extensions is not None:
            snapshot = getattr(extensions, "snapshot", None)
            if callable(snapshot):
                for account in snapshot().get("accounts", []):
                    accepted.update(key for item in account.get("solved", []) if (key := canonical_url(item.get("url"))))
        return accepted

    @staticmethod
    def _eligible_contest_row(row, options, lower, upper, solved):
        from insights import canonical_url
        difficulty = row.get("difficulty")
        if not isinstance(difficulty, (int, float)) or isinstance(difficulty, bool) or not lower <= difficulty <= upper:
            return False
        aliases = {"codeforces": "codeforces", "atcoder": "atcoder", "nowcoder": "牛客", "luogu": "洛谷"}
        platform = options["platform"].casefold()
        platform = aliases.get(platform, platform)
        if platform and platform != str(row.get("platform", "")).casefold():
            return False
        if options["tags"] and not set(options["tags"]) & set(row.get("tags", [])):
            return False
        if options["excludeSolved"] and (canonical_url(row.get("url")) or row["id"]) in solved:
            return False
        return not options["reviewedOnly"] or row.get("judgeScope") == "local"

    def preview_contest(self, body):
        options = self._contest_options(body)
        try:
            count = 1 if options["strategy"] == "single" else int(body.get("count", 6))
            duration = int(body.get("duration", 120))
            lower, upper = int(body.get("min", 1000)), int(body.get("max", 2100))
        except (ValueError, TypeError, AttributeError):
            raise ServiceError(400, "模拟赛参数无效")
        if not 1 <= count <= 10 or not 1 <= duration <= 360 or not 0 <= lower <= upper <= 5000:
            raise ServiceError(400, "题数须为 1–10，时长须为 1–360 分钟，难度上下限须有效")
        with self.lock:
            rows = self._library()
            active = {record["id"]: bool(record["accepted_at"]) for record in self.connection.execute("SELECT id,accepted_at FROM training WHERE active=1")}
            solved = self._solved_problem_keys(rows) if options["excludeSolved"] else set()
        eligible = self._asset_library().candidates(rows)
        with self.lock:
            seen = set()
            from insights import canonical_url
            eligible = [row for row in eligible if self._eligible_contest_row(row, options, lower, upper, solved)
                        and not ((canonical_url(row.get("url")) or row["id"]) in seen or seen.add(canonical_url(row.get("url")) or row["id"]))]
            available = len(eligible)
            if available < count:
                raise ServiceError(422, f"当前范围只有 {available} 道具备原题面和样例的题目，无法组成 {count} 题模拟赛。请扩大难度范围或减少题数。")
            levels = len({row["difficulty"] for row in eligible})
            if options["strategy"] == "comprehensive" and levels < count:
                raise ServiceError(422, f"当前可用题目只有 {levels} 档不同难度，无法组成 {count} 题递进模拟赛。请扩大难度范围或减少题数。")
            chosen, covered, main_tags, platforms = [], set(), set(), set()
            pool = list(eligible)
            random_rank = {row["id"]: self.rng.random() for row in eligible}
            band_width = max(100, (upper - lower) / count * .65)
            for index in range(count):
                center = lower + (upper - lower) * ((index + .5) / count)
                selected_difficulties = {row["difficulty"] for row in chosen}
                def score(row):
                    tags = row.get("tags", [])
                    main = tags[0] if tags else ""
                    fit = int(abs(row["difficulty"] - center) / band_width)
                    return (row["difficulty"] in selected_difficulties, fit + (0 if row.get("judgeScope") == "local" else 2), bool(main and main in main_tags), active.get(row["id"], False), row["id"] in active, row.get("platform") in platforms, random_rank[row["id"]] - .06 * min(3, len(set(tags) - covered)), abs(row["difficulty"] - center), row["id"])
                eligible.sort(key=score)
                row = eligible.pop(0)
                chosen.append(row)
                covered.update(row.get("tags", []))
                if row.get("tags"):
                    main_tags.add(row["tags"][0])
                platforms.add(row.get("platform"))
            # When the reviewed pool permits, include a DP problem, a graph problem,
            # and a basic technique without flattening the difficulty progression.
            def families(row):
                tags = row.get("tags", [])
                result = set()
                if any("DP" in tag or "动态规划" in tag for tag in tags):
                    result.add("dp")
                if any(tag in {"图论", "BFS", "拓扑排序", "差分约束", "最短路", "并查集", "树", "树形 DP"} for tag in tags):
                    result.add("graph")
                if any(tag in {"模拟", "枚举", "贪心", "排序", "前缀和", "差分", "二分查找", "双指针"} for tag in tags):
                    result.add("basic")
                return result
            required = {family for family in ("dp", "graph", "basic") if options["strategy"] == "comprehensive" and count >= 3 and any(row.get("judgeScope") == "local" and family in families(row) for row in pool)}
            for family in ("dp", "graph", "basic"):
                if family not in required or any(family in families(row) for row in chosen):
                    continue
                options = []
                for replacement in pool:
                    if replacement in chosen or family not in families(replacement) or replacement.get("judgeScope") != "local":
                        continue
                    for index, current in enumerate(chosen):
                        alternate = chosen[:index] + [replacement] + chosen[index + 1:]
                        if len({row["difficulty"] for row in alternate}) != len({row["difficulty"] for row in chosen}):
                            continue
                        protected = required & set().union(*(families(row) for row in chosen))
                        if not protected <= set().union(*(families(row) for row in alternate)):
                            continue
                        options.append((int(abs(replacement["difficulty"] - current["difficulty"]) / band_width), random_rank[replacement["id"]], index, replacement))
                if options:
                    _, _, index, replacement = min(options, key=lambda option: option[:3])
                    chosen[index] = replacement
            chosen.sort(key=lambda row: (row["difficulty"], row["id"]))
            preview_key = (count, duration, lower, upper, json.dumps(options, sort_keys=True, ensure_ascii=False))
            previous = self.previous_previews.get(preview_key)
            if previous == tuple(row["id"] for row in chosen):
                alternatives = []
                protected = required & set().union(*(families(row) for row in chosen))
                for replacement in pool:
                    if replacement in chosen:
                        continue
                    for index, current in enumerate(chosen):
                        if current.get("judgeScope") == "local" and replacement.get("judgeScope") != "local":
                            continue
                        if abs(replacement["difficulty"] - current["difficulty"]) > band_width * 1.5:
                            continue
                        alternate = chosen[:index] + [replacement] + chosen[index + 1:]
                        if len({row["difficulty"] for row in alternate}) != len({row["difficulty"] for row in chosen}) or not protected <= set().union(*(families(row) for row in alternate)):
                            continue
                        alternatives.append((random_rank[replacement["id"]], index, replacement))
                if alternatives:
                    _, index, replacement = min(alternatives, key=lambda option: option[:2])
                    chosen[index] = replacement
                    chosen.sort(key=lambda row: (row["difficulty"], row["id"]))
            self.previous_previews[preview_key] = tuple(row["id"] for row in chosen)
            slots = [{"letter": chr(65 + index), "id": row["id"], "title": row["title"], "difficulty": row["difficulty"], "tags": row.get("tags", []), "judgeScope": row.get("judgeScope", "samples")} for index, row in enumerate(chosen)]
            name = f"模拟赛 · {len(slots)} 题 / {duration} 分钟"
            # The server retains full metadata, but the random preview stays blind.
            public_slots = [{key: slot[key] for key in ("letter", "id", "title", "judgeScope")} for slot in slots]
            plan = {"previewId": uuid.uuid4().hex, "name": name, "slots": public_slots, "duration": duration, "min": lower, "max": upper, "strategy": options["strategy"], "constraints": options}
            self.previews[tuple(slot["id"] for slot in slots)] = {"plan": plan, "slots": slots, "at": self._now()}
            while len(self.previews) > 20:
                self.previews.pop(next(iter(self.previews)))
            return {"plan": plan, "available": available}

    def start_contest(self, body):
        ids = body.get("ids")
        if not isinstance(ids, list) or not ids or len(ids) > 10 or not all(isinstance(identity, str) for identity in ids) or len(set(ids)) != len(ids):
            raise ServiceError(400, "请选择 1–10 道不重复的模拟赛题目")
        try:
            duration = int(body.get("duration", 120))
        except (ValueError, TypeError):
            raise ServiceError(400, "模拟赛时长无效")
        with self.lock:
            self._expire()
            if self.connection.execute("SELECT 1 FROM contests WHERE status='running'").fetchone():
                raise ServiceError(409, "已有一场模拟赛正在进行，请先回到考场或交卷")
            preview = self.previews.get(tuple(ids))
            if not preview or duration != preview["plan"]["duration"] or (self._now() - preview["at"]).total_seconds() > 1800:
                raise ServiceError(409, "选题预览已变化或过期，请重新生成并确认")
            if "previewId" in body and body["previewId"] != preview["plan"]["previewId"]:
                raise ServiceError(409, "选题预览已更新，请使用当前预览")
            options = preview["plan"]["constraints"]
            if any(key in body for key in ("strategy", "mode", "tags", "topic", "platform", "excludeSolved", "reviewedOnly")):
                requested_body = {**options, **body}
                if "mode" in body and "strategy" not in body:
                    requested_body["strategy"] = body["mode"]
                if "topic" in body and "tags" not in body:
                    requested_body["tags"] = []
                requested = self._contest_options(requested_body)
                if requested != options:
                    raise ServiceError(409, "筛选条件已变化，请重新生成题目")
            if "count" in body and body["count"] != len(ids):
                raise ServiceError(409, "题数已变化，请重新生成题目")
            for key in ("min", "max"):
                if key in body and body[key] != preview["plan"][key]:
                    raise ServiceError(409, "难度条件已变化，请重新生成题目")
            solved = self._solved_problem_keys(self._library()) if options["excludeSolved"] else set()
            current_rows = {row["id"]: row for row in self._asset_library().candidates([self._row(identity) for identity in ids])}
            for identity in ids:
                row = current_rows.get(identity)
                if row is None:
                    raise ServiceError(409, "原题面或评测资料已变化，请重新生成题目")
                if not self._eligible_contest_row(row, options, preview["plan"]["min"], preview["plan"]["max"], solved):
                    raise ServiceError(409, "题目资料或通过状态已变化，请重新生成题目")
            name = body.get("name") or preview["plan"]["name"]
            if not isinstance(name, str) or len(name) > 100:
                raise ServiceError(400, "模拟赛名称过长")
            now = self._now()
            timestamp = iso(now)
            deadline = iso(now + dt.timedelta(minutes=duration))
            identity = "contest-" + uuid.uuid4().hex
            with self._write() as connection:
                connection.execute("INSERT INTO contests(id,name,status,started_at,deadline,finished_at,duration,slots,config) VALUES(?,?,'running',?,?,NULL,?,?,?)", (identity, name, timestamp, deadline, duration, json.dumps(preview["slots"], ensure_ascii=False), json.dumps(options, ensure_ascii=False)))
                for problem_id in ids:
                    self._activate(connection, problem_id, timestamp)
            self.previews.pop(tuple(ids), None)
            return {"contest": self._contest(self._contest_record(identity)), "workspace": self.workspace()}

    def _contest(self, record):
        records = self.connection.execute("SELECT * FROM submissions WHERE contest_id=? AND mode='submit' ORDER BY submitted_at,rowid", (record["id"],)).fetchall()
        by_problem = {}
        for submission in records:
            by_problem.setdefault(submission["problem_id"], []).append(submission)
        slots, penalty = [], 0
        for frozen in json.loads(record["slots"]):
            attempts = by_problem.get(frozen["id"], [])
            accepted = next((submission for submission in attempts if submission["finished_at"] and submission["verdict"] == "AC"), None)
            latest = attempts[-1] if attempts else None
            slot = {"letter": frozen["letter"], "id": frozen["id"], "title": frozen["title"], "accepted": accepted is not None, "verdict": latest["verdict"] if latest else None, "samplePassed": any(submission["verdict"] == "SAMPLE_PASS" for submission in attempts), "attempts": len(attempts), "solvedAt": accepted["submitted_at"] if accepted else None}
            if record["status"] == "finished":
                slot.update({key: frozen[key] for key in ("difficulty", "tags", "judgeScope")})
            if accepted:
                minutes = int((parse_time(accepted["submitted_at"]) - parse_time(record["started_at"])).total_seconds() // 60)
                failures = sum(submission["verdict"] in (FAILURES - {"CE", "ERROR"}) for submission in attempts[:attempts.index(accepted)])
                penalty += max(0, minutes) + 20 * failures
            slots.append(slot)
        until = parse_time(record["finished_at"] or record["deadline"])
        elapsed = max(0, int((min(self._now(), until) - parse_time(record["started_at"])).total_seconds()))
        config = json.loads(record["config"] or "{}")
        return {"id": record["id"], "name": record["name"], "status": record["status"], "startedAt": record["started_at"], "deadline": record["deadline"], "finishedAt": record["finished_at"], "duration": record["duration"], "slots": slots, "accepted": sum(slot["accepted"] for slot in slots), "total": len(slots), "penalty": penalty, "elapsedSeconds": elapsed, "strategy": config.get("strategy", "comprehensive"), "constraints": config}

    def contest(self, identity):
        with self.lock:
            self._expire()
            return {"contest": self._contest(self._contest_record(identity)), "now": iso(self._now())}

    def finish_contest(self, identity):
        with self.lock:
            self._expire()
            record = self._contest_record(identity)
            if record["status"] == "running":
                with self._write() as connection:
                    self._finish_record(connection, record, iso(self._now()))
            return {"contest": self._contest(self._contest_record(identity)), "workspace": self.workspace()}

    def workspace(self):
        with self.lock:
            self._expire()
            library = {row["id"]: row for row in self._library()}
            aliases = self._identity_map(list(library.values()))
            records = self.connection.execute("SELECT * FROM submissions WHERE mode='submit' ORDER BY submitted_at,rowid").fetchall()
            grouped = {}
            for submission in records:
                grouped.setdefault(aliases.get(submission["problem_id"], submission["problem_id"]), []).append(submission)
            running = self.connection.execute("SELECT * FROM contests WHERE status='running'").fetchone()
            locked = self._locked_ids(running) if running else set()
            now = self._now()
            training = []
            for record in self.connection.execute("SELECT * FROM training WHERE active=1 ORDER BY active_at,id"):
                canonical = aliases.get(record["id"], record["id"])
                attempts = grouped.get(canonical, [])
                completed = [submission for submission in attempts if submission["finished_at"]]
                latest = completed[-1] if completed else None
                accepted_at = next((submission["submitted_at"] for submission in completed if submission["verdict"] == "AC"), record["accepted_at"])
                accepted = bool(accepted_at)
                queue = None
                if canonical not in locked:
                    if latest and latest["verdict"] in FAILURES or record["mock_due"]:
                        queue = "fill"
                    elif record["rewrite_due"]:
                        queue = "rewrite"
                    elif latest and latest["verdict"] == "SAMPLE_PASS" and not accepted:
                        queue = "verify"
                    elif accepted and record["review_count"]:
                        if (now - parse_time(record["last_review_at"])).total_seconds() >= 30 * 86400:
                            queue = "check"
                    elif accepted and (now - parse_time(accepted_at)).total_seconds() >= 7 * 86400:
                        queue = "review"
                source = library.get(canonical)
                if source is None:
                    try:
                        source = self._row(record["id"])
                    except Exception as error:
                        if getattr(error, "status", None) != 404:
                            raise
                item = dict(source or {"id": record["id"], "title": record["id"], "contest": "", "problem": "", "difficulty": None, "tags": [], "knowledge": "", "platform": ""})
                last_attempt = attempts[-1] if attempts else None
                item.update({"id": canonical, "accepted": accepted, "verdict": last_attempt["verdict"] if last_attempt else None, "scope": "local" if accepted else last_attempt["scope"] if last_attempt else None, "attempts": len(attempts), "acceptedAt": accepted_at, "lastSubmittedAt": attempts[-1]["submitted_at"] if attempts else None, "queue": queue, "reviewCount": record["review_count"], "solutionSeen": bool(record["solution_pending"] or record["rewrite_due"]), "activeAt": record["active_at"]})
                if canonical in locked:
                    item.update({"difficulty": None, "tags": [], "knowledge": ""})
                training.append(item)
            merged = {}
            for item in training:
                previous = merged.get(item["id"])
                if previous:
                    previous["queue"] = previous["queue"] or item["queue"]
                    previous["solutionSeen"] = previous["solutionSeen"] or item["solutionSeen"]
                    previous["reviewCount"] = max(previous["reviewCount"], item["reviewCount"])
                else:
                    merged[item["id"]] = item
            training = list(merged.values())
            accepted_ids = {item["id"] for item in training if item["accepted"]}
            active_ids = {item["id"] for item in training}
            sets = []
            for record in self.connection.execute("SELECT * FROM practice_sets ORDER BY created_at DESC,id"):
                ids = list(dict.fromkeys(aliases.get(problem_id, problem_id) for problem_id in json.loads(record["ids"]) if aliases.get(problem_id, problem_id) in active_ids))
                if ids:
                    sets.append({"id": record["id"], "name": record["name"], "type": "practice", "ids": ids, "createdAt": record["created_at"], "accepted": len(set(ids) & accepted_ids), "total": len(set(ids))})
            contests = [self._contest(record) for record in self.connection.execute("SELECT * FROM contests ORDER BY started_at DESC,rowid DESC")]
            days = {parse_time(record["submitted_at"]).astimezone().date() for record in records}
            day = now.astimezone().date()
            if day not in days:
                day -= dt.timedelta(days=1)
            streak = 0
            while day in days:
                streak += 1
                day -= dt.timedelta(days=1)
            pending = self.connection.execute("SELECT COUNT(*) FROM submissions WHERE finished_at IS NULL").fetchone()[0]
            return {"training": training, "sets": sets, "contests": contests, "activeContest": next((contest for contest in contests if contest["status"] == "running"), None), "summary": {"total": len(training), "accepted": sum(item["accepted"] for item in training), "samplePassed": sum(item["verdict"] == "SAMPLE_PASS" and not item["accepted"] for item in training), "attempts": len(records), "due": sum(item["queue"] is not None for item in training), "streak": streak, "pending": pending}, "now": iso(now)}

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            for cancel in self.cancellations.values():
                cancel.set()
        self.executor.shutdown(wait=True, cancel_futures=False)
        self.leaderboard.close()
        with self.lock:
            self.connection.close()
