# from serial import Serial
# import serial.tools.list_ports
# import MotorController.Phytron_MCC2 as MCC2
# import time

# comlist = serial.tools.list_ports.comports()
# comlist = [com.device for com in comlist]
# print(comlist)
# port = comlist[2]

# port = "/dev/cu.xrusbmodem14321"
#
# # print(MCC2.com_check(port))
#
#
# print(port)
# ser = Serial(port, 115200, timeout=0.2)
#
# time.sleep(1)
# ser.flushInput()
# # ser.write(b'\x02' + b'0X50' + b'\x03')
# ser.write(b'\x02' + b'1SA' + b'\x03')
# # ser.write(MCC2.command_format('SA', 1))
#
# print(MCC2.read_reply(ser))
# # print(ser.read_until(b'\x03'))
# controller = 2
# motor = MCC2.PMotor(controller, 0)


print(3 or 4 in [1,2,3,4,5])