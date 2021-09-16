# -*- coding: utf-8 -*
from collections import OrderedDict
import datetime
import matplotlib.pyplot as plt
import numpy as np
import time
from time import sleep
from core.connector import Connector
from core.statusvariable import StatusVar
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from PyQt5.QtCore import QObject
from core.threadmanager import ThreadManager
from core.pi3_utils import delay, wavelength_to_freq
import numpy as np

class WlmLogger(GenericLogic):
    timetagger = Connector(interface='TT')
    wavemeter = Connector(interface='HighFinesseWavemeterClient')
    savelogic = Connector(interface='SaveLogic')

    queryInterval = ConfigOption('query_interval', 100)
    wavelength_buffer = 2000
    skip_rate = 3
    count_freq = 50
    intern_xmin = 500.00
    intern_xmax = 800.00
    zpl_bin_width = .00005
    current_wavelength = -1
    sig_update_gui = QtCore.Signal()
    sig_new_data_point = QtCore.Signal()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        pass
        # self.zpl_bin_width = .0001 # equivalent ~ 0.8 GHz
        # self.current_wavelength = -1
        # xx = np.arange(self.intern_xmin, self.intern_xmax, self.zpl_bin_width)
        # self.wlth_xs = xx
        # self.cts_ys = np.zeros(len(xx))
        # self.samples_num = np.zeros(len(xx))
        # self.plot_x = xx
        # self.plot_y = self.cts_ys
        # self.deviance_ys =  self.dy / self.samples_num
    def on_activate(self):
        self._wavemeter = self.wavemeter()
        self._timetagger = self.timetagger() 
        self._save_logic = self.savelogic()
        self.counter = self._timetagger.counter(binwidth = int((1 / self.count_freq) * 1e12), 
                                                n_values=1) #counts per second
        self.recalculate_histogram()
        # Initialie data matrix
        # delay timer for querying laser
        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.loop_body)#, QtCore.Qt.QueuedConnection)     
        self.queryTimer.start(self.queryInterval)
        

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
        return 


    @QtCore.Slot()
    def loop_body(self):
        qi = self.queryInterval
        self.queryTimer.start(qi)
        self.current_wavelength = self._wavemeter.get_current_wavelength()
        if self.current_wavelength > 0:
            self.cts = self.counter.getData()[-1]
            self.cts_ys[np.argmin(np.abs(self.current_wavelength - self.wlth_xs))] += self.cts
            self.samples_num[np.argmin(np.abs(self.current_wavelength - self.wlth_xs))] += 1
            
            self.plot_y = np.divide(self.cts_ys, self.samples_num, out = np.zeros_like(self.cts_ys), where=self.samples_num != 0)
            self.sig_update_gui.emit()

    def get_xy(self):
        if len(self.plot_y[self.plot_y > 0]) > 0:
            argmin, argmax = np.where(self.plot_y > 0)[0][0], np.where(self.plot_y > 0)[0][-1]
            if argmin != argmax:
                return self.plot_x[argmin:argmax], self.plot_y[argmin:argmax]
            else:
                return [self.plot_x[argmin]], [self.plot_y[argmin]]
        else:
            return self.plot_x[:10], self.plot_y[:10]
    def get_wavelengths(self):
        wlth = self._wavemeter.wavelengths[-self.wavelength_buffer:][::self.skip_rate]
        wlth = wlth[wlth > 0]
        time_wlm = np.linspace(0, len(wlth) * self.queryInterval,len(wlth))
        return wlth, time_wlm
    def recalculate_histogram(self, bins=None, xmin=None, xmax=None):
        if (bins is None) or (xmin is None) or (xmax is None):
            xx = np.arange(self.intern_xmin, self.intern_xmax, self.zpl_bin_width)
            self.wlth_xs = xx
            self.cts_ys = np.zeros(len(xx))
            self.samples_num = np.zeros(len(xx))
            self.plot_x = xx
            self.plot_y = self.cts_ys
        else:
            self.zpl_bin_width = bins
            self.intern_xmin = xmin
            self.intern_xmin = xmax
            xx = np.arange(xmin, xmax, bins)
            self.wlth_xs = xx
            self.cts_ys = np.zeros(len(xx))
            self.samples_num = np.zeros(len(xx))
            self.plot_x = xx
            self.plot_y = self.cts_ys
        