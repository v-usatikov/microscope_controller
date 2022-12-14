import threading, random
from copy import deepcopy
from time import sleep

import numpy as np
import cv2
from math import sqrt, pi, cos, sin, exp

from mscontr.microwatcher.camera_interface import CameraInterf
from motor_controller import Motor, Box
from motor_controller.Phytron_MCC2 import MCC2BoxEmulator
import mscontr.microwatcher as microwatcher
from mscontr.microwatcher.plasma_watcher import CameraCoordinates, show

DATA_FOLDER = microwatcher.__file__[:-11]+"data/"


def paint_circle(frame: np.ndarray, x: float, y: float, radius: float) -> None:
    if radius > 0:
        i_a = np.arange(2048)
        range_ = np.arange(1088)
        range_ = range_[np.abs(1088 - range_ - y - 1088 / 2) < radius + 60]
        # print(range_)
        for j in range_:
            r = np.sqrt((i_a - x - 2048 / 2) ** 2 + (1088 - j - y - 1088 / 2) ** 2)

            line = np.zeros(2048)
            line = frame[j, :] + 255 / (0.1 * (r - radius + 1) ** 2 + 1)
            line[r < radius] = 255
            line[line > 255] = 255

            frame[j, :] = line

def paint_line(frame: np.ndarray, line_x: float, d: float, transp=0.8) -> None:
    range_ = np.arange(2048)
    range_ = range_[np.abs(range_ - line_x - 2048 / 2) < d/2]
    # print(range_)
    line_frame = 254*np.ones(frame.shape)
    for i in range_:
        line_frame[:, i] = line_frame[:, i]*(1-transp)*np.sin(np.arccos((i - line_x - 2048 / 2)*2/d))

    mask = np.array(frame)
    frame[:,:] = frame[:,:] + line_frame[:,:]
    mask[:, :] = mask[:, :] + line_frame[:, :]

    frame[mask > 254] = 254


def paint_nozzle(frame: np.ndarray, nozzle: np.ndarray, nozzle_x: float) -> None:

    nozzle = nozzle.copy()
    ym, xm = nozzle.shape
    # show(frame)
    # show(nozzle)

    if nozzle_x < - xm/2 - 200 or nozzle_x > xm/2 + 200:
        return

    big_nozzle_frame = np.ones((300, xm*3))

    shift = round(nozzle_x)

    big_nozzle_frame[0:300, xm+shift:2*xm+shift] = nozzle[0:300, :]
    # show(big_nozzle_frame)

    nozzle[:300, :] = big_nozzle_frame[:, xm:2*xm]
    # show(nozzle)

    mask = nozzle != 1
    frame[mask] = nozzle[mask]
    # show(frame)


def paint_line_white(frame: np.ndarray, line_x: float, d: float, transp=0.4) -> None:
    range_ = np.arange(2048)
    range_ = range_[np.abs(range_ - line_x - 2048 / 2) < d/2]
    # print(range_)
    for i in range_:
        frame[:, i] = frame[:, i]*(1 - (1-transp)*np.sin(np.arccos((i - line_x - 2048 / 2)*2/d)))


def intens_from_dist(dist: float, d: float, intens_max: float = 1) -> float:
    if dist > 2*d:
        return 0
    else:
        return intens_max*exp(-(dist)**2/(0.375*d**2))


def plasma_radius_from_intens(intens: float, radius_max: float = 1, intens_max: float = 1) -> float:
    return intens*radius_max/intens_max


def flicker(mu: float, sigma: float):
    if sigma == 0:
        return mu
    if mu == 0:
        return 0
    res = random.normalvariate(mu, sigma)
    if res < 0:
        return 0
    return res


class JetEmulator:
    def __init__(self, def_init: bool = True, jet_x: Motor = None, jet_z: Motor = None, laser_z: Motor = None, laser_y: Motor = None,
                 phi: float = 90, psi: float = 45, g1: float = 10, g2: float = 10,
                 jet_d: float = 70, laser_d: float = 70, laser_jet_shift: float = 0, flicker_sigma: float = 0):

        if def_init:
            self.box_emulator = MCC2BoxEmulator(n_bus=2, n_axes=2, realtime=False)
            self.box = Box(self.box_emulator, input_file=DATA_FOLDER+'test_motor_input.csv')
            self.box.motors_cluster.calibrate_motors()
            self.jet_x = self.box.get_motor_by_name('JetX')
            self.jet_z = self.box.get_motor_by_name('JetZ')
            self.laser_z = self.box.get_motor_by_name('LaserZ')
            self.laser_y = self.box.get_motor_by_name('LaserY')
        else:
            self.jet_x = jet_x
            self.jet_z = jet_z
            self.laser_z = laser_z
            self.laser_y = laser_y

        self.jet_x_pos = 0
        self.jet_z_pos = 0
        self.laser_z_pos = 0
        self.laser_y_pos = 0

        self._motors = [self.jet_x, self.jet_z, self.laser_z, self.laser_y]

        for motor in self._motors:
            if motor is not None:
                motor.set_display_null(500)

        self.phi = phi * pi / 180
        self.psi = psi * pi / 180
        self.g1 = g1
        self.g2 = g2
        self.camera1_coord = CameraCoordinates(self.psi, jet_x, jet_z)
        self.camera2_coord = CameraCoordinates(self.phi + self.psi, jet_x, jet_z)

        self.jet_d = jet_d  # Jet Diameter in Mikrometer
        self.laser_d = laser_d  # Laser Diameter in Mikrometer
        self.laser_jet_shift = laser_jet_shift
        self.flicker_sigma = flicker_sigma

        self.exposure = 40000
        self.normal_exposure = 40000
        self.dark_exposure = 10000

        self._bg = cv2.imread(DATA_FOLDER+'hintg.bmp', 0)
        self._bg[:, :] = 0.1*self._bg[:, :]
        self._nozzle = cv2.imread(DATA_FOLDER + 'nozzle.bmp', 0)

        self.laser_on = False

        self._drift_on = False

    def realtime(self, realtime: bool):
        self.box_emulator.realtime = realtime

    def plasma_drift_on(self, speed: float = 2, max_shift: float = 1000, update_freq: float = 4):
        def drift(self, speed: float, max_shift: float, update_freq: float):
            direction = 1
            while self._drift_on:
                if abs(self.laser_jet_shift) > max_shift:
                    direction = -self.laser_jet_shift/abs(self.laser_jet_shift)
                self.laser_jet_shift += direction*speed/update_freq
                sleep(1/update_freq)
            print('drift_on:', self._drift_on)

        self._drift_on = True
        threading.Thread(target=drift, args=(self, speed, max_shift, update_freq)).start()

    def plasma_drift_off(self):
        self._drift_on = False

    def j_x(self):
        if self.jet_x is not None:
            self.jet_x_pos = self.jet_x.position('displ')
        return self.jet_x_pos

    def j_z(self):
        if self.jet_z is not None:
            self.jet_z_pos = self.jet_z.position('displ')
        return self.jet_z_pos

    def l_z(self):
        if self.laser_z is not None:
            self.laser_z_pos = self.laser_z.position('displ')
        return self.laser_z_pos

    def l_y(self):
        if self.laser_y is not None:
            self.laser_y_pos = self.laser_y.position('displ')
        return self.laser_y_pos

    def get_frame(self, camera_n: int):
        if camera_n not in [1, 2]:
            raise ValueError(f'Unerwartete Kameranummer "{camera_n}"')

        x = self.j_x()
        z = self.j_z()
        if camera_n == 1:
            g = self.g1
            pl_x, pl_z = self.camera1_coord.mc_to_cc(x, z)
            pl_z /= g
        else:
            g = self.g2
            pl_x, pl_z = self.camera2_coord.mc_to_cc(x, z)
            pl_z /= g
        pl_y = self.l_y()/g

        frame = deepcopy(self._bg)

        paint_line(frame, line_x=pl_z, d=self.jet_d / g, transp=0.6)
        paint_nozzle(frame, self._nozzle, nozzle_x=pl_z)

        k = self.exposure / self.normal_exposure
        mask = np.array(frame)*k
        frame[:,:] = frame[:,:] * k
        frame[mask > 254] = 254
        frame[frame < 1] = 1


        if self.laser_on:
            intens = intens_from_dist(dist=abs(self.j_z()-self.l_z()-self.laser_jet_shift), d=self.jet_d)
            intens = flicker(intens, self.flicker_sigma)
            intens *= self.exposure / self.dark_exposure
            plasma_radius = plasma_radius_from_intens(intens, radius_max=6*self.jet_d/(2*g))
            paint_circle(frame, pl_z, pl_y, plasma_radius)

        return frame

    # def plasma_intens(self) -> float:
    #
    # def plasma_pos(self) -> (float, float, float):


class CameraEmulator(CameraInterf):

    def __init__(self, camera_id: int, jet_emulator: JetEmulator = None, fps: float = 30):
        super().__init__()
        if jet_emulator is None:
            self.jet_emulator = JetEmulator()
        else:
            self.jet_emulator = jet_emulator

        if camera_id in [1, 2]:
            self.id = camera_id
        else:
            raise ValueError(f'Camera id muss 1 oder 2 sein und nicht "{camera_id}"')

        self.mode = 'single'
        self.stream_on = False
        self.fps = fps

    def is_streaming(self) -> bool:

        if self.mode == "stream":
            return True
        else:
            return False

    def get_resolution(self) -> (int, int):
        return 2048, 1088

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
        self.mode = 'stream'

    def _stream(self):
        while self.stream_on:
            self.new_frame_event(self.get_frame())
            sleep(1/self.fps)

    def stop_stream(self):
        self.stream_on = False
        self.mode = 'single'

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
    camera2.jet_emulator.jet_x.go_to(5000, 'displ', wait=True)
    camera2.jet_emulator.jet_x.go_to(-2000, 'displ', wait=True)
    sleep(1)
    camera2.jet_emulator.laser_on = True
    camera2.jet_emulator.exposure = 10000
    sleep(1)
    camera2.jet_emulator.jet_x.go_to(-1000, 'displ', wait=True)
    camera2.jet_emulator.jet_x.go_to(1000, 'displ', wait=True)
    camera2.jet_emulator.jet_x.go_to(-1000, 'displ', wait=True)
    camera2.jet_emulator.jet_x.go_to(1000, 'displ', wait=True)
    camera2.jet_emulator.jet_x.set_parameter('Lauffrequenz', 100)
    camera2.jet_emulator.jet_x.go_to(-500, 'displ', wait=True)
    camera2.jet_emulator.jet_x.set_parameter('Lauffrequenz', 20)
    camera2.jet_emulator.jet_x.go_to(0, 'displ', wait=True)
    sleep(1)

    # camera1.jet_emulator.jet_x.go_to(1, 'displ', wait=True)
    camera2.stop_video_record()
    camera2.stop_stream()