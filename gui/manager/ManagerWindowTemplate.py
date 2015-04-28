# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './gui/manager/ManagerWindowTemplate.ui'
#
# Created: Tue Apr 28 14:59:56 2015
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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(468, 547)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.toolBox = QtGui.QToolBox(self.centralwidget)
        self.toolBox.setObjectName(_fromUtf8("toolBox"))
        self.modules = QtGui.QWidget()
        self.modules.setGeometry(QtCore.QRect(0, 0, 123, 116))
        self.modules.setObjectName(_fromUtf8("modules"))
        self.gridLayout1 = QtGui.QGridLayout(self.modules)
        self.gridLayout1.setObjectName(_fromUtf8("gridLayout1"))
        self.loadAllButton = QtGui.QPushButton(self.modules)
        self.loadAllButton.setObjectName(_fromUtf8("loadAllButton"))
        self.gridLayout1.addWidget(self.loadAllButton, 0, 0, 1, 1)
        self.loadedModuleView = QtGui.QListView(self.modules)
        self.loadedModuleView.setObjectName(_fromUtf8("loadedModuleView"))
        self.gridLayout1.addWidget(self.loadedModuleView, 1, 0, 1, 1)
        self.toolBox.addItem(self.modules, _fromUtf8(""))
        self.page = QtGui.QWidget()
        self.page.setGeometry(QtCore.QRect(0, 0, 450, 432))
        self.page.setObjectName(_fromUtf8("page"))
        self.gridLayout2 = QtGui.QGridLayout(self.page)
        self.gridLayout2.setObjectName(_fromUtf8("gridLayout2"))
        self.treeWidget = QtGui.QTreeWidget(self.page)
        self.treeWidget.setObjectName(_fromUtf8("treeWidget"))
        self.treeWidget.headerItem().setText(0, _fromUtf8("1"))
        self.gridLayout2.addWidget(self.treeWidget, 0, 0, 1, 1)
        self.toolBox.addItem(self.page, _fromUtf8(""))
        self.gridLayout.addWidget(self.toolBox, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 468, 19))
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
        self.toolBox.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "qudi: Manager", None))
        self.loadAllButton.setText(_translate("MainWindow", "Load all modules", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.modules), _translate("MainWindow", "Modules", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page), _translate("MainWindow", "Configuraion", None))
        self.menuMenu.setTitle(_translate("MainWindow", "Menu", None))
        self.actionLoad_configuration.setText(_translate("MainWindow", "Load configuration", None))
        self.actionSave_configuration.setText(_translate("MainWindow", "Save configuration", None))
        self.action_Load_all_modules.setText(_translate("MainWindow", " Load all modules", None))
        self.actionStart_all_modules.setText(_translate("MainWindow", "Start all modules", None))
        self.actionQuit.setText(_translate("MainWindow", "Quit", None))

