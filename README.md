# GuiaSense (protótipo)

Sistema assistivo para pessoas com deficiência visual, com dois módulos independentes:

1. **Visão:** uma ESP32-CAM captura imagens, um PC identifica objetos com YOLO e fala os rótulos ("pessoa à frente, perto").
2. **Bengala:** um ESP32 com sensor ultrassônico aciona um buzzer cujo bipe acelera conforme o obstáculo se aproxima.

> Protótipo. Detecta apenas rótulos de objetos comuns e depende de um PC na mesma rede.

## Como funciona

```
ESP32-CAM ──Wi-Fi (hotspot do celular)──> PC (Python + Flask + YOLO) ──> voz (pyttsx3)
                                                   └──> página de status (localhost:5000)

ESP32 + HC-SR04 ──> buzzer (bipe mais rápido quanto mais perto)
```

O PC busca a foto em `http://IP_DO_ESP/capture` a cada ~1,5 s, detecta objetos, monta a frase (objeto + posição + "perto") e fala.

## Materiais

- ESP32-CAM (AI-Thinker) + adaptador FTDI ou base ESP32-CAM-MB
- ESP32 DevKit, sensor HC-SR04, buzzer, resistores 1 kΩ e 2 kΩ (divisor de tensão do ECHO)
- Fonte/power bank 5 V estável (1 A ou mais)
- Celular com hotspot 2,4 GHz
- PC com Python 3.9+

## Estrutura de pastas

```
guiasense/
├── README.md
├── servidor/
│   └── guiasense_server.py      # Flask + YOLO + voz
├── firmware_cam/
│   └── CameraWebServer/         # exemplo do Arduino, com SSID/senha do hotspot
├── firmware_bengala/
│   └── bengala.ino              # HC-SR04 + buzzer
└── docs/
    ├── circuito.png
    └── resultados.md            # testes, tempos e erros observados
```

## Como rodar

1. `pip install ultralytics opencv-python requests flask pyttsx3`
2. Grave o `CameraWebServer` no ESP32-CAM (modelo `CAMERA_MODEL_AI_THINKER`, SSID e senha do hotspot) e anote o IP no Serial Monitor.
3. Conecte o PC ao mesmo hotspot.
4. `set CAM_URL=http://IP_DO_ESP/capture` (Windows) ou `export CAM_URL=...` (Linux/Mac)
5. `python guiasense_server.py` e abra `http://localhost:5000`.

Teste sem ESP32: `CAM_URL=0` usa a webcam do PC.

## Limitações

- O YOLO (COCO) não detecta degrau, buraco, porta ou poste.
- "Perto" é estimado pelo tamanho da caixa na imagem, não é distância real.
- Atraso de alguns segundos entre captura e fala.
- O HC-SR04 não pega objetos baixos, macios ou muito inclinados.
- O PC precisa estar na mesma rede do ESP32-CAM.

---
## Onde buscar quando travar

| Problema | Onde procurar |
|---|---|
| ESP32-CAM não grava ou reinicia | Random Nerd Tutorials (ESP32-CAM), github.com/espressif/esp32-camera (issues) |
| Não acessa o IP do ESP32-CAM | Conferir se o PC e o ESP estão no mesmo hotspot, 2,4 GHz, e a opção de isolamento de clientes |
| YOLO lento ou sem detecção | docs.ultralytics.com (Predict, Tips), reduzir resolução |
| Voz em inglês | Instalar voz pt-BR do sistema e ver `pyttsx3.readthedocs.io` |
| HC-SR04 com leituras erradas | Datasheet, divisor de tensão no ECHO, mediana das leituras |
| Dúvida geral de ESP32 | docs.espressif.com/projects/arduino-esp32 |