"""Bounded background client for the shared TB ranking service; no code upload."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
import os
from pathlib import Path
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from progression import SHANGHAI

NOTICE = "排行统计客户端报告的首次本地审核通过题数，样例通过与重复题不计入；暂不提供防作弊认证。"


def validate_endpoint(value):
    from training import ServiceError
    if not isinstance(value, str) or len(value) > 2048:
        raise ServiceError(400, "排行榜服务地址无效")
    value = value.strip().rstrip("/")
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ServiceError(400, "排行榜服务地址无效")
    loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.scheme != "https" and not (loopback and parsed.scheme == "http"):
        raise ServiceError(400, "排行榜须使用 HTTPS 地址；本机测试可使用回环 HTTP")
    if parsed.scheme == "https" and port not in (None, 443) and not loopback:
        raise ServiceError(400, "排行榜 HTTPS 地址须使用标准 443 端口")
    return value


def default_endpoint():
    if os.environ.get("TB_OFFLINE") == "1":return ""
    if "TB_LEADERBOARD_URL" in os.environ:return validate_endpoint(os.environ["TB_LEADERBOARD_URL"])
    value = ""
    from paths import resource
    path = resource('leaderboard.defaults.json')
    if not value and path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get("endpoint", "")
        except (OSError, ValueError):
            value = ""
    return validate_endpoint(value)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # A configured service must not redirect the installation's bearer secret.
        raise URLError("排行榜服务发生重定向，请使用最终 HTTPS 地址")


class LeaderboardClient:
    def __init__(self, training, timeout=5):
        self.training = training
        self.timeout = timeout
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tb-ranking")
        self.opener = build_opener(NoRedirect())
        self.running = False
        self.closed = False
        self.dirty = False
        self.cache = {}
        self.status = "unconfigured"
        self.error = ""
        self.last_attempt = 0

    def _request(self, profile, method, path, data=None):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
        request = Request(profile["endpoint"] + path, data=payload, method=method,
                          headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": "Bearer " + profile["auth_token"],
                                   "X-TB-User": profile["user_id"], "User-Agent": "TB/0.5 Ranking"})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(262145)
            if len(raw) > 262144:
                raise ValueError("排行榜响应过大")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("排行榜响应格式无效")
            return value
        except HTTPError as error:
            raise RuntimeError(f"排行榜服务返回 HTTP {error.code}") from None
        except (URLError, TimeoutError, OSError, ValueError) as error:
            # Never echo response bodies, credentials or URLs containing secrets.
            raise RuntimeError("排行榜服务连接失败，请检查服务地址或稍后重试") from error

    def snapshot(self):
        profile = self.training._ranking_profile()
        with self.lock:
            configured = bool(profile["endpoint"])
            return {"configured": configured, "status": self.status if configured else "unconfigured", "endpoint": profile["endpoint"],
                    "lastSyncedAt": profile.get("last_synced_at"), "error": self.error if configured else "",
                    "notice": NOTICE if configured else "排行榜服务尚未配置；设置服务地址后自动同步。"}

    def queue_sync(self, force=False):
        profile = self.training._ranking_profile()
        with self.lock:
            if self.closed or not profile["endpoint"]:
                pass
            elif self.running:
                self.dirty = True
            elif force or self.status != "error" or time.monotonic() - self.last_attempt >= 60:
                self.running = True
                self.dirty = False
                self.status = "syncing"
                self.last_attempt = time.monotonic()
                self.executor.submit(self._sync)
        return self.snapshot()

    def invalidate(self):
        with self.lock:
            self.cache.clear()
            self.error = ""
        return self.queue_sync(force=True)

    def _sync(self):
        try:
            profile = self.training._ranking_profile()
            if not profile["endpoint"]:
                return
            registered = self._request(profile, "POST", "/v1/profile/register", {"userId": profile["user_id"], "nickname": profile["nickname"]})
            if registered.get("userId") != profile["user_id"]:
                raise RuntimeError("排行榜身份响应不匹配")
            self._request(profile, "PUT", "/v1/profile", {"nickname": profile["nickname"]})
            events = self.training._ranking_events(profile["endpoint"])
            for offset in range(0, len(events), 100):
                with self.lock:
                    if self.closed:
                        return
                batch = events[offset:offset + 100]
                answer = self._request(profile, "POST", "/v1/events", {"events": batch})
                if answer.get("processed") != len(batch):
                    raise RuntimeError("排行榜通过记录未完整接收")
                self.training._ranking_receipts(profile["endpoint"], batch)
            values = {}
            for period in ("daily", "weekly", "total"):
                with self.lock:
                    if self.closed:
                        return
                value = self._request(profile, "GET", "/v1/leaderboard?" + urlencode({"period": period}))
                if value.get("period") != period or not isinstance(value.get("entries"), list):
                    raise RuntimeError("排行榜响应格式无效")
                values[period] = (time.monotonic(), value)
            self.training._ranking_synced(profile["endpoint"])
            current_endpoint = self.training._ranking_profile()["endpoint"]
            with self.lock:
                if profile["endpoint"] == current_endpoint:
                    self.cache = values
                    self.status, self.error = "ready", ""
        except Exception as error:
            with self.lock:
                self.status, self.error = "error", str(error)[:200]
        finally:
            with self.lock:
                rerun = self.dirty and not self.closed
                self.running = False
                self.dirty = False
            if rerun:
                self.queue_sync()

    def rankings(self, period="daily"):
        from training import ServiceError
        if period not in {"daily", "weekly", "total"}:
            raise ServiceError(400, "排行周期须为 daily、weekly 或 total")
        state = self.snapshot()
        with self.lock:
            cached = self.cache.get(period)
        if state["configured"] and (cached is None or time.monotonic() - cached[0] > 60):
            self.queue_sync()
            state = self.snapshot()
        date = self.training._now().astimezone(SHANGHAI).date().isoformat()
        value = dict(cached[1]) if cached else {"period": period, "date": date, "entries": [], "self": None}
        value.update(state)
        return value

    def close(self):
        with self.lock:
            self.closed = True
        self.executor.shutdown(wait=True, cancel_futures=True)
