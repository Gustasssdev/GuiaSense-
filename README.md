# GuiaSense (protótipo)

Sistema assistivo para pessoas com deficiência visual, com dois módulos independentes:

1. **Visão:** uma ESP32-CAM tira uma foto a cada 2 s e envia ao PC. O PC detecta objetos com YOLOv3 e monta uma frase com objeto, posição e proximidade ("pessoa à frente, perto. duas cadeiras à esquerda"). A página de status fala a frase em português pelo navegador.
2. **Bengala:** um ESP32 com sensor ultrassônico HC-SR04 acende LEDs por faixa de distância e aciona um buzzer cujo bipe acelera conforme o obstáculo se aproxima.

> Protótipo. Detecta apenas as 80 classes do COCO e depende de um PC rodando o servidor.

## Como funciona

O sistema tem três formas de ligar a câmera ao servidor:

| Modo | Caminho da foto | Quando usar |
|---|---|---|
| **Rede local** | ESP32-CAM ─Wi-Fi─> PC na mesma rede | PC e placa no mesmo roteador ou hotspot |
| **Internet (túnel)** | ESP32-CAM ─hotspot do celular─> internet ─> túnel Cloudflare ─> PC | placa longe do PC, só com power bank e celular |
| **Cabo USB** | ESP32-CAM ─USB─> `cam_serial.py` ─> servidor | testes sem rede, ou plano B |

```
ESP32-CAM ──POST /detectar (JPEG, a cada 2 s)──> servidor.py: Flask + YOLOv3 (OpenCV DNN)
                                                   │  monta a frase e registra o evento
                                                   └──> página de status (porta 5000)
                                                          └──> voz pt-BR do navegador (PC ou celular)

ESP32 + HC-SR04 ──> LEDs (livre / atenção / perto) + buzzer (bipe mais rápido quanto mais perto)
```

**Posição:** a imagem é dividida em três faixas verticais (esquerda, frente, direita) pelo centro da caixa detectada.
**"Perto":** a caixa ocupa pelo menos 20% da área ou 60% da altura da imagem. É uma estimativa pelo tamanho, não uma distância real.
**Repetição:** a mesma frase só é falada de novo depois de 8 s, para a voz não repetir a cada foto. Uma frase diferente é falada na hora.

## Materiais

- ESP32-CAM (AI-Thinker) + adaptador FTDI ou base ESP32-CAM-MB
- ESP32 DevKit, sensor HC-SR04, 3 LEDs com resistores de 220 Ω, buzzer ativo, resistores de 1 kΩ e 2 kΩ (divisor de tensão do ECHO)
- Fonte ou power bank 5 V estável (1 A ou mais)
- Celular com hotspot 2,4 GHz
- PC com Python 3.9+

## Estrutura de pastas

```
GuiaSense/
├── README.md
├── platformio.ini            # ambientes: esp32cam, cam_serial e bengala
├── requirements.txt
├── include/
│   └── secrets.example.h     # modelo para Wi-Fi e endereço do servidor
├── src/
│   ├── esp_cam.cpp           # firmware da ESP32-CAM (Wi-Fi, HTTP ou HTTPS)
│   ├── cam_serial.cpp        # firmware da ESP32-CAM pelo cabo USB
│   └── bengala.cpp           # firmware da bengala
├── servidor/
│   ├── servidor.py           # Flask + YOLOv3 + frase
│   ├── baixar_yolo.py        # baixa os arquivos do YOLOv3
│   ├── enviar_imagem.py      # testa com uma foto do PC
│   ├── testar_webcam.py      # testa com a webcam do PC
│   ├── cam_serial.py         # recebe fotos da ESP32-CAM pelo cabo USB
│   └── templates/index.html  # página de status com voz
├── YOLO/                     # criada pelo baixar_yolo.py (fora do git)
├── eventos.txt               # um evento por alerta (JSON por linha)
└── resultados.txt            # histórico de todas as fotos
```

## Como rodar

### 1. Servidor (PC)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python servidor/baixar_yolo.py      # baixa ~240 MB para YOLO/
python servidor/servidor.py
```

Abra `http://localhost:5000` e ative **Alertas de voz**. No celular, abra `http://IP_DO_PC:5000`. O toque no botão é necessário, porque o navegador só libera a voz depois de uma ação do usuário.

Sem o download automático, baixe manualmente para `YOLO/`:
[yolov3.weights](https://pjreddie.com/media/files/yolov3.weights),
[yolov3.cfg](https://github.com/pjreddie/darknet/blob/master/cfg/yolov3.cfg) e
[coco.names](https://github.com/pjreddie/darknet/blob/master/data/coco.names).

### 2. Teste sem a ESP32-CAM

Com o servidor rodando, em outro terminal:

```bash
python servidor/testar_webcam.py           # usa a webcam do PC
python servidor/enviar_imagem.py foto.jpg  # envia uma foto
```

### 3. ESP32-CAM na rede local

1. Copie `include/secrets.example.h` para `include/secrets.h` e preencha o SSID e a senha do hotspot e o IP do PC (`ipconfig` no Windows, `ip a` no Linux).
2. Grave pelo PlatformIO: `pio run -e esp32cam -t upload`.
3. Abra o monitor serial (115200). A placa mostra o próprio IP e a resposta do servidor a cada foto.

### 4. Pela internet (túnel Cloudflare)

Para a placa funcionar longe do PC, usando só o hotspot do celular. O PC continua rodando o servidor.

1. Instale o túnel (Arch: `sudo pacman -S cloudflared`) e, com o `servidor.py` rodando, abra:
   ```bash
   cloudflared tunnel --protocol http2 --url http://localhost:5000
   ```
   Ele mostra um endereço `https://...trycloudflare.com`. O `--protocol http2` é necessário em redes que bloqueiam UDP.
2. No `include/secrets.h`, use o hotspot do celular (2,4 GHz, WPA2, dados móveis ligados) e o endereço do túnel:
   ```cpp
   #define SERVIDOR_URL  "https://ENDERECO.trycloudflare.com/detectar"
   ```
   O firmware usa HTTPS automaticamente quando o endereço começa com `https`.
3. Grave com `pio run -e esp32cam -t upload` e alimente a placa pelo power bank.
4. No celular, abra o endereço do túnel e ative **Alertas de voz**.

Cuidados: o endereço muda toda vez que o `cloudflared` é aberto de novo (aí é preciso regravar a placa), e o servidor fica acessível sem senha para quem tiver o endereço. Mantenha o PC sem suspender, por exemplo:
`systemd-inhibit --what=sleep:idle python servidor/servidor.py`.

### 5. Pelo cabo USB (sem rede)

Útil para testar o reconhecimento sem Wi-Fi. A placa fica ligada no PC.

```bash
pip install pyserial
pio run -e cam_serial -t upload      # não abra o monitor serial depois
python servidor/servidor.py          # terminal 1
python servidor/cam_serial.py        # terminal 2 (ou: cam_serial.py /dev/ttyUSB1)
```

A última foto recebida fica em `ultima_foto.jpg`. Se der "foto incompleta", troque 921600 por 460800 no `cam_serial.cpp` e no `cam_serial.py`.

### 6. Bengala

Monte o circuito descrito no topo de `src/bengala.cpp`. O ECHO do HC-SR04 precisa do divisor de tensão, pois sai em 5 V e o ESP32 aceita 3,3 V. Depois grave com `pio run -e bengala -t upload`.

| Distância | LEDs | Buzzer |
|---|---|---|
| ≥ 170 cm ou sem eco | amarelo | silêncio |
| 90 a 170 cm | amarelo + laranja | bipe lento (1 s a ~0,5 s) |
| 20 a 90 cm | todos | bipe rápido (até 0,1 s) |
| < 20 cm | todos | contínuo |

## Ajustes (variáveis de ambiente do servidor)

| Variável | Padrão | Efeito |
|---|---|---|
| `GUIASENSE_CONFIANCA` | `0.5` | confiança mínima de uma detecção |
| `GUIASENSE_PERTO_AREA` | `0.20` | fração da área para considerar "perto" |
| `GUIASENSE_PERTO_ALTURA` | `0.60` | fração da altura para considerar "perto" |
| `GUIASENSE_REPETIR` | `8` | segundos até repetir a mesma frase |
| `YOLO_DIR` | `YOLO/` | pasta dos arquivos do YOLOv3 |
| `GUIASENSE_DEBUG` | desligado | `1` ativa o modo debug do Flask |

## Rotas do servidor

| Rota | Uso |
|---|---|
| `POST /detectar` | recebe JPEG bruto e devolve `frase` e `deteccoes` |
| `GET /eventos?desde=ID` | eventos novos depois de `ID` e a última detecção |
| `GET /ultima-deteccao` | resultado da última foto |
| `GET /` | página de status |

## Limitações

- O YOLOv3 (COCO) não detecta degrau, buraco, porta ou poste.
- "Perto" é estimado pelo tamanho da caixa, não é distância real. Um ônibus longe pode parecer "perto" e uma garrafa perto pode não parecer.
- Há um atraso de 1 a 3 s entre a foto e a fala (envio + YOLOv3 na CPU + consulta da página).
- O HC-SR04 não pega objetos baixos, macios ou muito inclinados.
- Sem o túnel, o PC, a ESP32-CAM e o celular da página precisam estar na mesma rede. Com o túnel, o PC precisa ficar ligado e com internet.

## Onde buscar quando travar

| Problema | Onde procurar |
|---|---|
| ESP32-CAM não grava ou reinicia | Random Nerd Tutorials (ESP32-CAM), github.com/espressif/esp32-camera (issues), fonte 5 V estável |
| Erro "Copie include/secrets.example.h" | Falta criar o `include/secrets.h` (passo 3.1) |
| Monitor serial vazio | Apertar RST; com a base ESP32-CAM-MB, adicionar `monitor_rts = 0` e `monitor_dtr = 0` no `platformio.ini` |
| Wi-Fi não conecta (pontos sem parar) | Hotspot em 2,4 GHz e WPA2, nome e