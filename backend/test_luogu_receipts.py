"""Luogu login and confirmed request receipts, with no live account or network."""
import json
from pathlib import Path
import subprocess
import unittest
from test_official_v4 import NODE
from official_bridge import page_script, submission_target

SCRIPT = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const observer=fs.readFileSync(process.argv[1],'utf8'),messages=[],requests=[];
const location=new URL('https://www.luogu.com.cn/problem/P1063');
const ctx={sessionId:'fixture',platform:'洛谷',originalUrl:location.href,code:'int main(){}'};
const document={querySelector:()=>({textContent:JSON.stringify({user:{uid:12345}})})};
let responses=[];
const window={fetch:async(url,options)=>{requests.push({url,method:options?.method||'GET'});const value=responses.shift();return {ok:true,url:new URL(url,location).href,json:async()=>value,clone(){return {json:async()=>value}}}}};
const box={window,document,location,URL,URLSearchParams,Promise,AbortSignal,chrome:{webview:{postMessage(value){messages.push(JSON.parse(value))}}}};
vm.runInNewContext(observer+';window.state=installLuoguReceipts('+JSON.stringify(ctx)+');',box);window.state.armed=true;
async function request(url,body,response){responses.push(response);await window.fetch(url,{method:'POST',body:JSON.stringify(body)});await new Promise(r=>setImmediate(r));}
(async()=>{
 for(const [url,body] of [['/fe/api/problem/submit/P1064',{code:ctx.code}],['/api/ide_submit',{code:ctx.code}],['/fe/api/problem/submit/P1063',{code:'other'}],['https://evil.test/fe/api/problem/submit/P1063',{code:ctx.code}],['/fe/api/problem/submit/P1063?contestId=1',{code:ctx.code}]])await request(url,body,201);
 assert.equal(messages.length,0);
 await request('/fe/api/problem/submit/P1063',{code:ctx.code,lang:12},201);
 assert.equal(messages.at(-1).submissionId,'201');assert.equal(messages.at(-1).status,'judging');
 const record=(status,changes={})=>({data:{record:{id:201,problem:{pid:'P1063'},user:{uid:12345},status,...changes}}});
 for(const payload of [record(12,{id:200}),record(12,{problem:{pid:'P1064'}}),record(12,{user:{uid:999}}),record(1)]){responses.push(payload);await window.state.poll();}
 assert.equal(messages.length,1,'old IDs, other problems/accounts and pending cannot be AC');
 responses.push(record(12));await window.state.poll();assert.equal(messages.at(-1).verdict,'AC');
 assert.ok(requests.filter(r=>r.method==='GET').every(r=>r.url==='/record/201'));
 window.state.armed=true;
 await request('/fe/api/problem/submit/P1063',{code:ctx.code},202);
 responses.push({data:{record:{id:202,problem:{pid:'P1063'},user:{uid:12345},status:5}}});await window.state.poll();assert.equal(messages.at(-1).verdict,'TLE');
 console.log(JSON.stringify({ok:true,confirmedIdAndOwner:true,hostPolling:true}));
})().catch(e=>{console.error(e);process.exitCode=1});
'''


class LuoguReceiptTests(unittest.TestCase):
    def test_original_submit_and_record_correlation(self):
        result = subprocess.run([NODE, '-e', SCRIPT, str(Path(__file__).parents[1]/'desktop/official_luogu.js')],
                                capture_output=True, text=True, encoding='utf-8', timeout=15, check=True)
        self.assertTrue(json.loads(result.stdout)['ok'])

    def test_columba_logged_out_problem_reports_login_before_editor_is_loaded(self):
        session = dict(submission_target('https://www.luogu.com.cn/problem/P1063'),
                       sessionId='fixture',code='int main(){}',attempted=False)
        script = r'''
const vm=require('node:vm'),fs=require('node:fs');const payload=JSON.parse(fs.readFileSync(0,'utf8'));
const location=new URL('https://www.luogu.com.cn/problem/P1063#submit');
const window={};window.top=window;
const document={title:'P1063',body:{innerText:''},querySelector:selector=>selector==='#lentille-context'?{textContent:JSON.stringify({template:'problem.show',user:null})}:null,querySelectorAll:()=>[]};
process.stdout.write(JSON.stringify(vm.runInNewContext(payload.script,{window,document,location,URL,URLSearchParams,chrome:{webview:{postMessage(){}}}})));
'''
        result = subprocess.run([NODE,'-e',script],input=json.dumps({'script':page_script(session)}),
                                capture_output=True,text=True,encoding='utf-8',timeout=10,check=True)
        self.assertEqual(json.loads(result.stdout)['status'],'needs_login')
        self.assertEqual(session['loginUrl'],'https://www.luogu.com.cn/auth/login')


if __name__ == '__main__': unittest.main()
