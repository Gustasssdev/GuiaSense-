"""
GuiaSense - servidor de detecção.

Recebe fotos da ESP32-CAM (POST /detectar), detecta objetos com YOLOv3
(OpenCV DNN), monta uma frase em português com objeto, posição e
proximidade ("pessoa à frente, perto") e disponibiliza os eventos para a
página de status, que fala as frases pelo navegador.
"""

import os
import sys
import json
import time
import threading
from collections import deque
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# =====================================================
# CONFIGURAÇÃO (pode ser ajustada por variáveis de ambiente)
# =====================================================

# Confiança mínima para aceitar uma detecção (0 a 1)
CONFIANCA_MIN = float(os.environ.get('GUIASENSE_CONFIANCA', '0.5'))

# Limiar de sobreposição usado na supressão de não máximos (NMS)
LIMIAR_NMS = 0.4

# Uma caixa é considerada "perto" quando ocupa pelo menos esta fração
# da área da imagem ou esta fração da altura da imagem
LIMIAR_PERTO_AREA = float(os.environ.get('GUIASENSE_PERTO_AREA', '0.20'))
LIMIAR_PERTO_ALTURA = float(os.environ.get('GUIASENSE_PERTO_ALTURA', '0.60'))

# Uma frase igual à anterior só vira novo evento depois deste tempo (s),
# para a voz não repetir a mesma coisa a cada foto
REPETIR_APOS_S = float(os.environ.get('GUIASENSE_REPETIR', '8'))

# Máximo de grupos de objetos falados em uma frase
MAX_ITENS_FRASE = 3

# Quantos eventos recentes ficam em memória para a página
MAX_EVENTOS_MEMORIA = 200

# =====================================================
# CAMINHOS DOS ARQUIVOS
# =====================================================

DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))

DIR_RAIZ = (
    os.path.dirname(DIR_ATUAL)
    if os.path.basename(DIR_ATUAL) == 'servidor'
    else DIR_ATUAL
)

DIR_YOLO = os.environ.get('YOLO_DIR', os.path.join(DIR_RAIZ, 'YOLO'))

weights_path = os.path.join(DIR_YOLO, 'yolov3.weights')
config_path = os.path.join(DIR_YOLO, 'yolov3.cfg')
names_path = os.path.join(DIR_YOLO, 'coco.names')

arquivo_resultados = os.path.join(DIR_RAIZ, 'resultados.txt')
arquivo_eventos = os.path.join(DIR_RAIZ, 'eventos.txt')

# =====================================================
# NOMES DAS CLASSES EM PORTUGUÊS (singular, plural)
# =====================================================

NOMES_PT = {
    'person': ('pessoa', 'pessoas'),
    'bicycle': ('bicicleta', 'bicicletas'),
    'car': ('carro', 'carros'),
    'motorbike': ('moto', 'motos'),
    'motorcycle': ('moto', 'motos'),
    'aeroplane': ('avião', 'aviões'),
    'airplane': ('avião', 'aviões'),
    'bus': ('ônibus', 'ônibus'),
    'train': ('trem', 'trens'),
    'truck': ('caminhão', 'caminhões'),
    'boat': ('barco', 'barcos'),
    'traffic light': ('semáforo', 'semáforos'),
    'fire hydrant': ('hidrante', 'hidrantes'),
    'stop sign': ('placa de pare', 'placas de pare'),
    'parking meter': ('parquímetro', 'parquímetros'),
    'bench': ('banco', 'bancos'),
    'bird': ('pássaro', 'pássaros'),
    'cat': ('gato', 'gatos'),
    'dog': ('cachorro', 'cachorros'),
    'horse': ('cavalo', 'cavalos'),
    'sheep': ('ovelha', 'ovelhas'),
    'cow': ('vaca', 'vacas'),
    'elephant': ('elefante', 'elefantes'),
    'bear': ('urso', 'ursos'),
    'zebra': ('zebra', 'zebras'),
    'giraffe': ('girafa', 'girafas'),
    'backpack': ('mochila', 'mochilas'),
    'umbrella': ('guarda-chuva', 'guarda-chuvas'),
    'handbag': ('bolsa', 'bolsas'),
    'tie': ('gravata', 'gravatas'),
    'suitcase': ('mala', 'malas'),
    'frisbee': ('frisbee', 'frisbees'),
    'skis': ('esqui', 'esquis'),
    'snowboard': ('snowboard', 'snowboards'),
    'sports ball': ('bola', 'bolas'),
    'kite': ('pipa', 'pipas'),
    'baseball bat': ('taco de beisebol', 'tacos de beisebol'),
    'baseball glove': ('luva de beisebol', 'luvas de beisebol'),
    'skateboard': ('skate', 'skates'),
    'surfboard': ('prancha de surfe', 'pranchas de surfe'),
    'tennis racket': ('raquete', 'raquetes'),
    'bottle': ('garrafa', 'garrafas'),
    'wine glass': ('taça', 'taças'),
    'cup': ('copo', 'copos'),
    'fork': ('garfo', 'garfos'),
    'knife': ('faca', 'facas'),
    'spoon': ('colher', 'colheres'),
    'bowl': ('tigela', 'tigelas'),
    'banana': ('banana', 'bananas'),
    'apple': ('maçã', 'maçãs'),
    'sandwich': ('sanduíche', 'sanduíches'),
    'orange': ('laranja', 'laranjas'),
    'broccoli': ('brócolis', 'brócolis'),
    'carrot': ('cenoura', 'cenouras'),
    'hot dog': ('cachorro-quente', 'cachorros-quentes'),
    'pizza': ('pizza', 'pizzas'),
    'donut': ('rosquinha', 'rosquinhas'),
    'cake': ('bolo', 'bolos'),
    'chair': ('cadeira', 'cadeiras'),
    'sofa': ('sofá', 'sofás'),
    'couch': ('sofá', 'sofás'),
    'pottedplant': ('vaso de planta', 'vasos de planta'),
    'potted plant': ('vaso de planta', 'vasos de planta'),
    'bed': ('cama', 'camas'),
    'diningtable': ('mesa', 'mesas'),
    'dining table': ('mesa', 'mesas'),
    'toilet': ('vaso sanitário', 'vasos sanitários'),
    'tvmonitor': ('televisão', 'televisões'),
    'tv': ('televisão', 'televisões'),
    'laptop': ('notebook', 'notebooks'),
    'mouse': ('mouse', 'mouses'),
    'remote': ('controle remoto', 'controles remotos'),
    'keyboard': ('teclado', 'teclados'),
    'cell phone': ('celular', 'celulares'),
    'microwave': ('micro-ondas', 'micro-ondas'),
    'oven': ('forno', 'fornos'),
    'toaster': ('torradeira', 'torradeiras'),
    'sink': ('pia', 'pias'),
    'refrigerator': ('geladeira', 'geladeiras'),
    'book': ('livro', 'livros'),
    'clock': ('relógio', 'relógios'),
    'vase': ('vaso', 'vasos'),
    'scissors': ('tesoura', 'tesouras'),
    'teddy bear': ('ursinho de pelúcia', 'ursinhos de pelúcia'),
    'hair drier': ('secador de cabelo', 'secadores de cabelo'),
    'hair dryer': ('secador de cabelo', 'secadores de cabelo'),
    'toothbrush': ('escova de dentes', 'escovas de dentes'),
}

NUMEROS_PT = {2: 'duas', 3: 'três'}  # "duas pessoas", "três carros"
NUMEROS_PT_MASC = {2: 'dois', 3: 'três'}

# Palavras femininas, para concordar "duas"/"dois"
FEMININOS = {
    'pessoa', 'bicicleta', 'moto', 'placa de pare', 'ovelha', 'vaca',
    'zebra', 'girafa', 'mochila', 'bolsa', 'gravata', 'mala', 'bola',
    'pipa', 'luva de beisebol', 'prancha de surfe', 'raquete', 'garrafa',
    'taça', 'faca', 'colher', 'tigela', 'banana', 'maçã', 'laranja',
    'cenoura', 'pizza', 'rosquinha', 'cadeira', 'cama', 'mesa',
    'televisão', 'torradeira', 'pia', 'geladeira', 'tesoura',
    'escova de dentes',
}


def nome_em_portugues(classe, quantidade=1):
    """Traduz a classe do COCO; se não houver tradução, usa o nome original."""

    singular, plural = NOMES_PT.get(classe, (classe, classe))

    if quantidade == 1:
        return singular

    numeros = NUMEROS_PT if singular in FEMININOS else NUMEROS_PT_MASC
    numero = numeros.get(quantidade, str(quantidade))

    return f'{numero} {plural}'


# =====================================================
# POSIÇÃO, PROXIMIDADE E FRASE
# =====================================================

def posicao_na_imagem(x, w, largura):
    """Divide a imagem em três faixas verticais."""

    centro = x + w / 2

    if centro < largura / 3:
        return 'à esquerda'

    if centro > 2 * largura / 3:
        return 'à direita'

    return 'à frente'


def esta_perto(w, h, largura, altura):
    """
    Estimativa de proximidade pelo tamanho da caixa.
    Não é distância real: um objeto grande longe pode parecer "perto".
    """

    fracao_area = (w * h) / float(largura * altura)
    fracao_altura = h / float(altura)

    return (
        fracao_area >= LIMIAR_PERTO_AREA
        or fracao_altura >= LIMIAR_PERTO_ALTURA
    )


def montar_frase(deteccoes):
    """
    Agrupa as detecções por (classe, posição) e monta a frase falada.
    Grupos com algo perto vêm primeiro; depois os de maior área.
    Ex.: "pessoa à frente, perto. duas cadeiras à esquerda"
    """

    grupos = {}

    for d in deteccoes:

        chave = (d['classe'], d['posicao'])

        grupo = grupos.setdefault(chave, {
            'classe': d['classe'],
            'posicao': d['posicao'],
            'quantidade': 0,
            'perto': False,
            'area': 0.0,
        })

        grupo['quantidade'] += 1
        grupo['perto'] = grupo['perto'] or d['perto']
        grupo['area'] = max(grupo['area'], d['area'])

    ordenados = sorted(
        grupos.values(),
        key=lambda g: (not g['perto'], -g['area'])
    )

    partes = []

    for g in ordenados[:MAX_ITENS_FRASE]:

        texto = f"{nome_em_portugues(g['classe'], g['quantidade'])} {g['posicao']}"

        if g['perto']:
            texto += ', perto'

        partes.append(texto)

    return '. '.join(partes)


# =====================================================
# CARREGAMENTO DO YOLO
# =====================================================

def verificar_arquivos_yolo():

    faltando = [
        p for p in (weights_path, config_path, names_path)
        if not os.path.exists(p)
    ]

    if not faltando:
        return

    print('\n[GuiaSense] Arquivos do YOLOv3 não encontrados:')

    for p in faltando:
        print(f'  - {p}')

    print(
        '\nBaixe e coloque na pasta YOLO/ (na raiz do projeto):\n'
        '  https://pjreddie.com/media/files/yolov3.weights\n'
        '  https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg\n'
        '  https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names\n'
    )

    sys.exit(1)


verificar_arquivos_yolo()

net = cv2.dnn.readNet(weights_path, config_path)

with open(names_path, 'r', encoding='utf-8') as f:
    classes = [linha.strip() for linha in f if linha.strip()]

layer_names = net.getLayerNames()

output_layers = [
    layer_names[i - 1]
    for i in np.array(net.getUnconnectedOutLayers()).flatten()
]

# A rede do OpenCV não deve ser usada por duas requisições ao mesmo tempo
trava_rede = threading.Lock()

# Protege os arquivos e o estado compartilhado
trava_estado = threading.Lock()


def detectar_objetos(frame):
    """Roda o YOLOv3 e devolve a lista de detecções já com posição e proximidade."""

    altura, largura = frame.shape[:2]

    blob = cv2.dnn.blobFromImage(
        frame, 1 / 255.0, (416, 416), swapRB=True, crop=False
    )

    with trava_rede:
        net.setInput(blob)
        saidas = net.forward(output_layers)

    caixas, confiancas, ids_classe = [], [], []

    for saida in saidas:

        for deteccao in saida:

            scores = deteccao[5:]
            class_id = int(np.argmax(scores))
            confianca = float(scores[class_id])

            if confianca < CONFIANCA_MIN:
                continue

            cx = deteccao[0] * largura
            cy = deteccao[1] * altura
            w = deteccao[2] * largura
            h = deteccao[3] * altura

            # Recorta a caixa para dentro da imagem
            x0 = max(0, int(cx - w / 2))
            y0 = max(0, int(cy - h / 2))
            x1 = min(largura, int(cx + w / 2))
            y1 = min(altura, int(cy + h / 2))

            caixas.append([x0, y0, x1 - x0, y1 - y0])
            confiancas.append(confianca)
            ids_classe.append(class_id)

    if not caixas:
        return []

    # NMS por classe: uma pessoa não "apaga" a cadeira atrás dela
    indices = cv2.dnn.NMSBoxesBatched(
        caixas, confiancas, ids_classe, CONFIANCA_MIN, LIMIAR_NMS
    )

    resultados = []

    for i in np.array(indices).flatten():

        x, y, w, h = caixas[i]
        classe = classes[ids_classe[i]]

        resultados.append({
            'classe': classe,
            'objeto': nome_em_portugues(classe),
            'confianca': round(confiancas[i] * 100, 2),
            'posicao': posicao_na_imagem(x, w, largura),
            'perto': esta_perto(w, h, largura, altura),
            'area': round((w * h) / float(largura * altura), 4),
        })

    resultados.sort(key=lambda r: -r['confianca'])

    return resultados


# =====================================================
# EVENTOS (memória + arquivo)
# =====================================================

def carregar_eventos():
    """Lê eventos.txt ao iniciar, para continuar a numeração."""

    eventos = deque(maxlen=MAX_EVENTOS_MEMORIA)
    maior_id = 0

    if os.path.exists(arquivo_eventos):

        with open(arquivo_eventos, 'r', encoding='utf-8') as arquivo:

            for linha in arquivo:

                try:
                    evento = json.loads(linha)
                    maior_id = max(maior_id, int(evento['id']))
                    eventos.append(evento)

                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue

    return eventos, maior_id + 1


eventos_recentes, proximo_evento_id = carregar_eventos()

ultima_deteccao = {
    'objeto': 'nenhum',
    'confianca': 0.0,
    'frase': '',
    'deteccoes': [],
    'data_hora': None,
}

ultima_frase_evento = ''
instante_ultima_frase = 0.0


def salvar_resultado(resultados, frase, data_hora):
    """Histórico completo de cada imagem em resultados.txt."""

    with open(arquivo_resultados, 'a', encoding='utf-8') as arquivo:

        arquivo.write('=' * 50 + '\n')
        arquivo.write(f'Data e hora: {data_hora}\n')
        arquivo.write(f'Objetos detectados: {len(resultados)}\n')

        if resultados:

            arquivo.write(f'Frase: {frase}\n')
            arquivo.write('Descrição da imagem:\n')

            for item in resultados:
                arquivo.write(
                    f"- {item['objeto']} ({item['classe']}) {item['posicao']}"
                    f"{', perto' if item['perto'] else ''} "
                    f"(Confiança: {item['confianca']}%)\n"
                )

        else:
            arquivo.write('Nenhum objeto foi detectado na imagem.\n')

        arquivo.write('\n')


def registrar_evento(frase, resultados, data_hora):
    """Um evento por imagem com objetos, sem repetir a mesma frase em sequência."""

    global proximo_evento_id, ultima_frase_evento, instante_ultima_frase

    agora = time.monotonic()

    if (
        frase == ultima_frase_evento
        and agora - instante_ultima_frase < REPETIR_APOS_S
    ):
        return None

    evento = {
        'id': proximo_evento_id,
        'frase': frase,
        'objeto': resultados[0]['objeto'],
        'confianca': resultados[0]['confianca'],
        'objetos': [
            {k: r[k] for k in ('objeto', 'classe', 'confianca', 'posicao', 'perto')}
            for r in resultados
        ],
        'data_hora': data_hora,
    }

    with open(arquivo_eventos, 'a', encoding='utf-8') as arquivo:
        arquivo.write(json.dumps(evento, ensure_ascii=False) + '\n')

    eventos_recentes.append(evento)
    proximo_evento_id += 1
    ultima_frase_evento = frase
    instante_ultima_frase = agora

    return evento


# =====================================================
# ROTAS
# =====================================================

@app.route('/detectar', methods=['POST'])
def detectar():

    global ultima_deteccao

    dados_bytes = request.get_data()

    if not dados_bytes:
        return jsonify({'erro': 'Nenhum dado de imagem recebido'}), 400

    frame = cv2.imdecode(np.frombuffer(dados_bytes, np.uint8), cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({'erro': 'Falha ao decodificar a imagem'}), 400

    resultados = detectar_objetos(frame)
    frase = montar_frase(resultados) if resultados else ''
    data_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    with trava_estado:

        ultima_deteccao = {
            'objeto': resultados[0]['objeto'] if resultados else 'nenhum',
            'confianca': resultados[0]['confianca'] if resultados else 0.0,
            'frase': frase,
            'deteccoes': resultados,
            'data_hora': data_hora,
        }

        evento = registrar_evento(frase, resultados, data_hora) if resultados else None
        salvar_resultado(resultados, frase, data_hora)

    return jsonify({
        'status': 'sucesso',
        'frase': frase,
        'evento_id': evento['id'] if evento else None,
        'deteccoes': resultados,
    }), 200


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/ultima-deteccao', methods=['GET'])
def get_ultima_deteccao():

    with trava_estado:
        return jsonify(ultima_deteccao)


@app.route('/eventos', methods=['GET'])
def get_eventos():

    try:
        desde = int(request.args.get('desde', 0))

    except ValueError:
        return jsonify({'erro': 'Identificador invalido'}), 400

    with trava_estado:

        novos = [e for e in eventos_recentes if e['id'] > desde]

        return jsonify({
            'eventos': novos,
            'ultimo_id': proximo_evento_id - 1,
            'ultima_deteccao': ultima_deteccao,
        })


# =====================================================
# EXECUÇÃO
# =====================================================

if __name__ == '__main__':

    print(f'[GuiaSense] YOLOv3 carregado de {DIR_YOLO} ({len(classes)} classes)')
    print('[GuiaSense] Página de status: http://localhost:5000')

    # use_reloader=False: o modo debug com recarregador carregaria
    # o YOLO duas vezes (dois processos)
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('GUIASENSE_DEBUG') == '1',
        use_reloader=False,
        threaded=True,
    )
