"""TB archive and submission-derived personal training HTTP service."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from paths import STATE
sys.dont_write_bytecode = True
COMMON = Path(__file__).resolve().parent / 'common'
sys.path.insert(0, str(COMMON))
import toolutil
from training import TrainingService, ServiceError
from insights import canonical_url


from errors import APIError
from store import Store


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

    def end_headers(self):
        origin = self.headers.get('Origin')
        if origin in self.server.frontend_origins:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        super().end_headers()

    def do_OPTIONS(self):
        try:
            self.local_request()
            if self.headers.get('Origin') not in self.server.frontend_origins:
                raise APIError(403, '请求来源不匹配')
            self.send_response(204)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-TB-Token')
            self.send_header('Access-Control-Max-Age', '600')
            self.send_header('Content-Length', '0')
            self.end_headers()
        except APIError as error:
            self.send_json(error.status, {'error': error.message})

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
                if origin not in self.server.frontend_origins and (parsed.scheme != "http" or parsed.netloc.lower() != host.lower() or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
                    raise APIError(403, "请求来源不匹配")
            if self.headers.get("Sec-Fetch-Site") == "cross-site" and origin not in self.server.frontend_origins:
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
                elif path == "/api/training/clear":
                    value = training.clear_training()
                elif path == "/api/goals/save":
                    from goals import Goals
                    value = Goals(training).save(body)
                elif path == "/api/goals/archive":
                    from goals import Goals
                    value = Goals(training).archive(body.get('id'))
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
                    self.server.register_official_session(value["sessionId"], {"id": identity, "contestId": body.get("contestId"), "url": url, "code": code}, value)
                elif path == "/api/official/close":
                    if not callable(self.server.official_closer):
                        raise APIError(503, "当前浏览器没有原生官方面板")
                    value = self.server.official_closer(body.get("sessionId"))
                elif path == "/api/desktop/fullscreen":
                    if not callable(getattr(self.server, "desktop_fullscreen", None)):
                        raise APIError(503, "当前浏览器测试没有原生窗口，无法切换全屏")
                    requested = body.get("fullscreen")
                    if not isinstance(requested, bool):
                        raise APIError(400, "全屏参数必须是布尔值")
                    value = self.server.desktop_fullscreen(requested)
                elif path == "/api/problem/translate":
                    value = self.server.translate_problem(body.get("id"), body.get("contestId"))
                elif path == "/api/translation/test":
                    value = self.server.translation_service().test_connection()
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
            elif path == "/api/goals":
                from goals import Goals
                self.send_json(200, Goals(self.server.training).list())
            elif path == "/api/contests/events":
                self.send_json(200, self.server.training.replay_events())
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
            elif path == "/api/desktop/fullscreen":
                if callable(getattr(self.server, "desktop_state", None)):
                    self.send_json(200, self.server.desktop_state())
                else:
                    self.send_json(200, {"available": False, "fullscreen": False})
            elif path == "/api/official/status":
                identity = parse_qs(target.query).get("sessionId", [None])[0]
                if not callable(self.server.official_status):
                    raise APIError(503, "当前浏览器没有原生官方面板")
                with self.server.training.lock:
                    session = self.server.official_sessions.get(identity)
                    if not session:
                        raise APIError(404, "没有找到本次原站提交会话")
                    self.server.training.assert_solution_unlocked(session["id"])
                receipt = self.server.official_status(identity)
                self.server.record_official_receipt(identity, receipt)
                self.send_json(200, receipt)
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
        if root is None:
            raise APIError(404, "此服务只提供 API；请从前端入口打开 TB")
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
    def register_official_session(self, identity, session, receipt):
        with self.official_session_lock:
            self.official_sessions.setdefault(identity, session)
            pending = self.official_pending_receipts.pop(identity, None)
        if isinstance(pending or receipt, dict) and (pending or receipt).get('submissionId'):
            self.record_official_pending(identity, pending or receipt)
        return self.record_official_receipt(identity, pending or receipt)

    def record_official_pending(self, identity, session):
        """桥在确认原站受理（拿到提交 ID）时调用，冻结受理时刻与查看状态，
        返回持久化的 pending 供恢复用；落库失败返回 None。"""
        if not isinstance(session, dict):
            return None
        with self.official_session_lock:
            context = self.official_sessions.get(identity)
            if context is None:
                self.official_pending_receipts[identity] = dict(session)
                return None
        record = {"sessionId": identity, "submissionId": session.get("submissionId"),
                  "acceptedAt": session.get("acceptedAt"), "problemId": context["id"],
                  "url": context["url"], "code": context["code"],
                  "platform": session.get("platform")}
        try:
            self.training.save_official_pending(record)
        except Exception:
            return None
        return record

    def resume_official_sessions(self, url, code):
        """启动后按题目 URL + 代码恢复未完成官方回执，供桥重新绑定。"""
        try:
            return self.training.official_pending(url, code)
        except Exception:
            return []

    def record_official_receipt(self, identity, receipt):
        if not isinstance(receipt, dict) or receipt.get('status') != 'finished':
            return None
        with self.official_session_lock:
            session = self.official_sessions.get(identity)
            if session is None:
                # A fast native result can arrive while open() is returning,
                # before the HTTP handler has registered its immutable code.
                self.official_pending_receipts[identity] = dict(receipt)
                while len(self.official_pending_receipts) > 30:
                    self.official_pending_receipts.pop(next(iter(self.official_pending_receipts)))
        if session:
            saved = self.training.record_official(session, receipt)
            if saved and receipt.get('submissionId'):
                try:
                    self.training.clear_official_pending(url=session.get('url'), code=session.get('code'))
                except Exception:
                    pass
            return saved
        return None

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
            with self.official_session_lock:
                sessions = list(self.official_sessions.values())
            ids.update(session["id"] for session in sessions if key and canonical_url(session["url"]) == key)
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
                  official_submitter=None, official_status=None, official_closer=None, lectures=None, translation=None, library_file=None, frontend_origins=None):
    explicit_training = training_file is not None
    server = LocalServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.frontend_origins = frozenset(frontend_origins or os.environ.get("TB_FRONTEND_ORIGINS", "").split(",")) - {""}
    server.dist_dir = Path(dist_dir).resolve() if dist_dir else None
    if training_file is None:
        if history_file:
            training_file = Path(history_file).parent / "tb-personal.sqlite3"
        elif data_file:
            training_file = Path(data_file).parent / "tb-personal.sqlite3"
        else:
            training_file = STATE / "tb-personal.sqlite3"
    try:
        library_file = library_file or Path(training_file).parent / 'tb-library.sqlite3'
        server.store = Store(data_file, data_root, history_file, library_file=library_file)
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
        server.official_pending_receipts = {}
        server.official_session_lock = threading.RLock()
        server.desktop_state = None
        server.desktop_fullscreen = None
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
    parser.add_argument("--data-file", help="显式导入旧 Markdown 表，仅在 SQL 题库为空时读取")
    parser.add_argument("--state-dir", type=Path, default=STATE)
    parser.add_argument("--library", type=Path)
    parser.add_argument("--frontend", type=Path, help="可选静态界面目录；默认仅启动 API")
    parser.add_argument("--offline", action="store_true", help="禁用外部同步")
    args = parser.parse_args()
    if args.offline:
        os.environ['TB_OFFLINE'] = '1'
    server = start_server(args.port, data_file=args.data_file, training_file=args.state_dir / 'tb-personal.sqlite3',
                          library_file=args.library, dist_dir=args.frontend, integration_auto_start=not args.offline)
    print("TB API http://127.0.0.1:%d" % server.server_address[1], flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
