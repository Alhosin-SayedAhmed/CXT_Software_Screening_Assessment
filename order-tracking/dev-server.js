// سيرفر صغير لتجربة الموقع على جهازك: npm start ← http://localhost:3000
// على الإنترنت مش محتاجينه، Cloudflare Pages بيعرض فولدر public مباشرة.
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, 'public');
const PORT = Number(process.env.PORT) || 3000;
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
};

// نفس الهيدرز اللي في public/_headers (الجزء بتاع /*)
const headers = {};
let inAll = false;
for (const line of fs.readFileSync(path.join(ROOT, '_headers'), 'utf8').split('\n')) {
  if (/^\S/.test(line)) inAll = line.trim() === '/*';
  else if (inAll && line.includes(':')) {
    const i = line.indexOf(':');
    headers[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
}

function resolve(urlPath) {
  if (urlPath.startsWith('/track/')) return 'index.html';
  if (urlPath === '/') return 'index.html';
  const clean = path.normalize(decodeURIComponent(urlPath)).replace(/^([/\\])+/, '');
  if (clean.startsWith('..') || path.basename(clean).startsWith('_')) return null;
  for (const c of [clean, clean + '.html']) {
    const f = path.join(ROOT, c);
    if (f.startsWith(ROOT) && fs.existsSync(f) && fs.statSync(f).isFile()) return c;
  }
  return null;
}

http.createServer((req, res) => {
  let file;
  try { file = resolve(new URL(req.url, 'http://x').pathname); } catch { file = null; }
  const status = file ? 200 : 404;
  file = file || 'index.html';
  res.writeHead(status, { ...headers, 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
  fs.createReadStream(path.join(ROOT, file)).pipe(res);
}).listen(PORT, () => {
  console.log(`✅ الموقع شغال على جهازك: http://localhost:${PORT}`);
  console.log(`   لوحة التحكم: http://localhost:${PORT}/admin`);
});
