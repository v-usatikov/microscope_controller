import socket
import sys
# TCP_IP = 'localhost'
# TCP_PORT = 8007
import time

TCP_IP = '192.168.1.200'
TCP_PORT = 55551
BUFFER_SIZE = 20  # Normally 1024, but we want fast response


# s_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s = socket.socket()
host = TCP_IP
port = TCP_PORT
s.connect((host, port))
# time.sleep(2)

# s.send(b':DEV:NOBM?\r\n')
# s.send(b':MODule0:TEMPerature?\r\n')
# s.send(b':PROP:DEV:SNUM?\r\n')
# s.send(b':DEV:EST\r\n')
# s.send(b'*TST?\r\n')

# s.send(b':CHAN0:MMOD 4\r\n')
# s.send(b':CHAN0:CAL:OPT 0\r\n')
# s.send(b':CAL0\r\n')

# s.send(b':CHAN0:REF:OPT 0\r\n')
# s.send(b':REF0\r\n')

# s.send(b':CHAN0:MMOD 1\r\n')
# s.send(b':CHAN0:VEL 400000000\r\n')
# s.send(b':CHAN0:ACC 0\r\n')
# s.send(b':MOVE0 500000000\r\n')

# s.send(b'*IDN?\n')
# s.send(b':CHANnel0:POSition?\r\n')
# s.send(b':CHAN0:STAT?\r\n')
s.send(b':CHAN0:VEL?\r\n')

# s.send(b':SYST:ERR:COUN?\r\n')
# s.send(b':SYST:ERR:NEXT?\r\n')


print('Befehl gesendet')
data = s.recv(100)
print('received', data, len(data), 'bytes')
s.close()



# #Server
# s_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# host = 'localhost'
# port = 8007
# s_out.bind((host, port))
# s_out.listen(1)
# conn, addr = s_out.accept()
# data = conn.recv(1000000)
# # print 'client is at', addr , data
# conn.send(data)
# conn.close()