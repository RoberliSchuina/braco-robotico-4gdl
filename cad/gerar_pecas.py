# -*- coding: utf-8 -*-
"""
gerar_pecas.py — Modelagem paramétrica (CSG) das peças do braço robótico de 4 GDL
(base giratória, ombro, cotovelo e garra) acionado por 4 micro-servos SG90/MG90S.

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
from shapely.geometry import Polygon

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

# ------------------------------------------------------------------ "cortadores" reutilizáveis
# Sistema canônico do servo: eixo de saída = origem apontando +z; corpo estende-se ao longo de +x
# (centro do corpo em x = +5,3); face de apoio do flange em z = 0.
def corte_servo():
    """Rasgo passante do corpo do servo + 2 furos-piloto do flange."""
    cx = SV_DESLOC_EIXO
    rasgo = box(cx - SV_RASGO_L / 2, cx + SV_RASGO_L / 2, -SV_RASGO_W / 2, SV_RASGO_W / 2, -25, 25)
    f1 = cyl(SV_FURO_D / 2, 50, (cx + SV_FURO_X, 0, 0))
    f2 = cyl(SV_FURO_D / 2, 50, (cx - SV_FURO_X, 0, 0))
    return uniao(rasgo, f1, f2)

HORN_R_CUBO  = 4.6      # cubo do horn Ø8 + 0,3 mm de folga por lado
HORN_R_PONTA = 2.7      # meia-largura na ponta do braço (5,4 mm, como o rasgo reto da versão anterior)
HORN_CORTE_H = 8.2      # altura dos cortadores de furo: cobre os 4 mm de chapa nas três orientações, e só

def bolso_horn_2d(bracos):
    """Silhueta 2D do bolso do horn: cubo Ø9,2 unido a um tronco de cone por braço. O braço do horn do SG90
    não tem largura constante — sai tangente ao cubo e afina até a ponta —, então um rasgo reto de 5,4 mm
    deixa material sobrando junto ao cubo e o horn não assenta no fundo do bolso.
    bracos: lista de (ângulo em graus, comprimento do braço em mm)."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
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
    cx = SV_DESLOC_EIXO
    disco = cyl(55, 4, (0, 0, 2), n=128)
    torre = box(cx - 19.3, cx + 19.3, -14, 14, 3, 30)
    # 4 colunas de encosto: sem elas todo o conjunto girante (~60 g) pendura no estriado plastico do horn de S1
    apoios = [cyl(4.5, 36.3, (24.5 * math.cos(a), 24.5 * math.sin(a), 22.15))
              for a in np.radians([45, 135, 225, 315])]        # topo em z=40,3 -> 0,5 mm sob a plataforma
    corpo = uniao(disco, torre, *apoios)
    cavidade = box(cx - 14, cx + 14, -9, 9, -1, 27)            # aberta embaixo; tampa de 3 mm em z=27..30
    canal = box(-4, 4, 0, 60, -1, 2)                           # canal do cabo sob a base
    servo = coloca(corte_servo(), (0, 0, 30), (0, 0, 1), (1, 0, 0))
    furos = [cyl(1.7, 20, (47 * math.cos(a), 47 * math.sin(a), 2)) for a in np.radians([45, 135, 225, 315])]
    return subtrai(corpo, cavidade, canal, servo, *furos)

def plataforma():
    """Disco Ø60 fixado no horn de S1; parede vertical com o servo S2 (ombro, eixo horizontal Y)."""
    cx = SV_DESLOC_EIXO
    disco = cyl(30, 4, (0, 0, 2), n=128)
    parede = box(cx - 17.3, cx + 17.3, 4, 8, 3, 44)
    nerv1 = box(cx + 13.3, cx + 17.3, -6, 4.5, 3, 34)
    nerv2 = box(cx - 17.3, cx - 13.3, -6, 4.5, 3, 34)
    corpo = uniao(disco, parede, nerv1, nerv2)
    horn = coloca(corte_horn('cruz'), (0, 0, 0), (0, 0, 1), (1, 0, 0))
    servo = coloca(corte_servo(), (0, 8, 28), (0, 1, 0), (1, 0, 0))
    return subtrai(corpo, horn, servo)

def braco():
    """Elo superior: horn de S2 em z=0; servo S3 (cotovelo) em z=70. Chapa 4 mm no plano XZ."""
    corpo = uniao(box(-17, 17, 0, ESP, 0, 70),
                  cyl(17, ESP, (0, ESP / 2, 0), 'y'),
                  cyl(17, ESP, (0, ESP / 2, 70), 'y'))
    janela = box(-6, 6, -1, ESP + 1, 24, 46)
    horn = coloca(corte_horn('duplo'), (0, 0, 0), (0, 1, 0), (0, 0, 1))
    servo = coloca(corte_servo(), (0, ESP, 70), (0, 1, 0), (0, 0, -1))   # corpo do servo ao longo do elo
    return subtrai(corpo, janela, horn, servo)

def antebraco():
    """Elo inferior: horn de S3 em z=0; servo S4 (garra) em (-12, 60); pino M3 da engrenagem livre em (+12, 60)."""
    corpo = uniao(cyl(17, ESP, (0, ESP / 2, 0), 'y'),
                  box(-17, 17, 0, ESP, 0, 50),
                  box(-24, 24, 0, ESP, 36, 76))
    janela = box(-6, 6, -1, ESP + 1, 21, 33)      # comeca depois do horn 'duplo' (z=16,5) e do furo-piloto em z=12
    horn = coloca(corte_horn('duplo'), (0, 0, 0), (0, 1, 0), (0, 0, 1))
    servo = coloca(corte_servo(), (-12, ESP, 60), (0, 1, 0), (0, 0, -1))
    pino = cyl(1.7, 20, (12, ESP / 2, 60), 'y')
    return subtrai(corpo, janela, horn, servo, pino)

def dedo(motriz=True):
    """Dedo da garra = engrenagem (16 dentes, m=1,5) + haste 10x55 + mandíbula.
    motriz: bolso do horn de S4 na face superior.  livre: ressalto Ø9 x 10,8 + furo Ø3,4 (pino M3)."""
    fase = 0.0 if motriz else 360 / GEAR_N / 2       # meio passo: engrena com a motriz
    eng = extrude_polygon(engrenagem_poly(fase_graus=fase), ESP)
    s = 1 if motriz else -1                          # lado da mandíbula (aponta para o centro da garra)
    haste = box(-5, 5, 0, 55, 0, ESP)
    mand = box(min(0, s * 10), max(0, s * 10), 43, 55, 0, ESP)
    corpo = uniao(eng, haste, mand)
    if motriz:
        horn = coloca(corte_horn('simples'), (0, 0, ESP), (0, 0, -1), (0, 1, 0))
        return subtrai(corpo, horn)
    corpo = uniao(corpo, cyl(4.5, GAP_ELO, (0, 0, ESP + GAP_ELO / 2)))
    return subtrai(corpo, cyl(1.7, 60))

# ------------------------------------------------------------------ suporte dos joysticks (controle de mão)
JOY_PCB   = (34.0, 26.0)                    # placa do módulo KY-023 (comprimento x largura)
JOY_FUROS = (26.5, 20.0)                    # distância entre centros dos furos Ø3 da placa — conferir com paquímetro
JOY_POS   = [(-45.0, 14.0), (45.0, 14.0)]   # centros dos módulos no suporte (J1 à esquerda, J2 à direita)

def suporte_joysticks():
    """Placa em formato de controle de videogame (160 x 100 x 4) com, para cada módulo KY-023, 4 ressaltos Ø7 x 3
    (afastam a solda da placa) e rasgos em cruz 3,4 x 6 (toleram ±1,3 mm na furação). Rasgo para pendurar
    no topo e rasgos para abraçadeira dos cabos acima de cada módulo."""
    from shapely.geometry import Point, box as sbox
    from shapely.ops import unary_union
    corpo2d = sbox(-66, -8, 66, 38).buffer(14, join_style=1)                        # corpo com cantos R14
    pegas = unary_union([Point(-54, -26).buffer(22), Point(54, -26).buffer(22)])    # empunhaduras
    forma = unary_union([corpo2d, pegas]).buffer(4).buffer(-4)                      # fechamento: concordâncias R4
    placa = extrude_polygon(forma, ESP)
    ressaltos, furos = [], []
    for cx, cy in JOY_POS:
        for sx in (-1, 1):
            for sy in (-1, 1):
                fx, fy = cx + sx * JOY_FUROS[0] / 2, cy + sy * JOY_FUROS[1] / 2
                ressaltos.append(cyl(5.0, 3, (fx, fy, ESP + 1.5)))   # Ø10: o rasgo em cruz 3,4x6 cabia inteiro num Ø7
                furos += [box(fx - 1.7, fx + 1.7, fy - 3.0, fy + 3.0, -1, 20),       # rasgo em cruz (M3)
                          box(fx - 3.0, fx + 3.0, fy - 1.7, fy + 1.7, -1, 20)]
        furos += [box(cx - 12, cx - 9, 38, 46, -1, 20), box(cx + 9, cx + 12, 38, 46, -1, 20)]   # abraçadeira dos cabos
    pendurar = extrude_polygon(sbox(-5, 40, 5, 44).buffer(2.5, join_style=1), 22)
    pendurar.apply_translation([0, 0, -1])
    return subtrai(uniao(placa, *ressaltos), pendurar, *furos)

def joystick_dummy():
    """Volume aproximado do módulo KY-023 (placa, potenciômetros, haste e manípulo) para o render."""
    pcb = box(-JOY_PCB[0] / 2, JOY_PCB[0] / 2, -JOY_PCB[1] / 2, JOY_PCB[1] / 2, 0, 1.6)
    corpo = box(-8, 8, -8, 8, 1.6, 11.6)
    haste = cyl(3.5, 12, (0, 0, 17.6))
    manipulo = cyl(9, 8, (0, 0, 27.6))
    header = box(-6.5, 6.5, 10.5, 13, 1.6, 9.6)
    return uniao(pcb, corpo, haste, manipulo, header)

def servo_dummy():
    """Volume aproximado do servo (para o modelo montado), no sistema canônico."""
    cx = SV_DESLOC_EIXO
    corpo = box(cx - SV_L / 2, cx + SV_L / 2, -SV_W / 2, SV_W / 2, -SV_ABAIXO, SV_FLANGE_T + SV_ACIMA)
    flange = box(cx - 16.25, cx + 16.25, -SV_W / 2, SV_W / 2, 0, SV_FLANGE_T)
    eixo = cyl(2.9, SV_EIXO + 0.5, (0, 0, SV_FLANGE_T + SV_ACIMA + (SV_EIXO + 0.5) / 2))
    return uniao(corpo, flange, eixo)

PECAS = [
    # (arquivo, nome, função, construtor, transformação p/ orientação de impressão, obs. impressão)
    ("01_base_fixa",        "Base fixa",            "Apoio do braço; abriga o servo S1 (rotação da base)", base_fixa,  np.eye(4),
     "Disco para baixo. Tampa da torre faz ponte de 18 mm (OK na A1; opcionalmente ativar suportes)."),
    ("02_plataforma_giratoria", "Plataforma giratória", "Fixa no horn de S1; sustenta o servo S2 (ombro)", plataforma, np.eye(4),
     "Disco para baixo (bolso do horn fica na 1ª camada). Sem suportes."),
    ("03_braco",            "Braço (elo superior)", "Liga o ombro (S2) ao cotovelo (S3)", braco, T(0, 0, ESP) @ Rx(-90),
     "Deitado, bolso do horn para cima. Sem suportes."),
    ("04_antebraco",        "Antebraço (elo inferior)", "Liga o cotovelo (S3) à garra; suporta S4 e o pino da engrenagem livre", antebraco, T(0, 0, ESP) @ Rx(-90),
     "Deitado, bolso do horn para cima. Sem suportes."),
    ("05_garra_dedo_motriz", "Dedo motriz da garra", "Engrenagem acionada pelo horn de S4 + dedo", lambda: dedo(True), np.eye(4),
     "Deitado, bolso do horn para cima. Sem suportes."),
    ("06_garra_dedo_livre",  "Dedo livre da garra",  "Engrenagem espelhada que gira no pino M3 + dedo", lambda: dedo(False), np.eye(4),
     "Deitado, ressalto para cima. Sem suportes."),
    ("07_suporte_joysticks",  "Suporte dos joysticks", "Controle de mão: fixa os 2 módulos KY-023 (parafusos M3)", suporte_joysticks, np.eye(4),
     "Deitado, ressaltos para cima. Sem suportes."),
]

def exporta_peca(arquivo, mesh, Timp):
    m = mesh.copy(); m.apply_transform(Timp)
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])   # centra em XY, apoia em z=0
    m.export(os.path.join(DIR_STL, arquivo + ".stl"))
    return m

# ------------------------------------------------------------------ MONTAGEM
def montagem(pecas, th1=-20, th2=30, th3=90, alfa=15):
    """Posiciona peças e servos. th1: base; th2: braço (0 = vertical, + para +X);
    th3: ângulo absoluto do antebraço (90 = horizontal, +X); alfa: abertura de cada dedo."""
    z_plat = 30 + GAP_ELO                       # 40,8: face inferior da plataforma
    T_plat = T(0, 0, z_plat)
    z_s2 = z_plat + 28
    T_braco = T(0, 8 + GAP_ELO, z_s2) @ Ry(th2)
    p_s3 = (T_braco @ np.array([0, ESP, 70, 1]))[:3]
    T_ante = T(*(p_s3 + np.array([0, GAP_ELO, 0]))) @ Ry(th3)
    p_s4 = (T_ante @ np.array([-12, ESP, 60, 1]))[:3]
    dir_braco = (Ry(th2) @ np.array([0, 0, -1, 0]))[:3]
    dir_ante = (Ry(th3) @ np.array([0, 0, -1, 0]))[:3]
    sv = servo_dummy()
    itens = [
        (pecas["01_base_fixa"], np.eye(4), "#d9d9d9"),
        (sv, frame((0, 0, 30), (0, 0, 1), (1, 0, 0)), "#2b6cb0"),
        (pecas["02_plataforma_giratoria"], T_plat, "#f0a04b"),
        (sv, frame((0, 8, z_s2), (0, 1, 0), (1, 0, 0)), "#2b6cb0"),
        (pecas["03_braco"], T_braco, "#5aa469"),
        (sv, frame(p_s3, (0, 1, 0), dir_braco), "#2b6cb0"),
        (pecas["04_antebraco"], T_ante, "#e06666"),
        (sv, frame(p_s4, (0, 1, 0), dir_ante), "#2b6cb0"),
        (pecas["05_garra_dedo_motriz"], T_ante @ T(-12, ESP + HORN_TOPO + ESP - BOLSO_HORN, 60) @ Ry(-alfa) @ Rx(90), "#8e7cc3"),
        (pecas["06_garra_dedo_livre"],  T_ante @ T(12, ESP + HORN_TOPO + ESP - BOLSO_HORN, 60) @ Ry(alfa) @ Rx(90), "#8e7cc3"),
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

def render_pecas(pecas_imp, arquivo):
    """Todas as peças lado a lado, na orientação de impressão (como na mesa da A1)."""
    itens, x = [], 0.0
    cores = ["#d9d9d9", "#f0a04b", "#5aa469", "#e06666", "#8e7cc3", "#8e7cc3", "#6fa8dc"]
    for (arq, *_), cor in zip(PECAS, cores):
        m = pecas_imp[arq].copy(); lo, hi = m.bounds
        if arq.startswith("07"):                      # controle de mão em uma 2ª fileira
            m.apply_translation([60 - lo[0], -150 - lo[1], 0])
        else:
            m.apply_translation([x - lo[0], 0, 0]); x += (hi[0] - lo[0]) + 12
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
        print(f"{arq:28s} {dx:6.1f} x {dy:6.1f} x {dz:6.1f} mm  vol={vol:5.1f} cm3  ~{massa:4.1f} g  faces={len(m.faces)}")
    with open(os.path.join(RAIZ, "cad", "pecas_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    itens = montagem(pecas)
    trimesh.util.concatenate([m for m, _ in itens]).export(os.path.join(DIR_STL, "montagem_completa.stl"))
    render(itens, os.path.join(DIR_IMG, "montagem_vistas.png"),
           [("Vista isométrica", 28, -55), ("Vista frontal", 0, -90), ("Vista lateral", 0, 0), ("Vista superior", 90, -90)])
    render(itens, os.path.join(DIR_IMG, "montagem_isometrica.png"), [("Braço robótico 4 GDL — protótipo montado", 25, -50)])
    render(montagem(pecas, th1=0, th2=0, th3=90, alfa=15), os.path.join(DIR_IMG, "montagem_repouso.png"),
           [("Posição de repouso (home) — todos os servos em 90°", 20, -60)])
    render_pecas(pecas_imp, os.path.join(DIR_IMG, "pecas_impressao.png"))
    joy = joystick_dummy()
    itens_sup = [(pecas["07_suporte_joysticks"], "#6fa8dc")]
    for cx, cy in JOY_POS:
        j = joy.copy(); j.apply_translation([cx, cy, ESP + 3]); itens_sup.append((j, "#333333"))
    render(itens_sup, os.path.join(DIR_IMG, "suporte_joysticks.png"),
           [("Suporte dos joysticks (controle de mão) com os módulos KY-023", 35, -60), ("Vista superior", 90, -90)])
    print("OK ->", DIR_STL, DIR_IMG)
