import { passed, STATES } from './model.js';

const priority = row => row.status === STATES[2] ? 0 : row.status === STATES[1] ? 1 : 2;
const tagsOf = row => [...new Set((Array.isArray(row.tags) ? row.tags : []).filter(tag => typeof tag === 'string' && tag.trim()).map(tag => tag.trim()))];
const compareId = (a, b) => a < b ? -1 : a > b ? 1 : 0;

function seededRank(id, seed) {
  let hash = 2166136261;
  for (const char of `${seed}:${id}`) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

/** Select a temporary plan without changing rows, their statuses, or the source table. */
export function buildPlan(rows, { min = 1300, max = 2100, count = 6, seed = 0 } = {}) {
  const lower = Number(min), upper = Number(max), target = Math.floor(Number(count));
  if (min === '' || max === '' || min == null || max == null || !Number.isFinite(lower) || !Number.isFinite(upper) || lower < 0 || lower > upper || !Number.isFinite(target) || target <= 0) return [];
  const seen = new Set();
  const candidates = (Array.isArray(rows) ? rows : []).filter(row => {
    if (!row || row.id == null || seen.has(String(row.id)) || passed(row)) return false;
    if (row.difficulty == null || row.difficulty === '' || !Number.isFinite(Number(row.difficulty))) return false;
    if (Number(row.difficulty) < lower || Number(row.difficulty) > upper) return false;
    seen.add(String(row.id));
    return true;
  }).map(row => ({ row, tags: tagsOf(row) }));
  const center = (lower + upper) / 2;
  const covered = new Set();
  const plan = [];
  while (candidates.length && plan.length < target) {
    candidates.sort((a, b) => {
      const tier = priority(a.row) - priority(b.row);
      if (tier) return tier;
      const gained = b.tags.filter(tag => !covered.has(tag)).length - a.tags.filter(tag => !covered.has(tag)).length;
      if (gained) return gained;
      const distance = Math.abs(Number(a.row.difficulty) - center) - Math.abs(Number(b.row.difficulty) - center);
      if (distance) return distance;
      const idA = String(a.row.id), idB = String(b.row.id);
      if (seed !== 0) {
        const shuffled = seededRank(idA, seed) - seededRank(idB, seed);
        if (shuffled) return shuffled;
      }
      return compareId(idA, idB);
    });
    const chosen = candidates.shift();
    const newTags = chosen.tags.filter(tag => !covered.has(tag));
    chosen.tags.forEach(tag => covered.add(tag));
    const reason = chosen.row.status === STATES[2] ? '待重写，先独立重写一次'
      : chosen.row.status === STATES[1] ? '待补题，重新思考这题'
      : newTags.length ? `补充 ${newTags.slice(0, 2).join('、')}${newTags.length > 2 ? ` 等 ${newTags.length} 个知识点` : ''}`
      : '同一难度带的补充练习';
    plan.push({ row: chosen.row, reason, newTags });
  }
  return plan;
}
