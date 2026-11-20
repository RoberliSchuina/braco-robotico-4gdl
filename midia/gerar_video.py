# -*- coding: utf-8 -*-
"""Monta midia/braco_robotico_demo.mp4 a partir dos videos brutos do celular.

Entrada:  "Fotos e videos/Photos-1-001/*.mp4" (fora do repositorio: 8K HEVC,
          ~1,4 GB -- veja .gitignore)
Saida:    midia/braco_robotico_demo.mp4 (1920x1080, 30 fps, ~46 MB)

Duas etapas:
  1. proxy -- cada clipe 8K vira 1080p. Os dois primeiros foram filmados em
     retrato e recebem fundo desfocado do proprio quadro, para a linha do
     tempo inteira ficar em 16:9 sem tarjas pretas.
  2. montagem -- cartao de abertura, legenda por clipe, transicoes cruzadas,
     cartao de encerramento e audio original com ganho leve.

Rodar `python midia/gerar_cartoes.py` antes (gera os PNG de texto).

Armadilhas deste ambiente, ja contornadas aqui:
  * drawtext do ffmpeg da segfault (Fontconfig sem arquivo de configuracao),
    por isso todo texto vem rasterizado em PNG pelo gerar_cartoes.py;
  * o filtergraph passa de 6 kB e nao cabe na linha de comando do Windows,
    entao vai num arquivo (-filter_complex_script);
  * decodificar 8K custa ~3x o tempo real; a etapa de proxy e a demorada
    (~6 min no total) e e pulada se o arquivo ja existir.
"""
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
BRUTO = os.path.join(RAIZ, "Fotos e videos", "Photos-1-001")
PROXY = os.path.join(AQUI, "proxy")
CART = os.path.join(AQUI, "cartoes")
SAIDA = os.path.join(AQUI, "braco_robotico_demo.mp4")

RETRATO = 2           # quantos dos primeiros clipes foram filmados em retrato
TRANS = 0.6           # duracao das transicoes cruzadas
DUR_ABRE = 4.5        # cartao de abertura
DUR_FIM = 6.0         # cartao de encerramento
LEG_IN = 0.9          # quando a legenda entra
LEG_HOLD = 4.8        # quanto tempo fica cheia
LEG_FADE = 0.5
GANHO_AUDIO = 6       # dB -- o audio de origem e baixo (media ~-35 dB)

# fundo desfocado do proprio quadro para os clipes em retrato
F_RETRATO = ("[0:v]fps=30,split=2[bg][fg];"
             "[bg]scale=1920:1080:force_original_aspect_ratio=increase,"
             "crop=1920:1080,gblur=sigma=28,eq=brightness=-0.10:saturation=0.75[bgb];"
             "[fg]scale=-2:1080:flags=lanczos[fgs];"
             "[bgb][fgs]overlay=(W-w)/2:0,format=yuv420p")
F_PAISAGEM = "[0:v]fps=30,scale=1920:1080:flags=lanczos,format=yuv420p"


def duracao(caminho):
    s = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "json", caminho], capture_output=True, text=True, check=True)
    return float(json.loads(s.stdout)["format"]["duration"])


def gera_proxies():
    os.makedirs(PROXY, exist_ok=True)
    brutos = sorted(f for f in os.listdir(BRUTO) if f.lower().endswith(".mp4"))
    if not brutos:
        sys.exit("Nenhum .mp4 em %s" % BRUTO)
    saidas = []
    for i, nome in enumerate(brutos, 1):
        destino = os.path.join(PROXY, "p%d.mp4" % i)
        saidas.append(destino)
        if os.path.exists(destino):
            print("[%d/%d] %s (ja existe)" % (i, len(brutos), os.path.basename(destino)))
            continue
        print("[%d/%d] %s -> p%d.mp4" % (i, len(brutos), nome, i))
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-v", "warning", "-stats",
             "-hwaccel", "d3d11va", "-i", os.path.join(BRUTO, nome),
             "-filter_complex", F_RETRATO if i <= RETRATO else F_PAISAGEM,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
             "-c:a", "copy", "-movflags", "+faststart", "-y", destino], check=True)
    return saidas


def monta(proxies):
    n = len(proxies)
    durs = [duracao(p) for p in proxies]
    segs = [DUR_ABRE] + durs + [DUR_FIM]
    total = sum(segs) - TRANS * (len(segs) - 1)

    entradas = ["-loop", "1", "-framerate", "30", "-t", "%.3f" % DUR_ABRE,
                "-i", os.path.join(CART, "abertura.png")]
    for p in proxies:
        entradas += ["-i", p]
    entradas += ["-loop", "1", "-framerate", "30", "-t", "%.3f" % DUR_FIM,
                 "-i", os.path.join(CART, "final.png")]
    for i in range(1, n + 1):
        entradas += ["-loop", "1", "-framerate", "30",
                     "-i", os.path.join(CART, "leg%d.png" % i)]

    f = []
    norm = "fps=30,scale=1920:1080,setsar=1,format=yuv420p"
    f.append("[0:v]%s[v0];" % norm)
    f.append("[%d:v]%s[v%d];" % (n + 1, norm, n + 1))
    for i in range(1, n + 1):
        f.append("[%d:v]format=rgba,fade=t=in:st=%.2f:d=%.2f:alpha=1,"
                 "fade=t=out:st=%.2f:d=%.2f:alpha=1[lg%d];"
                 % (n + 1 + i, LEG_IN, LEG_FADE, LEG_IN + LEG_HOLD, LEG_FADE, i))
        f.append("[%d:v]%s[b%d];" % (i, norm, i))
        f.append("[b%d][lg%d]overlay=0:0:shortest=1,format=yuv420p[v%d];" % (i, i, i))

    acc, atual = 0.0, "v0"
    for k in range(1, len(segs)):
        acc += segs[k - 1]
        alvo = "x%d" % k if k < len(segs) - 1 else "vfim"
        f.append("[%s][v%d]xfade=transition=fade:duration=%.2f:offset=%.3f[%s];"
                 % (atual, k, TRANS, acc - TRANS * k, alvo))
        atual = alvo
    f.append("[vfim]fade=t=in:st=0:d=0.8,fade=t=out:st=%.3f:d=1.0,"
             "format=yuv420p[vout];" % (total - 1.0))

    anorm = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    f.append("anullsrc=channel_layout=stereo:sample_rate=48000,"
             "atrim=0:%.3f,asetpts=PTS-STARTPTS[a0];" % DUR_ABRE)
    f.append("anullsrc=channel_layout=stereo:sample_rate=48000,"
             "atrim=0:%.3f,asetpts=PTS-STARTPTS[a%d];" % (DUR_FIM, n + 1))
    for i in range(1, n + 1):
        f.append("[%d:a]%s,asetpts=PTS-STARTPTS[a%d];" % (i, anorm, i))
    atual = "a0"
    for k in range(1, len(segs)):
        alvo = "y%d" % k if k < len(segs) - 1 else "afim"
        f.append("[%s][a%d]acrossfade=d=%.2f:c1=tri:c2=tri[%s];" % (atual, k, TRANS, alvo))
        atual = alvo
    f.append("[afim]volume=%ddB,alimiter=limit=0.89,"
             "afade=t=out:st=%.3f:d=1.0[aout]" % (GANHO_AUDIO, total - 1.0))

    cam = os.path.join(AQUI, "filtro.txt")
    with open(cam, "w", encoding="utf-8") as fh:
        fh.write("\n".join(f))

    print("segmentos (s): " + ", ".join("%.2f" % s for s in segs))
    print("total: %.2f s (%d min %02d s)" % (total, total // 60, total % 60))
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "warning", "-stats"] + entradas +
        ["-filter_complex_script", cam, "-map", "[vout]", "-map", "[aout]",
         "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
         "-preset", "slow", "-crf", "23",
         "-maxrate", "3500k", "-bufsize", "7000k",
         "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
         "-movflags", "+faststart", "-y", SAIDA], check=True)
    os.remove(cam)
    print("OK: %s  %.1f MB" % (SAIDA, os.path.getsize(SAIDA) / 1048576))


if __name__ == "__main__":
    for p in ("abertura.png", "final.png"):
        if not os.path.exists(os.path.join(CART, p)):
            sys.exit("Falta %s -- rode antes: python midia/gerar_cartoes.py" % p)
    monta(gera_proxies())
