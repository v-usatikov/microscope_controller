from unittest import TestCase, main
import timeout_decorator

from .Phytron_MCC2 import *


# # noinspection PyPep8Naming
# class Test_command_format(TestCase):
#
#     def test_upper(self):
#         res = command_format('hello', 9)
#         self.assertEqual(res, b'\x029hello\x03')
#
#     def test_bus_too_big(self):
#         with self.assertRaises(ValueError):
#             command_format('hello', 10)
#
#     def test_not_str(self):
#         with self.assertRaises(AttributeError):
#             command_format(0, 9)
#
#     # def test_isupper(self):
#     #     self.assertTrue('FOO'.isupper())
#     #     self.assertFalse('Foo'.isupper())
#     #
#     # def test_split(self):
#     #     s_out = 'hello world'
#     #     self.assertEqual(s_out.split(), ['hello', 'world'])
#     #     # check that s_out.split fails when the separator is not a string
#     #     with self.assertRaises(TypeError):
#     #         s_out.split(2)

# box = MCC2BoxEmulator(n_bus=3, n_axes=2, realtime=False)

class Test__MCC2MotorEmulator(TestCase):

    @timeout_decorator.timeout(0.1)
    def test_move_to_fast(self):
        box = MCC2BoxEmulator()
        motor = MCC2MotorEmulator(box)
        init_position = motor.get_position()
        if init_position == 5000:
            motor.go_to(-5000)
            motor.wait_stop()
            self.assertEqual(motor.get_position(), -5000)
        else:
            motor.go_to(5000)
            motor.wait_stop()
            self.assertEqual(motor.get_position(), 5000)

    def test_set_position(self):
        box = MCC2BoxEmulator()
        motor = MCC2MotorEmulator(box)
        motor.set_position(0)
        self.assertEqual(motor.get_position(), 0)
        motor.set_position(500)
        self.assertEqual(motor.get_position(), 500)

    def test_move_to_thread(self):
        box = MCC2BoxEmulator(realtime=True)
        motor = MCC2MotorEmulator(box)
        motor.set_position(0)
        motor.go_to(400)
        motor.sleep_steps(2)
        self.assertTrue(0 < motor.get_position() < 350)
        motor.stop()

    def test_stop(self):
        box = MCC2BoxEmulator(realtime=True)
        motor = MCC2MotorEmulator(box)
        motor.set_position(0)
        motor.go_to(400)
        motor.sleep_steps(2)
        position_before_stop = motor.get_position()
        motor.sleep_steps(2)
        motor.stop()
        stop_position = motor.get_position()
        motor.sleep_steps(2)

        self.assertTrue(position_before_stop > 0)
        self.assertTrue(position_before_stop < stop_position)
        self.assertTrue(stop_position == motor.get_position())

    def test_stand(self):
        box = MCC2BoxEmulator(realtime=True)
        motor = MCC2MotorEmulator(box)
        motor.go_to(400)
        motor.sleep_one_step()
        self.assertFalse(motor.stand())
        motor.stop()
        motor.sleep_steps(2)
        self.assertTrue(motor.stand())

    @timeout_decorator.timeout(0.2)
    def test_initiators(self):
        box = MCC2BoxEmulator(realtime=False)
        motor = MCC2MotorEmulator(box)
        motor.go_to(30000)
        motor.wait_stop()
        self.assertEqual(motor.get_position(), 10000)
        motor.go_to(-30000)
        motor.wait_stop()
        self.assertEqual(motor.get_position(), -10000)



if __name__ == '__main__':
    main()
