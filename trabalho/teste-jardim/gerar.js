// Gera os quadros de teste das 3 direções: node gerar.js
const { chromium } = require('playwright');
const path = require('path'), http = require('http'), fs = require('fs');
(async () => {
  const tipos = { '.html': 'text/html', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
  const srv = http.createServer((req, res) => {
    const f = path.join(__dirname, decodeURIComponent(req.url.split('?')[0]));
    fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': tipos[path.extname(f)] || 'application/octet-stream' }); res.end(d); });
  }).listen(0, '127.0.0.1');
  await new Promise(r => srv.once('listening', r));
  const base = `http://127.0.0.1:${srv.address().port}/`;
  const b = await chromium.launch();
  for (const d of ['a', 'b', 'c']) {
    const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
    await p.goto(base + 'teste.html?d=' + d);
    await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
    await p.locator('#' + d.toUpperCase()).screenshot({ path: path.join(__dirname, `direcao-${d}.png`) });
    console.log('ok', d);
  }
  await b.close(); srv.close();
})();
