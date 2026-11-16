// Optional local preview server for the CoinKitty.org website.
// Dependency-free: node:http only, no npm install, no network access.
// Run it from this folder: node dev-server.mjs [--port 3000] [--host 127.0.0.1]
import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';

const args = process.argv.slice(2);
const value = (flag, fallback) => (args.includes(flag) ? args[args.indexOf(flag) + 1] : fallback);
const port = Number(value('--port', '3000'));
const host = value('--host', '127.0.0.1');
const root = resolve(import.meta.dirname);

const types = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.pdf': 'application/pdf',
  '.txt': 'text/plain; charset=utf-8'
};

const notFound = readFile(resolve(root, '404.html'), 'utf8');

http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://local');
    let path = resolve(root, '.' + decodeURIComponent(url.pathname));
    if (path !== root && !path.startsWith(root + sep)) {
      res.writeHead(403).end();
      return;
    }
    if (path === root || (await stat(path)).isDirectory()) {
      path = resolve(path, 'index.html');
    }
    const bytes = await readFile(path);
    res.writeHead(200, {
      'Content-Type': types[extname(path).toLowerCase()] || 'application/octet-stream',
      'X-Content-Type-Options': 'nosniff'
    });
    res.end(bytes);
  } catch {
    // Mirror Cloudflare Pages: any unknown address serves the 404 page.
    try {
      res.writeHead(404, { 'Content-Type': types['.html'] });
      res.end(await notFound);
    } catch {
      res.writeHead(404).end('Not found');
    }
  }
}).listen(port, host, () => console.log(`CoinKitty.org preview, local: http://${host}:${port}`));
