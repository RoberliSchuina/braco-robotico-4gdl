# -*- coding: utf-8 -*-
"""Prepara as fotos do prototipo em midia/fotos/ e a imagem de destaque do README.

O que faz:
  1. copia de "Fotos e videos/Photos-1-001/" o que ainda nao existe em fotos/;
  2. conserta qualquer foto de fotos/ cuja rotacao esteja so na etiqueta EXIF,
     gravando-a nos pixels;
  3. gera destaque.jpg, a versao leve que abre o README da raiz.

Por que o passo 2 existe: navegador e GitHub respeitam a etiqueta EXIF
Orientation, mas **Word e python-docx nao** -- uma foto so rotacionada pela
etiqueta entra de cabeca para baixo no relatorio.

ATENCAO -- a etiqueta do bruto NAO e confiavel. Em 6 das 12 fotos ela pedia uma
rotacao que os pixels exportados JA tinham, e grava-la virou a foto de novo (de
cabeca para baixo no GitHub). Essas 6 foram substituidas pelos arquivos que o
autor corrigiu a mao no proprio bruto e hoje ja vem com Orientation = 1. Nenhum
teste de programa separa "pixels crus" de "pixels ja girados": depois de rodar
com --forcar, OLHE as fotos.

Por que o passo 1 nao sobrescreve: fotos de fotos/ podem ter sido recortadas a
mao (foi o caso de 20261120_163538.jpg). Regenerar a partir do bruto apagaria o
recorte. Para refazer tudo a partir do original: `preparar_fotos.py --forcar`.
"""
import io
import os
import shutil
import sys

from PIL import Image, ImageOps
from PIL import JpegImagePlugin

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ORIGEM = os.path.join(RAIZ, "Fotos e videos", "Photos-1-001")
DESTINO = os.path.join(AQUI, "fotos")

DESTAQUE_ORIGEM = "20261120_163538.jpg"   # vista de cima do braco sobre a base
DESTAQUE_LARGURA = 1600

FORCAR = "--forcar" in sys.argv


def grava_rotacao(caminho):
    """Grava a rotacao do EXIF nos pixels e zera a etiqueta. Devolve o angulo
    aplicado, ou 0 se a foto ja estava correta.

    So pode ser chamada em copia recem-feita do BRUTO, onde a etiqueta foi
    escrita pela camera e e confiavel. Numa foto ja tratada a etiqueta pode
    estar obsoleta -- um editor de imagem costuma reescreve-la ao salvar,
    mesmo com os pixels ja girados -- e aplica-la giraria a foto de novo.
    """
    im = Image.open(caminho)
    orient = im.getexif().get(274, 1)
    if orient in (1, None):
        return 0
    # reencode com as tabelas de quantizacao da origem: mesma qualidade.
    # (subsampling="keep" NAO funciona depois do transpose -- a imagem deixa
    #  de ser "um JPEG" para o Pillow e ele levanta ValueError.)
    amostragem = JpegImagePlugin.get_sampling(im)
    qtabelas = im.quantization
    im2 = ImageOps.exif_transpose(im)
    exif = im2.getexif()
    exif[274] = 1

    buf = io.BytesIO()
    im2.save(buf, "JPEG", qtables=qtabelas, subsampling=amostragem,
             optimize=True, exif=exif)
    with open(caminho, "wb") as fh:
        fh.write(buf.getvalue())
    return {2: 0, 3: 180, 6: 90, 8: 270}.get(orient, orient)


def main():
    if not os.path.isdir(ORIGEM):
        sys.exit("Material bruto ausente: %s\n(fica fora do git -- ver midia/README.md)"
                 % ORIGEM)
    os.makedirs(DESTINO, exist_ok=True)

    copiadas = mantidas = giradas = 0
    for nome in sorted(os.listdir(ORIGEM)):
        if not nome.lower().endswith(".jpg"):
            continue
        destino = os.path.join(DESTINO, nome)
        if os.path.exists(destino) and not FORCAR:
            mantidas += 1
            continue
        shutil.copy2(os.path.join(ORIGEM, nome), destino)
        copiadas += 1
        ang = grava_rotacao(destino)          # so aqui: etiqueta da camera
        if ang:
            print("  %s: rotacao de %d graus gravada nos pixels" % (nome, ang))
            giradas += 1
    print("fotos: %d copiadas do bruto (%d giradas), %d ja existentes mantidas%s"
          % (copiadas, giradas, mantidas, " (--forcar refaz todas)" if mantidas else ""))
    if giradas:
        print("   CONFIRA as %d giradas: a etiqueta do bruto ja esteve errada neste" % giradas)
        print("   projeto (pixels exportados ja girados). Se alguma sair de cabeca para")
        print("   baixo, gire o arquivo no bruto e rode de novo -- ele e copiado byte a byte.")

    # conferencia: nenhuma foto pode depender da etiqueta para aparecer certa.
    # Nao consertamos automaticamente -- numa foto ja tratada nao da para saber
    # se a etiqueta ficou obsoleta (pixels certos) ou se a foto e nova e crua.
    ruins = [(n, Image.open(os.path.join(DESTINO, n)).getexif().get(274, 1))
             for n in sorted(os.listdir(DESTINO)) if n.lower().endswith(".jpg")]
    ruins = [(n, o) for n, o in ruins if o != 1]
    if not ruins:
        print("conferencia: OK - todas com orientacao 1")
    else:
        print("conferencia: ATENCAO - %d foto(s) com etiqueta de rotacao:" % len(ruins))
        for n, o in ruins:
            print("   %s  orientation=%s" % (n, o))
        print("   Abra cada uma e veja se ja aparece certa:")
        print("   - se SIM, a etiqueta ficou obsoleta (editor de imagem costuma")
        print("     reescreve-la ao salvar): apague so a etiqueta, nao gire os pixels;")
        print("   - se NAO, rode com --forcar para refazer a partir do bruto")
        print("     (atencao: --forcar descarta recortes feitos a mao).")

    # versao leve para abrir o README da raiz: a foto escolhida tem ~4000 px e
    # ~2 MB, e o README e a primeira pagina do repositorio (todo visitante
    # baixa a imagem).
    cam = os.path.join(DESTINO, DESTAQUE_ORIGEM)
    if os.path.exists(cam):
        im = Image.open(cam)
        alt = round(im.height * DESTAQUE_LARGURA / im.width)
        saida = os.path.join(AQUI, "destaque.jpg")
        im.resize((DESTAQUE_LARGURA, alt), Image.LANCZOS).save(
            saida, "JPEG", quality=88, optimize=True)
        print("destaque.jpg: %s -> %dx%d, %.0f kB"
              % (DESTAQUE_ORIGEM, DESTAQUE_LARGURA, alt, os.path.getsize(saida) / 1024))
    else:
        print("AVISO: %s nao encontrada, destaque.jpg nao foi gerada" % DESTAQUE_ORIGEM)

    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
