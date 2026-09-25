# -*- coding: utf-8 -*-
"""
gerar_pecas.py — Modelagem paramétrica (CSG) das peças do braço robótico de 4 GDL
(base giratória, ombro, cotovelo e garra) acionado por 4 micro-servos SG90/MG90S.

Arquitetura (revisão 2026-09-24):
  * Estrutura em FORQUILHA: cada elo tem duas chapas laterais (motriz + livre) simétricas
    em relação ao plano de rotação da base (y = 0). O servo fica entre elas, com o flange
    na chapa motriz; o lado livre gira num munhão Ø9 impresso na própria chapa.
  * GARRA NA PALMA: as engrenagens têm eixo ao longo de X do antebraço, ou seja, ficam
    VERTICAIS quando o antebraço está na horizontal — as mandíbulas fecham num plano
    horizontal (captura lateral de objetos apoiados na mesa).

Gera:
  STL/<peca>.stl            — uma peça por arquivo, já na orientação de impressão (Bambu Lab A1)
  STL/montagem_completa.stl — modelo montado (peças + servos) para visualização
  imagens/montagem_*.png    — vistas do protótipo montado
  cad/pecas_info.json       — dimensões, volume e estimativas de massa/tempo por peça

Uso:  python cad/gerar_pecas.py
Req.: pip install trimesh manifold3d shapely numpy matplotlib
"""
import os, json, math
import numpy as np
import trimesh
from trimesh.creation import box as _box, cylinder as _cyl, extrude_polygon
from trimesh.transformations import rotation_matrix, translation_matrix
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_STL = os.path.join(RAIZ, "STL")
DIR_IMG = os.path.join(RAIZ, "imagens")
os.makedirs(DIR_STL, exist_ok=True)
os.makedirs(DIR_IMG, exist_ok=True)

# ------------------------------------------------------------------ servo SG90 / MG90S (mm)
SV_L, SV_W        = 22.8, 12.2      # corpo (comprimento x largura)
SV_RASGO_L, SV_RASGO_W = 23.2, 12.6 # rasgo na peça: folga de 0,2 mm por lado
SV_DESLOC_EIXO    = 5.3             # eixo de saída deslocado 5,3 mm do centro do corpo
SV_FURO_X         = 13.75           # furos do flange a ±13,75 do centro do corpo (27,5 entre centros)
SV_FURO_D         = 1.7             # furo-piloto do flange: 85 % do Ø2,0 do PA (1,9 = 95 %, nao cortava rosca)
SV_ABAIXO         = 15.9            # corpo abaixo da face de apoio do flange
SV_FLANGE_T       = 2.5
SV_ACIMA          = 4.3             # corpo acima do flange
SV_EIXO           = 5.5             # ressalto + eixo estriado acima do corpo
HORN_TOPO   = SV_FLANGE_T + SV_ACIMA + SV_EIXO + 0.5   # 12,8: face superior do horn
BOLSO_HORN  = 2.0                                     # profundidade do bolso do horn na peça
GAP_ELO     = HORN_TOPO - BOLSO_HORN                  # 10,8: face interna do elo -> face de apoio do servo
ESP         = 4.0                                     # espessura padrão das chapas
GEAR_N, GEAR_M = 16, 1.5                              # engrenagens da garra: 16 dentes, módulo 1,5 (Ø primitivo 24)

# ------------------------------------------------------------------ forquilha (simetria em y = 0)
CX       = SV_DESLOC_EIXO
Y_PAR_A  = (4.0, 8.0)        # parede motriz da plataforma (flange de S2 apoia em y = 8)
Y_PAR_B  = (-14.0, -10.0)    # parede livre: corpo de S2 termina em y = -7,9 -> 2,1 mm de folga
Y_ELO1   = Y_PAR_A[1] + GAP_ELO                 # 18,8: face interna das chapas do braço (|y|)
Y_ELO2   = Y_ELO1 + ESP + GAP_ELO               # 33,6: face interna das chapas do antebraço (|y|)
MUNHAO_D     = 9.0           # munhão impresso do lado livre (mesmo Ø do espaçador do dedo livre)
MUNHAO_FOLGA = 0.4           # furo do mancal: Ø9,4
PIL_M3       = 2.5           # furo-piloto para M3 autoatarraxante em PLA (83 % do Ø nominal)
PASS_M3      = 3.4           # furo passante M3
Z_GARRA  = 62.0              # eixos das engrenagens, medidos do cotovelo
Y_GARRA  = GEAR_M * GEAR_N / 2                  # 12,0: ±12 -> 24 mm entre centros (= módulo x dentes)
PALMA_X  = (-14.0, -10.0)    # chapa da palma (normal X); face de apoio de S4 em x = -10
PALMA_Z  = (48.0, 78.0)

# ------------------------------------------------------------------ utilidades CSG
def box(x0, x1, y0, y1, z0, z1):
    m = _box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m

def cyl(r, h, c=(0, 0, 0), eixo='z', n=72):
    m = _cyl(radius=r, height=h, sections=n)
    if eixo == 'x':
        m.apply_transform(rotation_matrix(math.pi / 2, [0, 1, 0]))
    elif eixo == 'y':
        m.apply_transform(rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation(c)
    return m

def uniao(*ms):
    return trimesh.boolean.union(list(ms), engine='manifold')

def subtrai(a, *ms):
    return trimesh.boolean.difference([a] + list(ms), engine='manifold')

def frame(origem, eixo_z, eixo_x):
    """Matriz 4x4 que leva o sistema canônico (x, y, z) para (eixo_x, z×x, eixo_z) em 'origem'."""
    z = np.asarray(eixo_z, float); z /= np.linalg.norm(z)
    x = np.asarray(eixo_x, float); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    M = np.eye(4); M[:3, 0] = x; M[:3, 1] = y; M[:3, 2] = z; M[:3, 3] = origem
    return M

def coloca(m, origem, eixo_z, eixo_x):
    m = m.copy(); m.apply_transform(frame(origem, eixo_z, eixo_x)); return m

def Rx(g): return rotation_matrix(math.radians(g), [1, 0, 0])
def Ry(g): return rotation_matrix(math.radians(g), [0, 1, 0])
def Rz(g): return rotation_matrix(math.radians(g), [0, 0, 1])
def T(x, y, z): return translation_matrix([x, y, z])

def chapa(poligono_xz, espessura=ESP):
    """Extruda um perfil 2D dado em (x, z) numa chapa que ocupa y = -espessura .. 0.
    (Rx(+90) leva (x, y, z) -> (x, -z, y): o perfil vai para o plano XZ e a espessura para -y.)"""
    m = extrude_polygon(poligono_xz, espessura)
    m.apply_transform(Rx(90))
    return m

# ------------------------------------------------------------------ "cortadores" reutilizáveis
# Sistema canônico do servo: eixo de saída = origem apontando +z; corpo estende-se ao longo de +x
# (centro do corpo em x = +5,3); face de apoio do flange em z = 0.
def corte_servo():
    """Rasgo passante do corpo do servo + 2 furos-piloto do flange."""
    rasgo = box(CX - SV_RASGO_L / 2, CX + SV_RASGO_L / 2, -SV_RASGO_W / 2, SV_RASGO_W / 2, -25, 25)
    f1 = cyl(SV_FURO_D / 2, 50, (CX + SV_FURO_X, 0, 0))
    f2 = cyl(SV_FURO_D / 2, 50, (CX - SV_FURO_X, 0, 0))
    return uniao(rasgo, f1, f2)

HORN_R_CUBO  = 4.6      # cubo do horn Ø8 + 0,3 mm de folga por lado
HORN_R_PONTA = 2.7      # meia-largura na ponta do braço (5,4 mm, como o rasgo reto da versão anterior)
HORN_CORTE_H = 8.2      # altura dos cortadores de furo: cobre os 4 mm de chapa nas três orientações, e só

def bolso_horn_2d(bracos):
    """Silhueta 2D do bolso do horn: cubo Ø9,2 unido a um tronco de cone por braço. O braço do horn do SG90
    não tem largura constante — sai tangente ao cubo e afina até a ponta —, então um rasgo reto de 5,4 mm
    deixa material sobrando junto ao cubo e o horn não assenta no fundo do bolso.
    bracos: lista de (ângulo em graus, comprimento do braço em mm)."""
    cubo = Point(0, 0).buffer(HORN_R_CUBO, 64)
    formas = [cubo]
    for ang, comp in bracos:
        a = math.radians(ang)
        ponta = Point(comp * math.cos(a), comp * math.sin(a)).buffer(HORN_R_PONTA, 64)
        formas.append(unary_union([cubo, ponta]).convex_hull)
    return unary_union(formas)

def corte_horn(tipo):
    """Bolso para o horn do servo (face em z=0, entrando em +z), furo central Ø2,6 (passa o parafuso do eixo
    do servo; a cabeça apoia na peça) e furos-piloto Ø1,5 para os micro parafusos PA 1,7 x 6 do horn.
    tipo: 'cruz' | 'duplo' | 'simples'."""
    p = BOLSO_HORN
    if tipo == 'cruz':
        bracos = [(0, 14), (90, 14), (180, 14), (270, 14)]
        furos = [(7.5, 0), (-7.5, 0), (11, 0), (-11, 0), (0, 7.5), (0, -7.5), (0, 11), (0, -11)]
    elif tipo == 'duplo':
        bracos = [(0, 16.5), (180, 16.5)]
        furos = [(8, 0), (-8, 0), (12, 0), (-12, 0)]
    else:  # simples: um só braço apontando para +x
        bracos = [(0, 18)]
        furos = [(8, 0), (12, 0), (15, 0)]
    bolso = extrude_polygon(bolso_horn_2d(bracos), p + 1)
    bolso.apply_translation([0, 0, -1])                        # bolso de z=-1 a z=p
    partes = [bolso, cyl(1.3, HORN_CORTE_H)]                   # furo do parafuso central Ø2,6 (passante)
    partes += [cyl(0.75, HORN_CORTE_H, (fx, fy, 0)) for fx, fy in furos]
    return uniao(*partes)

def engrenagem_poly(N=GEAR_N, m=GEAR_M, fase_graus=0.0):
    """Perfil 2D de engrenagem reta com dentes trapezoidais (aproximação da evolvente, adequada a FDM)."""
    rp = m * N / 2; ra = rp + 0.8 * m; rf = rp - 1.25 * m      # addendum encurtado (0,8 m): sem interferencia de topo
    pts = []
    for k in range(N):
        t = math.radians(k * 360 / N + fase_graus)
        for r, da in [(rf, -8.0), (rp, -4.7), (ra, -2.5), (ra, 2.5), (rp, 4.7), (rf, 8.0)]:
            a = t + math.radians(da)
            pts.append((r * math.cos(a), r * math.sin(a)))
    return Polygon(pts)

# ------------------------------------------------------------------ PEÇAS (sistema local de cada peça)
def base_fixa():
    """Disco Ø110 x 4 com torre que abriga o servo S1 (eixo vertical)."""
    disco = cyl(55, 4, (0, 0, 2), n=128)
    torre = box(CX - 19.3, CX + 19.3, -14, 14, 3, 30)
    # 4 colunas de encosto: sem elas todo o conjunto girante pendura no estriado plastico do horn de S1
    apoios = [cyl(4.5, 36.3, (24.5 * math.cos(a), 24.5 * math.sin(a), 22.15))
              for a in np.radians([45, 135, 225, 315])]        # topo em z=40,3 -> 0,5 mm sob a plataforma
    corpo = uniao(disco, torre, *apoios)
    cavidade = box(CX - 14, CX + 14, -9, 9, -1, 27)            # aberta embaixo; tampa de 3 mm em z=27..30
    canal = box(-4, 4, 0, 60, -1, 2)                           # canal do cabo sob a base
    servo = coloca(corte_servo(), (0, 0, 30), (0, 0, 1), (1, 0, 0))
    furos = [cyl(1.7, 20, (47 * math.cos(a), 47 * math.sin(a), 2)) for a in np.radians([45, 135, 225, 315])]
    return subtrai(corpo, cavidade, canal, servo, *furos)

def plataforma():
    """Disco Ø60 fixado no horn de S1, com DUAS paredes: a motriz (y=4..8) recebe o servo S2 (ombro) e a
    livre (y=-14..-10) recebe o munhão da chapa livre do braço. As duas nervuras ligam as duas paredes
    entre si e ao disco, formando um caixote — é o que fecha a forquilha do ombro."""
    disco = cyl(30, ESP, (0, 0, ESP / 2), n=128)
    parA = box(CX - 17.3, CX + 17.3, Y_PAR_A[0], Y_PAR_A[1], 3, 44)
    parB = box(CX - 17.3, CX + 17.3, Y_PAR_B[0], Y_PAR_B[1], 3, 44)
    nerv = [box(CX + 13.3, CX + 17.3, Y_PAR_B[1], 4.5, 3, 30),
            box(CX - 17.3, CX - 13.3, Y_PAR_B[1], 4.5, 3, 30)]   # fora do corpo do servo (x = -6,1..16,7)
    corpo = uniao(disco, parA, parB, *nerv)
    horn = coloca(corte_horn('cruz'), (0, 0, 0), (0, 0, 1), (1, 0, 0))
    servo = coloca(corte_servo(), (0, Y_PAR_A[1], 28), (0, 1, 0), (1, 0, 0))
    mancal = cyl((MUNHAO_D + MUNHAO_FOLGA) / 2, 12, (0, -12, 28), 'y')   # furo Ø9,4 passante na parede livre
    return subtrai(corpo, horn, servo, mancal)

# ---- braço (elo superior): ombro em z=0, cotovelo em z=70
PERFIL_BRACO = unary_union([Polygon([(-17, 0), (17, 0), (17, 70), (-17, 70)]),
                            Point(0, 0).buffer(17, 64), Point(0, 70).buffer(17, 64)])
TRAV_Z = (56.0, 70.0)          # travessa do braço: fora da varredura da plataforma (r >= 30) e do corpo de S3
TRAV_FUROS_Z = (59.0, 67.0)

def braco_motriz():
    """Chapa lateral MOTRIZ do braço: bolso do horn de S2 na face interna (y=0) e servo S3 (cotovelo)
    com o flange na face externa (y=4), corpo entrando na forquilha."""
    corpo = chapa(PERFIL_BRACO); corpo.apply_translation([0, ESP, 0])     # chapa em y = 0..ESP
    janela = box(-8, 8, -1, ESP + 1, 22, 52)
    horn = coloca(corte_horn('duplo'), (0, 0, 0), (0, 1, 0), (0, 0, 1))
    servo = coloca(corte_servo(), (0, ESP, 70), (0, 1, 0), (0, 0, -1))    # corpo do servo ao longo do elo
    trav = [cyl(PASS_M3 / 2, 20, (-13, ESP / 2, z), 'y') for z in TRAV_FUROS_Z]
    return subtrai(corpo, janela, horn, servo, *trav)

def braco_livre():
    """Chapa lateral LIVRE do braço: munhão Ø9 que gira no mancal da parede livre da plataforma, mancal
    Ø9,4 do cotovelo e a travessa integrada que amarra as duas chapas (2 parafusos M3 x 10)."""
    corpo = chapa(PERFIL_BRACO)                                           # chapa em y = -ESP..0
    munhao = cyl(MUNHAO_D / 2, 9.8, (0, 3.9, 0), 'y')                     # y = -1..8,8 (entra 1 mm na chapa)
    L = 2 * Y_ELO1                                                        # 37,6: vão entre faces internas
    trav = box(-17, -13, -1, L, *TRAV_Z)
    pad = box(-17, -9, L - 8, L, *TRAV_Z)                                 # reforço dos furos-piloto
    corpo = uniao(corpo, munhao, trav, pad)
    janela = box(-8, 8, -ESP - 1, 1, 22, 52)
    cotovelo = cyl((MUNHAO_D + MUNHAO_FOLGA) / 2, 12, (0, -2, 70), 'y')
    pil = [cyl(PIL_M3 / 2, 8.4, (-13, L - 4, z), 'y') for z in TRAV_FUROS_Z]
    return subtrai(corpo, janela, cotovelo, *pil)

# ---- antebraço (elo inferior): cotovelo em z=0, garra em z=Z_GARRA
PERFIL_ANTE = unary_union([Polygon([(-17, 0), (17, 0), (17, 40), (0, 56), (0, 78), (-17, 78)]),
                           Point(0, 0).buffer(17, 64)])
PALMA_FUROS_Z = (54.0, 74.0)

def antebraco_motriz():
    """Chapa lateral MOTRIZ do antebraço: bolso do horn de S3 na face interna. A borda inferior recua de
    x=17 para x=6 na ponta para que as mandíbulas (x = 0,8..4,8) fiquem livres para descer sobre o objeto."""
    corpo = chapa(PERFIL_ANTE); corpo.apply_translation([0, ESP, 0])
    janela = box(-8, 8, -1, ESP + 1, 20, 44)
    horn = coloca(corte_horn('duplo'), (0, 0, 0), (0, 1, 0), (0, 0, 1))
    palma = [cyl(PASS_M3 / 2, 20, (-10, ESP / 2, z), 'y') for z in PALMA_FUROS_Z]
    return subtrai(corpo, janela, horn, *palma)

def antebraco_livre():
    """Chapa lateral LIVRE do antebraço + PALMA integrada (chapa normal a X que atravessa a forquilha).
    A palma é a travessa do antebraço e a base da garra: S4 é aparafusado nela com o eixo ao longo de X
    (vertical com o antebraço na horizontal) e o pino M3 do dedo livre atravessa-a em y = -12."""
    corpo = chapa(PERFIL_ANTE)
    munhao = cyl(MUNHAO_D / 2, GAP_ELO + ESP + 1, (0, (GAP_ELO + ESP - 1) / 2, 0), 'y')   # y = -1..14,8
    L = 2 * Y_ELO2                                                        # 67,2: vão entre faces internas
    palma = box(PALMA_X[0], PALMA_X[1], -1, L, *PALMA_Z)
    pads = [box(PALMA_X[0], -6, L - 8, L, z - 5, z + 5) for z in PALMA_FUROS_Z]
    corpo = uniao(corpo, munhao, palma, *pads)
    janela = box(-8, 8, -ESP - 1, 1, 20, 44)
    # garra: S4 em y = Y_ELO2 + Y_GARRA (corpo para -y), pino do dedo livre em y = Y_ELO2 - Y_GARRA
    servo = coloca(corte_servo(), (PALMA_X[1], Y_ELO2 + Y_GARRA, Z_GARRA), (1, 0, 0), (0, -1, 0))
    pino = cyl(PASS_M3 / 2, 12, (-12, Y_ELO2 - Y_GARRA, Z_GARRA), 'x')
    pil = [cyl(PIL_M3 / 2, 8.4, (-10, L - 4, z), 'y') for z in PALMA_FUROS_Z]
    jan_palma = box(PALMA_X[0] - 1, PALMA_X[1] + 1, 3, 16, 52, 74)
    return subtrai(corpo, janela, servo, pino, jan_palma, *pil)

def dedo(motriz=True, tipo='plana'):
    """Dedo da garra = engrenagem (16 dentes, m=1,5) + haste 10x55 + mandíbula.
    tipo 'plana': mandíbula reta 10 x 12 — objetos prismáticos (caixas, blocos, peças chatas).
    tipo 'v'    : mandíbula 10 x 17 com entalhe em V de ~95° — auto-centra cilindros e esferas. Com a garra
                  na horizontal o sulco do V fica VERTICAL, ou seja, segura canetas, pilhas e frascos em pé.
    Os dois tipos têm a mesma engrenagem e a mesma interface de montagem: é troca direta.
    motriz: bolso do horn de S4 na face superior.  livre: ressalto Ø9 x 10,8 + furo Ø3,4 (pino M3)."""
    fase = 0.0 if motriz else 360 / GEAR_N / 2       # meio passo: engrena com a motriz
    eng = extrude_polygon(engrenagem_poly(fase_graus=fase), ESP)
    s = 1 if motriz else -1                          # lado da mandíbula (aponta para o centro da garra)
    haste = box(-5, 5, 0, 55, 0, ESP)
    y0 = 43 if tipo == 'plana' else 38               # o V precisa de mandíbula mais longa
    mand = box(min(0, s * 10), max(0, s * 10), y0, 55, 0, ESP)
    corpo = uniao(eng, haste, mand)
    if tipo == 'v':                                  # entalhe: apex 5 mm dentro da face, abertura 11 mm
        tri = Polygon([(s * 10.5, 41.0), (s * 10.5, 52.0), (s * 5.0, 46.5)])
        corte = extrude_polygon(tri, ESP + 2); corte.apply_translation([0, 0, -1])
        corpo = subtrai(corpo, corte)
    if motriz:
        horn = coloca(corte_horn('simples'), (0, 0, ESP), (0, 0, -1), (0, 1, 0))
        return subtrai(corpo, horn)
    corpo = uniao(corpo, cyl(4.5, GAP_ELO, (0, 0, ESP + GAP_ELO / 2)))
    return subtrai(corpo, cyl(1.7, 60))

# ------------------------------------------------------------------ suporte dos joysticks (controle de mão)
JOY_PCB   = (34.0, 26.0)                    # placa do módulo KY-023 (comprimento x largura) — 34 x 26 mm
JOY_FUROS = (28.0, 20.0)                    # furos Ø3: NÃO é padronizado entre fabricantes (nenhum datasheet
                                            # publica a cota). Valor nominal; os rasgos radiais absorvem o resto.
JOY_FOLGA = 0.3                             # folga do berço em cada borda da placa
JOY_APOIO = 3.0                             # altura do assento (afasta as soldas da chapa)
JOY_LABIO = 2.2                             # lábio que trava a placa pela borda (PCB tem 1,6 mm)
JOY_RASGO = 8.0                             # curso radial de cada rasgo (aceita 21,5..34,5 x 15,4..24,6 mm)
JOY_POS   = [(-45.0, 14.0), (45.0, 14.0)]   # centros dos módulos no suporte (J1 à esquerda, J2 à direita)

def _canto_berco(cx, cy, sx, sy):
    """Canto em L do berço: assento de 3 mm sob o canto da placa + paredes de 2,5 mm que sobem mais 2,2 mm
    e posicionam o módulo pela borda (independe da furação da placa)."""
    x0 = cx + sx * (JOY_PCB[0] / 2 + JOY_FOLGA)      # face interna da parede = borda da placa
    y0 = cy + sy * (JOY_PCB[1] / 2 + JOY_FOLGA)
    z0, z1, z2 = ESP, ESP + JOY_APOIO, ESP + JOY_APOIO + JOY_LABIO
    assento = box(*sorted([x0, x0 - sx * 11]), *sorted([y0, y0 - sy * 8]), z0, z1)
    par_x = box(*sorted([x0, x0 + sx * 2.5]), *sorted([y0 + sy * 2.5, y0 - sy * 10]), z0, z2)
    par_y = box(*sorted([x0 + sx * 2.5, x0 - sx * 13]), *sorted([y0, y0 + sy * 2.5]), z0, z2)
    return uniao(assento, par_x, par_y)

def _rasgo_radial(cx, cy, fx, fy):
    """Rasgo 3,4 mm alongado na direção radial (centro do módulo -> furo nominal): o mesmo suporte serve
    para qualquer furação simétrica dentro do curso."""
    d = np.array([fx - cx, fy - cy], float); d /= np.linalg.norm(d)
    p = np.array([fx, fy])
    pol = LineString([p - d * JOY_RASGO / 2, p + d * JOY_RASGO / 2]).buffer(PASS_M3 / 2, 16)
    m = extrude_polygon(pol, 30); m.apply_translation([0, 0, -1])
    return m

def suporte_joysticks():
    """Placa em formato de controle de videogame (160 x 100 x 4). Para cada módulo KY-023: berço de 4 cantos
    em L (posiciona a placa pela borda, assento de 3 mm) + 4 rasgos radiais M3 (a furação do KY-023 varia
    entre fabricantes). Rasgo para pendurar no topo e rasgos de abraçadeira acima de cada módulo."""
    from shapely.geometry import box as sbox
    corpo2d = sbox(-66, -8, 66, 38).buffer(14, join_style=1)                        # corpo com cantos R14
    pegas = unary_union([Point(-54, -26).buffer(22), Point(54, -26).buffer(22)])    # empunhaduras
    forma = unary_union([corpo2d, pegas]).buffer(4).buffer(-4)                      # fechamento: concordâncias R4
    placa = extrude_polygon(forma, ESP)
    bercos, furos = [], []
    for cx, cy in JOY_POS:
        for sx in (-1, 1):
            for sy in (-1, 1):
                bercos.append(_canto_berco(cx, cy, sx, sy))
                furos.append(_rasgo_radial(cx, cy, cx + sx * JOY_FUROS[0] / 2, cy + sy * JOY_FUROS[1] / 2))
        furos += [box(cx - 12, cx - 9, 38, 46, -1, 20), box(cx + 9, cx + 12, 38, 46, -1, 20)]   # abraçadeira
    pendurar = extrude_polygon(sbox(-5, 40, 5, 44).buffer(2.5, join_style=1), 22)
    pendurar.apply_translation([0, 0, -1])
    return subtrai(uniao(placa, *bercos), pendurar, *furos)

def joystick_dummy():
    """Volume aproximado do módulo KY-023 (placa 34 x 26, gimbal ~22 x 22 x 20, haste e manípulo, barra de
    5 pinos na borda superior) — usado nos renders para conferir o encaixe no berço."""
    pcb = box(-JOY_PCB[0] / 2, JOY_PCB[0] / 2, -JOY_PCB[1] / 2, JOY_PCB[1] / 2, 0, 1.6)
    corpo = box(-11, 11, -13, 9, 1.6, 21.6)
    haste = cyl(3.5, 10, (0, -2, 26))
    manipulo = cyl(9, 8, (0, -2, 34))
    header = box(-6.5, 6.5, 10.5, 13, 1.6, 10)
    return uniao(pcb, corpo, haste, manipulo, header)

def servo_dummy():
    """Volume aproximado do servo (para o modelo montado), no sistema canônico."""
    corpo = box(CX - SV_L / 2, CX + SV_L / 2, -SV_W / 2, SV_W / 2, -SV_ABAIXO, SV_FLANGE_T + SV_ACIMA)
    flange = box(CX - 16.25, CX + 16.25, -SV_W / 2, SV_W / 2, 0, SV_FLANGE_T)
    eixo = cyl(2.9, SV_EIXO + 0.5, (0, 0, SV_FLANGE_T + SV_ACIMA + (SV_EIXO + 0.5) / 2))
    return uniao(corpo, flange, eixo)

PECAS = [
    # (arquivo, nome, função, construtor, transformação p/ orientação de impressão, obs. impressão)
    ("01_base_fixa",        "Base fixa",            "Apoio do braço; abriga o servo S1 (rotação da base)", base_fixa,  np.eye(4),
     "Disco para baixo. Tampa da torre faz ponte de 18 mm (OK na A1; opcionalmente ativar suportes)."),
    ("02_plataforma_giratoria", "Plataforma giratória", "Fixa no horn de S1; forquilha do ombro (parede motriz de S2 + parede do mancal)", plataforma, np.eye(4),
     "Disco para baixo (bolso do horn fica na 1ª camada). Sem suportes."),
    ("03_braco_motriz",     "Braço — chapa motriz", "Lado acionado do elo superior: horn de S2 e servo S3", braco_motriz, T(0, 0, ESP) @ Rx(-90),
     "Deitada, bolso do horn para cima. Sem suportes."),
    ("04_braco_livre",      "Braço — chapa livre",  "Lado livre do elo superior: munhão do ombro, mancal do cotovelo e travessa", braco_livre, T(0, 0, ESP) @ Rx(90),
     "Deitada, munhão e travessa para cima (tudo vertical na mesa). Sem suportes."),
    ("05_antebraco_motriz", "Antebraço — chapa motriz", "Lado acionado do elo inferior: horn de S3", antebraco_motriz, T(0, 0, ESP) @ Rx(-90),
     "Deitada, bolso do horn para cima. Sem suportes."),
    ("06_antebraco_livre",  "Antebraço — chapa livre + palma", "Lado livre do elo inferior e base da garra (servo S4 e pino do dedo livre)", antebraco_livre, T(0, 0, ESP) @ Rx(90),
     "Deitada, palma em pé (67 mm). Teto do rasgo de S4 faz ponte de 23 mm. Sem suportes."),
    ("07_garra_dedo_motriz", "Dedo motriz da garra", "Engrenagem acionada pelo horn de S4 + dedo", lambda: dedo(True), np.eye(4),
     "Deitado, bolso do horn para cima. Sem suportes."),
    ("08_garra_dedo_livre",  "Dedo livre da garra",  "Engrenagem espelhada que gira no pino M3 + dedo", lambda: dedo(False), np.eye(4),
     "Deitado, ressalto para cima. Sem suportes."),
    ("09_suporte_joysticks", "Suporte dos joysticks", "Controle de mão: berço dos 2 módulos KY-023 (4 rasgos M3 cada)", suporte_joysticks, np.eye(4),
     "Deitado, berços para cima. Sem suportes."),
    ("10_garra_v_dedo_motriz", "Dedo motriz da garra em V (opção B)", "Alternativa ao 07: mandíbula com entalhe em V que auto-centra cilindros e esferas", lambda: dedo(True, 'v'), np.eye(4),
     "Deitado, bolso do horn para cima. Sem suportes."),
    ("11_garra_v_dedo_livre", "Dedo livre da garra em V (opção B)", "Alternativa ao 08: mesma engrenagem espelhada, com o entalhe em V", lambda: dedo(False, 'v'), np.eye(4),
     "Deitado, ressalto para cima. Sem suportes."),
]

def exporta_peca(arquivo, mesh, Timp):
    m = mesh.copy(); m.apply_transform(Timp)
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])   # centra em XY, apoia em z=0
    caminho = os.path.join(DIR_STL, arquivo + ".stl")
    m.export(caminho)
    assert trimesh.load(caminho).is_watertight, f"{arquivo}: STL exportado não é estanque (aresta não-manifold?)"
    return m

# ------------------------------------------------------------------ MONTAGEM
def poses(th2=30, th3=95):
    """Matrizes dos planos de simetria do braço e do antebraço (y=0 = plano de rotação da base)."""
    z_plat = 30 + GAP_ELO                       # 40,8: face inferior da plataforma
    z_s2 = z_plat + 28
    T_br = T(0, 0, z_s2) @ Ry(th2)
    p_cot = (T_br @ np.array([0, 0, 70, 1]))[:3]
    T_an = T(*p_cot) @ Ry(th3)
    return z_plat, z_s2, T_br, T_an

def montagem(pecas, th1=-20, th2=30, th3=95, alfa=15):
    """Posiciona peças e servos. th1: base; th2: braço (0 = vertical, + para +X);
    th3: ângulo absoluto do antebraço (90 = horizontal, +X); alfa: abertura de cada dedo."""
    z_plat, z_s2, T_br, T_an = poses(th2, th3)
    sv = servo_dummy()
    dir_braco = (Ry(th2) @ np.array([0, 0, -1, 0]))[:3]
    p_s3 = (T_br @ np.array([0, Y_ELO1 + ESP, 70, 1]))[:3]
    p_s4 = (T_an @ np.array([PALMA_X[1], Y_GARRA, Z_GARRA, 1]))[:3]
    eixo_s4 = (T_an @ np.array([1, 0, 0, 0]))[:3]
    R_dedo = frame((0, 0, 0), (-1, 0, 0), (0, -1, 0))        # eixo da engrenagem em -X, haste em +Z
    itens = [
        (pecas["01_base_fixa"], np.eye(4), "#d9d9d9"),
        (sv, frame((0, 0, 30), (0, 0, 1), (1, 0, 0)), "#2b6cb0"),
        (pecas["02_plataforma_giratoria"], T(0, 0, z_plat), "#f0a04b"),
        (sv, frame((0, Y_PAR_A[1], z_s2), (0, 1, 0), (1, 0, 0)), "#2b6cb0"),
        (pecas["03_braco_motriz"], T_br @ T(0, Y_ELO1, 0), "#5aa469"),
        (pecas["04_braco_livre"],  T_br @ T(0, -Y_ELO1, 0), "#78c08a"),
        (sv, frame(p_s3, (0, 1, 0), dir_braco), "#2b6cb0"),
        (pecas["05_antebraco_motriz"], T_an @ T(0, Y_ELO2, 0), "#e06666"),
        (pecas["06_antebraco_livre"],  T_an @ T(0, -Y_ELO2, 0), "#ef8f8f"),
        (sv, frame(p_s4, eixo_s4, (0, -1, 0)), "#2b6cb0"),
        (pecas["07_garra_dedo_motriz"], T_an @ T(ESP + 0.8, Y_GARRA, Z_GARRA) @ Rx(-alfa) @ R_dedo, "#8e7cc3"),
        (pecas["08_garra_dedo_livre"],  T_an @ T(ESP + 0.8, -Y_GARRA, Z_GARRA) @ Rx(alfa) @ R_dedo, "#a694d6"),
    ]
    saida = []
    for i, (m, M, cor) in enumerate(itens):
        mm = m.copy(); mm.apply_transform(M)
        if i > 0:                                # tudo acima da base gira com S1
            mm.apply_transform(Rz(th1))
        saida.append((mm, cor))
    return saida

def render(itens, arquivo, vistas):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    luz = np.array([0.4, -0.6, 0.7]); luz /= np.linalg.norm(luz)
    tris, cores = [], []
    for m, cor in itens:
        m = m.subdivide_to_size(max_edge=5.0)            # triângulos pequenos => menos artefatos do "painter's algorithm"
        tris.append(m.vertices[m.faces])
        sombra = 0.55 + 0.45 * np.clip(m.face_normals @ luz, 0, 1)
        cores.append(np.clip(np.array(to_rgb(cor))[None, :] * sombra[:, None], 0, 1))
    tris = np.concatenate(tris); cores = np.concatenate(cores)
    todos = trimesh.util.concatenate([m for m, _ in itens])
    lo, hi = todos.bounds; ext = np.maximum(hi - lo, 20) * 1.04; c = (lo + hi) / 2
    n = len(vistas); cols = 2 if n > 1 else 1; rows = math.ceil(n / cols)
    fig = plt.figure(figsize=(8 * cols, 7 * rows), dpi=110)
    for i, (titulo, elev, azim) in enumerate(vistas, 1):
        ax = fig.add_subplot(rows, cols, i, projection='3d')
        ax.add_collection3d(Poly3DCollection(tris, facecolors=cores, edgecolors='none'))
        ax.set_xlim(c[0] - ext[0] / 2, c[0] + ext[0] / 2); ax.set_ylim(c[1] - ext[1] / 2, c[1] + ext[1] / 2)
        ax.set_zlim(c[2] - ext[2] / 2, c[2] + ext[2] / 2)
        ax.set_box_aspect(tuple(ext / ext.max())); ax.set_proj_type('ortho'); ax.view_init(elev, azim); ax.set_title(titulo, fontsize=13)
        ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)'); ax.set_zlabel('Z (mm)')
    plt.tight_layout(); fig.savefig(arquivo, facecolor='white'); plt.close(fig)

CORES_PECAS = ["#d9d9d9", "#f0a04b", "#5aa469", "#78c08a", "#e06666", "#ef8f8f", "#8e7cc3", "#a694d6", "#6fa8dc",
               "#c27ba0", "#d6a2bd"]

def objeto_dummy(tipo):
    """Objetos de referência nos renders da garra (só ilustração)."""
    if tipo == 'cubo':
        return box(-12.5, 12.5, -12.5, 12.5, -20, 20)          # bloco 25 x 25
    return cyl(8, 40, (0, 0, 0), 'z')                          # cilindro Ø16 (caneta/pilha em pé)

def cena_garras(pecas, alfa_plana=13.0, alfa_v=5.0):
    """As duas opções de garra lado a lado, vistas pelo eixo das engrenagens (o sulco do V é vertical na
    montagem, então esta vista é a que o objeto 'enxerga' chegando de frente)."""
    itens = []
    for dy, sufixo, alfa, obj in [(0.0, ("07_garra_dedo_motriz", "08_garra_dedo_livre"), alfa_plana, 'cubo'),
                                  (120.0, ("10_garra_v_dedo_motriz", "11_garra_v_dedo_livre"), alfa_v, 'cilindro')]:
        motriz, livre = sufixo
        itens.append((pecas[motriz].copy().apply_transform(T(dy - Y_GARRA, 0, 0) @ Rz(alfa)), "#8e7cc3"))
        itens.append((pecas[livre].copy().apply_transform(T(dy + Y_GARRA, 0, 0) @ Rz(-alfa)), "#a694d6"))
        o = objeto_dummy(obj); o.apply_translation([dy, 46.5, ESP / 2]); itens.append((o, "#7f8c8d"))
    return itens

def render_pecas(pecas_imp, arquivo):
    """Todas as peças lado a lado, na orientação de impressão (como na mesa da A1)."""
    itens, x, y, alt = [], 0.0, 0.0, 0.0
    for (arq, *_), cor in zip(PECAS, CORES_PECAS):
        m = pecas_imp[arq].copy(); lo, hi = m.bounds
        larg, prof = hi[0] - lo[0], hi[1] - lo[1]
        if x + larg > 240:                            # quebra de fileira (mesa da A1: 256 x 256)
            x, y, alt = 0.0, y - alt - 12, 0.0
        m.apply_translation([x - lo[0], y - lo[1], 0]); x += larg + 12; alt = max(alt, prof)
        itens.append((m, cor))
    render(itens, arquivo, [("Peças na orientação de impressão (mesa da Bambu Lab A1)", 40, -60)])

if __name__ == "__main__":
    info, pecas, pecas_imp = [], {}, {}
    for arq, nome, funcao, construtor, Timp, obs in PECAS:
        m = construtor()
        assert m.is_watertight, f"{arq}: malha não é estanque"
        pecas[arq] = m
        mi = exporta_peca(arq, m, Timp); pecas_imp[arq] = mi
        dx, dy, dz = mi.extents
        vol = m.volume / 1000.0                                # cm³ (sólido)
        massa = vol * 1.24 * 0.55                              # PLA 1,24 g/cm³; ~55 % do volume com 15 % de infill + paredes
        info.append(dict(arquivo=arq + ".stl", nome=nome, funcao=funcao,
                         dimensoes_mm=[round(dx, 1), round(dy, 1), round(dz, 1)],
                         volume_solido_cm3=round(vol, 1), massa_estimada_g=round(massa, 1),
                         tempo_estimado_min=int(round(massa / 20 * 60)), triangulos=len(m.faces), impressao=obs))
        print(f"{arq:24s} {dx:6.1f} x {dy:6.1f} x {dz:6.1f} mm  vol={vol:5.1f} cm3  ~{massa:4.1f} g  faces={len(m.faces)}")
    with open(os.path.join(RAIZ, "cad", "pecas_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"{'TOTAL':24s} {'':22s} {sum(d['massa_estimada_g'] for d in info):5.1f} g")

    itens = montagem(pecas)
    trimesh.util.concatenate([m for m, _ in itens]).export(os.path.join(DIR_STL, "montagem_completa.stl"))
    render(itens, os.path.join(DIR_IMG, "montagem_vistas.png"),
           [("Vista isométrica", 28, -55), ("Vista frontal", 0, -90), ("Vista lateral", 0, 0), ("Vista superior", 90, -90)])
    render(itens, os.path.join(DIR_IMG, "montagem_isometrica.png"), [("Braço robótico 4 GDL — protótipo montado", 25, -50)])
    render(montagem(pecas, th1=0, th2=0, th3=90, alfa=15), os.path.join(DIR_IMG, "montagem_repouso.png"),
           [("Posição de repouso (home) — todos os servos em 90°", 20, -60)])
    render(montagem(pecas, th1=0, th2=55, th3=90, alfa=18), os.path.join(DIR_IMG, "montagem_captura.png"),
           [("Captura na horizontal — mandíbulas fecham no plano horizontal", 18, -60), ("Vista superior", 90, -90)])
    render(cena_garras(pecas), os.path.join(DIR_IMG, "garras.png"),
           [("Opção A — mandíbula plana (bloco de 25 mm)\nOpção B — mandíbula em V (cilindro Ø16 em pé)", 90, -90)])
    render_pecas(pecas_imp, os.path.join(DIR_IMG, "pecas_impressao.png"))
    joy = joystick_dummy()
    itens_sup = [(pecas["09_suporte_joysticks"], "#6fa8dc")]
    for cx, cy in JOY_POS:
        j = joy.copy(); j.apply_translation([cx, cy, ESP + JOY_APOIO]); itens_sup.append((j, "#333333"))
    render(itens_sup, os.path.join(DIR_IMG, "suporte_joysticks.png"),
           [("Suporte dos joysticks (controle de mão) com os módulos KY-023", 35, -60), ("Vista superior", 90, -90)])
    print("OK ->", DIR_STL, DIR_IMG)
