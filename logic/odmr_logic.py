# -*- coding: utf-8 -*-

"""
This file contains the Qudi Logic module base class.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from qtpy import QtCore
from collections import OrderedDict
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge
import numpy as np
import time
import datetime
import matplotlib.pyplot as plt
import lmfit

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex

class ODMRLogic(GenericLogic):

    """This is the Logic class for ODMR."""
    _modclass = 'odmrlogic'
    _modtype = 'logic'
    # declare connectors
    _connectors = {
        'odmrcounter': 'ODMRCounterInterface',
        'fitlogic': 'FitLogic',
        'microwave1': 'mwsourceinterface',
        'savelogic': 'SaveLogic',
        'taskrunner': 'TaskRunner'
    }

    # Internal signals
    sigNextLine = QtCore.Signal()


    # Update signals, e.g. for GUI module
    sigParameterUpdated = QtCore.Signal(dict)
    sigOutputStateUpdated = QtCore.Signal(str, bool)
    sigOdmrPlotsUpdated = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray)
    sigOdmrFitUpdated = QtCore.Signal(np.ndarray, np.ndarray, str, str)
    sigOdmrElapsedTimeUpdated = QtCore.Signal(float, int)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

        self.threadlock = Mutex()

    def on_activate(self):
        """ 
        Initialisation performed during activation of the module.
        """
        # Get configuration
        config = self.getConfiguration()

        # Get connectors
        self._mw_device = self.get_connector('microwave1')
        self._fit_logic = self.get_connector('fitlogic')
        self._odmr_counter = self.get_connector('odmrcounter')
        self._save_logic = self.get_connector('savelogic')
        self._taskrunner = self.get_connector('taskrunner')

        # Setup fit container
        self.fc = self._fit_logic.make_fit_container('ODMR sum', '1d')
        self.fc.set_units(['Hz', 'c/s'])
        if 'fits' in self._statusVariables and isinstance(self._statusVariables['fits'], dict):
            self.fc.load_from_dict(self._statusVariables['fits'])
        else:
            d1 = OrderedDict()
            d1['Lorentzian dip'] = {
                'fit_function': 'lorentzian',
                'estimator': 'dip'
                }
            d1['Two Lorentzian dips'] = {
                'fit_function': 'lorentziandouble',
                'estimator': 'dip'
                }
            d1['N14'] = {
                'fit_function': 'lorentziantriple',
                'estimator': 'N14'
                }
            d1['N15'] = {
                'fit_function': 'lorentziandouble',
                'estimator': 'N15'
                }
            d1['Two Gaussian dips'] = {
                'fit_function': 'gaussiandouble',
                'estimator': 'dip'
                }
            default_fits = OrderedDict()
            default_fits['1d'] = d1
            self.fc.load_from_dict(default_fits)

        # Set/recall clock frequency for ODMR counting device in Hz
        if 'clock_frequency' in self._statusVariables:
            self.clock_frequency = self._statusVariables['clock_frequency']
        else:
            self.clock_frequency = 200

        # Set/recall microwave source parameters
        if 'mw_frequency' in self._statusVariables:
            self.mw_frequency = self._mw_device.get_limits().frequency_in_range(
                self._statusVariables['mw_frequency'])
        else:
            self.mw_frequency = self._mw_device.get_limits().frequency_in_range(2870e6)
        if 'mw_power' in self._statusVariables:
            self.mw_power = self._mw_device.get_limits().power_in_range(
                self._statusVariables['mw_power'])
        else:
            self.mw_power = self._mw_device.get_limits().power_in_range(-30)
        if 'mw_start' in self._statusVariables:
            self.mw_start = self._mw_device.get_limits().frequency_in_range(
                self._statusVariables['mw_start'])
        else:
            self.mw_start = self._mw_device.get_limits().frequency_in_range(2800e6)
        if 'mw_stop' in self._statusVariables:
            self.mw_stop = self._mw_device.get_limits().frequency_in_range(
                self._statusVariables['mw_stop'])
        else:
            self.mw_stop = self._mw_device.get_limits().frequency_in_range(2950e6)
        if 'mw_step' in self._statusVariables:
            self.mw_step = self._mw_device.get_limits().list_step_in_range(
                self._statusVariables['mw_step'])
        else:
            self.mw_step = self._mw_device.get_limits().list_step_in_range(2e6)

        # Set the trigger polarity (RISING/FALLING) of the mw-source input trigger
        # theoretically this can be changed, but the current counting scheme will not support that
        self.mw_trigger_pol = TriggerEdge.RISING
        self.set_trigger_pol(self.mw_trigger_pol)

        # Get scanmode from config. Currently only sweep and list is allowed
        if 'scanmode' in config:
            if ('sweep' in config['scanmode']) or ('SWEEP' in config['scanmode']):
                self.mw_scanmode = MicrowaveMode.SWEEP
            elif ('list' in config['scanmode']) or ('LIST' in config['scanmode']):
                self.mw_scanmode = MicrowaveMode.LIST
            else:
                self.mw_scanmode = MicrowaveMode.LIST
                self.log.error('Specified scanmode "{0}" not valid. Choose "list" or "sweep".\n'
                               'Falling back to list mode.'.format(config['scanmode']))
        else:
            self.mw_scanmode = MicrowaveMode.LIST
            self.log.warning('No scanmode defined in config for odmr_logic module.\n'
                             'Falling back to list mode.')

        # Set/recall ODMR runtime in seconds
        if 'run_time' in self._statusVariables:
            self.run_time = self._statusVariables['run_time']
        else:
            self.run_time = 60

        # Elapsed measurement time and number of sweeps
        self.elapsed_time = 0.0
        self.elapsed_sweeps = 0

        # Set flags
        # for stopping a measurement
        self._stopRequested = False
        # for clearing the ODMR data during a measurement
        self._clearOdmrData = False
        # for saving of raw data
        if 'saveRawData' in self._statusVariables:
            self._saveRawData = self._statusVariables['saveRawData']
        else:
            self._saveRawData = False

        # Set/recall number of lines in the raw data matrix
        if 'number_of_lines' in self._statusVariables:
            self.number_of_lines = self._statusVariables['number_of_lines']
        else:
            self.number_of_lines = 50

        # Initalize the ODMR data arrays (mean signal and sweep matrix)
        self._initialize_odmr_plots()

        # Switch off microwave and set CW mode with default/recalled frequency and power
        self.mw_off()
        self.set_cw(self.mw_frequency, self.mw_power)

        # Connect signals
        self.sigNextLine.connect(self._scan_ODMR_line, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Stop measurement if it is still running
        if self.getState() == 'locked':
            self.stop_odmr_scan()
        timeout = 30.0
        start_time = time.time()
        while self.getState() == 'locked':
            time.sleep(0.5)
            timeout -= (time.time() - start_time)
            if timeout <= 0.0:
                self.log.error('Failed to properly deactivate odmr logic. Odmr scan is still '
                               'running but can not be stopped after 30 sec.')
                break
        # Switch off microwave source for sure (also if CW mode is active or module is still locked)
        self._mw_device.off()
        # Disconnect signals
        self.sigNextLine.disconnect()
        # save parameters stored in app state store
        self._statusVariables['clock_frequency'] = self.clock_frequency
        self._statusVariables['mw_frequency'] = self.mw_frequency
        self._statusVariables['mw_power'] = self.mw_power
        self._statusVariables['mw_start'] = self.mw_start
        self._statusVariables['mw_stop'] = self.mw_stop
        self._statusVariables['mw_step'] = self.mw_step
        self._statusVariables['run_time'] = self.run_time
        self._statusVariables['saveRawData'] = self.saveRawData
        self._statusVariables['number_of_lines'] = self.number_of_lines
        if len(self.fc.fit_list) > 0:
            self._statusVariables['fits'] = self.fc.save_to_dict()

    def _initialize_odmr_plots(self):
        """ Initializing the ODMR plots (line and matrix). """
        self.odmr_plot_x = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step)
        self.odmr_plot_y = np.zeros(self.odmr_plot_x.size)
        self.odmr_fit_x = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step)
        self.odmr_fit_y = np.zeros(self.odmr_fit_x.size)
        self.odmr_plot_xy = np.zeros([self.number_of_lines, self.odmr_plot_x.size])
        self.sigOdmrPlotsUpdated.emit(self.odmr_plot_x, self.odmr_plot_y, self.odmr_plot_xy)
        current_fit = self.fc.current_fit
        self.sigOdmrFitUpdated.emit(self.odmr_fit_x, self.odmr_fit_y, '', current_fit)
        return

    def set_trigger_pol(self, trigger_pol):
        """
        Set trigger polarity of external microwave trigger (for list and sweep mode).
        
        @param object trigger_pol: one of [TriggerEdge.RISING, TriggerEdge.FALLING]
        
        @return object: actually set trigger polarity returned from hardware
        """
        if self.getState() != 'locked':
            self.mw_trigger_pol = self._mw_device.set_ext_trigger(trigger_pol)
        else:
            self.log.warning('set_trigger_pol failed. Logic is locked.')

        update_dict = {'trigger_pol': self.mw_trigger_pol}
        self.sigParameterChanged.emit(update_dict)
        return self.mw_trigger_pol

    def set_clock_frequency(self, clock_frequency):
        """
        Sets the frequency of the counter clock

        @param int clock_frequency: desired frequency of the clock

        @return int: actually set clock frequency
        """
        # checks if scanner is still running
        if self.getState() != 'locked' and isinstance(clock_frequency, (int, float)):
            self.clock_frequency = int(clock_frequency)
        else:
            self.log.warning('set_clock_frequency failed. Logic is either locked or input value is '
                             'no integer or float.')

        update_dict = {'clock_frequency': self.clock_frequency}
        self.sigParameterChanged.emit(update_dict)
        return self.clock_frequency

    def set_matrix_line_number(self, number_of_lines):
        """
        Sets the number of lines in the ODMR matrix

        @param int number_of_lines: desired number of matrix lines

        @return int: actually set number of matrix lines
        """
        if isinstance(number_of_lines, int):
            self.number_of_lines = number_of_lines
        else:
            self.log.warning('set_matrix_line_number failed. '
                             'Input parameter number_of_lines is no integer.')

        update_dict = {'number_of_lines': self.number_of_lines}
        self.sigParameterChanged.emit(update_dict)
        return self.number_of_lines

    def set_runtime(self, runtime):
        """
        Sets the runtime for ODMR measurement

        @param float runtime: desired runtime in seconds

        @return float: actually set runtime in seconds
        """
        if isinstance(runtime, (int, float)):
            self.run_time = runtime
        else:
            self.log.warning('set_runtime failed. Input parameter runtime is no integer or float.')

        update_dict = {'runtime': self.run_time}
        self.sigParameterChanged.emit(update_dict)
        return self.run_time

    def set_power(self, power):
        """ Forwarding the desired new power from the GUI to the MW source.

        @param float power: power set at the GUI

        @return float: currently set power in dBm
        """
        if self.getState() != 'locked' and isinstance(power, (int, float)):
            power_to_set = self._mw_device.get_limits().power_in_range(power)
            self.mw_power = self._mw_device.set_power(power_to_set)
        else:
            self.log.warning('set_power failed. Logic is either locked or input value is '
                             'no integer or float.')

        param_dict = {'mw_power': self.mw_power}
        self.sigParameterChanged.emit(param_dict)
        return self.mw_power

    def set_cw_frequency(self, frequency):
        """ Set the desired new cw mode frequency.

        @param float frequency: frequency to set in Hz

        @return float: actually set frequency in Hz
        """
        if self.getState() != 'locked' and isinstance(frequency, (int, float)):
            frequency_to_set = self._mw_device.get_limits().frequency_in_range(frequency)
            self.mw_frequency, dummy1, dummy2 = self._mw_device.set_cw(frequency=frequency_to_set)
        else:
            self.log.warning('set_cw_frequency failed. Logic is either locked or input value is '
                             'no integer or float.')

        param_dict = {'mw_frequency': self.mw_frequency}
        self.sigParameterChanged.emit(param_dict)
        return self.mw_frequency

    def set_sweep_frequencies(self, start, stop, step):
        """ Set the desired frequency parameters for list and sweep mode

        @param float start: start frequency to set in Hz
        @param float stop: stop frequency to set in Hz
        @param float step: step frequency to set in Hz

        @return float, float, float: current start_freq, current stop_freq, current freq_step
        """
        if self.getState() != 'locked':
            if isinstance(start, (int, float)):
                self.mw_start = self._mw_device.get_limits().frequency_in_range(start)
            if isinstance(stop, (int, float)):
                self.mw_stop = self._mw_device.get_limits().frequency_in_range(stop)
            if isinstance(step, (int, float)):
                if self.scanmode == MicrowaveMode.LIST:
                    self.mw_step = self._mw_device.get_limits().list_step_in_range(step)
                elif self.scanmode == MicrowaveMode.SWEEP:
                    self.mw_step = self._mw_device.get_limits().sweep_step_in_range(step)
        else:
            self.log.warning('set_list_parameters failed. Logic is locked.')

        param_dict = {'mw_start': self.mw_start, 'mw_stop': self.mw_stop, 'mw_step': self.mw_step}
        self.sigParameterChanged.emit(param_dict)
        return self.mw_start, self.mw_stop, self.mw_step

    def mw_cw_on(self):
        """ 
        Switching on the mw source in cw mode.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        if self.getState() == 'locked':
            self.log.error('Can not start microwave in CW mode. Odmr_logic is already locked.')
        else:
            self.mw_frequency, self.mw_power, mode = self._mw_device.set_cw(self.mw_frequency,
                                                                            self.mw_power)
            param_dict = {'mw_frequency': self.mw_frequency, 'mw_power': self.mw_power}
            self.sigParameterChanged.emit(param_dict)
            if mode != 'cw':
                self.log.error('Switching to CW microwave output mode failed.')
            else:
                err_code = self._mw_device.cw_on()
                if err_code < 0:
                    self.log.error('Activation of microwave output failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        return mode, is_running

    def mw_sweep_on(self):
        """ 
        Switching on the mw source in list/sweep mode.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        if self.scanmode == MicrowaveMode.LIST:
            if np.abs(self.mw_stop - self.mw_start) / self.mw_step >= self.limits.list_maxentries:
                self.log.warning('Number of frequency steps too large for microwave device. '
                                 'Lowering resolution to fit the maximum length.')
                self.mw_step = self.np.abs(self.mw_stop - self.mw_start) / (
                    self.limits.list_maxentries - 1)
        elif self.scanmode == MicrowaveMode.SWEEP:
            if np.abs(self.mw_stop - self.mw_start) / self.mw_step >= self.limits.sweep_maxentries:
                self.log.warning('Number of frequency steps too large for microwave device. '
                                 'Lowering resolution to fit the maximum length.')
                self.mw_step = self.np.abs(self.mw_stop - self.mw_start) / (
                    self.limits.list_maxentries - 1)

        if self.scanmode == MicrowaveMode.SWEEP:
            self.mw_start, \
            self.mw_stop, \
            self.mw_step, \
            self.mw_power, \
            mode = self._mw_device.set_sweep(self.mw_start, self.mw_stop,
                                             self.mw_step, self.mw_power)
            param_dict = {'mw_start': self.mw_start, 'mw_stop': self.mw_stop,
                          'mw_step': self.mw_step, 'mw_power': self.mw_power}
        else:
            freq_list = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step)
            freq_list, self.mw_power, mode = self._mw_device.set_list(freq_list, self.mw_power)
            param_dict = {'mw_power': self.mw_power}
        self.sigParameterChanged.emit(param_dict)

        if mode != 'list' and mode != 'sweep':
            self.log.error('Switching to list/sweep microwave output mode failed.')
        elif self.scanmode == MicrowaveMode.SWEEP:
            err_code = self._mw_device.sweep_on()
            if err_code < 0:
                self.log.error('Activation of microwave output failed.')
        else:
            err_code = self._mw_device.list_on()
            if err_code < 0:
                self.log.error('Activation of microwave output failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        return mode, is_running

    def reset_sweep(self):
        """
        Resets the list/sweep mode of the microwave source to the first frequency step.
        """
        if self.scanmode == MicrowaveMode.SWEEP:
            self._mw_device.reset_sweeppos()
        elif self.scanmode == MicrowaveMode.LIST:
            self._mw_device.reset_listpos()
        return

    def mw_off(self):
        """ Switching off the MW source.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        error_code = self._mw_device.off()
        if error_code < 0:
            self.log.error('Switching off microwave source failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        return mode, is_running

    def _start_odmr_counter(self):
        """
        Starting the ODMR counter and set up the clock for it.

        @return int: error code (0:OK, -1:error)
        """
        clock_status = self._odmr_counter.set_up_odmr_clock(clock_frequency=self.clock_frequency)
        if clock_status < 0:
            return -1

        counter_status = self._odmr_counter.set_up_odmr()
        if counter_status < 0:
            self._odmr_counter.close_odmr_clock()
            return -1

        return 0

    def _stop_odmr_counter(self):
        """ 
        Stopping the ODMR counter. 
        
        @return int: error code (0:OK, -1:error)
        """

        ret_val1 = self._odmr_counter.close_odmr()
        if ret_val1 != 0:
            self.log.error('ODMR counter could not be stopped!')
        ret_val2 = self._odmr_counter.close_odmr_clock()
        if ret_val2 != 0:
            self.log.error('ODMR clock could not be stopped!')

        # Check with a bitwise or:
        return ret_val1 | ret_val2

    def start_odmr_scan(self):
        """ Starting an ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self.log.error('Can not start ODMR scan. Logic is already locked.')
                return -1

            self.lock()
            self._clearOdmrData = False
            self.stopRequested = False
            self.fc.clear_result()

            self.elapsed_sweeps = 0
            self.elapsed_time = 0.0
            self._startTime = time.time()
            self.sigOdmrElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_sweeps)

            if self.saveRawData:
                self.log.info('Raw data saving...')
            else:
                self.log.info('Raw data NOT saved.')

            odmr_status = self._start_odmr_counter()
            if odmr_status < 0:
                mode, is_running = self._mw_device.get_status()
                self.sigOutputStateUpdated.emit(mode, is_running)
                self.unlock()
                return -1

            mode, is_running = self.mw_sweep_on()
            if not is_running:
                self._stop_odmr_counter()
                self.unlock()
                return -1

            self._initialize_ODMR_plots()
            self.sigNextLine.emit()
            return 0

    def continue_odmr_scan(self):
        """ Continue ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self.log.error('Can not start ODMR scan. Logic is already locked.')
                return -1

            self.lock()
            self.stopRequested = False
            self.fc.clear_result()

            self._startTime = time.time() - self.elapsed_time
            self.sigOdmrElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_sweeps)

            if self.saveRawData:
                self.log.info('Raw data saving...')
            else:
                self.log.info('Raw data NOT saved.')

            odmr_status = self._start_odmr_counter()
            if odmr_status < 0:
                mode, is_running = self._mw_device.get_status()
                self.sigOutputStateUpdated.emit(mode, is_running)
                self.unlock()
                return -1

            mode, is_running = self.mw_sweep_on()
            if not is_running:
                self._stop_odmr_counter()
                self.unlock()
                return -1

            self.sigNextLine.emit()
            return 0

    def stop_odmr_scan(self):
        """ Stop the ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
        return 0

    def clear_odmr_data(self):
        """¨Set the option to clear the curret ODMR data.

        The clear operation has to be performed within the method
        _scan_ODMR_line. This method just sets the flag for that. """
        with self.threadlock:
            if self.getState() == 'locked':
                self._clearOdmrData = True
        return

    def _scan_ODMR_line(self):
        """ Scans one line in ODMR

        (from mw_start to mw_stop in steps of mw_step)
        """
        with self.threadlock:
            # If the odmr measurement is not running do nothing
            if self.getState() != 'locked':
                return

            # Stop measurement if stop has been requested
            if self.stopRequested:
                self.stopRequested = False
                self.mw_off()
                self._stop_odmr_counter()
                self.unlock()
                return

            # if during the scan a clearing of the ODMR data is needed:
            if self._clearOdmrData:
                self.elapsed_sweeps = 0
                self._initialize_odmr_plots()
                self._clearOdmrData = False

            # reset position so every line starts from the same frequency
            self.reset_sweep()

            # Acquire count data
            new_counts = self._odmr_counter.count_odmr(length=len(self._mw_frequency_list))
            if new_counts[0] == -1:
                self.stopRequested = True
                self.sigNextLine.emit()
                return

            # Add new count data to mean signal
            self.odmr_plot_y = (self.elapsed_sweeps * self.odmr_plot_y + new_counts) / (
                self.elapsed_sweeps + 1)

            # React on the case, when the number of matrix lines have changed during the scan.
            # Essentially, there are three cases which can happen:
            curr_num_lines = self.odmr_plot_xy.shape[0]
            if curr_num_lines > self.number_of_lines:
                self.odmr_plot_xy = np.vstack(
                    (new_counts, self.odmr_plot_xy[:self.number_of_lines - 1, :]))
            elif curr_num_lines < self.number_of_lines:
                self.odmr_plot_xy = np.vstack((new_counts, self.odmr_plot_xy, np.zeros(
                    [self.number_of_lines - curr_num_lines - 1, new_counts.size])))
            else:
                self.odmr_plot_xy = np.vstack((new_counts, self.odmr_plot_xy[:-1, :]))

            # Save raw data
            #if self.saveRawData:
            #    self.ODMR_raw_data[:, self._odmrscan_counter] = new_counts  # adds the ne odmr line to the overall np.array

            # Update elapsed time/sweeps
            self.elapsed_sweeps += 1
            self.elapsed_time = time.time() - self._startTime
            if self.elapsed_time >= self.run_time:
                self.stopRequested = True

            # Fire update signals
            self.sigOdmrElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_sweeps)
            self.sigOdmrPlotsUpdated.emit(self.odmr_plot_x, self.odmr_plot_y, self.odmr_plot_xy)
            self.sigNextLine.emit()
            return

    def get_fit_functions(self):
        """ Return the names of all ocnfigured fit functions.
        @return list(str): list of fit function names
        """
        return list(self.fc.fit_list)

    def do_fit(self, fit_function=None, x_data=None, y_data=None):
        """ 
        Execute the currently configured fit on the measurement data. Optionally on passed data
        """
        if (x_data is None) or (y_data is None):
            x_data = self.odmr_plot_x
            y_data = self.odmr_plot_y

        if fit_function is not None and isinstance(fit_function, str):
            if fit_function in self.get_fit_functions():
                self.fc.set_current_fit(fit_function)
            else:
                self.fc.set_current_fit('No Fit')
                self.log.warning('Fit function "{0}" not available in ODMRLogic fit container.'
                                 ''.format(fit_function))

        self.odmr_fit_x, self.odmr_fit_y, result = self.fc.do_fit(x_data, y_data)

        self.sigOdmrFitUpdated.emit(self.odmr_fit_x, self.odmr_fit_y,
                                    result.result_str_dict, self.fc.current_fit)
        return

    def save_ODMR_Data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Saves the current ODMR data to a file."""

        # three paths to save the raw data (if desired), the odmr scan data and
        # the matrix data.
        filepath = self._save_logic.get_path_for_module(module_name='ODMR')
        filepath2 = self._save_logic.get_path_for_module(module_name='ODMR')
        filepath3 = self._save_logic.get_path_for_module(module_name='ODMR')

        timestamp = datetime.datetime.now()

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_ODMR_data'
            filelabel2 = tag + '_ODMR_data_matrix'
            filelabel3 = tag + '_ODMR_data_raw'
        else:
            filelabel = 'ODMR_data'
            filelabel2 = 'ODMR_data_matrix'
            filelabel3 = 'ODMR_data_raw'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data2 = OrderedDict()
        data3 = OrderedDict()
        freq_data = self.ODMR_plot_x
        count_data = self.ODMR_plot_y
        matrix_data = self.ODMR_plot_xy  # the data in the matrix plot
        data['frequency values (Hz)'] = np.array(freq_data)
        data['count data (counts/s)'] = np.array(count_data)
        data2['count data (counts/s)'] = np.array(matrix_data)  # saves the raw data used in the matrix NOT all only the size of the matrix

        parameters = OrderedDict()
        parameters['Microwave Power (dBm)'] = self.mw_power
        parameters['Run Time (s)'] = self.run_time
        parameters['Start Frequency (Hz)'] = self.mw_start
        parameters['Stop Frequency (Hz)'] = self.mw_stop
        parameters['Step size (Hz)'] = self.mw_step
        parameters['Clock Frequency (Hz)'] = self.clock_frequency
        parameters['Number of matrix lines (#)'] = self.number_of_lines
        if self.fc.current_fit != 'No Fit':
            parameters['Fit function'] = self.fc.fit_list[self.fc.current_fit]['fit_name']

        # add all fit parameter to the saved data:
        for name, param in self.fc.current_fit_param.items():
            parameters[name] = str(param)

        fig = self.draw_figure(cbar_range=colorscale_range,
                               percentile_range=percentile_range
                               )

        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   timestamp=timestamp,
                                   plotfig=fig)

        self._save_logic.save_data(data2,
                                   filepath=filepath2,
                                   parameters=parameters,
                                   filelabel=filelabel2,
                                   timestamp=timestamp)

        self.log.info('ODMR data saved to:\n{0}'.format(filepath))

        if self.saveRawData:
            raw_data = self.ODMR_raw_data  # array cotaining ALL messured data
            data3['count data'] = np.array(raw_data)  # saves the raw data, ALL of it so keep an eye on performance
            self._save_logic.save_data(data3,
                                       filepath=filepath3,
                                       parameters=parameters,
                                       filelabel=filelabel3,
                                       timestamp=timestamp)

            self.log.info('Raw data succesfully saved.')
        else:
            self.log.info('Raw data is NOT saved')

    def draw_figure(self, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        freq_data = self.ODMR_plot_x
        count_data = self.ODMR_plot_y
        fit_freq_vals = self.ODMR_fit_x
        fit_count_vals = self.ODMR_fit_y
        matrix_data = self.ODMR_plot_xy

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = [np.min(matrix_data), np.max(matrix_data)]

        # Convert cbar_range to numpy array for division in the SI prefix calculation
        cbar_range = np.array(cbar_range)

        prefix = ['', 'k', 'M', 'G', 'T']
        prefix_index = 0

        # Rescale counts data with SI prefix
        while np.max(count_data) > 1000:
            count_data = count_data / 1000
            fit_count_vals = fit_count_vals / 1000
            prefix_index = prefix_index + 1

        counts_prefix = prefix[prefix_index]

        # Rescale frequency data with SI prefix
        prefix_index = 0

        while np.max(freq_data) > 1000:
            freq_data = freq_data / 1000
            fit_freq_vals = fit_freq_vals / 1000
            prefix_index = prefix_index + 1

        mw_prefix = prefix[prefix_index]

        # Rescale matrix counts data with SI prefix
        prefix_index = 0

        while np.max(matrix_data) > 1000:
            matrix_data = matrix_data / 1000
            cbar_range = cbar_range / 1000
            prefix_index = prefix_index + 1

        cbar_prefix = prefix[prefix_index]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, (ax_mean, ax_matrix) = plt.subplots(nrows=2, ncols=1)

        ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
        ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))

        matrixplot = ax_matrix.imshow(matrix_data,
                                      cmap=plt.get_cmap('inferno'),  # reference the right place in qd
                                      origin='lower',
                                      vmin=cbar_range[0],
                                      vmax=cbar_range[1],
                                      extent=[np.min(freq_data),
                                              np.max(freq_data),
                                              0,
                                              self.number_of_lines
                                              ],
                                      aspect='auto',
                                      interpolation='nearest')

        ax_matrix.set_xlabel('Frequency (' + mw_prefix + 'Hz)')
        ax_matrix.set_ylabel('Scan #')

        # Adjust subplots to make room for colorbar
        fig.subplots_adjust(right=0.8)

        # Add colorbar axis to figure
        cbar_ax = fig.add_axes([0.85, 0.15, 0.02, 0.7])

        # Draw colorbar
        cbar = fig.colorbar(matrixplot, cax=cbar_ax)
        cbar.set_label('Fluorescence (' + cbar_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which=u'both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        return fig

    def perform_odmr_measurement(self, freq_start, freq_step, freq_stop, power,
                                 runtime, fit_function='No Fit',
                                 save_after_meas=True, name_tag=''):
        """ An independant method, which can be called by a task with the proper input values
            to perform an odmr measurement.

        @return dict: a parameter container, containing all measurement results
                      of the ODMR measurement.
        """

        while self.getState() != 'idle':
            time.sleep(1)
            print('wait until ready')

        # set all relevant parameter:
        self.mw_start = freq_start
        self.mw_step = freq_step
        self.mw_stop = freq_stop
        self.mw_power = power
        self.run_time = runtime

        # start the scan
        self.start_odmr_scan()

        # check just the state of the optimizer
        while self.getState() != 'idle' and not self.stopRequested:
            time.sleep(1)

        old_fit = self.fc.current_fit
        self.fc.set_current_fit(fit_function)
        self.do_fit()
        meas_param['ODMR frequency start (Hz)'] = self.mw_start
        meas_param['ODMR frequency step (Hz)'] = self.mw_step
        meas_param['ODMR frequency stop (Hz)'] = self.mw_stop
        meas_param['ODMR power (dBm)'] = self.mw_power
        meas_param['ODMR run time (s)'] = self.run_time
        meas_param['ODMR measurement saved separetely'] = save_after_meas

        if save_after_meas:
            timestamp = datetime.datetime.now()
            self.save_ODMR_Data(tag=name_tag)
            meas_param['ODMR measurement saved at time'] = timestamp

        self.fc.set_current_fit(old_fit)
        return meas_param
