# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'PoiManagerGuiUI.ui'
#
# Created: Mon Jun 15 21:04:44 2015
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
        PoiManager.resize(599, 747)
        PoiManager.setTabShape(QtGui.QTabWidget.Triangular)
        PoiManager.setDockOptions(QtGui.QMainWindow.AllowTabbedDocks|QtGui.QMainWindow.AnimatedDocks)
        self.centralwidget = QtGui.QWidget(PoiManager)
        self.centralwidget.setEnabled(True)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        PoiManager.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(PoiManager)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 599, 20))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuMenu = QtGui.QMenu(self.menubar)
        self.menuMenu.setObjectName(_fromUtf8("menuMenu"))
        self.menuView = QtGui.QMenu(self.menubar)
        self.menuView.setObjectName(_fromUtf8("menuView"))
        PoiManager.setMenuBar(self.menubar)
        self.toolBar = QtGui.QToolBar(PoiManager)
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.toolBar.setObjectName(_fromUtf8("toolBar"))
        PoiManager.addToolBar(QtCore.Qt.LeftToolBarArea, self.toolBar)
        self.poi_editor_dockWidget = QtGui.QDockWidget(PoiManager)
        self.poi_editor_dockWidget.setObjectName(_fromUtf8("poi_editor_dockWidget"))
        self.dockWidgetContents_3 = QtGui.QWidget()
        self.dockWidgetContents_3.setObjectName(_fromUtf8("dockWidgetContents_3"))
        self.verticalLayout_6 = QtGui.QVBoxLayout(self.dockWidgetContents_3)
        self.verticalLayout_6.setObjectName(_fromUtf8("verticalLayout_6"))
        self.set_poi_Button = QtGui.QPushButton(self.dockWidgetContents_3)
        self.set_poi_Button.setObjectName(_fromUtf8("set_poi_Button"))
        self.verticalLayout_6.addWidget(self.set_poi_Button)
        self.horizontalLayout_13 = QtGui.QHBoxLayout()
        self.horizontalLayout_13.setObjectName(_fromUtf8("horizontalLayout_13"))
        self.label = QtGui.QLabel(self.dockWidgetContents_3)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_13.addWidget(self.label)
        self.active_poi_Input = QtGui.QComboBox(self.dockWidgetContents_3)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.active_poi_Input.sizePolicy().hasHeightForWidth())
        self.active_poi_Input.setSizePolicy(sizePolicy)
        self.active_poi_Input.setEditable(False)
        self.active_poi_Input.setObjectName(_fromUtf8("active_poi_Input"))
        self.horizontalLayout_13.addWidget(self.active_poi_Input)
        self.verticalLayout_6.addLayout(self.horizontalLayout_13)
        self.horizontalLayout_14 = QtGui.QHBoxLayout()
        self.horizontalLayout_14.setObjectName(_fromUtf8("horizontalLayout_14"))
        self.label_3 = QtGui.QLabel(self.dockWidgetContents_3)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_14.addWidget(self.label_3)
        self.poi_name_Input = QtGui.QLineEdit(self.dockWidgetContents_3)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.poi_name_Input.sizePolicy().hasHeightForWidth())
        self.poi_name_Input.setSizePolicy(sizePolicy)
        self.poi_name_Input.setObjectName(_fromUtf8("poi_name_Input"))
        self.horizontalLayout_14.addWidget(self.poi_name_Input)
        self.verticalLayout_6.addLayout(self.horizontalLayout_14)
        self.delete_poi_Button = QtGui.QPushButton(self.dockWidgetContents_3)
        self.delete_poi_Button.setObjectName(_fromUtf8("delete_poi_Button"))
        self.verticalLayout_6.addWidget(self.delete_poi_Button)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_6.addItem(spacerItem)
        self.poi_editor_dockWidget.setWidget(self.dockWidgetContents_3)
        PoiManager.addDockWidget(QtCore.Qt.DockWidgetArea(8), self.poi_editor_dockWidget)
        self.poi_tracker_dockWidget = QtGui.QDockWidget(PoiManager)
        self.poi_tracker_dockWidget.setFloating(False)
        self.poi_tracker_dockWidget.setObjectName(_fromUtf8("poi_tracker_dockWidget"))
        self.dockWidgetContents_7 = QtGui.QWidget()
        self.dockWidgetContents_7.setObjectName(_fromUtf8("dockWidgetContents_7"))
        self.verticalLayout_5 = QtGui.QVBoxLayout(self.dockWidgetContents_7)
        self.verticalLayout_5.setObjectName(_fromUtf8("verticalLayout_5"))
        self.horizontalLayout_7 = QtGui.QHBoxLayout()
        self.horizontalLayout_7.setObjectName(_fromUtf8("horizontalLayout_7"))
        self.goto_poi_Button = QtGui.QPushButton(self.dockWidgetContents_7)
        self.goto_poi_Button.setObjectName(_fromUtf8("goto_poi_Button"))
        self.horizontalLayout_7.addWidget(self.goto_poi_Button)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem1)
        self.verticalLayout_5.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.update_poi_Button = QtGui.QPushButton(self.dockWidgetContents_7)
        self.update_poi_Button.setObjectName(_fromUtf8("update_poi_Button"))
        self.horizontalLayout_2.addWidget(self.update_poi_Button)
        self.label_4 = QtGui.QLabel(self.dockWidgetContents_7)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout_2.addWidget(self.label_4)
        self.verticalLayout_5.addLayout(self.horizontalLayout_2)
        self.update_method_Input = QtGui.QComboBox(self.dockWidgetContents_7)
        self.update_method_Input.setObjectName(_fromUtf8("update_method_Input"))
        self.update_method_Input.addItem(_fromUtf8(""))
        self.verticalLayout_5.addWidget(self.update_method_Input)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.goto_poi_after_update_checkBox = QtGui.QCheckBox(self.dockWidgetContents_7)
        self.goto_poi_after_update_checkBox.setObjectName(_fromUtf8("goto_poi_after_update_checkBox"))
        self.horizontalLayout_3.addWidget(self.goto_poi_after_update_checkBox)
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem2)
        self.verticalLayout_5.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_8 = QtGui.QHBoxLayout()
        self.horizontalLayout_8.setObjectName(_fromUtf8("horizontalLayout_8"))
        spacerItem3 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem3)
        self.delete_last_pos_Button = QtGui.QPushButton(self.dockWidgetContents_7)
        self.delete_last_pos_Button.setObjectName(_fromUtf8("delete_last_pos_Button"))
        self.horizontalLayout_8.addWidget(self.delete_last_pos_Button)
        self.verticalLayout_5.addLayout(self.horizontalLayout_8)
        self.horizontalLayout_11 = QtGui.QHBoxLayout()
        self.horizontalLayout_11.setObjectName(_fromUtf8("horizontalLayout_11"))
        self.periodic_update_Button = QtGui.QCheckBox(self.dockWidgetContents_7)
        self.periodic_update_Button.setObjectName(_fromUtf8("periodic_update_Button"))
        self.horizontalLayout_11.addWidget(self.periodic_update_Button)
        self.update_period_Input = QtGui.QSpinBox(self.dockWidgetContents_7)
        self.update_period_Input.setMinimum(5)
        self.update_period_Input.setMaximum(999)
        self.update_period_Input.setSingleStep(5)
        self.update_period_Input.setProperty("value", 15)
        self.update_period_Input.setObjectName(_fromUtf8("update_period_Input"))
        self.horizontalLayout_11.addWidget(self.update_period_Input)
        self.label_6 = QtGui.QLabel(self.dockWidgetContents_7)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.horizontalLayout_11.addWidget(self.label_6)
        self.verticalLayout_5.addLayout(self.horizontalLayout_11)
        self.time_till_next_update_Display = QtGui.QProgressBar(self.dockWidgetContents_7)
        self.time_till_next_update_Display.setMaximum(15)
        self.time_till_next_update_Display.setProperty("value", 15)
        self.time_till_next_update_Display.setObjectName(_fromUtf8("time_till_next_update_Display"))
        self.verticalLayout_5.addWidget(self.time_till_next_update_Display)
        self.horizontalLayout_12 = QtGui.QHBoxLayout()
        self.horizontalLayout_12.setObjectName(_fromUtf8("horizontalLayout_12"))
        self.manual_update_poi_Button = QtGui.QPushButton(self.dockWidgetContents_7)
        self.manual_update_poi_Button.setObjectName(_fromUtf8("manual_update_poi_Button"))
        self.horizontalLayout_12.addWidget(self.manual_update_poi_Button)
        self.verticalLayout_5.addLayout(self.horizontalLayout_12)
        spacerItem4 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_5.addItem(spacerItem4)
        self.poi_tracker_dockWidget.setWidget(self.dockWidgetContents_7)
        PoiManager.addDockWidget(QtCore.Qt.DockWidgetArea(8), self.poi_tracker_dockWidget)
        self.roi_map_dockWidget = QtGui.QDockWidget(PoiManager)
        self.roi_map_dockWidget.setObjectName(_fromUtf8("roi_map_dockWidget"))
        self.dockWidgetContents = QtGui.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.get_confocal_image_Button = QtGui.QPushButton(self.dockWidgetContents)
        self.get_confocal_image_Button.setObjectName(_fromUtf8("get_confocal_image_Button"))
        self.verticalLayout_2.addWidget(self.get_confocal_image_Button)
        self.horizontalLayout_10 = QtGui.QHBoxLayout()
        self.horizontalLayout_10.setObjectName(_fromUtf8("horizontalLayout_10"))
        self.roi_map_ViewWidget = PlotWidget(self.dockWidgetContents)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(6)
        sizePolicy.setHeightForWidth(self.roi_map_ViewWidget.sizePolicy().hasHeightForWidth())
        self.roi_map_ViewWidget.setSizePolicy(sizePolicy)
        self.roi_map_ViewWidget.setObjectName(_fromUtf8("roi_map_ViewWidget"))
        self.horizontalLayout_10.addWidget(self.roi_map_ViewWidget)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.roi_cb_max_InputWidget = QtGui.QSpinBox(self.dockWidgetContents)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.roi_cb_max_InputWidget.sizePolicy().hasHeightForWidth())
        self.roi_cb_max_InputWidget.setSizePolicy(sizePolicy)
        self.roi_cb_max_InputWidget.setMaximumSize(QtCore.QSize(80, 16777215))
        self.roi_cb_max_InputWidget.setMouseTracking(True)
        self.roi_cb_max_InputWidget.setAcceptDrops(True)
        self.roi_cb_max_InputWidget.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.roi_cb_max_InputWidget.setAccelerated(True)
        self.roi_cb_max_InputWidget.setMinimum(-100000000)
        self.roi_cb_max_InputWidget.setMaximum(100000000)
        self.roi_cb_max_InputWidget.setSingleStep(1000)
        self.roi_cb_max_InputWidget.setProperty("value", 100000)
        self.roi_cb_max_InputWidget.setObjectName(_fromUtf8("roi_cb_max_InputWidget"))
        self.verticalLayout.addWidget(self.roi_cb_max_InputWidget)
        self.horizontalLayout_9 = QtGui.QHBoxLayout()
        self.horizontalLayout_9.setObjectName(_fromUtf8("horizontalLayout_9"))
        self.roi_cb_high_centile_InputWidget = QtGui.QSpinBox(self.dockWidgetContents)
        self.roi_cb_high_centile_InputWidget.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.roi_cb_high_centile_InputWidget.setMinimum(50)
        self.roi_cb_high_centile_InputWidget.setMaximum(100)
        self.roi_cb_high_centile_InputWidget.setProperty("value", 100)
        self.roi_cb_high_centile_InputWidget.setObjectName(_fromUtf8("roi_cb_high_centile_InputWidget"))
        self.horizontalLayout_9.addWidget(self.roi_cb_high_centile_InputWidget)
        self.label_5 = QtGui.QLabel(self.dockWidgetContents)
        self.label_5.setMaximumSize(QtCore.QSize(30, 16777215))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.horizontalLayout_9.addWidget(self.label_5)
        self.verticalLayout.addLayout(self.horizontalLayout_9)
        self.roi_cb_ViewWidget = PlotWidget(self.dockWidgetContents)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.roi_cb_ViewWidget.sizePolicy().hasHeightForWidth())
        self.roi_cb_ViewWidget.setSizePolicy(sizePolicy)
        self.roi_cb_ViewWidget.setMaximumSize(QtCore.QSize(80, 16777215))
        self.roi_cb_ViewWidget.setObjectName(_fromUtf8("roi_cb_ViewWidget"))
        self.verticalLayout.addWidget(self.roi_cb_ViewWidget)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.roi_cb_low_centile_InputWidget = QtGui.QSpinBox(self.dockWidgetContents)
        self.roi_cb_low_centile_InputWidget.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.roi_cb_low_centile_InputWidget.setMaximum(50)
        self.roi_cb_low_centile_InputWidget.setProperty("value", 0)
        self.roi_cb_low_centile_InputWidget.setObjectName(_fromUtf8("roi_cb_low_centile_InputWidget"))
        self.horizontalLayout_4.addWidget(self.roi_cb_low_centile_InputWidget)
        self.label_2 = QtGui.QLabel(self.dockWidgetContents)
        self.label_2.setMaximumSize(QtCore.QSize(30, 16777215))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_4.addWidget(self.label_2)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.roi_cb_min_InputWidget = QtGui.QSpinBox(self.dockWidgetContents)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.roi_cb_min_InputWidget.sizePolicy().hasHeightForWidth())
        self.roi_cb_min_InputWidget.setSizePolicy(sizePolicy)
        self.roi_cb_min_InputWidget.setMaximumSize(QtCore.QSize(80, 16777215))
        self.roi_cb_min_InputWidget.setMouseTracking(True)
        self.roi_cb_min_InputWidget.setAcceptDrops(True)
        self.roi_cb_min_InputWidget.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.roi_cb_min_InputWidget.setAccelerated(True)
        self.roi_cb_min_InputWidget.setMinimum(-100000000)
        self.roi_cb_min_InputWidget.setMaximum(100000000)
        self.roi_cb_min_InputWidget.setSingleStep(1000)
        self.roi_cb_min_InputWidget.setProperty("value", 100)
        self.roi_cb_min_InputWidget.setObjectName(_fromUtf8("roi_cb_min_InputWidget"))
        self.verticalLayout.addWidget(self.roi_cb_min_InputWidget)
        self.roi_cb_centiles_RadioButton = QtGui.QRadioButton(self.dockWidgetContents)
        self.roi_cb_centiles_RadioButton.setChecked(True)
        self.roi_cb_centiles_RadioButton.setObjectName(_fromUtf8("roi_cb_centiles_RadioButton"))
        self.verticalLayout.addWidget(self.roi_cb_centiles_RadioButton)
        self.roi_cb_manual_RadioButton = QtGui.QRadioButton(self.dockWidgetContents)
        self.roi_cb_manual_RadioButton.setChecked(False)
        self.roi_cb_manual_RadioButton.setObjectName(_fromUtf8("roi_cb_manual_RadioButton"))
        self.verticalLayout.addWidget(self.roi_cb_manual_RadioButton)
        self.verticalLayout.setStretch(2, 1)
        self.horizontalLayout_10.addLayout(self.verticalLayout)
        self.verticalLayout_2.addLayout(self.horizontalLayout_10)
        self.roi_map_dockWidget.setWidget(self.dockWidgetContents)
        PoiManager.addDockWidget(QtCore.Qt.DockWidgetArea(4), self.roi_map_dockWidget)
        self.sample_shift_dockWidget = QtGui.QDockWidget(PoiManager)
        self.sample_shift_dockWidget.setObjectName(_fromUtf8("sample_shift_dockWidget"))
        self.dockWidgetContents_6 = QtGui.QWidget()
        self.dockWidgetContents_6.setObjectName(_fromUtf8("dockWidgetContents_6"))
        self.verticalLayout_4 = QtGui.QVBoxLayout(self.dockWidgetContents_6)
        self.verticalLayout_4.setObjectName(_fromUtf8("verticalLayout_4"))
        self.horizontalLayout_6 = QtGui.QHBoxLayout()
        self.horizontalLayout_6.setObjectName(_fromUtf8("horizontalLayout_6"))
        spacerItem5 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem5)
        self.radioButton_2 = QtGui.QRadioButton(self.dockWidgetContents_6)
        self.radioButton_2.setChecked(True)
        self.radioButton_2.setObjectName(_fromUtf8("radioButton_2"))
        self.horizontalLayout_6.addWidget(self.radioButton_2)
        self.radioButton = QtGui.QRadioButton(self.dockWidgetContents_6)
        self.radioButton.setObjectName(_fromUtf8("radioButton"))
        self.horizontalLayout_6.addWidget(self.radioButton)
        self.verticalLayout_4.addLayout(self.horizontalLayout_6)
        self.sample_shift_ViewWidget = PlotWidget(self.dockWidgetContents_6)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(6)
        sizePolicy.setHeightForWidth(self.sample_shift_ViewWidget.sizePolicy().hasHeightForWidth())
        self.sample_shift_ViewWidget.setSizePolicy(sizePolicy)
        self.sample_shift_ViewWidget.setObjectName(_fromUtf8("sample_shift_ViewWidget"))
        self.verticalLayout_4.addWidget(self.sample_shift_ViewWidget)
        self.sample_shift_dockWidget.setWidget(self.dockWidgetContents_6)
        PoiManager.addDockWidget(QtCore.Qt.DockWidgetArea(8), self.sample_shift_dockWidget)
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
        self.actionEdit_POIs = QtGui.QAction(PoiManager)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("document-properties"))
        self.actionEdit_POIs.setIcon(icon)
        self.actionEdit_POIs.setObjectName(_fromUtf8("actionEdit_POIs"))
        self.actionUpdate_POI_position = QtGui.QAction(PoiManager)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("edit-find"))
        self.actionUpdate_POI_position.setIcon(icon)
        self.actionUpdate_POI_position.setObjectName(_fromUtf8("actionUpdate_POI_position"))
        self.actionNew_POI = QtGui.QAction(PoiManager)
        self.actionNew_POI.setObjectName(_fromUtf8("actionNew_POI"))
        self.actionColorbar = QtGui.QAction(PoiManager)
        self.actionColorbar.setObjectName(_fromUtf8("actionColorbar"))
        self.menuMenu.addAction(self.actionNew_ROI)
        self.menuMenu.addAction(self.actionOpen_ROI)
        self.menuMenu.addAction(self.actionSave_ROI)
        self.menubar.addAction(self.menuMenu.menuAction())
        self.menubar.addAction(self.menuView.menuAction())
        self.toolBar.addAction(self.actionNew_ROI)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actionEdit_POIs)
        self.toolBar.addAction(self.actionUpdate_POI_position)

        self.retranslateUi(PoiManager)
        QtCore.QMetaObject.connectSlotsByName(PoiManager)

    def retranslateUi(self, PoiManager):
        PoiManager.setWindowTitle(_translate("PoiManager", "qudi: POI Manager", None))
        self.menuMenu.setTitle(_translate("PoiManager", "Menu", None))
        self.menuView.setTitle(_translate("PoiManager", "View", None))
        self.toolBar.setWindowTitle(_translate("PoiManager", "toolBar", None))
        self.poi_editor_dockWidget.setWindowTitle(_translate("PoiManager", "POI Editor", None))
        self.set_poi_Button.setToolTip(_translate("PoiManager", "Set current cursor position as a new trackpoint in the ROI map", None))
        self.set_poi_Button.setText(_translate("PoiManager", "Set new POI", None))
        self.label.setText(_translate("PoiManager", "Select:", None))
        self.label_3.setText(_translate("PoiManager", "Rename:", None))
        self.delete_poi_Button.setText(_translate("PoiManager", "Delete POI", None))
        self.poi_tracker_dockWidget.setWindowTitle(_translate("PoiManager", "POI Tracker", None))
        self.goto_poi_Button.setText(_translate("PoiManager", "Go to POI", None))
        self.update_poi_Button.setText(_translate("PoiManager", "Refind POI", None))
        self.label_4.setText(_translate("PoiManager", "using", None))
        self.update_method_Input.setItemText(0, _translate("PoiManager", "position optimisation", None))
        self.goto_poi_after_update_checkBox.setToolTip(_translate("PoiManager", "Move crosshair to updated POI position afterwards.", None))
        self.goto_poi_after_update_checkBox.setText(_translate("PoiManager", "Follow", None))
        self.delete_last_pos_Button.setText(_translate("PoiManager", "Delete last position", None))
        self.periodic_update_Button.setText(_translate("PoiManager", "Refind every", None))
        self.label_6.setText(_translate("PoiManager", "seconds", None))
        self.time_till_next_update_Display.setFormat(_translate("PoiManager", "%v s", None))
        self.manual_update_poi_Button.setToolTip(_translate("PoiManager", "This is for telling QuDi a totally new position for a known trackpoint.  For example, after manually shifting the sample to re-centre the ROI in the scan range.", None))
        self.manual_update_poi_Button.setText(_translate("PoiManager", "Manual update position", None))
        self.roi_map_dockWidget.setWindowTitle(_translate("PoiManager", "ROI Map", None))
        self.get_confocal_image_Button.setText(_translate("PoiManager", "Get Confocal image", None))
        self.label_5.setText(_translate("PoiManager", "%", None))
        self.label_2.setText(_translate("PoiManager", "%", None))
        self.roi_cb_centiles_RadioButton.setText(_translate("PoiManager", "Centiles", None))
        self.roi_cb_manual_RadioButton.setText(_translate("PoiManager", "Manual", None))
        self.sample_shift_dockWidget.setWindowTitle(_translate("PoiManager", "Sample shift", None))
        self.radioButton_2.setText(_translate("PoiManager", "Duration (seconds)", None))
        self.radioButton.setText(_translate("PoiManager", "Cliock time", None))
        self.actionNew_ROI.setText(_translate("PoiManager", "New ROI", None))
        self.actionNew_ROI.setToolTip(_translate("PoiManager", "Start a new ROI (such as after moving to a different part of the sample", None))
        self.actionSave_ROI.setText(_translate("PoiManager", "Save ROI", None))
        self.actionSave_ROI.setToolTip(_translate("PoiManager", "Save ROI for future reuse", None))
        self.actionOpen_ROI.setText(_translate("PoiManager", "Open ROI", None))
        self.actionOpen_ROI.setToolTip(_translate("PoiManager", "Load a saved ROI", None))
        self.actionEdit_POIs.setText(_translate("PoiManager", "Edit POIs", None))
        self.actionEdit_POIs.setToolTip(_translate("PoiManager", "Rename, select, delete POIs", None))
        self.actionUpdate_POI_position.setText(_translate("PoiManager", "Update POI position", None))
        self.actionNew_POI.setText(_translate("PoiManager", "New POI", None))
        self.actionColorbar.setText(_translate("PoiManager", "Colorbar", None))

from pyqtgraph import PlotWidget
