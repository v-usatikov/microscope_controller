import socket
import telnetlib
import threading
from time import sleep


class TCP_Emulator(threading.Thread):

    def go(self, TCP_IP, TCP_PORT):
        self.s_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s_out.bind((TCP_IP, TCP_PORT))
        self.start()

    def run(self) -> None:
        self.s_out.listen(1)
        self.conn, addr = self.s_out.accept()
        data = self.conn.recv(1000000)
        print('server got: ', data)

        for i in range(10):
            message = f"emulator at {i} sec\r\n".encode()
            self.conn.send(message)
            # print(message)
            sleep(0.5)
        # self.conn.close()
        # self.s_out.close()


TCP_IP = 'localhost'
TCP_PORT = 8001

server = TCP_Emulator()
server.go(TCP_IP, TCP_PORT)


s = socket.socket()
host = TCP_IP
port = TCP_PORT
s.connect((host, port))
s.send(b':CHAN0:VEL?\r\n')
s.settimeout(1)
for i in range(10):
    print("read")
    data = s.recv(100)
    print('received', data, len(data), 'bytes')
    sleep(2)
s.close()


# tn = telnetlib.Telnet(TCP_IP, TCP_PORT)
#
# tn.write(b'*IDN?')
# tn.timeout = 1
# for i in range(15):
#     print("read")
#     # print(tn.read_until(b'\n', 1))
#     print(tn.read_very_eager())
#     sleep(1)
# tn.close()