from unittest import TestCase
from .Phytron_MCC2 import command_format


class TestCommand_format(TestCase):
    def test_bus_too_big(self):
        with self.assertRaises(ValueError):
            command_format('hello', 9)


class TestCommand_format1(TestCase):
    def tests(self):
        self.fail()
