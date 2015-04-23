# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '.\gui\manager\ManagerWindowTemplate.ui'
#
# Created: Mon Apr 13 17:50:49 2015
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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.setGeometry(7,200,358, 298)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.loadAllButton = QtGui.QPushButton(self.centralwidget)
        self.loadAllButton.setObjectName(_fromUtf8("loadAllButton"))
        self.gridLayout.addWidget(self.loadAllButton, 0, 0, 1, 1)
        self.loadedModuleView = QtGui.QListView(self.centralwidget)
        self.loadedModuleView.setObjectName(_fromUtf8("loadedModuleView"))
        self.gridLayout.addWidget(self.loadedModuleView, 1, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 358, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuMenu = QtGui.QMenu(self.menubar)
        self.menuMenu.setObjectName(_fromUtf8("menuMenu"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.actionLoad_configuration = QtGui.QAction(MainWindow)
        self.actionLoad_configuration.setObjectName(_fromUtf8("actionLoad_configuration"))
        self.actionSave_configuration = QtGui.QAction(MainWindow)
        self.actionSave_configuration.setObjectName(_fromUtf8("actionSave_configuration"))
        self.action_Load_all_modules = QtGui.QAction(MainWindow)
        self.action_Load_all_modules.setObjectName(_fromUtf8("action_Load_all_modules"))
        self.actionStart_all_modules = QtGui.QAction(MainWindow)
        self.actionStart_all_modules.setObjectName(_fromUtf8("actionStart_all_modules"))
        self.actionQuit = QtGui.QAction(MainWindow)
        self.actionQuit.setObjectName(_fromUtf8("actionQuit"))
        self.menuMenu.addAction(self.actionLoad_configuration)
        self.menuMenu.addAction(self.actionSave_configuration)
        self.menuMenu.addSeparator()
        self.menuMenu.addAction(self.action_Load_all_modules)
        self.menuMenu.addAction(self.actionStart_all_modules)
        self.menuMenu.addSeparator()
        self.menuMenu.addAction(self.actionQuit)
        self.menubar.addAction(self.menuMenu.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))
        self.loadAllButton.setText(_translate("MainWindow", "Load all modules", None))
        self.menuMenu.setTitle(_translate("MainWindow", "Menu", None))
        self.actionLoad_configuration.setText(_translate("MainWindow", "Load configuration", None))
        self.actionSave_configuration.setText(_translate("MainWindow", "Save configuration", None))
        self.action_Load_all_modules.setText(_translate("MainWindow", " Load all modules", None))
        self.actionStart_all_modules.setText(_translate("MainWindow", "Start all modules", None))
        self.actionQuit.setText(_translate("MainWindow", "Quit", None))

