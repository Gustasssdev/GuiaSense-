"""
Usa a webcam do PC no lugar da ESP32-CAM: captura uma foto a cada
INTERVALO segundos e envia para o servidor, como a placa faria.

Uso (com o servidor.py rodando em outro terminal):
    python testar_webcam.py            # webcam 0
    python testar_webcam.py 1          # outra webcam
Ctrl+C para parar.
"""

import sys
import time

import cv2
import requests

URL = 'http://127.0.0.1:5000/detectar'
INTERVALO = 2.0

indice = int(sys.argv[1]) if len(sys.argv) > 1 else 0
camera = cv2.VideoCapture(indice)

if not camera.isOpened():
    print(f'Não foi possível abrir a webcam {indice}.')
    sys.exit(1)

print('Enviando fotos da webcam. Ctrl+C para parar.')

try:
    while True:

        ok, frame = camera.read()

        if not ok:
            print('Falha ao capturar da webcam.')
            time.sleep(INTERVALO)
            continue

        ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

        try:
            resposta = requests.post(
                URL, data=jpeg.tobytes(),
                headers={'Content-Type': 'image/jpeg'}, timeout=30
            )
            dados = resposta.json()
            print(dados.get('frase') or '(nada detectado)')

        except requests.RequestException as erro:
            print('Servidor indisponível:', erro)

        time.sleep(INTERVALO)

except KeyboardInterrupt:
    pass

finally:
    camera.release()
