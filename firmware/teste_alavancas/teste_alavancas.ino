/*
 * ============================================================================
 *  TESTE DAS ALAVANCAS — Braço Robótico 4 GDL
 *  Sketch de DIAGNÓSTICO, mínimo de propósito. Não é o firmware do braço.
 *
 *  POR QUE ELE EXISTE (20/11/2026)
 *  Sintoma: S1 (base) e S4 (garra) não respondem, nos dois .ino do projeto.
 *  Olhando a ligação, essas duas juntas são comandadas justamente pelos dois
 *  eixos X dos joysticks — e o firmware DESLIGA sozinho, em silêncio, qualquer
 *  eixo cujo centro não fique em 512 ± 150 counts ou que esteja ruidoso
 *  (é o `eixoOk[]` / `eixoAtivo[]`, posto ali em 20/10/2026 para a junta não
 *  disparar sozinha até o limite). Um eixo reprovado faz exatamente o que você
 *  descreve: o servo energiza, segura a posição e ignora a alavanca.
 *
 *        junta          eixo do joystick   pino analógico
 *        S1 base        J1-VRx             A0      <-- não responde
 *        S2 ombro       J1-VRy             A1
 *        S3 cotovelo    J2-VRy             A3
 *        S4 garra       J2-VRx             A2      <-- não responde
 *
 *  Este sketch tira TODAS as camadas de software do caminho: não tem
 *  calibração, não tem zona morta, não tem `eixoOk`, não tem limites, não tem
 *  máquina de estados, EEPROM, LED nem interpretador de comandos. Ele só lê os
 *  4 eixos e os 2 botões e mostra os números crus. Com isso o teste é direto:
 *
 *    - se A0 e A2 NÃO variam quando você move as alavancas  -> é fiação
 *      (fio do VRx solto, trocado ou no furo errado; ou o módulo sem +5V/GND);
 *    - se A0 e A2 variam de 0 a 1023 normalmente aqui       -> é software, e
 *      o culpado é a reprovação do eixo na calibração: no firmware mande 'j'
 *      com as alavancas soltas e leia a linha "Centro dos joysticks".
 *
 *  COMO USAR
 *  1. Grave e abra o Monitor Serial em 115200 bps.
 *  2. Não toque em nada: ele imprime o centro de repouso dos 4 eixos e
 *     fica QUIETO. A medição continua rodando em silêncio, a 50 Hz.
 *  3. Mova UMA alavanca de cada vez até o fim de curso, nos dois sentidos.
 *     Só sai UMA linha por eixo, quando ele responde pela primeira vez.
 *  4. Aperte os dois botões (SW = apertar a própria alavanca para baixo).
 *  5. Mande 'r': o relatório sai num bloco que PARA na tela, com tudo o que
 *     interessa (repouso, mínimo, máximo, variação e veredito por eixo).
 *     Pode selecionar com o mouse e copiar com Ctrl+C. A última linha do
 *     bloco é um RESUMO de uma linha, se for mais fácil transcrever.
 *
 *  A tela NÃO rola sozinha de propósito: a versão anterior deste sketch
 *  imprimia 4 linhas por segundo e não dava para copiar nada. Se quiser ver
 *  os números ao vivo enquanto mexe na alavanca, mande 'v' (e 'v' de novo
 *  para calar). O relatório não depende disso.
 *
 *  COMANDOS (uma letra, sem fim de linha obrigatório)
 *    r   relatório: tabela de mínimo/máximo por eixo + veredito + resumo
 *    z   zera os mínimos e máximos e começa a medir de novo
 *    v   liga/desliga a leitura ao vivo (começa DESLIGADA: tela quieta)
 *    m   liga/desliga o espelho nos servos (começa DESLIGADO: nenhum pulso)
 *
 *  O ESPELHO ('m') é opcional e serve para o segundo teste: cada eixo passa a
 *  comandar o seu servo em posição ABSOLUTA (alavanca no centro = meio da
 *  faixa), sem calibração nenhuma no meio do caminho. Se a junta seguir a
 *  alavanca aqui e não seguir no firmware, está provado que o problema é a
 *  calibração — e não o servo, o pino ou o fio de sinal.
 *  Os ângulos ficam presos na faixa segura de cada junta (as mesmas de
 *  ANG_MIN/ANG_MAX do firmware) e o movimento é limitado a 2°/20 ms para a
 *  junta não dar um tranco ao ligar.
 *
 *  LIGAÇÃO (a de 19/11/2026, igual à do firmware oficial e do sketch de bancada)
 *    Servos:  S1 -> D12   S2 -> D3   S3 -> D4   S4 -> D13
 *    Botões:  SW1 -> D6   SW2 -> D7  (INPUT_PULLUP: apertado = LOW)
 *    Eixos:   J1 VRx -> A0   J1 VRy -> A1   J2 VRx -> A2   J2 VRy -> A3
 *    Joysticks no +5V e no GND do ARDUINO; servos na fonte externa, GND comum.
 *  Se o braço ainda estiver fiado na pinagem antiga, troque PINO[] para
 *  { 2, 3, 4, 5 }. Para o teste das alavancas o PINO[] não importa: com o
 *  espelho desligado nenhum servo recebe pulso.
 *
 *  ATENÇÃO AO D13: é o pino do LED da placa e o bootloader o pulsa como SCK a
 *  cada reset/gravação — a garra dá um tranco de ~1 s ao ligar ou gravar.
 *  Grave com a garra vazia.
 *
 *  Placa: Arduino UNO (compila também para Nano e Mega). Biblioteca: Servo.h.
 * ============================================================================
 */
#include <Servo.h>

const uint32_t SERIAL_BPS = 115200;
const uint8_t  N = 4;                      // 4 eixos = 4 juntas

// ---------------------------------------------------------------- ligação
const uint8_t PIN_EIXO[N] = { A0, A1, A3, A2 };   // na ordem das juntas: S1 S2 S3 S4
const uint8_t PINO[N]     = { 12,  3,  4, 13 };   // servo de cada junta (só usado com o espelho ligado)
const uint8_t PIN_SW1 = 6, PIN_SW2 = 7;

const char* NOME[N] = { "S1 base    ", "S2 ombro   ", "S3 cotovelo", "S4 garra   " };
const char* EIXO[N] = { "A0 J1-VRx", "A1 J1-VRy", "A3 J2-VRy", "A2 J2-VRx" };

// faixa segura de cada junta (as mesmas de ANG_MIN/ANG_MAX do firmware oficial)
const uint8_t ANG_MIN[N] = {   5,  15,  40,  74 };
const uint8_t ANG_MAX[N] = { 175, 165, 140, 110 };

// ---------------------------------------------------------------- medição
const uint16_t PERIODO_MS   = 20;     // intervalo de amostragem (= período do pulso do servo)
const uint16_t IMPRIME_MS   = 250;    // intervalo da linha de leitura
const int      VARIACAO_OK  = 300;    // counts de variação que provam que o eixo responde
const int      CENTRO_TOL   = 150;    // mesma tolerância do firmware: centro aceito = 512 ± 150
const uint8_t  PASSO_MAX    = 2;      // graus por passo de 20 ms no espelho

int  leitura[N];
int  minimo[N], maximo[N];
bool respondeu[N];
int  repouso[N];                      // primeira leitura, com as alavancas soltas

Servo servo[N];
bool  espelho = false;
int   pos[N];

bool  aoVivo = false;          // leitura ao vivo DESLIGADA por padrão: a tela precisa ficar parada
                               // para o relatório poder ser selecionado e copiado

uint32_t tAmostra = 0, tImprime = 0;
bool     swAnterior[2] = { false, false };

// ---------------------------------------------------------------- utilidades
int limita(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }

void zeraMedicao() {
  for (uint8_t i = 0; i < N; i++) {
    leitura[i] = analogRead(PIN_EIXO[i]);
    minimo[i] = maximo[i] = leitura[i];
    respondeu[i] = false;
  }
  Serial.println(F("Minimos e maximos zerados: mova as alavancas de novo."));
}

void imprimeRepouso() {
  Serial.println(F("Leitura com as alavancas SOLTAS (o firmware espera 512, e reprova fora de 512 +/- 150):"));
  for (uint8_t i = 0; i < N; i++) {
    repouso[i] = analogRead(PIN_EIXO[i]);
    Serial.print(F("  ")); Serial.print(EIXO[i]);
    Serial.print(F(" -> ")); Serial.print(NOME[i]);
    Serial.print(F("  centro = ")); Serial.print(repouso[i]);
    int desvio = repouso[i] - 512;
    if (desvio < -CENTRO_TOL || desvio > CENTRO_TOL)
      Serial.print(F("   <<< FORA DA FAIXA: o firmware DESATIVA este eixo"));
    Serial.println();
  }
  Serial.println();
}

void relatorio() {
  Serial.println();
  Serial.println(F("vvvvvvvvvvvvvv COPIE DAQUI vvvvvvvvvvvvvv"));
  Serial.println(F("---------------- RELATORIO ----------------"));
  Serial.println(F("eixo        junta         repouso  minimo  maximo  variacao  veredito"));
  uint8_t mudos = 0;
  for (uint8_t i = 0; i < N; i++) {
    int var = maximo[i] - minimo[i];
    Serial.print(EIXO[i]);   Serial.print(F("   "));
    Serial.print(NOME[i]);   Serial.print(F("   "));
    Serial.print(repouso[i]); Serial.print(F("     "));
    Serial.print(minimo[i]);  Serial.print(F("     "));
    Serial.print(maximo[i]);  Serial.print(F("      "));
    Serial.print(var);        Serial.print(F("     "));
    if (var >= VARIACAO_OK)   Serial.println(F("responde"));
    else if (var > 30)      { Serial.println(F("MEXEU POUCO (fim de curso nao chegou a 0/1023?)")); mudos++; }
    else                    { Serial.println(F("PARADO <<<")); mudos++; }
  }
  Serial.println();
  if (mudos == 0) {
    Serial.println(F("Os 4 eixos respondem. Entao o hardware das alavancas esta bom e o"));
    Serial.println(F("problema de S1/S4 esta na CALIBRACAO do firmware: grave o firmware,"));
    Serial.println(F("mande 'j' com as alavancas soltas e leia a linha 'Centro dos joysticks'."));
  } else {
    Serial.println(F("Ha eixo PARADO. Antes de mexer no codigo, confira nele:"));
    Serial.println(F("  1. o fio do VRx/VRy daquele eixo esta no furo certo do Arduino?"));
    Serial.println(F("  2. o joystick tem +5V e GND do ARDUINO (nao da fonte dos servos)?"));
    Serial.println(F("  3. troque o fio do eixo parado pelo de um que responde: se o"));
    Serial.println(F("     defeito mudar de eixo, e fio/furo; se ficar, e o modulo."));
  }
  Serial.print(F("RESUMO "));
  for (uint8_t i = 0; i < N; i++) {
    Serial.print(' ');
    Serial.print(EIXO[i][0]); Serial.print(EIXO[i][1]);   // "A0", "A1", ...
    Serial.print('(');
    Serial.print(NOME[i][0]); Serial.print(NOME[i][1]);   // "S1", "S2", ...
    Serial.print(F(")="));
    Serial.print(repouso[i]); Serial.print('/');
    Serial.print(maximo[i] - minimo[i]);
    Serial.print((maximo[i] - minimo[i]) >= VARIACAO_OK ? F(":ok") : F(":PARADO"));
  }
  Serial.println();
  Serial.println(F("(cada eixo acima vem como repouso/variacao)"));
  Serial.println(F("-------------------------------------------"));
  Serial.println(F("^^^^^^^^^^^^^^ COPIE ATE AQUI ^^^^^^^^^^^^^^"));
  Serial.println();
}

// ---------------------------------------------------------------- espelho nos servos
void ligaEspelho(bool liga) {
  espelho = liga;
  if (liga) {
    for (uint8_t i = 0; i < N; i++) {
      pos[i] = (ANG_MIN[i] + ANG_MAX[i]) / 2;
      servo[i].attach(PINO[i], 600, 2400);
      servo[i].write(pos[i]);
      delay(150);                                   // um servo de cada vez, para o pico de corrente nao somar
    }
    Serial.println(F("Espelho LIGADO: cada alavanca comanda a posicao do seu servo (absoluta)."));
    Serial.println(F("Alavanca no centro = meio da faixa. Mande 'm' de novo para soltar os servos."));
  } else {
    for (uint8_t i = 0; i < N; i++) {
      servo[i].detach();
      pinMode(PINO[i], OUTPUT);
      digitalWrite(PINO[i], LOW);                   // pino em repouso: nenhum pulso
    }
    Serial.println(F("Espelho DESLIGADO: nenhum servo recebe pulso."));
  }
}

void moveEspelho() {
  for (uint8_t i = 0; i < N; i++) {
    int destino = map(leitura[i], 0, 1023, ANG_MIN[i], ANG_MAX[i]);
    destino = limita(destino, ANG_MIN[i], ANG_MAX[i]);
    int d = destino - pos[i];
    if (d >  PASSO_MAX) d =  PASSO_MAX;             // rampa: no maximo 2 graus por passo de 20 ms
    if (d < -PASSO_MAX) d = -PASSO_MAX;
    pos[i] += d;
    servo[i].writeMicroseconds(600 + 10 * pos[i]);  // mesma escala do firmware: 600 us = 0 grau
  }
}

// ---------------------------------------------------------------- setup / loop
void setup() {
  Serial.begin(SERIAL_BPS);
  pinMode(PIN_SW1, INPUT_PULLUP);
  pinMode(PIN_SW2, INPUT_PULLUP);
  for (uint8_t i = 0; i < N; i++) { pinMode(PINO[i], OUTPUT); digitalWrite(PINO[i], LOW); }

  delay(300);
  Serial.println();
  Serial.println(F("=========================================================="));
  Serial.println(F("  TESTE DAS ALAVANCAS - 4 eixos e 2 botoes, leitura crua"));
  Serial.println(F("  Nenhum servo recebe pulso enquanto o espelho estiver off."));
  Serial.println(F("=========================================================="));
  imprimeRepouso();
  zeraMedicao();
  Serial.println(F("Mova UMA alavanca de cada vez ate o fim de curso, nos dois sentidos."));
  Serial.println(F("A tela fica QUIETA (so 1 linha por eixo, quando ele responde): a medicao"));
  Serial.println(F("segue rodando. Quando terminar, mande 'r' e copie o bloco do relatorio."));
  Serial.println(F("Comandos:  r = relatorio   z = zera   v = leitura ao vivo   m = espelho"));
  Serial.println();
}

void loop() {
  // ------------------------------------------------ comandos (uma letra, sem interpretador de palavras)
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'r' || c == 'R') relatorio();
    else if (c == 'z' || c == 'Z') zeraMedicao();
    else if (c == 'm' || c == 'M') ligaEspelho(!espelho);
    else if (c == 'v' || c == 'V') {
      aoVivo = !aoVivo;
      Serial.println(aoVivo ? F("Leitura ao vivo LIGADA ('v' para calar).")
                            : F("Leitura ao vivo desligada: tela quieta, medicao continua."));
    }
  }

  uint32_t agora = millis();
  if (agora - tAmostra < PERIODO_MS) return;
  tAmostra = agora;

  // ------------------------------------------------ leitura dos 4 eixos
  for (uint8_t i = 0; i < N; i++) {
    leitura[i] = analogRead(PIN_EIXO[i]);
    if (leitura[i] < minimo[i]) minimo[i] = leitura[i];
    if (leitura[i] > maximo[i]) maximo[i] = leitura[i];
    if (!respondeu[i] && maximo[i] - minimo[i] >= VARIACAO_OK) {
      respondeu[i] = true;
      Serial.print(F(">>> ")); Serial.print(EIXO[i]);
      Serial.print(F(" RESPONDEU (")); Serial.print(minimo[i]);
      Serial.print(F(" a ")); Serial.print(maximo[i]);
      Serial.print(F(") -> ")); Serial.println(NOME[i]);
    }
  }

  if (espelho) moveEspelho();

  // ------------------------------------------------ botões (apertar a alavanca para baixo)
  for (uint8_t b = 0; b < 2; b++) {
    bool ap = (digitalRead(b == 0 ? PIN_SW1 : PIN_SW2) == LOW);
    if (ap != swAnterior[b]) {
      swAnterior[b] = ap;
      Serial.print(F(">>> SW")); Serial.print(b + 1);
      Serial.println(ap ? F(" APERTADO") : F(" soltou"));
    }
  }

  // ------------------------------------------------ linha de leitura
  if (aoVivo && agora - tImprime >= IMPRIME_MS) {
    tImprime = agora;
    for (uint8_t i = 0; i < N; i++) {
      Serial.print(EIXO[i][0]); Serial.print(EIXO[i][1]);   // "A0", "A1", ...
      Serial.print('=');
      int v = leitura[i];
      if (v < 10) Serial.print(F("   ")); else if (v < 100) Serial.print(F("  ")); else if (v < 1000) Serial.print(' ');
      Serial.print(v);
      Serial.print(respondeu[i] ? F(" ok  ") : F(" --  "));
    }
    Serial.print(F("SW1=")); Serial.print(swAnterior[0] ? F("ap") : F("  "));
    Serial.print(F(" SW2=")); Serial.print(swAnterior[1] ? F("ap") : F("  "));
    if (espelho) {
      Serial.print(F("  servos:"));
      for (uint8_t i = 0; i < N; i++) { Serial.print(' '); Serial.print(pos[i]); }
    }
    Serial.println();
  }
}
