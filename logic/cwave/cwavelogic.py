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
from core.pi3_utils import delay
import numpy as np

class SearchZPLplotThread(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """
    # signal to deliver the wavelength to the parent class
    sig_search_plot = QtCore.Signal(list, list, list)
    # sig_reset_zpl_search = QtCore.Signal()
    def __init__(self, parentclass):
        super().__init__()
        # remember the reference to the parent class to access functions ad settings
        self._parentclass = parentclass
       
    #save counts and wavelength to file for further plotting

    #plot from file
    def _calculate_search_plot(self):
        """ The threaded method querying the data from the wavemeter and calculating the serach scan.
        """
        # w1, w2 = self._parentclass.w1, self._parentclass.w2
        cts_wlm_time_s = self._parentclass._cts_wlm_time_s
        cts_wlm_time_s = np.nan_to_num(cts_wlm_time_s)
        plot_xs = self._parentclass.plot_xs 
        plot_ys = self._parentclass.plot_ys
        samples_num = self._parentclass.samples_num
        cts_wlm = cts_wlm_time_s[:,:2][cts_wlm_time_s[:,1] > 0]
        ind = np.searchsorted(plot_xs, cts_wlm[:,1], side='left', sorter=None)
        ind[ind == len(plot_xs)] = len(plot_xs) - 1
        plot_ys[ind] = plot_ys[ind] + cts_wlm[:,0]
        vls, norm = np.unique(ind, return_counts = True)
        norm[norm == 0] += 1 
        plot_ys[vls] = plot_ys[vls] / norm
        samples_num[vls] = norm
        self.sig_search_plot.emit(list(plot_xs), list(plot_ys), list(samples_num))
    
    def stop(self):
        self._isRunning = False
class CwaveLogic(GenericLogic):
    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """
    sig_data_updated = QtCore.Signal()
    # declare connectors
    cwavelaser = Connector(interface='CwaveLaser')
    timetagger = Connector(interface='TT')
    wavemeter = Connector(interface='HighFinesseWavemeterClient')
    savelogic = Connector(interface='SaveLogic')
    
    queryInterval = ConfigOption('query_interval', 100)
    _go_to_freq = StatusVar('go_to_freq', 25)
    _pix_integration = StatusVar('pix_integration', 0.5)
    _static_v = StatusVar('goto_voltage', 0)
    
    dy = 1000 #dark counts -- initial error of the countrate
    count_freq = 50
    _search_query_time = 2000
    _scan_query_time = 0.1
    sweep_speed = 10
    amplitude = 0.001
    zpl_bin_width = 0.001
    center_wl = None

    sig_update_gui = QtCore.Signal()

    sig_update_cwave_states = QtCore.Signal()

    sig_update_guiPanelPlots = QtCore.Signal()
    sig_update_guiPlotsRefInt = QtCore.Signal()
    sig_update_guiPlotsOpoReg = QtCore.Signal()
    sig_update_guiPlotsRefExt = QtCore.Signal()

    sig_calculate_search_scan = QtCore.Signal()
    # sig_reset_zpl_search = QtCore.Signal()
    # sig_start_add_zpl_hdf5 = QtCore.Signal()


    def __init__(self, **kwargs):
        """ Create CwaveScannerLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)
        self.fit_x = []
        self.fit_y = []
        
        
        self.max_len = 10
        self.w1, self.w2 = 619.0, 619.01
        
        self.plot_x, self.plot_y = np.zeros(10),np.zeros(10)
        xx = np.arange(self.w1, self.w2, self.zpl_bin_width)
        self.plot_xs = xx
        self.plot_ys = np.zeros(len(xx))
        self.samples_num = np.ones(len(xx))
        self.deviance_ys =  self.dy / self.samples_num
    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._cwavelaser = self.cwavelaser()
        self._wavemeter = self.wavemeter()
        self._timetagger = self.timetagger() 
        self._save_logic = self.savelogic()

        self.counter = self._timetagger.counter(binwidth = int((1 / self.count_freq) * 1e12), n_values=1) #counts per second
        wlm_res = self._wavemeter.start_acqusition()
        delta_t = self._wavemeter.sync_clocks()
        self.time_sync = lambda _: time.time() - delta_t #returns time synced with the server
        self.wavelength = self._wavemeter.get_current_wavelength()
        self._cts_wlm_time = np.zeros((2,3)) #np.array([self.counter.getData()[-1][-1].mean(), self._wavemeter.get_current_wavelength(), self.time_sync(0)])
        self._cts_wlm_time[:, 2] = np.ones(2) * self.time_sync(0)
        
        self._cts_wlm_time_s = self._cts_wlm_time
        
        if wlm_res != 0 and self.wavelength <= 0:
            self.wavelength = self._cwavelaser.wavelength if self._cwavelaser.wavelength is not None else 0 
        self.wlm_regmode = True if self._wavemeter.get_regulation_mode() == 'on' else False
        self.shutters = self._cwavelaser.shutters
        self.status_cwave = self._cwavelaser.status_cwave
        self.cwstate = self._cwavelaser.cwstate
        
        self.laserPD = self._cwavelaser.read_photodiode_laser()
        self.opoPD = self._cwavelaser.read_photodiode_opo()
        self.shgPD = self._cwavelaser.read_photodiode_shg()
        self.reg_modes = self._cwavelaser.get_regmodes()

        self.mode_zpl = None#'sweep'
        self.sig_update_cwave_states.connect(self.update_cwave_states)

        self._initialise_data_matrix()
        # Initialie data matrix
        # delay timer for querying laser
        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.loop_body)#, QtCore.Qt.QueuedConnection)     
        self.queryTimer.start(self.queryInterval)
        self.sig_update_gui.emit()

        # create an indepentent thread for the hardware communication
        self.zpl_serach_thread = QtCore.QThread()
        
        # # create an object for the hardware communication and let it live on the new thread
        self._zpl_serach_thread_pull = SearchZPLplotThread(self)
        self._zpl_serach_thread_pull.moveToThread(self.zpl_serach_thread)

        # connect the signals in and out of the threade
        self.sig_calculate_search_scan.connect(self._zpl_serach_thread_pull._calculate_search_plot, QtCore.Qt.QueuedConnection)
        self._zpl_serach_thread_pull.sig_search_plot.connect(self.handle_search_plot)
       
        self.zpl_serach_thread.start()
        return 
    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        try:
            self._cwavelaser.disconnect()
            self._cts_wlm_time = self._cts_wlm_time[1:] #empty buffer
            self._zpl_serach_thread_pull.stop()
            self.zpl_serach_thread.quit()
            self.zpl_serach_thread.wait()
            self._zpl_serach_thread_pull = None
        except:
            print("Oi oi")
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
        return 
    # @thread_safety
    def save_data(self):
        print("here we save")

    @QtCore.Slot()
    def loop_body(self):
        self.sig_update_cwave_states.emit()
        qi = self.queryInterval
        self.queryTimer.start(qi)
        self.get_cts_wlm_data()
        self.sig_update_gui.emit()

    def _initialise_data_matrix(self):
        """ Initializing the matrix plot. """

        self.scan_matrix = np.zeros((2,2))
    
 
        pd_len = 60000 # 60 sec
        self.plot_x_shg_pd = np.linspace(0,int(pd_len/1000) , int(pd_len/self.queryInterval))
        self.plot_y_shg_pd = np.zeros(int(pd_len/self.queryInterval))

        self.plot_x_opo_pd = np.linspace(0,int(pd_len/1000) , int(pd_len/self.queryInterval))
        self.plot_y_opo_pd = np.zeros(int(pd_len/self.queryInterval))

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
        self._cts_wlm_time = self._cts_wlm_time[self._cts_wlm_time[:, 2] > 0][:1] #empty buffer
        center_wl = self._wavemeter.get_current_wavelength() if self.center_wl is None else self.center_wl 
        self._wavemeter.set_reference_course(f"{center_wl} + {self.amplitude} * triangle(t/{self.sweep_speed})")
        self._wavemeter.set_regulation_mode("on")
        #set_timer
        self.scanQueryTimer = QtCore.QTimer()
        self.scanQueryTimer.setInterval(self._scan_query_time)
        self.scanQueryTimer.setSingleShot(True)
        self.mode_zpl = 'sweep'
        self.scanQueryTimer.timeout.connect(self.get_cts_wlm_data)#, QtCore.Qt.QueuedConnection)     
        self.scanQueryTimer.start(self._scan_query_time)

    @QtCore.Slot()
    def stop_sweep(self):
        self.regulate_wavelength(True)
        self._cts_wlm_time = self._cts_wlm_time[1:] #empty buffer
        self.scanQueryTimer.stop()
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.queryInterval/1000)



    @QtCore.Slot(bool)
    def regulate_wavelength(self, mode):
        mode_str = "on" if mode else "off"
        if mode_str == "on":
            cwl = self._wavemeter.get_current_wavelength()
            self._wavemeter.set_reference_course(str(cwl))
        self._wavemeter.set_regulation_mode(mode_str)
        self.wlm_regmode = mode


    @QtCore.Slot()
    def get_cts_wlm_data(self):
        if self._wavemeter.get_current_wavelength() is not None:
            wavelength = self._wavemeter.get_current_wavelength()
        else:
            wavelength = 0

        self._cts_wlm_time = np.vstack((self._cts_wlm_time, np.array([self.counter.getData()[-1][0] * self.count_freq, wavelength, self.time_sync(0)])))[-1500:]
        cts_times =  self._cts_wlm_time[:, 2]
        dt = cts_times[-1] - cts_times
        #take only counts whithin the past 60 / sweep speed * 2 sec
        self._cts_wlm_time = self._cts_wlm_time[dt < (60 / self.sweep_speed) * 2]

        self._cts_wlm_time_s = np.vstack((self._cts_wlm_time_s, np.array([self.counter.getData()[-1][0] * self.count_freq, wavelength, self.time_sync(0)])))
        if len(self._cts_wlm_time_s) > 500:
            self.sig_calculate_search_scan.emit()

        if self.mode_zpl == 'sweep':
            self.scanQueryTimer.start(self._scan_query_time)

    @QtCore.Slot()
    def data_was_added(self):
        self.sig_calculate_search_scan.emit()
        self._cts_wlm_time_s = self._cts_wlm_time_s[1:]

    @QtCore.Slot(float, float, int)
    def set_zpl_sweep_params(self, amplitude, center_wl, sweep_speed):
        self.amplitude = amplitude
        self.center_wl = center_wl
        self.sweep_speed = sweep_speed
        self.mode_zpl == 'sweep'

    @QtCore.Slot()
    def stop_zpl_search(self):
        self._cts_wlm_time = self._cts_wlm_time[1:] #empty buffer
        # self._zpl_serach_thread_pull.stop()
        # self.zpl_serach_thread.quit()
        # self.zpl_serach_thread.wait()
        # self._zpl_serach_thread_pull = None
        # self.zpl_serach_thread = None
    #ZPL search
    
    @QtCore.Slot(float, float, float)
    def update_zpl_search_params(self, w1,w2, zpl_bin_width):
        self.w1 = w1
        self.w2 = w2
        self.zpl_bin_width = zpl_bin_width
        print(w1, w2,zpl_bin_width)
        self.plot_xs = np.arange(w1, w2, zpl_bin_width)
        self.plot_ys = np.zeros(self.plot_xs.shape[0])
        self.samples_num = np.ones(self.plot_xs.shape[0])
        self.deviance_ys =  self.dy / self.samples_num

    @QtCore.Slot(list, list, list)
    def handle_search_plot(self, x, y, samples_num):

        self.plot_xs = np.array(x)
        self.plot_ys = np.array(y)
        if self.plot_xs.shape[0] != self.plot_ys.shape[0]:
            print("Ahtung!")
        samples_num = np.array(samples_num)
        samples_num[samples_num == 0] = 1 # to avoid division by zero
        self.samples_num = samples_num
        self.deviance_ys = self.dy/samples_num
        
    @QtCore.Slot()
    def refresh_search_zpl(self):
        self.sig_calculate_search_scan.emit()

    @QtCore.Slot()
    def reset_search_zpl(self):
        self._cts_wlm_time_s = self._cts_wlm_time_s[:1]
        # self.sig_reset_zpl_search.emit()
        self.plot_xs = np.arange(self.w1, self.w2, self.zpl_bin_width)
        self.plot_ys = np.zeros(self.plot_xs.shape[0])
        self.samples_num = np.ones(self.plot_xs.shape[0])
        self.deviance_ys = self.dy/samples_num
        # self.sig_calculate_search_scan.emit()


    @QtCore.Slot()
    def refresh_sweep_zpl(self):
        #self._cts_wlm_time = self._cts_wlm_time[:1]
        self.plot_x = np.zeros(10)
        self.plot_y = np.zeros(10)

    #! Laser control panel:
    @QtCore.Slot(str)
    def optimize_cwave(self, opt_command):
        self._cwavelaser.set_command(opt_command)

    @QtCore.Slot(str, bool)
    def change_shutter_state(self, shutter, state):
        self._cwavelaser.shutters.update({shutter: state})
        self._cwavelaser.set_shutters_states()
        self.shutters = self._cwavelaser.shutters
        self.sig_update_gui.emit()

    @QtCore.Slot()
    def update_cwave_states(self):
        self._cwavelaser.get_shutters_states()
        self._cwavelaser.get_laser_status()
        self.shutters = self._cwavelaser.shutters
        self.status_cwave = self._cwavelaser.status_cwave

        self.laserPD = self._cwavelaser.read_photodiode_laser()
        self.opoPD = self._cwavelaser.read_photodiode_opo()
        self.shgPD = self._cwavelaser.read_photodiode_shg()

        self.reg_modes = self._cwavelaser.get_regmodes()        
        
        self.plot_y_shg_pd = np.insert(self.plot_y_shg_pd, 0, self.shgPD)
        self.plot_y_shg_pd = np.delete(self.plot_y_shg_pd, -1)

        self.plot_y_opo_pd = np.insert(self.plot_y_opo_pd, 0, self.opoPD)
        self.plot_y_opo_pd = np.delete(self.plot_y_opo_pd, -1)

        #if wavelength changes a lot calculate the search scan
        # if self._wavemeter.get_current_wavelength() - self.wavelength > 0.0015:
        #     self.sig_calculate_search_scan.emit()
        self.wavelength = self._wavemeter.get_current_wavelength()
        if self.wavelength <= 500:
            self.wavelength = self._cwavelaser.get_wavelength()
        self.plot_y_wlm = self.plot_y_wlm[self.plot_y_wlm != 0]
        self.plot_y_wlm = np.insert(self.plot_y_wlm, 0, self.wavelength)[:250]
        # self.plot_y_wlm = np.delete(self.plot_y_wlm, -1)
        self.plot_x_wlm = np.linspace(0, len(self.plot_y_wlm) , len(self.plot_y_wlm))[:250]
        
        self.plot_x = self._cts_wlm_time[2:,1] #wlm
        self.plot_y = self._cts_wlm_time[2:, 0]#[x > 0] #cts

        self.sig_update_gui.emit()
    
    @QtCore.Slot()
    def connection_cwave(self):
        """ Connect to the cwave """
        if self.cwstate == 0:
            self._cwavelaser.connect()
        else:
            self._cwavelaser.disconnect()
        self.cwstate = self._cwavelaser.cwstate
        print('CWAVE state:', self.cwstate)
        self.sig_update_gui.emit()

    @QtCore.Slot(int)
    def adj_thick_etalon(self, adj):
        # print("here_we_go", adj)
        self._cwavelaser.set_thick_etalon(adj)
        delay(2)

    @QtCore.Slot(int)
    def adj_opo_lambda(self, adj):
        # print("here_we_go", adj)
        self._cwavelaser.set_wavelength(adj)
        delay(5)

    @QtCore.Slot(float)
    def refcav_setpoint(self, new_voltage):
        # print("New setpoint:", new_voltage)
        new_voltage_hex = int(65535 * new_voltage / 100)
        res = self._cwavelaser.set_int_value('x', new_voltage_hex)
        delay(wait_time = 1)
        if res == 1:
            return
        else:
            raise Exception('The ref cavity set setpoint command failed.')
        self.setpoint  = new_voltage

    @QtCore.Slot(str, str)
    def change_lock_mode(self, param, mode): 
        if mode == 'control':
            self._cwavelaser.set_regmode_control(param)
        elif mode =='manual':
            self._cwavelaser.set_regmode_manual(param)