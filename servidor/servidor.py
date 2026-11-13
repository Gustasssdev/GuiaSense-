from flask import Flask,request,jsonify

app = Flask(__name__)


@app.route('/upload', methods=['POST'])
def upload():

    dados = request.get_data()

    if not dados:
        return jsonify({'status': 'erro', 'mensagem': 'Nenhum dado recebido'}), 400

    eh_jpeg = dados.startswith(b'\xff\xd8')

    return(
        jsonify(
            {
                'status' : 'sucesso',
                'tamanho_bytes': len(dados),
                'fomato_valido': eh_jpeg, 
            }
        ), 200,
    )

if __name__ == '__main__':
    app.run(debug=True)