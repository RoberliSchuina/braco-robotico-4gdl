# -*- coding: utf-8 -*-
"""
chapas_mg996r.py — Chapas do braço e do antebraço para a plataforma com MG996R (peças 13..16).

Peças NOVAS; 03..06 (versão MG90S) continuam intactas. São as chapas que fecham a forquilha da
peça 12 (`cad/plataforma_mg996r.py`): sem elas a plataforma nova não monta.

  13_braco_motriz_mg996r      <- 03, com bolso do horn de 25 dentes do MG996R
  14_braco_livre_mg996r       <- 04, travessa de 6 mm e vão 53,50 mm
  15_antebraco_motriz_mg996r  <- 05, furos da palma reposicionados
  16_antebraco_livre_mg996r   <- 06, palma de 6 mm e vão 83,10 mm

O que muda e por quê
--------------------
* **Y_ELO1 = 26,75 mm** (era 18,80): imposto pelo corpo do MG996R, que desce 26,5 mm abaixo das
  abas e empurra a parede livre da plataforma. Y_ELO2 = Y_ELO1 + 4 + 10,8 = 41,55 (o cotovelo
  continua MG90S, então o GAP dele não muda).
* **Bolso do horn do ombro** passa a ser o do horn 25T do MG996R: cubo maior, braço mais largo e
  2,5 mm de profundidade (o braço do horn 25T é mais grosso que o do MG90S). O bolso **abre na
  borda** da chapa (braço até r = 18 contra r = 17 do perfil): o horn do MG996R é mais comprido
  que a extremidade da chapa e a sobra fica no ar, sem lábio para bater. Não é preciso cortar o horn.
* **Travessa 4 -> 6 mm** e **palma 4 -> 6 mm**: o vão cresceu 42 % (braço) e 24 % (antebraço), e a
  rigidez de uma viga cai com o cubo do vão. A travessa engrossou para DENTRO (x = -17..-11, segue
  dentro do perfil, nada no ar na impressão) e a palma para FORA (x = -16..-10), mantendo a face de
  apoio de S4 em x = -10 — ou seja, a garra, as engrenagens e os dedos 07/08 (ou 10/11) não mudam.
  Os parafusos passaram para o centro das vigas novas: x = -14 (travessa) e -13 (palma).
* O que NÃO muda: perfis das chapas, janelas, mancal/munhão Ø9, servo do cotovelo (MG90S), posição
  da garra no antebraço, bolso do horn do cotovelo e da garra, e a pose de referência.

Cotas do horn 25T são de catálogo (ver constantes HORN996_*): **MEDIR o horn do servo e regerar**
antes de imprimir — mesma disciplina do corpo do MG996R.

Uso:  python cad/chapas_mg996r.py            (gera, verifica e renderiza)
      python cad/chapas_mg996r.py --rapido   (pula a varredura de colisão do cotovelo)
"""
import os, sys, json, math
import numpy as np
import trimesh
from shapely.geometry import Point
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_pecas as G
import plataforma_mg996r as PL

RAPIDO = "--rapido" in sys.argv

# ------------------------------------------------------------------ cotas novas
Y1 = PL.Y_ELO1_996                      # 26,75: face interna das chapas do braço
Y2 = Y1 + G.ESP + G.GAP_ELO             # 41,55: face interna das chapas do antebraço
TRAV_X  = (-17.0, -11.0);  TRAV_CX  = -14.0     # travessa 6 mm e eixo dos 2 parafusos
PALMA_X = (-16.0, -10.0);  PALMA_CX = -13.0     # palma 6 mm; face de apoio de S4 continua em x = -10

# ------------------------------------------------------------------ horn 25T do MG996R — MEDIR
HORN996_R_CUBO  = 5.55     # cubo Ø10,5 + 0,3 mm de folga por lado
HORN996_R_PONTA = 3.60     # meia-largura na ponta do braço (7,2 mm)
HORN996_BRACO   = 18.0     # comprimento do bolso: 1 mm além do perfil (r = 17) -> abre na borda
HORN996_FUROS   = (9.0, 13.0)   # raios dos furos-piloto Ø1,7 em cada braço
BOLSO996        = 2.5      # espessura do braço do horn 25T
FURO_CENTRAL    = 3.4      # parafuso central M3 + arruela ampla (se o kit vier M4, abrir p/ 4,3)


def corte_horn_996():
    """Bolso do horn 25T 'duplo' (face em z=0, entrando em +z) + furo central + furos-piloto.
    Mesma receita de G.corte_horn: cubo unido a um tronco de cone por braço (o braço do horn sai
    tangente ao cubo e afina até a ponta; um rasgo reto deixaria material e o horn não assentaria)."""
    cubo = Point(0, 0).buffer(HORN996_R_CUBO, 64)
    formas = [cubo]
    for ang in (0.0, 180.0):
        a = math.radians(ang)
        ponta = Point(HORN996_BRACO * math.cos(a), HORN996_BRACO * math.sin(a)).buffer(HORN996_R_PONTA, 64)
        formas.append(unary_union([cubo, ponta]).convex_hull)
    bolso = G.extrude_polygon(unary_union(formas), BOLSO996 + 1)
    bolso.apply_translation([0, 0, -1])                       # z = -1 .. BOLSO996
    partes = [bolso, G.cyl(FURO_CENTRAL / 2, 12)]
    partes += [G.cyl(0.85, 12, (s * r, 0, 0)) for r in HORN996_FUROS for s in (-1, 1)]
    return G.uniao(*partes)


# ------------------------------------------------------------------ peças
def braco_motriz():
    """13: chapa MOTRIZ do braço — bolso do horn do MG996R (S2) na face interna e servo S3 (MG90S)
    com o flange na face externa."""
    corpo = G.chapa(G.PERFIL_BRACO); corpo.apply_translation([0, G.ESP, 0])
    janela = G.box(-8, 8, -1, G.ESP + 1, 22, 52)
    horn = G.coloca(corte_horn_996(), (0, 0, 0), (0, 1, 0), (0, 0, 1))
    servo = G.coloca(G.corte_servo(), (0, G.ESP, 70), (0, 1, 0), (0, 0, -1))
    trav = [G.cyl(G.PASS_M3 / 2, 20, (TRAV_CX, G.ESP / 2, z), 'y') for z in G.TRAV_FUROS_Z]
    return G.subtrai(corpo, janela, horn, servo, *trav)


def braco_livre():
    """14: chapa LIVRE do braço — munhão Ø9 no mancal da parede livre da plataforma, mancal do
    cotovelo e travessa de 6 mm que amarra as duas chapas (2 x M3 x 10)."""
    corpo = G.chapa(G.PERFIL_BRACO)
    munhao = G.cyl(G.MUNHAO_D / 2, 9.8, (0, 3.9, 0), 'y')                 # y = -1 .. 8,8
    L = 2 * Y1                                                            # 53,50
    trav = G.box(TRAV_X[0], TRAV_X[1], -1, L, *G.TRAV_Z)
    pad = G.box(-17, -9, L - 8, L, *G.TRAV_Z)                             # material em volta dos furos
    corpo = G.uniao(corpo, munhao, trav, pad)
    janela = G.box(-8, 8, -G.ESP - 1, 1, 22, 52)
    cotovelo = G.cyl((G.MUNHAO_D + G.MUNHAO_FOLGA) / 2, 12, (0, -2, 70), 'y')
    pil = [G.cyl(G.PIL_M3 / 2, 8.4, (TRAV_CX, L - 4, z), 'y') for z in G.TRAV_FUROS_Z]
    return G.subtrai(corpo, janela, cotovelo, *pil)


def antebraco_motriz():
    """15: chapa MOTRIZ do antebraço — bolso do horn de S3 (MG90S, inalterado) e os 2 furos
    passantes da palma, agora em x = -13."""
    corpo = G.chapa(G.PERFIL_ANTE); corpo.apply_translation([0, G.ESP, 0])
    janela = G.box(-8, 8, -1, G.ESP + 1, 20, 44)
    horn = G.coloca(G.corte_horn('duplo'), (0, 0, 0), (0, 1, 0), (0, 0, 1))
    palma = [G.cyl(G.PASS_M3 / 2, 20, (PALMA_CX, G.ESP / 2, z), 'y') for z in G.PALMA_FUROS_Z]
    return G.subtrai(corpo, janela, horn, *palma)


def antebraco_livre():
    """16: chapa LIVRE do antebraço + PALMA de 6 mm. S4 continua aparafusado na face interna da
    palma (x = -10) e o pino M3 do dedo livre continua atravessando-a."""
    corpo = G.chapa(G.PERFIL_ANTE)
    munhao = G.cyl(G.MUNHAO_D / 2, G.GAP_ELO + G.ESP + 1, (0, (G.GAP_ELO + G.ESP - 1) / 2, 0), 'y')
    L = 2 * Y2                                                            # 83,10
    palma = G.box(PALMA_X[0], PALMA_X[1], -1, L, *G.PALMA_Z)
    pads = [G.box(PALMA_X[0], -6, L - 8, L, z - 5, z + 5) for z in G.PALMA_FUROS_Z]
    corpo = G.uniao(corpo, munhao, palma, *pads)
    janela = G.box(-8, 8, -G.ESP - 1, 1, 20, 44)
    servo = G.coloca(G.corte_servo(), (PALMA_X[1], Y2 + G.Y_GARRA, G.Z_GARRA), (1, 0, 0), (0, -1, 0))
    pino = G.cyl(G.PASS_M3 / 2, 14, (PALMA_CX, Y2 - G.Y_GARRA, G.Z_GARRA), 'x')
    pil = [G.cyl(G.PIL_M3 / 2, 8.4, (PALMA_CX, L - 4, z), 'y') for z in G.PALMA_FUROS_Z]
    jan_palma = G.box(PALMA_X[0] - 1, PALMA_X[1] + 1, 3, 16, 52, 74)
    return G.subtrai(corpo, janela, servo, pino, jan_palma, *pil)


PECAS = [("13_braco_motriz_mg996r",     "Braço — chapa motriz (MG996R)",     braco_motriz,
          G.T(0, 0, G.ESP) @ G.Rx(-90), "Deitada, bolso do horn para cima. Sem suportes."),
         ("14_braco_livre_mg996r",      "Braço — chapa livre (MG996R)",      braco_livre,
          G.T(0, 0, G.ESP) @ G.Rx(90),  "Deitada, munhão e travessa (6 mm) para cima. Sem suportes."),
         ("15_antebraco_motriz_mg996r", "Antebraço — chapa motriz (MG996R)", antebraco_motriz,
          G.T(0, 0, G.ESP) @ G.Rx(-90), "Deitada, bolso do horn para cima. Sem suportes."),
         ("16_antebraco_livre_mg996r",  "Antebraço — chapa livre + palma (MG996R)", antebraco_livre,
          G.T(0, 0, G.ESP) @ G.Rx(90),  "Deitada, palma em pé (83 mm). Ponte de 23 mm no teto do rasgo de S4.")]


# ------------------------------------------------------------------ montagem (peças 12..16 + dedos)
def montagem(P, th1=0.0, th2=30.0, th3=95.0, alfa=15.0):
    z_plat, z_s2, T_br, T_an = G.poses(th2, th3)
    R_dedo = G.frame((0, 0, 0), (-1, 0, 0), (0, -1, 0))
    itens = [(PL.plataforma_mg996r(), G.T(0, 0, z_plat), "#f0a04b"),
             (P["13"], T_br @ G.T(0,  Y1, 0), "#5aa469"), (P["14"], T_br @ G.T(0, -Y1, 0), "#78c08a"),
             (P["15"], T_an @ G.T(0,  Y2, 0), "#e06666"), (P["16"], T_an @ G.T(0, -Y2, 0), "#ef8f8f"),
             (G.dedo(True),  T_an @ G.T(G.ESP + 0.8,  G.Y_GARRA, G.Z_GARRA) @ G.Rx(-alfa) @ R_dedo, "#8e7cc3"),
             (G.dedo(False), T_an @ G.T(G.ESP + 0.8, -G.Y_GARRA, G.Z_GARRA) @ G.Rx(alfa) @ R_dedo, "#a694d6"),
             (PL.mg996r_dummy(), G.T(0, 0, z_plat) @ G.frame((0, PL.Y_FLANGE, PL.Z_S2), (0, 1, 0), (1, 0, 0)),
              "#333333"),
             (G.servo_dummy(), T_br @ G.frame((0, Y1 + G.ESP, 70), (0, 1, 0), (0, 0, -1)), "#333333"),
             (G.servo_dummy(), T_an @ G.frame((G.PALMA_X[1], Y2 + G.Y_GARRA, G.Z_GARRA), (1, 0, 0), (0, -1, 0)),
              "#333333")]
    saida = []
    for m, M, cor in itens:
        mm = m.copy(); mm.apply_transform(M); mm.apply_transform(G.Rz(th1))
        saida.append((mm, cor))
    return saida


def inter_vol(a, b):
    """Volume (mm³) da interseção; 0 se vazia (o engine pode devolver None ou malha vazia)."""
    r = trimesh.boolean.intersection([a, b], engine='manifold')
    return 0.0 if r is None or r.is_empty else float(r.volume)


def grupo_antebraco(P, th2, th3):
    _, _z, _T, T_an = G.poses(th2, th3)
    out = []
    for k, y in (("15", Y2), ("16", -Y2)):
        m = P[k].copy(); m.apply_transform(T_an @ G.T(0, y, 0)); out.append(m)
    return out


if __name__ == "__main__":
    print(f"Y_ELO1 = {Y1:.2f} mm (era {18.8})   Y_ELO2 = {Y2:.2f} mm (era {33.6})"
          f"   travessa L = {2*Y1:.2f}   palma L = {2*Y2:.2f}")
    P, info = {}, []
    for arq, nome, construtor, Timp, obs in PECAS:
        m = construtor()
        assert m.is_watertight, f"{arq}: malha não é estanque"
        P[arq[:2]] = m
        mi = G.exporta_peca(arq, m, Timp)
        dx, dy, dz = mi.extents
        vol = m.volume / 1000.0; massa = vol * 1.24 * 0.55
        print(f"  {arq:28s} {dx:6.1f} x {dy:6.1f} x {dz:6.1f} mm  vol={vol:5.1f} cm3  ~{massa:4.1f} g")
        info.append(dict(arquivo=arq + ".stl", nome=nome, dimensoes_mm=[round(dx, 1), round(dy, 1), round(dz, 1)],
                         volume_solido_cm3=round(vol, 1), massa_estimada_g=round(massa, 1),
                         tempo_estimado_min=int(round(massa / 20 * 60)), impressao=obs))

    print("\n== verificação ==")
    ok = True
    def diz(rotulo, valor, cond):
        global ok
        ok = ok and bool(cond)
        print(f"  [{'OK ' if cond else 'FALHA'}] {rotulo}: {valor}")

    plat = PL.plataforma_mg996r()
    z_plat = G.poses(0, 90)[0]

    # 1. munhão do braço dentro do mancal da plataforma, sem tocar a parede
    mun_g = G.cyl(G.MUNHAO_D / 2, 9.8, (0, -Y1 + 3.9, PL.Z_S2), 'y')
    i1 = inter_vol(plat, mun_g)
    diz("munhão do braço x plataforma", f"{i1:.3f} mm3", i1 < 1.0)
    diz("penetração do munhão no mancal", f"{(-Y1 + 8.8) - PL.Y_PAR_B[0]:.2f} mm de 7,00",
        (-Y1 + 8.8) - PL.Y_PAR_B[0] > 6.5)

    # 2. horn do MG996R: o bolso tem de conter o braço do horn com folga
    folga = HORN996_R_CUBO - 5.25, HORN996_R_PONTA - 3.0
    diz("folga do bolso no cubo e na ponta do horn", f"{folga[0]:.2f} / {folga[1]:.2f} mm", min(folga) >= 0.25)
    diz("bolso abre na borda da chapa", f"braço {HORN996_BRACO:.1f} mm > perfil 17,0 mm", HORN996_BRACO > 17.0)
    diz("material sob o bolso do horn", f"{G.ESP - BOLSO996:.2f} mm", G.ESP - BOLSO996 >= 1.5)

    # 3. chapas x plataforma na pose de repouso e em todo o giro do ombro
    pior = 0.0
    for th2 in range(-75, 76, 25):
        for k, y in (("13", Y1), ("14", -Y1)):
            m = P[k].copy(); m.apply_transform(G.poses(th2, th2 + 90)[2] @ G.T(0, y, 0))
            pior = max(pior, inter_vol(m, plat))
    diz("chapas do braço x plataforma (ombro -75..75°)", f"{pior:.2f} mm3", pior < 1.0)

    # 4. limite do cotovelo: a palma encosta na parede da plataforma
    limite, pose_lim = None, None
    if not RAPIDO:
        for rel in range(120, 181, 10):          # ângulo RELATIVO braço<->antebraço (= ângulo de S3)
            for th2 in range(-75, 76, 25):       # o ombro muda a posição da plataforma em relação à palma
                if any(inter_vol(m, plat) > 0.5 for m in grupo_antebraco(P, th2, th2 + rel)):
                    limite, pose_lim = rel, th2
                    break
            if limite:
                break
        diz("limite do cotovelo (antebraço x plataforma, ombro -75..75°)",
            "sem contato até 180°" if limite is None else f"{limite}° com o ombro em {pose_lim:+d}° (era 148°)",
            limite is None or limite >= 140)

    # 5. carga útil com as massas REAIS das peças novas
    import carga_maxima as C
    C._cache[("03_braco_motriz", Y1, Y2)] = (P["13"].volume / 1000.0 * C.DENS, P["13"].center_mass.copy())
    C._cache[("04_braco_livre", Y1, Y2)] = (P["14"].volume / 1000.0 * C.DENS, P["14"].center_mass.copy())
    C._cache[("05_antebraco_motriz", Y1, Y2)] = (P["15"].volume / 1000.0 * C.DENS, P["15"].center_mass.copy())
    C._cache[("06_antebraco_livre", Y1, Y2)] = (P["16"].volume / 1000.0 * C.DENS, P["16"].center_mass.copy())
    carga = C.carga_max(90, 90, Y1, Y2, C.M_MG90S, C.STALL_996, C.STALL_90, 0.60)
    carga100 = C.carga_max(90, 90, Y1, Y2, C.M_MG90S, C.STALL_996, C.STALL_90, 1.00)
    t_omb, t_cot = C.torques(90, 90, carga, Y1, Y2, C.M_MG90S)
    print(f"  [INFO] carga útil com as peças reais: {carga:.0f} g a 60 % do stall ({carga100:.0f} g a 100 %)"
          f"  — ombro {t_omb:.2f} kgf.cm ({100*t_omb/C.STALL_996:.0f} %), cotovelo {t_cot:.2f} ({100*t_cot/C.STALL_90:.0f} %)")

    with open(os.path.join(G.RAIZ, "cad", "chapas_mg996r_info.json"), "w", encoding="utf-8") as f:
        json.dump(dict(y_elo1=Y1, y_elo2=round(Y2, 2), travessa_mm=round(2 * Y1, 2), palma_mm=round(2 * Y2, 2),
                       travessa_x=TRAV_X, palma_x=PALMA_X, horn_25t=dict(r_cubo=HORN996_R_CUBO,
                       r_ponta=HORN996_R_PONTA, braco=HORN996_BRACO, bolso=BOLSO996, furo_central=FURO_CENTRAL),
                       limite_cotovelo_graus=limite, carga_util_60_g=round(carga), carga_util_100_g=round(carga100),
                       verificacao_ok=bool(ok), pecas=info), f, ensure_ascii=False, indent=2)

    G.render(montagem(P, th1=0, th2=0, th3=90), os.path.join(G.DIR_IMG, "montagem_mg996r.png"),
             [("Braço com MG996R no ombro — posição de repouso", 22, -55), ("Vista frontal", 0, -90),
              ("Vista lateral", 0, 0), ("Vista superior", 90, -90)])
    G.render(montagem(P, th1=-20, th2=55, th3=90, alfa=18), os.path.join(G.DIR_IMG, "montagem_mg996r_captura.png"),
             [("Captura na horizontal com o ombro MG996R", 18, -60)])
    print("\nOK ->", G.DIR_STL)
    sys.exit(0 if ok else 1)
