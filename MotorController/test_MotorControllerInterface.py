from unittest import TestCase, main

# from MotorController.MotorControllerInterface import *
from MotorController.MotorControllerInterface import Connector, ReplyError


class TestConnector(TestCase):
    connector = Connector()
    connector.end_symbol = b' egg'
    connector.beg_symbol = b'bgg '

    def test_reply_format(self):
        res = self.connector.reply_format(b'bgg hello! egg')
        self.assertEqual(res, b'hello!')

    def test_mess_format(self):
        res = self.connector.message_format(b'hello!')
        self.assertEqual(res, b'bgg hello! egg')

    def none_reply(self):
        res = self.connector.reply_format(b'')
        self.assertEqual(res, None)

    def test_false_reply1(self):
        with self.assertRaises(ReplyError):
            self.connector.reply_format(b'egghello! egg')

    def test_false_reply2(self):
        with self.assertRaises(ReplyError):
            self.connector.reply_format(b'bgg hello! eg')


if __name__ == '__main__':
    main()