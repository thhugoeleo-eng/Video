#!/usr/bin/env python3
"""Remove o fundo de fotos localmente com BiRefNet (licença MIT).

Uso: python scripts/recortar.py ENTRADA.jpg [mais arquivos...] [--saida PASTA]
Gera <nome>_recorte.png (fundo transparente) na pasta de saída (padrão: a mesma da foto).
Modelo: /opt/models/birefnet_lite.onnx (baixe de huggingface.co/onnx-community/BiRefNet_lite-ONNX).
"""
import argparse
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

MODELO = "/opt/models/birefnet_lite.onnx"


def recortar(sess, caminho: Path, saida: Path) -> Path:
    im = Image.open(caminho).convert("RGB")
    x = np.asarray(im.resize((1024, 1024), Image.BILINEAR), dtype=np.float32) / 255.0
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    y = sess.run(None, {sess.get_inputs()[0].name: x})[0][0, 0]
    mask = 1 / (1 + np.exp(-y))  # sigmoid
    alpha = Image.fromarray((mask * 255).clip(0, 255).astype(np.uint8)).resize(im.size, Image.LANCZOS)
    out = im.convert("RGBA")
    out.putalpha(alpha)
    out = out.crop(alpha.point(lambda v: 255 if v > 8 else 0).getbbox())
    destino = saida / f"{caminho.stem}_recorte.png"
    out.save(destino)
    return destino


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivos", nargs="+")
    ap.add_argument("--saida")
    a = ap.parse_args()
    sess = ort.InferenceSession(MODELO, providers=["CPUExecutionProvider"])
    for f in a.arquivos:
        p = Path(f)
        print(recortar(sess, p, Path(a.saida) if a.saida else p.parent))


if __name__ == "__main__":
    main()
