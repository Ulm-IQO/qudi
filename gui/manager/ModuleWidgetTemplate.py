# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './gui/manager/ModuleWidgetTemplate.ui'
#
# Created: Thu Apr 30 10:30:27 2015
#      by: PyQt4 UI code generator 4.11.3
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

class Ui_ModuleWidget(object):
    def setupUi(self, ModuleWidget):
        ModuleWidget.setObjectName(_fromUtf8("ModuleWidget"))
        ModuleWidget.resize(400, 60)
        ModuleWidget.setMaximumSize(QtCore.QSize(400, 16777215))
        self.gridLayout = QtGui.QGridLayout(ModuleWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.loadButton = QtGui.QPushButton(ModuleWidget)
        self.loadButton.setObjectName(_fromUtf8("loadButton"))
        self.gridLayout.addWidget(self.loadButton, 0, 0, 1, 1)
        self.reloadButton = QtGui.QToolButton(ModuleWidget)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("view-refresh"))
        self.reloadButton.setIcon(icon)
        self.reloadButton.setObjectName(_fromUtf8("reloadButton"))
        self.gridLayout.addWidget(self.reloadButton, 0, 1, 1, 1)
        self.unloadButton = QtGui.QToolButton(ModuleWidget)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("application-exit"))
        self.unloadButton.setIcon(icon)
        self.unloadButton.setObjectName(_fromUtf8("unloadButton"))
        self.gridLayout.addWidget(self.unloadButton, 0, 2, 1, 1)
        self.statusLabel = QtGui.QLabel(ModuleWidget)
        self.statusLabel.setObjectName(_fromUtf8("statusLabel"))
        self.gridLayout.addWidget(self.statusLabel, 1, 0, 1, 3)

        self.retranslateUi(ModuleWidget)
        QtCore.QMetaObject.connectSlotsByName(ModuleWidget)

    def retranslateUi(self, ModuleWidget):
        ModuleWidget.setWindowTitle(_translate("ModuleWidget", "Form", None))
        self.loadButton.setText(_translate("ModuleWidget", "Load something.", None))
        self.reloadButton.setText(_translate("ModuleWidget", "...", None))
        self.unloadButton.setText(_translate("ModuleWidget", "...", None))
        self.statusLabel.setText(_translate("ModuleWidget", "Module status goes here.", None))

