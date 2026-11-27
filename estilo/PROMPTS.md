# Prompts e regras de edição

Juntei os padrões que mais se repetiam em guias e skills de edição com o Claude (fontes no
final). O Claude segue as regras abaixo em toda edição deste repositório. Se algo aqui
conflitar com `estilo/ESTILO.md`, vale o ESTILO.md.

## Regras gerais (valem para vídeo, foto e áudio)
1. Todo pedido de edição define quatro coisas: **o trecho**, **a mudança**, **o resultado**
   esperado e **o que não pode mudar**. Se faltar uma delas, pergunte ou assuma o padrão
   deste arquivo e diga qual padrão usou.
2. **Plano antes de editar.** Proponha a lista de cortes e inserções, com tempos, e espere
   a aprovação. Nada é cortado ou renderizado antes disso.
3. **Uma etapa por vez.** Nada de "editar tudo" de uma vez. Depois de cada etapa, confira
   os trechos que mudaram.
4. **Claude não ouve nem vê direto.** As decisões saem da transcrição (Whisper, com tempo
   por palavra) e de quadros extraídos. A execução é feita com ffmpeg ou HyperFrames.
5. **O original nunca é alterado.** O resultado vai para `trabalho/` ou `final/`.

## 🎬 Vídeo
- **Corte bruto:** transcrever com tempo por palavra e marcar pausas acima de 0,6 s,
  repetições, frases recomeçadas e erros. Mostrar a lista com início e fim antes de cortar.
  Não cortar no meio de uma palavra e deixar uns 0,2 s de respiro em cada corte.
- **Ritmo (Reels/Shorts):** nenhum plano parado por mais de 3 s. Onde não der para cortar,
  sugerir um zoom suave de 110% a 120%.
- **Gancho:** sugerir os 3 trechos mais fortes para os primeiros 3 segundos, com o motivo.
- **Clipes curtos:** de um vídeo longo, achar trechos de 20 a 45 s que façam sentido
  sozinhos, cada um com início, fim, título e gancho.
- **Legenda:** palavra por palavra, no máximo 3 palavras por vez, destacando a palavra-chave
  e fora da área da interface do Instagram/TikTok.
- **Letreiros, listas e gráficos:** listar onde entram, com o tempo e o texto exato, sem
  criar nada antes da aprovação.
- **Capítulos (YouTube):** gerar a partir da transcrição, com tempo e título curto.
- **Exportação padrão:** H.264, 30 fps, áudio a -14 LUFS. Vertical em 1080x1920 e
  horizontal em 1920x1080. Manter a qualidade do original.

## 📸 Foto
- O Claude edita foto com código (ffmpeg, ImageMagick, Python) ou passa os ajustes para o
  Lightroom ou Photoshop.
- **Retrato:** retocar a pele mantendo a textura, a identidade e a luz original, sem deixar
  com cara de plástico.
- **Correção de cor:** explicar cada ajuste (exposição, temperatura, contraste, HSL).
- **Em lote:** aplicar a mesma correção em toda a pasta e salvar em outra pasta, sem mexer
  nos originais.
- **Thumbnail:** 1280x720, rosto de um lado, no máximo 4 palavras grandes do outro e alto
  contraste.

## 🎧 Áudio
- **Limpeza:** classificar cada trecho da transcrição como vício de linguagem, recomeço,
  gagueira ou silêncio morto. Cortar com crossfade de 40 ms e preencher com o ruído de fundo
  da sala, para não ficar vácuo.
- **Tratamento (ffmpeg):** passa-alta em 80 Hz, redução de ruído leve, compressor e
  normalização em -14 LUFS (redes) ou -16 LUFS (podcast).
- **Música de fundo:** abaixar uns 12 dB quando houver fala (ducking), com transição suave.
- Mostrar a lista de cortes antes de aplicar.

## Fontes
- invideo: https://invideo.io/blog/video-editing-prompts-claude-chatgpt/
- Tella: https://www.tella.com/edit-with-ai/ai-video-editor-prompts
- Adobe: https://developer.adobe.com/adobe-for-creativity/prompts-and-workflows/
- PromptsRush: https://promptsrush.com/blog/how-to-edit-videos-with-claude
- MindStudio: https://mindstudio.ai/blog/ai-video-editing-claude-code-hyperframes
- Kapwing: https://www.kapwing.com/resources/how-to-edit-videos-with-claude-code-free-ai-video-editing-skill/
- AudioEditor (Daniel Miessler): https://skills.sh/danielmiessler/personal_ai_infrastructure/audioeditor
- podcast-edit (openclaudia): https://claudeskills.info/skills/openclaudia/openclaudia-skills/podcast-edit/
- Luma: https://lumalabs.ai/news/ai-photo-editing-prompts
- OpenArt: https://openart.ai/pt-br/blog/how-to-edit-videos-with-chatgpt-and-claude/
