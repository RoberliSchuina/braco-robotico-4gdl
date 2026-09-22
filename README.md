# Braço Robótico 4 GDL — Sistemas Embarcados (FAESA, 2026/2)

| Entrega | Onde está |
|---|---|
| Lista de componentes | `relatorio/Relatorio_Braco_Robotico.docx` (seção 4) |
| Peças 3D (uma por arquivo) + STL | `STL/01_…07_*.stl` (07 = suporte dos joysticks) — importar cada uma em um projeto do Tinkercad (Importar → STL) |
| Protótipo montado | `STL/montagem_completa.stl`, `imagens/montagem_*.png` |
| Código Arduino IDE | `firmware/braco_robotico/braco_robotico.ino` (placa UNO; libs Servo + EEPROM) |
| Esquema elétrico | `imagens/esquema_eletrico.png` |
| Guia de ligações furo a furo (protoboard) | `Circuito_Braco_Robotico.html` (autocontido; abrir no navegador ou imprimir) |
| Lista de parafusos e fixadores (à parte) | `relatorio/Lista_Parafusos_Fixadores.docx` (também Apêndice C do relatório) |
| Memória de desenvolvimento/revisão | `CLAUDE.md` |

Impressão (Bambu Lab A1): PLA, bico 0,4 mm, camada 0,20 mm, preenchimento 15 %, 3 paredes, sem suportes, peças já orientadas nos STL.

Regenerar tudo: `python cad/gerar_pecas.py && python cad/gerar_esquema.py && python relatorio/gerar_relatorio.py && python relatorio/gerar_lista_parafusos.py`
(requer `pip install trimesh manifold3d shapely numpy matplotlib python-docx`).

Comando: 2 módulos joystick KY-023 (J1 = base/ombro + botão gravar/reproduzir; J2 = garra/cotovelo + botão abre/fecha garra / home). Controle incremental com zona morta; ligar com os joysticks soltos (calibração do centro).

Firmware compilado com `arduino-cli compile --fqbn arduino:avr:uno` em 2026-09-19: 11 650 bytes de flash (36 %), 451 bytes de RAM (22 %), sem avisos.

Revisão de viabilidade (2026-09-19): geometria varrida por booleana em toda a faixa de movimento (zero colisões dentro dos limites do firmware), engrenagens da garra corrigidas (backlash 0,19 mm), limites de junta coerentes com a mecânica, base com colunas de encosto. A base **precisa** ser parafusada na tábua de apoio e S3/S4 precisam de extensores de cabo (BOM itens 14 e 15). Carga útil ≈ 25 g com o braço estendido.
