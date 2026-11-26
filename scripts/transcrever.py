#!/usr/bin/env python3
"""Transcreve um vídeo/áudio com Whisper (faster-whisper), localmente e de graça.

Uso:
    python scripts/transcrever.py [ARQUIVO] [--modelo small] [--idioma pt] [--saida trabalho]

Sem ARQUIVO, usa o vídeo mais recente da pasta bruto/.
Gera em trabalho/:
    <nome>.transcricao.txt   -> uma frase por linha, com [início --> fim]
    <nome>.transcricao.json  -> frases com tempos e palavras com tempos (para cortes precisos)
"""
import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXTENSOES = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".mp3", ".wav", ".m4a", ".aac", ".flac"}


def tempo(seg: float) -> str:
    h, resto = divmod(seg, 3600)
    m, s = divmod(resto, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def escolher_arquivo(arg: str | None) -> Path:
    if arg:
        p = Path(arg)
        if not p.is_absolute():
            p = (Path.cwd() / p) if (Path.cwd() / p).exists() else RAIZ / arg
        if not p.exists():
            sys.exit(f"Arquivo não encontrado: {arg}")
        return p
    candidatos = [p for p in (RAIZ / "bruto").iterdir() if p.suffix.lower() in EXTENSOES]
    if not candidatos:
        sys.exit("Nenhum vídeo encontrado em bruto/. Coloque o arquivo lá e rode de novo.")
    return max(candidatos, key=lambda p: p.stat().st_mtime)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo", nargs="?")
    ap.add_argument("--modelo", default="small", help="tiny, base, small, medium, large-v3 (padrão: small)")
    ap.add_argument("--idioma", default="pt")
    ap.add_argument("--saida", default=str(RAIZ / "trabalho"))
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    entrada = escolher_arquivo(args.arquivo)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    print(f"Transcrevendo {entrada.name} com o modelo '{args.modelo}' ({args.idioma})...", flush=True)
    inicio = time.time()
    modelo = WhisperModel(args.modelo, device="cpu", compute_type="int8")
    segmentos, info = modelo.transcribe(
        str(entrada),
        language=args.idioma,
        word_timestamps=True,
        vad_filter=False,  # mantém as pausas visíveis nos tempos, para o plano de edição
        condition_on_previous_text=False,  # evita repetir frases em trechos de silêncio
    )

    frases = []
    for i, s in enumerate(segmentos, 1):
        texto = s.text.strip()
        if not texto:
            continue
        frases.append({
            "id": i,
            "inicio": round(s.start, 3),
            "fim": round(s.end, 3),
            "texto": texto,
            "palavras": [
                {"inicio": round(w.start, 3), "fim": round(w.end, 3), "palavra": w.word.strip()}
                for w in (s.words or [])
            ],
        })
        print(f"  [{tempo(s.start)} --> {tempo(s.end)}] {texto}", flush=True)

    arq_json = saida / f"{entrada.stem}.transcricao.json"
    arq_txt = saida / f"{entrada.stem}.transcricao.txt"
    dados = {
        "arquivo": str(entrada.relative_to(RAIZ)) if entrada.is_relative_to(RAIZ) else str(entrada),
        "idioma": info.language,
        "duracao": round(info.duration, 3),
        "modelo": args.modelo,
        "frases": frases,
    }
    arq_json.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    arq_txt.write_text(
        "".join(f"[{tempo(f['inicio'])} --> {tempo(f['fim'])}] {f['texto']}\n" for f in frases),
        encoding="utf-8",
    )
    print(f"\nPronto em {time.time() - inicio:.0f}s: {len(frases)} frases.")
    print(f"  {arq_txt}")
    print(f"  {arq_json}")


if __name__ == "__main__":
    main()
