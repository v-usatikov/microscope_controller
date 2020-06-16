from copy import deepcopy
from statistics import mean
from time import sleep
from typing import List, Callable, Optional, Set

# from pymba import Vimba, VimbaException

import numpy as np
import cv2

def find_ray(frame: np.ndarray) -> float:
    """Bestimmt die Position des Stickstoffstrahls auf dem Frame."""
    frame = ~frame
    gray = frame
    # kernel_size = 5
    # blur_gray = cv2.GaussianBlur(gray,(kernel_size, kernel_size),0)
    low_threshold = 50
    high_threshold = 100
    edges = cv2.Canny(gray, low_threshold, high_threshold)

    rho = 1  # distance resolution in pixels of the Hough grid
    theta = np.pi / 180  # angular resolution in radians of the Hough grid
    threshold = 15  # minimum number of votes (intersections in Hough grid cell)
    min_line_length = 500  # minimum number of pixels making up a line
    max_line_gap = 20  # maximum gap in pixels between connectable line segments

    lines = cv2.HoughLinesP(edges, rho, theta, threshold, np.array([]),
                        min_line_length, max_line_gap)

    if len(lines) != 2:
        raise RecognitionError(f"Kein Stickstoffstrahl gefunden. {len(lines)} Linien wurde erkannt.")

    x = []
    for line in lines:
        for x1, y1, x2, y2 in line:
            if abs(x1-x2) > 4:
                raise RecognitionError(f"Kein Stickstoffstrahl gefunden. Die erkannte Linien sind nicht vertikal.")
            x.append(x1)
            x.append(x2)
    return mean(x)



class RecognitionError(Exception):
    "Fehler bei Erkennug der Objekten auf einem Frame"

