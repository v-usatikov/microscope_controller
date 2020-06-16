import time
from time import sleep
from typing import Callable
from bitarray import bitarray

import numpy

from MotorController.MotorControllerInterface import EthernetConnector


def timer(func: Callable, *args):
    start = time.time()
    res = func(*args)
    end = time.time()
    print(f'took {round((end - start)*1000, 1)} ms')
    return res

ip = '192.168.0.200'
port = 55551
connector = EthernetConnector(ip, port, end_symbol=b'\r\n', timeout=0.004)


connector.send(b'*IDN?')
# connector.send(b'*IDN?')
print(connector.read())

connector.send(b':CHAN0:MMOD 0')
connector.send(b':CHAN1:MMOD 0')
connector.send(b':CHAN2:MMOD 0')

pos =0
connector.send(f':MOVE0 {pos*10**9}'.encode())
# connector.send(f':MOVE1 {pos*10**9}'.encode())
connector.send(f':MOVE2 {pos*10**9}'.encode())


# # connector.send(b'*IDN?111')
# connector.send(b':SYST:ERR:COUN?', False)
# connector.send(b':SYST:ERR:NEXT?', False)
# connector.send(b':SYST:ERR:NEXT?', False)
# connector.send(b':SYST:ERR:NEXT?', False)
# connector.send(b':SYST:ERR:NEXT?', False)
# connector.send(b':SYST:ERR:NEXT?', False)
#
# print(connector.read())
# print(connector.read())
# print(connector.read())
# print(connector.read())
# print(connector.read())

# print(timer(connector.clear_buffer))
# timer(connector.send, b'*IDN?')
# timer(connector.send, b'*IDN?')
# timer(connector.send, b'*IDN?')
# print(timer(connector.read))
# print(timer(connector.read))
# print(timer(connector.read))

# for i in range(10000):
#     connector.send(b'*IDN?', False)
#     connector.send(b'*IDN?')
#     read1 = connector.read()
#     read2 = connector.read()
#     if read1 != b'SmarAct;MCS2-00000905;MCS2-00000905;11/09/18':
#         print(f'read1 is false!')
#         break
#     if read2 is not None:
#         print(f'Failed at {i}')
#         break
#     if i % 100 == 0:
#         print(i)
# else:
#     print('Success!')

sleep(0.5)
connector.send(b':CHAN0:STATe?')
reply = connector.read()
print(reply)
int32 = int(reply)
Bits = list(map(int, format(int32, '016b')))
Bits.reverse()
print(Bits)
print('in move0:', Bits[0])
print('in move15:', Bits[15])
print('Endstop:', bool(Bits[8]))

connector.send(b':SYST:ERR:COUN?', False)
connector.send(b':SYST:ERR:NEXT?', False)
print(connector.read())
print(connector.read())


# connector.send(b'*IDN?')
# # connector.send(b'*IDN?')
# print(connector.read())

# connector.send(b':CHAN0:VEL 10.5')
# # connector.send(b'*IDN?')
# print(connector.read())
#
#
# connector.send(b':SYST:ERR:COUN?', False)
# connector.send(b':SYST:ERR:NEXT?', False)
# print(connector.read())
# print(connector.read())