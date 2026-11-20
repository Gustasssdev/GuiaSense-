"""
Envia uma imagem do computador para o servidor, simulando a ESP32-CAM.

Uso:
    python enviar_imagem.py foto.jpg
    python enviar_imagem.py foto.jpg http://127.0.0.1:5000/detectar
"""

import sys
import requests

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

caminho_imagem = sys.argv[1]
url = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:5000/detectar'

with open(caminho_imagem, 'rb') as f:
    bytes_foto = f.read()

resposta = requests.post(
    url, data=bytes_foto, headers={'Content-Type': 'image/jpeg'}, timeout=30
)

print('Código HTTP:', resposta.status_code)
print('Resposta:', resposta.json())
