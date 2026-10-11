"""Production observer with intercepted requests; no real account submissions."""
import json
from pathlib import Path
import subprocess
import unittest
from test_official_v4 import NODE

SCRIPT = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const observer=fs.readFileSync(process.argv[1],'utf8');
const messages=[],location=new URL('https://ac.nowcoder.com/acm/contest/127263/B');
const ctx={sessionId:'fixture',platform:'牛客',originalUrl:location.href,code:'int main(){}'};
let responses=[];
const window={pageInfo:{contestId:'127263',questionId:'11604979'},globalInfo:{ownerId:12345},fetch:async(url)=>{
 const value=responses.shift();return {ok:true,url:new URL(url,location).href,clone(){return {json:async()=>value}}};
}};
const box={window,location,URL,URLSearchParams,Promise,chrome:{webview:{postMessage(value){messages.push(JSON.parse(value))}}},normal:text=>({'答案错误':'WA','运行超时':'TLE','AC':'AC'}[text]||null)};
vm.runInNewContext(observer+';window.state=installNowcoderReceipts('+JSON.stringify(ctx)+');',box);
window.state.armed=true;
async function request(url,body,response){responses.push(response);await window.fetch(url,{method:body?'POST':'GET',...(body?{body:JSON.stringify(body)}:{})});await new Promise(r=>setImmediate(r));}
const body={questionId:'11604979',content:ctx.code,submitType:1,userId:12345,appId:1,tagId:1};
(async()=>{
 // Old result, another task/code/account and self-test never become acceptance.
 await request('/status?submissionId=12',null,{code:0,data:{status:5}});
 for(const changed of [{questionId:'other'},{content:'other code'},{submitType:2},{userId:999},{selfInputData:'1'}]){
  await request('/api/service/judge/submit',{...body,...changed},{code:0,data:{id:12}});
 }
 assert.equal(messages.length,0);
 await request('/api/service/judge/submit',body,{code:0,data:{id:21}});
 assert.equal(messages.at(-1).status,'judging');
 const query='/api/service/judge/submit-status?id=21&submitType=1&userId=12345&appId=1&tagId=1';
 for(const url of [query.replace('id=21','id=20'),query.replace('submitType=1','submitType=2'),query.replace('userId=12345','userId=999')])await request(url,null,{code:0,data:{status:5}});
 await request(query,null,{code:0,data:{status:1,desc:'AC'}});
 assert.equal(messages.length,1);
 await request(query,null,{code:0,data:{status:4,desc:'答案错误',memo:'答案正确 AC'}});
 assert.equal(messages.at(-1).verdict,'WA');
 await request(query,null,{code:0,data:{status:5}});
 assert.equal(messages.at(-1).verdict,'AC');assert.equal(messages.at(-1).submissionId,'21');
 window.state.pending=null;
 await request('/submit_cd',{questionId:'11604979',content:ctx.code},{code:0,data:22});
 await request('/status?submissionId=22',null,{code:0,data:{status:5}});
 assert.equal(messages.at(-1).submissionId,'22');
 console.log(JSON.stringify({ok:true,legacy:true,modern:true,rejectedOldOtherTaskCodeOwnerAndSelfTest:true}));
})().catch(e=>{console.error(e);process.exitCode=1});
'''


class NowcoderReceiptTests(unittest.TestCase):
    def test_original_request_and_status_correlation(self):
        result = subprocess.run([NODE, '-e', SCRIPT, str(Path(__file__).parents[1]/'desktop/official_nowcoder.js')],
                                capture_output=True, text=True, encoding='utf-8', timeout=15, check=True)
        self.assertTrue(json.loads(result.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
