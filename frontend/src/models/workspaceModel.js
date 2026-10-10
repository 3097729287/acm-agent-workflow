import { matches } from "./model.js";
import { compareContestNewest } from "@/lib/practiceMetadata.js";

export const QUEUES = [
  {
    id: "rewrite",
    name: "独立重写",
    description: "看过题解后，再独立完成一次",
    color: "purple",
  },
  {
    id: "fill",
    name: "待攻克",
    description: "从上次未通过的地方继续",
    color: "orange",
  },
  {
    id: "verify",
    name: "待验证",
    description: "样例已通过，继续验证完整约束",
    color: "blue",
  },
  {
    id: "review",
    name: "间隔复习",
    description: "首次通过 7 天后，再独立写一次",
    color: "blue",
  },
  {
    id: "check",
    name: "巩固抽检",
    description: "复习通过 30 天后，检查掌握",
    color: "green",
  },
];
export const VERDICTS = {
  AC: "本地 AC",
  SAMPLE_PASS: "样例通过",
  RUN_OK: "运行完成（未校验）",
  WA: "答案错误",
  TLE: "超时",
  MLE: "内存超限",
  RE: "运行错误",
  CE: "编译错误",
  OLE: "输出超限",
  ERROR: "评测异常",
  RUNNING: "评测中",
  QUEUED: "排队中",
};
export function verdictLabel(value) {
  return VERDICTS[value] || value || "未提交";
}
export function verdictTone(value) {
  if (value === "AC") return "success";
  if (value === "SAMPLE_PASS" || ["运行完成", "RUN_OK"].includes(value)) return "sample";
  if (["QUEUED", "RUNNING"].includes(value)) return "pending";
  return value ? "failed" : "neutral";
}
export function progressMap(workspace) {
  return new Map((workspace?.training || []).map((row) => [row.id, row]));
}
export function progressRows(library, workspace) {
  const states = progressMap(workspace);
  const locked = new Set((workspace?.activeContest?.slots || []).map(s=>s.id));
  return library.map((row) => ({
    ...row,
    ...states.get(row.id),
    active: states.has(row.id),
    verdict: states.get(row.id)?.verdict || null,
    accepted: !!states.get(row.id)?.accepted,
    ...(locked.has(row.id) ? {difficulty:null,tags:[],knowledge:"",locked:true} : {}),
  }));
}
export function filterRows(rows, filters = {}) {
  const {
    query = "",
    platform = "",
    category = null,
    min = "",
    max = "",
    result = "",
    favoritesOnly = false,
    favorites = [],
    contest = "",
    sort = "contestDate",
    ids = null,
    desc = false,
  } = filters;
  return rows
    .filter(
      (row) =>
        (!ids || ids.includes(row.id)) &&
        matches({ ...row, status: verdictLabel(row.verdict) }, query) &&
        (!platform || row.platform === platform) &&
        (!category || row.tags.some((tag) => category.tags.includes(tag))) &&
        (min === "" ||
          (row.difficulty != null && row.difficulty >= Number(min))) &&
        (max === "" ||
          (row.difficulty != null && row.difficulty <= Number(max))) &&
        (!contest || row.contest === contest) &&
        (!favoritesOnly || favorites.includes(row.id)) &&
        (!result ||
          (result === "accepted"
            ? row.accepted
            : result === "pending"
              ? !row.accepted
              : result === "sample"
                ? row.verdict === "SAMPLE_PASS"
                : row.verdict === result)),
    )
    .sort((a, b) => {
      let order = 0;
      if (sort === "contestDate")
        order = compareContestNewest(a, b) || String(a.problem).localeCompare(String(b.problem), "en", { numeric: true });
      else if (sort === "difficulty")
        order = (a.difficulty ?? 9999) - (b.difficulty ?? 9999);
      else if (sort === "date")
        order = (a.lastSubmittedAt || a.activeAt || "").localeCompare(
          b.lastSubmittedAt || b.activeAt || "",
        );
      else if (sort === "title")
        order = a.title.localeCompare(b.title, "zh-CN");
      else
        order =
          a.contest.localeCompare(b.contest, "zh-CN", { numeric: true }) ||
          a.problem.localeCompare(b.problem, "en", { numeric: true });
      return desc ? -order : order;
    });
}
export function groupContests(rows) {
  const groups = new Map();
  for (const row of rows) {
    if (!groups.has(row.contest))
      groups.set(row.contest, {
        name: row.contest,
        platform: row.platform,
        rows: [],
      });
    groups.get(row.contest).rows.push(row);
  }
  return [...groups.values()].map((group) => ({
    ...group,
    total: group.rows.length,
    accepted: group.rows.filter((r) => r.accepted).length,
    active: group.rows.filter((r) => r.active).length,
    min: Math.min(...group.rows.map((r) => r.difficulty ?? Infinity)),
    max: Math.max(...group.rows.map((r) => r.difficulty ?? 0)),
    tags: [...new Set(group.rows.flatMap((r) => r.tags))],
  }));
}
export function categoryCounts(node, rows, training) {
  const has = (row) => row.tags.some((tag) => node.tags.includes(tag));
  const active = training.filter(has);
  return {
    available: rows.filter(has).length,
    active: active.length,
    accepted: active.filter((r) => r.accepted).length,
    due: active.filter((r) => r.queue).length,
  };
}
export function remainingSeconds(contest, now = Date.now()) {
  if (!contest || contest.status !== "running") return 0;
  return Math.max(0, Math.ceil((Date.parse(contest.deadline) - now) / 1000));
}
export function timerText(seconds) {
  const value = Math.max(0, Math.floor(seconds));
  return [Math.floor(value / 3600), Math.floor((value % 3600) / 60), value % 60]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");
}
export function nextSurviving(ids, currentId, remaining) {
  const position = ids.indexOf(currentId),
    valid = new Set(remaining);
  return (
    ids.slice(position + 1).find((id) => valid.has(id)) ||
    ids
      .slice(0, position)
      .reverse()
      .find((id) => valid.has(id)) ||
    remaining[0] ||
    null
  );
}
export const emptyWorkspace = {
  training: [],
  sets: [],
  contests: [],
  activeContest: null,
  summary: {
    total: 0,
    accepted: 0,
    samplePassed: 0,
    attempts: 0,
    due: 0,
    streak: 0,
  },
};
