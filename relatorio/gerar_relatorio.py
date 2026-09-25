# -*- coding: utf-8 -*-
"""gerar_relatorio.py — monta o relatório do projeto (relatorio/Relatorio_Braco_Robotico.docx) com python-docx.
Depende de: cad/pecas_info.json, imagens/*.png, firmware/braco_robotico/braco_robotico.ino."""
import os, json, sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "relatorio"))
from parafusos import FIXADORES, NOTAS, custo_total
IMG = lambda n: os.path.join(RAIZ, "imagens", n)
SAIDA = os.path.join(RAIZ, "relatorio", "Relatorio_Braco_Robotico.docx")
info = json.load(open(os.path.join(RAIZ, "cad", "pecas_info.json"), encoding="utf-8"))
codigo = open(os.path.join(RAIZ, "firmware", "braco_robotico", "braco_robotico.ino"), encoding="utf-8").read()

doc = Document()
for s in doc.sections:
    s.top_margin = s.bottom_margin = Cm(2.5); s.left_margin = Cm(3); s.right_margin = Cm(2)
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
for n, sz in [("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)]:
    doc.styles[n].font.size = Pt(sz); doc.styles[n].font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)

# ---------- utilidades
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
        cells = t.add_row().cells
        for c, v in zip(cells, ln):
            c.text = ""; r = c.paragraphs[0].add_run(str(v)); r.font.size = Pt(fs)
    if larguras:
        for row in t.rows:
            for c, w in zip(row.cells, larguras): c.width = Cm(w)
    doc.add_paragraph()
    return t
def figura(arq, legenda, larg=15.5):
    if os.path.exists(arq):
        doc.add_picture(arq, width=Cm(larg)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    P(legenda, i=True, al="c", sz=9)
def campo(p, instr):
    r = p.add_run(); f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "(pressione F9 para atualizar)"
    f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
    for e in (f1, it, f2, t, f3): r._r.append(e)
def codigo_bloco(txt):
    for linha in txt.splitlines():
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
        r = p.add_run(linha if linha else " "); r.font.name = "Consolas"; r.font.size = Pt(7.5)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")

# rodapé com número de página
fp = doc.sections[0].footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp.add_run("Braço Robótico 4 GDL — Sistemas Embarcados — FAESA        Página "); campo(fp, "PAGE")

# ================================================================== CAPA
for _ in range(4): P()
P("FAESA — CENTRO UNIVERSITÁRIO", b=True, al="c", sz=14)
P("Curso de Engenharia da Computação", al="c", sz=12)
P("Disciplina: Sistemas Embarcados — 2026/2", al="c", sz=12)
for _ in range(4): P()
P("BRAÇO ROBÓTICO DE 4 GRAUS DE LIBERDADE", b=True, al="c", sz=22)
P("Projeto, modelagem 3D, impressão (Bambu Lab A1) e firmware em Arduino", al="c", sz=13)
for _ in range(6): P()
P("Aluno(a): ______________________________________", al="c", sz=12)
P("Professor(a): ___________________________________", al="c", sz=12)
for _ in range(3): P()
P("Vitória – ES", al="c", sz=12); P("Setembro de 2026", al="c", sz=12)
doc.add_page_break()

# ================================================================== SUMÁRIO
H("Sumário", 1); p = doc.add_paragraph(); campo(p, 'TOC \\o "1-2" \\h \\z \\u')
doc.add_page_break()

# ================================================================== 1
H("1. Objetivo", 1)
P("Construir um braço robótico de 4 graus de liberdade (GDL) utilizando a plataforma de prototipação Arduino, "
  "cobrindo todo o ciclo de um sistema embarcado: especificação, projeto mecânico (peças modeladas em 3D e impressas "
  "na Bambu Lab A1), projeto eletrônico, firmware em Arduino IDE e testes.", al="j")
P("Entregas exigidas pela disciplina:", b=True)
N(["Lista de componentes necessários (seção 4).",
   "Modelo 3D de cada peça em arquivos separados, com os arquivos STL individuais para impressão (seções 5 e 6).",
   "Desenho do protótipo montado (seção 7).",
   "Código-fonte executado no Arduino IDE (seção 9 e Apêndice A)."])
P("Requisitos de fabricação: impressora Bambu Lab A1, altura de camada 0,2 mm e densidade de preenchimento 15 %.", al="j")

# ================================================================== 2
H("2. Visão geral da solução", 1)
P("O braço é do tipo articulado (antropomórfico) com quatro juntas acionadas por micro-servos SG90/MG90S: "
  "rotação da base (S1), ombro (S2), cotovelo (S3) e garra (S4). As juntas usam o próprio horn (braço) do servo "
  "encaixado em um bolso da peça — solução simples, barata e comum em braços didáticos.", al="j")
P("Cada elo é uma FORQUILHA: duas chapas de 4 mm, uma de cada lado do plano de rotação da base, ligadas por uma "
  "travessa aparafusada. O servo da junta fica entre as duas chapas, com o flange na chapa motriz; do lado oposto, um "
  "munhão Ø9 impresso na própria chapa gira em um mancal Ø9,4. Com isso a carga é dividida entre dois apoios "
  "(cisalhamento duplo) em vez de pendurar em balanço no eixo do servo, e o centro de massa fica sobre o eixo da base — "
  "o conjunto é simétrico e equilibrado, sem o esforço lateral que a versão anterior, em chapa única, impunha ao "
  "estriado de nylon do horn.", al="j")
P("A garra é de duas engrenagens espelhadas (16 dentes, módulo 1,5): uma acionada pelo servo e a outra girando livre "
  "em um pino M3, o que produz abertura simétrica dos dedos. Ela é montada sob a PALMA — uma chapa transversal na "
  "ponta do antebraço, que também é a travessa dessa forquilha —, com os eixos das engrenagens ao longo do eixo X do "
  "antebraço. Com o antebraço na horizontal esses eixos ficam VERTICAIS e as mandíbulas fecham num plano horizontal: "
  "o braço se aproxima de lado e agarra pelas laterais um objeto apoiado na mesa (captura na horizontal), em vez de "
  "descer sobre ele com o antebraço apontando para baixo.", al="j")
figura(IMG("montagem_isometrica.png"), "Figura 1 — Protótipo montado (modelo 3D gerado a partir das peças).")
tabela(["Item", "Especificação"], [
    ["Graus de liberdade", "4 (base, ombro, cotovelo, garra)"],
    ["Atuadores", "4 × micro-servo SG90 (plástico) ou MG90S (metálico, recomendado para ombro e cotovelo)"],
    ["Controlador", "Arduino UNO R3 (ATmega328P, 16 MHz)"],
    ["Interface de comando", "2 módulos joystick analógico KY-023 (4 eixos + 2 botões: gravar/reproduzir poses, abrir/fechar garra, home) + terminal serial"],
    ["Estrutura dos elos", "Forquilha simétrica: 2 chapas de 4 mm por elo (motriz + livre), vão de 37,6 mm no braço e 67,2 mm no antebraço; pivô livre em munhão Ø9 impresso"],
    ["Comprimento dos elos", "Braço 70 mm (ombro→cotovelo); antebraço 62 mm (cotovelo→eixo da garra); dedos 55 mm"],
    ["Plano de fechamento da garra", "Horizontal — engrenagens com eixo vertical quando o antebraço está na horizontal; as mandíbulas ficam 2,8 mm abaixo do eixo do antebraço e 39 mm à frente da ponta das chapas"],
    ["Alcance horizontal máx.", "≈ 186 mm a partir do eixo da base (ombro em 165°, cotovelo quase esticado); altura do ombro 68,8 mm; altura máxima da ponta dos dedos ≈ 249 mm"],
    ["Opções de garra", "Duas ferramentas intercambiáveis: A (mandíbula plana, objetos prismáticos) e B (mandíbula em V, auto-centrante para cilindros e esferas em pé) — ver seção 5.6"],
    ["Abertura da garra", "0 mm (mandíbulas encostadas, S4 ≈ 72,5°) a ≈ 57 mm na raiz / 71 mm nas pontas (S4 = 110°)"],
    ["Carga útil estimada", "≈ 20 g com o braço estendido (186 mm) e ≈ 65 g com o braço recolhido (vertical), mantendo o ombro em ≤ 50 % do torque de travamento (1,8 kgf·cm a 5 V); ≈ 30 g aceitando 60 %"],
    ["Alimentação", "Fonte 5 V / 3 A para os servos; Arduino pelo USB OU pela mesma fonte (nunca os dois ao mesmo tempo); GND comum"],
    ["Material / massa impressa", f"PLA, ≈ {sum(p['massa_estimada_g'] for p in info):.0f} g no total ({len(info)} peças, incluindo o controle de mão dos joysticks)"],
], [5, 11])
H("2.1 Envelope de trabalho", 2)
P("Alturas e alcances medidos no modelo 3D montado (referência: mesa de apoio da base, eixo Z; alcance medido a partir "
  "do eixo de rotação da base). A altura máxima ocorre com o braço totalmente esticado para cima — ombro a 90° e "
  "cotovelo a 180°, dentro dos limites ANG_MIN/ANG_MAX do firmware.", al="j")
tabela(["Referência (braço esticado para cima)", "Altura (mm)"], [
    ["Topo da torre da base (apoio do servo S1)", "30,0"],
    ["Eixo do ombro (S2)", "68,8"],
    ["Eixo do cotovelo (S3), braço vertical", "138,8"],
    ["Eixo da garra (S4), antebraço vertical (referência geométrica)", "200,8"],
    ["Ponta dos dedos — altura máxima medida no modelo (cotovelo em 20°)", "249,1"],
], [10, 4])
tabela(["Pose", "Ângulos (ombro / cotovelo)", "Altura máx. (mm)", "Alcance horizontal (mm)"], [
    ["Esticado para cima (altura máxima)", "90° / 20° (limite ANG_MIN do cotovelo)", "249", "53"],
    ["Repouso — home", "90° / 90°", "165", "119"],
    ["Alcance horizontal máximo", "165° (limite ANG_MAX do ombro) / 20°", "108", "186"],
], [5.5, 4, 3, 3.5])
P("Valores medidos diretamente no modelo 3D (cad/verificacao.py). Como a estrutura agora é simétrica, o centro da garra "
  "fica no PLANO do braço — não há mais o deslocamento lateral de ≈ 34 mm da versão em chapa única, e o alcance vale "
  "igualmente para os dois lados.", al="j")
P("Limite de operação (não é limite de software): com o ombro além de ≈ 135° e o cotovelo dobrado além de ≈ 140°, o "
  "antebraço desce abaixo do plano da mesa e chega a tocar o disco da base (interferência medida: 0,1 a 1,5 cm³ nas poses "
  "extremas; com o ombro em 165° a garra chega a ≈ 28 mm abaixo da mesa). Não há batente mecânico: ou o operador evita a "
  "combinação, ou se reduz ANG_MAX do ombro para 135° no firmware — o que custa ≈ 50 mm de alcance.", al="j")

# ================================================================== 3
H("3. Arquitetura do sistema embarcado", 1)
P("Do ponto de vista de sistemas embarcados, o projeto é um laço de controle em malha aberta a 50 Hz "
  "(mesmo período do sinal PWM dos servos, 20 ms). A cada ciclo o firmware lê os sensores (eixos e botões dos joysticks), "
  "decide o modo de operação (máquina de estados MANUAL / REPRODUZINDO) e atualiza os atuadores, limitando a "
  "velocidade de cada junta para obter movimentos suaves e reduzir picos de corrente. Como o joystick retorna ao centro "
  "por mola, o comando é incremental (controle de velocidade): a deflexão do eixo define a taxa de variação do ângulo da "
  "junta, com zona morta em torno do centro e curva quadrática para precisão em movimentos finos.", al="j")
B([("Entradas: ", "2 joysticks KY-023 — 4 eixos analógicos (A0–A3, ADC 10 bits) e 2 botões (D2, D4, pull-up interno); porta serial USB (115200 bps)."),
   ("Saídas: ", "4 sinais PWM de servo (D3, D5, D6, D9 — biblioteca Servo.h, pulsos de 500 a 2500 µs), LED de status (D13)."),
   ("Memória: ", "até 16 poses gravadas em RAM, com persistência opcional na EEPROM (assinatura de validação); centro de cada eixo do joystick calibrado na partida."),
   ("Segurança: ", "limites mínimo/máximo por junta em software (evitam colisão do antebraço com o braço), partida sequencial dos servos e posição de repouso na inicialização.")])

# ================================================================== 4
H("4. Lista de componentes (BOM)", 1)
P("Preços em reais são estimativas de mercado (2026) para orientar o orçamento; confirmar no momento da compra.", i=True)
bom = [
    ["1", "Arduino UNO R3 (ou compatível) + cabo USB A-B", "1", "80", "80", "Controlador"],
    ["2", "Micro-servo MG90S (engrenagem metálica, 180°)", "2", "28", "56", "Ombro (S2) e cotovelo (S3) — mesmo torque do SG90 a 5 V (1,8 kgf·cm), mas engrenagens metálicas e rolamento no eixo: resistem a travamentos e ao esforço lateral"],
    ["3", "Micro-servo SG90 (180°) com kit de horns e parafusos", "2", "15", "30", "Base (S1) e garra (S4)"],
    ["4", "Módulo joystick analógico KY-023 (2 eixos + botão)", "2", "9", "18", "Comando manual das 4 juntas (J1: base/ombro; J2: garra/cotovelo)"],
    ["5", "Cabo jumper fêmea-macho 20 cm (5 vias por joystick)", "10", "0,4", "4", "Ligação dos joysticks à protoboard"],
    ["6", "Fonte chaveada 5 V / 3 A com plug P4", "1", "35", "35", "Alimentação dos servos"],
    ["7", "Jack P4 fêmea com borne (adaptador)", "1", "6", "6", "Conexão da fonte na protoboard"],
    ["8", "Capacitor eletrolítico 1000 µF / 16 V", "1", "2", "2", "Desacoplamento do barramento dos servos"],
    ["9", "Protoboard 400 pontos", "1", "15", "15", "Montagem do circuito"],
    ["10", "Jumpers macho-macho e macho-fêmea (kit 40 + 40)", "1", "18", "18", "Ligações"],
    ["11", "Parafusos e fixadores — ver lista à parte (Apêndice C / Lista_Parafusos_Fixadores.docx)", "1", f"{custo_total()}", f"{custo_total()}", "PA 2,0×8, PA 1,7×6, M3×25 inox + nylock, M3×12 + porcas/arruelas, M3×16, espaçadores"],
    ["12", "Filamento PLA 1,75 mm (≈ 137 g usados, já com as duas opções de garra)", "1", "13", "13", "Custo proporcional do carretel (R$ 90 / kg)"],
    ["13", "Abraçadeiras de nylon 2,5 × 100 mm + fita dupla-face", "1", "6", "6", "Cabos nos elos e no suporte dos joysticks / fixação da base"],
    ["14", "Base de MDF ou acrílico 200 × 150 × 6 mm (OBRIGATÓRIA)", "1", "10", "10", "Fixação da base fixa (4 furos Ø3,4): o disco Ø110 solto tomba com ≈ 15 g na garra em extensão máxima"],
    ["15", "Cabo extensor de servo, 3 vias, 300 mm (padrão JR/Futaba)", "2", "4", "8", "S3 (cotovelo) e S4 (garra): o cabo de fábrica (≈ 250 mm) não chega ao circuito passando pelos elos"],
]
tabela(["#", "Componente", "Qtd", "Unit. (R$)", "Total (R$)", "Função / observação"], bom, [0.8, 6.0, 1.0, 1.6, 1.6, 5.0], 8.5)
P(f"Custo total estimado: R$ {sum(float(l[4]) for l in bom):.0f}.", b=True)
P("Os parafusos, porcas e arruelas estão dimensionados item a item (furo, empilhamento, modelo e material) na lista à parte do Apêndice C, "
  "também entregue como documento separado (relatorio/Lista_Parafusos_Fixadores.docx).", al="j")
P("Ferramentas: chave Phillips PH0/PH1, chave de boca 5,5 mm, alicate de corte, estilete (rebarbas), ferro de solda (opcional), paquímetro.", i=True)

# ================================================================== 5
H("5. Projeto mecânico e modelagem 3D", 1)
H("5.1 Método de modelagem", 2)
P("As peças foram projetadas de forma paramétrica por geometria construtiva de sólidos (CSG) — união e subtração de "
  "primitivas (caixas e cilindros), exatamente a lógica de trabalho do Tinkercad (sólidos e furos). O script "
  "cad/gerar_pecas.py contém todas as cotas e gera um STL por peça, já na orientação de impressão; a seção 6 descreve "
  "como reproduzir/importar cada peça no Tinkercad em um projeto separado.", al="j")
H("5.2 Peças", 2)
tabela(["Arquivo STL", "Peça", "Função", "Dimensões (mm)", "Massa est.", "Tempo est."],
       [[p["arquivo"], p["nome"], p["funcao"], " × ".join(str(d) for d in p["dimensoes_mm"]), f"{p['massa_estimada_g']} g", f"{p['tempo_estimado_min']} min"] for p in info],
       [3.6, 2.8, 5.2, 2.6, 1.4, 1.4], 8.5)
P(f"Total estimado: ≈ {sum(p['massa_estimada_g'] for p in info):.0f} g de PLA e ≈ {sum(p['tempo_estimado_min'] for p in info)/60:.1f} h de impressão "
  "(0,2 mm, 15 %). As peças cabem na mesa de 256 × 256 mm da A1 em uma ou duas chapas (o Bambu Studio arranja "
  "automaticamente; a base Ø110 e o suporte 160 × 100 não podem ficar lado a lado no mesmo eixo).", al="j")
figura(IMG("pecas_impressao.png"), "Figura 2 — As onze peças na orientação de impressão (como devem ficar na mesa): as travessas e a palma são impressas em pé sobre as chapas deitadas.")
H("5.3 Interfaces com o servo SG90/MG90S (cotas adotadas)", 2)
tabela(["Elemento", "Cota adotada", "Justificativa"], [
    ["Rasgo do corpo do servo", "23,2 × 12,6 mm (corpo 22,8 × 12,2)", "Folga de 0,2 mm por lado para FDM a 0,2 mm"],
    ["Furos do flange", "Ø1,7 mm, 27,5 mm entre centros", "Furo-piloto a 85 % do Ø2,0 do parafuso autoatarraxante do kit do servo"],
    ["Posição do eixo", "Deslocado 5,3 mm do centro do corpo", "O eixo do SG90 fica a 6,1 mm da extremidade"],
    ["Bolso do horn", "Cubo Ø9,2; braços em tronco de cone de 9,2 mm (junto ao cubo) a 5,4 mm (ponta); 2,0 mm de profundidade", "O braço do horn do SG90 sai tangente ao cubo Ø8 e afina até a ponta — um rasgo reto deixaria o horn sem assentar. Horn de 2 braços (elos), em cruz (plataforma) e simples (garra)"],
    ["Furo do parafuso central", "Ø2,6 mm passante", "Parafuso PA 2,0 × 6 + arruela M2 atravessa 2 mm de chapa e o topo do horn e rosqueia ≈ 3 mm no furo cego do eixo (medir a profundidade do furo antes: ver lista de fixadores)"],
    ["Furos-piloto do horn", "Ø1,5 mm", "Micro parafusos autoatarraxantes PA 1,7 × 6 (não vêm no kit do servo)"],
    ["Pino da engrenagem livre", "Ø3,4 mm (chapa) / Ø3,4 mm (engrenagem)", "Parafuso M3 × 25 inox como eixo + porca autotravante"],
    ["Engrenagens da garra", "16 dentes, módulo 1,5, Ø primitivo 24 (= distância entre centros), Ø externo 26,4 (addendum 0,8 m); folga de flanco 0,19 mm", "Dentes trapezoidais com addendum encurtado: sem interferência de topo; a folga (≈ 1,6° de backlash) absorve a imprecisão do FDM"],
    ["Munhão / mancal (lado livre)", "Munhão Ø9 impresso (8,8 mm no ombro, 14,8 mm no cotovelo) em mancal Ø9,4 passante", "Folga diametral de 0,4 mm — gira livre depois de tirar a rebarba. Não leva parafuso: quem prende axialmente é o parafuso central do horn do lado motriz somado à travessa"],
    ["Travessa do braço / palma do antebraço", "2 furos passantes Ø3,4 na chapa motriz + furo-piloto Ø2,5 × 8 mm no reforço; parafusos M3 × 10", "Amarram as duas chapas de cada elo (fecham a forquilha). Sem elas as chapas abrem sob esforço lateral e o munhão sai do mancal"],
    ["Espessura das chapas", "4 mm (≈ 20 camadas de 0,2 mm)", "Rigidez adequada com 15 % de preenchimento"],
], [4.5, 5.5, 6])
H("5.4 Análise simplificada de carga", 2)
P("O servo mais solicitado é o ombro (S2). O cálculo é um diagrama de corpo livre feito sobre o próprio modelo 3D "
  "(cad/verificacao.py soma massa × braço de alavanca peça por peça, usando o centro de massa de cada malha e "
  "13,4 g por MG90S e 9 g por SG90). Na pior pose — braço e antebraço na horizontal, alcance máximo — dá "
  "τ_S2 = 0,52 kgf·cm sem carga (29 % do travamento) e τ_S2 ≈ 0,52 + 0,018·m [kgf·cm, m em gramas] com uma massa m "
  "na ponta. A 5 V, SG90 e MG90S entregam o mesmo torque de travamento, ≈ 1,8 kgf·cm (os 2,2 kgf·cm do MG90S são a 6 V).", al="j")
P("Um servo de hobby não deve sustentar pose acima de ≈ 50 % do travamento: com 25 g o ombro vai a 54 % e com 50 g a "
  "79 % (aquece e perde posição). Daí a carga útil de ≈ 20 g em extensão máxima — ou ≈ 30 g aceitando 60 % do "
  "travamento em movimentos curtos. Com o braço recolhido (vertical) o braço de alavanca cai para o antebraço apenas e "
  "a carga útil sobe para ≈ 65 g. O cotovelo (S3) fica em 39 % mesmo com 50 g e a garra tem força de sobra "
  "(≈ 3,6 N de travamento na mandíbula).", al="j")
P("Comparação com a versão anterior, em chapa única: duplicar as chapas levou a massa móvel de ≈ 39 g para ≈ 59 g e o "
  "torque em vazio de 0,39 para 0,52 kgf·cm, custando ≈ 5 g de carga útil. Em troca, cada junta passou a trabalhar em "
  "cisalhamento duplo (dois apoios em vez de um balanço), o esforço lateral sobre o estriado de nylon do horn "
  "praticamente desapareceu e o centro de massa ficou sobre o eixo da base — o que também alivia S1. As janelas nas "
  "quatro chapas e na palma foram dimensionadas para recuperar parte dessa massa. O MG90S é indicado nas juntas 2 e 3 "
  "não pelo torque, mas pelas engrenagens metálicas e pelo rolamento do eixo. Ponto fraco remanescente: o conjunto "
  "girante pendura no eixo de S1 sem mancal — por isso a base tem quatro colunas de encosto a 0,5 mm da plataforma, "
  "que limitam o balanço sem travar o giro.", al="j")

H("5.5 Suporte dos joysticks (controle de mão)", 2)
P("Os dois módulos KY-023 são montados em uma placa impressa no formato de controle de videogame "
  "(160 × 100 × 9,2 mm, arquivo 09_suporte_joysticks.stl), inspirada nos suportes de MDF cortados a laser. "
  "Joystick 1 (esquerda) comanda base e ombro; joystick 2 (direita), garra e cotovelo — mesma lógica de um "
  "controle de videogame.", al="j")
P("Fixação — por que não é por furo: a placa do KY-023 mede 34 × 26 mm (valor confirmado nas fichas do fabricante e "
  "de distribuidores), mas NENHUM datasheet publica a distância entre os furos Ø3, e ela varia de fabricante para "
  "fabricante; além disso o gimbal do joystick (≈ 22 × 22 mm) encosta nos furos do lado estreito em vários clones. "
  "Por isso o suporte não depende dessa cota:", al="j")
B([("Berço de 4 cantos em L: ", "posiciona o módulo pela BORDA da placa (envelope 34,6 × 26,6 mm), com assento de 3 mm "
    "que afasta as soldas da chapa e lábio de 2,2 mm que trava a placa lateralmente."),
   ("4 rasgos radiais 3,4 × 11,4 mm: ", "o parafuso M3 corre 8 mm na direção radial, de modo que a mesma peça aceita "
    "qualquer furação simétrica entre ≈ 21,5 × 15,4 mm e ≈ 34,5 × 24,6 mm (o nominal adotado é 28 × 20 mm). "
    "Medir a placa com paquímetro só é necessário se ela estiver fora dessa faixa — aí basta alterar JOY_FUROS no script."),
   ("Parafusos M3 × 12 + arruela ampla Ø9 + porca: ", "2 a 4 por módulo, conforme os furos acessíveis na placa. "
    "Se o gimbal cobrir dois deles, os cantos do berço já impedem o módulo de sair de posição.")])
P("Acima de cada módulo há dois rasgos para abraçadeira de nylon, que prendem o chicote de 5 fios (barra de pinos "
  "voltada para cima), e no topo um rasgo para pendurar o controle.", al="j")
figura(IMG("suporte_joysticks.png"), "Figura 3 — Suporte dos joysticks: berço de cantos em L e rasgos radiais, com os dois módulos KY-023 posicionados.", 16)

H("5.6 Duas opções de garra (ferramenta intercambiável)", 2)
P("A garra é a interface com o objeto, e nenhuma geometria serve para tudo. O projeto entrega dois pares de dedos "
  "que usam a MESMA engrenagem, o mesmo bolso de horn, o mesmo pino M3 e a mesma distância entre centros — ou seja, "
  "são troca direta, sem alterar antebraço, palma, servo ou firmware:", al="j")
B([("Opção A — mandíbula plana (07 e 08): ", "faces retas de 10 × 12 mm. Contato em 2 pontos, ideal para objetos de "
    "faces planas e paralelas: blocos, caixinhas, cartões, peças prismáticas. É a garra montada nas figuras deste relatório."),
   ("Opção B — mandíbula em V (10 e 11): ", "faces de 10 × 17 mm com entalhe em V de ≈ 95° (apex 5 mm dentro da face, "
    "abertura 11 mm). Contato em 4 pontos: o objeto se auto-centra e não rola nem escapa. Como a garra fecha no plano "
    "horizontal, o sulco do V fica VERTICAL — é a opção para pegar cilindros e esferas em pé sobre a mesa: canetas, "
    "marcadores, pilhas, tubos de ensaio, frascos, bolinhas.")])
P("Capacidade medida no modelo (maior cilindro em pé que as duas mandíbulas tocam ao mesmo tempo, em função do ângulo "
  "do servo da garra; 75° = dedos paralelos, 110° = ANG_MAX):", al="j")
tabela(["Ângulo de S4", "75° (dedos paralelos)", "80°", "90°", "100°", "110° (aberta)"], [
    ["Opção A — plana", "Ø 4 mm", "Ø 13 mm", "Ø 29 mm", "Ø 44 mm", "Ø 58 mm"],
    ["Opção B — em V", "Ø 10 mm", "Ø 15 mm", "Ø 28 mm", "Ø 41 mm", "Ø 53 mm"],
], [3.2, 3.2, 2.2, 2.2, 2.2, 2.6])
P("Perto do fechamento a diferença é grande: com os dedos quase paralelos a opção A só consegue prender uma lâmina de "
  "4 mm, enquanto o V já abraça um cilindro de 10 mm. Na abertura máxima as duas são equivalentes (o V “gasta” 5 mm de "
  "cada mandíbula). Em ambas, o ângulo em que as mandíbulas se tocam é o mesmo (≈ 72,5° no servo), então GARRA_FECHADA "
  "e ANG_MIN[3] do firmware não mudam com a troca.", al="j")
P("Troca da garra (2 minutos): soltar o parafuso central do horn de S4 e o parafuso M3 × 25 do dedo livre, retirar os "
  "dois dedos, montar o outro par na mesma ordem da seção 7.1 (S4 em 75°, dedos paralelos) e reapertar. O horn continua "
  "no dedo motriz de cada par — quem imprimir as duas opções pode deixar um horn em cada uma e a troca fica ainda mais "
  "rápida (o kit do servo traz vários horns).", al="j")
figura(IMG("garras.png"), "Figura 4 — As duas opções de garra vistas pelo eixo das engrenagens: à esquerda a mandíbula plana com um bloco de 25 mm; à direita a mandíbula em V com um cilindro Ø16 em pé.", 16)

# ================================================================== 6
H("6. Modelagem no Tinkercad e geração dos STL", 1)
H("6.1 Importar os STL prontos (um projeto por peça)", 2)
N(["Acesse https://www.tinkercad.com/dashboard e clique em Criar → Projeto 3D.",
   "Clique em Importar (canto superior direito) → selecione STL/01_base_fixa.stl → unidade: milímetros → escala 100 %.",
   "Renomeie o projeto (ex.: “Braço 4GDL – 01 Base fixa”). Repita para as outras oito peças, cada uma em um projeto separado.",
   "Para o protótipo montado, importe STL/montagem_completa.stl em um décimo projeto (visualização).",
   "Exportar: Exportar → .STL (o Tinkercad gera um STL individual por projeto). Esses arquivos vão para o Bambu Studio."])
H("6.2 Receita para modelar cada peça com primitivas do Tinkercad", 2)
P("Caso se deseje construir as peças do zero no Tinkercad (sólidos = formas; furos = formas marcadas como “Furo”; "
  "alinhar e agrupar), as cotas abaixo reproduzem o modelo. Origem: centro da peça; Z para cima.", al="j")
receitas = [
    ("01 Base fixa", ["Sólidos: Cilindro Ø110 × 4; Caixa 38,6 × 28 × 27 (torre) apoiada em z=3, centro em x=+5,3; 4 Cilindros Ø9 × 36,3 (colunas de encosto) em raio 24,5 (45°, 135°, 225°, 315°), de z=4 a z=40,3.",
                      "Furos: Caixa 28 × 18 × 28 (cavidade, centro x=+5,3, de z=−1 a 27); Caixa 8 × 60 × 2 (canal do cabo, sob a base, x −4..4, y 0..60); "
                      "Caixa 23,2 × 12,6 (rasgo do servo na tampa, centro x=+5,3); 2 Cilindros Ø1,7 em x=−8,45 e x=+19,05; 4 Cilindros Ø3,4 em raio 47 (45°, 135°, 225°, 315°)."]),
    ("02 Plataforma giratória", ["Sólidos: Cilindro Ø60 × 4; DUAS Caixas 34,6 × 4 × 41 (paredes da forquilha: uma em y 4..8, outra em y −14..−10; z 3..44; centro x=+5,3); 2 Caixas 4 × 14,5 × 27 (nervuras que ligam as duas paredes, em x −12..−8 e 18,6..22,6; y −10..4,5; z 3..30).",
                                 "Furos: bolso em cruz na face inferior (Cilindro Ø9,2 × 2 + 4 braços de 14 mm em tronco de cone Ø9,2→Ø5,4, profundidade 2); Cilindro Ø2,6 passante no centro; 8 Cilindros Ø1,5 (±7,5 e ±11 nos dois eixos); "
                                 "rasgo 23,2 × 12,6 na parede motriz (centro x=+5,3, z=28) + 2 Cilindros Ø1,7 em x=−8,45 e +19,05 (z=28); Cilindro Ø9,4 passante na parede livre em (0; z=28) — é o mancal do munhão do braço."]),
    ("03 Braço — chapa motriz", ["Sólidos: Caixa 34 × 4 × 70 + 2 Cilindros Ø34 × 4 (eixo Y) em z=0 e z=70 (chapa no plano XZ).",
                  "Furos: janela 16 × 30 (z 22..52); bolso duplo na face interna (Cilindro Ø9,2 × 2 + 2 braços de 16,5 mm em tronco de cone Ø9,2→Ø5,4); Cilindro Ø2,6 passante em z=0; 4 furos Ø1,5 em z=±8 e ±12; "
                  "rasgo 12,6 (x) × 23,2 (z) centrado em (0; 64,7) [eixo do servo em z=70]; furos Ø1,7 em z=50,95 e z=78,45; 2 furos Ø3,4 em (−13; 59) e (−13; 67) para os parafusos da travessa."]),
    ("04 Braço — chapa livre", ["Sólidos: mesma silhueta da chapa motriz; Cilindro Ø9 × 9,8 saindo da face interna em z=0 (munhão do ombro); Caixa 4 × 38,6 × 14 (travessa: x −17..−13, y −1..37,6, z 56..70); Caixa 8 × 8 × 14 (reforço dos furos-piloto, x −17..−9, y 29,6..37,6).",
                  "Furos: janela 16 × 30 (z 22..52); Cilindro Ø9,4 passante em z=70 (mancal do cotovelo); 2 furos-piloto Ø2,5 × 8,4 na face livre do reforço, em (−13; 59) e (−13; 67)."]),
    ("05 Antebraço — chapa motriz", ["Sólidos: Cilindro Ø34 × 4 em z=0; Caixa 34 × 4 × 40; a partir de z=40 a borda inferior recua em diagonal até x=0 em z=56 e segue reta até a ponta (z=78), para deixar as mandíbulas livres.",
                      "Furos: janela 16 × 24 (z 20..44); bolso duplo + Ø2,6 + 4 furos Ø1,5 como no braço; 2 furos Ø3,4 em (−10; 54) e (−10; 74) para os parafusos da palma."]),
    ("06 Antebraço — chapa livre + palma", ["Sólidos: mesma silhueta da chapa motriz; Cilindro Ø9 × 15,8 na face interna em z=0 (munhão do cotovelo); Caixa 4 × 68,2 × 30 (PALMA: x −14..−10, y −1..67,2, z 48..78); 2 Caixas 8 × 8 × 10 (reforços dos furos-piloto na ponta da palma).",
                      "Furos: janela 16 × 24; na palma, rasgo 23,2 × 12,6 do servo S4 (eixo em y=45,6 medido da face interna, z=62; corpo ao longo de −y) + 2 Cilindros Ø1,7 em y=26,55 e y=54,05; Cilindro Ø3,4 em (y=21,6; z=62) — pino do dedo livre; janela 13 × 22 na palma (y 3..16, z 52..74); 2 furos-piloto Ø2,5 × 8,4 em (−10; 54) e (−10; 74)."]),
    ("07 Dedo motriz", ["Sólidos: Engrenagem (Geradores de forma → Gear): 16 dentes, módulo 1,5, Ø externo 26,4 (addendum 1,2 mm), altura 4; Caixa 10 × 55 × 4 (haste, y 0..55); Caixa 10 × 12 × 4 (mandíbula, x 0..10, y 43..55).",
                        "Furos: bolso simples na face superior (Cilindro Ø9,2 × 2 + 1 braço de 18 mm em tronco de cone Ø9,2→Ø5,4); Cilindro Ø2,6 passante; 3 furos Ø1,5 em y=8, 12 e 15."]),
    ("08 Dedo livre", ["Espelho do dedo motriz (mandíbula em x −10..0), sem bolso do horn; engrenagem girada 11,25° (meio dente).",
                       "Sólido extra: Cilindro Ø9 × 10,8 sobre a engrenagem (espaçador). Furo: Cilindro Ø3,4 passante."]),
    ("10 e 11 — Dedos da garra em V (opção B)", ["Iguais aos dedos 07 e 08, com duas diferenças: a mandíbula vai de y=38 a y=55 (em vez de y=43..55) e recebe um furo em forma de cunha.",
                                  "Furo: Triângulo (prisma de 4 mm de altura) com vértices (±10,5; 41), (±10,5; 52) e (±5; 46,5) — apex 5 mm dentro da face de trabalho, abertura de 11 mm. No Tinkercad: forma “Wedge”/“Roof” girada, ou um cilindro de 3 lados achatado, marcado como Furo."]),
    ("09 Suporte dos joysticks", ["Sólidos: Caixa 160 × 74 × 4 com cantos R14 (corpo, y −22..52); 2 Cilindros Ø44 × 4 em (±54; −26) (empunhaduras); "
                                  "por módulo (centros em (±45; 14)), 4 cantos em L alinhados com a borda da placa (envelope 34,6 × 26,6): assento 11 × 8 × 3 mm sob cada canto + 2 paredinhas de 2,5 mm de espessura e 5,2 mm de altura.",
                                  "Furos: 4 rasgos radiais por módulo (Caixa 3,4 × 8 com pontas redondas, apontando do centro do módulo para o furo nominal em ±14; ±10); 4 Caixas 3 × 8 em (±33..36; 38..46) e (±54..57; 38..46) (abraçadeiras); "
                                  "rasgo de pendurar 15 × 9 com pontas redondas centrado em (0; 42)."]),
]
for nome, linhas in receitas:
    P(nome, b=True); B(linhas)

# ================================================================== 7
H("7. Protótipo montado", 1)
figura(IMG("montagem_vistas.png"), "Figura 5 — Vistas isométrica, frontal, lateral e superior do protótipo montado (servos em azul).", 16)
figura(IMG("montagem_repouso.png"), "Figura 6 — Posição de repouso (home): todos os servos em 90°.", 11)
figura(IMG("montagem_captura.png"), "Figura 7 — Captura na horizontal: com o antebraço na horizontal, os eixos das engrenagens ficam verticais e as mandíbulas fecham no plano horizontal (vista superior à direita).", 16)
H("7.1 Sequência de montagem", 2)
N(["Remover rebarbas; testar o encaixe de cada servo nos rasgos (deve entrar justo, sem forçar) e de cada munhão Ø9 no seu mancal Ø9,4 (deve girar livre; se prender, lixar o munhão, nunca o furo). Rosquear um parafuso PA 2,0 no furo cego do eixo de cada servo, sem peça, e medir com paquímetro quanto entra: define o comprimento do parafuso central (lista de fixadores, item 1b).",
   "Base fixa: parafusar o disco na tábua de apoio (4 × M3 × 16 nos furos Ø3,4 — obrigatório, o braço estendido tomba sem isso); encaixar S1 por cima na torre (flange apoiado na tampa) e fixar com 2 parafusos PA 2,0 × 8 (do kit do servo).",
   "Ligar o Arduino, carregar o firmware e enviar 's 0 90', 's 1 90', 's 2 90', 's 3 75' para centralizar os servos antes de montar os horns.",
   "Plataforma: colocar o horn em cruz no bolso inferior (deve assentar no fundo; 4 micro parafusos PA 1,7 × 6), encaixar no eixo de S1 com a plataforma a 0,5 mm das colunas de encosto e fixar com o parafuso central (PA 2,0 × 6 + arruela M2). O estriado do eixo tem ≈ 21 dentes (≈ 17° por dente): escolher a posição mais próxima do alinhamento e corrigir o resto na calibração.",
   "Fixar S2 na parede MOTRIZ da plataforma (a de y = 4..8): o corpo atravessa a parede para dentro da forquilha e o flange fica na face externa. Conferir que a extremidade do corpo do servo não encosta na parede livre (folga de projeto: 2,1 mm).",
   "Braço: montar o horn duplo no bolso da chapa motriz (03). Encaixar primeiro a chapa LIVRE (04) — o munhão entra no mancal da parede livre —, depois a chapa motriz no eixo de S2, na vertical, e apertar o parafuso central. Fechar a forquilha aparafusando a travessa da chapa livre na chapa motriz (2 × M3 × 10, por fora da chapa motriz).",
   "Fixar S3 na chapa motriz do braço (flange na face externa, corpo para dentro da forquilha).",
   "Antebraço: montar o horn duplo no bolso da chapa motriz (05). Encaixar a chapa LIVRE (06, a que traz a palma) pelo munhão no mancal da chapa livre do braço; encaixar a chapa motriz no eixo de S3 a 90° do braço e apertar o parafuso central. Fechar a forquilha aparafusando a palma na chapa motriz (2 × M3 × 10).",
   "Garra: aparafusar S4 na palma pelo lado de baixo (flange contra a face interna da palma, corpo atravessando para cima; 2 × PA 2,0 × 8) ANTES de montar as engrenagens — um dos furos do flange fica sob a engrenagem motriz.",
   "Dedo livre: parafuso M3 × 25 de cima para baixo pela palma, arruela de nylon, dedo (espaçador Ø9 contra a palma), arruela e porca autotravante — apertar só até girar livre.",
   "Dedo motriz: horn simples no bolso; com S4 em 75° encaixar a engrenagem já engrenada com o dedo livre e os dois dedos paralelos; parafuso central. Conferir que as duas mandíbulas fecham no plano horizontal quando o antebraço está na horizontal.",
   "Ligar os extensores de 300 mm em S3 e S4 e passar os cabos ao longo dos elos (abraçadeiras), com uma laçada de folga em cada junta; S2 e S1 alcançam o circuito com o cabo de fábrica.",
   "Garra alternativa (opção B, peças 10 e 11): se quiser trocar o par de dedos, repetir os dois passos anteriores com os dedos em V — mesma ordem, mesmo parafuso M3 × 25 e mesmo ângulo de montagem (S4 em 75°, dedos paralelos).",
   "Controle de mão: assentar cada módulo KY-023 no berço (a placa encosta nos 4 cantos em L), parafusar com M3 × 12 + arruela ampla + porca nos rasgos radiais que coincidirem com os furos da placa (2 são suficientes se o gimbal cobrir os outros), com a barra de pinos voltada para cima; prender os chicotes nos rasgos com abraçadeiras e ligar à protoboard conforme o esquema."])


# ================================================================== 8
H("8. Projeto eletrônico", 1)
figura(IMG("esquema_eletrico.png"), "Figura 8 — Esquema elétrico de ligação.", 16.5)
tabela(["Sinal", "Pino Arduino", "Componente", "Observação"], [
    ["PWM servo base (S1)", "D3", "SG90 — fio laranja", "Servo.h, 600–2400 µs"],
    ["PWM servo ombro (S2)", "D5", "MG90S — fio laranja", ""],
    ["PWM servo cotovelo (S3)", "D6", "MG90S — fio laranja", ""],
    ["PWM servo garra (S4)", "D9", "SG90 — fio laranja", ""],
    ["Joystick 1 — VRx / VRy", "A0 / A1", "KY-023 (base / ombro)", "+5 V e GND do Arduino"],
    ["Joystick 1 — SW", "D2", "Botão do joystick (para GND)", "INPUT_PULLUP; curto = grava pose, longo = reproduz/para"],
    ["Joystick 2 — VRx / VRy", "A2 / A3", "KY-023 (garra / cotovelo)", "+5 V e GND do Arduino"],
    ["Joystick 2 — SW", "D4", "Botão do joystick (para GND)", "INPUT_PULLUP; curto = abre/fecha garra, longo = home"],
    ["LED de status", "D13", "LED da placa", "Aceso = manual; piscando = reproduzindo"],
    ["+5 V servos", "—", "Fonte 5 V / 3 A + C1 1000 µF", "NUNCA pelo 5 V do Arduino"],
    ["GND", "GND", "Comum a fonte, servos, pots e Arduino", "Obrigatório"],
], [3.8, 2.6, 4.6, 5])
P("Consumo: cada micro-servo pode drenar picos de 0,6–0,8 A ao partir ou sob carga; quatro servos exigem fonte de ao "
  "menos 2,5 A. O capacitor C1 próximo ao barramento reduz quedas de tensão que provocam reset do Arduino e "
  "tremores (jitter) nos servos.", al="j")

# ================================================================== 9
H("9. Firmware (Arduino IDE)", 1)
P("Arquivo: firmware/braco_robotico/braco_robotico.ino. Bibliotecas: Servo.h e EEPROM.h (nativas da IDE). Placa: Arduino UNO.", al="j")
H("9.1 Estrutura", 2)
B([("Configuração: ", "tabelas de pinos, limites (ANG_MIN/ANG_MAX) e posição de repouso (ANG_HOME) por junta."),
   ("Laço de controle (50 Hz): ", "lê os 4 eixos dos joysticks; fora da zona morta (±60 counts) calcula um incremento de ângulo proporcional ao quadrado da deflexão (até VEL_JOY = 2 °/passo = 100 °/s), soma ao alvo da junta dentro dos limites e aproxima a posição atual do alvo a no máximo velMax graus por passo (rampa de velocidade)."),
   ("Máquina de estados: ", "MANUAL (joysticks) ↔ REPRODUZINDO (percorre as poses gravadas com pausa de 0,5 s em cada uma). Ao parar a reprodução o alvo assume a posição atual, e os joysticks continuam de onde o braço parou, sem saltos."),
   ("Botões dos joysticks: ", "SW1 curto = grava pose (LED pisca 3×), SW1 longo ≥ 0,8 s = inicia/para reprodução; SW2 curto = abre/fecha a garra, SW2 longo = posição de repouso (home). Debounce por tempo; estrutura Botao reutilizada para os dois."),
   ("Serial: ", "comandos de uma letra para calibração e depuração (p, g, l, r, m, h, a, j, e, c, v<n>, s <junta> <ângulo>); 'j' recalibra o centro dos joysticks."),
   ("EEPROM: ", "poses salvas com assinatura 0xB4A1 e carregadas automaticamente na partida.")])
H("9.2 Fluxo de execução", 2)
N(["setup(): inicializa serial, botões e LED; anexa os servos um a um (150 ms entre eles) já na posição home; calibra o centro dos 4 eixos (16 leituras, joysticks soltos); carrega poses da EEPROM.",
   "loop(): trata serial e botões a cada iteração; a cada 20 ms executa o passo do modo atual (leJoysticks + avancaParaAlvo, ou passoReproducao) e atualiza o LED.",
   "avancaParaAlvo(): para cada junta, move no máximo velMax graus, satura nos limites e escreve nos servos."])
H("9.3 Testes e calibração", 2)
N(["Sem as peças montadas, carregar o firmware e usar 's <j> <ang>' para verificar o sentido e a faixa de cada servo.",
   "Montar e ajustar ANG_MIN/ANG_MAX de cada junta. O firmware sai com o cotovelo limitado a 40..140° (simétrico, porque o sentido do servo só se conhece agora). Cotovelo: descobrir com 's 2 <ang>' em qual sentido o antebraço dobra sobre o braço; desse lado NÃO passar de 145° (a palma encosta na parede da plataforma a 148°, medido por varredura booleana); do lado 'esticado' pode-se abrir até 20°, ganhando alcance. Ombro: com o ombro além de ≈ 135° e o cotovelo dobrado, o antebraço desce abaixo do plano da mesa e toca o disco da base — evitar a combinação ou reduzir ANG_MAX[1] para 135.",
   "Calibrar a garra: com o horn montado a 75° (dedos paralelos, vão de 4 mm), reduzir o ângulo de 1 em 1 grau ('s 3 74', 's 3 73'...) até as mandíbulas encostarem; anotar esse ângulo em ANG_MIN[3] e usar ≈ 2° acima dele em GARRA_FECHADA (nunca abaixo: o servo fica em travamento). 's 3 110' deve abrir ≈ 57 mm na raiz das mandíbulas.",
   "Verificar o sentido de cada eixo do joystick (inclinar para a direita deve girar a base para a direita etc.); inverter pelo vetor SENTIDO[] se necessário.",
   "Com os joysticks soltos, o braço deve ficar imóvel; se houver deriva, aumentar ZONA_MORTA ou recalibrar com 'j'.",
   "Validar o modo manual (suavidade, ausência de tremor) e o ciclo gravar → reproduzir com 4–6 poses (ex.: pegar e soltar um objeto de 20 g usando SW2 para a garra).",
   "Medir a corrente da fonte durante o movimento; se o Arduino reiniciar, verificar o GND comum e o capacitor C1."])

# ================================================================== 10
H("10. Parâmetros de impressão — Bambu Lab A1", 1)
tabela(["Parâmetro", "Valor", "Observação"], [
    ["Impressora / bico", "Bambu Lab A1, bico 0,4 mm", "Volume 256 × 256 × 256 mm"],
    ["Material", "PLA (Bambu PLA Basic ou similar)", "220 °C bico / 60 °C mesa (mesa PEI texturizada)"],
    ["Perfil de processo", "0.20 mm Standard @BBL A1", "Altura de camada 0,20 mm; 1ª camada 0,20 mm"],
    ["Preenchimento", "15 %, padrão Grid ou Gyroid", "Requisito do projeto"],
    ["Paredes / topo / base", "3 perímetros (1,2 mm) / 4 camadas / 3 camadas", "Rigidez das chapas de 4 mm"],
    ["Suportes", "Desativados", "Maior ponte: 23 mm (teto do rasgo do servo na plataforma e na palma); maior balanço: 2,6 mm. As travessas e a palma são impressas EM PÉ sobre a chapa (paredes verticais), e os munhões Ø9 saem na vertical — nenhuma dessas peças precisa de suporte"],
    ["Adesão", "Nenhuma (brim de 3 mm opcional na plataforma)", "Mesa limpa com álcool isopropílico"],
    ["Compensação de furos (X-Y hole compensation)", "0,10 mm se os furos ficarem justos", "Furos Ø1,5–1,9 tendem a encolher em FDM"],
    ["Orientação", "Conforme os STL (face plana para baixo)", "Ver Figura 2 e tabela da seção 5.2"],
    ["Fluxo de trabalho", "STL → Bambu Studio (ou MakerWorld) → fatiar → enviar por Wi-Fi/SD", ""],
], [4.5, 5.5, 6])

# ================================================================== 11
H("11. Cronograma sugerido e riscos", 1)
tabela(["Semana", "Atividade", "Entrega"], [
    ["1", "Compra dos componentes; revisão dos modelos no Tinkercad", "Projetos Tinkercad + STL"],
    ["2", "Impressão das 11 peças (≈ 7 h, incluindo as duas opções de garra) e ajustes de encaixe (munhões e bolsos)", "Peças impressas"],
    ["3", "Montagem mecânica + circuito na protoboard", "Protótipo montado"],
    ["4", "Firmware, calibração dos limites e testes de pega", "Vídeo de demonstração + relatório final"],
], [2, 9, 5])
B([("Risco — furos apertados: ", "usar compensação de furos de 0,1 mm ou alargar com broca de 1,8/3,5 mm."),
   ("Risco — servo sem torque: ", "verificar tensão da fonte sob carga; trocar SG90 por MG90S no ombro/cotovelo."),
   ("Risco — horn folgado no bolso: ", "aplicar uma gota de cola quente no bolso além dos parafusos."),
   ("Risco — reset do Arduino: ", "GND comum, capacitor C1 e nunca alimentar servos pela USB."),
   ("Risco — joystick com deriva (braço se move sozinho): ", "ligar o sistema com os joysticks soltos (calibração do centro), aumentar ZONA_MORTA ou usar o comando 'j'.")])

# ================================================================== 12
H("12. Referências", 1)
B(["Tinkercad — https://www.tinkercad.com/dashboard",
   "Bambu Lab A1 — especificações técnicas e Bambu Studio — https://bambulab.com/en/a1",
   "Arduino — referência da biblioteca Servo — https://www.arduino.cc/reference/en/libraries/servo/",
   "TowerPro — folha de dados do micro-servo SG90 / MG90S (corpo 22,8 × 12,2 mm; torque de travamento 1,8 kgf·cm a 4,8 V para ambos; MG90S 2,2 kgf·cm a 6 V; pulso 500–2400 µs).",
   "Trimesh + Manifold (modelagem CSG em Python) — https://trimesh.org",
   "NISE, N. S. Engenharia de Sistemas de Controle. 7. ed. LTC, 2017 (fundamentos de atuadores e controle)."])

# ================================================================== Apêndice A
doc.add_page_break()
H("Apêndice A — Código-fonte completo (braco_robotico.ino)", 1)
codigo_bloco(codigo)

# ================================================================== Apêndice B
doc.add_page_break()
H("Apêndice B — Estrutura de arquivos do projeto", 1)
codigo_bloco("""Braço Mecânico/
├── Detalhes.txt                      enunciado do projeto
├── README.md                         guia rápido
├── CLAUDE.md                         memória de desenvolvimento e revisão (decisões, cotas, pendências)
├── cad/
│   ├── gerar_pecas.py                modelagem paramétrica (gera STL, montagem e imagens)
│   ├── verificacao.py                varreduras de colisão, engrenagens, envelope e torque
│   ├── gerar_esquema.py              esquema elétrico
│   └── pecas_info.json               dimensões/massa/tempo de cada peça
├── STL/
│   ├── 01_base_fixa.stl … 11_garra_v_dedo_livre.stl  uma peça por arquivo (orientação de impressão)
│   └── montagem_completa.stl         protótipo montado
├── imagens/                          montagem_*.png, pecas_impressao.png, suporte_joysticks.png, esquema_eletrico.png
├── firmware/braco_robotico/braco_robotico.ino        código para o Arduino IDE
└── relatorio/
    ├── gerar_relatorio.py            gera este documento
    ├── parafusos.py                  dados da lista de fixadores (usada aqui e no documento à parte)
    ├── gerar_lista_parafusos.py      gera Lista_Parafusos_Fixadores.docx
    ├── Lista_Parafusos_Fixadores.docx
    └── Relatorio_Braco_Robotico.docx""")

# ================================================================== Apêndice C (lista à parte)
doc.add_page_break()
H("Apêndice C — Lista de parafusos e fixadores (lista de compras à parte)", 1)
P("Dimensionada pelos furos das peças e pelos empilhamentos de montagem. Também entregue como documento separado "
  "(relatorio/Lista_Parafusos_Fixadores.docx).", i=True)
tabela(["#", "Especificação (modelo)", "Necess.", "Comprar", "Onde é usado", "Furo / empilhamento", "Material", "R$"],
       [list(i) for i in FIXADORES], [0.6, 3.4, 1.2, 1.4, 3.6, 3.6, 2.2, 0.8], 7.5)
P(f"Custo total estimado dos fixadores: R$ {custo_total():.0f}.", b=True)
B(NOTAS)

# Word atualiza os campos (sumário, páginas) ao abrir
settings = doc.settings.element
uf = OxmlElement("w:updateFields"); uf.set(qn("w:val"), "true"); settings.append(uf)
try:
    doc.save(SAIDA); print("OK", SAIDA)
except PermissionError:                      # arquivo aberto no Word: salva com outro nome
    alt = SAIDA.replace(".docx", "_novo.docx"); doc.save(alt)
    print("AVISO: o .docx estava aberto no Word; salvo como", alt, "- feche o Word, apague o antigo e renomeie.")
