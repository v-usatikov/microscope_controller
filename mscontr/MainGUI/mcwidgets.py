import logging
import platform
import shutil
import threading
import time
import traceback
from abc import ABC
from typing import Tuple, Callable, List, Optional, Union, Dict, Collection, Set

import cv2
import numpy as np
import serial, serial.tools.list_ports
from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QMainWindow, QApplication, QScrollBar, QStatusBar, QGraphicsView, \
    QSizePolicy, QGroupBox, QStyle, QStyleFactory, QComboBox, QHBoxLayout, QGridLayout, QCheckBox, QLineEdit, \
    QPushButton, QVBoxLayout
from PyQt6.QtWidgets import QFrame, QWidget, QLabel
from PyQt6.QtGui import QPainter, QPen, QPixmap, QColor, QFont, QWindow
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from math import sqrt
from PIL import Image
from PyQt6.uic import loadUi
from graphic_ext import GraphicField, GraphicObject, GraphicZone, QPainter_ext
from graphic_ext.gr_field import Axes, Axis, RoundAxis
from motor_controller import Motor
import motor_controller as mc
from motor_controller.Phytron_MCC2 import MCC2BoxSerial
from motor_controller.interface import StandardStopIndicator, StopIndicator, WaitReporter, FileReadError

from mscontr.microwatcher.plasma_camera_emulator import JetEmulator, CameraEmulator
from mscontr.microwatcher.plasma_watcher import PlasmaWatcher
from tests.test_PlasmaWatcher import prepare_jet_watcher_to_test


point_n = Tuple[float, float]
point_p = Tuple[int, int]


def print_ex_time(f):

    def timed(*args, **kw):

        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        print('func:%r args:[%r, %r] took: %2.3f ms' % (f.__name__, args, kw, 1000*(te-ts)))
        return result

    return timed


def pass_all_errors_with_massage(mess: str = ''):
    def decorator(func):
        def inner(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as err:
                logging.exception(err)
                QMessageBox.warning(None, "Aktion fehlgeschlagen!", mess + " Fehler:\n" + traceback.format_exc())
        return inner
    return decorator


def pass_all_errors_in_thread_with_massage(mess: str = '', action: Callable = None):
    def decorator(func):
        def inner(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except Exception as err:
                logging.exception(err)
                self.massage_signal.emit("error", "Aktion fehlgeschlagen!", mess + " Fehler:\n" + traceback.format_exc())
                if action is not None:
                    action()
        return inner
    return decorator


def show_message(type: str = 'info', header: str = '', text: str = ''):

    if type == 'error':
        QMessageBox.warning(None, header, text)
    elif type == 'info':
        QMessageBox.information(None, header, text)
    else:
        raise ValueError('type muss "info" oder "error" sein!')


class SampleNavigator(GraphicField):
    pos_to_signal = pyqtSignal()

    def __init__(self, parent=None, sample_w: float = 1000, sample_h: float = 1000, fov_d: float = 60):
        super().__init__(parent=parent, x_range=sample_w, y_range=sample_h, margin=fov_d/2, keep_ratio=True, scale=True)

        self.__fov_d = fov_d

        # Erstellen die Objekten für FoV und FoV_to
        self.fov_to = FoVto(self)
        self.fov = FoV(self)

        self.photos = []

    def fov_d(self) -> float:
        return self.__fov_d

    def set_fov_d(self, fov_d: float):
        self.__fov_d = fov_d
        self.margin = fov_d/2

    def move_fov(self, x:float, y:float):
        self.fov.move_to(x, y)

    def move_fov_to(self, x: float, y: float):
        self.fov_to.move_to(x, y)

    def add_photo(self, photo_address: str):
        self.photos.append(SamplePhoto(self, photo_address))
        self.fov_to.raise_()
        self.fov.raise_()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(event)
        if self.mode() == 'normal':
            fov_x_to, fov_y_to = self.pixel_to_norm_coord(event.pos().x(), event.pos().y())
            self.move_fov_to(fov_x_to, fov_y_to)
            self.pos_to_signal.emit()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self.mode() == 'normal':
            self.mousePressEvent(event)

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        x, y = self.pixel_to_norm_coord(a0.x(), a0.y())
        for photo in self.photos:
            if photo.is_in(x, y):
                photo.mouseDoubleClickEvent(a0)


class FoV(GraphicObject):

    def __init__(self, s_navig: SampleNavigator, x: float = 0, y: float = 0):
        super().__init__(s_navig, x, y, True)

        self.s_navig = s_navig

    def d(self):
        return self.s_navig.__fov_d

    def d_pixel(self):
        return self.s_navig.norm_to_pixel_rel(self.s_navig.fov_d())

    def rescale(self):
        self.setFixedWidth(self.d_pixel()+4)
        self.setFixedHeight(self.d_pixel()+4)
        self.update()
        self.hello()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super().paintEvent(a0)
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint(qp)
        qp.end()

    def paint(self, qp):
        pen = QPen(Qt.GlobalColor.black, 1, Qt.BrushStyle.SolidLine)
        qp.setPen(pen)
        qp.setBrush(Qt.BrushStyle.NoBrush)
        qp.drawEllipse(QPoint(round(self.width() / 2), round(self.height() / 2)), self.d_pixel() / 2, self.d_pixel() / 2)

    def hello(self):
        print('FoV')


class FoVto(FoV):

    def paint(self, qp):
        pen = QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.DashLine)
        qp.setPen(pen)
        qp.setBrush(Qt.BrushStyle.NoBrush)
        qp.drawEllipse(QPoint(round(self.width()/2), round(self.height()/2)), self.d_pixel()/2, self.d_pixel()/2)

    def hello(self):
        print('FoV_to')


class SamplePhoto(FoV):

    def __init__(self, s_navig: SampleNavigator, photo_address: str):
        super().__init__(s_navig, s_navig.fov.x, s_navig.fov.y)
        self.photo_address = photo_address
        self.setPixmap(QtGui.QPixmap(self.photo_address))
        self.setScaledContents(True)
        self.show()
        self.refresh()

    def rescale(self):
        print('Photo')
        self.setFixedWidth(self.d_pixel())
        self.setFixedHeight(self.d_pixel())
        self.update()

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        img = Image.open(self.photo_address)
        img.show()

    def paint(self, qp):
        pass

    def is_in(self, x: float, y: float) -> bool:
        return sqrt((self.x - x)**2 + (self.y - y)**2) <= self.s_navig.fov_d()/2

    def hello(self):
        print('Photo')


class AktPositionSlider(QScrollBar):
    def __init__(self, parent=None):
        super(AktPositionSlider, self).__init__(Qt.Orientation.Horizontal, parent)
        self.low_x = -50
        self.up_x = 1050
        self.setEnabled(False)
        self.setInvertedAppearance(True)

    def paintEvent(self, e):
        # super().paintEvent(e)
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.drawLines(qp)
        qp.end()

    def drawLines(self, qp):
        pen = QPen(Qt.GlobalColor.gray, 2, Qt.PenStyle.SolidLine)

        # Parametern
        d_icon = 8
        h_icon = 4
        rund_k = 1
        h_hint = 20
        height = self.height()
        hcenter = round(height / 2)
        width = self.width()
        v_range = width - 2 * d_icon
        x_icon = round(d_icon + self.value() * v_range / 1000)
        # x_icon = d_icon + self.U_x * v_range / 1000

        # Hintergrund malen
        pen.setWidth(1)
        pen.setColor(Qt.GlobalColor.white)
        qp.setPen(pen)
        qp.setBrush(Qt.GlobalColor.white)
        qp.drawRect(0, hcenter - h_hint, width, 2 * h_hint)

        # Icon malen
        pen.setWidth(0)
        pen.setColor(Qt.GlobalColor.gray)
        qp.setPen(pen)
        qp.setBrush(Qt.GlobalColor.gray)
        qp.drawRoundedRect(x_icon - d_icon, hcenter - h_icon, 2 * d_icon, 2 * h_icon, rund_k * h_icon, rund_k * h_icon)
        # print(x_icon+d_icon, width)

        # Soft Limits malen
        pen.setWidth(2)
        qp.setPen(pen)
        U_pixel_x = round(d_icon + self.low_x * v_range / 1000)
        O_pixel_x = round(d_icon + self.up_x * v_range / 1000)
        try:
            qp.drawLine(U_pixel_x, hcenter - h_hint, U_pixel_x, hcenter + h_hint)
            qp.drawLine(O_pixel_x, hcenter - h_hint, O_pixel_x, hcenter + h_hint)
        except OverflowError:
            logging.error("OverflowError, kann nicht Soft Limits malen.")

    def set_soft_limits(self, low_x, up_x):
        if low_x is None:
            self.low_x = -50
        else:
            self.low_x = low_x
        if up_x is None:
            self.up_x = 1050
        else:
            self.up_x = up_x
        self.update()

        # M_d = 10.5
        # size = self.frameGeometry().width()
        # self.U_x = size - U_x * size / 1000
        # self.O_x = size - O_x * size / 1000
        # self.update()

    def Soft_Limits_einstellen(self, U_x, O_x):
        if U_x is None:
            self.U_x = -50
        else:
            self.U_x = U_x
        if O_x is None:
            self.O_x = 1050
        else:
            self.O_x = O_x
        self.update()

        # M_d = 10.5
        # size = self.frameGeometry().width()
        # self.U_x = size - U_x * size / 1000
        # self.O_x = size - O_x * size / 1000
        # self.update()


def m_err_handl_with_massage(func):
    def inner(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except mc.interface.NoReplyError as err:
            logging.exception(err)
            QMessageBox.warning(None, "Aktion fehlgeschlagen!", "Kontroller antwortet nicht!")
        except mc.interface.ControllerError as err:
            logging.exception(err)
            QMessageBox.warning(None, "Aktion fehlgeschlagen!", "Kontroller hat den Befehl nicht ausgeführt!")
        except Exception as err:
            logging.exception(err)
            QMessageBox.warning(None, "Unerwartete Fehler!",
                                traceback.format_exc())
    return inner


class MotorWidget(QGroupBox):

    motor: Motor | None = None

    def __init__(self, parent: Optional[QWidget], name: Optional[str] = None):
        super().__init__(parent)

        # self.setStyle()
        self.setupUi(self)

        if name is not None:
            self.setTitle(name)
        else:
            self.setTitle('')
        # print('1', self.styleSheet())
        # self.setStyle('windowsvista')

        self.__first_position_read = True
        self.position = 0
        self.position_NE = 0
        self.is_sleeping = True

        self.axis_p: Axis | None = None
        self.axis_m: Axis | None = None

        self.GeheZuEdit.returnPressed.connect(self.go_to)
        self.SL_U_Edit.textEdited.connect(self.set_soft_limits)
        self.SL_O_Edit.textEdited.connect(self.set_soft_limits)
        self.StopButton.clicked.connect(self.stop)
        self.minusBtn.clicked.connect(self.minus_step)
        self.plusBtn.clicked.connect(self.plus_step)
        self.NullBtn.clicked.connect(self.set_zero)

        self.is_in_error_state: bool = False

        self.setEnabled(False)

    def init(self, motor: Motor, awake: bool = True):

        self.motor = motor
        self.init_soft_limits()
        self.__first_position_read = True
        self.read_position()
        if not self.motor.is_calibratable():
            self.APSlider.hide()
            # self.APSlider.setEnabled(False)
            self.APSlider.setValue(0)
        else:
            self.APSlider.show()
            # self.APSlider.setEnabled(True)
            self.APSlider.setValue(round(self.position_NE))

        self.Units_label.setText(self.motor.config['display_units'])
        self.setTitle(self.motor.name)

        if awake:
            self.awake()

    def discard(self):

        self.setEnabled(False)
        self.motor = None

    @m_err_handl_with_massage
    def go_to(self, checked=False):
        self.motor.go_to(float(self.GeheZuEdit.text()), 'displ')

    @m_err_handl_with_massage
    def plus_step(self, checked=False):
        self.motor.go(float(self.SchrittEdit.text()), 'displ')

    @m_err_handl_with_massage
    def minus_step(self, checked=False):
        self.motor.go(-float(self.SchrittEdit.text()), 'displ')

    @m_err_handl_with_massage
    def stop(self, checked=False):
        self.motor.stop()

    def sleep(self):

        self.setEnabled(False)
        self.is_sleeping = True

    def awake(self):

        if self.motor is not None:
            self.setEnabled(True)
            self.is_sleeping = False

    def read_position(self, single_shot: bool = False):
        if not self.is_sleeping and self.motor is not None:
            position0 = self.position

            if isinstance(self.parent(), MotorWindow):
                try:
                    self.position = self.motor.position('displ')
                except mc.interface.ReplyError:
                    conn_window: ConnectionWindow = self.parent().conn_window
                    conn_window.motor_error_report(self.motor)
                    self.AktPosEdit.setText("Error!")
                    self.is_in_error_state = True
                else:
                    if self.is_in_error_state:
                        conn_window: ConnectionWindow = self.parent().conn_window
                        conn_window.cancel_motor_error_report(self.motor)
                        self.is_in_error_state = False
            else:
                self.position = self.motor.position('displ')

            if not self.is_in_error_state:
                if self.__first_position_read:
                    position0 = self.position
                    self.__first_position_read = False
                self.position_NE = self.motor.transform_units(self.position, 'displ', 'norm')
                self.AktPosEdit.setText(str(round(self.position, 4)))
                if self.motor.is_calibratable():
                    self.APSlider.setValue(int(self.position_NE))

            if self.axis_p is not None and self.axis_m is not None and self.motor is not None:
                shift = self.position - position0
                shift = self.motor.transform_units(shift, 'displ', 'contr', rel=True)
                tol = self.motor.communicator.tolerance
                if shift > tol:
                    if not self.axis_p.activated:
                        self.axis_p.activated = True
                        self.axis_m.activated = False
                        self.axis_p.axes_obj.update()
                elif shift < -tol:
                    if not self.axis_m.activated:
                        self.axis_p.activated = False
                        self.axis_m.activated = True
                        self.axis_p.axes_obj.update()
                elif self.axis_m.activated or self.axis_p.activated:
                    self.axis_p.activated = False
                    self.axis_m.activated = False
                    self.axis_p.axes_obj.update()

        if not single_shot and self.motor is not None:
            QtCore.QTimer.singleShot(200, self.read_position)

    def set_zero(self):
        self.motor.set_display_null()
        self.Soft_Limits_Lines_Einheiten_anpassen()

    def Soft_Limits_Lines_Einheiten_anpassen(self):
        Motor = self.motor

        U_Grenze = Motor.soft_limits[0]
        O_Grenze = Motor.soft_limits[1]

        if U_Grenze is not None:
            U_Grenze = Motor.transform_units(U_Grenze, 'norm', to='displ')
            self.SL_U_Edit.setText(str(round(U_Grenze, 4)))
        if O_Grenze is not None:
            O_Grenze = Motor.transform_units(O_Grenze, 'norm', to='displ')
            self.SL_O_Edit.setText(str(round(O_Grenze, 4)))

    def set_soft_limits(self):
        motor = self.motor
        lower_bound = self.SL_U_Edit.text()
        upper_bound = self.SL_O_Edit.text()

        try:
            float(lower_bound)
        except ValueError:
            lower_bound = ''
            self.SL_U_Edit.setStyleSheet("color: red;")

        try:
            float(upper_bound)
        except ValueError:
            upper_bound = ''
            self.SL_O_Edit.setStyleSheet("color: red;")

        # print('Einstellen', motor.Name, lower_bound, upper_bound)
        # print(lower_bound, upper_bound)


        lower_bound = motor.transform_units(float(lower_bound), 'displ', to='norm') if lower_bound != '' else None
        upper_bound = motor.transform_units(float(upper_bound), 'displ', to='norm') if upper_bound != '' else None

        motor.soft_limits = (lower_bound, upper_bound)

        if lower_bound is not None and upper_bound is not None:
            if upper_bound - lower_bound < 0:
                self.SL_U_Edit.setStyleSheet("color: red;")
                self.SL_O_Edit.setStyleSheet("color: red;")
            else:
                self.SL_U_Edit.setStyleSheet("color:;")
                self.SL_O_Edit.setStyleSheet("color:;")
        else:
            self.SL_U_Edit.setStyleSheet("color:;")
            self.SL_O_Edit.setStyleSheet("color:;")

        if lower_bound is None:
            self.SL_U_Edit.setStyleSheet("color: red;")
        if upper_bound is None:
            self.SL_O_Edit.setStyleSheet("color: red;")

        self.APSlider.set_soft_limits(lower_bound, upper_bound)

    def init_soft_limits(self):
        motor = self.motor

        lower_bound = motor.soft_limits[0]
        upper_bound = motor.soft_limits[1]
        # print('Init', motor.Name, lower_bound, upper_bound)

        if lower_bound is not None:
            lower_bound = motor.transform_units(lower_bound, 'norm', to='displ')
            self.SL_U_Edit.setText(str(round(lower_bound, 4)))
        else:
            self.SL_U_Edit.setText('')
        if upper_bound is not None:
            upper_bound = motor.transform_units(upper_bound, 'norm', to='displ')
            self.SL_O_Edit.setText(str(round(upper_bound, 4)))
        else:
            self.SL_O_Edit.setText('')

        self.set_soft_limits()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.is_closed = True
        super().closeEvent(a0)

    def setupUi(self, group_box: QGroupBox):

        group_box.setEnabled(False)
        group_box.setGeometry(QtCore.QRect(20, 90, 400, 121))
        sizePolicy = QtWidgets.QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(group_box.sizePolicy().hasHeightForWidth())
        group_box.setSizePolicy(sizePolicy)
        # group_box.setMinimumSize(QtCore.QSize(0, 121))
        # font = QtGui.QFont()
        # font.setPointSize(100)
        # group_box.setFont(font)
        group_box.setObjectName("MotorBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(group_box)
        self.verticalLayout_2.setContentsMargins(10, 5, 10, 5)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.APSlider = AktPositionSlider(group_box)
        self.APSlider.setEnabled(False)
        self.APSlider.setMouseTracking(True)
        self.APSlider.setMaximum(1000)
        self.APSlider.setPageStep(1)
        self.APSlider.setProperty("value", 300)
        self.APSlider.setSliderPosition(300)
        self.APSlider.setTracking(True)
        self.APSlider.setOrientation(Qt.Orientation.Horizontal)
        self.APSlider.setInvertedAppearance(True)
        self.APSlider.setInvertedControls(False)
        self.APSlider.setObjectName("APSlider")
        self.verticalLayout_2.addWidget(self.APSlider)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(1)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_6 = QtWidgets.QLabel(group_box)
        self.label_6.setObjectName("label_6")
        self.horizontalLayout_3.addWidget(self.label_6)
        self.AktPosEdit = QtWidgets.QLineEdit(group_box)
        self.AktPosEdit.setMinimumSize(QtCore.QSize(0, 21))
        self.AktPosEdit.setReadOnly(True)
        self.AktPosEdit.setObjectName("AktPosEdit")
        self.horizontalLayout_3.addWidget(self.AktPosEdit)
        self.Units_label = QtWidgets.QLabel(group_box)
        self.Units_label.setObjectName("Units_label")
        self.horizontalLayout_3.addWidget(self.Units_label)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.minusBtn = QtWidgets.QPushButton(group_box)
        self.minusBtn.setObjectName("minusBtn")
        self.horizontalLayout_3.addWidget(self.minusBtn)
        self.SchrittEdit = QtWidgets.QLineEdit(group_box)
        self.SchrittEdit.setMinimumSize(QtCore.QSize(0, 21))
        self.SchrittEdit.setDragEnabled(True)
        self.SchrittEdit.setObjectName("SchrittEdit")
        self.horizontalLayout_3.addWidget(self.SchrittEdit)
        self.plusBtn = QtWidgets.QPushButton(group_box)
        self.plusBtn.setObjectName("plusBtn")
        self.horizontalLayout_3.addWidget(self.plusBtn)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.label_7 = QtWidgets.QLabel(group_box)
        self.label_7.setMinimumSize(QtCore.QSize(0, 0))
        self.label_7.setObjectName("label_7")
        self.horizontalLayout_3.addWidget(self.label_7)
        self.GeheZuEdit = QtWidgets.QLineEdit(group_box)
        self.GeheZuEdit.setMinimumSize(QtCore.QSize(0, 21))
        self.GeheZuEdit.setDragEnabled(True)
        self.GeheZuEdit.setObjectName("GeheZuEdit")
        self.horizontalLayout_3.addWidget(self.GeheZuEdit)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.NullBtn = QtWidgets.QPushButton(group_box)
        self.NullBtn.setMaximumSize(QtCore.QSize(120, 16777215))
        self.NullBtn.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.NullBtn.setObjectName("NullBtn")
        self.horizontalLayout_4.addWidget(self.NullBtn)
        spacerItem2 = QtWidgets.QSpacerItem(30, 28, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem2)
        self.StopButton = QtWidgets.QPushButton(group_box)
        self.StopButton.setMinimumSize(QtCore.QSize(100, 0))
        self.StopButton.setObjectName("StopButton")
        self.horizontalLayout_4.addWidget(self.StopButton)
        self.line_2 = QtWidgets.QFrame(group_box)
        self.line_2.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_2.setObjectName("line_2")
        self.horizontalLayout_4.addWidget(self.line_2)
        self.label_8 = QtWidgets.QLabel(group_box)
        self.label_8.setObjectName("label_8")
        self.horizontalLayout_4.addWidget(self.label_8)
        self.label_9 = QtWidgets.QLabel(group_box)
        self.label_9.setObjectName("label_9")
        self.horizontalLayout_4.addWidget(self.label_9)
        self.SL_U_Edit = QtWidgets.QLineEdit(group_box)
        self.SL_U_Edit.setObjectName("SL_U_Edit")
        self.horizontalLayout_4.addWidget(self.SL_U_Edit)
        self.label_10 = QtWidgets.QLabel(group_box)
        self.label_10.setObjectName("label_10")
        self.horizontalLayout_4.addWidget(self.label_10)
        self.SL_O_Edit = QtWidgets.QLineEdit(group_box)
        self.SL_O_Edit.setObjectName("SL_O_Edit")
        self.horizontalLayout_4.addWidget(self.SL_O_Edit)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem3)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)



        _translate = QtCore.QCoreApplication.translate
        # group_box.setWindowTitle(_translate("Form", "Form"))
        group_box.setTitle(_translate("Form", "Motor 1"))
        self.label_6.setText(_translate("Form", "Aktuelle Position:"))
        self.Units_label.setText(_translate("Form", "NE"))
        self.minusBtn.setText(_translate("Form", "-"))
        self.SchrittEdit.setText(_translate("Form", "100"))
        self.plusBtn.setText(_translate("Form", "+"))
        self.label_7.setText(_translate("Form", "Gehe zu:"))
        self.NullBtn.setText(_translate("Form", "Null Einstellen"))
        self.StopButton.setText(_translate("Form", "Stop"))
        self.label_8.setText(_translate("Form", "Soft Limits:"))
        self.label_9.setText(_translate("Form", "unten:"))
        self.label_10.setText(_translate("Form", "oben:"))

        QtCore.QMetaObject.connectSlotsByName(group_box)


class VideoWidget(QLabel):

    def __init__(self, parent: Optional[QWidget]):
        super(VideoWidget, self).__init__(parent)

        sizePolicy = QtWidgets.QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setSizePolicy(sizePolicy)

        self.dark_bg_is_on = False

    def set_dark_bg(self):
        grey = QPixmap(self.width(), self.height())
        grey.fill(QColor('darkGray'))
        self.setPixmap(grey)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:

        super(VideoWidget, self).resizeEvent(a0)
        if self.dark_bg_is_on:
            self.set_dark_bg()

    # def set_dark_bg(self):
    #     grey = QPixmap(self.width(), self.height())
    #     grey.fill(QColor('darkGray'))
    #     self.setPixmap(grey)


class MicroscopeScheme(GraphicField):

    def __init__(self, parent: QWidget | None = None):

        super().__init__(parent)
        self.arrow_length = 61
        self.names_rel_font_size = 0.62  # Font-size relativ zu arrow_length
        self.axes_rel_font_size = 0.5  # Font-size relativ zu arrow_length
        self.arrow_parameters = {'arrow_head_rel_width': 0.3,
                                 'round_arrow_head_rel_width': 0.35,
                                 'round_arrow_head_rotation': 15}

        self.round_axis_parameters = {'rel_width': 0.65}
        self.axis_parameters = {'notation_shift': (0.55, 0.55)}

        self.pen_width = 1
        self.pen_width_activated = 2
        self.color_base = QColor('darkblue')
        self.color_activated = QColor('Orange')

    def names_font_size(self) -> int:

        return round(self.names_rel_font_size * self.norm_to_pixel_rel(self.arrow_length))


class MicroscopeZone(GraphicZone):

    def __init__(self, micr_scheme: MicroscopeScheme,
                 name: str,
                 name_pos: point_n,
                 axes_pos: point_n,
                 pointer_line: Tuple[point_n, point_n],
                 axes_to_enable: Dict[str, bool] | None = None,
                 mask_file: str | None = None):
        super().__init__(micr_scheme, mask_file=mask_file)

        if axes_to_enable is None:
            axes_to_enable = {}

        self.micr_scheme = micr_scheme
        self.name = name
        self.name_pos = name_pos
        self.pointer_line = pointer_line

        self.axes = Axes_Generator(self.micr_scheme, axes_pos,
                                   self.micr_scheme.arrow_length,
                                   self.micr_scheme.axes_rel_font_size,
                                   **axes_to_enable,
                                   pen_width=self.micr_scheme.pen_width,
                                   color_base=self.micr_scheme.color_base,
                                   color_activated=self.micr_scheme.color_activated,
                                   pen_width_activated=self.micr_scheme.pen_width_activated,
                                   plus_minus=False,
                                   arrow_parameters=self.micr_scheme.arrow_parameters,
                                   axis_parameters=self.micr_scheme.axis_parameters,
                                   round_axis_parameters=self.micr_scheme.round_axis_parameters)

        self.mouse_enter.connect(self.mouse_enter_event)
        self.mouse_leave.connect(self.mouse_leave_event)

    def set_activated(self, activated: bool):
        self.activated = activated
        self.axes.set_activated(activated)
        self.micr_scheme.update()

    def mouse_enter_event(self):
        self.set_activated(True)

    def mouse_leave_event(self):
        self.set_activated(False)

    def paint(self, painter: QPainter_ext):

        # set pen and font
        font = painter.font()
        if self.activated:
            pen = QPen(self.micr_scheme.color_activated, self.micr_scheme.pen_width_activated, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            font.setBold(True)
        else:
            pen = QPen(self.micr_scheme.color_base, self.micr_scheme.pen_width, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            font.setBold(False)

        # Name schreiben
        # font = QFont('Arial', self.micr_scheme.names_font_size())
        font.setPointSize(self.micr_scheme.names_font_size())
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 103)
        painter.setFont(font)

        pos = self.micr_scheme.norm_to_pixel_coord_int(*self.name_pos)
        painter.drawText_centered(pos, self.name)

        # Pointerlinie zeichnen
        start = self.micr_scheme.norm_to_pixel_coord_int(*self.pointer_line[0])
        end = self.micr_scheme.norm_to_pixel_coord_int(*self.pointer_line[1])
        painter.drawLine(*start, *end)


def Axes_Generator(gr_field: GraphicField,
                   pos: point_n,
                   arrow_length: float,
                   font_size_rel: float = 0.15,
                   pen_width: int = 1,
                   color_base: QColor = Qt.GlobalColor.black,
                   pen_width_activated: int = 2,
                   color_activated: QColor = Qt.GlobalColor.red,
                   x: bool = False,
                   rx: bool = False,
                   y: bool = False,
                   ry: bool = False,
                   z: bool = False,
                   rz: bool = False,
                   plus_minus: bool = False,
                   arrow_parameters: dict | None = None,
                   axis_parameters: dict | None = None,
                   round_axis_parameters: dict | None = None) -> Axes:

    def add_axis(name: str, rotation: bool, definition: tuple[int, int, int], axes: Axes):

        new_axes = []
        if not plus_minus:
            new_axis = Axis(axes, name, definition, axis_parameters)
            new_axes.append(new_axis)
            if rotation:
                new_axes.append(RoundAxis(new_axis, parameters=round_axis_parameters))
        else:
            k = 1.2
            r_axis_param_adj = round_axis_parameters.copy()
            if 'axis_notation_shift' not in r_axis_param_adj.keys():
                r_axis_param_adj['axis_notation_shift'] = RoundAxis.axis_notation_shift
            if 'notation_shift' not in r_axis_param_adj.keys():
                r_axis_param_adj['notation_shift'] = RoundAxis.notation_shift
            r_axis_param_adj['axis_notation_shift'] = tuple(k * np.array(r_axis_param_adj['axis_notation_shift']))
            r_axis_param_adj['notation_shift'] = tuple(k * np.array(r_axis_param_adj['notation_shift']))

            definition = np.array(definition)
            plus_axis = Axis(axes, '+' + name, tuple(definition), axis_parameters)
            notation_shift = tuple(k * np.array(plus_axis.notation_shift))
            plus_axis.notation_shift = notation_shift
            minus_axis = Axis(axes, '-' + name, tuple(-definition), axis_parameters)
            minus_axis.notation_shift = notation_shift
            new_axes += [plus_axis, minus_axis]
            if rotation:
                new_axes.append(RoundAxis(plus_axis, '+R' + name, r_axis_param_adj))
                new_axes.append(RoundAxis(minus_axis, '-R' + name, r_axis_param_adj))
        for axis in new_axes:
            axes.axes[axis.name] = axis

    if round_axis_parameters is None:
        round_axis_parameters = {}
    if axis_parameters is None:
        axis_parameters = {}

    axes = Axes(gr_field, *pos, arrow_length, font_size_rel,
                pen_width=pen_width,
                pen_color=color_base,
                pen_width_activated=pen_width_activated,
                pen_color_activated=color_activated,
                arrow_parameters=arrow_parameters,
                axis_parameters=axis_parameters,
                round_axis_parameters=round_axis_parameters)
    if x:
        add_axis('x', rx, (-1, 0, 0), axes)
    if y:
        add_axis('y', ry, (0, 0, 1), axes)
    if z:
        add_axis('z', rz, (0, 1, 0), axes)

    return axes


class ConnectionWindow(QWidget):

    controller_connected = pyqtSignal([dict])
    controller_disconnected = pyqtSignal([tuple])

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Verbindung")
        self.resize(636, 295)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.verticalLayout)

        self.conn_widgets: List[ConnectionWidget] = []

        self.mcc2_cw = MCC2_SerialConnectionWidget(self, "Phytron Box (MCC2)", 'input/MCC2_Motoren_config.csv')
        self.add_connection_widget(self.mcc2_cw)

        if MODE == 'emulator':
            self.mcc2_jet_cw = MCC2_SerialConnectionWidget(self, "Phytron Jet  (MCC2)", 'input/Jet_box_config_emulator.csv')
        else:
            self.mcc2_jet_cw = MCC2_SerialConnectionWidget(self, "Phytron Jet  (MCC2)", 'input/Jet_box_config.csv')
        self.add_connection_widget(self.mcc2_jet_cw)

        self.mcs_cw = MCS_SerialConnectionWidget(self, "SmarAct (MCS)", 'input/MCS_Motoren_config.csv')
        self.add_connection_widget(self.mcs_cw)

        self.mcs2_cw = MCS2_EthernetConnectionWidget(self, "SmarAct (MCS2)", 'input/MCS2_Motoren_config.csv')
        self.add_connection_widget(self.mcs2_cw)

        self.line = QtWidgets.QFrame(self)
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout.addWidget(self.line)

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding,
                                            QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem4)
        self.conn_all_btn = QtWidgets.QPushButton(self)
        self.conn_all_btn.setText('alle verbinden')
        self.horizontalLayout.addWidget(self.conn_all_btn)
        self.disconn_all_btn = QtWidgets.QPushButton(self)
        self.disconn_all_btn.setText('alle trennen')
        self.horizontalLayout.addWidget(self.disconn_all_btn)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.conn_all_btn.clicked.connect(self.connect_all)
        self.disconn_all_btn.clicked.connect(self.disconnect_all)

        self.boxes_cluster = mc.BoxesCluster()

        self.error_reports: Dict[mc.Motor, int] = {}

        self.make_saved_session_data_backup()

    def motor_error_report(self, motor: mc.Motor):

        if motor in self.error_reports.keys():
            self.error_reports[motor] += 1
            if self.error_reports[motor] >= 3:
                contr_name = self.disconnect_controller_by_motor(motor)
                if contr_name is not None:
                    QMessageBox.warning(None, "Fehler!",
                                        f'Den Kontroller "{contr_name}" wurde wegen eines Fehlers getrennt!')
        else:
            self.error_reports[motor] = 1

    def cancel_motor_error_report(self, motor: mc.Motor):

        if motor in self.error_reports.keys():
            del self.error_reports[motor]

    def disconnect_controller_by_motor(self, motor: mc.Motor) -> str | None:
        """Sucht den Kontroller, der angegebene Motor steuert, trennt den Kontroller
        und gibt den Namen des Kontrollers zurück. Gibt None zurück, wenn kein Kontroller gefunden wurde."""

        for conn_widget in self.conn_widgets:
            box = conn_widget.box
            if box is not None:
                motors_in_box = list(box.motors())
                if motor in motors_in_box:
                    conn_widget.disconnect_box()
                    return conn_widget.name
        return None

    def add_connection_widget(self, connection_widget):
        """Fügt das angegebene connection_widget hinzu."""

        self.conn_widgets.append(connection_widget)
        self.verticalLayout.addLayout(connection_widget)

    def connect_all(self):
        """Verbindet alle Kontroller."""

        for conn_widget in self.conn_widgets:
            if conn_widget.box is None:
                conn_widget.connection_btn_click()

    def disconnect_all(self):
        """Trennt alle verbundene Kontroller."""

        for conn_widget in self.conn_widgets:
            if conn_widget.box is not None:
                conn_widget.connection_btn_click()

    def open(self):

        self.show()
        self.raise_()

    @pass_all_errors_with_massage('Die Erstellung einer Sicherheitskopie von den Sitzungsdaten ist fehlgeschlagen!')
    def make_saved_session_data_backup(self, single_shot: bool = False):
        """Macht eine Sicherheitskopie von saved_session_data. Macht nichts, wenn kein Kontroller verbunden ist."""

        if self.boxes_cluster.boxes:
            shutil.copyfile("data/saved_session_data.txt", "data/saved_session_data_backup.txt")

        if not single_shot:
            QtCore.QTimer.singleShot(30000, self.make_saved_session_data_backup)

    # def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
    #
    #     super(ConnectionWindow, self).closeEvent(a0)
    #     print("conn wind closed")


class ConnectionWidget(QHBoxLayout):

    VerbButton: QtWidgets.QPushButton

    def __init__(self, conn_wind: ConnectionWindow, name: str, input_file: str):
        # super().__init__(conn_wind)
        super().__init__()

        self.conn_wind = conn_wind
        self.name = name
        self.input_file = input_file

        self.emulator: mc.Phytron_MCC2.BoxEmulator | None = None

        self.box: mc.Box | None = None
        self.connector: mc.Connector | None = None

    def is_connected(self) -> bool:
        """Gibt zuruck, ob den Kontroller verbunden wurde."""

        return self.box is None

    def connection_data(self) -> str:
        """Bekommt das Verbindung-Data aus der Felder des Widgets und gibt das zurück."""

        raise NotImplementedError

    def fill_widget_with_saved_connection_data(self, connection_data: str):
        """Füllt die Felder des Widgets mit angegebene Verbindung-Data"""

        pass

    def save_last_connection_data(self):
        """Speichert Data uber die letzte Verbindung in der Datei."""

        with open('data/' + self.name + '_last_conn_data.txt', 'w') as f:
            f.write(self.connection_data())

    def read_last_connection_data(self):
        """Liest Data uber die letzte Verbindung aus der Datei."""

        try:
            with open('data/' + self.name + '_last_conn_data.txt', 'r') as f:
                self.fill_widget_with_saved_connection_data(f.read())
        except FileNotFoundError:
            pass

    def get_communicator(self) -> mc.ContrCommunicator:

        raise NotImplementedError

    def is_emulation(self):

        return False

    def connect_box(self) -> mc.Box:

        self.disconnect_box()

        if self.is_emulation():
            self.emulator = mc.Phytron_MCC2.BoxEmulator(n_bus=5, n_axes=3, realtime=True)
            self.box = mc.Box(self.emulator, input_file=self.input_file)
        else:
            communicator = self.get_communicator()
            self.box = mc.Box(communicator, self.input_file)

        try:
            self.box.motors_cluster.read_saved_session_data()
        except FileNotFoundError:
            pass
        except FileReadError:
            mess = "Die Datei mit den gespeicherten Sitzungsdaten ist defekt!"
            try:
                self.box.motors_cluster.read_saved_session_data("data/saved_session_data_backup.txt")
                shutil.copyfile("data/saved_session_data_backup.txt", "data/saved_session_data.txt")
            except FileNotFoundError:
                mess += " Keine Sicherheitskopie gefunden."
            except FileReadError:
                mess += " Die Sicherheitskopie ist auch defekt."
            else:
                mess += " Die Sitzungsdaten wurden von der Sicherheitskopie geladen."
            finally:
                logging.warning(mess)
                QMessageBox.warning(self.conn_wind, "Fehler!", mess)



        self.conn_wind.boxes_cluster.add_box(self.box, self.name)
        self.conn_wind.controller_connected.emit(self.box.motors_cluster.motors)

        self.save_last_connection_data()
        return self.box

    def disconnect_box(self):

        if self.box is not None:
            self.conn_wind.controller_disconnected.emit(tuple(self.box.motors_cluster.motors.keys()))
            self.conn_wind.boxes_cluster.remove_box(self.box)
            try:
                self.box.close()
            except Exception:
                print('box not closed')
                pass
            self.box = None
        self._disconnect_connector()
        self.VerbButton.setText("verbinden")

    def _disconnect_connector(self):

        if self.connector is not None:
            try:
                self.connector.close()
            except Exception as err:
                self.box = None
                logging.exception(err)
                QMessageBox.warning(self.conn_wind, "Fehler!",
                                    "Den Connector wurde nicht getrennt. Fehler:\n" + traceback.format_exc())

    def connection_btn_click(self):

        if self.VerbButton.text() == 'verbinden':
            try:
                self.connect_box()
            except Exception as err:
                self.box = None
                self._disconnect_connector()
                logging.exception(err)
                QMessageBox.warning(self.conn_wind, "Verbindung fehlgeschlagen!",
                                    traceback.format_exc())
            else:
                if self.box.motors_cluster.motors:
                    self.VerbButton.setText("trennen")
                    QMessageBox.information(self.conn_wind, "Verbindung abgeschlossen!",
                                            self.box.report)
                else:
                    QMessageBox.information(self.conn_wind, "Kein Kontroller gefunden!",
                                            self.box.report)
                    self.disconnect_box()
        else:
            self.box.stop()
            self.conn_wind.boxes_cluster.save_session_data()
            self.disconnect_box()


class SerialConnectionWidget(ConnectionWidget):

    def __init__(self, conn_wind: ConnectionWindow, name: str, input_file: str):
        super().__init__(conn_wind, name, input_file)

        self.name_label = QLabel(self.conn_wind)
        self.name_label.setText(self.name)
        self.addWidget(self.name_label)

        self._line = QFrame(self.conn_wind)
        self._line.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self._line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.addWidget(self._line)

        self.port_label = QLabel(self.conn_wind)
        self.port_label.setText("Port:")
        self.addWidget(self.port_label)

        self.PortBox = QtWidgets.QComboBox(self.conn_wind)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.PortBox.sizePolicy().hasHeightForWidth())
        self.PortBox.setSizePolicy(sizePolicy)
        self.PortBox.setMinimumSize(QtCore.QSize(125, 0))
        self.PortBox.setCurrentText("")
        self.addWidget(self.PortBox)

        self.refrBtn = QtWidgets.QPushButton(self.conn_wind)
        self.refrBtn.setText("⟳")
        self.addWidget(self.refrBtn)

        spacerItem = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Policy.Minimum)
        self.addItem(spacerItem)

        self.VerbButton = QtWidgets.QPushButton(self.conn_wind)
        self.VerbButton.setText('verbinden')
        self.addWidget(self.VerbButton)

        self.refrBtn.clicked.connect(self.read_ports)
        self.VerbButton.clicked.connect(self.connection_btn_click)

        self.read_ports()
        self.read_last_connection_data()

    def connection_data(self) -> str:
        """Bekommt das Verbindung-Data aus der Felder des Widgets und gibt das zurück."""

        return self.PortBox.currentText()

    def fill_widget_with_saved_connection_data(self, connection_data: str):
        """Füllt die Felder des Widgets mit angegebene Verbindung-Data"""

        index = self.PortBox.findText(connection_data, flags=Qt.MatchFlag.MatchExactly)
        if index == -1:
            pass
        else:
            self.PortBox.setCurrentIndex(index)

    def read_ports(self):

        self.PortBox.clear()
        comlist = serial.tools.list_ports.comports()

        for element in comlist:
            self.PortBox.addItem(element.device)
        self.PortBox.addItem('Emulator')

        self.read_last_connection_data()

    def is_emulation(self):

        if self.PortBox.currentText() == 'Emulator':
            return True
        else:
            return False

    def get_communicator(self) -> mc.ContrCommunicator:

        raise NotImplementedError


class MCC2_SerialConnectionWidget(SerialConnectionWidget):

    def __init__(self, conn_wind: ConnectionWindow, name: str, input_file: str):
        super().__init__(conn_wind, name, input_file)

    def get_communicator(self) -> mc.ContrCommunicator:

        connector = mc.Phytron_MCC2.MCC2SerialConnector(port=self.PortBox.currentText())
        self.connector = connector
        return mc.Phytron_MCC2.MCC2Communicator(connector)


class MCS_SerialConnectionWidget(SerialConnectionWidget):

    def __init__(self, conn_wind: ConnectionWindow, name: str, input_file: str):
        super().__init__(conn_wind, name, input_file)

    def get_communicator(self) -> mc.ContrCommunicator:
        connector = mc.SmarAct_MCS.MCS_SerialConnector(port=self.PortBox.currentText())
        self.connector = connector
        return mc.SmarAct_MCS.MCSCommunicator(connector)


class EthernetConnectionWidget(ConnectionWidget):

    def __init__(self, conn_wind: ConnectionWindow, name: str, input_file: str):
        super().__init__(conn_wind, name, input_file)

        self.name_label = QtWidgets.QLabel(self.conn_wind)
        self.name_label.setText(self.name)
        self.addWidget(self.name_label)

        self._line = QtWidgets.QFrame(self.conn_wind)
        self._line.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self._line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.addWidget(self._line)

        self.ip_label = QtWidgets.QLabel(self.conn_wind)
        self.ip_label.setText("ip:")
        self.addWidget(self.ip_label)

        self.ipLine = QtWidgets.QLineEdit(self.conn_wind)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ipLine.sizePolicy().hasHeightForWidth())
        self.ipLine.setSizePolicy(sizePolicy)
        self.ipLine.setText("192.168.1.200")
        self.addWidget(self.ipLine)

        self.port_label = QtWidgets.QLabel(self.conn_wind)
        self.port_label.setText("Port:")
        self.addWidget(self.port_label)

        self.PortLine = QtWidgets.QLineEdit(self.conn_wind)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.PortLine.sizePolicy().hasHeightForWidth())
        self.PortLine.setSizePolicy(sizePolicy)
        self.PortLine.setText("55551")
        self.addWidget(self.PortLine)

        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding,
                                            QtWidgets.QSizePolicy.Policy.Minimum)
        self.addItem(spacerItem3)

        self.VerbButton = QtWidgets.QPushButton(self.conn_wind)
        self.VerbButton.setText('verbinden')
        self.addWidget(self.VerbButton)

        self.VerbButton.clicked.connect(self.connection_btn_click)

        self.read_last_connection_data()

    def connection_data(self) -> str:
        """Bekommt das Verbindung-Data aus der Felder des Widgets und gibt das zurück."""

        return self.ipLine.text() + ";" + self.PortLine.text()

    def fill_widget_with_saved_connection_data(self, connection_data: str):
        """Füllt die Felder des Widgets mit angegebene Verbindung-Data"""

        data = connection_data.split(';')
        if len(data) != 2:
            logging.error('Connection data is damaged.')
        else:
            ip, port = data
            self.ipLine.setText(ip)
            self.PortLine.setText(port)

    def is_emulation(self):

        if self.ipLine.text() == 'E':
            return True
        else:
            return False

    def get_communicator(self) -> mc.ContrCommunicator:

        raise NotImplementedError


class MCS2_EthernetConnectionWidget(EthernetConnectionWidget):

    def __init__(self, conn_wind: ConnectionWindow, name: str, input_file: str):
        super().__init__(conn_wind, name, input_file)

    def get_communicator(self) -> mc.ContrCommunicator:
        connector = mc.SmarAct_MCS2.MCS2_EthernetConnector(self.ipLine.text(), self.PortLine.text())
        self.connector = connector
        return mc.SmarAct_MCS2.MCS2Communicator(connector)



def calibr_wdgs_place_generator():

    for i in range(10):
        for j in range(3):
            yield i, j


class CalibrationWindow(QWidget):

    calibration_started = pyqtSignal([tuple])
    motor_is_ready = pyqtSignal(str)
    massage_signal = pyqtSignal(str, str, str)

    def __init__(self, conn_wind: ConnectionWindow, motors_zones: Dict[str, Collection[str]]):
        super().__init__()

        self.setWindowTitle('Kalibrierung')

        self.conn_wind = conn_wind
        self.calibr_widgets: Dict[str, CalibrationWidget] = {}

        self.grid = QGridLayout(self)
        self.grid.setVerticalSpacing(10)
        self.setLayout(self.grid)

        last_row = 0
        for (zone_name, motors_names), place in zip(motors_zones.items(), calibr_wdgs_place_generator()):
            calibr_widget = CalibrationWidget(self, motors_names, zone_name)
            self.calibr_widgets[zone_name] = calibr_widget
            self.grid.addWidget(calibr_widget, *place)
            last_row = place[0]

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.all_parallel_check = QCheckBox("alle parallel", self)
        self.horizontalLayout.addWidget(self.all_parallel_check)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding,
                                            QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem4)
        self.all_callibr_btn = QtWidgets.QPushButton(self)
        self.all_callibr_btn.setText('alle kalibrieren')
        self.horizontalLayout.addWidget(self.all_callibr_btn)
        self.all_stopp_btn = QtWidgets.QPushButton(self)
        self.all_stopp_btn.setText('alle stoppen')
        self.horizontalLayout.addWidget(self.all_stopp_btn)
        if len(motors_zones) > 3:
            column_span = 3
        else:
            column_span = len(motors_zones)
        self.grid.addItem(self.horizontalLayout, last_row + 1, 0, 1, column_span)

        self.all_callibr_btn.clicked.connect(self.calibrate_all)
        self.all_stopp_btn.clicked.connect(self.stop_all)
        self.all_parallel_check.stateChanged.connect(self.select_all_parallel_event)

        self.massage_signal.connect(show_message)

        self.read_settings()

    def open(self):

        self.show()
        self.raise_()

    def calibrate_all(self):

        for calibr_widgt in self.calibr_widgets.values():
            if calibr_widgt.callibr_btn.text() == 'kalibrieren':
                calibr_widgt.callibr_btn.click()

    def stop_all(self):
        for calibr_widgt in self.calibr_widgets.values():
            if calibr_widgt.callibr_btn.text() == 'Stop':
                calibr_widgt.callibr_btn.click()

    def select_all_parallel_event(self):

        for calibr_widget in self.calibr_widgets.values():
            calibr_widget.parallel_calibr_check.setChecked(self.all_parallel_check.isChecked())

    def save_settings(self):
        """Speichert die Auswahl, ob die Zonnen parallel kalibriert werden sollen."""

        with open('data/saved_calibr_settings.txt', 'w') as f:

            for name, cal_wdg in self.calibr_widgets.items():
                f.write(name + ';' + str(int(cal_wdg.parallel_calibr_check.isChecked())) + '\n')

    def read_settings(self):
        """Liest die gespeicherte Auswahl, ob die Zonnen parallel kalibriert werden sollen."""

        try:
            with open('data/saved_calibr_settings.txt', 'r') as f:
                lines = f.read().splitlines()
                for line in lines:
                    name, is_checked = line.split(';')
                    is_checked = bool(int(is_checked))
                    if name in self.calibr_widgets:
                        self.calibr_widgets[name].parallel_calibr_check.setChecked(is_checked)
        except ValueError:
            logging.warning('saved_calibr_settings Datei ist inkompatibel!')
        except FileNotFoundError:
            pass

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:

        self.save_settings()
        super(CalibrationWindow, self).closeEvent(a0)


class CalibrationWidget(QGroupBox):

    def __init__(self, calibr_wind: CalibrationWindow, motors_names: Collection[str], name: str | None = None):
        super().__init__(calibr_wind)

        if name is None:
            self.setTitle("")
        else:
            self.setTitle(name)

        self.calibr_wind = calibr_wind

        self.cal_thread = CalibrationThread(self.calibr_wind)
        self.cal_thread.calibration_complete.connect(self.calibration_complete)
        self.cal_thread.calibration_status_changed.connect(self.refresh_cal_state)

        self.v_layout = QVBoxLayout(self)
        self.setLayout(self.v_layout)

        self.parallel_calibr_check = QCheckBox("parallel kalibrieren", self)
        self.parallel_calibr_check.setChecked(True)
        self.v_layout.addWidget(self.parallel_calibr_check)

        self.line = QtWidgets.QFrame(self)
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        self.v_layout.addWidget(self.line)

        self.select_all_check = QCheckBox("", self)
        self.v_layout.addWidget(self.select_all_check)

        self.motors_check_boxes: Dict[str, QCheckBox] = {}

        for name in motors_names:
            check_box = QCheckBox(name, self)
            check_box.setEnabled(False)
            self.v_layout.addWidget(check_box)
            self.motors_check_boxes[name] = check_box

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding,
                                            QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem4)
        self.callibr_btn = QtWidgets.QPushButton(self)
        self.callibr_btn.setText('kalibrieren')
        self.horizontalLayout.addWidget(self.callibr_btn)
        self.v_layout.addItem(self.horizontalLayout)

        self.calibr_wind.conn_wind.controller_connected.connect(self.controller_connected_event)
        self.calibr_wind.conn_wind.controller_disconnected.connect(self.controller_disconnected_event)
        self.select_all_check.stateChanged.connect(self.select_all_check_event)
        self.callibr_btn.clicked.connect(self.calibrate)

    def controller_connected_event(self, motors_dict: Dict[str, Motor]):

        for name, m_check_b in self.motors_check_boxes.items():
            if name in motors_dict.keys():
                if motors_dict[name].is_calibratable():
                    m_check_b.setEnabled(True)
                    m_check_b.setChecked(True)

    def controller_disconnected_event(self, motors_names: Tuple[str]):

        for name, m_check_b in self.motors_check_boxes.items():
            if name in motors_names:
                m_check_b.setEnabled(False)
                m_check_b.setChecked(False)

    def select_all_check_event(self):

        for check_box in self.motors_check_boxes.values():
            if check_box.isEnabled():
                check_box.setChecked(self.select_all_check.isChecked())

    def calibration_complete(self):

        self.callibr_btn.setText("kalibrieren")
        self.calibr_wind.conn_wind.boxes_cluster.save_session_data()

        for conn_widg in self.calibr_wind.conn_wind.conn_widgets:
            if conn_widg.emulator is not None:
                conn_widg.emulator.realtime = True

    def calibrate(self):

        if self.callibr_btn.text() == "kalibrieren":
            self.callibr_btn.setText("Stop")

            for conn_widg in self.calibr_wind.conn_wind.conn_widgets:
                if conn_widg.emulator is not None:
                    conn_widg.emulator.realtime = False

            motors_names_to_calibration = []
            for check_box in self.motors_check_boxes.values():
                if check_box.isChecked() and check_box.isEnabled():
                    motors_names_to_calibration.append(check_box.text())

            self.cal_thread.start(motors_names_to_calibration, self.parallel_calibr_check.isChecked())

        else:
            self.cal_thread.stop = True

    def refresh_cal_state(self):

        for check_box in self.motors_check_boxes.values():
            if check_box.text() in self.cal_thread.motors_in_calibration:
                check_box.setStyleSheet("color: orange;")
            else:
                check_box.setStyleSheet("color:;")


class CalibrationThread(QThread):
    """Thread für Kalibrierung der Motoren"""

    calibration_status_changed = pyqtSignal()
    calibration_complete = pyqtSignal()
    stop = False

    def __init__(self, calibr_wind: CalibrationWindow):

        super().__init__()
        self.calibr_wind = calibr_wind
        self.motors_names_to_calibration = []
        self.motors_in_calibration = []
        self.parallel = False

    def start(self, motors_names_to_calibration: Collection[str], parallel: bool):
        self.motors_names_to_calibration = list(motors_names_to_calibration)
        self.parallel = parallel
        self.stop = False
        super().start()

    def run(self):
        calibration_reporter = GuiCalibrationReporter(self)
        stop_indicator = GuiStopIndicator(self)

        traceback_text = ''
        try:
            self.calibr_wind.conn_wind.boxes_cluster.calibrate_motors(names_to_calibration=self.motors_names_to_calibration,
                                                                      stop_indicator=stop_indicator,
                                                                      reporter=calibration_reporter,
                                                                      parallel=self.parallel)
        except Exception as err:
            logging.exception(err)
            traceback_text = traceback.format_exc()
            if not self.motors_in_calibration:
                self.calibr_wind.massage_signal.emit('error', "Fehler!",
                                                     'Während der Kalibrierung ist ein Fehler aufgetreten:\n'
                                                     + traceback_text)

        if self.motors_in_calibration:
            err_message = f'Kalibrieren der Motors {self.motors_in_calibration} ist fehlgeschlagen.'
            if traceback_text:
                err_message += ' Fehler:\n' + traceback_text
            self.calibr_wind.massage_signal.emit('error', "Kalibrieren fehlgeschlagen!", err_message)
            self.motors_in_calibration = []
            self.calibration_status_changed.emit()
        self.calibration_complete.emit()


class GuiCalibrationReporter(WaitReporter):
    """Durch dieses Objekt kann man während eine Kalibrierung die Liste der im Moment laufenden Motoren bekommen.
            Es wird als argument für PBox.calibrate_motors() verwendet."""

    def __init__(self, cal_thread: CalibrationThread):
        self.cal_thread = cal_thread

    def set_wait_list(self, wait_list: Set[str]):
        self.cal_thread.calibr_wind.calibration_started.emit(tuple(wait_list))
        self.cal_thread.motors_in_calibration = list(wait_list)
        self.cal_thread.calibration_status_changed.emit()

    def motor_is_done(self, motor_name: str):
        self.cal_thread.calibr_wind.motor_is_ready.emit(motor_name)
        self.cal_thread.motors_in_calibration.remove(motor_name)
        self.cal_thread.calibration_status_changed.emit()


class GuiStopIndicator(StopIndicator):
    """Durch dieses Objekt kann man Kalibrierung abbrechen.
    Es wird als argument für PBox.calibrate_motors() verwendet."""

    def __init__(self, kal_thread: CalibrationThread):
        self.kal_thread = kal_thread

    def has_stop_requested(self) -> bool:
        return self.kal_thread.stop


# def motors_wdgs_place_generator():
#
#     yield 1, 0
#     yield 2, 0
#     yield 1, 1
#     yield 2, 1
#     for i in range(3, 10):
#         for j in range(2):
#             yield i, j


def motors_wdgs_place_generator():

    for i in range(1, 10):
        for j in range(2):
            yield i, j


class MotorWindow(QWidget):

    def __init__(self, conn_window: ConnectionWindow, calibr_window: CalibrationWindow | None = None,
                 name: str | None = None):
        super().__init__()

        self.conn_window = conn_window
        self.calibr_window = calibr_window

        if name is not None:
            self.setWindowTitle(name)
        else:
            self.setWindowTitle("MotorWindow")

        self.motors_widgets: Dict[str, MotorWidget] = {}

        self.conn_window.controller_connected.connect(self.controller_connected_event)
        self.conn_window.controller_disconnected.connect(self.controller_disconnected_event)

        if calibr_window is not None:
            self.calibr_window.calibration_started.connect(self.calibration_started_event)
            self.calibr_window.motor_is_ready.connect(self.calibration_complete_event)

    def open(self):

        if self.isHidden():
            self.show()
        self.raise_()

    # @print_ex_time
    def update_saved_session_data(self, single_shot: bool = False):

        motors = []
        for m_widget in self.motors_widgets.values():
            if m_widget.motor is not None and not m_widget.is_sleeping:
                motors.append(m_widget.motor)
        if motors:
            motors_cluster = mc.MotorsCluster(motors)
            try:
                motors_cluster.save_session_data()
            except:
                print("update_saved_session_data fehlgeschlagen")

        if not single_shot and not self.isHidden():
            QtCore.QTimer.singleShot(3000, self.update_saved_session_data)

    def controller_connected_event(self, motors_dict: Dict[str, Motor]):

        for name, m_widg in self.motors_widgets.items():
            if name in motors_dict.keys():
                m_widg.init(motors_dict[name], awake=self.isVisible())

    def controller_disconnected_event(self, motors_names: Tuple[str]):

        for name, m_widg in self.motors_widgets.items():
            if name in motors_names:
                m_widg.discard()

    def calibration_started_event(self, motors_names: Collection[str]):

        for name, m_widg in self.motors_widgets.items():
            if name in motors_names:
                m_widg.sleep()
                m_widg.setTitle(name + ' (Kalibrierung)')

    def calibration_complete_event(self, motor_name: str):

        for name, m_widg in self.motors_widgets.items():
            if name == motor_name:
                m_widg.awake()
                m_widg.setTitle(name)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:

        for m_widg in self.motors_widgets.values():
            m_widg.sleep()
        super(MotorWindow, self).closeEvent(a0)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:

        super(MotorWindow, self).showEvent(a0)
        for m_widg in self.motors_widgets.values():
            m_widg.awake()
        self.update_saved_session_data()


class StandardMotorWindow(MotorWindow):

    def __init__(self, conn_window: ConnectionWindow,
                 motors_names: Collection[str],
                 calibr_window: CalibrationWindow | None = None,
                 name: str | None = None):

        super().__init__(conn_window, calibr_window, name)

        # self.resize(300, 300)
        self.grid = QGridLayout(self)
        self.grid.setVerticalSpacing(10)
        self.setLayout(self.grid)

        for name, place in zip(motors_names, motors_wdgs_place_generator()):
            motor_widget = MotorWidget(self, name)
            self.motors_widgets[name] = motor_widget
            self.grid.addWidget(motor_widget, *place)

            if name in self.conn_window.boxes_cluster.names():
                motor = self.conn_window.boxes_cluster.get_motor(name)
                motor_widget.init(motor, awake=False)

        self.motor_scheme = MicroscopZoneChema(self)
        if len(motors_names) > 1:
            column_span = 2
        else:
            column_span = 1
        self.grid.addWidget(self.motor_scheme, 0, 0, 1, column_span)

    def open(self):

        if self.isHidden():
            self.show()

            x_range, y_range = self.motor_scheme.x_range, self.motor_scheme.y_range
            left, top, right, bottom = self.grid.getContentsMargins()
            min_w = self.width() - left - right
            self.motor_scheme.setMinimumWidth(min_w)
            self.motor_scheme.setMinimumHeight(round(y_range / x_range * min_w))

        self.raise_()


class MicroscopZoneChema(GraphicField):

    def __init__(self, motor_wind: MotorWindow, img: str | None = None):
        super().__init__(motor_wind, 1000, 300)

        self.motor_wind = motor_wind

        if img is not None:
            self.set_background_from_file(img)

        self.__closed = True

        axes_to_enable: Dict[str, bool] = {}
        axes_mwidgs_dict: Dict[str, MotorWidget] = {}
        for name, motor_widg in self.motor_wind.motors_widgets.items():
            for axis_name in ['X', 'Y', 'Z']:
                axis_name_rot = 'R' + axis_name
                if name[-2:] == axis_name_rot:
                    axes_to_enable[axis_name_rot.lower()] = True
                    axes_to_enable[axis_name.lower()] = True
                    axes_mwidgs_dict['R' + axis_name.lower()] = motor_widg
                elif name[-1] == axis_name:
                    axes_to_enable[axis_name.lower()] = True
                    axes_mwidgs_dict[axis_name.lower()] = motor_widg

        width = self.y_range
        self.axes = Axes_Generator(self, (width/2, width/2), width/4, 0.2, **axes_to_enable,
                                   plus_minus=True,
                                   color_activated=QColor("orange"))
        # self.axes = Axes_Generator(self,
        #                            (width/2, width/2),
        #                            width/4,
        #                            0.2,
        #                            **axes_to_enable,
        #                            pen_width=self.micr_scheme.pen_width,
        #                            color_base=self.micr_scheme.color_base,
        #                            color_activated=self.micr_scheme.color_activated,
        #                            pen_width_activated=self.micr_scheme.pen_width_activated,
        #                            plus_minus=False,
        #                            arrow_parameters=self.micr_scheme.arrow_parameters,
        #                            axis_parameters=self.micr_scheme.axis_parameters,
        #                            round_axis_parameters=self.micr_scheme.round_axis_parameters)

        for axis_name, m_widg in axes_mwidgs_dict.items():
            m_widg.axis_p = self.axes.axes['+' + axis_name]
            m_widg.axis_m = self.axes.axes['-' + axis_name]

    def showEvent(self, a0: QtGui.QShowEvent) -> None:

        super(MicroscopZoneChema, self).showEvent(a0)
        self.__closed = False

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:

        super(MicroscopZoneChema, self).closeEvent(a0)
        self.__closed = True


MODE = "emulator"
MODE = "real"


def vimba_is_available() -> bool:
    """Gibt bool Wert zurück, ob Betriebsystem passt und kein Emulator Mode an ist."""

    return platform.system() in ['Windows', 'Linux'] and MODE == 'real'


if vimba_is_available():
    from mscontr.microwatcher.vimba_camera import Camera, get_cameras_list


class PlasmaMotorWindow(MotorWindow):

    massage_signal = pyqtSignal(str, str, str)
    VideoField: VideoWidget
    checkBox_laser: QCheckBox
    gainEdit: QLineEdit
    exposeEdit: QLineEdit
    JetXBox: MotorWidget
    JetZBox: MotorWidget
    comboBox_camera: QComboBox
    CalPlasmaBtn: QPushButton
    CalEnlBtn: QPushButton
    centreBtn: QPushButton
    CalEnlBtn: QPushButton
    StopButton: QPushButton
    plusBtn: QPushButton
    minusBtn: QPushButton
    cam_settings_btn: QPushButton
    recordBtn: QPushButton

    def __init__(self, conn_window: ConnectionWindow,
                 calibr_window: CalibrationWindow | None = None,
                 name: str | None = None):

        super().__init__(conn_window, calibr_window, name)

        loadUi('ui_forms/PlasmaMotorWindow.ui', self)

        self.is_recording = False
        self.stop_indicator = StandardStopIndicator()

        self.motors_widgets = {'JetX': self.JetXBox, 'JetZ': self.JetZBox,
                               'LaserZ': self.LaserZBox, 'LaserY': self.LaserYBox}
        self.plasma_watcher: PlasmaWatcher | None = None
        self.discard_plasma_watcher()

        self.jet_emulator: JetEmulator | None = None
        if MODE == "emulator":
            phi = 90
            psi = 45
            g1 = 10
            g2 = 10
            shift = 43

            self.jet_emulator = JetEmulator(phi=phi, psi=psi, g1=g1, g2=g2, jet_d=g1 * 7, laser_jet_shift=1500, def_init=False)

        self.CalPlasmaBtn.clicked.connect(self.calibr_plasma)
        self.CalEnlBtn.clicked.connect(self.calibr_enl)
        self.centreBtn.clicked.connect(self.centre_nozzle)
        self.recordBtn.clicked.connect(self.record)
        self.plusBtn.clicked.connect(self.plus_step)
        self.minusBtn.clicked.connect(self.minus_step)
        self.StopButton.clicked.connect(self.stop)
        self.cam_settings_btn.clicked.connect(self.cam_settings)

        self.checkBox_laser.stateChanged.connect(self.laser_status_changed)
        self.gainEdit.editingFinished.connect(self.set_gain)
        self.exposeEdit.editingFinished.connect(self.set_exposure)
        self.comboBox_camera.currentTextChanged.connect(self.change_camera)

        self.massage_signal.connect(show_message)

        self.exposeEdit.setValidator(QtGui.QIntValidator())
        self.gainEdit.setValidator(QtGui.QIntValidator())

        self._dark_exposure = 10000
        self._normal_exposure = 40000

        self._dark_gain = 10
        self._normal_gain = 10

        self.camera1: Camera | None = None
        self.camera2: Camera | None = None
        self.camera: Camera | None = None

        self.cam_settings_wind = CamerasDialog(self)

        self.get_cameras()

        self.camera = self.camera1
        self.change_camera()

    def cam_settings(self):

        self.cam_settings_wind.show()
        self.cam_settings_wind.refresh_list()

    def init_plasma_watcher(self):

        self.stop_all_tasks()

        jet_x = self.motors_widgets['JetX'].motor
        jet_z = self.motors_widgets['JetZ'].motor
        laser_z = self.motors_widgets['LaserZ'].motor
        laser_y = self.motors_widgets['LaserY'].motor

        phi = 80
        psi = 50

        if None not in [jet_x, jet_z, self.camera1, self.camera2]:
            self.plasma_watcher = PlasmaWatcher(self.camera1, self.camera2, jet_x=jet_x, jet_z=jet_z,
                                                laser_z=laser_z, laser_y=laser_y,
                                                phi=phi, psi=psi)
            self.CalEnlBtn.setEnabled(True)
            self.centreBtn.setEnabled(True)
            self.CalPlasmaBtn.setEnabled(True)
            self.StopButton.setEnabled(True)
            self.plusBtn.setEnabled(True)
            self.minusBtn.setEnabled(True)
        else:
            self.plasma_watcher = None

    def discard_plasma_watcher(self):

        self.stop_all_tasks()
        self.plasma_watcher = None
        self.CalEnlBtn.setEnabled(False)
        self.centreBtn.setEnabled(False)
        self.CalPlasmaBtn.setEnabled(False)
        self.StopButton.setEnabled(False)
        self.plusBtn.setEnabled(False)
        self.minusBtn.setEnabled(False)

    def __set_motoren_in_emulator(self):

        if self.jet_emulator is not None:
            self.jet_emulator.jet_x = self.motors_widgets['JetX'].motor
            self.jet_emulator.jet_z = self.motors_widgets['JetZ'].motor
            self.jet_emulator.laser_z = self.motors_widgets['LaserZ'].motor
            self.jet_emulator.laser_y = self.motors_widgets['LaserY'].motor

    def controller_connected_event(self, motors_dict: Dict[str, Motor]):

        super(PlasmaMotorWindow, self).controller_connected_event(motors_dict)
        if self.plasma_watcher is None:
            self.init_plasma_watcher()
        self.__set_motoren_in_emulator()

    def controller_disconnected_event(self, motors_names: Tuple[str]):

        super(PlasmaMotorWindow, self).controller_disconnected_event(motors_names)
        if 'JetX' in motors_names or 'JetZ' in motors_names:
            self.discard_plasma_watcher()
        elif 'LaserZ' in motors_names or 'LaserY' in motors_names:
            self.init_plasma_watcher()
        self.__set_motoren_in_emulator()

    def stop_all_tasks(self):

        tasks_buttons = [self.CalPlasmaBtn, self.CalEnlBtn, self.centreBtn]
        for btn in tasks_buttons:
            if btn.text() == "stop":
                btn.click()

        if self.is_recording:
            self.record()

    def change_camera(self):

        if self.camera is not None:
            try:
                self.camera.stop_stream()
            except Exception as err:
                logging.exception(err)
                QMessageBox.warning(None, "Unerwartete Fehler!",
                                    "Unerwartete Fehler:\n" + traceback.format_exc())
            if self.is_recording:
                self.record()
            self.camera.disconnect_from_stream(self.show_frame)

        if self.comboBox_camera.currentText() == "camera 1":
            self.camera = self.camera1
        elif self.comboBox_camera.currentText() == "camera 2":
            self.camera = self.camera2

        if self.camera is not None:
            self.camera.connect_to_stream(self.show_frame)
            if not self.isHidden():
                try:
                    self.camera.start_stream()
                except Exception as err:
                    logging.exception(err)
                    QMessageBox.warning(None, "Action fehlgeschlagen!",
                                        "Es hat nicht geklappt, den Stream von der Kamera zu starten. "
                                        "Fehler:\n" + traceback.format_exc())
                    return

                self.VideoField.dark_bg_is_on = False
                self.recordBtn.setEnabled(True)
                self.gainEdit.setEnabled(True)
                self.exposeEdit.setEnabled(True)

            self._set_gain_exposure()
        else:
            self.VideoField.dark_bg_is_on = True

            self._set_gain_exposure()

            self.recordBtn.setEnabled(False)
            self.gainEdit.setEnabled(False)
            self.exposeEdit.setEnabled(False)

    def get_cameras(self):

        self.stop_all_tasks()
        self.camera1 = None
        self.camera2 = None
        if MODE == "emulator":

            self.camera1 = CameraEmulator(1, self.jet_emulator)
            self.camera2 = CameraEmulator(2, self.jet_emulator)
            # if jet_cal:
            #     plasma_watcher.g1 = g1
            #     plasma_watcher.g2 = g2

            self.jet_emulator.laser_on = True

        elif vimba_is_available():

            id1, id2 = self.cam_settings_wind.cameras_ids()
            try:
                if id1:
                    self.camera1 = Camera(id1, bandwidth=60000000)

                if id2:
                    self.camera2 = Camera(id2, bandwidth=60000000)
            except Exception as err:
                logging.exception(err)
                QMessageBox.warning(None, "Action fehlgeschlagen!",
                                    "Es hat nicht geklappt, Kameras zu verbinden. Fehler:\n" + traceback.format_exc())

        self.change_camera()
        self.init_plasma_watcher()

        # self.camera1 = Camera('DEV_000F314E840B', bandwidth=60000000)
        # self.camera2 = Camera('DEV_000F314E840A', bandwidth=60000000)

    @pass_all_errors_with_massage('Videoaufnahme ist fehlgeschlagen!')
    def record(self, cheked=False):

        if self.camera is not None:
            if not self.is_recording:
                address = QFileDialog.getSaveFileName(self, 'Save video', '', "AVI Movie File (*.avi)")[0]
                if address == '':
                    return
                self.camera.start_video_record(address, start_stream=True)
                self.recordBtn.setText("stop recording")
                self.is_recording = True
            else:
                self.camera.stop_video_record()
                self.recordBtn.setText("record video")
                self.is_recording = False
        else:
            QMessageBox.warning(None, "Fehler!",
                                "Keine Kamera ist verbunden!")

    def laser_status_changed(self):

        if self.checkBox_laser.isChecked():
            self._normal_gain = int(self.gainEdit.text())
            self._normal_exposure = int(self.exposeEdit.text())

            self.gainEdit.setText(str(self._dark_gain))
            self.exposeEdit.setText(str(self._dark_exposure))
        else:
            self._dark_gain = int(self.gainEdit.text())
            self._dark_exposure = int(self.exposeEdit.text())

            self.gainEdit.setText(str(self._normal_gain))
            self.exposeEdit.setText(str(self._normal_exposure))

        if self.camera is not None:
            self.set_gain()
            self.set_exposure()

    @pass_all_errors_with_massage('gain Änderung ist fehlgeschlagen!')
    def set_gain(self):
        self.camera.set_gain(int(self.gainEdit.text()))

    @pass_all_errors_with_massage('exposure Änderung ist fehlgeschlagen!')
    def set_exposure(self):
        self.camera.set_exposure(int(self.exposeEdit.text()))

    def _set_gain_exposure(self):

        if self.checkBox_laser.isChecked():
            self.gainEdit.setText(str(self._dark_gain))
            self.exposeEdit.setText(str(self._dark_exposure))
        else:
            self.gainEdit.setText(str(self._normal_gain))
            self.exposeEdit.setText(str(self._normal_exposure))

        if self.camera is not None:
            self.set_gain()
            self.set_exposure()

    def show_frame(self, frame):
        qt_img = self.convert_cv_qt(frame)
        self.VideoField.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""

        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)

        if self.checkBox_cmark.isChecked():
            center = round(rgb_image.shape[1]/2)
            rgb_image = cv2.line(rgb_image, (center, 0), (center, rgb_image.shape[0]), (0, 255, 0), 2)

        if self.VideoField.width() >= self.VideoField.height()*2048/1088:
            height = int(self.VideoField.height())
            width = int(height*2048/1088)
        else:
            width = self.VideoField.width()
            height = int(width*1088/2048)

        dim = (width, height)
        rgb_image = cv2.resize(rgb_image, dim, interpolation=cv2.INTER_AREA)

        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        return QPixmap.fromImage(convert_to_Qt_format)

    @pass_all_errors_with_massage('Kalibrierung des Plasmas ist fehlgeschlagen!')
    def calibr_plasma(self, cheked=False):

        def final_action():

            self.CalPlasmaBtn.setText("calibr plasma")
            self.centreBtn.setEnabled(True)
            self.CalEnlBtn.setEnabled(True)

        @pass_all_errors_in_thread_with_massage('Kalibrierung des Plasmas ist fehlgeschlagen!', final_action)
        def in_thread(self):

            self.plasma_watcher.calibrate_plasma(mess_per_point=mess_per_point, on_the_spot=True,
                                                 stop_indicator=self.stop_indicator)
            final_action()

        if self.CalPlasmaBtn.text() == "calibr plasma":

            self.centreBtn.setEnabled(False)
            self.CalEnlBtn.setEnabled(False)

            mess_per_point = 5
            if self.jet_emulator is not None:
                self.jet_emulator.flicker_sigma = 0.1
            self.stop_indicator.restore()

            self.checkBox_laser.setChecked(True)
            self.camera1.start_stream()
            self.camera2.start_stream()

            threading.Thread(target=in_thread, args=[self]).start()
            self.CalPlasmaBtn.setText("stop")
        elif self.CalPlasmaBtn.text() == "stop":
            self.stop_indicator.stop()

    def centre_nozzle(self):

        def final_action():

            self.centreBtn.setText("zentrieren")
            self.CalPlasmaBtn.setEnabled(True)
            self.CalEnlBtn.setEnabled(True)

        @pass_all_errors_in_thread_with_massage('Zentrieren des Jets  ist fehlgeschlagen!', final_action)
        def in_thread(self):

            self.plasma_watcher.centre_the_nozzle(stop_indicator=self.stop_indicator)
            final_action()

        if self.centreBtn.text() == "zentrieren":
            self.CalPlasmaBtn.setEnabled(False)
            self.CalEnlBtn.setEnabled(False)
            self.stop_indicator.restore()
            self.checkBox_laser.setChecked(False)
            threading.Thread(target=in_thread, args=[self]).start()
            self.centreBtn.setText("stop")
        elif self.centreBtn.text() == "stop":
            self.stop_indicator.stop()

    def calibr_enl(self):

        def in_thread():
            g1, g2 = self.plasma_watcher.g1, self.plasma_watcher.g2
            try:
                report = self.plasma_watcher.calibrate_enl(init_step=100, rel_err=0.01, n_points=10,
                                                           stop_indicator=self.stop_indicator)
                print(report)
                self.massage_signal.emit("info", "Aktion abgeschlossen.",
                                       "Die Messung der Vergrößerungen der Kameras ist abgeschlossen:\n"
                                       + report)
                if self.stop_indicator.has_stop_requested():
                    self.plasma_watcher.g1, self.plasma_watcher.g2 = g1, g2
            except Exception as err:
                logging.exception(err)
                self.massage_signal.emit("error", "Aktion fehlgeschlagen!",
                                       "Messung der Vergrößerungen der Kameras ist fehlgeschlagen! Fehler:\n"
                                       + traceback.format_exc())
                self.plasma_watcher.g1, self.plasma_watcher.g2 = g1, g2
            finally:
                self.CalEnlBtn.setText("calibr enl")
                self.CalPlasmaBtn.setEnabled(True)
                self.centreBtn.setEnabled(True)

        if self.CalEnlBtn.text() == "calibr enl":
            self.CalPlasmaBtn.setEnabled(True)
            self.centreBtn.setEnabled(True)
            self.stop_indicator.restore()
            self.checkBox_laser.setChecked(False)
            threading.Thread(target=in_thread).start()
            self.CalEnlBtn.setText("stop")
        elif self.CalEnlBtn.text() == "stop":
            self.stop_indicator.stop()

    def move_in_cam_coord(self, shift: float):

        if self.comboBox_camera.currentText() == "camera 1":
            camera_coord = self.plasma_watcher.camera1_coord
        elif self.comboBox_camera.currentText() == "camera 2":
            camera_coord = self.plasma_watcher.camera2_coord
        else:
            raise ValueError("Unbekante Kamerabezeichnung!")

        shift_x, shift_z = camera_coord.cc_to_mc(x_=0, z_=shift)

        self.plasma_watcher.move_jet(shift_x, shift_z, units='displ')

    @m_err_handl_with_massage
    def plus_step(self, checked=False):
        self.move_in_cam_coord(float(self.SchrittEdit.text()))

    @m_err_handl_with_massage
    def minus_step(self, checked=False):
        self.move_in_cam_coord(-float(self.SchrittEdit.text()))

    @m_err_handl_with_massage
    def stop(self, checked=False):
        self.plasma_watcher.jet_x.stop()
        self.plasma_watcher.jet_z.stop()

    def closeEvent(self, a0: QtGui.QCloseEvent):

        self.stop_all_tasks()
        for camera in [self.camera1, self.camera2]:
            try:
                if camera is not None:
                    camera.stop_stream()
            except Exception as err:
                logging.exception(err)
        return super().closeEvent(a0)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:

        super(PlasmaMotorWindow, self).showEvent(a0)
        self.change_camera()


class CamerasDialog(QWidget):

    def __init__(self, plasm_wind: PlasmaMotorWindow):
        super().__init__()
        self.plasm_wind = plasm_wind

        self.setWindowTitle('Kameras Einstellung')

        self.grid = QGridLayout(self)
        self.grid.setVerticalSpacing(10)
        self.setLayout(self.grid)

        self.cam1_label = QLabel('Kamera 1:', self)
        self.grid.addWidget(self.cam1_label, 0, 0)
        self.cam1_box = QComboBox(self)
        self.grid.addWidget(self.cam1_box, 0, 1)

        self.cam2_label = QLabel('Kamera 2:', self)
        self.grid.addWidget(self.cam2_label, 1, 0)
        self.cam2_box = QComboBox(self)
        self.grid.addWidget(self.cam2_box, 1, 1)

        self.refr_btn = QtWidgets.QPushButton('⟲', self)
        self.grid.addWidget(self.refr_btn, 0, 2, 2, 1)

        self.apply_btn = QtWidgets.QPushButton('anwenden', self)
        self.grid.addWidget(self.apply_btn, 2, 0, 1, 2)

        self.saved_ids: List[str, str] = ['', '']

        self.read_saved_ids()
        self.refresh_list()

        self.refr_btn.clicked.connect(self.refresh_list)
        self.apply_btn.clicked.connect(self.apply)

    def apply(self):

        if vimba_is_available():
            self.plasm_wind.get_cameras()

            id1, id2 = self.cameras_ids()

            if id1:
                self.saved_ids[0] = id1
            if id2:
                self.saved_ids[1] = id2

            if id1 or id2:
                self.save_last_ids()

    def cameras_ids(self) -> Tuple[str, str]:

        return self.cam1_box.currentText(), self.cam2_box.currentText()

    def refresh_list(self):

        if vimba_is_available():
            try:
                self.cam1_box.clear()
                self.cam2_box.clear()
                cameras_list = get_cameras_list()
                for camera_id in cameras_list:
                    self.cam1_box.addItem(camera_id)
                    self.cam2_box.addItem(camera_id)

                if self.saved_ids:
                    id1, id2 = self.saved_ids
                    if id1 and id1 in cameras_list:
                        self.cam1_box.setCurrentText(id1)
                    if id2 and id2 in cameras_list:
                        self.cam2_box.setCurrentText(id2)
            except Exception as err:
                logging.exception(err)
                QMessageBox.warning(None, "Action fehlgeschlagen!",
                                    "Es hat nicht geklappt, Kameras IDs zu bekommen. Fehler:\n" + traceback.format_exc())
            else:
                return

        self.cam1_box.clear()
        self.cam2_box.clear()

    def save_last_ids(self):
        """Speichert Data uber die letzte Verbindung in der Datei."""

        if self.saved_ids != ['', '']:
            with open('data/saved_camera_ids.txt', 'w') as f:
                id1, id2 = self.saved_ids
                f.write(id1 + '\n' + id2)

    def read_saved_ids(self):
        """Liest Data uber die letzte Verbindung aus der Datei."""

        try:
            with open('data/saved_camera_ids.txt', 'r') as f:
                lines = f.read().splitlines()
                if len(lines) != 2:
                    logging.warning('saved_camera_ids Datei ist inkompatibel!')
                    self.saved_ids = ['', '']
                else:
                    self.saved_ids = lines
        except FileNotFoundError:
            self.saved_ids = ['', '']

