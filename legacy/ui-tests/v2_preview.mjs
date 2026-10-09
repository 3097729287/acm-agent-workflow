import {chromium} from 'playwright';
import {mkdir} from 'node:fs/promises';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1480,height:920}});
const errors=[];page.on('pageerror',error=>errors.push(error.message));
await mkdir('tests/screenshots',{recursive:true});
try{
  await page.goto('http://127.0.0.1:18766');
  await page.getByRole('button',{name:'去题库选题',exact:true}).waitFor();
  await page.getByRole('button',{name:'题库',exact:true}).click();
  await page.locator('.problem-table tbody tr').first().waitFor();
  await page.screenshot({path:'tests/screenshots/v2-library-dark.png',animations:'disabled'});
  const geometry=await page.evaluate(()=>({screen:innerHeight,topbar:document.querySelector('.topbar').getBoundingClientRect().height,table:document.querySelector('.table-scroll').getBoundingClientRect().height,rowsVisible:[...document.querySelectorAll('.problem-table tbody tr')].filter(r=>r.getBoundingClientRect().top<document.querySelector('.table-scroll').getBoundingClientRect().bottom).length,horizontal:document.documentElement.scrollWidth>innerWidth}));
  await page.getByRole('button',{name:'切换主题',exact:true}).click();
  await page.screenshot({path:'tests/screenshots/v2-library-light.png',animations:'disabled'});
  await page.getByRole('button',{name:'知识地图',exact:true}).click();
  await page.screenshot({path:'tests/screenshots/v2-knowledge-light.png',animations:'disabled'});
  await page.getByRole('button',{name:'模拟赛',exact:true}).click();
  await page.getByRole('button',{name:'生成试卷',exact:true}).click();
  await page.getByRole('button',{name:'开始 120 分钟模拟赛',exact:true}).waitFor({timeout:20000});
  await page.screenshot({path:'tests/screenshots/v2-mock-create.png',animations:'disabled'});
  await page.getByRole('button',{name:'题库',exact:true}).click();
  await page.getByRole('textbox',{name:'搜索题目',exact:true}).fill('ABC 478 D');
  await page.locator('.problem-table tbody tr .problem-title').first().click();
  await page.waitForFunction(()=>!!document.querySelector('.wb-code')&&!document.querySelector('.wb-code').disabled,{},{timeout:20000});
  await page.screenshot({path:'tests/screenshots/v2-workbench.png',animations:'disabled'});
  console.log(JSON.stringify({geometry,errors}));
}finally{await browser.close()}
