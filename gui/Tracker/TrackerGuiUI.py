# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'TrackerGuiUI.ui'
#
# Created: Tue Apr 28 15:34:55 2015
#      by: PyQt4 UI code generator 4.9.5
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(469, 843)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout_2 = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.xz_refocus_ViewWidget = PlotWidget(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(5)
        sizePolicy.setHeightForWidth(self.xz_refocus_ViewWidget.sizePolicy().hasHeightForWidth())
        self.xz_refocus_ViewWidget.setSizePolicy(sizePolicy)
        self.xz_refocus_ViewWidget.setObjectName(_fromUtf8("xz_refocus_ViewWidget"))
        self.gridLayout.addWidget(self.xz_refocus_ViewWidget, 5, 0, 1, 1)
        self.xy_refocus_ViewWidget = PlotWidget(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(6)
        sizePolicy.setHeightForWidth(self.xy_refocus_ViewWidget.sizePolicy().hasHeightForWidth())
        self.xy_refocus_ViewWidget.setSizePolicy(sizePolicy)
        self.xy_refocus_ViewWidget.setObjectName(_fromUtf8("xy_refocus_ViewWidget"))
        self.gridLayout.addWidget(self.xy_refocus_ViewWidget, 4, 0, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 469, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuOptions = QtGui.QMenu(self.menubar)
        self.menuOptions.setObjectName(_fromUtf8("menuOptions"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.action_Settings = QtGui.QAction(MainWindow)
        self.action_Settings.setObjectName(_fromUtf8("action_Settings"))
        self.menuOptions.addAction(self.action_Settings)
        self.menubar.addAction(self.menuOptions.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "qudi: Tracker", None, QtGui.QApplication.UnicodeUTF8))
        self.menuOptions.setTitle(QtGui.QApplication.translate("MainWindow", "&Options", None, QtGui.QApplication.UnicodeUTF8))
        self.action_Settings.setText(QtGui.QApplication.translate("MainWindow", "&Settings", None, QtGui.QApplication.UnicodeUTF8))

from pyqtgraph import PlotWidget
