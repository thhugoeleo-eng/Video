#!/usr/bin/env python3
"""Corta um vídeo mantendo só os trechos indicados e gera a transcrição remapeada.

Uso: python scripts/cortar_pausas.py ORIGEM.mov TRANSCRICAO.json SAIDA_DIR "0-1.36,1.88-10.5,..."
Gera SAIDA_DIR/assets/chamada.mp4 (1080x1920, 30 fps, com áudio, microfades nas emendas)
e SAIDA_DIR/palavras.json (palavras do original com os tempos já no vídeo cortado).
"""
import json, os, subprocess, sys

orig, transc, out, spec = sys.argv[1:5]
keep = [tuple(float(x) for x in seg.split('-')) for seg in spec.split(',')]
os.makedirs(f'{out}/assets', exist_ok=True)
n = len(keep)
f = [f"[0:v]scale=1080:1920,fps=30,eq=contrast=1.06:saturation=1.06,split={n}" + ''.join(f'[v{i}]' for i in range(n)) + ';',
     f"[0:a]asplit={n}" + ''.join(f'[a{i}]' for i in range(n)) + ';']
for i, (a, b) in enumerate(keep):
    f.append(f"[v{i}]trim={a}:{b},setpts=PTS-STARTPTS[s{i}];[a{i}]atrim={a}:{b},asetpts=PTS-STARTPTS,"
             f"afade=t=in:d=0.02,afade=t=out:st={b - a - 0.02:.3f}:d=0.02[t{i}];")
f.append(''.join(f'[s{i}][t{i}]' for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', orig, '-filter_complex', ''.join(f), '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart', f'{out}/assets/chamada.mp4'], check=True)

def novo(t):
    acc = 0.0
    for a, b in keep:
        if t < a: return None
        if t <= b: return acc + (t - a)
        acc += b - a
    return None

d = json.load(open(transc))
pal = []
for fr in d['frases']:
    for w in fr['palavras']:
        s, e = novo(w['inicio']), novo(w['fim'])
        if s is not None:
            pal.append({'palavra': w['palavra'], 'inicio': round(s, 3), 'fim': round(e if e is not None else s + 0.2, 3)})
dur = sum(b - a for a, b in keep)
json.dump({'duracao': round(dur, 3), 'palavras': pal}, open(f'{out}/palavras.json', 'w'), ensure_ascii=False, indent=1)
print(f'ok: {dur:.2f}s, {len(pal)} palavras')
