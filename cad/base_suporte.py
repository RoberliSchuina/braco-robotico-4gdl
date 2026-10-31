# -*- coding: utf-8 -*-
"""
base_suporte.py — Chapa de acrílico que suporta o braço robótico e abriga a eletrônica
(protoboard, Arduino UNO, distribuição de energia e o medidor de tensão/corrente DSN-VC288).

Por que uma chapa: o disco Ø110 da base solto tomba com ≈ 15 g na garra em extensão máxima
(raio de apoio = 55 mm = raio do centro de massa). A chapa resolve de duas formas ao mesmo tempo:
afasta a borda de apoio e, principalmente, coloca a própria massa dela e a da eletrônica ATRÁS
do eixo de S1 — o centro de massa do conjunto deixa de sair do apoio em qualquer carga útil.

Restrição que manda no layout: S1 varre ±85° a partir da frente com alcance de 186 mm, e nas
poses extremas a garra desce 28 mm ABAIXO do plano da base. Logo o semiplano da frente é zona
proibida num raio de 190 mm — nenhum componente pode ficar ali. Como o setor nunca passa de
±85°, tudo que fica atrás da linha do eixo de S1 é inalcançável: é onde vai a eletrônica.

A chapa fica ELEVADA sobre 4 espaçadores de 15 mm. O cabo de S1 sai pela lateral do disco,
dentro do setor de giro; ele desce pelo rasgo de passagem logo na saída e toda a fiação de
potência corre por baixo da chapa, invisível e fora do alcance da garra.

Gera:
  cad/corte_base_acrilico.dxf   — arquivo de corte (R12, camadas CORTE e GRAVACAO)
  cad/corte_base_acrilico.svg   — mesmo desenho em SVG (aceito pela maioria das laser)
  cad/base_info.json            — cotas, massas e resultados da verificação
  imagens/base_layout.png       — desenho cotado para o relatório e para a montagem

Uso:  python cad/base_suporte.py
Req.: pip install shapely numpy matplotlib trimesh
"""
import os, json, math
import numpy as np
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_IMG = os.path.join(RAIZ, "imagens")
DIR_CAD = os.path.dirname(os.path.abspath(__file__))
os.makedirs(DIR_IMG, exist_ok=True)

# ====================================================================== parâmetros
# ---- chapa
CH_W, CH_D, CH_T = 300.0, 260.0, 6.0     # largura x profundidade x espessura (mm)
CH_R = 6.0                                # raio dos cantos (acrílico lasca em canto vivo)
RHO_ACR = 1.19e-3                         # g/mm³ (PMMA)
PE_H = 15.0                               # altura do espaçador/pé: fiação passa por baixo

# ---- eixo de S1 na chapa. Frente = -Y (lado para onde o braço aponta).
EIXO = (CH_W / 2, 70.0)                   # 70 mm da borda da frente (disco Ø110 precisa de 55)
BASE_R_FUROS = 47.0                       # os 4 furos do disco (01_base_fixa) estão em r = 47
BASE_ANG = (45, 135, 225, 315)
D_M3 = 3.4                                # furo passante M3
D_PE = 3.4

# ---- envelope de giro (de cad/verificacao.py e do firmware)
S1_SETOR = 85.0                           # ±85° a partir da frente (limites 5..175 do firmware)
ALCANCE = 186.0                           # alcance horizontal máximo medido no modelo
DISCO_R = 55.0

# ---- componentes da faixa de eletrônica (y crescente = para trás)
Y_ELETRONICA = 130.0                      # início da faixa: disco termina em 70+55 = 125
UNO_W, UNO_D = 68.6, 53.3
UNO_POS = (15.0, 134.0)                   # canto inferior-esquerdo; USB virado para -X (sai pela esquerda)
UNO_FUROS = [(14.0, 2.5), (15.3, 50.8), (66.0, 35.3), (66.0, 7.6)]   # padrão UNO R3 (4; 3 acessíveis)
UNO_FUROS_USAR = (0, 1, 2)                # o furo (66.0, 7.6) fica sob o barramento de potência

PROTO_W, PROTO_D = 83.0, 55.0             # protoboard 400 pontos (colada pela fita dupla-face)
PROTO_POS = (95.0, 134.0)

WAGO_W, WAGO_D = 30.0, 13.0               # WAGO 221-415 (5 vias) — um para +5 V, um para GND
WAGO_POS = [(195.0, 134.0), (195.0, 154.0)]

# ---- rasgo de passagem do cabo de S1 (saída lateral do canal do disco: +X, na altura do eixo)
PASSA_CABO = (203.0, 70.0, 24.0, 10.0)    # cx, cy, comprimento(X), largura(Y) — extremidades arredondadas
PASSA_TRAS = (265.0, 145.0, 24.0, 10.0)   # retorno do chicote para a faixa de eletrônica

# ---- rasgos de abraçadeira (pares 3 x 10, passo 8 mm) para amarrar o chicote
ABRAC = [(150.0, 128.0), (255.0, 100.0), (255.0, 185.0), (60.0, 200.0), (240.0, 200.0)]
ABRAC_W, ABRAC_H, ABRAC_GAP = 3.0, 10.0, 8.0

# ---- painel inclinado (peça de acrílico separada, sustentada por 2 suportes impressos)
PN_W, PN_H, PN_T = 170.0, 75.0, 6.0
PN_INCL = 30.0                            # graus a partir da vertical (projeção 37,5 mm: cabe na chapa)
PN_Y = 210.0                              # linha onde a base do painel encosta na chapa
# DSN-VC288: NENHUM datasheet publica o recorte de painel e as medidas externas divergem entre
# vendedores (48x29x22 num anúncio, 47x28x16 noutro). Mesma situação dos furos do KY-023.
# MEÇA O SEU MÓDULO e ajuste esta cota — o resto do desenho é paramétrico.
# O módulo trava sozinho no recorte pelo clipe da própria moldura — por isso NÃO há furo de
# retenção: errar a janela em 1 mm no acrílico é irreversível, então MEÇA e regenere antes de cortar.
VC288_JANELA = (45.5, 26.5)               # recorte nominal (largura x altura)
D_JACK = 8.0                              # jack P4 de painel com rosca (DC-022B): furo Ø8
CHAVE_W, CHAVE_H = 19.0, 13.0             # chave gangorra KCD1-101
# fusível: porta-fusível de LINHA (rabicho) no cabo da fonte — não gasta alma do painel
PN_FUROS_FIX = 4                          # fixação nos suportes impressos

# ---- massas da eletrônica (g), medidas/catálogo
M_PROTO, M_UNO, M_VC288, M_MISC = 35.0, 25.0, 25.0, 25.0


# ====================================================================== geometria
def rrect(x0, y0, w, h, r=0.0):
    """Retângulo (opcionalmente com cantos arredondados) como polígono shapely."""
    p = sbox(x0, y0, x0 + w, y0 + h)
    return p if r <= 0 else p.buffer(-r, join_style=1).buffer(r, join_style=1)


def slot(cx, cy, comp, larg):
    """Rasgo de extremidades arredondadas: comprimento TOTAL `comp` em X, largura `larg`.
    Construido como segmento engrossado — engrossar um retangulo somaria `larg` a mais."""
    from shapely.geometry import LineString
    r = larg / 2.0
    return LineString([(cx - comp / 2 + r, cy), (cx + comp / 2 - r, cy)]).buffer(r, 32)


def furo(cx, cy, d):
    return Point(cx, cy).buffer(d / 2.0, 64)


def geometria_chapa():
    """(contorno, lista de recortes, lista de gravações) da chapa principal."""
    contorno = rrect(0, 0, CH_W, CH_D, CH_R)

    recortes = []
    # fixação do disco da base
    for a in BASE_ANG:
        # frente da chapa = -Y; o braço aponta em +X no CAD => X_chapa = eixo_x + y_cad, Y_chapa = eixo_y - x_cad
        xc = BASE_R_FUROS * math.cos(math.radians(a))
        yc = BASE_R_FUROS * math.sin(math.radians(a))
        recortes.append(furo(EIXO[0] + yc, EIXO[1] - xc, D_M3))
    # pés / espaçadores
    for px, py in [(25, 25), (CH_W - 25, 25), (25, CH_D - 25), (CH_W - 25, CH_D - 25)]:
        recortes.append(furo(px, py, D_PE))
    # Arduino UNO
    for i in UNO_FUROS_USAR:
        fx, fy = UNO_FUROS[i]
        recortes.append(furo(UNO_POS[0] + fx, UNO_POS[1] + fy, D_M3))
    # passagem de cabo
    recortes.append(slot(*PASSA_CABO))
    recortes.append(slot(*PASSA_TRAS))
    # abraçadeiras (pares de rasgos)
    for cx, cy in ABRAC:
        for s in (-1, 1):
            recortes.append(sbox(cx + s * ABRAC_GAP / 2 - ABRAC_W / 2, cy - ABRAC_H / 2,
                                 cx + s * ABRAC_GAP / 2 + ABRAC_W / 2, cy + ABRAC_H / 2))
    # fixação dos suportes impressos do painel
    for px in (EIXO[0] - PN_W / 2 + 25, EIXO[0] + PN_W / 2 - 25):
        for dy in (0, 20):
            recortes.append(furo(px, PN_Y + dy, D_M3))

    gravacoes = [rrect(*PROTO_POS, PROTO_W, PROTO_D),
                 rrect(*UNO_POS, UNO_W, UNO_D)]
    for wx, wy in WAGO_POS:
        gravacoes.append(rrect(wx, wy, WAGO_W, WAGO_D))
    # linha de referência do setor de giro de S1 (gravada: lembra de não pôr nada à frente dela)
    gravacoes.append(sbox(6, EIXO[1] - 0.25, CH_W - 6, EIXO[1] + 0.25))
    return contorno, recortes, gravacoes


def geometria_painel(x0, y0):
    """Painel frontal inclinado, nested no mesmo arquivo de corte a partir de (x0, y0).
    Layout com alma >= 2*t = 12 mm entre todos os recortes e as bordas (acrílico trinca)."""
    contorno = rrect(x0, y0, PN_W, PN_H, 4.0)
    yc = y0 + 45.0                                       # eixo dos instrumentos (janela acima dos furos)
    recortes = [rrect(x0 + 48 - VC288_JANELA[0] / 2, yc - VC288_JANELA[1] / 2, *VC288_JANELA, 1.5),
                rrect(x0 + 105 - CHAVE_W / 2, yc - CHAVE_H / 2, CHAVE_W, CHAVE_H),
                furo(x0 + 140, yc, D_JACK)]
    for i in range(PN_FUROS_FIX):
        recortes.append(furo(x0 + 20 + i * (PN_W - 40) / (PN_FUROS_FIX - 1), y0 + 14, D_M3))
    return contorno, recortes


# ====================================================================== saída DXF / SVG
def aneis(poly):
    """Lista de anéis (listas de (x, y)) de um polígono ou multipolígono shapely."""
    geoms = getattr(poly, "geoms", [poly])
    out = []
    for g in geoms:
        out.append(list(g.exterior.coords))
        out += [list(i.coords) for i in g.interiors]
    return out


def escreve_dxf(arquivo, camadas):
    """DXF R12 mínimo: POLYLINE fechada por anel, CIRCLE para furos redondos.
    R12 é o formato mais compatível com software de laser (RDWorks, LightBurn, CorelDraw)."""
    L = ["0", "SECTION", "2", "ENTITIES"]

    def polilinha(pts, camada):
        L.extend(["0", "POLYLINE", "8", camada, "66", "1", "70", "1",
                  "10", "0.0", "20", "0.0", "30", "0.0"])
        for x, y in pts[:-1]:
            L.extend(["0", "VERTEX", "8", camada, "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0"])
        L.extend(["0", "SEQEND", "8", camada])

    def circulo(cx, cy, r, camada):
        L.extend(["0", "CIRCLE", "8", camada,
                  "10", f"{cx:.4f}", "20", f"{cy:.4f}", "30", "0.0", "40", f"{r:.4f}"])

    for camada, geoms in camadas:
        for g in geoms:
            if isinstance(g, tuple):                 # ("circulo", cx, cy, r)
                circulo(g[1], g[2], g[3], camada)
            else:
                for anel in aneis(g):
                    polilinha(anel, camada)
    L.extend(["0", "ENDSEC", "0", "EOF", ""])
    with open(arquivo, "w", encoding="ascii", newline="\r\n") as f:
        f.write("\n".join(L))


def escreve_svg(arquivo, camadas, w, h):
    """SVG 1:1 em mm (Y invertido: SVG cresce para baixo). Corte em vermelho, gravação em azul."""
    cor = {"CORTE": "#ff0000", "GRAVACAO": "#0000ff"}
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
         f'viewBox="0 0 {w} {h}">']
    for camada, geoms in camadas:
        s.append(f'<g stroke="{cor[camada]}" fill="none" stroke-width="0.1">')
        for g in geoms:
            if isinstance(g, tuple):
                s.append(f'<circle cx="{g[1]:.3f}" cy="{h - g[2]:.3f}" r="{g[3]:.3f}"/>')
            else:
                for anel in aneis(g):
                    d = " ".join(f"{x:.3f},{h - y:.3f}" for x, y in anel)
                    s.append(f'<polygon points="{d}"/>')
        s.append("</g>")
    s.append("</svg>")
    with open(arquivo, "w", encoding="utf-8") as f:
        f.write("\n".join(s))


def separa_circulos(geoms):
    """Troca furos redondos por ('circulo', cx, cy, r) — laser corta círculo exato, não polígono."""
    out = []
    for g in geoms:
        c = g.centroid
        x0, y0, x1, y1 = g.bounds
        r = (x1 - x0) / 2.0
        # círculo: caixa quadrada E área de círculo. Só o perímetro aceitava rasgo em estádio
        # como círculo — e a laser cortava um furo redondo no lugar do rasgo.
        if (abs((x1 - x0) - (y1 - y0)) < 1e-6 and len(g.interiors) == 0
                and abs(g.area - math.pi * r * r) < 0.02 * math.pi * r * r):
            out.append(("circulo", c.x, c.y, r))
        else:
            out.append(g)
    return out


# ====================================================================== verificação
def verifica(info):
    print("== chapa de acrílico ==")
    area = geometria_chapa()[0].area
    m_ch = area * CH_T * RHO_ACR
    print(f"  {CH_W:.0f} x {CH_D:.0f} x {CH_T:.0f} mm de PMMA -> {m_ch:.0f} g "
          f"(área líquida {area/100:.0f} cm²)")
    info["chapa"] = {"largura": CH_W, "profundidade": CH_D, "espessura": CH_T,
                     "massa_g": round(m_ch, 1), "pe_altura": PE_H}

    # ---- 1. tombamento: centro de massa do conjunto contra a borda de apoio mais próxima
    import trimesh, sys
    sys.path.insert(0, DIR_CAD)
    import gerar_pecas as G
    P = {f.split('.')[0]: trimesh.load(os.path.join(RAIZ, "STL", f), process=False)
         for f in os.listdir(os.path.join(RAIZ, "STL")) if f.endswith(".stl") and f[0].isdigit()}

    def massa(m):
        return m.volume * 1.24e-3 * 0.55

    M_MG, M_SG = 13.4, 9.0
    Rd = G.Ry(90)

    def girante(carga):
        _, _, T_br, T_an = G.poses(90, 90)
        it = []
        for arq, M in [("03_braco_motriz", T_br @ G.T(0, G.Y_ELO1, 0)),
                       ("04_braco_livre", T_br @ G.T(0, -G.Y_ELO1, 0)),
                       ("05_antebraco_motriz", T_an @ G.T(0, G.Y_ELO2, 0)),
                       ("06_antebraco_livre", T_an @ G.T(0, -G.Y_ELO2, 0)),
                       ("07_garra_dedo_motriz", T_an @ G.T(G.ESP + 0.8, G.Y_GARRA, G.Z_GARRA) @ Rd),
                       ("08_garra_dedo_livre", T_an @ G.T(G.ESP + 0.8, -G.Y_GARRA, G.Z_GARRA) @ Rd)]:
            m = P[arq].copy(); m.apply_transform(M)
            it.append((massa(P[arq]), m.center_mass[0]))
        pl = P["02_plataforma_giratoria"]
        it += [(massa(pl), pl.center_mass[0]), (M_MG, 0.0),
               (M_MG, (T_br @ np.array([0, G.Y_ELO1 + G.ESP, 70, 1]))[0]),
               (M_SG, (T_an @ np.array([G.PALMA_X[1], G.Y_GARRA, G.Z_GARRA, 1]))[0])]
        if carga:
            it.append((carga, (T_an @ np.array([G.ESP + 2.8, 0, G.Z_GARRA + 49, 1]))[0]))
        mt = sum(m for m, _ in it)
        return mt, sum(m * r for m, r in it) / mt

    b = P["01_base_fixa"]
    m_b, r_b = massa(b), b.center_mass[0]
    # contrapesos: a chapa e a eletrônica, relativos ao eixo de S1 (negativo = atrás)
    pesos = [(m_ch, -(CH_D / 2 - EIXO[1])),
             (M_PROTO, -(PROTO_POS[1] + PROTO_D / 2 - EIXO[1])),
             (M_UNO, -(UNO_POS[1] + UNO_D / 2 - EIXO[1])),
             (M_VC288 + M_MISC, -(PN_Y + 20 - EIXO[1]))]

    def borda_min():
        """Borda de apoio mais próxima dentro do setor varrido por S1 (pés nos cantos)."""
        pes = [(25 - EIXO[0], 25 - EIXO[1]), (CH_W - 25 - EIXO[0], 25 - EIXO[1]),
               (25 - EIXO[0], CH_D - 25 - EIXO[1]), (CH_W - 25 - EIXO[0], CH_D - 25 - EIXO[1])]
        pol = Polygon(pes).convex_hull
        d = []
        for th in np.radians(np.arange(-S1_SETOR, S1_SETOR + 0.5, 1.0)):
            dx, dy = math.sin(th), -math.cos(th)
            lo, hi = 0.0, 1000.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if pol.contains(Point(dx * mid, dy * mid)):
                    lo = mid
                else:
                    hi = mid
            d.append(lo)
        return min(d)

    Rb = borda_min()
    print(f"\n  tombamento (apoio = polígono dos 4 pés; borda mais próxima no setor = {Rb:.0f} mm)")
    tomb = {}
    for carga in (0, 15, 20, 50):
        mg, rg = girante(carga)
        mt = mg + m_b + M_MG + sum(m for m, _ in pesos)
        rt = (mg * rg + m_b * r_b + sum(m * r for m, r in pesos)) / mt
        fs = "inf (CoM atras do eixo)" if rt <= 0 else f"{Rb/rt:.1f}x"
        print(f"     carga {carga:3d} g -> massa {mt:5.0f} g, CoM r = {rt:+6.1f} mm   margem {fs}")
        tomb[carga] = {"massa_total_g": round(mt, 1), "com_r_mm": round(rt, 1)}
    info["tombamento"] = {"borda_apoio_mm": round(Rb, 1), "casos": tomb}

    # ---- 2. setor livre: nenhum componente dentro do alcance do braço
    print(f"\n  setor livre (S1 ±{S1_SETOR:.0f}°, alcance {ALCANCE:.0f} mm, garra desce 28 mm)")
    setor = unary_union([Polygon([(EIXO[0], EIXO[1])] +
                                 [(EIXO[0] + ALCANCE * math.sin(t), EIXO[1] - ALCANCE * math.cos(t))
                                  for t in np.radians(np.arange(-S1_SETOR, S1_SETOR + 1, 2.0))])])
    comp = {"protoboard": rrect(*PROTO_POS, PROTO_W, PROTO_D),
            "Arduino UNO": rrect(*UNO_POS, UNO_W, UNO_D),
            "WAGO +5 V": rrect(*WAGO_POS[0], WAGO_W, WAGO_D),
            "WAGO GND": rrect(*WAGO_POS[1], WAGO_W, WAGO_D),
            "painel": sbox(EIXO[0] - PN_W / 2, PN_Y, EIXO[0] + PN_W / 2, PN_Y + 40)}
    livre = True
    for nome, g in comp.items():
        inter = g.intersection(setor).area
        ok = inter < 1e-6
        livre &= ok
        folga = g.bounds[1] - EIXO[1]
        print(f"     {nome:14s} {'OK  ' if ok else 'COLIDE'} "
              f"(borda da frente a {folga:+.0f} mm do eixo, interseção {inter:.1f} mm²)")
    info["setor_livre_ok"] = bool(livre)

    # ---- 3. acrílico: distância mínima de furo à borda (trinca) e flexão
    print("\n  acrílico: furos e rigidez")
    contorno, recortes, _ = geometria_chapa()
    dmin = min(contorno.exterior.distance(Point(g.centroid)) - math.sqrt(g.area / math.pi)
               for g in recortes)
    reg = 2 * CH_T
    print(f"     menor distância furo->borda: {dmin:.1f} mm  (regra pratica >= 2.t = {reg:.0f} mm) "
          f"{'OK' if dmin >= reg else 'REVER'}")
    E = 3000.0                                        # MPa, PMMA extrudado
    I = CH_W * CH_T ** 3 / 12.0
    Pn = (sum(m for m, _ in pesos) + 143.0) * 9.81e-3  # N: chapa+eletrônica+braço como carga central
    L = CH_D - 40.0
    flecha = Pn * L ** 3 / (48 * E * I)
    print(f"     flecha estimada (viga biapoiada, vão {L:.0f} mm, carga {Pn:.1f} N): {flecha:.2f} mm")
    info["acrilico"] = {"furo_borda_min_mm": round(dmin, 1), "regra_2t_mm": reg,
                        "flecha_mm": round(flecha, 3)}
    print(f"\n  pé de {PE_H:.0f} mm: a fiação de potência passa por baixo; o braço sobe "
          f"{PE_H + CH_T:.0f} mm, o que alivia a pose 'abaixo da mesa'.")
    return info


# ====================================================================== desenho para o relatório
def desenho(contorno, recortes, gravacoes, pn, arquivo):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly

    fig, ax = plt.subplots(figsize=(11, 9))

    def plota(g, **kw):
        for anel in aneis(g):
            ax.add_patch(MPoly(anel, closed=True, **kw))

    plota(contorno, facecolor="#dceaf2", edgecolor="#c0392b", lw=1.4)
    for g in recortes:
        plota(g, facecolor="white", edgecolor="#c0392b", lw=1.0)
    for g in gravacoes:
        plota(g, facecolor="none", edgecolor="#2471a3", lw=0.9, ls="--")
    for g in pn[1]:
        plota(g, facecolor="white", edgecolor="#c0392b", lw=1.0)
    plota(pn[0], facecolor="none", edgecolor="#c0392b", lw=1.4)

    # setor de giro
    th = np.radians(np.arange(-S1_SETOR, S1_SETOR + 1, 2.0))
    ax.fill([EIXO[0]] + list(EIXO[0] + ALCANCE * np.sin(th)),
            [EIXO[1]] + list(EIXO[1] - ALCANCE * np.cos(th)),
            color="#e74c3c", alpha=0.10, lw=0)
    ax.add_patch(plt.Circle(EIXO, DISCO_R, fill=False, ec="#7f8c8d", ls=":", lw=1.2))
    ax.plot(*EIXO, "+", color="#7f8c8d", ms=12)

    rot = [(EIXO[0], EIXO[1] - 95, "ZONA PROIBIDA\nsetor de giro de S1\n(±85°, 186 mm)", 9, "#c0392b"),
           (PROTO_POS[0] + PROTO_W / 2, PROTO_POS[1] + PROTO_D / 2, "protoboard\n400 pontos", 8, "#2471a3"),
           (UNO_POS[0] + UNO_W / 2, UNO_POS[1] + UNO_D / 2, "Arduino UNO", 8, "#2471a3"),
           (WAGO_POS[0][0] + WAGO_W / 2, WAGO_POS[0][1] + 6, "WAGO +5 V", 6, "#2471a3"),
           (WAGO_POS[1][0] + WAGO_W / 2, WAGO_POS[1][1] + 6, "WAGO GND", 6, "#2471a3"),
           (EIXO[0], PN_Y + 12, f"painel inclinado {PN_INCL:.0f}\u00b0", 8, "#2471a3"),
           (EIXO[0], EIXO[1] + 8, "linha do eixo de S1 — nada à frente", 7, "#7f8c8d"),
           (PASSA_CABO[0], PASSA_CABO[1] - 12, "passagem\ndo cabo de S1", 7, "#c0392b"),
           (pn[0].centroid.x, pn[0].bounds[3] + 8, "PAINEL (peça separada): janela DSN-VC288 | chave | jack P4", 8, "#c0392b")]
    for x, y, t, s, c in rot:
        ax.text(x, y, t, ha="center", va="center", fontsize=s, color=c)

    ax.set_xlim(-15, CH_W + 15); ax.set_ylim(-15, CH_D + 115)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"Chapa de apoio — acrílico {CH_W:.0f} × {CH_D:.0f} × {CH_T:.0f} mm "
                 f"(corte a laser) + painel do medidor", fontsize=11)
    fig.tight_layout(); fig.savefig(arquivo, dpi=150); plt.close(fig)


# ====================================================================== main
if __name__ == "__main__":
    contorno, recortes, gravacoes = geometria_chapa()
    pn = geometria_painel(CH_W / 2 - PN_W / 2, CH_D + 20)   # nested acima da chapa

    corte = separa_circulos([contorno] + recortes + [pn[0]] + list(pn[1]))
    camadas = [("CORTE", corte), ("GRAVACAO", gravacoes)]

    f_dxf = os.path.join(DIR_CAD, "corte_base_acrilico.dxf")
    f_svg = os.path.join(DIR_CAD, "corte_base_acrilico.svg")
    escreve_dxf(f_dxf, camadas)
    escreve_svg(f_svg, camadas, CH_W, CH_D + 20 + PN_H)
    print(f"corte -> {os.path.relpath(f_dxf, RAIZ)} e {os.path.relpath(f_svg, RAIZ)}")

    desenho(contorno, recortes, gravacoes, pn, os.path.join(DIR_IMG, "base_layout.png"))
    print(f"desenho -> imagens/base_layout.png\n")

    info = {"parametros": {"eixo_s1": EIXO, "setor_s1_graus": S1_SETOR, "alcance_mm": ALCANCE,
                           "vc288_janela": VC288_JANELA, "painel_inclinacao": PN_INCL}}
    info = verifica(info)
    with open(os.path.join(DIR_CAD, "base_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1, ensure_ascii=False)
    print("\nOK")
