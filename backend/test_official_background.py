"""Submission lifecycle guards without network or user state."""
import unittest
from official_bridge import OfficialBridge
from training import ServiceError


class BackgroundSessionsTests(unittest.TestCase):
    def bridge(self, on_receipt=None):
        bridge = OfficialBridge(object(), on_receipt=on_receipt)
        bridge._ui = lambda action: action()
        bridge._attach = lambda sid, foreground=False: bridge.views.update({sid: {}})
        bridge._reopen = lambda sid: setattr(bridge, 'current', sid)
        bridge.release = lambda sid: bridge.views.pop(sid, None)
        return bridge

    def test_same_pending_task_cannot_resubmit_different_code(self):
        bridge = self.bridge()
        url = 'https://atcoder.jp/contests/abc478/tasks/abc478_d'
        first = bridge.submit(url, 'int main(){}', 'fixture')
        bridge.sessions[first['sessionId']].update(attempted=True, status='judging')
        with self.assertRaises(ServiceError) as raised:
            bridge.submit(url, 'int main(){return 1;}', 'fixture')
        self.assertEqual(raised.exception.status, 409)
        self.assertEqual(bridge.sessions[first['sessionId']]['code'], 'int main(){}')
        self.assertIsNone(bridge.current)

    def test_code_changed_after_login_gets_an_immutable_new_session(self):
        bridge = self.bridge()
        url = 'https://atcoder.jp/contests/abc478/tasks/abc478_d'
        first = bridge.submit(url, 'int main(){}', 'fixture')
        bridge.sessions[first['sessionId']]['status'] = 'needs_login'
        second = bridge.submit(url, 'int main(){return 1;}', 'fixture')
        self.assertNotEqual(first['sessionId'], second['sessionId'])
        self.assertEqual(bridge.sessions[first['sessionId']]['status'], 'closed')
        self.assertEqual(bridge.sessions[second['sessionId']]['code'], 'int main(){return 1;}')

    def test_open_for_login_does_not_arm_submission(self):
        bridge = self.bridge()
        answer = bridge.open('https://atcoder.jp/contests/abc478/tasks/abc478_d', 'int main(){}', 'fixture')
        self.assertFalse(bridge.sessions[answer['sessionId']]['intent'])
        self.assertNotIn('code', answer)

    def test_pending_result_is_not_downgraded_by_late_ready_inspection(self):
        bridge = self.bridge()
        answer = bridge.submit('https://atcoder.jp/contests/abc478/tasks/abc478_d', 'int main(){}', 'fixture')
        sid = answer['sessionId']
        bridge._update(sid, {'status': 'judging', 'attempted': True, 'submissionId': '101'})
        bridge._update(sid, {'status': 'ready'})
        self.assertEqual(bridge.status(sid)['status'], 'judging')
        self.assertTrue(bridge.status(sid)['acceptedAt'])

    def test_terminal_status_survives_local_save_retry_and_late_navigation(self):
        saved = []
        bridge = self.bridge(lambda sid, value: saved.append(value) or len(saved) > 1)
        answer = bridge.submit('https://atcoder.jp/contests/abc478/tasks/abc478_d', 'int main(){}', 'fixture')
        sid = answer['sessionId']
        receipt = {'status': 'finished', 'verdict': 'AC', 'submissionId': '101', 'attempted': True}
        bridge._update(sid, receipt)
        self.assertEqual(bridge.status(sid)['status'], 'judging')
        bridge._update(sid, receipt)
        bridge._update(sid, {'status': 'loading'})
        self.assertEqual(bridge.status(sid)['status'], 'finished')
        self.assertEqual(len(saved), 2)


if __name__ == '__main__':
    unittest.main()
