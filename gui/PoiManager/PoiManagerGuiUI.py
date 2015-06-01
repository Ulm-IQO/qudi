# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'PoiManagerGuiUI.ui'
#
# Created: Mon Jun  1 16:52:04 2015
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

class Ui_PoiManager(object):
    def setupUi(self, PoiManager):
        PoiManager.setObjectName(_fromUtf8("PoiManager"))
        PoiManager.resize(599, 738)
        self.centralwidget = QtGui.QWidget(PoiManager)
        self.centralwidget.setEnabled(True)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.tabWidget = QtGui.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.roiMap = QtGui.QWidget()
        self.roiMap.setObjectName(_fromUtf8("roiMap"))
        self.verticalLayout = QtGui.QVBoxLayout(self.roiMap)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.get_confocal_image_Button = QtGui.QPushButton(self.roiMap)
        self.get_confocal_image_Button.setObjectName(_fromUtf8("get_confocal_image_Button"))
        self.verticalLayout.addWidget(self.get_confocal_image_Button)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.roi_map_ViewWidget = PlotWidget(self.roiMap)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(6)
        sizePolicy.setHeightForWidth(self.roi_map_ViewWidget.sizePolicy().hasHeightForWidth())
        self.roi_map_ViewWidget.setSizePolicy(sizePolicy)
        self.roi_map_ViewWidget.setObjectName(_fromUtf8("roi_map_ViewWidget"))
        self.horizontalLayout_4.addWidget(self.roi_map_ViewWidget)
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.roi_cb_max_InputWidget = QtGui.QSpinBox(self.roiMap)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.roi_cb_max_InputWidget.sizePolicy().hasHeightForWidth())
        self.roi_cb_max_InputWidget.setSizePolicy(sizePolicy)
        self.roi_cb_max_InputWidget.setMaximumSize(QtCore.QSize(70, 16777215))
        self.roi_cb_max_InputWidget.setMouseTracking(True)
        self.roi_cb_max_InputWidget.setAcceptDrops(True)
        self.roi_cb_max_InputWidget.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.roi_cb_max_InputWidget.setAccelerated(True)
        self.roi_cb_max_InputWidget.setMinimum(-100000000)
        self.roi_cb_max_InputWidget.setMaximum(100000000)
        self.roi_cb_max_InputWidget.setSingleStep(1000)
        self.roi_cb_max_InputWidget.setProperty("value", 100000)
        self.roi_cb_max_InputWidget.setObjectName(_fromUtf8("roi_cb_max_InputWidget"))
        self.gridLayout.addWidget(self.roi_cb_max_InputWidget, 0, 0, 1, 1)
        self.roi_cb_min_InputWidget = QtGui.QSpinBox(self.roiMap)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.roi_cb_min_InputWidget.sizePolicy().hasHeightForWidth())
        self.roi_cb_min_InputWidget.setSizePolicy(sizePolicy)
        self.roi_cb_min_InputWidget.setMaximumSize(QtCore.QSize(70, 16777215))
        self.roi_cb_min_InputWidget.setMouseTracking(True)
        self.roi_cb_min_InputWidget.setAcceptDrops(True)
        self.roi_cb_min_InputWidget.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.roi_cb_min_InputWidget.setAccelerated(True)
        self.roi_cb_min_InputWidget.setMinimum(-100000000)
        self.roi_cb_min_InputWidget.setMaximum(100000000)
        self.roi_cb_min_InputWidget.setSingleStep(1000)
        self.roi_cb_min_InputWidget.setProperty("value", 100)
        self.roi_cb_min_InputWidget.setObjectName(_fromUtf8("roi_cb_min_InputWidget"))
        self.gridLayout.addWidget(self.roi_cb_min_InputWidget, 2, 0, 1, 1)
        self.roi_cb_ViewWidget = PlotWidget(self.roiMap)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.roi_cb_ViewWidget.sizePolicy().hasHeightForWidth())
        self.roi_cb_ViewWidget.setSizePolicy(sizePolicy)
        self.roi_cb_ViewWidget.setMaximumSize(QtCore.QSize(70, 16777215))
        self.roi_cb_ViewWidget.setObjectName(_fromUtf8("roi_cb_ViewWidget"))
        self.gridLayout.addWidget(self.roi_cb_ViewWidget, 1, 0, 1, 1)
        self.roi_cb_manual_RadioButton = QtGui.QRadioButton(self.roiMap)
        self.roi_cb_manual_RadioButton.setChecked(False)
        self.roi_cb_manual_RadioButton.setObjectName(_fromUtf8("roi_cb_manual_RadioButton"))
        self.gridLayout.addWidget(self.roi_cb_manual_RadioButton, 3, 0, 1, 1)
        self.roi_cb_5_95_RadioButton = QtGui.QRadioButton(self.roiMap)
        self.roi_cb_5_95_RadioButton.setChecked(False)
        self.roi_cb_5_95_RadioButton.setObjectName(_fromUtf8("roi_cb_5_95_RadioButton"))
        self.gridLayout.addWidget(self.roi_cb_5_95_RadioButton, 5, 0, 1, 1)
        self.roi_cb_auto_RadioButton = QtGui.QRadioButton(self.roiMap)
        self.roi_cb_auto_RadioButton.setChecked(True)
        self.roi_cb_auto_RadioButton.setObjectName(_fromUtf8("roi_cb_auto_RadioButton"))
        self.gridLayout.addWidget(self.roi_cb_auto_RadioButton, 6, 0, 1, 1)
        self.horizontalLayout_4.addLayout(self.gridLayout)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.tabWidget.addTab(self.roiMap, _fromUtf8(""))
        self.sampleShift = QtGui.QWidget()
        self.sampleShift.setObjectName(_fromUtf8("sampleShift"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.sampleShift)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout_6 = QtGui.QHBoxLayout()
        self.horizontalLayout_6.setObjectName(_fromUtf8("horizontalLayout_6"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem)
        self.radioButton_2 = QtGui.QRadioButton(self.sampleShift)
        self.radioButton_2.setChecked(True)
        self.radioButton_2.setObjectName(_fromUtf8("radioButton_2"))
        self.horizontalLayout_6.addWidget(self.radioButton_2)
        self.radioButton = QtGui.QRadioButton(self.sampleShift)
        self.radioButton.setObjectName(_fromUtf8("radioButton"))
        self.horizontalLayout_6.addWidget(self.radioButton)
        self.verticalLayout_2.addLayout(self.horizontalLayout_6)
        self.sample_shift_ViewWidget = PlotWidget(self.sampleShift)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(6)
        sizePolicy.setHeightForWidth(self.sample_shift_ViewWidget.sizePolicy().hasHeightForWidth())
        self.sample_shift_ViewWidget.setSizePolicy(sizePolicy)
        self.sample_shift_ViewWidget.setObjectName(_fromUtf8("sample_shift_ViewWidget"))
        self.verticalLayout_2.addWidget(self.sample_shift_ViewWidget)
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
        self.verticalLayout_3.addWidget(self.tabWidget)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.set_poi_Button = QtGui.QPushButton(self.centralwidget)
        self.set_poi_Button.setObjectName(_fromUtf8("set_poi_Button"))
        self.horizontalLayout_3.addWidget(self.set_poi_Button)
        self.label = QtGui.QLabel(self.centralwidget)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_3.addWidget(self.label)
        self.active_poi_Input = QtGui.QComboBox(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.active_poi_Input.sizePolicy().hasHeightForWidth())
        self.active_poi_Input.setSizePolicy(sizePolicy)
        self.active_poi_Input.setEditable(False)
        self.active_poi_Input.setObjectName(_fromUtf8("active_poi_Input"))
        self.horizontalLayout_3.addWidget(self.active_poi_Input)
        self.label_4 = QtGui.QLabel(self.centralwidget)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout_3.addWidget(self.label_4)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.verticalLayout_3.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_7 = QtGui.QHBoxLayout()
        self.horizontalLayout_7.setObjectName(_fromUtf8("horizontalLayout_7"))
        self.label_3 = QtGui.QLabel(self.centralwidget)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_7.addWidget(self.label_3)
        self.poi_name_Input = QtGui.QLineEdit(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.poi_name_Input.sizePolicy().hasHeightForWidth())
        self.poi_name_Input.setSizePolicy(sizePolicy)
        self.poi_name_Input.setObjectName(_fromUtf8("poi_name_Input"))
        self.horizontalLayout_7.addWidget(self.poi_name_Input)
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem2)
        self.delete_poi_Button = QtGui.QPushButton(self.centralwidget)
        self.delete_poi_Button.setObjectName(_fromUtf8("delete_poi_Button"))
        self.horizontalLayout_7.addWidget(self.delete_poi_Button)
        self.verticalLayout_3.addLayout(self.horizontalLayout_7)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.goto_poi_Button = QtGui.QPushButton(self.centralwidget)
        self.goto_poi_Button.setObjectName(_fromUtf8("goto_poi_Button"))
        self.horizontalLayout.addWidget(self.goto_poi_Button)
        self.update_poi_Button = QtGui.QPushButton(self.centralwidget)
        self.update_poi_Button.setObjectName(_fromUtf8("update_poi_Button"))
        self.horizontalLayout.addWidget(self.update_poi_Button)
        self.update_method_Input = QtGui.QComboBox(self.centralwidget)
        self.update_method_Input.setObjectName(_fromUtf8("update_method_Input"))
        self.horizontalLayout.addWidget(self.update_method_Input)
        self.checkBox = QtGui.QCheckBox(self.centralwidget)
        self.checkBox.setObjectName(_fromUtf8("checkBox"))
        self.horizontalLayout.addWidget(self.checkBox)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.periodic_update_Button = QtGui.QCheckBox(self.centralwidget)
        self.periodic_update_Button.setObjectName(_fromUtf8("periodic_update_Button"))
        self.horizontalLayout_2.addWidget(self.periodic_update_Button)
        self.update_period_Input = QtGui.QSpinBox(self.centralwidget)
        self.update_period_Input.setMinimum(5)
        self.update_period_Input.setMaximum(999)
        self.update_period_Input.setSingleStep(5)
        self.update_period_Input.setProperty("value", 15)
        self.update_period_Input.setObjectName(_fromUtf8("update_period_Input"))
        self.horizontalLayout_2.addWidget(self.update_period_Input)
        self.label_6 = QtGui.QLabel(self.centralwidget)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.horizontalLayout_2.addWidget(self.label_6)
        self.time_till_next_update_Display = QtGui.QLCDNumber(self.centralwidget)
        self.time_till_next_update_Display.setSmallDecimalPoint(False)
        self.time_till_next_update_Display.setNumDigits(3)
        self.time_till_next_update_Display.setObjectName(_fromUtf8("time_till_next_update_Display"))
        self.horizontalLayout_2.addWidget(self.time_till_next_update_Display)
        spacerItem3 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem3)
        self.verticalLayout_3.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        self.manual_update_poi_Button = QtGui.QPushButton(self.centralwidget)
        self.manual_update_poi_Button.setObjectName(_fromUtf8("manual_update_poi_Button"))
        self.horizontalLayout_5.addWidget(self.manual_update_poi_Button)
        self.delete_last_pos_Button = QtGui.QPushButton(self.centralwidget)
        self.delete_last_pos_Button.setObjectName(_fromUtf8("delete_last_pos_Button"))
        self.horizontalLayout_5.addWidget(self.delete_last_pos_Button)
        self.verticalLayout_3.addLayout(self.horizontalLayout_5)
        PoiManager.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(PoiManager)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        PoiManager.setStatusBar(self.statusbar)
        self.menubar = QtGui.QMenuBar(PoiManager)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 599, 20))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuMenu = QtGui.QMenu(self.menubar)
        self.menuMenu.setObjectName(_fromUtf8("menuMenu"))
        PoiManager.setMenuBar(self.menubar)
        self.actionNew_ROI = QtGui.QAction(PoiManager)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("document-new"))
        self.actionNew_ROI.setIcon(icon)
        self.actionNew_ROI.setObjectName(_fromUtf8("actionNew_ROI"))
        self.actionSave_ROI = QtGui.QAction(PoiManager)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("document-save"))
        self.actionSave_ROI.setIcon(icon)
        self.actionSave_ROI.setObjectName(_fromUtf8("actionSave_ROI"))
        self.actionOpen_ROI = QtGui.QAction(PoiManager)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("document-open"))
        self.actionOpen_ROI.setIcon(icon)
        self.actionOpen_ROI.setObjectName(_fromUtf8("actionOpen_ROI"))
        self.menuMenu.addAction(self.actionNew_ROI)
        self.menuMenu.addAction(self.actionOpen_ROI)
        self.menuMenu.addAction(self.actionSave_ROI)
        self.menubar.addAction(self.menuMenu.menuAction())

        self.retranslateUi(PoiManager)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(PoiManager)

    def retranslateUi(self, PoiManager):
        PoiManager.setWindowTitle(_translate("PoiManager", "qudi: POI Manager", None))
        self.get_confocal_image_Button.setText(_translate("PoiManager", "Get Confocal image", None))
        self.roi_cb_manual_RadioButton.setText(_translate("PoiManager", "Manual", None))
        self.roi_cb_5_95_RadioButton.setText(_translate("PoiManager", "5-95%", None))
        self.roi_cb_auto_RadioButton.setText(_translate("PoiManager", "Min/Max", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.roiMap), _translate("PoiManager", "ROI Map", None))
        self.radioButton_2.setText(_translate("PoiManager", "Duration (seconds)", None))
        self.radioButton.setText(_translate("PoiManager", "Cliock time", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.sampleShift), _translate("PoiManager", "Sample shift", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("PoiManager", "Offset marker", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.triangulation), _translate("PoiManager", "Triangulation", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("PoiManager", "AutoFinder", None))
        self.set_poi_Button.setToolTip(_translate("PoiManager", "Set current cursor position as a new trackpoint in the ROI map", None))
        self.set_poi_Button.setText(_translate("PoiManager", "Set new POI", None))
        self.label.setText(_translate("PoiManager", "or use", None))
        self.label_4.setText(_translate("PoiManager", "as active POI", None))
        self.label_3.setText(_translate("PoiManager", "Rename:", None))
        self.delete_poi_Button.setText(_translate("PoiManager", "Delete POI", None))
        self.goto_poi_Button.setText(_translate("PoiManager", "Go to POI", None))
        self.update_poi_Button.setText(_translate("PoiManager", "Update using ", None))
        self.checkBox.setToolTip(_translate("PoiManager", "Move crosshair to updated POI position afterwards.", None))
        self.checkBox.setText(_translate("PoiManager", "Track", None))
        self.periodic_update_Button.setText(_translate("PoiManager", "Periodic update every:", None))
        self.label_6.setText(_translate("PoiManager", "seconds", None))
        self.manual_update_poi_Button.setToolTip(_translate("PoiManager", "This is for telling QuDi a totally new position for a known trackpoint.  For example, after manually shifting the sample to re-centre the ROI in the scan range.", None))
        self.manual_update_poi_Button.setText(_translate("PoiManager", "Manual update position", None))
        self.delete_last_pos_Button.setText(_translate("PoiManager", "Delete last position", None))
        self.menuMenu.setTitle(_translate("PoiManager", "Menu", None))
        self.actionNew_ROI.setText(_translate("PoiManager", "New ROI", None))
        self.actionNew_ROI.setToolTip(_translate("PoiManager", "Start a new ROI (such as after moving to a different part of the sample", None))
        self.actionSave_ROI.setText(_translate("PoiManager", "Save ROI", None))
        self.actionSave_ROI.setToolTip(_translate("PoiManager", "Save ROI for future reuse", None))
        self.actionOpen_ROI.setText(_translate("PoiManager", "Open ROI", None))
        self.actionOpen_ROI.setToolTip(_translate("PoiManager", "Load a saved ROI", None))

from pyqtgraph import PlotWidget
