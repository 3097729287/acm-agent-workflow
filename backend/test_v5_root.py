"""Compiler/version, real custom API transport, and public metadata regressions."""
import datetime as dt
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from persistence import load_document
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
import sys
_test_common = Path(__file__).resolve().parent / "common"
sys.path.insert(0,str(_test_common if _test_common.is_dir() else Path(__file__).resolve().parent.parent))
import integrations as I
import public_platforms as P
from official_bridge import page_script
from translation import DeepSeekProvider, TranslationService
from translation_config import ProviderSettings, normalize_base_url
from training import ServiceError


class CompilerVersions(unittest.TestCase):
    def candidate(self, label, code='int main(){}'):
        source=(Path(__file__).parent.parent/'desktop'/'official_languages.js').read_text(encoding='utf-8')
        result=subprocess.run([shutil.which('node'),'-e',source+'\nprocess.stdout.write(JSON.stringify(compilerCandidate('+json.dumps(label)+','+json.dumps(code)+')));'],
                              check=True,capture_output=True,text=True,encoding='utf-8',timeout=5)
        return json.loads(result.stdout)
    def test_current_oj_standard_and_compiler_labels(self):
        for label in ['GNU G++17 7.3.0','C++ 17 (gcc 12.2)','GNU G++20 13.2 (64 bit)','C++(g++ 13)','C++ (g++14)','GNU G++23 14.2']:
            with self.subTest(label=label):self.assertIsNotNone(self.candidate(label))
        for label in ['Java 21','C11','C++14','GNU G++11 5.1','C++ (gcc 7.3)']:
            with self.subTest(label=label):self.assertIsNone(self.candidate(label))
    def test_newer_language_features_need_matching_standard(self):
        source='#include <ranges>\nint main(){auto x=std::ranges::views::iota(1,4);}'
        self.assertIsNone(self.candidate('GNU G++17',source));self.assertIsNotNone(self.candidate('GNU G++20',source))
        source='#include <print>\nint main(){std::print("hi");}'
        self.assertIsNone(self.candidate('GNU G++20',source));self.assertIsNotNone(self.candidate('GNU G++23',source))
    def test_arbitrary_code_template_markers_remain_literal(self):
        source='// CONTEXT ACTION COMPILER_SELECTION\nint main(){}'
        generated=page_script({'code':source,'sessionId':'fixture'},'submit')
        self.assertIn(json.dumps(source),generated)


class CustomAPI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='tb-custom-api-');self.root=Path(self.temp.name)
        self.env=patch.dict('os.environ',{'DSH_HOME':str(self.root/'absent')},clear=True);self.env.start()
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_endpoint_key_isolation_and_normalization(self):
        settings=ProviderSettings(self.root)
        state=settings.configure({'provider':'custom','baseUrl':'https://example.com/v1/chat/completions/','model':'provider/model:latest','apiKey':'fixture+key/123='})
        self.assertEqual(state['baseUrl'],'https://example.com/v1');self.assertTrue(state['configured'])
        self.assertEqual(settings.credentials()[1],'https://example.com/v1/chat/completions')
        self.assertNotIn('fixture+key/123=',json.dumps(load_document(settings.path,{})))
        self.assertNotIn('protectedKey',state)
        self.assertTrue(settings.configure({'model':'another-model'})['keyStored'])
        self.assertFalse(settings.configure({'baseUrl':'https://another.example/v1'})['keyStored'])
        self.assertEqual(settings.credentials()[3],'', 'A custom endpoint can intentionally use anonymous auth')
        for url in ['ftp://example.com','https://user:password@example.com/v1','https://example.com/v1?key=x','http://example.com/x\nY']:
            with self.subTest(url=url),self.assertRaises(ServiceError):normalize_base_url(url)
        self.assertEqual(normalize_base_url('http://127.0.0.1:8788/v1/'),'http://127.0.0.1:8788/v1')
    def test_actual_http_translation_uses_user_base_and_model(self):
        observed=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                observed.append((self.path,payload,self.headers.get('Authorization')))
                result=payload['messages'][1]['content'].replace('Given the integer','给定整数').replace('find the answer and print it.','求出答案并输出。')
                raw=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':result}}]}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        class Assets:
            lock=threading.RLock()
            def _cached(self,identity):return {'id':identity,'markdown':'Given the integer $n$, find the answer and print it.\n```text\n1\n```','url':'https://atcoder.jp/contests/abc478/tasks/abc478_d','statementAvailable':True,'draft':'PRIVATE-DRAFT'}
        try:
            service=TranslationService(Assets(),self.root)
            service.configure({'provider':'custom','baseUrl':f'http://127.0.0.1:{server.server_port}/v1','model':'my-local-model','apiKey':'fixture-http-key'})
            result=service.translate('p');self.assertIn('给定整数 $n$',result['markdown']);self.assertTrue(service.status()['verified'])
            self.assertEqual(observed[0][0],'/v1/chat/completions');self.assertEqual(observed[0][1]['model'],'my-local-model')
            self.assertEqual(observed[0][2],'Bearer fixture-http-key');self.assertNotIn('PRIVATE-DRAFT',json.dumps(observed))
            self.assertTrue(service.translate('p')['cached']);self.assertEqual(len(observed),1)
        finally:server.shutdown();server.server_close();thread.join(2)


class LatestMetadata(unittest.TestCase):
    def test_old_archived_cf_rating_refreshes_by_exact_problem_url(self):
        class Store:
            data_root='unused'
            def raw_rows(self):return [{'场次':'Div.2 1123','题号':'E'}]
            def encode_row(self,*args):return {'url':'https://codeforces.com/problemset/problem/1/E'}
        class Client:
            def json(self,url,headers=None):return {'status':'OK','result':{'problems':[{'contestId':1,'index':'E','rating':2100,'tags':['dp']}]}}
        with tempfile.TemporaryDirectory() as root:
            service=I.IntegrationService(Store(),root,auto_start=False,client=Client())
            try:
                service._refresh_difficulties('codeforces')
                result=service.problem_metadata({},'https://codeforces.com/contest/1/problem/E')
                self.assertEqual(result['difficulty'],2100);self.assertEqual(result['difficultyConfidence'],'HIGH')
                self.assertFalse(result['difficultyEstimated']);self.assertIn('官方',result['difficultySource'])
                service._save()
            finally:service.close()
    def test_atcoder_public_counts_preserve_official_rating_scale(self):
        prefix='https://atcoder.jp/users/fixture'
        class Client:
            def json(self,url,headers=None):
                if url==prefix+'/history/json':return [{'IsRated':True,'NewRating':98,'EndTime':'2026-10-08T21:00:00+09:00'}]
                if '/ac_rank?' in url:return {'count':2,'rank':100}
                if '/submissions?' in url:return [{'id':1,'user_id':'fixture','epoch_second':100,'contest_id':'abc1','problem_id':'abc1_a','result':'AC'},{'id':2,'user_id':'fixture','epoch_second':200,'contest_id':'abc1','problem_id':'abc1_a','result':'AC'}]
                raise RuntimeError('unexpected fixture')
            def text(self,*args):return '<a href="/users/fixture">fixture</a>'
        result=P.account_at(Client(),'fixture')
        self.assertEqual(result['rating'],98);self.assertEqual(result['solvedCount'],2)
        self.assertEqual(result['submissionCount'],2);self.assertEqual(len(result['solved']),1)
        self.assertIn('AtCoder Problems',result['statisticsSource'])


if __name__=='__main__':unittest.main()
