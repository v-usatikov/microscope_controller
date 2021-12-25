import time
from copy import deepcopy
from math import pi
from unittest import TestCase
import numpy as np
import cv2

# from MicroWatcher.PlasmaWatcher import find_ray
# from MicroWatcher.camera_emulator import make_ray_photo

from mscontr.microwatcher.plasma_camera_emulator import paint_circle, paint_line, JetEmulator, CameraEmulator, \
    paint_nozzle
from mscontr.microwatcher.plasma_watcher import find_ray, find_plasma, draw_circle, PlasmaWatcher, \
    PlasmaWatcher_BoxInput, NoPlasmaError, merge_close_lines, CameraCoordinates, show, find_nozzle


def prepare_jet_watcher_to_test(phi = 90, psi = 45, g1 = 10, g2 = 10, shift = 43, laser_on = True, jet_cal = True,
                                pl_cal = True):
    jet_emulator = JetEmulator(phi=phi, psi=psi, g1=g1, g2=g2, jet_d=g1 * 7, laser_jet_shift=shift)
    camera1 = CameraEmulator(1, jet_emulator)
    camera2 = CameraEmulator(2, jet_emulator)
    plasma_watcher = PlasmaWatcher_BoxInput(camera1, camera2, jet_emulator.box, phi=phi, psi=psi)
    if jet_cal:
        plasma_watcher.g1 = g1
        plasma_watcher.g2 = g2
    if laser_on:
        jet_emulator.laser_on = True
        plasma_watcher.laser_on_mode()
    if pl_cal and laser_on:
        plasma_watcher.jett_laser_dz = jet_emulator.laser_jet_shift
        plasma_watcher.pl_r_max = plasma_watcher.find_plasma()[3]
        plasma_watcher.compensate_motor_error()
    return plasma_watcher, jet_emulator, camera1, camera2


class TestExternalFunctions(TestCase):
    # def test_find_ray(self):
    #     frame = cv2.imread('test_data/img_test2.bmp')
    #     self.assertAlmostEqual(612, find_ray(frame), delta=2)

    def test_paint_circle(self):
        img = np.zeros((1088, 2048), dtype='uint8')
        paint_circle(img, x=-500, y=-100, radius=20)

        # cv2.imshow('image', img)
        # cv2.waitKey(0)

    def test_paint_line(self):
        img = 255*np.ones((1088, 2048), dtype='uint8')
        paint_line(img, -200, 7, 0.3)

        # cv2.imshow('image', img)
        # cv2.waitKey(0)

    def test_find_ray(self):
        bg0 = cv2.imread('test_data/hintg.bmp', 0)
        bg0[:, :] = bg0[:, :] * 0.1
        points = np.linspace(-1000, 1000, 10)
        for x in points:
            bg = deepcopy(bg0)
            # show(bg)
            paint_line(bg, x, 7)
            # show(bg)
            self.assertAlmostEqual(find_ray(bg)-2048/2, x, delta=0.6)

    def test_find_nozzle(self):
        bg0 = cv2.imread('test_data/hintg.bmp', 0)
        nozzle = cv2.imread('test_data/nozzle.bmp', 0)
        bg0[:, :] = bg0[:, :] * 0.1
        points = np.linspace(-800, 800, 10)
        for x in points:
            bg = deepcopy(bg0)
            # show(bg)
            paint_nozzle(bg, nozzle, x)
            # show(bg)
            self.assertAlmostEqual(find_nozzle(bg)[0]-2048/2, x, delta=3)

    def test_find_plasma(self):
        bg0 = cv2.imread('test_data/hintg.bmp', 0)
        bg0[:, :] = bg0[:, :] * 0.25
        points_x = np.linspace(-1000, 1000, 10)
        points_z = np.linspace(-500, 500, 10)

        self.assertEqual((None, None, None), find_plasma(bg0))
        with self.assertRaises(NoPlasmaError):
            find_plasma(bg0, error_raise=True)

        for x in points_x:
            bg = deepcopy(bg0)
            paint_line(bg, x, 7)
            for z in points_z:
                bg2 = deepcopy(bg)
                paint_circle(bg2, x, z, 7)

                x_, z_, r = find_plasma(bg2, error_raise=True)

                self.assertAlmostEqual(x_-2048/2, x, delta=1)
                self.assertAlmostEqual(-z_ + 1088 / 2, z, delta=1)

    def test_merge_close_lines(self):
        lines = np.array([[1075, 1087, 1075, 0],
                          [1070, 1087, 1070, 144],
                          [1069, 1086, 1069, 0],
                          [800, 1000, 800, 0],
                          [1200, 1000, 1200, 500],
                          [1203, 600, 1203, 50],
                          [1201, 1500, 1201, 800],
                          [1202, 1500, 1202, 800]
                          ])

        res = np.array([[1075, 1087, 1075, 0],
                        [1069.5, 1087, 1069.5, 0],
                        [800, 1000, 800, 0],
                        [1201.5, 1500, 1201.5, 50]])

        # self.assertEqual(res.tolist(), merge_close_lines(lines).tolist())
        np.testing.assert_almost_equal(merge_close_lines(lines), res)

class TestCameraCoordinates(TestCase):

    def test_1(self):

        camera1_coord = CameraCoordinates(0, None, None)
        camera2_coord = CameraCoordinates(pi/2, None, None)

        x, z = camera1_coord.cc_to_mc(0, 1)
        self.assertAlmostEqual(0, x)
        self.assertAlmostEqual(1, z)

        x2, z2 = camera2_coord.mc_to_cc(x, z)
        self.assertAlmostEqual(1, x2)
        self.assertAlmostEqual(0, z2)


class TestPlasmaWatcher(TestCase):

    def test_calibrate_enl(self):
        plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(laser_on=False, jet_cal=False)

        # jet_emulator.realtime(True)
        # camera1.start_video_record(start_stream=True, fps=60)
        # try:
        #     report = plasma_watcher.calibrate_enl()
        # finally:
        #     camera1.stop_video_record()
        #     camera1.stop_stream()

        report = plasma_watcher.calibrate_enl(init_step=jet_emulator.g1 * 100, n_points=10)
        print(report)
        self.assertAlmostEqual(jet_emulator.g1, plasma_watcher.g1, delta=0.005)
        self.assertAlmostEqual(jet_emulator.g2, plasma_watcher.g2, delta=0.005)

    def test_move_jet_to(self):
        plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(laser_on=False)
        destinations = np.array([(1230, 4560), (3676.7, 456.5), (-2740.6, 100.5), (-2356.6, -566.8)])

        for point in destinations:
            plasma_watcher.move_jet_to(*point, wait=True)
            np.testing.assert_allclose(np.array(plasma_watcher.get_jet_position()), point, 0, plasma_watcher.tol())

    def test_move_plasma_to(self):
        plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test()
        destinations = np.array([(1230, 4560, 456.6), (3676.7, 456.5, 2567.67), (-2740.6, 100.5, -1726.4),
                                 (-2356.6, -566.8, -345.6)])

        jet_emulator.realtime(True)
        camera1.start_video_record(start_stream=True, fps=60)
        try:
            for point in destinations:
                plasma_watcher.move_plasma_to(*point, wait=True)
                np.testing.assert_allclose(np.array(plasma_watcher.get_plasma_position()), point, 0,
                                           plasma_watcher.tol())
                time.sleep(3)
        finally:
            camera1.stop_video_record()
            camera1.stop_stream()

    def test_calibrate_plasma(self):
        mess_per_point = 5
        plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(pl_cal=False, shift=1500)
        jet_emulator.flicker_sigma = 0.1
        record_video = False
        if record_video:
            jet_emulator.realtime(True)
            camera1.start_video_record(start_stream=True, fps=60)
            try:
                plasma_watcher.calibrate_plasma(mess_per_point=mess_per_point)
            finally:
                camera1.stop_video_record()
                camera1.stop_stream()
        else:
            plasma_watcher.calibrate_plasma(mess_per_point=mess_per_point)
        self.assertAlmostEqual(plasma_watcher.jett_laser_dz, jet_emulator.laser_jet_shift,
                               delta=plasma_watcher.laser_z.tol())

    def test_calibrate_plasma_silent(self):
        mess_per_point = 5
        plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(pl_cal=True, shift=1500)
        jet_emulator.flicker_sigma = 0.03
        record_video = False
        if record_video:
            jet_emulator.realtime(True)
            camera1.start_video_record(start_stream=True, fps=60)
            try:
                plasma_watcher.calibrate_plasma(mess_per_point=mess_per_point, on_the_spot=True,
                                                fine_step=0, brightness_decr=0)
            finally:
                camera1.stop_video_record()
                camera1.stop_stream()
        else:
            plasma_watcher.calibrate_plasma(mess_per_point=mess_per_point, on_the_spot=True,
                                            fine_step=0, brightness_decr=0)
        self.assertAlmostEqual(plasma_watcher.jett_laser_dz, jet_emulator.laser_jet_shift,
                               delta=plasma_watcher.laser_z.tol())

