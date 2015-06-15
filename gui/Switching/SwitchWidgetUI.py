# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './gui/Switching/SwitchWidgetUI.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
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

class Ui_SwitchWidget(object):
    def setupUi(self, SwitchWidget):
        SwitchWidget.setObjectName(_fromUtf8("SwitchWidget"))
        SwitchWidget.resize(400, 61)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SwitchWidget.sizePolicy().hasHeightForWidth())
        SwitchWidget.setSizePolicy(sizePolicy)
        self.gridLayout = QtGui.QGridLayout(SwitchWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.calOnLabel = QtGui.QLabel(SwitchWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.calOnLabel.sizePolicy().hasHeightForWidth())
        self.calOnLabel.setSizePolicy(sizePolicy)
        self.calOnLabel.setObjectName(_fromUtf8("calOnLabel"))
        self.gridLayout.addWidget(self.calOnLabel, 0, 1, 1, 1)
        self.calOffLabel = QtGui.QLabel(SwitchWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.calOffLabel.sizePolicy().hasHeightForWidth())
        self.calOffLabel.setSizePolicy(sizePolicy)
        self.calOffLabel.setObjectName(_fromUtf8("calOffLabel"))
        self.gridLayout.addWidget(self.calOffLabel, 0, 2, 1, 1)
        self.calOnVal = QtGui.QDoubleSpinBox(SwitchWidget)
        self.calOnVal.setObjectName(_fromUtf8("calOnVal"))
        self.gridLayout.addWidget(self.calOnVal, 1, 1, 1, 1)
        self.calOffVal = QtGui.QDoubleSpinBox(SwitchWidget)
        self.calOffVal.setObjectName(_fromUtf8("calOffVal"))
        self.gridLayout.addWidget(self.calOffVal, 1, 2, 1, 1)
        self.switchTimeLabel = QtGui.QLabel(SwitchWidget)
        self.switchTimeLabel.setObjectName(_fromUtf8("switchTimeLabel"))
        self.gridLayout.addWidget(self.switchTimeLabel, 1, 3, 1, 1)
        self.switchTImeLabelLabel = QtGui.QLabel(SwitchWidget)
        self.switchTImeLabelLabel.setObjectName(_fromUtf8("switchTImeLabelLabel"))
        self.gridLayout.addWidget(self.switchTImeLabelLabel, 0, 3, 1, 1)
        self.SwitchButton = QtGui.QCheckBox(SwitchWidget)
        self.SwitchButton.setCheckable(True)
        self.SwitchButton.setChecked(False)
        self.SwitchButton.setObjectName(_fromUtf8("SwitchButton"))
        self.gridLayout.addWidget(self.SwitchButton, 1, 0, 1, 1)

        self.retranslateUi(SwitchWidget)
        QtCore.QMetaObject.connectSlotsByName(SwitchWidget)

    def retranslateUi(self, SwitchWidget):
        SwitchWidget.setWindowTitle(_translate("SwitchWidget", "Form", None))
        self.calOnLabel.setText(_translate("SwitchWidget", "On Calibration", None))
        self.calOffLabel.setText(_translate("SwitchWidget", "Off Calibration", None))
        self.switchTimeLabel.setText(_translate("SwitchWidget", "Switching Time", None))
        self.switchTImeLabelLabel.setText(_translate("SwitchWidget", "Switching time", None))
        self.SwitchButton.setText(_translate("SwitchWidget", "On", None))

