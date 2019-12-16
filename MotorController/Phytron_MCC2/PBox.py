# coding= utf-8
import time
from copy import deepcopy

import numpy as np

# from StopIndicator import StopIndicator
from .PController import PController
from .PMotor import PMotor
from .functions import *

if __name__ == '__main__':
    ULoggingConfig.init_config()


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
        self.Controller = {}

        self.get_bus_list()
        logging.info(f'Box Objekt erstellt, {len(self.bus_list)} Controller gefunden.')

    def __iter__(self):
        return (Controller for Controller in self.Controller.values())

    def port_open(self):
        self.ser = Serial(self.port, 115200, timeout=self.timeout)

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


    def make_Controllers(self):
        """erstellt Objekten für alle verfügbare Controller"""
        self.Controller = {}
        for i in self.bus_list:
            self.Controller[i] = PController(self, i)
        logging.info('Box hat {} Controller Objekten für Bus {} erstellt.'.format(len(self.bus_list), self.bus_list))

    def Befehl(self, text, bus):
        """Befehl für die Box ausführen"""
        self.ser.flushInput()
        self.ser.write(command_format(text, bus))
        Antwort = read_reply(self.ser)
        if Antwort[0] is None:
            raise ConnectError('Controller Antwortet nicht!')
        return Antwort

    def Initialisierung(self, config_Datei='input/Phytron_Motoren_config.csv'):
        """Sucht und macht Objekte für alle verfügbare Controller und Motoren. Gibt ein Bericht zurück."""
        logging.info('Box Initialisierung wurde gestartet.')

        self.get_bus_list()
        report = ""
        n_axes = 0

        self.make_Controllers()
        for Controller in self:
            Controller.make_Motoren()
            axes_in_controller = Controller.n_Axen()
            n_axes += axes_in_controller

            report += f"Controller {Controller.bus} ({axes_in_controller} Achsen)\n"

        report = f"Box wurde initialisiert. {len(self.bus_list)} Controller und {n_axes} Achsen gefunden:\n" + report
        logging.info(report)
        self.report = report
        return report

    def Initialisierung_mit_configDatei(self, config_Datei='input/Phytron_Motoren_config.csv'):
        """Sucht und macht Objekte für alle verfügbare Controller und Motoren. Gibt ein Bericht zurück."""
        logging.info('Box Initialisierung wurde gestartet.')

        self.get_bus_list()
        Bericht = ""
        n_Motoren = 0
        n_Contr = 0
        self.Controller = {}

        Controller_zu_Init, Motoren_zu_Init, Motoren_info, Motoren_Parameter = self.Config_aus_Datei_lesen(config_Datei)

        # Controller initialisieren
        fehlende_bus = []
        for bus in Controller_zu_Init:
            if bus in self.bus_list:
                self.Controller[bus] = PController(self, bus)
                n_Contr += 1
            else:
                if not bus in fehlende_bus:
                    fehlende_bus.append(bus)
        if len(fehlende_bus) > 1:
            Bericht += f"Controller {bus} sind nicht verbunden und wurden nicht initialisiert.\n"
        elif len(fehlende_bus) == 1:
            Bericht += f"Controller {bus} ist nicht verbunden und wurde nicht initialisiert.\n"

        # Motoren initialisieren
        for bus, Axe in Motoren_zu_Init:
            if Axe <= self.Controller[bus].n_Axen():
                self.Controller[bus].Motor[Axe] = PMotor(self.Controller[bus], Axe)
                n_Motoren += 1
            else:
                Bericht += f"Axe {Axe} ist beim Controller {bus} nicht vorhanden, den Motor wurde nicht initialisiert.\n"

        self.Motoren_info_einstellen(Motoren_info)
        self.config(Motoren_Parameter)

        Bericht = f"{n_Contr} Controller und {n_Motoren} Motoren wurde initialisiert:\n" + Bericht
        for Controller in self:
            Bericht += f'Controller {Controller.bus}: '
            mehr_als_einen = False
            for Motor in Controller:
                if mehr_als_einen:
                    Bericht += ', '
                Bericht += Motor.Name
                mehr_als_einen = True
            Bericht += '\n'

        self.report = Bericht
        return Bericht

    def Motoren_info_einstellen(self, Motoren_info):
        """Einstellt Name, Initiatoren Status, Anz_Einheiten, AE_in_Schritt der Motoren anhand angegebene Dict"""
        for Motor_Coord, Motor_info in Motoren_info.items():
            Motor = self.get_Motor(Motor_Coord)
            Motor.info_einstellen(Motor_info)

    def alle_Motoren_stehen(self, Thread=None):
        """Gibt bool Wert zurück, ob alle Motoren stehen."""
        if Thread is not None:
            laufende_Motoren = []
            for Controller in self:
                for Motor in Controller:
                    if not Motor.steht():
                        laufende_Motoren.append(Motor.Name)
            if laufende_Motoren == []:
                return True
            else:
                Nachricht = getattr(Thread, "Nachricht", None)
                if Nachricht is not None:
                    Nachricht(f'Wartet auf Motoren: {", ".join(laufende_Motoren)}')
                return False
        else:
            for Controller in self:
                if Controller.Motoren_laufen():
                    return False
            return True

    # def allStop(self, stop_indicator: StopIndicator = None) -> bool:
    #
    #     if stop_indicator.has_stop_requested():
    #         return

    def allen_Motoren_Stop_warten(self, Thread=None):
        """Haltet die programme, bis alle Motoren stoppen."""
        while not self.alle_Motoren_stehen(Thread=Thread):
            if Thread is not None:
                if getattr(Thread, "Stop", False):
                    return
            time.sleep(0.5)

    def config(self, Motoren_Config):
        """Die Parametern einstellen laut angegebene Dict in Format {(bus, Axe) : Parameterwerte,}"""
        available_motors = self.Motoren_Liste()
        for motor_coord, Param_Werten in Motoren_Config.items():
            if motor_coord in available_motors:
                self.get_Motor(motor_coord).config(Param_Werten)
            else:
                logging.warning(f"Motor {motor_coord} ist nicht verbunden und kann nicht configuriert werden.")

    def get_config(self):
        """Liest die Parametern aus Controller und gibt zurück Dict mit Parameterwerten"""
        Motoren_Config = {}

        for Controller in self:
            for Motor in Controller:
                Motoren_Config[(Controller.bus, Motor.Axe)] = Motor.get_config()

        return Motoren_Config

    def leer_config_Detei_erstellen(self, address='input/Phytron_Motoren_config.csv'):
        """Erstellt eine Datei mit einer leeren Configurationtabelle"""
        f = open(address, "wt")

        separator = ';'
        Motoren_Config = self.get_config()

        # Motor liste schreiben
        Header = ['Motor Name', 'Bus', 'Axe', 'Mit Initiatoren(0 oder 1)', 'Einheiten', 'Einheiten pro Schritt']
        for Parameter_Name in self.PARAMETER_NUMBER.keys():
            Header.append(Parameter_Name)
        l = len(Header)
        Header = separator.join(Header)
        f.write(Header + '\n')

        for Controller in self:
            for Motor in Controller:
                Motorline = [''] * l
                Motorline[0] = Motor.Name
                Motorline[1] = str(Controller.bus)
                Motorline[2] = str(Motor.Axe)
                Motorline = separator.join(Motorline)
                f.write(Motorline + '\n')

        logging.info('Eine Datei mit einer leeren Configurationtabelle wurde erstellt.')

    def Config_aus_Datei_lesen(self, address='input/Phytron_Motoren_config.csv'):
        """Liest die Configuration aus Datei"""

        def check_parameters_values(parameters_values):
            """Prüfen, ob die Parameter erlaubte Werte haben."""
            pass

        f = open(address, "rt")

        separator = ';'

        Header = f.readline().rstrip('\n')
        Header = Header.split(separator)
        l = len(Header)

        # Kompatibelität der Datei prüfen
        if Header[:6] != ['Motor Name', 'Bus', 'Axe', 'Mit Initiatoren(0 oder 1)', 'Einheiten',
                          'Einheiten pro Schritt']:
            raise ReadConfigError(f'Datei {address} ist inkompatibel und kann nicht gelesen werden.')
        for Par_Name in Header[6:]:
            if not Par_Name in self.PARAMETER_NUMBER.keys():
                raise ReadConfigError(f'Ein unbekanter Parameter: {Par_Name}')

        Controller_zu_Inizialisierung = []
        Motoren_zu_Inizialisierung = []
        Motoren_info = {}
        Motoren_Parameter = {}

        for Motorline in f:
            Motorline = Motorline.rstrip('\n')
            Motorline = Motorline.split(separator)
            if len(Motorline) != l:
                raise ReadConfigError(
                    f'Datei {address} ist defekt oder inkompatibel und kann nicht gelesen werden. Spaltenahzahl ist nicht konstant.')

            # Motor info
            Name = Motorline[0]
            try:
                bus = int(Motorline[1])
            except ValueError:
                raise ReadConfigError(f'Fehler bei Bus von Motor {Name} lesen. ' +
                                      f'Bus muss ein int Wert zwischen 0 und 5 haben und kein {Motorline[1]}')
            try:
                Axe = int(Motorline[2])
            except ValueError:
                raise ReadConfigError(f'Fehler bei Axe von Motor {Name} lesen. ' +
                                      f'Axe muss ein int Wert 1 oder 2 haben und kein {Motorline[2]}')

            if not (bus, Axe) in Motoren_zu_Inizialisierung:
                Motoren_zu_Inizialisierung.append((bus, Axe))
            else:
                raise ReadConfigError(f'Motor {(bus, Axe)} ist mehrmals in der Datei beschrieben! .')

            if not bus in Controller_zu_Inizialisierung:
                Controller_zu_Inizialisierung.append(bus)

            if Motorline[3] == '0':
                ohne_Initiatoren = True
            elif Motorline[3] == '1' or Motorline[3] == '':
                ohne_Initiatoren = False
            else:
                raise ReadConfigError(
                    f'Motor {Name}: "Mit Initiatoren" muss ein Wert 0 oder 1 haben und kein {Motorline[3]}')

            if Motorline[4] != '':
                Anz_Einheiten = Motorline[4]
                if Motorline[5] != '':
                    try:
                        AE_in_Schritt = float(Motorline[5])
                    except ValueError:
                        raise ReadConfigError(
                            f'Motor {Name}: Einheiten pro Schritt muss ein float Wert haben und kein {Motorline[5]}')
                else:
                    AE_in_Schritt = 1
            else:
                Anz_Einheiten = "Schritte"
                AE_in_Schritt = 1

            Motoren_info[(bus, Axe)] = {'Name': Name, 'ohne_Initiatoren': ohne_Initiatoren,
                                        'Anz_Einheiten': Anz_Einheiten, 'AE_in_Schritt': AE_in_Schritt}

            # Parameter lesen
            Parameter_Werten = {}
            for i, Par_Wert_str in enumerate(Motorline[6:], 6):
                if Par_Wert_str != '':
                    try:
                        Parameter_Werten[Header[i]] = int(Par_Wert_str)
                    except ValueError:
                        raise ReadConfigError(
                            f'Motor {Name}: {Header[i]} muss {self.PARAMETER_DESCRIPTION[Header[i]]} sein und kein {Par_Wert_str}.')
                else:
                    Parameter_Werten[Header[i]] = self.PARAMETER_DEFAULT[Header[i]]

            check_parameters_values(Parameter_Werten)

            Motoren_Parameter[(bus, Axe)] = Parameter_Werten

        logging.info(f'Configuration aus Datei {address} wurde erfolgreich gelesen.')
        return Controller_zu_Inizialisierung, Motoren_zu_Inizialisierung, Motoren_info, Motoren_Parameter

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
                [self.Controller[bus].Motor[Axe] for bus, Axe in Liste_zu_Kalibrierung if
                 not self.Controller[bus].Motor[Axe].ohne_Initiatoren]

        # Voreinstellung der Parametern
        for Motor in Motoren_zu_Kalibrierung:
            Motor.Parameter_schreiben(1, 1)
            Motor.Parameter_schreiben(2, 1)
            Motor.Parameter_schreiben(3, 1)

        # Bis zum Ende laufen
        while True:
            alle_sind_am_Ende = True
            st = []
            for Motor in Motoren_zu_Kalibrierung:
                am_Ende = Motor.Initiatoren()[1]
                if not am_Ende:
                    alle_sind_am_Ende = False
                    Motor.geh(500000, Kalibrierung=True)
                st.append(Motor.Initiatoren())
            print(st)
            self.allen_Motoren_Stop_warten(Thread)
            if Thread is not None:
                if getattr(Thread, "Stop", False):
                    return

            if alle_sind_am_Ende:
                break

        Ende = []
        for Motor in Motoren_zu_Kalibrierung:
            Ende.append(Motor.Position())

        # Bis zum Anfang laufen
        while True:
            alle_sind_am_Anfang = True
            st = []
            for Motor in Motoren_zu_Kalibrierung:
                am_Anfang = Motor.Initiatoren()[0]
                if not am_Anfang:
                    alle_sind_am_Anfang = False
                    Motor.geh(-500000, Kalibrierung=True)
                st.append(Motor.Initiatoren())
            print(st)
            self.allen_Motoren_Stop_warten(Thread)
            if Thread is not None:
                if getattr(Thread, "Stop", False):
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
        for i, Koordinaten in enumerate(Motoren_Liste):
            Koordinaten = list(map(str, Koordinaten))
            Koordinaten = ','.join(Koordinaten)
            Motoren_Liste[i] = Koordinaten
        f.write(';'.join(Motoren_Liste) + '\n')

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
        for Controller in self:
            for Motor in Controller:
                if Motor.soft_limits != (None, None):
                    U_Grenze = Motor.soft_limits[0] if Motor.soft_limits[0] is not None else ''
                    O_Grenze = Motor.soft_limits[1] if Motor.soft_limits[1] is not None else ''
                    row = f"{Controller.bus},{Motor.Axe},{U_Grenze},{O_Grenze}\n"
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
            Motor = self.get_Motor(Motor_Coord)
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
                Motor = self.get_Motor(Motor_Koord)
                # Motor.Umrechnungsfaktor_einstellen(Umrechnungsfaktoren[i])
                Motor.Position_einstellen(Positionen[i])
                Motor.A_Null_einstellen(A_Nulls[i])

                Liste_zu_Kalibrierung.remove(Motor_Koord)

        logging.info('Kalibrierungsdaten für  Motoren {} wurde geladen.'.format(Motoren_Liste_f))
        if Liste_zu_Kalibrierung != []:
            logging.info('Motoren {} brauchen Kalibrierung.'.format(Liste_zu_Kalibrierung))

        return Liste_zu_Kalibrierung

    def Motoren_Liste(self):
        """Gibt zurück eine Liste der allen Motoren in Format: [(bus, Axe), …]"""
        Liste = []
        for Controller in self:
            for Motor in Controller:
                Liste.append((Controller.bus, Motor.Axe))
        return Liste

    def Motoren_Namen_Liste(self):
        """Gibt zurück eine Liste der Namen der Motoren"""
        Namen = []
        for Controller in self:
            for Motor in Controller:
                Namen.append(Motor.Name)
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
        for Controller in self:
            for Motor in Controller:
                if Motor.ohne_Initiatoren:
                    Liste.append((Controller.bus, Motor.Axe))
        return Liste

    def Motoren_mit_Init_Liste(self):
        """Gibt zurück eine Liste der allen Motoren ohne Initiatoren in Format: [(bus, Axe), …]"""
        Liste = []
        for Controller in self:
            for Motor in Controller:
                if not Motor.ohne_Initiatoren:
                    Liste.append((Controller.bus, Motor.Axe))
        return Liste

    def get_Motor(self, Koordinaten=None, Name=None):
        """Gibt den Motor objekt zurück aus Koordinaten in Format (bus, Axe)"""

        if Koordinaten is None and Name is None:
            raise ValueError("Kein Argument! Die Koordinaten oder der Name des Motors muss gegeben sein. ")
        elif Koordinaten is not None:
            bus, Axe = Koordinaten
            return self.Controller[bus].Motor[Axe]
        else:
            for Controller in self:
                for Motor in Controller:
                    if Motor.Name == Name:
                        return Motor
            raise ValueError(f"Es gibt kein Motor mit solchem Name: {Name}")

    def Stop(self):
        """Stoppt alle Axen"""
        Antwort = True
        for bus in self.Controller:
            Antwort = Antwort and self.Controller[bus].Stop()
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
