# -*- coding: utf-8 -*-
"""gerar_esquema_everycircuit.py — modelo equivalente do barramento de 5 V para
simular tensoes e correntes no EveryCircuit (ou qualquer simulador analogico).

O EveryCircuit so tem componentes analogicos/digitais primitivos (fontes,
resistores, reativos, chaves, amp-ops, diodos, transistores, portas logicas,
latches, CIs, medidores). NAO existe Arduino, servo nem joystick na biblioteca,
entao o esquema de imagens/esquema_eletrico.png nao pode ser digitado la.
O que se simula é o SUBSISTEMA DE POTENCIA, que é justamente onde estao as
tensoes e correntes de interesse (secao 8.1 do relatorio).

Saida:  imagens/esquema_everycircuit.png  + tabela de resultados esperados.
"""
import os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "imagens", "esquema_everycircuit.png")

# ---------------------------------------------------------------- parametros
V1      = 5.0        # V    fonte ideal
RS_5A   = 0.05       # Ohm  regulacao de carga de uma fonte 5 V/5 A (5 % em 5 A)
RS_3A   = 0.083      # Ohm  idem para 3 A
R_FIO   = 0.053      # Ohm  0,5 m de 22 AWG, ida e volta
R_CONT  = 0.030      # Ohm  um contato de protoboard
L_FIO   = 1e-6       # H    indutancia do par de fios da fonte
C1      = 1000e-6    # F
ESR     = 0.15       # Ohm  ESR tipica de um eletrolitico 1000 uF/16 V
V_MIN   = 4.8        # V    minimo do datasheet do servo

# Resistencia equivalente de cada servo (R = 5 V / corrente da secao 8.1)
R_SERVO_MOV   = {"S1 base (SG90)": 18.4, "S2 ombro (MG90S)": 13.2,
                 "S3 cotovelo (MG90S)": 15.1, "S4 garra (SG90)": 16.9}
R_SERVO_STALL = {"S1 base (SG90)": 7.7, "S2 ombro (MG90S)": 7.1,
                 "S3 cotovelo (MG90S)": 7.1, "S4 garra (SG90)": 7.7}
R_INVERSAO    = 3.6   # Ohm  servo invertendo o sentido (~1,4 A por alguns ms)

par = lambda rs: 1.0 / sum(1.0 / r for r in rs)
R_MOV, R_STALL = par(R_SERVO_MOV.values()), par(R_SERVO_STALL.values())
R_LINHA = R_FIO + R_CONT


# ---------------------------------------------------------------- desenho
VERM, PRETO, AZUL, VERDE, CINZA = "#d62728", "#222222", "#1f77b4", "#2ca02c", "#888888"
fig, ax = plt.subplots(figsize=(16, 11), dpi=110)
ax.set_xlim(0, 160); ax.set_ylim(0, 110); ax.axis('off')

def fio(pts, cor=PRETO, lw=2.0):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=cor, lw=lw, solid_capstyle='round', zorder=2)

def ponto(x, y, cor=PRETO): ax.add_patch(Circle((x, y), 0.6, fc=cor, ec=cor, zorder=4))

def rotulo(x, y, t, fs=8.5, cor=PRETO, ha='center', va='center', bold=False):
    ax.text(x, y, t, ha=ha, va=va, fontsize=fs, color=cor,
            fontweight='bold' if bold else 'normal', zorder=5)

def resistor(x, y, comp=10, vert=False, nome="", valor="", cor=PRETO):
    """Zigue-zague de resistor centrado em (x, y)."""
    n, amp = 6, 1.6
    t = np.linspace(0, 1, 2 * n + 1)
    desl = amp * np.array([0] + [(-1) ** i for i in range(2 * n - 1)] + [0])
    ao = -comp / 2 + t * comp
    if vert:
        xs, ys = x + desl, y + ao
        rotulo(x + 4.2, y + 1.6, nome, 8.5, cor, ha='left', bold=True)
        rotulo(x + 4.2, y - 1.6, valor, 8, cor, ha='left')
    else:
        xs, ys = x + ao, y + desl
        rotulo(x, y + 4.2, nome, 8.5, cor, bold=True)
        rotulo(x, y - 4.4, valor, 8, cor)
    ax.plot(xs, ys, color=cor, lw=2.0, zorder=3)

def capacitor(x, y, nome="", valor="", cor=PRETO):
    """Capacitor vertical centrado em (x, y); terminais em y +- 4."""
    fio([(x, y + 4), (x, y + 1)], cor); fio([(x, y - 4), (x, y - 1)], cor)
    fio([(x - 3.5, y + 1), (x + 3.5, y + 1)], cor, 2.6)
    fio([(x - 3.5, y - 1), (x + 3.5, y - 1)], cor, 2.6)
    rotulo(x + 4.6, y + 1.4, nome, 8.5, cor, ha='left', bold=True)
    rotulo(x + 4.6, y - 1.6, valor, 8, cor, ha='left')

def indutor(x, y, comp=10, nome="", valor="", cor=PRETO):
    """Indutor horizontal (4 arcos) centrado em (x, y)."""
    r = comp / 8
    for k in range(4):
        cx = x - comp / 2 + r * (2 * k + 1)
        th = np.linspace(0, np.pi, 30)
        ax.plot(cx + r * np.cos(th), y + r * np.sin(th), color=cor, lw=2.0, zorder=3)
    rotulo(x, y + 4.6, nome, 8.5, cor, bold=True)
    rotulo(x, y - 3.4, valor, 8, cor)

def chave(x, y, nome="", cor=PRETO):
    """Chave vertical aberta centrada em (x, y); terminais em y +- 4."""
    fio([(x, y + 4), (x, y + 2)], cor); fio([(x, y - 4), (x, y - 2)], cor)
    ponto(x, y + 2, cor); ponto(x, y - 2, cor)
    fio([(x, y - 2), (x + 3.0, y + 2.4)], cor)
    rotulo(x + 4.0, y, nome, 8.5, cor, ha='left', bold=True)

def fonte_v(x, y, nome="", valor="", cor=PRETO):
    """Fonte de tensao CC (circulo) centrada em (x, y); terminais em y +- 5."""
    ax.add_patch(Circle((x, y), 3.4, fc="white", ec=cor, lw=2.0, zorder=3))
    fio([(x, y + 5), (x, y + 3.4)], cor); fio([(x, y - 5), (x, y - 3.4)], cor)
    rotulo(x, y + 1.5, "+", 11, cor); rotulo(x, y - 1.6, "−", 11, cor)
    rotulo(x - 4.6, y + 1.4, nome, 8.5, cor, ha='right', bold=True)
    rotulo(x - 4.6, y - 1.6, valor, 8, cor, ha='right')

def fonte_i(x, y, nome="", valor="", cor=PRETO):
    """Fonte de corrente (circulo com seta) centrada em (x, y); terminais em y +- 5."""
    ax.add_patch(Circle((x, y), 3.4, fc="white", ec=cor, lw=2.0, zorder=3))
    ax.annotate("", xy=(x, y + 2.2), xytext=(x, y - 2.2), zorder=4,
                arrowprops=dict(arrowstyle="-|>", color=cor, lw=1.8))
    fio([(x, y + 5), (x, y + 3.4)], cor); fio([(x, y - 5), (x, y - 3.4)], cor)
    rotulo(x + 4.6, y + 1.4, nome, 8.5, cor, ha='left', bold=True)
    rotulo(x + 4.6, y - 1.6, valor, 8, cor, ha='left')

def medidor(x, y, letra, nome="", cor=AZUL, vert=False):
    ax.add_patch(Circle((x, y), 3.0, fc="#eef4fb", ec=cor, lw=1.8, zorder=3))
    rotulo(x, y, letra, 11, cor, bold=True)
    if vert: fio([(x, y + 5), (x, y + 3)], cor); fio([(x, y - 5), (x, y - 3)], cor)
    else:    fio([(x - 5, y), (x - 3, y)], cor); fio([(x + 5, y), (x + 3, y)], cor)
    rotulo(x, y + 5.4, nome, 8, cor, bold=True)

def terra(x, y, cor=PRETO):
    fio([(x, y), (x, y - 2)], cor)
    for i, w in enumerate((4.0, 2.6, 1.3)):
        fio([(x - w, y - 2 - i * 1.3), (x + w, y - 2 - i * 1.3)], cor, 2.2)


# ================================================================ PAINEL A
ax.add_patch(Rectangle((2, 63), 156, 44, fc="#f7fbf7", ec=VERDE, lw=1.6, zorder=0))
rotulo(5, 103.5, "MODELO A — minimo (4 componentes + terra, dentro do limite de 5 do plano GRATUITO)",
       12, VERDE, ha='left', bold=True)
rotulo(5, 99.8, "Mede a queda de tensao no barramento quando a carga dos servos salta. "
                "A fonte de corrente pulsada substitui os 4 servos.", 9, PRETO, ha='left')

YA_TOP, YA_BOT = 88, 70
fonte_v(16, 79, "V1", "5 V CC")
fio([(16, 84), (16, YA_TOP)]); fio([(16, YA_TOP), (32, YA_TOP)])
resistor(38, YA_TOP, 12, nome="R1", valor="0,13 Ω")
fio([(44, YA_TOP), (72, YA_TOP)], VERM, 2.6)
ponto(72, YA_TOP, VERM)
fio([(72, YA_TOP), (110, YA_TOP)], VERM, 2.6)
ponto(110, YA_TOP, VERM)
rotulo(91, YA_TOP + 3.0, "barramento +5 V dos servos", 9, VERM, bold=True)

capacitor(72, 79, "C1", "1000 µF")
fio([(72, YA_TOP), (72, 83)], VERM); fio([(72, 75), (72, YA_BOT)])

fonte_i(110, 79, "I1", "pulso 0,5 → 2,8 A")
fio([(110, YA_TOP), (110, 84)], VERM); fio([(110, 74), (110, YA_BOT)])
rotulo(126, 80.6, "onda quadrada, 100 Hz", 8.5, PRETO, ha='left')
rotulo(126, 77.4, "= os 4 servos partindo juntos", 8.5, PRETO, ha='left')

fio([(16, YA_BOT), (110, YA_BOT)])
fio([(16, 74), (16, YA_BOT)])
terra(63, YA_BOT)
rotulo(63, 63.6, "GND comum", 8.5)


# ================================================================ PAINEL B
ax.add_patch(Rectangle((2, 3), 156, 56, fc="#fbf8f4", ec="#b07d2b", lw=1.6, zorder=0))
rotulo(5, 55.5, "MODELO B — completo (17 elementos: exige a assinatura de US$ 5/mes)",
       12, "#b07d2b", ha='left', bold=True)
rotulo(5, 51.8, "Cada servo vira uma chave + resistor. Feche S1..S4 em qualquer combinacao "
                "e leia a corrente em A1 e a tensao em M1.", 9, PRETO, ha='left')

YB_TOP, YB_BOT = 40, 10
fonte_v(12, 25, "V1", "5 V CC")
fio([(12, 30), (12, YB_TOP)])
resistor(24, YB_TOP, 9, nome="Rs", valor="0,05 Ω", cor=CINZA)
rotulo(24, YB_TOP + 7.6, "regulacao da fonte", 7.5, CINZA)
indutor(38, YB_TOP, 9, nome="Lf", valor="1 µH", cor=CINZA)
resistor(52, YB_TOP, 9, nome="Rf", valor="0,08 Ω", cor=CINZA)
rotulo(52, YB_TOP - 7.8, "fio + contato", 7.5, CINZA)
for a, b in [(12, 19.5), (28.5, 33.5), (42.5, 47.5), (56.5, 62)]:
    fio([(a, YB_TOP), (b, YB_TOP)])
medidor(67, YB_TOP, "A", "A1 = corrente total")
fio([(72, YB_TOP), (80, YB_TOP)], VERM, 2.6)
ponto(80, YB_TOP, VERM)
fio([(80, YB_TOP), (148, YB_TOP)], VERM, 2.6)
rotulo(114, YB_TOP + 3.0, "barramento +5 V dos servos", 9, VERM, bold=True)

# ramo do capacitor (com ESR) e voltimetro
capacitor(80, 31, "C1", "1000 µF")
fio([(80, YB_TOP), (80, 35)], VERM)
fio([(80, 27), (80, 24)])
resistor(80, 19, 8, vert=True, nome="ESR", valor="0,15 Ω", cor=CINZA)
fio([(80, 15), (80, YB_BOT)])
medidor(93, 25, "V", "", vert=True)
rotulo(97.5, 25, "M1 = tensao", 8, AZUL, ha='left', bold=True)
fio([(93, YB_TOP), (93, 30)], VERM); ponto(93, YB_TOP, VERM)
fio([(93, 20), (93, YB_BOT)])

# os quatro servos
SERVOS = [(110, "S1", "7,7 Ω", "base SG90"), (123, "S2", "7,1 Ω", "ombro MG90S"),
          (136, "S3", "7,1 Ω", "cotovelo MG90S"), (148, "S4", "7,7 Ω", "garra SG90")]
for x, nome, val, desc in SERVOS:
    ponto(x, YB_TOP, VERM)
    fio([(x, YB_TOP), (x, 34)], VERM)
    chave(x, 30, nome)
    fio([(x, 26), (x, 23)])
    resistor(x, 18, 8, vert=True, nome="", valor=val, cor=VERM)
    fio([(x, 14), (x, YB_BOT)])
    rotulo(x, 7.0, desc, 7.5, PRETO)
fio([(12, YB_BOT), (148, YB_BOT)])
fio([(12, 20), (12, YB_BOT)])
terra(60, YB_BOT)

plt.tight_layout()
fig.savefig(SAIDA, bbox_inches='tight', facecolor='white')
print("OK", SAIDA)


# ---------------------------------------------------------------- resultados esperados
def dc(r_carga, rs):
    """Ponto de operacao CC: (corrente da fonte, tensao no barramento)."""
    rt = rs + R_LINHA + r_carga
    return V1 / rt, V1 * r_carga / rt

def transitorio(r_ini, r_fim, rs, c=C1, esr=ESR, t_fim=3e-3, dt=2e-9):
    """Degrau de carga. Retorna a menor tensao vista no barramento."""
    i_l, v_c = dc(r_ini, rs)[0], dc(r_ini, rs)[1]
    if c:
        v_c = dc(r_ini, rs)[1] - esr * 0.0    # em regime o capacitor nao conduz
    v_min, n = V1, int(t_fim / dt)
    for k in range(n):
        r = r_ini if k * dt < t_fim * 0.1 else r_fim
        if c:
            g = 1.0 / esr + 1.0 / r
            v_bus = (i_l + v_c / esr) / g
            v_c += ((v_bus - v_c) / esr) / c * dt
        else:
            v_bus = i_l * r
        i_l += (V1 - i_l * (rs + R_LINHA) - v_bus) / L_FIO * dt
        if k * dt > t_fim * 0.1:
            v_min = min(v_min, v_bus)
    return v_min

print("\n" + "=" * 76)
print("RESULTADOS ESPERADOS DA SIMULACAO (confira contra o EveryCircuit)")
print("=" * 76)
print(f"\nCarga equivalente dos 4 servos em paralelo:")
print(f"   em movimento : {R_MOV:5.2f} Ohm      travados : {R_STALL:5.2f} Ohm")

print(f"\n== regime permanente (V_min do servo = {V_MIN:.1f} V) ==")
print(f"   {'fonte':18s} {'condicao':22s} {'I total':>9s} {'V barramento':>14s}")
for rot_f, rs in [("5 V / 5 A (Rs=50 mOhm)", RS_5A), ("5 V / 3 A (Rs=83 mOhm)", RS_3A)]:
    for rot_c, rc in [("4 servos movendo", R_MOV), ("4 servos travados", R_STALL)]:
        i, v = dc(rc, rs)
        flag = "  OK" if v >= V_MIN else "  <-- abaixo de 4,8 V"
        print(f"   {rot_f:18s} {rot_c:22s} {i:7.2f} A {v:12.2f} V{flag}")

print(f"\n== transitorio: os 4 servos saltam de 'movendo' para 'travados' ==")
for rot, c in [("com C1 = 1000 uF (ESR 150 mOhm)", C1),
               ("com 2 x 470 uF (ESR 75 mOhm)", 940e-6),
               ("SEM capacitor", None)]:
    vm = transitorio(R_MOV, R_STALL, RS_5A, c, 0.075 if c == 940e-6 else ESR)
    print(f"   {rot:34s} tensao minima no barramento: {vm:5.2f} V")
print("\n   >> sem capacitor a indutancia do fio faz o barramento colapsar por ~1 us. A fonte")
print("      real tem capacitancia de saida propria, que atenua isso; o modelo a ignora de")
print("      proposito para isolar o efeito do C1, e o EveryCircuit mostrara o mesmo.")
print("   >> com C1 a queda instantanea passa a ser dominada pela ESR, nao pela capacitancia:")
print("      dois eletroliticos de 470 uF em paralelo (ESR pela metade) seguram melhor o")
print("      transitorio do que um unico de 1000 uF.")
