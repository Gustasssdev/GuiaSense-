"""
Pede fotos à ESP32-CAM pelo cabo USB e envia ao servidor.py (YOLOv3).
Não precisa de Wi-Fi.

Uso (com o servidor.py rodando em outro terminal):
    python servidor/cam_serial.py                 # usa /dev/ttyUSB0
    python servidor/cam_serial.py /dev/ttyUSB1
Ctrl+C para parar. A última foto fica salva em ultima_foto.jpg.
"""

import sys
import time

import requests
import serial

PORTA = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'
BAUD = 921600          # igual ao do cam_serial.cpp
URL = 'http://127.0.0.1:5000/detectar'
INTERVALO = 2.0


def abrir_porta():
    ser = serial.Serial()
    ser.port = PORTA
    ser.baudrate = BAUD
    ser.timeout = 5
    # DTR/RTS desligados: na base ESP32-CAM-MB eles resetam a placa
    # ou a colocam em modo de gravação
    ser.dtr = False
    ser.rts = False
    ser.open()
    time.sleep(2)
    return ser


def pedir_foto(ser):
    ser.reset_input_buffer()
    ser.write(b'F')

    limite = time.time() + 5

    while time.time() < limite:

        linha = ser.readline()

        if linha.startswith(b'FOTO:'):

            tamanho = int(linha[5:].strip())
            dados = ser.read(tamanho)

            if len(dados) != tamanho:
                print(f'  foto incompleta ({len(dados)} de {tamanho} bytes)')
                return None

            if not dados.startswith(b'\xff\xd8'):
                print('  dados recebidos não são JPEG')
                return None

            return dados

        texto = linha.decode(errors='replace').strip()

        if texto:
            print('  [ESP]', texto)

    print('  a placa não respondeu (confira a porta e se gravou o cam_serial)')
    return None


def main():
    try:
        ser = abrir_porta()
    except serial.SerialException as erro:
        print(f'Não consegui abrir {PORTA}: {erro}')
        print('Confira: placa conectada, monitor serial fechado e grupo uucp.')
        sys.exit(1)

    print(f'Conectado em {PORTA}. Ctrl+C para parar.')

    try:
        while True:

            inicio = time.time()
            foto = pedir_foto(ser)

            if foto:

                with open('ultima_foto.jpg', 'wb') as f:
                    f.write(foto)

                t_foto = time.time() - inicio

                try:
                    r = requests.post(
                        URL, data=foto,
                        headers={'Content-Type': 'image/jpeg'}, timeout=30
                    ).json()

                    frase = r.get('frase') or '(nada reconhecido)'
                    print(f'{frase}   [foto {len(foto)//1024} KB em {t_foto:.1f} s, '
                          f'total {time.time() - inicio:.1f} s]')

                except requests.RequestException:
                    print('  servidor.py não está rodando (python servidor/servidor.py)')

            time.sleep(INTERVALO)

    except KeyboardInterrupt:
        pass

    finally:
        ser.close()


if __name__ == '__main__':
    main()
