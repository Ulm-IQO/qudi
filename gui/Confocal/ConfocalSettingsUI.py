# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ConfocalSettingsUI.ui'
#
# Created: Sat May 23 18:32:47 2015
#      by: PyQt4 UI code generator 4.10.4
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
        SettingsDialog.resize(281, 249)
        self.gridLayout_2 = QtGui.QGridLayout(SettingsDialog)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.slider_stepwidth_InputWidget = QtGui.QDoubleSpinBox(SettingsDialog)
        self.slider_stepwidth_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.slider_stepwidth_InputWidget.setButtonSymbols(QtGui.QAbstractSpinBox.UpDownArrows)
        self.slider_stepwidth_InputWidget.setAccelerated(True)
        self.slider_stepwidth_InputWidget.setDecimals(3)
        self.slider_stepwidth_InputWidget.setSingleStep(0.0)
        self.slider_stepwidth_InputWidget.setProperty("value", 0.001)
        self.slider_stepwidth_InputWidget.setObjectName(_fromUtf8("slider_stepwidth_InputWidget"))
        self.gridLayout.addWidget(self.slider_stepwidth_InputWidget, 4, 1, 1, 1)
        self.label_4 = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_4.setFont(font)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)
        self.label_5 = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_5.setFont(font)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)
        self.fixed_aspect_xz_checkBox = QtGui.QCheckBox(SettingsDialog)
        self.fixed_aspect_xz_checkBox.setMaximumSize(QtCore.QSize(30, 16777215))
        self.fixed_aspect_xz_checkBox.setText(_fromUtf8(""))
        self.fixed_aspect_xz_checkBox.setChecked(True)
        self.fixed_aspect_xz_checkBox.setObjectName(_fromUtf8("fixed_aspect_xz_checkBox"))
        self.gridLayout.addWidget(self.fixed_aspect_xz_checkBox, 3, 1, 1, 1)
        self.fixed_aspect_xy_checkBox = QtGui.QCheckBox(SettingsDialog)
        self.fixed_aspect_xy_checkBox.setEnabled(True)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fixed_aspect_xy_checkBox.sizePolicy().hasHeightForWidth())
        self.fixed_aspect_xy_checkBox.setSizePolicy(sizePolicy)
        self.fixed_aspect_xy_checkBox.setMaximumSize(QtCore.QSize(20, 16777215))
        self.fixed_aspect_xy_checkBox.setAccessibleDescription(_fromUtf8(""))
        self.fixed_aspect_xy_checkBox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.fixed_aspect_xy_checkBox.setAutoFillBackground(False)
        self.fixed_aspect_xy_checkBox.setText(_fromUtf8(""))
        self.fixed_aspect_xy_checkBox.setChecked(True)
        self.fixed_aspect_xy_checkBox.setObjectName(_fromUtf8("fixed_aspect_xy_checkBox"))
        self.gridLayout.addWidget(self.fixed_aspect_xy_checkBox, 2, 1, 1, 1)
        self.label_3 = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_3.setFont(font)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.clock_frequency_InputWidget = QtGui.QLineEdit(SettingsDialog)
        self.clock_frequency_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.clock_frequency_InputWidget.setObjectName(_fromUtf8("clock_frequency_InputWidget"))
        self.gridLayout.addWidget(self.clock_frequency_InputWidget, 0, 1, 1, 1)
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
        self.label_7 = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_7.setFont(font)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.gridLayout.addWidget(self.label_7, 6, 0, 1, 1)
        self.x_padding_InputWidget = QtGui.QDoubleSpinBox(SettingsDialog)
        self.x_padding_InputWidget.setObjectName(_fromUtf8("x_padding_InputWidget"))
        self.gridLayout.addWidget(self.x_padding_InputWidget, 5, 1, 1, 1)
        self.y_padding_InputWidget = QtGui.QDoubleSpinBox(SettingsDialog)
        self.y_padding_InputWidget.setObjectName(_fromUtf8("y_padding_InputWidget"))
        self.gridLayout.addWidget(self.y_padding_InputWidget, 6, 1, 1, 1)
        self.label_6 = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_6.setFont(font)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout.addWidget(self.label_6, 5, 0, 1, 1)
        self.z_padding_InputWidget = QtGui.QDoubleSpinBox(SettingsDialog)
        self.z_padding_InputWidget.setObjectName(_fromUtf8("z_padding_InputWidget"))
        self.gridLayout.addWidget(self.z_padding_InputWidget, 7, 1, 1, 1)
        self.label_8 = QtGui.QLabel(SettingsDialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_8.setFont(font)
        self.label_8.setObjectName(_fromUtf8("label_8"))
        self.gridLayout.addWidget(self.label_8, 7, 0, 1, 1)
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
        SettingsDialog.setWindowTitle(_translate("SettingsDialog", "qudi: Confocal - Settings", None))
        self.label_4.setText(_translate("SettingsDialog", "Fixed Aspect Ratio XZ Scan :", None))
        self.label_5.setText(_translate("SettingsDialog", "Slider Stepwidth with Keys :", None))
        self.label_3.setText(_translate("SettingsDialog", "Fixed Aspect Ratio XY Scan :", None))
        self.label_2.setText(_translate("SettingsDialog", "Return slowness :", None))
        self.label.setText(_translate("SettingsDialog", "Clock frequency :", None))
        self.label_7.setText(_translate("SettingsDialog", "y Padding for image display (%)", None))
        self.label_6.setText(_translate("SettingsDialog", "x Padding for image display (%)", None))
        self.label_8.setText(_translate("SettingsDialog", "z Padding for image display (%)", None))

