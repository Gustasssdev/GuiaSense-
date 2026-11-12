#include <Arduino.h>

const int PINO_TRIG = 32; // Pino 32 conectado ao TRIG do HC-SR04
const int PINO_ECHO = 33; // Pino 33 conectado ao ECHO do HC-SR04
const int PINO_LED1 = 27; // Fio vermelho
const int PINO_LED2 = 14; // Fio laranja
const int PINO_LED3 = 12; // Fio amarelo

void setup() {
  Serial.begin(115200); // Inicializa a comunicação serial
  pinMode(PINO_TRIG, OUTPUT); // Configura o pino TRIG como saída
  pinMode(PINO_ECHO, INPUT); // Configura o pino ECHO como entrada
  pinMode(PINO_LED1, OUTPUT);
  pinMode(PINO_LED2, OUTPUT);
  pinMode(PINO_LED3, OUTPUT);
}

void loop() {

  digitalWrite(PINO_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PINO_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PINO_TRIG, LOW);
  
  long duracao = pulseIn(PINO_ECHO, HIGH); // Mede o tempo de resposta do ECHO  
  float distancia = (duracao * 0.0343) / 2;// Calcula a distância usando a velocidade do som (aproximadamente 343 m/s)
  Serial.print("Distância: ");
  Serial.print(distancia);
  Serial.println(" cm");

  if (distancia > 170){
    digitalWrite(PINO_LED3, HIGH);
    digitalWrite(PINO_LED2, LOW);
    digitalWrite(PINO_LED1, LOW);
  }else if (distancia < 170 && distancia > 90){
    digitalWrite(PINO_LED3, HIGH);
    digitalWrite(PINO_LED2, HIGH);
    digitalWrite(PINO_LED1, LOW);
  } else{
    digitalWrite(PINO_LED3, HIGH);
    digitalWrite(PINO_LED2, HIGH);
    digitalWrite(PINO_LED1, HIGH);
  }
  
  delay(1000); // Aguarda 1 segundo antes de fazer a próxima leitura
}


