# coding= utf-8
import csv

import numpy as np
import serial.tools.list_ports
from serial import Serial
import time
from copy import deepcopy
from typing import Dict, List, Tuple, Union

import logging
import ULoggingConfig

if __name__ == '__main__':
    ULoggingConfig.init_config()

M_Coord = Tuple[int, int]
Param_Val = Dict[str, float]


def command_format(text: str, bus: int):
    """Passt ein Minilog-Befehl an das richtiges Format, das man durch COM Port schicken kann."""
    if type(bus) is not int:
        raise TypeError('Befehl_Format: "bus" muss int sein, kein {}'.format(type(bus)))
    elif bus < 0 or bus > 9:
        raise ValueError('Befehl_Format: "bus" muss ein Wert zwischen 0 und 9 haben und kein {}'.format(bus))
    print(b"\x02" + str(bus).encode() + text.encode() + b"\x03")
    return b"\x02" + str(bus).encode() + text.encode() + b"\x03"


def read_reply(ser: Serial, timeout: float = None) -> (bool, bytes):
    """Antwort lesen, der nach einem Befehl erscheint."""
    if timeout is not None:
        timeout0 = ser.timeout
        ser.timeout = timeout
    reply = ser.read_until(b'\x03')
    if reply == b'\x02\x06\x03':
        result = (True, None)
    elif reply == b'\x02\x15\x03':
        result = (False, None)
    elif reply == b'':
        result = None, None
    elif reply[0] == 2 and reply[-1] == 3:
        result = (True, reply[2:-1])
    else:
        if timeout is not None:
            ser.timeout = timeout0
        raise ReplyError('Fehler bei Antwort_lesen: Unerwartete Antwort! "{}"'.format(reply))
    if timeout is not None:
        ser.timeout = timeout0
    return result


def com_list() -> List[str]:
    """Gibt eine Liste der verfügbaren COM-Ports"""
    comlist = serial.tools.list_ports.comports()
    n_list = []
    for element in comlist:
        n_list.append(element.device)
    return n_list


def bus_check(bus: int, port: str = None, ser: Serial = None, timeout: float = None) -> (bool, str):
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
        com_reply = read_reply(ser, timeout)
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


def __check_raw_config_data(raw_config_data: List[dict]) -> (bool, str):

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


def __transform_raw_config_data(raw_config_data: List[dict]) -> List[dict]:
    for motor_line in raw_config_data:

        if motor_line['Ohne Initiatoren(0 oder 1)'] != '':
            motor_line['Ohne Initiatoren(0 oder 1)'] = bool(int(motor_line['Ohne Initiatoren(0 oder 1)']))
        else:
            motor_line['Ohne Initiatoren(0 oder 1)'] = PMotor.DEFAULT_MOTOR_INFO['without_initiators']

        if motor_line['Einheiten'] != '':
            motor_line['Einheiten'] = motor_line['Einheiten']
        else:
            motor_line['Einheiten'] = PMotor.DEFAULT_MOTOR_INFO['display_units']

        if motor_line['Einheiten pro Schritt'] != '':
            motor_line['Einheiten pro Schritt'] = float(motor_line['Einheiten pro Schritt'])
        else:
            motor_line['Einheiten pro Schritt'] = PMotor.DEFAULT_MOTOR_INFO['display_u_per_step']

        for parameter_name in PBox.PARAMETER_NUMBER.keys():
            if motor_line[parameter_name] != '':
                motor_line[parameter_name] = float(motor_line[parameter_name])
            else:
                motor_line[parameter_name] = PBox.PARAMETER_DEFAULT[parameter_name]
    return raw_config_data


def read_config_from_file0(address: str = 'input/Phytron_Motoren_config.csv') \
        -> (List[int], List[M_Coord], Dict[M_Coord, dict], Dict[M_Coord, Param_Val]):
    """Liest die Configuration aus Datei"""

    # def check_parameters_values(parameters_values):
    #     """Prüfen, ob die Parameter erlaubte Werte haben."""
    #     pass

    f = open(address, "rt")

    separator = ';'

    header = f.readline().rstrip('\n')
    header = header.split(separator)
    header_length = len(header)

    # Kompatibilität der Datei prüfen
    if header[:6] != ['Motor Name', 'Bus', 'Achse', 'Ohne Initiatoren(0 oder 1)', 'Einheiten',
                      'Einheiten pro Schritt']:
        raise ReadConfigError(f'Datei {address} ist inkompatibel und kann nicht gelesen werden.')
    for par_name in header[6:]:
        if par_name not in PBox.PARAMETER_NUMBER.keys():
            raise ReadConfigError(f'Ein unbekannter Parameter: {par_name}')

    controllers_to_init = []
    motors_to_init = []
    motors_info = {}
    motors_parameters = {}

    for motorline in f:
        motorline = motorline.rstrip('\n')
        motorline = motorline.split(separator)
        if len(motorline) != header_length:
            raise ReadConfigError(f'Datei {address} ist defekt oder inkompatibel und kann nicht gelesen werden. '
                                  f'Spaltenanzahl ist nicht konstant.')

        # Motor info
        name = motorline[0]
        try:
            bus = int(motorline[1])
        except ValueError:
            raise ReadConfigError(f'Fehler bei Bus von Motor {name} lesen. ' +
                                  f'Bus muss ein int Wert zwischen 0 und 5 haben und kein {motorline[1]}')
        try:
            axis = int(motorline[2])
        except ValueError:
            raise ReadConfigError(f'Fehler bei Achse von Motor {name} lesen. ' +
                                  f'Achse muss ein int Wert 1 oder 2 haben und kein {motorline[2]}')

        if not (bus, axis) in motors_to_init:
            motors_to_init.append((bus, axis))
        else:
            raise ReadConfigError(f'Motor {(bus, axis)} ist mehrmals in der Datei beschrieben! .')

        if bus not in controllers_to_init:
            controllers_to_init.append(bus)

        if motorline[3] == '1':
            without_initiators = True
        elif motorline[3] == '0' or motorline[3] == '':
            without_initiators = False
        else:
            raise ReadConfigError(
                f'Motor {name}: "Mit Initiatoren" muss ein Wert 0 oder 1 haben und kein {motorline[3]}')

        if motorline[4] != '':
            ind_units = motorline[4]
            if motorline[5] != '':
                try:
                    iu_to_steps = float(motorline[5])
                except ValueError:
                    raise ReadConfigError(
                        f'Motor {name}: Einheiten pro Schritt muss ein float Wert haben und kein {motorline[5]}')
            else:
                iu_to_steps = 1
        else:
            ind_units = "Schritte"
            iu_to_steps = 1

        motors_info[(bus, axis)] = {'name': name, 'without_initiators': without_initiators,
                                    'display_units': ind_units, 'display_u_per_step': iu_to_steps}

        # Parameter lesen
        parameters_values = {}
        for i, par_val_str in enumerate(motorline[6:], 6):
            if par_val_str != '':
                try:
                    parameters_values[header[i]] = int(par_val_str)
                except ValueError:
                    raise ReadConfigError(
                        f'Motor {name}: {header[i]} muss {PBox.PARAMETER_DESCRIPTION[header[i]]} sein '
                        f'und kein {par_val_str}.')
            else:
                parameters_values[header[i]] = PBox.PARAMETER_DEFAULT[header[i]]

        # check_parameters_values(parameters_values)

        motors_parameters[(bus, axis)] = parameters_values

    logging.info(f'Configuration aus Datei {address} wurde erfolgreich gelesen.')
    return controllers_to_init, motors_to_init, motors_info, motors_parameters


def read_config_from_file(address: str = 'input/Phytron_Motoren_config.csv') \
        -> (List[int], List[M_Coord], Dict[M_Coord, dict], Dict[M_Coord, Param_Val]):

    raw_config_data = read_csv(address)

    correct, message = __check_raw_config_data(raw_config_data)
    if not correct:
        raise ReadConfigError("Datei hat inkorrekte Data. " + message)

    config_data = __transform_raw_config_data(raw_config_data)

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
    DEFAULT_MOTOR_INFO = {'name': "", 'without_initiators': False, 'display_units': 'Schritte', 'display_u_per_step': 1}

    def __init__(self, controller, axis: int, without_initiators: bool = False):
        self.controller: PController = controller
        self.box = self.controller.box
        self.axis = axis

        self.displ_null = 0  # Anzeiger Null in Normierte Einheiten
        self.conversion_factor = self.read_conversion_factors()

        self.set_info()

        self.soft_limits: Tuple[Union[None, float], Union[None, float]] = (None, None)

        self.without_initiators = without_initiators
        self.config()

    def config(self, parameters_values: Dict[str, float] = None):
        """Die Parametern einstellen laut angegebene Dict mit Parameterwerten"""
        # Parameter_Werte = {'Lauffrequenz': 4000, 'Stoppstrom': 5, 'Laufstrom': 11, 'Booststrom': 18}

        if parameters_values is None:
            parameters_values = self.box.PARAMETER_DEFAULT

        for name, value in parameters_values.items():
            self.set_parameter(self.box.PARAMETER_NUMBER[name], value)

    # noinspection PyAttributeOutsideInit
    def set_info(self, motor_info: dict = None):
        """Einstellt Name, Initiatoren Status, display_units, display_u_per_step anhand angegebene Dict"""
        if motor_info is None:
            name = 'Motor' + str(self.controller.bus) + "." + str(self.axis)
            motor_info = self.DEFAULT_MOTOR_INFO
            motor_info['name'] = name

        self.name = motor_info['name']
        self.without_initiators = motor_info['without_initiators']
        self.display_units = motor_info['display_units']
        self.display_u_per_step = motor_info['display_u_per_step']

    def get_parameters(self) -> Dict[str, float]:
        """Liest die Parametern aus Controller und gibt zurück Dict mit Parameterwerten"""
        parameters_values = {}
        for par_name, par_number in self.box.PARAMETER_NUMBER.items():
            parameter_value = self.read_parameter(par_number)
            parameters_values[par_name] = parameter_value
        return parameters_values

    def displ_from_norm(self, norm: float) -> float:
        """Transformiert einen Wert in normierte Einheiten zum Wert in Anzeige Einheiten"""
        norm_relative = norm - self.displ_null
        steps = norm_relative / self.conversion_factor
        return self.display_u_per_step * steps

    def norm_from_displ(self, displ: float):
        """Transformiert einen Wert in Anzeige Einheiten zum Wert in normierte Einheiten"""
        steps = displ / self.display_u_per_step
        norm_relative = steps * self.conversion_factor
        return norm_relative + self.displ_null

    def norm_from_displ_rel(self, displ: float) -> float:
        """Transformiert einen Wert in Anzeige Einheiten zum Wert in normierte Einheiten ohne Null zu wechseln"""
        steps = displ / self.display_u_per_step
        norm_relative = steps * self.conversion_factor
        return norm_relative

    def set_display_null(self, displ_null: float = None):
        """Anzeiger Null in Normierte Einheiten einstellen"""
        if displ_null is None:
            self.displ_null = self.position()
        else:
            self.displ_null = displ_null

    def soft_limits_einstellen(self, soft_limits, displ_u: bool = False):
        """soft limits einstellen"""
        if displ_u:
            self.soft_limits = tuple(map(self.norm_from_displ_rel, soft_limits))
        else:
            self.soft_limits = soft_limits

    def go_to(self, destination, displ=False):
        """Bewegt den motor zur absoluten position, die als destination gegeben wird."""
        destination = float(destination)
        if displ:
            destination = self.norm_from_displ(destination)

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

        reply = self.command("A" + str(destination))
        if reply[0] is True:
            logging.info(f'Motor {self.axis} beim Controller {self.controller.bus} wurde zu {destination} geschickt. '
                         f'Controller antwort ist "{reply}"')
        else:
            logging.error(
                f'Motor {self.axis} beim Controller {self.controller.bus} wurde zu {destination} nicht geschickt. '
                f'Controller antwort ist "{reply}"')
        return reply[0]

    def go(self, shift: float, displ_u: bool = False, calibrate: bool = False):
        """Bewegt den motor relativ um gegebener Verschiebung."""
        shift = float(shift)
        if displ_u:
            shift = self.norm_from_displ_rel(shift)
        if self.soft_limits != (None, None) and not calibrate:
            position = self.position()
            destination = position + shift
            return self.go_to(destination)

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

    def position(self, displ_u: bool = False) -> float:
        """Gibt die aktuelle position zurück"""
        position = self.read_parameter(20)
        if displ_u:
            return self.displ_from_norm(position)
        else:
            return position

    def at_the_end(self):
        """Gibt zurück einen bool Wert, ob der End-Initiator aktiviert ist."""
        return self.initiators()[1]

    def at_the_beginning(self):
        """Gibt zurück einen bool Wert, ob der Anfang-Initiator aktiviert ist."""
        return self.initiators()[0]

    def set_position(self, position: float):
        """Ändern die Zähler der aktuelle position zu angegebenen Wert"""
        position = float(position)
        self.set_parameter(20, position)
        logging.info('position wurde eingestellt. ({})'.format(position))

    def set_null(self):
        """Einstellt die aktuelle position als null"""
        self.set_parameter(20, 0)

    def read_conversion_factors(self) -> float:
        self.conversion_factor = self.read_parameter(3)
        return self.conversion_factor

    def set_conversion_factor(self, conversion_factor: float):
        self.set_parameter(3, conversion_factor)
        self.conversion_factor = conversion_factor

    async def calibrate(self, stop_indicator: StopIndicator = None):
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
            self.conversion_factor = 1000 / (end - beginning)

            logging.info(f'Kalibrierung von Motor {self.name} wurde abgeschlossen.')
        else:
            logging.error(f'Motor {self.name} hat keine Initiators und kann nicht kalibriert werden!')


class PController:
    """Diese Klasse entspricht einem MCC-2 Controller"""

    def __init__(self, box, bus: int):

        self.box: PBox = box
        self.ser = self.box.ser
        self.bus = bus
        self.motor: Dict[int, PMotor] = {}

        if self.check_controller()[0] is False:
            raise ConnectError("Controller #{} antwortet nicht oder ist nicht verbunden!".format(self.bus))

    def __iter__(self):
        return (motor for motor in self.motor.values())

    def check_controller(self):
        """Prüfen, ob der Controller da ist und funktioniert"""
        return bus_check(self.bus, ser=self.ser)

    def command(self, text: str, with_reply: bool = True, timeout: float = None) -> (bool, bytes):
        """Befehl für den Controller ausführen"""
        return self.box.command(text, self.bus, with_reply, timeout)

    def save_parameters_in_eprom(self):
        """Speichert die aktuelle Parametern in Flash EPROM des Controllers"""
        self.box.ser.timeout = 5
        reply = self.command("SA")
        self.box.ser.timeout = self.box.timeout
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

    def __init__(self, port: str, timeout: float = 0.2):
        self.ser = Serial(port, 115200, timeout=timeout)

        self.port = port
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
                check = bus_check(i, ser=self.ser)
                print(check)
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
        self.ser.flushInput()
        self.ser.write(command_format(text, bus))
        if with_reply:
            reply = read_reply(self.ser, timeout)
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
            motor.set_info(motor_info)

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
                self.get_motor(motor_coord).config(param_values)
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
        for controller in self:
            for motor in controller:
                motor.calibrate(stop_indicator)

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

        # Skala normieren
        thousand = np.array([1000] * len(beginning))
        end = np.array(end)
        beginning = np.array(beginning)

        conversion_factor = thousand / (end - beginning)

        i = 0
        for motor in motors_to_calibration:
            motor.set_parameter(3, conversion_factor[i])
            i += 1

        if all_motors:
            logging.info('Kalibrierung von allen Motoren wurde abgeschlossen.')
        else:
            logging.info(f'Kalibrierung von Motoren {list_to_calibration} wurde abgeschlossen.')

    def save_positions(self, address: str = "data/PMotoren_Positionen.txt"):
        """Sichert die aktuelle Positionen der Motoren in einer Datei"""

        f = open(address, "wt")

        # Motor liste schreiben
        motors_list = self.motors_list()
        motors_list_str = []
        for coordinates in motors_list:
            coordinates = list(map(str, coordinates))
            coordinates = ','.join(coordinates)
            motors_list_str.append(coordinates)
        f.write(';'.join(motors_list_str) + '\n')

        # Positionen schreiben
        positions = []
        for controller in self:
            for motor in controller:
                positions.append(motor.position())
        row = list(map(str, positions))
        f.write(';'.join(row) + '\n')

        # Anzeiger Null schreiben
        display_null = []
        for controller in self:
            for motor in controller:
                display_null.append(motor.displ_null)
        row = list(map(str, display_null))
        f.write(';'.join(row) + '\n')

        f.close()
        logging.info(f'Kalibrierungsdaten für  Motoren {self.motors_list()} wurde gespeichert.')

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

    def read_saved_positions(self, address: str = "data/PMotoren_Positionen.txt"):
        """Liest die gesicherte Positionen der Motoren aus einer Datei"""

        f = open(address, "r")

        # Motor Liste aus Datei lesen

        motor_line = f.readline()
        motors_list_f: list = motor_line.split(';')

        for i, coordinates in enumerate(motors_list_f):
            coordinates = coordinates.split(',')
            coordinates = tuple(map(int, coordinates))
            motors_list_f[i] = coordinates

        # Positionen aus Datei lesen
        positions_line = f.readline()
        positions = positions_line.split(';')
        positions = list(map(float, positions))

        # Anzeiger Nulls aus Datei lesen
        display_nulls_line = f.readline()
        display_nulls = display_nulls_line.split(';')
        display_nulls = list(map(float, display_nulls))

        f.close()

        motors_list = self.motors_list()
        list_to_calibration = deepcopy(motors_list)

        for i, motor_coord in enumerate(motors_list_f):
            if motor_coord in motors_list:
                motor = self.get_motor(motor_coord)
                motor.set_position(positions[i])
                motor.set_display_null(display_nulls[i])

                list_to_calibration.remove(motor_coord)

        logging.info('Kalibrierungsdaten für  Motoren {} wurde geladen.'.format(motors_list_f))
        if list_to_calibration:
            logging.info('Motoren {} brauchen Kalibrierung.'.format(list_to_calibration))

        return list_to_calibration

    def motors_list(self) -> List[M_Coord]:
        """Gibt zurück eine Liste der allen Motoren in Format: [(bus, Achse), …]"""
        m_list = []
        for controller in self:
            for motor in controller:
                m_list.append((controller.bus, motor.axis))
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
                    motors_list.append((controller.bus, motor.axis))
        return motors_list

    def motors_with_initiators(self) -> List[M_Coord]:
        """Gibt zurück eine Liste der allen Motoren ohne Initiatoren in Format: [(bus, Achse), …]"""
        motors_list = []
        for controller in self:
            for motor in controller:
                if not motor.without_initiators:
                    motors_list.append((controller.bus, motor.axis))
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
        return read_reply(self.ser)

    def close(self, without_eprom: bool = False, data_folder: str = 'data/'):
        """Alle nötige am Ende der Arbeit Operationen ausführen."""
        self.stop()
        self.save_positions(address=data_folder + 'PMotoren_Positionen.txt')
        self.save_soft_limits(address=data_folder + 'PSoft_Limits.txt')
        print('Positionen und Soft Limits gesichert')
        if not without_eprom:
            self.save_parameters_in_eprom()
        del self


class SerialError(Exception):
    """Base class for serial port related exceptions."""


class ConnectError(SerialError):
    """Grundklasse für die Fehler bei der Verbindung mit einem Controller"""


class ReplyError(SerialError):
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


if __name__ == '__main__':
    # config0 = read_config_from_file0('/Users/prouser/Dropbox/Proging/Python_Projects/MikroskopController/MCC2_Demo_GUI/input/Phytron_Motoren_config.csv')
    # config = read_config_from_file('/Users/prouser/Dropbox/Proging/Python_Projects/MikroskopController/MCC2_Demo_GUI/input/Phytron_Motoren_config.csv')
    # print(config == config0)

    comlist = serial.tools.list_ports.comports()
    comlist = [com.device for com in comlist]
    print(comlist)

    box1 = PBox(comlist[2])

    box1.initialize_with_config_file('/Users/prouser/Dropbox/Proging/Python_Projects/MikroskopController/MCC2_Demo_GUI/input/Phytron_Motoren_config.csv')
    print(box1.save_parameters_in_eprom_fast())