import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {unified} from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkRehype from 'remark-rehype';
import rehypeKatex from 'rehype-katex';
import {normalizeMarkdown} from '../src/normalizeMarkdown.js';

const file=process.argv[2]||fileURLToPath(new URL('../curated_lectures.json',import.meta.url));
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const pipeline=unified().use(remarkParse).use(remarkGfm).use(remarkMath).use(remarkRehype).use(rehypeKatex,{strict:false});
let formulas=0,changed=0;const errors=[];
for(const lesson of data.lectures){
  assert.ok(lesson.knowledgeName&&lesson.category&&lesson.topic,lesson.id);
  assert.ok(!/[$\\]/.test(lesson.displayTitle),'Card title must be readable plain text: '+lesson.id);
  const normalized=normalizeMarkdown(lesson.markdown);
  if(normalized!==lesson.markdown)changed++;
  assert.equal(normalizeMarkdown(normalized),normalized,lesson.id+' normalization must be idempotent');
  const tree=pipeline.runSync(pipeline.parse(normalized));
  function visit(node){
    const classes=node.properties?.className||[];
    if(classes.includes('katex'))formulas++;
    if(classes.includes('katex-error'))errors.push({id:lesson.id,concept:lesson.concept,error:node.properties.title,tex:node.children?.map(c=>c.value||'').join('')});
    for(const child of node.children||[])visit(child);
  }
  visit(tree);
}
console.log(JSON.stringify({lectures:data.lectures.length,formulas,changedLectures:changed,katexErrors:errors.length,errors},null,2));
assert.equal(errors.length,0,'All curated lessons must render without KaTeX errors');
