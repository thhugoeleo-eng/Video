#!/usr/bin/env python3
"""Pipeline em 3 etapas, cada uma casada com a sua referência e medida no fim:
  1) violão  -> playback de referência (EQ, compressão, estéreo Haas, reverb, limitador)
  2) voz     -> voz da mix de referência (EQ, de-esser, compressão, reverb)
  3) mix     -> mix de referência (equilíbrio, compressão de cola, EQ do master, limitador)

Uso: python3 pipeline.py VOZ_STEM VIOLAO_STEM REF_VIOLAO REF_VOZ REF_MIX PASTA_SAIDA
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

VOZ, VIO, REF_VIO, REF_VOZ, REF_MIX, OUT = sys.argv[1:7]
OUT = Path(OUT)
OUT.mkdir(parents=True, exist_ok=True)
SR = 48000
ALVO_LUFS = -11.5
BANDAS = [50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150,
          4000, 5000, 6300, 8000, 10000, 12500, 16000]
B = np.array(BANDAS)


# ---------- utilidades ----------
def ff(*args, entrada=None):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True, input=entrada)


def carregar(p, ch=2):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-ac", str(ch), "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(r, np.float32).reshape(-1, ch)


def salvar(p, x):
    ff("-f", "f32le", "-ar", str(SR), "-ac", str(x.shape[1]), "-i", "pipe:0", "-c:a", "pcm_f32le", str(p),
       entrada=x.astype("<f4").tobytes())


def lufs(p):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float([l for l in r.splitlines() if l.strip().startswith("I:")][-1].split()[1])


def perfil(x):
    x = x.mean(1)
    n, w = 8192, np.hanning(8192)
    s, k = 0, 0
    for i in range(0, len(x) - n, n // 2):
        seg = x[i:i + n]
        if np.sqrt(np.mean(seg ** 2)) < 3e-3:
            continue
        s, k = s + np.abs(np.fft.rfft(seg * w)) ** 2, k + 1
    f = np.fft.rfftfreq(n, 1 / SR)
    o = np.array([10 * np.log10((s / k)[(f > b / 2 ** (1 / 6)) & (f < b * 2 ** (1 / 6))].mean() + 1e-20) for b in BANDAS])
    return o - o[(B >= 200) & (B <= 5000)].mean()


def dinamica(x):
    m = x.mean(1)
    n = SR // 10
    e = 20 * np.log10(np.sqrt(np.array([np.mean(m[i:i + n] ** 2) for i in range(0, len(m) - n, n)])) + 1e-9)
    e = e[e > e.max() - 40]
    return np.percentile(e, 95) - np.percentile(e, 10)


def curva(alvo, atual, sobe=9, desce=9, limites=()):
    """Diferença suavizada alvo-atual; limites = [(freq_max, ganho_max), ...] para reforços."""
    # suavização de ~2/3 de oitava: casa o timbre, não as notas da música de referência (outra música, outro tom)
    d = np.convolve(np.pad(alvo - atual, 2, mode="edge"), np.array([1, 2, 3, 2, 1]) / 9, "valid")
    d = np.clip(d, -desce, sobe)
    for fmax, gmax in limites:
        d[B <= fmax] = np.minimum(d[B <= fmax], gmax)
    return d


def eq_arquivo(entrada, saida, d, taps=8191):
    """EQ de fase linear feita em numpy: curva interpolada em escala log de frequência (sem ondulação),
    filtro FIR por amostragem em frequência, atraso compensado (fica sincronizado com o vídeo)."""
    canais = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=channels",
                                 "-of", "csv=p=0", str(entrada)], capture_output=True, text=True).stdout.strip())
    x = carregar(entrada, canais)
    f = np.fft.rfftfreq(taps * 4, 1 / SR)
    lf = np.log10(np.maximum(f, 20))
    g_db = np.interp(lf, np.log10(B), d, left=d[0], right=d[-1])
    h = np.fft.irfft(10 ** (g_db / 20))
    h = np.roll(h, taps // 2)[:taps] * np.hanning(taps)
    n = len(x) + taps
    nfft = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft, axis=0) * np.fft.rfft(h, nfft)[:, None], nfft, axis=0)
    salvar(saida, y[taps // 2: taps // 2 + len(x)])


def ir_reverb(p, rt60=1.3, predelay=0.022, seed=7):
    n = int(1.5 * SR)
    t = np.arange(n) / SR
    ir = np.random.default_rng(seed).standard_normal((n, 2)) * np.exp(-6.91 * t / rt60)[:, None]
    ir = np.vstack([np.zeros((int(predelay * SR), 2)), ir])
    salvar(OUT / "ir_raw.wav", ir / np.abs(ir).max() * 0.5)
    ff("-i", str(OUT / "ir_raw.wav"), "-af", "highpass=f=350,lowpass=f=6500", str(p))


def relatorio(nome, x, ref):
    d = np.convolve(np.pad(perfil(x) - perfil(ref), 2, mode="edge"), np.array([1, 2, 3, 2, 1]) / 9, "valid")
    sel = (B >= 100) & (B <= 12500)
    print(f"[{nome}] dinâmica {dinamica(x):.1f} dB (ref {dinamica(ref):.1f}) | "
          f"maior diferença de timbre 100Hz-12k: {np.abs(d[sel]).max():.1f} dB | média {np.abs(d[sel]).mean():.1f} dB")
    print("   " + " ".join(f"{b}:{v:+.1f}" for b, v in zip(BANDAS, d)))


def escolher_compressao(entrada, cadeia_pre, alvo_dyn, opcoes, saida):
    """Testa ajustes de compressão e fica com o que chega mais perto da dinâmica da referência."""
    melhor = None
    for thr, ratio in opcoes:
        tmp = OUT / f"try_{thr}_{ratio}.wav"
        ff("-i", str(entrada), "-af", cadeia_pre +
           f",acompressor=threshold={thr}dB:ratio={ratio}:attack=12:release=160:knee=6:makeup=2", str(tmp))
        dd = abs(dinamica(carregar(tmp)) - alvo_dyn)
        if melhor is None or dd < melhor[0]:
            melhor = (dd, tmp, thr, ratio)
    Path(melhor[1]).replace(saida)
    for f in OUT.glob("try_*.wav"):
        f.unlink()
    return melhor[2], melhor[3]


ref_vio, ref_voz, ref_mix = carregar(REF_VIO), carregar(REF_VOZ), carregar(REF_MIX)
ir = OUT / "ir.wav"
ir_reverb(ir)

# ---------- 1) violão ----------
vio = carregar(VIO, 1)
salvar(OUT / "vio_cru.wav", vio)
ff("-i", str(OUT / "vio_cru.wav"), "-af", "highpass=f=70,highpass=f=70", "-c:a", "pcm_f32le", str(OUT / "vio_hp.wav"))
eq_arquivo(OUT / "vio_hp.wav", OUT / "vio_eq.wav",
           curva(perfil(ref_vio), perfil(carregar(OUT / "vio_hp.wav")), sobe=8, desce=9, limites=[(80, 0)]))
thr, ratio = escolher_compressao(OUT / "vio_eq.wav", "anull", dinamica(ref_vio) + 2,
                                 [(-30, 2), (-32, 3), (-34, 3), (-36, 4), (-38, 4)], OUT / "vio_comp.wav")
# estéreo como na B2 (Haas 13 ms) + reverb leve
ff("-i", str(OUT / "vio_comp.wav"), "-i", str(ir), "-filter_complex",
   "[0:a]asplit=3[a][b][c];[b]adelay=13,volume=-1dB[bd];[a][bd]join=inputs=2:channel_layout=stereo[w];"
   "[c]pan=stereo|c0=c0|c1=c0[cs];[cs][1:a]afir=dry=0:wet=1,volume=-19dB[r];"
   "[w][r]amix=inputs=2:normalize=0:duration=first", str(OUT / "vio_pre.wav"))
eq_arquivo(OUT / "vio_pre.wav", OUT / "vio_pre_eq.wav",
           curva(perfil(ref_vio), perfil(carregar(OUT / "vio_pre.wav")), sobe=6, desce=6, limites=[(80, 0)]))
ff("-i", str(OUT / "vio_pre_eq.wav"), "-af", "alimiter=limit=0.8:attack=3:release=60:level=false",
   "-c:a", "pcm_f32le", str(OUT / "1_violao.wav"))
print(f"violão: compressão {thr} dB / {ratio}:1")
relatorio("1 violão x playback", carregar(OUT / "1_violao.wav"), ref_vio)

# ---------- 2) voz ----------
voz = carregar(VOZ, 1)
salvar(OUT / "voz_cru.wav", voz)
# sem reforço abaixo de 100 Hz e no máximo +3 dB até 250 Hz (a referência é AAC com vazamento de violão)
ff("-i", str(OUT / "voz_cru.wav"), "-af", "highpass=f=90:p=2", "-c:a", "pcm_f32le", str(OUT / "voz_hp.wav"))
eq_arquivo(OUT / "voz_hp.wav", OUT / "voz_eq.wav",
           curva(perfil(ref_voz), perfil(carregar(OUT / "voz_hp.wav")), sobe=5, desce=9, limites=[(100, 0), (250, 3)]))
thr, ratio = escolher_compressao(OUT / "voz_eq.wav", "deesser=i=0.4:f=0.5", dinamica(ref_voz),
                                 [(-20, 2), (-22, 3), (-24, 3), (-24, 4), (-26, 4)], OUT / "voz_comp.wav")
ff("-i", str(OUT / "voz_comp.wav"), "-i", str(ir), "-filter_complex",
   "[0:a]pan=mono|c0=c0,asplit[a][b];[a]pan=stereo|c0=c0|c1=c0[d];[b]pan=stereo|c0=c0|c1=c0[bs];"
   "[bs][1:a]afir=dry=0:wet=1,volume=-15dB[r];[d][r]amix=inputs=2:normalize=0:duration=first",
   "-c:a", "pcm_f32le", str(OUT / "2_voz.wav"))
print(f"voz: compressão {thr} dB / {ratio}:1")
relatorio("2 voz x voz da referência", carregar(OUT / "2_voz.wav"), ref_voz)

# ---------- 3) mix + master ----------
gv = -18 - lufs(OUT / "2_voz.wav")
gg = -18 - 3.4 - lufs(OUT / "1_violao.wav")        # voz 3,4 LU acima do violão, como na mix de referência
ff("-i", str(OUT / "2_voz.wav"), "-i", str(OUT / "1_violao.wav"), "-filter_complex",
   f"[0:a]volume={gv:.2f}dB[v];[1:a]volume={gg:.2f}dB[g];[v][g]amix=inputs=2:normalize=0:duration=first,"
   "acompressor=threshold=-20dB:ratio=2:attack=30:release=250:makeup=1", "-c:a", "pcm_f32le", str(OUT / "mix_pre.wav"))
ff("-i", str(OUT / "mix_pre.wav"), "-af", "highpass=f=35", "-c:a", "pcm_f32le", str(OUT / "mix_hp.wav"))
eq_arquivo(OUT / "mix_hp.wav", OUT / "mix_eq.wav",
           curva(perfil(ref_mix), perfil(carregar(OUT / "mix_hp.wav")), sobe=3, desce=4, limites=[(80, 0)]))
ganho = ALVO_LUFS - lufs(OUT / "mix_eq.wav")
ff("-i", str(OUT / "mix_eq.wav"), "-af",
   f"volume={ganho:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=false", "-c:a", "pcm_f32le",
   str(OUT / "3_mix_master.wav"))
relatorio("3 mix x mix de referência", carregar(OUT / "3_mix_master.wav"), ref_mix)
print(f"volume final {lufs(OUT / '3_mix_master.wav'):.1f} LUFS")
