"""Isolated v4 fixtures: exact targets, source dates, lessons and public translation."""
import datetime as dt
import copy
import hashlib
import json
from pathlib import Path
from persistence import load_document
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
_test_common = Path(__file__).resolve().parent / "common"
sys.path.insert(0,str(_test_common if _test_common.is_dir() else Path(__file__).resolve().parent.parent))
from contestmeta import parse,ContestDates
from lectures import LectureLibrary
from translation import TranslationService,DeepSeekProvider,protect,restore,_local_key
from translation_config import ProviderSettings,existing_provider
from training import ServiceError
import integrations as I
import public_platforms as P


class Store:
    def __init__(self,root):self.data_root=str(root);self.values=[];self.extensions=None
    def raw_rows(self):return list(self.values)
    def encode_row(self,raw,today):return raw['encoded']

class NoNetwork:
    def json(self,*args):raise RuntimeError('fixture deliberately has no public network')
    def text(self,*args):raise RuntimeError('fixture deliberately has no public network')


class DataTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory(prefix='tb-v4-data-');self.root=Path(self.temp.name);self.store=Store(self.root)
    def tearDown(self):self.temp.cleanup()
    def test_exact_catalog_local_targets_and_legacy_no_invented_mapping(self):
        service=I.IntegrationService(self.store,self.root/'state',auto_start=False,client=NoNetwork())
        try:
            row=P.row('codeforces',{'id':1,'name':'Fixture','start':1,'end':2},'A','P','https://codeforces.com/contest/1/problem/A',1300,'official')
            with patch.dict(P.DISCOVERY_ADAPTERS,{'codeforces':lambda *_:([row],[],'actual fixture')}):service._catalog('codeforces',set())
            notification=service.snapshot()['notifications'][0]
            self.assertEqual(notification['problemIds'],[row['id']]);self.assertEqual(notification['problemUrls'],[row['url']]);self.assertEqual(notification['solutionIds'],[])
            original_added=service.rows()[0]['addedAt']
            row.pop('addedAt',None)
            with patch.dict(P.DISCOVERY_ADAPTERS,{'codeforces':lambda *_:([dict(row)],[],'repeat fixture')}):service._catalog('codeforces',set())
            self.assertEqual(service.rows()[0]['addedAt'],original_added)
            self.store.values=[{'场次':'Fixture','题号':'A','encoded':{'url':row['url'],'solutionAvailable':False}}];service._local()
            self.store.values[0]['encoded']['solutionAvailable']=True;service._local()
            self.assertEqual(service.snapshot()['notifications'][0]['solutionIds'],['Fixture::A'])
            service.state['notifications'].append({'id':'old','type':'content','count':607});service._save()
        finally:service.close()
        restored=I.IntegrationService(self.store,self.root/'state',auto_start=False)
        try:
            old=next(n for n in restored.snapshot()['notifications'] if n['id']=='old')
            self.assertEqual(old['problemIds'],[]);self.assertEqual(old['targets'],[]);self.assertIn('精确',old['targetNotice'])
            self.assertEqual(restored.snapshot()['settings']['githubRepo'],I.KNOWN_REPO)
            self.assertEqual(restored.contest_metadata(restored.row(row['id']))['startedAt'],row['startedAt'])
        finally:restored.close()
    def test_catalog_recovery_requires_prior_snapshot_matching_digest_and_notice(self):
        def row(letter):return {'id':'Fixture::'+letter,'platform':'codeforces','url':'https://codeforces.com/contest/1/problem/'+letter}
        first={'rows':{'Fixture::A':row('A')},'notifications':[]}
        unknown={'id':'catalog:codeforces:'+hashlib.sha256(json.dumps(sorted(first['rows'])).encode()).hexdigest()[:16],'type':'catalog','count':1,'title':'Unknown','body':'No before snapshot','createdAt':'earlier'}
        first['notifications']=[unknown]
        second=copy.deepcopy(first);second['rows']['Fixture::B']=row('B')
        digest=hashlib.sha256(json.dumps(sorted(second['rows'])).encode()).hexdigest()[:16]
        exact={'id':'catalog:codeforces:'+digest,'type':'catalog','count':1,'title':'Verified','body':'Actual snapshot delta','createdAt':'actual'}
        second['notifications'].append(exact)
        source=self.root/'state'/'integrations.json';source.parent.mkdir()
        a=self.root/'integrations.json.20261008-100000.bak';b=self.root/'integrations.json.20261008-100001.bak'
        a.write_text(json.dumps(first),encoding='utf-8');b.write_text(json.dumps(second),encoding='utf-8')
        current=copy.deepcopy(second)
        self.assertEqual(I.recover_catalog_targets(source,current,[b,a]),1)
        self.assertEqual(current['notifications'][1]['problemIds'],['Fixture::B'])
        self.assertNotIn('problemIds',current['notifications'][0]);self.assertNotIn('addedAt',current['rows']['Fixture::A'])
        corrupted=copy.deepcopy(second);corrupted['notifications'][1]['body']='Different notice'
        self.assertEqual(I.recover_catalog_targets(source,corrupted,[a,b]),0)
    def test_real_source_times_ignore_status_dates_and_file_mtime(self):
        at='var startTime = moment("2026-10-03T21:00:00+09:00"); var endTime = moment("2026-10-03T22:40:00+09:00");'
        value=parse(at,'https://atcoder.jp/contests/abc478/tasks/abc478_a')
        self.assertEqual(value['contestDate'],'2026-10-03T12:00:00+00:00');self.assertEqual(value['endedAt'],'2026-10-03T13:40:00+00:00')
        lg=parse({'data':{'contestOrigin':{'startTime':100,'endTime':200}}},'https://www.luogu.com.cn/problem/P1')
        self.assertEqual(lg['contestDate'],lg['startedAt']);self.assertIsNone(parse({'date':'2026-10-08'},'https://codeforces.com/contest/1/problem/A')['contestDate'])
        directory=self.root/'题解'/'AtCoder'/'ABC'/'478'/'_work'/'raw';directory.mkdir(parents=True);(directory/'A.html').write_text(at,encoding='utf-8')
        dates=ContestDates(self.store);self.assertEqual(dates.for_row({'场次':'ABC 478','日期':'2026-10-08'},'https://atcoder.jp/contests/abc478/tasks/abc478_a'),value)
        cf={'场次':'Div.2 1'};url='https://codeforces.com/contest/1/problem/A'
        self.assertIsNone(dates.for_row(cf,url)['contestDate'])
        dates.observe_cf([{'id':1,'phase':'FINISHED','startTimeSeconds':100,'durationSeconds':120}])
        self.assertEqual(dates.for_row(cf,url)['contestDate'],'1970-01-01T00:01:40+00:00')
        nc=parse('window.pageInfo = {"startTime":1791111600000,"endTime":1791118800000};','https://ac.nowcoder.com/acm/contest/141142')
        self.assertEqual(nc['contestDate'],'2026-10-04T11:00:00+00:00')
    def _lessons(self):
        folder=self.root/'题解'/'牛客'/'周赛'/'123';folder.mkdir(parents=True)
        body='### 从零讲：构造\n\n'+('先从最小例子看为什么，再给一个可以亲手算的例子。' * 7)+'\n\n公式 $x^2$。\n\n#### 为什么\n\n下一级标题仍属于完整讲解。\n\n'
        text='# 周赛 123 题解\n\n## 目录\n\n| 题号 | 题名 | 考点 | 难度 |\n|---|---|---|---|\n| C | Example | 构造 | 1400 |\n\n## C. Example\n\n'+body+'### 思路\n\n不包含在讲义。\n\n## D. Pointer\n\n### 从零讲：构造\n\n参见《周赛 123 题解》的 C 题从零讲：构造，已讲过。\n'
        path=folder/'123题解.md';path.write_text(text,encoding='utf-8');return path,body
    def test_full_lesson_verbatim_pointer_not_indexed_and_dynamic_signature(self):
        path,body=self._lessons();before=path.read_bytes();library=LectureLibrary(self.store,registry_path=self.root/'absent.md')
        snapshot=library.snapshot();self.assertEqual(len(snapshot['lectures']),1)
        self.assertEqual(library.get(snapshot['lectures'][0]['id'])['sourceMarkdown'],body)
        self.assertEqual(library.for_problem('周赛 123::D')[0]['sourceProblemIds'],['周赛 123::C'])
        self.assertEqual(path.read_bytes(),before)
        path.write_text(path.read_text(encoding='utf-8')+'\n## E. New\n\n'+body.replace('构造','前缀和'),encoding='utf-8');library.last_check=0
        self.assertNotEqual(library.snapshot()['revision'],snapshot['revision']);self.assertEqual(len(library.snapshot()['lectures']),2)
    def test_image_resolution_cannot_escape_archive(self):
        path,body=self._lessons();(path.parent/'figure.png').write_bytes(b'fixture');(self.root/'secret.png').write_bytes(b'never read')
        library=LectureLibrary(self.store)
        images=library._images('![safe](figure.png)\n![escape](../../../../../../secret.png)',path)
        self.assertEqual(set(images),{'figure.png'});self.assertTrue(images['figure.png'].startswith('data:image/png;'))


class TranslationTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory(prefix='tb-v4-translation-');self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_existing_provider_requires_explicit_safe_endpoint_and_model(self):
        home=self.root/'dsh';folder=home/'profiles'/'dsh-tui-safe';folder.mkdir(parents=True)
        path=folder/'cordis.patch.yml'
        text='config:\n  providers:\n    huoshan:\n      baseURL: https://ark.cn-beijing.volces.com/api/plan/v3\n      apiKeyEnv: HUOSHAN_API_KEY\n      models:\n        - id: deepseek-v4.1-flash\n'
        path.write_text(text,encoding='utf-8')
        self.assertEqual(existing_provider(home),{'provider':'huoshan','model':'deepseek-v4.1-flash'})
        with patch.dict('os.environ',{'DSH_HOME':str(home),'HUOSHAN_API_KEY':'fixture-'+('a'*32)},clear=True):
            settings=ProviderSettings(self.root/'state');status=settings.status()
            self.assertEqual(status['provider'],'huoshan');self.assertTrue(status['configured']);self.assertFalse(status['verified'])
            self.assertNotIn('apiKey',status);self.assertNotIn('protectedKey',status)
            self.assertEqual(settings.credentials()[1],'https://ark.cn-beijing.volces.com/api/plan/v3/chat/completions')
        path.write_text(text.replace('https://ark.cn-beijing.volces.com/api/plan/v3','https://example.com'),encoding='utf-8')
        self.assertEqual(existing_provider(home),{})
    def test_dpapi_config_round_trip_no_plaintext_or_unsafe_endpoint(self):
        settings=ProviderSettings(self.root/'state');key='sk-fixture-'+('b'*32)
        with patch.dict('os.environ',{'DSH_HOME':str(self.root/'missing')},clear=True):
            result=settings.configure({'provider':'deepseek','model':'deepseek-chat','apiKey':key})
            self.assertTrue(result['keyStored']);self.assertNotIn(key,json.dumps(result));self.assertNotIn(key,json.dumps(load_document(settings.path,{})))
            self.assertEqual(settings.credentials()[3],key)
            result=settings.configure({'provider':'huoshan','model':'deepseek-v4.1-flash'})
            self.assertFalse(result['keyStored'])
            with self.assertRaises(ServiceError):settings.credentials()
            with self.assertRaises(ServiceError):settings.configure({'baseUrl':'https://example.com','apiKey':key})
            self.assertNotIn(key,json.dumps(load_document(settings.path,{})))
    def test_math_code_numbers_urls_and_samples_protected_round_trip(self):
        source='# Problem\n\nGiven $n \\le 10^5$ and $$x^2$$, print the integer 42.\n\nExample https://atcoder.jp/contests/abc478\n\n```text\n1 2\n```\n'
        shielded,tokens=protect(source);translated=shielded.replace('Given','给定').replace('print the integer','输出整数')
        restored=restore(translated,tokens)
        for fragment in ('$n \\le 10^5$','$$x^2$$','42','https://atcoder.jp/contests/abc478','```text\n1 2\n```'):self.assertIn(fragment,restored)
        with self.assertRaises(ServiceError):restore(translated.replace(next(iter(tokens)),''),tokens)
        with self.assertRaises(ServiceError):restore(shielded,tokens)
    def test_only_public_statement_cached_by_source_hash_not_own_drafts(self):
        class Assets:
            lock=threading.RLock()
            text='Given the integer $n$, find the answer and print it.\n```text\n1\n```\n'
            def _cached(self,identity):return {'id':identity,'markdown':self.text,'url':'https://atcoder.jp/contests/abc478/tasks/abc478_d','statementAvailable':True,'draft':'USER_SECRET','submissions':[{'code':'PRIVATE_CODE'}]}
        class Provider:
            name='real-format fixture'
            calls=[]
            def __call__(self,text):self.calls.append(text);return text.replace('Given the integer','给定整数').replace('find the answer and print it.','求出答案并输出。')
        asset=Assets();provider=Provider();service=TranslationService(asset,self.root,provider)
        first=service.translate('ABC 478::D');self.assertFalse(first['cached']);self.assertTrue(service.translate('ABC 478::D')['cached']);self.assertEqual(len(provider.calls),1)
        self.assertNotIn('USER_SECRET',provider.calls[0]);self.assertNotIn('PRIVATE_CODE',provider.calls[0]);self.assertNotIn('$n$',provider.calls[0])
        asset.text+='Another public sentence.';self.assertFalse(service.translate('ABC 478::D')['cached']);self.assertEqual(len(provider.calls),2)
    def test_local_key_never_persisted_and_unknown_credentials_rejected(self):
        home=self.root/'dsh';home.mkdir();key='sk-'+('a'*32);(home/'.credentials.yaml').write_text('refs:\n  DEEPSEEK_API_KEY: '+key+'\nrecords:\n',encoding='utf-8')
        with patch.dict('os.environ',{},clear=True):self.assertEqual(_local_key(home),key)
        def transport(payload,secret):
            self.assertEqual(secret,key);self.assertEqual(payload['model'],'deepseek-flash');self.assertEqual(payload['thinking'],{'type':'disabled'});return {'choices':[{'finish_reason':'stop','message':{'content':'给定一个整数。'}}]}
        with patch.dict('os.environ',{},clear=True):self.assertEqual(DeepSeekProvider(home,transport)('Public statement'),'给定一个整数。')
        (home/'.credentials.yaml').write_text('refs:\n  DEEPSEEK_API_KEY: encrypted-reference\n',encoding='utf-8')
        with patch.dict('os.environ',{},clear=True),self.assertRaises(ServiceError):_local_key(home)
    def test_failed_marker_validation_never_creates_cache(self):
        class Assets:
            lock=threading.RLock()
            def _cached(self,identity):return {'markdown':'Given an integer $n$, please print the correct answer.','url':'https://codeforces.com/contest/1/problem/A','statementAvailable':True}
        class Bad:
            name='corrupt fixture'
            def __call__(self,text):return '给定一个整数，输出答案。'
        with self.assertRaises(ServiceError):TranslationService(Assets(),self.root,Bad()).translate('fixture')
        self.assertFalse((self.root/'translations').exists())

if __name__=='__main__':unittest.main(verbosity=2)
