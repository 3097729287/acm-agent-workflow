// Test-only HTTP adapter. Production runs worker.mjs on Cloudflare, with a real D1 binding.
import { createServer } from 'node:http';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import worker from '../src/worker.mjs';
import { D1Fixture } from './d1.mjs';

export async function startFixture({ database = ':memory:', now } = {}) {
  const DB = new D1Fixture(database), env = { DB, ...(now ? { TEST_NOW: now } : {}) };
  const server = createServer(async (request, response) => {
    try {
      const chunks = []; for await (const chunk of request) chunks.push(chunk);
      const init = { method: request.method, headers: request.headers };
      if (!['GET', 'HEAD'].includes(request.method)) init.body = Buffer.concat(chunks);
      const result = await worker.fetch(new Request('http://127.0.0.1' + request.url, init), env);
      response.writeHead(result.status, Object.fromEntries(result.headers));
      response.end(Buffer.from(await result.arrayBuffer()));
    } catch (error) { response.writeHead(500); response.end('Test adapter failed'); }
  });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  return { server, DB, env, endpoint: `http://127.0.0.1:${server.address().port}`,
    async close() { await new Promise(resolve => server.close(resolve)); DB.close(); } };
}

if (process.argv[1] && fileURLToPath(import.meta.url).toLowerCase() === resolve(process.argv[1]).toLowerCase()) {
  const fixture = await startFixture();
  process.stdout.write(JSON.stringify({ endpoint: fixture.endpoint }) + '\n');
  process.on('SIGTERM', async () => { await fixture.close(); process.exit(0); });
  process.on('SIGINT', async () => { await fixture.close(); process.exit(0); });
}
