# coding= utf-8
from .PBox import *
from .functions import bus_check
import logging
import ULoggingConfig
import time

if __name__ == '__main__':
    ULoggingConfig.init_config()


class PController:
    """Diese Klasse entspricht einem MCC-2 Controller"""

    def __init__(self, box: PBox, bus: int):

        self.ser = box.ser
        self.bus = bus
        self.Box = box
        self.Motor = {}

        if self.check_Controller()[0] is False:
            raise ConnectError("Controller #{} antwortet nicht oder ist nicht verbunden!".format(self.bus))

    def __iter__(self):
        return (Motor for Motor in self.Motor.values())

    def check_Controller(self):
        """Prüfen, ob der Controller da ist und funktioniert"""
        return bus_check(self.bus, ser=self.ser)

    def Befehl(self, text):
        """Befehl für den Contreller ausführen"""
        return self.Box.Befehl(text, self.bus)

    def Parametern_in_EPROM_speichern(self):
        """Speichert die aktuelle Parametern in Flash EPROM des Controllers"""
        self.Box.ser.timeout = 5
        Antwort = self.Befehl("SA")
        self.Box.ser.timeout = self.Box.timeout
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

    def make_Motoren(self):
        """erstellt Objekten für alle vervügbare Motoren"""
        n_Axen = self.n_Axen()
        self.Motor = {}
        for i in range(n_Axen):
            self.Motor[i + 1] = PMotor(self, i + 1)
        logging.info(f'Controller hat {n_Axen} Motor Objekten für alle verfügbare Axen erstellt.')

    def n_Axen(self):
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
