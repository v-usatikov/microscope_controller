import concurrent.futures
import csv
import logging
import time
from copy import deepcopy
from typing import Dict, List, Tuple, Union

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


class SerialConnector(Connector):
    """Connector Objekt für eine Verbindung durch Serial Port."""
    beg_symbol = b"\x02"
    end_symbol = b"\x03"

    def __init__(self, port: str, timeout: float = 0.2, baudrate: float = 115200):
        self.ser = Serial(port, baudrate, timeout=timeout)

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

    def __init__(self, connector: Connector):
        self.connector = connector

    def go(self, bus: int, axis: int, shift: float):
        raise NotImplementedError

    def go_to(self, bus: int, axis: int, destination: float):
        raise NotImplementedError

    def stop(self, bus: int, axis: int, destination: float):
        raise NotImplementedError

    def get_position(self, bus: int, axis: int) -> float:
        raise NotImplementedError

    def set_position(self, bus: int, axis: int, new_position: float):
        raise NotImplementedError

    def get_parameter(self, bus: int, axis: int, parameter_name: str) -> float:
        raise NotImplementedError

    def set_parameter(self, bus: int, axis: int, parameter_name: str, neu_value: float):
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

    def check_connection(self) -> (bool, str):
        raise NotImplementedError



M_Coord = Tuple[int, int]
Param_Val = Dict[str, float]


def bus_check(bus: int, connector: Connector, timeout: float = None) -> (bool, str):
    """Prüft ob es bei dem Bus-Nummer ein Controller gibt, und gibt die Version davon zurück."""

    connector.clear_buffer()
    connector.send(command_format("IVR", bus))
    try:
        com_reply = read_reply(connector, timeout)
    except ReplyError as err:
        logging.error(str(err))
        return False, str(err)
    # print(COM_Antwort)

    if com_reply[0] is None:
        return False, None
    elif com_reply[0] is False:
        return False, 'Controller sagt, dass der "IVR" Befehl nicht ausgeführt wurde.'
    elif com_reply[1][0:3] == b'MCC':
        return True, com_reply[1]
    else:
        return False, com_reply[1]


def check_connection(connector: Connector) -> (bool, str):
    """Prüft ob es bei dem Com-Port tatsächlich ein Controller gibt, und gibt die Version davon zurück."""
    check = False
    for i in range(10):
        for j in range(4):
            check = bus_check(i, connector)
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


def __check_raw_motors_data(raw_motors_data: List[dict]) -> bool:
    right_header = ['bus', 'axis', 'position', 'min_limit', 'max_limit'] + list(PMotor.DEFAULT_MOTOR_CONFIG.keys())
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


def __transform_raw_motors_data(raw_motors_data: List[dict]) -> List[Tuple[Tuple[int, int], float, tuple, dict]]:
    transformed_motors_data = []
    for motor_line in raw_motors_data:
        coord = (int(motor_line['bus']), int(motor_line['axis']))
        position = float(motor_line['position'])

        min_limit = float(motor_line['min_limit']) if motor_line['min_limit'] != '' else None
        max_limit = float(motor_line['max_limit']) if motor_line['max_limit'] != '' else None
        soft_limits = (min_limit, max_limit)

        config = {'without_initiators': int(motor_line['without_initiators']),
                  'display_units': motor_line['display_units']}
        for key, value in motor_line.items():
            if key not in ['without_initiators', 'display_units']:
                config[key] = float(motor_line[key])
        transformed_motors_data.append((coord, position, soft_limits, config))

    return transformed_motors_data


def __check_raw_parameters_data(raw_config_data: List[dict]) -> (bool, str):
    for motor_line in raw_config_data:

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


def __transform_raw_parameters_data(raw_config_data: List[dict]) -> List[dict]:
    for motor_line in raw_config_data:

        if motor_line['Ohne Initiatoren(0 oder 1)'] != '':
            motor_line['Ohne Initiatoren(0 oder 1)'] = bool(int(motor_line['Ohne Initiatoren(0 oder 1)']))
        else:
            motor_line['Ohne Initiatoren(0 oder 1)'] = PMotor.DEFAULT_MOTOR_CONFIG['without_initiators']

        if motor_line['Einheiten'] != '':
            motor_line['Einheiten'] = motor_line['Einheiten']
        else:
            motor_line['Einheiten'] = PMotor.DEFAULT_MOTOR_CONFIG['display_units']

        if motor_line['Einheiten pro Schritt'] != '':
            motor_line['Einheiten pro Schritt'] = float(motor_line['Einheiten pro Schritt'])
        else:
            motor_line['Einheiten pro Schritt'] = PMotor.DEFAULT_MOTOR_CONFIG['display_u_per_step']

        for parameter_name in PBox.PARAMETER_NUMBER.keys():
            if motor_line[parameter_name] != '':
                motor_line[parameter_name] = float(motor_line[parameter_name])
            else:
                motor_line[parameter_name] = PBox.PARAMETER_DEFAULT[parameter_name]
    return raw_config_data


def read_config_from_file(address: str = 'input/Phytron_Motoren_config.csv') \
        -> (List[int], List[M_Coord], Dict[M_Coord, dict], Dict[M_Coord, Param_Val]):
    raw_config_data = read_csv(address)

    correct, message = __check_raw_parameters_data(raw_config_data)
    if not correct:
        raise ReadConfigError("Datei hat inkorrekte Data. " + message)

    config_data = __transform_raw_parameters_data(raw_config_data)

    # for row in config_data:
    #     print(row.keys(), row.values())

    controllers_to_init = []
    motors_to_init = []
    motors_info = {}
    motors_parameters = {}

    for motor_line in config_data:
        motor_coord = (int(motor_line['Bus']), int(motor_line['Achse']))
        motors_to_init.append(motor_coord)

        if motor_coord[0] not in controllers_to_init:
            controllers_to_init.append(motor_coord[0])

        motor_info = {'name': motor_line['Motor Name'],
                      'without_initiators': motor_line['Ohne Initiatoren(0 oder 1)'],
                      'display_units': motor_line['Einheiten'],
                      'display_u_per_step': motor_line['Einheiten pro Schritt']}
        motors_info[motor_coord] = motor_info

        motor_parameters = {}
        for parameter_name in PBox.PARAMETER_NUMBER.keys():
            motor_parameters[parameter_name] = motor_line[parameter_name]
        motors_parameters[motor_coord] = motor_parameters

    return controllers_to_init, motors_to_init, motors_info, motors_parameters


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


class PMotor:
    """Diese Klasse entspricht einem Motor, der mit einem MCC-2 Controller verbunden ist."""
    DEFAULT_MOTOR_CONFIG = {'without_initiators': 0,
                            'display_units': 'Schritte',
                            'display_u_per_step': 1,
                            'norm_per_contr': 1,
                            'displ_per_norm': 1,
                            'displ_null': 0,  # Anzeiger Null in Normierte Einheiten
                            'null_position': 0,  # Position von Anfang in Controller Einheiten
                            'end_position': 1000  # Position von Ende in Controller Einheiten
                            }

    def __init__(self, controller, axis: int):
        self.controller: PController = controller
        self.box = self.controller.box
        self.axis = axis

        self.name = 'Motor' + str(self.controller.bus) + "." + str(self.axis)
        self.config = self.DEFAULT_MOTOR_CONFIG
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
            parameters_values = self.box.PARAMETER_DEFAULT

        for name, value in parameters_values.items():
            self.set_parameter(self.box.PARAMETER_NUMBER[name], value)

    def set_config(self, motor_config: dict = None):
        """Einstellt Name, Initiatoren Status, display_units, display_u_per_step anhand angegebene Dict"""
        if motor_config is None:
            self.config = self.DEFAULT_MOTOR_CONFIG
        else:
            for key, value in motor_config.items():
                self.config[key] = value

    def get_parameters(self) -> Dict[str, float]:
        """Liest die Parametern aus Controller und gibt zurück Dict mit Parameterwerten"""
        parameters_values = {}
        for par_name, par_number in self.box.PARAMETER_NUMBER.items():
            parameter_value = self.read_parameter(par_number)
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
            return self.__norm_to_displ(value, rel)
        elif current_u == "displ" and to == "norm":
            return self.__displ_to_norm(value, rel)
        elif current_u == "contr" and to == "displ":
            value = self.__contr_to_norm(value, rel)
            return self.__norm_to_displ(value, rel)
        elif current_u == "displ" and to == "contr":
            value = self.__displ_to_norm(value, rel)
            return self.__norm_to_contr(value, rel)

    def __contr_to_norm(self, value: float, rel: bool) -> float:
        if not rel:
            value = value - self.null_position
        value *= self.norm_per_contr
        return value

    def __norm_to_contr(self, value: float, rel: bool) -> float:
        value /= self.norm_per_contr
        if not rel:
            value = value + self.null_position
        return value

    def __norm_to_displ(self, value: float, rel: bool) -> float:
        if not rel:
            value = value - self.displ_null
        value *= self.displ_per_norm
        return value

    def __displ_to_norm(self, value: float, rel: bool) -> float:
        value /= self.displ_per_norm
        if not rel:
            value = value + self.displ_null
        return value

    def set_display_null(self, displ_null: float = None):
        """Anzeiger Null in Normierte Einheiten einstellen"""
        if displ_null is None:
            self.displ_null = self.position()
        else:
            self.displ_null = displ_null

    def soft_limits_einstellen(self, soft_limits, units: str = 'norm'):
        """soft limits einstellen"""
        self.soft_limits = tuple(map(lambda val: self.transform_units(val, units, to='norm'), soft_limits))

    def go_to(self, destination: float, units: str = 'norm') -> bool:
        """Bewegt den motor zur absoluten position, die als destination gegeben wird."""
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
        reply = self.command("A" + str(destination))
        if reply[0] is True:
            logging.info(f'Motor {self.axis} beim Controller {self.controller.bus} wurde zu {destination} geschickt. '
                         f'Controller antwort ist "{reply}"')
        else:
            logging.error(
                f'Motor {self.axis} beim Controller {self.controller.bus} wurde zu {destination} nicht geschickt. '
                f'Controller antwort ist "{reply}"')
        return reply[0]

    def go(self, shift: float, units: str = 'norm', calibrate: bool = False):
        """Bewegt den motor relativ um gegebener Verschiebung."""
        shift = float(shift)
        if self.soft_limits != (None, None) and not calibrate:
            shift = self.transform_units(shift, units, to='norm')
            position = self.position('norm')
            destination = position + shift
            return self.go_to(destination, 'norm')

        shift = self.transform_units(shift, units, to='contr')
        reply = self.command(str(shift))
        if reply[0] is True:
            logging.info(f'Motor {self.axis} beim Controller {self.controller.bus} wurde um {shift} verschoben. '
                         f'Controller antwort ist "{reply}"')
        else:
            msg = f'Motor {self.axis} beim Controller {self.controller.bus} wurde um {shift} nicht verschoben. ' \
                  f'Controller antwort ist "{reply}"'
            logging.error(msg)

        return reply[0]

    def stop(self):
        """Stoppt die Achse"""
        reply = self.command("S")
        logging.info(f'Motor {self.axis} beim Controller {self.controller.bus} wurde gestoppt. '
                     f'Controller antwort ist "{reply}"')
        return reply[0]

    def stand(self):
        """Gibt zurück bool Wert ob Motor steht"""
        reply = self.command('=H')
        if reply[1] == b'E':
            return True
        elif reply[1] == b'N':
            return False
        else:
            raise ReplyError('Unerwartete Antwort vom Controller!')

    def wait_motor_stop(self, stop_indicator: Union[StopIndicator, None] = None):
        """Haltet die programme, bis alle Motoren stoppen."""
        while not self.stand():
            if stop_indicator is not None:
                if stop_indicator.has_stop_requested():
                    return
            time.sleep(0.5)

    def command(self, text):
        """Befehl für den Motor ausführen"""
        return self.controller.command(str(self.axis) + str(text))

    def initiators(self, check: bool = True) -> (bool, bool):
        """Gibt zurück der Status der Initiatoren als List von bool Werten in folgende Reihenfolge: -, +"""
        if self.axis == 1:
            status = self.controller.initiators_status()[:2]
        elif self.axis == 2:
            status = self.controller.initiators_status()[2:]
        else:
            raise ValueError(f'Achsnummer ist falsch! "{self.axis}"')

        if check:
            if status[0] and status[1]:
                raise MotorError("Beider Initiatoren sind Aktiviert. Motor ist falsch konfiguriert oder kaputt!")

        return status[0], status[1]

    def read_parameter(self, number) -> float:
        """Liest einen Parameter Nummer number für die Achse"""
        reply = self.command("P" + str(number) + "R")
        if reply[0] is False:
            raise ConnectError(f"Hat nicht geklappt einen Parameter zu lesen. Controller Antwort ist: {reply}")
        return float(reply[1])

    def set_parameter(self, number: int, new_value: float) -> (bool, str):
        """Ändert einen Parameter Nummer number für die Achse"""
        reply = self.command("P" + str(number) + "S" + str(new_value))
        if reply[0] is False:
            raise ConnectError("Hat nicht geklappt einen Parameter zu ändern.")
        return reply[0]

    def position(self, units: str = 'norm') -> float:
        """Gibt die aktuelle position zurück"""
        position = self.read_parameter(20)
        return self.transform_units(position, 'contr', to=units)

    def at_the_end(self):
        """Gibt zurück einen bool Wert, ob der End-Initiator aktiviert ist."""
        return self.initiators()[1]

    def at_the_beginning(self):
        """Gibt zurück einen bool Wert, ob der Anfang-Initiator aktiviert ist."""
        return self.initiators()[0]

    def set_position(self, position: float, units: str = 'norm'):
        """Ändern die Zähler der aktuelle position zu angegebenen Wert"""
        position = float(position)
        self.set_parameter(20, self.transform_units(position, units, to='contr'))
        logging.info(f'position wurde eingestellt. ({position})')

    def set_null(self):
        """Einstellt die aktuelle position als null"""
        self.set_parameter(20, 0)

    def read_conversion_factors(self) -> float:
        self.norm_per_contr = self.read_parameter(3)
        return self.norm_per_contr

    def set_conversion_factor(self, conversion_factor: float):
        self.set_parameter(3, conversion_factor)
        self.norm_per_contr = conversion_factor

    def calibrate(self, stop_indicator: StopIndicator = None):
        """Kalibrierung von den gegebenen Motoren"""
        if not self.without_initiators:
            logging.info(f'Kalibrierung vom Motor {self.name} wurde angefangen.')

            motor = self

            # Voreinstellung der Parametern
            motor.set_parameter(1, 1)
            motor.set_parameter(2, 1)
            motor.set_parameter(3, 1)

            # Bis zum Ende laufen
            while not self.at_the_end():
                motor.go(500000, calibrate=True)
                self.wait_motor_stop(stop_indicator)
                if stop_indicator is not None:
                    if stop_indicator.has_stop_requested():
                        return
            end = motor.position()

            # Bis zum Anfang laufen
            while not self.at_the_beginning():
                motor.go(-500000, calibrate=True)
                self.wait_motor_stop(stop_indicator)
                if stop_indicator is not None:
                    if stop_indicator.has_stop_requested():
                        return
            beginning = motor.position()

            # Null einstellen
            motor.set_null()

            # Skala normieren
            self.norm_per_contr = 1000 / (end - beginning)

            logging.info(f'Kalibrierung von Motor {self.name} wurde abgeschlossen.')
        else:
            logging.error(f'Motor {self.name} hat keine Initiators und kann nicht kalibriert werden!')


class PController:
    """Diese Klasse entspricht einem MCC-2 Controller"""

    def __init__(self, box, bus: int):

        self.box: PBox = box
        self.connector = self.box.connector
        self.bus = bus
        self.motor: Dict[int, PMotor] = {}

        if self.check_controller()[0] is False:
            raise ConnectError("Controller #{} antwortet nicht oder ist nicht verbunden!".format(self.bus))

    def __iter__(self):
        return (motor for motor in self.motor.values())

    def check_controller(self):
        """Prüfen, ob der Controller da ist und funktioniert"""
        return bus_check(self.bus, self.connector)

    def command(self, text: str, with_reply: bool = True, timeout: float = None) -> (bool, bytes):
        """Befehl für den Controller ausführen"""
        return self.box.command(text, self.bus, with_reply, timeout)

    def save_parameters_in_eprom(self):
        """Speichert die aktuelle Parametern in Flash EPROM des Controllers"""
        reply = self.command("SA", timeout=5)
        if reply[0] is False:
            raise ConnectError("Hat nicht geklappt Parametern in Controller-Speicher zu sichern.")

    def initiators_status(self) -> (bool, bool, bool, bool):
        """Gibt zurück der Status der Initiatoren für beide Achsen als 4 bool Werten
        in folgende Reihenfolge: X-, X+, Y-, Y+ """
        reply = self.command("SUI")
        i_status = [False] * 4

        if reply[0] is True:
            reply_str = reply[1].decode()
            # print(Antwort_str)

            # für X Achse
            if reply_str[2] == "-":
                i_status[0] = True
            elif reply_str[2] == "+":
                i_status[1] = True
            elif reply_str[2] == "2":
                i_status[0] = True
                i_status[1] = True
            elif reply_str[2] == "0":
                i_status[0] = False
                i_status[1] = False
            else:
                raise ReplyError(f'Fehler: Unerwartete Antwort vom Controller. "{reply_str}"')

            # für Y Achse
            if reply_str[3] == "-":
                i_status[2] = True
            elif reply_str[3] == "+":
                i_status[3] = True
            elif reply_str[3] == "2":
                i_status[2] = True
                i_status[3] = True
            elif reply_str[3] == "0":
                i_status[2] = False
                i_status[3] = False
            else:
                raise ReplyError(f'Fehler: Unerwartete Antwort vom Controller. "{reply_str}"')

            return tuple(i_status)

        else:
            raise ConnectError(f"Controller #{self.bus} antwortet nicht oder ist nicht verbunden!")

    def motors_running(self) -> bool:
        """Gibt zurück der Status der Motoren, ob die Motoren in Lauf sind."""
        reply = self.command("SH")
        if reply[1] == b'E':
            return False
        elif reply[1] == b'N':
            return True
        else:
            raise ReplyError(f'Unerwartete Antwort vom Controller! "{reply[1]}"')

    def wait_stop(self):
        """Haltet die programme, bis die Motoren stoppen."""
        while self.motors_running():
            time.sleep(0.5)

    def make_motors(self):
        """erstellt Objekten für alle verfügbare Motoren"""
        n_axes = self.n_axes()
        self.motor = {}
        for i in range(n_axes):
            self.motor[i + 1] = PMotor(self, i + 1)
        logging.info(f'Controller hat {n_axes} Motor Objekten für alle verfügbare Achsen erstellt.')

    def n_axes(self):
        """Gibt die Anzahl der verfügbaren Achsen zurück"""
        reply = self.command('IAR')

        if reply[0] is True:
            n_axes = int(reply[1])
            return n_axes
        else:
            raise ControllerError(
                f'Lesen der Achsen anzahl des Controllers {self.bus} ist fehlgeschlagen. '
                f'Antwort des Controllers:{reply}')

    def stop(self):
        """Stoppt alle Achsen des Controllers"""
        reply = True
        for Motor in self:
            reply = reply and Motor.stop()
        return reply


class PBox:
    """Diese Klasse entspricht einem Box mit einem oder mehreren MCC-2 Controller"""

    def __init__(self, connector: Connector, timeout: float = 0.2):
        self.connector = connector

        self.timeout = timeout
        self.report = ""
        self.bus_list = []
        self.controller: Dict[int, PController] = {}

        self.get_bus_list()
        logging.info(f'Box Objekt erstellt, {len(self.bus_list)} Controller gefunden.')

    def __iter__(self):
        return (controller for controller in self.controller.values())

    # noinspection PyUnboundLocalVariable,PyUnboundLocalVariable
    def get_bus_list(self):
        """Erstellt eine Liste der verfügbaren Controller in Box."""
        self.bus_list = []
        for i in range(5):
            for j in range(3):
                check = bus_check(i, self.connector)
                # print(check)
                if check[0]:
                    self.bus_list.append(i)
                    break
            if not check[0]:
                logging.error(f'Bei Bus Nummer {i} keinen Kontroller gefunden. COM Antwort:{check[1]}')
        if not self.bus_list:
            raise SerialError("Es wurde keine Controller gefunden am COM-Port!")

    def make_controllers(self):
        """erstellt Objekten für alle verfügbare Controller"""
        self.controller = {}
        for i in self.bus_list:
            self.controller[i] = PController(self, i)
        logging.info('Box hat {} Controller Objekten für Bus {} erstellt.'.format(len(self.bus_list), self.bus_list))

    def command(self, text: str, bus: int, with_reply: bool = True, timeout: float = None) \
            -> Union[Tuple[bool, bytes], None]:
        """Befehl für die Box ausführen"""
        self.connector.clear_buffer()
        self.connector.send(command_format(text, bus))
        if with_reply:
            reply = read_reply(self.connector, timeout)
            if reply[0] is None:
                raise ConnectError('Controller Antwortet nicht!')
            return reply
        else:
            return None

    def initialize(self):
        """Sucht und macht Objekte für alle verfügbare Controller und Motoren. Gibt ein Bericht zurück."""
        logging.info('Box Initialisierung wurde gestartet.')

        self.get_bus_list()
        report = ""
        n_axes = 0

        self.make_controllers()
        for Controller in self:
            Controller.make_motors()
            axes_in_controller = Controller.n_axes()
            n_axes += axes_in_controller

            report += f"Controller {Controller.bus} ({axes_in_controller} Achsen)\n"

        report = f"Box wurde initialisiert. {len(self.bus_list)} Controller und {n_axes} Achsen gefunden:\n" + report
        logging.info(report)
        self.report = report
        return report

    def initialize_with_config_file(self, config_file: str = 'input/Phytron_Motoren_config.csv'):
        """Sucht und macht Objekte für alle verfügbare Controller und Motoren. Gibt ein Bericht zurück."""
        logging.info('Box Initialisierung wurde gestartet.')

        self.get_bus_list()
        report = ""
        n_motors = 0
        n_controllers = 0
        self.controller = {}

        controllers_to_init, motors_to_init, motors_info, motors_parameters = read_config_from_file(config_file)

        # Controller initialisieren
        absent_bus = []
        for bus in controllers_to_init:
            if bus in self.bus_list:
                self.controller[bus] = PController(self, bus)
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
            if axis <= self.controller[bus].n_axes():
                self.controller[bus].motor[axis] = PMotor(self.controller[bus], axis)
                n_motors += 1
            else:
                report += f"Achse {axis} ist beim Controller {bus} nicht vorhanden, " \
                          f"den Motor wurde nicht initialisiert.\n"

        self.set_motors_info(motors_info)
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

    def set_motors_info(self, motors_info: Dict[M_Coord, dict]):
        """Einstellt Name, Initiatoren Status, display_units, AE_in_Schritt der Motoren anhand angegebene Dict"""
        for motor_coord, motor_info in motors_info.items():
            motor = self.get_motor(motor_coord)
            motor.set_config(motor_info)

    def all_motors_stand(self) -> bool:
        """Gibt bool Wert zurück, ob alle Motoren stehen."""
        for controller in self:
            if controller.motors_running():
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
            for Motor in controller:
                motors_parameters[(controller.bus, Motor.axis)] = Motor.get_parameters()

        return motors_parameters

    def make_empty_config_file(self, address: str = 'input/Phytron_Motoren_config.csv'):
        """Erstellt eine Datei mit einer leeren Konfigurationstabelle"""
        f = open(address, "wt")

        separator = ';'

        # Motor liste schreiben
        header = ['Motor Name', 'Bus', 'Achse', 'Mit Initiatoren(0 oder 1)', 'Einheiten', 'Einheiten pro Schritt']
        for parameter_name in self.PARAMETER_NUMBER.keys():
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

    def initiators(self, motors_list: List[M_Coord] = None) -> List[Tuple[bool, bool]]:
        """Gibt zurück eine Liste mit Status von den Initiatoren von allen Motoren"""
        if motors_list is None:
            motors_list = self.motors_list()

        status_list = []
        for motor_coord in motors_list:
            motor = self.get_motor(motor_coord)
            status_list.append(motor.initiators())
        return status_list

    def calibrate_motors2(self, list_to_calibration: List[M_Coord] = None,
                          motors_to_calibration: List[PMotor] = None,
                          stop_indicator: StopIndicator = None,
                          reporter: WaitReporter = None):

        motors_to_calibration = [self.controller[bus].motor[axis] for bus, axis in self.motors_with_initiators()]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(lambda motor: motor.calibrate(), motors_to_calibration)

            for result in results:
                print(result)

    def calibrate_motors(self, list_to_calibration: List[M_Coord] = None,
                         motors_to_calibration: List[PMotor] = None,
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
                                     if not self.controller[bus].motor[axis].without_initiators]

        # Voreinstellung der Parametern
        for motor in motors_to_calibration:
            motor.set_parameter(1, 1)
            motor.set_parameter(2, 1)
            motor.set_parameter(3, 1)

        # Bis zum Ende laufen
        while True:
            all_at_the_end = True
            for motor in motors_to_calibration:
                at_the_end = motor.initiators()[1]
                if not at_the_end:
                    all_at_the_end = False
                    motor.go(500000, calibrate=True)
            print(self.initiators(list_to_calibration))
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
                at_the_beginning = motor.initiators()[0]
                if not at_the_beginning:
                    all_at_the_beginning = False
                    motor.go(-500000, calibrate=True)
            print(self.initiators(list_to_calibration))
            self.wait_all_motors_stop(stop_indicator, reporter)
            if stop_indicator is not None:
                if stop_indicator.has_stop_requested():
                    return
            if all_at_the_beginning:
                break

        beginning = []
        for motor in motors_to_calibration:
            beginning.append(motor.position())

        # Null einstellen
        for motor in motors_to_calibration:
            motor.set_null()

        for i, motor in enumerate(motors_to_calibration):
            motor.null_position = beginning[i]
            motor.end_position = end[i]
            motor.norm_per_contr = 1000 / (end[i] - beginning[i])

        if all_motors:
            logging.info('Kalibrierung von allen Motoren wurde abgeschlossen.')
        else:
            logging.info(f'Kalibrierung von Motoren {list_to_calibration} wurde abgeschlossen.')

    def save_data(self, address: str = "data/PMotoren_Positionen.txt"):
        """Sichert die aktuelle Positionen der Motoren in einer Datei"""

        def make_csv_row(list_to_convert: list) -> str:
            str_list = list(map(str, list_to_convert))
            return ';'.join(str_list) + '\n'

        def soft_limits_to_str(soft_limits: (float, float)) -> List[str, str]:
            min_limit = str(soft_limits[0]) if soft_limits[0] is not None else ''
            max_limit = str(soft_limits[1]) if soft_limits[1] is not None else ''
            return [min_limit, max_limit]

        f = open(address, "wt")

        header = ['bus', 'axis', 'position'] + list(PMotor.DEFAULT_MOTOR_CONFIG.keys())
        f.write(make_csv_row(header))

        for controller in self:
            for motor in controller:
                row = list(motor.coord()) + [motor.position('norm')] + + list(motor.config.values())
                f.write(make_csv_row(row))

        f.close()
        logging.info(f'Kalibrierungsdaten für  Motoren {self.motors_list()} wurde gespeichert.')

    def read_saved_motors_data(self, address: str = "data/PMotoren_Positionen.txt"):
        """Liest die gesicherte Positionen der Motoren aus einer Datei"""

        raw_config_data = read_csv(address)
        transform_raw_motors_data = __check_raw_parameters_data(raw_config_data)

        # logging.info('Kalibrierungsdaten für  Motoren {} wurde geladen.'.format(motors_list_f))
        # if list_to_calibration:
        #     logging.info('Motoren {} brauchen Kalibrierung.'.format(list_to_calibration))
        #
        # return list_to_calibration

    # noinspection PyUnboundLocalVariable
    def save_soft_limits(self, address: str = "data/PSoft_Limits.txt", without_read: bool = False):
        """Sichert die Soft Limits der Motoren in einer Datei"""
        # Sichern der Soft_Limits von unbenutzten in laufenden Program Motoren
        if not without_read:
            motors_list = self.motors_list()
            soft_limits_list_f = read_soft_limits(address)
            motors_in_file = list(soft_limits_list_f.keys())
            for motors_coord in motors_in_file:
                if motors_coord in motors_list:
                    del soft_limits_list_f[motors_coord]

        f = open(address, "wt")

        # Motor liste schreiben
        for controller in self:
            for motor in controller:
                if motor.soft_limits != (None, None):
                    bottom = motor.soft_limits[0] if motor.soft_limits[0] is not None else ''
                    top = motor.soft_limits[1] if motor.soft_limits[1] is not None else ''
                    row = f"{controller.bus},{motor.axis},{bottom},{top}\n"
                    f.write(row)

        if not without_read:
            for motor_coord, soft_limits in soft_limits_list_f.items():
                bottom = soft_limits[0] if soft_limits[0] is not None else ''
                top = soft_limits[1] if soft_limits[1] is not None else ''
                row = f"{motor_coord[0]},{motor_coord[1]},{bottom},{top}\n"
                f.write(row)

    def read_soft_limits(self, address: str = "data/PSoft_Limits.txt"):
        """Sichert die Soft Limits der Motoren in einer Datei"""
        soft_limits_list = read_soft_limits(address)

        for motor_coord, soft_limits in soft_limits_list.items():
            motor = self.get_motor(motor_coord)
            motor.soft_limits = soft_limits

    def motors_list(self) -> List[M_Coord]:
        """Gibt zurück eine Liste der allen Motoren in Format: [(bus, Achse), …]"""
        m_list = []
        for controller in self:
            for motor in controller:
                m_list.append(motor.coord())
        return m_list

    def motors_names_list(self) -> List[str]:
        """Gibt zurück eine Liste der Namen der Motoren"""
        names = []
        for controller in self:
            for motor in controller:
                names.append(motor.name)
        return names

    def controllers_list(self) -> List[int]:
        """Gibt zurück eine Liste der allen Controllern in Format: [bus, ...]"""
        controllers_list = []
        for Controller in self:
            controllers_list.append(Controller.bus)
        return controllers_list

    def motors_without_initiators(self) -> List[M_Coord]:
        """Gibt zurück eine Liste der allen Motoren ohne Initiatoren in Format: [(bus, Achse), …]"""
        motors_list = []
        for controller in self:
            for motor in controller:
                if motor.without_initiators:
                    motors_list.append(motor.coord())
        return motors_list

    def motors_with_initiators(self) -> List[M_Coord]:
        """Gibt zurück eine Liste der allen Motoren ohne Initiatoren in Format: [(bus, Achse), …]"""
        motors_list = []
        for controller in self:
            for motor in controller:
                if not motor.without_initiators:
                    motors_list.append(motor.coord())
        return motors_list

    def get_motor(self, coordinates: (int, int) = None, name: str = None) -> PMotor:
        """Gibt den Motor objekt zurück aus Koordinaten in Format (bus, Achse)"""

        if coordinates is None and name is None:
            raise ValueError("Kein Argument! Die Koordinaten oder der Name des Motors muss gegeben sein. ")
        elif coordinates is not None:
            bus, axis = coordinates
            return self.controller[bus].motor[axis]
        else:
            for controller in self:
                for motor in controller:
                    if motor.name == name:
                        return motor
            raise ValueError(f"Es gibt kein Motor mit solchem Name: {name}")

    def stop(self):
        """Stoppt alle Achsen"""
        reply = True
        for bus in self.controller:
            reply = reply and self.controller[bus].stop()
        return reply

    def save_parameters_in_eprom(self):
        """Speichert die aktuelle Parametern in Flash EPROM bei alle Controllern"""
        for Controller in self:
            Controller.save_parameters_in_eprom()

    def save_parameters_in_eprom_fast(self):
        """Speichert die aktuelle Parametern in Flash EPROM bei alle Controllern"""
        for Controller in self:
            Controller.command("SA", with_reply=False, timeout=5)
        return read_reply(self.connector)

    def close(self, without_eprom: bool = False, data_folder: str = 'data/'):
        """Alle nötige am Ende der Arbeit Operationen ausführen."""
        self.stop()
        self.save_data(address=data_folder + 'PMotoren_Positionen.txt')
        self.save_soft_limits(address=data_folder + 'PSoft_Limits.txt')
        print('Positionen und Soft Limits gesichert')
        if not without_eprom:
            self.save_parameters_in_eprom()
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


class FileReadError(Exception):
    """Grundklasse für alle Fehler mit der Datei"""


class PlantError(FileReadError):
    """Grundklasse für die Fehler wenn das Aufbau in Datei falsch beschrieben wurde."""


class ReadConfigError(Exception):
    """Grundklasse für alle Fehler mit Lesen der Configuration aus Datei"""


class UnitsTransformError(Exception):
    """Grundklasse für alle Fehler mit Transformation der Einheiten"""