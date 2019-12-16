import getpass
import sys
import telnetlib


tn = telnetlib.Telnet('192.168.1.200',55551)

tn.write(b'*IDN?')
print(tn.read_some())

