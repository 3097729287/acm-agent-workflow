// katex_check.js —— 用 KaTeX 逐个渲染 math.json 里的公式，报语法错误。
// 用法: node katex_check.js math.json
const katex = require("katex");
const fs = require("fs");

const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
let bad = 0, total = 0;
for (const [file, items] of Object.entries(data)) {
  for (const { line, tex } of items) {
    total++;
    try {
      katex.renderToString(tex, { throwOnError: true, strict: false, displayMode: false });
    } catch (e) {
      bad++;
      if (bad <= 80) {
        console.log(`${file.split(/[\\/]/).pop()} L${line}: ${String(e.message).split("\n")[0]}`);
        console.log(`   tex: ${tex}`);
      }
    }
  }
}
console.log(`共 ${total} 个公式，${bad} 个渲染失败`);
