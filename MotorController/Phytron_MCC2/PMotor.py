# coding= utf-8
from .PBox import *
import logging
import ULoggingConfig

if __name__ == '__main__':
    ULoggingConfig.init_config()

class PMotor:
    """Diese Klasse entspricht einem Motor, der mit einem MCC-2 Controller verbunden ist."""

    def __init__(self, controller: PController, Axe: int, ohne_Initiatoren: bool = False):
        self.Controller = controller
        self.Box = controller.Box
        self.Axe = Axe

        self.A_Null = 0  # Anzeiger Null in Normierte Einheiten
        self.Umrechnungsfaktor = self.Umrechnungsfaktor_lesen()

        self.info_einstellen()

        self.soft_limits = (None, None)

        self.ohne_Initiatoren = ohne_Initiatoren
        self.config()

    def config(self, Parameter_Werte=None):
        """Die Parametern einstellen laut angegebene Dict mit Parameterwerten"""
        # Parameter_Werte = {'Lauffrequenz': 4000, 'Stoppstrom': 5, 'Laufstrom': 11, 'Booststrom': 18}

        if Parameter_Werte is None:
            Parameter_Werte = self.Box.PARAMETER_DEFAULT

        for Name, Wert in Parameter_Werte.items():
            self.Parameter_schreiben(self.Box.PARAMETER_NUMBER[Name], Wert)

    def info_einstellen(self, Motor_info=None):
        """Einstellt Name, Initiatoren Status, Anz_Einheiten, AE_in_Schritt anhand angegebene Dict"""
        if Motor_info is None:
            Name = 'Motor' + str(self.Controller.bus) + "." + str(self.Axe)
            Motor_info = {'Name': Name, 'ohne_Initiatoren': False, 'Anz_Einheiten': 'Schritte', 'AE_in_Schritt': 1}

        self.Name = Motor_info['Name']
        self.ohne_Initiatoren = Motor_info['ohne_Initiatoren']
        self.Anz_Einheiten = Motor_info['Anz_Einheiten']
        self.AE_in_Schritt = Motor_info['AE_in_Schritt']

    def get_config(self):
        """Liest die Parametern aus Controller und gibt zurück Dict mit Parameterwerten"""
        Parameter_Werte = {}
        for Par_Name, Par_Nummer in self.Box.PARAMETER_NUMBER.items():
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
                              f'(Motor {self.Axe} beim Controller {self.Controller.bus}:)')
                return False

        Antwort = self.Befehl("A" + str(Ort))
        if Antwort[0] is True:
            logging.info(
                'Motor {} beim Controller {} wurde zu {} geschickt. Controller antwort ist "{}"'.format(self.Axe,
                                                                                                        self.Controller.bus,
                                                                                                        Ort, Antwort))
        else:
            logging.error(
                'Motor {} beim Controller {} wurde zu {} nicht geschickt. Controller antwort ist "{}"'.format(self.Axe,
                                                                                                              self.Controller.bus,
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
                'Motor {} beim Controller {} wurde um {} verschoben. Controller antwort ist "{}"'.format(self.Axe,
                                                                                                         self.Controller.bus,
                                                                                                         Verschiebung,
                                                                                                         Antwort))
        else:
            msg = f'Motor {self.Axe} beim Controller {self.Controller.bus} wurde um {Verschiebung} nicht verschoben. ' \
                  f'Controller antwort ist "{Antwort}"'
            logging.error(msg)

        return Antwort[0]

    def Stop(self):
        """Stoppt die Axe"""
        Antwort = self.Befehl("S")
        logging.info('Motor {} beim Controller {} wurde gestoppt. Controller antwort ist "{}"'.format(self.Axe,
                                                                                                      self.Controller.bus,
                                                                                                      Antwort))
        return Antwort[0]

    def steht(self):
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
        return self.Controller.Befehl(str(self.Axe) + str(text))

    def Initiatoren(self, check=True):
        """Gibt zurück der Status der Initiatoren als List von bool Werten in folgende Reihenfolge: -, +"""
        if self.Axe == 1:
            status = self.Controller.Initiatoren_Status()[:2]
        elif self.Axe == 2:
            status = self.Controller.Initiatoren_Status()[2:]
        else:
            raise ValueError('Axenummer ist falsch! "{}"'.format(self.Axe))

        if check:
            if status[0] and status[1]:
                raise MotorError("Beider Initiatoren sind Aktiviert. Motor ist falsch configuruert oder kaputt!")

        return status

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
            'Kalibrierung des Motors {} beim Controller {} wurde angefangen.'.format(self.Axe, self.Controller.bus))

        # Voreinstellung der Parametern
        self.Parameter_schreiben(1, 1)
        self.Parameter_schreiben(2, 1)
        self.Parameter_schreiben(3, 1)

        # Bis zum Ende laufen
        while not self.Initiatoren()[1]:
            self.geh(100000)
            self.Controller.Stop_warten()
        Ende = self.Position()

        # Bis zum Anfang laufen
        while not self.Initiatoren()[0]:
            self.geh(-100000)
            self.Controller.Stop_warten()
        Anfang = self.Position()

        # Null einstellen und die Skala normieren
        self.Null_einstellen()
        Umrechnungsfaktor = 1000 / (Ende - Anfang)
        self.Parameter_schreiben(3, Umrechnungsfaktor)

        logging.info(
            'Kalibrierung des Motors {} beim Controller {} wurde abgeschlossen.'.format(self.Axe, self.Controller.bus))
