# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_odmr_settings.ui'
#
# Created: Wed Jul  8 09:55:29 2015
#      by: PyQt4 UI code generator 4.11.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        SettingsDialog.setObjectName(_fromUtf8("SettingsDialog"))
        SettingsDialog.resize(255, 146)
        self.gridLayout_2 = QtGui.QGridLayout(SettingsDialog)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.matrix_lines_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.matrix_lines_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.matrix_lines_InputWidget.setObjectName(_fromUtf8("matrix_lines_InputWidget"))
        self.gridLayout.addWidget(self.matrix_lines_InputWidget, 0, 1, 1, 1)
        self.label_2 = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.clock_frequency_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.clock_frequency_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.clock_frequency_InputWidget.setObjectName(_fromUtf8("clock_frequency_InputWidget"))
        self.gridLayout.addWidget(self.clock_frequency_InputWidget, 1, 1, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(SettingsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Apply|QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout_2.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(SettingsDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), SettingsDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), SettingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SettingsDialog)

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(_translate("SettingsDialog", "qudi: ODMR - Settings", None))
        self.label.setToolTip(_translate("SettingsDialog", "This is the number of lines plotted in the Matrix Plot (lower plot).", None))
        self.label.setText(_translate("SettingsDialog", "Matrix Lines :", None))
        self.matrix_lines_InputWidget.setToolTip(_translate("SettingsDialog", "This is the number of lines plotted in the Matrix Plot (lower plot).", None))
        self.label_2.setToolTip(_translate("SettingsDialog", "That is the inverse time how long the scanner stays at the desired frequency and counts.", None))
        self.label_2.setText(_translate("SettingsDialog", "clock frequency :", None))
        self.clock_frequency_InputWidget.setToolTip(_translate("SettingsDialog", "That is the inverse time how long the scanner stays at the desired frequency and counts.", None))

