# -*- coding: utf-8 -*-
"""
plataforma_mg996r.py — Plataforma giratória REDESENHADA para um servo MG996R no ombro (S2).

NÃO substitui a peça 02 (`02_plataforma_giratoria.stl`, para MG90S/SG90): gera uma peça NOVA,
`STL/12_plataforma_giratoria_mg996r.stl`. As duas convivem — é só escolher qual imprimir.

O que muda em relação à peça 02
-------------------------------
O MG996R (40 x 19 x 43 mm) é ~3x o volume do MG90S (22,8 x 12,2), e o que manda na arquitetura é
o quanto o corpo desce ABAIXO da face de apoio das abas: 26,5 mm contra 15,9 mm do MG90S. Como o
servo do ombro fica DENTRO da forquilha, com o flange na parede motriz e o corpo entrando no vão,
esse comprimento define onde a parede livre (mancal do munhão) pode ficar — e, por simetria em
y = 0, onde ficam as chapas laterais do braço:

    MG90S  : vão interno da forquilha do ombro = 2 x 18,80 = 37,6 mm   (peça 02)
    MG996R : vão interno da forquilha do ombro = 2 x Y_ELO1_996 mm     (esta peça; ver saída)

Ou seja: esta peça só monta com chapas do braço (peças 03 e 04) refeitas com o novo Y_ELO1 e com
o bolso do horn de 25 dentes do MG996R. A peça está correta e verificada por si; a adaptação das
chapas do braço é o passo seguinte (os números a usar são impressos no fim deste script).

Mantidos de propósito (para não invalidar o resto do projeto):
  * interface com S1 — bolso do horn 'cruz' do MG90S na face inferior, mesmo furo central e mesmos
    8 furos-piloto: a base fixa (peça 01) continua servindo sem alteração;
  * altura do eixo do ombro em z = 28 mm acima da face inferior da plataforma — a cinemática
    (`cad/mapa_angulos.py`, alcance/altura do relatório) continua valendo;
  * mancal Ø9,4 para o munhão Ø9 impresso na chapa livre do braço, no eixo do ombro;
  * folga para as 4 colunas de encosto da base (r = 24,5 mm), que recebem o momento de tombamento.

Dimensões do MG996R: 40 x 19 x 43 mm foram informadas pelo usuário; as demais (altura abaixo das
abas, 49,5 mm entre centros dos furos, deslocamento do eixo) seguem o padrão "standard servo".
TODAS estão em constantes abaixo: MEDIR o servo recebido, ajustar e regerar antes de imprimir —
mesma disciplina já adotada para o KY-023 e o DSN-VC288.

Uso:  python cad/plataforma_mg996r.py
"""
import os, sys, json
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString, Point
from trimesh.creation import extrude_polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_pecas import (box, cyl, uniao, subtrai, coloca, corte_horn, exporta_peca, render,
                         ESP, MUNHAO_D, MUNHAO_FOLGA, PASS_M3, DIR_STL, DIR_IMG, RAIZ)

ARQ = "12_plataforma_giratoria_mg996r"

# ------------------------------------------------------------------ servo MG996R (mm) — MEDIR
SV_L, SV_W, SV_H = 40.0, 19.0, 43.0   # corpo, informado pelo usuário (catálogo: 40,7 x 19,7 x 42,9)
RASGO_L, RASGO_W = 41.4, 20.4          # rasgo na parede: aceita 40,0 e também o corpo "cheio" de 40,7
ABAIXO    = 26.5   # corpo abaixo da face de apoio das abas  <-- cota que define a forquilha
FLANGE_T  = 2.5    # espessura das abas
ACIMA     = 9.7    # caixa de engrenagens acima das abas
EIXO      = 4.2    # cubo estriado + eixo acima da caixa   (26,5 + 2,5 + 9,7 + 4,2 = 42,9 = altura total)
FURO_X    = 24.75  # abas: 49,5 mm entre centros (padrão standard servo)
FURO_Y    = 5.0    # 10 mm entre os dois furos de cada aba
ABA_L     = 27.0   # meia-extensão das abas (54 mm no total)
DESLOC    = 10.0   # eixo de saída deslocado do centro do corpo (eixo a 10 mm da extremidade)
HORN_TOPO = FLANGE_T + ACIMA + 6.0    # 18,2: face superior do horn 25T acima da face de apoio
BOLSO     = 2.5                       # profundidade do bolso do horn na chapa do braço (horn mais grosso)
GAP996    = HORN_TOPO - BOLSO         # 15,7: face de apoio do servo -> face interna da chapa motriz

# ------------------------------------------------------------------ forquilha do ombro
Z_S2        = 28.0   # altura do eixo do ombro (igual à peça 02: cinemática preservada)
T_PAR_A     = 6.0    # parede motriz (era 4,0: o MG996R tem 9,4 kgf.cm e 4 parafusos M3)
T_PAR_B     = 7.0    # parede livre: 7 mm de mancal no próprio corpo, sem ressalto
FOLGA_CORPO = 3.0    # fundo do servo -> face interna da parede livre
FOLGA_CHAPA = 1.3    # face externa da parede livre -> face interna da chapa livre do braço

# Layout axial: simetria em y = 0 (mantém o centro de massa sobre o eixo da base, como na peça 02)
D_LIVRE    = FOLGA_CHAPA + T_PAR_B + FOLGA_CORPO + ABAIXO   # do flange até a chapa livre do braço
Y_FLANGE   = (D_LIVRE - GAP996) / 2.0                       # face de apoio do servo (parede motriz)
Y_ELO1_996 = Y_FLANGE + GAP996                              # face interna das chapas do braço (|y|)
Y_PAR_A    = (Y_FLANGE - T_PAR_A, Y_FLANGE)                 # parede motriz
Y_FUNDO    = Y_FLANGE - ABAIXO                              # fundo do corpo do servo
Y_PAR_B    = (Y_FUNDO - FOLGA_CORPO - T_PAR_B, Y_FUNDO - FOLGA_CORPO)   # parede livre

# Paredes e nervuras
PAR_A_X = (DESLOC - FURO_X - 4.25, DESLOC + FURO_X + 4.75)   # abrange as abas com borda >= 4 mm
PAR_B_X = (-15.0, 15.0)
Z_TOPO  = Z_S2 + RASGO_W / 2 + 4.3                            # topo das paredes
Z_NERV  = Z_S2 - RASGO_W / 2 - 0.8                            # nervuras baixas: sob o corpo do servo
Z_NERV_TOPO = Z_S2 + RASGO_W / 2 + 0.8                        # nervura alta: sobre o corpo do servo
NERV_X  = [(-10.0, -4.0), (4.0, 10.0)]                        # fora das abas (porcas M3 livres em x = -14,75)

# Placa de base (retângulo arredondado): cobre o bolso do horn de S1, o pé das duas paredes e as
# 4 colunas de encosto da base em (+-17,3; +-17,3). O disco Ø60 da peça 02 não alcança a parede livre.
PLACA_X = (-22.0, PAR_A_X[1])
PLACA_Y = (Y_PAR_B[0], 22.0)
PLACA_R = 6.0
CABO    = ((18.0, -9.0), (26.0, -9.0), 3.0)   # rasgo do cabo de S2 (LineString engrossada)


# ------------------------------------------------------------------ cortadores
def corte_mg996r():
    """Rasgo passante do corpo do MG996R + 4 furos Ø3,4 das abas, no sistema canônico do servo
    (eixo de saída na origem apontando +z, corpo ao longo de x, face de apoio das abas em z = 0)."""
    rasgo = box(DESLOC - RASGO_L / 2, DESLOC + RASGO_L / 2, -RASGO_W / 2, RASGO_W / 2, -35, 35)
    furos = [cyl(PASS_M3 / 2, 40, (DESLOC + sx * FURO_X, sy * FURO_Y, 0))
             for sx in (-1, 1) for sy in (-1, 1)]
    return uniao(rasgo, *furos)


def mg996r_dummy():
    """Volume aproximado do MG996R (verificação e render), no sistema canônico do servo."""
    corpo = box(DESLOC - SV_L / 2, DESLOC + SV_L / 2, -SV_W / 2, SV_W / 2, -ABAIXO, FLANGE_T + ACIMA)
    abas  = box(DESLOC - ABA_L, DESLOC + ABA_L, -SV_W / 2, SV_W / 2, 0, FLANGE_T)
    eixo  = cyl(3.0, EIXO + 0.2, (0, 0, FLANGE_T + ACIMA + EIXO / 2))
    return uniao(corpo, abas, eixo)


def placa_poly():
    x0, x1 = PLACA_X; y0, y1 = PLACA_Y; r = PLACA_R
    return Polygon([(x0 + r, y0 + r), (x1 - r, y0 + r), (x1 - r, y1 - r), (x0 + r, y1 - r)]).buffer(r, 64)


# ------------------------------------------------------------------ peça
def plataforma_mg996r():
    """Plataforma giratória para MG996R no ombro: placa fixada no horn de S1 + forquilha de duas
    paredes (motriz com o servo, livre com o mancal do munhão) amarradas por 3 nervuras."""
    placa = extrude_polygon(placa_poly(), ESP)                         # z = 0..4
    parA = box(*PAR_A_X, *Y_PAR_A, 3, Z_TOPO)                          # entra 1 mm na placa
    parB = box(*PAR_B_X, *Y_PAR_B, 3, Z_TOPO)
    # nervuras: penetram 1 mm em cada parede (encostar apenas gera aresta não-manifold)
    y_n = (Y_PAR_B[1] - 1.0, Y_PAR_A[0] + 1.0)
    nerv = [box(a, b, *y_n, 3, Z_NERV) for a, b in NERV_X]
    nerv.append(box(NERV_X[0][0], NERV_X[1][1], *y_n, Z_NERV_TOPO, Z_TOPO))   # ponte de 23,5 mm
    corpo = uniao(placa, parA, parB, *nerv)

    horn   = coloca(corte_horn('cruz'), (0, 0, 0), (0, 0, 1), (1, 0, 0))      # horn de S1 (MG90S)
    servo  = coloca(corte_mg996r(), (0, Y_FLANGE, Z_S2), (0, 1, 0), (1, 0, 0))
    mancal = cyl((MUNHAO_D + MUNHAO_FOLGA) / 2, 20, (0, sum(Y_PAR_B) / 2, Z_S2), 'y')
    (ax, ay), (bx, by), rc = CABO
    cabo = extrude_polygon(LineString([(ax, ay), (bx, by)]).buffer(rc, 32), ESP + 2)
    cabo.apply_translation([0, 0, -1])
    return subtrai(corpo, horn, servo, mancal, cabo)


# ------------------------------------------------------------------ verificação
def verifica(m):
    np.seterr(divide="ignore", invalid="ignore")   # malha vazia (volume 0) no center_mass
    ok = True
    def diz(rotulo, valor, cond):
        nonlocal ok
        ok = ok and cond
        print(f"  [{'OK ' if cond else 'FALHA'}] {rotulo}: {valor}")

    inter = trimesh.boolean.intersection([m, coloca(mg996r_dummy(), (0, Y_FLANGE, Z_S2), (0, 1, 0), (1, 0, 0))],
                                         engine='manifold')
    diz("interferência peça x corpo do MG996R", f"{inter.volume:.3f} mm3", inter.volume < 1.0)

    # munhão Ø9 da chapa livre do braço (9,8 mm, como na peça 04) entrando no mancal
    y0 = -Y_ELO1_996
    mun = cyl(MUNHAO_D / 2, 9.8, (0, y0 + 4.9, Z_S2), 'y')
    i2 = trimesh.boolean.intersection([m, mun], engine='manifold')
    diz("interferência peça x munhão do braço", f"{i2.volume:.3f} mm3", i2.volume < 1.0)

    # chapa livre do braço (4 mm, face interna em -Y_ELO1) não pode raspar na placa nem na parede livre
    chapa_livre = box(-40, 55, y0 - ESP, y0, 0, Z_TOPO + 20)
    i3 = trimesh.boolean.intersection([m, chapa_livre], engine='manifold')
    diz("interferência peça x chapa livre do braço", f"{i3.volume:.3f} mm3", i3.volume < 1.0)

    diz("folga fundo do servo -> parede livre", f"{Y_FUNDO - Y_PAR_B[1]:.2f} mm", Y_FUNDO - Y_PAR_B[1] >= 2.0)
    diz("folga parede livre -> chapa livre", f"{Y_PAR_B[0] - y0:.2f} mm", Y_PAR_B[0] - y0 > 0.8)
    diz("folga nervura baixa -> corpo do servo", f"{Z_S2 - SV_W / 2 - Z_NERV:.2f} mm", Z_S2 - SV_W / 2 - Z_NERV > 0.5)
    diz("folga nervura alta -> corpo do servo", f"{Z_NERV_TOPO - (Z_S2 + SV_W / 2):.2f} mm",
        Z_NERV_TOPO - (Z_S2 + SV_W / 2) > 0.5)
    diz("material entre rasgo e furo da aba", f"{FURO_X - RASGO_L / 2 - PASS_M3 / 2:.2f} mm",
        FURO_X - RASGO_L / 2 - PASS_M3 / 2 > 1.5)

    # pé das paredes todo apoiado na placa (nada no ar na impressão, disco para baixo)
    pol = placa_poly()
    cantos = [(x, y) for x in PAR_A_X for y in Y_PAR_A] + [(x, y) for x in PAR_B_X for y in Y_PAR_B]
    fora = [c for c in cantos if not pol.buffer(1e-6).contains(Point(c))]
    diz("cantos das paredes sobre a placa", f"{len(cantos) - len(fora)}/{len(cantos)}", not fora)

    # colunas de encosto da base (r = 24,5 em 45/135/225/315 graus) sob a placa
    cob = [pol.contains(Point(24.5 * np.cos(a), 24.5 * np.sin(a)).buffer(2.0, 32))
           for a in np.radians([45, 135, 225, 315])]
    diz("colunas de encosto cobertas pela placa", f"{sum(cob)}/4", sum(cob) == 4)

    cm = m.center_mass
    diz("centro de massa fora do eixo de S1", f"{np.hypot(cm[0], cm[1]):.1f} mm (x={cm[0]:.1f}, y={cm[1]:.1f})",
        np.hypot(cm[0], cm[1]) < 14.0)
    return ok


if __name__ == "__main__":
    print("MG996R: corpo %.1f x %.1f x %.1f mm | abaixo das abas %.1f | furos %.1f entre centros"
          % (SV_L, SV_W, SV_H, ABAIXO, 2 * FURO_X))
    m = plataforma_mg996r()
    assert m.is_watertight, "malha não é estanque"
    mi = exporta_peca(ARQ, m, np.eye(4))
    dx, dy, dz = mi.extents
    vol = m.volume / 1000.0
    massa = vol * 1.24 * 0.55
    print(f"\n{ARQ}.stl  {dx:.1f} x {dy:.1f} x {dz:.1f} mm   vol={vol:.1f} cm3   ~{massa:.1f} g   faces={len(m.faces)}")

    print("\nVerificação:")
    ok = verifica(m)

    print("\nLayout axial da forquilha do ombro (y = 0 é o plano de rotação da base):")
    print(f"  parede motriz (6 mm) ............ y = {Y_PAR_A[0]:+.2f} .. {Y_PAR_A[1]:+.2f}"
          f"   (flange do MG996R em y = {Y_FLANGE:+.2f})")
    print(f"  corpo do servo .................. y = {Y_FUNDO:+.2f} .. {Y_FLANGE:+.2f}")
    print(f"  parede livre (7 mm, mancal Ø9,4)  y = {Y_PAR_B[0]:+.2f} .. {Y_PAR_B[1]:+.2f}")
    print(f"  chapas do braço (faces internas)  y = {-Y_ELO1_996:+.2f} e {Y_ELO1_996:+.2f}"
          f"   -> Y_ELO1 = {Y_ELO1_996:.2f} mm (era 18,80)")
    print(f"  travessa da chapa livre (peça 04) L = {2 * Y_ELO1_996:.2f} mm (era 37,60)")
    print(f"  bolso do horn 25T na peça 03 .... {BOLSO:.1f} mm de profundidade, GAP = {GAP996:.2f} mm (era 10,80)")

    info = dict(arquivo=ARQ + ".stl", nome="Plataforma giratória (MG996R)",
                funcao="Fixa no horn de S1; forquilha do ombro para servo MG996R (parede motriz + mancal)",
                servo_s2="MG996R", dimensoes_mm=[round(dx, 1), round(dy, 1), round(dz, 1)],
                volume_solido_cm3=round(vol, 1), massa_estimada_g=round(massa, 1),
                tempo_estimado_min=int(round(massa / 20 * 60)), triangulos=len(m.faces),
                eixo_ombro_z_mm=Z_S2, y_flange_mm=round(Y_FLANGE, 2),
                y_elo1_requerido_mm=round(Y_ELO1_996, 2), travessa_braco_mm=round(2 * Y_ELO1_996, 2),
                gap_horn_mm=round(GAP996, 2), verificacao_ok=bool(ok),
                mg996r_mm=dict(corpo=[SV_L, SV_W, SV_H], abaixo_das_abas=ABAIXO, flange_t=FLANGE_T,
                               acima=ACIMA, eixo=EIXO, furos_entre_centros=2 * FURO_X,
                               furos_por_aba=2 * FURO_Y, desloc_eixo=DESLOC),
                impressao="Placa para baixo (bolso do horn na 1ª camada). Sem suportes. "
                          "Nervura alta faz ponte de %.1f mm." % (Y_PAR_A[0] - Y_PAR_B[1]))
    with open(os.path.join(RAIZ, "cad", "plataforma_mg996r_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    servo = coloca(mg996r_dummy(), (0, Y_FLANGE, Z_S2), (0, 1, 0), (1, 0, 0))
    render([(m, "#f0a04b"), (servo, "#333333")], os.path.join(DIR_IMG, "plataforma_mg996r.png"),
           [("Plataforma giratória para MG996R (S2) — isométrica", 25, -55),
            ("Vista frontal (+X à direita)", 0, -90),
            ("Vista lateral (corpo do servo entre as paredes)", 0, 0),
            ("Vista superior", 90, -90)])
    print("\nOK ->", os.path.join(DIR_STL, ARQ + ".stl"))
    if not ok:
        sys.exit(1)
