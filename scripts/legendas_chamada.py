#!/usr/bin/env python3
"""Gera o projeto HyperFrames de uma chamada (legendas + faixa de informações), no visual vinho/dourado.

Uso: python scripts/legendas_chamada.py PASTA config.json
config.json: {"correcoes": [["palavra errada", "CERTA"], ...], "juntar": [["finca","pé"], ["fim","-capé"]],
  "titulo_final": "ANOTA AÍ!", "destaque_endereco": "endereço", "destaque_data": ["dia", 25],
  "faixa": {"nome": "BAR DO CÉLIO", "endereco": "AV. ...<br>CAMPO GRANDE - MS", "data": "SÁBADO 12/12 · A PARTIR DAS 14H"}}
Lê PASTA/palavras.json (de cortar_pausas.py) e escreve PASTA/index.html e PASTA/compositions/legendas.html.
"""
import html, json, os, re, sys

pasta, cfgp = sys.argv[1:3]
cfg = json.load(open(cfgp)); P = json.load(open(f'{pasta}/palavras.json'))
D = P['duracao']; ws = [dict(w) for w in P['palavras']]

# junta pares (ex.: "Finca" + "Pé" -> FINCAPÉ), mantendo a pontuação final
fix, i = [], 0
while i < len(ws):
    w = ws[i]; done = False
    for a, b in cfg.get('juntar', []):
        if i + 1 < len(ws) and w['palavra'].lower().startswith(a) and ws[i + 1]['palavra'].lower().startswith(b):
            pont = re.findall(r'[,.!?]+$', ws[i + 1]['palavra'])
            fix.append({'palavra': 'FINCAPÉ' + (pont[0] if pont else ''), 'inicio': w['inicio'], 'fim': ws[i + 1]['fim']}); i += 2; done = True; break
    if done: continue
    for errado, certo in cfg.get('correcoes', []):
        base = re.sub(r'[,.!?]+$', '', w['palavra'])
        if base.lower() == errado.lower(): w['palavra'] = certo + w['palavra'][len(base):]
    fix.append(w); i += 1

CON = {'do', 'no', 'de', 'da', 'das', 'e', 'o', 'a', 'que', 'os', 'as', 'dos', 'na', 'pra', 'uma', 'um', 'para', 'pro'}
grupos, cur = [], []
MAXC = 20  # letras por grupo (cabe na largura da tela com 118 px)
txt = lambda g: ' '.join(re.sub(r'[,.!?]+$', '', w['palavra']) for w in g)
for k, w in enumerate(fix):
    if cur and len(txt(cur + [w])) > MAXC:
        grupos.append(cur); cur = []
    cur.append(w); base = re.sub(r'[,.!?]+$', '', w['palavra']).lower()
    prox = fix[k + 1]['palavra'].lower() if k + 1 < len(fix) else ''
    if re.search(r'[,.!?]$', w['palavra']) or (len(cur) >= 3 and base not in CON and not prox.startswith('hora')):
        grupos.append(cur); cur = []
if cur: grupos.append(cur)

out, js = [], []
for gi, g in enumerate(grupos):
    st = g[0]['inicio']
    en = min(grupos[gi + 1][0]['inicio'], g[-1]['fim'] + 0.6) if gi + 1 < len(grupos) else D
    spans = ' '.join(f'<span id="w{gi}_{k}">{html.escape(re.sub(r"[,.!?]+$", "", w["palavra"]).upper())}</span>' for k, w in enumerate(g))
    out.append(f'    <div id="g{gi}" class="clip grupo" data-start="{st:.2f}" data-duration="{en - st:.2f}" data-track-index="2"><div class="caixa" id="cx{gi}">{spans}</div></div>')
    js.append(f'      tl.fromTo("#cx{gi}", {{ scale: 0.82, opacity: 0, y: 18 }}, {{ scale: 1, opacity: 1, y: 0, duration: 0.16, ease: "back.out(2)" }}, {st:.2f});')
    for k, w in enumerate(g):
        js.append(f'      tl.set("#w{gi}_{k}", {{ className: "ativa" }}, {w["inicio"]:.2f});')
        if k < len(g) - 1: js.append(f'      tl.set("#w{gi}_{k}", {{ className: "" }}, {g[k + 1]["inicio"]:.2f});')

def achar(p, depois=0):
    for w in fix:
        if w['inicio'] >= depois and w['palavra'].lower().startswith(p): return w['inicio']
    raise SystemExit(f'palavra não achada: {p}')
t_end = achar(cfg['destaque_endereco'])
t_data = achar(cfg['destaque_data'][0], cfg['destaque_data'][1])
t_fim = fix[-1]['inicio'] if cfg.get('fim_na_ultima_frase') is None else achar(cfg['fim_na_ultima_frase'], D - 4)
F = cfg['faixa']
print(' | '.join(' '.join(w['palavra'] for w in g) for g in grupos))
print(f'endereco {t_end:.2f}  data {t_data:.2f}  final {t_fim:.2f}  duracao {D:.2f}')

pin = '<svg viewBox="0 0 24 32"><path fill="#e9cf8f" d="M12 0C5.4 0 0 5.2 0 11.7 0 20.5 12 32 12 32s12-11.5 12-20.3C24 5.2 18.6 0 12 0zm0 16.5a5 5 0 1 1 0-10 5 5 0 0 1 0 10z"/></svg>'
comp = f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; font-family: "League Gothic", "Oswald", sans-serif; }}
    .grupo {{ position: absolute; left: 0; top: 1170px; width: 1080px; height: 200px; display: flex; align-items: center; justify-content: center; }}
    .caixa {{ display: flex; gap: 34px; padding: 0 30px; font-size: 118px; line-height: 1; letter-spacing: 2px; color: #fff8ee; white-space: nowrap;
      text-shadow: 0 6px 0 #3a0710, 0 0 14px rgba(0,0,0,.85), 0 0 34px rgba(0,0,0,.6); }}
    .caixa span {{ display: inline-block; }}
    .caixa span.ativa {{ color: #f3d58f; transform: scale(1.08); text-shadow: 0 6px 0 #5a0b18, 0 0 22px rgba(200,32,47,.85), 0 0 40px rgba(200,32,47,.5); }}
    #faixa {{ position: absolute; left: 30px; top: 1430px; width: 1020px; height: 330px; border-radius: 26px; overflow: hidden;
      background: linear-gradient(180deg, rgba(122,15,31,.94), rgba(70,6,16,.96)); box-shadow: 0 18px 40px rgba(0,0,0,.55), inset 0 0 0 3px rgba(233,207,143,.9); }}
    #faixa .brilho {{ position: absolute; top: 0; left: -300px; width: 260px; height: 100%; background: linear-gradient(100deg, transparent, rgba(255,240,200,.35), transparent); }}
    #faixa .logo {{ position: absolute; left: 34px; top: 92px; width: 300px; height: 124px;
      -webkit-mask: url("assets/fincape.png") center / contain no-repeat; mask: url("assets/fincape.png") center / contain no-repeat;
      background: linear-gradient(180deg, #fff6dc, #e9cf8f 45%, #b88a3a); }}
    #faixa .div {{ position: absolute; left: 362px; top: 40px; width: 3px; height: 250px; background: linear-gradient(transparent, #e9cf8f, transparent); }}
    #faixa .info {{ position: absolute; left: 395px; top: 34px; width: 610px; }}
    #faixa .nome {{ font-size: 96px; line-height: .95; color: #f3d58f; letter-spacing: 2px; text-shadow: 0 4px 0 #2a0309; }}
    #faixa .end {{ font-family: "Oswald"; font-weight: 600; font-size: 31px; color: #fff8ee; letter-spacing: 1.5px; margin-top: 8px; line-height: 1.25; }}
    #faixa .data {{ display: inline-block; margin-top: 14px; padding: 6px 18px 4px; border-radius: 10px; background: #e9cf8f; color: #4a0711; font-size: 48px; letter-spacing: 2px; }}
    #faixa svg {{ width: 20px; height: 26px; vertical-align: -3px; margin-right: 8px; }}
    #fim {{ position: absolute; left: 0; top: 560px; width: 1080px; text-align: center; }}
    #fim .t {{ font-size: 230px; line-height: .9; color: #f3d58f; letter-spacing: 4px; text-shadow: 0 10px 0 #5a0b18, 0 0 40px rgba(200,32,47,.8), 0 0 90px rgba(200,32,47,.5); }}
    #flash {{ position: absolute; inset: 0; background: #fff4e8; mix-blend-mode: screen; }}
    #vinho {{ position: absolute; inset: 0; mix-blend-mode: multiply; background: radial-gradient(75% 60% at 50% 45%, rgba(255,255,255,1) 55%, rgba(150,40,55,1) 100%); opacity: .5; }}
  </style>
  <div id="root" data-composition-id="legendas" data-width="1080" data-height="1920" data-layout-allow-overlap data-layout-allow-overflow>
    <div id="vinho" data-layout-ignore></div>
{chr(10).join(out)}
    <div id="faixa">
      <div class="logo"></div><div class="div"></div>
      <div class="info">
        <div class="nome">{F["nome"]}</div>
        <div class="end" id="end">{pin}{F["endereco"]}</div>
        <div class="data" id="data">{F["data"]}</div>
      </div>
      <div class="brilho" id="brilho"></div>
    </div>
    <div id="fim"><div class="t" id="fim-t">{html.escape(cfg["titulo_final"])}</div></div>
    <div id="flash" data-layout-ignore></div>
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
      gsap.set(["#flash", "#fim"], {{ opacity: 0 }});
      tl.fromTo("#faixa", {{ y: 420, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.55, ease: "expo.out" }}, 0.15);
      tl.fromTo("#brilho", {{ x: 0 }}, {{ x: 1500, duration: 0.9, ease: "power2.inOut" }}, 0.5);
      tl.fromTo("#end", {{ scale: 1 }}, {{ scale: 1.06, duration: 0.2, ease: "power2.out", yoyo: true, repeat: 1, transformOrigin: "0% 50%" }}, {t_end:.2f});
      tl.fromTo("#brilho", {{ x: 0 }}, {{ x: 1500, duration: 0.9, ease: "power2.inOut", immediateRender: false }}, {t_end + 0.1:.2f});
      tl.to("#flash", {{ opacity: 0.7, duration: 0.05 }}, {t_data - 0.05:.2f});
      tl.to("#flash", {{ opacity: 0, duration: 0.3 }}, {t_data:.2f});
      tl.fromTo("#data", {{ scale: 1 }}, {{ scale: 1.12, duration: 0.18, ease: "power2.out", yoyo: true, repeat: 1, transformOrigin: "0% 50%" }}, {t_data + 0.4:.2f});
      tl.fromTo("#brilho", {{ x: 0 }}, {{ x: 1500, duration: 0.9, ease: "power2.inOut", immediateRender: false }}, {t_data + 0.4:.2f});
      tl.to("#flash", {{ opacity: 0.8, duration: 0.05 }}, {t_fim - 0.05:.2f});
      tl.to("#flash", {{ opacity: 0, duration: 0.35 }}, {t_fim:.2f});
      tl.fromTo("#fim", {{ opacity: 0, scale: 1.6, filter: "blur(18px)" }}, {{ opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.35, ease: "expo.out" }}, {t_fim:.2f});
{chr(10).join(js)}
      window.__timelines["legendas"] = tl;
    }})();
  </script>
</template>
'''
os.makedirs(f'{pasta}/compositions', exist_ok=True)
open(f'{pasta}/compositions/legendas.html', 'w').write(comp)
idx = f'''<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ width: 100%; height: 100%; }}
      #cam {{ position: absolute; inset: 0; transform-origin: 540px 800px; }}
      #cam video {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D:.2f}" data-width="1080" data-height="1920">
      <div id="cam"><video id="video" class="clip" src="assets/chamada.mp4" data-start="0" data-duration="{D:.2f}" data-track-index="0" data-has-audio="true" playsinline></video></div>
      <div id="legendas" data-composition-id="legendas" data-composition-src="compositions/legendas.html" data-start="0" data-duration="{D:.2f}"
        data-track-index="1" data-track-kind="graphics" data-width="1080" data-height="1920"></div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.to("#cam", {{ scale: 1.1, duration: 0.6, ease: "power2.inOut" }}, {t_end - 0.1:.2f});
      tl.to("#cam", {{ scale: 1.0, duration: 0.6, ease: "power2.inOut" }}, {t_end + 4.0:.2f});
      tl.set("#cam", {{ scale: 1.18 }}, {t_data - 0.05:.2f});
      tl.to("#cam", {{ scale: 1.05, duration: 1.2, ease: "power3.out" }}, {t_data:.2f});
      tl.to("#cam", {{ scale: 1.0, duration: 0.6, ease: "power2.inOut" }}, {t_data + 1.6:.2f});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
'''
open(f'{pasta}/index.html', 'w').write(idx)
