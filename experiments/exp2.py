# from time import sleep
#
# from MotorController.MotorControllerInterface import Connector, SerialConnector, com_list
#
# print(com_list())
# connector = SerialConnector(com_list()[2])
# sleep(1)
#
# connector.send(b'22=I-')
# print(connector.read())
#
# # connector.send(b'22+200000')
# # print(connector.read())

# symbol = '89'
# print(symbol in '123456789ABCDEFabcdef')

# print(int(b'A', 16))

# string = 'A'
# print(string[1:])
# print('a='.upper())

set1 = {2,1,4,3}
list1 = [1,2,4,3]
list2 = [2,1,4,3]
print(list(set1) == list1)
print(list2 == list1)