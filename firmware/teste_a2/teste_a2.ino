/*
 * ============================================================================
 *  TESTE DO CANAL A2 — Braço Robótico 4 GDL   (diagnóstico, 20/11/2026)
 *
 *  PERGUNTA QUE ELE RESPONDE
 *  O eixo da garra (A2) lê lixo com a alavanca solta: passeia ~±130 counts em
 *  torno de ~510, que é justamente o valor do canal lido logo antes (A3). Duas
 *  explicações possíveis, e elas pedem conserto em lugares opostos:
 *
 *   (a) ARTEFATO DO MULTIPLEXADOR (software): o ADC do AVR tem UM conversor e
 *       um capacitor de amostragem (~14 pF) compartilhado por todos os canais.
 *       Ao trocar de canal, esse capacitor ainda carrega a tensão do canal
 *       anterior; se a fonte tiver impedância alta, a conversão sai puxada para
 *       o valor antigo. Conserto: leitura-fantasma (ler e descartar) ou média.
 *
 *   (b) PINO EM ABERTO (hardware): sem nada ligado, o pino flutua e guarda a
 *       carga da conversão anterior — produz exatamente o mesmo sintoma.
 *
 *  COMO DISTINGUIR, SEM TOCAR EM NADA
 *  Ligando o PULL-UP INTERNO do pino (~36 kohm para o 5V):
 *    - potenciômetro de 10 k ligado: o divisor puxa pouco. A leitura sobe
 *      algumas dezenas de counts e VOLTA na hora quando o pull-up desliga.
 *    - pino em aberto: nada segura o pino, ele crava perto de 1023 e, ao
 *      desligar o pull-up, cai devagar (a carga escoa sozinha).
 *  O A1 (ombro), que está comprovadamente bom, serve de controle: os dois
 *  canais passam pelo mesmo teste e as colunas são comparadas lado a lado.
 *
 *  O QUE ELE NÃO FAZ
 *  Não toca em NENHUM pino de servo: nada é energizado e nada se move. O único
 *  movimento possível é o tranco de ~1 s da garra no reset da gravação, porque
 *  o D13 é o pino do LED da placa e o bootloader o pulsa como SCK.
 *  GRAVE COM A GARRA VAZIA.
 *
 *  Monitor Serial a 115200 bps. Imprime um bloco a cada 2 s. Não precisa de
 *  comando nenhum: é só olhar a tabela e ler o veredito na última linha.
 * ============================================================================
 */

const uint8_t CANAL[] = { A0, A1, A2, A3 };
const char*   NOME[]  = { "A0 base   ", "A1 ombro  ", "A2 GARRA  ", "A3 cotovelo" };
const uint8_t N = 4;

// leitura "crua", do jeito que o firmware faz: um analogRead logo depois do canal anterior
int leBruto(uint8_t ch) { return analogRead(ch); }

// leitura com descarte: a primeira conversão paga o tempo de carga do capacitor e é jogada fora
int leComDescarte(uint8_t ch) {
  analogRead(ch);
  delayMicroseconds(200);
  return analogRead(ch);
}

// média de 32 leituras, com o espalhamento (maior - menor) devolvido por referência
int leMedia(uint8_t ch, int &espalhamento) {
  long soma = 0; int menor = 1023, maior = 0;
  for (uint8_t k = 0; k < 32; k++) {
    int v = analogRead(ch);
    soma += v;
    if (v < menor) menor = v;
    if (v > maior) maior = v;
  }
  espalhamento = maior - menor;
  return soma / 32;
}

// o teste que decide: pull-up ligado, leitura; pull-up desligado, leitura imediata e depois de 20 ms
void testePullup(uint8_t ch, int &comPullup, int &logoApos, int &passados20ms) {
  pinMode(ch, INPUT_PULLUP);
  delay(10);
  comPullup = analogRead(ch);
  pinMode(ch, INPUT);          // volta a alta impedância (sem pull-up)
  delayMicroseconds(500);
  logoApos = analogRead(ch);
  delay(20);
  passados20ms = analogRead(ch);
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println();
  Serial.println(F("================================================================"));
  Serial.println(F("  TESTE DO CANAL A2 - nenhum servo e energizado neste sketch"));
  Serial.println(F("  Deixe as alavancas SOLTAS. Um bloco a cada 2 s."));
  Serial.println(F("================================================================"));
  for (uint8_t i = 0; i < N; i++) pinMode(CANAL[i], INPUT);
}

void loop() {
  int bruto[N], descarte[N], media[N], espalha[N], pu[N], apos[N], ms20[N];

  for (uint8_t i = 0; i < N; i++) {
    bruto[i]    = leBruto(CANAL[i]);
    descarte[i] = leComDescarte(CANAL[i]);
    media[i]    = leMedia(CANAL[i], espalha[i]);
  }
  for (uint8_t i = 0; i < N; i++) testePullup(CANAL[i], pu[i], apos[i], ms20[i]);

  Serial.println();
  Serial.println(F("canal        bruto  descarte  media  espalha | pullup  solto  +20ms"));
  for (uint8_t i = 0; i < N; i++) {
    Serial.print(NOME[i]);  Serial.print(F("  "));
    Serial.print(bruto[i]);    Serial.print(F("     "));
    Serial.print(descarte[i]); Serial.print(F("      "));
    Serial.print(media[i]);    Serial.print(F("     "));
    Serial.print(espalha[i]);  Serial.print(F("  |  "));
    Serial.print(pu[i]);       Serial.print(F("    "));
    Serial.print(apos[i]);     Serial.print(F("   "));
    Serial.println(ms20[i]);
  }

  // ---- veredito automatico para o A2 (indice 2), com o A1 (indice 1) de controle
  Serial.print(F("VEREDITO A2: "));
  if (pu[2] > 950 && pu[1] < 800) {
    Serial.println(F("PINO EM ABERTO. O pull-up levou o A2 a ~1023 enquanto o A1, ligado,"));
    Serial.println(F("  ficou bem abaixo. Nao ha potenciometro segurando o A2: e fio/contato."));
  } else if (espalha[2] > 40 && espalha[1] <= 40 && pu[2] < 800) {
    Serial.println(F("POTENCIOMETRO LIGADO, mas leitura instavel."));
    Serial.println(F("  Se a coluna 'descarte'/'media' estabilizou, o ruido era do multiplexador"));
    Serial.println(F("  do ADC e se conserta no firmware (leitura-fantasma + media)."));
  } else if (espalha[2] <= 40) {
    Serial.println(F("A2 ESTAVEL agora. O defeito e intermitente: mexa no fio e veja se volta."));
  } else {
    Serial.println(F("inconclusivo - compare as colunas do A2 com as do A1 na tabela acima."));
  }
  delay(2000);
}
