"""Execute the production receipt inspector against isolated official DOM models."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from official_bridge import OfficialBridge,page_script

NODE=shutil.which('node') or 'D:/Software/Other/nodejs/node-v24.18.1-win-x64/node.exe'
INSPECT=r'''
const fs=require('node:fs'),vm=require('node:vm');
const payload=JSON.parse(fs.readFileSync(0,'utf8'));
const location=new URL('https://codeforces.com/contest/123/my');
const a=href=>({getAttribute:()=>href});
const rows=payload.rows.map(r=>({querySelectorAll(selector){
  if(selector==='a[href]')return [a('/contest/123/submission/'+r.id),a(r.task)];
  return [{getAttribute:()=>null,textContent:r.verdict}];
}}));
const document={title:'My submissions',body:{innerText:''},querySelector:()=>null,
  querySelectorAll:selector=>selector==='tr'?rows:[]};
const result=vm.runInNewContext(payload.script,{URL,location,document,chrome:{webview:{postMessage(){}}}});
process.stdout.write(JSON.stringify(result));
'''

class ReceiptInspectorTests(unittest.TestCase):
    def test_native_closing_callback_has_hashable_return_and_does_not_cancel(self):
        from webview.event import Event
        event=Event(object(),should_lock=True)
        event+=OfficialBridge(object()).on_closing
        with self.assertNoLogs('pywebview',level='ERROR'):
            self.assertFalse(event.set())
    def inspect(self,rows,baseline=('100',),baseline_known=True):
        session={'sessionId':'fixture','platform':'Codeforces','problem':'A','code':'int main(){}',
                 'originalUrl':'https://codeforces.com/problemset/problem/123/A','attempted':True,
                 'baseline':list(baseline),'baselineKnown':baseline_known}
        value=subprocess.run([NODE,'-e',INSPECT],input=json.dumps({'script':page_script(session),'rows':rows}),
                             text=True,encoding='utf-8',capture_output=True,check=True,timeout=10)
        return json.loads(value.stdout)
    def test_same_cf_task_routes_recognize_only_new_receipt(self):
        value=self.inspect([{'id':'100','task':'/contest/123/problem/A','verdict':'Accepted'},
                            {'id':'101','task':'/contest/123/problem/A','verdict':'Wrong Answer'}])
        self.assertEqual((value['status'],value['submissionId'],value['verdict']),('finished','101','WA'))
    def test_old_receipt_unknown_baseline_other_task_and_other_origin_never_ac(self):
        for rows,known in [([{'id':'100','task':'/contest/123/problem/A','verdict':'Accepted'}],True),
                           ([{'id':'101','task':'/contest/123/problem/A','verdict':'Accepted'}],False),
                           ([{'id':'101','task':'/contest/123/problem/B','verdict':'Accepted'}],True),
                           ([{'id':'101','task':'https://example.org/contest/123/problem/A','verdict':'Accepted'}],True)]:
            with self.subTest(rows=rows,known=known):
                self.assertEqual(self.inspect(rows,baseline_known=known)['status'],'submitted')
    def test_real_pending_receipt_is_judging_not_finished(self):
        value=self.inspect([{'id':'101','task':'/contest/123/problem/A','verdict':'Running'}])
        self.assertEqual(value['status'],'judging');self.assertNotIn('verdict',value)

if __name__=='__main__':unittest.main()
