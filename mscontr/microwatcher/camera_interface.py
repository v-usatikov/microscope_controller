import threading
from copy import deepcopy
from time import sleep
from typing import Callable, Set
import numpy as np

import cv2
import timeout_decorator


def show_video_frame(frame):
    cv2.imshow('Image', frame)
    cv2.waitKey(1)


class CameraInterf:

    def __init__(self):
        self._connected_to_stream: Set[Callable] = set()
        self.stream_delay = 0
        self._frame: np.ndarray = np.zeros(self.get_resolution())
        self._record_on = False
        self._record_fps = 30

        self._frame_is_new = False
        self.new_frame_signal = threading.Event()

    def is_streaming(self) -> bool:
        raise NotImplementedError

    def get_resolution(self) -> (int, int):
        raise NotImplementedError

    def set_exposure(self, value: float):
        raise NotImplementedError

    def get_exposure(self) -> float:
        raise NotImplementedError

    def set_gain(self, value: float):
        raise NotImplementedError

    def get_gain(self) -> float:
        raise NotImplementedError

    def start_stream(self, delay: float = 0):
        raise NotImplementedError

    def stop_stream(self):
        raise NotImplementedError

    def get_frame(self, timeout_s: float = 3) -> np.ndarray:
        if self.is_streaming():
            self.new_frame_signal.clear()
            self.new_frame_signal.wait(timeout=timeout_s)
            return self._frame.copy()
        else:
            frame = self.get_single_frame(timeout_s=timeout_s)
            self._frame = frame
            return frame.copy()

    def get_single_frame(self, timeout_s: float) -> np.ndarray:
        raise NotImplementedError

    def connect_to_stream(self, action: Callable):
        self._connected_to_stream.add(action)

    def disconnect_from_stream(self, action: Callable):
        self._connected_to_stream.discard(action)
        # self.disconnect_from_stream(show_video_frame)

    def new_frame_event(self, frame: np.ndarray):
        frame = frame.copy()
        self._frame = frame
        self.new_frame_signal.set()
        for action in self._connected_to_stream.copy():
            action(frame)
        sleep(self.stream_delay)

    # TODO удалить функции wait
    def wait_new_frame(self, timeout_s=10):
        timeout_decorator.timeout(timeout_s, use_signals=False)(self._wait_new_frame)()

    def _wait_new_frame(self):
        self._frame_is_new = False
        while not self._frame_is_new:
            sleep(1/60)

    def show_frame(self):
        frame = self.get_frame()
        cv2.imshow('Image', frame)
        cv2.waitKey(0)

    def show_video(self, time: float = 10, fps: float = 30, start_stream: bool = False):
        if start_stream:
            self.start_stream()
        while True:
            img = self._frame
            res_x, res_y = self.get_resolution()
            img = cv2.resize(img, (round(res_x/3), round(res_y/3)))
            cv2.imshow('Image', img)
            if cv2.waitKey(round(1000/fps)) & 0xFF == ord('q'):
                break

    def start_video_record(self, video_addres: str = 'jet_video.avi', fps: float = 30, start_stream: bool = False):
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter(video_addres, fourcc, fps, self.get_resolution(), 0)
        self._record_on = True
        self._record_fps = fps
        if start_stream and not self.is_streaming():
            self.start_stream()
        threading.Thread(target=self._video_record, args=(out,)).start()

    def _video_record(self, out: cv2.VideoWriter):
        while self._record_on:
            out.write(self.get_frame())
            sleep(1/self._record_fps)
        out.release()

    def stop_video_record(self):
        self._record_on = False


class CameraError(Exception):
    """Alle Fehler, die mit Camera verbunden sind."""

