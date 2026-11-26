---
name: transcricao
description: Transcreve o vídeo bruto da pasta bruto/ com Whisper (local e gratuito), em português, e salva em trabalho/ o texto com o tempo de início e fim de cada frase. Use sempre que o usuário pedir para transcrever, legendar, "tirar o texto", "pegar a fala" ou começar a editar um vídeo novo, mesmo que não diga "transcrição" ou "Whisper". É o primeiro passo antes da skill plano-de-edicao.
---

# Transcrição

Transforma a fala do vídeo em texto com tempos, para que dê para planejar cortes e
inserções com precisão. Tudo roda na máquina: nada é enviado para fora e não há custo.

## Passos

1. **Escolher o vídeo.** Se o usuário não disser qual, use o mais recente em `bruto/`.
   Se `bruto/` estiver vazio, peça para ele colocar o vídeo lá e pare.
   Se houver vários e não for óbvio qual ele quer, liste-os e pergunte.

2. **Rodar o script** a partir da raiz do repositório:

   ```bash
   PY=/opt/whisper-venv/bin/python; [ -x "$PY" ] || PY=python3
   "$PY" scripts/transcrever.py [bruto/ARQUIVO] --idioma pt --modelo small
   ```

   - Se der `ModuleNotFoundError: faster_whisper`, instale com
     `python3 -m pip install -r requirements.txt` e rode de novo.
   - Modelo: `small` é o padrão (bom equilíbrio para português em CPU, ~1x tempo real).
     Use `medium` se o usuário pedir mais precisão ou se a transcrição sair com muitos
     erros; `base` se ele tiver pressa. Vídeos longos levam tempo: rode em segundo plano
     e avise o usuário.
   - O áudio é extraído pelo próprio Whisper (com FFmpeg por baixo), não precisa converter antes.

3. **Conferir o resultado.** O script gera em `trabalho/`:
   - `<nome>.transcricao.txt`: uma frase por linha, `[00:00:01.200 --> 00:00:04.800] texto`
   - `<nome>.transcricao.json`: as mesmas frases com `inicio`/`fim` em segundos e, dentro
     de cada uma, as `palavras` com seus tempos (útil para cortar no meio de uma frase).

   Abra o `.txt` e verifique rapidamente: idioma certo, sem trechos repetidos em loop,
   duração coerente com o vídeo (`ffprobe -v error -show_entries format=duration -of csv=p=0 ARQUIVO`).

4. **Mostrar ao usuário** um resumo curto: quantas frases, duração, onde ficaram os
   arquivos e as primeiras linhas do texto. Nomes próprios e termos técnicos costumam sair
   errados; aponte os que parecerem estranhos e ofereça corrigir no `.txt` e no `.json`
   (mantendo os tempos).

5. Sugira o próximo passo: a skill **plano-de-edicao**.

## Por que assim

- Os tempos por palavra deixam os cortes do plano de edição precisos ao décimo de segundo.
- O filtro de silêncio (VAD) fica desligado de propósito: as pausas precisam aparecer como
  intervalos entre frases, porque o plano de edição usa isso para sugerir cortes.
