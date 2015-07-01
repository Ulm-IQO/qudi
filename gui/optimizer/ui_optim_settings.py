# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_optim_settings.ui'
#
# Created: Thu Jul  2 00:24:28 2015
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
        self.label_3 = QtGui.QLabel(SettingsDialog)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.label_4 = QtGui.QLabel(SettingsDialog)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)
        self.label_2 = QtGui.QLabel(SettingsDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.line = QtGui.QFrame(SettingsDialog)
        self.line.setFrameShape(QtGui.QFrame.VLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.gridLayout.addWidget(self.line, 0, 2, 4, 1)
        self.label = QtGui.QLabel(SettingsDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 1, 5, 1, 1)
        self.label_5 = QtGui.QLabel(SettingsDialog)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout.addWidget(self.label_5, 1, 3, 1, 1)
        self.label_6 = QtGui.QLabel(SettingsDialog)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout.addWidget(self.label_6, 2, 3, 1, 1)
        self.xy_refocusrange_DoubleSpinBox = QtGui.QDoubleSpinBox(SettingsDialog)
        self.xy_refocusrange_DoubleSpinBox.setButtonSymbols(QtGui.QAbstractSpinBox.PlusMinus)
        self.xy_refocusrange_DoubleSpinBox.setSpecialValueText(_fromUtf8(""))
        self.xy_refocusrange_DoubleSpinBox.setDecimals(3)
        self.xy_refocusrange_DoubleSpinBox.setMaximum(10.0)
        self.xy_refocusrange_DoubleSpinBox.setSingleStep(0.01)
        self.xy_refocusrange_DoubleSpinBox.setProperty("value", 0.6)
        self.xy_refocusrange_DoubleSpinBox.setObjectName(_fromUtf8("xy_refocusrange_DoubleSpinBox"))
        self.gridLayout.addWidget(self.xy_refocusrange_DoubleSpinBox, 0, 1, 1, 1)
        self.xy_refocusstepsize_DoubleSpinBox = QtGui.QDoubleSpinBox(SettingsDialog)
        self.xy_refocusstepsize_DoubleSpinBox.setDecimals(3)
        self.xy_refocusstepsize_DoubleSpinBox.setMaximum(10.0)
        self.xy_refocusstepsize_DoubleSpinBox.setSingleStep(0.001)
        self.xy_refocusstepsize_DoubleSpinBox.setProperty("value", 0.06)
        self.xy_refocusstepsize_DoubleSpinBox.setObjectName(_fromUtf8("xy_refocusstepsize_DoubleSpinBox"))
        self.gridLayout.addWidget(self.xy_refocusstepsize_DoubleSpinBox, 1, 1, 1, 1)
        self.z_refocusrange_DoubleSpinBox = QtGui.QDoubleSpinBox(SettingsDialog)
        self.z_refocusrange_DoubleSpinBox.setSuffix(_fromUtf8(""))
        self.z_refocusrange_DoubleSpinBox.setDecimals(3)
        self.z_refocusrange_DoubleSpinBox.setMaximum(5.0)
        self.z_refocusrange_DoubleSpinBox.setSingleStep(0.01)
        self.z_refocusrange_DoubleSpinBox.setProperty("value", 2.0)
        self.z_refocusrange_DoubleSpinBox.setObjectName(_fromUtf8("z_refocusrange_DoubleSpinBox"))
        self.gridLayout.addWidget(self.z_refocusrange_DoubleSpinBox, 2, 1, 1, 1)
        self.z_refocusstepsize_DoubleSpinBox = QtGui.QDoubleSpinBox(SettingsDialog)
        self.z_refocusstepsize_DoubleSpinBox.setDecimals(3)
        self.z_refocusstepsize_DoubleSpinBox.setMaximum(1.0)
        self.z_refocusstepsize_DoubleSpinBox.setSingleStep(0.001)
        self.z_refocusstepsize_DoubleSpinBox.setProperty("value", 0.1)
        self.z_refocusstepsize_DoubleSpinBox.setObjectName(_fromUtf8("z_refocusstepsize_DoubleSpinBox"))
        self.gridLayout.addWidget(self.z_refocusstepsize_DoubleSpinBox, 3, 1, 1, 1)
        self.return_slow_SpinBox = QtGui.QSpinBox(SettingsDialog)
        self.return_slow_SpinBox.setMaximum(1000)
        self.return_slow_SpinBox.setProperty("value", 20)
        self.return_slow_SpinBox.setObjectName(_fromUtf8("return_slow_SpinBox"))
        self.gridLayout.addWidget(self.return_slow_SpinBox, 2, 4, 1, 1)
        self.count_freq_SpinBox = QtGui.QSpinBox(SettingsDialog)
        self.count_freq_SpinBox.setMaximum(10000)
        self.count_freq_SpinBox.setProperty("value", 200)
        self.count_freq_SpinBox.setObjectName(_fromUtf8("count_freq_SpinBox"))
        self.gridLayout.addWidget(self.count_freq_SpinBox, 1, 4, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.retranslateUi(SettingsDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), SettingsDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), SettingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SettingsDialog)

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(_translate("SettingsDialog", "qudi: Optimizer - Settings", None))
        self.label_3.setText(_translate("SettingsDialog", "Z Range (µm):", None))
        self.label_4.setText(_translate("SettingsDialog", "Z Stepsize (µm):", None))
        self.label_2.setToolTip(_translate("SettingsDialog", "<html><head/><body><p><br/></p></body></html>", None))
        self.label_2.setText(_translate("SettingsDialog", "XY Range (µm):", None))
        self.label.setText(_translate("SettingsDialog", "XY Stepsize (µm):", None))
        self.label_5.setToolTip(_translate("SettingsDialog", "<html><head/><body><p><span style=\" font-size:10pt;\">That is the inverse time how long the scanner stays at the desired position during the scan and counts.</span></p></body></html>", None))
        self.label_5.setText(_translate("SettingsDialog", "Count frequency (Hz):", None))
        self.label_6.setToolTip(_translate("SettingsDialog", "<html><head/><body><p><span style=\" font-size:10pt;\">That is basically the \'scan\' resolution when the scanner moves backwards to prepare to scan again a line. </span></p><p><span style=\" font-size:10pt;\">How many points are scanned in one line is depending on the resolution. Since the scanner is permanently counting during the scan, only the clock frequency determined the speed, how fast a line is scanned by a given resolution. If the scanner has to move back, it uses the same scan line method but just in the reverse. How many points are approached in the backwards movement depends on the \'return slowness\' parameter. If you scan with 10 point resolution (for XY Range of 10 and YX Stepsize of 1) and set return slowness to 2, than the return movement will be 5 times faster.</span></p></body></html>", None))
        self.label_6.setText(_translate("SettingsDialog", "return slowdown (points):", None))
        self.xy_refocusrange_DoubleSpinBox.setToolTip(_translate("SettingsDialog", "<html><head/><body><p><span style=\" font-size:10pt;\">Scan range of the optimizer in the xy area.</span></p></body></html>", None))
        self.xy_refocusstepsize_DoubleSpinBox.setToolTip(_translate("SettingsDialog", "<html><head/><body><p><span style=\" font-size:10pt;\">Specify the distance between two subsequent scanned points for optimizer in xy scan.</span></p></body></html>", None))
        self.z_refocusrange_DoubleSpinBox.setToolTip(_translate("SettingsDialog", "<html><head/><body><p><span style=\" font-size:10pt;\">Scan range of the optimizer in the z direction.</span></p></body></html>", None))
        self.z_refocusstepsize_DoubleSpinBox.setToolTip(_translate("SettingsDialog", "<html><head/><body><p><span style=\" font-size:10pt;\">Specify the distance between two subsequent scanned points for optimizer z scan.</span></p></body></html>", None))
        self.return_slow_SpinBox.setToolTip(_translate("SettingsDialog", "<html><head/><body><p>That is basically the \'scan\' resolution when the scanner moves backwards to prepare to scan again a line.</p></body></html>", None))

