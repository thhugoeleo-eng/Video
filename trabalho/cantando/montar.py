#!/usr/bin/env python3
"""Legenda palavra por palavra (estilo da referência) + zoom suave por frase.
Gera legenda.ass e zoom.txt (expressão do zoompan) a partir da transcrição."""
import json, re
from pathlib import Path

AQUI = Path(__file__).parent
d = json.load(open(AQUI / 'A001_11181550_C190.transcricao.json'))
fr = d['frases'] if isinstance(d, dict) else d
ws = [dict(w) for f in fr for w in f['palavras']]

# correções da letra: "sogrão e..." -> "sobrenome" (o Whisper errou)
for i, w in enumerate(ws):
    if w['palavra'].lower().startswith('sogrão'):
        w['palavra'] = 'sobrenome'; w['fim'] = ws[i + 1]['fim']; del ws[i + 1]; break

limpa = lambda s: re.sub(r'[,.!?…]+$', '', s).upper()
# linhas curtas como na referência (índices de início de cada linha, pelo texto)
LINHAS = ["EU SEI QUE VOCÊ PODERIA", "SÓ PEDIR ELA EM NAMORO", "MAS MANDA ESSA AQUI PRA ELA",
          "EU TROCO MINHA PAZ", "POR UM BEIJO SEU", "EU TROCO MEU DESTINO", "PRA VIVER NO SEU",
          "EU TROCO MINHA CAMA", "PRA DORMIR NA SUA", "EU TROCO MIL ESTRELAS", "PRA TE DAR A LUA",
          "E TUDO QUE VOCÊ QUISER", "E SE VOCÊ QUISER", "TE DOU MEU SOBRENOME"]
grupos, k = [], 0
for linha in LINHAS:
    n = len(linha.split()); g = ws[k:k + n]
    assert ' '.join(limpa(w['palavra']) for w in g) == linha, (linha, [w['palavra'] for w in g])
    grupos.append(g); k += n
assert k == len(ws)

def ts(t):
    cs = int(round(t * 100)); h, r = divmod(cs, 360000); m, r = divmod(r, 6000); s, c = divmod(r, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"

ev = []
for gi, g in enumerate(grupos):
    st = g[0]['inicio'] - 0.05
    en = min(grupos[gi + 1][0]['inicio'] - 0.05, g[-1]['fim'] + 0.8) if gi + 1 < len(grupos) else g[-1]['fim'] + 0.6
    partes = []
    for w in g:
        a = int((w['inicio'] - st) * 1000)
        partes.append(f"{{\\alpha&HFF&\\t({a},{a + 220},\\alpha&H00&)}}{limpa(w['palavra'])}")
    ev.append(f"Dialogue: 0,{ts(st)},{ts(en)},Leg,,0,0,0,,{{\\fad(0,180)}}" + ' '.join(partes))

ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Leg,Gloria Hallelujah,50,&H00FFFFFF,&H00FFFFFF,&H90000000,&H80000000,0,0,0,0,100,100,2,0,1,1.6,2,2,60,60,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + '\n'.join(ev) + '\n'
(AQUI / 'legenda.ass').write_text(ass)

# zoom: a cada linha da música o enquadramento desliza para um novo zoom (suave, 1,2 s)
alvos = [1.00, 1.10, 1.04, 1.14, 1.06, 1.16, 1.08, 1.12, 1.03, 1.15, 1.07, 1.18, 1.10, 1.22]
z, termos = alvos[0], []
for g, alvo in zip(grupos[1:], alvos[1:]):
    t0 = g[0]['inicio'] - 0.3; dz = alvo - z; z = alvo
    s = f"clip((it-{t0:.2f})/1.2,0,1)"
    termos.append(f"{dz:+.3f}*{s}*{s}*(3-2*{s})")
(AQUI / 'zoom.txt').write_text(f"{alvos[0]}" + ''.join(termos))
print(len(grupos), 'linhas; zoom final', z)
