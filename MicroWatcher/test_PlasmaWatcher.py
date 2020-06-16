from unittest import TestCase
import numpy as np
import cv2

# from MicroWatcher.PlasmaWatcher import find_ray
# from MicroWatcher.camera_emulator import make_ray_photo

from MicroWatcher.PlasmaCameraEmulator import paint_circle


class TestExternalFunctions(TestCase):
    # def test_find_ray(self):
    #     frame = cv2.imread('test_data/img_test2.bmp')
    #     self.assertAlmostEqual(612, find_ray(frame), delta=2)

    def test_paint_circle(self):
        img = np.zeros((1088, 2048), dtype='uint8')
        paint_circle(img, pl_x=-500, pl_y=-100, radius=20)
        self.assertTrue(True)


# class test_JetEmulator(TestCase):
#     def test_make_ray_photo(self):
#         make_ray_photo(700)


# class test_CameraEmulator(TestCase):
#     def test_make_ray_photo(self):
#         make_ray_photo(700)