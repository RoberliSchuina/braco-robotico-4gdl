# -*- coding: utf-8 -*-
"""gerar_esquema.py — desenha o esquema elétrico de ligação (imagens/esquema_eletrico.png).
Arduino UNO + 4 servos (fonte externa) + 2 módulos joystick KY-023 (alimentados pelo Arduino)."""
import os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "imagens", "esquema_eletrico.png")

VERM, PRETO, LARANJA, AZUL, VERDE = "#d62728", "#222222", "#ff9900", "#1f77b4", "#2ca02c"
fig, ax = plt.subplots(figsize=(16, 10), dpi=110)
ax.set_xlim(0, 168); ax.set_ylim(0, 102); ax.axis('off')

def caixa(x, y, w, h, titulo, cor="#f2f2f2", fs=11, ty=None):
    ax.add_patch(Rectangle((x, y), w, h, fc=cor, ec="#333", lw=1.5))
    ax.text(x + w / 2, ty if ty else y + h - 3, titulo, ha='center', va='top', fontsize=fs, fontweight='bold')

def fio(pts, cor, lw=2.2):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=cor, lw=lw, solid_capstyle='round')

def ponto(x, y, cor=PRETO): ax.add_patch(Circle((x, y), 0.7, fc=cor, ec=cor))

# ---------------- Arduino UNO
caixa(38, 22, 30, 62, "ARDUINO UNO R3", "#dfe9f5", 12)
pinos_esq = {"5V": 80, "D2": 74, "A0": 66, "A1": 61, "A2": 50, "A3": 45, "D4": 38, "GND": 32}
pinos_dir = {"D3": 73, "D5": 63, "D6": 53, "D9": 43}
for n, y in pinos_esq.items(): ax.text(39, y, n, ha='left', va='center', fontsize=9)
for n, y in pinos_dir.items(): ax.text(67, y, n, ha='right', va='center', fontsize=9)
ax.text(53, 27, "USB (programação)", ha='center', fontsize=8, style='italic')
ax.text(53, 56, "LED de status: D13\n(LED da própria placa)", ha='center', fontsize=8)

# ---------------- barramentos
Y_VEXT, Y_GND = 82, 10
fio([(75, Y_VEXT), (146, Y_VEXT)], VERM, 3); ax.text(76, Y_VEXT + 1.5, "+5 V servos (fonte externa)", fontsize=8.5, color=VERM)
fio([(1, Y_GND), (150, Y_GND)], PRETO, 3);   ax.text(152, Y_GND, "GND comum", va='center', fontsize=9)

# fonte externa
caixa(112, 86, 34, 12, "FONTE 5 V / 5 A (plug P4)", "#fde9d9", 10)
ax.text(116, 88, "V+", ha='center', fontsize=8, color=VERM); ax.text(142, 88, "GND", ha='center', fontsize=8)
fio([(116, 86), (116, Y_VEXT)], VERM); ponto(116, Y_VEXT, VERM)
fio([(142, 86), (142, 84.5), (149, 84.5), (149, Y_GND)], PRETO); ponto(149, Y_GND)
# capacitor de desacoplamento (na extremidade do barramento)
fio([(146, Y_VEXT), (146, 79)], VERM); fio([(146, 77), (146, Y_GND)], PRETO); ponto(146, Y_GND)
fio([(143, 79), (149, 79)], PRETO, 3); fio([(143, 77), (149, 77)], PRETO, 3)
ax.text(150.5, 78, "C1 1000 µF / 16 V", va='center', fontsize=7.5)

# ---------------- servos
servos = [("S1 BASE", "D3", 73), ("S2 OMBRO", "D5", 63), ("S3 COTOVELO", "D6", 53), ("S4 GARRA", "D9", 43)]
for i, (nome, pino, ypin) in enumerate(servos):
    x, y = 100, 66 - i * 15
    caixa(x, y, 32, 11, nome, "#e2f0d9", 9)
    ax.text(x + 4, y + 2.5, "SIN", fontsize=7, color=LARANJA); ax.text(x + 14, y + 2.5, "VCC", fontsize=7, color=VERM); ax.text(x + 24, y + 2.5, "GND", fontsize=7)
    fio([(68, ypin), (78 + i * 2, ypin), (78 + i * 2, y + 1), (x + 6, y + 1), (x + 6, y)], LARANJA)     # sinal
    fio([(x + 16, y), (x + 16, y - 3), (138 - i, y - 3), (138 - i, Y_VEXT)], VERM)                        # VCC (fonte externa)
    fio([(x + 26, y), (x + 26, y - 5), (142 - i, y - 5), (142 - i, Y_GND)], PRETO)                        # GND
    ponto(138 - i, Y_VEXT, VERM); ponto(142 - i, Y_GND)

# ---------------- joysticks (alimentados pelo 5 V do Arduino)
fio([(38, 80), (36, 80), (36, 82.5), (3, 82.5), (3, 47)], LARANJA)          # trilho +5 V (Arduino)
ax.text(4, 84, "+5 V (Arduino)", fontsize=8, color=LARANJA)
fio([(38, 32), (34, 32), (34, Y_GND)], PRETO); ponto(34, Y_GND)              # GND Arduino -> barramento
joys = [  # (nome, y0, terminais direita: (rótulo, y, pino Arduino, y do pino, cor), +5V y, GND y)
    ("JOYSTICK 1\n(KY-023)", 58, [("SW", 74, "D2", 74, VERDE), ("VRx", 66, "A0", 66, AZUL), ("VRy", 61, "A1", 61, AZUL)], 76, 68,
     "base (VRx) · ombro (VRy)\nSW: grava / reproduz"),
    ("JOYSTICK 2\n(KY-023)", 30, [("VRx", 50, "A2", 50, AZUL), ("VRy", 45, "A3", 45, AZUL), ("SW", 38, "D4", 38, VERDE)], 47, 34,
     "garra (VRx) · cotovelo (VRy)\nSW: abre/fecha garra; longo = home"),
]
for nome, y0, terms, y5, yg, desc in joys:
    caixa(6, y0, 16, 22, nome, "#fff2cc", 8, ty=y0 + 13)
    ax.text(7, y5, "+5V", fontsize=6.5, va='center', color=LARANJA); ax.text(7, yg, "GND", fontsize=6.5, va='center')
    fio([(6, y5), (3, y5)], LARANJA); ponto(3, y5, LARANJA)
    fio([(6, yg), (1, yg), (1, Y_GND)], PRETO); ponto(1, Y_GND)
    for rot, yt, pino, yp, cor in terms:
        ax.text(21, yt, rot, fontsize=6.5, va='center', ha='right', color=cor)
        fio([(22, yt), (38, yp)], cor)
    ax.text(14, y0 - 1.5, desc, ha='center', va='top', fontsize=6.5, style='italic')

# ---------------- notas
ax.text(2, 8, "Notas: (1) o GND da fonte externa DEVE ser ligado ao GND do Arduino (barramento comum);  (2) nunca alimente os servos pelo 5 V do Arduino/USB;\n"
              "(3) C1 cobre o degrau de corrente da inversão de sentido (µs a ms) até a fonte reagir — não substitui a corrente da fonte (ver 8.1 do relatório);\n"
              "      pior caso de operação 1,85 A, com os 4 servos travados 2,70 A;  (4) cabos dos servos: laranja = sinal, vermelho = VCC, marrom = GND;\n"
              "(5) os joysticks (≈ 2 mA cada) são alimentados pelo 5 V do Arduino; o botão SW vai a GND quando pressionado (usar INPUT_PULLUP);\n"
              "(6) alimente o Arduino de UMA forma só: pelo USB (programação/depuração) OU por um jumper da fonte ao pino 5V — nunca os dois ao mesmo tempo\n"
              "     (a fonte ficaria em paralelo com o USB do computador);  (7) só há conexão elétrica onde há ponto (•); fios que apenas se cruzam não se conectam.",
        ha='left', va='top', fontsize=7.8)
ax.set_title("Esquema elétrico — Braço robótico 4 GDL (Arduino UNO + 4 servos + 2 joysticks KY-023)", fontsize=13, fontweight='bold')
plt.tight_layout(); fig.savefig(SAIDA, facecolor='white'); print("OK", SAIDA)
