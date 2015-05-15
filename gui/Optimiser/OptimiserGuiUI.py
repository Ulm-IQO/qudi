# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'OptimiserGuiUI.ui'
#
# Created: Fri May 15 16:46:40 2015
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
        MainWindow.resize(255, 412)
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
        self.xy_refocus_ViewWidget = PlotWidget(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(6)
        sizePolicy.setHeightForWidth(self.xy_refocus_ViewWidget.sizePolicy().hasHeightForWidth())
        self.xy_refocus_ViewWidget.setSizePolicy(sizePolicy)
        self.xy_refocus_ViewWidget.setObjectName(_fromUtf8("xy_refocus_ViewWidget"))
        self.gridLayout.addWidget(self.xy_refocus_ViewWidget, 4, 0, 1, 1)
        self.xy_refocus_cb_ViewWidget = PlotWidget(self.centralwidget)
        self.xy_refocus_cb_ViewWidget.setMaximumSize(QtCore.QSize(70, 16777215))
        self.xy_refocus_cb_ViewWidget.setObjectName(_fromUtf8("xy_refocus_cb_ViewWidget"))
        self.gridLayout.addWidget(self.xy_refocus_cb_ViewWidget, 4, 1, 1, 1)
        self.xz_refocus_ViewWidget = PlotWidget(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(5)
        sizePolicy.setHeightForWidth(self.xz_refocus_ViewWidget.sizePolicy().hasHeightForWidth())
        self.xz_refocus_ViewWidget.setSizePolicy(sizePolicy)
        self.xz_refocus_ViewWidget.setObjectName(_fromUtf8("xz_refocus_ViewWidget"))
        self.gridLayout.addWidget(self.xz_refocus_ViewWidget, 5, 0, 1, 2)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.x_label = QtGui.QLabel(self.centralwidget)
        self.x_label.setObjectName(_fromUtf8("x_label"))
        self.horizontalLayout.addWidget(self.x_label)
        self.optimal_x = QtGui.QLineEdit(self.centralwidget)
        self.optimal_x.setObjectName(_fromUtf8("optimal_x"))
        self.horizontalLayout.addWidget(self.optimal_x)
        self.y_label = QtGui.QLabel(self.centralwidget)
        self.y_label.setObjectName(_fromUtf8("y_label"))
        self.horizontalLayout.addWidget(self.y_label)
        self.optimal_y = QtGui.QLineEdit(self.centralwidget)
        self.optimal_y.setObjectName(_fromUtf8("optimal_y"))
        self.horizontalLayout.addWidget(self.optimal_y)
        self.z_label = QtGui.QLabel(self.centralwidget)
        self.z_label.setObjectName(_fromUtf8("z_label"))
        self.horizontalLayout.addWidget(self.z_label)
        self.optimal_z = QtGui.QLineEdit(self.centralwidget)
        self.optimal_z.setObjectName(_fromUtf8("optimal_z"))
        self.horizontalLayout.addWidget(self.optimal_z)
        self.gridLayout_2.addLayout(self.horizontalLayout, 1, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 255, 26))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuOptions = QtGui.QMenu(self.menubar)
        self.menuOptions.setObjectName(_fromUtf8("menuOptions"))
        self.menu_File = QtGui.QMenu(self.menubar)
        self.menu_File.setObjectName(_fromUtf8("menu_File"))
        MainWindow.setMenuBar(self.menubar)
        self.action_Settings = QtGui.QAction(MainWindow)
        self.action_Settings.setObjectName(_fromUtf8("action_Settings"))
        self.action_Exit = QtGui.QAction(MainWindow)
        self.action_Exit.setObjectName(_fromUtf8("action_Exit"))
        self.menuOptions.addAction(self.action_Settings)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.action_Exit)
        self.menubar.addAction(self.menu_File.menuAction())
        self.menubar.addAction(self.menuOptions.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QObject.connect(self.action_Exit, QtCore.SIGNAL(_fromUtf8("triggered()")), MainWindow.close)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "qudi: Optimiser", None, QtGui.QApplication.UnicodeUTF8))
        self.x_label.setText(QtGui.QApplication.translate("MainWindow", "X", None, QtGui.QApplication.UnicodeUTF8))
        self.y_label.setText(QtGui.QApplication.translate("MainWindow", "Y", None, QtGui.QApplication.UnicodeUTF8))
        self.z_label.setText(QtGui.QApplication.translate("MainWindow", "Z", None, QtGui.QApplication.UnicodeUTF8))
        self.menuOptions.setTitle(QtGui.QApplication.translate("MainWindow", "&Options", None, QtGui.QApplication.UnicodeUTF8))
        self.menu_File.setTitle(QtGui.QApplication.translate("MainWindow", "&File", None, QtGui.QApplication.UnicodeUTF8))
        self.action_Settings.setText(QtGui.QApplication.translate("MainWindow", "&Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.action_Exit.setText(QtGui.QApplication.translate("MainWindow", "&Exit", None, QtGui.QApplication.UnicodeUTF8))

from pyqtgraph import PlotWidget
