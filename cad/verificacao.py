# -*- coding: utf-8 -*-
"""
verificacao.py — Checagens de viabilidade do braço (rodar depois de gerar_pecas.py).

1. Malhas estanques e folga dos mancais.
2. Varreduras booleanas: cotovelo x braço, braço x plataforma/base, conjunto girante x colunas da base.
3. Engrenagens da garra: interpenetração e folga de flanco em 361 posições.
4. Torque nos servos (corpo livre com as massas do modelo) e carga útil.

Uso:  python cad/verificacao.py            (varredura de 5 em 5 graus)
      python cad/verificacao.py --fino     (de 1 em 1 grau perto dos limites)
"""
import sys, os, math
import numpy as np
import trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_pecas as G
from shapely.geometry import Point, Polygon as SPoly
from shapely.ops import unary_union

FINO = "--fino" in sys.argv
DENS = 1.24 * 0.55          # g/cm³ efetivos: PLA a 15 % de infill + 3 paredes
M_SG90, M_MG90S = 9.0, 13.4   # g (a BOM usa MG90S no ombro e no cotovelo)
STALL = 1.8                 # kgf·cm a 5 V (SG90 e MG90S)


def massa(m):
    return m.volume / 1000.0 * DENS


def inter(a, b):
    """Volume (mm³) da interseção entre duas malhas."""
    try:
        r = trimesh.boolean.intersection([a, b], engine='manifold')
        return 0.0 if r is None or r.is_empty else r.volume
    except Exception:
        return float('nan')


def junta(ms):
    return trimesh.util.concatenate(ms)


print("== peças ==")
P = {}
for arq, nome, _f, construtor, _t, _o in G.PECAS:
    m = construtor()
    P[arq] = m
    print(f"  {arq:24s} estanque={m.is_watertight}  {massa(m):5.1f} g")
sv = G.servo_dummy()
m_pla = sum(massa(m) for m in P.values())
print(f"  total impresso {m_pla:.1f} g  (+ 2 SG90 + 2 MG90S = {m_pla + 2 * M_SG90 + 2 * M_MG90S:.1f} g)")

# ---------------------------------------------------------------- grupos móveis (frames locais)
# braço: frame no plano de simetria, eixo do ombro na origem, cotovelo em z=70
braco = junta([_m.copy().apply_transform(T) for _m, T in
               [(P["03_braco_motriz"], G.T(0, G.Y_ELO1, 0)), (P["04_braco_livre"], G.T(0, -G.Y_ELO1, 0)),
                (sv, G.frame((0, G.Y_ELO1 + G.ESP, 70), (0, 1, 0), (0, 0, -1)))]])

R_dedo = G.frame((0, 0, 0), (-1, 0, 0), (0, -1, 0))
def antebraco(alfa=15.0):
    p_s4 = (G.PALMA_X[1], G.Y_GARRA, G.Z_GARRA)
    return junta([_m.copy().apply_transform(T) for _m, T in
                  [(P["05_antebraco_motriz"], G.T(0, G.Y_ELO2, 0)), (P["06_antebraco_livre"], G.T(0, -G.Y_ELO2, 0)),
                   (sv, G.frame(p_s4, (1, 0, 0), (0, -1, 0))),
                   (P["07_garra_dedo_motriz"], G.T(G.ESP + 0.8, G.Y_GARRA, G.Z_GARRA) @ G.Rx(-alfa) @ R_dedo),
                   (P["08_garra_dedo_livre"], G.T(G.ESP + 0.8, -G.Y_GARRA, G.Z_GARRA) @ G.Rx(alfa) @ R_dedo)]])

ante = antebraco()
z_plat, z_s2, _, _ = G.poses(0, 90)
base_plat = junta([P["01_base_fixa"],
                   sv.copy().apply_transform(G.frame((0, 0, 30), (0, 0, 1), (1, 0, 0))),
                   P["02_plataforma_giratoria"].copy().apply_transform(G.T(0, 0, z_plat)),
                   sv.copy().apply_transform(G.frame((0, G.Y_PAR_A[1], z_s2), (0, 1, 0), (1, 0, 0)))])

# ---------------------------------------------------------------- 2. varreduras
passo = 1 if FINO else 5
print("\n== varredura cotovelo (antebraço x braço; ângulo relativo, 180 = dobrado sobre o braço) ==")
onset = None
for a in range(0, 181, passo):
    A = ante.copy(); A.apply_transform(G.T(0, 0, 70) @ G.Ry(a))
    v = inter(A, braco)
    if v > 1.0 and onset is None:
        onset = a
    if v > 1.0 or a % 30 == 0:
        print(f"   {a:3d}° -> {v:9.1f} mm³")
    if onset is not None and a >= onset + 2 * passo:
        break
print(f"   primeiro contato em {onset}°" if onset else "   sem colisão em 0..180°")

print("\n== varredura ombro x plataforma/base (cotovelo em ângulo RELATIVO = ângulo do servo) ==")
pior = 0.0
for rel in (20, 90, 140, 146, 150):
    for th2 in range(-75, 76, 15):
        M = G.T(0, 0, z_s2) @ G.Ry(th2)
        A = ante.copy(); A.apply_transform(M @ G.T(0, 0, 70) @ G.Ry(rel))
        B = braco.copy(); B.apply_transform(M)
        v = inter(B, base_plat) + inter(A, base_plat)
        if rel <= 140:
            pior = max(pior, v)
        if v > 1.0:
            alvo = "disco da base: pose abaixo do plano da mesa" if th2 >= 45 else "plataforma"
            print(f"   ombro {90+th2:3d}° cotovelo {rel:3d}° -> {v:8.1f} mm³   [{alvo}]")
print(f"   pior caso dentro dos limites do firmware (ombro 15..165°, cotovelo 20..140°): {pior:.1f} mm³")
print("   nota: com o ombro > 135° e o cotovelo dobrado o antebraço desce abaixo do plano da mesa e encosta")
print("         no disco da base — limite do operador (ou elevar a base 30 mm), não do firmware.")

# ---------------------------------------------------------------- 2b. envelope de trabalho
print("\n== envelope (mm; z medido da mesa, alcance medido do eixo da base) ==")
def envelope(th2, th3):
    _, _, T_br, T_an = G.poses(th2, th3)
    B = braco.copy(); B.apply_transform(T_br)
    A = ante.copy(); A.apply_transform(T_an)
    pts = np.vstack([B.vertices, A.vertices])
    return pts[:, 2].max(), np.hypot(pts[:, 0], pts[:, 1]).max(), pts[:, 2].min()

for th2, s3, rot in [(0, 20, "altura máxima (ombro 90°, cotovelo 20° = quase esticado)"),
                     (0, 90, "repouso/home (ombro 90°, cotovelo 90°)"),
                     (75, 90, "alcance máximo (ombro 165°, cotovelo 90°)"),
                     (75, 20, "ombro 165°, cotovelo 20° (braço e antebraço alinhados)"),
                     (45, 90, "ombro 135°, cotovelo 90° (garra abaixo da mesa?)")]:
    zmax, rmax, zmin = envelope(th2, th2 + s3)
    print(f"   {rot:52s} z {zmin:6.1f} .. {zmax:6.1f}   alcance {rmax:6.1f}")

# ---------------------------------------------------------------- 3. engrenagens (2D)
print("\n== engrenagens da garra ==")
from shapely.affinity import rotate, translate
pior_int, pior_folga = 0.0, 9.9
for k in range(0, 361):
    a = k * 0.25
    g1 = rotate(G.engrenagem_poly(), a, origin=(0, 0))
    g2 = rotate(G.engrenagem_poly(fase_graus=360 / G.GEAR_N / 2), -a, origin=(0, 0))
    g2 = translate(g2, xoff=2 * G.Y_GARRA)
    pior_int = max(pior_int, g1.intersection(g2).area)
    pior_folga = min(pior_folga, g1.distance(g2) if g1.distance(g2) > 0 else 0.0)
print(f"   interpenetração máxima {pior_int:.4f} mm²   folga de flanco mínima {pior_folga:.3f} mm")

# ---------------------------------------------------------------- 3b. opções de garra
print("\n== garra: opção A (mandíbula plana) x opção B (mandíbula em V) ==")
from shapely.geometry import box as sbox
from shapely.affinity import rotate as rot2d, translate as tr2d

def perfil_dedo(tipo, s=1, com_engrenagem=True):
    """Silhueta 2D do dedo no plano das engrenagens (mesmas cotas de gerar_pecas.dedo)."""
    partes = [sbox(-5, 0, 5, 55), sbox(min(0, s * 10), 43 if tipo == "plana" else 38, max(0, s * 10), 55)]
    if com_engrenagem:
        partes.append(G.engrenagem_poly(fase_graus=0.0 if s > 0 else 360 / G.GEAR_N / 2))
    forma = unary_union(partes)
    if tipo == "v":
        forma = forma.difference(SPoly([(s * 10.5, 41.0), (s * 10.5, 52.0), (s * 5.0, 46.5)]))
    return forma

def garra_2d(tipo, alfa, com_engrenagem=True):
    """Dedos montados com centros a 24 mm; alfa = 0 são dedos paralelos, alfa > 0 abre (S4 = 75 + alfa)."""
    a = tr2d(rot2d(perfil_dedo(tipo, +1, com_engrenagem), +alfa, origin=(0, 0)), xoff=-G.Y_GARRA)
    b = tr2d(rot2d(perfil_dedo(tipo, -1, com_engrenagem), -alfa, origin=(0, 0)), xoff=+G.Y_GARRA)
    return a, b

def objeto_maximo(tipo, alfa):
    """Maior cilindro em pé (Ø, mm) que as duas mandíbulas tocam ao mesmo tempo."""
    a, b = garra_2d(tipo, alfa)
    ym = 49.0 if tipo == "plana" else 46.5          # meio da face útil da mandíbula
    r = math.radians(alfa)
    yc = 10 * math.sin(r) + ym * math.cos(r)
    c = Point(0.0, yc)
    return 2 * min(c.distance(a), c.distance(b))

for tipo, nome in [("plana", "A — plana"), ("v", "B — em V ")]:
    print(f"   {nome}  " + " | ".join(f"S4={s:3d}°: Ø{objeto_maximo(tipo, s - 75):5.1f}" for s in (75, 80, 90, 100, 110)))
for tipo, nome in [("plana", "A"), ("v", "B")]:
    toque = None
    for alfa in np.arange(0.0, -10.01, -0.25):
        a, b = garra_2d(tipo, alfa, com_engrenagem=False)
        if a.intersects(b) and a.intersection(b).area > 0.02:
            toque = alfa + 0.25; break
    print(f"   mandíbulas {nome} se tocam em alfa = {toque:.2f}°  ->  S4 mínimo {75 + toque:.2f}°")
print("   (S4 = 75° = dedos paralelos, 110° = ANG_MAX. A opção B toca o cilindro em 4 pontos e auto-centra;")
print("    a opção A toca em 2 pontos, melhor para faces planas.)")


# ---------------------------------------------------------------- 4. torque
print("\n== torque (kgf·cm; stall SG90/MG90S a 5 V = 1,8) ==")
def corpos(th2, th3, carga_g=0.0):
    """(massa, centro de massa global) de cada corpo, com o braço em th2 e o antebraço em th3 (absoluto)."""
    _, zs2, T_br, T_an = G.poses(th2, th3)
    itens = []
    for arq, M in [("03_braco_motriz", T_br @ G.T(0, G.Y_ELO1, 0)), ("04_braco_livre", T_br @ G.T(0, -G.Y_ELO1, 0)),
                   ("05_antebraco_motriz", T_an @ G.T(0, G.Y_ELO2, 0)), ("06_antebraco_livre", T_an @ G.T(0, -G.Y_ELO2, 0)),
                   ("07_garra_dedo_motriz", T_an @ G.T(G.ESP + 0.8, G.Y_GARRA, G.Z_GARRA) @ R_dedo),
                   ("08_garra_dedo_livre", T_an @ G.T(G.ESP + 0.8, -G.Y_GARRA, G.Z_GARRA) @ R_dedo)]:
        m = P[arq].copy(); m.apply_transform(M)
        itens.append((massa(P[arq]), m.center_mass, not arq.startswith(("03", "04"))))
    p_s3 = (T_br @ np.array([0, G.Y_ELO1 + G.ESP, 70, 1]))[:3]
    p_s4 = (T_an @ np.array([G.PALMA_X[1], G.Y_GARRA, G.Z_GARRA, 1]))[:3]
    itens += [(M_MG90S, p_s3, False), (M_SG90, p_s4, True)]
    if carga_g:
        itens.append((carga_g, (T_an @ np.array([G.ESP + 2.8, 0, G.Z_GARRA + 49, 1]))[:3], True))
    return itens, zs2, T_an

def torques(th2, th3, carga_g=0.0):
    itens, zs2, T_an = corpos(th2, th3, carga_g)
    p_cot = (G.poses(th2, th3)[2] @ np.array([0, 0, 70, 1]))[:3]
    t_omb = sum(m / 1000.0 * c[0] / 10.0 for m, c, _ in itens)                       # braço de alavanca em x (cm)
    t_cot = sum(m / 1000.0 * (c[0] - p_cot[0]) / 10.0 for m, c, dist in itens if dist)
    return abs(t_omb), abs(t_cot)

for th2, th3, carga, rot in [(90, 90, 0, "braço horizontal, antebraço horizontal (alcance máximo)"),
                             (90, 90, 25, "idem + 25 g na garra"),
                             (90, 90, 50, "idem + 50 g na garra"),
                             (75, 90, 0, "th2 = +75° (limite do firmware)"),
                             (0, 90, 25, "braço vertical, antebraço horizontal + 25 g")]:
    a, b = torques(th2, th3, carga)
    print(f"   {rot:52s} ombro {a:5.2f} ({100*a/STALL:3.0f} %)   cotovelo {b:5.2f} ({100*b/STALL:3.0f} %)")

# carga útil: maior massa na garra com 60 % do stall no ombro (margem de 40 %)
lo, hi = 0.0, 200.0
for _ in range(24):
    mid = (lo + hi) / 2
    a, b = torques(90, 90, mid)
    if max(a, b) <= 0.6 * STALL:
        lo = mid
    else:
        hi = mid
print(f"   carga útil com alcance máximo e 60 % do stall: {lo:.0f} g")
print("\nOK")
