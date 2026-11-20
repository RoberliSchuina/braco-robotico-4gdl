# Mídia do protótipo em funcionamento

Registro do braço montado e operando, feito em 20/11/2026.

[![Braço robótico em operação](capa.jpg)](braco_robotico_demo.mp4)

▶ **[Assistir ao vídeo](braco_robotico_demo.mp4)** (o GitHub abre o player ao clicar no arquivo).

| Arquivo | O que é |
|---|---|
| `braco_robotico_demo.mp4` | Vídeo editado — 1920×1080, 30 fps, 2 min 27 s, 46 MB |
| `fotos/` | 12 fotos do protótipo (4000 × 1848, originais do celular) |
| `capa.jpg` | Quadro de abertura usado acima (quadro em 1:15 do vídeo, 1280 px) |
| `destaque.jpg` | Foto que abre o `README.md` da raiz — `fotos/20261120_163259.jpg` reduzida a 1600 px (281 kB, porque a original tem 2 MB e todo visitante do repositório baixa a imagem); gerada por `preparar_fotos.py` |

## O vídeo

Sete clipes, na ordem em que foram filmados, com cartão de abertura, legenda por
trecho e cartão de encerramento:

| Trecho | Legenda |
|---|---|
| 1 | O protótipo — estrutura em PLA impresso sobre a base de apoio |
| 2 | Comando por joysticks — dois módulos KY-023 |
| 3 | Ombro — elevação e recolhimento do conjunto braço–antebraço |
| 4 | Cotovelo — antebraço da horizontal à vertical |
| 5 | Juntas em série — ombro e cotovelo combinados |
| 6 | Antebraço e garra — chapas em forquilha e mandíbulas planas |
| 7 | Sequência completa — base, ombro, cotovelo e garra |

O áudio é o original das filmagens (ruído dos servos e do ambiente), com ganho de
6 dB e limitador, já que a gravação é baixa (média ≈ −35 dB).

## As fotos

As 12 fotos são os arquivos do celular, com uma única alteração: **a rotação, que
vinha só na etiqueta EXIF, foi gravada nos próprios pixels** (10 das 12 fotos; 5
delas estavam a 180°). Navegador respeita EXIF, mas o Word e o `python-docx` não —
sem isso, metade das fotos entraria de cabeça para baixo no relatório. As que já
estavam na orientação correta foram copiadas byte a byte, sem recompressão.

## Como regenerar

O material bruto (7 vídeos em 8K HEVC e as fotos, ≈ 1,4 GB) **não** está no
repositório — fica em `Fotos e videos/Photos-1-001/`, ignorada pelo git. Com ela
no lugar:

```bash
python midia/preparar_fotos.py   # ~5 s   -> midia/fotos/
python midia/gerar_cartoes.py    # ~2 s   -> midia/cartoes/ (PNG de texto)
python midia/gerar_video.py      # ~9 min -> midia/braco_robotico_demo.mp4
```

`gerar_video.py` roda em duas etapas: primeiro converte cada clipe 8K em um proxy
1080p (`midia/proxy/`, ~6 min, pulado se o arquivo já existir), depois monta a
linha do tempo numa única passagem de codificação.

### Decisões que não são óbvias

- **Clipes 1 e 2 foram filmados em retrato**, os outros cinco em paisagem. Em vez
  de tarjas pretas, os dois primeiros recebem como fundo uma cópia ampliada e
  desfocada do próprio quadro — a linha do tempo inteira fica em 16:9.
- **Todo o texto é rasterizado em PNG pelo `gerar_cartoes.py`**, não desenhado pelo
  ffmpeg: o filtro `drawtext` falha com *segmentation fault* nesta máquina porque o
  Fontconfig não tem arquivo de configuração. O PNG também dá tipografia melhor
  (entre-letras, painel com sombra).
- **O filtergraph vai num arquivo**, não na linha de comando: passa de 6 kB e o
  Windows trunca.
- **Decodificar 8K custa ~3× o tempo real** — daí a etapa de proxy, que evita
  redecodificar os 1,4 GB a cada ajuste de legenda.
- A taxa foi calibrada (CRF 23, teto de 3500 kbps) para o arquivo ficar **abaixo
  dos 50 MB** em que o GitHub passa a avisar sobre arquivos grandes.
