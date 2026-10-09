// Shared display bands and chronology. Personal submission dates are never
// substituted for the date of the original contest.
export function difficultyBand(value) {
  if (value == null || !Number.isFinite(Number(value))) return "unknown";
  const rating = Number(value);
  return rating < 1200 ? "intro" : rating < 1500 ? "basic" : rating < 1800 ? "intermediate" : rating < 2100 ? "challenge" : "advanced";
}

export function contestTime(row) {
  for (const value of [row?.contestDate, row?.startedAt, row?.endedAt]) {
    if (typeof value !== "string" || !value.trim()) continue;
    const time = Date.parse(value);
    if (Number.isFinite(time)) return time;
  }
  const times = (row?.rows || []).map(contestTime).filter(Number.isFinite);
  return times.length ? Math.max(...times) : null;
}

function roundInfo(row) {
  const name = String(row?.contest || row?.name || "");
  const matches = [...name.matchAll(/\d+/g)];
  const standard = name.match(/(?:Round\s+|ABC\s*|ARC\s*|Div\.\s*[234]\s+|周赛\s*|小白月赛\s*|练习赛\s*|挑战赛\s*|入门赛\s*|基础赛\s*|月赛\s*)(\d+)/i);
  const number = standard ? Number(standard[1]) : matches.length ? Number(matches.at(-1)[0]) : 0;
  const family = String(row?.series || name.replace(/\d+/g, "").replace(/\s+/g, " ").trim());
  return { name, family, number, platform: String(row?.platform || "") };
}

export function compareContestNewest(a, b) {
  const left = contestTime(a), right = contestTime(b);
  if (left != null && right != null && left !== right) return right - left;
  if (left != null && right == null) return -1;
  if (left == null && right != null) return 1;
  const x = roundInfo(a), y = roundInfo(b);
  if (x.platform === y.platform && x.family === y.family && x.number !== y.number) return y.number - x.number;
  return x.platform.localeCompare(y.platform, "zh-CN") || x.family.localeCompare(y.family, "zh-CN") || y.number - x.number || y.name.localeCompare(x.name, "zh-CN", { numeric: true });
}

// Collapse teaching sections in the display layer; the source Markdown stays
// unchanged. Ignore heading-like text inside fenced C++/shell snippets.
export function solutionBlocks(markdown = "", lectures = []) {
  const lines = String(markdown).split("\n"), blocks = [];
  let buffered = [], lesson = null, fence = null;
  const flush = () => {
    if (!buffered.length) return;
    blocks.push(lesson ? { type: "lecture", markdown: buffered.join("\n"), heading: lesson.heading, lecture: lesson.lecture } : { type: "markdown", markdown: buffered.join("\n") });
    buffered = [];
  };
  for (const line of lines) {
    const code = line.match(/^\s*(`{3,}|~{3,})/);
    if (code) {
      if (!fence) fence = code[1][0];
      else if (fence === code[1][0]) fence = null;
      buffered.push(line);
      continue;
    }
    const heading = !fence && line.match(/^(#{1,6})\s+(.+)$/);
    if (heading && lesson && heading[1].length <= lesson.level) { flush(); lesson = null; }
    if (heading && /从零讲\s*[：:]/.test(heading[2])) {
      flush();
      const title = heading[2].replace(/^[\d.、\s]+/, "").replace(/^从零讲\s*[：:]\s*/, "").trim();
      const reference = lectures.find(item => [item.title, item.concept, item.heading].some(name => name && (name === title || name === heading[2] || name.includes(title) || title.includes(name))));
      lesson = { level: heading[1].length, heading: title, lecture: reference };
    }
    buffered.push(line);
  }
  flush();
  return blocks;
}
