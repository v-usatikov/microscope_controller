import sys

from PyQt6.QtGui import QWindow
from PyQt6.QtWidgets import QMainWindow, QApplication, QPushButton
from PyQt6.uic import loadUi

from mscontr.MainGUI.arrows import Window
from mscontr.MainGUI.mcwidgets import MicroscopeScheme, MicroscopeZone, MotorWindow, ConnectionWindow


class MainWindow(QMainWindow):

    micr_scheme: MicroscopeScheme
    conn_btn: QPushButton
    calibr_btn: QPushButton

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        loadUi('ui_forms/main_window.ui', self)

        self.micr_scheme.set_background_from_file('img/main_view.png', use_picture_coordinates=True)

        self.conn_window = ConnectionWindow()

        self.ml_window = MotorWindow(self.conn_window, ['MirrorX', 'MirrorY', 'MirrorZ', 'MirrorRX', 'MirrorRY'])
        self.ml_zone = MicroscopeZone(self.micr_scheme,
                                              'Multilayer',
                                              name_pos=(450, 622),
                                              axes_pos=(490, 790),
                                              pointer_line=((546, 622), (680, 610)),
                                              axes_to_enable={'x': True, 'rx': True, 'y': True, 'ry': True, 'z': True},
                                              mask_file='img/ml_mask.png')
        self.ml_zone.double_clicked.connect(self.ml_window.open)
        self.micr_scheme.zones.append(self.ml_zone)

        self.micr_scheme.setMouseTracking(True)

        self.ml_zone.double_clicked.connect(self.ml_window.open)
        self.conn_btn.clicked.connect(self.conn_window.open)

        # self.GoButton.clicked.connect(self.go_to)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('macos')
    form = MainWindow()
    form.show()
    # form.update() #start with something
    app.exec()

    print("DONE")