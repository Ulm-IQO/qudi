# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ConfocalWindowTemplate.ui'
#
# Created: Fri Apr 24 11:38:31 2015
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
        MainWindow.resize(1062, 768)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout_2 = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.xz_ViewWidget = PlotWidget(self.centralwidget)
        self.xz_ViewWidget.setObjectName(_fromUtf8("xz_ViewWidget"))
        self.gridLayout.addWidget(self.xz_ViewWidget, 1, 1, 1, 1)
        self.xy_ViewWidget = PlotWidget(self.centralwidget)
        self.xy_ViewWidget.setObjectName(_fromUtf8("xy_ViewWidget"))
        self.gridLayout.addWidget(self.xy_ViewWidget, 1, 0, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 2)
        self.gridLayout_3 = QtGui.QGridLayout()
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.horizontalLayout_6 = QtGui.QHBoxLayout()
        self.horizontalLayout_6.setObjectName(_fromUtf8("horizontalLayout_6"))
        self.radioButton = QtGui.QRadioButton(self.centralwidget)
        self.radioButton.setObjectName(_fromUtf8("radioButton"))
        self.horizontalLayout_6.addWidget(self.radioButton)
        self.radioButton_2 = QtGui.QRadioButton(self.centralwidget)
        self.radioButton_2.setObjectName(_fromUtf8("radioButton_2"))
        self.horizontalLayout_6.addWidget(self.radioButton_2)
        self.radioButton_3 = QtGui.QRadioButton(self.centralwidget)
        self.radioButton_3.setObjectName(_fromUtf8("radioButton_3"))
        self.horizontalLayout_6.addWidget(self.radioButton_3)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem)
        self.gridLayout_3.addLayout(self.horizontalLayout_6, 5, 0, 1, 1)
        self.horizontalLayout_7 = QtGui.QHBoxLayout()
        self.horizontalLayout_7.setObjectName(_fromUtf8("horizontalLayout_7"))
        spacerItem1 = QtGui.QSpacerItem(56, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem1)
        self.label_4 = QtGui.QLabel(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setMinimumSize(QtCore.QSize(50, 0))
        self.label_4.setMaximumSize(QtCore.QSize(125, 16777215))
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout_7.addWidget(self.label_4)
        self.line = QtGui.QFrame(self.centralwidget)
        self.line.setFrameShape(QtGui.QFrame.VLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.horizontalLayout_7.addWidget(self.line)
        spacerItem2 = QtGui.QSpacerItem(30, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem2)
        self.label_5 = QtGui.QLabel(self.centralwidget)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.horizontalLayout_7.addWidget(self.label_5)
        spacerItem3 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem3)
        self.gridLayout_3.addLayout(self.horizontalLayout_7, 0, 0, 1, 1)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label_2 = QtGui.QLabel(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_2.setFont(font)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_3.addWidget(self.label_2)
        spacerItem4 = QtGui.QSpacerItem(56, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem4)
        self.line_3 = QtGui.QFrame(self.centralwidget)
        self.line_3.setFrameShape(QtGui.QFrame.VLine)
        self.line_3.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_3.setObjectName(_fromUtf8("line_3"))
        self.horizontalLayout_3.addWidget(self.line_3)
        self.y_min_InputWidget = QtGui.QLineEdit(self.centralwidget)
        self.y_min_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.y_min_InputWidget.setObjectName(_fromUtf8("y_min_InputWidget"))
        self.horizontalLayout_3.addWidget(self.y_min_InputWidget)
        self.y_max_InputWidget = QtGui.QLineEdit(self.centralwidget)
        self.y_max_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.y_max_InputWidget.setObjectName(_fromUtf8("y_max_InputWidget"))
        self.horizontalLayout_3.addWidget(self.y_max_InputWidget)
        self.y_SliderWidget = QtGui.QSlider(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.y_SliderWidget.sizePolicy().hasHeightForWidth())
        self.y_SliderWidget.setSizePolicy(sizePolicy)
        self.y_SliderWidget.setMinimumSize(QtCore.QSize(150, 0))
        self.y_SliderWidget.setSizeIncrement(QtCore.QSize(0, 0))
        self.y_SliderWidget.setBaseSize(QtCore.QSize(0, 0))
        self.y_SliderWidget.setOrientation(QtCore.Qt.Horizontal)
        self.y_SliderWidget.setObjectName(_fromUtf8("y_SliderWidget"))
        self.horizontalLayout_3.addWidget(self.y_SliderWidget)
        self.y_current_InputWidget = QtGui.QLineEdit(self.centralwidget)
        self.y_current_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.y_current_InputWidget.setObjectName(_fromUtf8("y_current_InputWidget"))
        self.horizontalLayout_3.addWidget(self.y_current_InputWidget)
        self.gridLayout_3.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setScaledContents(False)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.xy_res_InputWidget = QtGui.QLineEdit(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.xy_res_InputWidget.sizePolicy().hasHeightForWidth())
        self.xy_res_InputWidget.setSizePolicy(sizePolicy)
        self.xy_res_InputWidget.setMinimumSize(QtCore.QSize(0, 0))
        self.xy_res_InputWidget.setMaximumSize(QtCore.QSize(50, 1111))
        self.xy_res_InputWidget.setObjectName(_fromUtf8("xy_res_InputWidget"))
        self.horizontalLayout.addWidget(self.xy_res_InputWidget)
        self.line_2 = QtGui.QFrame(self.centralwidget)
        self.line_2.setFrameShape(QtGui.QFrame.VLine)
        self.line_2.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_2.setObjectName(_fromUtf8("line_2"))
        self.horizontalLayout.addWidget(self.line_2)
        self.x_min_InputWidget = QtGui.QLineEdit(self.centralwidget)
        self.x_min_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.x_min_InputWidget.setObjectName(_fromUtf8("x_min_InputWidget"))
        self.horizontalLayout.addWidget(self.x_min_InputWidget)
        self.x_max_InputWidget = QtGui.QLineEdit(self.centralwidget)
        self.x_max_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.x_max_InputWidget.setObjectName(_fromUtf8("x_max_InputWidget"))
        self.horizontalLayout.addWidget(self.x_max_InputWidget)
        self.x_SliderWidget = QtGui.QSlider(self.centralwidget)
        self.x_SliderWidget.setMinimumSize(QtCore.QSize(150, 0))
        self.x_SliderWidget.setOrientation(QtCore.Qt.Horizontal)
        self.x_SliderWidget.setObjectName(_fromUtf8("x_SliderWidget"))
        self.horizontalLayout.addWidget(self.x_SliderWidget)
        self.x_current_InputWidget = QtGui.QLineEdit(self.centralwidget)
        self.x_current_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.x_current_InputWidget.setObjectName(_fromUtf8("x_current_InputWidget"))
        self.horizontalLayout.addWidget(self.x_current_InputWidget)
        self.gridLayout_3.addLayout(self.horizontalLayout, 1, 0, 1, 1)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_3 = QtGui.QLabel(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        self.label_3.setMinimumSize(QtCore.QSize(51, 0))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_3.setFont(font)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_2.addWidget(self.label_3)
        self.z_res_InputWidget = QtGui.QLineEdit(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.z_res_InputWidget.sizePolicy().hasHeightForWidth())
        self.z_res_InputWidget.setSizePolicy(sizePolicy)
        self.z_res_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.z_res_InputWidget.setObjectName(_fromUtf8("z_res_InputWidget"))
        self.horizontalLayout_2.addWidget(self.z_res_InputWidget)
        self.line_4 = QtGui.QFrame(self.centralwidget)
        self.line_4.setFrameShape(QtGui.QFrame.VLine)
        self.line_4.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_4.setObjectName(_fromUtf8("line_4"))
        self.horizontalLayout_2.addWidget(self.line_4)
        self.z_min_InputWidget = QtGui.QLineEdit(self.centralwidget)
        self.z_min_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.z_min_InputWidget.setObjectName(_fromUtf8("z_min_InputWidget"))
        self.horizontalLayout_2.addWidget(self.z_min_InputWidget)
        self.z_max_InputWidget = QtGui.QLineEdit(self.centralwidget)
        self.z_max_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.z_max_InputWidget.setObjectName(_fromUtf8("z_max_InputWidget"))
        self.horizontalLayout_2.addWidget(self.z_max_InputWidget)
        self.z_SliderWidget = QtGui.QSlider(self.centralwidget)
        self.z_SliderWidget.setMinimumSize(QtCore.QSize(150, 0))
        self.z_SliderWidget.setOrientation(QtCore.Qt.Horizontal)
        self.z_SliderWidget.setObjectName(_fromUtf8("z_SliderWidget"))
        self.horizontalLayout_2.addWidget(self.z_SliderWidget)
        self.z_current_InputWidget = QtGui.QLineEdit(self.centralwidget)
        self.z_current_InputWidget.setMaximumSize(QtCore.QSize(50, 16777215))
        self.z_current_InputWidget.setObjectName(_fromUtf8("z_current_InputWidget"))
        self.horizontalLayout_2.addWidget(self.z_current_InputWidget)
        self.gridLayout_3.addLayout(self.horizontalLayout_2, 3, 0, 1, 1)
        self.horizontalLayout_61 = QtGui.QHBoxLayout()
        self.horizontalLayout_61.setObjectName(_fromUtf8("horizontalLayout_61"))
        self.ready_StateWidget = QtGui.QRadioButton(self.centralwidget)
        self.ready_StateWidget.setObjectName(_fromUtf8("ready_StateWidget"))
        self.horizontalLayout_61.addWidget(self.ready_StateWidget)
        self.xy_scan_StateWidget = QtGui.QRadioButton(self.centralwidget)
        self.xy_scan_StateWidget.setObjectName(_fromUtf8("xy_scan_StateWidget"))
        self.horizontalLayout_61.addWidget(self.xy_scan_StateWidget)
        self.xz_scan_StateWidget = QtGui.QRadioButton(self.centralwidget)
        self.xz_scan_StateWidget.setObjectName(_fromUtf8("xz_scan_StateWidget"))
        self.horizontalLayout_61.addWidget(self.xz_scan_StateWidget)
        self.refocus_StateWidget = QtGui.QRadioButton(self.centralwidget)
        self.refocus_StateWidget.setObjectName(_fromUtf8("refocus_StateWidget"))
        self.horizontalLayout_61.addWidget(self.refocus_StateWidget)
        spacerItem5 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_61.addItem(spacerItem5)
        self.gridLayout_3.addLayout(self.horizontalLayout_61, 4, 0, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout_3, 1, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1062, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName(_fromUtf8("menuFile"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.actionSave_as = QtGui.QAction(MainWindow)
        self.actionSave_as.setObjectName(_fromUtf8("actionSave_as"))
        self.menuFile.addAction(self.actionSave_as)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))
        self.radioButton.setText(_translate("MainWindow", "Scan XY", None))
        self.radioButton_2.setText(_translate("MainWindow", "Scan Z", None))
        self.radioButton_3.setText(_translate("MainWindow", "Refocus", None))
        self.label_4.setText(_translate("MainWindow", "Resolution", None))
        self.label_5.setText(_translate("MainWindow", "Scan Range", None))
        self.label_2.setText(_translate("MainWindow", "Y-Axis :", None))
        self.y_min_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Y_Min</span></p></body></html>", None))
        self.y_max_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Y_Max</span></p></body></html>", None))
        self.y_current_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Y-position</span></p></body></html>", None))
        self.label.setText(_translate("MainWindow", "X-Axis :", None))
        self.xy_res_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">XY-Resolution</span></p></body></html>", None))
        self.x_min_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">X_Min</span></p></body></html>", None))
        self.x_max_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">X_Max</span></p></body></html>", None))
        self.x_current_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">X-position</span></p></body></html>", None))
        self.label_3.setText(_translate("MainWindow", "Z-Axis :", None))
        self.z_res_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Z-Resolution</span></p></body></html>", None))
        self.z_min_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Z_Min</span></p></body></html>", None))
        self.z_max_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Z_Max</span></p></body></html>", None))
        self.z_current_InputWidget.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:10pt; font-weight:600;\">Z-position</span></p></body></html>", None))
        self.ready_StateWidget.setText(_translate("MainWindow", "Ready", None))
        self.xy_scan_StateWidget.setText(_translate("MainWindow", "Scan XY", None))
        self.xz_scan_StateWidget.setText(_translate("MainWindow", "Scan XZ", None))
        self.refocus_StateWidget.setText(_translate("MainWindow", "Refocus", None))
        self.menuFile.setTitle(_translate("MainWindow", "&File", None))
        self.actionSave_as.setText(_translate("MainWindow", "Save as", None))

from pyqtgraph import PlotWidget
