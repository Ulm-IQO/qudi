# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'OptimizerGuiUI.ui'
#
# Created: Tue Jun 23 20:59:11 2015
#      by: PyQt4 UI code generator 4.11.1
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
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.x_label.sizePolicy().hasHeightForWidth())
        self.x_label.setSizePolicy(sizePolicy)
        self.x_label.setObjectName(_fromUtf8("x_label"))
        self.horizontalLayout.addWidget(self.x_label)
        self.optimal_coordinates = QtGui.QLabel(self.centralwidget)
        self.optimal_coordinates.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.optimal_coordinates.setObjectName(_fromUtf8("optimal_coordinates"))
        self.horizontalLayout.addWidget(self.optimal_coordinates)
        self.gridLayout_2.addLayout(self.horizontalLayout, 1, 0, 1, 1)
        self.optimiseButton = QtGui.QPushButton(self.centralwidget)
        self.optimiseButton.setObjectName(_fromUtf8("optimiseButton"))
        self.gridLayout_2.addWidget(self.optimiseButton, 2, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 255, 20))
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
        MainWindow.setWindowTitle(_translate("MainWindow", "qudi: Optimizer", None))
        self.x_label.setText(_translate("MainWindow", "(x,y,z): ", None))
        self.optimal_coordinates.setToolTip(_translate("MainWindow", "This text is selectable.  Copy and paste into labnotes.", None))
        self.optimal_coordinates.setText(_translate("MainWindow", "(?, ?, ?)", None))
        self.optimiseButton.setText(_translate("MainWindow", "Optimise position", None))
        self.menuOptions.setTitle(_translate("MainWindow", "&Options", None))
        self.menu_File.setTitle(_translate("MainWindow", "&File", None))
        self.action_Settings.setText(_translate("MainWindow", "&Settings", None))
        self.action_Exit.setText(_translate("MainWindow", "&Exit", None))

from pyqtgraph import PlotWidget
