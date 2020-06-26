# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

from MainGUI.gr_field import MyGraphField


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(527, 421)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_x = QtWidgets.QLabel(self.centralwidget)
        self.label_x.setMaximumSize(QtCore.QSize(60, 16777215))
        self.label_x.setObjectName("label_x")
        self.verticalLayout.addWidget(self.label_x)
        self.label_y = QtWidgets.QLabel(self.centralwidget)
        self.label_y.setMaximumSize(QtCore.QSize(60, 16777215))
        self.label_y.setObjectName("label_y")
        self.verticalLayout.addWidget(self.label_y)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.label_x_to = QtWidgets.QLabel(self.centralwidget)
        self.label_x_to.setText("")
        self.label_x_to.setObjectName("label_x_to")
        self.verticalLayout.addWidget(self.label_x_to)
        self.label_y_to = QtWidgets.QLabel(self.centralwidget)
        self.label_y_to.setText("")
        self.label_y_to.setObjectName("label_y_to")
        self.verticalLayout.addWidget(self.label_y_to)
        self.GoButton = QtWidgets.QPushButton(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.GoButton.sizePolicy().hasHeightForWidth())
        self.GoButton.setSizePolicy(sizePolicy)
        self.GoButton.setObjectName("GoButton")
        self.verticalLayout.addWidget(self.GoButton)
        self.FotoButton = QtWidgets.QPushButton(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.FotoButton.sizePolicy().hasHeightForWidth())
        self.FotoButton.setSizePolicy(sizePolicy)
        self.FotoButton.setObjectName("FotoButton")
        self.verticalLayout.addWidget(self.FotoButton)
        self.horizontalLayout.addLayout(self.verticalLayout)

        self.widget = MyGraphField(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setAutoFillBackground(True)
        self.widget.setObjectName("widget")
        self.horizontalLayout.addWidget(self.widget)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label_x.setText(_translate("MainWindow", "x: "))
        self.label_y.setText(_translate("MainWindow", "y: "))
        self.GoButton.setText(_translate("MainWindow", "fahr"))
        self.FotoButton.setText(_translate("MainWindow", "Foto"))

