from time import sleep

from MotorController.MotorControllerInterface import Connector, SerialConnector, com_list

print(com_list())
connector = SerialConnector(com_list()[2])
sleep(1)

connector.send(b'22=I-')
print(connector.read())

# connector.send(b'22+200000')
# print(connector.read())