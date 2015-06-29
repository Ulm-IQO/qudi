# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './gui/console/ConsoleWindowUI.ui'
#
# Created by: PyQt4 UI code generator 4.11.3
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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(800, 600)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 19))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuOptions = QtGui.QMenu(self.menubar)
        self.menuOptions.setObjectName(_fromUtf8("menuOptions"))
        self.menuConsole = QtGui.QMenu(self.menubar)
        self.menuConsole.setObjectName(_fromUtf8("menuConsole"))
        MainWindow.setMenuBar(self.menubar)
        self.actionSettings = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("preferences-system"))
        self.actionSettings.setIcon(icon)
        self.actionSettings.setObjectName(_fromUtf8("actionSettings"))
        self.actionClose = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("application-exit"))
        self.actionClose.setIcon(icon)
        self.actionClose.setObjectName(_fromUtf8("actionClose"))
        self.menuOptions.addAction(self.actionSettings)
        self.menuConsole.addAction(self.actionClose)
        self.menubar.addAction(self.menuConsole.menuAction())
        self.menubar.addAction(self.menuOptions.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QObject.connect(self.actionClose, QtCore.SIGNAL(_fromUtf8("triggered()")), MainWindow.close)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "qudi: Console", None))
        self.menuOptions.setTitle(_translate("MainWindow", "Options", None))
        self.menuConsole.setTitle(_translate("MainWindow", "Console", None))
        self.actionSettings.setText(_translate("MainWindow", "Settings", None))
        self.actionClose.setText(_translate("MainWindow", "Close", None))

