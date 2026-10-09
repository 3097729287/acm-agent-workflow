// Presentation only: keep archive bytes and mathematical content unchanged.
// The fetch tool's comment banner is metadata already shown by the workbench.
export function normalizeStatement(markdown, samples = [], title = '') {
  let text = String(markdown || '').replaceAll('\r\n', '\n');
  const lines = text.split('\n');
  if (/^#{12,}\s*$/.test(lines[0] || '')) {
    const end = lines.findIndex((line, index) => index > 0 && /^#{12,}\s*$/.test(line));
    if (end > 0 && lines.slice(0, end).some(line => /^#\s*来源[:：]/.test(line))) {
      text = lines.slice(end + 1).join('\n').trimStart();
    }
  } else if (title && text.startsWith('# ' + title + '\n')) {
    const prefix = text.match(/^# [^\n]+\n\s*原题[:：]\s*https?:\/\/[^\n]+\n\s*/);
    if (prefix) text = text.slice(prefix[0].length);
  }
  // Platform automation notices do not change the task's inputs, outputs or constraints.
  text = text.replace(/::anti-ai\[[^\]]*\]/g, '');
  const sampleBanner = /\n={12,}\s*\n官方样例\s*\n={12,}\s*\n/;
  const banner = text.match(sampleBanner);
  if (banner && samples.length) {
    text = text.slice(0, banner.index).trimEnd() + '\n\n## 样例\n\n' + samples.map((sample, index) => {
      const fence = '```';
      // Official inputs are plain text. Use a longer fence if a literal fence occurs in a sample.
      const longest = Math.max(0,...[String(sample.input || ''),String(sample.output || '')].flatMap(value => [...value.matchAll(/`+/g)].map(match => match[0].length)));
      const delimiter = longest >= 3 ? '`'.repeat(longest + 1) : fence;
      return `### 样例 ${index + 1}\n\n输入\n\n${delimiter}text\n${String(sample.input || '').trimEnd()}\n${delimiter}\n\n输出\n\n${delimiter}text\n${String(sample.output || '').trimEnd()}\n${delimiter}`;
    }).join('\n\n');
  }
  return text.trim();
}
