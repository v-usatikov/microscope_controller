# coding= utf-8
import logging
import platform
import threading
import time
from typing import List, Set, Dict

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QMainWindow, QApplication, QScrollBar, QStatusBar
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
# from pyqt_led import Led
import sys
# import pylab
import serial, serial.tools.list_ports
# import pyqtgraph
from PyQt5.uic import loadUi

from motor_controller import MotorsCluster, Motor, BoxesCluster
from motor_controller.SmarAct_MCS import MCSBoxSerial
from motor_controller.SmarAct_MCS2 import MCS2BoxEthernet

from motor_controller.interface import SerialConnector, ContrCommunicator
from motor_controller.Phytron_MCC2 import Box, StopIndicator, WaitReporter, MCC2BoxSerial, MCC2BoxEmulator, \
    MCC2Communicator
import logscolor

if __name__ == '__main__':
    logscolor.init_config()


class AktPositionSlider(QScrollBar):
    def __init__(self, parent=None):
        super(AktPositionSlider, self).__init__(Qt.Horizontal, parent)
        self.low_x = 0
        self.up_x = 100
        self.setInvertedAppearance(True)
        self.setMaximum(1000)

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


class CalibrationThread(QThread):
    """Thread für Kalibrierung der Motoren"""
    Kalibrierung_gestartet = pyqtSignal()
    Kalibrierung_fertig = pyqtSignal()
    Kalibrierung_unterbrochen = pyqtSignal()
    Kalibrierung_Status_Nachricht = pyqtSignal()
    stop = False
    status = ''
    motors_cluster: MotorsCluster = None
    motor: Motor = None

    def start(self, motors_cluster: MotorsCluster, motor: Motor=None):
        self.motors_cluster = motors_cluster
        self.motor = motor
        self.stop = False
        super().start()

    def run(self):
        calibration_reporter = GuiCalibrationReporter(self)
        stop_indicator = GuiStopIndicator(self)
        if self.motor is None:
            self.motors_cluster.calibrate_motors(stop_indicator=stop_indicator, reporter=calibration_reporter)
        else:
            self.motors_cluster.calibrate_motors(motors_to_calibration=[self.motor],
                                                 stop_indicator=stop_indicator, reporter=calibration_reporter)

        if self.stop:
            self.motors_cluster.stop()
            self.Kalibrierung_unterbrochen.emit()
        else:
            self.Kalibrierung_fertig.emit()

    def report(self, text):
        self.status = text
        print(self.status)
        self.Kalibrierung_Status_Nachricht.emit()


class GuiCalibrationReporter(WaitReporter):
    """Durch dieses Objekt kann man während eine Kalibrierung die Liste der im Moment laufenden Motoren bekommen.
            Es wird als argument für PBox.calibrate_motors() verwendet."""

    def __init__(self, kal_thread: CalibrationThread):
        self.kal_thread = kal_thread
        self.wait_list = set()

    def set_wait_list(self, wait_list: Set[str]):
        self.wait_list = wait_list
        self.__report()

    def motor_is_done(self, motor_name: str):
        self.wait_list -= {motor_name}
        self.__report()

    def __report(self):
        report = f'Wartet auf Motoren: {", ".join(self.wait_list)}'
        self.kal_thread.report(report)


class GuiStopIndicator(StopIndicator):
    """Durch dieses Objekt kann man Kalibrierung abbrechen.
    Es wird als argument für PBox.calibrate_motors() verwendet."""

    def __init__(self, kal_thread: CalibrationThread):
        self.kal_thread = kal_thread

    def has_stop_requested(self) -> bool:
        return self.kal_thread.stop


class ExampleApp(QMainWindow):

    motors_cluster: MotorsCluster
    motor: Motor

    def __init__(self, parent=None):
        super(ExampleApp, self).__init__(parent)
        loadUi('GUI_form/mainwindow.ui', self)

        # if platform.system() == "Windows":
        #     self.setMinimumSize(QSize(1000, 0))

        self.boxes: Dict[str, Box] = {}
        self.emulators: Dict[str, MCC2BoxEmulator] = {}

        self.position = 0
        self.position_NE = 0

        self.StatusBar = QStatusBar(self)
        self.StatusBar.setObjectName("statusbar")
        self.setStatusBar(self.StatusBar)

        self.cal_thread = CalibrationThread()
        self.cal_thread.Kalibrierung_unterbrochen.connect(self.Kalibrierung_unterbrochen)
        self.cal_thread.Kalibrierung_fertig.connect(self.Kalibrierung_fertig)
        self.cal_thread.Kalibrierung_Status_Nachricht.connect(self.Kalibrierung_Status_zeigen)

        # self.c = Communicate()
        self.horizontalScrollBar1.setParent(None)

        self.horizontalScrollBar1 = AktPositionSlider()
        self.horizontalLayout_4.addWidget(self.horizontalScrollBar1)
        self.horizontalScrollBar1.setEnabled(False)
        self.horizontalScrollBar1.set_soft_limits(None, None)

        self.refrBtn_MCS.clicked.connect(self.ports_lesen)
        self.refrBtn_MCC2.clicked.connect(self.ports_lesen)
        self.VerbButton_MCC2.clicked.connect(self.connect_MCC2)
        self.VerbButton_MCS.clicked.connect(self.connect_MCS)
        self.VerbButton_MCS2.clicked.connect(self.connect_MCS2)
        self.KalibrBtn.clicked.connect(self.calibrate1_all)
        self.KalibrBtn1.clicked.connect(self.calibrate1)
        self.StopButton.clicked.connect(self.stop)
        self.minusBtn1.clicked.connect(self.Minus1)
        self.plusBtn1.clicked.connect(self.Plus1)
        self.NullBtn1.clicked.connect(self.Null_einstellen)

        self.horizontalSlider1.sliderReleased.connect(self.Schieber_geh_zu)
        self.GeheZuEdit1.returnPressed.connect(self.geh_zu)
        self.SL_U_Edit.textEdited.connect(self.set_soft_limits)
        self.SL_O_Edit.textEdited.connect(self.set_soft_limits)
        self.EinheitenBox1.stateChanged.connect(self.Einheiten_wechseln)
        self.MotorCBox.currentTextChanged.connect(self.change_current_motor)
        # self.c.Kal_done.connect(self.Position_lesen)

        self.NullBtn1.setEnabled(False)

        # self.line_Th_Einst.editingFinished.connect(self.Thermo_Einst_schicken)

        self.SchrittEdit1.setValidator(QtGui.QDoubleValidator())
        self.GeheZuEdit1.setValidator(QtGui.QDoubleValidator())
        self.SL_U_Edit.setValidator(QtGui.QDoubleValidator())
        self.SL_O_Edit.setValidator(QtGui.QDoubleValidator())

        self.Kal_in_Lauf = False
        self.refresh_position = True
        self.connected = False
        self.comm_emulation = False
        self.serial_emulation = False

        self.units = 'norm'

        self.ports_lesen()

        # self.horizontalSlider1.setTickPosition(300)
        # self.horizontalSlider1.setTickInterval(100)
        # self.drawLines()

        # self.horizontalSlider1.drawLines = drawLines
        # self.horizontalSlider1.paintEvent = paintEvent

    def Kalibrierung_Status_zeigen(self):
        self.StatusBar.showMessage(self.cal_thread.status)

    def load_motors_names(self):
        self.MotorCBox.clear()
        names = self.motors_cluster.motors.keys()
        for name in names:
            self.MotorCBox.addItem(name)

    def change_current_motor(self):
        if self.MotorCBox.currentText() != '':
            self.motor = self.motors_cluster.get_motor(self.MotorCBox.currentText())
            self.init_soft_limits()
            self.read_position(single_shot=True)
            if not self.motor.is_calibratable():
                self.horizontalSlider1.setEnabled(False)
                self.horizontalScrollBar1.setValue(0)
                self.horizontalSlider1.setValue(0)
                self.Motor1Box.setTitle(self.motor.name)
                self.KalibrBtn1.setEnabled(False)
            else:
                self.horizontalSlider1.setEnabled(True)
                self.set_HSlider_tr(int(self.position))
                self.Motor1Box.setTitle(self.motor.name)
                self.KalibrBtn1.setEnabled(True)
            self.Motor1Box.setEnabled(True)
        else:
            self.Motor1Box.setEnabled(False)

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

        if self.EinheitenBox1.checkState():
            pass
            lower_bound = motor.transform_units(float(lower_bound), 'displ', to='norm') if lower_bound != '' else None
            upper_bound = motor.transform_units(float(upper_bound), 'displ', to='norm') if upper_bound != '' else None
        else:
            lower_bound = float(lower_bound) if lower_bound != '' else None
            upper_bound = float(upper_bound) if upper_bound != '' else None

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

        self.horizontalScrollBar1.set_soft_limits(lower_bound, upper_bound)

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

    def Einheiten_wechseln(self):
        if self.EinheitenBox1.checkState():
            self.Einheit_label.setText(self.motor.config['display_units'])
            self.units = 'displ'
        else:
            self.Einheit_label.setText('NE')
            self.units = 'norm'
        self.NullBtn1.setEnabled(self.EinheitenBox1.checkState())
        self.Soft_Limits_Lines_Einheiten_anpassen()

    def geh_zu(self):
        self.motor.go_to(float(self.GeheZuEdit1.text()), self.units)
        self.set_HSlider_tr(int(float(self.GeheZuEdit1.text())))

    def NE_aus_AE(self, AE):
        return self.motor.transform_units(AE, 'displ', to='norm')

    def set_HSlider_tr(self, Val):
        if self.EinheitenBox1.checkState():
            self.set_HSlider(int(self.NE_aus_AE(Val)))
        else:
            self.set_HSlider(Val)

    def set_HSlider(self, Val):
        if self.motor.is_calibratable():
            self.horizontalSlider1.setValue(Val)

    def Plus1(self):
        self.motor.go(float(self.SchrittEdit1.text()), self.units)
        self.set_HSlider_tr(self.position + float(self.SchrittEdit1.text()))

    def Minus1(self):
        self.motor.go(-float(self.SchrittEdit1.text()), self.units)
        self.set_HSlider_tr(self.position - float(self.SchrittEdit1.text()))

    def stop(self):
        self.motors_cluster.stop()
        self.set_HSlider(self.position_NE)

    def Schieber_geh_zu(self):
        self.motor.go_to(self.horizontalSlider1.value())
        if self.EinheitenBox1.checkState():
            self.GeheZuEdit1.setText(
                str(round(self.motor.transform_units(self.horizontalSlider1.value(), 'norm', to='displ'), 4)))
        else:
            self.GeheZuEdit1.setText(str(self.horizontalSlider1.value()))

    def Null_einstellen(self):
        self.motor.set_display_null()
        self.Soft_Limits_Lines_Einheiten_anpassen()

    def connect_MCC2(self):

        input_file = 'input/MCC2_Motoren_config.csv'
        input_file = 'input/Jet_box_config.csv'

        emulator_input_file = 'input/MCC2_Emulator_config.csv'
        self._connect_controller('MCC2', input_file, emulator_input_file)

    def connect_MCS(self):

        input_file = 'input/MCS_Motoren_config.csv'
        emulator_input_file = 'input/MCS_Emulator_config.csv'
        self._connect_controller('MCS', input_file, emulator_input_file)

    def connect_MCS2(self):

        input_file = 'input/MCS2_Motoren_config.csv'
        emulator_input_file = 'input/MCS2_Emulator_config.csv'
        self._connect_controller('MCS2', input_file, emulator_input_file)

    def _connect_controller(self, type: str, input_file: str, emulator_input_file: str):

        if self.connected:
            self.motors_cluster.stop()
            self.save_session_data()

        self.refresh_position = False

        emulator = MCC2BoxEmulator(n_bus=5, n_axes=3, realtime=True)

        if type == 'MCC2':
            if self.PortBox_MCC2.currentText() == 'CommunicatorEmulator':
                self.boxes[type] = Box(emulator, input_file=emulator_input_file)
                self.emulators[type] = emulator
            elif self.PortBox_MCC2.currentText() == 'SerialEmulator':
                connector = SerialConnector(emulator=emulator, beg_symbol=b'\x02', end_symbol=b'\x03')
                emul_communicator = MCC2Communicator(connector)
                self.boxes[type] = Box(emul_communicator, input_file=emulator_input_file)
                self.emulators[type] = emulator
            else:
                self.boxes[type] = MCC2BoxSerial(self.PortBox_MCC2.currentText(), input_file=input_file, baudrate=115200)
        elif type == 'MCS':
            if self.PortBox_MCS.currentText() == 'CommunicatorEmulator':
                self.boxes[type] = Box(emulator, input_file=emulator_input_file)
                self.emulators[type] = emulator
            elif self.PortBox_MCS.currentText() == 'SerialEmulator':
                connector = SerialConnector(emulator=emulator, beg_symbol=b'\x02', end_symbol=b'\x03')
                emul_communicator = MCC2Communicator(connector)
                self.boxes[type] = Box(emul_communicator, input_file=emulator_input_file)
                self.emulators[type] = emulator
            else:
                self.boxes[type] = MCSBoxSerial(self.PortBox_MCS.currentText(), input_file=input_file)
        elif type == 'MCS2':
            if self.ipLine.text() == 'E':
                self.boxes[type] = Box(emulator, input_file=emulator_input_file)
                self.emulators[type] = emulator
            else:
                self.boxes[type] = MCS2BoxEthernet(self.ipLine.text(),
                                                   self.PortLine.text(),
                                                   input_file=input_file)
        else:
            raise ValueError(f'Unknown type: "{type}"')

        self.motors_cluster = BoxesCluster(self.boxes)

        if len(self.boxes[type].motors_cluster.motors) == 0:
            QMessageBox.warning(self, "Verbindung fehlgeschlagen!",
                                    self.boxes[type].report)
            return

        try:
            self.read_saved_session_data()
        except FileNotFoundError:
            pass

        self.load_motors_names()
        self.KalibrBtn.setEnabled(True)
        # self.Motor1Box.setEnabled(True)
        self.MotorCBox.setEnabled(True)
        self.Motorlabel.setEnabled(True)

        self.refresh_position = True
        if not self.connected:
            self.read_position()

        # self.set_HSlider(int(self.Position))
        # self.Motor1Box.setTitle(self.motor.name)

        self.connected = True
        QMessageBox.information(self, "Verbindung abgeschlossen!",
                                self.boxes[type].report)

    def read_position(self, single_shot=False):
        if self.refresh_position:
            self.position = self.motor.position(self.units)
            self.position_NE = self.motor.position()
            self.AktPosEdit1.setText(str(round(self.position, 4)))
            if self.motor.is_calibratable():
                self.horizontalScrollBar1.setValue(int(self.position_NE))
        if not single_shot:
            QtCore.QTimer.singleShot(100, self.read_position)

    def Kalibrierung_fertig(self):

        self.Kalibrierung_unterbrochen()
        self.StatusBar.clearMessage()

    def Kalibrierung_unterbrochen(self):
        self.Motor1Box.setEnabled(True)
        self.MotorCBox.setEnabled(True)
        self.Motorlabel.setEnabled(True)
        self.refresh_position = True
        self.read_position(single_shot=True)
        self.set_HSlider(int(self.position))

        self.VerbButton_MCC2.setEnabled(True)
        self.VerbButton_MCS.setEnabled(True)
        self.VerbButton_MCS2.setEnabled(True)
        self.Kal_in_Lauf = False
        self.KalibrBtn.setText("alle kalibrieren")
        self.KalibrBtn1.setText("kalibrieren")
        self.StatusBar.showMessage("Kalibrierung wurde unterbrochen")

        for emulator in self.emulators.values():
            emulator.realtime = True

    def calibrate(self, motor=None):

        if not self.Kal_in_Lauf:
            self.Kal_in_Lauf = True
            self.VerbButton_MCC2.setEnabled(False)
            self.VerbButton_MCS.setEnabled(False)
            self.VerbButton_MCS2.setEnabled(False)
            self.Motor1Box.setEnabled(False)
            self.MotorCBox.setEnabled(False)
            self.Motorlabel.setEnabled(False)
            self.KalibrBtn.setText("Stop")
            self.KalibrBtn1.setText("Stop")
            self.refresh_position = False

            for emulator in self.emulators.values():
                emulator.realtime = False

            self.cal_thread.start(self.motors_cluster, motor)
            print("Thr started")

        else:
            self.cal_thread.stop = True

    def calibrate1_all(self):

        self.calibrate()

    def calibrate1(self):

        self.calibrate(self.motor)

    def ports_lesen(self):
        self.PortBox_MCS.clear()
        self.PortBox_MCC2.clear()
        comlist = serial.tools.list_ports.comports()

        for element in comlist:
            self.PortBox_MCS.addItem(element.device)
            self.PortBox_MCC2.addItem(element.device)
        self.PortBox_MCS.addItem('SerialEmulator')
        self.PortBox_MCS.addItem('CommunicatorEmulator')


        self.PortBox_MCC2.addItem('SerialEmulator')
        self.PortBox_MCC2.addItem('CommunicatorEmulator')

        if not self.Kal_in_Lauf:
            self.VerbButton_MCC2.setEnabled(True)
            self.VerbButton_MCS.setEnabled(True)
            self.VerbButton_MCS2.setEnabled(True)

    def save_session_data(self):
        self.motors_cluster.save_session_data("data/saved_session_data.txt")

    def read_saved_session_data(self):
        self.motors_cluster.read_saved_session_data("data/saved_session_data.txt")


    # QtCore.QTimer.singleShot(1000, self.weiter) # QUICKLY repeat


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('macintosh')
    form = ExampleApp()
    form.show()
    # form.update() #start with something

    try:
        app.exec_()
    finally:
        if form.connected:
            form.stop()
            form.save_session_data()
            form.motors_cluster.close()
