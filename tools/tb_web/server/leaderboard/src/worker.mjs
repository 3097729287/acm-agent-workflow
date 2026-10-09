const VERSION = '0.5.0';
const NOTICE = '排行统计客户端报告的首次本地审核通过题数，样例通过与重复题不计入；暂不提供防作弊认证。';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const hashPattern = /^[a-f0-9]{64}$/;
class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

function json(value, status = 200, extra = {}) {
  return new Response(JSON.stringify(value), { status, headers: {
    'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff', ...extra,
  } });
}

async function digest(value) {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return [...new Uint8Array(bytes)].map(b => b.toString(16).padStart(2, '0')).join('');
}

function equalHash(a, b) {
  if (a.length !== b.length) return false;
  let difference = 0;
  for (let index = 0; index < a.length; index++) difference |= a.charCodeAt(index) ^ b.charCodeAt(index);
  return difference === 0;
}

function nickname(value) {
  if (typeof value !== 'string' || /[\u0000-\u001f\u007f]/u.test(value)) throw new ApiError(400, '昵称无效');
  const result = value.trim();
  if ([...result].length < 1 || [...result].length > 32 || new TextEncoder().encode(result).length > 128) throw new ApiError(400, '昵称须为 1–32 个可显示字符');
  return result;
}

async function body(request, allowed) {
  if (!request.headers.get('Content-Type')?.toLowerCase().startsWith('application/json')) throw new ApiError(415, '请求须使用 application/json');
  const declared = Number(request.headers.get('Content-Length') || 0);
  if (!Number.isFinite(declared) || declared > 65536) throw new ApiError(413, '请求不能超过 64 KB');
  if (!request.body) throw new ApiError(400, '缺少 JSON 请求');
  const reader = request.body.getReader();
  const chunks = []; let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > 65536) { await reader.cancel(); throw new ApiError(413, '请求不能超过 64 KB'); }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  let value;
  try { value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
  catch { throw new ApiError(400, 'JSON 请求无效'); }
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(key => !allowed.includes(key))) throw new ApiError(400, '请求字段无效');
  return value;
}

function credentials(request) {
  const userId = request.headers.get('X-TB-User') || '';
  const bearer = /^Bearer ([A-Za-z0-9_-]{32,200})$/.exec(request.headers.get('Authorization') || '');
  if (!uuid.test(userId) || !bearer) throw new ApiError(401, '需要有效的安装身份');
  return { userId, token: bearer[1] };
}

async function authenticate(request, env) {
  const auth = credentials(request);
  const user = await env.DB.prepare('SELECT * FROM users WHERE user_id=?').bind(auth.userId).first();
  if (!user || !equalHash(user.token_hash, await digest(auth.token))) throw new ApiError(401, '安装身份验证失败');
  return user;
}

async function limit(env, bucket, maximum, windowSeconds, now) {
  const window = Math.floor(now / windowSeconds);
  const key = bucket + ':' + window;
  const row = await env.DB.prepare(`INSERT INTO request_limits(bucket,count,expires_at) VALUES(?,1,?)
    ON CONFLICT(bucket) DO UPDATE SET count=count+1 RETURNING count`).bind(key, (window + 1) * windowSeconds).first();
  if (row.count > maximum) throw new ApiError(429, '请求过于频繁，请稍后重试');
}

function bounds(period, now) {
  const day = new Date(now + 8 * 3600 * 1000).toISOString().slice(0, 10);
  const startDate = new Date(day + 'T00:00:00Z');
  if (period === 'weekly') startDate.setUTCDate(startDate.getUTCDate() - (startDate.getUTCDay() + 6) % 7);
  const start = startDate.toISOString().slice(0, 10);
  startDate.setUTCDate(startDate.getUTCDate() + (period === 'weekly' ? 7 : 1));
  return { day, start, end: startDate.toISOString().slice(0, 10) };
}

function rankingRow(row) {
  return { rank: row.rank, userId: row.user_id, nickname: row.nickname, displayName: row.nickname + ' #' + row.user_id, count: row.count };
}

async function leaderboard(user, env, period, now) {
  if (!['daily', 'weekly', 'total'].includes(period)) throw new ApiError(400, '排行周期无效');
  const range = bounds(period, now);
  const where = period === 'total' ? '' : 'WHERE accepted_day>=? AND accepted_day<?';
  const parameters = period === 'total' ? [] : [range.start, range.end];
  const cte = `WITH counts AS (SELECT user_id,COUNT(*) AS count FROM ac_events ${where} GROUP BY user_id),
    ranked AS (SELECT users.user_id,users.nickname,counts.count,
      RANK() OVER(ORDER BY counts.count DESC) AS rank FROM counts JOIN users USING(user_id))`;
  const rows = await env.DB.prepare(cte + ' SELECT * FROM ranked ORDER BY count DESC,user_id LIMIT 100').bind(...parameters).all();
  const own = await env.DB.prepare(cte + ' SELECT * FROM ranked WHERE user_id=?').bind(...parameters, user.user_id).first();
  return { period, date: range.day, timezone: 'Asia/Shanghai', startDate: period === 'total' ? null : range.start,
    endDate: period === 'total' ? null : range.end, entries: rows.results.map(rankingRow),
    self: own ? rankingRow(own) : { rank: null, userId: user.user_id, nickname: user.nickname, displayName: user.nickname + ' #' + user.user_id, count: 0 }, notice: NOTICE };
}

function event(item, now) {
  const fields = ['eventId', 'problemKey', 'acceptedAt', 'difficulty', 'scope'];
  if (!item || typeof item !== 'object' || Array.isArray(item) || Object.keys(item).some(key => !fields.includes(key)) ||
      !hashPattern.test(item.eventId || '') || !hashPattern.test(item.problemKey || '') || item.scope !== 'local-reviewed') throw new ApiError(400, '通过记录字段无效');
  if (typeof item.acceptedAt !== 'string' || item.acceptedAt.length > 40 || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(item.acceptedAt)) throw new ApiError(400, '通过时间无效');
  const time = Date.parse(item.acceptedAt);
  if (!Number.isFinite(time) || time < Date.parse('2000-01-01T00:00:00Z') || time > now + 5 * 60 * 1000) throw new ApiError(400, '通过时间超出有效范围');
  if (item.difficulty != null && (typeof item.difficulty !== 'number' || !Number.isFinite(item.difficulty) || item.difficulty < 0 || item.difficulty > 5000)) throw new ApiError(400, '题目难度无效');
  return { ...item, acceptedAt: new Date(time).toISOString(), day: bounds('daily', time).day };
}

export async function handle(request, env) {
  try {
    if (!env.DB) throw new ApiError(503, '排行榜数据库尚未配置');
    const url = new URL(request.url), path = url.pathname.replace(/\/$/, '');
    const now = env.TEST_NOW == null ? Date.now() : Number(env.TEST_NOW);
    const timestamp = new Date(now).toISOString();
    if (path === '/v1/health' && request.method === 'GET') return json({ ok: true, version: VERSION });
    if (path === '/v1/profile/register' && request.method === 'POST') {
      const auth = credentials(request), value = await body(request, ['userId', 'nickname']);
      if (value.userId !== auth.userId) throw new ApiError(403, '只能注册自己的安装身份');
      const tokenHash = await digest(auth.token);
      const existing = await env.DB.prepare('SELECT * FROM users WHERE user_id=?').bind(auth.userId).first();
      if (existing) {
        if (!equalHash(existing.token_hash, tokenHash)) throw new ApiError(401, '安装身份验证失败');
        return json({ userId: existing.user_id, nickname: existing.nickname, createdAt: existing.created_at });
      }
      const ipHash = await digest((env.RATE_LIMIT_SALT || 'tb-ranking-registration') + ':' + (request.headers.get('CF-Connecting-IP') || 'unknown'));
      await limit(env, 'register-minute:' + ipHash, 10, 60, Math.floor(now / 1000));
      await limit(env, 'register-day:' + ipHash, Math.min(1000, Math.max(1, Number(env.REGISTRATIONS_PER_IP_DAY) || 100)), 86400, Math.floor(now / 1000));
      await env.DB.prepare('INSERT OR IGNORE INTO users(user_id,nickname,token_hash,created_at,updated_at) VALUES(?,?,?,?,?)')
        .bind(auth.userId, nickname(value.nickname), tokenHash, timestamp, timestamp).run();
      const user = await authenticate(request, env);
      return json({ userId: user.user_id, nickname: user.nickname, createdAt: user.created_at }, 201);
    }
    const user = await authenticate(request, env);
    await limit(env, 'user:' + user.user_id, Math.min(600, Math.max(10, Number(env.REQUESTS_PER_USER_MINUTE) || 120)), 60, Math.floor(now / 1000));
    if (path === '/v1/profile' && request.method === 'GET') return json({ userId: user.user_id, nickname: user.nickname, displayName: user.nickname + ' #' + user.user_id, createdAt: user.created_at });
    if (path === '/v1/profile' && request.method === 'PUT') {
      const value = await body(request, ['nickname']), name = nickname(value.nickname);
      await env.DB.prepare('UPDATE users SET nickname=?,updated_at=? WHERE user_id=?').bind(name, timestamp, user.user_id).run();
      return json({ userId: user.user_id, nickname: name, displayName: name + ' #' + user.user_id });
    }
    if (path === '/v1/events' && request.method === 'POST') {
      const value = await body(request, ['events']);
      if (!Array.isArray(value.events) || value.events.length < 1 || value.events.length > 100) throw new ApiError(400, '每次须提交 1–100 条通过记录');
      const events = value.events.map(item => event(item, now));
      const statements = events.map(item => env.DB.prepare(`INSERT INTO ac_events(user_id,problem_key,event_id,accepted_at,accepted_day,difficulty,received_at)
        VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,problem_key) DO UPDATE SET
        accepted_at=MIN(ac_events.accepted_at,excluded.accepted_at),
        accepted_day=CASE WHEN excluded.accepted_at<ac_events.accepted_at THEN excluded.accepted_day ELSE ac_events.accepted_day END,
        difficulty=COALESCE(ac_events.difficulty,excluded.difficulty)`)
        .bind(user.user_id, item.problemKey, item.eventId, item.acceptedAt, item.day, item.difficulty ?? null, timestamp));
      try { await env.DB.batch(statements); }
      catch (error) {
        if (/UNIQUE constraint/i.test(String(error))) throw new ApiError(409, '通过记录编号与原题不匹配');
        throw error;
      }
      return json({ processed: events.length, scope: 'local-reviewed', notice: NOTICE });
    }
    if (path === '/v1/leaderboard' && request.method === 'GET') return json(await leaderboard(user, env, url.searchParams.get('period') || 'daily', now));
    throw new ApiError(404, '没有找到这个接口');
  } catch (error) {
    if (error instanceof ApiError) return json({ error: error.message }, error.status, error.status === 429 ? { 'Retry-After': '60' } : {});
    // Do not log tokens, metadata bodies or D1 statements with bound parameters.
    return json({ error: '排行榜服务暂时无法完成请求' }, 503);
  }
}

export default {
  fetch: handle,
  async scheduled(controller, env) {
    await env.DB.prepare('DELETE FROM request_limits WHERE expires_at<?').bind(Math.floor(Date.now() / 1000)).run();
  },
};
