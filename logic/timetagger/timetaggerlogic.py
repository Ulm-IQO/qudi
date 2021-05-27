from qtpy import QtCore
import sys

from core.connector import Connector
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
import yaml

class TimeTaggerLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """

    timetagger = Connector(interface='TT')
    savelogic = Connector(interface='SaveLogic')

    
    sigUpdate = QtCore.Signal()
    sigNewMeasurement = QtCore.Signal()
    sigHistRefresh = QtCore.Signal()
    sigUpdateGuiParams=QtCore.Signal()
    def __init__(self, **kwargs):
        """ Create CwaveScannerLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)


        # locking for thread safety
        self.stopRequested = False
        self.fit_x = []
        self.fit_y = []
        self.plot_x = []
        self.plot_y = []
        self.refresh_time = 1000
        self.load_params()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._timetagger = self.timetagger()
        self._save_logic = self.savelogic()
                # Initialie data matrix
        self.stopRequested = False

        self.sigNewMeasurement.connect(self.new_measurement)
        self.sigHistRefresh.connect(self.set_hist_refresh_time)
        
        self.init_plot_params()
        self.init_plots()

        # delay timer for querying laser
        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.loop_body, QtCore.Qt.QueuedConnection)     
        self.queryTimer.start(self.queryInterval)
        self.set_hist_refresh_time.emit(self.refresh_time)
        

        self.sigUpdate.emit()

    @QtCore.Slot(float)
    def set_hist_refresh_time(self, refresh_time):
        self.hist_update_timer = QtCore.QTimer()
        self.hist_update_timer.setInterval(refresh_time)
        self.hist_update_timer.setSingleShot(True)
        self.hist_update_timer.timeout.connect(self.refresh_hist_loop, QtCore.Qt.QueuedConnection)     
        self.hist_update_timer.start(refresh_time)
        self.refresh_time = refresh_time


    @QtCore.Slot(str, str, int)
    def update_tt_params(self, curve, param, value):
        curve_d = next((k for k in self.__dict__.keys() if curve in k), None) 
        self.__dict__[f"{curve_d}_params"][param] = value
        # self.hist_params = 

    @QtCore.Slot()
    def init_plots(self):
        self.time_counter = np.linspace(0, self.counter_params['number_of_bins']*self.counter_params['bins_width']/1000, self.counter_params['number_of_bins'])
        self.time_hist = np.linspace(0, self.hist_params['number_of_bins']*self.hist_params['bins_width']/1000, self.hist_params['number_of_bins'])
        self.time_corr = np.linspace(0, self.corr_params['number_of_bins']*self.corr_params['bins_width']/1000, self.corr_params['number_of_bins'])

        self.hist_tt = self._timetagger.histogram(self.hist_params)
        self.corr_tt = self._timetagger.correlation(self.corr_params)
        self.counter_tt = self._timetagger.counter(self.counter_params)


    @QtCore.Slot()
    def load_params(self):
        with open("params.yaml", 'r') as param_file:
            try:
                self.tt_params = yaml.safe_load(param_file)
            except yaml.YAMLError as exc:
                print(exc)
        for key in self.tt_params:
            setattr(self, f"{key}_params", self.tt_params[key])
        self.sigNewMeasurement.emit()
        self.sigUpdateGuiParams.emit()

    @QtCore.Slot()
    def save_params(self):
        with open("params.yaml", 'w') as param_file:
            for key in self.tt_params:
                key = key.split("_params")[0]
                self.tt_params[key] = getattr(self, key, 0)
            try:
                yaml.dump(self.tt_params, param_file)
            except yaml.YAMLError as exc:
                print(exc)        

    @QtCore.Slot(int)
    def change_hist_channel(self, channel):
        self.hist_params['channel'] = channel
        self.sigNewMeasurement.emit()

    # @thread_safety
    @QtCore.Slot()
    def loop_body(self):
        self.sigUpdate.emit()

    @QtCore.Slot()
    def refresh_hist_loop(self):
        self.hist_tt.clear()

    @QtCore.Slot()
    def new_measurement(self):
        self.init_plots()
        self.sigUpdate.emit()

