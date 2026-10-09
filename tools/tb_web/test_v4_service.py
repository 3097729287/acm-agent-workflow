"""v4 samples, recommendation bands, API and mock protection in temporary stores."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import time
import unittest
from urllib.parse import quote
import backend
import judge
from insights import build_insights
from training import TrainingService,UTC
import test_training as legacy
import test_v3_service as v3

CODE='#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<"\\n";}'

class SampleAssets:
    def __init__(self):
        self.samples=[{'name':'样例 1','input':'2 3\n','output':'5\n'},{'name':'样例 2','input':'10 4\n','output':'14\n'}]
        self.data={'scope':'local','cases':self.samples+[{'name':'hidden','input':'99 1\n','output':'100\n'}], 'limits':{'timeMs':600,'memoryMb':128}}
    def problem(self,identity):return {'samples':self.samples,'judge':{'scope':'local'}}
    def bundle(self,identity):return self.data

class SampleRunTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='tb-v4-samples-');self.root=Path(self.temp.name);self.assets=SampleAssets()
        self.engine=judge.Judge(self.assets,self.root/'jobs');self.library=legacy.Library();self.clock=legacy.Clock()
        self.service=TrainingService(self.library,self.root/'personal.sqlite',self.assets,self.engine,self.clock,self.root/'backups')
    def tearDown(self):self.service.close();self.temp.cleanup()
    def completed(self,code=CODE,**kwargs):
        value=self.service.submit('fixture::A',code,mode='run',**kwargs)['submission'];until=time.monotonic()+10
        while time.monotonic()<until:
            value=self.service.submission(value['id'])['submission']
            if value['finishedAt']:return value
            time.sleep(.02)
        self.fail('Real sample job did not finish')
    def test_official_samples_compare_persist_without_hidden_cases_or_progress(self):
        value=self.completed(sample_run=True)
        self.assertEqual(value['verdict'],'SAMPLE_PASS');self.assertEqual(value['total'],2)
        self.assertEqual([case['expected'] for case in value['caseResults']],['5\n','14\n'])
        self.assertEqual([case['actual'] for case in value['caseResults']],['5\r\n','14\r\n'])
        self.assertTrue(all(case['verdict']=='SAMPLE_PASS' for case in value['caseResults']))
        self.assertEqual(self.service.workspace()['summary']['total'],0)
        self.service.close();self.service=TrainingService(self.library,self.root/'personal.sqlite',self.assets,self.engine,self.clock,self.root/'backups')
        self.assertEqual(self.service.submission(value['id'])['submission']['caseResults'],value['caseResults'])
        self.assertEqual(list((self.root/'jobs').iterdir()),[])
    def test_wrong_sample_shows_each_expected_and_actual(self):
        value=self.completed(CODE.replace('a+b','a-b'),sample_run=True)
        self.assertEqual(value['verdict'],'WA');self.assertEqual(value['passed'],0)
        self.assertEqual([case['actual'] for case in value['caseResults']],['-1\r\n','6\r\n'])
        self.assertEqual([case['verdict'] for case in value['caseResults']],['WA','WA'])
    def test_custom_input_including_empty_has_no_fabricated_expected(self):
        value=self.completed(sample_run=False,input_text='8 9\n')
        self.assertEqual(value['verdict'],'RUN_OK');self.assertEqual(value['passed'],0)
        self.assertIsNone(value['caseResults'][0]['expected']);self.assertEqual(value['caseResults'][0]['actual'],'17\r\n')
        value=self.completed('int main(){}',sample_run=False,input_text='')
        self.assertEqual(value['verdict'],'RUN_OK');self.assertIsNone(value['caseResults'][0]['expected'])
    def test_whitespace_and_checker_same_rules_as_submit(self):
        value=self.completed(CODE.replace('a+b<<"\\n"','" \\t"<<a+b<<" \\n\\n"'),sample_run=True)
        self.assertEqual(value['verdict'],'SAMPLE_PASS')
        self.assets.data['checker']=lambda inp,out,expected:int(out.strip())==int(expected.strip())
        value=self.completed(CODE.replace('a+b<<"\\n"','"0"<<a+b<<"\\n"'),sample_run=True)
        self.assertEqual(value['verdict'],'SAMPLE_PASS')
    def test_compile_and_runtime_errors_are_truthful(self):
        value=self.completed('not C++',sample_run=True)
        self.assertEqual(value['verdict'],'CE');self.assertTrue(value['stderr'])
        value=self.completed('int main(){return 7;}',sample_run=True)
        self.assertEqual(value['verdict'],'RE');self.assertEqual(value['caseResults'][0]['exitCode'],7)
    def test_case_payload_is_bounded_and_utf8_safe(self):
        values=[{'name':'n','input':'汉'*70000,'expected':'汉'*70000,'actual':'汉'*70000,'verdict':'WA'}]*100
        result=TrainingService._case_results(values)
        self.assertLessEqual(sum(len((case[key] or '').encode()) for case in result for key in ('input','expected','actual')),262144)
        self.assertLessEqual(len(result),100)

class RecommendationTests(unittest.TestCase):
    def row(self,identity,difficulty,tags):return {'id':identity,'title':'题目 '+identity,'difficulty':difficulty,'tags':tags,'platform':'测试','contest':'fixture','source':'archive'}
    def insights(self,rows,records=None,hub=None,training=None):
        workspace={'training':training or [],'contests':[]}
        return build_insights(rows,records or [],[],workspace,hub or {},dt.datetime(2026,10,8,12,tzinfo=UTC))
    def test_cold_start_introductory_true_problem_not_advanced_or_alphabetical(self):
        rows=[self.row('advanced',1100,['Hall 定理']),self.row('dfs-order',1100,['DFS序']),self.row('dp',1150,['线性 DP']),self.row('hard',2100,['模拟']),self.row('basic',1100,['排序']),self.row('enumerate',1200,['枚举'])]
        value=self.insights(rows)
        self.assertIsNone(value['assessment']['rating']);self.assertEqual(value['assessment']['recommendationLevel'],1100)
        self.assertEqual({item['problem']['id'] for item in value['recommendations']},{'basic','enumerate'})
        self.assertTrue(all(item['stage']=='foundation' for item in value['recommendations']))
        self.assertEqual(value['recommendations'][0]['band'],{'min':1000,'max':1250,'target':1100})
    def test_real_evidence_moves_band_and_due_cannot_force_excessive_difficulty(self):
        rows=[self.row('p1',1300,['排序']),self.row('p2',1500,['前缀和']),self.row('p3',1700,['枚举']),self.row('next',1550,['BFS']),self.row('hall',1500,['Hall 定理']),self.row('too-hard',2100,['模拟'])]
        records=[{'problem_id':row['id'],'mode':'submit','finished_at':'2026-10-08T10:00:00Z','submitted_at':'2026-10-08T09:00:00Z','verdict':'AC','scope':'local','solution_seen':0,'code':'code '+row['id']} for row in rows[:3]]
        value=self.insights(rows,records,training=[dict(rows[-1],queue='fill',accepted=False)])
        self.assertEqual(value['assessment']['recommendationLevel'],1500)
        self.assertEqual([item['problem']['id'] for item in value['recommendations']],['next'])
        self.assertEqual(value['recommendations'][0]['stage'],'stretch')
    def test_cf_rating_can_guide_band_other_platform_rating_not_converted(self):
        rows=[self.row('intro',1100,['排序']),self.row('near-cf',1450,['排序'])]
        value=self.insights(rows,hub={'accounts':[{'platform':'atcoder','status':'ready','rating':2000,'solved':[]}]})
        self.assertEqual(value['assessment']['recommendationLevel'],1100)
        value=self.insights(rows,hub={'accounts':[{'platform':'codeforces','status':'ready','rating':1550,'solved':[]}]})
        self.assertEqual(value['assessment']['recommendationLevel'],1450);self.assertIsNone(value['assessment']['rating'])

class LectureFixture:
    def snapshot(self):return {'lectures':[{'id':'lesson','sourceProblemIds':['remote:codeforces:123::A'],'title':'从零讲排序'}],'revision':'fixture'}
    def get(self,identity):return {'id':identity,'sourceProblemIds':['remote:codeforces:123::A'],'markdown':'### 从零讲排序\n真实fixture正文'}
    def for_problem(self,identity):return self.snapshot()['lectures']

class TranslationFixture:
    def __init__(self):self.calls=[]
    def translate(self,identity):self.calls.append(identity);return {'id':identity,'markdown':'原题中文fixture','sourceLanguage':'en','targetLanguage':'zh-CN','provider':'fixture','cached':False}

class AdditiveHTTPTests(unittest.TestCase):
    setUp=v3.OverlayHTTPTests.setUp
    tearDown=v3.OverlayHTTPTests.tearDown
    request=v3.OverlayHTTPTests.request
    def test_lecture_translation_and_official_session_endpoints(self):
        self.server.lectures=LectureFixture();self.server.translation=TranslationFixture()
        self.assertEqual(self.request('/api/lectures')[1]['revision'],'fixture')
        self.assertEqual(self.request('/api/lecture?id=lesson')[0],200)
        self.assertEqual(self.request('/api/problem/translate',{'id':self.remote['id']})[1]['provider'],'fixture')
        sessions={}
        def opened(url,code,title):sessions['native']={'sessionId':'native','status':'needs_login','url':url};return sessions['native']
        self.server.official_submitter=opened;self.server.official_status=lambda identity:sessions[identity]
        self.server.official_closer=lambda identity:{'status':'closed'}
        status,value=self.request('/api/official/submit',{'id':self.remote['id'],'code':'int main(){}'})
        self.assertEqual(status,200);self.assertEqual(value['status'],'needs_login')
        self.assertEqual(self.request('/api/official/status?sessionId=native')[1]['status'],'needs_login')
        self.assertEqual(self.request('/api/official/close',{'sessionId':'native'})[1]['status'],'closed')
        self.assertEqual(self.request('/api/official/submit',{'id':self.remote['id'],'code':'int main(){}'},token=False)[0],403)
    def test_active_mock_protects_lecture_translation_and_official_reentry(self):
        self.server.lectures=LectureFixture();self.server.translation=TranslationFixture();self.server.training.assets=legacy.Assets(self.server.store)
        self.server.official_opener=lambda url,code,title:{'sessionId':'native','status':'ready'}
        self.server.official_status=lambda identity:{'sessionId':identity,'status':'ready'}
        closed=[];self.server.official_closer=lambda identity:closed.append(identity) or {'status':'closed'}
        self.request('/api/official/open',{'id':self.remote['id'],'code':'int main(){}'})
        plan=self.server.training.preview_contest({'count':1,'min':1300,'max':1300})['plan']
        status,value=self.request('/api/contests/start',{'ids':[slot['id'] for slot in plan['slots']],'duration':120})
        self.assertEqual(status,200);self.assertEqual(closed,[None])
        self.assertEqual(self.request('/api/lecture?id=lesson')[0],403)
        self.assertEqual(self.request('/api/official/status?sessionId=native')[0],403)
        self.assertEqual(self.request('/api/problem/translate',{'id':self.remote['id']})[0],403)
        self.assertEqual(self.request('/api/problem/translate',{'id':self.remote['id'],'contestId':value['contest']['id']})[0],200)
    def test_actual_contest_times_and_solution_lecture_refs(self):
        self.server.lectures=LectureFixture()
        directory,source=backend.toolutil.contest_paths(str(self.root),'ABC',478)
        source=Path(source);source.parent.mkdir(parents=True)
        source.write_text('# ABC 478\nhttps://atcoder.jp/contests/abc478\n## 目录\n| 题号 | 题名 | 考点 | 难度 |\n|---|---|---|---|\n| D | 原归档 | 排序 | 1100 |\n## D. 原归档\n正文\n',encoding='utf-8')
        raw=Path(directory)/'_work'/'raw';raw.mkdir(parents=True)
        (raw/'contest.html').write_text('var startTime = moment("2026-10-08T21:00:00+09:00"); var endTime = moment("2026-10-08T22:40:00+09:00");',encoding='utf-8')
        value=self.server.store.data()['rows'][0]
        self.assertEqual(value['contestDate'],'2026-10-08T12:00:00+00:00')
        self.assertNotEqual(value['contestDate'][:10],value['date'])
        self.assertEqual(self.request('/api/solution?id='+quote('ABC 478::D'))[1]['lectures'][0]['id'],'lesson')

if __name__=='__main__':unittest.main()
