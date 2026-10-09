import assert from 'node:assert/strict';
import { buildPlan } from '../src/planner.js';

const row = (id, status = '未做', difficulty = 1700, tags = []) => ({ id, status, difficulty, tags, title: `题目 ${id}`, contest: '测试比赛', problem: String(id) });
let checked = 0;
function check(name, callback) { callback(); checked++; console.log(`PASS ${name}`); }

check('待重写 / 不会优先于其他未做题，先处理待重写', () => {
  const plan = buildPlan([row('new', '未做', 1700, ['A', 'B', 'C']), row('stuck', '不会', 1700, ['D']), row('rewrite', '待重写', 1300)], { count: 3 });
  assert.deepEqual(plan.map(item => item.row.id), ['rewrite', 'stuck', 'new']);
  assert.match(plan[0].reason, /待重写/);
  assert.match(plan[1].reason, /待补题/);
});
check('范围包含上下界，排除未知难度和所有 AC 类状态', () => {
  const records = [row('low', '未做', 1300), row('high', '未做', 2100), row('below', '待重写', 1299), row('above', '不会', 2101), row('null', '未做', null), row('blank', '未做', ''), row('nan', '未做', 'unknown'), ...['复现AC', '独立AC', '巩固'].map(status => row(status, status))];
  assert.deepEqual(buildPlan(records, { count: 10 }).map(item => item.row.id).sort(), ['high', 'low']);
});
check('按照题数截断，不足时只返回实际可练题目', () => {
  const records = Array.from({ length: 12 }, (_, i) => row(String(i)));
  for (const count of [3, 6, 10]) assert.equal(buildPlan(records, { count }).length, count);
  assert.equal(buildPlan(records.slice(0, 2), { count: 6 }).length, 2);
});
check('每道题只出现一次，支持数值 0 作为题目 ID', () => {
  const plan = buildPlan([row(0), row('a'), row('a'), row('b'), row(null)], { count: 10 });
  assert.equal(plan.length, 3);
  assert.equal(new Set(plan.map(item => String(item.row.id))).size, 3);
  assert(plan.some(item => item.row.id === 0));
});
check('贪心选择新覆盖知识点，而不是重复知识点或重复标签', () => {
  const plan = buildPlan([row('a', '未做', 1700, ['A', 'B']), row('b', '未做', 1700, ['A', 'B']), row('c', '未做', 1700, ['C']), row('d', '未做', 1700, ['A', 'A', 'A'])], { count: 2 });
  assert.deepEqual(plan.map(item => item.row.id), ['a', 'c']);
  assert.deepEqual(plan[1].newTags, ['C']);
  assert.equal(plan[1].reason, '补充 C');
});
check('覆盖相同时选择接近难度中心的题目，完全相同时稳定按 ID 排序', () => {
  assert.equal(buildPlan([row('far', '未做', 1300, ['A']), row('near', '未做', 1700, ['B'])], { count: 1 })[0].row.id, 'near');
  assert.equal(buildPlan([row('z'), row('a'), row('m')], { count: 1 })[0].row.id, 'a');
});
check('相同种子结果稳定，不受原始行顺序影响，刷新可更换同条件题目', () => {
  const records = Array.from({ length: 18 }, (_, i) => row(`id-${i}`, '未做', 1700, ['A']));
  const ids = (source, seed) => buildPlan(source, { count: 3, seed }).map(item => item.row.id);
  assert.deepEqual(ids(records, 3), ids([...records].reverse(), 3));
  const original = JSON.stringify(ids(records, 0));
  assert(Array.from({ length: 10 }, (_, i) => JSON.stringify(ids(records, i + 1))).some(value => value !== original));
});
check('无效范围 / 数量返回空推荐，生成过程不修改源数据', () => {
  const records = [row('a', '待重写', 1700, ['A']), row('b')];
  const snapshot = JSON.stringify(records);
  for (const options of [{ min: 2100, max: 1300 }, { min: '' }, { max: '' }, { min: null }, { min: -1 }, { max: NaN }, { count: 0 }]) assert.deepEqual(buildPlan(records, options), []);
  buildPlan(records);
  assert.equal(JSON.stringify(records), snapshot);
  assert.equal(buildPlan(records)[0].row, records[0]);
});
console.log(`${checked} planner checks passed.`);
