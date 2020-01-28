from unittest import TestCase, main

# from MotorController.MotorControllerInterface import *
from MotorController.MotorControllerInterface import Connector, ReplyError, Controller, Motor, CalibrationError
from MotorController.Phytron_MCC2 import MCC2BoxEmulator, MCC2Communicator


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


class TestController(TestCase):
    def test_make_motors(self):
        emulator_box = MCC2BoxEmulator(n_bus=16, n_axes=5, realtime=False)
        controller = Controller(emulator_box, 1)

        controller.make_motors()
        self.assertEqual(5, len(controller.motor))
        self.assertEqual([1, 2, 3, 4, 5], list(controller.motor.keys()))
        for i in range(1, 6):
            motor = controller.motor[i]
            self.assertEqual(Motor, type(motor))
            self.assertEqual(1, motor.controller.bus)
            self.assertEqual(i, motor.axis)
            self.assertEqual(Motor.DEFAULT_MOTOR_CONFIG, motor.config)


def preparation_to_test(realtime=False):
    emulator = MCC2BoxEmulator(n_bus=2, n_axes=2, realtime=realtime)
    controller = Controller(emulator, 1)
    motor = Motor(controller, 2)

    # 'contr' = Kelvin, 'norm' = Celsius, 'displ' = Fahrenheit
    motor.set_config({'display_units': 'F',
                      'norm_per_contr': 1,
                      'displ_per_contr': 9 / 5,
                      'displ_null': -17.7778,  # Anzeiger Null in normierte Einheiten
                      'null_position': 273.15  # Position von Anfang in Controller Einheiten
                      })
    step = 0.1
    emulator.set_parameter('Umrechnungsfaktor', step, 1, 2)

    motor_emulator = emulator.controller[1].motor[2]
    return motor, step, motor_emulator


class TestMotor(TestCase):
    def test_set_config(self):
        emulator_box = MCC2BoxEmulator(n_bus=2, n_axes=2, realtime=False)
        controller = Controller(emulator_box, 1)
        motor = Motor(controller, 2)

        self.assertEqual(Motor.DEFAULT_MOTOR_CONFIG, motor.config)

        new_config = {'with_initiators': 1,
                      'display_units': 'Pupkini',
                      'norm_per_contr': 4678.34,
                      'displ_per_contr': 123.489,
                      'displ_null': 3245.3,
                      'null_position': 123123.5}
        motor.set_config(new_config)
        self.assertEqual(new_config, motor.config)

        motor.set_config({'display_units': 'ml von Borschtsch', 'displ_null': 225.55, 'name': 'super motor'})
        self.assertEqual('ml von Borschtsch', motor.config['display_units'])
        self.assertEqual(225.55, motor.config['displ_null'])
        self.assertEqual('super motor', motor.name)

        with self.assertRaises(ValueError):
            motor.set_config({'abrakadabra!': 546})

        motor.set_config()
        self.assertEqual(Motor.DEFAULT_MOTOR_CONFIG, motor.config)

    def test_transform_units(self):
        emulator_box = MCC2BoxEmulator(n_bus=2, n_axes=2, realtime=False)
        controller = Controller(emulator_box, 1)
        motor = Motor(controller, 2)

        # 'contr' = Kelvin*0.123, 'norm' = Celsius, 'displ' = Fahrenheit
        motor.set_config({'display_units': 'F',
                          'norm_per_contr': 1 / 0.123,
                          'displ_per_contr': (9 / 5) / 0.123,
                          'displ_null': -17.7778,  # Anzeiger Null in normierte Einheiten
                          'null_position': 273.15 * 0.123  # Position von Anfang in Controller Einheiten
                          })

        self.assertEqual(round(373.15 * 0.123, 4), round(motor.transform_units(100, 'norm', to='contr'), 4))
        self.assertEqual(212, round(motor.transform_units(100, 'norm', to='displ'), 4))
        self.assertEqual(212, round(motor.transform_units(373.15 * 0.123, 'contr', to='displ'), 4))

        self.assertEqual(-40, round(motor.transform_units(-40, 'norm', to='displ'), 4))
        self.assertEqual(-40, round(motor.transform_units(-40, 'displ', to='norm'), 4))

        self.assertEqual(0, round(motor.transform_units(-459.67, 'displ', to='contr'), 4))

        self.assertEqual(-50, round(motor.transform_units(223.15 * 0.123, 'contr', to='norm'), 4))

        value = 3567.345
        value = motor.transform_units(value, 'contr', to='norm')
        value = motor.transform_units(value, 'norm', to='displ')
        value = motor.transform_units(value, 'displ', to='contr')
        self.assertEqual(3567.345, round(value, 4))

        # relative Transformation
        self.assertEqual(round(1 / 0.123, 4), round(motor.transform_units(1, 'contr', to='norm', rel=True), 4))
        self.assertEqual(0.123, round(motor.transform_units(1, 'norm', to='contr', rel=True), 4))
        self.assertEqual(round((9 / 5) / 0.123, 4), round(motor.transform_units(1, 'contr', to='displ', rel=True), 4))
        self.assertEqual(1, round(motor.transform_units(round((9 / 5) / 0.123, 4), 'displ', to='contr', rel=True), 4))
        self.assertEqual(round(9 / 5, 4), round(motor.transform_units(1, 'norm', to='displ', rel=True), 4))
        self.assertEqual(1, round(motor.transform_units(round(9 / 5, 4), 'displ', to='norm', rel=True), 4))

    def test_get_set_position(self):
        motor = preparation_to_test()[0]

        motor.set_position(0, 'norm')
        self.assertEqual(0, round(motor.position('norm'), 4))
        self.assertEqual(273.15, round(motor.position('contr'), 4))
        self.assertEqual(32, round(motor.position('displ'), 4))

        motor.set_position(373.15, 'contr')
        self.assertEqual(100, round(motor.position('norm'), 4))
        motor.set_position(0, 'norm')
        self.assertEqual(0, round(motor.position('norm'), 4))
        motor.set_position(212, 'displ')
        self.assertEqual(100, round(motor.position('norm'), 4))

    def test_go_to(self):
        motor, step, motor_emulator = preparation_to_test()

        motor.go_to(373.15, 'contr')
        motor_emulator.wait_stop()
        self.assertTrue(abs(100 - motor.position('norm')) < 2 * step, f"Ist bei {motor.position('norm')} statt 100")

        motor.go_to(0, 'norm')
        motor_emulator.wait_stop()
        self.assertTrue(abs(motor.position('norm')) < 2 * step, f"Ist bei {motor.position('norm')} statt 0")

        motor.go_to(212, 'displ')
        motor_emulator.wait_stop()
        self.assertTrue(abs(100 - motor.position('norm')) < 2 * step, f"Ist bei {motor.position('norm')} statt 100")

    def test_go(self):
        motor, step, motor_emulator = preparation_to_test()
        motor.set_position(0, 'norm')

        motor.go(-10.4, 'contr')
        motor_emulator.wait_stop()
        self.assertTrue(abs(-10.4 - motor.position('norm')) < 2 * step)
        motor.go(30.4, 'norm')
        motor_emulator.wait_stop()
        self.assertTrue(abs(20 - motor.position('norm')) < 2 * step, f"Ist bei {motor.position('norm')} statt 20")
        motor.go(10, 'displ')
        motor_emulator.wait_stop()
        self.assertTrue(abs(20 + 10 * 5 / 9 - motor.position('norm')) < 2 * step,
                        f"Ist bei {motor.position('norm')} statt {20 + 10 * 5 / 9}")

    def test_stand(self):
        motor, step, motor_emulator = preparation_to_test(realtime=True)

        motor.set_position(0)

        self.assertTrue(motor.stand())
        motor.go_to(1000)
        self.assertFalse(motor.stand())
        motor_emulator.box.realtime = False
        motor_emulator.wait_stop()
        self.assertTrue(motor.stand())

    def test_stop(self):
        motor, step, motor_emulator = preparation_to_test(realtime=True)

        motor.set_position(0)
        motor.go_to(1000)
        motor_emulator.sleep_steps(2)
        self.assertFalse(motor_emulator.stand())
        motor.stop()
        motor_emulator.sleep_steps(2)
        self.assertTrue(motor_emulator.stand())

    def test_read_parameter(self):
        motor, step, motor_emulator = preparation_to_test()

        for param_name in MCC2Communicator.PARAMETER_DEFAULT.keys():
            motor_emulator.box.set_parameter(param_name, 134.5, 1, 2)
            self.assertEqual(134.5, motor.read_parameter(param_name))

    def test_set_parameter(self):
        motor, step, motor_emulator = preparation_to_test()

        for param_name in MCC2Communicator.PARAMETER_DEFAULT.keys():
            motor.set_parameter(param_name, 134.5)
            self.assertEqual(134.5, motor_emulator.box.get_parameter(param_name, 1, 2))

    def test_at_the_end(self):
        motor, step, motor_emulator = preparation_to_test()

        motor_emulator.end_initiator = True
        self.assertTrue(motor.at_the_end())

        motor_emulator.end_initiator = False
        self.assertFalse(motor.at_the_end())

    def test_at_the_beginning(self):
        motor, step, motor_emulator = preparation_to_test()

        motor_emulator.beg_initiator = True
        self.assertTrue(motor.at_the_beginning())

        motor_emulator.beg_initiator = False
        self.assertFalse(motor.at_the_beginning())

    def test_calibrate(self):
        emulator = MCC2BoxEmulator(n_bus=2, n_axes=2)
        controller = Controller(emulator, 1)
        motor = Motor(controller, 2)
        motor_emulator = emulator.controller[1].motor[2]

        motor.config['with_initiators'] = False
        with self.assertRaises(CalibrationError):
            motor.calibrate()

        motor.config['with_initiators'] = True
        motor.calibrate()
        motor.go_to(0, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(-10000, motor.position('contr'))

        motor.go_to(1000, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(10000, motor.position('contr'))

    def test_soft_limits(self):
        emulator = MCC2BoxEmulator(n_bus=2, n_axes=2)
        controller = Controller(emulator, 1)
        motor = Motor(controller, 2)
        motor_emulator = emulator.controller[1].motor[2]
        motor.set_config({'norm_per_contr': 0.05, 'displ_per_contr': 1.0, 'null_position': -10000})

        motor.go_to(600, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(600, round(motor.position('norm'), 4))
        motor.go_to(400, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(400, round(motor.position('norm'), 4))

        motor.soft_limits = (430.2, 560.4)
        motor.go_to(600, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(560.4, round(motor.position('norm'), 4))
        motor.go_to(400, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(430.2, round(motor.position('norm'), 4))

        motor.soft_limits = (None, 560.4)
        motor.go_to(600, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(560.4, round(motor.position('norm'), 4))
        motor.go_to(400, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(400, round(motor.position('norm'), 4))

        motor.soft_limits = (430.2, None)
        motor.go_to(600, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(600, round(motor.position('norm'), 4))
        motor.go_to(400, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(430.2, round(motor.position('norm'), 4))

        motor.soft_limits = (None, None)
        motor.go_to(600, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(600, round(motor.position('norm'), 4))
        motor.go_to(400, 'norm')
        motor_emulator.wait_stop()
        self.assertEqual(400, round(motor.position('norm'), 4))

    def test_soft_limits_einstellen(self):
        motor, step, motor_emulator = preparation_to_test()

        motor.soft_limits_einstellen((123.45, 345.67), 'norm')
        self.assertEqual((123.45, 345.67), motor.soft_limits)

        motor.soft_limits_einstellen((273.15, 373.15), 'contr')
        self.assertEqual((0, 100), motor.soft_limits)

        motor.soft_limits_einstellen((32, 212), 'displ')
        self.assertEqual((0, 100), tuple(map(round, motor.soft_limits)))

        motor.soft_limits_einstellen((None, 345.67), 'norm')
        self.assertEqual((None, 345.67), motor.soft_limits)

        motor.soft_limits_einstellen((123.45, None), 'norm')
        self.assertEqual((123.45, None), motor.soft_limits)

        motor.soft_limits_einstellen((None, None), 'norm')
        self.assertEqual((None, None), motor.soft_limits)

        motor.soft_limits_einstellen((None, 212), 'displ')
        beg, end = motor.soft_limits
        end = round(end, 4)
        self.assertEqual((None, 100), (beg, end))

        motor.soft_limits_einstellen((32, None), 'displ')
        beg, end = motor.soft_limits
        beg = round(beg, 4)
        self.assertEqual((0, None), (beg, end))

        motor.soft_limits_einstellen((None, None), 'displ')
        self.assertEqual((None, None), motor.soft_limits)

    def test_get_parameters(self):
        emulator = MCC2BoxEmulator(n_bus=2, n_axes=2)
        controller = Controller(emulator, 1)
        motor = Motor(controller, 2)

        self.assertEqual(MCC2Communicator.PARAMETER_DEFAULT, motor.get_parameters())

    def test_set_parameters(self):
        emulator = MCC2BoxEmulator(n_bus=2, n_axes=2)
        controller = Controller(emulator, 1)
        motor = Motor(controller, 2)

        new_parameters = {'Lauffrequenz': 3435.4,
                          'Stoppstrom': 56456.3454,
                          'Laufstrom': 76576.445,
                          'Booststrom': 3424.45,
                          'Initiatortyp': 1}

        motor.set_parameters(new_parameters)
        parameters = motor.get_parameters()
        for key, value in new_parameters.items():
            self.assertEqual(value, parameters[key])


if __name__ == '__main__':
    main()
