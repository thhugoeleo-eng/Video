#!/usr/bin/env python3
"""Mixa e masteriza voz + violão (stems separados pelo Demucs) seguindo as referências.

Uso: python3 mixar.py VOZ.wav VIOLAO.wav CURVAS.json PREFIXO SAIDA.wav
  CURVAS.json: saída da análise (bandas + curvas "<PREFIXO>_voz" e "<PREFIXO>_gtr" em dB)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

VOZ, VIO, CURVAS, PREF, SAIDA = sys.argv[1:6]
SR = 48000
VOZ_ACIMA_DO_VIOLAO = 3.4   # LU, medido na mix de referência
ALVO_LUFS = -11.5
TMP = Path(tempfile.mkdtemp())


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def lufs(p):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    linhas = [l for l in r.splitlines() if l.strip().startswith("I:")]
    return float(linhas[-1].split()[1])


def eq(chave, lim_baixo=None):
    c = json.load(open(CURVAS))
    pts = []
    for f, g in zip(c["bandas"], c[chave]):
        if lim_baixo:
            for fmax, gmax in lim_baixo:
                if f <= fmax:
                    g = min(g, gmax)
                    break
        pts.append(f"entry({f},{g:.1f})")
    return "firequalizer=gain_entry='" + ";".join(pts) + "':gain='cubic_interpolate(f)'"


def reverb_ir(p, dur=1.5, predelay=0.022, rt60=1.3):
    """Reverb de placa sintético: ruído estéreo descorrelacionado com decaimento exponencial."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.exp(-6.91 * t / rt60)
    rng = np.random.default_rng(7)
    ir = rng.standard_normal((n, 2)) * env[:, None]
    ir = np.vstack([np.zeros((int(predelay * SR), 2)), ir])
    ir /= np.abs(ir).max()
    raw = (ir * 0.5).astype("<f4").tobytes()
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2",
                    "-i", "pipe:0", "-af", "highpass=f=350,lowpass=f=6500", str(p)], input=raw, check=True)


ir = TMP / "ir.wav"
reverb_ir(ir)

# Voz: sem reforço de grave abaixo de 100 Hz e no máximo +3 dB até 250 Hz (a referência é AAC com vazamento de violão)
voz_eq = eq(f"{PREF}_voz", lim_baixo=[(100, 0), (250, 3), (20000, 5)])
ff("-i", VOZ, "-af",
   "pan=mono|c0=0.5*c0+0.5*c1,aresample=48000,highpass=f=90:p=2," + voz_eq +
   ",deesser=i=0.4:f=0.5,acompressor=threshold=-24dB:ratio=4:attack=5:release=90:makeup=4,"
   "acompressor=threshold=-14dB:ratio=2:attack=15:release=200", str(TMP / "voz_seca.wav"))
# Violão: curva da referência limitada a ±6 dB, compressão leve
vio_eq = eq(f"{PREF}_gtr", lim_baixo=[(20000, 6)])
ff("-i", VIO, "-af",
   "pan=mono|c0=0.5*c0+0.5*c1,aresample=48000,highpass=f=60:p=2," + vio_eq +
   ",acompressor=threshold=-30dB:ratio=2.5:attack=20:release=220:makeup=3", str(TMP / "vio_seco.wav"))

# Equilíbrio: voz VOZ_ACIMA_DO_VIOLAO LU acima do violão
gv = -18 - lufs(TMP / "voz_seca.wav")
gg = -18 - VOZ_ACIMA_DO_VIOLAO - lufs(TMP / "vio_seco.wav")

ff("-i", str(TMP / "voz_seca.wav"), "-i", str(TMP / "vio_seco.wav"), "-i", str(ir), "-filter_complex",
   f"[0:a]volume={gv:.2f}dB,asplit[v1][v2];"
   f"[1:a]volume={gg:.2f}dB,asplit=3[g1][g2][g3];"
   "[2:a]asplit[ir1][ir2];"
   # voz no centro + reverb estéreo
   "[v1]pan=stereo|c0=c0|c1=c0[vc];"
   "[v2]pan=stereo|c0=c0|c1=c0[vs];[vs][ir1]afir=dry=0:wet=1[vr];[vr]volume=-15dB[vrev];"
   # violão aberto: esquerdo direto, direito atrasado (Haas) + reverb
   "[g2]adelay=13,volume=-1dB[gd];[g1][gd]join=inputs=2:channel_layout=stereo[gw];"
   "[g3]pan=stereo|c0=c0|c1=c0[gs];[gs][ir2]afir=dry=0:wet=1[gr];[gr]volume=-19dB[grev];"
   "[vc][vrev][gw][grev]amix=inputs=4:normalize=0[mix];"
   # master: cola, brilho leve, limitador
   "[mix]acompressor=threshold=-20dB:ratio=2:attack=30:release=250:makeup=1,"
   "highshelf=f=10000:g=1[m]", "-map", "[m]", "-ar", "48000", str(TMP / "mix.wav"))

ganho = ALVO_LUFS - lufs(TMP / "mix.wav")
ff("-i", str(TMP / "mix.wav"), "-af",
   f"volume={ganho:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=false", "-ar", "48000", SAIDA)
print(f"{SAIDA}: {lufs(SAIDA):.1f} LUFS")
