import logging
from typing import Tuple, Callable, List, Optional

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QMainWindow, QApplication, QScrollBar, QStatusBar, QGraphicsView, \
    QSizePolicy, QGroupBox, QStyle, QStyleFactory
from PyQt5.QtWidgets import QFrame, QWidget, QLabel
from PyQt5.QtGui import QPainter, QPen, QPixmap, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from math import sqrt
from PIL import Image
from graphic_ext import GraphicField, GraphicObject
from motor_controller import Motor


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
        super().__init__(s_navig, x, y)

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
        qp.setRenderHint(QPainter.Antialiasing)
        self.paint(qp)
        qp.end()

    def paint(self, qp):
        pen = QPen(Qt.black, 1, Qt.SolidLine)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        qp.drawEllipse(QPoint(round(self.width() / 2), round(self.height() / 2)), self.d_pixel() / 2, self.d_pixel() / 2)

    def hello(self):
        print('FoV')


class FoVto(FoV):

    def paint(self, qp):
        pen = QPen(Qt.gray, 1, Qt.DashLine)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
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
        super(AktPositionSlider, self).__init__(Qt.Horizontal, parent)
        self.low_x = 0
        self.up_x = 100
        self.setInvertedAppearance(True)

    def paintEvent(self, e):
        # super().paintEvent(e)
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        self.drawLines(qp)
        qp.end()

    def drawLines(self, qp):
        pen = QPen(Qt.gray, 2, Qt.SolidLine)

        # Parametern
        d_icon = 8
        h_icon = 4
        rund_k = 1
        h_hint = 7
        height = self.height()
        hcenter = height / 2
        width = self.width()
        v_range = width - 2 * d_icon
        x_icon = d_icon + self.value() * v_range / 1000
        # x_icon = d_icon + self.U_x * v_range / 1000

        # Hintergrund malen
        pen.setWidth(1)
        pen.setColor(Qt.white)
        qp.setPen(pen)
        qp.setBrush(Qt.white)
        qp.drawRect(0, hcenter - h_hint, width, 2 * h_hint)

        # Icon malen
        pen.setWidth(0)
        pen.setColor(Qt.gray)
        qp.setPen(pen)
        qp.setBrush(Qt.gray)
        qp.drawRoundedRect(x_icon - d_icon, hcenter - h_icon, 2 * d_icon, 2 * h_icon, rund_k * h_icon, rund_k * h_icon)
        # print(x_icon+d_icon, width)

        # Soft Limits malen
        pen.setWidth(2)
        qp.setPen(pen)
        U_pixel_x = d_icon + self.low_x * v_range / 1000
        O_pixel_x = d_icon + self.up_x * v_range / 1000
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

    def __init__(self, parent: Optional[QWidget]):
        super().__init__(parent)
        # self.setStyle()
        self.setupUi(self)

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
            self.APSlider.setValue(self.position_NE)

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
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(group_box.sizePolicy().hasHeightForWidth())
        group_box.setSizePolicy(sizePolicy)
        # group_box.setMinimumSize(QtCore.QSize(0, 121))
        font = QtGui.QFont()
        font.setPointSize(100)
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
        self.APSlider.setOrientation(Qt.Horizontal)
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
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
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
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
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
        self.NullBtn.setLayoutDirection(Qt.LeftToRight)
        self.NullBtn.setObjectName("NullBtn")
        self.horizontalLayout_4.addWidget(self.NullBtn)
        spacerItem2 = QtWidgets.QSpacerItem(30, 28, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem2)
        self.StopButton = QtWidgets.QPushButton(group_box)
        self.StopButton.setMinimumSize(QtCore.QSize(120, 0))
        self.StopButton.setObjectName("StopButton")
        self.horizontalLayout_4.addWidget(self.StopButton)
        self.line_2 = QtWidgets.QFrame(group_box)
        self.line_2.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
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
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
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

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setSizePolicy(sizePolicy)


    def set_dark_bg(self):
        grey = QPixmap(self.width(), self.height())
        grey.fill(QColor('darkGray'))
        self.setPixmap(grey)


