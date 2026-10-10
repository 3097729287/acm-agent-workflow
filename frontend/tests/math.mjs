import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {unified} from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkRehype from 'remark-rehype';
import rehypeKatex from 'rehype-katex';
import {normalizeMarkdown} from '../src/lib/normalizeMarkdown.js';

const samples=[
  '```cpp\nconst char *s="$$a\\nb$$";\n```\n',
  '~~~text\n$a$$b$\n~~~\n',
  '````text\n```\n$$x\ny$$\n````\n',
  '`$a$$b$` and \\$10',
  '$$unclosed\nmath',
  'ordinary $unclosed text',
  '$$$unclosed text',
  String.raw`Unclosed \(x and \[y`,
  String.raw`Escaped \\(x\\) and \\[y\\]`,
  String.raw`Code: \`\(x\) $$$y$$$\``.replaceAll('\\`', '`'),
];
for(const text of samples)assert.equal(normalizeMarkdown(text),text,'Code/unmatched delimiter must be preserved');
assert.equal(normalizeMarkdown('$a$$b$'),'$a$ $b$');
assert.equal(normalizeMarkdown('$$x\ny$$'),'$$\nx\ny\n$$');
assert.equal(normalizeMarkdown('$$\nx\ny\n$$'),'$$\nx\ny\n$$');
assert.equal(normalizeMarkdown(String.raw`\(a_i\)`),'$a_i$');
assert.equal(normalizeMarkdown(String.raw`\[a_i\]`),'$$\na_i\n$$');
assert.equal(normalizeMarkdown('$$$a$$$$$$b$$$'),'$a$ $b$');
assert.equal(normalizeMarkdown('$$$x\ny$$$'),'$$\nx\ny\n$$');
for(const text of [String.raw`\(a\)\(b\)`,String.raw`$a$\(b\)`,String.raw`\(a\)$b$`,String.raw`$$$a$$$\(b\)`]){
  assert.equal(normalizeMarkdown(text),'$a$ $b$');
  assert.equal(normalizeMarkdown(normalizeMarkdown(text)),normalizeMarkdown(text));
}

const directory=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(directory,'../..');
const solutions=JSON.parse(readFileSync(path.join(root,'data/library/solutions.json'),'utf8'));
const lectures=JSON.parse(readFileSync(path.join(root,'data/library/lectures.json'),'utf8'));
const data={solutions:solutions.map(s=>({id:s.problem_id,markdown:s.markdown})).concat(lectures.map(l=>({id:l.content.id,markdown:l.content.markdown})))};
assert.ok(data.solutions.length>=985,'Inspect the distributed library content');
const pipeline=unified().use(remarkParse).use(remarkGfm).use(remarkMath).use(remarkRehype).use(rehypeKatex,{strict:false});
const reportedFormula=String.raw`F(i, j) = a_i \cdot \prod_{k=1}^{j} a_k = a_i \cdot \left(a_1 \cdot a_2 \cdot \ldots \cdot a_j\right)`;
for(const text of [`$${reportedFormula}$`, `$$${reportedFormula}$$`, `$$$${reportedFormula}$$$`, `\\(${reportedFormula}\\)`, `\\[${reportedFormula}\\]`]){
  const normalized=normalizeMarkdown(text);
  assert.equal(normalizeMarkdown(normalized),normalized);
  const tree=pipeline.runSync(pipeline.parse(normalized));
  const nodes=[];
  function collect(node){nodes.push(node);for(const child of node.children||[])collect(child)}
  collect(tree);
  assert.ok(nodes.some(node=>node.properties?.className?.includes('katex')), 'The reported product formula must be typeset');
  assert.ok(!nodes.some(node=>node.properties?.className?.includes('katex-error')));
}
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
console.log(JSON.stringify({solutions:data.solutions.length,formulas,changedSolutions:changed,katexErrors:errors.length,errors},null,2));
assert.equal(errors.length,0,'Every real solution must render without KaTeX errors');
