import socket

from serial import Serial


class Connector:
    """Ein Objekt, durch das die Kommunikation zwischen dem Programm und dem Controller stattfindet."""
    def send(self, message: bytes):
        """Schickt ein Nachricht zum Controller."""
        raise NotImplementedError

    # def read(self, n_bytes: int) -> bytes:
    #     """Liest eine bestimmte anzahl von Bytes von dem Controller und gibt das zurück."""
    #     raise NotImplementedError
    #
    # def read_until(self, end_symbol: bytes):
    #     """Liest ein Nachricht von dem Controller bis zum bestimmten End-Symbol und gibt das zurück."""
    #     raise NotImplementedError


class SerialConnector(Connector):
    """Connector Objekt für eine Verbindung durch Serial Port."""

    def __init__(self, port: str, timeout: float = 0.2, baudrate: float = 115200):
        self.ser = Serial(port, baudrate, timeout=timeout)

    def send(self, message: bytes):
        """Schickt ein Nachricht zum Controller."""
        self.ser.write(message)

    def read_until(self, end_symbol: bytes):
        """Liest ein Nachricht von dem Controller bis zum bestimmten End-Symbol und gibt das zurück."""
        return self.ser.read_until(end_symbol)


class EthernetConnector(Connector):
    """Connector Objekt für eine Verbindung durch Ethernet."""

    def __init__(self, ip: str, port: str, timeout: float = 1):
        self.socket = socket.socket()
        self.socket.connect((ip, port))
        self.socket.settimeout(timeout)

    def send(self, message: bytes):
        """Schickt ein Nachricht zum Controller."""
        self.socket.send(message)

    def read(self, max_size: int = 1024):
        """Liest ein Nachricht von dem Controller bis zum bestimmten End-Symbol und gibt das zurück."""
        return self.socket.recv(max_size)