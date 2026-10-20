/*
 * ============================================================================
 *  BRAÇO ROBÓTICO 4 GDL — Sistemas Embarcados (FAESA – Engenharia da Computação)
 *  Plataforma: Arduino UNO R3 (ATmega328P) — Arduino IDE 2.x
 *              (compila também para Nano, Mega 2560 e UNO R4 Minima/WiFi sem alterações)
 *  Atuadores : 4 micro-servos SG90/MG90S  (base, ombro, cotovelo, garra)
 *  Comando   : 2 módulos joystick analógico KY-023 (2 eixos + botão cada)
 *  Bibliotecas: Servo.h e EEPROM.h (já vêm com a Arduino IDE — não é preciso instalar nada)
 * ----------------------------------------------------------------------------
 *  MAPA DE PINOS
 *    D3  -> sinal servo S1 (base)          JOYSTICK 1:  VRx -> A0 (base)
 *    D5  -> sinal servo S2 (ombro)                      VRy -> A1 (ombro)
 *    D6  -> sinal servo S3 (cotovelo)                   SW  -> D2 (gravar / reproduzir)
 *    D9  -> sinal servo S4 (garra)         JOYSTICK 2:  VRx -> A2 (garra)
 *    D13 -> LED de status (LED da placa)                VRy -> A3 (cotovelo)
 *                                                       SW  -> D4 (volta a referencia; longo = garra)
 *    Joysticks: +5V e GND do Arduino. Servos: fonte externa 5 V / 5 A (GND comum!)
 * ----------------------------------------------------------------------------
 *  CONTROLE
 *    O joystick volta sozinho ao centro, por isso o comando é INCREMENTAL (velocidade):
 *    inclinar o eixo move a junta na direção correspondente, tanto mais rápido quanto
 *    maior a inclinação (curva quadrática para precisão perto do centro); soltar = para.
 *    O centro de cada eixo é calibrado na partida (não toque nos joysticks ao ligar).
 *    Um eixo que na partida não lê perto do meio da faixa (alavanca inclinada, fio solto, módulo sem
 *    +5V) é DESATIVADO e avisado no Monitor Serial — sem isso a junta correria sozinha até o limite.
 *  MODOS
 *    MANUAL      : joysticks comandam as juntas.
 *    REPRODUZINDO: percorre ciclicamente as poses gravadas (até 16).
 *  BOTÕES
 *    SW1 curto = grava a pose atual      SW1 longo (> 0,8 s) = inicia/para a reprodução
 *    SW2 curto = VOLTA À POSIÇÃO DE REFERÊNCIA (POS_REF, todas as juntas em 90°)
 *    SW2 longo (> 0,8 s) = abre/fecha a garra
 *    (garra: 74° ≈ fechada, 110° = aberta — valores nominais, calibrar; os dedos se tocam em ~72,5°)
 *    A garra é montada sob a palma, com as engrenagens de eixo vertical: com o antebraço na horizontal as
 *    mandíbulas fecham num PLANO HORIZONTAL (o braço agarra o objeto pelos lados, apoiado na mesa).
 *    Há dois pares de dedos intercambiáveis (mandíbula plana e mandíbula em V, auto-centrante para
 *    cilindros e esferas em pé). Os dois têm o mesmo ângulo de toque, então nada muda aqui na troca.
 *  COMANDOS SERIAIS (115200 bps, qualquer opção de fim de linha) — calibração e depuração:
 *    p  imprime posições      g  grava pose        l  limpa poses       r  reproduz/para
 *    m  manual (para)         h  pos. de referência a  abre/fecha garra  j  recalibra centro dos joysticks
 *    e  salva poses na EEPROM c  carrega da EEPROM v <n> velocidade máx. (1..10 °/passo)
 *    s <j> <ang>  move a junta j (0..3) para <ang> graus
 *    d  diagnóstico liga/desliga (leituras cruas dos joysticks, botões e tensão da placa a cada 0,5 s)
 *    ?  lista os comandos
 * ----------------------------------------------------------------------------
 *  REVISÃO 2026-10-20 (mesmos pinos, botões, comandos, limites e formato da EEPROM da versão anterior)
 *    - constante do LED renomeada para PIN_LED_STATUS: no UNO R4 (e em outras placas) PIN_LED já é uma
 *      macro da própria placa e a linha "const uint8_t PIN_LED = 13;" não compilava
 *    - servos escritos ANTES do attach (o 1º pulso já sai na referência) e joysticks calibrados só
 *      depois que os servos param (a corrente de partida não entra na leitura do centro)
 *    - calibração confere cada eixo: centro fora de 512 ± 150 ou leitura instável -> eixo desativado + aviso
 *    - debounce dos botões por estabilidade (25 ms) e piscar do LED sem delay()
 *    - leitura serial sem String e sem bloqueio; aceita "Nenhum final de linha", NL, CR ou NL e CR
 *    - comandos 'd' (diagnóstico) e '?' (ajuda); a lista de comandos aparece na partida
 *    - pulso escrito em microssegundos (passo de 0,1° em vez de 1°: movimento lento sem "degraus")
 *    - reprodução protegida contra lista de poses vazia/encurtada; pose gravada com arredondamento
 * ============================================================================
 */
#include <Servo.h>
#include <EEPROM.h>

// ------------------------------------------------------------ configuração
const uint8_t  N_JUNTAS       = 4;
const uint8_t  PIN_SW1        = 2;      // botão do joystick 1
const uint8_t  PIN_SW2        = 4;      // botão do joystick 2
const uint8_t  PIN_LED_STATUS = 13;     // LED da placa (D13)
const uint32_t SERIAL_BPS     = 115200; // configure o Monitor Serial com a MESMA velocidade
const uint16_t PERIODO_MS     = 20;     // período do laço de controle (50 Hz = período do PWM dos servos)
const uint16_t TOQUE_LONGO_MS = 800;
const uint16_t DEBOUNCE_MS    = 25;     // o contato do botão precisa ficar estável esse tempo
const uint8_t  MAX_POSES      = 16;
const uint16_t PAUSA_POSE_MS  = 500;    // parada em cada pose durante a reprodução
const uint16_t EEPROM_MAGIC   = 0xB4A1; // assinatura para validar dados na EEPROM
const int      ZONA_MORTA     = 60;     // counts do ADC (~6 %) ignorados em torno do centro do joystick
const float    VEL_JOY        = 2.0f;   // graus por passo com o joystick no fim de curso (2 °/20 ms = 100 °/s)
const int      CENTRO_TOL     = 150;    // na calibração o centro tem de cair em 512 ± 150 counts...
const int      RUIDO_MAX      = 40;     // ...e as 16 leituras não podem variar mais que isso (pino solto "flutua")
const uint16_t PULSO_MIN_US   = 600;    // pulso de 0°   (SG90/MG90S aceitam 500..2400 µs; 2500 forçava o batente)
const uint16_t PULSO_MAX_US   = 2400;   // pulso de 180°

// limites mecânicos (graus do servo) — AJUSTE NA CALIBRAÇÃO (seção 9 do relatório). Valores nominais:
//   base     : 5..175 — nunca 0/180 (extremos da faixa de pulso = batente interno do servo, zumbido e aquecimento)
//   ombro    : 15..165 — com o ombro > ~45° e o antebraço apontando para baixo a garra passa do plano da mesa:
//              não há batente mecânico, o operador (ou a base elevada) evita
//   cotovelo : 40..140 — dobrando o antebraço sobre o braço, a PALMA da garra encosta na parede da plataforma
//              a partir de 148° (varredura booleana; no braço em si só toca a 160°). Como o sentido do servo só
//              se conhece na calibração, o limite é simétrico: depois de calibrar, o lado "esticado" pode ir a
//              20° e o lado "dobrado" NUNCA deve passar de 145°
//   garra    : 72..110 — as mandíbulas se tocam em ~72,5° (horn montado a 75° = dedos paralelos); abaixo disso
//              o servo fica em travamento (stall) permanente
//                                   base   ombro  cotovelo garra
const uint8_t ANG_MIN[N_JUNTAS]  = {   5,    15,    40,    72 };
const uint8_t ANG_MAX[N_JUNTAS]  = { 175,   165,   140,   110 };

// POSIÇÃO DE REFERÊNCIA (pose de repouso, também chamada de "home"): é onde o braço é inicializado no
// setup() e para onde ele volta sempre que se aperta o botão do joystick 2 (toque curto) ou se envia 'h'.
// Todas as juntas em 90°, o meio da faixa útil de cada servo, porque:
//   base     90° : centro do curso (5..175) -> mesmo alcance para os dois lados
//   ombro    90° : braço na VERTICAL -> braço de alavanca ~0 e torque mínimo no servo mais carregado
//   cotovelo 90° : antebraço perpendicular ao braço -> longe dos 148° em que a palma encosta na
//                  plataforma e longe do fim de curso esticado
//   garra    90° : meio curso (74..110), ~30 mm de vão -> não aperta o objeto nem fecha contra si mesma
// É também a pose em que os horns dos servos são encaixados na montagem (manual de montagem, etapa 7):
// mudar estes valores obriga a remontar os horns, não é só mexer no código.
// Nesta pose o modelo mede 165 mm de altura e 119 mm de alcance horizontal (cad/mapa_angulos.json).
const uint8_t POS_REF[N_JUNTAS]  = {  90,    90,    90,    90 };
const uint8_t PIN_SERVO[N_JUNTAS] = { 3, 5, 6, 9 };
const uint8_t PIN_EIXO[N_JUNTAS]  = { A0, A1, A3, A2 };   // J1-VRx, J1-VRy, J2-VRy, J2-VRx
const int8_t  SENTIDO[N_JUNTAS]   = { 1, 1, 1, 1 };       // troque para -1 para inverter o sentido de um eixo
const char*   NOME[N_JUNTAS]      = { "base", "ombro", "cotovelo", "garra" };
const char*   NOME_EIXO[N_JUNTAS] = { "A0 (J1-VRx)", "A1 (J1-VRy)", "A3 (J2-VRy)", "A2 (J2-VRx)" };
const uint8_t GARRA = 3;
const uint8_t GARRA_FECHADA = 74, GARRA_ABERTA = 110;   // 74 ≈ 2 mm de vão; 110 ≈ 57 mm. Calibrar (seção 9.3)

// ------------------------------------------------------------ tipos e estado
// (todos os tipos vêm antes da primeira função: a Arduino IDE gera os protótipos no topo do arquivo)
enum Modo : uint8_t { MANUAL, REPRODUZINDO };

struct Botao {
  uint8_t  pino;
  bool     bruto;            // última leitura crua (true = apertado)
  bool     estavel;          // estado depois do debounce
  bool     longoDisparado;   // o toque longo já foi tratado neste aperto
  uint32_t tMudanca;         // instante da última mudança da leitura crua
  uint32_t tInicio;          // instante em que o aperto (já filtrado) começou
};

Servo   servo[N_JUNTAS];
float   posAtual[N_JUNTAS];             // posição comandada (graus, com casas decimais para suavizar)
float   alvo[N_JUNTAS];                 // posição desejada
int     centro[N_JUNTAS];               // leitura do ADC com o joystick em repouso (calibrada na partida)
bool    eixoAtivo[N_JUNTAS];            // false = eixo reprovado na calibração (ignorado até o próximo 'j')
float   velMax = 3.0f;                  // graus por passo (3 °/20 ms = 150 °/s) — usado em referência / reprodução / comando s
Modo    modo   = MANUAL;

uint8_t  poses[MAX_POSES][N_JUNTAS];
uint8_t  nPoses = 0;
uint8_t  poseAtual = 0;
uint32_t tPausaPose = 0;                // != 0: chegou na pose e está parado nela desde esse instante

Botao sw1 = { PIN_SW1, false, false, false, 0, 0 }, sw2 = { PIN_SW2, false, false, false, 0, 0 };

uint8_t  piscadasLed = 0;               // meias-piscadas que faltam (confirmação de pose gravada)
uint32_t tPiscaLed = 0;

char     linha[32];                     // comando serial em montagem
uint8_t  nLinha = 0;
uint32_t tUltimoCaractere = 0;

bool     diagnostico = false;
uint32_t tDiagnostico = 0;

// ------------------------------------------------------------ utilidades
static float limita(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

// graus (com fração) -> microssegundos; mesma escala do Servo.write() com attach(pino, 600, 2400)
void escreveServo(uint8_t j) {
  float us = PULSO_MIN_US + posAtual[j] * ((PULSO_MAX_US - PULSO_MIN_US) / 180.0f);
  servo[j].writeMicroseconds((int)(us + 0.5f));
}

void aplicaServos() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) escreveServo(j);
}

// aproxima posAtual de alvo respeitando a velocidade máxima -> movimentos suaves, sem "trancos"
bool avancaParaAlvo() {
  bool chegou = true;
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    float d = alvo[j] - posAtual[j];
    if (fabs(d) > velMax) { posAtual[j] += (d > 0 ? velMax : -velMax); chegou = false; }
    else                  { posAtual[j] = alvo[j]; }
    posAtual[j] = limita(posAtual[j], ANG_MIN[j], ANG_MAX[j]);
  }
  aplicaServos();
  return chegou;
}

// lê 16 amostras de cada eixo com os joysticks soltos; reprova o eixo cujo "centro" não está no meio da
// faixa (alavanca inclinada ao ligar, fio solto/trocado, módulo sem +5V/GND) ou cuja leitura oscila (pino
// analógico sem nada ligado). Eixo reprovado fica parado: é melhor do que a junta disparar sozinha.
void calibraJoysticks() {
  uint8_t reprovados = 0;
  Serial.print(F("Centro dos joysticks:"));
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    long soma = 0; int menor = 1023, maior = 0;
    for (uint8_t k = 0; k < 16; k++) {
      int v = analogRead(PIN_EIXO[j]);
      soma += v;
      if (v < menor) menor = v;
      if (v > maior) maior = v;
      delay(2);
    }
    centro[j] = soma / 16;
    int desvio = centro[j] - 512;
    eixoAtivo[j] = (desvio >= -CENTRO_TOL && desvio <= CENTRO_TOL && maior - menor <= RUIDO_MAX);
    if (!eixoAtivo[j]) reprovados++;
    Serial.print(' '); Serial.print(centro[j]);
    if (!eixoAtivo[j]) Serial.print(F("(DESATIVADO)"));
  }
  Serial.println();
  if (!reprovados) return;
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    if (eixoAtivo[j]) continue;
    Serial.print(F("ATENCAO: eixo ")); Serial.print(NOME_EIXO[j]); Serial.print(F(" -> ")); Serial.print(NOME[j]);
    Serial.print(F(" leu ")); Serial.print(centro[j]); Serial.println(F(" (esperado ~512). Eixo desativado."));
  }
  Serial.println(F("  Causas: alavanca inclinada ao ligar, fio solto/trocado ou joystick sem +5V/GND."));
  Serial.println(F("  Solte os joysticks e envie 'j' para recalibrar; 'd' mostra as leituras cruas."));
}

// controle incremental: deflexão do joystick -> incremento de ângulo por passo
void leJoysticks() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    if (!eixoAtivo[j]) continue;
    int d = analogRead(PIN_EIXO[j]) - centro[j];                       // ~-512..+511 em torno do centro
    int ad = d < 0 ? -d : d;
    if (ad < ZONA_MORTA) continue;                                     // dentro da zona morta: não move
    float n = (ad - ZONA_MORTA) / (512.0f - ZONA_MORTA);               // 0..1
    n = limita(n, 0.0f, 1.0f);
    float inc = VEL_JOY * n * n * (d > 0 ? 1 : -1) * SENTIDO[j];       // curva quadrática: fino perto do centro
    alvo[j] = limita(alvo[j] + inc, ANG_MIN[j], ANG_MAX[j]);
  }
}

void imprimePosicoes() {
  Serial.print(F("modo=")); Serial.print(modo == MANUAL ? F("MANUAL") : F("REPRODUZINDO"));
  Serial.print(F(" poses=")); Serial.print(nPoses);
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    Serial.print(F("  ")); Serial.print(NOME[j]); Serial.print('='); Serial.print((int)(posAtual[j] + 0.5f));
  }
  Serial.println();
}

void imprimeAjuda() {
  Serial.println(F("Comandos (Monitor Serial a 115200, qualquer fim de linha):"));
  Serial.println(F("  p  posicoes          g  grava pose         l  limpa poses        r  reproduz/para"));
  Serial.println(F("  m  modo manual       h  pos. referencia    a  abre/fecha garra   j  recalibra joysticks"));
  Serial.println(F("  e  salva na EEPROM   c  carrega da EEPROM  d  diagnostico on/off ?  esta ajuda"));
  Serial.println(F("  v <1..10>  velocidade maxima (graus/20 ms)    s <junta 0..3> <angulo>  move uma junta"));
  Serial.println(F("Botoes: SW1 curto = grava | SW1 longo = reproduz/para | SW2 curto = referencia | SW2 longo = garra"));
}

// tensão de alimentação do próprio Arduino, medida contra a referência interna de 1,1 V (±10 %).
// Se ela afunda quando os servos se mexem, os servos estão puxando corrente da placa: confira a fonte externa
// e o GND comum. Só nos AVR clássicos (UNO, Nano, Mega); nas outras placas devolve 0 (não medido).
long leVccMilivolts() {
#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__) || defined(__AVR_ATmega2560__) || \
    defined(__AVR_ATmega1280__) || defined(__AVR_ATmega32U4__)
#if defined(MUX5)                                              // Mega / Leonardo: canal da referência = 011110
  ADCSRB &= ~_BV(MUX5);
  ADMUX = _BV(REFS0) | _BV(MUX4) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
#else                                                          // UNO / Nano: canal da referência = 1110
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
#endif
  delay(2);                                                    // a referência de 1,1 V precisa assentar
  ADCSRA |= _BV(ADSC);
  while (ADCSRA & _BV(ADSC)) {}
  uint16_t adc = ADC;
  return adc ? 1125300L / adc : 0;                             // 1,1 V × 1023 × 1000
#else
  return 0;
#endif
}

void imprimeDiagnostico() {
  if (millis() - tDiagnostico < 500) return;
  tDiagnostico = millis();
  Serial.print(F("diag:"));
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    Serial.print(' '); Serial.print(NOME[j]); Serial.print('['); Serial.print(NOME_EIXO[j][0]); Serial.print(NOME_EIXO[j][1]);
    Serial.print(F("]=")); Serial.print(analogRead(PIN_EIXO[j]));
    Serial.print('/'); Serial.print(centro[j]);
    if (!eixoAtivo[j]) Serial.print(F("(OFF)"));
  }
  Serial.print(F("  SW1=")); Serial.print(digitalRead(PIN_SW1) == LOW ? F("apertado") : F("solto"));
  Serial.print(F(" SW2=")); Serial.print(digitalRead(PIN_SW2) == LOW ? F("apertado") : F("solto"));
  long vcc = leVccMilivolts();
  if (vcc) { Serial.print(F("  Vcc~")); Serial.print(vcc / 1000.0, 2); Serial.print('V'); }
  Serial.println();
}

void piscaLed(uint8_t vezes) { piscadasLed = 2 * vezes; tPiscaLed = millis(); }

// LED: aceso = MANUAL, piscando = REPRODUZINDO; pisca rápido 3× ao gravar uma pose
void atualizaLed() {
  if (piscadasLed) {
    if (millis() - tPiscaLed >= 60) { tPiscaLed = millis(); piscadasLed--; }
    digitalWrite(PIN_LED_STATUS, (piscadasLed & 1) ? LOW : HIGH);
  } else if (modo == REPRODUZINDO) {
    digitalWrite(PIN_LED_STATUS, ((millis() / 250) % 2) ? HIGH : LOW);
  } else {
    digitalWrite(PIN_LED_STATUS, HIGH);
  }
}

void gravaPose() {
  if (nPoses >= MAX_POSES) { Serial.println(F("Memoria de poses cheia (16).")); return; }
  for (uint8_t j = 0; j < N_JUNTAS; j++) poses[nPoses][j] = (uint8_t)(posAtual[j] + 0.5f);
  nPoses++;
  Serial.print(F("Pose gravada #")); Serial.println(nPoses);
  piscaLed(3);
}

void iniciaReproducao() {
  if (nPoses == 0) { Serial.println(F("Nenhuma pose gravada.")); return; }
  modo = REPRODUZINDO; poseAtual = 0; tPausaPose = 0;
  Serial.println(F("Reproduzindo sequencia (SW1 longo, 'r' ou 'm' para parar)."));
}

void pararReproducao() {
  modo = MANUAL;
  for (uint8_t j = 0; j < N_JUNTAS; j++) alvo[j] = posAtual[j];         // joysticks continuam de onde parou
  Serial.println(F("Reproducao parada. Modo MANUAL."));
}

// volta todas as juntas para a posição de referência, no mesmo ritmo controlado da reprodução
// (velMax graus por passo). limita() protege contra uma POS_REF editada fora dos limites calibrados.
void vaiParaReferencia() {
  modo = MANUAL;
  for (uint8_t j = 0; j < N_JUNTAS; j++) alvo[j] = limita(POS_REF[j], ANG_MIN[j], ANG_MAX[j]);
  Serial.print(F("Voltando para a posicao de referencia:"));
  for (uint8_t j = 0; j < N_JUNTAS; j++) { Serial.print(' '); Serial.print((int)alvo[j]); }
  Serial.println(F(" graus."));
}

void alternaGarra() {
  if (modo == REPRODUZINDO) pararReproducao();                  // senão a reprodução sobrescreve o alvo
  bool aberta = alvo[GARRA] > (GARRA_FECHADA + GARRA_ABERTA) / 2;
  alvo[GARRA] = aberta ? GARRA_FECHADA : GARRA_ABERTA;
  Serial.println(aberta ? F("Garra: fechando") : F("Garra: abrindo"));
}

// ------------------------------------------------------------ EEPROM (poses persistentes)
// formato: assinatura (2 bytes) | nPoses (1 byte) | nPoses × 4 ângulos — o mesmo da versão anterior
void salvaEEPROM() {
  int a = 0;
  EEPROM.put(a, EEPROM_MAGIC); a += sizeof(EEPROM_MAGIC);
  EEPROM.put(a, nPoses);       a += sizeof(nPoses);
  for (uint8_t i = 0; i < nPoses; i++)
    for (uint8_t j = 0; j < N_JUNTAS; j++) EEPROM.update(a++, poses[i][j]);
  Serial.print(F("Salvo na EEPROM: ")); Serial.print(nPoses); Serial.println(F(" poses."));
}

bool carregaEEPROM() {
  int a = 0; uint16_t magic; uint8_t n;
  EEPROM.get(a, magic); a += sizeof(magic);
  if (magic != EEPROM_MAGIC) return false;
  EEPROM.get(a, n); a += sizeof(n);
  if (n > MAX_POSES) return false;
  for (uint8_t i = 0; i < n; i++)
    for (uint8_t j = 0; j < N_JUNTAS; j++) poses[i][j] = EEPROM.read(a++);
  nPoses = n;
  Serial.print(F("EEPROM: ")); Serial.print(nPoses); Serial.println(F(" poses carregadas."));
  return true;
}

// ------------------------------------------------------------ botões (toque curto / longo, com debounce)
// retorna 1 = toque curto (ao soltar), 2 = toque longo (ao completar 0,8 s apertado), 0 = nada
uint8_t leBotao(Botao &b) {
  uint32_t agora = millis();
  bool leitura = (digitalRead(b.pino) == LOW);                 // INPUT_PULLUP: apertado = LOW
  if (leitura != b.bruto) { b.bruto = leitura; b.tMudanca = agora; }
  if (b.bruto != b.estavel && agora - b.tMudanca >= DEBOUNCE_MS) {
    b.estavel = b.bruto;
    if (b.estavel) { b.tInicio = agora; b.longoDisparado = false; }
    else if (!b.longoDisparado) return 1;
  }
  if (b.estavel && !b.longoDisparado && agora - b.tInicio >= TOQUE_LONGO_MS) {
    b.longoDisparado = true; return 2;
  }
  return 0;
}

void trataBotoes() {
  uint8_t e1 = leBotao(sw1), e2 = leBotao(sw2);
  if (e1 == 2)      { if (modo == REPRODUZINDO) pararReproducao(); else iniciaReproducao(); }
  else if (e1 == 1) { if (modo == REPRODUZINDO) pararReproducao(); else gravaPose(); }
  // toque curto no botão do joystick 2 = volta à posição de referência (vaiParaReferencia() já devolve
  // o modo para MANUAL, por isso não precisa de pararReproducao() antes)
  if (e2 == 1)      vaiParaReferencia();
  else if (e2 == 2) alternaGarra();
}

// ------------------------------------------------------------ comandos seriais
// lê um número inteiro a partir de *p (pula espaços); devolve false se não houver número
bool leInteiro(char *&p, long &valor) {
  char *fim;
  valor = strtol(p, &fim, 10);
  if (fim == p) return false;
  p = fim;
  return true;
}

void executaComando() {
  linha[nLinha] = '\0';
  nLinha = 0;
  char *p = linha;
  while (*p == ' ' || *p == '\t') p++;
  if (*p == '\0') return;
  char c = *p++;
  if (c >= 'A' && c <= 'Z') c += 'a' - 'A';                    // aceita maiúsculas
  long a, b;
  switch (c) {
    case 'p': imprimePosicoes(); break;
    case 'g': gravaPose(); break;
    case 'l': nPoses = 0; if (modo == REPRODUZINDO) pararReproducao(); Serial.println(F("Poses apagadas.")); break;
    case 'r': if (modo == REPRODUZINDO) pararReproducao(); else iniciaReproducao(); break;
    case 'm': if (modo == REPRODUZINDO) pararReproducao(); else Serial.println(F("Modo MANUAL (joysticks).")); break;
    case 'h': vaiParaReferencia(); break;
    case 'a': alternaGarra(); break;
    case 'j': calibraJoysticks(); break;
    case 'e': salvaEEPROM(); break;
    case 'c': if (!carregaEEPROM()) Serial.println(F("EEPROM sem dados validos.")); break;
    case 'd':
      diagnostico = !diagnostico; tDiagnostico = 0;
      Serial.println(diagnostico ? F("Diagnostico LIGADO (eixo=leitura/centro). 'd' desliga.") : F("Diagnostico desligado."));
      break;
    case 'v':
      if (leInteiro(p, a) && a >= 1 && a <= 10) velMax = a;
      else Serial.println(F("Uso: v <1..10>"));
      Serial.print(F("velMax=")); Serial.println(velMax);
      break;
    case 's':                                                  // s <junta> <angulo>
      if (leInteiro(p, a) && leInteiro(p, b) && a >= 0 && a < N_JUNTAS && b >= 0 && b <= 180) {
        if (modo == REPRODUZINDO) pararReproducao();
        alvo[a] = limita(b, ANG_MIN[a], ANG_MAX[a]);
        Serial.print(NOME[a]); Serial.print(F(" -> ")); Serial.print((int)alvo[a]);
        if (alvo[a] != b) { Serial.print(F(" (limitado a ")); Serial.print(ANG_MIN[a]); Serial.print(F("..")); Serial.print(ANG_MAX[a]); Serial.print(')'); }
        Serial.println();
      } else Serial.println(F("Uso: s <junta 0..3> <angulo 0..180>   ex.: s 3 75"));
      break;
    case '?': imprimeAjuda(); break;
    default: Serial.print(F("Comando desconhecido: ")); Serial.println(c); imprimeAjuda();
  }
}

// junta os caracteres até o fim de linha (NL ou CR). Com o Monitor Serial em "Nenhum final de linha" o
// comando é executado quando a serial fica 100 ms em silêncio. Não bloqueia o laço de controle.
void trataSerial() {
  while (Serial.available()) {
    char ch = Serial.read();
    tUltimoCaractere = millis();
    if (ch == '\n' || ch == '\r') { executaComando(); continue; }
    if (nLinha < sizeof(linha) - 1) linha[nLinha++] = ch;
  }
  if (nLinha && millis() - tUltimoCaractere > 100) executaComando();
}

// ------------------------------------------------------------ reprodução de sequência
void passoReproducao() {
  if (nPoses == 0) { pararReproducao(); return; }
  if (tPausaPose) {                                            // parado na pose por PAUSA_POSE_MS
    if (millis() - tPausaPose < PAUSA_POSE_MS) return;
    tPausaPose = 0;
    poseAtual++;
  }
  if (poseAtual >= nPoses) poseAtual = 0;                      // fim da lista (ou lista recarregada mais curta)
  // limita a pose aos limites atuais: uma pose gravada antes de recalibrar ANG_MIN/ANG_MAX (ou lida de uma
  // EEPROM antiga) deixaria alvo fora da faixa e avancaParaAlvo() nunca "chegaria" -> reprodução congelada
  for (uint8_t j = 0; j < N_JUNTAS; j++) alvo[j] = limita(poses[poseAtual][j], ANG_MIN[j], ANG_MAX[j]);
  if (avancaParaAlvo()) tPausaPose = millis();
}

// ------------------------------------------------------------ setup / loop
void setup() {
  Serial.begin(SERIAL_BPS);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 2000) {}                   // placas com USB nativo (UNO R4, Leonardo)
  pinMode(PIN_SW1, INPUT_PULLUP);
  pinMode(PIN_SW2, INPUT_PULLUP);
  pinMode(PIN_LED_STATUS, OUTPUT);
  digitalWrite(PIN_LED_STATUS, LOW);

  Serial.println(F("\nBraco robotico 4 GDL (joysticks) - iniciando..."));
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    posAtual[j] = alvo[j] = limita(POS_REF[j], ANG_MIN[j], ANG_MAX[j]);
    escreveServo(j);                                           // AVR: o 1º pulso já sai na referência
    servo[j].attach(PIN_SERVO[j], PULSO_MIN_US, PULSO_MAX_US);
    escreveServo(j);                                           // outras placas só aceitam a escrita após o attach
    delay(150);                                                // liga os servos em sequência (pico de corrente menor)
  }
  delay(500);                                                  // espera os servos chegarem antes de ler os joysticks
  calibraJoysticks();                                          // joysticks devem estar soltos (centro)
  carregaEEPROM();
  Serial.println(F("Pronto."));
  imprimeAjuda();
  imprimePosicoes();
}

void loop() {
  static uint32_t tUltimo = 0;
  trataSerial();
  trataBotoes();

  uint32_t agora = millis();
  if (agora - tUltimo < PERIODO_MS) return;                    // laço de controle a 50 Hz
  // se um bloqueio longo atrasou vários períodos, ressincroniza em vez de executar os ciclos perdidos em
  // rajada (que somaria vários incrementos do joystick num único salto)
  tUltimo = (agora - tUltimo > 3UL * PERIODO_MS) ? agora : tUltimo + PERIODO_MS;

  if (modo == REPRODUZINDO) passoReproducao();
  else { leJoysticks(); avancaParaAlvo(); }                    // MANUAL: joysticks incrementam o alvo
  atualizaLed();
  if (diagnostico) imprimeDiagnostico();
}
