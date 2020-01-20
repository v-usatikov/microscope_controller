from serial import Serial
import serial.tools.list_ports
import MotorController.Phytron_MCC2 as MCC2
import time

comlist = serial.tools.list_ports.comports()
comlist = [com.device for com in comlist]
print(comlist)
port = comlist[2]

# port = "/dev/cu.xrusbmodem14321"
#
# # print(MCC2.com_check(port))
#
#
# print(port)
ser = Serial(port, 115200, timeout=0.2)

time.sleep(1)
ser.flushInput()
# ser.write(b'\x02' + b'2Y33' + b'\x03')
# ser.write(b'\x02' + b'22P20S500' + b'\x03')
ser.write(b'\x02' + b'22S' + b'\x03')
ser.write(b'\x02' + b'4vbsdfhj' + b'\x03')


# ser.write(b'\x02' + b'1SA' + b'\x03')
# # ser.write(MCC2.command_format('SA', 1))
#
# print(MCC2.read_reply(ser))
print(ser.read_until(b'\x03'))
print(ser.read_until(b'\x03'))
# controller = 2
# motor = MCC2.PMotor(controller, 0)


# print([8, 9] + [1,2,3,4,5])
# if 1.1:
#     print(bool(str(False)))

# f = open("address.txt", "rt")

# print({1,2,3,4} | {2,4})
# print(str.isnumeric('0.4'))

# a = b'0123456'
# print(len(a), a[-2:], bool(b''))

# print(f'{15:x}')

# s = 'word1 word2 word3'
# s = b'wwww 2'
# print(s.split(b' ', 1))
# print(b' ' in s)
# command = b'\x02wwww 2\x03'
# print(command[:1], command[-1:], command[1:-1])
# print(command[:1] == b"\x02" and command[-1:] == b"\x03")
