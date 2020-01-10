# coding= utf-8
import threading

import serial.tools.list_ports

from MotorController.MotorControllerInterface import *

if __name__ == '__main__':
    ULoggingConfig.init_config()


# noinspection PyPep8Naming
def MCC2SerialConnector(port: str, timeout: float = 0.2, baudrate: float = 115200) -> SerialConnector:
    return SerialConnector(port=port, beg_symbol=b'\x02', end_symbol=b'\x03', timeout=timeout, baudrate=baudrate)


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
    PARAMETER_DEFAULT = {'Lauffrequenz': 400.0, 'Stoppstrom': 2, 'Laufstrom': 2, 'Booststrom': 2, 'Initiatortyp': 0}

    def __init__(self, connector: Connector):
        super().__init__(connector)
        self.connector.beg_symbol = b"\x02"
        self.connector.end_symbol = b"\x03"

    def go(self, shift: float, bus: int, axis: int):
        command = self.__prefix(bus, axis) + str(shift).encode()
        self.connector.send(command)
        self.__check_command_result(self.read_reply())

    def go_to(self, destination: float, bus: int, axis: int):
        command = self.__prefix(bus, axis) + "A".encode() + str(destination).encode()
        self.connector.send(command)
        self.__check_command_result(self.read_reply())

    def stop(self, bus: int, axis: int):
        command = self.__prefix(bus, axis) + "S".encode()
        self.connector.send(command)
        self.__check_command_result(self.read_reply())

    def get_position(self, bus: int, axis: int) -> float:
        command = self.__prefix(bus, axis) + f"P20".encode()
        self.connector.send(command)
        reply = self.read_reply()
        return self.__get_float_reply(reply)

    def set_position(self, new_position: float, bus: int, axis: int):
        command = self.__prefix(bus, axis) + f"P20S{new_position}".encode()
        self.connector.send(command)
        self.__check_command_result(self.read_reply())

    def get_parameter(self, parameter_name: str, bus: int, axis: int) -> float:
        param_number = self.PARAMETER_NUMBER[parameter_name]
        command = self.__prefix(bus, axis) + f"P{param_number}".encode()
        self.connector.send(command)
        reply = self.read_reply()
        return self.__get_float_reply(reply)

    def set_parameter(self, parameter_name: str, neu_value: float, bus: int, axis: int):
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
        elif reply[:1] == b'\x06':
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
            if not check[0]:
                logging.error(f'Bei Bus Nummer {i} keinen Kontroller gefunden. Controller Antwort:{check[1]}')
        if not bus_list:
            raise SerialError("Es wurde keine Controller gefunden!")
        return tuple(bus_list)

    def axes_list(self, bus: int) -> Tuple[int]:
        command = self.__contr_prefix(bus) + "IAR".encode()
        self.connector.send(command)
        reply = self.read_reply()
        n_axes = int(self.__get_float_reply(reply))
        return tuple(range(n_axes))

    def check_connection(self) -> (bool, bytes):
        """Prüft ob es bei dem Com-Port tatsächlich ein Controller gibt, und gibt die Version davon zurück."""
        check = False
        for i in range(15):
            for j in range(4):
                check = self.bus_check(i)
                # print(check)
                if check[0]:
                    return check
        return check

    def command_to_modul(self, command: bytes, bus: int) -> (bool, bytes):
        command = self.__contr_prefix(bus) + command
        self.connector.send(command)
        return self.read_reply()

    def command_to_motor(self, command: bytes, bus: int, axis: int) -> (bool, bytes):
        command = self.__prefix(bus, axis) + command
        self.connector.send(command)
        return self.read_reply()

    def check_raw_input_data(self, raw_input_data: List[dict]) -> (bool, str):
        for motor_line in raw_input_data:

            init_status = motor_line['Ohne Initiatoren(0 oder 1)']
            message = f'"Ohne Initiatoren" muss 0 oder 1 sein, und kein "{init_status}"'
            if init_status != '':
                try:
                    init_status = bool(int(motor_line['Ohne Initiatoren(0 oder 1)']))
                except ValueError:
                    return False, message
                if init_status not in (0, 1):
                    return False, message

            units_per_step = motor_line['Einheiten pro Schritt']
            message = f'"Einheiten pro Schritt" muss ein float Wert haben, und kein "{units_per_step}"'
            if units_per_step != '':
                try:
                    float(motor_line['Ohne Initiatoren(0 oder 1)'])
                except ValueError:
                    return False, message

        return True, ""

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
                return float(reply[1])
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


# noinspection PyPep8Naming
def MCC2BoxSerial(port: str, timeout: float = 0.2, baudrate: float = 115200, input_file: str = None) -> Box:
    connector = MCC2SerialConnector(port=port, timeout=timeout, baudrate=baudrate)
    communicator = MCC2Communicator(connector)
    return Box(communicator=communicator, input_file=input_file)


class MCC2BoxEmulator(SerialEmulator):
    def __init__(self, n_bus: int = 3, n_axes: int = 2, realtime: bool = False):
        self.realtime = realtime
        controller = {}
        for i in range(n_bus):
            controller[i] = MCC2ControllerEmulator(self, n_axes)

        self.buffer: bytes = b''

    def flushInput(self):
        self.buffer = b''

    def read_until(self, end_symbol: bytes) -> bytes:
        if end_symbol in self.buffer:
            answer, self.buffer = self.buffer.split(end_symbol, 1)
            return answer
        else:
            return self.buffer

    def write(self, command: bytes):
        """Liest, interpretiert und ausführt den angegebenen Befehl."""
        answer = b''
        confirm = b'\x06'
        denial = b'\x15'

        if command[:1] == b'\x02' and command[-1:] == b'\x03':
            command = command[1:-1]
            if command == b'IVR':
                answer = confirm + self.__controller_version()

        self.buffer += answer

    @staticmethod
    def __controller_version() -> bytes:
        return b'MCC2 Emulator v1.0'




class MCC2ControllerEmulator:
    def __init__(self, box: MCC2BoxEmulator, n_axes: int = 2):
        self.box = box
        motor = {}
        for i in range(1, n_axes+1):
            motor[i] = MCC2MotorEmulator(box)


class MCC2MotorEmulator:

    PARAMETER_NAME = inv_map = {v: k for k, v in MCC2Communicator.PARAMETER_NUMBER.items()}
    PARAMETER_VALUES = MCC2Communicator.PARAMETER_DEFAULT

    PARAMETER_NAME[3] = 'Umrechungsfaktor'
    PARAMETER_VALUES['Umrechungsfaktor'] = 1

    PARAMETER_NAME[20] = 'Position'
    PARAMETER_VALUES['Position'] = 0.0

    beginning = -10000
    end = 10000

    def __init__(self, box: MCC2BoxEmulator):
        self.box = box
        self.__stand = True
        self.__beg_initiator = False
        self.__end_initiator = False
        self.__destination = 0
        self.__stop = False

    def stand(self):
        return self.__stand

    def at_the_beg(self):
        return self.__beg_initiator

    def at_the_end(self):
        return self.__end_initiator

    def position(self):
        return self.__position() * self.PARAMETER_VALUES['Umrechungsfaktor']

    def set_position(self, value: float):
        self.PARAMETER_VALUES['Position'] = value/self.PARAMETER_VALUES['Umrechungsfaktor']

    def set_parameter(self, n, value):
        self.PARAMETER_VALUES[self.PARAMETER_NAME[n]] = value

    def move_to(self, destination: float):
        self.__destination = int(destination/self.PARAMETER_VALUES['Umrechungsfaktor'])
        if self.stand():
            threading.Thread(target=self.__move).start()

    def move(self, shift: float):
        self.move_to(self.position() + shift)

    def stop(self):
        self.__stop = True

    def sleep_one_step(self):
        time.sleep(1/self.__freq())

    def sleep_steps(self, n):
        for i in range(n):
            time.sleep(1 / self.__freq())

    def wait_stop(self):
        while not self.__stand:
            self.sleep_one_step()

    def __position(self):
        return self.PARAMETER_VALUES['Position']

    def __move(self):
        self.__stop = False
        self.__stand = False
        while self.__position() != self.__destination:
            if self.__position() > self.__destination:
                self.__step_back()
            else:
                self.__step_forward()
            if self.box.realtime:
                self.sleep_one_step()
            if self.__stop:
                break
        self.__stand = True

    def __step_forward(self):
        if not self.__end_initiator:
            self.PARAMETER_VALUES['Position'] += 1
        self.__initiators_sensor()

    def __step_back(self):
        if not self.__beg_initiator:
            self.PARAMETER_VALUES['Position'] -= 1
        self.__initiators_sensor()

    def __initiators_sensor(self):
        if self.__position() >= self.end:
            self.stop()
            self.__end_initiator = True
        else:
            self.__end_initiator = False

        if self.__position() <= self.beginning:
            self.stop()
            self.__beg_initiator = True
        else:
            self.__beg_initiator = False

    def __freq(self):
        return self.PARAMETER_VALUES['Lauffrequenz']









if __name__ == '__main__':
    # config0 = read_config_from_file0('/Users/prouser/Dropbox/Proging/Python_Projects/MikroskopController/MCC2_Demo_GUI/input/Phytron_Motoren_config.csv')
    # config = read_config_from_file('/Users/prouser/Dropbox/Proging/Python_Projects/MikroskopController/MCC2_Demo_GUI/input/Phytron_Motoren_config.csv')
    # print(config == config0)

    comlist = serial.tools.list_ports.comports()
    comlist = [com.device for com in comlist]
    print(comlist)

    connector1 = SerialConnector(comlist[2])
    box1 = Box(connector1)

    box1.initialize_with_input_file('/Users/prouser/Dropbox/Proging/Python_Projects/MikroskopController/MCC2_Demo_GUI/input/Phytron_Motoren_config.csv')
    # print(box1.save_parameters_in_eprom_fast())


    # asyncio.run(box1.get_motor((2, 2)).calibrate())
    # box1.calibrate_motors2()

