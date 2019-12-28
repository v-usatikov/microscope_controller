from unittest import TestCase, main
from .Phytron_MCC2 import *


# noinspection PyPep8Naming
class Test_command_format(TestCase):

    def test_upper(self):
        res = command_format('hello', 9)
        self.assertEqual(res, b'\x029hello\x03')

    def test_bus_too_big(self):
        with self.assertRaises(ValueError):
            command_format('hello', 10)

    def test_not_str(self):
        with self.assertRaises(AttributeError):
            command_format(0, 9)

    # def test_isupper(self):
    #     self.assertTrue('FOO'.isupper())
    #     self.assertFalse('Foo'.isupper())
    #
    # def test_split(self):
    #     s_out = 'hello world'
    #     self.assertEqual(s_out.split(), ['hello', 'world'])
    #     # check that s_out.split fails when the separator is not a string
    #     with self.assertRaises(TypeError):
    #         s_out.split(2)

if __name__ == '__main__':
    main()


