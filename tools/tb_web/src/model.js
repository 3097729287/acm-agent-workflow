export const STATES = ["未做", "不会", "待重写", "复现AC", "独立AC", "巩固"];
export const STATE_CLASS = [
  "new",
  "stuck",
  "rewrite",
  "reproduce",
  "independent",
  "mastered",
];
export const QUEUES = [
  {
    id: "rewrite",
    name: "待重写",
    desc: "先把看过的题独立写出来",
    color: "pink",
  },
  { id: "fill", name: "待补题", desc: "重新思考，再查阅题解", color: "orange" },
  {
    id: "review",
    name: "间隔复习",
    desc: "AC 后第 7 天，再做一次",
    color: "blue",
  },
  {
    id: "check",
    name: "巩固抽检",
    desc: "巩固后第 30 天，检查掌握",
    color: "green",
  },
];
export const mastered = (row) => ["独立AC", "巩固"].includes(row.status);
export const passed = (row) =>
  ["复现AC", "独立AC", "巩固"].includes(row.status);
export function matches(row, query) {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  return words.every((word) => {
    const range = word.match(/^(\d+)\s*[-~～]\s*(\d+)$/);
    if (range)
      return (
        row.difficulty != null &&
        row.difficulty >= Number(range[1]) &&
        row.difficulty <= Number(range[2])
      );
    if (/^\d+$/.test(word))
      return (
        String(row.difficulty ?? "") === word ||
        row.contest.toLowerCase().includes(word)
      );
    if (/^[a-z]\d?$/.test(word)) return row.problem.toLowerCase() === word;
    return [row.contest, row.title, row.knowledge, row.status, row.platform]
      .join(" ")
      .toLowerCase()
      .replaceAll(" ", "")
      .includes(word.replaceAll(" ", ""));
  });
}
export function filteredRows(
  rows,
  {
    query = "",
    status = "",
    platform = "",
    tags = null,
    min = "",
    max = "",
    sort = "contest",
    desc = false,
  },
) {
  return rows
    .filter(
      (r) =>
        matches(r, query) &&
        (!status || r.status === status) &&
        (!platform || r.platform === platform) &&
        (!tags || r.tags.some((t) => tags.includes(t))) &&
        (min === "" || (r.difficulty != null && r.difficulty >= Number(min))) &&
        (max === "" || (r.difficulty != null && r.difficulty <= Number(max))),
    )
    .sort((a, b) => {
      let result;
      if (sort === "difficulty")
        result = (a.difficulty ?? -1) - (b.difficulty ?? -1);
      else if (sort === "date") result = a.date.localeCompare(b.date);
      else if (sort === "title")
        result = a.title.localeCompare(b.title, "zh-CN");
      else
        result =
          a.contest.localeCompare(b.contest, "zh-CN", { numeric: true }) ||
          a.problem.localeCompare(b.problem, "en", { numeric: true });
      return desc ? -result : result;
    });
}
export function categoryStats(node, rows) {
  const tags = node.tags || [node.name];
  const matched = rows.filter((r) => r.tags.some((t) => tags.includes(t)));
  return {
    total: matched.length,
    passed: matched.filter(passed).length,
    weak: matched.filter((r) => ["不会", "待重写"].includes(r.status)).length,
  };
}
// Display groups keep the dictionary's standard tags and existing branches intact.
export function organizeCategories(source) {
  const pending=new Map(source.map(node=>[node.name,node]));
  const take=names=>names.map(name=>{const node=pending.get(name);pending.delete(name);return node}).filter(Boolean);
  const group=(name,children)=>({name,children,tags:[...new Set(children.flatMap(n=>n.tags||[n.name]))]});
  const nodes=[];
  const add=(name,names)=>{const children=take(names);if(children.length)nodes.push(group(name,children))};
  add('思维与策略',['模拟','枚举','贪心','构造','排序','折半枚举']);
  const dp=take(['线性 DP','DP']);if(dp.length)nodes.push({...dp[0],name:'动态规划'});
  add('基础技巧',['前缀和与差分','二分','双指针','位运算','离散化','连续段','递推','倍增']);
  const structures=take(['数据结构']);if(structures.length){const extra=take(['莫队']);nodes.push(group('数据结构',[...structures[0].children,...extra]))}
  const graphs=take(['图论']);nodes.push(...graphs);
  add('数学与计数',['数学','计数','置换环']);
  const strings=take(['字符串']);nodes.push(...strings);
  const search=take(['搜索']);nodes.push(...search);
  add('计算几何',['计算几何','扫描线']);
  if(pending.size)nodes.push(group('专题方法',[...pending.values()]));
  return nodes;
}
