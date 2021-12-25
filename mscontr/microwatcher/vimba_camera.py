import signal
import sys
from copy import deepcopy
from time import sleep

# from pymba import Vimba, VimbaException, Frame
from typing import List, Callable, Optional, Set

import numpy as np
import cv2
# from pymba.camera import Camera as VimbaCamera
from vimba import Camera as VimbaCamera, Frame as VimbaFrame, Vimba, VimbaFeatureError

from mscontr.microwatcher.camera_interface import CameraInterf, CameraError


def get_cameras_list():
    """gibt zurück eine Liste der verfügbaren Kameras."""
    camera_ids = []
    with Vimba.get_instance() as vimba:
        cams: List[VimbaCamera] = vimba.get_all_cameras()

        print('Cameras found: {}'.format(len(cams)))

        for cam in cams:
            camera_ids.append(cam.get_id())

    return camera_ids


# class VimbaSystem:
#
#     def __init__(self):
#         self.vimba = Vimba.get_instance()
#         self.cameras: List[Camera] = []
#
#     def __enter__(self):
#         self.vimba.__enter__()
#
#         return self
#
#     def __exit__(self, exc_type, exc_value, exc_traceback):
#         for camera in self.cameras:
#             camera.close()
#         self.vimba.__exit__(exc_type, exc_value, exc_traceback)


class Camera(CameraInterf):
    def __init__(self, camera_id: str, bandwidth: Optional[int] = None):
        super().__init__()
        self._id = camera_id
        self._vimba = Vimba.get_instance()
        self._vimba.__enter__()

        self.camera: VimbaCamera = self._vimba.get_camera_by_id(camera_id)
        self.camera.__enter__()

        try:
            self.camera.GVSPAdjustPacketSize.run()

            while not self.camera.GVSPAdjustPacketSize.is_done():
                pass

        except (AttributeError, VimbaFeatureError):
            pass

        # if bandwidth is not None:
        #     self.set_bandwidth(bandwidth)

        self.stream_delay = 0
        self.attempts_limit: int = 10

    def is_streaming(self) -> bool:
        return self.camera.is_streaming()

    def id(self):
        return self._id

    def set_parameter(self, parameter_name: str, value: float):
        feature = self.camera.get_feature_by_name(parameter_name)
        feature.set(value)

    def get_parameter(self, parameter_name: str):
        feature = self.camera.get_feature_by_name(parameter_name)
        return feature.get()

    # TODO Die Funktion richtig umschreiben
    def get_resolution(self) -> (int, int):
        return 2048, 1088

    def get_parameters_list(self) -> List[str]:
        features_list = []
        for feature in self.camera.get_all_features():
            features_list.append(feature.get_name())

        return features_list

    def set_bandwidth(self, value: int):
        self.set_parameter('StreamBytesPerSecond', value)

    def get_bandwidth(self) -> int:
        return self.get_parameter('StreamBytesPerSecond')

    def set_exposure(self, value: float):
        self.set_parameter('ExposureTimeAbs', value)

    def get_exposure(self):
        return self.get_parameter('ExposureTimeAbs')

    def set_gain(self, value: float):
        self.set_parameter('Gain', value)

    def get_gain(self):
        return self.get_parameter('Gain')

    def start_stream(self, delay: float = 0):
        # print('start stream', self.id(), self.mode)
        self.camera.start_streaming(handler=self._new_frame_event, buffer_count=5)
        # print(self.id(), self.mode)
        self.stream_delay = delay

    def stop_stream(self):
        self.camera.stop_streaming()

    def get_single_frame(self, timeout_s: float = 3) -> np.ndarray:
        frame_vimb = None
        # TODO Настроить общий таймаут, чтобы он не умножался на количество попыток
        for frame_vimb in self.camera.get_frame_generator(limit=10, timeout_ms=round(1000*timeout_s)):
            if not frame_vimb.get_status():
                break
        if frame_vimb is None:
            raise CameraError("Hat nicht geklappt ein Frame abzulesen!")

        frame_ndarray = frame_vimb.as_numpy_ndarray().reshape((1088, 2048))
        return frame_ndarray

    def _new_frame_event(self, cam: VimbaCamera, frame: VimbaFrame):
        print(frame.get_id(), frame.get_status())
        if not frame.get_status():
            numpy_frame = frame.as_numpy_ndarray().reshape((1088, 2048))
            self.new_frame_event(numpy_frame)
        cam.queue_frame(frame)

    def __del__(self):
        print(1)
        # self.stop_stream()
        self.camera.__exit__(*sys.exc_info())
        print(2)
        self._vimba.__exit__(*sys.exc_info())
        print(3)


if __name__ == '__main__':
    print(get_cameras_list())
    camera = Camera('DEV_000F314E840A')
    camera.set_exposure(40000)
    camera.set_gain(10)
    # camera.show_frame()
    camera.show_video(start_stream=True)