# -*- coding: utf-8 -*-
"""
verificacao_eletrica.py — Dimensionamento da fonte dos servos (4 x MG90S/SG90 a 5 V).

Responde a duas perguntas do projeto:
  1. A fonte de 5 V / 3 A basta, considerando as correntes de pico?
  2. O capacitor C1 resolve sozinho o problema, ou ele resolve outro problema?

Modelo: motor CC com escovas dentro do servo. A corrente cresce linearmente com o
torque exigido, de I0 (girando em vazio) ate I_STALL (rotor travado):

        I(T) = I0 + (I_STALL - I0) * (T / T_STALL)

As fracoes de torque por junta vem de `verificacao.py` (secao 4, corpo livre com
as massas reais das malhas). Nao ha dependencia de CSG aqui: roda em 1 s.

Uso:  python cad/verificacao_eletrica.py
"""

# ---------------------------------------------------------------- 1. dados do servo
# O datasheet oficial TowerPro do MG90S publica SO: 13,4 g; 22,5 x 12 x 35,5 mm;
# 1,8 kgf.cm (4,8 V) / 2,2 kgf.cm (6 V); 0,1 s/60 graus (4,8 V); 4,8-6,0 V; banda
# morta 5 us. NAO ha nenhuma especificacao de corrente no datasheet -- os valores
# abaixo sao de medicao de terceiros (ProtoSupplies, a 5 V) e sao a base do calculo.
V_NOM     = 5.0     # V   tensao do barramento dos servos
V_MIN_SRV = 4.8     # V   minimo do datasheet (4,8-6,0 V)
I_REPOUSO = 0.010   # A   parado, sem erro de posicao (10 mA tipico)
I_VAZIO   = 0.250   # A   girando sem carga (faixa medida 120-250 mA; usa-se o pior)
I_STALL   = 0.700   # A   MG90S com rotor travado a 5 V (medido)
I_STALL_SG = 0.650  # A   SG90 (mesmo motor, engrenagem plastica) — BOM: 2 de cada
T_STALL   = 1.8     # kgf.cm a 4,8-5 V (datasheet)

# Pico de inversao: partindo da velocidade maxima e invertendo o sentido, a fcem
# soma-se a tensao aplicada sobre a mesma resistencia de armadura -> ate ~2x o
# stall, por alguns ms (decai com a constante de tempo mecanica).
I_PICO_INV = 2.0 * I_STALL

N_SERVOS = 4


def corrente(frac_torque, movendo=True):
    """Corrente de um servo exigido a `frac_torque` (0..1) do seu torque de stall."""
    base = I_VAZIO if movendo else I_REPOUSO
    return base + (I_STALL - base) * min(frac_torque, 1.0)


# ---------------------------------------------------------------- 2. carga por junta
# Fracao do stall exigida de cada servo (fonte: verificacao.py, secao 4).
#   ombro: 0,52 kgf.cm em vazio (29 %), 0,97 com 25 g (54 %), 1,43 com 50 g (79 %)
#   cotovelo: 39 % com 50 g na garra
#   base: eixo VERTICAL -> so inercia e atrito do disco, praticamente vazio
#   garra: fecha CONTRA o objeto -> fica em stall parcial de forma CONTINUA
CARGA = {
    #  junta        vazio   com 25 g   com 50 g
    "S1 base":     (0.05,   0.08,      0.10),
    "S2 ombro":    (0.29,   0.54,      0.79),
    "S3 cotovelo": (0.18,   0.28,      0.39),
    "S4 garra":    (0.10,   0.60,      0.60),   # segurando: stall parcial continuo
}

print("=" * 78)
print("DIMENSIONAMENTO DA FONTE — braco robotico 4 GDL (4 servos a 5 V)")
print("=" * 78)
print(f"\nModelo do servo (5 V): I_repouso={I_REPOUSO*1000:.0f} mA  "
      f"I_vazio={I_VAZIO*1000:.0f} mA  I_stall={I_STALL*1000:.0f} mA  "
      f"I_pico_inversao~{I_PICO_INV*1000:.0f} mA")

print("\n== 1. corrente por junta (mA) ==")
print(f"   {'junta':14s} {'%stall':>7s} {'movendo':>9s} {'%stall':>7s} {'c/25 g':>9s} "
      f"{'%stall':>7s} {'c/50 g':>9s}")
for nome, (f0, f25, f50) in CARGA.items():
    print(f"   {nome:14s} {100*f0:6.0f}% {1000*corrente(f0):8.0f} "
          f"{100*f25:6.0f}% {1000*corrente(f25):8.0f} "
          f"{100*f50:6.0f}% {1000*corrente(f50):8.0f}")

# ---------------------------------------------------------------- 3. cenarios
def total(fracs, movendo):
    return sum(corrente(f, m) for f, m in zip(fracs, movendo))

idx = {"vazio": 0, "25g": 1, "50g": 2}
f = lambda c: [CARGA[k][idx[c]] for k in CARGA]

cenarios = [
    ("A. repouso — 4 servos parados, garra aberta",
     total(f("vazio"), [False] * 4)),
    ("B. manual (joystick) — 1 eixo movendo, 3 segurando",
     corrente(CARGA["S2 ombro"][0]) + 3 * corrente(0.15, False)),
    ("C. manual com objeto de 25 g — 1 eixo movendo, garra apertando",
     corrente(CARGA["S2 ombro"][1]) + 2 * corrente(0.20, False) + corrente(0.60, False)),
    ("D. reproducao — 4 eixos simultaneos, sem carga",
     total(f("vazio"), [True] * 4)),
    ("E. reproducao — 4 eixos simultaneos + 25 g na garra",
     total(f("25g"), [True] * 4)),
    ("F. reproducao — 4 eixos simultaneos + 50 g (carga util max.)",
     total(f("50g"), [True] * 4)),
    ("G. FALHA — 4 servos travados ao mesmo tempo (braco preso)",
     2 * I_STALL + 2 * I_STALL_SG),   # BOM: 2 x MG90S (ombro/cotovelo) + 2 x SG90
]
print("\n== 2. cenarios de consumo (regime, sem transitorio) ==")
FONTE = 3.0
for nome, i in cenarios:
    marca = "  <-- limite" if i > 0.85 * FONTE else ""
    print(f"   {nome:60s} {i:5.2f} A  ({100*i/FONTE:3.0f} % de {FONTE:.0f} A){marca}")

pico_real = cenarios[4][1] + (I_PICO_INV - corrente(CARGA['S2 ombro'][1]))
pico_max = N_SERVOS * I_PICO_INV
print(f"\n   pico ms a ms, 1 servo invertendo durante o cenario E : {pico_real:5.2f} A")
print(f"   pico ms a ms, 4 servos invertendo ao mesmo tempo      : {pico_max:5.2f} A"
      "   (so o capacitor entrega isso)")

# ---------------------------------------------------------------- 4. o capacitor
print("\n== 3. o que o capacitor C1 resolve (e o que nao resolve) ==")
C1 = 1000e-6
for dV in (0.2, 0.5):
    q = C1 * dV
    print(f"   C1 = {C1*1e6:.0f} uF aceitando queda de {dV:.1f} V -> carga util {q*1e3:.2f} mC")
    for deficit in (1.0, 2.0):
        print(f"      sustenta um deficit de {deficit:.1f} A por apenas "
              f"{q/deficit*1e6:7.0f} us")

print("\n   Capacitancia NECESSARIA para cobrir um deficit de corrente, por duracao:")
print(f"   {'deficit':>9s} {'duracao':>9s} {'C p/ queda 0,2 V':>18s} {'C p/ queda 0,5 V':>18s}")
for deficit, t, rot in [(2.0, 100e-6, "ringing do cabo"),
                        (2.0, 1e-3,   "resposta da fonte chaveada"),
                        (1.0, 50e-3,  "aceleracao de um servo"),
                        (1.0, 1.0,    "stall de 1 s")]:
    c2 = deficit * t / 0.2
    c5 = deficit * t / 0.5
    print(f"   {deficit:6.1f} A {t*1e3:7.1f} ms {c2*1e6:15.0f} uF {c5*1e6:15.0f} uF   ({rot})")

print("\n   >> O capacitor cobre MICROSSEGUNDOS a poucos MILISSEGUNDOS (di/dt, indutancia")
print("      do cabo, tempo de resposta da malha da fonte). Para cobrir um stall de 1 s")
print("      seriam precisos ~2 F (2.000.000 uF): impossivel. Capacitor e capacidade de")
print("      corrente da fonte resolvem problemas DIFERENTES — um nao substitui o outro.")

# ---------------------------------------------------------------- 5. queda nos cabos
print("\n== 4. queda de tensao na fiacao (ida + volta) ==")
RHO = {"28 AWG (rabicho do servo)": 0.2129, "26 AWG (extensor)": 0.1339,
       "22 AWG (jumper comum)": 0.0530, "20 AWG": 0.0333, "18 AWG": 0.0209}
print(f"   orcamento: {V_NOM:.1f} V - {V_MIN_SRV:.1f} V (minimo do datasheet) = "
      f"{(V_NOM-V_MIN_SRV)*1000:.0f} mV\n")
print(f"   {'condutor':28s} {'compr.':>8s} {'corrente':>9s} {'R (ida+volta)':>14s} {'queda':>8s}")
for nome, r_m in RHO.items():
    L, I = (0.3, 0.7) if "servo" in nome or "extensor" in nome else (0.5, 2.0)
    R = 2 * L * r_m
    print(f"   {nome:28s} {L*100:6.0f} cm {I:8.2f} A {R*1000:11.0f} mOhm "
          f"{R*I*1000:6.0f} mV")
print(f"\n   contato de protoboard (1 ponto, ~30 mOhm) com 2,0 A: "
      f"{0.030*2.0*1000:.0f} mV e {0.030*2.0**2:.2f} W dissipados no contato")
print("   >> alimentar a trilha + da protoboard por UM unico ponto e o elo mais fraco.")

# ---------------------------------------------------------------- 6. veredito
print("\n" + "=" * 78)
pior_normal = max(i for n, i in cenarios if not n.startswith("G"))
falha = cenarios[-1][1]
print("VEREDITO")
print("=" * 78)
print(f"   Pior caso de OPERACAO NORMAL      : {pior_normal:.2f} A "
      f"({100*pior_normal/FONTE:.0f} % de 3 A)  -> 3 A sobra")
print(f"   Pior caso de FALHA (4 em stall)   : {falha:.2f} A "
      f"({100*falha/FONTE:.0f} % de 3 A)  -> 3 A no limite")
for cand in (3.0, 4.0, 5.0):
    print(f"   Fonte de {cand:.0f} A: margem sobre a operacao normal "
          f"{100*(cand/pior_normal - 1):3.0f} %, sobre a falha "
          f"{100*(cand/falha - 1):4.0f} %")
print("\n   Recomendacao: 5 V / 5 A chaveada (25 W). 3 A NAO impede o funcionamento,")
print("   mas nao cobre o travamento simultaneo e depende da honestidade da placa.")
print("   Manter C1 = 1000 uF (2200 uF melhor) + 100 nF ceramico em cada servo.")
