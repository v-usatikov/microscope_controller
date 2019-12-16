import socket
import sys

TCP_IP = '192.168.1.200'
TCP_PORT = 55551
BUFFER_SIZE = 20  # Normally 1024, but we want fast response


# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s = socket.socket()
host = TCP_IP
port = TCP_PORT
s.connect((host, port))

# s.send(b'*IDN?\n')
# s.send(b':DEV:NOBM?\r\n')
# s.send(b':PROP:DEV:SNUM?\r\n')
s.send(b':DEV:EST\r\n')
# s.send(b'*TST?\r\n')


print('Befehl gesendet')
data = s.recv(100)
print('received', data, len(data), 'bytes')
s.close()



# #Server
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# host = 'localhost'
# port = 8007
# s.bind((host, port))
# s.listen(1)
# conn, addr = s.accept()
# data = conn.recv(1000000)
# # print 'client is at', addr , data
# conn.send(data)
# conn.close()