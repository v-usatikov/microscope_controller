import socket

from serial import Serial
from typing import Dict, List, Tuple, Union
import serial.tools.list_ports


class Connector:
    """Ein Objekt, durch das die Kommunikation zwischen dem Programm und dem Controller stattfindet."""
    def send(self, message: bytes):
        """Schickt ein Nachricht zum Controller."""
        raise NotImplementedError

    def read(self, end_symbol: bytes = None, max_bytes: int = 1024) -> bytes:
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

    def __init__(self, port: str, timeout: float = 0.2, baudrate: float = 115200):
        self.ser = Serial(port, baudrate, timeout=timeout)

    def send(self, message: bytes):
        """Schickt ein Nachricht zum Controller."""
        self.ser.write(message)

    def read(self, end_symbol: bytes = None, max_bytes: int = 1024) -> bytes:
        """Liest ein Nachricht von dem Controller bis zum bestimmten End-Symbol und gibt das zurück."""
        return self.ser.read_until(end_symbol, max_bytes)

    def clear_buffer(self):
        """Löscht alle vorher empfangene information aus Buffer"""
        self.ser.flushInput()

    def set_timeout(self, timeout: float):
        """Einstellt das Time-out"""
        self.ser.timeout = timeout

    def get_timeout(self) -> float:
        """Gibt den Wert des Time-outs zurück"""
        return self.ser.timeout


class EthernetConnector(Connector):
    """Connector Objekt für eine Verbindung durch Ethernet."""

    def __init__(self, ip: str, port: str, timeout: float = 1):
        self.socket = socket.socket()
        self.socket.connect((ip, port))
        self.socket.settimeout(timeout)

    def send(self, message: bytes):
        """Schickt ein Nachricht zum Controller."""
        self.socket.send(message)

    def read(self, end_symbol: bytes = None, max_bytes: int = 1024) -> bytes:
        """Liest ein Nachricht von dem Controller und gibt das zurück."""
        return self.socket.recv(max_bytes)
