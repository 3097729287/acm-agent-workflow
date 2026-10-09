import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {createServer} from 'vite';
import {mkdir} from 'node:fs/promises';
const vite=await createServer({server:{host:'127.0.0.1',port:18769,strictPort:true}});await vite.listen();
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1480,height:920}});page.setDefaultTimeout(10000);
const errors=[],writes=[];page.on('pageerror',e=>errors.push(e.message));
const now=()=>new Date().toISOString();
const library=['A','B','C','D','E','F'].map((letter,i)=>({id:'周赛 164::'+letter,contest:'周赛 164',problem:letter,title:['前缀练习','树上查询','背包练习','区间统计','数论练习','字符串练习'][i],tags:[['前缀和'],['LCA'],['背包 DP'],['差分'],['素数'],['KMP']][i],platform:'牛客',series:'周赛',difficulty:1100+200*i,status:'独立AC',date:'2026-09-01',queue:null,url:'https://ac.nowcoder.com/acm/contest/126120/'+letter,solutionAvailable:i!==5}));
const categories=[{name:'前缀和与差分',tags:['前缀和','差分'],children:[{name:'前缀和',tags:['前缀和'],children:[]},{name:'差分',tags:['差分'],children:[]}]},{name:'图论',tags:['LCA'],children:[{name:'树',tags:['LCA'],children:[{name:'LCA',tags:['LCA'],children:[]}]}]}];
const training=new Map(),archive=new Map(),drafts=new Map(),submissions=[];let opened=0;
function activate(id){let state=archive.get(id)||{...library.find(r=>r.id===id),accepted:false,verdict:null,scope:null,attempts:0,queue:null,activeAt:now()};training.set(id,state);archive.set(id,state)}
activate(library[0].id);Object.assign(training.get(library[0].id),{accepted:true,verdict:'AC',attempts:1,scope:'local'});
activate(library[1].id);Object.assign(training.get(library[1].id),{verdict:'WA',attempts:1,scope:'local',queue:'fill'});
const hub={version:'0.3.0',settings:{githubRepo:'',autoSync:true,intervalHours:6,minDifficulty:1000,maxDifficulty:2199,accounts:{codeforces:'',atcoder:'',nowcoder:'',luogu:''}},accounts:[],sync:{busy:false,message:'公开题库已检查',providers:[]},updates:{configured:false,currentVersion:'0.3.0'},notifications:[{id:'notice-1',type:'content',title:'新增题解',body:'发现新的归档题解',createdAt:now(),read:false,count:1}]};
const insights={summary:{active:2,accepted:1,submissions:2,activeDays:1,streak:1,longestStreak:1,completedContests:0,officialSolved:0,localAccepted:1,samplePassed:0},growth:{xp:120,totalXp:120,level:1,levelName:'开始积累',currentLevelXp:120,nextLevelXp:500,nextMilestone:'再积累380XP'},activity:[{date:now().slice(0,10),submissions:2,accepted:1,officialAccepted:0}],knowledge:[{name:'LCA',tags:['LCA'],available:1,participated:1,accepted:0,attempts:1,failures:1,due:1,mastery:0,confidence:'low',label:'通过覆盖率',priority:5,reason:'这道题还需要攻克',suggestedIds:[library[1].id]}],recommendations:[{name:'LCA',reason:'这道题还需要攻克',priority:5,ids:[library[1].id]}],achievements:[{id:'first',name:'第一次通过',description:'通过第一道本地审核题',unlocked:true,progress:1,target:1}],assessment:{rating:null,label:'独立通过证据不足',confidence:'none',evidenceCount:1,explanation:'至少五道独立本地通过题再估算',platforms:[],trend:[]}};
const workspace=()=>({training:[...training.values()],sets:[],contests:[],activeContest:null,summary:{total:training.size,accepted:[...training.values()].filter(r=>r.accepted).length,attempts:2,due:[...training.values()].filter(r=>r.queue).length,pending:0,samplePassed:0,streak:1},now:now()});
await page.route('**/api/**',async route=>{
 const req=route.request(),url=new URL(req.url()),path=url.pathname,id=url.searchParams.get('id'),body=req.method()==='POST'?req.postDataJSON():null;
 if(body){assert.equal(req.headers()['x-tb-token'],'fixture');writes.push({path,body})}
 let value;
 if(path==='/api/data')value={rows:library,categories,token:'fixture',statuses:[],today:now().slice(0,10),revision:'fixture'};
 else if(path==='/api/workspace')value=workspace();
 else if(path==='/api/inbox')value={pending:0,errors:[]};
 else if(path==='/api/hub')value=hub;
 else if(path==='/api/insights')value=insights;
 else if(path==='/api/hub/configure'){Object.assign(hub.settings,body);value=hub}
 else if(path==='/api/hub/sync')value=hub;
 else if(path==='/api/hub/dismiss'){hub.notifications.find(n=>n.id===body.id).read=true;value=hub}
 else if(path==='/api/training/remove'){training.delete(body.id);value={workspace:workspace()}}
 else if(path==='/api/training/start'){activate(body.id);value={workspace:workspace()}}
 else if(path==='/api/training/contest'){library.forEach(r=>activate(r.id));value={set:{id:'set-1',ids:library.map(r=>r.id)},workspace:workspace()}}
 else if(path==='/api/problem')value={id,title:library.find(r=>r.id===id)?.title,markdown:'## 题目描述\n\n输出一个整数 $n$。\n\n### 输入\n一个整数。',samples:[{name:'样例1',input:'1\n',output:'1\n'}],url:library.find(r=>r.id===id)?.url,limits:{timeMs:2000,memoryMb:256},judge:{scope:'local',label:'本地审核测试',cases:3},locked:false,draft:drafts.get(id)||'',submissions:[],statementAvailable:true};
 else if(path==='/api/draft'){drafts.set(body.id,body.code);value={savedAt:now()}}
 else if(path==='/api/official/open'){opened++;value={sessionId:'official-fixture',platform:'牛客',url:library.find(r=>r.id===body.id)?.url,status:'opened'}}
 else if(path==='/api/submissions'&&body){let sub={id:'s'+submissions.length,problemId:body.id,mode:body.mode,verdict:'QUEUED',scope:'local',code:body.code,submittedAt:now(),finishedAt:null,passed:0,total:3};submissions.push(sub);value={submission:sub}}
 else if(path==='/api/submission'){const sub=submissions.find(s=>s.id===id);Object.assign(sub,{verdict:'SAMPLE_PASS',finishedAt:now(),timeMs:2,memoryKb:2000,passed:3,total:3,output:'1\n',message:'运行完成'});value={submission:sub,workspace:workspace()}}
 else if(path==='/api/submissions')value={submissions};
 else if(path==='/api/solution')value={title:'题解',markdown:'## 思路\n\n$1+1=2$。',url:'https://ac.nowcoder.com/acm/contest/126120/A'};
 else throw new Error('Unhandled API '+path);
 await route.fulfill({json:value});
});
try{
 await page.goto('http://127.0.0.1:18769');await page.getByRole('button',{name:'成长与能力',exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:'知识地图',exact:true}).count(),0);
 assert.equal(await page.getByRole('button',{name:/按比赛/}).count(),0);
 const list=page.locator('.table-scroll');await list.focus();
 const removedTitle=await page.locator('.problem-table tr[data-selected=true] .problem-title').textContent();
 await page.keyboard.press('Delete');await page.waitForFunction(()=>document.querySelectorAll('.problem-table tbody tr').length===1);
 assert.equal(await page.locator('.progress-chip strong').textContent(),'0 / 1');
 assert.equal(await list.evaluate(e=>e===document.activeElement),true);
 await page.getByRole('button',{name:'恢复',exact:true}).press('Enter');await page.waitForFunction(()=>document.querySelectorAll('.problem-table tbody tr').length===2);
 assert.equal(await page.locator('.progress-chip strong').textContent(),'1 / 2');
 await page.keyboard.press('Control+4');const contestCard=page.getByRole('button',{name:/查看 牛客 周赛 164/});await contestCard.focus();await contestCard.press('Enter');
 assert.equal(await page.locator('.competition-question').count(),6);assert.equal(await page.locator('.competition-question').last().getByText('题解未生成').count(),1);
 await page.getByRole('button',{name:'全部比赛',exact:true}).press('Enter');assert.equal(await contestCard.count(),1);
 await page.keyboard.press('Control+7');await page.locator('.progress-page').waitFor();assert.equal(await page.getByText('第一次通过',{exact:true}).count(),1);
 await page.keyboard.press('Control+8');const currentDay=page.getByRole('gridcell',{name:new RegExp(now().slice(0,10))});await currentDay.focus();await page.keyboard.press('ArrowLeft');assert.equal(await page.locator('.activity-day:focus').count(),1);await page.keyboard.press('Enter');
 await page.keyboard.press('Control+9');await page.getByRole('textbox',{name:'Codeforces公开账号'}).fill('test_handle');await page.getByRole('button',{name:'保存账号',exact:true}).press('Enter');await page.getByText('账号设置已保存，正在后台读取公开记录。').waitFor();
 await page.getByRole('textbox',{name:'GitHub公开仓库'}).fill('example/tb');await page.getByRole('button',{name:'保存更新偏好'}).press('Enter');assert.equal(hub.settings.githubRepo,'example/tb');
 const area=page.locator('.settings-page');const width=await area.evaluate(e=>e.clientWidth);assert.ok(width>1100,'settings fills workspace instead of central narrow column');
 await page.getByRole('button',{name:'字号 17',exact:true}).press('Enter');
 assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--ui-font-size').trim()),'17px');
 await mkdir('tests/screenshots',{recursive:true});await page.screenshot({path:'tests/screenshots/v3-settings.png',animations:'disabled'});
 await page.keyboard.press('Control+2');await page.getByRole('button',{name:removedTitle,exact:true}).press('Enter');const editor=page.getByRole('textbox',{name:'C++ 代码',exact:true});await page.locator('.cm-content[contenteditable=true]').waitFor();
 await editor.fill('#include <iostream>\nint main() { return 0; }');await page.waitForFunction(()=>document.querySelectorAll('.cm-line span').length>2);assert.ok(await page.locator('.cm-gutters').count());
 await editor.press('Control+Shift+Enter');await page.waitForFunction(()=>document.querySelector('.wb-notice')?.textContent.includes('官方'));assert.equal(opened,1);assert.equal(submissions.length,0,'opening official window never invents a local submission/AC');
 await editor.press('Control+K');await page.getByRole('textbox',{name:'搜索快捷操作'}).waitFor();await page.keyboard.press('Escape');await editor.focus();await page.keyboard.press('F6');assert.notEqual(await page.locator('.cm-content').evaluate(e=>e===document.activeElement),true,'F6 exits editor');
 await editor.focus();await page.keyboard.press('Control+r');await page.getByText('运行完成',{exact:true}).first().waitFor();assert.equal(submissions.at(-1).mode,'run');
 await page.screenshot({path:'tests/screenshots/v3-code-editor.png',animations:'disabled'});
 await page.keyboard.press('Control+9');await page.setViewportSize({width:1050,height:700});await page.waitForTimeout(150);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.ok(await page.locator('.settings-page').evaluate(e=>e.scrollWidth<=e.clientWidth+1));
 await page.getByRole('button',{name:'更新通知',exact:true}).press('Enter');const updatesDialog=page.getByRole('dialog',{name:'更新与新内容',exact:true});await updatesDialog.getByText('新增题解',{exact:true}).waitFor();await updatesDialog.getByRole('button',{name:'标为已读',exact:true}).press('Enter');await updatesDialog.getByRole('checkbox',{name:'只看未读'}).press('Space');await updatesDialog.getByText('没有未读通知。',{exact:true}).waitFor();await page.keyboard.press('Escape');
 assert.equal(writes.some(w=>w.path==='/api/status'),false);assert.deepEqual(errors,[]);
 console.log('v3 UI passed: remove/restore/history, standalone contests, growth/activity, account/update config, full-width settings/fonts, real CodeMirror tokens, official route, keyboard regions, 1050 layout.');
}finally{await browser.close();await vite.close()}
