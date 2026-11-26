---
name: plano-de-edicao
description: Lê a transcrição em trabalho/ e o guia estilo/ESTILO.md, entende o assunto do vídeo, sugere cortes (pausas longas, repetições, retomadas, erros) e lista onde entram letreiros, gráficos, listas e zooms, com início, fim e descrição. Salva em trabalho/plano.json e sempre mostra o plano ao usuário para aprovação antes de criar qualquer coisa. Use sempre que o usuário quiser planejar a edição, decidir cortes, "ver o que dá para tirar", marcar onde entram textos/animações, ou quando a transcrição já existir e o próximo passo for editar.
---

# Plano de edição

Produz um roteiro de edição revisável. O plano é só uma proposta: nada é cortado,
renderizado ou criado até o usuário aprovar, porque é o vídeo dele e é muito mais barato
corrigir um JSON do que refazer uma renderização.

## Entradas

- `trabalho/<nome>.transcricao.json` (da skill **transcricao**). Se não existir, ofereça
  rodar a transcrição primeiro. Se houver mais de uma, use a do vídeo que o usuário indicar
  ou a mais recente.
- `estilo/ESTILO.md`: preferências do canal (tom, ritmo, cores, fontes, quando usar zoom,
  palavras a evitar...). Leia inteiro e siga. Se não existir, avise, use bom senso para um
  vídeo de YouTube e sugira preencher o modelo em `estilo/ESTILO.md`.

## Passos

1. **Entenda o vídeo.** Leia a transcrição inteira e resuma em 2 ou 3 frases: assunto,
   público e estrutura (abertura, blocos, chamada final). Esse entendimento decide o que é
   essencial e o que é sobra.

2. **Encontre candidatos a corte.** Rode o detector como ponto de partida:

   ```bash
   python3 .claude/skills/plano-de-edicao/scripts/pausas.py trabalho/<nome>.transcricao.json --pausa 1.2
   ```

   Depois, lendo o texto, decida o que cortar de verdade:
   - **pausas longas**: deixe uns 0,2 s de respiro de cada lado para o corte não ficar seco;
   - **repetições e retomadas** ("então… então o que eu quero dizer é"): normalmente fica a
     última versão, que costuma ser a boa; corte a anterior inteira;
   - **erros, gaguejos, "ééé", "tipo", "né"** em excesso, se o ESTILO.md não disser o contrário;
   - **trechos fora do assunto**: só sugira, com motivo, porque é uma decisão editorial.
   Use os tempos das `palavras` para cortar no ponto exato.

3. **Planeje as inserções** onde ajudam a entender ou a reter atenção:
   - **letreiro**: nome, termo-chave, título de seção, número importante;
   - **grafico**: quando a fala cita dados, comparações, evolução;
   - **lista**: quando a fala enumera passos ou itens (mostre o item no momento em que é dito);
   - **zoom**: ênfase, piada, momento emocional, mudança de bloco (siga o ritmo do ESTILO.md).
   Não exagere: inserções demais cansam. Prefira momentos com motivo claro.

4. **Salve `trabalho/plano.json`** neste formato (tempos em segundos do vídeo **original**):

   ```json
   {
     "video": "bruto/aula-01.mp4",
     "transcricao": "trabalho/aula-01.transcricao.json",
     "resumo": "Do que o vídeo trata, para quem, e como está estruturado.",
     "duracao_original": 612.4,
     "duracao_estimada_final": 541.0,
     "cortes": [
       {"id": "c1", "inicio": 0.0, "fim": 2.3, "tipo": "pausa", "motivo": "Silêncio antes da primeira fala"},
       {"id": "c2", "inicio": 48.1, "fim": 53.7, "tipo": "retomada", "motivo": "Repetiu a frase; fica a segunda versão",
        "texto_removido": "então o que eu quero"}
     ],
     "insercoes": [
       {"id": "i1", "tipo": "letreiro", "inicio": 3.0, "fim": 6.5,
        "descricao": "Título: 'Como montar um orçamento'", "texto": "Como montar um orçamento"},
       {"id": "i2", "tipo": "lista", "inicio": 120.0, "fim": 150.0,
        "descricao": "3 passos, cada item aparece quando é falado", "itens": ["Anote", "Separe", "Revise"]},
       {"id": "i3", "tipo": "grafico", "inicio": 200.0, "fim": 210.0,
        "descricao": "Barras: gastos de janeiro x fevereiro", "dados": {"jan": 1200, "fev": 900}},
       {"id": "i4", "tipo": "zoom", "inicio": 305.2, "fim": 308.0,
        "descricao": "Zoom in 115% no rosto, ênfase na frase 'isso muda tudo'"}
     ],
     "observacoes": ["Decisões editoriais que precisam do usuário"],
     "status": "aguardando_aprovacao"
   }
   ```

   `tipo` de corte: `pausa`, `repeticao`, `retomada`, `erro`, `fora_do_assunto`.
   `tipo` de inserção: `letreiro`, `grafico`, `lista`, `zoom`. Inserções sem corte não
   devem cair dentro de um trecho cortado.

5. **Mostre o plano para aprovação**, em linguagem simples e não como JSON cru:
   - o resumo do vídeo e a duração antes → depois;
   - uma tabela de cortes (início, fim, tipo, o que é dito/motivo);
   - uma tabela de inserções (início, fim, tipo, descrição);
   - as dúvidas editoriais.
   Use o formato `mm:ss` nas tabelas. Termine perguntando o que aprovar, mudar ou remover.

6. **Espere a resposta.** Ajuste o `plano.json` conforme o usuário pedir e mostre de novo
   o que mudou. Só quando ele aprovar explicitamente, mude `"status"` para `"aprovado"`.
   Não corte o vídeo, não gere gráficos nem chame a HyperFrames antes disso: aprovar é o
   gatilho para criar qualquer coisa.
