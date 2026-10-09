import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID, createHash } from 'node:crypto';
import { startFixture } from './local-server.mjs';

const NOW = Date.parse('2026-10-08T15:59:00Z');
const key = text => createHash('sha256').update(text).digest('hex');
function identity() { return { userId: randomUUID(), token: key(randomUUID()) }; }
async function request(fixture, user, method, path, body) {
  const result = await fetch(fixture.endpoint + path, { method,
    headers: { 'X-TB-User': user.userId, Authorization: 'Bearer ' + user.token, 'Content-Type': 'application/json' },
    ...(body == null ? {} : { body: JSON.stringify(body) }) });
  return { status: result.status, value: await result.json() };
}
async function register(fixture, user, nickname = '训练者') {
  return request(fixture, user, 'POST', '/v1/profile/register', { userId: user.userId, nickname });
}
function ac(user, name, acceptedAt = '2026-10-08T10:00:00Z') {
  return { eventId: key(user.userId + name), problemKey: key(name), acceptedAt, difficulty: 1500, scope: 'local-reviewed' };
}

test('unique persisted identity, authenticated ownership, nickname + full ID', async () => {
  const fixture = await startFixture({ now: NOW });
  try {
    const a = identity(), b = identity();
    assert.equal((await register(fixture, a)).status, 201);
    assert.equal((await register(fixture, b, '另一用户')).status, 201);
    assert.notEqual(a.userId, b.userId);
    assert.equal((await register(fixture, a)).status, 200);
    const stolen = { ...a, token: b.token };
    assert.equal((await register(fixture, stolen)).status, 401);
    assert.equal((await request(fixture, stolen, 'PUT', '/v1/profile', { nickname: '冒领' })).status, 401);
    assert.equal((await request(fixture, a, 'PUT', '/v1/profile', { nickname: '新昵称' })).status, 200);
    const profile = await request(fixture, a, 'GET', '/v1/profile');
    assert.equal(profile.value.displayName, '新昵称 #' + a.userId);
    assert(!JSON.stringify(profile.value).includes('token'));
    assert.equal((await request(fixture, a, 'PUT', '/v1/profile', { nickname: 'X', userId: b.userId })).status, 400);
  } finally { await fixture.close(); }
});

test('AC events are unique by original problem, retry safe, actual SQLite batches roll back', async () => {
  const fixture = await startFixture({ now: NOW });
  try {
    const user = identity(); await register(fixture, user);
    const event = ac(user, 'problem1');
    for (let index = 0; index < 3; index++) assert.equal((await request(fixture, user, 'POST', '/v1/events', { events: [event] })).status, 200);
    const parallel = await Promise.all(Array.from({ length: 8 }, () => request(fixture, user, 'POST', '/v1/events', { events: [event] })));
    assert(parallel.every(value => value.status === 200));
    assert.equal((await request(fixture, user, 'POST', '/v1/events', { events: [{ ...event, eventId: key('replay') }] })).status, 200);
    let score = (await request(fixture, user, 'GET', '/v1/leaderboard?period=total')).value;
    assert.equal(score.self.count, 1);
    const invalid = { ...ac(user, 'problem2'), eventId: event.eventId };
    assert.equal((await request(fixture, user, 'POST', '/v1/events', { events: [ac(user, 'problem3'), invalid] })).status, 409);
    score = (await request(fixture, user, 'GET', '/v1/leaderboard?period=total')).value;
    assert.equal(score.self.count, 1);
    assert.equal(fixture.DB.database.prepare('SELECT COUNT(*) AS n FROM ac_events').get().n, 1);
  } finally { await fixture.close(); }
});

test('daily Beijing midnight and Monday week, repeated later dates cannot farm', async () => {
  const fixture = await startFixture({ now: NOW });
  try {
    const user = identity(); await register(fixture, user);
    const events = [ac(user, 'today', '2026-10-08T10:00:00Z'), ac(user, 'this-week', '2026-10-05T08:00:00Z'), ac(user, 'last-week', '2026-10-04T10:00:00Z')];
    assert.equal((await request(fixture, user, 'POST', '/v1/events', { events })).status, 200);
    assert.equal((await request(fixture, user, 'GET', '/v1/leaderboard?period=daily')).value.self.count, 1);
    assert.equal((await request(fixture, user, 'GET', '/v1/leaderboard?period=weekly')).value.self.count, 2);
    assert.equal((await request(fixture, user, 'GET', '/v1/leaderboard?period=total')).value.self.count, 3);
    fixture.env.TEST_NOW = NOW + 120000;
    assert.equal((await request(fixture, user, 'GET', '/v1/leaderboard?period=daily')).value.self.count, 0);
    assert.equal((await request(fixture, user, 'POST', '/v1/events', { events: [{ ...events[0], acceptedAt: '2026-10-08T16:00:00Z' }] })).status, 200);
    assert.equal((await request(fixture, user, 'GET', '/v1/leaderboard?period=daily')).value.self.count, 0);
    // Out-of-order completion can correct a first acceptance to an earlier date.
    assert.equal((await request(fixture, user, 'POST', '/v1/events', { events: [{ ...events[0], acceptedAt: '2026-10-04T10:00:00Z' }] })).status, 200);
    assert.equal((await request(fixture, user, 'GET', '/v1/leaderboard?period=weekly')).value.self.count, 1);
  } finally { await fixture.close(); }
});

test('ranks real users only, bounds bad payloads, excludes samples and impersonation', async () => {
  const fixture = await startFixture({ now: NOW });
  try {
    const a = identity(), b = identity(); await register(fixture, a); await register(fixture, b);
    assert.equal((await request(fixture, a, 'GET', '/v1/leaderboard')).value.entries.length, 0);
    await request(fixture, a, 'POST', '/v1/events', { events: [ac(a, 'p1'), ac(a, 'p2')] });
    await request(fixture, b, 'POST', '/v1/events', { events: [ac(b, 'p3')] });
    const scores = (await request(fixture, b, 'GET', '/v1/leaderboard')).value;
    assert.deepEqual(scores.entries.map(entry => entry.count), [2, 1]);
    assert.equal(scores.self.rank, 2);
    for (const events of [[{ ...ac(a, 'sample'), scope: 'samples' }], [{ ...ac(a, 'future'), acceptedAt: '2026-10-10T00:00:00Z' }], [{ ...ac(a, 'private'), code: 'PRIVATE CODE' }], Array(101).fill(ac(a, 'big'))]) {
      assert.equal((await request(fixture, a, 'POST', '/v1/events', { events })).status, 400);
    }
    assert.equal((await request(fixture, a, 'POST', '/v1/events', { userId: b.userId, events: [ac(a, 'p4')] })).status, 400);
    assert.equal((await request(fixture, a, 'POST', '/v1/events', { events: [ac(a, 'p4')], junk: 'x'.repeat(66000) })).status, 413);
    assert.equal((await request(fixture, a, 'GET', '/v1/leaderboard?period=invalid')).status, 400);
    assert.equal((await request(fixture, a, 'PUT', '/v1/profile', { nickname: '\u0000bad' })).status, 400);
  } finally { await fixture.close(); }
});

test('per-user rate limits are atomic and have expiry', async () => {
  const fixture = await startFixture({ now: NOW });
  try {
    fixture.env.REQUESTS_PER_USER_MINUTE = 10;
    const user = identity(); await register(fixture, user);
    for (let index = 0; index < 10; index++) assert.equal((await request(fixture, user, 'GET', '/v1/profile')).status, 200);
    assert.equal((await request(fixture, user, 'GET', '/v1/profile')).status, 429);
    fixture.env.TEST_NOW += 61000;
    assert.equal((await request(fixture, user, 'GET', '/v1/profile')).status, 200);
  } finally { await fixture.close(); }
});
