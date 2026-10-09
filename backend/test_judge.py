"""Real isolated compiler/Job tests plus read-only reviewed-profile validation."""
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
import assets
import re
import hashlib
from library import LibraryDatabase
from paths import LIBRARY_SEED
import backend
import judge
import reviewed_cases

class FixtureAssets:
    def __init__(self,scope='samples',time_ms=600,memory_mb=128,checker=None):
        self.data={'scope':scope,'cases':[{'name':'加法','input':'2 3\n','output':'5\n'}],
                   'limits':{'timeMs':time_ms,'memoryMb':memory_mb},'checker':checker}
    def bundle(self,identity):return self.data

@unittest.skipUnless(os.name=='nt','Windows Job implementation')
class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='tb-judge-test-')
        self.directory=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def execute(self,source,fixture=None,**kwargs):
        engine=judge.Judge(fixture or FixtureAssets(),self.directory)
        value=engine.execute('fixture',source,**kwargs)
        self.assertEqual(list(self.directory.iterdir()),[],'All submission files must be cleaned')
        return value
    def test_samples_never_claim_ac_and_run_never_claims_ac(self):
        code='#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b;}'
        self.assertEqual(self.execute(code)['verdict'],'SAMPLE_PASS')
        self.assertEqual(self.execute(code,FixtureAssets('local'))['verdict'],'AC')
        value=self.execute(code,FixtureAssets('local'),mode='run',input_text='8 9')
        self.assertEqual(value['verdict'],'RUN_OK');self.assertEqual(value['output'],'17')
    def test_wrong_answer_compile_error_runtime_error(self):
        self.assertEqual(self.execute('#include <iostream>\nint main(){std::cout<<9;}')['verdict'],'WA')
        value=self.execute('this is not C++');self.assertEqual(value['verdict'],'CE');self.assertTrue(value['stderr'])
        self.assertEqual(self.execute('int main(){return 7;}')['verdict'],'RE')
    def test_cpu_limit_cancellation_and_output_limit(self):
        value=self.execute('int main(){volatile unsigned long long x=0;for(;;)++x;}',FixtureAssets(time_ms=150))
        self.assertEqual(value['verdict'],'TLE',value)
        event=threading.Event();event.set()
        self.assertEqual(self.execute('int main(){}',cancel=event)['verdict'],'ERROR')
        value=self.execute('#include <cstdio>\nint main(){char s[8192];for(auto &c:s)c=65;for(;;)fwrite(s,1,sizeof(s),stdout);}',FixtureAssets(time_ms=4000))
        self.assertEqual(value['verdict'],'OLE',value)
        self.assertLessEqual(len(value['output']),65536)
    def test_memory_limit_has_job_evidence(self):
        value=self.execute('#include <cstdlib>\nint main(){volatile char *p=(char*)malloc(128*1024*1024);if(!p)return 12;for(int i=0;i<128*1024*1024;i+=4096)p[i]=1;}',FixtureAssets(memory_mb=16))
        self.assertEqual(value['verdict'],'MLE',value)
        self.assertIsNotNone(value['memoryKb'])
    def test_nonunique_without_checker_is_not_false_wa(self):
        fixture=FixtureAssets();fixture.data['nonunique']=True
        value=self.execute('#include <iostream>\nint main(){std::cout<<6;}',fixture)
        self.assertEqual(value['verdict'],'ERROR')
    def test_checker_accepts_alternate_valid_output(self):
        fixture=FixtureAssets('local',checker=lambda inp,out,expected:out.strip() in ('5','05'))
        self.assertEqual(self.execute('#include <iostream>\nint main(){std::cout<<"05";}',fixture)['verdict'],'AC')

class ProfileTests(unittest.TestCase):
    def test_constraint_checker_rejects_invalid_and_accepts_alternate(self):
        checker=reviewed_cases.inequality_checker
        inp='3 2\n1 1 2\n0 2 3\n'
        self.assertTrue(checker(inp,'Yes\n1 3 3','Yes'))
        self.assertFalse(checker(inp,'Yes\n3 1 1','Yes'))
        self.assertFalse(checker(inp,'No','Yes'))
        self.assertFalse(checker(inp,'Yes\n1 2 4','Yes'))
        self.assertTrue(checker('1 1\n1 1 1','No','No'))
    def test_actual_profiles_have_usable_assets_and_independent_cases(self):
        before=hashlib.sha256(LIBRARY_SEED.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix='tb-profile-assets-') as root:
            store=backend.Store(library_file=Path(root)/'library.sqlite3');library=assets.AssetLibrary(store)
            for identity in reviewed_cases.PROFILES:
                with self.subTest(identity=identity):
                    value=library.problem(identity);bundle=library.bundle(identity)
                    self.assertTrue(value['statementAvailable']);self.assertTrue(value['samples'])
                    self.assertEqual(bundle['scope'],'local');self.assertGreater(len(bundle['cases']),len(value['samples']))
                    self.assertNotIn('参考代码',value['markdown'])
        self.assertEqual(before,hashlib.sha256(LIBRARY_SEED.read_bytes()).hexdigest())
    @unittest.skipUnless(os.name=='nt','Windows C++ integration')
    def test_all_reviewed_profiles_against_read_only_archived_reference(self):
        before=hashlib.sha256(LIBRARY_SEED.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix='tb-profile-proof-') as work:
            store=backend.Store(library_file=Path(work)/'library.sqlite3');library=assets.AssetLibrary(store)
            engine=judge.Judge(library,Path(work)/'compiler')
            for identity in reviewed_cases.PROFILES:
                with self.subTest(identity=identity):
                    markdown=store.solution(identity)['markdown']
                    sources=[code for code in re.findall(r'```(?:cpp|c\+\+)\s*\n(.*?)```',markdown,re.S) if re.search(r'\bmain\s*\(',code)]
                    self.assertTrue(sources,identity)
                    value=engine.execute(identity,sources[-1])
                    print(identity,value['verdict'],value['passed'],value['total'],value['timeMs'],value['memoryKb'],flush=True)
                    self.assertEqual(value['verdict'],'AC',value)
            self.assertEqual(list((Path(work)/'compiler').iterdir()),[])
        self.assertEqual(before,hashlib.sha256(LIBRARY_SEED.read_bytes()).hexdigest())

class AssetSafetyTests(unittest.TestCase):
    def test_ast_samples_never_execute_archive_python(self):
        with tempfile.TemporaryDirectory(prefix='tb-asset-ast-') as temporary:
            root=Path(temporary);work=root/'题解'/'AtCoder'/'ABC'/'1'/'_work'
            (work/'题面').mkdir(parents=True)
            (work/'题面'/'A.txt').write_text('Original complete statement',encoding='utf-8')
            (work/'samples.py').write_text("SAMPLES=[('A sample 1','1\\n','2\\n'),('B sample 1','3','4')]\nraise RuntimeError('MUST NOT EXECUTE')\n",encoding='utf-8')
            row={'场次':'ABC 1','题号':'A','题名':'fixture','知识点':'枚举'}
            store=type('Store',(),{'data_root':str(root),'row':lambda s,i:row})()
            from archive_assets import LegacyAssetLibrary
            problem=LegacyAssetLibrary(store)._cached('ABC 1::A')
            self.assertEqual(problem['samples'],[{'name':'A sample 1','input':'1\n','output':'2\n'}])
            self.assertTrue(problem['statementAvailable'])
    @unittest.skipUnless(os.name=='nt','Windows Job lifecycle')
    def test_job_close_terminates_descendants_and_runtime_cancellation(self):
        source=r'''#include <windows.h>
#include <fstream>
int main(int argc,char**argv){
 if(argc>1){Sleep(800);std::ofstream("escaped.txt")<<"escaped";return 0;}
 wchar_t exe[32768];GetModuleFileNameW(NULL,exe,32768);
 std::wstring cmd=std::wstring(L"\"")+exe+L"\" child";
 STARTUPINFOW s={};s.cb=sizeof(s);PROCESS_INFORMATION p={};
 if(!CreateProcessW(exe,&cmd[0],NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,NULL,&s,&p))return 8;
 CloseHandle(p.hThread);CloseHandle(p.hProcess);return 0;
}'''
        with tempfile.TemporaryDirectory(prefix='tb-job-tree-') as temporary:
            root=Path(temporary);cpp=root/'tree.cpp';exe=root/'tree.exe';cpp.write_text(source,encoding='utf-8')
            subprocess.run([judge.shutil.which('g++'),'-std=c++17',str(cpp),'-o',str(exe)],check=True,capture_output=True,timeout=30)
            result=judge._run([exe],'',root,2000,128,max_processes=4)
            self.assertIsNone(result['verdict'],result)
            time.sleep(1)
            self.assertFalse((root/'escaped.txt').exists(),'Child must die when runner closes Job')
            # Runtime cancellation happens after the process actually starts.
            cpp.write_text('int main(){volatile int i=0;for(;;)++i;}',encoding='utf-8')
            subprocess.run([judge.shutil.which('g++'),str(cpp),'-o',str(exe)],check=True,capture_output=True,timeout=30)
            event=threading.Event();timer=threading.Timer(.1,event.set);timer.start()
            try:self.assertEqual(judge._run([exe],'',root,2000,128,cancel=event)['verdict'],'ERROR')
            finally:timer.cancel()

class AdditionalReviewTests(unittest.TestCase):
    def test_candidate_scan_uses_scoped_snapshot_and_never_fetches(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='tb-candidate-snapshot-') as temporary:
            root=Path(temporary);work=root/'题解'/'AtCoder'/'ABC'/'1'/'_work'
            (work/'题面').mkdir(parents=True)
            (work/'题面'/'A.txt').write_text('Original statement',encoding='utf-8')
            (work/'samples.py').write_text("SAMPLES=[('A sample 1','1','2')]",encoding='utf-8')
            row={'场次':'ABC 1','题号':'A','题名':'fixture','知识点':'枚举'}
            class Store:
                data_root=str(root)
                scans=0
                def raw_rows(self):self.scans+=1;return [row]
                def row(self,identity):raise AssertionError('Repeated table lookup')
            store=Store();store.library=LibraryDatabase(root/'library.sqlite3')
            store.library.save_statement('ABC 1::A',{'markdown':'Original statement','samples':[{'name':'Sample','input':'1','output':'2'}]})
            library=assets.AssetLibrary(store)
            with patch.object(assets,'urlopen',side_effect=AssertionError('Preview must not fetch')):
                result=library.candidates([{'id':'ABC 1::A'}])
            self.assertEqual(result,[{'id':'ABC 1::A','judgeScope':'samples'}])
            self.assertEqual(store.scans,1);self.assertIsNone(library._candidate_rows)
    def test_gcd_checker_rejects_nonoptimal_and_accepts_alternatives(self):
        self.assertTrue(reviewed_cases.gcd_checker('2\n2 8\n6 10','4 4\n10 6',''))
        self.assertFalse(reviewed_cases.gcd_checker('1\n2 8','2 8',''))
        self.assertFalse(reviewed_cases.gcd_checker('1\n2 8','4 5',''))
        self.assertFalse(reviewed_cases.gcd_checker('1\n2 8','0 0',''))
    def test_personal_official_fetch_cache_does_not_modify_archive(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='tb-fetch-isolation-') as temporary:
            root=Path(temporary);directory=root/'data'/'题解'/'牛客'/'周赛'/'1'
            directory.mkdir(parents=True)
            solution=directory/'1题解.md';original='# 周赛 1 题解\n> https://ac.nowcoder.com/acm/contest/123/A\n'
            solution.write_text(original,encoding='utf-8')
            row={'场次':'周赛 1','题号':'A','题名':'fixture','知识点':'枚举'}
            store=type('Store',(),{'data_root':str(root/'data'),'row':lambda s,i:row})()
            store.library=LibraryDatabase(root/'personal'/'library.sqlite3')
            store._archive_info=lambda row:(False,'https://ac.nowcoder.com/acm/contest/123/A')
            library=assets.AssetLibrary(store,root/'personal')
            html=b'<div>\xe9\xa2\x98\xe7\x9b\xae\xe6\x8f\x8f\xe8\xbf\xb0</div><div>input description</div><div class="question-oi"><textarea data-clipboard-text-id="input1">1</textarea><textarea data-clipboard-text-id="output1">2</textarea></div>'
            class Response:
                url='https://ac.nowcoder.com/acm/contest/123/A'
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def read(self,size):return html
            with patch.object(assets,'urlopen',return_value=Response()) as network:
                first=library.problem('周赛 1::A');second=library.problem('周赛 1::A')
                self.assertEqual(network.call_count,1)
            self.assertTrue(first['statementAvailable']);self.assertEqual(first['samples'][0]['output'],'2')
            self.assertEqual(first['judge']['scope'],'samples');self.assertEqual(second['judge'],first['judge'])
            self.assertEqual(solution.read_text(encoding='utf-8'),original)
            self.assertEqual(list(directory.iterdir()),[solution]);self.assertEqual(len(list((root/'personal').glob('*.json'))),0)
            self.assertTrue(store.library.statement('周赛 1::A')['statementAvailable'])
    @unittest.skipUnless(os.name=='nt','C++ case-insensitive sample comparison')
    def test_declared_case_insensitive_output(self):
        with tempfile.TemporaryDirectory(prefix='tb-case-policy-') as temporary:
            fixture=FixtureAssets();fixture.data['caseInsensitive']=True;fixture.data['cases'][0]['output']='YES'
            value=judge.Judge(fixture,temporary).execute('fixture','#include <iostream>\nint main(){std::cout<<"yes";}')
            self.assertEqual(value['verdict'],'SAMPLE_PASS',value)

if __name__=='__main__':unittest.main(verbosity=2)
