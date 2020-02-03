from time import sleep

from MotorController.MotorControllerInterface import Connector, SerialConnector, com_list
from MotorController.Phytron_MCC2 import MCC2SerialConnector

print(com_list())
connector = MCC2SerialConnector(com_list()[2])
sleep(1)

connector.send(b'22P3S0.1')
print(connector.read())

connector.send(b'22P20R')
print(connector.read()[1:])
#
# connector.send(b'22A100')
# print(connector.read())

# symbol = '89'
# print(symbol in '123456789ABCDEFabcdef')

# print(int(b'A', 16))

# string = 'A'
# print(string[1:])
# print('a='.upper())

# set1 = {2,1,4,3}
# list1 = [1,2,4,3]
# list2 = [2,1,4,3]
# print(list(set1) == list1)
# print(list2 == list1)