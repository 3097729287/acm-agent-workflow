import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, copyFile, access } from 'node:fs/promises';
import { dirname, basename, join, resolve } from 'node:path';
import { homedir } from 'node:os';

// This probe performs GET requests only. Reuse it on an upgraded installation;
// do not repeat the fresh-install probe's submissions or mission claims.
assert.ok(process.env.BASE_URL && process.env.UPGRADE_BEFORE && process.env.UPGRADE_OUTPUT,
  'Set BASE_URL, UPGRADE_BEFORE and UPGRADE_OUTPUT.');
const endpoint = new URL(process.env.BASE_URL);
assert.equal(endpoint.protocol, 'http:');
assert.ok(['127.0.0.1', 'localhost'].includes(endpoint.hostname));
assert.ok(endpoint.port && endpoint.port !== '18765');
const base = endpoint.origin;
const before = JSON.parse(await readFile(process.env.UPGRADE_BEFORE, 'utf8'));
const output = resolve(process.env.UPGRADE_OUTPUT);

async function get(path) {
  const response = await fetch(`${base}/api/${path}`, { signal: AbortSignal.timeout(60000) });
  assert.equal(response.ok, true, `GET ${path}: ${response.status}`);
  return response.json();
}

async function save(name, value) {
  await mkdir(output, { recursive: true });
  const path = join(output, name);
  let exists = false;
  try { await access(path); exists = true; } catch { /* New report. */ }
  if (exists) {
    const mirror = dirname(path).replaceAll(':', '').replaceAll('\\', '_').replaceAll('/', '_');
    const backup = join(homedir(), '.dsh', 'backups', mirror);
    await mkdir(backup, { recursive: true });
    const stamp = new Date().toISOString().replaceAll(/[-:T.Z]/g, '');
    await copyFile(path, join(backup, `${basename(path)}.${stamp}.bak`));
  }
  await writeFile(path, JSON.stringify(value, null, 2) + '\n', 'utf8');
}

const [identity, workspace, history, insights] = await Promise.all([
  get('profile'), get('workspace'), get('submissions'), get('insights'),
]);
const after = {
  profile: identity.profile,
  summary: workspace.summary,
  training: workspace.training,
  sets: workspace.sets,
  contests: workspace.contests,
  submissions: history.submissions,
  totalSubmissions: history.total,
  growth: insights.growth,
  dailyTasks: insights.dailyTasks,
  achievements: insights.achievements,
};
await save('upgrade-after.json', after);

const checks = [];
const failures = [];
const sorted = items => [...items].sort((first, second) => String(first.id).localeCompare(String(second.id)));
const pick = (item, keys) => Object.fromEntries(keys.map(key => [key, item[key]]));
function check(name, actual, expected) {
  try { assert.deepEqual(actual, expected); checks.push(name); }
  catch (error) { failures.push({ name, error: error.message }); }
}

check('persistent UUID, nickname and creation time', after.profile, before.profile);
check('personal summary counters', after.summary, before.summary);
check('all historical submission records and exact source code', sorted(after.submissions), sorted(before.submissions));
check('historical submission total', after.totalSubmissions, before.totalSubmissions);
const trainingKeys = ['id', 'accepted', 'verdict', 'scope', 'attempts', 'acceptedAt', 'lastSubmittedAt', 'reviewCount', 'solutionSeen', 'activeAt', 'queue'];
check('training activation, acceptance, review and due state', sorted(after.training).map(item => pick(item, trainingKeys)), sorted(before.training).map(item => pick(item, trainingKeys)));
check('original contest practice sets', sorted(after.sets), sorted(before.sets));
const contestKeys = ['id', 'name', 'status', 'startedAt', 'deadline', 'finishedAt', 'duration', 'slots', 'accepted', 'total', 'penalty', 'strategy', 'constraints'];
check('mock session, timing, frozen questions and results', sorted(after.contests).map(item => pick(item, contestKeys)), sorted(before.contests).map(item => pick(item, contestKeys)));
check('experience and level including claimed mission experience', after.growth, before.growth);
check('daily definitions, progress and claim timestamps', after.dailyTasks, before.dailyTasks);
check('all achievement progress and unlock timestamps', sorted(after.achievements), sorted(before.achievements));

const report = {
  passed: !failures.length,
  readOnly: true,
  localAccepted: after.summary.accepted,
  submissions: after.totalSubmissions,
  xp: after.growth.totalXp,
  mockSessions: after.contests.length,
  uuidPreserved: after.profile.userId === before.profile.userId,
  nicknamePreserved: after.profile.nickname === before.profile.nickname,
  checks,
  failures,
};
await save('report.json', report);
console.log(JSON.stringify(report, null, 2));
assert.equal(failures.length, 0, 'Upgrade must preserve every personal record checked above.');
