
import os
import cv2
import numpy as np

from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

# Obtém o caminho absoluto do diretório onde este arquivo de script está salvo
DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))

# Se o script estiver dentro da subpasta 'servidor', aponta para a raiz do projeto;
# caso contrário, usa o próprio diretório
DIR_RAIZ = (
    os.path.dirname(DIR_ATUAL)
    if os.path.basename(DIR_ATUAL) == 'servidor'
    else DIR_ATUAL
)

# Define os caminhos absolutos dinâmicos para a pasta YOLO na raiz
weights_path = os.path.join(DIR_RAIZ, 'YOLO', 'yolov3.weights')
config_path = os.path.join(DIR_RAIZ, 'YOLO', 'yolov3.cfg')
names_path = os.path.join(DIR_RAIZ, 'YOLO', 'coco.names')

# Caminho do arquivo de resultados
arquivo_resultados = os.path.join(DIR_RAIZ, 'resultados.txt')

# Carrega a rede YOLO e as classes do COCO
net = cv2.dnn.readNet(weights_path, config_path)

with open(names_path, 'r') as f:
    classes = [line.strip() for line in f.readlines()]

# Obtém as camadas de saída da rede neural
layer_names = net.getLayerNames()
out_layers = net.getUnconnectedOutLayers()

output_layers = [
    layer_names[i - 1]
    for i in out_layers.flatten()
]


def salvar_resultado(resultados):
    """Salva as detecções da imagem em um arquivo TXT."""

    data_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    with open(arquivo_resultados, 'a', encoding='utf-8') as arquivo:
        arquivo.write('=' * 50 + '\n')
        arquivo.write(f'Data e hora: {data_hora}\n')
        arquivo.write(f'Objetos detectados: {len(resultados)}\n')

        if resultados:
            arquivo.write('Descrição da imagem:\n')

            for item in resultados:
                arquivo.write(
                    f"- {item['objeto']} "
                    f"(Confiança: {item['confianca']}%)\n"
                )
        else:
            arquivo.write('Nenhum objeto foi detectado na imagem.\n')

        arquivo.write('\n')


@app.route('/detectar', methods=['POST'])
def detectar():
    dados_bytes = request.get_data()

    if not dados_bytes:
        return jsonify({
            'erro': 'Nenhum dado de imagem recebido'
        }), 400

    # Converte os bytes brutos em uma imagem do OpenCV
    np_arr = np.frombuffer(dados_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({
            'erro': 'Falha ao decodificar a imagem'
        }), 400

    height, width, _ = frame.shape

    # Prepara a imagem (blob) para a rede YOLO
    blob = cv2.dnn.blobFromImage(
        frame,
        1 / 255.0,
        (416, 416),
        swapRB=True,
        crop=False
    )

    net.setInput(blob)
    layer_outputs = net.forward(output_layers)

    objetos_detectados = []
    confiancas = []
    caixas = []

    # Processa as saídas do modelo
    for output in layer_outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            if confidence > 0.4:
                # Calcula as coordenadas da caixa delimitadora
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                caixas.append([x, y, w, h])
                confiancas.append(float(confidence))
                objetos_detectados.append(classes[class_id])

    # Elimina caixas sobrepostas duplicadas (NMS)
    indices = cv2.dnn.NMSBoxes(
        caixas,
        confiancas,
        0.4,
        0.4
    )

    resultados = []

    if len(indices) > 0:
        for i in indices.flatten():
            resultados.append({
                'objeto': objetos_detectados[i],
                'confianca': round(confiancas[i] * 100, 2),
            })

    # Salva os resultados no arquivo TXT
    salvar_resultado(resultados)

    return jsonify({
        'status': 'sucesso',
        'deteccoes': resultados
    }), 200


if __name__ == '__main__':
    # host='0.0.0.0' garante visibilidade na rede local
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )




