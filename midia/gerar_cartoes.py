# -*- coding: utf-8 -*-
"""Gera os cartoes de abertura/encerramento e as legendas (lower thirds)
do video de demonstracao do braco robotico. Saida: PNG 1920x1080.

drawtext do ffmpeg esta quebrado neste ambiente (Fontconfig sem config ->
segfault), por isso todo o texto e rasterizado aqui com PIL.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cartoes")
os.makedirs(OUT, exist_ok=True)

F = "C:/Windows/Fonts/"
BOLD = F + "segoeuib.ttf"
REG = F + "segoeui.ttf"
LIGHT = F + "segoeuil.ttf"
MONO = F + "consolab.ttf"

BG1 = (16, 24, 34)
BG2 = (9, 13, 19)
ACC = (46, 168, 207)
TXT = (240, 245, 249)
MUT = (152, 174, 191)


def f(path, size):
    return ImageFont.truetype(path, size)


def largura(txt, fonte, tracking=0):
    if not txt:
        return 0
    b = fonte.getbbox(txt)
    return (b[2] - b[0]) + tracking * (len(txt) - 1)


def escreve(d, xy, txt, fonte, fill, tracking=0):
    """Desenha texto com entre-letras (PIL nao tem tracking nativo)."""
    if tracking == 0:
        d.text(xy, txt, font=fonte, fill=fill)
        return
    x, y = xy
    for ch in txt:
        d.text((x, y), ch, font=fonte, fill=fill)
        x += fonte.getlength(ch) + tracking


def ajusta(txt, caminho, tamanho, max_larg, tracking=0):
    """Reduz o corpo da fonte ate o texto caber em max_larg."""
    while tamanho > 10:
        fonte = f(caminho, tamanho)
        if largura(txt, fonte, tracking) <= max_larg:
            return fonte
        tamanho -= 2
    return f(caminho, 10)


def fundo():
    """Gradiente vertical + brilho diagonal na cor de destaque."""
    img = Image.new("RGB", (W, H), BG2)
    grad = Image.new("RGB", (1, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        t = y / (H - 1)
        gd.point((0, y), fill=tuple(int(BG1[i] + (BG2[i] - BG1[i]) * t) for i in range(3)))
    img = grad.resize((W, H))

    brilho = Image.new("L", (W, H), 0)
    bd = ImageDraw.Draw(brilho)
    bd.ellipse([W - 620, -360, W + 360, 620], fill=70)
    bd.ellipse([-420, H - 420, 520, H + 420], fill=34)
    brilho = brilho.filter(ImageFilter.GaussianBlur(190))
    img = Image.composite(Image.new("RGB", (W, H), ACC), img, brilho.point(lambda v: int(v * 0.55)))
    return img


def cartao_abertura():
    img = fundo()
    d = ImageDraw.Draw(img)
    x = 150

    d.rectangle([x, 318, x + 96, 324], fill=ACC)
    escreve(d, (x, 356), "SISTEMAS EMBARCADOS", f(BOLD, 30), ACC, tracking=7)
    escreve(d, (x, 402), "ENGENHARIA DA COMPUTA\u00c7\u00c3O  \u00b7  FAESA  \u00b7  2026/2",
            f(REG, 28), MUT, tracking=4)

    l1 = "BRA\u00c7O ROB\u00d3TICO"
    l2 = "DE 4 GRAUS DE LIBERDADE"
    fo1 = ajusta(l1, BOLD, 136, W - 2 * x)
    fo2 = ajusta(l2, BOLD, 136, W - 2 * x)
    d.text((x, 492), l1, font=fo1, fill=TXT)
    d.text((x, 492 + fo1.size + 14), l2, font=fo2, fill=ACC)

    y = 492 + fo1.size + 14 + fo2.size + 46
    d.text((x, y), "Prot\u00f3tipo montado em funcionamento", font=f(LIGHT, 48), fill=MUT)

    d.rectangle([x, H - 150, W - x, H - 148], fill=(44, 58, 72))
    d.text((x, H - 124), "github.com/RoberliSchuina/braco-robotico-4gdl",
           font=f(MONO, 28), fill=MUT)
    img.save(os.path.join(OUT, "abertura.png"))


def cartao_final():
    img = fundo()
    d = ImageDraw.Draw(img)
    x = 150

    d.rectangle([x, 150, x + 96, 156], fill=ACC)
    d.text((x, 186), "Bra\u00e7o Rob\u00f3tico 4 GDL", font=f(BOLD, 76), fill=TXT)
    d.text((x, 290), "Resumo do projeto", font=f(LIGHT, 38), fill=MUT)

    itens = [
        ("Graus de liberdade", "base, ombro, cotovelo e garra"),
        ("Estrutura", "PLA impresso em 3D, elos em forquilha (chapas duplas)"),
        ("Atuadores", "micro-servos de 1,8 kgf\u00b7cm, garra por engrenagens de 16 dentes"),
        ("Controle", "Arduino UNO e dois joysticks KY-023"),
        ("Alimenta\u00e7\u00e3o", "5 V / 5 A, base de apoio em acr\u00edlico"),
        ("Envelope", "alcance horizontal 186 mm, altura m\u00e1xima 249 mm"),
        ("Firmware", "modo manual, grava\u00e7\u00e3o e reprodu\u00e7\u00e3o de poses na EEPROM"),
    ]
    fr = f(BOLD, 32)
    fv = f(REG, 32)
    lab = max(largura(k, fr) for k, _ in itens) + 34
    y = 380
    for k, v in itens:
        d.ellipse([x + 4, y + 13, x + 14, y + 23], fill=ACC)
        d.text((x + 34, y), k, font=fr, fill=TXT)
        d.text((x + 34 + lab, y), v, font=fv, fill=MUT)
        y += 52

    y += 26
    url = "github.com/RoberliSchuina/braco-robotico-4gdl"
    fu = f(MONO, 34)
    lu = largura(url, fu)
    d.rounded_rectangle([x, y, x + lu + 72, y + 74], radius=10,
                        fill=(14, 20, 28), outline=ACC, width=2)
    d.text((x + 36, y + 16), url, font=fu, fill=ACC)

    d.text((x, H - 118), "Sistemas Embarcados  \u00b7  Engenharia da Computa\u00e7\u00e3o  \u00b7  FAESA  \u00b7  2026/2",
           font=f(REG, 28), fill=(104, 124, 140))
    img.save(os.path.join(OUT, "final.png"))


def legenda(nome, titulo, sub):
    """Lower third com alfa: painel arredondado embaixo a esquerda."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ft = f(BOLD, 50)
    fs = f(REG, 32)
    larg = max(largura(titulo, ft), largura(sub, fs))
    x0, y0 = 120, 836
    x1 = min(x0 + larg + 132, W - 120)
    y1 = y0 + 144

    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle([x0, y0 + 8, x1, y1 + 8], radius=14,
                                             fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img, sombra.filter(ImageFilter.GaussianBlur(16)))

    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=(10, 15, 21, 198))
    d.rounded_rectangle([x0 + 26, y0 + 26, x0 + 33, y1 - 26], radius=4, fill=ACC)
    d.text((x0 + 58, y0 + 22), titulo, font=ft, fill=TXT)
    d.text((x0 + 58, y0 + 86), sub, font=fs, fill=MUT)
    img.save(os.path.join(OUT, nome))


LEGENDAS = [
    ("leg1.png", "O prot\u00f3tipo",
     "Estrutura em PLA impresso sobre a base de apoio"),
    ("leg2.png", "Comando por joysticks",
     "Dois m\u00f3dulos KY-023: a alavanca define a velocidade da junta"),
    ("leg3.png", "Ombro",
     "Eleva\u00e7\u00e3o e recolhimento do conjunto bra\u00e7o\u2013antebra\u00e7o"),
    ("leg4.png", "Cotovelo",
     "Antebra\u00e7o da horizontal \u00e0 vertical"),
    ("leg5.png", "Juntas em s\u00e9rie",
     "Ombro e cotovelo combinados no mesmo movimento"),
    ("leg6.png", "Antebra\u00e7o e garra",
     "Chapas em forquilha com janelas de al\u00edvio e mand\u00edbulas planas"),
    ("leg7.png", "Sequ\u00eancia completa",
     "Base, ombro, cotovelo e garra em opera\u00e7\u00e3o"),
]

if __name__ == "__main__":
    cartao_abertura()
    cartao_final()
    for nome, t, s in LEGENDAS:
        legenda(nome, t, s)
    print("gerados em", OUT)
    for n in sorted(os.listdir(OUT)):
        print(" ", n)
