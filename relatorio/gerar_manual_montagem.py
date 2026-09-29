# -*- coding: utf-8 -*-
"""gerar_manual_montagem.py — manual de montagem passo a passo (relatorio/Manual_Montagem.docx).

Documento de bancada: quem recebe as peças impressas, os 4 servos e os fixadores consegue montar,
ligar, calibrar e usar o braço sem consultar o relatório. Todas as cotas vêm de cad/gerar_pecas.py,
os fixadores de relatorio/parafusos.py e os ângulos/comandos de firmware/braco_robotico.ino.
"""
import os, json, sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "relatorio"))
from parafusos import FIXADORES, custo_total
IMG = lambda n: os.path.join(RAIZ, "imagens", n)
SAIDA = os.path.join(RAIZ, "relatorio", "Manual_Montagem.docx")
info = json.load(open(os.path.join(RAIZ, "cad", "pecas_info.json"), encoding="utf-8"))

doc = Document()
for s in doc.sections:
    s.top_margin = s.bottom_margin = Cm(2.2); s.left_margin = Cm(2.5); s.right_margin = Cm(2)
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
for n, sz in [("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)]:
    doc.styles[n].font.size = Pt(sz); doc.styles[n].font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)

# ------------------------------------------------------------------ utilidades de layout
def H(t, n=1): return doc.add_heading(t, n)

def P(t="", b=False, i=False, al=None, sz=None):
    p = doc.add_paragraph(); r = p.add_run(t); r.bold = b; r.italic = i
    if sz: r.font.size = Pt(sz)
    if al == "c": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if al == "j": p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p

def B(items, style="List Bullet"):
    for t in items:
        p = doc.add_paragraph(style=style)
        if isinstance(t, tuple): r = p.add_run(t[0]); r.bold = True; p.add_run(t[1])
        else: p.add_run(t)

def N(items): B(items, "List Number")

def tabela(cab, linhas, larguras=None, fs=9):
    t = doc.add_table(rows=1, cols=len(cab)); t.style = "Light Grid Accent 1"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, h in zip(t.rows[0].cells, cab):
        c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(fs)
    for ln in linhas:
        for c, v in zip(t.add_row().cells, ln):
            c.text = ""; r = c.paragraphs[0].add_run(str(v)); r.font.size = Pt(fs)
    if larguras:
        for row in t.rows:
            for c, w in zip(row.cells, larguras): c.width = Cm(w)
    doc.add_paragraph()
    return t

def figura(arq, legenda, larg=15.0):
    if os.path.exists(arq):
        doc.add_picture(arq, width=Cm(larg)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    P(legenda, i=True, al="c", sz=9)

def campo(p, instr):
    r = p.add_run(); f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "(F9 atualiza)"
    f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
    for e in (f1, it, f2, t, f3): r._r.append(e)

CORES = {"ATENÇÃO": "FFF2CC", "NUNCA": "F8CBAD", "DICA": "E2EFDA", "CONFERIR": "DEEAF6"}
def caixa(rotulo, texto):
    """Bloco destacado de uma célula (aviso, dica ou ponto de conferência)."""
    t = doc.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cel = t.rows[0].cells[0]; cel.width = Cm(16)
    sh = OxmlElement("w:shd"); sh.set(qn("w:fill"), CORES.get(rotulo, "F2F2F2"))
    cel._tc.get_or_add_tcPr().append(sh)
    cel.text = ""
    p = cel.paragraphs[0]
    r = p.add_run(rotulo + " — "); r.bold = True; r.font.size = Pt(9.5)
    r2 = p.add_run(texto); r2.font.size = Pt(9.5)
    doc.add_paragraph()

def passo(num, titulo, tempo, pecas, fixadores, fazer, porque, conferir, avisos=()):
    """Bloco padrão de uma etapa de montagem."""
    H(f"Etapa {num} — {titulo}", 2)
    t = doc.add_table(rows=3, cols=2); t.style = "Light List Accent 1"
    for i, (k, v) in enumerate([("Tempo", tempo), ("Peças", pecas), ("Fixadores", fixadores)]):
        c0, c1 = t.rows[i].cells
        c0.text = ""; r = c0.paragraphs[0].add_run(k); r.bold = True; r.font.size = Pt(9)
        c1.text = ""; r = c1.paragraphs[0].add_run(v); r.font.size = Pt(9)
        c0.width = Cm(2.6); c1.width = Cm(13.4)
    doc.add_paragraph()
    P("Como fazer", b=True, sz=10.5); N(fazer)
    P("Por que assim", b=True, sz=10.5); P(porque, al="j", sz=10)
    caixa("CONFERIR", conferir)
    for a in avisos: caixa(a[0], a[1])

# rodapé
fp = doc.sections[0].footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp.add_run("Manual de Montagem — Braço Robótico 4 GDL — FAESA        Página "); campo(fp, "PAGE")

# ================================================================== CAPA
for _ in range(5): P()
P("BRAÇO ROBÓTICO DE 4 GRAUS DE LIBERDADE", b=True, al="c", sz=22)
P("MANUAL DE MONTAGEM", b=True, al="c", sz=18)
P("Da peça impressa ao braço calibrado — passo a passo", al="c", sz=12, i=True)
P()
figura(IMG("montagem_isometrica.png"), "", 13.5)
P("FAESA — Engenharia da Computação — Sistemas Embarcados — 2026/2", al="c", sz=11)
P("Aluno(a): ______________________________    Data da montagem: ____ / ____ / ______", al="c", sz=10)
doc.add_page_break()

# ================================================================== COMO USAR
H("Como usar este manual", 1)
P("Leia a etapa inteira antes de executá-la. Cada etapa tem sempre a mesma estrutura: o que fazer "
  "(passos numerados, na ordem), por que assim (o motivo do projeto — ajuda a decidir na hora que algo "
  "não encaixa) e um ponto de conferência, que você só deve ultrapassar depois de conferir.", al="j")
tabela(["Bloco", "Significado"], [
    ["CONFERIR", "Teste de fim de etapa. Se não passar, não siga adiante — o erro só fica mais caro depois."],
    ["ATENÇÃO", "Ponto onde é fácil errar e o prejuízo é retrabalho (desmontar, reimprimir uma peça)."],
    ["NUNCA", "Ação que queima componente ou quebra peça. Sem exceção."],
    ["DICA", "Atalho ou truque de bancada que não é obrigatório."],
], [3.0, 13.0])
P("Convenções de nome", b=True)
B([("Motriz e livre: ", "cada elo do braço é formado por DUAS chapas. A motriz é a que recebe o horn do servo "
    "(é ela que é puxada pelo motor); a livre é a do outro lado, que só gira apoiada num pino impresso (munhão). "
    "As duas juntas formam uma forquilha, como um garfo."),
   ("S1, S2, S3, S4: ", "os quatro servos — S1 base (gira o conjunto), S2 ombro, S3 cotovelo, S4 garra."),
   ("Horn: ", "a haste plástica branca que acompanha o servo e se encaixa no eixo estriado."),
   ("Munhão e mancal: ", "munhão é o pino Ø9 mm impresso na peça; mancal é o furo Ø9,4 mm que o recebe. "
    "É o par que substitui o rolamento do lado livre.")])
P("Tempo total previsto", b=True)
tabela(["Fase", "Tempo", "Observação"], [
    ["Impressão das peças", "≈ 6 h 40 min", "132 g de PLA no total (braço 93 g + suporte do controle 38 g)"],
    ["Preparo das peças e dos servos", "40 min", "Limpeza de furos e centragem dos servos em 90°"],
    ["Montagem mecânica (etapas 1 a 12)", "1 h 30 min", "Sem pressa, conferindo cada etapa"],
    ["Montagem elétrica", "40 min", "Protoboard, fonte e cabos"],
    ["Firmware, calibração e testes", "1 h", "Ajuste de ANG_MIN/ANG_MAX na bancada"],
], [5.5, 3.0, 7.5])
doc.add_page_break()

# ================================================================== 1 ANTES DE COMEÇAR
H("1. Antes de começar", 1)

H("1.1 O que você vai montar", 2)
P("Um braço de 4 graus de liberdade (base, ombro, cotovelo e garra) acionado por 4 micro servos e "
  "comandado por dois joysticks analógicos. O firmware grava até 16 poses e as reproduz em sequência. "
  "Na posição de repouso (todos os servos em 90°) o braço fica com o elo superior na vertical e o "
  "antebraço na horizontal, com a garra a 165 mm de altura e 119 mm à frente do centro da base.", al="j")
figura(IMG("montagem_repouso.png"),
       "Figura 1 — Posição de repouso (home). É esta a pose de referência para encaixar todos os horns.", 13.0)
P("Números do conjunto montado (medidos no modelo):", b=True, sz=10.5)
tabela(["Grandeza", "Valor"], [
    ["Alcance horizontal máximo", "186 mm (ombro 165°, cotovelo 20°)"],
    ["Altura máxima da garra", "249 mm"],
    ["Abertura da garra (mandíbula plana)", "Ø4 mm (fechada) a Ø58 mm (aberta)"],
    ["Abertura da garra (mandíbula em V)", "Ø10 mm a Ø53 mm, com 4 pontos de contato"],
    ["Carga útil", "≈ 20 g com o braço estendido; ≈ 65 g recolhido"],
    ["Massa da parte móvel", "≈ 59 g"],
], [6.5, 9.5])

H("1.2 Ferramentas", 2)
tabela(["Ferramenta", "Onde é usada", "Obrigatória?"], [
    ["Chave Phillips PH0 (ponta fina)", "Micro parafusos dos horns e parafusos dos servos", "Sim"],
    ["Chave Phillips PH1", "Parafusos M3 (travessas, palma, joysticks, base)", "Sim"],
    ["Chave de boca ou canhão 5,5 mm", "Porcas M3 (pino da garra e joysticks)", "Sim"],
    ["Brocas 1,5 / 1,6 / 2,5 / 3,4 mm (à mão)", "Repassar furos que fecharam na impressão", "Sim"],
    ["Lixa 220", "Ajustar o munhão Ø9 se entrar apertado", "Sim"],
    ["Alicate de bico e estilete", "Retirar bolinhas de filamento e rebarbas", "Sim"],
    ["Multímetro", "Conferir 5 V e continuidade antes de ligar os servos", "Muito recomendável"],
    ["Ferro de solda", "Só se optar por soldar os extensores de cabo", "Não"],
    ["Paquímetro", "Conferir Ø9 do munhão e Ø9,4 do mancal", "Não"],
], [5.5, 7.5, 3.0])
caixa("DICA", "Uma chave PH0 de eletrônica (as de kit de celular) é o que funciona nos micro parafusos de 1,7 mm. "
               "Chave grande demais arredonda a cabeça no primeiro aperto.")

H("1.3 Segurança", 2)
caixa("NUNCA", "Alimentar o Arduino pelo USB e pela fonte externa no pino 5V ao mesmo tempo. As duas fontes "
                "brigam pelo mesmo barramento e o regulador do Arduino pode queimar. Escolha uma das duas.")
caixa("NUNCA", "Usar fonte de 6 V. Toda a análise de torque e corrente do projeto é para 5 V; a 6 V a corrente "
                "de travamento sobe para ≈ 0,85 A por servo (3,4 A no total).")
caixa("ATENÇÃO", "Não gire o braço com a mão enquanto os servos estiverem energizados: você está forçando a "
                  "engrenagem interna contra o motor. Desligue a fonte antes de reposicionar qualquer elo.")
caixa("ATENÇÃO", "A garra fecha com força suficiente para machucar a ponta do dedo e para quebrar o dente da "
                  "engrenagem impressa. Mantenha os dedos fora do vão ao energizar.")
caixa("ATENÇÃO", "A base solta TOMBA com cerca de 15 g na garra em extensão máxima. Fixar o disco na tábua "
                  "(etapa 11) não é opcional.")

H("1.4 Conferência do material", 2)
P("Peças impressas (11 arquivos STL; as peças 10 e 11 são a garra alternativa — imprima 07/08 ou 10/11):", b=True, sz=10.5)
tabela(["Arquivo", "Peça", "Massa", "Tempo", "Orientação de impressão"],
       [[p["arquivo"].replace(".stl", ""), p["nome"], f"{p['massa_estimada_g']:.1f} g",
         f"{p['tempo_estimado_min']} min", p["impressao"]] for p in info],
       [3.6, 3.4, 1.5, 1.4, 6.1], fs=8)
figura(IMG("pecas_impressao.png"), "Figura 2 — As peças na orientação em que devem ser impressas (PLA, 0,2 mm, "
                                   "15 % de preenchimento, 3 paredes, SEM suportes).", 15.0)
P("Fixadores (lista completa, com quantidade a comprar):", b=True, sz=10.5)
tabela(["#", "Fixador", "Qtd.", "Onde"],
       [[f[0], f[1][:78], f[2], f[4][:88]] for f in FIXADORES], [0.9, 6.6, 1.0, 7.5], fs=8)
P(f"Custo estimado dos fixadores: R$ {custo_total():.0f}.", sz=9, i=True)
P("Eletrônica:", b=True, sz=10.5)
tabela(["Item", "Qtd.", "Observação"], [
    ["Arduino UNO R3", "1", "Qualquer clone serve; o firmware usa 36 % da flash"],
    ["Micro servo MG90S (ou SG90)", "4", "MG90S tem engrenagem metálica e rolamento; mesmo torque a 5 V"],
    ["Módulo joystick KY-023", "2", "Com os 5 pinos (GND, +5V, VRx, VRy, SW)"],
    ["Fonte chaveada 5 V / 5 A", "1", "3 A já atende (pico normal 1,85 A); 5 A é margem"],
    ["Capacitor eletrolítico 1000 µF / 16 V", "1", "No barramento de 5 V dos servos, junto à protoboard"],
    ["Capacitor cerâmico 100 nF", "4", "Um em cada servo, o mais perto possível dos terminais"],
    ["Protoboard 830 furos + jumpers", "1", "Só o lado direito das trilhas é usado"],
    ["Extensor de servo 300 mm", "2", "Os 250 mm de fábrica não chegam de S3 e S4 ao circuito"],
    ["Tábua/MDF ≈ 200 × 200 mm", "1", "Base de fixação — obrigatória"],
], [6.0, 1.2, 8.8])
doc.add_page_break()

# ================================================================== 2 PREPARO
H("2. Preparo (não pule esta parte)", 1)

H("2.1 Repassar os furos das peças impressas", 2)
P("A impressão 3D fecha furos pequenos em 0,2 a 0,3 mm. Passe a broca à mão (sem furadeira, girando entre os "
  "dedos) em todos os furos, só para tirar a sobra de material — o furo já está no lugar certo:", al="j")
tabela(["Furo no desenho", "Broca", "Para que serve", "Onde está"], [
    ["Ø1,5 mm", "1,5 mm", "Micro parafuso PA 1,7 × 6 do horn", "Fundo dos 4 bolsos de horn"],
    ["Ø1,7 mm", "1,6 mm", "Parafuso PA 2,0 × 8 do flange do servo", "2 furos ao lado de cada rasgo de servo"],
    ["Ø2,5 mm", "2,5 mm", "Furo-piloto do M3 × 10 (a rosca é feita no PLA)", "Reforço da travessa e da palma"],
    ["Ø2,6 mm", "2,6 mm", "Parafuso central do horn (passante)", "Centro de cada bolso de horn"],
    ["Ø3,4 mm", "3,4 mm", "M3 passante", "Pino da garra, travessas, disco da base, suporte"],
    ["Ø9,4 mm", "—", "Mancal do munhão — NÃO alargar", "Parede livre da plataforma e chapa livre do braço"],
], [3.0, 1.6, 6.4, 5.0])
caixa("NUNCA", "Alargar o mancal Ø9,4 para o munhão entrar mais fácil. Quem deve ser lixado é o munhão (o macho), "
                "nunca o furo: alargando o furo você cria folga que vira trepidação na ponta da garra.")
caixa("DICA", "Faça o teste a seco agora: encaixe cada munhão no seu mancal sem parafuso nenhum. Deve entrar com "
               "a força dos dedos e girar liso. Se raspar, lixe o munhão (lixa 220, meia volta de cada vez) até girar. "
               "Descobrir isso agora custa 2 minutos; descobrir na etapa 6 custa desmontar o braço.")

H("2.2 Identificar as peças", 2)
P("As chapas motriz e livre de cada elo são parecidas de longe. Marque com fita crepe antes de começar — a "
  "diferença é fácil de ver de perto:", al="j")
tabela(["Peça", "Como reconhecer"], [
    ["03 Braço motriz", "Chapa plana de 4 mm com DOIS recortes: o bolso do horn (redondo, raso) e o rasgo retangular do servo S3"],
    ["04 Braço livre", "Tem um pino Ø9 saliente (munhão do ombro), um furo Ø9,4 (mancal do cotovelo) e a travessa em L"],
    ["05 Antebraço motriz", "Chapa plana com UM bolso de horn e nenhum rasgo de servo"],
    ["06 Antebraço livre", "A maior das quatro: chapa + a palma em pé (67 mm), com o rasgo do servo S4"],
    ["07/10 Dedo motriz", "Engrenagem com bolso de horn (para o horn simples de S4)"],
    ["08/11 Dedo livre", "Engrenagem com ressalto cilíndrico Ø9 × 10,8 e furo Ø3,4 passante"],
], [4.0, 12.0])

H("2.3 Centrar os 4 servos em 90° — a etapa mais importante do manual", 2)
P("O eixo do servo é estriado (≈ 21 dentes). Cada dente vale 17,1°; encaixar o horn um dente fora desloca todo "
  "o elo em até 8,6°. Por isso o horn NUNCA é encaixado com o servo desligado: primeiro o servo vai para 90° "
  "por software, depois o horn é encaixado na posição certa.", al="j")
N(["Monte só o mínimo elétrico: Arduino ligado ao USB, o servo em D3, alimentado pela fonte de 5 V com o GND "
   "comum (veja a seção 5). Um servo por vez basta.",
   "Grave o firmware definitivo (seção 6). Ao ligar, ele já leva todas as saídas para 90° — é exatamente o que "
   "precisamos.",
   "Ligue e deixe o servo atingir a posição. Não gire o eixo com a mão depois disso.",
   "Repita com os quatro servos e escreva S1, S2, S3, S4 em cada um com fita.",
   "Para o servo da garra (S4), mande pelo Monitor Serial o comando 's 3 75' (a 115200 bauds): a garra é montada "
   "a 75°, quase fechada, e não a 90°."])
caixa("ATENÇÃO", "Se você não tiver o circuito pronto ainda, pode centrar os servos com um sketch mínimo "
                  "(Servo.attach + write(90)). O que não vale é encaixar o horn 'no olho'.")
caixa("CONFERIR", "Com o servo em 90°, o horn encaixado deve poder girar ~85° para cada lado sem bater no batente "
                   "interno. Se de um lado ele trava logo, o horn está um dente fora: puxe e reencaixe.")
P("Qual horn em qual servo:", b=True, sz=10.5)
tabela(["Servo", "Junta", "Horn", "Micro parafusos", "Vai fixado em"], [
    ["S1", "Base (gira tudo)", "Em cruz (4 braços)", "4", "02 Plataforma giratória"],
    ["S2", "Ombro", "Duplo (2 braços)", "4", "03 Braço motriz"],
    ["S3", "Cotovelo", "Duplo (2 braços)", "4", "05 Antebraço motriz"],
    ["S4", "Garra", "Simples (1 braço)", "2", "07 (ou 10) Dedo motriz"],
], [1.6, 3.4, 3.6, 2.4, 5.0])
doc.add_page_break()

# ================================================================== 3 MONTAGEM
H("3. Montagem mecânica", 1)
P("Regra geral que vale para as quatro juntas: o horn é parafusado na PEÇA primeiro, com o horn fora do servo. "
  "Só depois o conjunto peça+horn é empurrado no eixo estriado e travado com o parafuso central. É muito mais "
  "fácil acertar os micro parafusos com a peça apoiada na mesa do que no ar.", al="j")
caixa("DICA", "Separe os fixadores em potinhos por etapa antes de começar. Micro parafuso de 1,7 mm que cai no "
               "chão não é encontrado.")

passo(1, "Servo S1 dentro da base fixa", "10 min",
      "01_base_fixa", "2 × PA 2,0 × 8 (item 1)",
      ["Passe o cabo de S1 por dentro da torre, de cima para baixo, e puxe-o pelo canal que sai sob o disco.",
       "Encaixe o corpo do servo no rasgo retangular do topo da torre, de cima para baixo. O rasgo é "
       "assimétrico (o eixo do servo é deslocado 5,3 mm do centro do corpo): só entra de um jeito.",
       "A aba (flange) do servo deve encostar no topo da torre, com o eixo estriado para cima.",
       "Aperte os 2 parafusos PA 2,0 × 8 nos furos-piloto Ø1,7, até encostar + 1/4 de volta."],
      "S1 fica pendurado dentro da torre oca para baixar o centro de massa e para o cabo sair sem laço. As 4 "
      "colunas Ø9 em volta não seguram o servo: elas são o encosto da plataforma, para que o peso do braço não "
      "fique todo no estriado plástico do horn.",
      "O eixo de S1 deve estar na vertical, girar livre com a mão e o cabo deve sair pelo canal sem ficar "
      "prensado. A folga entre o topo das colunas (z = 40,3 mm) e a futura plataforma é de apenas 0,5 mm.",
      [("ATENÇÃO", "Não aperte o parafuso até o fim de curso da rosca — o PLA racha. Aperto de encosto + 1/4 de volta.")])

passo(2, "Plataforma giratória no horn de S1", "10 min",
      "02_plataforma_giratoria", "4 × micro PA 1,7 × 6 (item 2) + 1 × PA 2,0 × 6 com arruela M2 (item 1b)",
      ["Com a plataforma de cabeça para baixo na mesa, encaixe o horn em CRUZ no bolso raso (2 mm) do lado de baixo.",
       "Prenda o horn com 4 micro parafusos PA 1,7 × 6 — um em cada braço da cruz, no furo mais próximo do centro.",
       "Confirme que S1 está em 90° (energizado). Empurre o conjunto plataforma+horn no eixo estriado, com a "
       "plataforma alinhada com a base (veja a Figura 1).",
       "Coloque a arruela M2 no parafuso central PA 2,0 × 6 e aperte-o no furo cego do eixo do servo, pelo furo "
       "Ø2,6 da plataforma."],
      "O bolso de 2 mm é quem transmite o torque (encaixe de forma); o parafuso central só impede que a peça "
      "escape do eixo. Por isso o bolso tem o formato do horn — cubo Ø9,2 mm e braços afinando até Ø5,4 mm.",
      "Gire a plataforma com a mão (servo desligado): ela deve girar sem raspar, apoiada nas 4 colunas. "
      "Energizando, S1 deve conseguir girar a plataforma de 5° a 175° sem esforço audível.",
      [("ATENÇÃO", "Antes de apertar o parafuso central, rosqueie-o no eixo SEM a peça e veja quanto ele entra. "
                    "O furo cego do eixo varia de 3 a 5 mm entre fabricantes: parafuso comprido demais bate no fundo "
                    "e a peça continua solta.")])

passo(3, "Servo S2 (ombro) na plataforma", "5 min",
      "02_plataforma_giratoria (já montada)", "2 × PA 2,0 × 8 (item 1)",
      ["Identifique as duas paredes verticais da plataforma: a MOTRIZ (a mais próxima do centro) tem o rasgo do "
       "servo; a LIVRE (a mais afastada) tem só o furo redondo Ø9,4 do mancal.",
       "Encaixe S2 no rasgo da parede motriz com o CORPO apontando para dentro da forquilha (para o lado da "
       "parede livre) e a aba apoiada na face externa.",
       "Aperte os 2 parafusos PA 2,0 × 8.",
       "Passe o cabo de S2 para baixo, junto ao cabo de S1."],
      "As duas paredes não são simétricas de propósito: o corpo do SG90 avança 15,9 mm abaixo da aba, e a parede "
      "livre precisa ficar além disso (sobram 2,1 mm de folga). As duas nervuras que ligam as paredes ao disco "
      "formam um caixote — é o que impede a forquilha de abrir sob carga.",
      "Com S2 em 90°, o eixo estriado deve estar na altura do furo do mancal da parede oposta, e os dois devem "
      "estar alinhados: essa é a linha de rotação do ombro.")

passo(4, "Servo S3 (cotovelo) na chapa motriz do braço — bancada", "5 min",
      "03_braco_motriz", "2 × PA 2,0 × 8 (item 1)",
      ["Com a chapa 03 na mesa, localize o rasgo do servo na ponta oposta ao bolso do horn.",
       "Encaixe S3 com o corpo para o lado de DENTRO (o mesmo lado em que ficará a outra chapa do braço) e a aba "
       "apoiada na face externa da chapa.",
       "Aperte os 2 parafusos PA 2,0 × 8."],
      "Montar S3 agora, com a chapa solta na bancada, evita ter que trabalhar dentro do vão de 37,6 mm da "
      "forquilha depois. O empilhamento em Y do projeto é fixo: parede motriz em 4..8 mm, chapas do braço em "
      "±18,8..22,8 mm, chapas do antebraço em ±33,6..37,6 mm.",
      "A aba do servo deve estar encostada na chapa, sem folga. O eixo de S3 aponta para o mesmo lado que o "
      "bolso do horn de S2 na outra ponta da chapa.")

passo(5, "Braço (chapa motriz) no horn de S2", "10 min",
      "03_braco_motriz + S3", "4 × micro PA 1,7 × 6 (item 2) + 1 × PA 2,0 × 6 com arruela (item 1b)",
      ["Parafuse o horn DUPLO no bolso da chapa 03 com 4 micro parafusos (2 em cada braço do horn).",
       "Com S2 energizado em 90°, empurre o conjunto no eixo de S2 de modo que o braço fique na VERTICAL, "
       "apontando para cima (Figura 1).",
       "Coloque o parafuso central com a arruela e aperte.",
       "Balance o braço de leve: ele deve acompanhar o servo sem folga angular perceptível."],
      "Este é o ponto onde um dente de indexação errado se nota mais: 8,6° de erro no ombro deslocam a garra "
      "cerca de 25 mm no fim do braço. Se o braço não ficar vertical com o servo em 90°, tire e reencaixe.",
      "Braço na vertical com S2 em 90°; sem folga entre o horn e o bolso; o parafuso central apertado.",
      [("ATENÇÃO", "Neste momento o braço está preso por UM lado só. Não solte o conjunto e não pendure peso "
                    "até fechar a forquilha na etapa 6.")])

passo(6, "Fechar a forquilha do braço (chapa livre + travessa)", "10 min",
      "04_braco_livre", "2 × M3 × 10 (item 3b)",
      ["Aproxime a chapa 04 do lado oposto, com o munhão Ø9 apontando para o furo Ø9,4 da parede LIVRE da plataforma.",
       "Encaixe primeiro o munhão no mancal (entra com a força dos dedos).",
       "Gire a chapa até que a travessa em L encoste na chapa motriz 03, alinhando os 2 furos.",
       "Aperte os 2 parafusos M3 × 10 através da chapa 03 (furo passante Ø3,4) para dentro dos furos-piloto "
       "Ø2,5 da travessa. Vá alternando entre os dois, meia volta de cada vez.",
       "Mova o ombro com a mão (servo desligado): as duas chapas têm que subir e descer juntas, como uma peça só."],
      "É a travessa que transforma duas chapas soltas numa forquilha. Sem ela, as chapas abrem sob carga e o "
      "munhão escapa do mancal. Com ela, cada junta trabalha em cisalhamento duplo e o esforço lateral no "
      "estriado de nylon do horn praticamente desaparece.",
      "Sem os 2 parafusos M3 × 10 o conjunto abre com a mão; com eles, não deve haver nenhum movimento relativo "
      "entre as chapas. O ombro continua girando livre.",
      [("NUNCA", "Deixar de instalar os M3 × 10 'porque está justo'. Eles são o fecho estrutural do elo.")])

passo(7, "Antebraço (chapa motriz) no horn de S3", "10 min",
      "05_antebraco_motriz", "4 × micro PA 1,7 × 6 (item 2) + 1 × PA 2,0 × 6 com arruela (item 1b)",
      ["Parafuse o horn DUPLO no bolso da chapa 05 com 4 micro parafusos.",
       "Com S3 energizado em 90°, encaixe o conjunto no eixo de S3 com o antebraço na HORIZONTAL, apontando "
       "para a frente (Figura 1).",
       "Aperte o parafuso central com a arruela."],
      "Com S2 e S3 em 90° o braço fica vertical e o antebraço horizontal: é a pose de home, e é a partir dela "
      "que os limites de software (40° a 140° no cotovelo) fazem sentido.",
      "Antebraço horizontal com S3 em 90°. Dobrando o cotovelo com a mão (servo desligado), nada deve bater "
      "antes de ~148°, quando a palma encosta na parede da plataforma.")

passo(8, "Servo S4 na palma — bancada", "5 min",
      "06_antebraco_livre", "2 × PA 2,0 × 8 (item 1)",
      ["Apoie a peça 06 na mesa com a palma (a aba alta de 67 mm) para cima.",
       "Encaixe S4 no rasgo da palma pela face INTERNA, com o corpo saindo para FORA (para longe do braço) e o "
       "eixo estriado apontando para dentro.",
       "Aperte os 2 parafusos PA 2,0 × 8."],
      "Os eixos das engrenagens da garra ficam ao longo do antebraço: com o antebraço na horizontal, eles ficam "
      "verticais e as mandíbulas fecham num plano horizontal — a garra pega objetos apoiados na mesa pelo lado, "
      "em vez de ter que mergulhar por cima.",
      "O corpo de S4 deve ficar totalmente fora do vão da garra; o horn, do lado de dentro, a cerca de 11 mm "
      "da face da palma.")

passo(9, "Garra (dois dedos) — bancada", "15 min",
      "07 + 08 (mandíbula plana) ou 10 + 11 (mandíbula em V)",
      "2 × micro PA 1,7 × 6 (item 2) + 1 × M3 × 25 (item 3) + 1 porca nylock (item 4) + 2 arruelas (item 5)",
      ["Parafuse o horn SIMPLES no bolso do DEDO MOTRIZ (peça 07 ou 10) com 2 micro parafusos.",
       "Mande 's 3 75' pelo Serial para levar S4 a 75° (quase fechado) e encaixe o dedo motriz no eixo, com a "
       "mandíbula apontando para a frente do antebraço. Aperte o parafuso central.",
       "Monte o dedo livre: arruela de nylon entre o ressalto Ø9 e a palma, parafuso M3 × 25 passando pela palma "
       "e pelo dedo, segunda arruela e porca nylock do outro lado.",
       "Antes de apertar a porca, engrene os dentes de modo que as duas mandíbulas fiquem simétricas (a mesma "
       "distância do centro). Se ficarem tortas, levante o dedo livre e gire UM dente (11,25°).",
       "Aperte a nylock só até a folga sumir — o dedo livre tem que girar solto. Não é um parafuso de fixação, "
       "é um eixo."],
      "As engrenagens são de 16 dentes, módulo 1,5, com o dente afinado 0,5° por flanco e addendum encurtado: "
      "a interpenetração medida é zero em 361 posições, com 0,19 mm de folga de flanco (≈1,6° de backlash). "
      "O dedo livre já sai do CAD com meia fase de dente (11,25°) para que as mandíbulas fechem paralelas.",
      "Girando o dedo motriz com a mão, o livre acompanha sem ranger e sem travar. As mandíbulas devem se "
      "encostar (sem esmagar) por volta de 72,5° no servo e abrir até ≈57 mm a 110°.",
      [("ATENÇÃO", "Se apertar a nylock até o fim, a engrenagem prende e S4 trava — o servo esquenta e pode "
                    "queimar. A porca autotravante existe justamente para poder ficar frouxa sem soltar."),
       ("DICA", "Quem imprimir as duas opções de dedo (plana 07/08 e em V 10/11) pode deixar um horn montado em "
                 "cada dedo motriz: a troca passa a ser só o parafuso central e o pino M3.")])
figura(IMG("garras.png"), "Figura 3 — As duas opções de dedo: mandíbula plana (07/08) e mandíbula em V, "
                          "auto-centrante (10/11). Mesmo eixo, mesmo pino, mesma distância entre centros.", 14.5)

passo(10, "Fechar a forquilha do antebraço", "10 min",
      "06_antebraco_livre (com S4 e a garra)", "2 × M3 × 10 (item 3b)",
      ["Leve o conjunto 06 até o braço e encaixe o munhão do antebraço no mancal Ø9,4 da chapa livre do braço (04).",
       "Gire até que a palma encoste na chapa motriz do antebraço (05) e os 2 furos se alinhem.",
       "Aperte os 2 parafusos M3 × 10 pela chapa 05 para dentro dos furos-piloto da palma, alternando.",
       "Passe os cabos de S3 e S4 por dentro das janelas das chapas, folgados o suficiente para o cotovelo "
       "percorrer toda a faixa sem esticar."],
      "A palma faz o mesmo papel da travessa do braço: fecha a forquilha e ainda serve de base para o servo da "
      "garra e para o pino do dedo livre. O vão interno do antebraço é de 67,2 mm.",
      "Dobre o cotovelo devagar por toda a faixa (servo desligado) enquanto olha os cabos: nada pode ficar "
      "tracionado nem entrar na engrenagem da garra.",
      [("ATENÇÃO", "Cabo preso é a falha mais comum depois da montagem: ele não quebra na hora, mas a cada ciclo "
                    "puxa o conector até soltar um fio.")])

passo(11, "Fixar a base na tábua", "10 min",
      "01_base_fixa + tábua ou MDF ≈ 200 × 200 mm", "4 × M3 × 16 + porcas (item 9)",
      ["Marque na tábua os 4 furos do disco (raio 47 mm, a 45°, 135°, 225° e 315°).",
       "Fure a tábua com broca de 3,2 mm (para M3 com porca) ou 2,5 mm (para parafuso de madeira).",
       "Aparafuse o disco na tábua, sem apertar a ponto de deformar o PLA.",
       "Deixe o canal do cabo livre: os cabos de S1 e S2 passam por baixo do disco."],
      "Com o braço estendido, o centro de massa sai do raio de apoio do disco Ø110: bastam ≈15 g na garra para "
      "tombar o conjunto. A tábua aumenta o raio de apoio e é o que torna os testes de carga seguros.",
      "Segure a tábua e estenda o braço à frente: o conjunto não pode balançar nem levantar do apoio.")

passo(12, "Controle: os dois joysticks no suporte", "15 min",
      "09_suporte_joysticks + 2 × KY-023", "8 × M3 × 12 (item 6) + 8 porcas (item 7) + 8 arruelas amplas (item 8)",
      ["Apoie cada módulo KY-023 no berço: os 4 cantos em L posicionam a placa pela borda (envelope 34,6 × 26,6 mm).",
       "Alinhe os furos da placa com os rasgos radiais do suporte — eles aceitam furação de 21,5 a 34,5 mm por "
       "15,4 a 24,6 mm, que cobre os clones de KY-023 do mercado.",
       "Coloque um parafuso M3 × 12 com arruela ampla Ø9 por cima, e porca por baixo. Aperte pouco: a placa é fina.",
       "Se o gimbal do seu módulo cobrir os furos de um dos lados, use só 2 parafusos na diagonal — os cantos "
       "em L já impedem a placa de escorregar."],
      "Nenhum datasheet do KY-023 publica a distância entre os furos (Joy-IT, Mantech, espboards e arduinomodules "
      "só informam a placa de 34 × 26 mm), e em vários clones o gimbal cobre os furos do lado estreito. Por isso "
      "o berço não depende dessa cota: quem posiciona são os cantos, e os rasgos radiais aceitam a furação que vier.",
      "Os dois módulos firmes no berço, com os cabos saindo para o mesmo lado, e as alavancas livres para ir ao "
      "fim de curso nas quatro direções.")
figura(IMG("suporte_joysticks.png"), "Figura 4 — Suporte dos joysticks: cantos em L e rasgos radiais.", 13.5)

figura(IMG("montagem_vistas.png"), "Figura 5 — Vistas do conjunto montado, para conferência final da mecânica.", 15.0)
doc.add_page_break()

# ================================================================== 4 ELÉTRICA
H("4. Montagem elétrica", 1)
P("O guia furo a furo da protoboard está no arquivo Circuito_Braco_Robotico.html (abra no navegador): ele mostra "
  "em qual furo entra cada perna. O que segue é o resumo e a ordem segura de energizar.", al="j")

H("4.1 Pinagem", 2)
tabela(["Sinal", "Pino do Arduino", "Observação"], [
    ["Servo S1 — base", "D3", "Fio laranja/amarelo (sinal)"],
    ["Servo S2 — ombro", "D5", ""],
    ["Servo S3 — cotovelo", "D6", "Precisa de extensor de 300 mm"],
    ["Servo S4 — garra", "D9", "Precisa de extensor de 300 mm"],
    ["Joystick 1 — VRx (base)", "A0", "J1 = mão esquerda"],
    ["Joystick 1 — VRy (ombro)", "A1", ""],
    ["Joystick 1 — SW", "D2", "Entrada com pull-up interno"],
    ["Joystick 2 — VRx (garra)", "A2", "J2 = mão direita"],
    ["Joystick 2 — VRy (cotovelo)", "A3", ""],
    ["Joystick 2 — SW", "D4", ""],
    ["LED de estado", "D13", "LED da própria placa"],
    ["+5 V dos servos", "Fonte externa", "NÃO sai do Arduino"],
    ["+5 V dos joysticks", "5V do Arduino", "Consumo desprezível"],
    ["GND", "Comum", "Fonte e Arduino obrigatoriamente no mesmo GND"],
], [5.2, 4.0, 6.8])

H("4.2 Ordem de montagem do circuito", 2)
N(["Monte a protoboard SEM os servos e SEM o Arduino: fonte na trilha + / −, capacitor de 1000 µF entre + e − "
   "(respeitando a polaridade, a perna marcada é o negativo), e os 4 trios de furos que receberão os servos.",
   "Ligue a fonte e meça com o multímetro: tem que haver 5,0 V entre a trilha + e a trilha −, e 0 V em qualquer "
   "outro lugar. Desligue.",
   "Ligue o GND do Arduino à trilha − (esse é o GND comum). Sem isso, o sinal dos servos não tem referência e "
   "eles tremem sem parar.",
   "Encaixe os servos: marrom/preto no −, vermelho no +, laranja/amarelo no pino de sinal correspondente.",
   "Ligue os joysticks: +5V no 5V do Arduino, GND na trilha −, e os eixos nas entradas analógicas.",
   "Solde (ou encaixe) um capacitor cerâmico de 100 nF entre + e − de cada servo, o mais perto possível do conector."])
caixa("ATENÇÃO", "Um contato de protoboard aguenta cerca de 1 A e o barramento chega a 1,85 A na reprodução com "
                  "carga. Alimente a trilha + por DOIS furos afastados (ou use borne parafusado) e espalhe os "
                  "servos pela trilha, em vez de enfileirá-los em furos vizinhos.")
caixa("ATENÇÃO", "O orçamento de queda de tensão é de 200 mV (5,0 V na fonte, 4,8 V no servo). Meio metro de fio "
                  "22 AWG com 2 A já gasta 106 mV: use 20 AWG ou mais grosso entre a fonte e a protoboard.")
figura(IMG("esquema_eletrico.png"), "Figura 6 — Esquema elétrico completo.", 15.5)

H("4.3 Primeira energização (nesta ordem)", 2)
N(["Arduino desconectado do USB, fonte desligada. Confira visualmente a polaridade de todos os conectores de servo.",
   "Ligue só a fonte. Meça 5 V na trilha. Nenhum servo deve se mexer (não há sinal ainda).",
   "Conecte o USB do Arduino (já com o firmware gravado). Os quatro servos vão para 90° — esse é o teste de que "
   "a alimentação e o sinal estão certos.",
   "Meça a tensão na trilha + com os servos se movendo: não pode cair abaixo de 4,8 V.",
   "Abra o Monitor Serial a 115200 bauds. Deve aparecer o cabeçalho do firmware com a lista de comandos."])
caixa("CONFERIR", "Consumo esperado: ≈0,47 A parado, 0,72 a 1,21 A movendo um ou dois eixos, 1,85 A no pior caso "
                   "normal (reprodução com 4 eixos e 50 g na garra). Se a fonte esquentar muito ou a tensão cair "
                   "abaixo de 4,8 V, pare e revise a fiação antes de continuar.")
doc.add_page_break()

# ================================================================== 5 FIRMWARE
H("5. Firmware", 1)
N(["Abra firmware/braco_robotico/braco_robotico.ino na Arduino IDE.",
   "Ferramentas → Placa: Arduino UNO. Ferramentas → Porta: a porta COM do seu Arduino.",
   "A biblioteca Servo já vem com a IDE; não é preciso instalar nada.",
   "Carregue (Ctrl+U). O sketch ocupa 36 % da flash e 22 % da RAM.",
   "Abra o Monitor Serial em 115200 bauds."])
P("Comandos do Monitor Serial:", b=True, sz=10.5)
tabela(["Comando", "O que faz"], [
    ["p", "Imprime as posições atuais das 4 juntas"],
    ["s <junta> <ângulo>", "Move uma junta para um ângulo (junta 0=base, 1=ombro, 2=cotovelo, 3=garra)"],
    ["h", "Vai para a posição de home (90° em todas)"],
    ["a", "Alterna a garra entre aberta e fechada"],
    ["g", "Grava a pose atual (máximo de 16)"],
    ["r", "Inicia ou para a reprodução das poses gravadas"],
    ["l", "Apaga todas as poses"],
    ["m", "Volta ao modo manual (joysticks)"],
    ["j", "Recalibra o centro dos joysticks (não toque nas alavancas)"],
    ["e", "Salva as poses na EEPROM"],
    ["c", "Carrega as poses da EEPROM"],
    ["v<1 a 10>", "Ajusta a velocidade máxima em graus por passo de 20 ms (padrão 3 = 150 °/s)"],
], [4.2, 11.8])
P("Controles no joystick:", b=True, sz=10.5)
tabela(["Ação", "Resultado"], [
    ["Joystick 1 — eixo X", "Gira a base (junta 0)"],
    ["Joystick 1 — eixo Y", "Levanta/abaixa o ombro (junta 1)"],
    ["Joystick 2 — eixo Y", "Dobra/estica o cotovelo (junta 2)"],
    ["Joystick 2 — eixo X", "Abre/fecha a garra (junta 3)"],
    ["Botão 1 (toque curto)", "Grava a pose atual"],
    ["Botão 1 (toque longo, 0,8 s)", "Inicia ou para a reprodução; LED pisca enquanto reproduz"],
    ["Botão 2 (toque curto)", "Abre/fecha a garra de uma vez"],
    ["Botão 2 (toque longo, 0,8 s)", "Volta para home"],
], [6.0, 10.0])
P("O joystick funciona como VELOCIDADE, não como posição: a junta se move enquanto a alavanca estiver fora do "
  "centro, e para onde estiver quando você soltar. A zona morta é de ±60 counts (≈6 %) e a velocidade cresce com "
  "o quadrado do deslocamento, o que dá controle fino perto do centro e movimento rápido no fim de curso.", al="j")
doc.add_page_break()

# ================================================================== 6 CALIBRAÇÃO
H("6. Calibração (obrigatória antes de usar)", 1)
P("Os limites que saem de fábrica no firmware são simétricos e conservadores porque o sentido de giro de cada "
  "servo só é conhecido depois de montado, e o encaixe estriado tem erro de indexação de até ±8,6°. Calibrar é "
  "medir, no SEU braço, até onde cada junta pode ir sem bater.", al="j")
tabela(["Junta", "Limites de fábrica", "Limite físico medido no modelo"], [
    ["0 — base", "5° a 175°", "Sem colisão em toda a faixa"],
    ["1 — ombro", "15° a 165°", "Acima de 135° com o cotovelo dobrado, o antebraço desce abaixo do plano da mesa"],
    ["2 — cotovelo", "40° a 140°", "A palma encosta na plataforma a 148°; o braço só a 160°"],
    ["3 — garra", "72° a 110°", "Mandíbulas se tocam em ≈72,5°; abertura máxima em 110°"],
], [2.6, 4.4, 9.0])

H("6.1 Centro dos joysticks", 2)
N(["Solte as alavancas e não encoste nelas.",
   "Mande o comando 'j'. O firmware lê 16 amostras de cada eixo e adota a média como centro.",
   "Confirme com 'p' e mexendo de leve: nenhuma junta pode andar sozinha com a alavanca solta."])

H("6.2 Sentido de cada eixo", 2)
N(["Empurre cada alavanca para um lado e veja se a junta vai para o lado esperado.",
   "Se algum eixo estiver invertido, troque o sinal correspondente no vetor SENTIDO[] do firmware "
   "(1 vira −1) e recarregue. A ordem do vetor é base, ombro, cotovelo, garra."])

H("6.3 ANG_MIN e ANG_MAX de bancada", 2)
caixa("ATENÇÃO", "Faça esta etapa com o braço preso na tábua, uma junta de cada vez, com a mão perto do cabo da "
                  "fonte para desligar se algo encostar.")
N(["Leve tudo para home com 'h'.",
   "Escolha uma junta e vá aumentando o ângulo de 5 em 5 graus com 's <junta> <ângulo>', olhando o ponto de "
   "colisão mais próximo.",
   "Quando faltarem uns 5° para encostar, pare e anote o valor: esse é o seu ANG_MAX daquela junta.",
   "Repita no sentido contrário para achar ANG_MIN.",
   "Passe os quatro pares para os vetores ANG_MIN[] e ANG_MAX[] no firmware e recarregue.",
   "Repita o teste depois de recarregar: agora o firmware recusa qualquer comando fora da faixa."])
caixa("DICA", "Depois de calibrado, o lado esticado do cotovelo costuma chegar a 20° e o dobrado nunca passa de "
               "145°. Se quiser eliminar de vez a pose em que o antebraço desce abaixo da mesa, limite o ombro a "
               "135° — o custo é cerca de 50 mm de alcance.")

H("6.4 Garra", 2)
N(["Com 's 3 <ângulo>', feche a garra de 1 em 1 grau até as mandíbulas se encostarem SEM forçar (o servo não "
   "pode zumbir). Esse valor é o GARRA_FECHADA (referência: 74°).",
   "Abra até a posição máxima útil e anote: é o GARRA_ABERTA (referência: 110°).",
   "Atualize as duas constantes no firmware e recarregue."])
caixa("NUNCA", "Deixar a garra fechada contra um objeto rígido por muito tempo. Servo travado puxa ≈0,7 A, "
                "esquenta e é a forma mais rápida de queimar um MG90S.")

H("6.5 Gravar e reproduzir uma sequência", 2)
N(["No modo manual, leve o braço até a primeira pose com os joysticks.",
   "Toque curto no botão 1 (ou comando 'g') para gravar. Repita até 16 poses.",
   "Toque longo no botão 1 (ou 'r') para reproduzir em laço. O LED pisca enquanto reproduz.",
   "Mande 'e' para salvar na EEPROM — assim a sequência sobrevive a desligar a alimentação.",
   "Se mudar ANG_MIN/ANG_MAX depois de gravar, não há problema: a reprodução limita cada pose aos limites "
   "atuais antes de enviá-la aos servos."])
doc.add_page_break()

# ================================================================== 7 TESTES
H("7. Testes de aceitação", 1)
P("Preencha esta tabela na entrega — ela é a evidência de que o protótipo funciona.", al="j")
tabela(["#", "Teste", "Critério", "OK?"], [
    ["1", "Home ao ligar", "Os 4 servos vão para 90° e o braço fica como a Figura 1", "☐"],
    ["2", "Faixa de cada junta", "Cada junta percorre ANG_MIN..ANG_MAX sem encostar em nada", "☐"],
    ["3", "Alcance horizontal", "≈186 mm do centro da base com o braço estendido", "☐"],
    ["4", "Altura máxima", "≈249 mm", "☐"],
    ["5", "Garra — objeto prismático", "Segura uma borracha ou caixinha sem escorregar", "☐"],
    ["6", "Garra — objeto cilíndrico", "Segura uma caneta em pé (use os dedos em V se escorregar)", "☐"],
    ["7", "Carga útil", "Levanta ≈20 g com o braço estendido sem o ombro ceder", "☐"],
    ["8", "Gravar e reproduzir", "4 poses gravadas reproduzem em laço sem travar", "☐"],
    ["9", "Persistência", "Depois de desligar e religar, 'c' recupera as poses", "☐"],
    ["10", "Tensão sob carga", "A trilha de 5 V não cai abaixo de 4,8 V na reprodução", "☐"],
    ["11", "Estabilidade", "Com a tábua fixada, o conjunto não tomba em nenhuma pose", "☐"],
    ["12", "Temperatura", "Depois de 5 min de reprodução, nenhum servo está quente ao toque", "☐"],
], [0.8, 6.0, 7.4, 1.2])
figura(IMG("montagem_captura.png"), "Figura 7 — Pose de captura: a garra fecha num plano horizontal, pegando o "
                                    "objeto pelo lado.", 13.5)
doc.add_page_break()

# ================================================================== 8 PROBLEMAS
H("8. Solução de problemas", 1)
tabela(["Sintoma", "Causa provável", "O que fazer"], [
    ["Todos os servos tremem sem parar",
     "GND da fonte não está ligado ao GND do Arduino",
     "Ligar o GND comum. É a falha número um."],
    ["Um servo treme sozinho, parado",
     "Ruído no sinal ou queda de tensão momentânea",
     "Capacitor de 100 nF junto ao servo; encurtar o cabo de sinal; conferir 4,8 V mínimos."],
    ["O braço cai quando desligo",
     "Comportamento normal: sem energia não há torque",
     "Guardar o braço recolhido; apoiar antes de desligar."],
    ["Uma junta anda sozinha com o joystick solto",
     "Centro do joystick desatualizado",
     "Comando 'j' com as alavancas soltas."],
    ["A junta vai para o lado errado",
     "Sentido do servo invertido na montagem",
     "Trocar 1 por −1 na posição correspondente de SENTIDO[]."],
    ["O elo ficou torto com o servo em 90°",
     "Horn encaixado um dente fora (17,1° por dente)",
     "Soltar o parafuso central, puxar o horn e reencaixar um dente para o lado."],
    ["A garra não fecha de todo / esmaga",
     "GARRA_FECHADA fora do ponto de toque real",
     "Refazer a seção 6.4 de 1 em 1 grau."],
    ["Um dedo da garra pula dente",
     "Porca nylock frouxa demais ou dente com rebarba",
     "Apertar a nylock até tirar a folga axial (sem prender) e limpar o dente com estilete."],
    ["A garra trava e o servo zumbe",
     "Nylock apertada demais, prendendo a engrenagem",
     "Afrouxar até o dedo livre girar solto. Desligar imediatamente enquanto ajusta."],
    ["As chapas do elo abrem sob carga",
     "Faltam os parafusos M3 × 10 da travessa/palma",
     "Instalar os 4 parafusos do item 3b."],
    ["O munhão sai do mancal",
     "Forquilha aberta (mesma causa acima) ou mancal alargado",
     "Fechar a forquilha; se o furo foi alargado, reimprimir a peça."],
    ["Micro parafuso gira sem prender",
     "Furo-piloto Ø1,5 alargado demais ou rosca espanada no PLA",
     "Usar o furo vizinho do horn (a grade tem 2 ou 3 furos por braço)."],
    ["A reprodução congela numa pose",
     "Pose gravada fora dos limites atuais",
     "Já tratado no firmware (a pose é limitada); se persistir, apagar com 'l' e regravar."],
    ["O Arduino reinicia sozinho",
     "Fonte ligada no pino 5V junto com o USB, ou queda de tensão",
     "Usar uma alimentação só; reforçar o fio da fonte para 20 AWG."],
    ["A base tomba",
     "Braço sem a tábua de fixação",
     "Etapa 11 — não é opcional."],
    ["Furos ficaram todos apertados",
     "Compensação de furo da impressora",
     "Ativar 'X-Y hole compensation' de 0,1 mm no fatiador e reimprimir."],
], [4.6, 5.2, 6.2], fs=8.5)

H("9. Manutenção", 1)
B(["Reaperte os 4 parafusos M3 × 10 e os parafusos centrais dos horns depois da primeira hora de uso: o PLA "
   "acomoda e aparece folga.",
   "Guarde o braço na pose de home ou recolhido — deixar o braço estendido por dias com o servo desligado "
   "deforma nada, mas facilita esbarrões.",
   "Se aparecer folga angular numa junta, o suspeito é o bolso do horn (desgaste do encaixe de forma) — é a "
   "peça que se reimprime, não o servo.",
   "Não lubrifique as engrenagens impressas: graxa atrai pó de PLA e vira pasta abrasiva.",
   "Antes de qualquer alteração de cota, lembre que as peças vêm de cad/gerar_pecas.py — altere lá e regere, "
   "nunca edite o STL."])

P()
P("Fim do manual. Em caso de dúvida sobre uma cota, o desenho vale mais que o texto: cad/gerar_pecas.py é a "
  "fonte de todas as dimensões citadas aqui.", i=True, sz=9.5)

doc.save(SAIDA)
print("Manual gerado em", SAIDA)
