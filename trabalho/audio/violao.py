#!/usr/bin/env python3
"""Trata o violão (stem do Demucs) para soar como o playback de referência.

Cadeia: EQ casada com a referência -> compressão em 2 estágios -> dobra artificial (ADT) em estéreo
        -> reverb estéreo -> limitador -> correção fina de EQ (2ª passada, medindo o resultado).

Uso: python3 violao.py VIOLAO_STEM.wav REFERENCIA.wav SAIDA.wav
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

STEM, REF, SAIDA = sys.argv[1:4]
SR = 48000
TMP = Path(tempfile.mkdtemp())
BANDAS = [50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150,
          4000, 5000, 6300, 8000, 10000, 12500, 16000]


def ff(*args, entrada=None):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True, input=entrada)


def carregar(p, ch=1):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-ac", str(ch), "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(r, np.float32).reshape(-1, ch)


def salvar(p, x):
    ff("-f", "f32le", "-ar", str(SR), "-ac", str(x.shape[1]), "-i", "pipe:0", "-c:a", "pcm_f32le", str(p),
       entrada=x.astype("<f4").tobytes())


def perfil(x):
    x = x.mean(1)
    n = 8192
    w = np.hanning(n)
    s, k = 0, 0
    for i in range(0, len(x) - n, n // 2):
        seg = x[i:i + n]
        if np.sqrt(np.mean(seg ** 2)) < 3e-3:
            continue
        s = s + np.abs(np.fft.rfft(seg * w)) ** 2
        k += 1
    f = np.fft.rfftfreq(n, 1 / SR)
    s = s / k
    o = np.array([10 * np.log10(s[(f > b / 2 ** (1 / 6)) & (f < b * 2 ** (1 / 6))].mean() + 1e-20) for b in BANDAS])
    return o - o[[200 <= b <= 5000 for b in BANDAS]].mean()


def curva(alvo, atual, lim=9, lim_corte=9):
    d = alvo - atual
    d = np.convolve(np.pad(d, 1, mode="edge"), [0.25, 0.5, 0.25], "valid")
    d = np.clip(d, -lim_corte, lim)
    d[np.array(BANDAS) <= 63] = np.minimum(d[np.array(BANDAS) <= 63], 2)   # não levantar ruído de subgrave
    return d


def fireq(d):
    return ("firequalizer=gain_entry='" + ";".join(f"entry({b},{g:.1f})" for b, g in zip(BANDAS, d)) +
            "':gain='cubic_interpolate(f)'")


def dinamica(x):
    m = x.mean(1)
    n = SR // 10
    e = 20 * np.log10(np.sqrt(np.array([np.mean(m[i:i + n] ** 2) for i in range(0, len(m) - n, n)])) + 1e-9)
    e = e[e > e.max() - 40]
    return np.percentile(e, 95) - np.percentile(e, 10)


def correlacao(x):
    return np.corrcoef(x[:, 0], x[:, 1])[0, 1]


def adt(x, atraso_ms=19, prof_ms=2.2, seed=3):
    """Dobra artificial: cópia com atraso que varia lentamente (como uma segunda execução, levemente fora do tempo)."""
    n = len(x)
    rng = np.random.default_rng(seed)
    # ruído lento (~0.3-1 Hz) para variar o atraso
    pts = rng.uniform(-1, 1, n // (SR // 2) + 3)
    lento = np.interp(np.arange(n) / (SR // 2), np.arange(len(pts)), pts)
    atraso = (atraso_ms + prof_ms * lento) * SR / 1000
    idx = np.arange(n) - atraso
    i0 = np.clip(np.floor(idx).astype(int), 0, n - 1)
    fr = idx - np.floor(idx)
    i1 = np.clip(i0 + 1, 0, n - 1)
    y = x[i0] * (1 - fr) + x[i1] * fr
    y[idx < 0] = 0
    return y


ref = carregar(REF, 2)
alvo = perfil(ref)

# 1) EQ casada + compressão em 2 estágios (mono)
cru = carregar(STEM, 1)
salvar(TMP / "cru.wav", cru)
eq1 = fireq(curva(alvo, perfil(cru)))
ff("-i", str(TMP / "cru.wav"), "-af",
   "highpass=f=90,highpass=f=90,highpass=f=80," + eq1 +
   ",acompressor=threshold=-36dB:ratio=4:attack=20:release=180:knee=6:makeup=6"
   ",acompressor=threshold=-24dB:ratio=4:attack=6:release=90:knee=4:makeup=4",
   str(TMP / "comp.wav"))
comp = carregar(TMP / "comp.wav", 1)[:, 0]

# 2) estéreo M/S: meio = execução original; lados = dobra artificial (só acima de 200 Hz).
#    L = M + S, R = M - S -> somando em mono (alto-falante do celular) os lados se cancelam e sobra o violão intacto.
LARGURA = 1.3
dobra = adt(comp)
salvar(TMP / "dobra.wav", dobra[:, None])
ff("-i", str(TMP / "dobra.wav"), "-af",
   "equalizer=f=900:t=o:w=1.5:g=-1.5,equalizer=f=3000:t=o:w=1:g=1,highpass=f=200,highpass=f=200",
   str(TMP / "lados.wav"))
lados = carregar(TMP / "lados.wav", 1)[:, 0] * LARGURA
est = np.stack([comp + lados, comp - lados], 1)
salvar(TMP / "estereo.wav", est)

# 3) reverb estéreo (placa sintética) + limitador
n = int(1.4 * SR)
t = np.arange(n) / SR
rng = np.random.default_rng(11)
ir = rng.standard_normal((n, 2)) * np.exp(-6.91 * t / 1.2)[:, None]
ir = np.vstack([np.zeros((int(0.025 * SR), 2)), ir])
salvar(TMP / "ir_raw.wav", ir / np.abs(ir).max() * 0.5)
ff("-i", str(TMP / "ir_raw.wav"), "-af", "highpass=f=300,lowpass=f=6000", str(TMP / "ir.wav"))
ff("-i", str(TMP / "estereo.wav"), "-i", str(TMP / "ir.wav"), "-filter_complex",
   "[0:a]asplit[a][b];[b][1:a]afir=dry=0:wet=1,volume=-17dB[r];[a][r]amix=inputs=2:normalize=0,"
   "alimiter=limit=0.7:attack=2:release=50:level=false", str(TMP / "pre.wav"))

# 4) correção fina: mede o resultado e acerta o que sobrou da curva
pre = carregar(TMP / "pre.wav", 2)
eq2 = fireq(curva(alvo, perfil(pre), lim=4, lim_corte=9))
ff("-i", str(TMP / "pre.wav"), "-af", eq2 + ",alimiter=limit=0.7:attack=2:release=50:level=false", "-c:a", "pcm_f32le", SAIDA)

fim = carregar(SAIDA, 2)
print(f"dinâmica {dinamica(fim):.1f} dB (ref {dinamica(ref):.1f}) | correlação L/R {correlacao(fim):.2f} (ref {correlacao(ref):.2f})")
print("dif. timbre vs ref (dB): " + " ".join(f"{b}:{d:+.1f}" for b, d in zip(BANDAS, perfil(fim) - alvo)))
