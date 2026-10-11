"""Per-submission capabilities for the user's ordinary browser; no cookie access."""
from __future__ import annotations

import datetime as dt
import secrets
import threading
import time
import uuid
import webbrowser
from urllib.parse import urlencode, urlsplit

from official_bridge import submission_target, LOGIN_HOSTS
from training import ServiceError

EXTENSION_ID = 'blgkmkjbdekeoenepgnajpeafofccbjm'
EXTENSION_ORIGIN = 'chrome-extension://' + EXTENSION_ID
TERMINAL = {'finished', 'error', 'closed', 'unconfirmed'}
STATES = TERMINAL | {'loading', 'needs_browser', 'needs_login', 'needs_verification', 'ready', 'submitted', 'judging'}
VERDICTS = {'AC', 'WA', 'TLE', 'MLE', 'RE', 'CE', 'OLE'}


class BrowserBridge:
    def __init__(self, base_url, guard=None, on_receipt=None, on_pending=None, opener=None, clock=None):
        self.base_url = base_url.rstrip('/')
        self.guard, self.on_receipt, self.on_pending = guard, on_receipt, on_pending
        self.opener, self.clock = opener or webbrowser.open, clock or time.monotonic
        self.sessions = {}
        self.lock = threading.RLock()

    def _expire(self, session):
        if session['status'] in TERMINAL:
            return
        now = self.clock()
        if session.get('dispatchedAt') is not None and not session.get('submissionId') and now - session['dispatchedAt'] > 45:
            session.update(status='unconfirmed', intent=False,
                           message='45 秒内未收到原站受理编号。请在浏览器核对提交记录后再重试；TB 不会自动重复提交。')
        elif session.get('claimed') and now - session.get('lastSeen', now) > 90:
            session.update(status='unconfirmed' if session.get('dispatchedAt') is not None else 'error', intent=False,
                           message='浏览器连接已中断，请打开原站核对提交记录后再重试。')
        elif not session.get('claimed') and now - session['createdAt'] > 12:
            session.update(status='needs_browser', message='请在已登录账号的浏览器启用 TB 浏览器连接扩展，然后刷新连接页。')
        if now - session['createdAt'] > 900:
            session.update(status='unconfirmed' if session.get('submissionId') else 'error', intent=False,
                           message='等待原站结果超时，请在浏览器核对提交记录。')

    def _open(self, url, code, title, intent):
        from insights import canonical_url
        target = submission_target(url)
        if not isinstance(code, str) or not code.strip() or len(code.encode('utf-8')) > 65536:
            raise ServiceError(400, '请先输入不超过 64 KiB 的待提交代码')
        if self.guard:
            self.guard(url)
        with self.lock:
            for item in self.sessions.values():
                self._expire(item)
            session = next((s for s in self.sessions.values() if s['status'] not in TERMINAL
                            and canonical_url(s['originalUrl']) == canonical_url(url)), None)
            if session and intent and (session.get('dispatchedAt') is not None or session.get('intent')):
                raise ServiceError(409, '这道题已有提交正在处理，请先核对本次提交结果。')
            if session and session['code'] != code:
                session.update(status='closed', intent=False)
                session = None
            if session is None:
                if sum(s['status'] not in TERMINAL for s in self.sessions.values()) >= 8:
                    raise ServiceError(409, '已有多个浏览器提交等待处理，请先查看结果。')
                identity = 'official-' + uuid.uuid4().hex
                session = {**target, 'sessionId': identity, 'code': code, 'title': str(title),
                           'status': 'loading', 'message': '正在连接已登录的浏览器。', 'intent': intent,
                           'attempted': False, 'baseline': [], 'baselineKnown': False, 'baselineOwner': '',
                           'capability': secrets.token_urlsafe(32), 'createdAt': self.clock(), 'command': 0}
                self.sessions[identity] = session
            else:
                session.update(intent=intent)
                if intent:
                    session.update(status='loading', message='正在检查浏览器登录和提交页面。')
            session['navigateTo'] = session['loginUrl'] if not intent and session['status'] == 'needs_login' else session['url']
            fragment = urlencode({'session': session['sessionId'], 'key': session['capability']})
        self.opener(self.base_url + '/browser-connect.html#' + fragment)
        return self.status(session['sessionId'])

    def submit(self, url, code, title):
        return self._open(url, code, title, True)

    def open(self, url, code, title):
        return self._open(url, code, title, False)

    def status(self, identity):
        with self.lock:
            session = self.sessions.get(identity)
            if not session:
                raise ServiceError(404, '没有找到本次浏览器提交')
            self._expire(session)
            return {key: session[key] for key in ('sessionId', 'platform', 'url', 'status', 'message',
                    'submissionId', 'verdict', 'acceptedAt', 'compiler') if key in session}

    def _authenticate(self, identity, capability):
        session = self.sessions.get(identity)
        if not session or not isinstance(capability, str) or not secrets.compare_digest(session['capability'], capability):
            raise ServiceError(403, '浏览器连接已失效，请从 TB 重新打开')
        return session

    def exchange(self, body, capability):
        """Only the bundled extension can call this route, using this job's secret."""
        with self.lock:
            original = self._authenticate(body.get('sessionId'), capability)['originalUrl']
        # Do not hold the bridge lock while entering training/storage locks.
        if self.guard:
            self.guard(original)
        answer = self._exchange(body, capability)
        self._persist(body.get('sessionId'))
        if answer.get('stop') and self.status(body.get('sessionId'))['status'] not in TERMINAL:
            return {'ack': True}
        return answer

    def _exchange(self, body, capability):
        with self.lock:
            session = self._authenticate(body.get('sessionId'), capability)
            self._expire(session)
            if body.get('claim'):
                session.update(claimed=True, lastSeen=self.clock())
                if session['status'] == 'needs_browser':
                    session['status'] = 'loading'
                return {'url': session['navigateTo'], 'sessionId': session['sessionId'], 'status': session['status']}
            page = urlsplit(str(body.get('pageUrl', '')))
            if page.scheme != 'https' or page.hostname not in LOGIN_HOSTS[session['platform']] or page.port not in (None, 443) or page.username or page.password:
                raise ServiceError(403, '只接受本次竞赛平台的浏览器页面')
            session['lastSeen'] = self.clock()
            value = body.get('event')
            if isinstance(value, dict):
                self._update(session, value)
            if session['status'] in TERMINAL:
                return {'stop': True, 'status': session['status']}
            if isinstance(value, dict):
                return {'ack': True}
            action = 'inspect'
            if session.get('intent') and session['status'] == 'ready' and session.get('dispatchedAt') is None:
                action = 'submit'
                session.update(intent=False, dispatchedAt=self.clock(), status='submitted',
                               message='正在操作原站提交表单，尚未确认受理。')
                session['command'] += 1
            context = {k: session.get(k) for k in ('sessionId', 'platform', 'problem', 'code', 'originalUrl',
                       'attempted', 'baseline', 'baselineKnown', 'baselineOwner', 'submissionId')}
            return {'context': context, 'action': action, 'command': session['command']}

    def _update(self, session, value):
        if session['status'] in TERMINAL or value.get('status') not in STATES:
            return
        status = value['status']
        remote_id = str(value.get('submissionId', session.get('submissionId', '')))
        if status in ('judging', 'finished'):
            if session.get('dispatchedAt') is None or not remote_id.isascii() or not remote_id.isdigit() or int(remote_id) <= 0:
                return
            if session.get('submissionId') and remote_id != session['submissionId']:
                return
            if status == 'finished' and value.get('verdict') not in VERDICTS:
                return
        if session.get('submissionId') and status in ('loading', 'ready', 'submitted'):
            return
        if session.get('dispatchedAt') is not None and status in ('ready', 'loading'):
            return
        if status in ('needs_login', 'needs_verification', 'error'):
            session['intent'] = False
            if value.get('attempted') is False:
                session.pop('dispatchedAt', None)
                session['attempted'] = False
        for key in ('status', 'message', 'compiler', 'attempted', 'baseline', 'baselineKnown', 'baselineOwner'):
            if key in value:
                item = value[key]
                if key in ('message', 'compiler', 'baselineOwner'):
                    if not isinstance(item, str):
                        continue
                    item = item[:500]
                if key in ('attempted', 'baselineKnown') and not isinstance(item, bool):
                    continue
                if key == 'baseline':
                    if not isinstance(item, list) or len(item) > 1000 or any(not isinstance(v, str) or not v.isascii() or not v.isdigit() for v in item):
                        continue
                session[key] = item
        if status in ('judging', 'finished'):
            session['submissionId'] = remote_id
            session.setdefault('acceptedAt', dt.datetime.now(dt.timezone.utc).isoformat())
        if status == 'finished':
            session['verdict'] = value['verdict']

    def _persist(self, identity):
        with self.lock:
            session = self.sessions[identity]
            snapshot = dict(session)
        if snapshot.get('submissionId') and not snapshot.get('pendingSaved') and self.on_pending:
            if self.on_pending(identity, snapshot) is not None:
                with self.lock:
                    session['pendingSaved'] = True
        if snapshot['status'] == 'finished' and self.on_receipt and not snapshot.get('saved'):
            saved = self.on_receipt(identity, snapshot)
            with self.lock:
                if saved is not False:
                    session['saved'] = True
                    return
                session.update(status='judging', message='结果保存失败，正在重试。')

    def close(self, identity=None):
        # Leaving a workbench does not discard a pending official result.
        return self.status(identity) if identity else {'status': 'ready'}

    def on_closing(self):
        with self.lock:
            for session in self.sessions.values():
                if session['status'] not in TERMINAL:
                    session.update(status='closed', intent=False)
