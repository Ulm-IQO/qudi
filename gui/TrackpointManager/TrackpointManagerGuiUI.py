# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'TrackpointManagerUI.ui'
#
# Created: Tue May  5 21:16:41 2015
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

class Ui_TrackpointManager(object):
    def setupUi(self, TrackpointManager):
        TrackpointManager.setObjectName(_fromUtf8("TrackpointManager"))
        TrackpointManager.resize(579, 684)
        self.centralwidget = QtGui.QWidget(TrackpointManager)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.tabWidget = QtGui.QTabWidget(self.centralwidget)
        self.tabWidget.setGeometry(QtCore.QRect(0, 0, 571, 611))
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.roiMap = QtGui.QWidget()
        self.roiMap.setObjectName(_fromUtf8("roiMap"))
        self.xy_refocus_ViewWidget = PlotWidget(self.roiMap)
        self.xy_refocus_ViewWidget.setGeometry(QtCore.QRect(10, 40, 541, 391))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(6)
        sizePolicy.setHeightForWidth(self.xy_refocus_ViewWidget.sizePolicy().hasHeightForWidth())
        self.xy_refocus_ViewWidget.setSizePolicy(sizePolicy)
        self.xy_refocus_ViewWidget.setObjectName(_fromUtf8("xy_refocus_ViewWidget"))
        self.get_confocal_image_Button = QtGui.QPushButton(self.roiMap)
        self.get_confocal_image_Button.setGeometry(QtCore.QRect(10, 10, 151, 23))
        self.get_confocal_image_Button.setObjectName(_fromUtf8("get_confocal_image_Button"))
        self.set_tp_Button = QtGui.QPushButton(self.roiMap)
        self.set_tp_Button.setGeometry(QtCore.QRect(10, 440, 121, 23))
        self.set_tp_Button.setObjectName(_fromUtf8("set_tp_Button"))
        self.label = QtGui.QLabel(self.roiMap)
        self.label.setGeometry(QtCore.QRect(50, 480, 121, 20))
        self.label.setObjectName(_fromUtf8("label"))
        self.tp_name_Input = QtGui.QLineEdit(self.roiMap)
        self.tp_name_Input.setGeometry(QtCore.QRect(160, 510, 113, 22))
        self.tp_name_Input.setObjectName(_fromUtf8("tp_name_Input"))
        self.manage_tp_comboBox = QtGui.QComboBox(self.roiMap)
        self.manage_tp_comboBox.setGeometry(QtCore.QRect(170, 480, 85, 23))
        self.manage_tp_comboBox.setObjectName(_fromUtf8("manage_tp_comboBox"))
        self.label_3 = QtGui.QLabel(self.roiMap)
        self.label_3.setGeometry(QtCore.QRect(90, 510, 58, 21))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.delete_tp_Button = QtGui.QPushButton(self.roiMap)
        self.delete_tp_Button.setGeometry(QtCore.QRect(320, 540, 95, 23))
        self.delete_tp_Button.setObjectName(_fromUtf8("delete_tp_Button"))
        self.line = QtGui.QFrame(self.roiMap)
        self.line.setGeometry(QtCore.QRect(10, 460, 541, 20))
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.manual_update_tp_Button = QtGui.QPushButton(self.roiMap)
        self.manual_update_tp_Button.setGeometry(QtCore.QRect(90, 540, 181, 23))
        self.manual_update_tp_Button.setObjectName(_fromUtf8("manual_update_tp_Button"))
        self.tabWidget.addTab(self.roiMap, _fromUtf8(""))
        self.sampleShift = QtGui.QWidget()
        self.sampleShift.setObjectName(_fromUtf8("sampleShift"))
        self.xy_refocus_ViewWidget_2 = PlotWidget(self.sampleShift)
        self.xy_refocus_ViewWidget_2.setGeometry(QtCore.QRect(10, 10, 431, 431))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(6)
        sizePolicy.setHeightForWidth(self.xy_refocus_ViewWidget_2.sizePolicy().hasHeightForWidth())
        self.xy_refocus_ViewWidget_2.setSizePolicy(sizePolicy)
        self.xy_refocus_ViewWidget_2.setObjectName(_fromUtf8("xy_refocus_ViewWidget_2"))
        self.listView = QtGui.QListView(self.sampleShift)
        self.listView.setGeometry(QtCore.QRect(450, 10, 111, 431))
        self.listView.setObjectName(_fromUtf8("listView"))
        self.tabWidget.addTab(self.sampleShift, _fromUtf8(""))
        self.tab = QtGui.QWidget()
        self.tab.setObjectName(_fromUtf8("tab"))
        self.tabWidget.addTab(self.tab, _fromUtf8(""))
        self.triangulation = QtGui.QWidget()
        self.triangulation.setObjectName(_fromUtf8("triangulation"))
        self.tabWidget.addTab(self.triangulation, _fromUtf8(""))
        self.tab_2 = QtGui.QWidget()
        self.tab_2.setObjectName(_fromUtf8("tab_2"))
        self.tabWidget.addTab(self.tab_2, _fromUtf8(""))
        self.horizontalLayoutWidget = QtGui.QWidget(self.centralwidget)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(10, 619, 561, 25))
        self.horizontalLayoutWidget.setObjectName(_fromUtf8("horizontalLayoutWidget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label_2 = QtGui.QLabel(self.horizontalLayoutWidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout.addWidget(self.label_2)
        self.active_tp_Input = QtGui.QComboBox(self.horizontalLayoutWidget)
        self.active_tp_Input.setEditable(False)
        self.active_tp_Input.setObjectName(_fromUtf8("active_tp_Input"))
        self.horizontalLayout.addWidget(self.active_tp_Input)
        self.goto_tp_Button = QtGui.QRadioButton(self.horizontalLayoutWidget)
        self.goto_tp_Button.setObjectName(_fromUtf8("goto_tp_Button"))
        self.horizontalLayout.addWidget(self.goto_tp_Button)
        self.update_tp_Button = QtGui.QRadioButton(self.horizontalLayoutWidget)
        self.update_tp_Button.setObjectName(_fromUtf8("update_tp_Button"))
        self.horizontalLayout.addWidget(self.update_tp_Button)
        self.update_method_Input = QtGui.QComboBox(self.horizontalLayoutWidget)
        self.update_method_Input.setObjectName(_fromUtf8("update_method_Input"))
        self.horizontalLayout.addWidget(self.update_method_Input)
        TrackpointManager.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(TrackpointManager)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 579, 20))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        TrackpointManager.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(TrackpointManager)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        TrackpointManager.setStatusBar(self.statusbar)

        self.retranslateUi(TrackpointManager)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(TrackpointManager)

    def retranslateUi(self, TrackpointManager):
        TrackpointManager.setWindowTitle(_translate("TrackpointManager", "qudi: Trackpoint Manager", None))
        self.get_confocal_image_Button.setText(_translate("TrackpointManager", "Get Confocal image", None))
        self.set_tp_Button.setText(_translate("TrackpointManager", "Set trackpoint", None))
        self.label.setText(_translate("TrackpointManager", "Manage trackpoint ", None))
        self.label_3.setText(_translate("TrackpointManager", "Name: ", None))
        self.delete_tp_Button.setText(_translate("TrackpointManager", "Delete", None))
        self.manual_update_tp_Button.setText(_translate("TrackpointManager", "Manual update position", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.roiMap), _translate("TrackpointManager", "ROI Map", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.sampleShift), _translate("TrackpointManager", "Sample shift", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("TrackpointManager", "Offset marker", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.triangulation), _translate("TrackpointManager", "Triangulation", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("TrackpointManager", "AutoFinder", None))
        self.label_2.setText(_translate("TrackpointManager", "For trackpoint", None))
        self.goto_tp_Button.setText(_translate("TrackpointManager", "Goto TP", None))
        self.update_tp_Button.setText(_translate("TrackpointManager", "Update using ", None))

from pyqtgraph import PlotWidget
