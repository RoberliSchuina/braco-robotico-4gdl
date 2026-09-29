# -*- coding: utf-8 -*-
"""mapa_angulos.py — traduz o ângulo de cada servo para a pose física do elo correspondente.

Fonte única: a convenção de ângulos está em cad/gerar_pecas.py (função montagem/poses) e os limites
em firmware/braco_robotico/braco_robotico.ino. Este script NÃO repete nenhum número à mão: lê os
limites do .ino, aplica as mesmas transformações do CAD e mede o envelope resultante nas malhas.

Convenção do modelo (gerar_pecas.montagem):
    th1  = base,     0  = braço apontando para +X            -> servo S1 = 90 + th1
    th2  = braço,    0  = vertical, + gira para +X           -> servo S2 = 90 + th2
    s3   = cotovelo, ângulo RELATIVO braço->antebraço        -> servo S3 = s3   (th3 absoluto = th2 + s3)
    alfa = giro de cada dedo, 0 = mandíbulas paralelas       -> servo S4 = 75 + alfa

Saída: tabela no terminal + cad/mapa_angulos.json (consumido por relatorio/gerar_manual_montagem.py).
Tempo: ~1 min (constrói as 11 peças).
"""
import os, sys, json, re
import numpy as np
import trimesh

sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # console cp1252 nao aceita os sinais tipograficos

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "cad"))
import gerar_pecas as G

# ------------------------------------------------------------------ limites lidos do firmware
INO = open(os.path.join(RAIZ, "firmware", "braco_robotico", "braco_robotico.ino"), encoding="utf-8").read()
def vetor(nome):
    m = re.search(nome + r"\[N_JUNTAS\]\s*=\s*\{([^}]*)\}", INO)
    return [int(x) for x in m.group(1).split(",")]
def escalar(nome):
    return int(re.search(nome + r"\s*=\s*(\d+)", INO).group(1))

ANG_MIN, ANG_MAX, ANG_HOME = vetor("ANG_MIN"), vetor("ANG_MAX"), vetor("ANG_HOME")
G_FECHADA = escalar("GARRA_FECHADA")
G_ABERTA  = int(re.search(r"GARRA_ABERTA\s*=\s*(\d+)", INO).group(1))
S4_PARALELO = 75          # gerar_pecas: alfa = 0 (dedos paralelos) é montado com o servo em 75°

# ------------------------------------------------------------------ malhas e grupos móveis
P = {arq: construtor() for arq, _n, _f, construtor, _t, _o in G.PECAS}
sv = G.servo_dummy()
R_dedo = G.frame((0, 0, 0), (-1, 0, 0), (0, -1, 0))

braco = trimesh.util.concatenate([m.copy().apply_transform(T) for m, T in [
    (P["03_braco_motriz"], G.T(0, G.Y_ELO1, 0)), (P["04_braco_livre"], G.T(0, -G.Y_ELO1, 0)),
    (sv, G.frame((0, G.Y_ELO1 + G.ESP, 70), (0, 1, 0), (0, 0, -1)))]])

def antebraco(alfa=15.0):
    p_s4 = (G.PALMA_X[1], G.Y_GARRA, G.Z_GARRA)
    return trimesh.util.concatenate([m.copy().apply_transform(T) for m, T in [
        (P["05_antebraco_motriz"], G.T(0, G.Y_ELO2, 0)), (P["06_antebraco_livre"], G.T(0, -G.Y_ELO2, 0)),
        (sv, G.frame(p_s4, (1, 0, 0), (0, -1, 0))),
        (P["07_garra_dedo_motriz"], G.T(G.ESP + 0.8, G.Y_GARRA, G.Z_GARRA) @ G.Rx(-alfa) @ R_dedo),
        (P["08_garra_dedo_livre"], G.T(G.ESP + 0.8, -G.Y_GARRA, G.Z_GARRA) @ G.Rx(alfa) @ R_dedo)]])

ante = antebraco()

def envelope(s2, s3):
    """(z mínimo, z máximo, alcance radial máximo) em mm, com os servos do ombro e do cotovelo nesses ângulos."""
    th2 = s2 - 90
    _, _, T_br, T_an = G.poses(th2, th2 + s3)
    B = braco.copy(); B.apply_transform(T_br)
    A = ante.copy();  A.apply_transform(T_an)
    pts = np.vstack([B.vertices, A.vertices])
    return pts[:, 2].min(), pts[:, 2].max(), np.hypot(pts[:, 0], pts[:, 1]).max()

# ------------------------------------------------------------------ mapas
Z_OMBRO = G.poses(0, 90)[1]          # altura do eixo do ombro (68,8 mm)

def descr_ombro(s2):
    th2 = s2 - 90
    if th2 == 0:  return "braço na VERTICAL (referência)"
    lado = "para a frente (+X)" if th2 > 0 else "para tras (-X)"
    return f"braço {abs(th2)}° fora da vertical, inclinado {lado}"

def descr_cotovelo(s3):
    if s3 == 90: return "antebraço PERPENDICULAR ao braço (referência)"
    if s3 < 90:  return f"antebraço aberto: {90 - s3}° a mais que a perpendicular (tende a alinhar com o braço em 0°)"
    return f"antebraço dobrado sobre o braço: {s3 - 90}° além da perpendicular"

mapa = {"limites": {"ANG_MIN": ANG_MIN, "ANG_MAX": ANG_MAX, "ANG_HOME": ANG_HOME,
                    "GARRA_FECHADA": G_FECHADA, "GARRA_ABERTA": G_ABERTA},
        "z_ombro": round(float(Z_OMBRO), 1)}

# --- S1: base (não muda o envelope, só a direção)
mapa["base"] = [[s1, s1 - 90,
                 ("braço apontando para a frente (referência)" if s1 == 90 else
                  f"conjunto girado {abs(s1 - 90)}° para a {'esquerda' if s1 > 90 else 'direita'}"),
                 ("ANG_MIN" if s1 == ANG_MIN[0] else "ANG_MAX" if s1 == ANG_MAX[0] else
                  "HOME" if s1 == ANG_HOME[0] else "")]
                for s1 in [ANG_MIN[0], 45, ANG_HOME[0], 135, ANG_MAX[0]]]

# --- S2: ombro (cotovelo mantido em home)
mapa["ombro"] = []
for s2 in [ANG_MIN[1], 45, ANG_HOME[1], 120, 135, ANG_MAX[1]]:
    zmin, zmax, r = envelope(s2, ANG_HOME[2])
    nota = ("ANG_MIN" if s2 == ANG_MIN[1] else "ANG_MAX" if s2 == ANG_MAX[1] else
            "HOME" if s2 == ANG_HOME[1] else "")
    if zmin < 0 and not nota: nota = "antebraço abaixo do plano da mesa"
    mapa["ombro"].append([s2, s2 - 90, descr_ombro(s2), round(zmax, 0), round(r, 0), round(zmin, 0), nota])

# --- S3: cotovelo (braço na vertical)
mapa["cotovelo"] = []
for s3 in [20, ANG_MIN[2], 60, ANG_HOME[2], 120, ANG_MAX[2], 148]:
    zmin, zmax, r = envelope(ANG_HOME[1], s3)
    nota = ("ANG_MIN de fábrica" if s3 == ANG_MIN[2] else "ANG_MAX de fábrica" if s3 == ANG_MAX[2] else
            "HOME" if s3 == ANG_HOME[2] else "limite físico: a palma encosta na plataforma" if s3 == 148 else
            "alcance/altura máximos depois de calibrar" if s3 == 20 else "")
    mapa["cotovelo"].append([s3, descr_cotovelo(s3), round(zmax, 0), round(r, 0), round(zmin, 0), nota])

# --- S4: garra
mapa["garra"] = []
for s4 in [72, G_FECHADA, S4_PARALELO, 80, 90, 100, G_ABERTA]:
    alfa = s4 - S4_PARALELO
    nota = ("ANG_MIN de fábrica — 1° ABAIXO do toque das mandíbulas (73°, medido por verificacao.py)" if s4 == ANG_MIN[3] else
            "GARRA_FECHADA" if s4 == G_FECHADA else "GARRA_ABERTA = ANG_MAX" if s4 == G_ABERTA else
            "mandíbulas paralelas — pose de montagem do horn" if s4 == S4_PARALELO else
            "HOME" if s4 == ANG_HOME[3] else "")
    mapa["garra"].append([s4, alfa, round(2 * alfa, 1), nota])

json.dump(mapa, open(os.path.join(RAIZ, "cad", "mapa_angulos.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ relatório no terminal
print(f"Limites lidos do firmware: MIN {ANG_MIN}  MAX {ANG_MAX}  HOME {ANG_HOME}  garra {G_FECHADA}/{G_ABERTA}")
print(f"Eixo do ombro a {Z_OMBRO:.1f} mm da mesa; cotovelo a 70 mm do ombro.\n")
print("== S1 base ==")
for s1, th1, d, n in mapa["base"]:
    print(f"   {s1:3d}° -> th1 = {th1:+4d}°  {d:55s} {n}")
print("\n== S2 ombro (cotovelo em 90°) ==       z máx  alcance  z mín")
for s2, th2, d, zmax, r, zmin, n in mapa["ombro"]:
    print(f"   {s2:3d}° -> th2 = {th2:+4d}°  {d:48s} {zmax:5.0f} {r:7.0f} {zmin:7.0f}   {n}")
print("\n== S3 cotovelo (braço na vertical) ==  z máx  alcance  z mín")
for s3, d, zmax, r, zmin, n in mapa["cotovelo"]:
    print(f"   {s3:3d}°  {d:64s} {zmax:5.0f} {r:7.0f} {zmin:7.0f}   {n}")
print("\n== S4 garra ==")
for s4, alfa, abert, n in mapa["garra"]:
    print(f"   {s4:3d}° -> alfa = {alfa:+3d}°  abertura angular entre mandíbulas {abert:+5.1f}°   {n}")
print("\ncad/mapa_angulos.json atualizado.")
