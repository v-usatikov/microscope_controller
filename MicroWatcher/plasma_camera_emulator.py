import threading
from copy import deepcopy
from time import sleep

import numpy as np
import cv2
from math import sqrt, pi, cos, sin, exp

from MicroWatcher.camera_interface import CameraInterf
from MotorController.MotorControllerInterface import Motor, Box
from MotorController.Phytron_MCC2 import MCC2BoxEmulator


def paint_circle(frame: np.ndarray, pl_x: float, pl_y: float, radius: float) -> None:
    if radius > 0:
        i_a = np.arange(2048)
        range_ = np.arange(1088)
        range_ = range_[np.abs(1088 - range_ - pl_y - 1088 / 2) < radius+60]
        # print(range_)
        for j in range_:
            r = np.sqrt((i_a - pl_x - 2048 / 2) ** 2 + (1088 - j - pl_y - 1088 / 2) ** 2)

            line = np.zeros(2048)
            line = frame[j, :] + 255 / (0.1 * (r - radius + 1) ** 2 + 1)
            line[r < radius] = 255
            line[line > 255] = 255

            frame[j, :] = line


def paint_line(frame: np.ndarray, line_x: float, d: float, transp=0.4) -> None:
    range_ = np.arange(2048)
    range_ = range_[np.abs(range_ - line_x - 2048 / 2) < d/2]
    # print(range_)
    for i in range_:
        frame[:, i] = frame[:, i]*(1 - (1-transp)*np.sin(np.arccos((i - line_x - 2048 / 2)*2/d)))


def intens_from_dist(dist: float, d: float, intens_max: float = 1) -> float:
    if dist > 2*d:
        return 0
    else:
        return intens_max*exp(-dist**2/(1.5*d**2))


def plasma_radius_from_intens(intens: float, radius_max: float = 1, intens_max: float = 1) -> float:
    return intens*radius_max/intens_max


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

        self.jet_d = 0.07  # Jet Diameter in mm
        self.laser_d = 0.07  # Laser Diameter in mm

        self.exposure = 40000
        self.normal_exposure = 40000
        self.dark_exposure = 10000

        self._bg = cv2.imread('test_data/hintg.bmp', 0)

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

    def get_frame(self, camera_n: int):
        if camera_n not in [1, 2]:
            raise ValueError(f'Unerwartete Kameranummer "{camera_n}"')

        if camera_n == 1:
            g = self.g1
            pl_x = self.g1 * self.j_x()
            pl_z = self.g1 * self.l_z()
        else:
            g = self.g2
            pl_x = self.g2*(self.j_x()*cos(self.phi) - self.j_y()*sin(self.phi))
            pl_z = self.g2 * self.l_z()

        frame = deepcopy(self._bg)

        k = self.exposure / self.normal_exposure
        frame[:,:] = frame[:,:] * k
        frame[frame > 255] = 255

        paint_line(frame, line_x=pl_x, d=g*self.jet_d, transp=0.4)

        if self.laser_on:
            intens = intens_from_dist(dist=abs(self.j_y()-self.l_y()), d=self.jet_d)
            intens *= self.exposure / self.dark_exposure
            plasma_radius = plasma_radius_from_intens(intens, radius_max=6*g*self.jet_d/2)
            paint_circle(frame, pl_x, pl_z, plasma_radius)

        return frame

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
        self.jet_emulator.exposure = value

    def get_exposure(self) -> float:
        return self.jet_emulator.exposure

    def set_gain(self, value: float):
        pass

    def get_gain(self) -> float:
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
        return self.jet_emulator.get_frame(self.id)


# cv2.imshow('image', img)
# cv2.waitKey(0)
# cv2.destroyAllWindows()

if __name__ == '__main__':
    camera1 = CameraEmulator(1)

    # camera1.jet_emulator.realtime(False)
    # camera1.jet_emulator.jet_x.go_to(-5, 'displ')
    # camera1.show_frame()

    # camera1.jet_emulator.realtime(True)
    # camera1.start_video_record(start_stream=True)
    # sleep(1)
    # camera1.jet_emulator.jet_x.go_to(-5, 'displ', wait=True)
    # # camera1.jet_emulator.jet_x.go_to(1, 'displ', wait=True)
    # camera1.stop_video_record()
    # camera1.stop_stream()

    # camera1.jet_emulator.realtime(True)
    # camera1.jet_emulator.jet_x.go_to(-5, 'displ')
    # camera1.show_video()


    # camera1.jet_emulator.realtime(False)
    # camera1.jet_emulator.jet_x.go_to(-5, 'displ')
    # camera1.jet_emulator.laser_on = True
    # camera1.jet_emulator.exposure = 10000
    # camera1.show_frame()

    camera2 = CameraEmulator(2)
    camera2.jet_emulator.realtime(True)
    camera2.start_video_record(start_stream=True, fps=60)
    sleep(1)
    camera2.jet_emulator.jet_y.go_to(5, 'displ', wait=True)
    camera2.jet_emulator.jet_y.go_to(-2, 'displ', wait=True)
    sleep(1)
    camera2.jet_emulator.laser_on = True
    camera2.jet_emulator.exposure = 10000
    sleep(1)
    camera2.jet_emulator.jet_y.go_to(-1, 'displ', wait=True)
    camera2.jet_emulator.jet_y.go_to(1, 'displ', wait=True)
    camera2.jet_emulator.jet_y.go_to(-1, 'displ', wait=True)
    camera2.jet_emulator.jet_y.go_to(1, 'displ', wait=True)
    camera2.jet_emulator.jet_y.set_parameter('Lauffrequenz', 20)
    camera2.jet_emulator.jet_y.go_to(-0.5, 'displ', wait=True)
    camera2.jet_emulator.jet_y.set_parameter('Lauffrequenz', 5)
    camera2.jet_emulator.jet_y.go_to(0, 'displ', wait=True)
    sleep(1)

    # camera1.jet_emulator.jet_x.go_to(1, 'displ', wait=True)
    camera2.stop_video_record()
    camera2.stop_stream()