"""
Baixa os arquivos do YOLOv3 para a pasta YOLO/ na raiz do projeto.

Uso:
    python baixar_yolo.py
"""

import os
import sys
import requests

DIR_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_YOLO = os.path.join(DIR_RAIZ, 'YOLO')

ARQUIVOS = {
    'yolov3.cfg': 'https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg',
    'coco.names': 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names',
    'yolov3.weights': 'https://pjreddie.com/media/files/yolov3.weights',  # ~237 MB
}

os.makedirs(DIR_YOLO, exist_ok=True)

for nome, url in ARQUIVOS.items():

    destino = os.path.join(DIR_YOLO, nome)

    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        print(f'{nome}: já existe, pulando.')
        continue

    print(f'Baixando {nome}...')

    try:
        with requests.get(url, stream=True, timeout=30) as resposta:

            resposta.raise_for_status()
            total = int(resposta.headers.get('content-length', 0))
            baixado = 0

            with open(destino + '.parcial', 'wb') as arquivo:

                for bloco in resposta.iter_content(chunk_size=1 << 20):

                    arquivo.write(bloco)
                    baixado += len(bloco)

                    if total:
                        print(f'\r  {baixado * 100 // total}%', end='')

        os.replace(destino + '.parcial', destino)
        print(f'\r  {nome} salvo em YOLO/')

    except requests.RequestException as erro:
        print(f'\n  Falha ao baixar {nome}: {erro}')
        print(f'  Baixe manualmente: {url}')
        sys.exit(1)

print('Pronto.')
