/*
 * ============================================================================
 *  BRAÇO ROBÓTICO 4 GDL — FIRMWARE DEFINITIVO
 *  Sistemas Embarcados (FAESA – Engenharia da Computação) — Arduino IDE 2.x
 *  Plataforma: Arduino UNO R3 (ATmega328P) — compila também em Nano, Mega 2560 e UNO R4
 *  Atuadores : 4 micro-servos SG90/MG90S (base, ombro, cotovelo, garra)
 *  Comando   : 2 módulos joystick analógico KY-023 (2 eixos + botão cada)
 *  Sinalização: LED RGB de estados (liga/desliga, 7 cores) + LED da placa (D13)
 *  Bibliotecas: Servo.h e EEPROM.h (já vêm com a Arduino IDE — não é preciso instalar nada)
 *
 *  Esta versão (09/11/2026) é a FUSÃO do firmware de operação com o sketch de bancada
 *  teste_braco_09.11: o programa que opera o braço é o mesmo que calibra os fins de curso.
 *  Não há mais um segundo .ino no projeto.
 * ----------------------------------------------------------------------------
 *  MAPA DE PINOS — os 9 sinais ocupam D2..D10 EM SEQUÊNCIA, sem furo vago no conector
 *    D2  -> sinal servo S1 (base)          JOYSTICK 1: VRx -> A0 (base)
 *    D3  -> sinal servo S2 (ombro)                     VRy -> A1 (ombro)
 *    D4  -> sinal servo S3 (cotovelo)                  SW  -> D6 (gravar / reproduzir)
 *    D5  -> sinal servo S4 (garra)         JOYSTICK 2: VRx -> A2 (garra)
 *    D8  -> LED RGB vermelho (R)                       VRy -> A3 (cotovelo)
 *    D9  -> LED RGB verde (G)                          SW  -> D7 (referência; longo = garra)
 *    D10 -> LED RGB azul (B)
 *    D13 -> LED da própria placa (status simples)      D11, D12 e 0/1 (RX/TX): livres / não usar
 *    Joysticks: +5V e GND do Arduino. Servos: fonte externa 5 V / 5 A (GND comum!)
 *    LED RGB: perna comum no GND, 220 Ω em cada cor (módulo KY-016 já traz os resistores).
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
 *    ATALHO: se algum eixo tiver sido REPROVADO na calibração (LED vermelho piscando), um toque em
 *    qualquer um dos dois botões recalibra — é o mesmo que o comando 'j', sem precisar do PC.
 *    Só vale nesse estado; com tudo calibrado os botões mantêm as funções acima.
 *    (garra: 74° ≈ fechada, 110° = aberta — valores nominais, calibrar; os dedos se tocam em ~72,5°)
 *    A garra é montada sob a palma, com as engrenagens de eixo vertical: com o antebraço na horizontal as
 *    mandíbulas fecham num PLANO HORIZONTAL (o braço agarra o objeto pelos lados, apoiado na mesa).
 *    Há dois pares de dedos intercambiáveis (mandíbula plana e mandíbula em V, auto-centrante para
 *    cilindros e esferas em pé). Os dois têm o mesmo ângulo de toque, então nada muda aqui na troca.
 * ----------------------------------------------------------------------------
 *  LED RGB DE ESTADOS — a COR diz o modo, o PISCAR diz que há movimento.
 *  Quando duas situações valem ao mesmo tempo, vence a de cima da lista.
 *    vermelho piscando rápido (3 Hz) eixo de joystick reprovado na calibração: aquela junta não
 *                                    responde. Um toque em qualquer botão recalibra.
 *    branco, lampejo a cada 2 s      nenhum servo energizado (comando 'x'): tudo solto, sem torque —
 *                                    o braço CAI se não estiver apoiado. 'liga' devolve o torque.
 *    magenta                         faixa LIVRE 0..180 ligada: os limites de software estão
 *                                    desligados e a peça pode bater. Use só para medir fim de curso.
 *    ciano piscando (1,7 Hz)         sequência de bancada 'teste' ou 'varre' em curso (move sozinho)
 *    azul piscando (1,7 Hz)          REPRODUZINDO as poses gravadas
 *    amarelo                         MANUAL, mas com alguma junta DESLIGADA em JUNTA_LIGADA[]
 *    verde                           MANUAL, tudo calibrado e no lugar
 *    (a cor fixa pisca a 5 Hz enquanto alguma junta se move; volta a ficar fixa ao chegar — com o
 *     joystick no fim de curso, parar de piscar significa que a junta chegou ao limite)
 *  LAMPEJOS DE EVENTO (sobrepõem a cor do estado por alguns décimos de segundo)
 *    branco   pose gravada, EEPROM salva/carregada, botão reconhecido
 *    amarelo  ângulo cortado pelos limites, ou limite marcado com 'limite'
 *    vermelho comando recusado, memória de poses cheia (16) ou junta desligada
 * ----------------------------------------------------------------------------
 *  COMANDOS SERIAIS (115200 bps, qualquer opção de fim de linha)
 *   OPERAÇÃO (uma letra)
 *    p  imprime posições      g  grava pose        l  limpa poses       r  reproduz/para
 *    m  manual (para)         h  pos. de referência a  abre/fecha garra  j  recalibra centro dos joysticks
 *    e  salva poses na EEPROM c  carrega da EEPROM v <n> velocidade máx. (1..10 °/passo)
 *    s <j> <ang>  move a junta j (0..3) para <ang> graus
 *    d  diagnóstico liga/desliga (leituras cruas dos joysticks, botões e tensão da placa a cada 0,5 s)
 *    x  corta o pulso de TODOS os servos (soltos, sem torque)   ?  lista os comandos
 *   BANCADA E CALIBRAÇÃO (palavras inteiras)
 *    liga          devolve o pulso aos servos depois do 'x', na posição em que eles estão
 *    teste <j>     leva a junta j a 90° -> mínimo -> máximo -> 90°, parando 1 s em cada ponto
 *    varre <j>     varredura contínua mínimo <-> máximo na junta j (qualquer comando interrompe)
 *    livre         liga/desliga a faixa LIVRE 0..180 — SEM limites de software, vá de 1 em 1 grau
 *    limite <j>    marca a posição atual da junta j como fim de curso (abaixo de 90° = mínimo, acima = máximo)
 *    limites       imprime as linhas de ANG_MIN/ANG_MAX prontas para colar aqui no código
 *    led           repete o teste do LED RGB e imprime a legenda das cores
 *    O procedimento de calibração da seção 9.3 do relatório é: x -> posicione a junta à mão -> liga ->
 *    livre -> aproxime de 1 em 1 grau com 's <j> <ang>' -> limite <j> nos dois extremos -> limites.
 * ----------------------------------------------------------------------------
 *  HISTÓRICO
 *   2026-10-20  constante do LED renomeada para PIN_LED_STATUS (no UNO R4 PIN_LED é macro da placa);
 *               servos escritos antes E depois do attach; calibração reprova eixo fora de 512 ± 150 ou
 *               instável; debounce por estabilidade (25 ms); LED sem delay(); serial sem String;
 *               comandos 'd' e '?'; pulso em microssegundos; reprodução protegida contra pose inválida.
 *   2026-10-29  JUNTA_LIGADA[]: opera com uma junta desligada (o servo S1 está com defeito).
 *   2026-11-07  repinagem dos sinais para D2..D10 em sequência, para não errar ao ligar os jumpers.
 *   2026-11-09  FUSÃO com o sketch de bancada: LED RGB de estados, 'x'/'liga', 'teste'/'varre',
 *               'livre', 'limite'/'limites', 'led' e o atalho de recalibração pelos botões.
 *               Pinos, limites, POS_REF, botões e o formato da EEPROM (0xB4A1) NÃO mudaram.
 *
 *  OPERAR COM UMA JUNTA DESLIGADA — vetor JUNTA_LIGADA[] logo abaixo da configuração:
 *    - a junta desligada NÃO recebe attach() nem pulso: o pino fica em repouso, o servo defeituoso
 *      não zumbe nem puxa corrente de travamento e nada se move sozinho;
 *    - o eixo do joystick que a comandava fica inerte (J1-VRx/A0 no caso da base);
 *    - 'p' e 'd' mostram a junta como DESLIGADA, os comandos que a moveriam avisam e o LED fica AMARELO;
 *    - a reprodução e a volta à referência seguem funcionando com as juntas restantes.
 *    PARA RELIGAR depois de trocar o servo: JUNTA_LIGADA[0] = true (e recalibrar o horn da base em 90°).
 * ============================================================================
 */
#include <Servo.h>
#include <EEPROM.h>

// ------------------------------------------------------------ configuração
const uint8_t  N_JUNTAS       = 4;
const uint8_t  PIN_SW1        = 6;      // botão do joystick 1
const uint8_t  PIN_SW2        = 7;      // botão do joystick 2
const uint8_t  PIN_LED_STATUS = 13;     // LED da placa (D13)
const uint32_t SERIAL_BPS     = 115200; // configure o Monitor Serial com a MESMA velocidade
const uint16_t PERIODO_MS     = 20;     // período do laço de controle (50 Hz = período do PWM dos servos)
const uint16_t TOQUE_LONGO_MS = 800;
const uint16_t DEBOUNCE_MS    = 25;     // o contato do botão precisa ficar estável esse tempo
const uint8_t  MAX_POSES      = 16;
const uint16_t PAUSA_POSE_MS  = 500;    // parada em cada pose durante a reprodução
const uint16_t PAUSA_SEQ_MS   = 1000;   // parada em cada ponto de 'teste' / 'varre'
const uint16_t EEPROM_MAGIC   = 0xB4A1; // assinatura para validar dados na EEPROM
const int      ZONA_MORTA     = 60;     // counts do ADC (~6 %) ignorados em torno do centro do joystick
const float    VEL_JOY        = 2.0f;   // graus por passo com o joystick no fim de curso (2 °/20 ms = 100 °/s)
const int      CENTRO_TOL     = 150;    // na calibração o centro tem de cair em 512 ± 150 counts...
const int      RUIDO_MAX      = 40;     // ...e as 16 leituras não podem variar mais que isso (pino solto "flutua")
const uint16_t PULSO_MIN_US   = 600;    // pulso de 0°   (SG90/MG90S aceitam 500..2400 µs; 2500 forçava o batente)
const uint16_t PULSO_MAX_US   = 2400;   // pulso de 180°

// LED RGB de estados: 3 pinos em liga/desliga = 7 cores. NÃO usa analogWrite de propósito — a biblioteca
// Servo ocupa o Timer1 do AVR, que é o gerador de PWM de D9 e D10, exatamente os canais G e B. Em
// digitalWrite não há conflito nenhum e a cor sai sempre igual.
// Prefixo PIN_RGB_ de propósito: PIN_LED, LEDR, LEDG e LEDB são macros de placa em várias placas.
const uint8_t  PIN_RGB_R = 8, PIN_RGB_G = 9, PIN_RGB_B = 10;
const bool     LED_ANODO_COMUM = false; // false = catodo comum (perna comum no GND, caso do KY-016)
                                        // true  = ânodo comum (perna comum no +5V): inverte os 3 pinos
const uint16_t LAMPEJO_MS = 400;        // duração do lampejo de evento

// limites mecânicos (graus do servo) — AJUSTE NA CALIBRAÇÃO (seção 9.3 do relatório). Não são const:
// os comandos 'limite <j>' / 'limites' escrevem aqui durante a calibração de bancada. Valores nominais:
//   base     : 5..175 — nunca 0/180 (extremos da faixa de pulso = batente interno do servo, zumbido e aquecimento)
//   ombro    : 15..165 — com o ombro > ~45° e o antebraço apontando para baixo a garra passa do plano da mesa:
//              não há batente mecânico, o operador (ou a base elevada) evita
//   cotovelo : 40..140 — dobrando o antebraço sobre o braço, a PALMA da garra encosta na parede da plataforma
//              a partir de 148° (varredura booleana; no braço em si só toca a 160°). Como o sentido do servo só
//              se conhece na calibração, o limite é simétrico: depois de calibrar, o lado "esticado" pode ir a
//              20° e o lado "dobrado" NUNCA deve passar de 145°
//   garra    : 72..110 — as mandíbulas se tocam em ~72,5° (horn montado a 75° = dedos paralelos); abaixo disso
//              o servo fica em travamento (stall) permanente
//                             base   ombro  cotovelo garra
uint8_t ANG_MIN[N_JUNTAS]  = {   5,    15,    40,    72 };
uint8_t ANG_MAX[N_JUNTAS]  = { 175,   165,   140,   110 };

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
const uint8_t PIN_SERVO[N_JUNTAS] = { 2, 3, 4, 5 };
const uint8_t PIN_EIXO[N_JUNTAS]  = { A0, A1, A3, A2 };   // J1-VRx, J1-VRy, J2-VRy, J2-VRx
const int8_t  SENTIDO[N_JUNTAS]   = { 1, 1, 1, 1 };       // troque para -1 para inverter o sentido de um eixo
const char*   NOME[N_JUNTAS]      = { "base", "ombro", "cotovelo", "garra" };
const char*   NOME_EIXO[N_JUNTAS] = { "A0 (J1-VRx)", "A1 (J1-VRy)", "A3 (J2-VRy)", "A2 (J2-VRx)" };
const uint8_t GARRA = 3;
const uint8_t GARRA_FECHADA = 74, GARRA_ABERTA = 110;   // 74 ≈ 2 mm de vão; 110 ≈ 57 mm. Calibrar (seção 9.3)

// JUNTAS EM USO — false = junta desligada (servo com defeito, ausente ou ainda não montado).
// A junta desligada não recebe attach() nem pulso: o pino de sinal fica em repouso (INPUT), o servo não
// zumbe nem trava, o eixo do joystick dela fica inerte e as outras juntas funcionam normalmente.
// 2026-10-29: a BASE (S1 em D2, eixo A0) está desligada por defeito no servo. Trocado o servo, volte
// este valor para true, monte o horn com a junta em 90° e refaça a calibração de ANG_MIN/ANG_MAX.
//                                    base   ombro  cotovelo garra
const bool JUNTA_LIGADA[N_JUNTAS] = { false,  true,   true,   true };

// ------------------------------------------------------------ tipos e estado
// (todos os tipos vêm antes da primeira função: a Arduino IDE gera os protótipos no topo do arquivo)
enum Modo : uint8_t { MANUAL, REPRODUZINDO };

enum Sequencia : uint8_t { NENHUMA, SEQ_TESTE, SEQ_VARREDURA };

enum Cor : uint8_t {                    // bit 0 = vermelho, bit 1 = verde, bit 2 = azul
  PRETO = 0, VERMELHO = 1, VERDE = 2, AMARELO = 3, AZUL = 4, MAGENTA = 5, CIANO = 6, BRANCO = 7
};

// estados sinalizados no LED RGB, do mais urgente para o menos (o primeiro que casar é o que aparece)
enum EstadoLed : uint8_t {
  LED_FALHA,        // vermelho 3 Hz : eixo de joystick reprovado na calibração
  LED_SOLTO,        // branco 2 s    : nenhum servo energizado ('x')
  LED_LIVRE,        // magenta       : faixa LIVRE 0..180, sem limites de software
  LED_SEQUENCIA,    // ciano 1,7 Hz  : 'teste' / 'varre' em curso
  LED_REPRODUZINDO, // azul 1,7 Hz   : reproduzindo as poses gravadas
  LED_DEGRADADO,    // amarelo       : MANUAL com alguma junta desligada
  LED_MANUAL        // verde         : MANUAL, tudo certo
};

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
bool    anexado[N_JUNTAS];              // false = servo sem pulso (comando 'x'); 'liga' devolve
float   velMax = 3.0f;                  // graus por passo (3 °/20 ms = 150 °/s) — referência / reprodução / comando s
Modo    modo   = MANUAL;
bool    faixaLivre = false;             // true = ignora ANG_MIN/ANG_MAX (medição de fim de curso)

uint8_t  poses[MAX_POSES][N_JUNTAS];
uint8_t  nPoses = 0;
uint8_t  poseAtual = 0;
uint32_t tPausaPose = 0;                // != 0: chegou na pose e está parado nela desde esse instante

Sequencia seq = NENHUMA;                // sequência de bancada ('teste' / 'varre')
uint8_t   seqJunta = 0;
uint8_t   passoSeq = 0;
uint32_t  tChegadaSeq = 0;
bool      seqParado = true;

Botao sw1 = { PIN_SW1, false, false, false, 0, 0 }, sw2 = { PIN_SW2, false, false, false, 0, 0 };

uint8_t  piscadasLed = 0;               // meias-piscadas que faltam no LED da placa (pose gravada)
uint32_t tPiscaLed = 0;

uint8_t  corLampejo = PRETO;            // lampejo de evento no LED RGB (prioridade máxima)
uint32_t tLampejo   = 0;
uint16_t msLampejo  = 0;

char     linha[32];                     // comando serial em montagem
uint8_t  nLinha = 0;
uint32_t tUltimoCaractere = 0;

bool     diagnostico = false;
uint32_t tDiagnostico = 0;

// ------------------------------------------------------------ utilidades
static float limita(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

// faixa útil de cada junta; com 'livre' ligado o software deixa passar 0..180 (só para medir fim de curso)
float limInf(uint8_t j) { return faixaLivre ? 0   : ANG_MIN[j]; }
float limSup(uint8_t j) { return faixaLivre ? 180 : ANG_MAX[j]; }

// graus (com fração) -> microssegundos; mesma escala do Servo.write() com attach(pino, 600, 2400)
// Junta desligada ou solta pelo 'x': nenhum pulso sai (o objeto Servo não está anexado ao pino).
void escreveServo(uint8_t j) {
  if (!JUNTA_LIGADA[j] || !anexado[j]) return;
  float us = PULSO_MIN_US + posAtual[j] * ((PULSO_MAX_US - PULSO_MIN_US) / 180.0f);
  servo[j].writeMicroseconds((int)(us + 0.5f));
}

// lista as juntas desligadas (aviso na partida e na ajuda, para não parecer defeito de montagem)
void avisaJuntasDesligadas() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    if (JUNTA_LIGADA[j]) continue;
    Serial.print(F("JUNTA DESLIGADA: ")); Serial.print(NOME[j]);
    Serial.print(F(" (servo em D")); Serial.print(PIN_SERVO[j]);
    Serial.print(F(", eixo ")); Serial.print(NOME_EIXO[j]);
    Serial.println(F(") - sem pulso; as outras juntas funcionam normalmente."));
  }
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
    posAtual[j] = limita(posAtual[j], limInf(j), limSup(j));
  }
  aplicaServos();
  return chegou;
}

// true enquanto alguma junta energizada ainda não chegou ao alvo (usado pelo piscar do LED RGB)
bool algumaJuntaMovendo() {
  for (uint8_t j = 0; j < N_JUNTAS; j++)
    if (JUNTA_LIGADA[j] && anexado[j] && posAtual[j] != alvo[j]) return true;
  return false;
}

bool algumServoEnergizado() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) if (JUNTA_LIGADA[j] && anexado[j]) return true;
  return false;
}

bool algumEixoReprovado() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) if (JUNTA_LIGADA[j] && !eixoAtivo[j]) return true;
  return false;
}

bool algumaJuntaDesligada() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) if (!JUNTA_LIGADA[j]) return true;
  return false;
}

// ------------------------------------------------------------ LED RGB de estados
void escreveLed(uint8_t cor) {
  bool r = cor & VERMELHO, g = cor & VERDE, b = cor & AZUL;
  if (LED_ANODO_COMUM) { r = !r; g = !g; b = !b; }   // ânodo comum: o pino puxa para o GND para acender
  digitalWrite(PIN_RGB_R, r);
  digitalWrite(PIN_RGB_G, g);
  digitalWrite(PIN_RGB_B, b);
}

// lampejo de evento: sobrepõe a cor do estado por alguns décimos de segundo, sem travar o laço
void lampeja(uint8_t cor, uint16_t ms) { corLampejo = cor; msLampejo = ms; tLampejo = millis(); }

EstadoLed estadoLed() {
  if (algumEixoReprovado())   return LED_FALHA;
  if (!algumServoEnergizado())return LED_SOLTO;
  if (faixaLivre)             return LED_LIVRE;
  if (seq != NENHUMA)         return LED_SEQUENCIA;
  if (modo == REPRODUZINDO)   return LED_REPRODUZINDO;
  if (algumaJuntaDesligada()) return LED_DEGRADADO;
  return LED_MANUAL;
}

// cor = modo, piscar = atividade. Chamada a cada 20 ms; não usa delay()
void atualizaLedRgb() {
  uint32_t ms = millis();
  if (ms - tLampejo < msLampejo) { escreveLed(corLampejo); return; }

  uint8_t  cor     = VERDE;
  uint16_t periodo = 0, aceso = 0;                   // periodo 0 = cor fixa
  switch (estadoLed()) {
    case LED_FALHA:        cor = VERMELHO; periodo =  300; aceso = 150; break;
    case LED_SOLTO:        cor = BRANCO;   periodo = 2000; aceso =  80; break;
    case LED_LIVRE:        cor = MAGENTA;  break;
    case LED_SEQUENCIA:    cor = CIANO;    periodo =  600; aceso = 300; break;
    case LED_REPRODUZINDO: cor = AZUL;     periodo =  600; aceso = 300; break;
    case LED_DEGRADADO:    cor = AMARELO;  break;
    default:               cor = VERDE;    break;
  }
  if (!periodo && algumaJuntaMovendo()) { periodo = 200; aceso = 100; }   // mexendo: a cor do modo pisca
  escreveLed((!periodo || ms % periodo < aceso) ? cor : (uint8_t)PRETO);
}

// teste de fiação: acende cada cor por 400 ms dizendo qual deveria ser
void testaLed() {
  Serial.print(F("Teste do LED RGB (D8=R, D9=G, D10=B): vermelho"));
  escreveLed(VERMELHO); delay(400);
  Serial.print(F(", verde"));     escreveLed(VERDE);  delay(400);
  Serial.print(F(", azul"));      escreveLed(AZUL);   delay(400);
  Serial.println(F(", branco.")); escreveLed(BRANCO); delay(400);
  escreveLed(PRETO);
  Serial.println(F("  Cor trocada = pinos R/G/B trocados. Acende o contrario do dito = mude LED_ANODO_COMUM."));
  Serial.println(F("  Nao acende nada = perna comum sem GND, resistor solto ou LED ao contrario."));
}

void imprimeLegendaLed() {
  Serial.println(F("LED RGB: verde MANUAL | amarelo MANUAL com junta desligada | azul reproduzindo | ciano teste/varre"));
  Serial.println(F("         magenta faixa LIVRE | branco (lampejo 2 s) servos soltos | vermelho rapido eixo reprovado"));
  Serial.println(F("         a cor pisca a 5 Hz enquanto ha movimento; lampejo: branco ok, amarelo limite, vermelho recusado"));
}

// ------------------------------------------------------------ joysticks
// o SW do KY-023 fica no próprio eixo: apertar empurra a alavanca e a inclina. Antes de medir o centro
// espera o botão soltar e mais 150 ms de sossego, senão a calibração guarda um centro deslocado e o eixo
// pode até ser reprovado (512 ± 150). Teto de 3 s para um botão preso não travar o braço.
void esperaBotoesSoltos() {
  uint32_t t0 = millis();
  while (millis() - t0 < 3000) {
    if (digitalRead(PIN_SW1) == HIGH && digitalRead(PIN_SW2) == HIGH) {
      delay(150);
      if (digitalRead(PIN_SW1) == HIGH && digitalRead(PIN_SW2) == HIGH) return;
    }
    delay(5);
  }
  Serial.println(F("  ATENCAO: botao continua apertado (fio em curto com o GND?). Medindo assim mesmo."));
}

// lê 16 amostras de cada eixo com os joysticks soltos; reprova o eixo cujo "centro" não está no meio da
// faixa (alavanca inclinada ao ligar, fio solto/trocado, módulo sem +5V/GND) ou cuja leitura oscila (pino
// analógico sem nada ligado). Eixo reprovado fica parado: é melhor do que a junta disparar sozinha.
void calibraJoysticks() {
  uint8_t reprovados = 0;
  escreveLed(AMARELO);                      // amarelo fixo enquanto mede: não toque nas alavancas
  Serial.print(F("Centro dos joysticks:"));
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    if (!JUNTA_LIGADA[j]) {                 // junta desligada: não há o que calibrar nem o que reprovar
      centro[j] = 512; eixoAtivo[j] = false;
      Serial.print(F(" --"));
      continue;
    }
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
  if (!reprovados) { lampeja(BRANCO, LAMPEJO_MS); return; }
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    if (eixoAtivo[j] || !JUNTA_LIGADA[j]) continue;
    Serial.print(F("ATENCAO: eixo ")); Serial.print(NOME_EIXO[j]); Serial.print(F(" -> ")); Serial.print(NOME[j]);
    Serial.print(F(" leu ")); Serial.print(centro[j]); Serial.println(F(" (esperado ~512). Eixo desativado."));
  }
  Serial.println(F("  Causas: alavanca inclinada ao ligar, fio solto/trocado ou joystick sem +5V/GND."));
  Serial.println(F("  Solte os joysticks e envie 'j' (ou aperte um botao) para recalibrar; 'd' mostra as leituras."));
}

// controle incremental: deflexão do joystick -> incremento de ângulo por passo
void leJoysticks() {
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    if (!JUNTA_LIGADA[j] || !eixoAtivo[j] || !anexado[j]) continue;    // desligada / reprovada / solta
    int d = analogRead(PIN_EIXO[j]) - centro[j];                     // ~-512..+511 em torno do centro
    int ad = d < 0 ? -d : d;
    if (ad < ZONA_MORTA) continue;                                     // dentro da zona morta: não move
    float n = (ad - ZONA_MORTA) / (512.0f - ZONA_MORTA);               // 0..1
    n = limita(n, 0.0f, 1.0f);
    float inc = VEL_JOY * n * n * (d > 0 ? 1 : -1) * SENTIDO[j];       // curva quadrática: fino perto do centro
    alvo[j] = limita(alvo[j] + inc, limInf(j), limSup(j));
  }
}

// ------------------------------------------------------------ informação
void imprimePosicoes() {
  Serial.print(F("modo=")); Serial.print(modo == MANUAL ? F("MANUAL") : F("REPRODUZINDO"));
  Serial.print(F(" poses=")); Serial.print(nPoses);
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    Serial.print(F("  ")); Serial.print(NOME[j]); Serial.print('=');
    if (!JUNTA_LIGADA[j])   Serial.print(F("DESLIGADA"));
    else if (!anexado[j])   Serial.print(F("solta"));
    else                    Serial.print((int)(posAtual[j] + 0.5f));
  }
  if (faixaLivre) Serial.print(F("  [faixa LIVRE 0..180]"));
  Serial.println();
}

void imprimeLimites() {
  Serial.print(F("Limites:"));
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    Serial.print(F("  ")); Serial.print(NOME[j]); Serial.print(' ');
    Serial.print(ANG_MIN[j]); Serial.print(F("..")); Serial.print(ANG_MAX[j]);
  }
  Serial.println();
}

void imprimeAlinhado(int v, uint8_t largura) {
  uint8_t n = v >= 100 ? 3 : (v >= 10 ? 2 : 1);
  for (uint8_t k = n; k < largura; k++) Serial.print(' ');
  Serial.print(v);
}

void imprimeVetor(bool minimo) {
  Serial.print(minimo ? F("uint8_t ANG_MIN[N_JUNTAS]  = {") : F("uint8_t ANG_MAX[N_JUNTAS]  = {"));
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    imprimeAlinhado(minimo ? ANG_MIN[j] : ANG_MAX[j], j == 0 ? 4 : 6);
    Serial.print(j < N_JUNTAS - 1 ? ',' : ' ');
  }
  Serial.println(F("};"));
}

// imprime as duas linhas prontas para colar na seção de configuração deste arquivo
void imprimeLinhasFirmware() {
  Serial.println(F("Linhas para colar na configuracao deste firmware (substitua as que existem):"));
  imprimeVetor(true);
  imprimeVetor(false);
  Serial.print(F("const uint8_t GARRA_FECHADA = ")); Serial.print(ANG_MIN[GARRA]);
  Serial.print(F(", GARRA_ABERTA = ")); Serial.print(ANG_MAX[GARRA]); Serial.println(';');
}

void imprimeAjuda() {
  Serial.println(F("OPERACAO (Monitor Serial a 115200, qualquer fim de linha):"));
  Serial.println(F("  p  posicoes          g  grava pose         l  limpa poses        r  reproduz/para"));
  Serial.println(F("  m  modo manual       h  pos. referencia    a  abre/fecha garra   j  recalibra joysticks"));
  Serial.println(F("  e  salva na EEPROM   c  carrega da EEPROM  d  diagnostico on/off ?  esta ajuda"));
  Serial.println(F("  v <1..10>  velocidade maxima (graus/20 ms)    s <junta 0..3> <angulo>  move uma junta"));
  Serial.println(F("  x  solta TODOS os servos (sem torque)        liga  devolve o pulso aos servos"));
  Serial.println(F("BANCADA / CALIBRACAO (palavras inteiras):"));
  Serial.println(F("  teste <j>  90->min->max->90   varre <j>  varredura continua   led  testa o LED RGB"));
  Serial.println(F("  livre  liga/desliga a faixa 0..180   limite <j>  marca fim de curso   limites  linhas p/ colar"));
  Serial.println(F("Botoes: SW1 curto = grava | SW1 longo = reproduz/para | SW2 curto = referencia | SW2 longo = garra"));
  Serial.println(F("        com eixo reprovado (LED vermelho piscando), qualquer botao recalibra (= 'j')"));
  imprimeLegendaLed();
  avisaJuntasDesligadas();
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
    Serial.print(F("]=")); Serial.print(analogRead(PIN_EIXO[j]));   // o eixo continua sendo lido: serve de teste
    Serial.print('/'); Serial.print(centro[j]);
    if (!JUNTA_LIGADA[j])   Serial.print(F("(DESLIGADA)"));
    else if (!anexado[j])   Serial.print(F("(SOLTA)"));
    else if (!eixoAtivo[j]) Serial.print(F("(OFF)"));
  }
  Serial.print(F("  SW1=")); Serial.print(digitalRead(PIN_SW1) == LOW ? F("apertado") : F("solto"));
  Serial.print(F(" SW2=")); Serial.print(digitalRead(PIN_SW2) == LOW ? F("apertado") : F("solto"));
  long vcc = leVccMilivolts();
  if (vcc) { Serial.print(F("  Vcc~")); Serial.print(vcc / 1000.0, 2); Serial.print('V'); }
  Serial.println();
}

void piscaLed(uint8_t vezes) { piscadasLed = 2 * vezes; tPiscaLed = millis(); }

// LED da placa (D13): aceso = MANUAL, piscando = REPRODUZINDO; pisca rápido 3× ao gravar uma pose.
// É o indicador simples; quem conta a história completa é o LED RGB.
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

// ------------------------------------------------------------ poses, modos e garra
void paraSequencia(bool avisa) {
  if (seq == NENHUMA) return;
  seq = NENHUMA;
  if (avisa) Serial.println(F("(sequencia interrompida)"));
}

void gravaPose() {
  if (nPoses >= MAX_POSES) {
    lampeja(VERMELHO, 600);
    Serial.println(F("Memoria de poses cheia (16)."));
    return;
  }
  for (uint8_t j = 0; j < N_JUNTAS; j++) poses[nPoses][j] = (uint8_t)(posAtual[j] + 0.5f);
  nPoses++;
  Serial.print(F("Pose gravada #")); Serial.println(nPoses);
  piscaLed(3);
  lampeja(BRANCO, LAMPEJO_MS);
}

void iniciaReproducao() {
  if (nPoses == 0) { lampeja(VERMELHO, 600); Serial.println(F("Nenhuma pose gravada.")); return; }
  if (!algumServoEnergizado()) { lampeja(VERMELHO, 600); Serial.println(F("Servos soltos: envie 'liga' antes.")); return; }
  paraSequencia(false);
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
  paraSequencia(false);
  for (uint8_t j = 0; j < N_JUNTAS; j++) alvo[j] = limita(POS_REF[j], limInf(j), limSup(j));
  Serial.print(F("Voltando para a posicao de referencia:"));
  for (uint8_t j = 0; j < N_JUNTAS; j++) { Serial.print(' '); Serial.print((int)alvo[j]); }
  Serial.println(F(" graus."));
}

void alternaGarra() {
  if (!JUNTA_LIGADA[GARRA]) { lampeja(VERMELHO, 600); Serial.println(F("Garra desligada (JUNTA_LIGADA).")); return; }
  if (modo == REPRODUZINDO) pararReproducao();                // senão a reprodução sobrescreve o alvo
  paraSequencia(false);
  bool aberta = alvo[GARRA] > (GARRA_FECHADA + GARRA_ABERTA) / 2;
  alvo[GARRA] = aberta ? GARRA_FECHADA : GARRA_ABERTA;
  Serial.println(aberta ? F("Garra: fechando") : F("Garra: abrindo"));
}

// ------------------------------------------------------------ energizar / soltar os servos
void anexaServo(uint8_t j) {
  if (!JUNTA_LIGADA[j] || anexado[j]) return;
  anexado[j] = true;
  escreveServo(j);                                           // AVR: o 1º pulso já sai na posição certa
  servo[j].attach(PIN_SERVO[j], PULSO_MIN_US, PULSO_MAX_US);
  escreveServo(j);                                           // outras placas só aceitam a escrita após o attach
}

// corta o pulso de todos os servos: ficam soltos, sem torque. Serve para posicionar o braço à mão na
// calibração e para montar/desmontar sem forçar as engrenagens. ATENÇÃO: o braço CAI se não estiver apoiado.
void soltaServos() {
  paraSequencia(false);
  if (modo == REPRODUZINDO) modo = MANUAL;
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    if (!anexado[j]) continue;
    servo[j].detach();
    pinMode(PIN_SERVO[j], OUTPUT);
    digitalWrite(PIN_SERVO[j], LOW);
    anexado[j] = false;
  }
  Serial.println(F("Pulso cortado em TODOS os servos: soltos, sem torque. CUIDADO: o braco cai."));
  Serial.println(F("  'liga' devolve o pulso na posicao em que os servos estiverem."));
}

// devolve o pulso. Como o braço pode ter sido movido à mão, o alvo é zerado na posição atual comandada
// para o servo não dar um tranco ao religar: ele volta devagar para onde estava.
void ligaServos() {
  uint8_t n = 0;
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    if (!JUNTA_LIGADA[j] || anexado[j]) continue;
    alvo[j] = posAtual[j];
    anexaServo(j);
    n++;
    delay(150);                                              // um de cada vez: pico de corrente menor
  }
  if (!n) { Serial.println(F("Os servos ja estao energizados.")); return; }
  Serial.print(F("Pulso devolvido a ")); Serial.print(n); Serial.println(F(" servo(s)."));
  imprimePosicoes();
}

// ------------------------------------------------------------ calibração de fim de curso
// marca a posição atual como limite da junta: abaixo de 90° = mínimo, acima = máximo (mesma regra da bancada)
void marcaLimite(uint8_t j) {
  if (!JUNTA_LIGADA[j]) { lampeja(VERMELHO, 600); Serial.println(F("Junta DESLIGADA (JUNTA_LIGADA).")); return; }
  if (posAtual[j] != alvo[j]) {
    lampeja(VERMELHO, 600);
    Serial.println(F("A junta ainda esta se movendo: espere parar e mande 'limite <j>' de novo."));
    return;
  }
  int a = (int)(posAtual[j] + 0.5f);
  if (a == 90) {
    lampeja(VERMELHO, 600);
    Serial.println(F("Afaste-se de 90 graus: abaixo de 90 marca o minimo, acima marca o maximo."));
    return;
  }
  if (a < 90) ANG_MIN[j] = a; else ANG_MAX[j] = a;
  lampeja(AMARELO, LAMPEJO_MS);
  Serial.print(NOME[j]); Serial.print(a < 90 ? F(": minimo agora ") : F(": maximo agora ")); Serial.print(a);
  Serial.print(F(" (faixa ")); Serial.print(ANG_MIN[j]); Serial.print(F(".."));
  Serial.print(ANG_MAX[j]); Serial.println(F(")."));
  if (j == 2 && (a > 145 || a < 35))
    Serial.println(F("  ATENCAO: do lado em que o antebraco DOBRA sobre o braco, a palma bate na plataforma a 148."));
}

// ------------------------------------------------------------ sequências de bancada ('teste' / 'varre')
void proximoPassoSequencia() {
  float ref = limita(90, limInf(seqJunta), limSup(seqJunta));
  if (seq == SEQ_TESTE) {
    if (passoSeq >= 4) { seq = NENHUMA; Serial.println(F("Teste concluido.")); return; }
    const float pontos[4] = { ref, limInf(seqJunta), limSup(seqJunta), ref };
    Serial.print(F("Teste ")); Serial.print(passoSeq + 1); Serial.print(F("/4 -> "));
    alvo[seqJunta] = pontos[passoSeq];
    passoSeq++;
  } else {
    alvo[seqJunta] = (passoSeq++ % 2) ? limInf(seqJunta) : limSup(seqJunta);
    Serial.print(F("Varredura -> "));
  }
  Serial.print((int)alvo[seqJunta]); Serial.println(F(" graus"));
  seqParado = false;
}

void iniciaSequencia(Sequencia s, uint8_t j) {
  if (!JUNTA_LIGADA[j]) { lampeja(VERMELHO, 600); Serial.println(F("Junta DESLIGADA (JUNTA_LIGADA).")); return; }
  if (!anexado[j])      { lampeja(VERMELHO, 600); Serial.println(F("Servos soltos: envie 'liga' antes.")); return; }
  if (modo == REPRODUZINDO) pararReproducao();
  seq = s; seqJunta = j; passoSeq = 0;
  Serial.print(NOME[j]);
  Serial.println(s == SEQ_TESTE ? F(": teste automatico (qualquer comando interrompe)")
                                : F(": varredura continua (qualquer comando interrompe)"));
  proximoPassoSequencia();
}

void passoSequencia() {
  if (!seqParado && posAtual[seqJunta] == alvo[seqJunta]) { seqParado = true; tChegadaSeq = millis(); }
  if (seqParado && millis() - tChegadaSeq >= PAUSA_SEQ_MS) proximoPassoSequencia();
}

// ------------------------------------------------------------ EEPROM (poses persistentes)
// formato: assinatura (2 bytes) | nPoses (1 byte) | nPoses × 4 ângulos — o mesmo das versões anteriores
void salvaEEPROM() {
  int a = 0;
  EEPROM.put(a, EEPROM_MAGIC); a += sizeof(EEPROM_MAGIC);
  EEPROM.put(a, nPoses);       a += sizeof(nPoses);
  for (uint8_t i = 0; i < nPoses; i++)
    for (uint8_t j = 0; j < N_JUNTAS; j++) EEPROM.update(a++, poses[i][j]);
  lampeja(BRANCO, LAMPEJO_MS);
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
  if (!e1 && !e2) return;

  // ATALHO: com algum eixo reprovado na calibração o braço está meio morto e exigiria um PC para
  // mandar 'j'. Nesse estado (e só nele) qualquer toque recalibra, igual ao comando 'j'.
  if (algumEixoReprovado()) {
    Serial.println(F("> botao: recalibrando os joysticks (igual ao comando 'j'). Solte o botao e as alavancas."));
    escreveLed(BRANCO);
    esperaBotoesSoltos();
    calibraJoysticks();
    sw1.longoDisparado = sw2.longoDisparado = true;            // não deixa o mesmo aperto virar toque longo
    return;
  }

  lampeja(BRANCO, 150);                                        // confirma no LED que o botão foi lido
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

// lê o número da junta (0..3) que vem depois de um comando de palavra
bool leJunta(char *p, uint8_t &j) {
  long a;
  if (leInteiro(p, a) && a >= 0 && a < N_JUNTAS) { j = (uint8_t)a; return true; }
  lampeja(VERMELHO, 600);
  Serial.println(F("Falta o numero da junta: 0 base, 1 ombro, 2 cotovelo, 3 garra.  Ex.: teste 2"));
  return false;
}

// comandos de PALAVRA inteira, testados ANTES das letras soltas — senão "limite" seria lido como 'l'
// (limpa poses) e "livre" idem. Devolve true se tratou o comando.
bool executaPalavra(char *p) {
  uint8_t j;
  if (!strcmp(p, "liga"))    { ligaServos(); return true; }
  if (!strcmp(p, "led"))     { testaLed(); imprimeLegendaLed(); return true; }
  if (!strcmp(p, "limites")) { imprimeLimites(); imprimeLinhasFirmware(); return true; }
  if (!strcmp(p, "livre")) {
    faixaLivre = !faixaLivre;
    if (faixaLivre) {
      Serial.println(F("Faixa LIVRE 0..180 LIGADA - sem limites de software: va de 1 em 1 grau, a peca pode bater."));
      Serial.println(F("  'livre' de novo restaura os limites; 'x' solta tudo."));
    } else {
      Serial.println(F("Limites restaurados."));
      for (uint8_t k = 0; k < N_JUNTAS; k++) alvo[k] = limita(alvo[k], limInf(k), limSup(k));
    }
    imprimeLimites();
    return true;
  }
  if (!strncmp(p, "limite", 6) && (p[6] == '\0' || p[6] == ' ')) {
    if (leJunta(p + 6, j)) marcaLimite(j);
    return true;
  }
  if (!strncmp(p, "teste", 5) && (p[5] == '\0' || p[5] == ' ')) {
    if (leJunta(p + 5, j)) iniciaSequencia(SEQ_TESTE, j);
    return true;
  }
  if (!strncmp(p, "varre", 5) && (p[5] == '\0' || p[5] == ' ')) {
    if (leJunta(p + 5, j)) iniciaSequencia(SEQ_VARREDURA, j);
    return true;
  }
  return false;
}

void executaComando() {
  linha[nLinha] = '\0';
  nLinha = 0;
  char *p = linha;
  while (*p == ' ' || *p == '\t') p++;
  for (char *q = p; *q; q++) if (*q >= 'A' && *q <= 'Z') *q += 'a' - 'A';   // aceita maiúsculas
  for (char *q = p + strlen(p); q > p && q[-1] == ' '; ) *--q = '\0';       // tira espaços do fim
  if (*p == '\0') return;

  // consulta = não interrompe uma sequência em curso nem mexe no braço
  bool consulta = !strcmp(p, "p") || !strcmp(p, "?") || !strcmp(p, "d")
               || !strcmp(p, "limites") || !strcmp(p, "led");
  if (!consulta) paraSequencia(seq != NENHUMA);

  if (executaPalavra(p)) return;

  char c = *p++;
  long a, b;
  switch (c) {
    case 'p': imprimePosicoes(); imprimeLimites(); break;
    case 'g': gravaPose(); break;
    case 'l': nPoses = 0; if (modo == REPRODUZINDO) pararReproducao(); Serial.println(F("Poses apagadas.")); break;
    case 'r': if (modo == REPRODUZINDO) pararReproducao(); else iniciaReproducao(); break;
    case 'm': if (modo == REPRODUZINDO) pararReproducao(); else Serial.println(F("Modo MANUAL (joysticks).")); break;
    case 'h': vaiParaReferencia(); break;
    case 'a': alternaGarra(); break;
    case 'j': esperaBotoesSoltos(); calibraJoysticks(); break;
    case 'e': salvaEEPROM(); break;
    case 'c': if (!carregaEEPROM()) { lampeja(VERMELHO, 600); Serial.println(F("EEPROM sem dados validos.")); } break;
    case 'x': soltaServos(); break;
    case 'd':
      diagnostico = !diagnostico; tDiagnostico = 0;
      Serial.println(diagnostico ? F("Diagnostico LIGADO (eixo=leitura/centro). 'd' desliga.") : F("Diagnostico desligado."));
      break;
    case 'v':
      if (leInteiro(p, a) && a >= 1 && a <= 10) velMax = a;
      else { lampeja(VERMELHO, 600); Serial.println(F("Uso: v <1..10>")); }
      Serial.print(F("velMax=")); Serial.println(velMax);
      break;
    case 's':                                                  // s <junta> <angulo>
      if (leInteiro(p, a) && leInteiro(p, b) && a >= 0 && a < N_JUNTAS && b >= 0 && b <= 180) {
        if (!JUNTA_LIGADA[a]) {
          lampeja(VERMELHO, 600);
          Serial.print(NOME[a]); Serial.println(F(": junta DESLIGADA (JUNTA_LIGADA) - comando ignorado."));
          break;
        }
        if (!anexado[a]) { lampeja(VERMELHO, 600); Serial.println(F("Servos soltos: envie 'liga' antes.")); break; }
        if (modo == REPRODUZINDO) pararReproducao();
        alvo[a] = limita(b, limInf(a), limSup(a));
        Serial.print(NOME[a]); Serial.print(F(" -> ")); Serial.print((int)alvo[a]);
        if (alvo[a] != b) {
          lampeja(AMARELO, LAMPEJO_MS);
          Serial.print(F(" (limitado a ")); Serial.print((int)limInf(a));
          Serial.print(F("..")); Serial.print((int)limSup(a)); Serial.print(')');
        }
        Serial.println();
      } else { lampeja(VERMELHO, 600); Serial.println(F("Uso: s <junta 0..3> <angulo 0..180>   ex.: s 3 75")); }
      break;
    case '?': imprimeAjuda(); break;
    default:
      lampeja(VERMELHO, 600);
      Serial.print(F("Comando desconhecido: ")); Serial.println(p - 1); imprimeAjuda();
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
  pinMode(PIN_RGB_R, OUTPUT); pinMode(PIN_RGB_G, OUTPUT); pinMode(PIN_RGB_B, OUTPUT);
  escreveLed(PRETO);

  Serial.println(F("\nBraco robotico 4 GDL - firmware definitivo (09/11/2026) - iniciando..."));
  testaLed();                                                  // confere a fiação do LED antes de mexer nos servos
  for (uint8_t j = 0; j < N_JUNTAS; j++) {
    posAtual[j] = alvo[j] = limita(POS_REF[j], ANG_MIN[j], ANG_MAX[j]);
    if (!JUNTA_LIGADA[j]) continue;                            // junta desligada: sem attach, o pino fica em repouso
    anexaServo(j);
    delay(150);                                                // liga os servos em sequência (pico de corrente menor)
  }
  avisaJuntasDesligadas();
  delay(500);                                                  // espera os servos chegarem antes de ler os joysticks
  calibraJoysticks();                                          // joysticks devem estar soltos (centro)
  carregaEEPROM();
  Serial.println(F("Pronto."));
  imprimeAjuda();
  imprimePosicoes();
  imprimeLimites();
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

  if (modo == REPRODUZINDO)   passoReproducao();
  else if (seq != NENHUMA)    { passoSequencia(); avancaParaAlvo(); }
  else                        { leJoysticks(); avancaParaAlvo(); }   // MANUAL: joysticks incrementam o alvo
  atualizaLed();
  atualizaLedRgb();
  if (diagnostico) imprimeDiagnostico();
}
