# coding= utf-8
import numpy as np
import serial.tools.list_ports
from serial import Serial
import time
from copy import deepcopy
from typing import Dict, List, Tuple

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


def com_list() -> List[str]:
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
        self.controller = {}

        self.get_bus_list()
        logging.info(f'Box Objekt erstellt, {len(self.bus_list)} Controller gefunden.')

    def __iter__(self):
        return (c_proxy(controller) for controller in self.controller.values())

    # noinspection PyUnboundLocalVariable,PyUnboundLocalVariable
    def get_bus_list(self):
        """Erstellt eine Liste der verfügbaren Controller in Box."""
        self.bus_list = []
        for i in range(5):
            for j in range(3):
                check = bus_check(i, ser=self.ser)
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

    def command(self, text: str, bus: int) -> (bool, str):
        """Befehl für die Box ausführen"""
        self.ser.flushInput()
        self.ser.write(command_format(text, bus))
        reply = read_reply(self.ser)
        if reply[0] is None:
            raise ConnectError('Controller Antwortet nicht!')
        return reply

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

        controllers_to_init, motors_to_init, motors_info, motors_parameters = self.read_config_from_file(config_file)

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
        self.config(motors_parameters)

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
        """Einstellt Name, Initiatoren Status, Anz_Einheiten, AE_in_Schritt der Motoren anhand angegebene Dict"""
        for motor_coord, motor_info in motors_info.items():
            motor = self.get_motor(motor_coord)
            motor.set_info(motor_info)

    def all_motors_stand(self, thread=None) -> bool:
        """Gibt bool Wert zurück, ob alle Motoren stehen."""
        if thread is not None:
            running_motors = []
            for controller in self:
                for motor in controller:
                    if not motor.stand():
                        running_motors.append(motor.name)
            if not running_motors:
                return True
            else:
                report = getattr(thread, "report", None)
                if report is not None:
                    report(f'Wartet auf Motoren: {", ".join(running_motors)}')
                return False
        else:
            for controller in self:
                if controller.Motoren_laufen():
                    return False
            return True

    # def allStop(self, stop_indicator: StopIndicator = None) -> bool:
    #
    #     if stop_indicator.has_stop_requested():
    #         return

    def wait_all_motors_stop(self, thread=None) -> None:
        """Haltet die programme, bis alle Motoren stoppen."""
        while not self.all_motors_stand(thread=thread):
            if thread is not None:
                if getattr(thread, "stop", False):
                    return
            time.sleep(0.5)

    def config(self, motors_config: Dict[M_Coord, Param_Val]):
        """Die Parametern einstellen laut angegebene Dict in Format {(bus, Axe) : Parameterwerte,}"""
        available_motors = self.Motoren_Liste()
        for motor_coord, param_values in motors_config.items():
            if motor_coord in available_motors:
                self.get_motor(motor_coord).config(param_values)
            else:
                logging.warning(f"Motor {motor_coord} ist nicht verbunden und kann nicht configuriert werden.")

    def get_config(self) -> Dict[M_Coord, Param_Val]:
        """Liest die Parametern aus Controller und gibt zurück Dict mit Parameterwerten"""
        motors_config = {}

        for controller in self:
            for Motor in controller:
                motors_config[(controller.bus, Motor.axis)] = Motor.get_config()

        return motors_config

    def make_empty_config_file(self, address: str = 'input/Phytron_Motoren_config.csv'):
        """Erstellt eine Datei mit einer leeren Configurationtabelle"""
        f = open(address, "wt")

        separator = ';'

        # Motor liste schreiben
        header = ['Motor Name', 'Bus', 'Axe', 'Mit Initiatoren(0 oder 1)', 'Einheiten', 'Einheiten pro Schritt']
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

        logging.info('Eine Datei mit einer leeren Configurationtabelle wurde erstellt.')

    def read_config_from_file(self, address: str = 'input/Phytron_Motoren_config.csv') \
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

        # Kompatibelität der Datei prüfen
        if header[:6] != ['Motor Name', 'Bus', 'Axe', 'Mit Initiatoren(0 oder 1)', 'Einheiten',
                          'Einheiten pro Schritt']:
            raise ReadConfigError(f'Datei {address} ist inkompatibel und kann nicht gelesen werden.')
        for par_name in header[6:]:
            if par_name not in self.PARAMETER_NUMBER.keys():
                raise ReadConfigError(f'Ein unbekanter Parameter: {par_name}')

        controllers_to_init = []
        motors_to_init = []
        motors_info = {}
        motors_parameters = {}

        for motorline in f:
            motorline = motorline.rstrip('\n')
            motorline = motorline.split(separator)
            if len(motorline) != header_length:
                raise ReadConfigError(f'Datei {address} ist defekt oder inkompatibel und kann nicht gelesen werden. '
                                      f'Spaltenahzahl ist nicht konstant.')

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
                raise ReadConfigError(f'Fehler bei Axe von Motor {name} lesen. ' +
                                      f'Axe muss ein int Wert 1 oder 2 haben und kein {motorline[2]}')

            if not (bus, axis) in motors_to_init:
                motors_to_init.append((bus, axis))
            else:
                raise ReadConfigError(f'Motor {(bus, axis)} ist mehrmals in der Datei beschrieben! .')

            if bus not in controllers_to_init:
                controllers_to_init.append(bus)

            if motorline[3] == '0':
                without_initiators = True
            elif motorline[3] == '1' or motorline[3] == '':
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

            motors_info[(bus, axis)] = {'Name': name, 'ohne_Initiatoren': without_initiators,
                                        'Anz_Einheiten': ind_units, 'AE_in_Schritt': iu_to_steps}

            # Parameter lesen
            parameters_values = {}
            for i, par_val_str in enumerate(motorline[6:], 6):
                if par_val_str != '':
                    try:
                        parameters_values[header[i]] = int(par_val_str)
                    except ValueError:
                        raise ReadConfigError(
                            f'Motor {name}: {header[i]} muss {self.PARAMETER_DESCRIPTION[header[i]]} sein '
                            f'und kein {par_val_str}.')
                else:
                    parameters_values[header[i]] = self.PARAMETER_DEFAULT[header[i]]

            # check_parameters_values(parameters_values)

            motors_parameters[(bus, axis)] = parameters_values

        logging.info(f'Configuration aus Datei {address} wurde erfolgreich gelesen.')
        return controllers_to_init, motors_to_init, motors_info, motors_parameters

    def initiators(self, motors_list: Tuple[int, int] = None) -> List[Tuple[bool, bool]]:
        """Gibt zurück eine Liste mit Status von den Initiatoren von allen Motoren"""
        if motors_list is None:
            motors_list = self.Motoren_Liste()

        status_list = []
        for motor_coord in motors_list:
            motor = self.get_motor(motor_coord)
            status_list.append(motor.initiators())
        return status_list

    def Motoren_kalibrieren(self, Liste_zu_Kalibrierung=None, Motoren_zu_Kalibrierung=None, Thread=None):
        """Kalibrierung von den gegebenen Motoren"""
        logging.info('Kalibrierung von allen Motoren wurde angefangen.')

        if Liste_zu_Kalibrierung is None and Motoren_zu_Kalibrierung is None:
            Liste_zu_Kalibrierung = self.Motoren_mit_Init_Liste()
            alle = True
        else:
            alle = False

        if Motoren_zu_Kalibrierung is None:
            Motoren_zu_Kalibrierung = \
                [self.controller[bus].motor[Axe] for bus, Axe in Liste_zu_Kalibrierung if
                 not self.controller[bus].motor[Axe].ohne_Initiatoren]

        # Voreinstellung der Parametern
        for Motor in Motoren_zu_Kalibrierung:
            Motor.Parameter_schreiben(1, 1)
            Motor.Parameter_schreiben(2, 1)
            Motor.Parameter_schreiben(3, 1)

        # Bis zum Ende laufen
        while True:
            alle_sind_am_Ende = True
            for Motor in Motoren_zu_Kalibrierung:
                am_Ende = Motor.initiators()[1]
                if not am_Ende:
                    alle_sind_am_Ende = False
                    Motor.geh(500000, Kalibrierung=True)
            print(self.initiators(Liste_zu_Kalibrierung))
            self.wait_all_motors_stop(Thread)
            if Thread is not None:
                if getattr(Thread, "stop", False):
                    return

            if alle_sind_am_Ende:
                break

        Ende = []
        for Motor in Motoren_zu_Kalibrierung:
            Ende.append(Motor.Position())

        # Bis zum Anfang laufen
        while True:
            alle_sind_am_Anfang = True
            for Motor in Motoren_zu_Kalibrierung:
                am_Anfang = Motor.initiators()[0]
                if not am_Anfang:
                    alle_sind_am_Anfang = False
                    Motor.geh(-500000, Kalibrierung=True)
            print(self.initiators(Liste_zu_Kalibrierung))
            self.wait_all_motors_stop(Thread)
            if Thread is not None:
                if getattr(Thread, "stop", False):
                    return

            if alle_sind_am_Anfang:
                break

        Anfang = []
        for Motor in Motoren_zu_Kalibrierung:
            Anfang.append(Motor.Position())

        # Null einstellen
        for Motor in Motoren_zu_Kalibrierung:
            Motor.Null_einstellen()

        # Skala normieren
        Tausend = np.array([1000] * len(Anfang))
        Ende = np.array(Ende)
        Anfang = np.array(Anfang)

        Umrechnungsfaktor = Tausend / (Ende - Anfang)

        i = 0
        for Motor in Motoren_zu_Kalibrierung:
            Motor.Parameter_schreiben(3, Umrechnungsfaktor[i])
            i += 1

        if alle:
            logging.info('Kalibrierung von allen Motoren wurde abgeschlossen.')
        else:
            logging.info('Kalibrierung von Motoren {} wurde abgeschlossen.'.format(Liste_zu_Kalibrierung))

    def Positionen_sichern(self, address="data/PMotoren_Positionen.txt"):
        """Sichert die aktuelle Positionen der Motoren in einer Datei"""

        f = open(address, "wt")

        # Motor liste schreiben

        Motoren_Liste = self.Motoren_Liste()
        Motoren_Liste_str = []
        for Koordinaten in Motoren_Liste:
            Koordinaten = list(map(str, Koordinaten))
            Koordinaten = ','.join(Koordinaten)
            Motoren_Liste_str.append(Koordinaten)
        f.write(';'.join(Motoren_Liste_str) + '\n')

        # Umrechnungsfaktoren schreiben

        Umrechnungsfaktoren = []
        for Controller in self:
            for Motor in Controller:
                Umrechnungsfaktoren.append(Motor.Umrechnungsfaktor_lesen())
        row = list(map(str, Umrechnungsfaktoren))
        f.write(';'.join(row) + '\n')

        # Positionen schreiben

        Positionen = []
        for Controller in self:
            for Motor in Controller:
                Positionen.append(Motor.Position())
        row = list(map(str, Positionen))
        f.write(';'.join(row) + '\n')

        # Anzeiger Null schreiben
        A_Null = []
        for Controller in self:
            for Motor in Controller:
                A_Null.append(Motor.A_Null)
        row = list(map(str, A_Null))
        f.write(';'.join(row) + '\n')

        f.close()
        logging.info('Kalibrierungsdaten für  Motoren {} wurde gespeichert.'.format(self.Motoren_Liste()))

    def Soft_Limits_sichern(self, address="data/PSoft_Limits.txt", ohne_lesen=False):
        """Sichert die Soft Limits der Motoren in einer Datei"""
        # Sichern der Soft_Limits von unbenutzten in laufenden Program Motoren
        if not ohne_lesen:
            Motoren_Liste = self.Motoren_Liste()
            Soft_Limits_Liste_f = read_soft_limits(address)
            Motoren_in_Datei = list(Soft_Limits_Liste_f.keys())
            for Motoren_Coord in Motoren_in_Datei:
                if Motoren_Coord in Motoren_Liste:
                    del Soft_Limits_Liste_f[Motoren_Coord]

        f = open(address, "wt")

        # Motor liste schreiben
        for controller in self:
            for motor in controller:
                if motor.soft_limits != (None, None):
                    U_Grenze = motor.soft_limits[0] if motor.soft_limits[0] is not None else ''
                    O_Grenze = motor.soft_limits[1] if motor.soft_limits[1] is not None else ''
                    row = f"{controller.bus},{motor.axis},{U_Grenze},{O_Grenze}\n"
                    f.write(row)

        if not ohne_lesen:
            for Motor_Coord, Soft_Limits in Soft_Limits_Liste_f.items():
                U_Grenze = Soft_Limits[0] if Soft_Limits[0] is not None else ''
                O_Grenze = Soft_Limits[1] if Soft_Limits[1] is not None else ''
                row = f"{Motor_Coord[0]},{Motor_Coord[1]},{U_Grenze},{O_Grenze}\n"
                f.write(row)

    def Soft_Limits_lesen(self, address="data/PSoft_Limits.txt"):
        """Sichert die Soft Limits der Motoren in einer Datei"""
        Soft_Limits_Liste = read_soft_limits(address)

        for Motor_Coord, Soft_Limits in Soft_Limits_Liste.items():
            Motor = self.get_motor(Motor_Coord)
            Motor.soft_limits = Soft_Limits

    def Positionen_lesen(self, address="data/PMotoren_Positionen.txt"):
        """Sichert die aktuelle Positionen der Motoren in einer Datei"""

        f = open(address, "r")

        # Motor Liste aus Datei lesen

        Motor_line = f.readline()
        Motoren_Liste_f = Motor_line.split(';')

        for i, Koordinaten in enumerate(Motoren_Liste_f):
            Koordinaten = Koordinaten.split(',')
            Koordinaten = tuple(map(int, Koordinaten))
            Motoren_Liste_f[i] = Koordinaten

        # Umrechnungsfaktoren aus Datei lesen
        Umrechnungsfaktoren_line = f.readline()
        Umrechnungsfaktoren = Umrechnungsfaktoren_line.split(';')
        Umrechnungsfaktoren = list(map(float, Umrechnungsfaktoren))

        # Positionen aus Datei lesen
        Positionen_line = f.readline()
        Positionen = Positionen_line.split(';')
        Positionen = list(map(float, Positionen))

        # Anzeiger Nulls aus Datei lesen
        A_Nulls_line = f.readline()
        A_Nulls = A_Nulls_line.split(';')
        A_Nulls = list(map(float, A_Nulls))

        f.close()

        Motoren_Liste = self.Motoren_Liste()
        Liste_zu_Kalibrierung = deepcopy(Motoren_Liste)

        for i, Motor_Koord in enumerate(Motoren_Liste_f):
            if Motor_Koord in Motoren_Liste:
                Motor = self.get_motor(Motor_Koord)
                # Motor.Umrechnungsfaktor_einstellen(Umrechnungsfaktoren[i])
                Motor.Position_einstellen(Positionen[i])
                Motor.A_Null_einstellen(A_Nulls[i])

                Liste_zu_Kalibrierung.remove(Motor_Koord)

        logging.info('Kalibrierungsdaten für  Motoren {} wurde geladen.'.format(Motoren_Liste_f))
        if Liste_zu_Kalibrierung:
            logging.info('Motoren {} brauchen Kalibrierung.'.format(Liste_zu_Kalibrierung))

        return Liste_zu_Kalibrierung

    def Motoren_Liste(self):
        """Gibt zurück eine Liste der allen Motoren in Format: [(bus, Axe), …]"""
        Liste = []
        for controller in self:
            for motor in controller:
                Liste.append((controller.bus, motor.axis))
        return Liste

    def Motoren_Namen_Liste(self):
        """Gibt zurück eine Liste der Namen der Motoren"""
        Namen = []
        for Controller in self:
            for Motor in Controller:
                Namen.append(Motor.name)
        return Namen

    def Controller_Liste(self):
        """Gibt zurück eine Liste der allen Motoren in Format: [(bus, Axe), …]"""
        Liste = []
        for Controller in self:
            Liste.append(Controller.bus)
        return Liste

    def Motoren_ohne_Init_Liste(self):
        """Gibt zurück eine Liste der allen Motoren ohne Initiatoren in Format: [(bus, Axe), …]"""
        Liste = []
        for controller in self:
            for motor in controller:
                if motor.ohne_Initiatoren:
                    Liste.append((controller.bus, motor.axis))
        return Liste

    def Motoren_mit_Init_Liste(self):
        """Gibt zurück eine Liste der allen Motoren ohne Initiatoren in Format: [(bus, Axe), …]"""
        Liste = []
        for controller in self:
            for motor in controller:
                if not motor.ohne_Initiatoren:
                    Liste.append((controller.bus, motor.axis))
        return Liste

    def get_motor(self, coordinates: (int, int) = None, name: str = None):
        """Gibt den Motor objekt zurück aus Koordinaten in Format (bus, Axe)"""
        return get_motor(self, coordinates, name)

    def Stop(self):
        """Stoppt alle Axen"""
        Antwort = True
        for bus in self.controller:
            Antwort = Antwort and self.controller[bus].Stop()
        return Antwort

    def Parametern_in_EPROM_speichern(self):
        """Speichert die aktuelle Parametern in Flash EPROM bei alle Controllern"""
        for Controller in self:
            Controller.Parametern_in_EPROM_speichern()

    def close(self, ohne_EPROM: bool = False, data_folder: str = 'data/'):
        """Alle nötige am Ende der Arbeit Operationen ausführen."""
        self.Stop()
        self.Positionen_sichern(address=data_folder + 'PMotoren_Positionen.txt')
        self.Soft_Limits_sichern(address=data_folder + 'PSoft_Limits.txt')
        print('Positionen und Soft Limits gesichert')
        if not ohne_EPROM:
            self.Parametern_in_EPROM_speichern()
        del self


class PController:
    """Diese Klasse entspricht einem MCC-2 Controller"""

    def __init__(self, box: PBox, bus: int):

        self.ser = box.ser
        self.bus = bus
        self.box = box
        self.motor = {}

        if self.check_Controller()[0] is False:
            raise ConnectError("Controller #{} antwortet nicht oder ist nicht verbunden!".format(self.bus))

    def __iter__(self):
        return (m_proxy(Motor) for Motor in self.motor.values())

    def check_Controller(self):
        """Prüfen, ob der Controller da ist und funktioniert"""
        return bus_check(self.bus, ser=self.ser)

    def Befehl(self, text):
        """Befehl für den Contreller ausführen"""
        return self.box.command(text, self.bus)

    def Parametern_in_EPROM_speichern(self):
        """Speichert die aktuelle Parametern in Flash EPROM des Controllers"""
        self.box.ser.timeout = 5
        Antwort = self.Befehl("SA")
        self.box.ser.timeout = self.box.timeout
        if Antwort[0] is False:
            raise ConnectError("Hat nicht geklappt Parametern in Controllerspeicher zu sichern.")

    def Initiatoren_Status(self):
        """Gibt zurück der Status der Initiatoren für beide Axen als List von bool Werten
        in folgende Reihenfolge: X-, X+, Y-, Y+ """
        Antwort = self.Befehl("SUI")
        I_Status = [False] * 4

        if Antwort[0] is True:
            Antwort_str = Antwort[1].decode()
            # print(Antwort_str)

            # für X Axe
            if Antwort_str[2] == "-":
                I_Status[0] = True
            elif Antwort_str[2] == "+":
                I_Status[1] = True
            elif Antwort_str[2] == "2":
                I_Status[0] = True
                I_Status[1] = True
            elif Antwort_str[2] == "0":
                I_Status[0] = False
                I_Status[1] = False
            else:
                raise ReplyError('Fehler: Unerwartete Antwort vom Controller. "{}"" '.format(Antwort_str))

            # für Y Axe
            if Antwort_str[3] == "-":
                I_Status[2] = True
            elif Antwort_str[3] == "+":
                I_Status[3] = True
            elif Antwort_str[3] == "2":
                I_Status[2] = True
                I_Status[3] = True
            elif Antwort_str[3] == "0":
                I_Status[2] = False
                I_Status[3] = False
            else:
                raise ReplyError('Fehler: Unerwartete Antwort vom Controller. "{}"" '.format(Antwort_str))

            return I_Status

        else:
            raise ConnectError("Controller #{} antwortet nicht oder ist nicht verbunden!".format(self.bus))

    def Motoren_laufen(self):
        """Gibt zurück der Status der Motoren, ob die Motoren in Lauf sind."""
        Antwort = self.Befehl("SH")
        if Antwort[1] == b'E':
            return False
        elif Antwort[1] == b'N':
            return True
        else:
            raise ReplyError('Unerwartete Antwort vom Controller!')

    def Stop_warten(self):
        """Haltet die programme, bis die Motoren stoppen."""
        while self.Motoren_laufen():
            time.sleep(0.5)

    def make_motors(self):
        """erstellt Objekten für alle vervügbare Motoren"""
        n_Axen = self.n_axes()
        self.motor = {}
        for i in range(n_Axen):
            self.motor[i + 1] = PMotor(self, i + 1)
        logging.info(f'Controller hat {n_Axen} Motor Objekten für alle verfügbare Axen erstellt.')

    def n_axes(self):
        """Gibt die Anzahl der verfügbaren Axen zurück"""
        Antwort = self.Befehl('IAR')

        if Antwort[0] is True:
            n_Axen = int(Antwort[1])
            return n_Axen
        else:
            raise ControllerError(
                f'Lesen der Axen anzahl des Controllers {self.bus} ist fehlgeschlagen. Antwort des Controllers:{Antwort}')

    def fehlende_Motoren(self):
        """Gibt die Liste der fehlenden Motoren zurück"""
        fehlende_Axen = []
        I_Status = self.Initiatoren_Status()
        if (I_Status[0] and I_Status[1]):
            fehlende_Axen.append(1)
        if (I_Status[2] and I_Status[3]):
            fehlende_Axen.append(2)
        return fehlende_Axen

    def Stop(self):
        """Stoppt alle Axen des Controllers"""
        Antwort = True
        for Motor in self:
            Antwort = Antwort and Motor.Stop()
        return Antwort


class PMotor:
    """Diese Klasse entspricht einem Motor, der mit einem MCC-2 Controller verbunden ist."""

    def __init__(self, controller: PController, axis: int, ohne_Initiatoren: bool = False):
        self.controller = controller
        self.box = controller.box
        self.axis = axis

        self.A_Null = 0  # Anzeiger Null in Normierte Einheiten
        self.Umrechnungsfaktor = self.Umrechnungsfaktor_lesen()

        self.set_info()

        self.soft_limits = (None, None)

        self.ohne_Initiatoren = ohne_Initiatoren
        self.config()

    def config(self, Parameter_Werte=None):
        """Die Parametern einstellen laut angegebene Dict mit Parameterwerten"""
        # Parameter_Werte = {'Lauffrequenz': 4000, 'Stoppstrom': 5, 'Laufstrom': 11, 'Booststrom': 18}

        if Parameter_Werte is None:
            Parameter_Werte = self.box.PARAMETER_DEFAULT

        for Name, Wert in Parameter_Werte.items():
            self.Parameter_schreiben(self.box.PARAMETER_NUMBER[Name], Wert)

    def set_info(self, Motor_info=None):
        """Einstellt Name, Initiatoren Status, Anz_Einheiten, AE_in_Schritt anhand angegebene Dict"""
        if Motor_info is None:
            Name = 'Motor' + str(self.controller.bus) + "." + str(self.axis)
            Motor_info = {'Name': Name, 'ohne_Initiatoren': False, 'Anz_Einheiten': 'Schritte', 'AE_in_Schritt': 1}

        self.name = Motor_info['Name']
        self.ohne_Initiatoren = Motor_info['ohne_Initiatoren']
        self.Anz_Einheiten = Motor_info['Anz_Einheiten']
        self.AE_in_Schritt = Motor_info['AE_in_Schritt']

    def get_config(self):
        """Liest die Parametern aus Controller und gibt zurück Dict mit Parameterwerten"""
        Parameter_Werte = {}
        for Par_Name, Par_Nummer in self.box.PARAMETER_NUMBER.items():
            Par_Wert = self.Parameter_lesen(Par_Nummer)
            Parameter_Werte[Par_Name] = Par_Wert
        return Parameter_Werte

    def AE_aus_NE(self, NE):
        """Transformiert einen Wert in normierte Einheiten zum Wert in Anzeige Einheiten"""
        NE_relativ = NE - self.A_Null
        Schritte = NE_relativ / self.Umrechnungsfaktor
        return self.AE_in_Schritt * Schritte

    def NE_aus_AE(self, AE):
        """Transformiert einen Wert in Anzeige Einheiten zum Wert in normierte Einheiten"""
        Schritte = AE / self.AE_in_Schritt
        NE_relativ = Schritte * self.Umrechnungsfaktor
        return NE_relativ + self.A_Null

    def NE_aus_AE_rel(self, AE):
        """Transformiert einen Wert in Anzeige Einheiten zum Wert in normierte Einheiten ohne Null zu wechselln"""
        Schritte = AE / self.AE_in_Schritt
        NE_relativ = Schritte * self.Umrechnungsfaktor
        return NE_relativ

    def A_Null_einstellen(self, A_Null=None):
        """Anzeiger Null in Normierte Einheiten einstellen"""
        if A_Null is None:
            self.A_Null = self.Position()
        else:
            self.A_Null = A_Null

    def soft_limits_einstellen(self, soft_limits, AE=False):
        """soft limits einstellen"""
        if AE:
            self.soft_limits = tuple(map(self.NE_aus_AE_rel, soft_limits))
        else:
            self.soft_limits = soft_limits

    def geh_zu(self, Ort, AE=False):
        """Bewegt den motor zur absoluten Position, die als Ort gegeben wird."""
        Ort = float(Ort)
        if AE:
            Ort = self.NE_aus_AE(Ort)

        U_Grenze, O_Grenze = self.soft_limits
        if U_Grenze is not None:
            if Ort < U_Grenze:
                Ort = U_Grenze
        if O_Grenze is not None:
            if Ort > O_Grenze:
                Ort = O_Grenze
        if U_Grenze is not None and O_Grenze is not None:
            if O_Grenze - U_Grenze < 0:
                logging.error(f'Soft Limits Fehler: Obere Grenze ist kleiner als Untere! '
                              f'(Motor {self.axis} beim Controller {self.controller.bus}:)')
                return False

        Antwort = self.Befehl("A" + str(Ort))
        if Antwort[0] is True:
            logging.info(
                'Motor {} beim Controller {} wurde zu {} geschickt. Controller antwort ist "{}"'.format(self.axis,
                                                                                                        self.controller.bus,
                                                                                                        Ort, Antwort))
        else:
            logging.error(
                'Motor {} beim Controller {} wurde zu {} nicht geschickt. Controller antwort ist "{}"'.format(self.axis,
                                                                                                              self.controller.bus,
                                                                                                              Ort,
                                                                                                              Antwort))
        return Antwort[0]

    def geh(self, Verschiebung, AE=False, Kalibrierung=False):
        """Bewegt den motor relativ um gegebener Verschiebung."""
        Verschiebung = float(Verschiebung)
        if AE:
            Verschiebung = self.NE_aus_AE_rel(Verschiebung)
        if self.soft_limits != (None, None) and not Kalibrierung:
            Position = self.Position()
            Ort = Position + Verschiebung
            return self.geh_zu(Ort)

        Antwort = self.Befehl(str(Verschiebung))
        if Antwort[0] is True:
            logging.info(
                'Motor {} beim Controller {} wurde um {} verschoben. Controller antwort ist "{}"'.format(self.axis,
                                                                                                         self.controller.bus,
                                                                                                         Verschiebung,
                                                                                                         Antwort))
        else:
            msg = f'Motor {self.axis} beim Controller {self.controller.bus} wurde um {Verschiebung} nicht verschoben. ' \
                  f'Controller antwort ist "{Antwort}"'
            logging.error(msg)

        return Antwort[0]

    def Stop(self):
        """Stoppt die Axe"""
        Antwort = self.Befehl("S")
        logging.info('Motor {} beim Controller {} wurde gestoppt. Controller antwort ist "{}"'.format(self.axis,
                                                                                                      self.controller.bus,
                                                                                                      Antwort))
        return Antwort[0]

    def stand(self):
        """Gibt zurück bool Wert ob Motor steht"""
        Antwort = self.Befehl('=H')
        if Antwort[1] == b'E':
            return True
        elif Antwort[1] == b'N':
            return False
        else:
            raise ReplyError('Unerwartete Antwort vom Controller!')

    def Befehl(self, text):
        """Befehl für den Motor ausführen"""
        return self.controller.Befehl(str(self.axis) + str(text))

    def initiators(self, check: bool = True) -> (bool, bool):
        """Gibt zurück der Status der Initiatoren als List von bool Werten in folgende Reihenfolge: -, +"""
        if self.axis == 1:
            status = self.controller.Initiatoren_Status()[:2]
        elif self.axis == 2:
            status = self.controller.Initiatoren_Status()[2:]
        else:
            raise ValueError('Axenummer ist falsch! "{}"'.format(self.axis))

        if check:
            if status[0] and status[1]:
                raise MotorError("Beider Initiatoren sind Aktiviert. Motor ist falsch configuruert oder kaputt!")

        return status[0], status[1]

    def Parameter_lesen(self, N):
        """Liest einen Parameter Nummer N für die Axe"""
        Antwort = self.Befehl("P" + str(N) + "R")
        if Antwort[0] is False:
            raise ConnectError(f"Hat nicht geklappt einen Parameter zu lesen. Controller Antwort ist: {Antwort}")
        return float(Antwort[1])

    def Parameter_schreiben(self, N, neuer_Wert):
        """Ändert einen Parameter Nummer N für die Axe"""
        Antwort = self.Befehl("P" + str(N) + "S" + str(neuer_Wert))
        if Antwort[0] is False:
            raise ConnectError("Hat nicht geklappt einen Parameter zu ändern.")

        return Antwort[0]

    def Position(self, AE=False):
        """Gibt die aktuelle Position zurück"""
        Position = self.Parameter_lesen(20)
        if AE:
            return self.AE_aus_NE(Position)
        else:
            return Position

    def Position21(self):
        """Gibt die aktuelle Position zurück"""
        return self.Parameter_lesen(21)

    def Position_einstellen(self, Position):
        """Ändern die Zähler der aktuelle position zu angegebenen Wert"""
        self.Parameter_schreiben(21, Position)
        self.Parameter_schreiben(20, Position)
        logging.info('Position wurde eingestellt. ({})'.format(Position))

    def Null_einstellen(self):
        """Einstellt die aktuele Position als null"""
        self.Parameter_schreiben(21, 0)
        self.Parameter_schreiben(20, 0)

    def Umrechnungsfaktor_lesen(self):
        self.Umrechnungsfaktor = self.Parameter_lesen(3)
        return self.Umrechnungsfaktor

    def Umrechnungsfaktor_einstellen(self, Umrechnungsfaktor):
        self.Parameter_schreiben(3, Umrechnungsfaktor)
        self.Umrechnungsfaktor = Umrechnungsfaktor

    def kalibrieren(self):
        """Kalibrierung des Motors"""
        logging.info(
            'Kalibrierung des Motors {} beim Controller {} wurde angefangen.'.format(self.axis, self.controller.bus))

        # Voreinstellung der Parametern
        self.Parameter_schreiben(1, 1)
        self.Parameter_schreiben(2, 1)
        self.Parameter_schreiben(3, 1)

        # Bis zum Ende laufen
        while not self.initiators()[1]:
            self.geh(100000)
            self.controller.Stop_warten()
        Ende = self.Position()

        # Bis zum Anfang laufen
        while not self.initiators()[0]:
            self.geh(-100000)
            self.controller.Stop_warten()
        Anfang = self.Position()

        # Null einstellen und die Skala normieren
        self.Null_einstellen()
        Umrechnungsfaktor = 1000 / (Ende - Anfang)
        self.Parameter_schreiben(3, Umrechnungsfaktor)

        logging.info(
            'Kalibrierung des Motors {} beim Controller {} wurde abgeschlossen.'.format(self.axis, self.controller.bus))


def get_motor(box: PBox, coordinates: (int, int) = None, name: str = None) -> PMotor:
    """Gibt den Motor objekt zurück aus Koordinaten in Format (bus, Axe)"""

    if coordinates is None and name is None:
        raise ValueError("Kein Argument! Die Koordinaten oder der Name des Motors muss gegeben sein. ")
    elif coordinates is not None:
        bus, axis = coordinates
        return box.controller[bus].motor[axis]
    else:
        for Controller in box:
            for Motor in Controller:
                if Motor.name == name:
                    return Motor
        raise ValueError(f"Es gibt kein Motor mit solchem Name: {name}")


def c_proxy(controller: PController) -> PController:
    return controller


def m_proxy(motor: PMotor) -> PMotor:
    return motor


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
    """Grundklasse für alle Fehler mit der Detei"""


class PlantError(FileReadError):
    """Grundklasse für die Fehler wenn das Aufbau in Datei falsch beschrieben wurde."""


class ReadConfigError(Exception):
    """Grundklasse für alle Fehler mit Lesen der Configuration aus Detei"""
