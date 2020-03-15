from typing import Tuple, Callable

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QMainWindow, QApplication, QScrollBar, QStatusBar, QGraphicsView, \
    QSizePolicy
from PyQt5.QtWidgets import QFrame, QWidget, QLabel
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint


class SampleNavigator(QFrame):
    zoomed = pyqtSignal()

    def __init__(self, get_photo: Callable, sample_w: float = 1000, sample_h: float = 1000, fov_d: float = 7.5):
        super().__init__()

        # physische Maßen, alles in Normierte Einheiten
        self.sample_w = sample_w
        self.sample_h = sample_h
        self.fov_d = fov_d

        # Zoom Daten (in Normierte Einheiten)
        self.zoom_x = 0
        self.zoom_y = 0
        self.zoom_d = 1000

        # Positionen von FoV und Fov-to (in Normierte Einheiten)
        self.fov_x = 0
        self.fov_y = 0
        self.fov_x_to = 0
        self.fov_y_to = 0

        # Mode einstellen ('navig', 'move' oder 'zoom')
        self.mode = 'navig'

        # Erstellen die Objekten für FoV und FoV_to
        self.fov_to = FoVto(self)
        self.fov = FoV(self)

        self.photos = []

    def norm_to_pixel_rel(self, value: float) -> int:
        """Transformiert ein Wert in normierte Einheiten zu Pixel."""
        return round(self.width()/(self.zoom_d + self.fov_d) * value)

    def pixel_to_norm_rel(self, value: float) -> float:
        """Transformiert ein Wert in Pixel zu normierte Einheiten."""
        return (self.zoom_d + self.fov_d)/self.width() * value

    def norm_to_pixel_coord(self, x: float, y: float) -> (float, float):
        """Transformiert Koordinaten in normierte Einheiten zu Pixel."""
        x = self.norm_to_pixel_rel(x - self.zoom_x + self.fov_d/2)
        y = self.norm_to_pixel_rel(y - self.zoom_y + self.fov_d/2)
        return x, y

    def pixel_to_norm_coord(self, x: float, y: float) -> (float, float):
        """Transformiert Koordinaten in Pixel zu normierte Einheiten."""
        x = self.pixel_to_norm_rel(x) + self.zoom_x - self.fov_d/2
        y = self.pixel_to_norm_rel(y) + self.zoom_y - self.fov_d/2
        return x, y

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        size = min(a0.size().width(), a0.size().height())
        self.resize(size, size)
        print(a0.size())

class GraphicObjekt(QLabel):

    def __init__(self, s_navig: SampleNavigator):
        super().__init__(s_navig)
        self.setText('')
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.s_navig = s_navig

        self.x = 0
        self.y = 0

        self.s_navig.zoomed.connect(self.refresh)

    def d(self):
        return self.s_navig.fov_d

    def d_pixel(self):
        return self.s_navig.norm_to_pixel_rel(self.s_navig.fov_d)

    def rescale(self):
        self.setFixedWidth(self.d_pixel() + 2)
        self.setFixedHeight(self.d_pixel() + 2)
        self.update()

    def reposition(self):
        x, y = self.s_navig.norm_to_pixel_coord(self.x, self.y)
        self.move(round(x - self.width() / 2), round(y - self.height() / 2))

    def move_to(self, x, y):
        self.x = x
        self.y = y
        self.reposition()

    def refresh(self):
        self.rescale()
        self.reposition()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.gray, 1, Qt.SolidLine)

        pen.setWidth(1)
        pen.setColor(Qt.black)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        qp.drawEllipse(QPoint(int(self.width()/2), int(self.height()/2)), self.d_pixel()/2, self.d_pixel()/2)

class FoV(QLabel):

    def __init__(self, s_navig: SampleNavigator):
        super().__init__(s_navig)
        self.setText('')
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.s_navig = s_navig

        self.x = 0
        self.y = 0

        self.s_navig.zoomed.connect(self.refresh)

    def d(self):
        return self.s_navig.fov_d

    def d_pixel(self):
        return self.s_navig.norm_to_pixel_rel(self.s_navig.fov_d)

    def rescale(self):
        self.setFixedWidth(self.d_pixel() + 2)
        self.setFixedHeight(self.d_pixel() + 2)
        self.update()

    def reposition(self):
        x, y = self.s_navig.norm_to_pixel_coord(self.x, self.y)
        self.move(round(x - self.width() / 2), round(y - self.height() / 2))

    def move_to(self, x, y):
        self.x = x
        self.y = y
        self.reposition()

    def refresh(self):
        self.rescale()
        self.reposition()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.gray, 1, Qt.SolidLine)

        pen.setWidth(1)
        pen.setColor(Qt.black)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        qp.drawEllipse(QPoint(int(self.width()/2), int(self.height()/2)), self.d_pixel()/2, self.d_pixel()/2)


class FoVto(FoV):

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.gray, 1, Qt.DashLine)

        pen.setWidth(1)
        pen.setColor(Qt.gray)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        qp.drawEllipse(QPoint(int(self.width()/2), int(self.height()/2)), self.d_pixel()/2, self.d_pixel()/2)


class SamplePhoto(FoV):

    def __init__(self, s_navig: SampleNavigator, photo_address: str):
        super().__init__(s_navig)
        self.photo_address = photo_address

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.gray, 1, Qt.DashLine)

        pen.setWidth(1)
        pen.setColor(Qt.gray)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        qp.drawEllipse(QPoint(int(self.width()/2), int(self.height()/2)), self.d_pixel()/2, self.d_pixel()/2)