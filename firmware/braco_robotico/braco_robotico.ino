/*
 * ============================================================================
 *  BRAÇO ROBÓTICO 4 GDL — Sistemas Embarcados (FAESA – Engenharia da Computação)
 *  Plataforma: Arduino UNO R3 (ATmega328P) — Arduino IDE 2.x
 *  Atuadores : 4 micro-servos SG90/MG90S  (base, ombro, cotovelo, garra)
 *  Comando   : 2 módulos joystick analógico KY-023 (2 eixos + botão cada)
 * ----------------------------------------------------------------------------
 *  MAPA DE PINOS
 *    D3  -> sinal servo S1 (base)          JOYSTICK 1:  VRx -> A0 (base)
 *    D5  -> sinal servo S2 (ombro)                      VRy -> A1 (ombro)
 *    D6  -> sinal servo S3 (cotovelo)                   SW  -> D2 (gravar / reproduzir)
 *    D9  -> sinal servo S4 (garra)         JOYSTICK 2:  VRx -> A2 (garra)
 *    D13 -> LED de status (LED da placa)                VRy -> A3 (cotovelo)
 *                                                       SW  -> D4 (abrir/fechar garra; longo = home)
 *    Joysticks: +5V e GND do Arduino. Servos: fonte externa 5 V / 3 A (GND comum!)
 * ----------------------------------------------------------------------------
 *  CONTROLE
 *    O joystick volta sozinho ao centro, por isso o comando é INCREMENTAL (velocidade):
 *    inclinar o eixo move a junta na direção correspondente, tanto mais rápido quanto
 *    maior a inclinação (curva quadrática para precisão perto do centro); soltar = para.
 *    O centro de cada eixo é calibrado na partida (não toque nos joysticks ao ligar).
 *  MODOS
 *    MANUAL      : joysticks comandam as juntas.
 *    REPRODUZINDO: percorre ciclicamente as poses gravadas (até 16).
 *  BOTÕES
 *    SW1 curto = grava a pose atual      SW1 longo (> 0,8 s) = inicia/para a reprodução
 *    SW2 curto = abre/fecha a garra      SW2 longo (> 0,8 s) = vai para a posição de repouso (home)
 *    (garra: 74° ≈ fechada, 110° = aberta — valores nominais, calibrar; os dedos se tocam em ~72,5°)
 *    A garra é montada sob a palma, com as engrenagens de eixo vertical: com o antebraço na horizontal as
 *    mandíbulas fecham num PLANO HORIZONTAL (o braço agarra o objeto pelos lados, apoiado na mesa).
 *  COMANDOS SERIAIS (115200 bps) — calibração e depuração:
 *    p  imprime posições      g  grava pose        l  limpa poses       r  reproduz/para
 *    m  manual (para)         h  home              a  abre/fecha garra  j  recalibra centro dos joysticks
 *    e  salva poses na EEPROM c  carrega da EEPROM v <n> velocidade máx. (1..10 °/passo)
 *    s <j> <ang>  move a junta j (0..3) para <ang> graus
 * ============================================================================
 */
#include <Servo.h>
#include <EEPROM.h>

// ------------------------------------------------------------ configuração
const uint8_t  N_JUNTAS       = 4;
const uint8_t  PIN_SW1        = 2;      // botão do joystick 1
const uint8_t  PIN_SW2        = 4;      // botão do joystick 2
const uint8_t  PIN_LED        = 13;
const uint16_t PERIODO_MS     = 20;     // período do laço de controle (50 Hz = período do PWM dos servos)
const uint16_t TOQUE_LONGO_MS = 800;
const uint8_t  MAX_POSES      = 16;
const uint16_t EEPROM_MAGIC   = 0xB4A1; // assinatura para validar dados na EEPROM
const int      ZONA_MORTA     = 60;     // counts do ADC (~6 %) ignorados em torno do centro do joystick
const float    VEL_JOY        = 2.0f;   // graus por passo com o joystick no fim de curso (2 °/20 ms = 100 °/s)

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
const uint8_t ANG_HOME[N_JUNTAS] = {  90,    90,    90,    90 };
const uint8_t PIN_SERVO[N_JUNTAS] = { 3, 5, 6, 9 };
const uint8_t PIN_EIXO[N_JUNTAS]  = { A0, A1, A3, A2 };   // J1-VRx, J1-VRy, J2-VRy, J2-VRx
const int8_t  SENTIDO[N_JUNTAS]   = { 1, 1, 1, 1 };       // troque para -1 para inverter o sentido de um eixo
const char*   NOME[N_JUNTAS]      = { "base", "ombro", "cotovelo", "garra" };
const uint8_t GARRA = 3;
const uint8_t GARRA_FECHADA = 74, GARRA_ABERTA = 110;   // 74 ≈ 2 mm de vão; 110 ≈ 57 mm. Calibrar (seção 9.3)

// ------------------------------------------------------------ estado
enum Modo : uint8_t { MANUAL, REPRODUZINDO };

Servo   servo[N_JUNTAS];
float   posAtual[N_JUNTAS];             // posição comandada (graus, com casas decimais para suavizar)
float   alvo[N_JUNTAS];                 // posição desejada
int     centro[N_JUNTAS];               // leitura do ADC com o joystick em repouso (calibrada na partida)
float   velMax = 3.0f;                  // graus por passo (3 °/20 ms = 150 °/s) — usado em home / reprodução / comando s
Modo    modo   = MANUAL;

uint8_t poses[MAX_POSES][N_JUNTAS];
uint8_t nPoses = 0;
uint8_t poseAtual = 0;
uint32_t tPausaPose = 0;                // pausa entre poses na reprodução

// botões dos joysticks (definidos antes das funções: o Arduino IDE gera os protótipos no topo do arquivo)
struct Botao {
  uint8_t  pino;
  bool     pressionado;
  bool     longoDisparado;
  uint32_t tInicio;
};
Botao sw1 = { PIN_SW1, false, false, 0 }, sw2 = { PIN_SW2, false, false, 0 };

// ------------------------------------------------------------ utilidades
static float limita(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

void aplicaServos() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) servo[j].write((int)(posAtual[j] + 0.5f));
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

void calibraJoysticks() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    long soma = 0;
    for (uint8_t k = 0; k < 16; k++) { soma += analogRead(PIN_EIXO[j]); delay(2); }
    centro[j] = soma / 16;
  }
  Serial.print(F("Centro dos joysticks:"));
  for (uint8_t j = 0; j < N_JUNTAS; j++) { Serial.print(' '); Serial.print(centro[j]); }
  Serial.println();
}

// controle incremental: deflexão do joystick -> incremento de ângulo por passo
void leJoysticks() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    int d = analogRead(PIN_EIXO[j]) - centro[j];                       // -512..+511 em torno do centro
    if (abs(d) < ZONA_MORTA) continue;                                 // dentro da zona morta: não move
    float n = (abs(d) - ZONA_MORTA) / (512.0f - ZONA_MORTA);           // 0..1
    n = limita(n, 0.0f, 1.0f);
    float inc = VEL_JOY * n * n * (d > 0 ? 1 : -1) * SENTIDO[j];       // curva quadrática: fino perto do centro
    alvo[j] = limita(alvo[j] + inc, ANG_MIN[j], ANG_MAX[j]);
  }
}

void imprimePosicoes() {
  Serial.print(F("modo=")); Serial.print(modo == MANUAL ? F("MANUAL") : F("REPRODUZINDO"));
  Serial.print(F(" poses=")); Serial.print(nPoses);
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    Serial.print(F("  ")); Serial.print(NOME[j]); Serial.print('='); Serial.print((int)posAtual[j]);
  }
  Serial.println();
}

void gravaPose() {
  if (nPoses >= MAX_POSES) { Serial.println(F("Memoria de poses cheia (16).")); return; }
  for (uint8_t j = 0; j < N_JUNTAS; j++) poses[nPoses][j] = (uint8_t)posAtual[j];
  nPoses++;
  Serial.print(F("Pose gravada #")); Serial.println(nPoses);
  for (uint8_t i = 0; i < 3; i++) { digitalWrite(PIN_LED, HIGH); delay(60); digitalWrite(PIN_LED, LOW); delay(60); }
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

void vaiParaHome() {
  modo = MANUAL;
  for (uint8_t j = 0; j < N_JUNTAS; j++) alvo[j] = ANG_HOME[j];
  Serial.println(F("Indo para home..."));
}

void alternaGarra() {
  bool aberta = alvo[GARRA] > (GARRA_FECHADA + GARRA_ABERTA) / 2;
  alvo[GARRA] = aberta ? GARRA_FECHADA : GARRA_ABERTA;
  Serial.println(aberta ? F("Garra: fechando") : F("Garra: abrindo"));
}

// ------------------------------------------------------------ EEPROM (poses persistentes)
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
// retorna 1 = toque curto, 2 = toque longo, 0 = nada
uint8_t leBotao(Botao &b) {
  bool agora = (digitalRead(b.pino) == LOW);
  if (agora && !b.pressionado) { b.pressionado = true; b.tInicio = millis(); b.longoDisparado = false; }
  if (agora && b.pressionado && !b.longoDisparado && millis() - b.tInicio >= TOQUE_LONGO_MS) {
    b.longoDisparado = true; return 2;
  }
  if (!agora && b.pressionado) {
    b.pressionado = false;
    if (!b.longoDisparado && millis() - b.tInicio > 30) return 1;
  }
  return 0;
}

void trataBotoes() {
  uint8_t e1 = leBotao(sw1), e2 = leBotao(sw2);
  if (e1 == 2)      { if (modo == REPRODUZINDO) pararReproducao(); else iniciaReproducao(); }
  else if (e1 == 1) { if (modo == REPRODUZINDO) pararReproducao(); else gravaPose(); }
  if (e2 == 2)      vaiParaHome();
  else if (e2 == 1) { if (modo == REPRODUZINDO) pararReproducao(); alternaGarra(); }
}

// ------------------------------------------------------------ comandos seriais
void trataSerial() {
  if (!Serial.available()) return;
  String linha = Serial.readStringUntil('\n'); linha.trim();
  if (linha.length() == 0) return;
  char c = linha.charAt(0);
  switch (c) {
    case 'p': imprimePosicoes(); break;
    case 'g': gravaPose(); break;
    case 'l': nPoses = 0; if (modo == REPRODUZINDO) pararReproducao(); Serial.println(F("Poses apagadas.")); break;
    case 'r': if (modo == REPRODUZINDO) pararReproducao(); else iniciaReproducao(); break;
    case 'm': if (modo == REPRODUZINDO) pararReproducao(); else Serial.println(F("Modo MANUAL (joysticks).")); break;
    case 'h': vaiParaHome(); break;
    case 'a': alternaGarra(); break;
    case 'j': calibraJoysticks(); break;
    case 'e': salvaEEPROM(); break;
    case 'c': if (!carregaEEPROM()) Serial.println(F("EEPROM sem dados validos.")); break;
    case 'v': { int v = linha.substring(1).toInt(); if (v >= 1 && v <= 10) velMax = v; Serial.print(F("velMax=")); Serial.println(velMax); } break;
    case 's': {                                                // s <junta> <angulo>
      int j = linha.substring(1).toInt();
      int sp = linha.indexOf(' ', 2);
      int ang = (sp > 0) ? linha.substring(sp + 1).toInt() : -1;
      if (j >= 0 && j < N_JUNTAS && ang >= 0 && ang <= 180) {
        if (modo == REPRODUZINDO) pararReproducao();
        alvo[j] = limita(ang, ANG_MIN[j], ANG_MAX[j]);
        Serial.print(NOME[j]); Serial.print(F(" -> ")); Serial.println((int)alvo[j]);
      } else Serial.println(F("Uso: s <junta 0..3> <angulo 0..180>"));
    } break;
    default: Serial.println(F("Comandos: p g l r m h a j e c v<n> s<j> <ang>"));
  }
}

// ------------------------------------------------------------ reprodução de sequência
void passoReproducao() {
  if (tPausaPose) {                                            // pausa de 500 ms em cada pose
    if (millis() - tPausaPose < 500) return;
    tPausaPose = 0;
    poseAtual = (poseAtual + 1) % nPoses;
  }
  if (nPoses == 0) { pararReproducao(); return; }
  // limita a pose aos limites atuais: uma pose gravada antes de recalibrar ANG_MIN/ANG_MAX (ou lida de uma
  // EEPROM antiga) deixaria alvo fora da faixa e avancaParaAlvo() nunca "chegaria" -> reprodução congelada
  for (uint8_t j = 0; j < N_JUNTAS; j++) alvo[j] = limita(poses[poseAtual][j], ANG_MIN[j], ANG_MAX[j]);
  if (avancaParaAlvo()) tPausaPose = millis();
}

// ------------------------------------------------------------ setup / loop
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(50);
  pinMode(PIN_SW1, INPUT_PULLUP);
  pinMode(PIN_SW2, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);

  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    posAtual[j] = alvo[j] = ANG_HOME[j];
    servo[j].attach(PIN_SERVO[j], 600, 2400);                  // dentro da faixa do SG90/MG90S (500-2400 µs); 2500 forçava o batente
    servo[j].write(ANG_HOME[j]);
    delay(150);                                                // liga os servos em sequência (pico de corrente menor)
  }
  calibraJoysticks();                                          // joysticks devem estar soltos (centro)
  carregaEEPROM();
  Serial.println(F("\nBraco robotico 4 GDL (joysticks) pronto. Digite '?' para ajuda."));
  imprimePosicoes();
}

void loop() {
  static uint32_t tUltimo = 0;
  trataSerial();
  trataBotoes();

  uint32_t agora = millis();
  if (agora - tUltimo < PERIODO_MS) return;                    // laço de controle a 50 Hz
  // se um bloqueio longo (ex.: os delay() de gravaPose) atrasou vários períodos, ressincroniza em vez de
  // executar os ciclos perdidos em rajada (que somaria vários incrementos do joystick num único salto)
  tUltimo = (agora - tUltimo > 3UL * PERIODO_MS) ? agora : tUltimo + PERIODO_MS;

  if (modo == REPRODUZINDO) {
    passoReproducao();
    digitalWrite(PIN_LED, (millis() / 250) % 2);               // LED piscando = reproduzindo
    return;
  }

  leJoysticks();                                               // MANUAL: joysticks incrementam o alvo
  avancaParaAlvo();
  digitalWrite(PIN_LED, HIGH);
}
