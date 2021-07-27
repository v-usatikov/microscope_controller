import sys
import threading

import cv2
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QCheckBox, QLineEdit, QFileDialog
from PyQt5.uic import loadUi
from motor_controller.Phytron_MCC2 import MCC2BoxSerial

from mscontr.MainGUI.mcwidgets import VideoWidget, MotorWidget
from mscontr.microwatcher.plasma_watcher import PlasmaWatcher_BoxInput
from tests.qtplayer import prepare_jet_watcher_to_test

MODE = "emulator"
# MODE = "real"

class PlasmaMotorWindow(QWidget):
    VideoField: VideoWidget
    checkBox_laser: QCheckBox
    gainEdit: QLineEdit
    JetXBox: MotorWidget

    def __init__(self, parent=None):
        super(PlasmaMotorWindow, self).__init__(parent)
        loadUi('GUI_form/PlasmaMotorWindow.ui', self)

        self.connected = False
        self.is_recording = False

        self.CalPlasmaBtn.clicked.connect(self.calibr_plasma)
        self.CalEnlBtn.clicked.connect(self.calibr_enl)
        self.recordBtn.clicked.connect(self.record)
        self.checkBox_laser.stateChanged.connect(self.laser_status_changed)
        self.gainEdit.editingFinished.connect(self.set_gain)
        self.exposeEdit.editingFinished.connect(self.set_exposure)

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

            self.JetXBox.init(self.plasma_watcher.jet_x)
            self.JetZBox.init(self.plasma_watcher.jet_z)

            # self.test1()
        elif MODE == "real":
            from mscontr.microwatcher.vimba_camera import Camera

            self.camera1 = Camera('DEV_000F314E840A')
            self.camera2 = Camera('DEV_000F314E840A')

            input_file = 'input/MCC2_Motoren_config.csv'
            self.box = MCC2BoxSerial(self.PortBox_MCC2.currentText(), input_file=input_file, baudrate=115200)
            self.box.motors_cluster.read_saved_session_data("data/saved_session_data.txt")
            self.connected = True

            phi = 90
            psi = 45

            self.plasma_watcher = PlasmaWatcher_BoxInput(self.camera1, self.camera2, self.box, phi=phi, psi=psi)

        self.camera = self.camera1

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
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        return QPixmap.fromImage(convert_to_Qt_format)

    def calibr_plasma(self):

        mess_per_point = 5
        self.jet_emulator.flicker_sigma = 0.1

        self.checkBox_laser.setChecked(True)
        target = lambda: self.plasma_watcher.calibrate_plasma(mess_per_point=mess_per_point)
        threading.Thread(target=target).start()

    def calibr_enl(self):

        def in_thread():
            report = self.plasma_watcher.calibrate_enl(init_step=1000, rel_err=0.01, n_points=10)
            print(report)

        self.checkBox_laser.setChecked(False)
        threading.Thread(target=in_thread).start()

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.camera1.stop_stream()
        print('closed')
        return super().closeEvent(a0)

    def save_session_data(self):
        self.motors_cluster.save_session_data("data/saved_session_data.txt")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('macintosh')
    form = PlasmaMotorWindow()
    form.show()
    # form.update() #start with something

    try:
        app.exec_()
    finally:
        if form.connected:
            form.box.stop()
            form.save_session_data()
            form.box.close()