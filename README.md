# GuiaSense (protótipo)

Sistema assistivo para pessoas com deficiência visual, com dois módulos independentes:

1. **Visão:** uma ESP32-CAM tira uma foto a cada 2 s e envia ao PC. O PC detecta objetos com YOLOv3 e monta uma frase com objeto, posição e proximidade ("pessoa à frente, perto. duas cadeiras à esquerda"). A página de status fala a frase em português pelo navegador.
2. **Bengala:** um ESP32 com sensor ultrassônico HC-SR04 acende LEDs por faixa de distância e aciona um buzzer cujo bipe acelera conforme o obstáculo se aproxima.

> Protótipo. Detecta apenas as 80 classes do COCO e depende de um PC na mesma rede.

## Como funciona

```
ESP32-CAM ──POST /detectar (JPEG, a cada 2 s)──> PC: Flask + YOLOv3 (OpenCV DNN)
                                                   │  monta a frase e registra o evento
                                                   └──> página de status (porta 5000)
                                                          └──> voz pt-BR do navegador

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
├── platformio.ini            # dois ambientes: esp32cam e bengala
├── requirements.txt
├── include/
│   └── secrets.example.h     # modelo para Wi-Fi e IP do servidor
├── src/
│   ├── esp_cam.cpp           # firmware da ESP32-CAM
│   └── bengala.cpp           # firmware da bengala
├── servidor/
│   ├── servidor.py           # Flask + YOLOv3 + frase
│   ├── baixar_yolo.py        # baixa os arquivos do YOLOv3
│   ├── enviar_imagem.py      # testa com uma foto do PC
│   ├── testar_webcam.py      # testa com a webcam do PC
│   └── templates/index.html  # página de status com voz
├── YOLO/                     # criada pelo baixar_yolo.py (fora do git)
├── eventos.txt               # um evento por alerta (JSON por linha)
└── resultados.txt            # histórico de todas as fotos
```

## Como rodar

### 1. Servidor (PC)

```bash
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

### 3. ESP32-CAM

1. Copie `include/secrets.example.h` para `include/secrets.h` e preencha o SSID e a senha do hotspot e o IP do PC (`ipconfig` no Windows, `ip a` no Linux).
2. Grave pelo PlatformIO: `pio run -e esp32cam -t upload`.
3. Abra o monitor serial (115200). A placa mostra o próprio IP e a resposta do servidor a cada foto.

### 4. Bengala

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
- O PC, a ESP32-CAM e o celular da página precisam estar na mesma rede.

## Onde buscar quando travar

| Problema | Onde procurar |
|---|---|
| ESP32-CAM não grava ou reinicia | Random Nerd Tutorials (ESP32-CAM), github.com/espressif/esp32-camera (issues), fonte 5 V estável |
| Erro "Copie include/secrets.example.h" | Falta criar o `include/secrets.h` (passo 3.1) |
| ESP32-CAM não alcança o servidor | PC e placa no mesmo hotspot 2,4 GHz, IP certo no `secrets.h`, firewall liberando a porta 5000, isolamento de clientes desligado |
| Servidor fecha dizendo que faltam arquivos | Rodar `python servidor/baixar_yolo.py` |
| Voz não fala | Ativar o botão de alertas (o navegador exige um toque) e instalar uma voz pt-BR no sistema |
| HC-SR04 com leituras erradas | Datasheet, divisor de tensão no ECHO, alimentação em 5 V |
| Dúvida geral de ESP32 | docs.espressif.com/projects/arduino-esp32 |
