"""TB archive and submission-derived personal training HTTP service."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlsplit

TOOLS = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
COMMON = Path(__file__).resolve().parent / 'common'
sys.path.insert(0, str(COMMON if COMMON.is_dir() else TOOLS))
import knowledge_dict as KD
import status_report as SR
import toolutil
from training import TrainingService, ServiceError
from insights import canonical_url


class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def _gui():
    # Importing the existing GUI does not construct a Tk root or write files.
    import status_gui
    return status_gui


def _revision(raw):
    return hashlib.sha256(raw).hexdigest()


def _atomic_bytes(path, raw):
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Store:
    def __init__(self, data_file=None, data_root=None, history_file=None):
        self.data_file = Path(data_file or SR.DEFAULT_FILE).resolve()
        self.data_root = str(Path(data_root or toolutil.DATA_ROOT).resolve())
        self.history_file = Path(history_file or (TOOLS.parent / "logs" / "tb-web-history.jsonl"))
        self.lock = threading.RLock()
        self.token = secrets.token_urlsafe(32)
        self.dictionary = KD.load()
        self.extensions = None
        self._catalog_cache = {}
        from contestmeta import ContestDates
        self.contest_dates = ContestDates(self)

    def contest_metadata(self, row, url=None):
        method = getattr(self.extensions, "contest_metadata", None)
        return method(row, url) if callable(method) else self.contest_dates.for_row(row, url)

    def raw_rows(self):
        try:
            return SR.parse_table(str(self.data_file))
        except SystemExit as error:
            raise APIError(422, str(error)) from error

    def row(self, identity):
        hits = [r for r in self.raw_rows() if r["场次"] + "::" + r["题号"] == identity]
        if not hits:
            remote = self.extensions.row(identity) if self.extensions is not None else None
            if remote:
                return remote
            raise APIError(404, "没有找到这道题，请刷新列表")
        if len(hits) != 1:
            raise APIError(409, "这道题存在重复记录，已停止操作")
        return hits[0]

    def categories(self):
        from knowledge import dictionary
        catalog = dictionary()
        groups = catalog["groups"]
        standards = set(catalog["names"])
        children = {child for parent, kids in groups.items() for child in kids if child != parent}

        def branch(name, ancestry=()):
            if name in ancestry:
                return {"name": name, "children": [], "tags": [name] if name in standards else []}
            nodes = []
            for child in groups.get(name, []):
                if child == name:
                    nodes.append({"name": child, "children": [], "tags": [child] if child in standards else []})
                else:
                    nodes.append(branch(child, ancestry + (name,)))
            tags = ([name] if name in standards else []) + [tag for node in nodes for tag in node["tags"]]
            return {"name": name, "children": nodes, "tags": list(dict.fromkeys(tags))}

        roots = [name for name in groups if name not in children]
        represented = set(groups) | children
        roots += [name for name in catalog["names"] if name not in represented]
        return [branch(name) for name in roots]

    def _enrich_knowledge(self, row):
        from knowledge import enrich_row
        cache = getattr(self, "knowledge_analysis", None)
        if cache is not None:
            with cache.lock:
                previous = cache.state.get(row.get("id"))
                if previous:
                    row = {**row, "knowledgeAnalysis": previous}
        return enrich_row(row)

    def encode_row(self, row, today):
        if row.get("_remote"):
            return self._enrich_knowledge({"id": row["_id"], "contest": row["场次"], "problem": row["题号"], "title": row["题名"], "knowledge": row["知识点"], "tags": KD.split_names(row["知识点"]), "difficulty": SR.difficulty_num(str(row["难度"])), "status": "未做", "date": "", "platform": row.get("_platform", "其他"), "series": row.get("_series", "其他"), "queue": None, "url": row.get("_url"), "source": "remote", "solutionAvailable": False, "solutionState": "missing", **self.contest_metadata(row, row.get("_url"))})
        series, _ = toolutil.parse_contest(row["场次"])
        platform = toolutil.SERIES.get(series, {}).get("dir", ("其他",))[0]
        date = SR.parse_date(row["日期"]) if row["日期"] else None
        age = (today - date).days if date else None
        state = row["状态"]
        queue = None
        if state == SR.TODO_HARD:
            queue = "rewrite"
        elif state in SR.TODO_FILL:
            queue = "fill"
        elif state in SR.REVIEW and age is not None and age >= 7:
            queue = "review"
        elif state == SR.KEEP and age is not None and age >= SR.KEEP_DAYS:
            queue = "check"
        tags = [self.dictionary.canonical(name) or name for name in KD.split_names(row["知识点"])]
        available, url = self._archive_info(row)
        metadata = getattr(self.extensions, "problem_metadata", None)
        latest = metadata(row, url) if callable(metadata) else {}
        return self._enrich_knowledge({"id": row["场次"] + "::" + row["题号"], "contest": row["场次"],
                "problem": row["题号"], "title": row["题名"], "knowledge": row["知识点"],
                "tags": list(dict.fromkeys(tags)), "difficulty": SR.difficulty_num(row["难度"]),
                "status": state, "date": row["日期"], "platform": platform,
                "series": series or "其他", "queue": queue, "source": "archive",
                "url": url, "solutionAvailable": available, "solutionState": "available" if available else "missing", **self.contest_metadata(row, url), **latest})

    def _archive_info(self, row):
        series, number = toolutil.parse_contest(row["场次"])
        if series is None:
            return False, None
        directory, source = toolutil.contest_paths(self.data_root, series, number)
        if not source:
            return False, None
        path = Path(source)
        listing = Path(directory) / "_work" / "题单.md"
        try:
            signatures = tuple((str(item), item.stat().st_mtime_ns, item.stat().st_size) if item.exists() else (str(item), None, None) for item in (path, listing))
        except OSError:
            return False, None
        key = str(path)
        cached = self._catalog_cache.get(key)
        if cached is None or cached[0] != signatures:
            catalog = toolutil.parse_catalog(str(path)) if path.is_file() else {}
            urls = {}
            for letter in catalog:
                probe = dict(row, 题号=letter)
                urls[letter], _ = _gui().StatusGui.parse_problem_url(SimpleNamespace(data_root=self.data_root), probe)
            cached = self._catalog_cache[key] = (signatures, catalog, urls)
        return row["题号"] in cached[1], cached[2].get(row["题号"])

    def data(self):
        with self.lock:
            today = dt.date.today()
            before = self.data_file.read_bytes()
            rows = self.raw_rows()
            after = self.data_file.read_bytes()
            if before != after:
                raise APIError(409, "数据刚被其他程序修改，请刷新")
            encoded = [self.encode_row(row, today) for row in rows]
            seen_urls = {canonical_url(row.get("url")) for row in encoded if canonical_url(row.get("url"))}
            seen_ids = {row["id"] for row in encoded}
            remote = self.extensions.rows() if self.extensions is not None else []
            for row in remote:
                key = canonical_url(row.get("url"))
                if row["id"] in seen_ids or key and key in seen_urls:
                    continue
                encoded.append(self._enrich_knowledge(row))
                seen_ids.add(row["id"])
                if key:
                    seen_urls.add(key)
            revision = _revision(after) if not remote else _revision(after + json.dumps(remote, sort_keys=True, ensure_ascii=False).encode())
            return {"rows": encoded, "statuses": list(SR.STATES),
                    "categories": self.categories(), "revision": revision,
                    "today": today.isoformat(), "token": self.token}

    def solution(self, identity):
        row = self.row(identity)
        if row.get("_remote"):
            key = canonical_url(row.get("_url"))
            row = next((candidate for candidate in self.raw_rows() if key and canonical_url(self._archive_info(candidate)[1]) == key), None)
            if row is None:
                raise APIError(404, "题解未生成")
        series, number = toolutil.parse_contest(row["场次"])
        if series is None:
            raise APIError(404, "没有找到这场比赛的题解")
        _, path = toolutil.contest_paths(self.data_root, series, number)
        if not path or not Path(path).is_file():
            raise APIError(404, "没有找到这场比赛的题解")
        text = Path(path).read_text(encoding="utf-8-sig")
        catalog = toolutil.parse_catalog(path)
        letter = row["题号"]
        if letter not in catalog:
            raise APIError(404, "题解目录中没有这道题")
        lines = text.splitlines(keepends=True)
        masked = toolutil.fence_mask(lines, tilde=True)
        headings, candidates = [], []
        for i, line in enumerate(lines):
            if masked[i]:
                continue
            heading = re.match(r"^##(?!#)\s+(.+?)\s*$", line)
            if not heading:
                continue
            headings.append(i)
            match = re.match(r"^" + re.escape(letter) + r"(?:[.．、:：]\s*|\s+)(.+)$", heading.group(1))
            if match:
                candidates.append((i, toolutil.norm_title(match.group(1)) == toolutil.norm_title(catalog[letter][0])))
        exact = [i for i, matches_title in candidates if matches_title]
        # Math/HTML escaping may differ between a directory cell and its heading.
        # A unique problem-code heading remains authoritative once catalog membership is confirmed.
        if len(exact) == 1:
            start = exact[0]
        elif len(candidates) == 1:
            start = candidates[0][0]
        else:
            raise APIError(404, "没有找到这道题对应的题解章节")
        end = next((i for i in headings if i > start), len(lines))
        url, _ = _gui().StatusGui.parse_problem_url(SimpleNamespace(data_root=self.data_root), row)
        return {"markdown": "".join(lines[start:end]).rstrip(), "path": path,
                "url": url, "title": row["题名"]}

    def update(self, body):
        if not isinstance(body, dict):
            raise APIError(400, "请求必须是 JSON 对象")
        identity, status, expected = body.get("id"), body.get("status"), body.get("expected")
        if not isinstance(identity, str) or status not in SR.STATES:
            raise APIError(400, "题目或状态无效")
        if not isinstance(expected, dict) or not all(isinstance(expected.get(k), str) for k in ("status", "date")):
            raise APIError(400, "缺少当前状态与日期，请刷新后重试")
        date = body.get("date", dt.date.today().isoformat())
        if not isinstance(date, str) or (date and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or SR.parse_date(date) is None)):
            raise APIError(400, "日期必须为空或 YYYY-MM-DD")
        with self.lock:
            stat = self.data_file.stat()
            raw = self.data_file.read_bytes()
            row = self.row(identity)
            if row.get("_remote"):
                raise APIError(400, "远程题目不支持旧状态标记，请使用正式提交记录")
            if {"status": row["状态"], "date": row["日期"]} != {k: expected[k] for k in ("status", "date")}:
                raise APIError(409, "这道题已被其他窗口修改，请刷新后重试")
            lines = raw.decode("utf-8-sig").splitlines(keepends=True)
            gui = _gui()
            index = gui.locate_row(lines, (row["场次"], row["题号"]))
            lines[index] = gui.replace_cells(lines[index], {"状态": status, "日期": date})
            new = "".join(lines).encode("utf-8")
            if raw.startswith(b"\xef\xbb\xbf"):
                new = b"\xef\xbb\xbf" + new
            if new != raw:
                self.history_file.parent.mkdir(parents=True, exist_ok=True)
                # Open the append-only journal before committing the table.
                with self.history_file.open("a", encoding="utf-8", newline="\n") as history:
                    toolutil.backup_to_repo(str(self.data_file))
                    current = self.data_file.stat()
                    if (stat.st_mtime_ns, stat.st_size) != (current.st_mtime_ns, current.st_size) or self.data_file.read_bytes() != raw:
                        raise APIError(409, "数据刚被其他程序修改，本次写入已停止，请刷新")
                    _atomic_bytes(self.data_file, new)
                    entry = {"at": dt.datetime.now().astimezone().isoformat(), "id": identity,
                             "before": {"status": row["状态"], "date": row["日期"]},
                             "after": {"status": status, "date": date}, "revision": _revision(new)}
                    history.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    history.flush()
                    os.fsync(history.fileno())
            row["状态"], row["日期"] = status, date
            return {"row": self.encode_row(row, dt.date.today()), "revision": _revision(new)}

    def inbox(self, action=None):
        import tb_inbox
        with self.lock:
            inbox = Path(tb_inbox.inbox_dir(self.data_root))
            if not inbox.exists() and action is None:
                return {"pending": 0, "conflicts": [], "errors": [], "adds": [], "files": [], "path": str(inbox)}
            plan = tb_inbox.scan(self.data_root, str(self.data_file))
            summary = {"pending": len(plan["adds"]) + len(plan["conflicts"]),
                       "conflicts": plan["conflicts"], "errors": plan["errors"],
                       "adds": plan["adds"], "files": plan["files"], "path": str(inbox)}
            if action is None:
                return summary
            if action not in ("import", "skip", "overwrite"):
                raise APIError(400, "收件箱操作无效")
            if plan.get("fatal") or plan.get("fatal_inbox"):
                raise APIError(422, plan.get("fatal") or plan.get("fatal_inbox"))
            if action == "import" and plan["conflicts"]:
                return dict(summary, needsChoice=True)
            result = tb_inbox.apply(plan, str(self.data_file), on_conflict="overwrite" if action == "overwrite" else "skip")
            # Keep implementation-specific backup paths out of UI responses.
            result.pop("bak", None)
            return dict(summary, result=result, needsChoice=False)


class Handler(BaseHTTPRequestHandler):
    server_version = "TBLocal/1"

    def log_message(self, fmt, *args):
        pass

    def send_json(self, status, value):
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def local_request(self, writing=False):
        port = self.server.server_address[1]
        host = self.headers.get("Host", "")
        allowed = {"127.0.0.1:%d" % port, "localhost:%d" % port}
        if host.lower() not in allowed:
            raise APIError(403, "只接受本机请求")
        if writing:
            origin = self.headers.get("Origin")
            if origin:
                parsed = urlsplit(origin)
                if parsed.scheme != "http" or parsed.netloc.lower() != host.lower() or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
                    raise APIError(403, "请求来源不匹配")
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                raise APIError(403, "不接受跨站请求")
            token = self.headers.get("X-TB-Token", "")
            if not secrets.compare_digest(token, self.server.store.token):
                raise APIError(403, "会话已失效，请刷新")

    def dispatch(self, writing=False):
        body_consumed = False
        try:
            self.local_request(writing)
            target = urlsplit(self.path)
            path = unquote(target.path)
            if "\\" in path or "\x00" in path or any(part in (".", "..") for part in path.split("/")):
                raise APIError(404, "没有找到这个页面")
            store = self.server.store
            if writing:
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    raise APIError(400, "请求长度无效")
                if size <= 0 or size > 262144:
                    raise APIError(400, "请求数据大小无效")
                if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                    raise APIError(415, "请求必须使用 application/json")
                try:
                    raw_body = self.rfile.read(size)
                    body_consumed = True
                    body = json.loads(raw_body.decode("utf-8"))
                except (ValueError, UnicodeError):
                    raise APIError(400, "JSON 格式无效")
                if not isinstance(body, dict):
                    raise APIError(400, "请求必须是 JSON 对象")
                training = self.server.training
                if path == "/api/status":
                    with training.lock:
                        training.assert_solution_unlocked(body.get("id"))
                        value = store.update(body)
                elif path == "/api/inbox":
                    value = store.inbox(body.get("action", "import"))
                elif path == "/api/training/start":
                    value = training.start_training(body.get("id"))
                elif path == "/api/training/remove":
                    value = training.remove_training(body.get("id"))
                elif path == "/api/training/contest":
                    value = training.start_practice_set(body.get("contest"))
                elif path == "/api/draft":
                    value = training.save_draft(body.get("id"), body.get("code"), body.get("contestId"))
                elif path == "/api/submissions":
                    value = training.submit(body.get("id"), body.get("code"), body.get("mode", "submit"), body.get("input", ""), body.get("contestId"), body.get("sampleRun"))
                elif path == "/api/contests/preview":
                    value = training.preview_contest(body)
                elif path == "/api/contests/start":
                    value = training.start_contest(body)
                    if callable(self.server.official_closer):
                        self.server.official_closer(None)
                elif path == "/api/contests/finish":
                    value = training.finish_contest(body.get("contestId"))
                elif path == "/api/daily-tasks/claim":
                    value = training.claim_daily_task(body.get("id"), body.get("date"))
                elif path in ("/api/profile", "/api/identity"):
                    value = training.configure_profile(body)
                elif path in ("/api/leaderboard/sync", "/api/rankings/sync"):
                    value = training.leaderboard.queue_sync(force=True)
                elif path == "/api/hub/configure":
                    value = store.extensions.configure(body)
                elif path == "/api/hub/sync":
                    value = store.extensions.sync(body)
                elif path == "/api/hub/dismiss":
                    value = store.extensions.dismiss(body.get("id"))
                elif path in ("/api/official/open", "/api/official/submit"):
                    identity = body.get("id")
                    code = training._code(body.get("code"))
                    if not code.strip():
                        raise APIError(400, "请先输入要提交的代码")
                    with training.lock:
                        row = training._row(identity)
                        training._context(identity, body.get("contestId"))
                        training.assert_solution_unlocked(identity)
                    opener = self.server.official_submitter if path.endswith("/submit") else self.server.official_opener
                    if not callable(opener):
                        raise APIError(503, "当前浏览器测试没有原生提交面板，请在 TB 桌面版打开")
                    url = row.get("url")
                    if not url:
                        url = training._asset_library().problem(identity).get("url")
                    if not canonical_url(url):
                        raise APIError(422, "没有找到这道题的原站链接")
                    with training.lock:
                        training.assert_solution_unlocked(identity)
                        opened = opener(url, code, row["title"])
                    value = opened if isinstance(opened, dict) else {"sessionId": opened, "platform": row.get("platform"), "url": url, "status": "opened"}
                    if not isinstance(value.get("sessionId"), str):
                        raise APIError(503, "原生提交面板没有返回有效会话")
                    self.server.official_sessions[value["sessionId"]] = {"id": identity, "contestId": body.get("contestId"), "url": url}
                elif path == "/api/official/close":
                    if not callable(self.server.official_closer):
                        raise APIError(503, "当前浏览器没有原生官方面板")
                    value = self.server.official_closer(body.get("sessionId"))
                elif path == "/api/problem/translate":
                    value = self.server.translate_problem(body.get("id"), body.get("contestId"))
                elif path == "/api/translation/settings":
                    value = self.server.translation_service().configure(body)
                else:
                    raise APIError(404, "没有找到这个接口")
                self.send_json(200, value)
            elif path == "/api/data":
                self.send_json(200, store.data())
            elif path == "/api/solution":
                identity = parse_qs(target.query).get("id", [None])[0]
                if not identity:
                    raise APIError(400, "缺少题目编号")
                with self.server.training.lock:
                    self.server.training.assert_solution_unlocked(identity)
                    solution = store.solution(identity)
                    self.server.training.mark_solution_seen(identity)
                    solution["lectures"] = self.server.lectures.for_problem(identity)
                self.send_json(200, solution)
            elif path == "/api/workspace":
                self.send_json(200, self.server.training.workspace())
            elif path == "/api/hub":
                self.send_json(200, store.extensions.snapshot())
            elif path == "/api/insights":
                self.send_json(200, self.server.training.insights(store.extensions.snapshot()))
            elif path == "/api/daily-tasks":
                self.send_json(200, self.server.training.daily_tasks())
            elif path in ("/api/profile", "/api/identity"):
                self.send_json(200, self.server.training.profile())
            elif path in ("/api/leaderboard", "/api/rankings"):
                period = parse_qs(target.query).get("period", ["daily"])[0]
                self.send_json(200, self.server.training.leaderboard.rankings(period))
            elif path == "/api/problem":
                query = parse_qs(target.query)
                self.send_json(200, self.server.training.problem(query.get("id", [None])[0], query.get("contestId", [None])[0]))
            elif path == "/api/problem/translate":
                query = parse_qs(target.query)
                self.send_json(200, self.server.translate_problem(query.get("id", [None])[0], query.get("contestId", [None])[0]))
            elif path == "/api/translation/settings":
                self.send_json(200, self.server.translation_service().status())
            elif path == "/api/lectures":
                self.send_json(200, self.server.lectures.snapshot())
            elif path == "/api/lecture":
                identity = parse_qs(target.query).get("id", [None])[0]
                value = self.server.lectures.get(identity)
                with self.server.training.lock:
                    for source in value.get("sourceProblemIds", []):
                        self.server.training.assert_solution_unlocked(source)
                self.send_json(200, value)
            elif path == "/api/official/status":
                identity = parse_qs(target.query).get("sessionId", [None])[0]
                if not callable(self.server.official_status):
                    raise APIError(503, "当前浏览器没有原生官方面板")
                with self.server.training.lock:
                    session = self.server.official_sessions.get(identity)
                    if not session:
                        raise APIError(404, "没有找到本次原站提交会话")
                    self.server.training.assert_solution_unlocked(session["id"])
                self.send_json(200, self.server.official_status(identity))
            elif path == "/api/submission":
                identity = parse_qs(target.query).get("id", [None])[0]
                self.send_json(200, self.server.training.submission(identity))
            elif path == "/api/submissions":
                query = parse_qs(target.query)
                self.send_json(200, self.server.training.submissions(query.get("id", [None])[0], query.get("contestId", [None])[0], limit=query.get("limit", [100])[0], offset=query.get("offset", [0])[0]))
            elif path == "/api/contest":
                identity = parse_qs(target.query).get("id", [None])[0]
                self.send_json(200, self.server.training.contest(identity))
            elif path == "/api/inbox":
                self.send_json(200, store.inbox())
            elif path.startswith("/api/"):
                raise APIError(404, "没有找到这个接口")
            else:
                self.static(path)
        except (APIError, ServiceError) as error:
            if writing and not body_consumed:
                # Consume a small rejected body before closing the HTTP/1.0 socket.
                # Otherwise Windows may reset it before the caller receives the 403.
                previous_timeout = self.connection.gettimeout()
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if 0 < size <= 262144:
                        self.connection.settimeout(.25)
                        self.rfile.read(size)
                except (ValueError, OSError):
                    pass
                finally:
                    self.connection.settimeout(previous_timeout)
            self.send_json(error.status, {"error": error.message})
        except (OSError, RuntimeError, ValueError) as error:
            self.send_json(500, {"error": "操作未完成：" + str(error)})
        except Exception:
            self.send_json(500, {"error": "操作未完成，请刷新后重试"})

    def static(self, path):
        root = self.server.dist_dir
        source = (root / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise APIError(404, "没有找到这个页面")
        raw = source.read_bytes()
        mime = mimetypes.guess_type(str(source))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") or mime == "application/javascript" else ""))
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch(writing=True)


class LocalServer(ThreadingHTTPServer):
    def translation_service(self):
        with self.translation_lock:
            if self.translation is None:
                from translation import TranslationService
                self.translation = TranslationService(self.training._asset_library(), self.state_dir)
            return self.translation

    def validate_official_url(self, url):
        with self.training.lock:
            key = canonical_url(url)
            ids = {row["id"] for row in self.store.data()["rows"] if key and canonical_url(row.get("url")) == key}
            ids.update(session["id"] for session in self.official_sessions.values() if key and canonical_url(session["url"]) == key)
            if not ids:
                raise ServiceError(404, "这道原站题目不在当前题库中")
            for identity in ids:
                self.training.assert_solution_unlocked(identity)

    def translate_problem(self, identity, contest_id=None):
        def validate():
            with self.training.lock:
                self.training._row(identity)
                self.training._context(identity, contest_id)
                self.training._history_visible(identity, contest_id)
        validate()
        value = self.translation_service().translate(identity)
        validate()
        return value

    def server_close(self):
        super().server_close()
        extensions = getattr(getattr(self, "store", None), "extensions", None)
        training = getattr(self, "training", None)
        try:
            if extensions is not None:
                extensions.close()
        finally:
            if training is not None:
                training.close()


def create_server(port=0, data_file=None, data_root=None, dist_dir=None, history_file=None,
                  training_file=None, assets=None, judge=None, clock=None, backup_dir=None, rng=None,
                  integration_state_dir=None, integration_auto_start=None, integrations=None, official_opener=None,
                  official_submitter=None, official_status=None, official_closer=None, lectures=None, translation=None):
    explicit_training = training_file is not None
    server = LocalServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.store = Store(data_file, data_root, history_file)
    server.dist_dir = Path(dist_dir or (Path(__file__).resolve().parent / "dist")).resolve()
    if training_file is None:
        if history_file:
            training_file = Path(history_file).parent / "tb-personal.sqlite3"
        elif data_file:
            training_file = Path(data_file).parent / "tb-personal.sqlite3"
        else:
            training_file = TOOLS.parent / "state" / "tb-personal.sqlite3"
    try:
        if integration_auto_start is None:
            integration_auto_start = not (explicit_training or data_file or history_file)
        if integrations is not None:
            server.store.extensions = integrations
        else:
            from integrations import IntegrationService
            server.store.extensions = IntegrationService(server.store, Path(integration_state_dir or Path(training_file).parent), auto_start=integration_auto_start)
        server.official_opener = official_opener
        server.official_submitter, server.official_status, server.official_closer = official_submitter, official_status, official_closer
        server.official_sessions = {}
        server.state_dir = Path(training_file).parent
        from knowledge import KnowledgeAnalysisCache
        server.store.knowledge_analysis = KnowledgeAnalysisCache(server.state_dir / "tb-knowledge-analysis.json")
        server.translation = translation
        server.translation_lock = threading.RLock()
        server.training = TrainingService(server.store, training_file, assets=assets, judge=judge, clock=clock, backup_dir=backup_dir, rng=rng)
        if lectures is None:
            from lectures import LectureLibrary
            lectures = LectureLibrary(server.store, server.state_dir)
        server.lectures = lectures
    except Exception:
        server.server_close()
        raise
    return server


def start_server(port=18765, **kwargs):
    """Return an unstarted server; desktop launchers own the serving thread."""
    return create_server(port=port, **kwargs)


def main():
    parser = argparse.ArgumentParser(description="TB 本机数据服务")
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--data-file")
    args = parser.parse_args()
    server = start_server(args.port, data_file=args.data_file)
    print("TB http://127.0.0.1:%d" % server.server_address[1], flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
