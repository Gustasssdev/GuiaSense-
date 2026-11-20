#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"

// --- CONFIGURAÇÕES DE REDE ---
const char* ssid = "GUSTA";
const char* password = "gustavo113";
const char* serverUrl = "http://10.250.197.48:5000/detectar"; // Coloque o IP do seu PC aqui

// Intervalo entre envios: 1 minutos (60.000 ms)
const unsigned long INTERVALO_MS = 60000;

// --- MAPEAMENTO DE PINOS (AI-THINKER) ---
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

bool iniciarCamera() {
    camera_config_t config;

    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;

    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;

    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;

    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;

    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;

    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 12;
    config.fb_count = 1;

    return esp_camera_init(&config) == ESP_OK;
}

void enviarFoto() {
    camera_fb_t *fb = esp_camera_fb_get();

    if (!fb) {
        Serial.println("Falha ao capturar foto!");
        return;
    }

    HTTPClient http;

    http.begin(serverUrl);
    http.setTimeout(15000);
    http.addHeader("Content-Type", "image/jpeg");

    int statusHttp = http.POST(fb->buf, fb->len);

    if (statusHttp > 0) {
        Serial.printf("Foto enviada com sucesso! Código HTTP: %d\n", statusHttp);

        String resposta = http.getString();
        Serial.println("Deteções recebidas do YOLO: " + resposta);
    } else {
        Serial.printf(
            "Erro ao enviar POST: %s\n",
            http.errorToString(statusHttp).c_str()
        );
    }

    http.end();
    esp_camera_fb_return(fb);
}

void setup() {
    Serial.begin(115200);

    if (!iniciarCamera()) {
        Serial.println("Erro na inicialização da câmera!");

        while (true) {
            delay(1000);
        }
    }

    WiFi.begin(ssid, password);

    Serial.print("Conectando ao Wi-Fi");

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWi-Fi Conectado!");

    // Envia a primeira foto assim que a placa inicia
    enviarFoto();
}

void loop() {
    static unsigned long ultimaCaptura = 0;

    unsigned long agora = millis();

    if (agora - ultimaCaptura >= INTERVALO_MS) {
        ultimaCaptura = agora;

        if (WiFi.status() == WL_CONNECTED) {
            enviarFoto();
        }
    }
}
