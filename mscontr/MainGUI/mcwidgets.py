import logging
import traceback
from abc import ABC
from typing import Tuple, Callable, List, Optional, Union, Dict

import numpy as np
import serial, serial.tools.list_ports
from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QMainWindow, QApplication, QScrollBar, QStatusBar, QGraphicsView, \
    QSizePolicy, QGroupBox, QStyle, QStyleFactory, QComboBox, QHBoxLayout
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

point_n = Tuple[float, float]
point_p = Tuple[int, int]


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
        self.low_x = 0
        self.up_x = 100
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
        h_hint = 7
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


class MotorWidget(QGroupBox):

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

        self.position = 0
        self.position_NE = 0
        self.is_closed = False
        self.refresh_position = True

        self.GeheZuEdit.returnPressed.connect(self.go_to)
        self.SL_U_Edit.textEdited.connect(self.set_soft_limits)
        self.SL_O_Edit.textEdited.connect(self.set_soft_limits)
        self.StopButton.clicked.connect(self.stop)
        self.minusBtn.clicked.connect(self.minus_step)
        self.plusBtn.clicked.connect(self.plus_step)
        self.NullBtn.clicked.connect(self.set_zero)

    def init(self, motor: Motor):

        self.motor = motor
        self.init_soft_limits()
        self.read_position()
        if not self.motor.is_calibratable():
            self.APSlider.setEnabled(False)
            self.APSlider.setValue(0)
        else:
            self.APSlider.setEnabled(True)
            self.APSlider.setValue(round(self.position_NE))

        self.Units_label.setText(self.motor.config['display_units'])
        self.setTitle(self.motor.name)
        self.setEnabled(True)

    def go_to(self):
        self.motor.go_to(float(self.GeheZuEdit.text()), 'displ')

    def plus_step(self):
        self.motor.go(float(self.SchrittEdit.text()), 'displ')

    def minus_step(self):
        self.motor.go(-float(self.SchrittEdit.text()), 'displ')

    def stop(self):
        self.motor.stop()

    def read_position(self, single_shot=False):
        if self.refresh_position:
            self.position = self.motor.position('displ')
            self.position_NE = self.motor.transform_units(self.position, 'displ', 'norm')
            self.AktPosEdit.setText(str(round(self.position, 4)))
            if self.motor.is_calibratable():
                self.APSlider.setValue(int(self.position_NE))
        if not single_shot and not self.is_closed:
            QtCore.QTimer.singleShot(200, self.read_position)

    def set_zero(self):
        self.motor.set_display_null()
        self.Soft_Limits_Lines_Einheiten_anpassen()

    def Soft_Limits_Lines_Einheiten_anpassen(self):
        Motor = self.motor

        U_Grenze = Motor.soft_limits[0]
        O_Grenze = Motor.soft_limits[1]

        if U_Grenze is not None:
            if self.EinheitenBox1.checkState():
                U_Grenze = Motor.transform_units(U_Grenze, 'norm', to='displ')
            self.SL_U_Edit.setText(str(round(U_Grenze, 4)))
        if O_Grenze is not None:
            if self.EinheitenBox1.checkState():
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
            if self.EinheitenBox1.checkState():
                lower_bound = motor.transform_units(lower_bound, 'norm', to='displ')
            self.SL_U_Edit.setText(str(round(lower_bound, 4)))
        else:
            self.SL_U_Edit.setText('')
        if upper_bound is not None:
            if self.EinheitenBox1.checkState():
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
        sizePolicy = QtWidgets.QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(group_box.sizePolicy().hasHeightForWidth())
        group_box.setSizePolicy(sizePolicy)
        # group_box.setMinimumSize(QtCore.QSize(0, 121))
        font = QtGui.QFont()
        # font.setPointSize(100)
        group_box.setFont(font)
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


    def set_dark_bg(self):
        grey = QPixmap(self.width(), self.height())
        grey.fill(QColor('darkGray'))
        self.setPixmap(grey)


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
        axes.axes += new_axes

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


class MotorWindow(QWindow):

    def __init__(self, parent: QWindow, ):
        super().__init__(parent)


class ConnectionWindow(QWidget):

    controller_connected = pyqtSignal(Dict[str, Motor])
    controller_disconnected = pyqtSignal(Tuple[str])

    PortBox_MCC2_box: QComboBox
    PortBox_MCC2_jet: QComboBox
    PortBox_MCS: QComboBox

    def __init__(self):
        super().__init__()

        self.setObjectName("Connection Window")
        self.resize(636, 295)
        self.verticalLayout = QtWidgets.QVBoxLayout(self)

        self.conn_widgets: List[ConnectionWidget] = []

        self.mcc2_cw = MCC2_SerialConnectionWidget(self, "Phytron Box (MCC2)", 'input/MCC2_Motoren_config.csv')
        self.add_connection_widget(self.mcc2_cw)

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
        self.horizontalLayout.addWidget(self.conn_all_btn)
        self.disconn_all_btn = QtWidgets.QPushButton(self)
        self.horizontalLayout.addWidget(self.disconn_all_btn)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.conn_all_btn.clicked.connect(self.connect_all)
        self.disconn_all_btn.clicked.connect(self.disconnect_all)

        self.boxes_cluster = mc.BoxesCluster()

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


class ConnectionWidget(QHBoxLayout):

    VerbButton: QtWidgets.QPushButton

    def __init__(self, conn_wind: ConnectionWindow, name: str, input_file: str):
        super().__init__(parent=conn_wind)

        self.conn_wind = conn_wind
        self.name = name
        self.input_file = input_file

        self.box: mc.Box | None = None

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

    def get_communicator(self, connector: mc.Connector) -> mc.ContrCommunicator:

        raise NotImplementedError

    def is_emulation(self):

        return False

    def connect_box(self) -> mc.Box:

        self.disconnect_box()

        if self.is_emulation():
            emulator = mc.Phytron_MCC2.BoxEmulator(n_bus=5, n_axes=3, realtime=True)
            self.box = mc.Box(emulator, input_file=self.input_file)
        else:
            communicator = self.get_communicator(self.get_connector())
            self.box = mc.Box(communicator, self.input_file)

        self.conn_wind.boxes_cluster.add_box(self.box, self.name)
        self.conn_wind.controller_connected.emit(self.box.motors_cluster.motors)

        self.save_last_connection_data()
        return self.box

    def disconnect_box(self):

        if self.box is not None:
            self.conn_wind.controller_disconnected.emit(tuple(self.box.motors_cluster.motors.keys()))
            self.conn_wind.boxes_cluster.remove_box(self.box)
            self.box.close()
            self.box = None

    def connection_btn_click(self):

        if self.VerbButton.text() == 'verbinden':
            try:
                self.connect_box()
            except Exception as err:
                logging.exception(err)
                QMessageBox.warning(self.conn_wind, "Verbindung fehlgeschlagen!",
                                    traceback.format_exc())
            else:
                self.VerbButton.setText("trennen")
                QMessageBox.information(self.conn_wind, "Verbindung abgeschlossen!",
                                        self.box.report)
        else:
            self.disconnect_box()
            self.VerbButton.setText("verbinden")


class SerialConnectionWidget(ConnectionWidget):

    def __int__(self, conn_wind: ConnectionWindow, name: str, input_file: str):
        super().__init__(conn_wind, name, input_file)

        self.name_label = QLabel(self.conn_wind)
        self.name_label.setText(self.name)
        self.addWidget(self.name_label)

        self._line = QFrame(self)
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

    def is_emulation(self):

        if self.PortBox.currentText() == 'Emulator':
            return True
        else:
            return False

    def get_communicator(self, connector: mc.Connector) -> mc.ContrCommunicator:

        raise NotImplementedError


class MCC2_SerialConnectionWidget(SerialConnectionWidget):

    def get_communicator(self, connector: mc.Connector) -> mc.ContrCommunicator:

        connector = mc.Phytron_MCC2.MCC2SerialConnector(port=self.PortBox.currentText())
        return mc.Phytron_MCC2.MCC2Communicator(connector)


class MCS_SerialConnectionWidget(SerialConnectionWidget):

    def get_communicator(self, connector: mc.Connector) -> mc.ContrCommunicator:
        connector = mc.SmarAct_MCS.MCS_SerialConnector(port=self.PortBox.currentText())
        return mc.SmarAct_MCS.MCSCommunicator(connector)


class EthernetConnectionWidget(ConnectionWidget):

    def __int__(self, conn_wind: ConnectionWindow, name: str, input_file: str):
        super().__init__(conn_wind, name, input_file)

        self.name_label = QtWidgets.QLabel(self.conn_wind)
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
        self.addWidget(self.PortLine)

        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding,
                                            QtWidgets.QSizePolicy.Policy.Minimum)
        self.addItem(spacerItem3)

        self.VerbButton = QtWidgets.QPushButton(self.conn_wind)
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

    def get_communicator(self, connector: mc.Connector) -> mc.ContrCommunicator:

        raise NotImplementedError


class MCS2_EthernetConnectionWidget(EthernetConnectionWidget):

    def get_communicator(self, connector: mc.Connector) -> mc.ContrCommunicator:
        connector = mc.SmarAct_MCS2.MCS2_EthernetConnector(self.ipLine.text(), self.PortLine.text())
        return mc.SmarAct_MCS2.MCS2Communicator(connector)

# class AxesPainter:
#
#     def __init__(self, gr_field: GraphicField,
#                  origin_point: Tuple,
#                  arrow_length: float,
#                  def_color: Union[QColor, int] = Qt.black,
#                  select_color: Union[QColor, int] = Qt.darkYellow,
#                  lines_width: int = 2,
#
#
#
#         self.def_color =

# class Axis:
#
#     name: str
#     end_point: Tuple[]
#
#     def __init__(self, ):
#         self.