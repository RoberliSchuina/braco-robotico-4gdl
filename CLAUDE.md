# Braço Robótico 4 GDL — memória de desenvolvimento e revisão

Projeto da disciplina Sistemas Embarcados (FAESA, Eng. da Computação, 2026/2). Enunciado em `Detalhes.txt`.
Entregas: BOM, peças 3D (Tinkercad, uma por arquivo) + STL, protótipo montado, código Arduino IDE, relatório .docx.

## Estado atual (2026-09-19)
- [x] 7 peças modeladas (CSG em Python/trimesh) e exportadas em `STL/` na orientação de impressão (07 = suporte dos joysticks em formato de controle, adicionado em 2026-09-19)
- [x] Montagem (`STL/montagem_completa.stl`) + renders em `imagens/`
- [x] Firmware `firmware/braco_robotico/braco_robotico.ino` (4 servos, 2 joysticks KY-023, gravar/reproduzir, serial, EEPROM)
- [x] 2026-09-19: potenciômetros + botão avulso substituídos por 2 joysticks KY-023 (firmware, esquema, BOM e relatório atualizados; mecânica inalterada)
- [x] Esquema elétrico `imagens/esquema_eletrico.png`
- [x] 2026-09-21: repositório GitHub privado `RoberliSchuina/braco-robotico-4gdl` (remote `origin`, branch `main`); `gh` instalado em `C:\Program Files\GitHub CLI\` e autenticado. Após alterar/regenerar: `git add -A && git commit && git push`
- [x] 2026-09-20: guia de ligações furo a furo `Circuito_Braco_Robotico.html` (mesmo formato do Lab 1; SVG da protoboard + lista numerada + verificação; esquema PNG embutido em base64 — regerar o PNG exige reembutir)
- [x] Relatório `relatorio/Relatorio_Braco_Robotico.docx` (gerado por `relatorio/gerar_relatorio.py`)
- [x] Lista de parafusos/fixadores à parte: dados em `relatorio/parafusos.py` → `Lista_Parafusos_Fixadores.docx` (gerar_lista_parafusos.py) e Apêndice C do relatório. Alterar parafuso = editar só `parafusos.py` e rodar os dois geradores.
- [x] 2026-09-19: revisão de viabilidade física (90 agentes: cinemática, servo, torque, FDM, firmware, elétrica, montagem, docs) → 24 correções aplicadas; ver seção "Revisão de viabilidade" abaixo
- [ ] Importar cada STL em um projeto separado no Tinkercad (dashboard do aluno) e exportar de lá — passo manual
- [ ] Preencher nome do aluno/professor na capa do relatório; abrir no Word e aceitar "atualizar campos" (sumário)
- [ ] Imprimir, montar, calibrar `ANG_MIN/ANG_MAX` no firmware e registrar resultados dos testes na seção 9.3

## Regra: sincronizar com o GitHub
Toda alteração em arquivos deste diretório (fonte ou regenerados) deve terminar com `git add -A && git commit -m "..." && git push` para `RoberliSchuina/braco-robotico-4gdl` — pedido do usuário em 2026-09-21, autorização permanente (não perguntar). Se o push falhar, avisar.

## Como regenerar tudo
```bash
pip install trimesh manifold3d shapely numpy matplotlib python-docx
python cad/gerar_pecas.py        # ~1 min (renders são a parte lenta) -> STL/, imagens/, cad/pecas_info.json
python cad/gerar_esquema.py      # -> imagens/esquema_eletrico.png
python relatorio/gerar_relatorio.py
python relatorio/gerar_lista_parafusos.py
```
Toda cota está em `cad/gerar_pecas.py`; alterar lá e regenerar (não editar STL manualmente).

## Decisões de projeto (e porquê)
- **Tinkercad não tem API** → modelagem paramétrica em Python com a mesma lógica (sólidos/furos) e STL importável no Tinkercad. O relatório (seção 6) traz a "receita" de primitivas de cada peça para reproduzir nativamente se o professor exigir.
- **Junta = horn do servo em bolso de 2 mm + parafuso central** (sem rolamentos): simples, barato, suficiente para SG90/MG90S. O bolso NÃO é um rasgo reto: o braço do horn do SG90 sai tangente ao cubo Ø8 e afina até a ponta, por isso `bolso_horn_2d()` faz cubo Ø9,2 + tronco de cone Ø9,2→Ø5,4 por braço (`HORN_R_CUBO`/`HORN_R_PONTA`). Com rasgo reto de 5,4 mm o horn não assentava no fundo. Os furinhos Ø1,5 seguem uma grade típica (horns não são padronizados) — conferir com o horn comprado.
- **S1 sem mancal** → a base tem 4 colunas de encosto Ø9 em r=24,5, topo a 0,5 mm da plataforma (z=40,3): limitam o balanço do conjunto girante (~60 g pendurados no estriado de nylon) sem travar o giro. Verificado por booleana: zero interferência em todas as poses extremas.
- **Eixo do SG90 é deslocado 5,3 mm do centro do corpo** → rasgos e furos do flange são assimétricos em relação ao eixo (constante `SV_DESLOC_EIXO`). Não "centralizar" o rasgo.
- **Empilhamento em Y (degraus)**: parede da plataforma y=4..8 → braço y=18,8..22,8 → antebraço y=33,6..37,6 → engrenagens y≈45. `GAP_ELO = 10,8` (face interna do elo em relação à face de apoio do flange). Todos os servos têm o flange na face **externa** (+Y) e o corpo atravessa a chapa para −Y.
- **Garra no plano do braço** (engrenagens de eixo Y): abre "em bico". Pega objetos por cima com o antebraço apontando para baixo. Evita uma peça extra de punho e junta fraca em L.
- **Cotovelo**: o corpo de S4 (avança 11,9 mm para −Y) só encosta no braço quando o antebraço dobra **≥ 165°** sobre ele (varredura booleana 2026-09-19; 0 mm³ até 160°). A justificativa antiga "ANG_MIN[2]=40" estava errada (protegia o lado esticado, que é livre). Como o sentido do servo só se conhece na calibração, o firmware usa limite simétrico 20..160; depois de calibrar, o lado esticado pode ir a 5°.
- **Engrenagens 16 dentes m=1,5, dentes trapezoidais, addendum encurtado 0,8·m (Ø ext. 26,4) e flancos afinados 0,5°/lado** → interpenetração 0,000 mm² em 361 posições, folga de flanco 0,19 mm (≈ 1,6° de backlash), topo do dente 1,15 mm. A versão anterior (addendum 1·m, flancos ±5,2°) tinha backlash NEGATIVO em todos os ângulos — a garra travaria. Não "engrossar" o dente de volta. Dedo livre tem fase de meio dente (11,25°) por ser espelhado. Mandíbulas se tocam em alfa ≈ −2,5° (servo ≈ 72,5° com o horn montado a 75° = dedos paralelos, vão de 4 mm). Pino = **M3×25 inox + nylock** (empilhamento 4 + 14,8 + arruelas + porca ≈ 24 mm; M3×20 era curto) com espaçador Ø9×10,8 integrado ao dedo livre.
- **Tolerâncias FDM**: rasgo do servo +0,4 mm; furos-piloto **Ø1,7** (PA 2,0×8 — era Ø1,9 = 95 % do parafuso, não cortava rosca; 1,7 = 85 %) e Ø1,5 (PA 1,7×6 do horn); furo M3 passante Ø3,4; furo do parafuso central do horn **Ø2,6** (era Ø3,6 — maior que a cabeça Ø4 do PA 2,0; corrigido em 2026-09-19).
- **Parafusos**: o kit do servo traz 2 PA 2,0×8 (fixação). Parafuso central do horn = **PA 2,0×6 + arruela M2** (item 1b): aperto real é 2 mm de chapa + ~0,8 mm do topo do horn = 2,8 mm, e o furo cego do eixo tem só 3–5 mm — um 8 mm pode bater no fundo e não apertar. Medir o furo do eixo antes de montar (passo 1 da montagem). Micro parafusos do horn (PA 1,7×6) não vêm no kit. Joysticks: M3×12 + arruela ampla Ø9 (cobre o rasgo em cruz de 6 mm) + porca.
- Impressão: PLA, 0,2 mm, 15 % infill, 3 paredes, sem suportes (maior ponte 23 mm no teto do rasgo da plataforma; maior balanço 2,6 mm — medido camada a camada). Massa total ≈ 110 g, ≈ 5,5 h a 20 g/h (braço ≈ 73 g + controle ≈ 37 g). Base Ø110 e suporte 160×100 não cabem lado a lado no mesmo eixo da mesa (256): deixar o Bambu Studio arranjar.
- **Suporte dos joysticks** (`suporte_joysticks()`): silhueta 2D em shapely (retângulo R14 ∪ 2 círculos R22, fechamento morfológico R4) extrudada 4 mm; ressaltos **Ø10**×3 (Ø7 virava anel de 0,05 mm de parede depois do rasgo) e rasgos em cruz 3,4×6 porque a furação do KY-023 varia entre fabricantes (`JOY_FUROS = 26,5 × 20` é o valor típico — conferir com paquímetro). Não entra na `montagem()` (é o controle de mão); render próprio em `imagens/suporte_joysticks.png` com `joystick_dummy()`.

## Firmware — fatos não óbvios
- Protoboard (guia HTML): só as trilhas da direita são usadas — + = 5 V da fonte (servos), − = GND comum; 5 V do Arduino para os joysticks vai pela linha 21 (a21/b21/c21) da metade a–e. Sugestão de linhas: fonte 2/3, C1 4, GND Arduino 5, S1 6/7, S2 10/11, S3 14/15, S4 18/19, J1 GND 24, J2 GND 29.
- Pinos: servos D3/D5/D6/D9; J1: VRx→A0 (base), VRy→A1 (ombro), SW→D2; J2: VRx→A2 (garra), VRy→A3 (cotovelo), SW→D4; LED D13. `PIN_EIXO` está na ordem das juntas = {A0, A1, A3, A2}. Servos em fonte 5 V/3 A externa, GND comum; joysticks no 5 V do Arduino.
- Controle **incremental** (joystick = velocidade): zona morta ±60 counts, incremento = VEL_JOY·n² (2 °/passo máx.), `SENTIDO[]` inverte eixo. Centro calibrado no setup (16 leituras) e pelo comando `j` — ligar com os joysticks soltos.
- Máquina de estados só MANUAL ↔ REPRODUZINDO (PARADO foi eliminado: ao parar, alvo = posição atual, sem salto).
- SW1 curto = grava pose (máx. 16); SW1 longo ≥ 0,8 s = reproduz/para. SW2 curto = abre/fecha garra (74↔110); SW2 longo = home. EEPROM assinatura 0xB4A1 (`e`/`c`). `passoReproducao()` limita cada pose a ANG_MIN/MAX (pose fora da faixa congelava a reprodução, pois `avancaParaAlvo()` nunca "chegava").
- Rampa: `velMax` graus por passo de 20 ms (3 → 150 °/s) para home/reprodução/`s`. Servo.attach(pin, **600, 2400**) — 2500 µs excedia o datasheet (500–2400) e, com o alvo saturado em ANG_MAX, deixava o servo no batente interno. Relógio do laço: se um bloqueio (`gravaPose()` = 360 ms de delay) atrasar > 3 períodos, `tUltimo = agora` (antes "pagava" 18 ciclos em rajada = salto de 36°).
- Armadilha Arduino IDE: `struct Botao` precisa vir antes de qualquer função (a IDE gera protótipos no topo; `leBotao(Botao&)` falhava).
- Home = 90° em todas; limites {5,15,20,72}..{175,165,160,110}; garra: 74 = fechada (≈ 2 mm de vão), 110 = aberta (≈ 57 mm na raiz) — nominais, calibrar. Montar os horns com os servos em 90° (garra 75°); estriado de ~21 dentes → erro de indexação até ±8,6°, por isso ANG_MIN/MAX são sempre de bancada.
- Ombro além de ~45° com o antebraço para baixo leva a garra até 30 mm abaixo do plano da mesa: não há batente; documentado como limite do operador (alternativa: elevar a base 30 mm). Decisão do usuário, não corrigir em código sem pedir.

## Revisão de viabilidade (2026-09-19) — conclusões que não estão no código
- Veredito: executável. Antes da revisão, o braço de 3 GDL funcionava mas a garra travava (backlash negativo + GARRA_FECHADA 33° além do batente). Corrigido.
- Torque (corpo livre com massas do modelo): ombro 0,39 kgf·cm vazio (22 % do stall 1,8 a 5 V), 0,39 + 0,0185·m[g] com carga na ponta → carga útil ≈ 25 g estendido / ≈ 60 g recolhido. Cotovelo 39 % com 50 g. Estrutura FS > 60. SG90 e MG90S têm o MESMO torque a 5 V (2,2 do MG90S é a 6 V); MG90S vale pelo rolamento e engrenagem metálica.
- Estabilidade: disco Ø110 solto tomba com ≈ 15 g na garra (r_CoM = 55 mm = raio de apoio) → tábua de fixação OBRIGATÓRIA (BOM 14, lista item 9).
- Cabos: os 250 mm de fábrica não chegam de S3/S4 ao circuito → 2 extensores de 300 mm (BOM 15).
- Nunca alimentar o Arduino por USB e pela fonte no pino 5V ao mesmo tempo (nota 6 do esquema).
- Firmware compila em 36 % flash / 22 % RAM sem avisos; Servo usa Timer1 (D9/D10 sem analogWrite — irrelevante, D9 é servo).

## Pendências / ideias de revisão
- Possível melhoria: rolamento 623ZZ na base (as colunas de encosto já resolvem o balanço), mola de retorno no ombro, controle por Bluetooth (HC-05), cinemática inversa, gravação de trajetória contínua.
- Se furos ficarem apertados na A1: "X-Y hole compensation" 0,1 mm no Bambu Studio.

## Verificação
- STLs: malhas estanques (assert `is_watertight` no gerador) — OK em 2026-09-19.
- Firmware (versão joystick, limites revisados): compila sem avisos (`arduino-cli compile --fqbn arduino:avr:uno --warnings all`), 36 % flash / 22 % RAM — 2026-09-19.
- Geometria: varredura booleana cotovelo 0..180° (onset 165°), garra alfa −5..35° (contato −2,5°), colunas × conjunto girante em 18 poses extremas (0 mm³), engrenagens 361 posições (0 mm²) — 2026-09-19. arduino-cli instalado via winget em `C:\Program Files\Arduino CLI\`.
