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

class ScannerWorker(QObject):
    finished = QtCore.Signal()
    update_progress = QtCore.Signal(list)
    ramp = list()
    nicard = None

    def run(self):
        """Scan with NI card."""
        self.is_Running = True
        if self.nicard is None or len(self.ramp) <= 0:
            return
        plot_y = self.nicard.scan_line(self.ramp).flatten()
        # sleep(10)
        self.update_progress.emit(list(plot_y))
        self.finished.emit()

class CwaveLogic(GenericLogic):


    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """

    sig_data_updated = QtCore.Signal()

    # declare connectors
    timetagger = Connector(interface='TT')
    cwavelaser = Connector(interface='CwaveLaser')
    wavemeter = Connector(interface='HighFinesseWavemeter')
    savelogic = Connector(interface='SaveLogic')
    nicard = Connector(interface='NationalInstrumentsXSeries')
    counterlogic = Connector(interface='CounterLogic')

    queryInterval = ConfigOption('query_interval', 500)

    _scan_range = StatusVar('scan_range', [0, 100])
    _go_to_freq = StatusVar('go_to_freq', 25)
    _number_of_repeats = StatusVar(default=1)
    _number_of_bins = StatusVar('number_of_bins', 100)
    _pix_integration = StatusVar('pix_integration', 0.5)
    # _scan_duration = StatusVar('scan_duration', 10 * 1000) #10 sec
    _static_v = StatusVar('goto_voltage', 0)

    sigSetpointChanged = QtCore.Signal(float)
    sigNextPixel = QtCore.Signal()
    sigNextLine_ext = QtCore.Signal()

    sigScanNextLine = QtCore.Signal()
    
    sigUpdate = QtCore.Signal()
    sigUpdateScanPlots = QtCore.Signal()
    sigScanFinished = QtCore.Signal()
    sigScanStarted = QtCore.Signal()
    sigDataNext = QtCore.Signal()
    sigGetUpdates = QtCore.Signal()
    sigGoToVoltage = QtCore.Signal(float)
    
    sigAdjEta = QtCore.Signal(int)
    sigOpoLambda = QtCore.Signal(int)
    sigUpdatePanelPlots = QtCore.Signal()

    sigUpdatePlotsRefInt = QtCore.Signal()
    sigUpdatePlotsOpoReg = QtCore.Signal()
    sigUpdatePlotsRefExt = QtCore.Signal()

    #! SCANWITH_MODES = ('oporeg', 'refcavext', 'refcavint')



    def __init__(self, **kwargs):
        """ Create CwaveScannerLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()
        self.threadManager = ThreadManager()
        self.stopRequested = False
        self.fit_x = []
        self.fit_y = []
        self.plot_x = []
        self.plot_y = []

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._cwavelaser = self.cwavelaser()
        self._wavemeter = self.wavemeter()
        self._timetagger = self.timetagger() 
        self._save_logic = self.savelogic()
        self._nicard = self.nicard()
        self._counter_logic = self.counterlogic()
        if self._counter_logic.module_state() == 'idle':
            self._counter_logic.startCount()

        if self._counter_logic.get_saving_state():
            self._counter_logic.save_data()
        resume = False
        self._counter_logic.start_saving(resume=resume)

        wlm_res = self._wavemeter.start_acqusition()
        self.wavelength = self._wavemeter.get_current_wavelength()
        self._acqusition_start_time = self._counter_logic._saving_start_time
        self._wavelength_data = np.array([0, 0])

        if wlm_res != 0 and self.wavelength <= 0:
            self.wavelength = self._cwavelaser.wavelength
        # print("wavelength", self.wavelength)


        self.shutters = self._cwavelaser.shutters
        self.status_cwave = self._cwavelaser.status_cwave
        self.cwstate = self._cwavelaser.cwstate
        self.scan_mode = 'refcavint'#refcavext or refcavint
        self.laserPD = self._cwavelaser.read_photodiode_laser()
        self.opoPD = self._cwavelaser.read_photodiode_opo()
        self.shgPD = self._cwavelaser.read_photodiode_shg()
        self.reg_modes = self._cwavelaser.get_regmodes()
        self.number_of_bins = self._number_of_bins
        self.number_of_repeats = self._number_of_repeats
        self.scan_range = self._scan_range
        self.pix_integration = self._pix_integration
        self.clock_freq = 1/self.pix_integration
        self.a_range = self._cwavelaser.VoltRange
        self.setpoint = self._cwavelaser.scanner_setpoint

        self.sigSetpointChanged.connect(self.change_setpoint)
        self.sigNextPixel.connect(self.scan_lines)
        self.sigNextLine_ext.connect(self.scan_line_ext, QtCore.Qt.QueuedConnection)
        self.sigAdjEta.connect(self.adj_thick_etalon)
        self.sigOpoLambda.connect(self.adj_opo_lambda)
        
        self.sigGoToVoltage.connect(self.go_to_voltage, QtCore.Qt.QueuedConnection)

        self.sigGetUpdates.connect(self.update_cwave_states)
        self.sigUpdatePanelPlots.connect(self.update_panel_plots)
        self.set_scan_range(self.scan_range)
        # self.goto_voltage(self._static_v)
        #############################
        # self.scan_hist = self._timetagger.histogram(number_of_bins= self.number_of_bins)
        
        self._initialise_data_matrix()

        # Initialie data matrix
        self.stopRequested = False

        # delay timer for querying laser
        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.loop_body)#, QtCore.Qt.QueuedConnection)     
        self.queryTimer.start(self.queryInterval)
        


        self.sigUpdate.emit()
        return 

    # @thread_safety
    @QtCore.Slot()
    def loop_body(self):
        # print("hey_yo")
        self.sigGetUpdates.emit()
        self.sigUpdatePanelPlots.emit()
        # #! update gui: (create qurey interval)
        qi = self.queryInterval
        self.queryTimer.start(qi)
        # if self.stopRequested and self.scan_mode == 'refcavext':
            # try:
            #     self.close_scanner()
            # except:
            #     print("Couldn't close the scanner")
        
        self.sigUpdate.emit()

    # @set_param_when_threading
  
    # @set_param_when_threading
    def close_scanner(self):
        self._nicard.close_scanner_clock()
        self._nicard.close_scanner()

    def init_ni_scanner(self, clock_freq):
        """Initialise the clock and locks for a scan"""
        self._nicard.set_up_scanner_clock(clock_frequency=clock_freq)
        self._nicard.set_up_scanner()
    
    @QtCore.Slot(list)
    def set_scan_range(self, scan_range):
        r_max = np.clip(scan_range[1], self.a_range[0], self.a_range[1])
        r_min = np.clip(scan_range[0], self.a_range[0], r_max)
        self.scan_range = [r_min, r_max]
        print("New scan range:", self.scan_range)
    
    def set_scan_lines(self, scan_lines):
        self.number_of_repeats = int(np.clip(scan_lines, 1, 1e6))

    def _initialise_data_matrix(self):
        """ Initializing the matrix plot. """

        self.scan_matrix = np.zeros((self.number_of_repeats, self.number_of_bins))
    
        self.plot_x = np.linspace(self.scan_range[0], self.scan_range[1], self.number_of_bins)
        self.plot_y = np.zeros(self.number_of_bins)
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
    def start_scanning(self):
        print('start scanning')
        self.stopRequested = False
        # self.close_scanner()
        #TODO hardcoded limit on the scan duration
        self.scan_range[0], self.scan_range[1]

        if self.cwstate == 0:
            print("cwave is not connected")
            return 
        if self.scan_mode == "refcavint":
            if self.pix_integration*self.number_of_bins > 5: 
                print("Scan range: ", self.scan_range)
                print("self.number_of_bins", self.number_of_bins)
                self._initialise_data_matrix()
                self.scan_points = np.linspace(self.scan_range[0], 
                self.scan_range[1], 
                self.number_of_bins)
                self.scan_counter = self._timetagger.countrate() 
                self.scan_lines()
            else:
                raise Exception("Too fast scanning!")

        elif self.scan_mode == "refcavext":
            self.scan_ext()
            
            # self.sigNextLine_ext.emit()

        elif self.scan_mode == "oporeg":
            print("Scan range: ", self.scan_range)
            print("number_of_bins", self.number_of_bins)
            self._initialise_data_matrix()
            scan_duration = self.number_of_bins * self.pix_integration
            if scan_duration < 3000:
                print("Wow, let's make a slower scan first")
            else:
                # delay timer for querying laser
                self.scanQueryTimer = QtCore.QTimer()
                self.scanQueryTimer.setInterval(scan_duration)
                self.scanQueryTimer.setSingleShot(True)
                self.scanQueryTimer.timeout.connect(self.update_opo_reg_scan_plots, QtCore.Qt.QueuedConnection)     
                self.scan_trace = self._timetagger.counter(refresh_rate=self.pix_integration, n_values=self.number_of_bins)
                self.scanQueryTimer.start()
                self._cwavelaser.scan(scan_duration, self.scan_range[0], self.scan_range[1])
    
    @QtCore.Slot()
    def stop_scanning(self):
        print('stop scanning')
        self.stopRequested = True
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.queryInterval/1000)

    def kill_scanner(self):
        """Closing the scanner device.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._nicard.close_scanner()
        except Exception as e:
            self.log.exception('Could not close the scanner.')
        try:
            self._nicard.close_scanner_clock()
        except Exception as e:
            self.log.exception('Could not close the scanner clock.')
        try:
            self._nicard.module_state.unlock()
        except Exception as e:
            pass
            # self.log.exception('Could not unlock scanning device.')

        return 0

    @QtCore.Slot()
    def update_opo_reg_scan_plots(self):
        if self.stopRequested:
            self.scanQueryTimer.stop()
            return 
        self.plot_y = self.scan_trace.getData().sum(axis=0) * (1/self.pix_integration) # to counts 

        self.scan_matrix = np.vstack((self.scan_matrix, self.plot_y))
        self.sigUpdateScanPlots.emit()
        self.scan_trace.clear()

    @QtCore.Slot()
    def scan_lines(self):
        print("Next Pix")
        if self.stopRequested:
            return 
        if (self.scan_points.shape[0] > 0) and (not self.stopRequested):
            self.change_setpoint(self.scan_points[0])
            self.scan_counter.clear()
            sleep(self.pix_integration)
            self.plot_y[self.number_of_bins - self.scan_points.shape[0]] = self.scan_counter.getData().sum()
            # print("pix number:", self.number_of_bins - self.scan_points.shape[0], self.scan_counter.getData().sum())
            self.scan_points = np.delete(self.scan_points, 0)
            # print("self.scan_points", self.scan_points)
            self.sigUpdateScanPlots.emit()
            self.sigUpdate.emit()
            self.sigUpdatePanelPlots.emit()
            self.sigNextPixel.emit()
        else:
            #NEXT line
            print("Next LINE")
            self.scan_matrix = np.vstack((self.scan_matrix, self.plot_y))
            self.plot_y = np.zeros(self.number_of_bins)
            self.scan_points = np.linspace(self.scan_range[0], self.scan_range[1], self.number_of_bins)
            self.change_setpoint(self.scan_range[0], slowly=True)
            self.sigNextPixel.emit()
    
    def scan_ext(self):
        """ 
        Start external scanner
        """
        self.is_Running = False
        self._initialise_data_matrix()
        self.clock_freq = 1/self.pix_integration
        scan_duration = self.number_of_bins * self.pix_integration
        self.ramp = self.make_ramp(*self.scan_range, self.number_of_bins)
        self.sigNextLine_ext.emit()
        
    def scan_line_ext(self):
        self.init_ni_scanner(self.clock_freq)
        print("Start scan line")
        if self.stopRequested:
            self.go_to
            self.kill_scanner()
            return
        if self.is_Running:
            print("Thread is already running")
            self.scan_line_ext() 
        self.thread = self.threadManager.newThread("nicard+cwave")
        self.worker = ScannerWorker()
        self.worker.ramp = self.ramp
        self.worker.nicard = self._nicard

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.update_progress.connect(self.scan_lines_ext_finished)
       
        self.thread.start()

        self._nicard.module_state.lock()

        self.thread.finished.connect(
            self.stop_thread
        )

    def stop_thread(self):
        
        self.threadManager.joinThread("nicard+cwave", 100)
        self.threadManager.cleanupThread("nicard+cwave")
        # try: 
        #     self.threadManager.getItemByNumber("nicard+cwave")
        #     self.is_Running = True
        # except:
        #     self.is_Running = False
        # # self._nicard.module_state.unlock()
    
    @QtCore.Slot(list)
    def scan_lines_ext_finished(self, plot_y):
        self.kill_scanner()
        self.scan_matrix = np.vstack((self.scan_matrix, np.array(plot_y)))
        self.sigUpdatePanelPlots.emit()
        self.sigUpdateScanPlots.emit()

        self.sigGoToVoltage.emit(self.scan_range[0])
        print("StopReq", self.stopRequested)
        if not self.stopRequested and not self.is_Running:
            print("Scanning again!")
            # sleep(5)
            # self.scan_ext()
            self.sigNextLine_ext.emit()
           
    def make_ramp(self, start=0, stop=0, steps_number=50):
        current_pos = np.array(self._nicard.get_scanner_position())
        if start == 0:
            start = current_pos[-1]
        ramp = np.ones(steps_number) * current_pos[:, np.newaxis]
        scan_points = np.linspace(start, stop, steps_number)
        ramp[-1] = scan_points
        return ramp 

    @QtCore.Slot(int)
    def set_number_of_bins(self, number_of_bins):
        self.number_of_bins = number_of_bins

    #! Laser control panel:
    @QtCore.Slot(str)
    def optimize_cwave(self, opt_command):
        self._cwavelaser.set_command(opt_command)

    @QtCore.Slot(str, bool)
    def change_shutter_state(self, shutter, state):
        self._cwavelaser.shutters.update({shutter: state})
        self._cwavelaser.set_shutters_states()
        self.shutters = self._cwavelaser.shutters
        self.sigUpdate.emit()

    @QtCore.Slot(str)
    def change_scan_mode(self, scan_mode):
        self.scan_mode = scan_mode
        # self._initialise_data_matrix()
        # if scan_mode == 'refcavint':
        #     self.plot_x = np.linspace(self.scan_range[0], self.scan_range[1], self.number_of_bins)
        #     self.plot_y = np.zeros(self.number_of_bins)
        print("Scanning mode: ", scan_mode)

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

        self.wavelength = self._wavemeter.get_current_wavelength()
        if self.wavelength <= 500:
            self.wavelength = self._cwavelaser.get_wavelength()
        else:
            time_stamp = time.time() - self._acqusition_start_time

        # only wavelength >200 nm make sense, ignore the rest
            if self.wavelength > 500:
                self._wavelength_data = np.vstack((self._wavelength_data,
                    np.array([time_stamp, self.wavelength])
                ))


        self.sigUpdate.emit()

    @QtCore.Slot()
    def update_panel_plots(self):
        self.sigGetUpdates.emit()
        self.plot_y_shg_pd = np.insert(self.plot_y_shg_pd, 0, self.shgPD)
        self.plot_y_shg_pd = np.delete(self.plot_y_shg_pd, -1)

        self.plot_y_opo_pd = np.insert(self.plot_y_opo_pd, 0, self.opoPD)
        self.plot_y_opo_pd = np.delete(self.plot_y_opo_pd, -1)
        self.plot_y_wlm = self.plot_y_wlm[self.plot_y_wlm != 0]
        self.plot_y_wlm = np.insert(self.plot_y_wlm, 0, self.wavelength)
        # self.plot_y_wlm = np.delete(self.plot_y_wlm, -1)
        self.plot_x_wlm = np.linspace(0, len(self.plot_y_wlm) , len(self.plot_y_wlm)) 
        

    @QtCore.Slot()
    def connection_cwave(self):
        """ Connect to the cwave """
        if self.cwstate == 0:
            self._cwavelaser.connect()
        else:
            self._cwavelaser.disconnect()
        self.cwstate = self._cwavelaser.cwstate
        print('CWAVE state:', self.cwstate)
        self.sigUpdate.emit()

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
    def go_to_voltage(self, voltage):
        
        ramp = self.make_ramp(stop = voltage, steps_number = 150)
        freq_diff = np.abs(ramp[-1][-1] - ramp[-1][0]) 
        self.init_ni_scanner(clock_freq=self._go_to_freq * 100/freq_diff)
        self._nicard.scan_line(ramp)
        delay(delay_sec = 1)
        self.kill_scanner()

    @QtCore.Slot(float)
    def change_setpoint(self, new_voltage, slowly=False):
        # print("New setpoint:", new_voltage)
        
        if self.scan_mode == 'refcavint':
            delta = np.abs(self.setpoint - new_voltage)
            delta_v = np.linspace(self.setpoint, new_voltage, int(delta)+1)
            print(delta_v, self.setpoint, new_voltage)
            wait_time = 0.1
            if slowly == True:
                wait_time = 0.5
            for v in delta_v:
                new_voltage_hex = int(65535 * v / 100)
                res = self._cwavelaser.set_int_value('x', new_voltage_hex)
                delay(wait_time = 1)
            new_voltage_hex = int(65535 * new_voltage / 100)
            res = self._cwavelaser.set_int_value('x', new_voltage_hex)
            if res == 1:
                return
            else:
                raise Exception('The ref cavity set setpoint command failed.')
        elif self.scan_mode == 'oporeg':
            pass
        elif self.scan_mode == 'refcavext':
            self.sigGoToVoltage.emit(new_voltage)

        self.setpoint  = new_voltage


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._cwavelaser.disconnect()
        for i in range(5):
            QtCore.QCoreApplication.processEvents()
        return 

    @QtCore.Slot(str, str)
    def change_lock_mode(self, param, mode): 
        if mode == 'control':
            self._cwavelaser.set_regmode_control(param)
        elif mode =='manual':
            self._cwavelaser.set_regmode_manual(param)