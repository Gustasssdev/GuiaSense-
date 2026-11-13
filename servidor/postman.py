import requests

url = 'http://127.0.0.1:5000/detectar'

caminho_imagem = 'Diogo.jpeg'

with open(caminho_imagem, 'rb') as f: 
    bytes_foto = f.read()

resposta = requests.post(url, data=bytes_foto, headers={'Content-Type': 'image/jpeg'})

print('Código HTTP:', resposta.status_code) 
print('Resposta do Flask:', resposta.json())