// GuiaSense - firmware da ESP32-CAM (AI-Thinker)
// Captura uma foto a cada INTERVALO_MS e envia por POST para o servidor.

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include <WiFiClientSecure.h>


#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Copie include/secrets.example.h para include/secrets.h e preencha Wi-Fi e IP do servidor."
#endif

// Intervalo entre fotos (ms). O YOLOv3 na CPU leva ~0,5 a 2 s por foto,
// então valores muito menores só criam fila.
const unsigned long INTERVALO_MS = 2000;

// --- MAPEAMENTO DE PINOS (AI-THINKER) ---
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

bool iniciarCamera()
{
    camera_config_t config = {};

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

    // Dois buffers na PSRAM + GRAB_LATEST: a foto enviada é a mais recente.
    // Com 1 buffer, a placa enviava uma foto tirada no ciclo anterior.
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_LATEST;

    return esp_camera_init(&config) == ESP_OK;
}

void conectarWiFi()
{
    Serial.print("Conectando ao Wi-Fi");

    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false); // menos atraso no envio
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_SENHA);

        int n = WiFi.scanNetworks();
    Serial.printf("\nRedes encontradas: %d\n", n);
    for (int i = 0; i < n; i++) {
        Serial.printf("  \"%s\"  sinal %d dBm\n", WiFi.SSID(i).c_str(), WiFi.RSSI(i));
    }
    
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.print("\nWi-Fi conectado! IP da ESP32-CAM: ");
    Serial.println(WiFi.localIP());
}

void enviarFoto()
{
    camera_fb_t *fb = esp_camera_fb_get();

    if (!fb)
    {
        Serial.println("Falha ao capturar foto!");
        return;
    }

    HTTPClient http;

    WiFiClientSecure clienteSeguro;
    clienteSeguro.setInsecure(); // não valida o certificado (ok para protótipo)

    if (strncmp(SERVIDOR_URL, "https", 5) == 0)
    {
        http.begin(clienteSeguro, SERVIDOR_URL);
    }
    else
    {
        http.begin(SERVIDOR_URL);
    }
    http.setTimeout(15000);
    http.addHeader("Content-Type", "image/jpeg");

    int statusHttp = http.POST(fb->buf, fb->len);

    // Devolve o buffer logo após o envio, antes de ler a resposta
    esp_camera_fb_return(fb);

    if (statusHttp > 0)
    {
        Serial.printf("Foto enviada. HTTP %d: ", statusHttp);
        Serial.println(http.getString());
    }
    else
    {
        Serial.printf("Erro ao enviar POST: %s\n",
                      http.errorToString(statusHttp).c_str());
    }

    http.end();
}

void setup()
{
    Serial.begin(115200);

    if (!iniciarCamera())
    {
        Serial.println("Erro na inicialização da câmera! Verifique o cabo e a alimentação 5 V.");
        while (true)
        {
            delay(1000);
        }
    }

    conectarWiFi();
    enviarFoto();
}

void loop()
{
    static unsigned long ultimaCaptura = 0;
    static unsigned long ultimaTentativaWiFi = 0;

    unsigned long agora = millis();

    if (WiFi.status() != WL_CONNECTED)
    {
        // Tenta reconectar a cada 5 s sem travar a placa
        if (agora - ultimaTentativaWiFi >= 5000)
        {
            ultimaTentativaWiFi = agora;
            Serial.println("Wi-Fi caiu, reconectando...");
            WiFi.reconnect();
        }
        return;
    }

    if (agora - ultimaCaptura >= INTERVALO_MS)
    {
        ultimaCaptura = agora;
        enviarFoto();
    }
}
