#include <Arduino.h>

const int PINO_TRIG = 32;   // Pino 32 conectado ao TRIG do HC-SR04
const int PINO_ECHO = 33;   // Pino 33 conectado ao ECHO do HC-SR04
const int PINO_BUZZER = 27; // Buzzer (no lugar dos LEDs)

const int DURACAO_BIPE = 100; // Duração de cada bipe (ms)
const int PAUSA_BIPE = 100;   // Pausa entre bipes (ms)

// Emite 'quantidade' bipes curtos
void bipar(int quantidade) {
  for (int i = 0; i < quantidade; i++) {
    digitalWrite(PINO_BUZZER, HIGH);
    delay(DURACAO_BIPE);
    digitalWrite(PINO_BUZZER, LOW);
    delay(PAUSA_BIPE);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PINO_TRIG, OUTPUT);
  pinMode(PINO_ECHO, INPUT);
  pinMode(PINO_BUZZER, OUTPUT);
  digitalWrite(PINO_BUZZER, LOW);
}

void loop() {
  digitalWrite(PINO_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PINO_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PINO_TRIG, LOW);

  // Timeout de 30 ms (~5 m) para não travar se não houver eco
  long duracao = pulseIn(PINO_ECHO, HIGH, 30000);

  if (duracao == 0) {
    Serial.println("Sem leitura90 (fora de alcance)");
    delay(1000);
    return;
  }

  float distancia = (duracao * 0.0343) / 2;
  Serial.print("Distância: ");
  Serial.print(distancia);
  Serial.println(" cm");

  // Mesma lógica dos LEDs: 1, 2 ou 3 bipes conforme a proximidade
  if (distancia >= 120){
    bipar(1);
  } else if (distancia > 70) {
    bipar(2);
  } else {
    bipar(10);
  }

  delay(1000); // Aguarda antes da próxima leitura
}

o led vai ser substitudo pelo buzzer, ta certo esse codigo?