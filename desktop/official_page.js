function tbOfficialPage(ctx, action, postMessage) {
if(typeof window!=='undefined'&&(window!==window.top||!['codeforces.com','www.codeforces.com','atcoder.jp','ac.nowcoder.com','www.luogu.com.cn','luogu.com.cn'].includes(location.hostname)))return null;
COMPILER_SELECTION
NOWCODER_RECEIPTS
LUOGU_RECEIPTS
const send=value=>{postMessage({tbOfficial:true,sessionId:ctx.sessionId,...value});return value;};
const ncReceipt=installNowcoderReceipts(ctx, send);
const lgReceipt=installLuoguReceipts(ctx, send);
const visible=e=>e&&e.getClientRects().length>0;
const editors=()=>[...document.querySelectorAll('textarea')].filter(e=>/source|code|editor/i.test((e.name||'')+' '+(e.id||'')));
const hasEditor=()=>editors().length||document.querySelector('.CodeMirror,.cm-editor,.ace_editor,.monaco-editor');
const login=()=>[...document.querySelectorAll('input[type=password]')].some(visible)||/\/login|\/enter(?:\/|$)|\/auth\/login/i.test(location.pathname);
function luoguLoggedOut(){
if(ctx.platform!=='洛谷')return false;
try{const data=JSON.parse(document.querySelector('#lentille-context')?.textContent||'null');if(data&&Object.prototype.hasOwnProperty.call(data,'user'))return data.user===null;}catch{}
const legacy=window._feInjection;if(legacy&&Object.prototype.hasOwnProperty.call(legacy,'currentUser'))return !legacy.currentUser;
return false;
}
const verification=()=>[...document.querySelectorAll('iframe')].some(e=>visible(e)&&/captcha|challenge/i.test(e.src))||!hasEditor()&&/just a moment|checking your browser|人机验证|安全验证|验证码/i.test(document.title+' '+(document.body?.innerText||'').slice(0,1200));
function normal(text){
text=(text||'').trim().replace(/_/g,' ').replace(/\s+/g,' ');
const map={'AC':'AC','OK':'AC','ACCEPTED':'AC','通过':'AC','WA':'WA','WRONG ANSWER':'WA','答案错误':'WA','TLE':'TLE','TIME LIMIT EXCEEDED':'TLE','超时':'TLE','MLE':'MLE','MEMORY LIMIT EXCEEDED':'MLE','内存超限':'MLE','RE':'RE','RUNTIME ERROR':'RE','运行错误':'RE','CE':'CE','COMPILATION ERROR':'CE','COMPILE ERROR':'CE','编译错误':'CE','OLE':'OLE','OUTPUT LIMIT EXCEEDED':'OLE'};
const exact=map[text.toUpperCase()];if(exact)return exact;
for(const [label,value] of Object.entries(map))if(label.length>3&&new RegExp('^'+label+'(?:\\s+(?:on|in|at)\\b|$)','i').test(text))return value;
return /^(WJ|WR|TESTING|Judging|Running|Waiting|Pending|Queuing|评测中|等待评测)(\b|$)/i.test(text)?'JUDGING':null;
}
function taskPath(path){return path.replace(/^\/problemset\/problem\/(\d+)\/([A-Za-z]\d?)$/,'/contest/$1/problem/$2');}
function receipts(doc=document){const rows=[];doc.querySelectorAll('tr').forEach(row=>{const links=[...row.querySelectorAll('a[href]')];const a=links.find(a=>/\/submission(?:s)?\/\d+/.test(a.getAttribute('href')||''));if(!a)return;const id=(a.getAttribute('href')||'').match(/\/submission(?:s)?\/(\d+)/)?.[1];const task=links.some(a=>{try{const target=new URL(a.getAttribute('href'),location.href),original=new URL(ctx.originalUrl);return target.origin===location.origin&&taskPath(target.pathname)===taskPath(original.pathname)}catch{return false}});const owner=!ctx.baselineOwner||links.some(a=>{try{const link=new URL(a.getAttribute('href'),location.href);return link.origin===location.origin&&link.pathname==='/profile/'+ctx.baselineOwner}catch{return false}});const verdict=[...row.querySelectorAll('.label,.submissionVerdictWrapper,.verdict,[data-verdict],.verdict-accepted,.verdict-rejected,.status-cell')].map(e=>normal(e.getAttribute('data-verdict')||e.getAttribute('verdict')||e.textContent)).find(Boolean);if(id&&task&&owner)rows.push({id,verdict});});return rows;}
function newerReceipt(id,baseline){
if(!/^\d+$/.test(id))return false;
const previous=[...baseline].filter(value=>/^\d+$/.test(value));
return !baseline.has(id)&&previous.every(value=>BigInt(id)>BigInt(value));
}
function cfOwner(doc=document){
return [...doc.querySelectorAll('#header a[href],header a[href],.lang-chooser a[href]')].map(a=>{try{const url=new URL(a.getAttribute('href'),location.href);return url.origin===location.origin&&url.pathname.match(/^\/profile\/([A-Za-z0-9_.-]{1,64})\/?$/)?.[1]}catch{return null}}).find(Boolean)||'';
}
function myPaths(){
const original=new URL(ctx.originalUrl),match=taskPath(original.pathname).match(/^\/(contest|gym)\/(\d+)\/problem\//);
return match?[`/${match[1]}/${match[2]}/my`,...(match[1]==='contest'?['/problemset/my']:[])]:[];
}
async function myPage(path){
const response=await fetch(path,{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});
const final=new URL(response.url||path,location.href);
if(!response.ok||final.origin!==location.origin||!myPaths().includes(final.pathname))return null;
const doc=new DOMParser().parseFromString((await response.text()).slice(0,2000000),'text/html');
if(/just a moment|checking your browser|人机验证|安全验证|验证码/i.test(doc.title+' '+(doc.body?.textContent||'').slice(0,1200))||doc.querySelector('input[type=password],iframe[src*=captcha],iframe[src*=challenge]'))return null;
const table=doc.querySelector('table.status-frame-datatable')||[...doc.querySelectorAll('table')].find(t=>/submission|提交|status|verdict|结果|when/i.test([...t.querySelectorAll('th,tr:first-child td')].map(e=>e.textContent).join(' ')));
return table?doc:null;
}
function receiptValue(receipt){return {status:receipt.verdict==='JUDGING'?'judging':'finished',submissionId:receipt.id,...(receipt.verdict==='JUDGING'?{}:{verdict:receipt.verdict}),message:receipt.verdict==='JUDGING'?'原站已接收，正在评测。':'本次提交结果：'+receipt.verdict};}
function inspect(){
if(login()||luoguLoggedOut()||(ctx.platform==='牛客'&&window.globalInfo?.ownerId!=null&&Number(window.globalInfo.ownerId)<=0))return {status:'needs_login',message:'请在浏览器登录原站，完成后回到 TB 点击提交。'};
if(verification())return {status:'needs_verification',message:'请在浏览器完成原站验证，然后回到 TB 查看状态。'};
if(ncReceipt?.receipt)return ncReceipt.receipt;
if(lgReceipt?.receipt)return lgReceipt.receipt;
if(ctx.attempted&&!ctx.submissionId){
const errors=[...document.querySelectorAll('.el-message--error,.el-notification.error,.ivu-message-error,.ant-message-error')].filter(visible).map(e=>e.textContent.trim()).filter(Boolean);
if(errors.length)return {status:'error',attempted:false,message:'原站未受理代码：'+errors.join('；').slice(0,200)};
}
if(ctx.platform==='Codeforces'&&ctx.attempted&&/\/submit$/.test(location.pathname)){
const errors=[...document.querySelectorAll('span.error,.error-message,.submit-error')].filter(visible).map(e=>e.textContent.trim()).filter(Boolean);
if(errors.length)return {status:'error',attempted:false,message:'Codeforces 未受理代码：'+errors.join('；').slice(0,200)};
}
if(ctx.attempted&&ctx.baselineKnown){const baseline=new Set(ctx.baseline||[]);const receipt=receipts().find(r=>newerReceipt(r.id,baseline)&&(!ctx.submissionId||r.id===ctx.submissionId));if(receipt?.verdict)return receiptValue(receipt);}
return hasEditor()?{status:ctx.attempted?'submitted':'ready',message:ctx.attempted?'已操作原站提交表单，尚未收到受理编号。':'浏览器已就绪，使用当前登录账号提交。'}:{status:ctx.attempted?'submitted':'loading',message:ctx.attempted?'尚未收到原站受理编号，请留意浏览器中的提示。':'正在加载浏览器中的原站提交页。'};
}
async function submit(){
const state=inspect();if(['needs_login','needs_verification'].includes(state.status))return send(state);
if(!hasEditor())return send({status:'error',message:'没有找到原站代码编辑器，请进入本题提交页；不会点击其它表单。'});
let task=!ctx.problem,filled=0;
document.querySelectorAll('select').forEach(s=>{const field=(s.name||s.id||'').toLowerCase();if(/problem|task/.test(field)&&ctx.problem){const o=[...s.options].find(o=>o.value===ctx.problem);if(o){s.value=o.value;s.dispatchEvent(new Event('change',{bubbles:true}));task=true;}}});
if(['牛客','洛谷'].includes(ctx.platform))task=location.pathname===new URL(ctx.originalUrl).pathname;
if(!task)return send({status:'error',message:'未能准确选定本题，已停止；请在原站确认题目。'});
const compiler=await selectOfficialCompiler(ctx.code,ctx.platform);
if(!compiler)return send({status:'error',message:'没有找到支持当前代码的 C++17 / C++20 / C++23 编译器，请在原站确认语言后重试。'});
editors().forEach(e=>{Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,ctx.code);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));filled++;});
document.querySelectorAll('.CodeMirror').forEach(e=>{if(e.CodeMirror){e.CodeMirror.setValue(ctx.code);filled++;}});document.querySelectorAll('.ace_editor').forEach(e=>{try{if(window.ace){window.ace.edit(e).setValue(ctx.code,-1);filled++;}}catch{}});try{window.monaco?.editor?.getModels?.().filter(m=>!m.isDisposed()&&/cpp|c\+\+/.test(m.getLanguageId?.()||'')).forEach(m=>{m.setValue(ctx.code);filled++;});}catch{}
document.querySelectorAll('.cm-editor .cm-content').forEach(e=>{const view=e.cmView?.view;if(view?.state?.doc&&view?.dispatch){view.dispatch({changes:{from:0,to:view.state.doc.length,insert:ctx.code}});filled++;}});
if(!filled)return send({status:'error',message:'编辑器接口不可用，请手动粘贴并提交；未发出自动提交。'});
let baseline=[],baselineKnown=false,baselineOwner='';
if(ctx.platform==='Codeforces'){
baselineOwner=cfOwner();
}
if(ctx.platform==='Codeforces'){
for(const path of myPaths()){try{const doc=await myPage(path);if(!doc)continue;baselineOwner=baselineOwner||cfOwner(doc);baseline=[...doc.querySelectorAll('a[href]')].map(a=>(a.getAttribute('href')||'').match(/\/submission\/(\d+)/)?.[1]).filter(Boolean);baselineKnown=true;break;}catch{}}
}else{
try{let path=null;if(ctx.platform==='AtCoder')path=location.pathname.replace(/\/submit$/,'/submissions/me');if(path){const r=await fetch(path,{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});if(r.ok&&new URL(r.url).origin===location.origin&&new URL(r.url).pathname===path){const html=await r.text();const doc=new DOMParser().parseFromString(html.slice(0,2000000),'text/html');const challenge=/just a moment|checking your browser|人机验证|安全验证|验证码/i.test(doc.title+' '+(doc.body?.textContent||'').slice(0,1200));const table=[...doc.querySelectorAll('table')].some(t=>/submission|提出|提交|status|verdict|結果|时间|when/i.test([...t.querySelectorAll('th, tr:first-child td')].map(e=>e.textContent).join(' ')));if(!challenge&&table&&!doc.querySelector('input[type=password],iframe[src*=captcha],iframe[src*=challenge]')){baseline=receipts(doc).map(r=>r.id);baselineKnown=true;}}}}catch{}
}
// The official public API provides a bounded snapshot when the HTML list is
// unavailable. Only the authenticated page's own handle is used. A global ID
// lower bound prevents older records outside this snapshot from becoming AC.
if(ctx.platform==='Codeforces'&&!baselineKnown&&baselineOwner){
try{const r=await fetch('/api/user.status?handle='+encodeURIComponent(baselineOwner)+'&from=1&count=100',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});if(r.ok){const value=await r.json();if(value.status==='OK'&&Array.isArray(value.result)&&value.result.every(row=>Number.isSafeInteger(row.id)&&row.id>0)){baseline=value.result.map(row=>String(row.id));baselineKnown=true;}}}catch{}
}
if(['Codeforces','AtCoder'].includes(ctx.platform)&&!baselineKnown)return send({status:'error',message:'暂时无法读取本账号的提交记录。请在浏览器完成登录或验证，再重试提交。'});
const form=editors().map(e=>e.closest('form')).find(Boolean)||[...document.querySelectorAll('form')].find(f=>f.querySelector('.CodeMirror,.cm-editor,.ace_editor,.monaco-editor'));
let button=[...(form?.querySelectorAll('button[type=submit],input[type=submit],#submit')||[])].find(b=>visible(b)&&!b.disabled);if(!button&&['牛客','洛谷'].includes(ctx.platform))button=[...document.querySelectorAll('button,[role=button],.btn-submit,.submit-btn,.submit-button')].find(b=>visible(b)&&!b.disabled&&b.getAttribute('aria-disabled')!=='true'&&/^(?:保存并)?提交(?:代码|题目|评测)?$/.test(b.textContent.trim()));
if(!button)return send({status:'error',message:'未找到与代码编辑器对应的官方提交控件，请手动提交；未点击其它按钮。'});
if(ncReceipt){ncReceipt.armed=true;ncReceipt.pending=null;ncReceipt.receipt=null;}
if(lgReceipt){lgReceipt.armed=true;lgReceipt.pending=null;lgReceipt.receipt=null;}
// Persist the pre-submit snapshot before a native form can navigate away.
// Browser transport acknowledges this checkpoint; WebView transport is immediate.
await postMessage({tbOfficial:true,sessionId:ctx.sessionId,status:'submitted',message:'已选择 '+compiler.label+'，正在操作原站表单，尚未确认受理。',compiler:compiler.label,baseline,baselineKnown,baselineOwner,attempted:true});button.click();return {status:'submitted'};
}
if(action==='observe')return null;
if(action==='submit'){submit().catch(e=>send({status:'error',message:'表单操作未完成：'+String(e).slice(0,160)}));return {status:'loading'};}
const state=inspect();
if(ctx.attempted&&ncReceipt)ncReceipt.poll();
if(ctx.attempted&&lgReceipt)lgReceipt.poll();
if(ctx.platform==='AtCoder'&&ctx.attempted&&ctx.baselineKnown&&state.status!=='finished'){
  (async()=>{try{
    const path=new URL(ctx.originalUrl).pathname.replace(/\/tasks\/[^/]+$/,'/submissions/me');
    const response=await fetch(path,{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});
    if(!response.ok||new URL(response.url,location.href).origin!==location.origin||new URL(response.url,location.href).pathname!==path)return;
    const doc=new DOMParser().parseFromString((await response.text()).slice(0,2000000),'text/html');
    if(doc.querySelector('input[type=password]'))return;
    const receipt=receipts(doc).find(r=>newerReceipt(r.id,new Set(ctx.baseline||[]))&&(!ctx.submissionId||r.id===ctx.submissionId));
    if(receipt?.verdict)send(receiptValue(receipt));
  }catch{}})();
}
if(ctx.platform==='Codeforces'&&ctx.attempted&&ctx.baselineKnown&&state.status!=='finished'){
  const owner=ctx.baselineOwner||cfOwner();
  (async()=>{try{
    // A hidden CF page may stop updating its live verdict cells. Read a fresh
    // authenticated list as well as the public API instead of waiting for DOM.
    for(const path of myPaths()){
      try{const doc=await myPage(path);if(!doc)continue;const candidate=receipts(doc).find(row=>newerReceipt(row.id,new Set(ctx.baseline||[]))&&(!ctx.submissionId||row.id===ctx.submissionId));if(candidate?.verdict){send(receiptValue(candidate));return;}}catch{}
    }
    if(!owner)return;
    const response=await fetch('/api/user.status?handle='+encodeURIComponent(owner)+'&from=1&count=100',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});
    if(!response.ok||new URL(response.url,location.href).origin!==location.origin)return;
    const value=await response.json(),original=new URL(ctx.originalUrl),match=taskPath(original.pathname).match(/^\/(?:contest|gym)\/(\d+)\/problem\/([A-Za-z]\d?)$/);
    if(value.status!=='OK'||!Array.isArray(value.result)||!match)return;
    const baseline=new Set(ctx.baseline||[]);
    const receipt=value.result.filter(row=>Number.isSafeInteger(row.id)&&newerReceipt(String(row.id),baseline)&&(!ctx.submissionId||String(row.id)===ctx.submissionId)&&String(row.problem?.contestId)===match[1]&&row.problem?.index.toUpperCase()===match[2].toUpperCase()&&row.author?.members?.some(member=>member.handle?.toLowerCase()===owner.toLowerCase())).sort((a,b)=>a.id-b.id)[0];
    if(!receipt)return;
    const verdict=normal(receipt.verdict)||'JUDGING';
    send({status:verdict==='JUDGING'?'judging':'finished',submissionId:String(receipt.id),...(verdict==='JUDGING'?{}:{verdict}),message:verdict==='JUDGING'?'原站已接收，正在评测。':'已读取原站本次新提交结果：'+verdict});
  }catch{}})();
}
return state;
}
