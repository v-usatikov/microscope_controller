import threading
from copy import deepcopy
from time import sleep

import numpy as np
import cv2
from math import sqrt, pi, cos, sin

from MicroWatcher.CameraInterface import CameraInterf
from MotorController.MotorControllerInterface import Motor, Box
from MotorController.Phytron_MCC2 import MCC2BoxEmulator


def paint_circle(frame: np.ndarray, pl_x: float, pl_y: float, radius: float):
    if radius > 0:
        i_a = np.arange(2048)
        range_ = np.arange(1088)
        range_ = range_[np.abs(1088 - range_ - pl_y - 1088 / 2) < radius+60]
        print(range_)
        for j in range_:
            r = np.sqrt((i_a - pl_x - 2048 / 2) ** 2 + (1088 - j - pl_y - 1088 / 2) ** 2)
            frame[j, :] = 255 / (0.1 * (r - radius + 1) ** 2 + 1)
            frame[j, r<radius] = 255


class JetEmulator:
    def __init__(self, jet_x: Motor = None, jet_y: Motor = None, laser_y: Motor = None, laser_z: Motor = None,
                 phi: float = 30, g1: float = 100, g2: float = 100):

        if None in [jet_x, jet_y, laser_y, laser_z]:
            self.box_emulator = MCC2BoxEmulator(n_bus=2, n_axes=2, realtime=False)
            box = Box(self.box_emulator, input_file='test_data/test_motor_input.csv')
            box.calibrate_motors()
            self.jet_x = box.get_motor_by_name('JetX')
            self.jet_y = box.get_motor_by_name('JetY')
            self.laser_y = box.get_motor_by_name('LaserY')
            self.laser_z = box.get_motor_by_name('LaserZ')
        else:
            self.jet_x = jet_x
            self.jet_y = jet_y
            self.laser_y = laser_y
            self.laser_z = laser_z

        self._motors = [self.jet_x, self.jet_y, self.laser_y, self.laser_z]

        for motor in self._motors:
            motor.set_position(500, 'norm')
            motor.set_display_null()


        self.phi = phi * pi / 180
        self.g1 = g1
        self.g2 = g2

        self.jet_d = 0.02  # Jet Diameter in mm
        self.laser_d = 0.5  # Laser Diameter in mm

        self._bg = cv2.imread('test_data/hintg.bmp', 0)
        self._ray = ~cv2.imread('test_data/ray.bmp', 0) / 255

        self.laser_on = False

    def realtime(self, realtime: bool):
        self.box_emulator.realtime = realtime

    def j_x(self):
        return self.jet_x.position('displ')

    def j_y(self):
        return self.jet_y.position('displ')

    def l_y(self):
        return self.laser_y.position('displ')

    def l_z(self):
        return self.laser_z.position('displ')

    def _make_ray_frame(self, x_p):
        img = deepcopy(self._bg)
        x_p = round(2088 / 2 + x_p)
        print(x_p)
        img[:, x_p - 6:x_p + 7] = img[:, x_p - 6:x_p + 7] * self._ray
        return img

    def get_camera1_frame(self):
        if not self.laser_on:
            return self._make_ray_frame(self.g1*(self.j_x()))

    def get_camera2_frame(self):
        if not self.laser_on:
            return self._make_ray_frame(self.g2*(self.j_x()*cos(self.phi) - self.j_y()*sin(self.phi)))

    # def plasma_intens(self) -> float:
    #
    # def plasma_pos(self) -> (float, float, float):


class CameraEmulator(CameraInterf):

    def __init__(self, camera_id: int, jet_emulator: JetEmulator = None, fps: float = 30):
        super().__init__()
        if jet_emulator is None:
            self.jet_emulator = JetEmulator()

        if camera_id in [1, 2]:
            self.id = camera_id
        else:
            raise ValueError(f'Camera id muss 1 oder 2 sein und nicht "{camera_id}"')

        self.stream_on = False
        self.fps = fps

    def set_exposure(self, value: float):
        pass

    def get_exposure(self):
        return 1

    def set_gain(self, value: float):
        pass

    def get_gain(self):
        return 0

    def start_stream(self, delay: float = 0):
        self.stream_on = True
        threading.Thread(target=self._stream).start()

    def _stream(self):
        while self.stream_on:
            self.new_frame_event(self.get_frame())
            sleep(1/self.fps)

    def stop_stream(self):
        self.stream_on = False

    def get_frame(self) -> np.ndarray:
        if self.id == 1:
            return self.jet_emulator.get_camera1_frame()
        elif self.id == 2:
            return self.jet_emulator.get_camera2_frame()


# cv2.imshow('image', img)
# cv2.waitKey(0)
# cv2.destroyAllWindows()

if __name__ == '__main__':
    camera1 = CameraEmulator(1)

    # camera1.jet_emulator.realtime(False)
    # camera1.jet_emulator.jet_x.go_to(-5, 'displ')
    # camera1.show_frame()

    camera1.jet_emulator.realtime(True)
    camera1.start_video_record(start_stream=True)
    camera1.jet_emulator.jet_x.go_to(-5, 'displ', wait=True)
    camera1.stop_video_record()
    camera1.stop_stream()

    # camera1.jet_emulator.realtime(True)
    # camera1.jet_emulator.jet_x.go_to(-5, 'displ')
    # camera1.show_video()