# coding= utf-8
import serial.tools.list_ports
from serial import Serial

import logging
import ULoggingConfig
from .PErrors import *

if __name__ == '__main__':
    ULoggingConfig.init_config()


def command_format(text: str, bus: int):
    """Passt ein Minilog-Befehl an das richtiges Format, das man durch COM Port schicken kann."""
    if type(bus) is not int:
        raise TypeError('Befehl_Format: "bus" muss int sein, kein {}'.format(type(bus)))
    elif bus < 0 or bus > 9:
        raise ValueError('Befehl_Format: "bus" muss ein Wert zwischen 0 und 9 haben und kein {}'.format(bus))
    # print(b"\x02" + str(bus).encode() + text.encode() + b"\x03")
    return b"\x02" + str(bus).encode() + text.encode() + b"\x03"


def read_reply(ser: Serial) -> (bool, str):
    """Antwort lesen, der nach einem Befehl erscheint."""
    reply = ser.read_until(b'\x03')
    if reply == b'\x02\x06\x03':
        return True, None
    elif reply == b'\x02\x15\x03':
        return False, None
    elif reply == b'':
        return None, None
    elif reply[0] == 2 and reply[-1] == 3:
        return True, reply[2:-1]
    else:
        raise ReplyError('Fehler bei Antwort_lesen: Unerwartete Antwort! "{}"'.format(reply))


def com_list() -> list:
    """Gibt eine Liste der verfügbaren COM-Ports"""
    comlist = serial.tools.list_ports.comports()
    n_list = []
    for element in comlist:
        n_list.append(element.device)
    return n_list


def bus_check(bus: int, port: str = None, ser: Serial = None) -> (bool, str):
    """Prüft ob es bei dem Bus-Nummer ein Controller gibt, und gibt die Version davon zurück."""
    if ser is None:
        if port is not None:
            ser = serial.Serial(port, 115200, timeout=1)
        else:
            raise TypeError("Bus_check: Es gibt kein Argument! port oder ser muss gegeben sein!")
    else:
        port = None

    ser.flushInput()
    ser.write(command_format("IVR", bus))
    try:
        com_reply = read_reply(ser)
    except ReplyError as err:
        logging.error(str(err))
        return False, str(err)
    # print(COM_Antwort)

    if port is not None:
        ser.close()

    if com_reply[0] is None:
        return False, None
    elif com_reply[0] is False:
        return False, 'Controller sagt, dass der "IVR" Befehl nicht ausgeführt wurde.'
    elif com_reply[1][0:3] == b'MCC':
        return True, com_reply[1]
    else:
        return False, com_reply[1]


def com_check(port: str) -> (bool, str):
    """Prüft ob es bei dem Com-Port tatsächlich ein Controller gibt, und gibt die Version davon zurück."""
    check = False
    for i in range(10):
        for j in range(4):
            check = bus_check(i, port)
            # print(check)
            if check[0]:
                return check
    return check


def read_soft_limits(address="PSoft_Limits.txt"):
    """Liest die Soft Limits aus Datei und gibt Dict zurück"""
    try:
        f = open(address, "rt")
    except FileNotFoundError:
        return {}

    soft_limits_list = {}
    for row in f:
        row = row.rstrip('\n')
        row = row.split(',')
        bottom = float(row[2]) if row[2] != '' else None
        top = float(row[3]) if row[3] != '' else None
        soft_limits_list[(int(row[0]), int(row[1]))] = (bottom, top)

    return soft_limits_list
