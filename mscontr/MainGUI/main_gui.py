import sys

from PyQt6 import QtGui
from PyQt6.QtGui import QWindow
from PyQt6.QtWidgets import QMainWindow, QApplication, QPushButton
from PyQt6.uic import loadUi

from mscontr.MainGUI.arrows import Window
from mscontr.MainGUI.mcwidgets import MicroscopeScheme, MicroscopeZone, StandardMotorWindow, ConnectionWindow, \
    CalibrationWindow, PlasmaMotorWindow


class MainWindow(QMainWindow):
    micr_scheme: MicroscopeScheme
    conn_btn: QPushButton
    calibr_btn: QPushButton

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        loadUi('ui_forms/main_window.ui', self)

        self.micr_scheme.set_background_from_file('img/main_view.png', use_picture_coordinates=True)
        self.windows = []

        self.conn_window = ConnectionWindow()
        self.windows.append(self.conn_window)

        motors_zones = {"Multilayer": ('MirrorX', 'MirrorY', 'MirrorZ', 'MirrorRX', 'MirrorRY'),
                        "Probe": ('ProbeX', 'ProbeY', 'ProbeZ', 'ProbeRX'),
                        "Zonenplatte": ('ZPlatte_X', 'ZPlatte_Y', 'ZPlatte_Z'),
                        "Mittenstopp": ('CStoppX', 'CStoppY'),
                        "Jet": ('JetX', 'JetZ'),
                        "Laser": ('LaserX', 'LaserY')}

        self.calibr_window = CalibrationWindow(self.conn_window, motors_zones)
        self.windows.append(self.calibr_window)

        # Multilayer
        self.ml_window = StandardMotorWindow(self.conn_window,
                                             ['MirrorX', 'MirrorY', 'MirrorZ', 'MirrorRX', 'MirrorRY'],
                                             self.calibr_window,
                                             "Multilayer")
        self.windows.append(self.ml_window)
        self.ml_zone = MicroscopeZone(self.micr_scheme,
                                      'Multilayer',
                                      name_pos=(450, 622),
                                      axes_pos=(490, 790),
                                      pointer_line=((546, 622), (680, 610)),
                                      axes_to_enable={'x': True, 'rx': True, 'y': True, 'ry': True, 'z': True},
                                      mask_file='img/ml_mask.png')
        self.ml_zone.double_clicked.connect(self.ml_window.open)
        self.micr_scheme.zones.append(self.ml_zone)

        # Plasma Window
        self.plasma_window = PlasmaMotorWindow(self.conn_window, self.calibr_window, "Plasmakammer")
        self.windows.append(self.plasma_window)
        self.jet_zone = MicroscopeZone(self.micr_scheme,
                                       'Jet',
                                       name_pos=(1253, 105),
                                       axes_pos=(1253, 190),
                                       pointer_line=((1220, 127), (1181, 168)),
                                       axes_to_enable={'x': True, 'z': True},
                                       mask_file='img/jet_mask.png')
        self.jet_zone.double_clicked.connect(self.plasma_window.open)
        self.micr_scheme.zones.append(self.jet_zone)

        # Mittenstop
        self.mstopp_window = StandardMotorWindow(self.conn_window,
                                                 ['CStoppX', 'CStoppY'],
                                                 self.calibr_window,
                                                 "Mittenstop")
        self.windows.append(self.mstopp_window)
        self.mstopp_zone = MicroscopeZone(self.micr_scheme,
                                          'Mittenstopp',
                                          name_pos=(941, 867),
                                          axes_pos=(941 - 80, 867 + 120),
                                          pointer_line=((956, 835), (1093, 772)),
                                          axes_to_enable={'x': True, 'y': True},
                                          mask_file='img/mittenstop_mask.png')
        self.mstopp_zone.double_clicked.connect(self.mstopp_window.open)
        self.micr_scheme.zones.append(self.mstopp_zone)

        # Probe
        self.probe_window = StandardMotorWindow(self.conn_window,
                                                ['ProbeX', 'ProbeY', 'ProbeZ', 'ProbeRX'],
                                                self.calibr_window,
                                                "Probe")
        self.windows.append(self.probe_window)
        self.probe_zone = MicroscopeZone(self.micr_scheme,
                                         'Probe',
                                         name_pos=(1093, 1074),
                                         axes_pos=(1093 + 90, 1074),
                                         pointer_line=((1093, 1074 - 35), (1129, 957 + 10)),
                                         axes_to_enable={'x': True, 'rx': True, 'y': True, 'z': True},
                                         mask_file='img/probe_mask.png')
        self.probe_zone.double_clicked.connect(self.probe_window.open)
        self.micr_scheme.zones.append(self.probe_zone)

        # Zonenplatte
        self.zplatte_window = StandardMotorWindow(self.conn_window,
                                                  ['ZPlatte_X', 'ZPlatte_Y', 'ZPlatte_Z'],
                                                  self.calibr_window,
                                                  "Zonenplatte")
        self.windows.append(self.zplatte_window)
        self.zplatte_zone = MicroscopeZone(self.micr_scheme,
                                           'Zonenplatte',
                                           name_pos=(1637-40, 598),
                                           axes_pos=(1637 -40 - 20, 598 + 120),
                                           pointer_line=((1477 + 20, 649), (1374, 793)),
                                           axes_to_enable={'x': True, 'y': True, 'z': True},
                                           mask_file='img/zplatte_mask.png')
        self.zplatte_zone.double_clicked.connect(self.zplatte_window.open)
        self.micr_scheme.zones.append(self.zplatte_zone)

        self.micr_scheme.setMouseTracking(True)

        self.ml_zone.double_clicked.connect(self.ml_window.open)
        self.conn_btn.clicked.connect(self.conn_window.open)
        self.calibr_btn.clicked.connect(self.calibr_window.open)

        # self.GoButton.clicked.connect(self.go_to)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.calibr_window.stop_all()
        self.conn_window.disconnect_all()
        super(MainWindow, self).closeEvent(a0)
        for window in self.windows:
            window.close()
        # sys.exit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('macos')
    form = MainWindow()
    form.show()
    # form.update() #start with something
    app.exec()

    print("DONE")
