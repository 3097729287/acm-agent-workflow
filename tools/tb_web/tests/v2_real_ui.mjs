import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1480,height:920}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
async function get(path){const response=await page.request.get('http://127.0.0.1:18766/api/'+path);assert.equal(response.ok(),true);return response.json()}
try{
 await page.goto('http://127.0.0.1:18766');await page.getByRole('heading',{name:'从第一道题开始',exact:true}).waitFor();
 await page.keyboard.press('Control+2');const search=page.getByRole('textbox',{name:'搜索题目'});await search.fill('入门赛 49 D');
 await page.locator('.problem-table tbody tr .problem-title').first().click();
 const editor=page.getByRole('textbox',{name:'C++17 代码'});await page.waitForFunction(()=>document.querySelector('.wb-code')&&!document.querySelector('.wb-code').disabled);
 assert.equal(await page.locator('.wb-scope-local').count(),1);
 const solution='#include <bits/stdc++.h>\nusing namespace std; int main(){int n;cin>>n;long long one[61]={1},two[61]={0};for(int i=1;i<=n;++i){one[i]=one[i-1]+two[i-1];if(i>=2)two[i]=one[i-2];}cout<<one[n]+two[n]<<"\\n";}\n';
 await editor.fill(solution);await editor.press('Control+r');
 await page.waitForFunction(()=>document.querySelector('.wb-result-summary')?.textContent.includes('运行完成'),{},{timeout:30000});
 let progress=await get('workspace');assert.equal(progress.summary.accepted,0,'run never accepted');
 await editor.press('Control+Enter');await page.waitForFunction(()=>document.querySelector('.wb-result-summary')?.textContent.includes('本地 AC'),{},{timeout:40000});
 progress=await get('workspace');assert.equal(progress.summary.total,1);assert.equal(progress.summary.accepted,1);
 await mkdir('tests/screenshots',{recursive:true});await page.screenshot({path:'tests/screenshots/v2-real-local-ac.png',animations:'disabled'});
 await page.getByRole('button',{name:'返回列表',exact:true}).click();await page.keyboard.press('Control+4');
 await page.getByRole('button',{name:'生成试卷',exact:true}).click();await page.getByRole('button',{name:'开始 120 分钟模拟赛',exact:true}).waitFor();
 const difficulties=await page.locator('.paper-slot .difficulty').allTextContents();assert.equal(difficulties.length,6);assert.equal(new Set(difficulties).size,6);assert.equal(difficulties.every((d,i)=>!i||Number(d)>Number(difficulties[i-1])),true);
 assert.equal(await page.locator('.paper-slot').filter({hasText:'本地评测'}).count(),6);
 await page.getByRole('button',{name:'开始 120 分钟模拟赛',exact:true}).click();await page.locator('.contest-tabs').waitFor();
 await page.waitForFunction(()=>document.querySelector('.wb-code')&&!document.querySelector('.wb-code').disabled);
 progress=await get('workspace');const mock=progress.activeContest;assert.equal(mock.total,6);assert.equal(mock.accepted,0);assert.equal(progress.summary.total,new Set(['入门赛 49::D',...mock.slots.map(s=>s.id)]).size,'overlap unique');
 assert.equal(mock.slots.some(slot=>'difficulty'in slot||'tags'in slot),false,'blind contest slot metadata');
 const locked=await page.request.get('http://127.0.0.1:18766/api/solution?id='+encodeURIComponent(mock.slots[0].id));assert.equal(locked.status(),403);
 await page.screenshot({path:'tests/screenshots/v2-real-contest.png',animations:'disabled'});
 await page.locator('.wb-statement').focus();await page.keyboard.press('2');await page.waitForFunction(()=>document.querySelector('.wb-letter')?.textContent==='B');
 await page.getByRole('button',{name:'结束比赛',exact:true}).click();await page.getByRole('button',{name:'结束并复盘',exact:true}).click();await page.locator('.record-detail').waitFor();
 progress=await get('workspace');assert.equal(progress.activeContest,null);assert.equal(progress.contests.length,1);assert.equal(progress.contests[0].total,6);
 await page.keyboard.press('Control+3');await page.getByRole('region',{name:'今日待办题目'}).waitFor();assert.equal(await page.locator('.problem-table tbody tr[data-id]').count(),6,'unfinished mock slots due even old personal AC');
 await page.screenshot({path:'tests/screenshots/v2-real-today.png',animations:'disabled'});
 assert.deepEqual(errors,[]);
 console.log('Real C++17 run → local AC → 6 strictly ascending reviewed mock questions → backend solution lock → record + automatic due queue. Temporary personal DB only.');
}finally{await browser.close()}
