# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ConfocalSettingsUI.ui'
#
# Created: Mon May 18 10:14:53 2015
#      by: PyQt4 UI code generator 4.9.5
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        SettingsDialog.setObjectName(_fromUtf8("SettingsDialog"))
        SettingsDialog.resize(255, 95)
        self.gridLayout_2 = QtGui.QGridLayout(SettingsDialog)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_2 = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.label = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.return_slowness_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.return_slowness_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.return_slowness_InputWidget.setObjectName(_fromUtf8("return_slowness_InputWidget"))
        self.gridLayout.addWidget(self.return_slowness_InputWidget, 1, 1, 1, 1)
        self.clock_frequency_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.clock_frequency_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.clock_frequency_InputWidget.setObjectName(_fromUtf8("clock_frequency_InputWidget"))
        self.gridLayout.addWidget(self.clock_frequency_InputWidget, 0, 1, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 1, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(SettingsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Apply|QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout_2.addWidget(self.buttonBox, 1, 1, 1, 1)

        self.retranslateUi(SettingsDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), SettingsDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), SettingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SettingsDialog)

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(QtGui.QApplication.translate("SettingsDialog", "qudi: Confocal - Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("SettingsDialog", "Return slowness :", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("SettingsDialog", "Clock frequency :", None, QtGui.QApplication.UnicodeUTF8))

