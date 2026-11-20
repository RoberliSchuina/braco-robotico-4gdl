# -*- coding: utf-8 -*-
"""Copia as fotos do protetipo para midia/fotos/ gravando a rotacao do EXIF
nos proprios pixels.

Motivo: 10 das 12 fotos so carregam a rotacao na tag EXIF Orientation
(5 delas a 180 graus). Navegador respeita; Word/python-docx e varios
visualizadores nao -- a foto sairia de cabeca para baixo no relatorio.
Depois da gravacao a tag vira 1 e o arquivo fica correto em qualquer lugar.
"""
import io
import os
import sys

import shutil

from PIL import Image, ImageOps
from PIL import JpegImagePlugin

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ORIGEM = os.path.join(RAIZ, "Fotos e videos", "Photos-1-001")
DESTINO = os.path.join(AQUI, "fotos")

os.makedirs(DESTINO, exist_ok=True)
total_ant = total_dep = 0
for nome in sorted(os.listdir(ORIGEM)):
    if not nome.lower().endswith(".jpg"):
        continue
    cam = os.path.join(ORIGEM, nome)
    im = Image.open(cam)
    orient = im.getexif().get(274, 1)
    antes = im.size

    destino = os.path.join(DESTINO, nome)
    if orient in (1, None):
        # nada a girar: copia byte a byte, sem gerar perda
        shutil.copy2(cam, destino)
        im2 = im
        dados = open(destino, "rb").read()
    else:
        amostragem = JpegImagePlugin.get_sampling(im)
        qtabelas = im.quantization
        im2 = ImageOps.exif_transpose(im)      # grava a rotacao nos pixels
        exif = im2.getexif()
        exif[274] = 1                          # orientacao agora e "normal"

        buf = io.BytesIO()
        # reencode com as tabelas de quantizacao da origem: mesma qualidade
        im2.save(buf, "JPEG", qtables=qtabelas, subsampling=amostragem,
                 optimize=True, exif=exif)
        dados = buf.getvalue()
        with open(destino, "wb") as fh:
            fh.write(dados)

    a = os.path.getsize(cam)
    total_ant += a
    total_dep += len(dados)
    print("%s  exif=%d  %sx%s -> %sx%s  %.2f -> %.2f MB"
          % (nome, orient, antes[0], antes[1], im2.size[0], im2.size[1],
             a / 1048576, len(dados) / 1048576))

print("\ntotal: %.1f MB -> %.1f MB" % (total_ant / 1048576, total_dep / 1048576))

# conferencia: reabre e exige orientacao 1
ruins = []
for nome in sorted(os.listdir(DESTINO)):
    if nome.lower().endswith(".jpg"):
        o = Image.open(os.path.join(DESTINO, nome)).getexif().get(274, 1)
        if o != 1:
            ruins.append((nome, o))
print("conferencia:", "OK - todas com orientacao 1" if not ruins else ruins)
sys.exit(1 if ruins else 0)
