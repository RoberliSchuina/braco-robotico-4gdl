# -*- coding: utf-8 -*-
"""parafusos.py — lista de parafusos e fixadores do braço robótico, dimensionada pelos furos das peças
(cad/gerar_pecas.py). Usada por gerar_lista_parafusos.py (documento à parte) e por gerar_relatorio.py (Apêndice C)."""

# Cada item: (#, especificação, qtd necessária, qtd a comprar, onde é usado, furo na peça / empilhamento, material sugerido, preço est. R$)
FIXADORES = [
    ("1", "Parafuso autoatarraxante PA 2,0 × 8 mm, cabeça panela Phillips (ponta aguda)",
     "8", "20 (pacote)",
     "Fixação dos 4 servos nos rasgos (2 por flange). Os 2 parafusos de fixação que vêm no kit de cada servo servem",
     "Furos-piloto Ø1,7 na peça (85 % do Ø2,0: o PLA faz a rosca). Empilhamento: 2,5 mm da aba do servo + 3–4 mm de chapa",
     "Aço carbono zincado (branco ou preto)", 6),
    ("1b", "Parafuso autoatarraxante PA 2,0 × 6 mm (central do horn) + arruela M2 Ø2,2 × Ø5 × 0,3 mm",
     "4", "10",
     "Parafuso central dos 4 horns (plataforma, braço, antebraço e dedo motriz), rosqueado no furo cego do eixo estriado do servo. A arruela apoia a cabeça na chapa",
     "Furo passante Ø2,6 no elo. Aperto real: 2,0 mm de chapa sobre o horn + ≈ 0,8 mm do topo do horn acima do eixo = 2,8 mm; sobram 3,2 mm para o furo cego do eixo (profundidade típica 3–5 mm, varia por fabricante). ANTES DE MONTAR: rosquear o parafuso no eixo sem a peça e medir quanto entra; se entrar ≥ 5 mm, o PA 2,0 × 8 do item 1 também serve; se entrar < 3 mm, usar o parafuso do próprio kit (≈ 5 mm) — um parafuso comprido demais bate no fundo e não aperta",
     "Aço carbono zincado", 3),
    ("2", "Micro parafuso autoatarraxante PA 1,7 × 6 mm (alternativa: 1,5 × 6), cabeça panela Phillips",
     "14", "50 (kit de micro parafusos)",
     "Prendem os horns dentro dos bolsos: 4 × plataforma (horn em cruz), 4 × braço, 4 × antebraço (horn duplo), 2 × dedo motriz (horn simples)",
     "Furos-piloto Ø1,5 na peça, através dos furos Ø1,3–1,5 dos braços do horn (se necessário, alargar o horn com broca de 1,5 mm)",
     "Aço zincado ou oxidado preto", 12),
    ("3", "Parafuso M3 × 25 mm, cabeça panela Phillips ou cilíndrica Allen (rosca total)",
     "1", "2",
     "Pino/eixo da engrenagem livre da garra",
     "Ø3,4 no antebraço e no dedo livre. Empilhamento: chapa 4 + ressalto/engrenagem 14,8 + 2 arruelas 1,0 + porca autotravante 4,0 ≈ 24 mm",
     "Aço inox A2 (superfície lisa = menos atrito na engrenagem)", 2),
    ("4", "Porca autotravante M3 (nylock, DIN 985)",
     "1", "2",
     "Trava o pino da engrenagem livre sem apertar (a engrenagem deve girar solta)",
     "—", "Aço inox A2 ou zincado", 1),
    ("5", "Arruela lisa M3 (Ø3,2 × Ø7 × 0,5 mm)",
     "2", "4",
     "Uma entre o ressalto do dedo livre e a chapa do antebraço; outra sob a porca",
     "—", "Nylon (a do ressalto, menor atrito) e inox (a da porca)", 1),
    ("6", "Parafuso M3 × 12 mm, cabeça panela Phillips",
     "8", "10",
     "Fixação dos 2 módulos joystick KY-023 no suporte impresso (4 por módulo)",
     "Rasgos em cruz 3,4 × 6 no suporte + furos Ø3 da placa. Empilhamento: placa 1,6 + ressalto 3 + chapa 4 + arruela 0,5 + porca 2,4 = 11,5 mm",
     "Aço zincado ou inox A2", 4),
    ("7", "Porca sextavada M3 (DIN 934)",
     "8", "10",
     "Idem item 6", "—", "Aço zincado", 2),
    ("8", "Arruela lisa M3 ampla (Ø3,2 × Ø9 × 0,8 mm) — se não houver, a comum Ø7 serve",
     "8", "10",
     "Sob a cabeça dos parafusos dos joysticks: cobre o rasgo em cruz de 6 mm",
     "—", "Aço zincado", 2),
    ("9", "Parafuso M3 × 16 mm + porca M3 (ou parafuso para madeira 3,0 × 16 mm, se a base for MDF)",
     "4", "4",
     "Fixação da base fixa na tábua/MDF de apoio — OBRIGATÓRIA: o disco Ø110 solto tomba com ≈ 15 g na garra em extensão máxima (raio de apoio 55 mm = raio do centro de massa)",
     "4 furos Ø3,4 no disco da base (raio 47 mm, a 45°, 135°, 225° e 315°)",
     "Aço zincado", 2),
    ("10", "Parafuso M3 × 6 mm + espaçador de nylon M3 × 6 mm com rosca (ou M3 × 10 + porca)",
     "4", "4",
     "Fixação do Arduino UNO na base de apoio (furos Ø3,2 da placa; normalmente 3 são acessíveis)",
     "—", "Nylon (espaçador) + aço zincado", 4),
]

NOTAS = [
    "Cotas conferidas com os furos de cad/gerar_pecas.py: Ø1,5 e Ø1,7 = furos-piloto para parafusos autoatarraxantes (o PLA "
    "faz a rosca); Ø2,6 e Ø3,4 = furos passantes (parafuso desliza; a cabeça apoia na peça).",
    "Comprimento indicado é o do corpo (sob a cabeça). Se o parafuso ficar 1–2 mm mais longo não há problema; mais curto "
    "que o empilhamento indicado não fixa.",
    "Peças impressas com 0,2 mm tendem a fechar furos pequenos em 0,2–0,3 mm: se um autoatarraxante entrar duro, "
    "alargar com broca de 1,5 mm (furos Ø1,5) ou 1,6 mm (furos Ø1,7). Nunca forçar: o PLA racha.",
    "Horns de SG90 não são padronizados: os furos-piloto Ø1,5 dos bolsos seguem uma grade típica (7,5/11 mm na cruz, 8/12 mm no duplo, "
    "8/12/15 mm no simples). Conferir com o horn comprado; se não coincidirem, furar em obra com broca de 1,5 mm usando o próprio horn como gabarito.",
    "Não apertar demais o pino da garra (item 3/4) nem os parafusos dos servos: aperto até encostar + 1/4 de volta.",
    "Ferramentas: chave Phillips PH0 (itens 1, 2 e 6), PH1 (itens 3, 9, 10), chave de boca/canhão 5,5 mm (porcas M3), "
    "chave Allen 2,5 mm se optar pela cabeça cilíndrica no item 3.",
    "Onde comprar: lojas de parafusos/ferragens (M3), lojas de eletrônica/robótica e kits de micro parafusos (PA 1,7 e 2,0).",
]

def custo_total():
    return sum(i[7] for i in FIXADORES)
