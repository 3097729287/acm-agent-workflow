import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {createServer} from 'vite';
import {mkdir} from 'node:fs/promises';
const server=await createServer({server:{host:'127.0.0.1',port:18769,strictPort:true}});
await server.listen();
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1480,height:920}});
const page=await context.newPage();page.setDefaultTimeout(10000);
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const ids=['A','B','C','D','E','F','G'];
const titles=['前缀练习','树上查询','背包练习','区间统计','数论练习','字符串练习','独立单题'];
const tags=[['前缀和'],['LCA'],['背包 DP'],['差分'],['素数'],['KMP'],['模拟']];
const library=ids.map((problem,i)=>({id:'周赛 164::'+problem,contest:'周赛 164',problem,title:titles[i],tags:tags[i],knowledge:tags[i].join(' + '),platform:'牛客',series:'周赛',difficulty:1100+i*150,status:i?'独立AC':'不会',date:'2026-09-01',queue:'fill'}));
library[6].contest='ABC 478';library[6].id='ABC 478::G';library[6].platform='AtCoder';
const categories=[{name:'前缀和与差分',tags:['前缀和','差分'],children:[{name:'前缀和',tags:['前缀和'],children:[]},{name:'差分',tags:['差分'],children:[]}]},{name:'图论',tags:['LCA'],children:[{name:'树',tags:['LCA'],children:[{name:'LCA',tags:['LCA'],children:[]}]}]},{name:'线性 DP',tags:['背包 DP'],children:[{name:'背包 DP',tags:['背包 DP'],children:[]}]}];
const training=new Map(),sets=[],contests=[],drafts=new Map(),submissions=[];
let active=null,job=0,manual=0,legacyRevision=0;
const timestamp=()=>new Date().toISOString();
function activate(id){if(!training.has(id))training.set(id,{...library.find(r=>r.id===id),activeAt:timestamp(),accepted:false,verdict:null,scope:null,acceptedAt:null,lastSubmittedAt:null,attempts:0,reviewCount:0,queue:null,solutionSeen:false})}
function workspace(){return {training:[...training.values()],sets,contests,activeContest:active,summary:{total:training.size,accepted:[...training.values()].filter(r=>r.accepted).length,samplePassed:[...training.values()].filter(r=>r.verdict==='SAMPLE_PASS'&&!r.accepted).length,attempts:submissions.filter(s=>s.mode==='submit').length,due:[...training.values()].filter(r=>r.queue).length,streak:0,pending:submissions.filter(s=>!s.finishedAt).length},now:timestamp()}}
const baseProblem={markdown:'## 题目描述\n\n求 $a + b$。\n\n$$\n\\sum_{i=1}^{n} a_i\n$$\n\n### 输入\n\n两个整数。',samples:[{name:'样例 1',input:'2 3\n',output:'5\n'}],url:'https://example.com/problem',limits:{timeMs:2000,memoryMb:256},judge:{scope:'local',label:'本地审核测试',cases:3},statementAvailable:true};
await context.route('**/api/**',async route=>{
  const req=route.request(),url=new URL(req.url()),path=url.pathname,body=req.method()==='POST'?req.postDataJSON():null,id=url.searchParams.get('id');
  if(body)assert.equal(req.headers()['x-tb-token'],'fixture-token');
  let result;
  if(path==='/api/data')result={rows:library,statuses:['未做','不会','待重写','复现AC','独立AC','巩固'],categories,revision:String(legacyRevision),today:'2026-10-08',token:'fixture-token'};
  else if(path==='/api/workspace')result=workspace();
  else if(path==='/api/inbox'&&!body)result={pending:0,errors:[],path:'fixture inbox'};
  else if(path==='/api/training/start'){activate(body.id);result={workspace:workspace()}}
  else if(path==='/api/training/contest'){
    let set=sets.find(s=>s.name===body.contest);
    if(!set){const chosen=library.filter(r=>r.contest===body.contest);chosen.forEach(r=>activate(r.id));set={id:'set-'+sets.length,name:body.contest,ids:chosen.map(r=>r.id),type:'practice',createdAt:timestamp(),accepted:0,total:chosen.length};sets.push(set)}
    result={set,workspace:workspace()};
  }
  else if(path==='/api/problem'){
    const contestId=url.searchParams.get('contestId');
    result={...baseProblem,id,title:library.find(r=>r.id===id)?.title,locked:!!(active&&active.slots.some(s=>s.id===id)),draft:drafts.get((contestId||'solo')+':'+id)||'',submissions:submissions.filter(s=>s.problemId===id&&s.contestId===(contestId||null))};
  }
  else if(path==='/api/draft'){drafts.set((body.contestId||'solo')+':'+body.id,body.code);result={savedAt:timestamp()}}
  else if(path==='/api/submissions'&&body){
    const sub={id:'submission-'+(++job),problemId:body.id,contestId:body.contestId||null,mode:body.mode,verdict:'QUEUED',scope:body.code.includes('sample')?'samples':'local',code:body.code,submittedAt:timestamp(),finishedAt:null,timeMs:null,memoryKb:null,passed:0,total:3,output:'',stderr:'',message:''};
    if(body.mode==='submit')activate(body.id);submissions.unshift(sub);result={submission:sub};
  }
  else if(path==='/api/submission'){
    const sub=submissions.find(s=>s.id===id);
    if(!sub.finishedAt){
      sub.verdict=sub.mode==='run'?'SAMPLE_PASS':sub.code.includes('fail')?'WA':sub.code.includes('sample')?'SAMPLE_PASS':'AC';
      sub.finishedAt=timestamp();sub.timeMs=5;sub.memoryKb=3000;sub.passed=sub.verdict==='WA'?0:3;sub.output='5\n';sub.message=sub.mode==='run'?'运行完成':'fixture completed';
      if(sub.mode==='submit'){
        const row=training.get(sub.problemId);row.verdict=sub.verdict;row.scope=sub.scope;row.attempts++;row.lastSubmittedAt=sub.submittedAt;row.accepted||=sub.verdict==='AC';row.queue=sub.verdict==='WA'?'fill':sub.verdict==='SAMPLE_PASS'?'verify':null;
        sets.forEach(set=>{set.accepted=set.ids.filter(id=>training.get(id)?.accepted).length});
        if(sub.contestId){const contest=contests.find(c=>c.id===sub.contestId),slot=contest.slots.find(s=>s.id===sub.problemId);slot.verdict=sub.verdict;slot.attempts++;slot.accepted||=sub.verdict==='AC';contest.accepted=contest.slots.filter(s=>s.accepted).length;}
      }
    }
    result={submission:sub,workspace:workspace()};
  }
  else if(path==='/api/submissions')result={submissions};
  else if(path==='/api/solution'){
    if(active?.slots.some(s=>s.id===id)){await route.fulfill({status:403,json:{error:'题解已锁定'}});return}
    if(training.has(id))training.get(id).solutionSeen=true;
    result={title:library.find(r=>r.id===id)?.title,markdown:baseProblem.markdown+'\n\n```cpp\nint main() {}\n```',url:'https://example.com/problem'};
  }
  else if(path==='/api/contests/preview')result={plan:{name:'fixture mock',duration:body.duration,min:body.min,max:body.max,slots:library.slice(0,6).map((r,i)=>({letter:ids[i],id:r.id,title:r.title,difficulty:r.difficulty,tags:r.tags,judgeScope:'local'}))},available:7};
  else if(path==='/api/contests/start'){
    const startedAt=timestamp();active={id:'contest-1',name:body.name,status:'running',startedAt,deadline:new Date(Date.now()+body.duration*60000).toISOString(),finishedAt:null,duration:body.duration,slots:body.ids.map((id,i)=>({letter:ids[i],id,title:library.find(r=>r.id===id).title,accepted:false,verdict:null,samplePassed:false,attempts:0,solvedAt:null})),accepted:0,total:body.ids.length,penalty:0,elapsedSeconds:0};
    body.ids.forEach(activate);contests.unshift(active);result={contest:active,workspace:workspace()};
  }
  else if(path==='/api/contests/finish'){
    const finished=active;finished.status='finished';finished.finishedAt=timestamp();finished.slots.forEach(slot=>{const row=library.find(r=>r.id===slot.id);slot.difficulty=row.difficulty;slot.tags=row.tags;if(!slot.accepted)training.get(slot.id).queue='fill'});active=null;result={contest:finished,workspace:workspace()};
  }
  else if(path==='/api/contest')result={contest:contests.find(c=>c.id===id),now:timestamp()};
  else if(path==='/api/status'){manual++;legacyRevision++;throw Error('v2 must not manually mutate TB status')}
  else throw new Error('Unexpected API '+path);
  await route.fulfill({json:result});
});

try{
  await page.goto('http://127.0.0.1:18769');
  await page.getByRole('heading',{name:'从第一道题开始',exact:true}).waitFor();
  assert.match(await page.getByRole('button',{name:'训练概览',exact:true}).innerText(),/0\s*\/\s*0/);
  await page.keyboard.press('Control+2');
  await page.locator('.problem-table tbody tr').first().waitFor();
  assert.equal(await page.locator('.problem-table tbody tr').count(),7);
  assert.equal(await page.locator('.problem-table .verdict.success').count(),0,'legacy AC is ignored');
  const table=page.getByRole('region',{name:'题目列表'});await table.focus();
  const first=await page.locator('tr[data-selected=true]').getAttribute('data-id');
  for(const digit of ['1','2','3','4','5','6'])await page.keyboard.press(digit);
  assert.equal(await page.locator('tr[data-selected=true]').getAttribute('data-id'),first);
  assert.equal(await table.evaluate(el=>el===document.activeElement),true,'old digits leave focus intact');
  await page.keyboard.press('f');assert.equal(await page.getByRole('textbox',{name:'搜索题目'}).evaluate(el=>el===document.activeElement),true);
  await page.getByRole('textbox',{name:'搜索题目'}).fill('1300-1700');
  await page.waitForFunction(()=>document.querySelectorAll('.problem-table tbody tr').length===3);
  await page.keyboard.press('Escape');await page.waitForFunction(()=>document.querySelectorAll('.problem-table tbody tr').length===7);
  await page.keyboard.press('Control+b');await page.waitForFunction(()=>Math.round(document.querySelector('.sidebar').getBoundingClientRect().width)===62);
  await page.keyboard.press('Control+b');
  const graph=page.locator('.sidebar').getByRole('treeitem').filter({hasText:'图论'});await graph.focus();await graph.press('ArrowRight');
  await graph.press('ArrowRight');await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowRight');await page.keyboard.press('Enter');
  await page.waitForFunction(()=>document.querySelectorAll('.problem-table tbody tr').length===1);
  assert.match(await page.locator('.problem-table tbody').innerText(),/树上查询/);
  await page.getByRole('button',{name:'清除知识点筛选',exact:true}).click();
  await page.getByRole('button',{name:'收藏 前缀练习',exact:true}).click();
  await page.getByRole('button',{name:'收藏题目筛选',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.problem-table tbody tr').length===1);
  await page.getByRole('button',{name:'收藏题目筛选',exact:true}).click();
  await page.getByRole('button',{name:'筛选',exact:true}).click();
  await page.getByRole('spinbutton',{name:'最低难度',exact:true}).fill('1400');
  await page.getByRole('button',{name:'保存筛选',exact:true}).click();
  await page.getByRole('textbox',{name:'筛选名称',exact:true}).fill('更进一步');
  await page.getByRole('dialog',{name:'保存常用筛选'}).getByRole('button',{name:'保存筛选',exact:true}).click();
  await page.getByRole('button',{name:'重置',exact:true}).click();
  await page.getByRole('button',{name:'按比赛',exact:false}).click();
  await page.locator('.contest-library-row').filter({hasText:'周赛 164'}).getByRole('button',{name:'加入训练',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.page-identity h1')?.textContent==='我的训练');
  assert.equal(training.size,6,'only proactively selected original contest activates');
  assert.equal(await page.locator('.problem-table tbody tr').count(),6);
  await page.getByRole('button',{name:'尚未 AC',exact:false}).click();
  await table.focus();await page.keyboard.press('Home');
  assert.match(await page.locator('tr[data-selected=true]').innerText(),/前缀练习/);
  await page.keyboard.press('Enter');
  const editor=page.getByRole('textbox',{name:'C++17 代码'});
  await page.waitForFunction(()=>!!document.querySelector('.wb-code')&&!document.querySelector('.wb-code').disabled);
  await editor.fill('local correct');await editor.press('Control+Enter');
  await page.waitForFunction(()=>document.querySelector('.wb-result-summary')?.textContent.includes('本地 AC'));
  await page.getByRole('button',{name:'返回列表',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.problem-table tbody tr').length===5);
  assert.match(await page.locator('tr[data-selected=true]').innerText(),/树上查询/,'after passed filtered row, lock next row');
  assert.equal(await table.evaluate(el=>el===document.activeElement),true,'restore list keyboard focus');
  await page.keyboard.press('Enter');await page.waitForFunction(()=>!!document.querySelector('.wb-code')&&!document.querySelector('.wb-code').disabled);
  await editor.fill('sample correct');await editor.press('Control+Enter');
  await page.waitForFunction(()=>document.querySelector('.wb-result-summary')?.textContent.includes('样例通过'));
  await page.getByRole('button',{name:'返回列表',exact:true}).click();
  assert.equal([...training.values()].filter(r=>r.accepted).length,1,'samples never increment AC');
  await page.getByRole('button',{name:'练习 背包练习',exact:true}).click();await page.waitForFunction(()=>!!document.querySelector('.wb-code')&&!document.querySelector('.wb-code').disabled);
  await editor.fill('fail this');await editor.press('Control+Enter');await page.waitForFunction(()=>document.querySelector('.wb-result-summary')?.textContent.includes('答案错误'));
  await page.getByRole('button',{name:'返回列表',exact:true}).click();
  await page.keyboard.press('Control+2');await page.getByRole('textbox',{name:'搜索题目'}).fill('独立单题');
  await page.keyboard.press('Control+3');
  await page.getByRole('region',{name:'今日待办题目'}).waitFor();
  assert.equal(await page.locator('.problem-table tbody tr[data-id]').count(),2,'today ignores library filters and legacy queues');
  assert.match(await page.locator('.problem-table tbody').innerText(),/树上查询/);
  assert.match(await page.locator('.problem-table tbody').innerText(),/背包练习/);
  await page.keyboard.press('Control+4');await page.getByRole('button',{name:'生成试卷',exact:true}).click();await page.getByRole('button',{name:'开始 120 分钟模拟赛',exact:true}).click();
  await page.getByRole('tab',{name:/A/}).waitFor();
  assert.equal(await page.locator('.contest-tab').count(),6);
  assert.equal(active.accepted,0,'earlier single AC does not solve new contest');
  assert.equal(training.size,6,'overlap counted once');
  assert.equal(await page.getByRole('button',{name:'题解',exact:true}).count(),0,'contest no solution button');
  await page.locator('.wb-statement').focus();await page.keyboard.press('2');
  await page.waitForFunction(()=>document.querySelector('.wb-letter')?.textContent==='B');
  await page.waitForFunction(()=>!!document.querySelector('.wb-code')&&!document.querySelector('.wb-code').disabled);
  assert.notEqual(await editor.inputValue(),'sample correct','mock code context independent');
  await editor.fill('contest local correct');await editor.press('Control+s');
  await page.waitForFunction(()=>document.querySelector('.wb-save-state')?.textContent.includes('已保存'));
  await editor.press('Control+Enter');await page.waitForFunction(()=>document.querySelector('.wb-result-summary')?.textContent.includes('本地 AC'));
  assert.equal(active.accepted,1);
  await page.getByRole('button',{name:'结束比赛',exact:true}).click();
  await page.getByRole('dialog',{name:'结束这场模拟赛'}).getByRole('button',{name:'结束并复盘',exact:true}).click();
  await page.locator('.record-detail').waitFor();assert.equal(active,null);
  assert.equal(await page.locator('.record-slot').count(),6);
  await page.getByRole('button',{name:'只看未 AC',exact:true}).click();assert.equal(await page.locator('.record-slot').count(),5);
  await page.locator('.record-slot').first().getByRole('button',{name:/题解/}).click();
  await page.locator('.reader-panel .katex').first().waitFor();assert.equal(await page.locator('.katex-error').count(),0);
  await page.getByRole('button',{name:'题解全屏',exact:true}).click();await page.keyboard.press('Escape');
  assert.equal(await page.locator('.reader-panel').count(),0);
  await page.keyboard.press('Control+k');await page.getByRole('dialog',{name:'快捷操作'}).waitFor();
  await page.getByRole('button',{name:'切换深浅主题',exact:true}).click();
  assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
  await page.getByRole('button',{name:'偏好设置',exact:true}).click();
  await page.getByRole('checkbox',{name:'界面动效',exact:true}).uncheck();
  await page.getByRole('button',{name:'澄空蓝',exact:true}).click();
  await page.reload();await page.getByRole('heading',{name:'我的训练',exact:true}).waitFor();
  assert.equal(await page.locator('html').getAttribute('data-theme'),'light');assert.equal(await page.locator('html').getAttribute('data-accent'),'blue');assert.equal(await page.locator('html').getAttribute('data-motion'),'off');
  await page.keyboard.press('Control+2');await page.setViewportSize({width:1050,height:700});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  const libraryRows=await page.locator('.problem-table tbody tr').count();assert.equal(libraryRows,7,'library keeps all problems');
  const nav=page.getByRole('button',{name:'知识地图',exact:true});await nav.focus();await nav.press('Enter');assert.equal(await page.getByRole('heading',{name:'知识地图',exact:true}).count(),1,'navigation Enter is native');
  assert.equal(manual,0);assert.equal(legacyRevision,0);assert.deepEqual(errors,[]);
  await mkdir('tests/screenshots',{recursive:true});await page.screenshot({path:'tests/screenshots/v2-fixture-responsive.png',animations:'disabled'});
  console.log('TB v2 UI: library isolation, real-progress denominator, next-row focus, today-only queues, keyboard tree/nav, saved filters, mock scopes/history/locks, themes, 1050 layout. No manual statuses or page errors.');
}finally{await browser.close();await server.close()}
