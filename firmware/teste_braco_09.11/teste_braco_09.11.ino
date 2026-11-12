/*
 * ============================================================================
 *  TESTE DE SERVOS E JOYSTICKS — Braço Robótico 4 GDL (só para bancada; NÃO é o firmware do braço)
 *
 *  >> PROCEDÊNCIA (11/11/2026) — ESTE ARQUIVO É UMA RECONSTRUÇÃO <<
 *  O original de 07/11/2026 foi renomeado para teste_braco_09.11.ino, o que o tornou um arquivo não
 *  rastreado pelo git, e foi apagado em 09/11 na fusão do firmware — sem nunca ter sido commitado.
 *  Esta cópia foi remontada a partir da última versão que o git tinha (blob d076b30, de 29/10, já com
 *  o ajuste de bancada da garra em 50..95), reaplicando na mesma ordem os mesmos scripts de patch de
 *  07/11: LED RGB de estados -> repinagem para D2..D10 -> correções de comentário -> atalho do botão.
 *  Compila em 18864 bytes de flash e 604 de RAM no UNO: os MESMOS números do original, o que indica
 *  que o binário gerado é idêntico (o tamanho conta cada string F() e cada byte de código).
 *
 *  O FIRMWARE OFICIAL DO PROJETO é firmware/braco_robotico/braco_robotico.ino, que desde 09/11 já
 *  traz tudo que está aqui (LED RGB, 'x'/'liga', 'teste'/'varre', 'livre', 'limite'/'limites', 'led').
 *  Este sketch fica como referência histórica do desenvolvimento do LED. ATENÇÃO: os dois usam a
 *  MESMA pinagem (D2..D10), então gravar um ou outro não exige refiar nada.
 *  Placa: Arduino UNO (compila também para Nano, Mega e UNO R4). Biblioteca: Servo.h (vem com a IDE).
 *  Monitor Serial: 115200 bps, qualquer opção de fim de linha.
 * ----------------------------------------------------------------------------
 *  Ao ligar, NENHUM servo recebe pulso. Há dois jeitos de testar:
 *
 *  1) PELO MONITOR SERIAL, UM SERVO POR VEZ (os outros ficam sem sinal)
 *    s1 s2 s3 s4   seleciona o servo (desliga os outros) e leva o escolhido a 90°
 *    <número>      vai para esse ângulo (ex.: 45)         +  /  -   1° a mais / a menos  (+5, -10 ...)
 *    c             referência (90°)                       min / max   extremos da faixa
 *    t             teste automático: 90° -> mínimo -> máximo -> 90°, parando 1 s em cada ponto
 *    v             varredura contínua mínimo <-> máximo (qualquer comando interrompe)
 *    vel <n>       velocidade em graus/s (5..300, padrão 30)
 *    livre         alterna a faixa do servo <-> 0..180 (para medir limites; vá de 1 em 1 grau)
 *
 *  2) PELOS JOYSTICKS (mesma ligação e mesmo jeito de comandar do firmware do braço)
 *    j             liga o modo joystick com os 4 servos
 *    j 124         liga só os servos da lista (ex.: para testar sem um deles)
 *    j             (de novo) sai do modo joystick; os servos continuam segurando a posição
 *    Não toque nos joysticks ao mandar 'j': o centro de cada eixo é medido nessa hora.
 *    SW1 (botão do J1) = mostra as posições    SW2 (botão do J2) = todos voltam a 90°   (já no modo joystick)
 *
 *    ATALHO SEM PC: fora do modo joystick, um toque no botão de QUALQUER um dos dois joysticks faz o
 *    mesmo que o comando 'j' — liga os 4 servos e mede o centro dos eixos. Como apertar o KY-023
 *    empurra a alavanca e a inclina um pouco, o programa espera você SOLTAR o botão antes de medir.
 *
 *  GARRA (S4)
 *    abre / fecha  vai a 120° (aberta) / 70° (fechada); funciona também no modo joystick
 *
 *  LIMITES
 *    limite        marca a posição atual como limite do servo selecionado (abaixo de 90° = mínimo, acima = máximo)
 *    limites       mostra as linhas prontas para colar no firmware do braço (ANG_MIN, ANG_MAX e a garra)
 *
 *  SEMPRE
 *    Cada comando recebido é repetido na tela ("> s4"): se ele não aparecer, o comando não chegou à placa.
 *    x             corta o pulso de TODOS os servos (ficam soltos, sem torque)
 *    d             leitura crua dos joysticks e botões a cada 0,5 s (liga/desliga)
 *    p             estado atual        ?   esta ajuda
 *    led           repete o teste do LED RGB (vermelho, verde, azul, branco) e imprime a legenda das cores
 *
 *  LED RGB DE ESTADOS (R -> D8, G -> D9, B -> D10, pino comum no GND; 220 ohm em cada cor)
 *    branco, lampejo curto a cada 2 s  nenhum servo com pulso: tudo solto, sem torque (estado de partida)
 *    azul                              modo serial: o servo selecionado esta energizado e parado
 *    verde                             modo joystick: servos energizados e parados
 *    azul/verde piscando 5x por s      algum servo esta se movendo (a cor continua sendo a do modo)
 *    amarelo fixo                      medindo o centro dos joysticks: NAO toque nas alavancas
 *    ciano piscando                    teste automatico 't' ou varredura 'v' em curso
 *    magenta                           faixa LIVRE 0..180: os limites de software estao desligados
 *    vermelho piscando rapido          eixo de joystick reprovado na calibracao (aquela junta nao responde)
 *    lampejo amarelo                   pedido limitado pela faixa, ou limite marcado com 'limite'
 *    lampejo vermelho                  comando recusado (desconhecido ou fora de contexto)
 *    lampejo branco                    botao SW1/SW2 reconhecido no modo joystick
 *  Os 3 pinos sao usados em liga/desliga (7 cores), sem analogWrite: a biblioteca Servo ocupa o Timer1,
 *  que e justamente quem faz o PWM de D9 e D10 (= G e B). Liga/desliga ainda da uma cor sempre igual.
 *
 *    Servo  Pino  Junta      Joystick     Faixa
 *    S1     D2    base       J1-X (A0)    0..180
 *    S2     D3    ombro      J1-Y (A1)    0..110
 *    S3     D4    cotovelo   J2-Y (A3)    0..180   (no modelo 3D a palma encosta na plataforma a 148° dobrando sobre o braço)
 *    S4     D5    garra      J2-X (A2)    70..120  (70 = fechada, 120 = aberta)
 *    LED RGB  D8 (R) / D9 (G) / D10 (B)   estados do sketch; pino comum do LED no GND do Arduino
 *    Botões: SW1 -> D6, SW2 -> D7. Joysticks no +5V e GND do Arduino; servos na fonte externa (GND comum).
 *  Pinagem de 2026-11-07: os 9 sinais ocupam D2..D10 EM SEQUÊNCIA - D2 D3 D4 D5 = servos S1..S4,
 *  D6 D7 = botões SW1/SW2, D8 D9 D10 = LED RGB. Contando do RX<-0: do 3º ao 8º furo do bloco 0-7 e do
 *  1º ao 3º do bloco 8-13. Ficam livres os pinos 0 e 1 (RX/TX, não usar) e D11, D12, D13.
 *  O firmware do braço (braco_robotico.ino) usa exatamente os mesmos pinos: trocar de sketch não refia nada.
 *  O pulso usa a mesma escala do firmware do braço: 600 µs = 0°, 2400 µs = 180° (10 µs por grau).
 * ============================================================================
 */
#include <Servo.h>

const uint32_t SERIAL_BPS   = 115200;
const uint16_t PULSO_MIN_US = 600;      // 0°
const uint16_t PULSO_MAX_US = 2400;     // 180°
const uint16_t PERIODO_MS   = 20;       // passo da rampa (50 Hz, o mesmo período do pulso do servo)
const uint16_t PAUSA_MS     = 1000;     // parada em cada ponto do teste automático e da varredura

const uint8_t N_SERVOS = 4;
const uint8_t PINO[N_SERVOS]      = {   2,   3,   4,   5 };
const char*   NOME[N_SERVOS]      = { "S1 base", "S2 ombro", "S3 cotovelo", "S4 garra" };
//                                    base  ombro  cotovelo garra
uint8_t       limiteMin[N_SERVOS] = {   0,    0,     0,     50 };   // limites medidos na bancada
uint8_t       limiteMax[N_SERVOS] = { 180,  110,   180,    95 };   // (o comando 'limite' ajusta em tempo real)
const uint8_t COTOVELO = 2;
const int     COTOVELO_DOBRADO_MAX = 145;   // dobrando o antebraço sobre o braço, a palma bate na plataforma a 148°
const uint8_t GARRA = 3;                     // garra: limiteMin = fechada, limiteMax = aberta

// joysticks (mesma ligação e mesmas constantes do firmware do braço)
const uint8_t PIN_SW1 = 6, PIN_SW2 = 7;
const uint8_t PIN_EIXO[N_SERVOS]  = { A0, A1, A3, A2 };       // eixo que comanda cada servo
const char*   NOME_EIXO[N_SERVOS] = { "J1-X (A0)", "J1-Y (A1)", "J2-Y (A3)", "J2-X (A2)" };
const int8_t  SENTIDO[N_SERVOS]   = { 1, 1, 1, 1 };           // troque para -1 para inverter um eixo
const int     ZONA_MORTA = 60;          // counts do ADC ignorados em torno do centro
const float   VEL_JOY    = 2.0f;        // graus por passo de 20 ms com o joystick no fim de curso (100 °/s)
const int     CENTRO_TOL = 150;         // centro aceito: 512 ± 150 counts...
const int     RUIDO_MAX  = 40;          // ...com as 16 leituras variando no máximo isso

// LED RGB de estados: 3 pinos em liga/desliga = 7 cores. Nao usa analogWrite de proposito: a Servo ocupa
// o Timer1 do AVR, que e o gerador de PWM de D9 e D10 - exatamente os pinos de G e B. Em digitalWrite nao
// ha conflito nenhum, e D8/D9/D10 estao livres tanto aqui quanto no firmware do braco.
// Prefixo PIN_RGB_ de proposito: PIN_LED, LEDR, LEDG e LEDB sao macros de placa em varias placas
// (no UNO R4 "const uint8_t PIN_LED = 13;" nem compila) e o nome colidiria com a macro.
const uint8_t PIN_RGB_R = 8, PIN_RGB_G = 9, PIN_RGB_B = 10;
const bool    LED_ANODO_COMUM = false;  // false = catodo comum (perna comum no GND, o caso normal e o KY-016)
                                        // true  = anodo comum (perna comum no +5V): inverte os 3 pinos
const uint16_t LAMPEJO_MS = 400;        // duracao do lampejo de evento (amarelo/vermelho/branco)

enum Cor : uint8_t {                    // bit 0 = vermelho, bit 1 = verde, bit 2 = azul
  PRETO = 0, VERMELHO = 1, VERDE = 2, AMARELO = 3, AZUL = 4, MAGENTA = 5, CIANO = 6, BRANCO = 7
};

// estados sinalizados, do mais urgente para o menos (o primeiro que casar e o que aparece no LED)
enum EstadoLed : uint8_t {
  LED_FALHA,      // vermelho piscando rapido: eixo de joystick reprovado na calibracao
  LED_LIVRE,      // magenta: faixa LIVRE 0..180, sem limites de software
  LED_SEQUENCIA,  // ciano piscando: teste automatico ou varredura em curso
  LED_JOYSTICK,   // verde: modo joystick
  LED_SERIAL,     // azul: modo serial com o servo selecionado energizado
  LED_SOLTO       // branco, lampejo a cada 2 s: nenhum servo com pulso
};

enum Sequencia : uint8_t { NENHUMA, TESTE, VARREDURA };

Servo     servo[N_SERVOS];
bool      ligado[N_SERVOS];             // o servo está recebendo pulso
float     pos[N_SERVOS]  = { 90, 90, 90, 90 };   // graus
float     alvo[N_SERVOS] = { 90, 90, 90, 90 };
int8_t    atual = -1;                   // servo selecionado no modo serial (-1 = nenhum)
bool      faixaLivre = false;
float     velGrausS = 30;
bool      parado = true;
uint32_t  tChegada = 0;
Sequencia seq = NENHUMA;
uint8_t   passoSeq = 0;

bool      modoJoystick = false;
bool      joyAtivo[N_SERVOS];           // servo comandado pelo joystick
int       centro[N_SERVOS] = { 512, 512, 512, 512 };
bool      eixoOk[N_SERVOS];
bool      mudou = false;                // alguma posição mudou desde a última impressão
uint32_t  tImpressao = 0;

const uint8_t PIN_BOTAO[2] = { PIN_SW1, PIN_SW2 };
bool      botaoEstavel[2], botaoLeitura[2];

bool      diagnostico = false;
uint32_t  tDiagnostico = 0;

char      linha[24];
uint8_t   nLinha = 0;
uint32_t  tUltimoCaractere = 0;

uint8_t   corLampejo = PRETO;           // lampejo de evento: tem prioridade sobre a cor do estado
uint32_t  tLampejo   = 0;
uint16_t  msLampejo  = 0;

// ------------------------------------------------------------ utilidades
float limita(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
int   pulsoUs(float graus) { return (int)(PULSO_MIN_US + graus * ((PULSO_MAX_US - PULSO_MIN_US) / 180.0f) + 0.5f); }

// faixa e posição de referência de cada servo
float limInf(uint8_t i) { return limiteMin[i]; }
float limSup(uint8_t i) { return limiteMax[i]; }
float referencia(uint8_t i) { return limita(90, limInf(i), limSup(i)); }
float limMin() { return faixaLivre ? 0 : limInf(atual); }
float limMax() { return faixaLivre ? 180 : limSup(atual); }

void escreve(uint8_t i) { servo[i].writeMicroseconds(pulsoUs(pos[i])); }

void liga(uint8_t i) {
  if (ligado[i]) return;
  escreve(i);                                                  // AVR: o 1º pulso já sai na posição certa
  servo[i].attach(PINO[i], PULSO_MIN_US, PULSO_MAX_US);
  escreve(i);                                                  // outras placas só aceitam depois do attach
  ligado[i] = true;
}

void desliga(uint8_t i) {
  if (!ligado[i]) return;
  servo[i].detach();
  digitalWrite(PINO[i], LOW);
  ligado[i] = false;
  alvo[i] = pos[i];
}

void imprimePosicoes() {
  Serial.print(F("Posicoes:"));
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    Serial.print(F("  S")); Serial.print(i + 1); Serial.print('=');
    if (!ligado[i]) { Serial.print(F("solto")); continue; }
    Serial.print((int)(pos[i] + 0.5f));
  }
  Serial.println();
}

void imprimeLimites() {
  Serial.print(F("Limites:"));
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    Serial.print(F("  S")); Serial.print(i + 1); Serial.print(' ');
    Serial.print(limiteMin[i]); Serial.print(F("..")); Serial.print(limiteMax[i]);
  }
  Serial.println(F("   (garra: fechada = minimo, aberta = maximo)"));
}

void seleciona(uint8_t i) {
  for (uint8_t k = 0; k < N_SERVOS; k++) if (k != i) desliga(k);
  atual = i; faixaLivre = false;
  pos[i] = alvo[i] = referencia(i); parado = true;
  if (ligado[i]) escreve(i); else liga(i);
  Serial.print(F("Selecionado ")); Serial.print(NOME[i]); Serial.print(F(" (pino D")); Serial.print(PINO[i]);
  Serial.print(F("), faixa ")); Serial.print((int)limInf(i)); Serial.print(F("..")); Serial.print((int)limSup(i));
  Serial.print(F(". Foi para ")); Serial.print((int)pos[i]); Serial.println(F(" graus; os outros servos estao sem pulso."));
}

void vaiPara(float graus) {
  if (atual < 0) { Serial.println(F("Nenhum servo selecionado: digite s1, s2, s3 ou s4 (garra = s4), ou j para os joysticks.")); return; }
  if (!ligado[atual]) { liga(atual); Serial.println(F("Pulso religado.")); }
  alvo[atual] = limita(graus, limMin(), limMax());
  parado = false;
  Serial.print(F("-> ")); Serial.print(alvo[atual], 1); Serial.print(F(" graus (")); Serial.print(pulsoUs(alvo[atual])); Serial.print(F(" us)"));
  if (alvo[atual] != graus) { lampeja(AMARELO, LAMPEJO_MS); Serial.print(F("  [limitado a ")); Serial.print((int)limMin()); Serial.print(F("..")); Serial.print((int)limMax()); Serial.print(']'); }
  Serial.println();
}

// ------------------------------------------------------------ limites e linhas para o firmware do braço
void imprimeAlinhado(int v, uint8_t largura) {
  uint8_t n = v >= 100 ? 3 : (v >= 10 ? 2 : 1);
  for (uint8_t k = n; k < largura; k++) Serial.print(' ');
  Serial.print(v);
}

void imprimeVetor(bool minimo) {
  Serial.print(minimo ? F("const uint8_t ANG_MIN[N_JUNTAS]  = {") : F("const uint8_t ANG_MAX[N_JUNTAS]  = {"));
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    imprimeAlinhado((int)(minimo ? limInf(i) : limSup(i)), i == 0 ? 4 : 6);
    Serial.print(i < N_SERVOS - 1 ? ',' : ' ');
  }
  Serial.println(F("};"));
}

void imprimeLinhasFirmware() {
  Serial.println(F("Linhas para o firmware do braco (braco_robotico.ino) - substitua as que existem:"));
  imprimeVetor(true);
  imprimeVetor(false);
  Serial.print(F("const uint8_t GARRA_FECHADA = ")); Serial.print((int)limInf(GARRA));
  Serial.print(F(", GARRA_ABERTA = ")); Serial.print((int)limSup(GARRA)); Serial.println(';');
}

// marca a posição atual como limite do servo selecionado: abaixo de 90° = mínimo, acima = máximo
void marcaLimite() {
  if (atual < 0 || !ligado[atual]) { lampeja(VERMELHO, LAMPEJO_MS); Serial.println(F("Selecione o servo (s1..s4) e leve-o ate uns 5 graus antes de encostar.")); return; }
  if (pos[atual] != alvo[atual]) { lampeja(VERMELHO, LAMPEJO_MS); Serial.println(F("O servo ainda esta se movendo: espere ele parar e mande 'limite' de novo.")); return; }
  int a = (int)(pos[atual] + 0.5f);
  if (a == 90) { lampeja(VERMELHO, LAMPEJO_MS); Serial.println(F("Afaste-se de 90 graus: abaixo de 90 marca o minimo, acima marca o maximo.")); return; }
  if (a < 90) limiteMin[atual] = a; else limiteMax[atual] = a;
  lampeja(AMARELO, LAMPEJO_MS);
  Serial.print(NOME[atual]); Serial.print(a < 90 ? F(": minimo agora ") : F(": maximo agora ")); Serial.print(a);
  Serial.print(F(" (faixa ")); Serial.print(limiteMin[atual]); Serial.print(F("..")); Serial.print(limiteMax[atual]); Serial.println(F(")."));
  if (atual == COTOVELO && (a > COTOVELO_DOBRADO_MAX || a < 180 - COTOVELO_DOBRADO_MAX)) {
    Serial.println(F("  ATENCAO: do lado em que o antebraco DOBRA sobre o braco, no modelo 3D a palma bate na plataforma a 148."));
  }
}

void imprimeEstado() {
  if (modoJoystick) {
    Serial.print(F("Modo JOYSTICK, servos comandados:"));
    for (uint8_t i = 0; i < N_SERVOS; i++) if (joyAtivo[i]) { Serial.print(F(" S")); Serial.print(i + 1); }
    Serial.println();
  } else if (atual < 0) {
    Serial.println(F("Modo serial, nenhum servo selecionado."));
  } else {
    Serial.print(NOME[atual]); Serial.print(F(" (D")); Serial.print(PINO[atual]); Serial.print(F(")  pulso "));
    Serial.print(ligado[atual] ? F("LIGADO") : F("DESLIGADO"));
    Serial.print(F("  posicao ")); Serial.print(pos[atual], 1); Serial.print(F(" graus = ")); Serial.print(pulsoUs(pos[atual])); Serial.print(F(" us"));
    Serial.print(F("  alvo ")); Serial.print(alvo[atual], 1);
    Serial.print(F("  faixa ")); Serial.print((int)limMin()); Serial.print(F("..")); Serial.print((int)limMax());
    Serial.print(faixaLivre ? F(" (LIVRE)") : F(""));
    Serial.print(F("  vel ")); Serial.print((int)velGrausS); Serial.println(F(" graus/s"));
  }
  imprimePosicoes();
  imprimeLimites();
  imprimeEstadoLed();
}

void imprimeAjuda() {
  Serial.println(F("Serial (um servo): s1..s4 seleciona | <angulo> ex. 45 | + - (+5 -10) | c referencia | min | max"));
  Serial.println(F("                   t teste 90->min->max->90 | v varredura | vel <graus/s> | livre 0..180"));
  Serial.println(F("Joysticks: j liga com os 4 servos (S1..S4) | j 124 so os listados | j de novo sai | SW1 posicoes | SW2 a 90"));
  Serial.println(F("           sem PC: fora do modo joystick, um toque em SW1 ou SW2 ja faz o mesmo que 'j'"));
  Serial.println(F("Garra: abre (120) | fecha (70)    Limites: limite (marca o atual) | limites = linhas p/ o firmware"));
  Serial.println(F("Sempre: x solta todos | d leitura crua dos joysticks | p estado | led testa o LED RGB | ? ajuda"));
  imprimeLegendaLed();
}

// ------------------------------------------------------------ LED RGB de estados
void escreveLed(uint8_t cor) {
  bool r = cor & VERMELHO, g = cor & VERDE, b = cor & AZUL;
  if (LED_ANODO_COMUM) { r = !r; g = !g; b = !b; }    // anodo comum: o pino puxa para o GND para acender
  digitalWrite(PIN_RGB_R, r);
  digitalWrite(PIN_RGB_G, g);
  digitalWrite(PIN_RGB_B, b);
}

// lampejo de evento: sobrepoe a cor do estado por alguns centesimos de segundo (sem travar o loop)
void lampeja(uint8_t cor, uint16_t ms) { corLampejo = cor; msLampejo = ms; tLampejo = millis(); }

EstadoLed estadoLed() {
  if (modoJoystick) {
    for (uint8_t i = 0; i < N_SERVOS; i++) if (joyAtivo[i] && !eixoOk[i]) return LED_FALHA;
  }
  if (faixaLivre && atual >= 0 && ligado[atual]) return LED_LIVRE;
  if (seq != NENHUMA)                            return LED_SEQUENCIA;
  if (modoJoystick)                              return LED_JOYSTICK;
  if (atual >= 0 && ligado[atual])               return LED_SERIAL;
  return LED_SOLTO;
}

// cor = modo, piscar = atividade. Chamada a cada 20 ms; nao usa delay()
void atualizaLed() {
  uint32_t ms = millis();
  if (ms - tLampejo < msLampejo) { escreveLed(corLampejo); return; }

  bool movendo = false;
  for (uint8_t i = 0; i < N_SERVOS; i++) if (ligado[i] && pos[i] != alvo[i]) movendo = true;

  uint8_t  cor     = BRANCO;
  uint16_t periodo = 0, aceso = 0;                   // periodo 0 = cor fixa
  switch (estadoLed()) {
    case LED_FALHA:     cor = VERMELHO; periodo =  300; aceso = 150; break;
    case LED_SEQUENCIA: cor = CIANO;    periodo =  600; aceso = 300; break;
    case LED_LIVRE:     cor = MAGENTA;  break;
    case LED_JOYSTICK:  cor = VERDE;    break;
    case LED_SERIAL:    cor = AZUL;     break;
    default:            cor = BRANCO;   periodo = 2000; aceso =  80; break;   // LED_SOLTO
  }
  if (!periodo && movendo) { periodo = 200; aceso = 100; }   // mexendo: a cor do modo pisca rapido
  escreveLed((!periodo || ms % periodo < aceso) ? cor : (uint8_t)PRETO);
}

// teste de fiacao: acende cada cor por 400 ms dizendo qual deveria ser
void testaLed() {
  Serial.print(F("Teste do LED RGB (D8=R, D9=G, D10=B): vermelho"));
  escreveLed(VERMELHO); delay(400);
  Serial.print(F(", verde"));  escreveLed(VERDE);  delay(400);
  Serial.print(F(", azul"));   escreveLed(AZUL);   delay(400);
  Serial.println(F(", branco.")); escreveLed(BRANCO); delay(400);
  escreveLed(PRETO);
  Serial.println(F("  Cor trocada = pinos R/G/B trocados. Acende o contrario do dito = mude LED_ANODO_COMUM no codigo."));
  Serial.println(F("  Nao acende nada = perna comum sem GND, resistor solto ou LED ao contrario."));
}

void imprimeLegendaLed() {
  Serial.println(F("LED RGB: branco (lampejo a cada 2 s) nada energizado | azul serial | verde joystick | piscando = movendo"));
  Serial.println(F("         amarelo fixo = medindo o centro dos joysticks | ciano = teste/varredura | magenta = faixa LIVRE"));
  Serial.println(F("         vermelho rapido = eixo de joystick reprovado | lampejo: amarelo limite, vermelho recusado, branco botao"));
}

void imprimeEstadoLed() {
  Serial.print(F("LED: "));
  switch (estadoLed()) {
    case LED_FALHA:     Serial.println(F("vermelho piscando (eixo de joystick reprovado)")); break;
    case LED_LIVRE:     Serial.println(F("magenta (faixa LIVRE 0..180)")); break;
    case LED_SEQUENCIA: Serial.println(F("ciano piscando (sequencia em curso)")); break;
    case LED_JOYSTICK:  Serial.println(F("verde (modo joystick)")); break;
    case LED_SERIAL:    Serial.println(F("azul (modo serial, servo energizado)")); break;
    default:            Serial.println(F("branco em lampejos (nenhum servo com pulso)")); break;
  }
}

// ------------------------------------------------------------ garra
// abre / fecha a garra; no modo joystick não tira o controle dos joysticks
void moveGarra(bool abrir) {
  float a = abrir ? limSup(GARRA) : limInf(GARRA);
  if (modoJoystick) {
    if (!ligado[GARRA]) { Serial.println(F("A garra esta sem pulso neste modo (use j 4 ou j).")); return; }
    alvo[GARRA] = a;
    Serial.print(abrir ? F("Garra abrindo (") : F("Garra fechando (")); Serial.print((int)a); Serial.println(F(" graus)."));
    return;
  }
  if (atual != GARRA) seleciona(GARRA);
  vaiPara(a);
}

// ------------------------------------------------------------ sequências (teste automático e varredura)
void proximoPassoSequencia() {
  if (seq == TESTE) {
    if (passoSeq >= 4) { seq = NENHUMA; Serial.println(F("Teste concluido.")); return; }
    float pontos[4] = { referencia(atual), limMin(), limMax(), referencia(atual) };
    const char* nomes[4] = { "referencia", "minimo", "maximo", "referencia" };
    Serial.print(F("Teste ")); Serial.print(passoSeq + 1); Serial.print(F("/4 (")); Serial.print(nomes[passoSeq]); Serial.print(F(") "));
    vaiPara(limita(pontos[passoSeq], limMin(), limMax()));
    passoSeq++;
  } else if (seq == VARREDURA) {
    vaiPara((passoSeq++ % 2) ? limMin() : limMax());
  }
}

void iniciaSequencia(Sequencia s) {
  if (atual < 0) { Serial.println(F("Nenhum servo selecionado: digite s1, s2, s3 ou s4 (garra = s4) antes do t / v.")); return; }
  seq = s; passoSeq = 0;
  Serial.println(s == TESTE ? F("Teste automatico (qualquer comando interrompe):") : F("Varredura continua (qualquer comando interrompe):"));
  proximoPassoSequencia();
}

// ------------------------------------------------------------ joysticks
// mede o centro de cada eixo com as alavancas soltas; eixo fora de 512 ± 150 ou instável fica desativado
void calibraJoysticks() {
  Serial.print(F("Centro dos joysticks:"));
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    long soma = 0; int menor = 1023, maior = 0;
    for (uint8_t k = 0; k < 16; k++) {
      int v = analogRead(PIN_EIXO[i]);
      soma += v;
      if (v < menor) menor = v;
      if (v > maior) maior = v;
      delay(2);
    }
    centro[i] = soma / 16;
    int desvio = centro[i] - 512;
    eixoOk[i] = (desvio >= -CENTRO_TOL && desvio <= CENTRO_TOL && maior - menor <= RUIDO_MAX);
    Serial.print(' '); Serial.print(NOME_EIXO[i]); Serial.print('='); Serial.print(centro[i]);
    if (!eixoOk[i]) Serial.print(F("(DESATIVADO)"));
  }
  Serial.println();
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    if (eixoOk[i] || !joyAtivo[i]) continue;
    Serial.print(F("ATENCAO: ")); Serial.print(NOME_EIXO[i]); Serial.print(F(" leu ")); Serial.print(centro[i]);
    Serial.print(F(" (esperado ~512): ")); Serial.print(NOME[i]); Serial.println(F(" nao vai responder ao joystick."));
    Serial.println(F("  Alavanca inclinada, fio solto/trocado ou joystick sem +5V/GND. Solte as alavancas e mande 'j' de novo."));
  }
}

void iniciaJoystick(const char *lista) {
  bool algum = false;
  for (uint8_t i = 0; i < N_SERVOS; i++) joyAtivo[i] = false;
  for (const char *c = lista; *c; c++) if (*c >= '1' && *c <= '4') { joyAtivo[*c - '1'] = true; algum = true; }
  if (!algum) for (uint8_t i = 0; i < N_SERVOS; i++) joyAtivo[i] = true;
  seq = NENHUMA; atual = -1; faixaLivre = false;

  escreveLed(AMARELO);                               // amarelo fixo enquanto mede o centro: nao toque
  Serial.println(F("Modo joystick: ligando os servos (nao toque nos joysticks)..."));
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    if (!joyAtivo[i]) { desliga(i); continue; }
    if (!ligado[i]) { pos[i] = alvo[i] = referencia(i); liga(i); delay(150); }   // um de cada vez
    else alvo[i] = limita(pos[i], limInf(i), limSup(i));
  }
  delay(500);                                                  // espera os servos pararem antes de medir o centro
  calibraJoysticks();
  modoJoystick = true; mudou = false;
  Serial.print(F("Joystick comanda:"));
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    if (!joyAtivo[i]) continue;
    Serial.print(F("  ")); Serial.print(NOME_EIXO[i]); Serial.print(F(" -> ")); Serial.print(NOME[i]);
    if (!eixoOk[i]) Serial.print(F(" (eixo desativado)"));
  }
  Serial.println();
  Serial.println(F("SW1 = mostra posicoes | SW2 = todos a 90 | abre / fecha = garra | 'j' sai | 'x' solta todos"));
  imprimePosicoes();
}

void saiJoystick() {
  modoJoystick = false;
  Serial.println(F("Modo joystick desligado. Os servos continuam segurando a posicao ('x' solta todos)."));
}

// controle incremental, igual ao firmware do braço: deflexão -> incremento de ângulo por passo
void leJoysticks() {
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    if (!joyAtivo[i] || !eixoOk[i] || !ligado[i]) continue;
    int d = analogRead(PIN_EIXO[i]) - centro[i];
    int ad = d < 0 ? -d : d;
    if (ad < ZONA_MORTA) continue;
    float n = limita((ad - ZONA_MORTA) / (512.0f - ZONA_MORTA), 0.0f, 1.0f);
    alvo[i] = limita(alvo[i] + VEL_JOY * n * n * (d > 0 ? 1 : -1) * SENTIDO[i], limInf(i), limSup(i));
  }
}

// lido a cada 20 ms: a mudança só vale quando duas leituras seguidas concordam (filtra o repique do contato)
bool botaoApertou(uint8_t b) {
  bool l = (digitalRead(PIN_BOTAO[b]) == LOW);
  bool apertou = false;
  if (l == botaoLeitura[b] && l != botaoEstavel[b]) { botaoEstavel[b] = l; apertou = l; }
  botaoLeitura[b] = l;
  return apertou;
}

// o SW do KY-023 fica no proprio eixo: apertar empurra a alavanca e a inclina. Antes de medir o centro
// espera o botao soltar e mais 150 ms de sossego, senao a calibracao guarda um centro deslocado e o
// eixo pode ate ser reprovado (512 +- 150). Teto de 3 s para um botao preso nao travar a bancada.
void esperaBotoesSoltos() {
  uint32_t t0 = millis();
  while (millis() - t0 < 3000) {
    if (digitalRead(PIN_SW1) == HIGH && digitalRead(PIN_SW2) == HIGH) {
      delay(150);
      if (digitalRead(PIN_SW1) == HIGH && digitalRead(PIN_SW2) == HIGH) return;
    }
    delay(5);
  }
  Serial.println(F("  ATENCAO: botao continua apertado (fio em curto com o GND?). Medindo o centro assim mesmo."));
}

void trataBotoes() {
  bool sw1 = botaoApertou(0), sw2 = botaoApertou(1);
  if (!modoJoystick) {
    // fora do modo joystick os botoes nao tinham funcao: agora um toque faz o mesmo que o comando 'j'
    // (liga os 4 servos e calibra), para operar a bancada sem o Monitor Serial. Tambem interrompe uma
    // sequencia 't'/'v' em curso, porque iniciaJoystick() zera seq.
    if (sw1 || sw2) {
      Serial.print(F("> "));
      Serial.print(sw1 ? F("SW1") : F("SW2"));
      Serial.println(F(" (botao do joystick): ligando o modo joystick, igual ao comando 'j'. Solte o botao."));
      escreveLed(BRANCO);                            // confirma que o toque foi lido
      esperaBotoesSoltos();
      iniciaJoystick("");                            // "" = os 4 servos; acende amarelo enquanto mede
    }
    return;
  }
  if (sw1 || sw2) lampeja(BRANCO, 150);              // confirma no LED que o botao foi lido
  if (sw1) { Serial.print(F("SW1 -> ")); imprimePosicoes(); }
  if (sw2) {
    for (uint8_t i = 0; i < N_SERVOS; i++) if (joyAtivo[i] && ligado[i]) alvo[i] = referencia(i);
    Serial.println(F("SW2 -> todos voltando a 90 graus"));
  }
}

void imprimeDiagnostico() {
  if (millis() - tDiagnostico < 500) return;
  tDiagnostico = millis();
  Serial.print(F("diag:"));
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    Serial.print(F("  ")); Serial.print(NOME_EIXO[i]); Serial.print('='); Serial.print(analogRead(PIN_EIXO[i]));
  }
  Serial.print(F("  SW1=")); Serial.print(digitalRead(PIN_SW1) == LOW ? F("apertado") : F("solto"));
  Serial.print(F("  SW2=")); Serial.println(digitalRead(PIN_SW2) == LOW ? F("apertado") : F("solto"));
}

// ------------------------------------------------------------ movimento
// rampa: aproxima cada posição do alvo; no modo serial avisa quando o servo selecionado chega
void passoMovimento() {
  float passo = velGrausS * PERIODO_MS / 1000.0f;
  if (modoJoystick && passo < VEL_JOY) passo = VEL_JOY;      // o joystick nunca fica mais lento que no braço
  for (uint8_t i = 0; i < N_SERVOS; i++) {
    if (!ligado[i]) continue;
    float d = alvo[i] - pos[i];
    if (d > passo) pos[i] += passo; else if (d < -passo) pos[i] -= passo; else pos[i] = alvo[i];
    if (d != 0) mudou = true;
    escreve(i);
  }
  if (modoJoystick) {
    if (mudou && millis() - tImpressao >= 300) { imprimePosicoes(); tImpressao = millis(); mudou = false; }
    return;
  }
  if (atual < 0 || !ligado[atual]) return;
  if (!parado && pos[atual] == alvo[atual]) {
    parado = true; tChegada = millis();
    Serial.print(F("   chegou em ")); Serial.print(pos[atual], 1); Serial.println(F(" graus"));
  }
  if (seq != NENHUMA && parado && millis() - tChegada >= PAUSA_MS) proximoPassoSequencia();
}

// ------------------------------------------------------------ comandos seriais
void executaComando() {
  linha[nLinha] = '\0';
  nLinha = 0;
  char *p = linha;
  while (*p == ' ' || *p == '\t') p++;
  for (char *q = p; *q; q++) if (*q >= 'A' && *q <= 'Z') *q += 'a' - 'A';
  for (char *q = p + strlen(p); q > p && q[-1] == ' '; ) *--q = '\0';
  if (*p == '\0') return;
  Serial.print(F("> ")); Serial.println(p);                    // eco: mostra que o comando chegou à placa

  bool consulta = !strcmp(p, "p") || !strcmp(p, "?") || !strcmp(p, "d") || !strcmp(p, "limites")
               || !strcmp(p, "led")
               || (modoJoystick && (!strcmp(p, "abre") || !strcmp(p, "fecha")));
  if (!consulta && seq != NENHUMA) { seq = NENHUMA; Serial.println(F("(sequencia interrompida)")); }

  if (p[0] == 'j' && (p[1] == '\0' || p[1] == ' ' || (p[1] >= '1' && p[1] <= '4'))) {
    if (modoJoystick && p[1] == '\0') saiJoystick(); else iniciaJoystick(p + 1);
    return;
  }
  if (!consulta && modoJoystick) saiJoystick();                // comando serial assume o controle

  if (p[0] == 's' && p[1] >= '1' && p[1] <= '4' && p[2] == '\0') seleciona(p[1] - '1');
  else if (p[0] == 's' && p[1] == ' ')
    Serial.println(F("Aqui e s1 base, s2 ombro, s3 cotovelo, s4 garra (sem espaco); depois digite o angulo. Ex.: s4 e depois 75. ('s 3 75' e do firmware do braco.)"));
  else if (p[0] >= '0' && p[0] <= '9') vaiPara(atof(p));
  else if (p[0] == '+' || p[0] == '-') {
    float n = p[1] ? atof(p + 1) : 1;
    if (atual >= 0) vaiPara(alvo[atual] + (p[0] == '+' ? n : -n)); else vaiPara(0);
  }
  else if (!strcmp(p, "c"))        { if (atual >= 0) vaiPara(referencia(atual)); else vaiPara(0); }
  else if (!strcmp(p, "min"))      { if (atual >= 0) vaiPara(limMin()); else vaiPara(0); }
  else if (!strcmp(p, "max"))      { if (atual >= 0) vaiPara(limMax()); else vaiPara(0); }
  else if (!strcmp(p, "t"))        iniciaSequencia(TESTE);
  else if (!strcmp(p, "v"))        iniciaSequencia(VARREDURA);
  else if (!strcmp(p, "abre"))     moveGarra(true);
  else if (!strcmp(p, "fecha"))    moveGarra(false);
  else if (!strcmp(p, "limite"))   marcaLimite();
  else if (!strcmp(p, "limites"))  { imprimeLimites(); imprimeLinhasFirmware(); }
  else if (!strncmp(p, "vel", 3)) {
    if (p[3]) velGrausS = limita(atof(p + 3), 5, 300);
    Serial.print(F("Velocidade: ")); Serial.print((int)velGrausS); Serial.println(F(" graus/s"));
  }
  else if (!strcmp(p, "x")) {
    for (uint8_t i = 0; i < N_SERVOS; i++) desliga(i);
    parado = true;
    Serial.println(F("Pulso cortado em todos os servos: soltos (sem torque)."));
  }
  else if (!strcmp(p, "livre")) {
    if (atual < 0) { Serial.println(F("Nenhum servo selecionado.")); return; }
    faixaLivre = !faixaLivre;
    if (faixaLivre) Serial.println(F("Faixa LIVRE 0..180 - va de 1 em 1 grau: no braco a peca pode bater ('x' solta)."));
    else { Serial.println(F("Faixa do servo restaurada.")); vaiPara(alvo[atual]); }
  }
  else if (!strcmp(p, "d")) {
    diagnostico = !diagnostico; tDiagnostico = 0;
    Serial.println(diagnostico ? F("Leitura crua LIGADA (centro ~512; mexendo vai de ~0 a ~1023). 'd' desliga.") : F("Leitura crua desligada."));
  }
  else if (!strcmp(p, "p")) imprimeEstado();
  else if (!strcmp(p, "?")) imprimeAjuda();
  else if (!strcmp(p, "led")) { testaLed(); imprimeLegendaLed(); imprimeEstadoLed(); }
  else { lampeja(VERMELHO, 600); Serial.print(F("Comando desconhecido: ")); Serial.println(p); imprimeAjuda(); }
}

// junta caracteres até NL/CR; em "Nenhum final de linha" executa após 100 ms sem novos caracteres
void trataSerial() {
  while (Serial.available()) {
    char ch = Serial.read();
    tUltimoCaractere = millis();
    if (ch == '\n' || ch == '\r') { executaComando(); continue; }
    if (nLinha < sizeof(linha) - 1) linha[nLinha++] = ch;
  }
  if (nLinha && millis() - tUltimoCaractere > 100) executaComando();
}

// ------------------------------------------------------------ setup / loop
void setup() {
  for (uint8_t i = 0; i < N_SERVOS; i++) { pinMode(PINO[i], OUTPUT); digitalWrite(PINO[i], LOW); }   // sem pulso
  pinMode(PIN_SW1, INPUT_PULLUP);
  pinMode(PIN_SW2, INPUT_PULLUP);
  pinMode(PIN_RGB_R, OUTPUT); pinMode(PIN_RGB_G, OUTPUT); pinMode(PIN_RGB_B, OUTPUT);
  escreveLed(PRETO);
  Serial.begin(SERIAL_BPS);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 2000) {}                   // placas com USB nativo (UNO R4, Leonardo)
  Serial.println(F("\nTESTE DE SERVOS E JOYSTICKS - nenhum servo com pulso."));
  Serial.println(F("Digite s1..s4 ou j - ou simplesmente aperte o botao de um dos joysticks."));
  imprimeAjuda();
  imprimeLimites();
  testaLed();
}

void loop() {
  static uint32_t tUltimo = 0;
  trataSerial();
  if (millis() - tUltimo < PERIODO_MS) return;
  tUltimo = millis();
  trataBotoes();
  if (modoJoystick) leJoysticks();
  passoMovimento();
  atualizaLed();
  if (diagnostico) imprimeDiagnostico();
}