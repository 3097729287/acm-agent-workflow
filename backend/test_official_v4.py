"""Execute the production receipt inspector against isolated official DOM models."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

# `desktop/` 与 `backend/common/` 不在 `-s backend` discover 的 sys.path 上；
# 本测试直接 import 生产代码，显式补路径，保证单文件与整套都能收集。
_ROOT = Path(__file__).resolve().parent.parent
for _extra in (_ROOT / "desktop", _ROOT / "backend" / "common"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

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
    def api_inspect(self, records, **overrides):
        session={'sessionId':'fixture','platform':'Codeforces','problem':'A','code':'int main(){}',
                 'originalUrl':'https://codeforces.com/problemset/problem/123/A','attempted':True,
                 'baseline':['100','110'],'baselineKnown':True,'baselineOwner':'owner',**overrides}
        script=INSPECT.replace('process.stdout.write(JSON.stringify(result));',r'''
setTimeout(()=>process.stdout.write(JSON.stringify(messages)),10);
''').replace("chrome:{webview:{postMessage(){}}}","AbortSignal,fetch:async()=>({ok:true,url:'https://codeforces.com/api/user.status',json:async()=>({status:'OK',result:payload.records})}),chrome:{webview:{postMessage(value){messages.push(JSON.parse(value))}}}")
        script=script.replace('const result=vm.runInNewContext','const messages=[];const result=vm.runInNewContext')
        output=subprocess.run([NODE,'-e',script],input=json.dumps({'script':page_script(session),'rows':[],'records':records}),
                              text=True,encoding='utf-8',capture_output=True,check=True,timeout=10)
        return json.loads(output.stdout)

    def test_cf_api_receipt_matches_current_owner_task_and_newer_than_entire_baseline(self):
        record=lambda identity,owner='owner',index='A',verdict='OK':{'id':identity,'problem':{'contestId':123,'index':index},'author':{'members':[{'handle':owner}]},'verdict':verdict}
        values=self.api_inspect([record(105),record(112,owner='other'),record(113,index='B'),record(114,owner='OWNER')])
        receipt=next(item for item in values if item.get('status')=='finished')
        self.assertEqual((receipt['submissionId'],receipt['verdict']),('114','AC'))
        for overrides in ({'baselineKnown':False},{'baselineOwner':''}):
            self.assertFalse(any(item.get('status')=='finished' for item in self.api_inspect([record(114)],**overrides)))
        self.assertFalse(any(item.get('status')=='finished' for item in self.api_inspect([record(105),record(112,owner='other')])))

    def test_terminal_receipt_callback_survives_hidden_frontend_and_late_pending_status(self):
        saved=[];bridge=OfficialBridge(object(),on_receipt=lambda identity,value:saved.append((identity,value)))
        bridge.sessions['fixture']={'status':'submitted'}
        bridge._update('fixture',{'status':'finished','submissionId':'114','verdict':'AC'})
        bridge._update('fixture',{'status':'submitted'})
        self.assertEqual(bridge.sessions['fixture']['status'],'finished')
        self.assertEqual(len(saved),1);self.assertEqual(saved[0][1]['verdict'],'AC')

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
    def test_real_cf_verdict_spelling_and_test_suffixes(self):
        for label,expected in [('Accepted','AC'),('OK','AC'),('Wrong answer on test 1','WA'),('Time limit exceeded on test 3','TLE'),('Compilation error','CE')]:
            with self.subTest(label=label):
                value=self.inspect([{'id':'101','task':'/contest/123/problem/A','verdict':label}])
                self.assertEqual((value['status'],value['verdict']),('finished',expected))
    def test_record_outside_bounded_baseline_but_older_than_maximum_never_ac(self):
        value=self.inspect([{'id':'50','task':'/contest/123/problem/A','verdict':'Accepted'}],baseline=('100',))
        self.assertEqual(value['status'],'submitted')

if __name__=='__main__':unittest.main()
