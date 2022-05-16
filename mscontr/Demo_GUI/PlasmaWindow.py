import sys
import threading

import cv2
import serial.tools.list_ports
from PyQt6 import QtGui
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget, QCheckBox, QLineEdit, QFileDialog, QComboBox, \
    QStyleFactory, QPushButton
from PyQt6.uic import loadUi
from motor_controller.Phytron_MCC2 import MCC2BoxSerial
from motor_controller.interface import StandardStopIndicator

from mscontr.MainGUI.mcwidgets import VideoWidget, MotorWidget
from mscontr.microwatcher.plasma_watcher import PlasmaWatcher_BoxInput, PlasmaWatcher
from tests.qtplayer import prepare_jet_watcher_to_test

MODE = "emulator"
# MODE = "real"

class PlasmaMotorWindow(QWidget):
    VideoField: VideoWidget
    checkBox_laser: QCheckBox
    gainEdit: QLineEdit
    JetXBox: MotorWidget
    comboBox_camera: QComboBox
    CalPlasmaBtn: QPushButton

    def __init__(self, parent=None):
        super(PlasmaMotorWindow, self).__init__(parent)
        loadUi('GUI_form/PlasmaMotorWindow.ui', self)

        print('0', self.recordBtn.styleSheet())

        self.connected = False
        self.is_recording = False
        self.stop_indicator = StandardStopIndicator()

        self.CalPlasmaBtn.clicked.connect(self.calibr_plasma)
        self.CalEnlBtn.clicked.connect(self.calibr_enl)
        self.centreBtn.clicked.connect(self.centre_nozzle)
        self.recordBtn.clicked.connect(self.record)
        self.calJXBtn.clicked.connect(self.calibrate_JetX)
        self.calJZBtn.clicked.connect(self.calibrate_JetZ)
        self.plusBtn.clicked.connect(self.plus_step)
        self.minusBtn.clicked.connect(self.minus_step)
        self.StopButton.clicked.connect(self.stop)
        self.checkBox_laser.stateChanged.connect(self.laser_status_changed)
        self.gainEdit.editingFinished.connect(self.set_gain)
        self.exposeEdit.editingFinished.connect(self.set_exposure)
        self.comboBox_camera.currentTextChanged.connect(self.change_camera)

        self.exposeEdit.setValidator(QtGui.QIntValidator())
        self.gainEdit.setValidator(QtGui.QIntValidator())

        self._dark_exposure = 10000
        self._normal_exposure = 40000

        self._dark_gain = 10
        self._normal_gain = 10

        if MODE == "emulator":
            self.plasma_watcher, self.jet_emulator, self.camera1, self.camera2 = prepare_jet_watcher_to_test(pl_cal=False,
                                                                                                             shift=1500)
            self.jet_emulator.realtime(True)


            # self.test1()
        elif MODE == "real":
            from mscontr.microwatcher.vimba_camera import Camera, get_cameras_list

            plasma_watcher, self.jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(
                pl_cal=False,
                shift=1500)

            print(get_cameras_list())
            self.camera1 = Camera('DEV_000F314E840B', bandwidth=60000000)
            self.camera2 = Camera('DEV_000F314E840A', bandwidth=60000000)


            print(serial.tools.list_ports.comports())
            port = "COM5"
            input_file = 'input/Jet_box_config.csv'
            self.box = MCC2BoxSerial(port, input_file=input_file, baudrate=115200)

            try:
                self.box.motors_cluster.read_saved_session_data("data/saved_session_data_Jet.txt")
            except FileNotFoundError:
                pass

            self.connected = True

            phi = 80
            psi = 50

            jet_x = self.box.get_motor_by_name('JetX')
            jet_z = self.box.get_motor_by_name('JetZ')
            laser_z = plasma_watcher.laser_z
            laser_y = plasma_watcher.laser_y
            self.plasma_watcher = PlasmaWatcher(self.camera1, self.camera2, jet_x, jet_z, laser_z, laser_y, phi, psi)

        self.JetXBox.init(self.plasma_watcher.jet_x)
        self.JetZBox.init(self.plasma_watcher.jet_z)

        self.camera = self.camera1
        self.change_camera()

    def calibrate_JetX(self):
        def in_thread():
            self.plasma_watcher.jet_x.calibrate()
            self.plasma_watcher.jet_x.go_to(500, 'norm')

        threading.Thread(target=in_thread).start()

    def calibrate_JetZ(self):
        def in_thread():
            self.plasma_watcher.jet_z.calibrate()
            self.plasma_watcher.jet_z.go_to(500, 'norm')

        threading.Thread(target=in_thread).start()

    def change_camera(self):

        self.camera.stop_stream()
        self.camera.disconnect_from_stream(self.show_frame)
        if self.comboBox_camera.currentText() == "camera 1":
            self.camera = self.camera1
        elif self.comboBox_camera.currentText() == "camera 2":
            self.camera = self.camera2

        self.camera.connect_to_stream(self.show_frame)
        self.camera.start_stream()

    def record(self):
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
        self.set_gain()
        self.set_exposure()

    def set_gain(self):
        self.camera.set_gain(int(self.gainEdit.text()))

    def set_exposure(self):
        self.camera.set_exposure(int(self.exposeEdit.text()))

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

    def calibr_plasma(self):

        def in_thread():

            self.plasma_watcher.calibrate_plasma(mess_per_point=mess_per_point, on_the_spot=True,
                                                 stop_indicator=self.stop_indicator)
            self.CalPlasmaBtn.setText("calibr plasma")

        if self.CalPlasmaBtn.text() == "calibr plasma":

            mess_per_point = 5
            self.jet_emulator.flicker_sigma = 0.1
            self.stop_indicator.restore()

            self.checkBox_laser.setChecked(True)
            self.camera1.start_stream()
            self.camera2.start_stream()

            threading.Thread(target=in_thread).start()
            self.CalPlasmaBtn.setText("stop")
        elif self.CalPlasmaBtn.text() == "stop":
            self.stop_indicator.stop()
            self.CalPlasmaBtn.setText("calibr plasma")

    def centre_nozzle(self):

        def in_thread():

            self.plasma_watcher.centre_the_nozzle(stop_indicator=self.stop_indicator)
            self.centreBtn.setText("zentrieren")

        if self.centreBtn.text() == "zentrieren":
            self.stop_indicator.restore()
            self.checkBox_laser.setChecked(False)
            threading.Thread(target=in_thread).start()
            self.centreBtn.setText("stop")
        elif self.centreBtn.text() == "stop":
            self.stop_indicator.stop()
            self.centreBtn.setText("zentrieren")

    def calibr_enl(self):

        def in_thread():

            report = self.plasma_watcher.calibrate_enl(init_step=100, rel_err=0.01, n_points=10,
                                                       stop_indicator=self.stop_indicator)
            print(report)
            self.CalEnlBtn.setText("calibr enl")

        if self.CalEnlBtn.text() == "calibr enl":
            self.stop_indicator.restore()
            self.checkBox_laser.setChecked(False)
            threading.Thread(target=in_thread).start()
            self.CalEnlBtn.setText("stop")
        elif self.CalEnlBtn.text() == "stop":
            self.stop_indicator.stop()
            self.CalEnlBtn.setText("calibr enl")

    def move_in_cam_coord(self, shift: float):

        if self.comboBox_camera.currentText() == "camera 1":
            camera_coord = self.plasma_watcher.camera1_coord
        elif self.comboBox_camera.currentText() == "camera 2":
            camera_coord = self.plasma_watcher.camera2_coord
        else:
            raise ValueError("Unbekante Kamerabezeichnung!")

        shift_x, shift_z = camera_coord.cc_to_mc(x_=0, z_=shift)

        self.plasma_watcher.move_jet(shift_x, shift_z, units='displ')

    def plus_step(self):
        self.move_in_cam_coord(float(self.SchrittEdit.text()))

    def minus_step(self):
        self.move_in_cam_coord(-float(self.SchrittEdit.text()))

    def stop(self):
        self.plasma_watcher.jet_x.stop()
        self.plasma_watcher.jet_z.stop()

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.camera1.stop_stream()
        self.camera2.stop_stream()
        print('closed')
        return super().closeEvent(a0)

    def save_session_data(self):
        self.box.motors_cluster.save_session_data("data/saved_session_data_Jet.txt")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    print(QStyleFactory.keys())
    app.setStyle('windowsvista')
    form = PlasmaMotorWindow()
    form.show()
    # form.update() #start with something

    try:
        app.exec()
    finally:
        if form.connected:
            form.box.stop()
            form.save_session_data()
            form.box.close()