import socket

#Server
s_in = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = 'localhost'
port = 8007
s_in.bind((host, port))
s_in.listen(1)
conn, addr = s_in.accept()

TCP_IP = '192.168.1.200'
TCP_PORT = 55551

s_out = socket.socket()
s_out.connect((TCP_IP, TCP_PORT))

while True:
    data = conn.recv(1000000)
    print('client is at', addr, data)
    s_out.send(data)
    print('Befehl gesendet')
    data = s_out.recv(100)
    print('received', data, len(data), 'bytes')
    conn.send(data)

# conn.close()
# s_out.close()
