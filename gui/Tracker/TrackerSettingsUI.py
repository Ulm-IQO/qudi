# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'TrackerSettings.ui'
#
# Created: Thu Apr 30 12:52:59 2015
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
        SettingsDialog.resize(432, 234)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SettingsDialog.sizePolicy().hasHeightForWidth())
        SettingsDialog.setSizePolicy(sizePolicy)
        self.gridLayout_2 = QtGui.QGridLayout(SettingsDialog)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem, 1, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(SettingsDialog)
        self.buttonBox.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Apply|QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout_2.addWidget(self.buttonBox, 2, 0, 1, 1)
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_2 = QtGui.QLabel(SettingsDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.xy_refocusrange_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.xy_refocusrange_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.xy_refocusrange_InputWidget.setObjectName(_fromUtf8("xy_refocusrange_InputWidget"))
        self.gridLayout.addWidget(self.xy_refocusrange_InputWidget, 0, 1, 1, 1)
        self.label = QtGui.QLabel(SettingsDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.z_refocusstepsize_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.z_refocusstepsize_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.z_refocusstepsize_InputWidget.setObjectName(_fromUtf8("z_refocusstepsize_InputWidget"))
        self.gridLayout.addWidget(self.z_refocusstepsize_InputWidget, 3, 1, 1, 1)
        self.z_refocusrange_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.z_refocusrange_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.z_refocusrange_InputWidget.setObjectName(_fromUtf8("z_refocusrange_InputWidget"))
        self.gridLayout.addWidget(self.z_refocusrange_InputWidget, 2, 1, 1, 1)
        self.xy_refocusstepsize_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.xy_refocusstepsize_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.xy_refocusstepsize_InputWidget.setObjectName(_fromUtf8("xy_refocusstepsize_InputWidget"))
        self.gridLayout.addWidget(self.xy_refocusstepsize_InputWidget, 1, 1, 1, 1)
        self.label_3 = QtGui.QLabel(SettingsDialog)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.label_4 = QtGui.QLabel(SettingsDialog)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)
        self.line = QtGui.QFrame(SettingsDialog)
        self.line.setFrameShape(QtGui.QFrame.VLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.gridLayout.addWidget(self.line, 0, 2, 4, 1)
        self.count_freq_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.count_freq_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.count_freq_InputWidget.setObjectName(_fromUtf8("count_freq_InputWidget"))
        self.gridLayout.addWidget(self.count_freq_InputWidget, 1, 4, 1, 1)
        self.return_slow_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.return_slow_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.return_slow_InputWidget.setObjectName(_fromUtf8("return_slow_InputWidget"))
        self.gridLayout.addWidget(self.return_slow_InputWidget, 2, 4, 1, 1)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 1, 5, 1, 1)
        self.label_5 = QtGui.QLabel(SettingsDialog)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout.addWidget(self.label_5, 1, 3, 1, 1)
        self.label_6 = QtGui.QLabel(SettingsDialog)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout.addWidget(self.label_6, 2, 3, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.retranslateUi(SettingsDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), SettingsDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), SettingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SettingsDialog)

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(QtGui.QApplication.translate("SettingsDialog", "qudi: Tracker - Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("SettingsDialog", "XY Range :", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("SettingsDialog", "XY Stepsize :", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("SettingsDialog", "Z Range :", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("SettingsDialog", "Z Stepsize :", None, QtGui.QApplication.UnicodeUTF8))
        self.label_5.setText(QtGui.QApplication.translate("SettingsDialog", "Count frequency :", None, QtGui.QApplication.UnicodeUTF8))
        self.label_6.setText(QtGui.QApplication.translate("SettingsDialog", "return slowdown :", None, QtGui.QApplication.UnicodeUTF8))

