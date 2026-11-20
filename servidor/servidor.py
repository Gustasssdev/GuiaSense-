
import os
import cv2
import json
import numpy as np

from datetime import datetime
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# =====================================================
# ULTIMA DETECCAO
# =====================================================

ultima_deteccao = {
    "objeto": "nenhum",
    "confianca": 0.0
}

# =====================================================
# CAMINHOS DOS ARQUIVOS
# =====================================================

DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))

DIR_RAIZ = (
    os.path.dirname(DIR_ATUAL)
    if os.path.basename(DIR_ATUAL) == 'servidor'
    else DIR_ATUAL
)

# Caminhos dos arquivos YOLO
weights_path = os.path.join(DIR_RAIZ, 'YOLO', 'yolov3.weights')
config_path = os.path.join(DIR_RAIZ, 'YOLO', 'yolov3.cfg')
names_path = os.path.join(DIR_RAIZ, 'YOLO', 'coco.names')

# Arquivos de registros
arquivo_resultados = os.path.join(DIR_RAIZ, 'resultados.txt')
arquivo_eventos = os.path.join(DIR_RAIZ, 'eventos.txt')

# =====================================================
# CONTROLE DOS IDENTIFICADORES
# =====================================================

def obter_proximo_id():
    """
    Recupera o maior ID existente no arquivo
    para continuar a numeracao após reiniciar o Flask.
    """

    maior_id = 0

    if os.path.exists(arquivo_eventos):

        with open(arquivo_eventos, 'r', encoding='utf-8') as arquivo:

            for linha in arquivo:

                try:
                    evento = json.loads(linha)
                    maior_id = max(maior_id, evento['id'])

                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

    return maior_id + 1


proximo_evento_id = obter_proximo_id()

# =====================================================
# CARREGAMENTO DO YOLO
# =====================================================

net = cv2.dnn.readNet(weights_path, config_path)

with open(names_path, 'r') as f:
    classes = [line.strip() for line in f.readlines()]

layer_names = net.getLayerNames()
out_layers = net.getUnconnectedOutLayers()

output_layers = [
    layer_names[i - 1]
    for i in out_layers.flatten()
]

# =====================================================
# SALVAR RESULTADOS NO TXT
# =====================================================

def salvar_resultado(resultados):
    """Salva as detecções da imagem em resultados.txt."""

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


# =====================================================
# REGISTRAR EVENTOS NO TXT
# =====================================================

def salvar_evento(objeto, confianca):
    """
    Cria um identificador único e registra
    o evento no arquivo eventos.txt.
    """

    global proximo_evento_id

    data_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    evento = {
        'id': proximo_evento_id,
        'objeto': objeto,
        'confianca': confianca,
        'data_hora': data_hora
    }

    with open(arquivo_eventos, 'a', encoding='utf-8') as arquivo:

        arquivo.write(json.dumps(evento, ensure_ascii=False) + '\n')

    proximo_evento_id += 1

    return evento


# =====================================================
# LER EVENTOS DO TXT
# =====================================================

def ler_eventos():

    eventos = []

    if not os.path.exists(arquivo_eventos):
        return eventos

    with open(arquivo_eventos, 'r', encoding='utf-8') as arquivo:

        for linha in arquivo:

            try:
                evento = json.loads(linha)
                eventos.append(evento)

            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    return eventos


# =====================================================
# ROTA DE DETECCAO
# =====================================================

@app.route('/detectar', methods=['POST'])
def detectar():

    global ultima_deteccao

    dados_bytes = request.get_data()

    if not dados_bytes:
        return jsonify({
            'erro': 'Nenhum dado de imagem recebido'
        }), 400

    # Converte os bytes brutos em uma imagem OpenCV
    np_arr = np.frombuffer(dados_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({
            'erro': 'Falha ao decodificar a imagem'
        }), 400

    height, width, _ = frame.shape

    # Prepara a imagem para a rede YOLO
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

                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)

                w = int(detection[2] * width)
                h = int(detection[3] * height)

                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                caixas.append([x, y, w, h])
                confiancas.append(float(confidence))
                objetos_detectados.append(classes[class_id])

    # Elimina caixas sobrepostas duplicadas
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
                'confianca': round(confiancas[i] * 100, 2)
            })

    # =================================================
    # ATUALIZA ULTIMA DETECCAO E REGISTRA EVENTOS
    # =================================================

    if resultados:

        ultima_deteccao = resultados[0].copy()

        # Cada objeto detectado gera um evento com ID próprio
        for item in resultados:

            salvar_evento(
                item['objeto'],
                item['confianca']
            )

    else:

        ultima_deteccao = {
            "objeto": "nenhum",
            "confianca": 0.0
        }

    # Salva o histórico completo da imagem
    salvar_resultado(resultados)

    return jsonify({
        'status': 'sucesso',
        'deteccoes': resultados
    }), 200


# =====================================================
# ROTA DA PAGINA INICIAL
# =====================================================

@app.route('/')
def index():
    return render_template('index.html')


# =====================================================
# ROTA PARA CONSULTAR ULTIMA DETECCAO
# =====================================================

@app.route('/ultima-deteccao', methods=['GET'])
def get_ultima_deteccao():
    return jsonify(ultima_deteccao)


# =====================================================
# ROTA PARA CONSULTAR NOVOS EVENTOS
# =====================================================

@app.route('/eventos', methods=['GET'])
def get_eventos():

    try:
        ultimo_id_recebido = int(request.args.get('desde', 0))

    except ValueError:
        return jsonify({
            'erro': 'Identificador invalido'
        }), 400

    eventos = ler_eventos()

    # Filtra somente eventos posteriores ao ID recebido
    novos_eventos = [
        evento
        for evento in eventos
        if evento['id'] > ultimo_id_recebido
    ]

    # Recupera o último ID registrado
    ultimo_id = eventos[-1]['id'] if eventos else 0

    return jsonify({
        'eventos': novos_eventos,
        'ultimo_id': ultimo_id,
        'ultima_deteccao': ultima_deteccao
    })


# =====================================================
# EXECUCAO DO SERVIDOR
# =====================================================

if __name__ == '__main__':

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )
