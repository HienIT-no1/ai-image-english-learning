import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { once } from 'node:events';
import { createAdminServer } from '../server.mjs';
import { errorMessage, request, ApiError } from '../api.js';

async function listen(server) {
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  return `http://127.0.0.1:${server.address().port}`;
}
async function close(server) { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }

await test('HTTP proxy contract', async t => {
  let observed;
  const backend = http.createServer(async (req,res) => {
    const chunks = []; for await (const chunk of req) chunks.push(chunk);
    observed = { path:req.url, method:req.method, token:req.headers.authorization, body:Buffer.concat(chunks).toString() };
    const status = req.url === '/admin/topics/9' ? 409 : req.url === '/users/me' ? 403 : req.method === 'POST' ? 201 : 200;
    res.writeHead(status, {'content-type':'application/json'});
    res.end(JSON.stringify(status === 409 ? {detail:'Topic still contains vocabulary'} : status === 403 ? {detail:'Admin access required'} : {ok:true}));
  });
  const backendUrl = await listen(backend), proxy = createAdminServer({backend:backendUrl}), url = await listen(proxy);
  t.after(async () => { await close(proxy); await close(backend); });
  await t.test('serves the console with browser security headers', async () => {
    const res = await fetch(url);
    assert.equal(res.status,200); assert.match(await res.text(),/lang="vi"/);
    assert.equal(res.headers.get('x-content-type-options'),'nosniff');
    assert.match(res.headers.get('content-security-policy'),/script-src 'self'/);
    for (const asset of ['app.js','api.js','styles.css']) assert.equal((await fetch(`${url}/${asset}`)).status,200);
  });
  await t.test('forwards bearer token and user pagination', async () => {
    const res = await fetch(`${url}/api/admin/users?offset=99&limit=100`,{headers:{Authorization:'Bearer test-token'}});
    assert.equal(res.status,200); assert.equal(observed.token,'Bearer test-token');
    assert.equal(observed.path,'/admin/users?offset=99&limit=100');
    assert.equal(res.headers.get('cache-control'),'no-store');
  });
  await t.test('forwards login and vocabulary payload without changing Unicode', async () => {
    for (const route of ['/auth/login','/admin/vocabularies']) {
      const payload = {word:'apple',meaning_vi:'quả táo',topic_ids:[1]};
      const res = await fetch(`${url}/api${route}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      assert.equal(res.status,201); assert.equal(observed.method,'POST'); assert.deepEqual(JSON.parse(observed.body),payload);
    }
    const res = await fetch(`${url}/api/admin/vocabularies/2`,{method:'PUT',body:JSON.stringify({word:'pear'})});
    assert.equal(res.status,200); assert.equal(observed.method,'PUT');
  });
  await t.test('preserves backend authorization and conflict errors', async () => {
    let res = await fetch(`${url}/api/users/me`); assert.equal(res.status,403);
    res = await fetch(`${url}/api/admin/topics/9`,{method:'DELETE'});
    assert.equal(res.status,409); assert.equal((await res.json()).detail,'Topic still contains vocabulary');
  });
  await t.test('rejects unrelated API routes, files and unsupported methods', async () => {
    for (const route of ['/api/database','/api/auth/register','/server.mjs','/package.json','/.env','/../backend/.env','/%2e%2e/backend/.env']) assert.equal((await fetch(url+route)).status,404,route);
    assert.equal((await fetch(`${url}/api/admin/users`,{method:'DELETE'})).status,404);
    assert.equal((await fetch(`${url}/api/admin/vocabularies/1`,{method:'DELETE'})).status,404);
    assert.equal((await fetch(url,{method:'POST'})).status,405);
  });
  await t.test('rejects cross-origin writes and oversized payloads', async () => {
    assert.equal((await fetch(`${url}/api/admin/topics`,{method:'POST',headers:{Origin:'https://other.invalid'},body:'{}'})).status,403);
    assert.equal((await fetch(`${url}/api/admin/topics`,{method:'POST',body:'x'.repeat(129*1024)})).status,413);
  });
  await t.test('reports unavailable backend without exposing internals', async () => {
    const unavailable = http.createServer(); const deadUrl = await listen(unavailable); await close(unavailable);
    const broken = createAdminServer({backend:deadUrl}); const brokenUrl = await listen(broken);
    try { const res = await fetch(`${brokenUrl}/api/admin/summary`); assert.equal(res.status,502); assert.deepEqual(await res.json(),{detail:'Cannot connect to backend'}); }
    finally { await close(broken); }
  });
});

test('client translates validation and known backend errors', () => {
  assert.match(errorMessage('Topic still contains vocabulary'),/Chủ đề còn từ vựng/);
  assert.match(errorMessage([{loc:['body','word'],msg:'Field required'}]),/word: Field required/);
  assert.match(errorMessage(null),/không thành công/);
});

test('client sends JSON and bearer token, rejects authorization errors', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  let captured;
  globalThis.fetch = async (url,options) => { captured = {url,options}; return new Response(JSON.stringify({ok:true}),{status:200}); };
  await request('/admin/topics',{token:'sample',method:'POST',body:{name:'Động vật'}});
  assert.equal(captured.url,'/api/admin/topics'); assert.equal(captured.options.headers.Authorization,'Bearer sample');
  assert.deepEqual(JSON.parse(captured.options.body),{name:'Động vật'});
  globalThis.fetch = async () => new Response(JSON.stringify({detail:'Admin access required'}),{status:403});
  await assert.rejects(request('/admin/topics'),e => e instanceof ApiError && e.status === 403 && /quyền quản trị/.test(e.message));
  globalThis.fetch = async () => { throw new Error('offline'); };
  await assert.rejects(request('/admin/topics'),e => e.status === 0);
});
