# Braço Robótico 4 GDL — memória de desenvolvimento e revisão

Projeto da disciplina Sistemas Embarcados (FAESA, Eng. da Computação, 2026/2). Enunciado em `Detalhes.txt`.
Entregas: BOM, peças 3D (Tinkercad, uma por arquivo) + STL, protótipo montado, código Arduino IDE, relatório .docx.

## Estado atual (2026-09-24)
- [x] 11 peças modeladas (CSG em Python/trimesh) e exportadas em `STL/` na orientação de impressão (9 do braço + 2 da garra alternativa)
- [x] 2026-09-24: **estrutura em forquilha** — cada elo tem 2 chapas laterais simétricas em relação ao plano de rotação da base (pedido do usuário: "duplique a estrutura lateral de modo a equilibrá-la")
- [x] 2026-09-24: **garra na palma** — engrenagens com eixo ao longo de X do antebraço: com o antebraço na horizontal os eixos ficam verticais e as mandíbulas fecham num plano horizontal (captura lateral)
- [x] 2026-09-24: berço dos joysticks refeito (cantos em L + rasgos radiais); ver "Suporte dos joysticks"
- [x] 2026-09-24: **segunda opção de garra** — dedos 10/11 com mandíbula em V (auto-centrante), troca direta com os dedos planos 07/08
- [x] Montagem (`STL/montagem_completa.stl`) + renders em `imagens/` (inclui `montagem_captura.png`)
- [x] Firmware `firmware/braco_robotico/braco_robotico.ino` (4 servos, 2 joysticks KY-023, gravar/reproduzir, serial, EEPROM)
- [x] 2026-09-19: potenciômetros + botão avulso substituídos por 2 joysticks KY-023
- [x] Esquema elétrico `imagens/esquema_eletrico.png` (eletrônica NÃO mudou na revisão de 2026-09-24)
- [x] 2026-09-26: **dimensionamento da fonte** — `cad/verificacao_eletrica.py` + seção 8.1 do relatório; fonte passou a 5 V / 5 A (ver "Elétrica")
- [x] 2026-09-21: repositório GitHub `RoberliSchuina/braco-robotico-4gdl` — público desde 2026-09-22 (remote `origin`, branch `main`); `gh` instalado em `C:\Program Files\GitHub CLI\` e autenticado
- [x] 2026-09-20: guia de ligações furo a furo `Circuito_Braco_Robotico.html` (SVG da protoboard + esquema PNG em base64 — regerar o PNG exige reembutir)
- [x] Relatório `relatorio/Relatorio_Braco_Robotico.docx` (gerado por `relatorio/gerar_relatorio.py`)
- [x] Lista de parafusos à parte: dados em `relatorio/parafusos.py` → `Lista_Parafusos_Fixadores.docx` + Apêndice C
- [x] `cad/verificacao.py`: varreduras de colisão, engrenagens, envelope e torque (rodar depois de qualquer mudança de cota)
- [ ] Importar cada STL em um projeto separado no Tinkercad e exportar de lá — passo manual
- [ ] Preencher nome do aluno/professor na capa do relatório; abrir no Word e aceitar "atualizar campos" (sumário)
- [ ] Imprimir, montar, calibrar `ANG_MIN/ANG_MAX` e registrar os testes na seção 9.3

## Regra: sincronizar com o GitHub
Toda alteração em arquivos deste diretório (fonte ou regenerados) deve terminar com `git add -A && git commit -m "..." && git push` para `RoberliSchuina/braco-robotico-4gdl` — pedido do usuário em 2026-09-21, autorização permanente (não perguntar). Se o push falhar, avisar.

## Como regenerar tudo
```bash
pip install trimesh manifold3d shapely numpy matplotlib python-docx
python cad/gerar_pecas.py        # ~3 min (renders são a parte lenta) -> STL/, imagens/, cad/pecas_info.json
python cad/verificacao.py        # ~4 min: colisões, engrenagens, envelope, torque
python cad/verificacao_eletrica.py   # ~1 s: consumo, fonte, capacitor, queda nos cabos
python cad/gerar_esquema.py      # -> imagens/esquema_eletrico.png
python relatorio/gerar_relatorio.py
python relatorio/gerar_lista_parafusos.py
```
Toda cota está em `cad/gerar_pecas.py`; alterar lá e regenerar (não editar STL manualmente).
Armadilha de ambiente: patches via `python - <<'EOF'` (heredoc) no Git Bash às vezes falham em casar strings com acento — escrever o script de patch em arquivo (Write) e executá-lo.

## Arquitetura mecânica (revisão 2026-09-24)
- **Forquilha**: cada elo = 2 chapas (motriz + livre) simétricas em y = 0. Faces internas em |y| = 18,8 (braço) e 33,6 (antebraço); o servo da junta fica entre as chapas com o flange na chapa **motriz** e o corpo para dentro da forquilha. O lado **livre** gira num **munhão Ø9 impresso na própria chapa**, que entra num mancal Ø9,4 passante (folga 0,4 mm). Não há parafuso no lado livre: quem prende axialmente é o parafuso central do horn (lado motriz) + a travessa.
- **Travessas**: `04_braco_livre` traz uma travessa integrada (x = −17..−13, z = 56..70) e `06_antebraco_livre` traz a **palma** (x = −14..−10, z = 48..78); ambas atravessam a forquilha e são aparafusadas na chapa motriz com 2 × M3 × 10 em furo-piloto Ø2,5 dentro de um reforço de 8 mm. **São elas que fecham a estrutura** — sem elas as chapas abrem e o munhão sai do mancal.
- **Plataforma com 2 paredes**: motriz em y = 4..8 (flange de S2 em y = 8) e livre em y = −14..−10 (mancal). A parede livre NÃO é simétrica à motriz porque o corpo do SG90 avança 15,9 mm abaixo do flange e termina em y = −7,9: a parede livre tem de ficar além disso (folga de 2,1 mm). As duas nervuras (x = −12..−8 e 18,6..22,6) ligam as duas paredes e o disco, formando um caixote; ficam fora do corpo do servo (x = −6,1..16,7).
- **Garra na palma**: eixos das engrenagens ao longo de X do antebraço, em y = ±12 (24 mm entre centros = m·N), z = 62. S4 é aparafusado na face **interna** da palma (x = −10) com o corpo saindo para fora (x até −25,9) e o horn para dentro (x = +2,8); as engrenagens ficam em x = 0,8..4,8, ou seja, ~11 mm abaixo da palma e livres por baixo (a borda inferior das chapas recua até x = 0 na ponta). As mandíbulas ficam 39 mm à frente da ponta das chapas.
- **Duas opções de garra (ferramenta intercambiável)**: 07/08 = mandíbula plana 10 × 12 (objetos prismáticos, 2 pontos de contato); 10/11 = mandíbula 10 × 17 com entalhe em V de ≈95° (apex 5 mm dentro da face, abertura 11 mm) — 4 pontos de contato, auto-centra cilindros e esferas. Como a garra fecha no plano horizontal, o sulco do V fica **vertical**: pega caneta, pilha e frasco em pé. Mesma engrenagem, mesmo bolso de horn, mesmo pino M3 e mesma distância entre centros → nada muda no antebraço, na palma, no servo ou no firmware (o ângulo de toque das mandíbulas é o mesmo, ≈ 72,5° no servo). Capacidade medida (maior cilindro tocado pelas duas mandíbulas): plana Ø4 a Ø58, V Ø10 a Ø53, conforme S4 vai de 75° a 110°. O corte do V e o prolongamento da mandíbula têm o mesmo volume (100 mm³) — as duas versões pesam igual.
- **Por que a garra é assim**: pedido do usuário ("captura na horizontal"). A versão anterior tinha as engrenagens no plano do braço (eixo Y) e pegava por cima com o antebraço apontando para baixo.
- **Ganho da forquilha**: cisalhamento duplo em todas as juntas, esforço lateral no estriado de nylon praticamente eliminado e centro de massa sobre o eixo da base (a garra ficou no plano do braço — sumiu o desalinhamento de 34 mm da versão anterior).
- **Custo da forquilha**: massa móvel de ≈ 39 g → ≈ 59 g; torque do ombro em vazio de 0,39 → 0,52 kgf·cm; carga útil de ≈ 25 g → ≈ 20 g em extensão máxima. Janelas nas 4 chapas e na palma recuperam parte disso. Não "engrossar" as peças sem refazer o cálculo de torque.

## Decisões de projeto (e porquê)
- **Tinkercad não tem API** → modelagem paramétrica em Python com a mesma lógica (sólidos/furos) e STL importável. O relatório (seção 6) traz a "receita" de primitivas de cada peça.
- **Junta = horn do servo em bolso de 2 mm + parafuso central** (sem rolamentos). O bolso NÃO é um rasgo reto: `bolso_horn_2d()` faz cubo Ø9,2 + tronco de cone Ø9,2→Ø5,4 por braço (`HORN_R_CUBO`/`HORN_R_PONTA`). Os furinhos Ø1,5 seguem uma grade típica — conferir com o horn comprado.
- **S1 sem mancal** → a base tem 4 colunas de encosto Ø9 em r=24,5, topo a 0,5 mm da plataforma (z=40,3). Verificado por booleana: zero interferência.
- **Eixo do SG90 é deslocado 5,3 mm do centro do corpo** → rasgos e furos do flange são assimétricos (constante `SV_DESLOC_EIXO`). Não "centralizar" o rasgo.
- **Empilhamento em Y**: parede motriz 4..8 → chapas do braço ±18,8..22,8 → chapas do antebraço ±33,6..37,6. `GAP_ELO = 10,8` (altura do horn 12,8 − bolso 2,0). Vãos internos: 37,6 mm (braço) e 67,2 mm (antebraço).
- **Limite do cotovelo**: dobrando o antebraço sobre o braço, a **palma encosta na parede da plataforma a 148°** (varredura booleana; no braço em si só toca a 160°). Firmware sai com 40..140 (simétrico, porque o sentido do servo só se conhece na calibração); depois de calibrar, o lado esticado pode ir a 20° e o dobrado nunca passa de 145°.
- **Pose abaixo da mesa**: com o ombro > 135° e o cotovelo dobrado, o antebraço desce abaixo do plano da mesa e toca o disco da base (0,1–1,5 cm³ nas poses extremas; a garra chega a 28 mm abaixo). Já existia na versão anterior. É limite do operador — corrigir em código (ANG_MAX[1] = 135) custa ~50 mm de alcance. **Decisão do usuário, não mexer sem pedir.**
- **Engrenagens 16 dentes m=1,5**, dentes trapezoidais, addendum encurtado 0,8·m (Ø ext. 26,4), flancos afinados 0,5°/lado → interpenetração 0,000 mm² em 361 posições, folga de flanco 0,19 mm (≈1,6° de backlash). Não "engrossar" o dente de volta. Dedo livre tem fase de meio dente (11,25°). Mandíbulas se tocam em alfa ≈ −2,5° (servo ≈ 72,5°). Pino = **M3×25 inox + nylock** com espaçador Ø9×10,8 integrado ao dedo livre (agora atravessa a palma).
- **Tolerâncias FDM**: rasgo do servo +0,4 mm; furos-piloto Ø1,7 (PA 2,0×8), Ø1,5 (PA 1,7×6 do horn) e **Ø2,5 (M3 autoatarraxante nas travessas)**; furo M3 passante Ø3,4; furo do parafuso central do horn Ø2,6; mancal do munhão Ø9,4 para munhão Ø9.
- **Parafusos**: kit do servo traz 2 PA 2,0×8. Parafuso central do horn = PA 2,0×6 + arruela M2 (medir a profundidade do furo cego do eixo antes de montar). Micro parafusos do horn (PA 1,7×6) não vêm no kit. **Novo: 4 × M3×10** (2 na travessa do braço, 2 na palma). Joysticks: M3×12 + arruela ampla Ø9 + porca.
- **Impressão**: PLA, 0,2 mm, 15 % infill, 3 paredes, **sem suportes**. As travessas/palma são impressas em pé sobre a chapa deitada (paredes verticais) e os munhões saem na vertical. Maior ponte 23 mm (teto do rasgo do servo na plataforma e na palma). Massa total ≈ 132 g ≈ 6,6 h (braço ≈ 93 g + controle 38 g).
- **Armadilha CSG**: sólidos que apenas **encostam** na chapa (travessa, palma, munhão) geram aresta não-manifold — o STL abre como "não estanque" mesmo com `is_watertight` passando em memória. Todos penetram 1 mm na chapa, e `exporta_peca()` recarrega o STL e refaz o assert.
- **Suporte dos joysticks** (`suporte_joysticks()`): silhueta 2D em shapely extrudada 4 mm; **nenhum datasheet publica a distância entre os furos do KY-023** (conferido em Joy-IT, Mantech, espboards, arduinomodules — todos só dão a placa 34 × 26 mm), e o gimbal (~22 × 22) cobre os furos do lado estreito em vários clones. Por isso a fixação não depende dessa cota: 4 **cantos em L** posicionam o módulo pela borda (envelope 34,6 × 26,6; assento 3 mm + lábio 2,2 mm) e 4 **rasgos radiais 3,4 × 11,4** aceitam furação de 21,5..34,5 × 15,4..24,6 mm (nominal 28 × 20). Não entra na `montagem()`; render próprio com `joystick_dummy()`.

## Firmware — fatos não óbvios
- Protoboard (guia HTML): só as trilhas da direita são usadas — + = 5 V da fonte (servos), − = GND comum; 5 V do Arduino para os joysticks vai pela linha 21. Sugestão de linhas: fonte 2/3, C1 4, GND Arduino 5, S1 6/7, S2 10/11, S3 14/15, S4 18/19, J1 GND 24, J2 GND 29.
- Pinos: servos D3/D5/D6/D9; J1: VRx→A0 (base), VRy→A1 (ombro), SW→D2; J2: VRx→A2 (garra), VRy→A3 (cotovelo), SW→D4; LED D13. `PIN_EIXO` está na ordem das juntas = {A0, A1, A3, A2}.
- Controle **incremental** (joystick = velocidade): zona morta ±60 counts, incremento = VEL_JOY·n², `SENTIDO[]` inverte eixo. Centro calibrado no setup e pelo comando `j`.
- Máquina de estados só MANUAL ↔ REPRODUZINDO. SW1 curto = grava pose (máx. 16); SW1 longo = reproduz/para. SW2 curto = abre/fecha garra (74↔110); SW2 longo = home. EEPROM assinatura 0xB4A1.
- `passoReproducao()` limita cada pose a ANG_MIN/MAX (pose fora da faixa congelava a reprodução).
- Rampa: `velMax` graus por passo de 20 ms. Servo.attach(pin, **600, 2400**). Se um bloqueio atrasar > 3 períodos, `tUltimo = agora`.
- Armadilha Arduino IDE: `struct Botao` precisa vir antes de qualquer função.
- Home = 90° em todas; limites **{5,15,40,72}..{175,165,140,110}**; garra: 74 = fechada, 110 = aberta. Montar os horns com os servos em 90° (garra 75°); estriado de ~21 dentes → erro de indexação até ±8,6°, por isso ANG_MIN/MAX são sempre de bancada.

## Revisão de viabilidade — conclusões que não estão no código
- Veredito: executável. Torque (corpo livre com as massas reais das malhas, MG90S = 13,4 g, SG90 = 9 g): ombro **0,52 kgf·cm vazio (29 % do stall 1,8 a 5 V)**; +25 g → 0,97 (54 %); +50 g → 1,43 (79 %). Cotovelo 39 % com 50 g. Carga útil ≈ **20 g estendido** (50 % do stall), ≈ 30 g a 60 %, ≈ 65 g com o braço recolhido.
- Envelope medido no modelo: altura máx. 249 mm; home = topo 165 mm e alcance 119 mm; alcance horizontal máx. **186 mm** (ombro 165°, cotovelo 20°).
- SG90 e MG90S têm o MESMO torque a 5 V (2,2 do MG90S é a 6 V); MG90S vale pelo rolamento e engrenagem metálica.
- Estabilidade: disco Ø110 solto tomba com pouca carga na garra → tábua de fixação OBRIGATÓRIA (BOM 14, lista item 9).
- Cabos: os 250 mm de fábrica não chegam de S3/S4 ao circuito → 2 extensores de 300 mm (BOM 15).
- Nunca alimentar o Arduino por USB e pela fonte no pino 5V ao mesmo tempo (nota 6 do esquema).

## Elétrica — dimensionamento da fonte (2026-09-26, `cad/verificacao_eletrica.py`)
- **O datasheet TowerPro do MG90S não publica corrente nenhuma** (só 13,4 g, 22,5×12×35,5, 1,8/2,2 kgf·cm, 0,1 s/60°, 4,8–6,0 V, banda morta 5 µs). Os valores usados são de medição de terceiros a 5 V: 10 mA parado, 120–250 mA em vazio, **700 mA travado (MG90S) / 650 mA (SG90)**. Não citar "corrente de datasheet" no relatório.
- Modelo: `I(T) = I0 + (I_stall − I0)·(T/T_stall)`, alimentado pelas frações de torque de `verificacao.py`. Resultados: repouso 0,47 A; manual 0,72–1,21 A; reprodução 4 eixos + 50 g **1,85 A (pior caso normal)**; **falha com os 4 travados 2,70 A**; pico de inversão de sentido ≈ 1,4 A por servo (fcem soma à tensão aplicada), ≈ 2,6 A no barramento.
- **Veredito: 3 A funciona** (62 % em operação, 90 % no travamento). Fonte especificada mudou para **5 V / 5 A** só por margem — decisão reversível, é trocar BOM 6 e os rótulos. Não subir para 6 V: stall vira ≈ 0,85 A/servo (3,4 A) e toda a análise de torque é para 1,8 kgf·cm a 5 V.
- **Capacitor não substitui corrente de fonte** (e vice-versa). C1 = 1000 µF com 0,2 V de queda guarda 0,2 mC = 2 A por 100 µs — cobre o degrau de µs/ms até a malha da fonte reagir. Cobrir 1 s de travamento exigiria ≈ 2 F. Acrescentado 100 nF cerâmico em cada servo (BOM 8).
- Orçamento de queda: 5,0 → 4,8 V = **200 mV**. 0,5 m de 22 AWG com 2 A já gasta 106 mV → usar 20 AWG ou mais grosso no trecho fonte → protoboard. Contato de protoboard aguenta ~1 A: alimentar a trilha por dois furos (ou borne parafusado) e espalhar os servos.
- Se o Arduino for alimentado pelo USB, afundar o barramento dos servos **não** reseta o MCU — só perde torque e dá jitter. O risco de reset só existe com o jumper da fonte no pino 5V.
- Firmware compila em 36 % flash / 22 % RAM sem avisos; Servo usa Timer1.

## Pendências / ideias de revisão
- Possível melhoria: rolamento 623ZZ na base, mola de retorno no ombro, Bluetooth (HC-05), cinemática inversa, gravação de trajetória contínua, trava de software para a pose "abaixo da mesa".
- Se furos ficarem apertados na A1: "X-Y hole compensation" 0,1 mm no Bambu Studio.

## Verificação (2026-09-24, `python cad/verificacao.py`)
- STLs: 11 malhas estanques, conferidas **depois de exportadas** (o assert em memória não pega aresta não-manifold).
- Colisões: cotovelo × braço → primeiro contato em 160°; antebraço (palma) × plataforma → 148°; dentro de 20..140° do cotovelo e ±75° do ombro, a única interferência é a pose abaixo da mesa (antebraço × disco da base).
- Engrenagens: interpenetração 0,0000 mm² e folga de flanco 0,190 mm em 361 posições.
- Firmware: compila sem avisos (`arduino-cli compile --fqbn arduino:avr:uno --warnings all`), 36 % flash / 22 % RAM. arduino-cli em `C:\Program Files\Arduino CLI\`.
