import concurrent.futures
import csv
import logging
import time
from copy import deepcopy
from typing import Dict, List, Tuple, Union, Set

import serial.tools.list_ports
import serial.tools.list_ports
from serial import Serial

import ULoggingConfig

if __name__ == '__main__':
    ULoggingConfig.init_config()


class Connector:
    """Ein Objekt, durch das die Kommunikation zwischen dem Programm und dem Controller stattfindet."""
    beg_symbol: bytes
    end_symbol: bytes

    def mess_format(self, mess: bytes) -> bytes:
        return self.beg_symbol + mess + self.end_symbol

    def reply_format(self, reply: bytes) -> Union[bytes, None]:
        f_reply = deepcopy(reply)
        err = ReplyError(f'Unerwartete Antwort: "{reply}""')
        if not reply:
            return None

        if self.beg_symbol:
            if reply[:len(self.beg_symbol)] == self.beg_symbol:
                f_reply = f_reply[len(self.beg_symbol):]
            else:
                raise err
        if self.end_symbol:
            if reply[-len(self.end_symbol):] == self.end_symbol:
                f_reply = f_reply[:-len(self.end_symbol)]
            else:
                raise err
        return f_reply

    def send(self, message: bytes, clear_buffer=True):
        """Schickt ein Nachricht zum Controller."""
        raise NotImplementedError

    def read(self) -> Union[bytes, None]:
        """Liest ein Nachricht von dem Controller bis zum bestimmten End-Symbol oder bis zum maximale Anzahl von Bytes
         und gibt das zurück."""
        raise NotImplementedError

    def clear_buffer(self):
        """Löscht alle vorher empfangene information aus Buffer"""
        raise NotImplementedError

    def set_timeout(self, timeout: float):
        """Einstellt das Time-out"""
        raise NotImplementedError

    def get_timeout(self) -> float:
        """Einstellt das Time-out"""
        raise NotImplementedError


def com_list() -> List[str]:
    """Gibt eine Liste der verfügbaren COM-Ports"""
    comlist = serial.tools.list_ports.comports()
    n_list = []
    for element in comlist:
        n_list.append(element.device)
    return n_list


class SerialEmulator:
    """Interface für eine Emulation von einer Serial-Verbindung."""
    timeout: float = 0

    def write(self, command: bytes):
        raise NotImplementedError

    def read_until(self, end_symbol: bytes) -> bytes:
        raise NotImplementedError

    # noinspection PyPep8Naming
    def flushInput(self):
        raise NotImplementedError


class SerialConnector(Connector):
    """Connector Objekt für eine Verbindung durch Serial Port."""
    def __init__(self,
                 port: str = '',
                 beg_symbol: bytes = b'',
                 end_symbol: bytes = b'\n',
                 timeout: float = 0.2,
                 baudrate: float = 115200,
                 emulator: SerialEmulator = None):
        if emulator is not None:
            self.ser = emulator
        elif not port:
            raise ValueError('Port muss angegeben werden!')
        else:
            self.ser = Serial(port, baudrate, timeout=timeout)
        self.beg_symbol = beg_symbol
        self.end_symbol = end_symbol

    def send(self, message: bytes, clear_buffer=True):
        """Schickt ein Nachricht zum Controller."""
        if clear_buffer:
            self.clear_buffer()
        self.ser.write(self.mess_format(message))

    def read(self) -> bytes:
        """Liest ein Nachricht von dem Controller bis zum bestimmten End-Symbol und gibt das zurück."""
        return self.reply_format(self.ser.read_until(self.end_symbol))

    def clear_buffer(self):
        """Löscht alle vorher empfangene information aus Buffer"""
        self.ser.flushInput()

    def set_timeout(self, timeout: float):
        """Einstellt das Time-out"""
        self.ser.timeout = timeout

    def get_timeout(self) -> float:
        """Gibt den Wert des Time-outs zurück"""
        return self.ser.timeout


# class EthernetConnector(Connector):
#     """Connector Objekt für eine Verbindung durch Ethernet."""
#     beg_symbol = b''
#     end_symbol = b'\r\n'
#
#     def __init__(self, ip: str, port: str, timeout: float = 1):
#         self.socket = socket.socket()
#         self.socket.connect((ip, port))
#         self.socket.settimeout(timeout)
#
#     def send(self, message: bytes):
#         """Schickt ein Nachricht zum Controller."""
#         self.socket.send(message)
#
#     def read(self, end_symbol: bytes = None, max_bytes: int = 1024) -> bytes:
#         """Liest ein Nachricht von dem Controller und gibt das zurück."""
#         return self.socket.recv(max_bytes)


class ContrCommunicator:
    """Diese Klasse beschreibt die Sprache, die man braucht, um mit einem Controller zu kommunizieren.
    Hier sind alle herstellerspezifische Eigenschaften und Algorithmen zusammen gesammelt"""

    PARAMETER_DEFAULT: Dict

    def go(self, shift: float, bus: int, axis: int):
        raise NotImplementedError

    def go_to(self, destination: float, bus: int, axis: int):
        raise NotImplementedError

    def stop(self, bus: int, axis: int):
        raise NotImplementedError

    def get_position(self, bus: int, axis: int) -> float:
        raise NotImplementedError

    def set_position(self, new_position: float, bus: int, axis: int):
        raise NotImplementedError

    def get_parameter(self, parameter_name: str, bus: int, axis: int) -> float:
        raise NotImplementedError

    def set_parameter(self, parameter_name: str, neu_value: float, bus: int, axis: int):
        raise NotImplementedError

    def motor_stand(self, bus: int, axis: int) -> bool:
        raise NotImplementedError

    def motor_at_the_beg(self, bus: int, axis: int) -> bool:
        raise NotImplementedError

    def motor_at_the_end(self, bus: int, axis: int) -> bool:
        raise NotImplementedError

    def read_reply(self) -> (bool, bytes):
        raise NotImplementedError

    def bus_list(self) -> Tuple[int]:
        raise NotImplementedError

    def axes_list(self, bus: int) -> Tuple[int]:
        raise NotImplementedError

    def check_connection(self) -> (bool, bytes):
        raise NotImplementedError

    def command_to_box(self, command: bytes) -> bytes:
        raise NotImplementedError

    def command_to_modul(self, command: bytes, bus: int) -> bytes:
        raise NotImplementedError

    def command_to_motor(self, command: bytes, bus: int, axis: int) -> bytes:
        raise NotImplementedError

    def check_raw_input_data(self, raw_input_data: List[dict]) -> (bool, str):
        raise NotImplementedError


M_Coord = Tuple[int, int]
Param_Val = Dict[str, float]


# def bus_check(bus: int, connector: Connector, timeout: float = None) -> (bool, str):
#     """Prüft ob es bei dem Bus-Nummer ein Controller gibt, und gibt die Version davon zurück."""
#
#     connector.clear_buffer()
#     connector.send(command_format("IVR", bus))
#     try:
#         com_reply = read_reply(connector, timeout)
#     except ReplyError as err:
#         logging.error(str(err))
#         return False, str(err)
#     # print(COM_Antwort)
#
#     if com_reply[0] is None:
#         return False, None
#     elif com_reply[0] is False:
#         return False, 'Controller sagt, dass der "IVR" Befehl nicht ausgeführt wurde.'
#     elif com_reply[1][0:3] == b'MCC':
#         return True, com_reply[1]
#     else:
#         return False, com_reply[1]
#
#
# def check_connection(connector: Connector) -> (bool, str):
#     """Prüft ob es bei dem Com-Port tatsächlich ein Controller gibt, und gibt die Version davon zurück."""
#     check = False
#     for i in range(10):
#         for j in range(4):
#             check = bus_check(i, connector)
#             # print(check)
#             if check[0]:
#                 return check
#     return check


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


def read_csv(address: str, delimiter: str = ';') -> List[dict]:
    """Liest CSV-Datei, und gibt die Liste von Dicts für jede Reihe."""
    with open(address, newline='') as config_file:
        csv.register_dialect('my', delimiter=delimiter)
        data_from_file = list(csv.DictReader(config_file, dialect='my'))

    # Datei prüfen
    defect_error = FileReadError('Die CSV-Datei ist defekt und kann nicht gelesen werden!')
    if None in list(file_row.values() for file_row in data_from_file):
        raise defect_error

    n_columns = len(data_from_file[0])
    for file_row in data_from_file:
        if len(file_row) != n_columns:
            raise defect_error

    return data_from_file


def __check_raw_saved_data(raw_motors_data: List[dict]) -> bool:
    right_header = ['bus', 'axis', '__position', 'min_limit', 'max_limit'] + list(Motor.DEFAULT_MOTOR_CONFIG.keys())
    if raw_motors_data[0].keys() != right_header:
        return False

    for motor_line in raw_motors_data:
        if motor_line['min_limit'] != '':
            try:
                float(motor_line['min_limit'])
            except ValueError:
                return False
        if motor_line['max_limit'] != '':
            try:
                float(motor_line['max_limit'])
            except ValueError:
                return False

        for key, value in motor_line.items():
            if key not in ['display_units', 'min_limit', 'max_limit']:
                try:
                    float(motor_line['min_limit'])
                except ValueError:
                    return False
    return True


def __transform_raw_saved_data(raw_motors_data: List[dict]) -> Dict[Tuple[int, int], Tuple[float, tuple, dict]]:
    transformed_motors_data = {}
    for motor_line in raw_motors_data:
        coord = (int(motor_line['bus']), int(motor_line['axis']))
        position = float(motor_line['__position'])

        min_limit = float(motor_line['min_limit']) if motor_line['min_limit'] != 'None' else None
        max_limit = float(motor_line['max_limit']) if motor_line['max_limit'] != 'None' else None
        soft_limits = (min_limit, max_limit)

        config = {'without_initiators': int(motor_line['without_initiators']),
                  'display_units': motor_line['display_units']}
        for key, value in motor_line.items():
            if key not in ['without_initiators', 'display_units']:
                config[key] = float(motor_line[key])
        transformed_motors_data[coord] = (position, soft_limits, config)

    return transformed_motors_data


def read_saved_motors_data_from_file(address: str = 'data/saved_motors_data.csv'):
    raw_data = read_csv(address)
    __check_raw_saved_data(raw_data)
    return __transform_raw_saved_data(raw_data)


def __transform_raw_input_data(raw_config_data: List[dict], communicator: ContrCommunicator) -> List[dict]:
    for motor_line in raw_config_data:

        if motor_line['Ohne Initiatoren(0 oder 1)'] != '':
            motor_line['Ohne Initiatoren(0 oder 1)'] = int(motor_line['Ohne Initiatoren(0 oder 1)'])
        else:
            motor_line['Ohne Initiatoren(0 oder 1)'] = Motor.DEFAULT_MOTOR_CONFIG['without_initiators']

        if motor_line['Einheiten'] != '':
            motor_line['Einheiten'] = motor_line['Einheiten']
        else:
            motor_line['Einheiten'] = Motor.DEFAULT_MOTOR_CONFIG['display_units']

        if motor_line['Einheiten pro Schritt'] != '':
            motor_line['Einheiten pro Schritt'] = float(motor_line['Einheiten pro Schritt'])
        else:
            motor_line['Einheiten pro Schritt'] = Motor.DEFAULT_MOTOR_CONFIG['display_u_per_step']

        for parameter_name in communicator.PARAMETER_DEFAULT.keys():
            if motor_line[parameter_name] != '':
                motor_line[parameter_name] = float(motor_line[parameter_name])
            else:
                motor_line[parameter_name] = communicator.PARAMETER_DEFAULT[parameter_name]
    return raw_config_data


def read_input_config_from_file(communicator: ContrCommunicator, address: str = 'input/Phytron_Motoren_config.csv') \
        -> (List[int], List[M_Coord], Dict[M_Coord, dict], Dict[M_Coord, Param_Val]):
    raw_config_data = read_csv(address)

    correct, message = communicator.check_raw_input_data(raw_config_data)
    if not correct:
        raise ReadConfigError("Datei hat inkorrekte Data. " + message)

    config_data = __transform_raw_input_data(raw_config_data, communicator)

    # for row in config_data:
    #     print(row.keys(), row.values())

    controllers_to_init = []
    motors_to_init = []
    motors_config = {}
    motors_parameters = {}

    for motor_line in config_data:
        motor_coord = (int(motor_line['Bus']), int(motor_line['Achse']))
        motors_to_init.append(motor_coord)

        if motor_coord[0] not in controllers_to_init:
            controllers_to_init.append(motor_coord[0])

        motor_config = {'name': motor_line['Motor Name'],
                        'without_initiators': motor_line['Ohne Initiatoren(0 oder 1)'],
                        'display_units': motor_line['Einheiten'],
                        'display_u_per_step': motor_line['Einheiten pro Schritt']}
        motors_config[motor_coord] = motor_config

        motor_parameters = {}
        for parameter_name in communicator.PARAMETER_DEFAULT.keys():
            motor_parameters[parameter_name] = motor_line[parameter_name]
        motors_parameters[motor_coord] = motor_parameters

    return controllers_to_init, motors_to_init, motors_config, motors_parameters


class PTranslator:
    """Diese Klasse beschreibt die Sprache, die man braucht^ um mit MCC2 Controller zu kommunizieren."""


class StopIndicator:
    """Durch dieses Objekt kann man Erwartung von dem Stop von allen Motoren abbrechen.
    Es wird als argument für PBox.wait_all_motors_stop() verwendet."""

    def has_stop_requested(self) -> bool:
        raise NotImplementedError


class WaitReporter:
    """Durch dieses Objekt kann man die Liste der im Moment laufenden Motoren bekommen.
        Es wird als argument für PBox.wait_all_motors_stop() verwendet."""

    def report(self, motors_list: List[str]):
        raise NotImplementedError


class Motor:
    """Diese Klasse entspricht einem Motor, der mit einem MCC-2 Controller verbunden ist."""
    DEFAULT_MOTOR_CONFIG = {'without_initiators': 0,
                            'display_units': 'Schritte',
                            'display_u_per_step': 1.0,
                            'norm_per_contr': 1.0,
                            'displ_per_contr': 1.0,
                            'displ_null': 0.0,  # Anzeiger Null in normierte Einheiten
                            'null_position': 0.0,  # Position von Anfang in Controller Einheiten
                            }

    def __init__(self, controller, axis: int):
        self.controller: Controller = controller
        self.box = self.controller.box
        self.communicator = self.box.communicator
        self.axis = axis

        self.name = 'Motor' + str(self.controller.bus) + "." + str(self.axis)
        self.config = deepcopy(self.DEFAULT_MOTOR_CONFIG)
        self.set_parameters()

        self.soft_limits: Tuple[Union[None, float], Union[None, float]] = (None, None)

    def coord(self) -> (int, int):
        """Gibt die Koordinaten des Motors zurück"""
        return self.controller.bus, self.axis

    def without_initiators(self) -> bool:
        """Zeigt ob der Motor ohne Initiatoren ist."""
        return bool(self.config['without_initiators'])

    def set_parameters(self, parameters_values: Dict[str, float] = None):
        """Die Parametern einstellen laut angegebene Dict mit Parameterwerten"""
        # Parameter_Werte = {'Lauffrequenz': 4000, 'Stoppstrom': 5, 'Laufstrom': 11, 'Booststrom': 18}

        if parameters_values is None:
            parameters_values = self.communicator.PARAMETER_DEFAULT

        for name, value in parameters_values.items():
            self.set_parameter(name, value)

    def set_config(self, motor_config: dict = None):
        """Einstellt Name, Initiatoren Status, display_units, display_u_per_step anhand angegebene Dict"""
        if motor_config is None:
            self.config = deepcopy(self.DEFAULT_MOTOR_CONFIG)
        else:
            # print('motor_config', motor_config)
            for key, value in motor_config.items():
                if key == 'name':
                    self.name = value
                else:
                    self.config[key] = value
            # print(self.config)
            print('init', self.coord(), self.without_initiators())

    def get_parameters(self) -> Dict[str, float]:
        """Liest die Parametern aus Controller und gibt zurück Dict mit Parameterwerten"""
        parameters_values = {}
        for par_name in self.communicator.PARAMETER_DEFAULT.keys():
            parameter_value = self.read_parameter(par_name)
            parameters_values[par_name] = parameter_value
        return parameters_values

    def transform_units(self, value: float, current_u: str, to: str, rel: bool = False) -> float:
        """Transformiert einen Wert in andere Einheiten."""
        units_list = ["norm", "displ", "contr"]
        if current_u not in units_list:
            raise ValueError(f'Unbekante Einheiten! {units_list} wurde erwartet und kein: "{current_u}".')
        elif to not in units_list:
            raise ValueError(f'Unbekante Einheiten! {units_list} wurde erwartet und kein: "{to}".')
        if current_u == to:
            return value

        if current_u == "contr" and to == "norm":
            return self.__contr_to_norm(value, rel)
        elif current_u == "norm" and to == "contr":
            return self.__norm_to_contr(value, rel)
        elif current_u == "norm" and to == "displ":
            value = self.__norm_to_contr(value, rel)
            return self.__contr_to_displ(value, rel)
        elif current_u == "displ" and to == "norm":
            value = self.__displ_to_contr(value, rel)
            return self.__contr_to_norm(value, rel)
        elif current_u == "contr" and to == "displ":
            return self.__contr_to_displ(value, rel)
        elif current_u == "displ" and to == "contr":
            return self.__displ_to_contr(value, rel)

    def __contr_to_norm(self, value: float, rel: bool = False) -> float:
        if not rel:
            value = value - self.config['null_position']
        value *= self.config['norm_per_contr']
        return value

    def __norm_to_contr(self, value: float, rel: bool = False) -> float:
        value /= self.config['norm_per_contr']
        if not rel:
            value = value + self.config['null_position']
        return value

    def __contr_to_displ(self, value: float, rel: bool = False) -> float:
        if not rel:
            value = value - self.__norm_to_contr(self.config['displ_null'])
        value *= self.config['displ_per_contr']
        return value

    def __displ_to_contr(self, value: float, rel: bool = False) -> float:
        value /= self.config['displ_per_contr']
        if not rel:
            value = value + self.__norm_to_contr(self.config['displ_null'])
        return value

    def set_display_null(self, displ_null: float = None):
        """Anzeiger Null in Normierte Einheiten einstellen"""
        if displ_null is None:
            self.config['displ_null'] = self.position()
        else:
            self.config['displ_null'] = displ_null

    def soft_limits_einstellen(self, soft_limits: Tuple[float, float], units: str = 'norm'):
        """soft limits einstellen"""
        self.soft_limits = tuple(map(lambda val: self.transform_units(val, units, to='norm'), soft_limits))

    def go_to(self, destination: float, units: str = 'norm'):
        """Bewegt den motor zur absoluten __position, die als destination gegeben wird."""
        destination = float(destination)
        destination = self.transform_units(destination, units, to='norm')

        bottom, top = self.soft_limits
        if bottom is not None:
            if destination < bottom:
                destination = bottom
        if top is not None:
            if destination > top:
                destination = top
        if bottom is not None and top is not None:
            if top - bottom < 0:
                logging.error(f'Soft Limits Fehler: Obere Grenze ist kleiner als Untere! '
                              f'(Motor {self.axis} beim Controller {self.controller.bus}:)')
                return False

        destination = self.transform_units(destination, 'norm', to='contr')
        self.communicator.go_to(destination, *self.coord())
        logging.info(f'Motor {self.axis} beim Controller {self.controller.bus} wurde zu {destination} geschickt.')

    def go(self, shift: float, units: str = 'norm', calibrate: bool = False):
        """Bewegt den motor relativ um gegebener Verschiebung."""
        shift = float(shift)
        if self.soft_limits != (None, None) and not calibrate:
            shift = self.transform_units(shift, units, to='norm')
            position = self.position('norm')
            destination = position + shift
            return self.go_to(destination, 'norm')

        shift = self.transform_units(shift, units, to='contr')
        self.communicator.go(shift, *self.coord())
        logging.info(f'Motor {self.axis} beim Controller {self.controller.bus} wurde um {shift} verschoben. ')

    def stop(self):
        """Stoppt die Achse"""
        self.communicator.stop(*self.coord())
        logging.info(f'Motor {self.axis} beim Controller {self.controller.bus} wurde gestoppt.')

    def stand(self):
        """Gibt zurück bool Wert ob Motor steht"""
        return self.communicator.motor_stand(*self.coord())

    def wait_motor_stop(self, stop_indicator: Union[StopIndicator, None] = None):
        """Haltet die programme, bis alle Motoren stoppen."""
        while not self.stand():
            if stop_indicator is not None:
                if stop_indicator.has_stop_requested():
                    return
            time.sleep(0.5)

    def command(self, text):
        """Befehl für den Motor ausführen"""
        return self.communicator.command_to_motor(text, *self.coord())

    def read_parameter(self, parameter_name: str) -> float:
        """Liest einen Parameter Nummer number für die Achse"""
        return self.communicator.get_parameter(parameter_name, *self.coord())

    def set_parameter(self, parameter_name: str, new_value: float):
        """Ändert einen Parameter Nummer number für die Achse"""
        self.communicator.set_parameter(parameter_name, new_value, *self.coord())

    def position(self, units: str = 'norm') -> float:
        """Gibt die aktuelle __position zurück"""
        position = self.communicator.get_position(*self.coord())
        return self.transform_units(position, 'contr', to=units)

    def at_the_end(self):
        """Gibt zurück einen bool Wert, ob der End-Initiator aktiviert ist."""
        return self.communicator.motor_at_the_end(*self.coord())

    def at_the_beginning(self):
        """Gibt zurück einen bool Wert, ob der Anfang-Initiator aktiviert ist."""
        return self.communicator.motor_at_the_beg(*self.coord())

    def set_position(self, position: float, units: str = 'norm'):
        """Ändern die Zähler der aktuelle __position zu angegebenen Wert"""
        position = float(position)
        self.communicator.set_position(self.transform_units(position, units, to='contr'), *self.coord())
        logging.info(f'__position wurde eingestellt. ({position})')

    def set_displ_null(self):
        """Einstellt die aktuelle __position als null"""
        self.config['displ_null'] = self.position(units='norm')

    def calibrate(self, stop_indicator: StopIndicator = None):
        """Kalibrierung von den gegebenen Motoren"""
        if not self.without_initiators():
            logging.info(f'Kalibrierung vom Motor {self.name} wurde angefangen.')

            motor = self

            # Voreinstellung der Parametern
            motor.set_parameters()

            # Bis zum Ende laufen
            while not self.at_the_end():
                motor.go(500000, calibrate=True)
                self.wait_motor_stop(stop_indicator)
                if stop_indicator is not None:
                    if stop_indicator.has_stop_requested():
                        return
            end = motor.position('contr')

            # Bis zum Anfang laufen
            while not self.at_the_beginning():
                motor.go(-500000, calibrate=True)
                self.wait_motor_stop(stop_indicator)
                if stop_indicator is not None:
                    if stop_indicator.has_stop_requested():
                        return
            beginning = motor.position('contr')

            # Skala normieren
            self.config['norm_per_contr'] = 1000 / (end - beginning)
            self.config['null_position'] = beginning


            logging.info(f'Kalibrierung von Motor {self.name} wurde abgeschlossen.')
        else:
            logging.error(f'Motor {self.name} hat keine Initiators und kann nicht kalibriert werden!')


class Controller:
    """Diese Klasse entspricht einem MCC-2 Controller"""

    def __init__(self, box, bus: int):

        self.box: Box = box
        self.communicator = self.box.communicator
        self.bus = bus
        self.motor: Dict[int, Motor] = {}

    def __iter__(self):
        return (motor for motor in self.motor.values())

    def command(self, command: bytes) -> (bool, bytes):
        """Befehl für den Controller ausführen"""
        return self.communicator.command_to_modul(command, self.bus)

    # def save_parameters_in_eprom(self):
    #     """Speichert die aktuelle Parametern in Flash EPROM des Controllers"""
    #     reply = self.command("SA", timeout=5)
    #     if reply[0] is False:
    #         raise ConnectError("Hat nicht geklappt Parametern in Controller-Speicher zu sichern.")

    def motors_stand(self) -> bool:
        """Gibt zurück der Status der Motoren, ob die Motoren in Lauf sind."""
        for motor in self:
            if not motor.stand():
                return False
        return True

    def wait_stop(self):
        """Haltet die programme, bis die Motoren stoppen."""
        while not self.motors_stand():
            time.sleep(0.5)

    def make_motors(self):
        """erstellt Objekten für alle verfügbare Motoren"""
        axes_list = self.communicator.axes_list(self.bus)
        self.motor = {}
        for i in axes_list:
            self.motor[i] = Motor(self, i)
        logging.info(
            f'Controller hat {len(axes_list)} Motor Objekten für alle verfügbare Achsen erstellt, nämlich {axes_list}.')

    def stop(self):
        """Stoppt alle Achsen des Controllers"""
        for motor in self:
            motor.stop()


class Box:
    """Diese Klasse entspricht einem Box mit einem oder mehreren MCC-2 Controller"""

    def __init__(self, communicator: ContrCommunicator, input_file: str = None):
        self.communicator = communicator

        self.report = ""
        self.controller: Dict[int, Controller] = {}

        if input_file is not None:
            self.initialize_with_input_file(input_file)
        else:
            self.initialize()

    def __iter__(self):
        return (controller for controller in self.controller.values())

    def command(self, text: bytes) -> bytes:
        """Befehl für die Box ausführen"""
        return self.communicator.command_to_box(text)

    def initialize(self):
        """Sucht und macht Objekte für alle verfügbare Controller und Motoren. Gibt ein Bericht zurück."""
        logging.info('Box Initialisierung wurde gestartet.')

        report = ""
        n_axes = 0

        self.controller = {}
        for i in self.communicator.bus_list():
            self.controller[i] = Controller(self, i)

        for controller in self:
            controller.make_motors()
            axes_in_controller = len(controller.motor)
            n_axes += axes_in_controller

            report += f"Controller {controller.bus} ({axes_in_controller} Achsen)\n"

        report = f"Box wurde initialisiert. {len(self.controller)} Controller und {n_axes} Achsen gefunden:\n" + report
        logging.info(report)
        self.report = report
        return report

    def initialize_with_input_file(self, config_file: str = 'input/Phytron_Motoren_config.csv'):
        """Sucht und macht Objekte für alle verfügbare Controller und Motoren. Gibt ein Bericht zurück."""
        logging.info('Box Initialisierung wurde gestartet.')

        report = ""
        n_motors = 0
        n_controllers = 0
        self.controller = {}

        input_config = read_input_config_from_file(self.communicator, config_file)
        controllers_to_init, motors_to_init, motors_config, motors_parameters = input_config

        # Controller initialisieren
        absent_bus = []
        bus_list = self.communicator.bus_list()
        for bus in controllers_to_init:
            if bus in bus_list:
                self.controller[bus] = Controller(self, bus)
                n_controllers += 1
            else:
                if bus not in absent_bus:
                    absent_bus.append(bus)
        if len(absent_bus) > 1:
            report += f"Controller {absent_bus} sind nicht verbunden und wurden nicht initialisiert.\n"
        elif len(absent_bus) == 1:
            report += f"Controller {absent_bus} ist nicht verbunden und wurde nicht initialisiert.\n"

        # Motoren initialisieren
        for bus, axis in motors_to_init:
            if axis in self.communicator.axes_list(bus):
                self.controller[bus].motor[axis] = Motor(self.controller[bus], axis)
                n_motors += 1
            else:
                report += f"Achse {axis} ist beim Controller {bus} nicht vorhanden, " \
                          f"den Motor wurde nicht initialisiert.\n"

        print(motors_config)
        self.set_motors_config(motors_config)
        self.set_parameters(motors_parameters)

        report = f"{n_controllers} Controller und {n_motors} Motoren wurde initialisiert:\n" + report
        for controller in self:
            report += f'Controller {controller.bus}: '
            more_then_one = False
            for motor in controller:
                if more_then_one:
                    report += ', '
                report += motor.name
                more_then_one = True
            report += '\n'

        self.report = report
        return report

    def set_motors_config(self, motors_config: Dict[M_Coord, dict]):
        """Einstellt Name, Initiatoren Status, display_units, AE_in_Schritt der Motoren anhand angegebene Dict"""
        for motor_coord, motor_config in motors_config.items():
            motor = self.get_motor(motor_coord)
            motor.set_config(motor_config)

    def all_motors_stand(self) -> bool:
        """Gibt bool Wert zurück, ob alle Motoren stehen."""
        for controller in self:
            if not controller.motors_stand():
                return False
        return True

    def names_from_running_motors(self):
        """Gibt eine Liste der Namen von den im Moment laufenden Motoren zurück."""
        running_motors = []
        for controller in self:
            for motor in controller:
                if not motor.stand():
                    running_motors.append(motor.name)
        return running_motors

    def wait_all_motors_stop(self, stop_indicator: Union[StopIndicator, None] = None,
                             reporter: Union[WaitReporter, None] = None):
        """Haltet die programme, bis alle Motoren stoppen."""
        while not self.all_motors_stand():
            if stop_indicator is not None:
                if stop_indicator.has_stop_requested():
                    return
            if reporter is not None:
                reporter.report(self.names_from_running_motors())
            time.sleep(0.5)

    def set_parameters(self, motors_config: Dict[M_Coord, Param_Val]):
        """Die Parametern einstellen laut angegebene Dict in Format {(bus, Achse) : Parameterwerte,}"""
        available_motors = self.motors_list()
        for motor_coord, param_values in motors_config.items():
            if motor_coord in available_motors:
                self.get_motor(motor_coord).set_parameters(param_values)
            else:
                logging.warning(f"Motor {motor_coord} ist nicht verbunden und kann nicht konfiguriert werden.")

    def get_parameters(self) -> Dict[M_Coord, Param_Val]:
        """Liest die Parametern aus Controller und gibt zurück Dict mit Parameterwerten"""
        motors_parameters = {}

        for controller in self:
            for motor in controller:
                motors_parameters[(controller.bus, motor.axis)] = motor.get_parameters()

        return motors_parameters

    def make_empty_config_file(self, address: str = 'input/Phytron_Motoren_config.csv'):
        """Erstellt eine Datei mit einer leeren Konfigurationstabelle"""
        f = open(address, "wt")

        separator = ';'

        # Motor liste schreiben
        header = ['Motor Name', 'Bus', 'Achse', 'Mit Initiatoren(0 oder 1)', 'Einheiten', 'Einheiten pro Schritt']
        for parameter_name in self.communicator.PARAMETER_DEFAULT.keys():
            header.append(parameter_name)
        header_length = len(header)
        header = separator.join(header)
        f.write(header + '\n')

        for controller in self:
            for motor in controller:
                motorline = [''] * header_length
                motorline[0] = motor.name
                motorline[1] = str(controller.bus)
                motorline[2] = str(motor.axis)
                motorline = separator.join(motorline)
                f.write(motorline + '\n')

        logging.info('Eine Datei mit einer leeren Konfigurationstabelle wurde erstellt.')

    def __initiators(self, motors_list: List[M_Coord] = None) -> List[Tuple[bool, bool]]:
        """Gibt zurück eine Liste mit Status von den Initiatoren von allen Motoren"""
        if motors_list is None:
            motors_list = self.motors_list()

        status_list = []
        for motor_coord in motors_list:
            motor = self.get_motor(motor_coord)
            status_list.append((motor.at_the_beginning(), motor.at_the_end()))
        return status_list

    # def calibrate_motors2(self, list_to_calibration: List[M_Coord] = None,
    #                       motors_to_calibration: List[Motor] = None,
    #                       stop_indicator: StopIndicator = None,
    #                       reporter: WaitReporter = None):
    #
    #     motors_to_calibration = [self.controller[bus].motor[axis] for bus, axis in self.motors_with_initiators()]
    #
    #     with concurrent.futures.ThreadPoolExecutor() as executor:
    #         results = executor.map(lambda motor: motor.calibrate(), motors_to_calibration)
    #
    #         for result in results:
    #             print(result)

    def calibrate_motors(self, list_to_calibration: List[M_Coord] = None,
                         motors_to_calibration: List[Motor] = None,
                         stop_indicator: StopIndicator = None,
                         reporter: WaitReporter = None):
        """Kalibrierung von den gegebenen Motoren"""
        logging.info('Kalibrierung von allen Motoren wurde angefangen.')

        if list_to_calibration is None and motors_to_calibration is None:
            list_to_calibration = self.motors_with_initiators()
            all_motors = True
        else:
            all_motors = False

        # Motoren ohne Initiatoren aus der Liste entfernen
        if motors_to_calibration is None:
            motors_to_calibration = [self.controller[bus].motor[axis] for bus, axis in list_to_calibration
                                     if not self.controller[bus].motor[axis].without_initiators()]

        # # Voreinstellung der Parametern
        # for motor in motors_to_calibration:
        #     motor.set_parameters()

        # Bis zum Ende laufen
        while True:
            all_at_the_end = True
            for motor in motors_to_calibration:
                if not motor.at_the_end():
                    all_at_the_end = False
                    motor.go(500000, units='contr', calibrate=True)
            print(self.__initiators(list_to_calibration))
            self.wait_all_motors_stop(stop_indicator, reporter)
            if stop_indicator is not None:
                if stop_indicator.has_stop_requested():
                    return

            if all_at_the_end:
                break

        end = []
        for motor in motors_to_calibration:
            end.append(motor.position())

        # Bis zum Anfang laufen
        while True:
            all_at_the_beginning = True
            for motor in motors_to_calibration:
                if not motor.at_the_beginning():
                    all_at_the_beginning = False
                    motor.go(-500000, units='contr', calibrate=True)
            print(self.__initiators(list_to_calibration))
            self.wait_all_motors_stop(stop_indicator, reporter)
            if stop_indicator is not None:
                if stop_indicator.has_stop_requested():
                    return
            if all_at_the_beginning:
                break

        beginning = []
        for motor in motors_to_calibration:
            beginning.append(motor.position())

        for i, motor in enumerate(motors_to_calibration):
            motor.config['null_position'] = beginning[i]
            motor.config['norm_per_contr'] = 1000 / (end[i] - beginning[i])

        if all_motors:
            logging.info('Kalibrierung von allen Motoren wurde abgeschlossen.')
        else:
            logging.info(f'Kalibrierung von Motoren {list_to_calibration} wurde abgeschlossen.')

    def save_data(self, address: str = "data/saved_motors_data.txt"):
        """Sichert die aktuelle Positionen der Motoren in einer Datei"""

        def make_csv_row(list_to_convert: list) -> str:
            str_list = list(map(str, list_to_convert))
            return ';'.join(str_list) + '\n'

        def soft_limits_to_str(soft_limits: (float, float)) -> List[str, str]:
            min_limit = str(soft_limits[0]) if soft_limits[0] is not None else ''
            max_limit = str(soft_limits[1]) if soft_limits[1] is not None else ''
            return [min_limit, max_limit]

        # Bevor die Datei geändert wurde, die Data daraus sichern.
        try:
            saved_data = read_saved_motors_data_from_file(address)
        except FileNotFoundError:
            saved_data = {}

        f = open(address, "wt")

        header = ['bus', 'axis', '__position', 'min_limit', 'max_limit'] + list(Motor.DEFAULT_MOTOR_CONFIG.keys())
        f.write(make_csv_row(header))

        for controller in self:
            for motor in controller:
                row = [*motor.coord(), motor.position('norm')] + list(motor.soft_limits) + list(motor.config.values())
                f.write(make_csv_row(row))

        # Data von den abwesenden Motoren zurück in Datei schreiben
        # TODO разобраться можно ли расчитывать на определённый порядок в словаре питона
        if saved_data:
            absent_motors = set(saved_data.keys()) - self.motors_list()
            for coord in absent_motors:
                row = [*coord, saved_data[coord][0]] + list(saved_data[coord][1]) + list(saved_data[coord][2].values())
                f.write(make_csv_row(row))

        f.close()
        logging.info(f'Kalibrierungsdaten für  Motoren {self.motors_list()} wurde gespeichert.')

    def read_saved_motors_data(self, address: str = "data/saved_motors_data.txt"):
        """Liest die gesicherte Positionen der Motoren aus einer Datei"""
        saved_data = read_saved_motors_data_from_file(address)
        list_to_calibration = []
        success_list = []

        for controller in self:
            for motor in controller:
                if motor.coord() in saved_data.keys():
                    motor.config = saved_data[motor.coord()][2]
                    motor.set_position(saved_data[motor.coord()][0])
                    motor.soft_limits = saved_data[motor.coord()][1]
                    success_list.append(motor.coord())
                else:
                    list_to_calibration.append(motor.coord())

        logging.info(f'Gesicherte Daten für Motoren {success_list} wurde geladen.')
        if list_to_calibration:
            logging.info(f'Motoren {list_to_calibration} brauchen Kalibrierung.')

        return list_to_calibration

    def motors_list(self) -> Set[M_Coord]:
        """Gibt zurück eine Liste der allen Motoren in Format: [(bus, Achse), …]"""
        m_list = set()
        for controller in self:
            for motor in controller:
                m_list.add(motor.coord())
        return m_list

    def motors_names_list(self) -> Set[str]:
        """Gibt zurück eine Liste der Namen der Motoren"""
        names = []
        for controller in self:
            for motor in controller:
                names.append(motor.name)
        names_set = set(names)
        if len(names) < len(names_set):
            raise MotorNameError('Es gibt wiederholte Namen der Motoren!')
        return names_set

    def controllers_list(self) -> List[int]:
        """Gibt zurück eine Liste der allen Controllern in Format: [bus, ...]"""
        controllers_list = []
        for controller in self:
            controllers_list.append(controller.bus)
        return controllers_list

    def motors_without_initiators(self) -> List[M_Coord]:
        """Gibt zurück eine Liste der allen Motoren ohne Initiatoren in Format: [(bus, Achse), …]"""
        motors_list = []
        for controller in self:
            for motor in controller:
                if motor.without_initiators():
                    motors_list.append(motor.coord())
        return motors_list

    def motors_with_initiators(self) -> List[M_Coord]:
        """Gibt zurück eine Liste der allen Motoren ohne Initiatoren in Format: [(bus, Achse), …]"""
        motors_list = []
        for controller in self:
            for motor in controller:
                print(motor.coord(), motor.without_initiators())
                if not motor.without_initiators():
                    motors_list.append(motor.coord())
        print(motors_list)
        return motors_list

    def get_motor(self, coordinates: (int, int) = None, name: str = None) -> Motor:
        """Gibt den Motor objekt zurück aus Koordinaten in Format (bus, Achse)"""

        if coordinates is not None:
            bus, axis = coordinates
            return self.controller[bus].motor[axis]
        elif name is not None:
            for controller in self:
                for motor in controller:
                    if motor.name == name:
                        return motor
            raise ValueError(f"Es gibt kein Motor mit solchem Name: {name}")
        else:
            raise ValueError("Kein Argument! Die Koordinaten oder der Name des Motors muss gegeben sein. ")

    def stop(self):
        """Stoppt alle Achsen"""
        for controller in self:
            controller.stop()

    # def save_parameters_in_eprom(self):
    #     """Speichert die aktuelle Parametern in Flash EPROM bei alle Controllern"""
    #     for Controller in self:
    #         Controller.save_parameters_in_eprom()
    #
    # def save_parameters_in_eprom_fast(self):
    #     """Speichert die aktuelle Parametern in Flash EPROM bei alle Controllern"""
    #     for Controller in self:
    #         Controller.command("SA", with_reply=False, timeout=5)
    #     return read_reply(self.connector)

    def close(self, without_eprom: bool = False, data_folder: str = 'data/'):
        """Alle nötige am Ende der Arbeit Operationen ausführen."""
        self.stop()
        self.save_data(address=data_folder + 'saved_motors_data.txt')
        print('Motoren Data gesichert')
        # if not without_eprom:
        #     self.save_parameters_in_eprom()
        del self


class SerialError(Exception):
    """Base class for serial port related exceptions."""


class ConnectError(Exception):
    """Grundklasse für die Fehler bei der Verbindung mit einem Controller"""


class ReplyError(Exception):
    """Grundklasse für die Fehler bei der Verbindung mit einem Controller"""


class ControllerError(Exception):
    """Grundklasse für alle Fehler mit den Controllern"""


class MotorError(Exception):
    """Grundklasse für alle Fehler mit den Motoren"""


class NoMotorError(MotorError):
    """Grundklasse für die Fehler wann Motor nicht verbunden oder kaputt ist"""


class MotorNameError(Exception):
    """Grundklasse für die Fehler wann Motor nicht verbunden oder kaputt ist"""


class FileReadError(Exception):
    """Grundklasse für alle Fehler mit der Datei"""


class PlantError(FileReadError):
    """Grundklasse für die Fehler wenn das Aufbau in Datei falsch beschrieben wurde."""


class ReadConfigError(Exception):
    """Grundklasse für alle Fehler mit Lesen der Configuration aus Datei"""


class UnitsTransformError(Exception):
    """Grundklasse für alle Fehler mit Transformation der Einheiten"""
