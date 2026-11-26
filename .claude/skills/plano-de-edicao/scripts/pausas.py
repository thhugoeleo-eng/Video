#!/usr/bin/env python3
"""Lista pausas longas e frases repetidas numa transcrição (trabalho/*.transcricao.json).

Uso: python pausas.py TRANSCRICAO.json [--pausa 1.2]

Imprime JSON com:
  pausas:     intervalos sem fala maiores que --pausa segundos (entre palavras)
  repeticoes: pares de frases próximas muito parecidas (provável retomada/erro de gravação)
É só um ponto de partida: quem decide os cortes é a leitura do conteúdo.
"""
import argparse
import json
import re
from difflib import SequenceMatcher


def norm(t: str) -> str:
    return re.sub(r"[^\w\s]", "", t.lower()).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("transcricao")
    ap.add_argument("--pausa", type=float, default=1.2)
    a = ap.parse_args()
    d = json.load(open(a.transcricao, encoding="utf-8"))
    frases = d["frases"]

    palavras = [w for f in frases for w in (f.get("palavras") or [])] or [
        {"inicio": f["inicio"], "fim": f["fim"]} for f in frases
    ]
    pausas = []
    if palavras and palavras[0]["inicio"] > a.pausa:
        pausas.append({"inicio": 0.0, "fim": palavras[0]["inicio"], "duracao": round(palavras[0]["inicio"], 2), "onde": "início"})
    for p, q in zip(palavras, palavras[1:]):
        gap = q["inicio"] - p["fim"]
        if gap >= a.pausa:
            pausas.append({"inicio": p["fim"], "fim": q["inicio"], "duracao": round(gap, 2)})
    fim_fala = palavras[-1]["fim"] if palavras else 0
    if d.get("duracao", 0) - fim_fala > a.pausa:
        pausas.append({"inicio": fim_fala, "fim": d["duracao"], "duracao": round(d["duracao"] - fim_fala, 2), "onde": "final"})

    repeticoes = []
    for i, f in enumerate(frases):
        for g in frases[i + 1 : i + 4]:
            a1, b1 = norm(f["texto"]), norm(g["texto"])
            if len(a1) < 8 or len(b1) < 8:
                continue
            curto, longo = sorted((a1, b1), key=len)
            ratio = SequenceMatcher(None, a1, b1).ratio()
            if ratio > 0.7 or longo.startswith(curto[: max(12, len(curto) // 2)]):
                repeticoes.append({"frase_a": f["id"], "frase_b": g["id"], "semelhanca": round(ratio, 2),
                                   "a": f["texto"], "b": g["texto"]})

    print(json.dumps({"pausas": pausas, "repeticoes": repeticoes}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
