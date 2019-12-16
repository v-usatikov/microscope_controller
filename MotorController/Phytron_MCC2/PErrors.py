# coding= utf-8
"""Definition der möglichen Fehler"""


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
