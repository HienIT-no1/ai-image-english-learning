import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.dirname(fileURLToPath(import.meta.url));
const assets = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/api.js', ['api.js', 'text/javascript; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
]);
export function createAdminServer({ backend = process.env.BACKEND_URL || 'http://127.0.0.1:8000' } = {}) {
  const target = new URL(backend);
  if (!['http:', 'https:'].includes(target.protocol) || target.username || target.password || target.search || target.hash) throw new Error('Invalid BACKEND_URL');
  const base = target.href.replace(/\/$/, '');
  return http.createServer(async (req, res) => {
    const send = (status, detail) => {
      res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
      res.end(JSON.stringify({ detail }));
    };
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'no-referrer');
    res.setHeader('X-Frame-Options', 'DENY');
    res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
    try {
      const url = new URL(req.url, 'http://localhost');
      if (url.pathname.startsWith('/api/')) {
        const route = url.pathname.slice(4);
        const allowed = new Map([
          ['/auth/login', ['POST']], ['/users/me', ['GET']], ['/admin/summary', ['GET']],
          ['/admin/users', ['GET']], ['/admin/topics', ['GET', 'POST']], ['/admin/vocabularies', ['GET', 'POST']],
        ]);
        const methods = allowed.get(route) || (/^\/admin\/topics\/[1-9]\d*$/.test(route) ? ['PUT', 'DELETE'] : /^\/admin\/vocabularies\/[1-9]\d*$/.test(route) ? ['PUT'] : []);
        if (!methods.includes(req.method)) return send(404, 'API route not available');
        if (req.headers.origin && req.headers.origin !== `http://${req.headers.host}` && req.headers.origin !== `https://${req.headers.host}`) return send(403, 'Cross-origin request rejected');
        const chunks = []; let size = 0;
        for await (const chunk of req) {
          size += chunk.length;
          if (size > 128 * 1024) return send(413, 'Request too large');
          chunks.push(chunk);
        }
        const headers = { accept: 'application/json' };
        if (req.headers.authorization) headers.authorization = req.headers.authorization;
        if (size) headers['content-type'] = 'application/json';
        const response = await fetch(base + route + url.search, {
          method: req.method, headers, body: size ? Buffer.concat(chunks) : undefined,
          signal: AbortSignal.timeout(20000), redirect: 'error',
        });
        const content = Buffer.from(await response.arrayBuffer());
        res.writeHead(response.status, { 'content-type': response.headers.get('content-type') || 'application/json', 'cache-control': 'no-store' });
        res.end(content); return;
      }
      if (!['GET', 'HEAD'].includes(req.method)) return send(405, 'Method not allowed');
      const asset = assets.get(url.pathname);
      if (!asset) return send(404, 'Not found');
      const content = await readFile(path.join(root, asset[0]));
      res.writeHead(200, { 'content-type': asset[1], 'cache-control': 'no-cache' });
      res.end(req.method === 'HEAD' ? undefined : content);
    } catch (error) {
      if (!res.headersSent) send(502, error.name === 'TimeoutError' ? 'Backend timed out' : 'Cannot connect to backend');
      else res.end();
    }
  });
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 3001), host = process.env.HOST || '127.0.0.1';
  createAdminServer().listen(port, host, () => console.log(`LENLEARN Admin: http://${host}:${port}`));
}
