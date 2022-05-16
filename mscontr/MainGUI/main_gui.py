import sys

from PyQt6.QtGui import QWindow
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.uic import loadUi

from mscontr.MainGUI.arrows import Window
from mscontr.MainGUI.mcwidgets import MicroscopeScheme, MicroscopeZone


class MainWindow(QMainWindow):

    micr_scheme: MicroscopeScheme

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        loadUi('ui_forms/main_window.ui', self)

        self.micr_scheme.set_background_from_file('img/main_view.png', use_picture_coordinates=True)

        self.ml_zone = MicroscopeZone(self.micr_scheme,
                                              'Multilayer',
                                              name_pos=(450, 622),
                                              axes_pos=(490, 790),
                                              pointer_line=((546, 622), (680, 610)),
                                              axes_to_enable={'x': True, 'rx': True, 'y': True, 'ry': True, 'z': True},
                                              mask_file='img/ml_mask.png')

        self.micr_scheme.zones.append(self.ml_zone)
        self.micr_scheme.setMouseTracking(True)

        self.window = Window()
        self.window.hide()

        self.ml_zone.double_clicked.connect(self.open_window)

        # self.GoButton.clicked.connect(self.go_to)

    def open_window(self):

        self.window.show()
        self.window.raise_()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('macos')
    form = MainWindow()
    form.show()
    # form.update() #start with something
    app.exec()

    print("DONE")