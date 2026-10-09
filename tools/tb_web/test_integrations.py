"""Isolated fixtures: public schemas, retries, schedule and no archive writes."""
import base64
import datetime as dt
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import sys
_test_common = Path(__file__).resolve().parent / "common"
sys.path.insert(0,str(_test_common if _test_common.is_dir() else Path(__file__).resolve().parent.parent))
import assets
import integrations as I
import public_platforms as P
from training import ServiceError

NOW=dt.datetime(2026,10,8,tzinfo=dt.timezone.utc)

class Store:
    data_root='fixture-unused'
    values=[]
    def raw_rows(self):return list(self.values)
    def encode_row(self,row,today):return row['encoded']
    def row(self,identity):return self.extensions.row(identity)

class Client:
    def __init__(self,responses=None):self.responses=responses or {};self.calls=[]
    def json(self,url,headers=None):
        self.calls.append(url);value=self.responses.get(url)
        if isinstance(value,Exception):raise value
        if value is None:raise RuntimeError('HTTP 404 fixture '+url)
        return value
    def text(self,url,headers=None):return self.json(url,headers)

def completed_row(index='A',difficulty=1300,url=None):
    return P.row('codeforces',{'id':1,'name':'Fixture finished','start':1,'end':100},index,'Fixture '+index,url or 'https://codeforces.com/contest/1/problem/'+index,difficulty,'Codeforces 官方 rating',['贪心'])

class PublicSchemaTests(unittest.TestCase):
    def test_cf_finished_and_missing_rating_do_not_guess(self):
        client=Client({'https://codeforces.com/api/contest.list?gym=false':{'status':'OK','result':[{'id':1,'name':'Ended','phase':'FINISHED','startTimeSeconds':1,'durationSeconds':100},{'id':2,'name':'Future','phase':'FINISHED','startTimeSeconds':int(NOW.timestamp())+100,'durationSeconds':1}]},'https://codeforces.com/api/problemset.problems':{'status':'OK','result':{'problems':[{'contestId':1,'index':'A','name':'Rated','rating':1300,'tags':['greedy']},{'contestId':1,'index':'B','name':'Unrated','tags':[]},{'contestId':2,'index':'A','name':'Future','rating':1300}]}}})
        rows,pending,_=P.discover_cf(client,NOW)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['difficulty'],1300);self.assertEqual(rows[0]['tags'],['贪心']);self.assertEqual(len(pending),1)
    def test_cf_exact_url_earliest_accept_and_unique_counts(self):
        prefix='https://codeforces.com/api/'
        submissions=[{'creationTimeSeconds':200,'verdict':'OK','problem':{'contestId':1,'index':'A','name':'P','tags':['dp'],'rating':1400}},{'creationTimeSeconds':100,'verdict':'OK','problem':{'contestId':1,'index':'A','name':'P','tags':['dp'],'rating':1400}},{'creationTimeSeconds':50,'verdict':'WRONG_ANSWER','problem':{'contestId':1,'index':'B'}}]
        client=Client({prefix+'user.info?handles=fixture':{'status':'OK','result':[{'handle':'fixture','rating':1400,'maxRating':1500,'rank':'specialist'}]},prefix+'user.rating?handle=fixture':{'status':'OK','result':[{'newRating':1400,'ratingUpdateTimeSeconds':80,'contestName':'C','rank':1}]},prefix+'user.status?handle=fixture&from=1&count=1000':{'status':'OK','result':submissions}})
        value=P.account_cf(client,'fixture');self.assertEqual(value['solvedCount'],1);self.assertEqual(value['submissionCount'],3)
        self.assertEqual(value['solved'][0]['url'],'https://codeforces.com/contest/1/problem/A');self.assertEqual(value['solved'][0]['acceptedAt'],P.utc(100));self.assertEqual(sum(x['accepted'] for x in value['activity']),1)
    def test_luogu_does_not_substitute_social_score_for_rating(self):
        client=Client({'https://www.luogu.com.cn/user/1':{'status':200,'data':{'user':{'uid':1,'name':'Fixture','eloValue':None,'passedProblemCount':None,'ranking':5},'gu':{'rating':9999},'elo':[]}}})
        value=P.account_lg(client,'1');self.assertIsNone(value['rating']);self.assertIsNone(value['solvedCount']);self.assertIsNone(value['submissionCount']);self.assertEqual(value['status'],'partial')
    def test_atcoder_rating_history_preserves_own_scale_unknown_solved(self):
        client=Client({'https://atcoder.jp/users/fixture/history/json':[{'IsRated':True,'NewRating':800,'EndTime':'2026-01-01T12:00:00+09:00','ContestName':'ABC','Place':10}],'https://atcoder.jp/users/fixture?lang=en':'<a href="/users/fixture">fixture</a>'})
        value=P.account_at(client,'fixture');self.assertEqual(value['rating'],800);self.assertIsNone(value['solvedCount']);self.assertIsNone(value['submissionCount']);self.assertEqual(value['solved'],[])
    def test_atcoder_ended_duration_and_missing_difficulty_pending(self):
        html='<tr><td><time>2026-10-01 12:00:00+0900</time></td><td><a href="/contests/abc001">ABC 001</a></td><td>01:40</td></tr><tr><td><time>2027-10-01 12:00:00+0900</time></td><td><a href="/contests/abc002">Future</a></td><td>01:40</td></tr>'
        tasks='<td class="text-center no-break"><a href="/contests/abc001/tasks/abc001_c">C</a></td><td><a href="/contests/abc001/tasks/abc001_c">Unrated</a></td>'
        rows,pending,_=P.discover_at(Client({'https://atcoder.jp/contests/archive?lang=en':html,'https://atcoder.jp/contests/abc001/tasks?lang=en':tasks}),NOW)
        self.assertEqual(rows,[]);self.assertEqual(len(pending),1);self.assertEqual(pending[0]['contestId'],'abc001')
    def test_atcoder_models_reuse_existing_cf_eq_estimate_and_keep_missing(self):
        page='<tr><td><time>2026-10-01 12:00:00+0900</time></td><td><a href="/contests/abc001">ABC 001</a></td><td>01:40</td></tr>'
        tasks='<td class="text-center no-break"><a href="/contests/abc001/tasks/abc001_c">C</a></td><td><a href="/contests/abc001/tasks/abc001_c">Rated</a></td><td class="text-center no-break"><a href="/contests/abc001/tasks/abc001_d">D</a></td><td><a href="/contests/abc001/tasks/abc001_d">Unrated</a></td>'
        client=Client({'https://atcoder.jp/contests/archive?lang=en':page,'https://atcoder.jp/contests/abc001/tasks?lang=en':tasks,'https://kenkoooo.com/atcoder/resources/problem-models.json':{'abc001_c':{'difficulty':1000}}})
        rows,pending,_=P.discover_at(client,NOW)
        import cf_eq
        self.assertEqual(rows[0]['difficulty'],cf_eq.cf_eq_atcoder(1000)['cf_eq_rating']);self.assertEqual(rows[0]['difficultySource'],'CF-EQ · AtCoder Problems估算');self.assertEqual(len(pending),1)
    def test_nowcoder_score_and_accept_ratio_not_difficulty(self):
        meta={'contestStartTime':1,'contestEndTime':100}
        page='<div data-id="1" data-json="'+json.dumps(meta).replace('"','&quot;')+'"><h4><a>Fixture</a></h4></div>'
        client=Client({'https://ac.nowcoder.com/acm/contest/vip-index':page,'https://ac.nowcoder.com/acm/contest/problem-list?token=&id=1':{'code':0,'data':{'data':[{'index':'C','title':'P','score':200,'acceptedCount':2,'submitCount':100}]}}})
        rows,pending,_=P.discover_nc(client,NOW);self.assertEqual(rows,[]);self.assertEqual(len(pending),1);self.assertIn('难度',pending[0]['reason'])
    def test_nowcoder_partial_only_explicit_profile_fields(self):
        page='<h1 class="profile-name">Fixture</h1><p>Rating: 1200</p>'
        value=P.account_nc(Client({'https://ac.nowcoder.com/acm/contest/profile/1':page}),'1')
        self.assertEqual(value['rating'],1200);self.assertIsNone(value['solvedCount']);self.assertIsNone(value['maxRating'])

class CacheSafetyTests(unittest.TestCase):
    def test_get_host_validation_cache_and_failure_keeps_old_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            calls=[]
            def transport(url,headers):calls.append(url);return b'{"public":true}','etag'
            client=I.PublicClient(root,transport=transport,spacing=0)
            url='https://api.github.com/repos/owner/repo/releases'
            self.assertEqual(client.json(url),{'public':True});self.assertEqual(client.json(url),{'public':True});self.assertEqual(len(calls),1)
            for bad in ('http://api.github.com/a','https://localhost/a','https://api.github.com:123/a','https://user:password@api.github.com/a'):
                with self.subTest(url=bad),self.assertRaises(ValueError):client.text(bad)
            path=next((Path(root)/'http').glob('*.json'));saved=json.loads(path.read_text());saved['at']=0;path.write_text(json.dumps(saved))
            client.transport=lambda *_:(_ for _ in ()).throw(OSError('offline'))
            with self.assertRaises(RuntimeError):client.json(url)
            self.assertEqual(json.loads(path.read_text())['text'],'{"public":true}')
            self.assertTrue(client.backoff)
    def test_constructor_and_snapshot_do_not_wait_for_network(self):
        with tempfile.TemporaryDirectory() as root:
            client=Client();service=I.IntegrationService(Store(),root,auto_start=False,client=client)
            self.assertEqual(client.calls,[]);self.assertEqual(service.snapshot()['settings']['githubRepo'],I.KNOWN_REPO);self.assertEqual(len(service.snapshot()['accounts']),4);service.close()

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=Store();self.client=Client();self.service=I.IntegrationService(self.store,self.root,auto_start=False,client=self.client,clock=lambda:NOW);self.store.extensions=self.service
    def tearDown(self):self.service.close();self.temp.cleanup()
    def test_strict_filter_dedupe_local_first_and_unknown_pending(self):
        values=[completed_row('A',999),completed_row('B',1000),completed_row('C',2199),completed_row('D',2200)]
        with patch.dict(P.DISCOVERY_ADAPTERS,{'codeforces':lambda *_:(values,[{'reason':'missing'}],'fixture')}):
            result=self.service._catalog('codeforces',{'https://codeforces.com/contest/1/problem/B'})
        self.assertEqual([r['problem'] for r in self.service.rows()],['C']);self.assertEqual(result['added'],1);self.assertEqual(result['pending'],1)
        self.assertTrue(self.service.row(values[2]['id'])['_remote']);self.assertEqual(self.service.snapshot()['notifications'][0]['type'],'catalog')
    def test_failures_keep_account_and_catalog(self):
        value=completed_row();self.service.state['rows'][value['id']]=value;self.service.state['settings']['accounts']['codeforces']='fixture';self.service.state['accounts']['codeforces']=dict(P.profile('codeforces','fixture'),rating=1500,solvedCount=1,status='ready')
        self.service._account('codeforces');hub=self.service.snapshot()
        self.assertEqual(hub['accounts'][0]['rating'],1500);self.assertEqual(hub['accounts'][0]['solvedCount'],1);self.assertEqual(hub['accounts'][0]['status'],'error');self.assertEqual(len(self.service.rows()),1)
    def test_updated_out_of_scope_rating_preserves_history_row_but_excludes_library(self):
        old=completed_row();self.service.state['rows'][old['id']]=old
        with patch.dict(P.DISCOVERY_ADAPTERS,{'codeforces':lambda *_:([completed_row(difficulty=2300)],[],'official updated')}):self.service._catalog('codeforces',set())
        self.assertEqual(self.service.rows(),[]);self.assertEqual(self.service.row(old['id'])['难度'],'2300')
    def test_configuration_clears_binding_validates_and_persists(self):
        self.service._ensure_worker=lambda:None
        hub=self.service.configure({'githubRepo':'https://github.com/owner/repo','accounts':{'codeforces':'fixture'},'intervalHours':1})
        self.assertEqual(hub['settings']['githubRepo'],'owner/repo');self.assertEqual(hub['accounts'][0]['handle'],'fixture')
        self.service.configure({'accounts':{'codeforces':''}});self.assertEqual(self.service.snapshot()['accounts'][0]['status'],'unconfigured')
        for bad in ({'githubRepo':'https://evil.example/a'},{'minDifficulty':999},{'maxDifficulty':2200},{'intervalHours':0},{'accounts':{'luogu':'password?token'}}):
            with self.subTest(body=bad),self.assertRaises(ServiceError):self.service.configure(bad)
        restored=I.IntegrationService(self.store,self.root,auto_start=False,client=self.client);self.assertEqual(restored.snapshot()['settings']['githubRepo'],'owner/repo');restored.close()
    def test_local_baseline_then_new_solution_notification_no_table_write(self):
        raw={'场次':'Fixture','题号':'A','encoded':{'url':'https://codeforces.com/contest/1/problem/A','solutionAvailable':False}}
        self.store.values=[raw];self.service._local();self.assertEqual(self.service.snapshot()['notifications'],[])
        raw['encoded']['solutionAvailable']=True;self.service._local();self.assertEqual(len(self.service.snapshot()['notifications']),1)
        self.service._local();self.assertEqual(len(self.service.snapshot()['notifications']),1)
        identity=self.service.snapshot()['notifications'][0]['id'];self.assertTrue(self.service.dismiss(identity)['notifications'][0]['read'])
    def test_remote_statement_cache_sample_scope_preview_no_network(self):
        value=P.row('luogu',{'id':1,'name':'Fixture','start':1,'end':100},'A','P','https://www.luogu.com.cn/problem/P1002',1150,'CF-EQ 官方档')
        self.service.state['rows'][value['id']]=value
        self.client.responses[value['url']]={'status':200,'data':{'problem':{'pid':'P1002','content':{'description':'Original $n$','formatI':'n','formatO':'answer'},'samples':[['1','2']],'limits':{'time':[1000],'memory':[128000]}}}}
        self.store.data_root=str(self.root);library=assets.AssetLibrary(self.store,self.root/'local-cache')
        self.assertEqual(library.candidates([value]),[]);self.assertEqual(self.client.calls,[])
        problem=library.problem(value['id']);self.assertEqual(problem['judge']['scope'],'samples');self.assertEqual(problem['samples'][0]['output'],'2');self.assertEqual(problem['limits'],{'timeMs':1000,'memoryMb':128})
        self.assertEqual(len(library.candidates([value])),1);self.assertEqual(len(self.client.calls),1);self.assertFalse((self.root/'题解').exists())
    def test_github_release_and_content_notify_once_no_install(self):
        repo='owner/repo';self.service.state['settings']['githubRepo']=repo
        prefix='https://api.github.com/repos/'+repo
        manifest={'schema':1,'contents':[{'id':'solution1','sha256':'abc','title':'Fixture'}]}
        self.client.responses={prefix+'/releases?per_page=20':[{'id':1,'tag_name':'v0.4.1','body':'Fixture notes','published_at':'2026-01-01T00:00:00Z','prerelease':True,'draft':False}],prefix+'/contents/tb-update.json':{'encoding':'base64','size':100,'content':base64.b64encode(json.dumps(manifest).encode()).decode()}}
        self.service._github();self.service._github();hub=self.service.snapshot();self.assertEqual(hub['updates']['latestVersion'],'v0.4.1');self.assertEqual({n['type'] for n in hub['notifications']},{'release','content'});self.assertEqual(len(hub['notifications']),2)
        self.client.responses[prefix+'/releases?per_page=20']=RuntimeError('offline');self.service._github();self.assertEqual(self.service.snapshot()['updates']['latestVersion'],'v0.4.1');self.assertIn('offline',self.service.snapshot()['updates']['error'])
        self.assertFalse((self.root/'downloads').exists())
    def test_release_comparison_uses_actual_current_version(self):
        repo='owner/repo';self.service.state['settings']['githubRepo']=repo
        prefix='https://api.github.com/repos/'+repo
        manifest={'encoding':'base64','size':100,'content':base64.b64encode(json.dumps({'schema':1,'contents':[]}).encode()).decode()}
        for current,latest,expected in [('0.4.0','v0.3.9',False),('0.4.0','v0.4.0',False),('0.4.0','v0.4.1',True),('0.4.0','v0.10.0',True),('2.0.0','v1.9.9',False),('2.0.0','v2.0.1',True),('0.4.0','Tk-v9.0.0',False)]:
            with self.subTest(current=current,latest=latest),patch.object(I,'VERSION',current):
                self.service.state['notifications']=[]
                self.client.responses={prefix+'/releases?per_page=20':[{'id':1,'tag_name':latest,'published_at':'2026-01-01','draft':False}],prefix+'/contents/tb-update.json':manifest}
                self.service._github()
                self.assertEqual(any(n['type']=='release' for n in self.service.snapshot()['notifications']),expected)
                self.assertEqual(self.service.snapshot()['updates']['currentVersion'],current)
    def test_async_sync_is_immediate_and_real_periodic_refresh(self):
        clock=[NOW];started=threading.Event();unblock=threading.Event();calls=[]
        def refresh(selected):
            calls.append(selected);started.set();unblock.wait(2)
            self.service.state['sync']['nextCheckAt']=(clock[0]+dt.timedelta(hours=1)).isoformat()
        self.service._refresh=refresh;self.service.auto_start=True;self.service.clock=lambda:clock[0]
        before=time.monotonic();hub=self.service.sync();self.assertLess(time.monotonic()-before,.2);self.assertTrue(hub['sync']['busy']);self.assertTrue(started.wait(1));unblock.set()
        deadline=time.monotonic()+2
        while self.service.snapshot()['sync']['busy'] and time.monotonic()<deadline:time.sleep(.01)
        clock[0]+=dt.timedelta(hours=2);self.service.wake.set();deadline=time.monotonic()+2
        while len(calls)<2 and time.monotonic()<deadline:time.sleep(.01)
        self.assertGreaterEqual(len(calls),2,'A real worker performs due periodic refresh')
    def test_repository_change_discards_late_old_notifications(self):
        self.service.state['settings']['githubRepo']='owner/old'
        def late(url,headers=None):
            self.service.state['settings']['githubRepo']='owner/new'
            return [{'id':1,'tag_name':'v0.4.0','published_at':'2026-01-01','draft':False}]
        self.client.json=late;self.service._github()
        self.assertEqual(self.service.snapshot()['notifications'],[]);self.assertEqual(self.service.state['manifestIds'],{})
    def test_personal_statement_cache_preserves_fetched_limits(self):
        library=assets.AssetLibrary(self.store,self.root/'limits-cache')
        identity='fixture::A';url='https://atcoder.jp/contests/abc001/tasks/abc001_a'
        library.cache_dir.mkdir(parents=True)
        library._cache_path(identity).write_text(json.dumps({'id':identity,'url':url,'markdown':'Official statement','samples':[{'name':'Sample','input':'1','output':'2'}],'limits':{'timeMs':1000,'memoryMb':512}}),encoding='utf-8')
        with patch.object(library,'_paths',return_value=({'题名':'Fixture','题号':'A'},None)),patch('status_gui.StatusGui.parse_problem_url',return_value=(url,None)):
            self.assertEqual(library._cached(identity)['limits'],{'timeMs':1000,'memoryMb':512})
    def test_disabled_auto_sync_does_not_contact_network_on_reopen(self):
        self.service.state['settings']['autoSync']=False;self.service._save()
        restarted=I.IntegrationService(self.store,self.root,auto_start=True,client=self.client)
        try:self.assertEqual(self.client.calls,[]);self.assertIsNone(restarted.worker);self.assertFalse(restarted.snapshot()['sync']['busy'])
        finally:restarted.close()

if __name__=='__main__':unittest.main(verbosity=2)
