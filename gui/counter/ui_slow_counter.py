# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_slow_counter.ui'
#
# Created: Tue Jul  7 11:25:00 2015
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
        MainWindow.resize(800, 600)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 20))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuView = QtGui.QMenu(self.menubar)
        self.menuView.setObjectName(_fromUtf8("menuView"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.counter_trace_DockWidget = QtGui.QDockWidget(MainWindow)
        self.counter_trace_DockWidget.setObjectName(_fromUtf8("counter_trace_DockWidget"))
        self.dockWidgetContents = QtGui.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout = QtGui.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.count_value_Label = QtGui.QLabel(self.dockWidgetContents)
        font = QtGui.QFont()
        font.setPointSize(60)
        self.count_value_Label.setFont(font)
        self.count_value_Label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.count_value_Label.setObjectName(_fromUtf8("count_value_Label"))
        self.verticalLayout.addWidget(self.count_value_Label)
        self.counter_trace_PlotWidget = PlotWidget(self.dockWidgetContents)
        self.counter_trace_PlotWidget.setObjectName(_fromUtf8("counter_trace_PlotWidget"))
        self.verticalLayout.addWidget(self.counter_trace_PlotWidget)
        self.counter_trace_DockWidget.setWidget(self.dockWidgetContents)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(4), self.counter_trace_DockWidget)
        self.slow_counter_control_DockWidget = QtGui.QDockWidget(MainWindow)
        self.slow_counter_control_DockWidget.setObjectName(_fromUtf8("slow_counter_control_DockWidget"))
        self.dockWidgetContents_2 = QtGui.QWidget()
        self.dockWidgetContents_2.setObjectName(_fromUtf8("dockWidgetContents_2"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.dockWidgetContents_2)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(self.dockWidgetContents_2)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.count_length_SpinBox = QtGui.QSpinBox(self.dockWidgetContents_2)
        self.count_length_SpinBox.setMinimum(1)
        self.count_length_SpinBox.setMaximum(1000000)
        self.count_length_SpinBox.setSingleStep(10)
        self.count_length_SpinBox.setProperty("value", 300)
        self.count_length_SpinBox.setObjectName(_fromUtf8("count_length_SpinBox"))
        self.horizontalLayout.addWidget(self.count_length_SpinBox)
        self.label_2 = QtGui.QLabel(self.dockWidgetContents_2)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout.addWidget(self.label_2)
        self.count_freq_SpinBox = QtGui.QSpinBox(self.dockWidgetContents_2)
        self.count_freq_SpinBox.setMinimum(1)
        self.count_freq_SpinBox.setMaximum(1000000)
        self.count_freq_SpinBox.setSingleStep(10)
        self.count_freq_SpinBox.setProperty("value", 50)
        self.count_freq_SpinBox.setObjectName(_fromUtf8("count_freq_SpinBox"))
        self.horizontalLayout.addWidget(self.count_freq_SpinBox)
        self.label_3 = QtGui.QLabel(self.dockWidgetContents_2)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout.addWidget(self.label_3)
        self.oversampling_SpinBox = QtGui.QSpinBox(self.dockWidgetContents_2)
        self.oversampling_SpinBox.setMinimum(1)
        self.oversampling_SpinBox.setMaximum(10000)
        self.oversampling_SpinBox.setProperty("value", 1)
        self.oversampling_SpinBox.setObjectName(_fromUtf8("oversampling_SpinBox"))
        self.horizontalLayout.addWidget(self.oversampling_SpinBox)
        self.slow_counter_control_DockWidget.setWidget(self.dockWidgetContents_2)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(8), self.slow_counter_control_DockWidget)
        self.toolBar = QtGui.QToolBar(MainWindow)
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.toolBar.setObjectName(_fromUtf8("toolBar"))
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.start_counter_Action = QtGui.QAction(MainWindow)
        self.start_counter_Action.setCheckable(True)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("start_counter"))
        self.start_counter_Action.setIcon(icon)
        self.start_counter_Action.setObjectName(_fromUtf8("start_counter_Action"))
        self.record_counts_Action = QtGui.QAction(MainWindow)
        self.record_counts_Action.setCheckable(True)
        icon = QtGui.QIcon.fromTheme(_fromUtf8("record_counter"))
        self.record_counts_Action.setIcon(icon)
        self.record_counts_Action.setObjectName(_fromUtf8("record_counts_Action"))
        self.slow_counter_view_Action = QtGui.QAction(MainWindow)
        self.slow_counter_view_Action.setCheckable(True)
        self.slow_counter_view_Action.setObjectName(_fromUtf8("slow_counter_view_Action"))
        self.slow_counter_control_view_Action = QtGui.QAction(MainWindow)
        self.slow_counter_control_view_Action.setCheckable(True)
        self.slow_counter_control_view_Action.setObjectName(_fromUtf8("slow_counter_control_view_Action"))
        self.menuView.addAction(self.slow_counter_view_Action)
        self.menuView.addAction(self.slow_counter_control_view_Action)
        self.menubar.addAction(self.menuView.menuAction())
        self.toolBar.addAction(self.start_counter_Action)
        self.toolBar.addAction(self.record_counts_Action)

        self.retranslateUi(MainWindow)
        QtCore.QObject.connect(self.slow_counter_view_Action, QtCore.SIGNAL(_fromUtf8("triggered(bool)")), self.counter_trace_DockWidget.setVisible)
        QtCore.QObject.connect(self.counter_trace_DockWidget, QtCore.SIGNAL(_fromUtf8("visibilityChanged(bool)")), self.slow_counter_view_Action.setChecked)
        QtCore.QObject.connect(self.slow_counter_control_view_Action, QtCore.SIGNAL(_fromUtf8("triggered(bool)")), self.slow_counter_control_DockWidget.setVisible)
        QtCore.QObject.connect(self.slow_counter_control_DockWidget, QtCore.SIGNAL(_fromUtf8("visibilityChanged(bool)")), self.slow_counter_control_view_Action.setChecked)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Slow Counter", None))
        self.menuView.setTitle(_translate("MainWindow", "View", None))
        self.counter_trace_DockWidget.setWindowTitle(_translate("MainWindow", "Slow counter", None))
        self.count_value_Label.setText(_translate("MainWindow", "TextLabel", None))
        self.slow_counter_control_DockWidget.setWindowTitle(_translate("MainWindow", "Slow counter control", None))
        self.label.setText(_translate("MainWindow", "Count length (#):", None))
        self.label_2.setText(_translate("MainWindow", "Count frequency (Hz):", None))
        self.label_3.setToolTip(_translate("MainWindow", "If bigger than 1, the number of samples is averaged over the given number and then displayed. \n"
"Use for extremely fast counting, since all the raw data is saved. \n"
"Timestamps in oversampling interval are all equal to the averaging time.", None))
        self.label_3.setText(_translate("MainWindow", "Oversampling (#):", None))
        self.oversampling_SpinBox.setToolTip(_translate("MainWindow", "If bigger than 1, the number of samples is averaged over the given number and then displayed. \n"
"Use for extremely fast counting, since all the raw data is saved. \n"
"Timestamps in oversampling interval are all equal to the averaging time.", None))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar", None))
        self.start_counter_Action.setText(_translate("MainWindow", "Start counter", None))
        self.start_counter_Action.setToolTip(_translate("MainWindow", "Start the counter", None))
        self.record_counts_Action.setText(_translate("MainWindow", "Record counts", None))
        self.record_counts_Action.setToolTip(_translate("MainWindow", "Save count trace to file", None))
        self.slow_counter_view_Action.setText(_translate("MainWindow", "Slow counter", None))
        self.slow_counter_view_Action.setToolTip(_translate("MainWindow", "Show the Slow counter", None))
        self.slow_counter_control_view_Action.setText(_translate("MainWindow", "Slow counter control", None))
        self.slow_counter_control_view_Action.setToolTip(_translate("MainWindow", "Show Slow counter control", None))

from pyqtgraph import PlotWidget
