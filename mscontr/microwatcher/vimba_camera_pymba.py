from copy import deepcopy
from time import sleep

from pymba import Vimba, VimbaException, Frame
from typing import List, Callable, Optional, Set

import numpy as np
import cv2
from pymba.camera import Camera as PymbaCamera

from mscontr.microwatcher.camera_interface import CameraInterf


def get_cameras_list():
    """gibt zurück eine Liste der verfügbaren Kameras."""
    with Vimba() as vimba:
        return vimba.camera_ids()


def arm_camera_to_stream(camera: PymbaCamera, new_frame_event: Callable):
    camera.arm('Continuous', lambda frame: new_frame_event(frame.buffer_data_numpy()))


class Camera(CameraInterf):
    def __init__(self, camera_id: str, bandwidth: Optional[int] = None):
        super().__init__()
        self._id = camera_id
        self._vimba = Vimba()
        self._vimba.startup()

        self.camera = self._vimba.camera(self._id)
        self.camera.open()

        if bandwidth is not None:
            self.set_bandwidth(bandwidth)

        self.mode = 'single'
        self.camera.arm('SingleFrame')
        self._single_mode()

        self.stream_delay = 0
        self._frame: Optional[np.ndarray] = None

    def _single_mode(self):
        if self.mode == 'stream':
            self.camera.disarm()
            self.camera.arm('SingleFrame')
            self.mode = 'single'

    def id(self):
        return self._id

    def set_parameter(self, parameter_name: str, value: float):
        feature = self.camera.feature(parameter_name)
        feature.value = value

    def get_parameter(self, parameter_name: str):
        feature = self.camera.feature(parameter_name)
        return feature.value

    # TODO Die Funktion richtig umschreiben
    def get_resolution(self) -> (int, int):
        return 2048, 1088

    def get_parameters_list(self) -> List[str]:
        return self.camera.feature_names()

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
        self.camera.disarm()
        self.camera.arm('Continuous', self.new_frame_event)
        self.camera.start_frame_acquisition()
        self.mode = 'stream'
        # print(self.id(), self.mode)
        self.stream_delay = delay

    def stop_stream(self):
        self.camera.stop_frame_acquisition()
        self._single_mode()

    def get_frame(self):
        # print(self.id(), self.mode)
        if self.mode == 'single':
            frame = self.camera.acquire_frame().buffer_data_numpy()
            self._frame = frame
            return frame.copy()
        elif self.mode == 'stream':
            return self._frame.copy()

    def new_frame_event(self, frame: Frame):
        numpy_frame = frame.buffer_data_numpy()
        super().new_frame_event(numpy_frame)

    def __del__(self):
        if self.mode == 'stream':
            self.camera.stop_frame_acquisition()
        self.camera.disarm()
        self.camera.close()
        self._vimba.shutdown()

    def close(self):
        del self


if __name__ == '__main__':
    print(get_cameras_list())
    camera = Camera('DEV_000F314E840A')
    camera.set_exposure(40000)
    camera.set_gain(10)
    # camera.show_frame()
    camera.show_video()