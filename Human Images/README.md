# Human Images — Nano Banana Pro

Gera imagens com o **Nano Banana Pro** (`gemini-3-pro-image-preview`) pela API do Google Gemini.
O guia de prompts está em `imageprompts.md` (formato `CAMERA:` … `MOOD & ART DIRECTION:`).

## Configuração

Adicione `GEMINI_API_KEY` nas configurações do ambiente (Network secrets / variável de ambiente).
Não é preciso instalar nada: o script usa só a biblioteca padrão do Python.

## Uso

```bash
python3 "Human Images/scripts/render_image.py" render "Human Images/output/{run_id}/prompt.txt" --aspect-ratio "4:5" --resolution "2k" --output-dir "Human Images/output/{run_id}"
```

Com imagem de referência (repetível):

```bash
python3 "Human Images/scripts/render_image.py" render "Human Images/output/{run_id}/prompt.txt" --aspect-ratio "16:9" --resolution "2k" --output-dir "Human Images/output/{run_id}" --reference "Human Images/imagem base.png"
```

- Formatos: `auto, 1:1, 3:2, 2:3, 4:3, 3:4, 4:5, 5:4, 9:16, 16:9, 21:9`
- Resoluções: `1k, 2k, 4k`
- `--count N` gera N variações; `--model` troca o modelo.

As imagens e um `render.json` ficam na pasta de saída (`Human Images/output/` não vai para o git).
