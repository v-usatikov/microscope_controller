from copy import deepcopy
from unittest import TestCase
import numpy as np
import cv2

# from MicroWatcher.PlasmaWatcher import find_ray
# from MicroWatcher.camera_emulator import make_ray_photo

from mscontr.microwatcher.plasma_camera_emulator import paint_circle, paint_line, JetEmulator, CameraEmulator
from mscontr.microwatcher.plasma_watcher import find_ray, find_plasma, draw_circle, PlasmaWatcher, \
    PlasmaWatcher_BoxInput, NoPlasmaError, merge_close_lines

def prepare_jet_watcher_to_test(phi = 90, psi = 45, g1 = 10, g2 = 10, shift = 43, laser_on = True):
    jet_emulator = JetEmulator(phi=phi, psi=psi, g1=g1, g2=g2, jet_d=g1 * 7, laser_jet_shift=shift)
    camera1 = CameraEmulator(1, jet_emulator)
    camera2 = CameraEmulator(2, jet_emulator)
    plasma_watcher = PlasmaWatcher_BoxInput(camera1, camera2, jet_emulator.box, phi=phi, psi=psi)
    plasma_watcher.g1 = g1
    plasma_watcher.g2 = g2
    if laser_on:
        jet_emulator.laser_on = True
        plasma_watcher.laser_on_mode()
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
        points = np.linspace(-1000, 1000, 1)
        for x in points:
            bg = deepcopy(bg0)
            paint_line(bg, x, 7)
            self.assertAlmostEqual(find_ray(bg)-2048/2, x, delta=0.6)

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

                x_, z_, r = find_plasma(bg2)

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


class TestPlasmaWatcher(TestCase):

    def test_calibrate_enl(self):
        phi = 90
        psi = 45
        g1 = 10
        g2 = 10
        jet_emulator = JetEmulator(phi=phi, psi=psi, g1=g1, g2=g2, jet_d=g1 * 7)
        camera1 = CameraEmulator(1, jet_emulator)
        camera2 = CameraEmulator(2, jet_emulator)
        plasma_watcher = PlasmaWatcher_BoxInput(camera1, camera2, jet_emulator.box, phi=phi, psi=psi)

        # jet_emulator.realtime(True)
        # camera1.start_video_record(start_stream=True, fps=60)
        # try:
        #     report = plasma_watcher.calibrate_enl()
        # finally:
        #     camera1.stop_video_record()
        #     camera1.stop_stream()

        report = plasma_watcher.calibrate_enl(init_step=g1 * 100, n_points=10)
        print(report)
        self.assertAlmostEqual(g1, plasma_watcher.g1, delta=0.001)
        self.assertAlmostEqual(g2, plasma_watcher.g2, delta=0.001)

    def test_move_jet_to(self):
        plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(laser_on=False)
        destinations = np.array([(123, 456), (367.67, 45.65), (-274.6, 10.5), (-235.6, -56.8)])

        for point in destinations:
            plasma_watcher.move_jet_to(*point, wait=True)
            np.testing.assert_allclose(np.array(plasma_watcher.get_jet_position()), point, 0, plasma_watcher.tol())

    def test_calibrate_plasma(self):
        plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test()

        record_video = False
        if record_video:
            jet_emulator.realtime(True)
            camera1.start_video_record(start_stream=True, fps=60)
            try:
                plasma_watcher.calibrate_plasma()
            finally:
                camera1.stop_video_record()
                camera1.stop_stream()
        else:
            plasma_watcher.calibrate_plasma()
        self.assertAlmostEqual(plasma_watcher.jett_laser_dx, jet_emulator.laser_jet_shift,
                               delta=plasma_watcher.laser_x.tol())

