
import numpy as np
import os
import pyqtgraph as pg
import time

from core.connector import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic



class TTWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ttg2.ui')

        # Load it
        super(TTWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class TTGui(GUIBase):
    # declare connectors
    timetaggerlogic = Connector(interface='TimeTaggerLogic')
    savelogic = Connector(interface='SaveLogic')
    sigStopScan = QtCore.Signal()
    sig_update_tt_params = QtCore.Signal(str, str, int)
    sig_change_channel = QtCore.Signal(int)
    sig_load_params =QtCore.Signal()
    
    

    def on_deactivate(self):
        self._mw.close()
        return 0

    def on_activate(self):
        self._timetaggerlogic = self.timetaggerlogic()
        self._savelogic = self.savelogic()

        
        self._mw.bins_width_ttTextField.editingFinished.connect(self.update_tt_params)
        self._mw.number_of_bins_ttTextField.editingFinished.connect(self.update_tt_params)
        self.sig_update_tt_params.connect(self._timetaggerlogic.update_tt_params)

        self._mw.hist_channel_ComboBox.editingFinished.connect(self.change_hist_channel)
        self.sig_change_channel.connect(self._timetaggerlogic.change_hist_channel)
        
        self._timetaggerlogic.sigUpdateGuiParams.connect(self.update_gui_params)

        self._mw.refreshTextField.editingFinished.connect(self.refresh_time_changed)
        self._mw.tabsWidget.currentChanged.connect(self.updateParams)
        # self._mw.dumpSizeTextField
        # self._mw.saveDumpCheckBox
        # self._mw.dump_name_TextField.connect(self.)
        # self._mw.delay_TextField.editingFinished.connect(self.)
        self._mw.new_measurement_PushButton.clicked.connect(self.new_measurement)
        self._mw.freeze_PushButton.clicked.connect(self.freeze)
        self._mw.saveParams_PushButton.clicked.connect(self._timetaggerlogic.saveParams)
        self._mw.loadParams_PushButton.clicked.connect(self.loadParams)
        self.sig_load_params.connect(self._timetaggerlogic.loadParams)
        # self._mw.saveFig_PushButton.clicked.connect(self.)

        self.setup_plots()

    def new_measurement(self):
        self._timetaggerlogic.sigNewMeasurement.emit()
    def loadParams(self):
        self.sig_load_params.emit()

    def update_gui_params(self):
        curve = self._mw.tabsWidget.currentWidget().objectName()
        curve = curve.split('_')[0]
        self._mw.bins_width_ttTextField.setText(self._timetaggerlogic.tt_params[curve]['bins_width'])
        self._mw.number_of_bins_ttTextField.setText(self._timetaggerlogic.tt_params[curve]['number_of_bins'])
        self._timetaggerlogic.sigUpdate.emit()

    def update_tt_params(self):
        sender = self.sender()
        curve = self._mw.tabsWidget.currentWidget().objectName()
        curve = curve.split('_')[0]
        param = sender.objectName().split("_ttTextField")[0]
        value = int(sender.text()) if sender.text() is not '' else 0
        self.sig_update_tt_params.emit(curve, param, value)

    def refresh_time_changed(self):
        sender = self.sender()
        refresh_time = 1000 * float(sender.text()) # in sec
        self._timetaggerlogic.sigHistRefresh.emit(refresh_time)

    def change_hist_channel(self):
        ch = self.sender()
        self.sig_change_channel.emit(ch.currentIndex()+1)

    def setup_plots(self):
        self.font = QtGui.QFont()
        self.font.setPixelSize(20)

        self.p1 = self._mw.widget_counter.addPlot()
        self.p1 = self.plot_curve(self.p1, return_p=True)
        self.curve_counter = self.p1.plot()

        self.p2 = self._mw.widget_hist.addPlot()
        self.p2 = self.plot_curve(self.p2, return_p=True)
        self.curve_hist = self.p2.plot()

        self.p3 = self._mw.widget_corr.addPlot()
        self.curve_corr = self.plot_curve(self.p3)

        self.p41 = self._mw.widget_freeze.addPlot()
        self.p41 = self.plot_curve(self.p41, return_p=True)
        self.p41.addItem(self.lr41)
        self.curve_freeze_1 = self.p41.plot()

        self._mw.widget_freeze.nextRow()
        self.p42 = self._mw.widget_freeze.addPlot()
        self.p42 = self.plot_curve(self.p42, return_p=True)
        self.p42.addItem(self.lr42)
        self.curve_freeze_2 = self.p42.plot()

    def switch(self):
        self.freeze = not self.freeze

    def update_gui(self):
        # t = np.linspace(0, self.numBins*self.binWidth/1000, self.numBins)
        def plot_counter():
            self.curve_counter.setData(self._timetaggerlogic.time_counter, 
                                    self._timetaggerlogic.counter_tt.getData())

        def plot_histog():
            self.curve_hist.setData(self._timetaggerlogic.time_hist, 
                                    self._timetaggerlogic.hist_tt.getData())

        def plot_correlation():
            self.curve_corr.setData(self._timetaggerlogic.time_corr, 
                                    self._timetaggerlogic.corr_tt.getData())

        def plot_freeze():
            if self.freeze:
                self.curve_freeze_1.setData(self._timetaggerlogic.time_hist, 
                                    self._timetaggerlogic.hist_tt.getData())
            else:
                self.curve_freeze_2.setData(self._timetaggerlogic.time_hist, 
                                    self._timetaggerlogic.hist_tt.getData())

        graphs = [plot_counter, plot_histog, plot_correlation, plot_freeze]
        graphs[self.m_ui.tabsWidget.currentIndex()]()
        

