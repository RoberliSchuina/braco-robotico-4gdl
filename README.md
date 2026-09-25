# Braço Robótico 4 GDL — Sistemas Embarcados (FAESA, 2026/2)

| Entrega | Onde está |
|---|---|
| Lista de componentes | `relatorio/Relatorio_Braco_Robotico.docx` (seção 4) |
| Peças 3D (uma por arquivo) + STL | `STL/01_…09_*.stl` (09 = suporte dos joysticks) — importar cada uma em um projeto do Tinkercad (Importar → STL) |
| Protótipo montado | `STL/montagem_completa.stl`, `imagens/montagem_*.png` |
| Código Arduino IDE | `firmware/braco_robotico/braco_robotico.ino` (placa UNO; libs Servo + EEPROM) |
| Esquema elétrico | `imagens/esquema_eletrico.png` |
| Guia de ligações furo a furo (protoboard) | `Circuito_Braco_Robotico.html` (autocontido; abrir no navegador ou imprimir) |
| Lista de parafusos e fixadores (à parte) | `relatorio/Lista_Parafusos_Fixadores.docx` (também Apêndice C do relatório) |
| Memória de desenvolvimento/revisão | `CLAUDE.md` |

Impressão (Bambu Lab A1): PLA, bico 0,4 mm, camada 0,20 mm, preenchimento 15 %, 3 paredes, sem suportes, peças já orientadas nos STL (≈ 132 g, ≈ 6,6 h).

**Revisão de 2026-09-24 — estrutura em forquilha e garra horizontal.** Cada elo passou a ter duas chapas laterais simétricas em relação ao plano de rotação da base (03/04 = braço, 05/06 = antebraço), amarradas por uma travessa aparafusada; o servo trabalha entre elas e o lado oposto gira num munhão Ø9 impresso, em cisalhamento duplo. A garra foi para baixo da palma, com as engrenagens de eixo vertical: com o antebraço na horizontal as mandíbulas fecham num plano horizontal e o braço agarra o objeto pelos lados (captura na horizontal). O suporte dos joysticks ganhou berço de cantos em L e rasgos radiais, porque a furação do KY-023 não é padronizada.

Regenerar tudo: `python cad/gerar_pecas.py && python cad/gerar_esquema.py && python relatorio/gerar_relatorio.py && python relatorio/gerar_lista_parafusos.py`\nConferir a mecânica (colisões, engrenagens, envelope e torque): `python cad/verificacao.py`
(requer `pip install trimesh manifold3d shapely numpy matplotlib python-docx`).

Comando: 2 módulos joystick KY-023 (J1 = base/ombro + botão gravar/reproduzir; J2 = garra/cotovelo + botão abre/fecha garra / home). Controle incremental com zona morta; ligar com os joysticks soltos (calibração do centro).

Firmware compilado com `arduino-cli compile --fqbn arduino:avr:uno` em 2026-09-19: 11 650 bytes de flash (36 %), 451 bytes de RAM (22 %), sem avisos.

Verificação (2026-09-24, `python cad/verificacao.py`): 9 malhas estanques conferidas depois de exportadas; varredura booleana do cotovelo (palma encosta na plataforma a 148° → firmware limitado a 40..140°) e do ombro; engrenagens com interpenetração 0,0000 mm² e folga de flanco 0,190 mm; envelope medido no modelo (alcance 186 mm, altura 249 mm); torque do ombro 0,52 kgf·cm em vazio (29 % do travamento) e carga útil ≈ 20 g estendido / ≈ 65 g recolhido. A base **precisa** ser parafusada na tábua de apoio e S3/S4 precisam de extensores de cabo (BOM itens 14 e 15). Limite de operação: com o ombro além de 135° e o cotovelo dobrado, o antebraço desce abaixo do plano da mesa e toca o disco da base.
