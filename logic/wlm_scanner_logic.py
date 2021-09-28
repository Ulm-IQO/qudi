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

class WlmScannerLogic(GenericLogic):
    """
    Scanning with the HighFinesse Wlm
    """
    # declare connectors
    timetagger = Connector(interface='TT')
    wavemeter = Connector(interface='HighFinesseWavemeterClient')
    savelogic = Connector(interface='SaveLogic')
    
    queryInterval = ConfigOption('query_interval', 100)
    n_scan_bins = 500
    n_scan_lines = 10
    count_freq = 50
    sweep_speed = 10
    amplitude = 0.005
    center_wl = None

    sig_update_gui = QtCore.Signal()
    sig_update_plots = QtCore.Signal()
    sig_set_sweep_params = QtCore.Signal(float, float, int)

    def __init__(self, **kwargs):
        """ Create CwaveScannerLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)
        self.fit_x = []
        self.fit_y = []
        self.plot_x, self.plot_y = np.zeros(10),np.zeros(10)
        
    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._wavemeter = self.wavemeter()
        self._timetagger = self.timetagger() 
        self._save_logic = self.savelogic()

        self.sig_update_plots.connect(self.update_plots)
        self.sig_set_sweep_params.connect(self.set_sweep_params)

        # self.counter = self._timetagger.counter(binwidth = int((1 / self.count_freq) * 1e12), n_values=1) #counts per second
        self.bins_width_scan = int(1e12 * 60 / (self.sweep_speed * self.n_scan_bins))
        self.time_diff = self._timetagger.time_differences(click_channel=2, 
        start_channel=8, 
        next_channel=-8, 
        binwidth=self.bins_width_scan,
        n_bins = self.n_scan_bins,
        n_histograms = self.n_scan_lines)
        self.time_diff.setMaxCounts(1)
        self.time_diff.stop()

        wlm_res = self._wavemeter.sig_send_request.emit("start_acqusition", "")#self._wavemeter.start_acqusition()
        self.wavelength = self._wavemeter.get_current_wavelength()
        if wlm_res != 0 and self.wavelength <= 0:
            self.wavelength = self._cwavelaser.wavelength if self._cwavelaser.wavelength is not None else 0 
        self.cwl = self._wavemeter.get_current_wavelength()
        self.wlm_regmode = True if self._wavemeter.get_regulation_mode() == 'on' else False

        self._initialize_plots()
        # Initialie data matrix
        # delay timer for querying laser
        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.loop_body)#, QtCore.Qt.QueuedConnection)     
        self.queryTimer.start(self.queryInterval)
        self.sig_update_gui.emit()


        return 
    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
        return 
    # @thread_safety
    def save_data(self):
        print("here we save")

    @QtCore.Slot()
    def loop_body(self):
        qi = self.queryInterval
        self.sig_update_plots.emit()
        self.queryTimer.start(qi)
        if self.time_diff.ready():
            print("SAVE PLOT!")
            self.time_diff.clear()
        self.sig_update_gui.emit()

    def _initialize_plots(self):
        """ Initializing the matrix plot. """
        self.plot_x, self.plot_y = np.zeros(10),np.zeros(10)
        self.scan_full_matrix = np.zeros(self.n_scan_bins)
        self.scan_matrix = np.zeros((2,2))
        wlm_len = 60000 # 60 sec
        self.plot_x_wlm = np.linspace(0,int(wlm_len/1000) , int(wlm_len/self.queryInterval))
        self.wavelength = self._wavemeter.get_current_wavelength()
        # print("Init matrix ", self.wavelength)
        if self.wavelength <= 0:
            self.wavelength = self._cwavelaser.get_wavelength()
        if self.wavelength == None:
            self.wavelength = 0
        self.plot_y_wlm = np.ones(int(wlm_len/self.queryInterval)) * self.wavelength

    @QtCore.Slot()
    def start_sweep(self):
        self.cwl = self._wavemeter.get_current_wavelength()#if self.center_wl is None else self.center_wl 
        # self._wavemeter.set_reference_course(f"{center_wl} + {self.amplitude} * triangle(t/{self.sweep_speed})")
        self._wavemeter.sig_send_request.emit("set_reference_course", f"{self.cwl} + {self.amplitude} * triangle(t/{self.sweep_speed})")
        self._wavemeter.sig_send_request.emit("set_regulation_mode", "on")
        #set_timer
        self.time_diff = self._timetagger.time_differences( 
        click_channel=2, 
        start_channel=8, 
        next_channel=-8, 
        binwidth=self.bins_width_scan,
        n_bins = self.n_scan_bins,
        n_histograms = self.n_scan_lines)
        self.time_diff.setMaxCounts(1)
        self.scan_full_matrix = np.zeros(self.n_scan_bins)



    @QtCore.Slot()
    def stop_sweep(self):
        self.time_diff.stop()
        # self.time_diff.clear()
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.queryInterval/1000)

    @QtCore.Slot()
    def update_plots(self):
        
        self.wavelength = self._wavemeter.get_current_wavelength()
        self.plot_y_wlm = self.plot_y_wlm[self.plot_y_wlm != 0]
        self.plot_y_wlm = np.insert(self.plot_y_wlm, 0, self.wavelength)[:250]
        # self.plot_y_wlm = np.delete(self.plot_y_wlm, -1)
        self.plot_x_wlm = np.linspace(0, len(self.plot_y_wlm) , len(self.plot_y_wlm))[:250]
 
        scan_data = self.time_diff.getData()  / (60 / (self.sweep_speed * self.n_scan_bins))
        if not self.time_diff.ready():
            self.scan_matrix = np.vstack((self.scan_full_matrix, scan_data))
        else:
            self.scan_full_matrix = self.scan_matrix
            self.time_diff.clear()
            scan_new_data = self.time_diff.getData()  / (60 / (self.sweep_speed * self.n_scan_bins))
            self.scan_matrix = np.vstack((self.scan_full_matrix, scan_new_data))


        scan_line = scan_data.flatten()
        scan_line = scan_line[scan_line > 0][-self.n_scan_bins:]
        self.plot_x = range(len(scan_line))#self._cts_wlm_time[2:,1] #wlm
        self.plot_y = scan_line#self._cts_wlm_time[2:, 0]#[x > 0] #cts
        self.sig_update_gui.emit()

    @QtCore.Slot(float, float, int)
    def set_sweep_params(self, amplitude, center_wl, sweep_speed):
        self.amplitude = amplitude
        self.center_wl = center_wl
        self.sweep_speed = sweep_speed
        self._initialize_plots()
        self.time_diff.clear()
        # self.counter.clear()

    @QtCore.Slot(bool)
    def regulate_wavelength(self, mode):
        mode_str = "on" if mode else "off"
        if mode_str == "on":
            self.cwl = self._wavemeter.get_current_wavelength()
            self._wavemeter.sig_send_request.emit("set_reference_course", str(self.cwl))
            # self._wavemeter.set_reference_course(str(cwl))
        # self._wavemeter.set_regulation_mode(mode_str)
        self._wavemeter.sig_send_request.emit("set_regulation_mode", str(mode_str))
        self.wlm_regmode = mode

