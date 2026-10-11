"""Behavior and preservation checks for the local update, with disposable state."""
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

# `-s backend` discover 的 sys.path 不含 desktop/common，本测试直接 import 生产代码。
_ROOT = Path(__file__).resolve().parent.parent
for _extra in (_ROOT / "desktop", _ROOT / "backend" / "common"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import test_training as fixtures
from goals import Goals
from training import ServiceError, TrainingService
from window_memory import fit_bounds
from translation import protect,restore


class FeatureTests(unittest.TestCase):
    setUp=fixtures.ServiceTests.setUp
    tearDown=fixtures.ServiceTests.tearDown
    completed=fixtures.ServiceTests.completed
    accept=fixtures.ServiceTests.accept

    def test_chinese_xcpc_names_keep_all_difficulties_and_official_accept_takes_precedence(self):
        from contest_rules import is_xcpc,event_info
        from integrations import IntegrationService
        for name in ('2026年ICPC西安邀请赛','第十届CCPC总决赛','XCPC2026'):
            for difficulty in (50,4500,None):
                row={'contest':name,'difficulty':difficulty}
                self.assertTrue(is_xcpc(row))
                self.assertTrue(IntegrationService._collectable(row,{'minDifficulty':1000,'maxDifficulty':2100}))
                self.assertEqual(event_info(name,[row])['duration'],300)
        self.library.rows[0]['url']='https://codeforces.com/contest/123/problem/A'
        self.completed()
        self.service.record_official({'id':'fixture::A','url':self.library.rows[0]['url'],'code':'int main(){}'},
                                     {'status':'finished','submissionId':'123456','verdict':'AC'})
        self.assertEqual(self.service.workspace()['training'][0]['scope'],'official')
        self.completed(code='WA');self.assertEqual(self.service.workspace()['training'][0]['scope'],'official')

    def test_native_receipt_before_http_registration_is_saved_without_frontend_poll(self):
        import threading
        from backend import LocalServer
        self.library.rows[0]['url']='https://codeforces.com/contest/123/problem/A'
        server=object.__new__(LocalServer)
        server.training=self.service;server.official_sessions={};server.official_pending_receipts={};server.official_session_lock=threading.RLock()
        receipt={'status':'finished','submissionId':'123456','verdict':'AC'}
        server.record_official_receipt('fast',receipt)
        self.assertEqual(self.service.submissions()['total'],0)
        server.register_official_session('fast',{'id':'fixture::A','url':self.library.rows[0]['url'],'code':'int main(){}'},{'status':'submitted'})
        self.assertEqual(self.service.submissions()['total'],1)
        self.assertTrue(self.service.workspace()['training'][0]['accepted'])
        self.assertEqual(server.official_pending_receipts,{})

    def test_native_pending_uses_registered_problem_url_and_immutable_code(self):
        import threading
        from backend import LocalServer
        self.library.rows[0]['url']='https://codeforces.com/contest/123/problem/A'
        server=object.__new__(LocalServer)
        server.training=self.service;server.official_sessions={};server.official_pending_receipts={};server.official_session_lock=threading.RLock()
        original={'id':'fixture::A','url':self.library.rows[0]['url'],'code':'int main(){}'}
        server.register_official_session('pending',original,{'status':'ready'})
        server.register_official_session('pending',{**original,'code':'int main(){return 1;}'},{'status':'ready'})
        stamp='2026-10-11T00:00:00+00:00'
        saved=server.record_official_pending('pending',{'submissionId':'123456','acceptedAt':stamp,'url':'https://codeforces.com/contest/123/submit'})
        self.assertEqual(saved['problemId'],'fixture::A')
        self.assertEqual(saved['url'],original['url'])
        self.assertEqual(saved['code'],original['code'])
        self.assertEqual(self.service.official_pending(original['url'],original['code'])[0]['acceptedAt'],stamp)

    def test_clear_keeps_drafts_codes_results_identity_goals_and_rejoin(self):
        self.service.start_training('fixture::A');self.accept();self.service.save_draft('fixture::A','int main(){} // preserved')
        self.service.start_practice_set('fixture')
        identity=self.service.profile()['profile']['userId']
        goal=Goals(self.service).save({'title':'练习计划','deadline':'2026-11-08','totalProblems':5})['goals'][0]
        cleared=self.service.clear_training()
        self.assertEqual(cleared['cleared'],8);self.assertEqual(cleared['workspace']['training'],[])
        self.assertEqual(self.service.problem('fixture::A')['draft'],'int main(){} // preserved')
        self.assertEqual(len(self.service.submissions()['submissions']),1)
        self.assertEqual(self.service.profile()['profile']['userId'],identity)
        self.assertEqual(Goals(self.service).list()['goals'][0]['id'],goal['id'])
        self.service.start_training('fixture::A')
        self.assertTrue(self.service.workspace()['training'][0]['accepted'])

    def test_clear_rejects_running_contest_and_pending_judge_atomically(self):
        self.service.submit('fixture::A','BLOCK')
        with self.assertRaises(ServiceError):self.service.clear_training()
        self.judge.release.set()
        self.completed('fixture::B')
        plan=self.service.preview_contest({'mode':'single'})['plan']
        self.service.start_contest({'ids':[slot['id'] for slot in plan['slots']],'duration':plan['duration']})
        with self.assertRaises(ServiceError):self.service.clear_training()
        self.assertGreater(self.service.workspace()['summary']['total'],0)

    def test_replay_keeps_unknown_easiest_extreme_solved_order_and_native_duration(self):
        self.library.rows[0].update(difficulty=50,problem='A',startedAt='2026-09-01T01:00:00Z',endedAt='2026-09-01T06:00:00Z')
        self.library.rows[1].update(difficulty=4500,problem='B')
        self.library.rows[2].update(difficulty=None,problem='C')
        for row in self.library.rows:row['contest']='ICPC fixture';row['contestProblemCount']=8
        self.completed()
        plan=self.service.preview_contest({'mode':'replay','contest':'ICPC fixture','excludeSolved':True,'min':1500,'max':1600})['plan']
        self.assertEqual(len(plan['slots']),8);self.assertEqual(plan['duration'],300)
        self.assertEqual([slot['letter'] for slot in plan['slots']],list('ABCDEFGH'))
        self.assertFalse(any('difficulty' in slot or 'tags' in slot for slot in plan['slots']))
        contest=self.service.start_contest({'ids':[slot['id'] for slot in plan['slots']],'duration':300,'previewId':plan['previewId']})['contest']
        self.assertEqual(contest['constraints']['rules'],'xcpc')
        with self.assertRaises(ServiceError):self.service.assert_solution_unlocked('fixture::A')
        finished=self.service.finish_contest(contest['id'])['contest']
        self.assertEqual([slot['difficulty'] for slot in finished['slots']][:3],[50,4500,None])

    def test_replay_rejects_partial_catalog_and_missing_statement(self):
        self.library.rows[0]['contestProblemCount']=9
        with self.assertRaisesRegex(ServiceError,'题单尚不完整'):self.service.preview_contest({'mode':'replay','contest':'fixture'})
        self.library.rows[0].pop('contestProblemCount')
        with patch.object(self.assets,'candidates',return_value=[]),self.assertRaisesRegex(ServiceError,'尚缺完整题面'):
            self.service.preview_contest({'mode':'replay','contest':'fixture'})

    def test_xcpc_custom_penalty_freezes_and_ce_does_not_penalize_by_default(self):
        plan=self.service.preview_contest({'mode':'single','rules':'xcpc','wrongPenalty':30})['plan']
        self.assertEqual(plan['duration'],300)
        with self.assertRaises(ServiceError):self.service.start_contest({'ids':[plan['slots'][0]['id']],'duration':300,'wrongPenalty':10})
        contest=self.service.start_contest({'ids':[plan['slots'][0]['id']],'duration':300})['contest'];identity=plan['slots'][0]['id']
        self.completed(identity,'CE',contest_id=contest['id']);self.completed(identity,'WA',contest_id=contest['id'])
        self.clock.advance(minutes=15);self.completed(identity,contest_id=contest['id'])
        self.assertEqual(self.service.contest(contest['id'])['contest']['penalty'],45)

    def test_goals_dates_capacity_daily_progress_unique_and_restart(self):
        planner=Goals(self.service)
        result=planner.save({'title':'CF 2200','deadline':'2026-10-09','dailyMinutes':30,'currentRating':1000})
        goal=result['goals'][0];self.assertTrue(goal['warnings']);self.assertEqual(goal['progress'],0)
        self.clock.advance(seconds=1);self.service.start_training('fixture::A');self.accept(submission_id=9301);self.assertEqual(planner.list()['goals'][0]['progress'],1)
        self.clock.advance(minutes=1);self.service.start_training('fixture::B');self.accept('fixture::B',submission_id=9302)
        goal=planner.list()['goals'][0];self.assertEqual(goal['progress'],2);self.assertEqual(goal['dailyTask']['progress'],2)
        self.accept('fixture::B',submission_id=9303);self.assertEqual(planner.list()['goals'][0]['progress'],2)
        self.service.start_training('fixture::H');self.accept('fixture::H',submission_id=9304);self.assertEqual(planner.list()['goals'][0]['progress'],3)
        self.service.close();self.service=TrainingService(self.library,self.db,self.assets,self.judge,self.clock,self.root/'backups')
        self.assertEqual(Goals(self.service).list()['goals'][0]['progress'],3)
        self.clock.advance(days=3);self.assertTrue(any('截止日期已过' in s for s in Goals(self.service).list()['goals'][0]['warnings']))
        with self.assertRaises(ServiceError):Goals(self.service).save({'title':'过期','deadline':'2026-10-01'})

    def test_official_receipt_persists_once_as_official_accept_and_preserves_on_restart(self):
        url='https://codeforces.com/contest/123/problem/A';self.library.rows[0]['url']=url
        session={'id':'fixture::A','url':url,'code':'int main(){}'}
        receipt={'status':'finished','submissionId':'123456','verdict':'AC'}
        first=self.service.record_official(session,receipt)
        self.service.record_official(session,receipt)
        self.assertEqual(len(self.service.submissions()['submissions']),1)
        self.assertEqual(first['scope'],'official');self.assertTrue(self.service.workspace()['training'][0]['accepted'])
        self.assertIn('codeforces.com/contest/123/problem/A',self.service._solved_problem_keys(self.library.rows))
        self.assertEqual(self.service.insights()['summary']['officialSolved'],1)
        self.assertEqual(self.service.insights()['summary']['localAccepted'],0)
        self.service.close();self.service=TrainingService(self.library,self.db,self.assets,self.judge,self.clock,self.root/'backups')
        self.assertTrue(self.service.workspace()['training'][0]['accepted'])
        self.assertEqual(self.service.workspace()['training'][0]['scope'],'official')
        self.assertEqual(self.service.submissions()['submissions'][0]['code'],'int main(){}')
        self.completed(code='WA')
        self.assertTrue(self.service.workspace()['training'][0]['accepted'])
        self.assertEqual(self.service.workspace()['training'][0]['scope'],'official')


class ProtectionTests(unittest.TestCase):
    def test_window_offscreen_negative_display_normal_maximized_and_invalid_bounds(self):
        screens=[(0,0,1920,1040),(-1920,0,1920,1040)]
        saved={'x':-1800,'y':100,'width':1200,'height':750,'maximized':True}
        self.assertEqual(fit_bounds(saved,screens),saved)
        moved=fit_bounds(saved,[screens[0]])
        self.assertGreaterEqual(moved['x'],0);self.assertTrue(moved['maximized'])
        self.assertLessEqual(fit_bounds({},[(0,0,1280,720)])['height'],720)

    def test_formula_reordering_only_within_same_paragraph_and_no_duplicates(self):
        original='Output $a$ after $q$ operations.\n\nGiven $n$.'
        shielded,tokens=protect(original);names=list(tokens)
        swapped=shielded.replace(names[0],'SWAP').replace(names[1],names[0]).replace('SWAP',names[1]).replace('Output','输出')
        self.assertIn('$a$',restore(swapped,tokens))
        with self.assertRaises(ServiceError):restore(swapped+names[0],tokens)
        with self.assertRaises(ServiceError):restore(swapped.replace(names[0],'SWAP').replace(names[-1],names[0]).replace('SWAP',names[-1]),tokens)


class APIProtectionTests(unittest.TestCase):
    setUp=fixtures.HTTPTests.setUp
    tearDown=fixtures.HTTPTests.tearDown
    request=fixtures.HTTPTests.request

    def test_new_write_endpoints_need_session_token_and_goal_receipt_has_no_public_write(self):
        for endpoint in ('training/clear','goals/save','goals/archive'):
            self.assertEqual(self.request('POST','/api/'+endpoint,{},token=False)[0],403)
        self.assertEqual(self.request('GET','/api/goals')[0],200)
        self.assertEqual(self.request('GET','/api/contests/events')[0],200)
        self.assertEqual(self.request('POST','/api/official/record',{'verdict':'AC'})[0],404)
