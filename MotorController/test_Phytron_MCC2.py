from unittest import TestCase, main
import timeout_decorator

from .Phytron_MCC2 import *


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


class TestMCC2BoxEmulator(TestCase):
    def test_read_until(self):
        emulator_box = MCC2BoxEmulator(n_bus=3, n_axes=2, realtime=False)
        emulator_box.buffer = b'\x02command1\x03\x02command2\x03\x02command3\x03'

        self.assertEqual(b'\x02command1\x03', emulator_box.read_until(b'\x03'))
        self.assertEqual(b'\x02command2\x03\x02command3\x03', emulator_box.buffer)

        self.assertEqual(b'\x02command2\x03', emulator_box.read_until(b'\x03'))
        self.assertEqual(b'\x02command3\x03', emulator_box.buffer,)

        self.assertEqual(emulator_box.read_until(b'\x03'), b'\x02command3\x03', emulator_box.read_until(b'\x03'))
        self.assertEqual(b'', emulator_box.buffer)

        self.assertEqual(b'', emulator_box.read_until(b'\x03'))
        self.assertEqual(b'', emulator_box.buffer)

    def test_contr_version(self):
        emulator_box = MCC2BoxEmulator(n_bus=13, n_axes=2, realtime=False)
        emulator_box.flushInput()

        vers = b'\x02\x06MCC2 Emulator v1.0\x03'

        for i in range(13):
            bus_index = f'{i:x}'.encode()
            emulator_box.write(b'\x02' + bus_index + b'IVR\x03')
            self.assertEqual(vers, emulator_box.read_until(b'\x03'), f'Fehler beim Modul {i}')

        emulator_box.write(b'\x02DIVR\x03')
        self.assertEqual(b'', emulator_box.read_until(b'\x03'))

    def test_get_set_parameter(self):
        emulator_box = MCC2BoxEmulator(n_bus=16, n_axes=2, realtime=False)
        emulator_box.flushInput()
        for bus in range(16):
            for axis in (1, 2):
                for param_n in MCC2Communicator.PARAMETER_NUMBER.values():
                    # set 5.1
                    emulator_box.write(f'\x02{bus:x}{axis}P{param_n}S{5.1}\x03'.encode())
                    self.assertEqual(b'\x02\x06\x03', emulator_box.read_until(b'\x03'))
                    # read 5.1
                    emulator_box.write(f'\x02{bus:x}{axis}P{param_n}\x03'.encode())
                    self.assertEqual(b'\x02\x065.1\x03', emulator_box.read_until(b'\x03'))

                    # set 2560.89
                    emulator_box.write(f'\x02{bus:x}{axis}P{param_n}S{2560.89}\x03'.encode())
                    self.assertEqual(b'\x02\x06\x03', emulator_box.read_until(b'\x03'))
                    # read 2560.89
                    emulator_box.write(f'\x02{bus:x}{axis}P{param_n}\x03'.encode())
                    self.assertEqual(b'\x02\x062560.89\x03', emulator_box.read_until(b'\x03'))

        bus, axis = 0, 1
        # Unkorrekte Eingang1
        emulator_box.write(f'\x02{bus:x}{axis}P{3}Sf324sf\x03'.encode())
        self.assertEqual(b'\x02\x15\x03', emulator_box.read_until(b'\x03'))
        # Unkorrekte Eingang2
        emulator_box.write(f'\x02{bus:x}{axis}Pf3d4sf2d\x03'.encode())
        self.assertEqual(b'\x02\x15\x03', emulator_box.read_until(b'\x03'))
        # Unkorrekte Parameternummer get
        emulator_box.write(f'\x02{bus:x}{axis}P104\x03'.encode())
        self.assertEqual(b'\x02\x15\x03', emulator_box.read_until(b'\x03'))
        # Unkorrekte Parameternummer set
        emulator_box.write(f'\x02{bus:x}{axis}P103S20\x03'.encode())
        self.assertEqual(b'\x02\x15\x03', emulator_box.read_until(b'\x03'))

    def test_get_set_position(self):
        emulator_box = MCC2BoxEmulator(n_bus=16, n_axes=2, realtime=False)
        for bus in range(16):
            for axis in (1, 2):
                # Umrechnungsfactor gleich 1 einstellen
                emulator_box.write(f'\x02{bus:x}{axis}P{3}S{1}\x03'.encode())
                emulator_box.flushInput()

                # set -5.1
                emulator_box.write(f'\x02{bus:x}{axis}P{20}S{-5.1}\x03'.encode())
                self.assertEqual(b'\x02\x06\x03', emulator_box.read_until(b'\x03'))
                # read -5.1
                emulator_box.write(f'\x02{bus:x}{axis}P{20}\x03'.encode())
                self.assertEqual(b'\x02\x06-5.1\x03', emulator_box.read_until(b'\x03'))

                # set 600.52
                emulator_box.write(f'\x02{bus:x}{axis}P{20}S{600.52}\x03'.encode())
                self.assertEqual(b'\x02\x06\x03', emulator_box.read_until(b'\x03'))
                # read 600.52
                emulator_box.write(f'\x02{bus:x}{axis}P{20}\x03'.encode())
                self.assertEqual(b'\x02\x06600.52\x03', emulator_box.read_until(b'\x03'))

                # TODO Проверить действительно ли текущая позиция изменяется при изменении Umrechnungsfactor
                # Umrechnungsfactor gleich 0.5 einstellen
                emulator_box.write(f'\x02{bus:x}{axis}P{3}S{0.5}\x03'.encode())
                emulator_box.flushInput()
                emulator_box.write(f'\x02{bus:x}{axis}P{20}\x03'.encode())
                self.assertEqual(b'\x02\x06300.26\x03', emulator_box.read_until(b'\x03'))

    @timeout_decorator.timeout(1)
    def test_go_to(self):
        emulator_box = MCC2BoxEmulator(n_bus=16, n_axes=2, realtime=False)

        for bus in range(16):
            for axis in (1, 2):
                motor = emulator_box.controller[bus].motor[axis]
                motor.set_parameter(3, 1)
                # go to 200
                emulator_box.write(f'\x02{bus:x}{axis}A{200}\x03'.encode())
                self.assertEqual(b'\x02\x06\x03', emulator_box.read_until(b'\x03'), f'Fehler beim Motor ({bus},{axis})')
                motor.wait_stop()
                self.assertEqual(200, motor.get_position(), f'Fehler beim Motor ({bus},{axis})')

                # go to -5000
                emulator_box.write(f'\x02{bus:x}{axis}A{-5000}\x03'.encode())
                self.assertEqual(b'\x02\x06\x03', emulator_box.read_until(b'\x03'), f'Fehler beim Motor ({bus},{axis})')
                motor.wait_stop()
                self.assertEqual(-5000, motor.get_position()), f'Fehler beim Motor ({bus},{axis})'

        # Unkorrekte Eingang1
        emulator_box.write(f'\x02{0}{1}A324fg\x03'.encode())
        self.assertEqual(b'\x02\x15\x03', emulator_box.read_until(b'\x03'))
        # Unkorrekte Eingang2
        emulator_box.write(f'\x02{0}{1}A\x03'.encode())
        self.assertEqual(b'\x02\x15\x03', emulator_box.read_until(b'\x03'))

    @timeout_decorator.timeout(1)
    def test_go(self):
        emulator_box = MCC2BoxEmulator(n_bus=16, n_axes=2, realtime=False)

        for bus in range(16):
            for axis in (1, 2):
                motor = emulator_box.controller[bus].motor[axis]
                motor.set_parameter(3, 1)
                motor.set_position(0)

                # go 300
                emulator_box.write(f'\x02{bus:x}{axis}{300}\x03'.encode())
                self.assertEqual(b'\x02\x06\x03', emulator_box.read_until(b'\x03'), f'Fehler beim Motor ({bus},{axis})')
                motor.wait_stop()
                self.assertEqual(300, motor.get_position(), f'Fehler beim Motor ({bus},{axis})')

                # go -4300
                emulator_box.write(f'\x02{bus:x}{axis}{-4300}\x03'.encode())
                self.assertEqual(b'\x02\x06\x03', emulator_box.read_until(b'\x03'), f'Fehler beim Motor ({bus},{axis})')
                motor.wait_stop()
                self.assertEqual(-4000, motor.get_position(), f'Fehler beim Motor ({bus},{axis})')

        # Unkorrekte Eingang1
        emulator_box.write(f'\x02{0}{1}324fg\x03'.encode())
        self.assertEqual(b'\x02\x15\x03', emulator_box.read_until(b'\x03'))
        # Unkorrekte Eingang2
        emulator_box.write(f'\x02{0}{1}\x03'.encode())
        self.assertEqual(b'\x02\x15\x03', emulator_box.read_until(b'\x03'))

    def test_stop(self):
        emulator_box = MCC2BoxEmulator(n_bus=16, n_axes=2, realtime=True)

        for bus in range(16):
            for axis in (1, 2):
                motor = emulator_box.controller[bus].motor[axis]
                motor.set_parameter(3, 1)
                motor.set_position(0)
                motor.go_to(30000)
                self.assertFalse(motor.stand())
                emulator_box.write(f'\x02{bus:x}{axis}S\x03'.encode())
                self.assertEqual(b'\x02\x06\x03', emulator_box.read_until(b'\x03'), f'Fehler beim Motor ({bus},{axis})')
                motor.sleep_steps(2)
                self.assertTrue(motor.stand())

    def test_stand(self):
        emulator_box = MCC2BoxEmulator(n_bus=16, n_axes=2, realtime=True)

        for bus in range(16):
            for axis in (1, 2):
                motor = emulator_box.controller[bus].motor[axis]
                motor.set_parameter(3, 1)
                motor.set_position(0)

                emulator_box.write(f'\x02{bus:x}{axis}=H\x03'.encode())
                self.assertEqual(b'\x02\x06E\x03', emulator_box.read_until(b'\x03'),
                                 f'Fehler beim Motor ({bus},{axis})')

                motor.go_to(30000)
                emulator_box.write(f'\x02{bus:x}{axis}=H\x03'.encode())
                self.assertEqual(b'\x02\x06N\x03', emulator_box.read_until(b'\x03'),
                                 f'Fehler beim Motor ({bus},{axis})')

                motor.stop()
                motor.sleep_steps(2)
                emulator_box.write(f'\x02{bus:x}{axis}=H\x03'.encode())
                self.assertEqual(b'\x02\x06E\x03', emulator_box.read_until(b'\x03'),
                                 f'Fehler beim Motor ({bus},{axis})')

    @timeout_decorator.timeout(0.2)
    def test_initiators(self):
        emulator_box = MCC2BoxEmulator(n_bus=16, n_axes=2, realtime=False)
        emulator_box.flushInput()

        for bus in range(16):
            for axis in (1, 2):
                motor = emulator_box.controller[bus].motor[axis]
                motor.set_parameter(3, 1)
                motor.set_position(0)

                emulator_box.write(f'\x02{bus:x}{axis}=I-\x03'.encode())
                self.assertEqual(b'\x02\x06N\x03', emulator_box.read_until(b'\x03'),
                                 f'Fehler beim Motor ({bus},{axis})')
                emulator_box.write(f'\x02{bus:x}{axis}=I+\x03'.encode())
                self.assertEqual(b'\x02\x06N\x03', emulator_box.read_until(b'\x03'),
                                 f'Fehler beim Motor ({bus},{axis})')

                motor.set_position(14998)
                motor.go_to(30000)
                motor.wait_stop()

                emulator_box.write(f'\x02{bus:x}{axis}=I-\x03'.encode())
                self.assertEqual(b'\x02\x06N\x03', emulator_box.read_until(b'\x03'),
                                 f'Fehler beim Motor ({bus},{axis})')
                emulator_box.write(f'\x02{bus:x}{axis}=I+\x03'.encode())
                self.assertEqual(b'\x02\x06E\x03', emulator_box.read_until(b'\x03'),
                                 f'Fehler beim Motor ({bus},{axis})')

                motor.set_position(-14998)
                motor.go_to(-30000)
                motor.wait_stop()

                emulator_box.write(f'\x02{bus:x}{axis}=I-\x03'.encode())
                self.assertEqual(b'\x02\x06E\x03', emulator_box.read_until(b'\x03'),
                                 f'Fehler beim Motor ({bus},{axis})')
                emulator_box.write(f'\x02{bus:x}{axis}=I+\x03'.encode())
                self.assertEqual(b'\x02\x06N\x03', emulator_box.read_until(b'\x03'),
                                 f'Fehler beim Motor ({bus},{axis})')


if __name__ == '__main__':
    main()
