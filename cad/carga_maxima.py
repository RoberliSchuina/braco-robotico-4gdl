# -*- coding: utf-8 -*-
"""
carga_maxima.py — Peso máximo que o braço suporta na garra, com o MG996R no ombro (S2).

Mesmo modelo de corpo livre de `verificacao.py` (massas reais das malhas, braço de alavanca
horizontal em cada eixo), com três diferenças:

  1. o ombro passa a ser MG996R (9,4 kgf.cm a 4,8 V) em vez de MG90S (1,8 kgf.cm a 5 V);
  2. a forquilha do ombro alarga de Y_ELO1 = 18,80 para 26,75 mm (ver `plataforma_mg996r.py`),
     o que alonga a travessa do braço e a palma do antebraço — as chapas 03..06 são
     RECONSTRUÍDAS aqui com o novo vão para que a massa móvel seja a verdadeira;
  3. a massa do próprio MG996R NÃO entra no cálculo: ele fica na plataforma, abaixo do eixo
     do ombro, e não é carga para nenhum eixo (só para S1 e para o tombamento).

Além do torque, o script fecha os outros tetos: atrito da garra, tombamento da base de
acrílico e esmagamento do bolso do horn.

Uso:  python cad/carga_maxima.py
"""
import os, sys, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_pecas as G

DENS      = 1.24 * 0.55     # g/cm³ efetivos (PLA, 15 % infill + 3 paredes) — igual a verificacao.py
M_SG90    = 9.0
M_MG90S   = 13.4
M_MG996R  = 55.0
STALL_90  = 1.8             # kgf.cm a 5 V (SG90 e MG90S)
STALL_996 = 9.4             # kgf.cm a 4,8 V (a 6 V são 11,0; o barramento do projeto cai a ~4,6 V)
R_dedo    = G.frame((0, 0, 0), (-1, 0, 0), (0, -1, 0))
R_CARGA   = 49.0            # mm do eixo do dedo ao centro da mandíbula plana (y = 43..55 em dedo())
R_CARGA_V = 46.5            # idem para a mandíbula em V (contato nos flancos do entalhe)

_cache = {}


def corpo_local(arq, y1, y2):
    """(massa em g, centro de massa no frame local da peça) reconstruindo a peça com o vão pedido."""
    chave = (arq, y1, y2)
    if chave not in _cache:
        y1_ant, y2_ant = G.Y_ELO1, G.Y_ELO2
        G.Y_ELO1, G.Y_ELO2 = y1, y2                      # as chapas livres leem L = 2*Y_ELO* em tempo de chamada
        try:
            m = dict(G.PECAS_POR_ARQ)[arq]()
        finally:
            G.Y_ELO1, G.Y_ELO2 = y1_ant, y2_ant
        _cache[chave] = (m.volume / 1000.0 * DENS, m.center_mass.copy())
    return _cache[chave]


def corpos(th2, th3, carga_g, y1, y2, m_s3, tipo='plana'):
    """[(massa, ponto global, conta_no_cotovelo)] com o braço em th2 e o antebraço em th3 (absoluto)."""
    _, _zs2, T_br, T_an = G.poses(th2, th3)
    itens = []
    for arq, M, no_cot in [("03_braco_motriz",      T_br @ G.T(0,  y1, 0), False),
                           ("04_braco_livre",       T_br @ G.T(0, -y1, 0), False),
                           ("05_antebraco_motriz",  T_an @ G.T(0,  y2, 0), True),
                           ("06_antebraco_livre",   T_an @ G.T(0, -y2, 0), True),
                           ("07_garra_dedo_motriz", T_an @ G.T(G.ESP + 0.8,  G.Y_GARRA, G.Z_GARRA) @ R_dedo, True),
                           ("08_garra_dedo_livre",  T_an @ G.T(G.ESP + 0.8, -G.Y_GARRA, G.Z_GARRA) @ R_dedo, True)]:
        massa, com = corpo_local(arq, y1, y2)
        itens.append((massa, (M @ np.append(com, 1.0))[:3], no_cot))
    itens.append((m_s3,   (T_br @ np.array([0, y1 + G.ESP, 70, 1]))[:3], False))              # servo do cotovelo
    itens.append((M_SG90, (T_an @ np.array([G.PALMA_X[1], G.Y_GARRA, G.Z_GARRA, 1]))[:3], True))  # servo da garra
    if carga_g:
        r = R_CARGA if tipo == 'plana' else R_CARGA_V
        itens.append((carga_g, (T_an @ np.array([G.ESP + 2.8, 0, G.Z_GARRA + r, 1]))[:3], True))
    return itens, (T_br @ np.array([0, 0, 70, 1]))[:3]


def torques(th2, th3, carga_g, y1, y2, m_s3, tipo='plana'):
    """(torque no ombro, torque no cotovelo) em kgf.cm."""
    itens, p_cot = corpos(th2, th3, carga_g, y1, y2, m_s3, tipo)
    t_omb = sum(m / 1000.0 * c[0] / 10.0 for m, c, _ in itens)
    t_cot = sum(m / 1000.0 * (c[0] - p_cot[0]) / 10.0 for m, c, no_cot in itens if no_cot)
    return abs(t_omb), abs(t_cot)


def carga_max(th2, th3, y1, y2, m_s3, s_omb, s_cot, frac, tipo='plana'):
    """Maior massa na garra (g) que mantém os dois eixos abaixo de `frac` do stall."""
    lo, hi = 0.0, 3000.0
    if max(torques(th2, th3, 0.0, y1, y2, m_s3, tipo)[i] / s for i, s in ((0, s_omb), (1, s_cot))) > frac:
        return 0.0
    for _ in range(30):
        mid = (lo + hi) / 2
        a, b = torques(th2, th3, mid, y1, y2, m_s3, tipo)
        if a / s_omb <= frac and b / s_cot <= frac:
            lo = mid
        else:
            hi = mid
    return lo


def eixo_critico(th2, th3, carga, y1, y2, m_s3, s_omb, s_cot):
    a, b = torques(th2, th3, carga, y1, y2, m_s3)
    return ("ombro" if a / s_omb > b / s_cot else "cotovelo"), a / s_omb, b / s_cot


G.PECAS_POR_ARQ = {arq: construtor for arq, _n, _f, construtor, _t, _o in G.PECAS}

# vãos: original (MG90S no ombro) e novo (MG996R no ombro, ver plataforma_mg996r.py)
Y1_ORI, Y2_ORI = G.Y_ELO1, G.Y_ELO2                      # 18,80 e 33,60
Y1_996 = 26.75
Y2_996 = Y1_996 + G.ESP + G.GAP_ELO                      # cotovelo continua MG90S -> GAP 10,8

CENARIOS = [
    ("Projeto atual (MG90S no ombro)",            Y1_ORI, Y2_ORI, M_MG90S,  STALL_90,  STALL_90),
    ("MG996R no ombro, MG90S no cotovelo",        Y1_996, Y2_996, M_MG90S,  STALL_996, STALL_90),
    ("MG996R no ombro E no cotovelo (hipótese)",  Y1_996, Y2_996, M_MG996R, STALL_996, STALL_996),
]
POSES = [("alcance máximo (ombro 90°, antebraço horizontal)", 90, 90),
         ("limite do firmware (ombro 75°)",                    75, 75 + 15),
         ("braço vertical, antebraço horizontal (recolhido)",   0, 90)]

if __name__ == "__main__":
    print("== massa móvel (chapas reconstruídas com o vão de cada cenário) ==")
    for rot, y1, y2, m_s3, *_ in CENARIOS:
        tot = sum(corpo_local(a, y1, y2)[0] for a in ["03_braco_motriz", "04_braco_livre", "05_antebraco_motriz",
                                                      "06_antebraco_livre", "07_garra_dedo_motriz",
                                                      "08_garra_dedo_livre"]) + m_s3 + M_SG90
        print(f"  {rot:44s} vão {2*y1:5.1f} mm   massa móvel {tot:5.1f} g")

    print("\n== carga máxima na garra (g) — critério: nenhum eixo acima da fração do stall ==")
    print(f"  {'cenário':44s} {'pose':52s} {'60 %':>7s} {'80 %':>7s} {'100 %':>7s}  eixo crítico")
    saida = []
    for rot, y1, y2, m_s3, s_o, s_c in CENARIOS:
        for pose, th2, th3 in POSES:
            vals = [carga_max(th2, th3, y1, y2, m_s3, s_o, s_c, f) for f in (0.60, 0.80, 1.00)]
            crit, fo, fc = eixo_critico(th2, th3, vals[0], y1, y2, m_s3, s_o, s_c)
            print(f"  {rot:44s} {pose:52s} {vals[0]:7.0f} {vals[1]:7.0f} {vals[2]:7.0f}  {crit}")
            saida.append(dict(cenario=rot, pose=pose, th2=th2, th3=th3, eixo_critico=crit,
                              carga_60=round(vals[0]), carga_80=round(vals[1]), carga_100=round(vals[2])))
        print()

    print("== pior pose de toda a faixa permitida (ombro -75..75°, cotovelo 40..140° relativo) ==")
    piores = []
    for rot, y1, y2, m_s3, s_o, s_c in CENARIOS:
        pior = (1e9, None)
        for th2 in range(-75, 76, 15):
            for rel in range(40, 141, 20):
                c = carga_max(th2, th2 + rel - 0, y1, y2, m_s3, s_o, s_c, 0.60)
                if c < pior[0]:
                    pior = (c, (th2, rel))
        print(f"  {rot:44s} {pior[0]:5.0f} g a 60 % do stall  (ombro {pior[1][0]:+d}°, cotovelo {pior[1][1]}° relativo)")
        piores.append(dict(cenario=rot, carga_60_pior_pose=round(pior[0]), ombro=pior[1][0], cotovelo_rel=pior[1][1]))

    print("\n== outros tetos (independentes do torque do ombro) ==")
    for mu, sup in ((0.30, "PLA liso (plástico polido)"), (0.50, "borracha/papelão colado na mandíbula")):
        for frac, rotf in ((0.60, "60 %"), (1.00, "100 %")):
            F = STALL_90 * frac * 9.80665 / (R_CARGA / 10.0) / 1.0   # kgf.cm -> N na mandíbula
            W = 2 * mu * F / 9.80665 * 1000                          # g sustentados por atrito nas 2 mandíbulas
            print(f"  atrito da garra (S4 SG90 a {rotf} do stall, mu={mu:.2f}, {sup:38s}) {W:5.0f} g")
    # tombamento: base de acrílico (cad/base_info.json), carga a ~178 mm do eixo de S1
    bi = json.load(open(os.path.join(G.RAIZ, "cad", "base_info.json"), encoding="utf-8"))
    M0 = bi["tombamento"]["casos"]["0"]["massa_total_g"]; r0 = bi["tombamento"]["casos"]["0"]["com_r_mm"]
    borda = bi["tombamento"]["borda_apoio_mm"]; r_c = 178.0
    m_tomb = M0 * (borda - r0) / (r_c - borda)
    print(f"  tombamento da base de acrílico (CoM atinge a borda de apoio a {borda:.0f} mm)        {m_tomb:5.0f} g")
    # bolso do horn de S2: 2 braços de 5,4 x 2,5 mm a r = 14 mm transmitindo o stall do MG996R
    p = STALL_996 * 9.80665 / 100 / (14e-3) / (2 * 5.4e-3 * 2.5e-3) / 1e6
    print(f"  pressão no bolso do horn de S2 com o stall do MG996R: {p:.1f} MPa (PLA ~40 MPa) -> OK")

    with open(os.path.join(G.RAIZ, "cad", "carga_maxima.json"), "w", encoding="utf-8") as f:
        json.dump(dict(criterio="torque <= fração do stall em ombro e cotovelo",
                       stall_kgfcm=dict(mg90s=STALL_90, mg996r=STALL_996),
                       massas_g=dict(sg90=M_SG90, mg90s=M_MG90S, mg996r=M_MG996R),
                       raio_carga_mm=R_CARGA, casos=saida, pior_pose=piores,
                       tombamento_g=round(m_tomb), atrito_garra_g_mu030_60=round(
                           2 * 0.30 * (STALL_90 * 0.60 * 9.80665 / (R_CARGA / 10.0)) / 9.80665 * 1000)),
                  f, ensure_ascii=False, indent=2)
    print("\nOK -> cad/carga_maxima.json")
