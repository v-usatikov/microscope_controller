# coding= utf-8
import concurrent.futures
import csv
import logging
import time
from copy import deepcopy

import numpy as np
import serial.tools.list_ports

import ULoggingConfig
from MotorController.MotorControllerInterface import *

if __name__ == '__main__':
    ULoggingConfig.init_config()


class MCC2Communicator(ContrCommunicator):
    """Diese Klasse beschreibt die Sprache, die man braucht, um mit MCC2 Controller zu kommunizieren.
    Hier sind alle MCC2-spezifische Eigenschaften zusammen gesammelt"""

    # Dict, der für jeder Parameter dazugehöriger Nummer ausgibt.
    PARAMETER_NUMBER = {'Lauffrequenz': 14, 'Stoppstrom': 40, 'Laufstrom': 41, 'Booststrom': 42, 'Initiatortyp': 27}
    # Dict, mit den Beschreibungen der Parametern.
    PARAMETER_DESCRIPTION = {'Lauffrequenz': 'ein int Wert in Hz (max 40 000)',
                             'Stoppstrom': '',
                             'Laufstrom': '',
                             'Booststrom': '',
                             'Initiatortyp': '0 = PNP-Öffner oder 1 = PNP-Schließer'}
    # Dict, mit den Defaultwerten der Parametern.
    PARAMETER_DEFAULT = {'Lauffrequenz': 400, 'Stoppstrom': 2, 'Laufstrom': 2, 'Booststrom': 2, 'Initiatortyp': 0}

    def go(self, bus: int, axis: int, shift: float):
        command = self.__prefix(bus, axis) + str(shift).encode()
        self.connector.send(command)
        self.__check_command_result(self.read_reply())

    def go_to(self, bus: int, axis: int, destination: float):
        command = self.__prefix(bus, axis) + "A".encode() + str(destination).encode()
        self.connector.send(command)
        self.__check_command_result(self.read_reply())

    def stop(self, bus: int, axis: int, destination: float):
        command = self.__prefix(bus, axis) + "S".encode()
        self.connector.send(command)
        self.__check_command_result(self.read_reply())

    def get_position(self, bus: int, axis: int) -> float:
        command = self.__prefix(bus, axis) + f"P20".encode()
        self.connector.send(command)
        reply = self.read_reply()
        return self.__get_float_reply(reply)

    def set_position(self, bus: int, axis: int, new_position: float):
        command = self.__prefix(bus, axis) + f"P20S{new_position}".encode()
        self.connector.send(command)
        self.__check_command_result(self.read_reply())

    def get_parameter(self, bus: int, axis: int, parameter_name: str) -> float:
        param_number = self.PARAMETER_NUMBER[parameter_name]
        command = self.__prefix(bus, axis) + f"P{param_number}".encode()
        self.connector.send(command)
        reply = self.read_reply()
        return self.__get_float_reply(reply)

    def set_parameter(self, bus: int, axis: int, parameter_name: str, neu_value: float):
        param_number = self.PARAMETER_NUMBER[parameter_name]
        command = self.__prefix(bus, axis) + f"P{param_number}S{neu_value}".encode()
        self.connector.send(command)
        self.__check_command_result(self.read_reply())

    def motor_stand(self, bus: int, axis: int) -> bool:
        command = self.__prefix(bus, axis) + '=H'.encode()
        self.connector.send(command)
        reply = self.read_reply()
        return self.__get_bool_reply(reply)

    def motor_at_the_beg(self, bus: int, axis: int) -> bool:
        command = self.__prefix(bus, axis) + '=I-'.encode()
        self.connector.send(command)
        reply = self.read_reply()
        return self.__get_bool_reply(reply)

    def motor_at_the_end(self, bus: int, axis: int) -> bool:
        command = self.__prefix(bus, axis) + '=I+'.encode()
        self.connector.send(command)
        reply = self.read_reply()
        return self.__get_bool_reply(reply)

    def read_reply(self) -> (bool, Union[bytes, None]):
        """Antwort lesen, der nach einem Befehl erscheint."""
        reply = self.connector.read()

        if reply is None:
            return None, None
        elif reply[0] == b'\x06':
            return True, reply[1:]
        elif reply == b'\x15':
            return False, None
        else:
            raise ReplyError(f'Unerwartete Antwort vom Controller: {reply[1]}')

    def bus_list(self) -> Tuple[int]:
        bus_list = []
        for i in range(15):
            for j in range(4):
                check = self.bus_check(i)
                if check[0]:
                    bus_list.append(i)
                    break
        return tuple(bus_list)

    def axes_list(self, bus: int) -> Tuple[int]:
        command = self.__contr_prefix(bus) + "IAR".encode()
        self.connector.send(command)
        reply = self.read_reply()
        n_axes = int(self.__get_float_reply(reply))
        return tuple(range(n_axes))

    def check_connection(self) -> (bool, str):
        """Prüft ob es bei dem Com-Port tatsächlich ein Controller gibt, und gibt die Version davon zurück."""
        check = False
        for i in range(15):
            for j in range(4):
                check = self.bus_check(i)
                # print(check)
                if check[0]:
                    return check
        return check

    def bus_check(self, bus: int) -> (bool, str):
        """Prüft ob es bei dem Bus-Nummer ein Controller gibt, und gibt die Version davon zurück."""
        command = self.__contr_prefix(bus) + "IVR".encode()
        self.connector.send(command)
        try:
            reply = self.read_reply()
        except ReplyError as err:
            logging.error(str(err))
            return False, str(err)

        if reply[0] is None:
            return False, None
        elif reply[0] is False:
            return False, f'Unerwartete Antwort vom Controller: {reply[1]}!'
        elif reply[1][0:3] == b'MCC':
            return True, reply[1]
        else:
            return False, reply[1]

    @staticmethod
    def __check_command_result(reply: Tuple[bool, Union[bytes, None]]):
        if reply[0] is None:
            raise ReplyError('Der Controller antwortet nicht!')
        elif reply[0] is False:
            raise ControllerError('Controller hat den Befehl negativ quittiert!')
        elif reply[0] is True:
            if reply[1]:
                raise ReplyError(f'Unerwartete Antwort vom Controller: {reply[1]}!')

    @staticmethod
    def __get_float_reply(reply: Tuple[bool, Union[bytes, None]]) -> float:
        if reply[0] is None:
            raise ReplyError('Der Controller antwortet nicht!')
        elif reply[0] is False:
            raise ControllerError('Controller hat den Befehl negativ quittiert!')
        elif reply[0] is True:
            try:
                float(reply[1])
            except ValueError:
                raise ReplyError(f'Unerwartete Antwort vom Controller: {reply}!')

    @staticmethod
    def __get_bool_reply(reply: Tuple[bool, Union[bytes, None]]) -> bool:
        if reply[0] is None:
            raise ReplyError('Der Controller antwortet nicht!')
        elif reply[0] is False:
            raise ControllerError('Controller hat den Befehl negativ quittiert!')
        elif reply[1] == b'E':
            return True
        elif reply[1] == b'N':
            return False
        else:
            raise ReplyError(f'Unerwartete Antwort vom Controller: {reply[1]}')

    @staticmethod
    def __contr_prefix(bus: int) -> bytes:
        if bus > 15 or bus < 0:
            raise ValueError(f'bus muss ein Wert zwischen 0 und 15 haben und kein {bus}')
        return f'{bus:x}'.encode()

    @staticmethod
    def __axis_prefix(axis: int) -> bytes:
        if axis > 9 or axis < 0:
            raise ValueError(f'axis muss ein Wert zwischen 0 und 9 haben und kein {axis}')
        return str(axis).encode()

    def __prefix(self, bus: int, axis: int) -> bytes:
        return self.__contr_prefix(bus) + self.__axis_prefix(axis)

if __name__ == '__main__':
    # config0 = read_config_from_file0('/Users/prouser/Dropbox/Proging/Python_Projects/MikroskopController/MCC2_Demo_GUI/input/Phytron_Motoren_config.csv')
    # config = read_config_from_file('/Users/prouser/Dropbox/Proging/Python_Projects/MikroskopController/MCC2_Demo_GUI/input/Phytron_Motoren_config.csv')
    # print(config == config0)

    comlist = serial.tools.list_ports.comports()
    comlist = [com.device for com in comlist]
    print(comlist)

    connector1 = SerialConnector(comlist[2])
    box1 = PBox(connector1)

    box1.initialize_with_config_file('/Users/prouser/Dropbox/Proging/Python_Projects/MikroskopController/MCC2_Demo_GUI/input/Phytron_Motoren_config.csv')
    # print(box1.save_parameters_in_eprom_fast())


    # asyncio.run(box1.get_motor((2, 2)).calibrate())
    # box1.calibrate_motors2()

