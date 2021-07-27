import logging
import threading
from copy import deepcopy
from math import pi, cos, sin, isclose
from statistics import mean, pstdev
from time import sleep
from typing import List, Callable, Optional, Set, Tuple, Union
from lmfit import models
# import matplotlib.pyplot as plt

import numpy as np
import cv2
from motor_controller import Motor, Box, MotorsCluster
from motor_controller.interface import MotorError

from mscontr.microwatcher.camera_interface import CameraInterf
# import matplotlib

# from mscontr.microwatcher.plasma_camera_emulator import JetEmulator, CameraEmulator


def find_ray(frame: np.ndarray, error_raise: bool = False) -> Optional[float]:
    """Bestimmt die Position des Stickstoffstrahls auf dem Frame."""
    frame0 = deepcopy(frame)
    frame = ~frame
    gray = frame
    # kernel_size = 5
    # gray = cv2.GaussianBlur(gray,(kernel_size, kernel_size),0)
    low_threshold = 50
    high_threshold = 100
    edges = cv2.Canny(gray, low_threshold, high_threshold, apertureSize = 3)

    rho = 1  # distance resolution in pixels of the Hough grid
    theta = np.pi / 180  # angular resolution in radians of the Hough grid
    threshold = 15  # minimum number of votes (intersections in Hough grid cell)
    min_line_length = 500  # minimum number of pixels making up a line
    max_line_gap = 100  # maximum gap in pixels between connectable line segments

    lines = cv2.HoughLinesP(edges, rho, theta, threshold, np.array([]),
                        min_line_length, max_line_gap)[:, 0, :]

    lines = merge_close_lines(lines)

    if lines is None or lines == []:
        if error_raise:
            raise NoJetError("Es wurde kein Jet-Strahl gefunden!")
        else:
            return None
    elif len(lines) != 2:
        print(lines)
        cv2.imwrite('/Users/prouser/Dropbox/Proging/Python_Projects/MicroscopeController/experiments/jet_error.png', frame0)
        cv2.imwrite('/Users/prouser/Dropbox/Proging/Python_Projects/MicroscopeController/experiments/jet_error_mask.png',
                    edges)

        cv2.imshow('image', frame0)
        cv2.waitKey(0)
        # cv2.imshow('image', gray)
        # cv2.waitKey(0)
        cv2.imshow('image', edges)
        cv2.waitKey(0)
        raise RecognitionError(f"Kein Stickstoffstrahl erkannt. {len(lines)} Linien wurde erkannt.")

    x = []
    for line in lines:
        x1, y1, x2, y2 = line
        if abs(x1-x2) > 4:
            raise RecognitionError(f"Kein Stickstoffstrahl gefunden. Die erkannte Linien sind nicht vertikal.")
        x.append(x1)
        x.append(x2)

    # cv2.imshow('image', frame0)
    # cv2.waitKey(0)
    # # cv2.imshow('image', gray)
    # # cv2.waitKey(0)
    # cv2.imshow('image', edges)
    # cv2.waitKey(0)
    return mean(x)


def merge_close_lines(lines: np.ndarray) -> np.ndarray:
    """Vereint die erkante Geraden, die nebeneinander liegen."""
    def line_is_close(new_line: np.ndarray, close_lines: np.ndarray) -> bool:
        for line in close_lines:
            if abs(new_line[0] - line[0]) <= 1 and abs(new_line[2] - line[2]) <= 1:
                return True
        return False

    def add_new_line(new_line: np.ndarray, close_lines: np.ndarray) -> np.ndarray:
        close_lines = deepcopy(close_lines)
        for line in close_lines:
            if abs(new_line[0] - line[0]) <= 0.0001 and abs(new_line[2] - line[2]) <= 0.0001:
                line[1] = min(line[1], new_line[1])
                line[3] = max(line[3], new_line[3])
                return close_lines
        return np.append(close_lines, [new_line], axis=0)

    def merge_lines(lines: np.ndarray) -> np.ndarray:
        line = np.zeros(4)
        line[0] = np.mean(lines[:, 0])
        line[1] = max(lines[:, 1])
        line[2] = np.mean(lines[:, 2])
        line[3] = min(lines[:, 3])
        return line

    def merge_groups(group1: np.ndarray, group2: np.ndarray) -> np.ndarray:
        res_group = np.concatenate((group1, group2), axis=0)
        res_group = np.unique(res_group, axis=0)
        return res_group

    def have_repeated_elements(group1: np.ndarray, group2: np.ndarray) -> bool:
        sum = np.concatenate((group1, group2), axis=0)
        if len(np.unique(sum, axis=0)) < len(sum):
            return True
        else:
            return False

    def check_and_merge(lines_groups: List[np.ndarray]) -> List[np.ndarray]:
        for i, group in enumerate(lines_groups):
            for j, group2 in enumerate(lines_groups[i+1:]):
                if have_repeated_elements(group, group2):
                    lines_groups[i] = merge_groups(group, group2)
                    lines_groups.pop(i+j+1)
                    return check_and_merge(lines_groups)
        return lines_groups

    # sammeln die nebeneinander liegende Geraden in Gruppen
    lines_groups = [lines[:1], ]
    for line in lines[1:]:
        added = False
        for i, group in enumerate(lines_groups):
            if line_is_close(line, group):
                lines_groups[i] = add_new_line(line, group)
                added = True
        if not added:
            lines_groups.append(np.array([line, ]))

    # prüfen, ob die bekommene Gruppen nebeneinander liegen, und vereinen wenn solche vorhanden sind.
    lines_groups = check_and_merge(lines_groups)

    # vereinigen die nebeneinander liegende Geraden
    res_lines = []
    for group in lines_groups:
        res_lines.append(merge_lines(group))

    return np.array(res_lines)


def find_plasma(frame: np.ndarray, HG: int = 240, error_raise: bool = False) \
        -> Union[Tuple[float, float, float], Tuple[None, None, None]]:
    """Bestimmt die Position der Plasmakugel auf dem Frame."""

    gray = frame
    # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # cv2.imshow('image', gray)
    # cv2.waitKey(0)
    thresh = cv2.threshold(gray, HG, 255, cv2.THRESH_BINARY)[1]
    # cv2.imshow('image', thresh)
    # cv2.waitKey(0)
    thresh = cv2.erode(thresh, None, iterations=2)
    # cv2.imshow('image', thresh)
    # cv2.waitKey(0)
    thresh = cv2.dilate(thresh, None, iterations=4)
    # cv2.imshow('image', thresh)
    # cv2.waitKey(0)

    conts, h = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    if len(conts) > 1:
        raise RecognitionError("Mehrere Objekte gefunden!")
    elif conts is None or conts == []:
        if error_raise:
            raise NoPlasmaError("Es wurde kein Plasmakugel gefunden!")
        else:
            return None, None, None

    (x, y), r = cv2.minEnclosingCircle(conts[0])

    return x, y, r


def draw_circle(frame, x: float, y: float, r: float, center: bool = False) -> np.ndarray:
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    cv2.circle(frame, (round(x), round(y))
               , round(r), (0, 255, 0), 1)
    cv2.circle(frame, (round(x), round(y))
               , 0, (0, 0, 255), 1)
    return frame


def draw_ray(frame, x: float):
    x = round(x)
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    cv2.line(frame, (x, 0), (x, 1088), (0, 255, 0), 1)
    return frame


def fit_the_data(x: np.ndarray, y: np.ndarray, model: str = 'linear', n_sigma: float = 3, plot: bool = False) \
        -> (np.ndarray, np.ndarray):
    if model == 'linear':
        mod = models.LinearModel()  # definiert das Modell (zB: models.LorentzianModel, models.linear,...)
    elif model == 'quadr':
        mod = models.QuadraticModel()
    elif model == 'gauss':
        mod = models.GaussianModel()
    else:
        raise ValueError(f'Unbekanntes Model: "{model}". Probieren Sie "linear" oder "quadr"')

    pars = mod.guess(y, x=x)  # hier werden die Startparameter geschätzt
    out = mod.fit(y, pars, x=x)  # das eigentliche Fitten passiert hier

    if plot:
        fig, gs = out.plot(numpoints=100)
        fig.show()

    if out.covar is not None:
        err = n_sigma*np.sqrt(np.diag(out.covar))
    else:
        err = np.zeros(len(out.best_values))

    return np.array(list(out.best_values.values())), err


def find_plasma_max_from_data(z: np.ndarray, r: np.ndarray) -> float:
    # koef, err = fit_the_data(x, r, 'gauss', plot=True)

    # x = x[r > max(r) * 0.8]
    # r = r[r > max(r)*0.8]

    koef, err = fit_the_data(z, r, 'gauss', plot=True)

    print(koef)
    # maximum = -koef[1]/(2*koef[0])
    # return maximum
    return koef[1]


class CameraCoordinates:
    """Eine Klasse um das Kamera Koordinatensystem ins Mikroskop Koordinatensystem zu transformieren und zurück."""

    def __init__(self, psi: float, jet_x: Motor, jet_z: Motor):
        self.psi = psi
        self.jet_x = jet_x
        self.jet_z = jet_z

    def cc_to_mc(self, x_: float, z_: float) -> (float, float):
        """Transformiert das Kamera Koordinatensystem ins Mikroskop Koordinatensystem."""

        x = x_ * cos(self.psi) + z_ * sin(self.psi)
        z = - x_ * sin(self.psi) + z_ * cos(self.psi)
        return x, z

    def mc_to_cc(self, x: float, z: float) -> (float, float):
        """Transformiert das Mikroskop Koordinatensystem ins Kamera Koordinatensystem."""

        x_ = x * cos(-self.psi) + z * sin(-self.psi)
        z_ = - x * sin(-self.psi) + z * cos(-self.psi)
        return x_, z_

    def move_jet_in_cc(self, shift_x: float, shift_z: float, wait: bool = False):
        """Bewegt den Jet-Strahl in Kamera Koordinatensystem"""

        shift_x, schift_z = self.mc_to_cc(shift_x, shift_z)
        self.jet_x.go(shift_x, 'displ', wait)
        self.jet_z.go(shift_z, 'displ', wait)

    def move_jet_in_cc_to(self, target_x: float, target_z: float, wait: bool = False):
        """Bewegt den Jet-Strahl in Kamera Koordinatensystem"""

        target_x, target_z = self.mc_to_cc(target_x, target_z)
        self.jet_x.go_to(target_x, 'displ', wait)
        self.jet_z.go_to(target_z, 'displ', wait)

    # def motors_position_in_cc(self):


class PlasmaWatcher:

    def __init__(self, camera1: CameraInterf, camera2: CameraInterf,
                 jet_x: Motor, jet_z: Motor, laser_z: Motor, laser_y: Motor,
                 phi: float, psi: float,
                 tol_pixel: float = 1):
        self.camera1 = camera1
        self.camera2 = camera2

        jet_z.name = 'JetZ'
        jet_x.name = 'JetX'
        laser_z.name = 'LaserZ'
        laser_y.name = 'LaserY'

        self.jet_z = jet_z
        self.jet_x = jet_x
        self.laser_z = laser_z
        self.laser_y = laser_y
        self.motors_cl = MotorsCluster([jet_z, jet_x, laser_z, laser_y])

        self.g1 = 1  #Vergröserung der ersten Kamera
        self.g2 = 1  #Vergröserung der zweiten Kamera
        self._phi = pi*phi/180  #Winkel zwischen den Kameras
        self._psi = pi * psi / 180  # Winkel zwischen den Kamera1 und X-Achse
        self.tol_pixel = tol_pixel  # Akzeptable Abweichung der Messungen in pixel

        self.camera1_coord = CameraCoordinates(self._psi, jet_x, jet_z)
        self.camera2_coord = CameraCoordinates(self._phi + self._psi, jet_x, jet_z)

        self.res_x, self.res_y = self.camera1.get_resolution()
        if (self.res_x, self.res_y) != self.camera2.get_resolution():
            raise EquipmentError("Auflösungen der Kameras sind nicht gleich!")

        self._laser_on = False
        self.l_on_exposure = 10000
        self.l_off_exposure = 40000

        self._j_x1 = 0
        self._j_x2 = 0
        self._pl_y1 = 0
        self._pl_y2 = 0
        self._pl_r1 = 0
        self._pl_r2 = 0

        self.jett_laser_dz = 0
        self.pl_r_max = 0

        self._frame1_is_new = True
        self._frame2_is_new = True

        self.plasma_holder = PlasmaHolder(self, freq=1/3, brightness_tol=0.1)
        self._hold_plasma_is_on = False
        self.dont_move = False  # ein Marker um automatische bewegungen wehrend der Messung zu verbitten

        self.camera1.connect_to_stream(self._new_frame1_event)
        self.camera2.connect_to_stream(self._new_frame2_event)

        self.displ_units = self.jet_z.config['display_units']

    def laser_on_mode(self):
        """Passt die einstellungen für die eingeschaltete Laser an."""

        self.camera1.set_exposure(self.l_on_exposure)
        self.camera2.set_exposure(self.l_on_exposure)
        self._laser_on = True

    def laser_off_mode(self):
        """Passt die einstellungen für die ausgeschaltete Laser an."""

        self.camera1.set_exposure(self.l_off_exposure)
        self.camera2.set_exposure(self.l_off_exposure)
        self._laser_on = False

    def phi(self):
        """Gibt den Winkel zwischen den Kameras in Grad zurück"""
        return 180*self._phi/pi

    def set_phi(self, value):
        """Ändert den Wert des Winkels zwischen den Kameras mit angegebenen Wert in Grad zurück"""
        self._phi = pi*value/180

    def psi(self):
        """Gibt den Winkel zwischen den Kamera1 und X-Achse in Grad zurück"""
        return 180*self._psi/pi

    def set_psi(self, value):
        """Ändert den Wert des Winkels zwischen den Kamera1 und X-Achse mit angegebenen Wert in Grad zurück"""
        self._psi = pi*value/180

    def tol(self) -> float:
        """gibt die akzeptable Abweichung der Messungen in mym zurück"""
        return max(self.g1, self.g2)*self.tol_pixel

    def _new_frame1_event(self, frame: np.ndarray):
        self._frame1_is_new = True

    def _new_frame2_event(self, frame: np.ndarray):
        self._frame2_is_new = True

    def _get_j_x1(self, error_raise: bool = False) -> float:
        """Gibt Jet-Position auf der ersten Kamera in Pixel zurück"""

        if self.camera1.mode == 'stream' and not self._frame1_is_new:
            pass
        else:
            frame1 = self.camera1.get_frame()
            self._frame1_is_new = False
            self._j_x1 = find_ray(frame1, error_raise)
        return self._j_x1

    def _get_j_x2(self, error_raise: bool = False) -> float:
        """Gibt Jet-Position auf der zweiten Kamera in Pixel zurück"""

        if self.camera2.mode == 'stream' and not self._frame2_is_new:
            pass
        else:
            frame2 = self.camera2.get_frame()
            self._frame2_is_new = False
            self._j_x2 = find_ray(frame2, error_raise)
        return self._j_x2

    def _find_plasma1(self, error_raise: bool = False) -> (float, float, float):
        """Gibt die Plasma-Position und den Radius (x, z, r) auf der ersten Kamera in Pixel zurück"""

        if self.camera1.mode == 'stream' and not self._frame1_is_new:
            pass
        else:
            frame1 = self.camera1.get_frame()
            self._frame1_is_new = False
            self._pl_x1, self._pl_y1, self._pl_r1 = find_plasma(frame1, error_raise=error_raise)
        return self._pl_x1, self._pl_y1, self._pl_r1

    def _find_plasma2(self, error_raise: bool = False) -> (float, float, float):
        """Gibt die Plasma-Position und den Radius (x, z, r) auf der zweiten Kamera in Pixel zurück"""

        if self.camera2.mode == 'stream' and not self._frame2_is_new:
            pass
        else:
            frame2 = self.camera2.get_frame()
            self._frame2_is_new = False
            self._pl_x2, self._pl_y2, self._pl_r2 = find_plasma(frame2, error_raise=error_raise)
        return self._pl_x2, self._pl_y2, self._pl_r2

    def get_jet_position(self, error_raise: bool = False) -> Optional[Tuple[float, float]]:
        """Gibt Jet-Position in Raum (x, y) zurück."""

        x1_p = self._get_j_x1(error_raise)
        x2_p = self._get_j_x2(error_raise)
        if x1_p is None or x2_p is None:
            return None

        x1 = self.g1*(x1_p - self.res_x/2)
        x2 = self.g2*(x2_p - self.res_x/2)

        x_ = (x1 * cos(self._phi) - x2) / sin(self._phi)
        z_ = x1

        x, z = self.camera1_coord.cc_to_mc(x_, z_)

        return x, z

    def find_plasma(self, error_raise: bool = False) \
            -> Union[Tuple[float, float, float, float], Tuple[None, None, None, None]]:
        """Gibt die Plasma-Position in Raum und den Radius (x, y, z, r) zurück."""

        x1, y1, r1 = self._find_plasma1(error_raise)
        x2, y2, r2 = self._find_plasma2(error_raise)
        if x1 is None or x2 is None:
            return None, None, None, None

        x1 = self.g1*(x1 - self.res_x/2)
        y1 = self.g1*(-y1 + self.res_y/2)
        r1 *= self.g1

        x2 = self.g2*(x2 - self.res_x/2)

        x_ = (x1*cos(self._phi) - x2)/sin(self._phi)
        z_ = x1

        x, z = self.camera1_coord.cc_to_mc(x_, z_)
        y = y1
        r = r1

        return x, y, z, r

    def get_plasma_position(self, error_raise: bool = False) \
            -> Union[Tuple[float, float, float], Tuple[None, None, None]]:
        """Gibt die Plasma-Position in Raum (x, y, z) zurück."""

        x, y, z, r = self.find_plasma(error_raise)
        return x, y, z

    def j_x(self, error_raise: bool = False) -> Optional[float]:
        """Gibt x-Koordinate von der Jet-Position in Raum zurück."""

        pos = self.get_jet_position(error_raise)
        if pos is None:
            return None
        else:
            return pos[0]

    def j_z(self, error_raise: bool = False) -> Optional[float]:
        """Gibt z-Koordinate von der Jet-Position in Raum zurück."""

        pos = self.get_jet_position(error_raise)
        if pos is None:
            return None
        else:
            return pos[1]

    def move_jet(self, shift_x: float, shift_z: float, units: str = 'displ', wait: bool = False):
        """Bewegt Jet-Strahl zu den angegebenen Verschiebungen."""

        self.motors_cl.go({'JetX': shift_x, 'JetZ': shift_z}, units=units, wait=wait)

    def move_jet_to(self, target_x: Optional[float], target_z: Optional[float], wait: bool = False):
        """Bewegt Jet-Strahl zur absoluten Position, die als target gegeben wird. Wenn als target None gegeben ist,
        wird diese Achse nicht bewegt."""

        j_pos = self.get_jet_position(error_raise=True)
        if j_pos is None:
            raise NoJetError("Die Verschiebung kann nicht gerechnet werden, da kein Jet-Strahl gefunden wurde.")
        x, z = j_pos

        if target_x is not None:
            shift_x = target_x - x
        else:
            shift_x = 0

        if target_z is not None:
            shift_z = target_z - z
        else:
            shift_z = 0
        self.move_jet(shift_x, shift_z, units='displ', wait=wait)

    def calibrate_enl(self, init_step: float = 1000, rel_err: float = 0.01, n_points: int = 10) -> str:
        """Führt eine Messung von den Vergröserungkoeffizienten g1 und g2 und speichert die Werte."""

        def measure_run(m_targets: np.ndarray, camera_coord: CameraCoordinates, get_jet_x: Callable) \
                -> (np.ndarray, np.ndarray):
            x_array_pixel = []
            x_array_displ = []

            for m_target in m_targets:
                target_x, target_z = camera_coord.cc_to_mc(0, m_target)
                self.move_jet_to(target_x, target_z, wait=True)
                x_array_pixel.append(get_jet_x(error_raise=True))

                jet_x_pos, jet_z_pos = self.jet_x.position('displ'), self.jet_z.position('displ')
                x_projection = camera_coord.mc_to_cc(jet_x_pos, jet_z_pos)[1]
                x_array_displ.append(x_projection)
            x_array_pixel = np.array(x_array_pixel) - self.res_x / 2
            x_array_displ = np.array(x_array_displ)
            return x_array_pixel, x_array_displ

        # zum Mittelpunkt gehen
        self.jet_x.go_to(500, units='norm', wait=True)
        self.jet_z.go_to(500, units='norm', wait=True)

        # g1 und g2 grob abschätzen
        x1_0_pixel = self._get_j_x1(error_raise=True)
        x2_0_pixel = self._get_j_x2(error_raise=True)
        jet_z_0_pos = self.jet_z.position('displ')

        while abs(x1_0_pixel - self._get_j_x1(error_raise=True)) < self.res_x/8:
            self.jet_z.go(-init_step, units='displ', wait=True)
        self.jet_z.go(self.jet_z.position('displ') - jet_z_0_pos, units='displ', wait=True)

        delta_z_displ = self.jet_z.position('displ') - jet_z_0_pos
        self.g1 = self.camera1_coord.mc_to_cc(0, delta_z_displ)[1] / (self._get_j_x1(error_raise=True) - x1_0_pixel)
        self.g2 = self.camera2_coord.mc_to_cc(0, delta_z_displ)[1] / (self._get_j_x2(error_raise=True) - x2_0_pixel)

        # Messungen durchführen
        m_targets = np.linspace(-3/8, 3/8, n_points) * self.res_x
        x1_array_pixel, x1_array_displ = measure_run(m_targets * self.g1, self.camera1_coord, self._get_j_x1)
        x2_array_pixel, x2_array_displ = measure_run(m_targets * self.g2, self.camera2_coord, self._get_j_x2)

        # Messungen auswerten

        koef1, err1 = fit_the_data(x1_array_pixel, x1_array_displ, 'linear', plot=False)
        koef2, err2 = fit_the_data(x2_array_pixel, x2_array_displ, 'linear', plot=False)

        if err1[0]/koef1[0] > rel_err or err2[0]/koef2[0] > rel_err:
            raise FitError(f'Der relative Fehler ist zu groß, '
                           f'die Auswertung scheint nicht repräsentativ zu sein.')

        self.g1 = koef1[0]
        self.g2 = koef2[0]

        report = f'Koeffizienten ({self.displ_units}/pixel):\n' \
                 f'g1 = {koef1[0]} +- {err1[0]}\n' \
                 f'g2 = {koef2[0]} +- {err2[0]}\n' \
                 f'Abweichung der Cameras vor Zentralposition ({self.displ_units}):\n' \
                 f'Kamera1: {koef1[1]} +- {err1[1]}\n' \
                 f'Kamera2: {koef2[1]} +- {err2[1]}\n'
        return report

    def calibrate_plasma(self, ray_d: float = 70, s_range: float = 500, max_s_range: float = 10000,
                         fine_step: float = 7, on_the_spot: bool = False, mess_per_point: int = 1,
                         time_per_point: float = 0,
                         brightness_decr: float = 0.10, keep_position: bool = False):


        def jet_z_move_with_check(value: float, mode: str = 'go'):
            if mode == 'go':
                done, message = self.jet_z.go(value, units='displ', wait=True, check=True)
            elif mode == 'go_to':
                done, message = self.jet_z.go_to(value, units='displ', wait=True, check=True)
            else:
                raise ValueError()

            if not done:
                raise MotorError("Der Motor bewegt sich nicht zum Ziel! "
                                 "Die Kalibrierung kann nicht abgeschlossen werden.")

        def plasma_search(on_the_spot: bool):
            start0 = 0
            if not on_the_spot:
                self.motors_cl.go_to({'JetX': 0, 'JetZ': 0, 'LaserZ': 0, 'LaserY': 0}, 'displ', wait=True)
            else:
                start0 = self.jet_z.position('displ')

            step = 2 * ray_d / 4
            i = 0
            stop_search = False
            while True:
                start = i * s_range + start0
                points = np.concatenate((np.arange(start, start + s_range, step),
                                         np.flipud(np.arange(-start - s_range, -start, step))))
                for point in points:
                    self.jet_z.go_to(point, units='displ', wait=True)
                    for _ in range(3):
                        r = self.find_plasma()[3]
                        if r is None:
                            break
                        sleep(time_per_point / mess_per_point)
                    if r is not None:
                        stop_search = True
                        start_point = point
                        break
                if stop_search:
                    break
                i += 1
                if i * s_range > max_s_range:
                    raise NoPlasmaError('Es ist kein Plasma gefunden innerhalb des angegebenen Suchbereichs.'
                                        'Die Kalibrierung kann nicht abgeschlossen werden.')
            return start_point

        def measure_point(repeats: int) -> (float, float, float):
            position = self.jet_z.position('displ')
            pl_r_values = []
            for _ in range(repeats):
                r = self.find_plasma()[3]
                if r is not None:
                    pl_r_values.append(r)

            if len(pl_r_values) >= 3 * mess_per_point / 4:
                r_mean = mean(pl_r_values)
                r_sigma = pstdev(pl_r_values)
            else:
                r_mean = None
                r_sigma = None

            return position, r_mean, r_sigma

        # --------------start--------------------

        if keep_position:
            plasma_position = self.get_plasma_position(error_raise=True)

        if fine_step < self.jet_z.tol():
            fine_step = self.jet_z.tol()
            logging.warning('"fine_step" ist kleiner als die Abweichung von den Motoren!'
                            ' Die Abweichung wird als "fine_step" genommen.')

        # erstmal Plasma finden
        start_point = plasma_search(on_the_spot=on_the_spot)

        # die Kurve messen
        step = fine_step
        direction = -1
        r_max = 0
        r_max_sigma = 0
        jet_z_arr = []
        pl_r_arr = []
        stop = False
        # nach links bis zu dunkle Zone bewegen dann zurück zur Startposition und nach rechts bis zu dunkle Zone bewegen
        while True:
            position, r_mean, r_sigma = measure_point(repeats=mess_per_point)

            if r_mean is None:
                if len(pl_r_arr) == 0:
                    start_point = plasma_search(on_the_spot=True)
                    continue
                else:
                    for _ in range(2):
                        jet_z_move_with_check(direction * step)
                        position, r_mean, r_sigma = measure_point(repeats=mess_per_point)
                        if r_mean is not None:
                            break
                    stop = True

            if not stop:
                if r_mean < r_max - max(r_max * brightness_decr, 3 * r_max_sigma):
                    r_values = [r_mean, ]
                    stop = True
                    for _ in range(2):
                        position, r_mean, r_sigma = measure_point(repeats=mess_per_point)
                        if r_mean is None:
                            pass
                        elif not r_mean < r_max - max(r_max * brightness_decr, 3 * r_max_sigma):
                            stop = False
                            break
                        else:
                            r_values.append(r_mean)
                    r_mean = mean(r_values)

            if r_mean is not None:
                jet_z_arr.append(position)
                pl_r_arr.append(r_mean)
                if r_mean > r_max:
                    r_max = r_mean
                    r_max_sigma = r_sigma

            if stop:
                if direction == 1:
                    break

                jet_z_arr.reverse()
                pl_r_arr.reverse()
                # wenn der Start nicht in der dunklen Zone ist, dann zurück zur Startposition und die Richtung wechseln
                if not pl_r_arr[-1] < r_max - max(r_max * brightness_decr, 3 * r_max_sigma):
                    jet_z_move_with_check(start_point, 'go_to')
                    direction = 1
                stop = False

            jet_z_move_with_check(direction * step)

        jet_z_arr = np.array(jet_z_arr)
        pl_r_arr = np.array(pl_r_arr)

        # die Kurve auswerten
        max_position = find_plasma_max_from_data(jet_z_arr, pl_r_arr)
        print(max_position, len(jet_z_arr))

        # in die optimale Position fahren
        self.jet_z.go_to(max_position, 'displ', wait=True)

        # alle nötige Daten speichern
        self.pl_r_max = self.find_plasma()[3]
        self.jett_laser_dz = self.jet_z.position('displ') - self.laser_z.position('displ')

        # plasma Zurück verschieben, wenn nötig
        if keep_position:
            self.move_plasma_to(*plasma_position, wait=True, br_control=False)

    def compensate_motor_error(self):
        """Prüfen, ob der Abstand zwischen Jet- und Laserstrahl sich geändert hat, und korrigieren."""

        if abs(self.laser_z.position('displ') - self.jet_z.position('displ') - self.jett_laser_dz) > self.laser_z.tol():
            plasma_position = self.get_plasma_position(error_raise=True)
            self.jet_z.go_to(self.laser_z.position('displ') + self.jett_laser_dz, 'displ', wait=True)
            self.move_plasma_to(*plasma_position, wait=True, br_control=False)

    # def check_plasma_brightness(self, keep_position: bool = True, calibrate: bool = True, actions: List[Callable] = [])\
    #         -> bool:
    #     """Helligkeit vom Plasma prüfen und erneut kalibrieren, wenn es dunkler geworden ist."""
    #
    #     r = self.find_plasma()[3]
    #     print(r, self.pl_r_max*(1 - self.brightness_tol))
    #     if r is None:
    #         if calibrate:
    #             self.calibrate_plasma(keep_position=False, on_the_spot=True, fine_step=0,
    #                                   mess_per_point=4, brightness_decr=0)
    #         return False
    #     elif r < self.pl_r_max*(1 - self.brightness_tol):
    #         if calibrate:
    #             self.calibrate_plasma(keep_position=keep_position, on_the_spot=True, fine_step=0,
    #                                   mess_per_point=4, brightness_decr=0)
    #         return False
    #     else:
    #         return True

    def hold_plasma(self):

        self.plasma_holder.position = self.get_plasma_position(error_raise=True)
        self.plasma_holder.start()

    def stop_hold_plasma(self):
        self.plasma_holder.stop()

    def move_plasma(self, shift_x: float, shift_y: float, shift_z: float, units: str = 'displ',
                    wait: bool = False, br_control: bool = True):
        """Bewegt Plasma zu den angegebenen Verschiebungen."""

        self.compensate_motor_error()
        if br_control and not wait:
            self.check_plasma_brightness(keep_position=True)

        self.motors_cl.go({'JetX': shift_x, 'JetZ': shift_z, 'LaserX': shift_x, 'LaserY': shift_y},
                          units=units, wait=wait)

        if br_control and wait:
            self.check_plasma_brightness(keep_position=True)

    def move_plasma_to(self, target_x: Optional[float], target_y: Optional[float], target_z: Optional[float],
                       wait: bool = False, br_control: bool = True):
        """Bewegt Plasma zur absoluten Position, die als target gegeben wird. Wenn als target None gegeben ist,
        wird diese Achse nicht bewegt."""

        x, y, z = self.get_plasma_position(error_raise=False)
        if x is None:
            raise NoPlasmaError("Die Verschiebung kann nicht gerechnet werden, da kein Plasma gefunden wurde.")

        if target_x is not None:
            shift_x = target_x - x
        else:
            shift_x = 0

        if target_y is not None:
            shift_y = target_y - y
        else:
            shift_y = 0

        if target_z is not None:
            shift_z = target_z - z
        else:
            shift_z = 0
        self.move_plasma(shift_x, shift_y, shift_z, units='displ', wait=wait, br_control=br_control)


class PlasmaHolder(threading.Thread):
    """Thread-Objekt für PlasmaWatcher, der die Position und Helligkeit des Plasmas aufbewahrt."""

    def __init__(self, pl_watcher: PlasmaWatcher, freq: float = 1 / 3, brightness_tol: float = 0.1):
        super().__init__()
        self.pl_watcher = pl_watcher
        self.freq = freq

        self.brightness_tol = brightness_tol

        self._stop = False

        self.dont_move = False
        self.br_control = False
        self.position_control = False

        self.position: List[float, float, float] = [0, 0, 0]
        self.pl_shift: Tuple[float, float, float] = (0, 0, 0)

        self.actions_by_shift: List[Callable] = []
        self.actions_by_dimming: List[Callable] = []
        self.do_shift_actions_in_run = False
        self.do_dimming_actions_in_run = False

        self._brightness = 1

    def stop(self):
        self._stop = True

    def is_running(self):
        return self.is_alive()

    def brightness(self):
        return self._brightness

    def start(self, do_shift_actions: bool = True, do_dimming_actions: bool = True):
        self._stop = False
        self.do_shift_actions_in_run = do_shift_actions
        self.do_dimming_actions_in_run = do_dimming_actions
        super().start()

    def run(self):
        while not self._stop:

            self._check(brightness=True,
                        calibrate=True,
                        do_dimming_actions=self.do_dimming_actions_in_run,
                        position=self.position_control,
                        do_shift_actions=self.do_shift_actions_in_run)

            sleep(1 / self.freq)

    def _check(self, position: bool = False, brightness: bool = False, brightness_tol: Optional[float] = None,
               calibrate: bool = False, keep_position_by_cal: bool = False, do_shift_actions: bool = False,
               do_dimming_actions: bool = False, move_by_shift: bool = False) -> (Optional[bool], Optional[bool]):

        x, y, z, r = self.pl_watcher.find_plasma(error_raise=not brightness)
        brightness_is_ok = None
        position_is_ok = None

        if brightness_tol is None:
            brightness_tol = self.brightness_tol

        # check brightness
        if brightness:
            if r is None:
                if do_dimming_actions:
                    self._do_actions_by_dimming()
                if calibrate and not self.dont_move:
                    self.pl_watcher.calibrate_plasma(keep_position=False, on_the_spot=True, fine_step=0,
                                          mess_per_point=4, brightness_decr=0)
                brightness_is_ok = False
            elif r < self.pl_watcher.pl_r_max*(1 - self.brightness_tol):
                if do_dimming_actions:
                    self._do_actions_by_dimming()
                if calibrate and not self.dont_move:
                    self.pl_watcher.calibrate_plasma(keep_position=keep_position_by_cal, on_the_spot=True, fine_step=0,
                                          mess_per_point=4, brightness_decr=0)
                brightness_is_ok = False
            else:
                brightness_is_ok = True

        # check position
        if position:
            x0, y0, z0 = self.position
            self.pl_shift = (x - x0, y - y0, z - z0)

            if not np.all(np.array(self.pl_shift) < self.pl_watcher.jet_x.tol()):
                if do_shift_actions:
                    self._do_actions_by_shift()
                if not self.dont_move and move_by_shift:
                    self.pl_watcher.move_plasma_to(*self.position, wait=True, br_control=False)
                position_is_ok = False
            else:
                position_is_ok = True

        return brightness_is_ok, position_is_ok

    def check_brightness(self, keep_position: bool = False, calibrate: bool = False, do_actions: bool = False,
                         brightness_tol: Optional[float] = None) -> bool:
        """Helligkeit vom Plasma prüfen und erneut kalibrieren, wenn es dunkler geworden ist."""

        return self._check(brightness=True, brightness_tol=brightness_tol, calibrate=calibrate,
                           keep_position_by_cal=keep_position, do_dimming_actions=do_actions)[0]

    def check_position(self, dont_move: bool = False, do_actions: bool = False) -> bool:
        """Position vom Plasma prüfen und zurückbewegen, wenn es verschoben ist."""

        return self._check(position=True, do_shift_actions=do_actions, move_by_shift=not dont_move)[1]

    def complete_check(self, calibrate: bool = True,
                       keep_position_by_cal: bool = False,
                       do_dimming_actions: bool = True,
                       do_shift_actions: bool = True,
                       brightness_tol: Optional[float] = None,
                       move_by_shift: bool = True) -> (bool, bool):

        return self._check(brightness=True, brightness_tol=brightness_tol, calibrate=calibrate,
                           keep_position_by_cal=keep_position_by_cal, do_dimming_actions=do_dimming_actions,
                           position=True, do_shift_actions=do_shift_actions, move_by_shift=move_by_shift)

    def _do_actions_by_shift(self):
        for action in self.actions_by_shift:
            action()

    def _do_actions_by_dimming(self):
        for action in self.actions_by_dimming:
            action()


def PlasmaWatcher_BoxInput(camera1: CameraInterf, camera2: CameraInterf,
                           box: Box, phi: float, psi: float, tol_pixel: float = 1) -> PlasmaWatcher:
    jet_x = box.get_motor_by_name('JetX')
    jet_z = box.get_motor_by_name('JetZ')
    laser_z = box.get_motor_by_name('LaserZ')
    laser_y = box.get_motor_by_name('LaserY')
    return PlasmaWatcher(camera1, camera2, jet_x, jet_z, laser_z, laser_y, phi, psi, tol_pixel)


class RecognitionError(Exception):
    """Fehler bei Erkennug der Objekten auf einem Frame"""


class NoJetError(Exception):
    """Fehler, wenn ein Jet-Strahl benötigt, ist aber kein gufunden."""


class NoPlasmaError(Exception):
    """Fehler, wenn ein Plasmakugel benötigt, ist aber kein gufunden."""


class FitError(Exception):
    """Fehler bei Erkennug der Objekten auf einem Frame"""


class EquipmentError(Exception):
    """Fehler mit dem Aufbau"""


if __name__ == "__main__":
    img = cv2.imread('/Users/prouser/Dropbox/Proging/Python_Projects/MicroscopeController/tests/test_data/img_real.jpg', 0)
    x, z, r = find_plasma(img)
    # img = draw_circle(img, x, z, r)
    img = draw_ray(img, x)
    cv2.imshow('image', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()