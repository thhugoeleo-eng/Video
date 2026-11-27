#!/usr/bin/env python3
"""Zoom suave (subpixel) para o cover: lê o vídeo, aplica o zoom e devolve quadros 1080x1920 crus em stdout.

Uso: python3 zoom_suave.py ENTRADA DURACAO [CONFIG.json] | ffmpeg -f rawvideo -pix_fmt bgr24 -s 1080x1920 -r 30 -i - ...
"""
import json
import subprocess
import sys

import cv2
import numpy as np

ENT, DUR = sys.argv[1], float(sys.argv[2])
SW, SH = 2160, 3840          # vídeo de origem (vertical)
OW, OH = 1080, 1920          # saída
FPS = 30

# (início, fim, zoom inicial, zoom final) — suavizado com smoothstep; saltos entre trechos são intencionais
TRECHOS = [(0, 5.1, 1.00, 1.08), (5.2, 11.6, 1.00, 1.08), (11.66, 17.6, 1.14, 1.18),
           (17.68, 18.6, 1.18, 1.04), (18.6, 21.0, 1.04, 1.04), (21.0, 23.3, 1.04, 1.10),
           (23.32, 27.4, 1.10, 1.25), (27.4, 99, 1.25, 1.25)]


INICIO = 0.0   # segundos cortados do começo do vídeo de origem
CX_FIXO = None
if len(sys.argv) > 3:
    cfg = json.load(open(sys.argv[3]))
    TRECHOS = [tuple(x) for x in cfg["trechos"]]
    INICIO = cfg.get("inicio", 0.0)
    CX_FIXO = cfg.get("centro_x")


def suave(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def zoom(t):
    for a, b, z0, z1 in TRECHOS:
        if t < b:
            return z0 + (z1 - z0) * suave((t - a) / (b - a))
    return TRECHOS[-1][3]


def centro_x(t):
    if CX_FIXO is not None:
        return CX_FIXO
    return 0.5 if t < 23.32 else 0.5 - 0.08 * suave((t - 23.32) / 4.08)


dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(INICIO), "-t", str(DUR), "-i", ENT, "-vf", f"scale={SW}:{SH}",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
tam = SW * SH * 3
out = sys.stdout.buffer
n = 0
while True:
    buf = dec.stdout.read(tam)
    if len(buf) < tam:
        break
    img = np.frombuffer(buf, np.uint8).reshape(SH, SW, 3)
    t = n / FPS
    z = zoom(t)
    cw, ch = SW / z, SH / z
    x0, y0 = (SW - cw) * centro_x(t), (SH - ch) * 0.4
    m = np.float32([[z, 0, -x0 * z], [0, z, -y0 * z]])
    grande = cv2.warpAffine(img, m, (SW, SH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    out.write(cv2.resize(grande, (OW, OH), interpolation=cv2.INTER_AREA).tobytes())
    n += 1
dec.wait()
