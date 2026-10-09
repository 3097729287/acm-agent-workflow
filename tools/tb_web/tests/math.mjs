import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {unified} from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkRehype from 'remark-rehype';
import rehypeKatex from 'rehype-katex';
import {normalizeMarkdown} from '../src/normalizeMarkdown.js';

const samples=[
  '```cpp\nconst char *s="$$a\\nb$$";\n```\n',
  '~~~text\n$a$$b$\n~~~\n',
  '````text\n```\n$$x\ny$$\n````\n',
  '`$a$$b$` and \\$10',
  '$$unclosed\nmath',
  'ordinary $unclosed text',
];
for(const text of samples)assert.equal(normalizeMarkdown(text),text,'Code/unmatched delimiter must be preserved');
assert.equal(normalizeMarkdown('$a$$b$'),'$a$ $b$');
assert.equal(normalizeMarkdown('$$x\ny$$'),'$$\nx\ny\n$$');
assert.equal(normalizeMarkdown('$$\nx\ny\n$$'),'$$\nx\ny\n$$');

const directory=path.dirname(fileURLToPath(import.meta.url));
const backendDirectory=path.resolve(directory,'..');
const python=process.env.TB_PYTHON||'C:/Users/lenovo/AppData/Local/Programs/Python/Python313/python.exe';
const source=`import sys,json,hashlib\nsys.path.insert(0,${JSON.stringify(backendDirectory)})\nimport backend\nstore=backend.Store()\nbefore=store.data_file.read_bytes()\ndata=store.data()\nsolutions=[dict(id=r['id'],**store.solution(r['id'])) for r in data['rows']]\nassert before==store.data_file.read_bytes(), 'Real TB changed during read-only inspection'\nprint(json.dumps({'solutions':solutions,'tableHash':hashlib.sha256(before).hexdigest()},ensure_ascii=True))`;
const run=spawnSync(python,['-B','-c',source],{encoding:'utf8',maxBuffer:64*1024*1024});
assert.equal(run.status,0,run.stderr);
const data=JSON.parse(run.stdout);
assert.ok(data.solutions.length>0,'Actual library must be inspected');
const pipeline=unified().use(remarkParse).use(remarkGfm).use(remarkMath).use(remarkRehype).use(rehypeKatex,{strict:false});
let formulas=0,changed=0;const errors=[];
for(const solution of data.solutions){
  const normalized=normalizeMarkdown(solution.markdown);
  if(normalized!==solution.markdown)changed++;
  assert.equal(normalizeMarkdown(normalized),normalized,solution.id+' normalization must be idempotent');
  const tree=pipeline.runSync(pipeline.parse(normalized));
  function visit(node){
    const classes=node.properties?.className||[];
    if(classes.includes('katex'))formulas++;
    if(classes.includes('katex-error'))errors.push({id:solution.id,error:node.properties.title});
    for(const child of node.children||[])visit(child);
  }
  visit(tree);
}
console.log(JSON.stringify({solutions:data.solutions.length,formulas,changedSolutions:changed,katexErrors:errors.length,tableHash:data.tableHash,errors},null,2));
assert.equal(errors.length,0,'Every real solution must render without KaTeX errors');
