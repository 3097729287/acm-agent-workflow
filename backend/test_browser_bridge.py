"""Browser capabilities, at-most-once dispatch and honest receipt states."""
import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'desktop'))
from browser_bridge import BrowserBridge, EXTENSION_ID, EXTENSION_ORIGIN
from training import ServiceError


class BrowserBridgeTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.opened, self.saved, self.pending, self.guarded = [], [], [], []
        self.bridge = BrowserBridge('http://127.0.0.1:18765', opener=self.opened.append,
            clock=lambda: self.now, guard=self.guarded.append,
            on_receipt=lambda sid, s: self.saved.append(s) or True,
            on_pending=lambda sid, s: self.pending.append(s) or s)
        self.url = 'https://ac.nowcoder.com/acm/contest/127263/B'

    def create(self):
        reply = self.bridge.submit(self.url, 'int main(){}', 'fixture')
        self.sid = reply['sessionId']
        self.secret = self.bridge.sessions[self.sid]['capability']
        return reply

    def exchange(self, **values):
        return self.bridge.exchange({'sessionId': self.sid, 'pageUrl': self.url, **values}, self.secret)

    def dispatch(self):
        self.create()
        self.exchange(claim=True)
        self.exchange(event={'status': 'ready'})
        answer = self.exchange()
        self.assertEqual(answer['action'], 'submit')
        return answer

    def test_all_four_platforms_submit_without_opening_browser(self):
        for url in (self.url, 'https://codeforces.com/contest/123/problem/A',
                    'https://atcoder.jp/contests/abc100/tasks/abc100_a', 'https://www.luogu.com.cn/problem/P1001'):
            answer = self.bridge.submit(url, 'int main(){}', 'fixture')
            self.assertNotIn('code', answer)
            self.assertNotIn('capability', answer)
            self.assertEqual(self.opened, [])

    def test_unknown_or_cross_session_secret_cannot_read_code(self):
        self.create()
        with self.assertRaises(ServiceError):
            self.bridge.exchange({'sessionId': self.sid, 'claim': True}, 'wrong')
        other = self.bridge.submit('https://www.luogu.com.cn/problem/P1001', 'other code', 'fixture')
        with self.assertRaises(ServiceError):
            self.bridge.exchange({'sessionId': other['sessionId'], 'claim': True}, self.secret)
        with self.assertRaises(ServiceError):
            self.exchange(pageUrl='https://ac.nowcoder.com.evil.test/')

    def test_click_is_never_acceptance_and_dispatch_is_not_replayed(self):
        command = self.dispatch()
        self.assertEqual(command['context']['code'], 'int main(){}')
        self.exchange(event={'status': 'submitted', 'attempted': True})
        for _ in range(3):
            self.assertEqual(self.exchange()['action'], 'inspect')
        self.assertEqual(self.pending, [])
        self.assertEqual(self.saved, [])
        with self.assertRaises(ServiceError):
            self.bridge.submit(self.url, 'new code', 'fixture')
        self.now = 46
        self.assertEqual(self.bridge.status(self.sid)['status'], 'unconfirmed')
        self.assertEqual(self.exchange()['action'], 'inspect')
        self.exchange(event={'status': 'finished', 'submissionId': '101', 'verdict': 'AC'})
        self.assertEqual(self.bridge.status(self.sid)['verdict'], 'AC', 'late receipts still reach TB')

    def test_missing_extension_is_actionable_and_reconnect_keeps_intent(self):
        self.create(); self.now = 13
        self.assertEqual(self.bridge.status(self.sid)['status'], 'needs_browser')
        self.exchange(claim=True)
        self.exchange(event={'status': 'ready'})
        self.assertEqual(self.exchange()['action'], 'submit')

    def test_login_never_submits_until_user_retries(self):
        self.create(); self.exchange(claim=True)
        self.exchange(event={'status': 'needs_login'})
        self.exchange(event={'status': 'ready'})
        self.assertEqual(self.exchange()['action'], 'inspect')
        self.bridge.submit(self.url, 'int main(){}', 'fixture')
        self.exchange(event={'status': 'ready'})
        self.assertEqual(self.exchange()['action'], 'submit')

    def test_open_button_is_read_only_after_an_unknown_result(self):
        self.dispatch(); self.now = 46
        self.assertEqual(self.bridge.status(self.sid)['status'], 'unconfirmed')
        opened = self.bridge.open(self.url, 'int main(){}', 'fixture')
        self.assertTrue(self.opened[-1].startswith('http://127.0.0.1:18765/browser-connect.html#'))
        self.sid = opened['sessionId']; self.secret = self.bridge.sessions[self.sid]['capability']
        self.exchange(claim=True); self.exchange(event={'status': 'ready'})
        self.assertEqual(self.exchange()['action'], 'inspect')

    def test_receipt_requires_dispatch_and_exact_id_and_saves_once(self):
        self.create(); self.exchange(claim=True)
        self.exchange(event={'status': 'finished', 'submissionId': '99', 'verdict': 'AC'})
        self.assertFalse(self.saved)
        self.exchange(event={'status': 'ready'}); self.exchange()
        self.exchange(event={'status': 'judging', 'submissionId': '101'})
        self.exchange(event={'status': 'finished', 'submissionId': '102', 'verdict': 'AC'})
        self.assertFalse(self.saved)
        event = {'status': 'finished', 'submissionId': '101', 'verdict': 'AC'}
        self.exchange(event=event); self.exchange(event=event)
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(len(self.pending), 1)
        self.assertEqual(self.saved[0]['code'], 'int main(){}')

    def test_closing_workbench_does_not_cancel_receipt(self):
        self.dispatch(); self.bridge.close(self.sid)
        self.exchange(event={'status': 'finished', 'submissionId': '101', 'verdict': 'WA'})
        self.assertEqual(self.bridge.status(self.sid)['verdict'], 'WA')

    def test_lock_guard_is_rechecked_before_browser_commands(self):
        self.create()
        def locked(url):
            raise ServiceError(409, 'contest locked')
        self.bridge.guard = locked
        with self.assertRaises(ServiceError):
            self.exchange(claim=True)

    def test_background_queue_is_scoped_and_assigned_once(self):
        import uuid
        first, second = str(uuid.uuid4()), str(uuid.uuid4())
        key = self.bridge.register_browser({'clientId': first})['key']
        other_key = self.bridge.register_browser({'clientId': second})['key']
        self.create()
        with self.assertRaises(ServiceError):
            self.bridge.browser_queue({'clientId': first}, other_key)
        queued = self.bridge.browser_queue({'clientId': first}, key)['jobs']
        self.assertEqual(queued, [{'sessionId': self.sid, 'key': self.secret}])
        self.assertEqual(self.bridge.browser_queue({'clientId': second}, other_key)['jobs'], [])
        self.assertNotIn('code', queued[0])

    def test_api_extension_origin_has_no_general_app_write_access(self):
        from backend import Handler
        from http.server import ThreadingHTTPServer
        from types import SimpleNamespace
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.frontend_origins = set()
        server.store = SimpleNamespace(token='app-secret')
        server.browser_bridge = self.bridge
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:' + str(server.server_port)
        self.create()
        body = json.dumps({'sessionId': self.sid, 'claim': True}).encode()
        headers = {'Content-Type': 'application/json', 'Origin': EXTENSION_ORIGIN,
                   'X-TB-Browser': self.secret, 'X-TB-Browser-Client': EXTENSION_ID}
        try:
            with urlopen(Request(base + '/api/browser/exchange', body, headers), timeout=5) as response:
                self.assertEqual(response.status, 200)
            for path, changed in [('/api/browser/exchange', {'Origin': 'https://ac.nowcoder.com'}),
                                  ('/api/browser/exchange', {'X-TB-Browser': 'wrong'}),
                                  ('/api/draft', {})]:
                with self.assertRaises(HTTPError) as raised:
                    urlopen(Request(base + path, body, headers | changed), timeout=5)
                self.assertEqual(raised.exception.code, 403)
            import uuid
            registration = json.dumps({'clientId': str(uuid.uuid4())}).encode()
            for origin in ('https://ac.nowcoder.com', None):
                bad = {k: v for k, v in headers.items() if k != 'Origin'}
                if origin:
                    bad['Origin'] = origin
                with self.assertRaises(HTTPError) as raised:
                    urlopen(Request(base + '/api/browser/register', registration, bad), timeout=5)
                self.assertEqual(raised.exception.code, 403)
            with urlopen(Request(base + '/api/browser/register', registration, headers), timeout=5) as response:
                self.assertTrue(json.load(response)['key'])
        finally:
            server.shutdown(); server.server_close()


if __name__ == '__main__':
    unittest.main()
