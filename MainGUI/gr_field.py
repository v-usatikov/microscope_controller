# coding= utf-8
import logging
import time
from typing import List, Set

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QMainWindow, QApplication, QScrollBar, QStatusBar, QGraphicsView, \
    QSizePolicy
from PyQt5.QtWidgets import QFrame, QWidget, QLabel
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint, QSize
import sys
# import pylab
import serial, serial.tools.list_ports
# import pyqtgraph
from PyQt5.uic import loadUi

from MotorController.MotorControllerInterface import SerialConnector
from MotorController.Phytron_MCC2 import Box, StopIndicator, WaitReporter, MCC2BoxSerial, MCC2BoxEmulator, \
    MCC2Communicator
import ULoggingConfig

if __name__ == '__main__':
    ULoggingConfig.init_config()


class MyGraphField(QFrame):
    pos_signal = pyqtSignal()
    pos_to_signal = pyqtSignal()

    def __init__(self, perent=None):
        super().__init__(perent)
        self.d = 7
        self.x = int(self.d/2)
        self.y = int(self.d/2)

        self.x_to = int(self.d/2)
        self.y_to = int(self.d/2)

        self.round_to = RoundLabel(self, self.d, Qt.DashLine, Qt.gray)
        self.round_pos = RoundLabel(self, self.d)

        self.round_pos.move_to(self.x, self.y)
        self.round_to.move_to(self.x_to, self.y_to)

        # sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # sizePolicy.setHeightForWidth(True)
        # self.setSizePolicy(sizePolicy)

        self.photos = []

    def set_fixed(self):
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(True)
        self.setSizePolicy(sizePolicy)

    def set_expanding(self):
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHeightForWidth(True)
        self.setSizePolicy(sizePolicy)

    # def sizeHint(self):
    #     return QSize(400, 600)
    #
    # def heightForWidth(self, width):
    #     return width

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.x_to = event.pos().x()
        self.y_to = event.pos().y()
        self.round_to.move_to(self.x_to, self.y_to)
        self.pos_to_signal.emit()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        self.mousePressEvent(event)

    def make_photo(self):
        self.photo = RoundLabel(self, self.d, Qt.NoPen, Qt.blue, Qt.Dense5Pattern)
        # self.photo = RoundLabel(self, self.d)
        self.photo.move_to(self.x, self.y)
        self.photo.show()
        self.photos.append(self.photo)

    def go_to(self):
        if self.x > self.x_to:
            self.x -= 1
        elif self.x < self.x_to:
            self.x += 1

        if self.y > self.y_to:
            self.y -= 1
        elif self.y < self.y_to:
            self.y += 1

        self.round_pos.move_to(self.x, self.y)
        self.pos_signal.emit()

        if self.x != self.x_to or self.y != self.y_to:
            QtCore.QTimer.singleShot(int(1000/60), self.go_to)  # QUICKLY repeat

    def paintEvent(self, event: QtGui.QPaintEvent):
        super().paintEvent(event)

        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # Hintergrund malen
        pen = QPen(Qt.gray, 2, Qt.SolidLine)
        pen.setWidth(1)
        pen.setColor(Qt.white)
        qp.setPen(pen)
        qp.setBrush(Qt.white)
        qp.drawRect(0, 0, self.width(), self.height())

        qp.end()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        size = min(a0.size().width(), a0.size().height())
        # self.set_fixed()
        # size = 600
        self.resize(size, size)
        # self.set_expanding()
        print(a0.size())



class RoundLabel(QLabel):

    def __init__(self, parent, d: float = 60, line=Qt.SolidLine, color=Qt.black, brush=Qt.NoBrush):
        super().__init__(parent)
        self.setText('')
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.d = 0
        self.set_diameter(d)
        self.line = line
        self.color = color
        self.brush = brush

    def set_diameter(self, d):
        self.d = d
        self.setFixedWidth(1.3*d)
        self.setFixedHeight(1.3*d)

    def move_to(self, x, y):
        self.move(int(x-self.width()/2), int(y-self.height()/2))

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.gray, 1, self.line)

        pen.setWidth(1)
        pen.setColor(self.color)
        qp.setPen(pen)
        qp.setBrush(self.brush)
        qp.drawEllipse(QPoint(int(self.width()/2), int(self.height()/2)), self.d/2, self.d/2)

    # def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
    #     print('Hello!')


class ExampleApp(QMainWindow):
    def __init__(self, parent=None):
        super(ExampleApp, self).__init__(parent)
        loadUi('MainGUI/mainwindow.ui', self)

        self.widget.setParent(None)

        self.mygrfield = MyGraphField(self.centralwidget)
        self.horizontalLayout.addWidget(self.mygrfield)

        self.GoButton.clicked.connect(self.mygrfield.go_to)
        self.FotoButton.clicked.connect(self.mygrfield.make_photo)

        self.mygrfield.pos_signal.connect(self.update_pos)
        self.mygrfield.pos_to_signal.connect(self.update_to_pos)

        self.update_pos()

    def update_to_pos(self):
        self.label_x_to.setText(f'{self.mygrfield.x_to}')
        self.label_y_to.setText(f'{self.mygrfield.y_to}')

    def update_pos(self):
        self.label_x.setText(f'x: {self.mygrfield.x}')
        self.label_y.setText(f'y: {self.mygrfield.y}')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('macintosh')
    form = ExampleApp()
    form.show()
    # form.update() #start with something
    app.exec_()

    print("DONE")