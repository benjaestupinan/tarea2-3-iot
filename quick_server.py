import socket
import struct
import time

HOST = "0.0.0.0"
PORT = 1883

numeros = [10, 20, 30, 40, 50]

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as svr:
    svr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    svr.bind((HOST, PORT))
    svr.listen(1)

    print(f"Esperando conexion en {HOST}:{PORT}")

    conn, addr = svr.accept()

    with conn:
        print("Conectado por", addr)

        for n in numeros:
            conn.sendall(struct.pack("!I", n))
            print("Enviado:", n)
            time.sleep(1)

    print("Conexion cerrada")
