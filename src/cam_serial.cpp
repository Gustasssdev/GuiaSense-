// GuiaSense - ESP32-CAM enviando fotos pelo cabo USB (sem Wi-Fi)
//
// Quando o PC manda o caractere 'F', a placa tira uma foto e responde:
//     FOTO:<tamanho>\n<bytes do JPEG>\n
// Quem recebe é o servidor/cam_serial.py, que repassa a foto ao servidor.py.
//
// Gravar: pio run -e cam_serial -t upload   (não abra o monitor serial depois:
//         a porta precisa ficar livre para o cam_serial.py)

#include <Arduino.h>
#include "esp_camera.h"

const unsigned long BAUD = 921600; // tem que ser igual ao do cam_serial.py

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

bool cameraOk = false;

bool iniciarCamera() {
    camera_config_t config = {};
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;  config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;  config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;  config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;  config.pin_d7 = Y9_GPIO_NUM;
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
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_LATEST;

    if (!psramFound()) {
        config.fb_count = 1;
        config.fb_location = CAMERA_FB_IN_DRAM;
        config.frame_size = FRAMESIZE_QVGA;
    }

    return esp_camera_init(&config) == ESP_OK;
}

void setup() {
    Serial.begin(BAUD);
    delay(500);

    cameraOk = iniciarCamera();
    Serial.println(cameraOk
        ? "CAMERA_OK"
        : "ERRO_CAMERA: confira o cabo flat e a fonte 5 V");
}

void loop() {
    if (!Serial.available()) {
        return;
    }

    char comando = Serial.read();
    if (comando != 'F') {
        return;
    }

    if (!cameraOk) {
        Serial.println("ERRO_CAMERA");
        return;
    }

    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("ERRO_CAPTURA");
        return;
    }

    Serial.printf("FOTO:%u\n", fb->len);
    Serial.write(fb->buf, fb->len);
    Serial.print("\n");
    Serial.flush();

    esp_camera_fb_return(fb);
}
