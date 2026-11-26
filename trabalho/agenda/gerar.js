// Gera os PNGs do flyer (1080 px e 2x): node gerar.js  (precisa do Playwright)
const { chromium } = require('playwright');
const path = require('path');
const http = require('http');
const fs = require('fs');
(async () => {
  // servidor local: a máscara do logo não carrega via file://
  const tipos = { '.html': 'text/html', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
  const srv = http.createServer((req, res) => {
    const f = path.join(__dirname, decodeURIComponent(req.url.split('?')[0]));
    fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': tipos[path.extname(f)] || 'application/octet-stream' }); res.end(d); });
  }).listen(0, '127.0.0.1');
  await new Promise(r => srv.once('listening', r));
  const base = `http://127.0.0.1:${srv.address().port}/`;
  const b = await chromium.launch();
  const out = path.resolve(__dirname, '../../final');
  for (const escala of [1, 2]) for (const [f, h] of [['story', 1920], ['feed', 1350]]) {
    const p = await b.newPage({ viewport: { width: 1080, height: h }, deviceScaleFactor: escala });
    await p.goto(base + 'flyer.html?f=' + f);
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(300);
    await p.locator('#arte').screenshot({ path: path.join(out, `fincape-agenda-${f}${escala === 2 ? '-2x' : ''}.png`) });
    console.log('ok', f, escala + 'x');
  }
  await b.close();
  srv.close();
})();
