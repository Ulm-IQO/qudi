# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic which controls all pulsed measurements.

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
import numpy as np
import time
import datetime
import matplotlib.pyplot as plt

from core.module import Connector, ConfigOption, StatusVar
from core.util.mutex import Mutex
from core.util.network import netobtain
from core.util import units
from logic.generic_logic import GenericLogic


class PulsedMeasurementLogic(GenericLogic):
    """
    This is the Logic class for the control of pulsed measurements.
    """
    _modclass = 'PulsedMeasurementLogic'
    _modtype = 'logic'

    ## declare connectors
    pulseanalysislogic = Connector(interface='PulseAnalysisLogic')
    pulseextractionlogic = Connector(interface='PulseExtractionLogic')
    fitlogic = Connector(interface='FitLogic')
    savelogic = Connector(interface='SaveLogic')
    fastcounter = Connector(interface='FastCounterInterface')
    microwave = Connector(interface='MWInterface')
    pulsegenerator = Connector(interface='PulserInterface')

    # status variables
    __microwave_power = StatusVar(default=-30.0)
    __microwave_freq = StatusVar(default=2870e6)
    __use_ext_microwave = StatusVar(default=False)

    __fast_counter_record_length = StatusVar(default=3.0e-6)
    __fast_counter_binwidth = StatusVar(default=1.0e-9)
    __fast_counter_gates = StatusVar(default=0)

    __timer_interval = StatusVar(default=5)

    # Container to store information about the currently running sequence
    _sequence_information = StatusVar(default={'alternating': False,
                                               'number_of_lasers': 50,
                                               'controlled_variable': np.arange(1, 51)})

    # fourier transform status var:
    zeropad = StatusVar(default=0)
    psd = StatusVar(default=False)
    window = StatusVar(default='none')
    base_corr = StatusVar(default=True)
    save_alt_signal = StatusVar(default=False)

    # signals
    sigMeasurementDataUpdated = QtCore.Signal()
    sigTimerUpdated = QtCore.Signal(float, float)
    sigFitUpdated = QtCore.Signal(str, np.ndarray, np.ndarray, object)
    sigMeasurementStatusUpdated = QtCore.Signal(bool, bool)
    sigPulserRunningUpdated = QtCore.Signal(bool)
    sigExtMicrowaveRunningUpdated = QtCore.Signal(bool)
    sigExtMicrowaveSettingsUpdated = QtCore.Signal(dict)
    sigFastCounterSettingsUpdated = QtCore.Signal(dict)
    sigPulseSequenceSettingsUpdated = QtCore.Signal(dict)
    sigAnalysisSettingsUpdated = QtCore.Signal(dict)
    sigAnalysisMethodsUpdated = QtCore.Signal(dict)
    sigExtractionSettingsUpdated = QtCore.Signal(dict)
    sigExtractionMethodsUpdated = QtCore.Signal(dict)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # timer for measurement
        self.__analysis_timer = None
        self.__start_time = 0
        self.__elapsed_time = 0

        # threading
        self._threadlock = Mutex()

        # measurement data
        self.signal_data = np.empty((2, 0), dtype=float)
        self.signal_alt_data = np.empty((2, 0), dtype=float)
        self.measurement_error = np.empty((2, 0), dtype=float)
        self.laser_data = np.zeros((10, 20), dtype='int64')
        self.raw_data = np.zeros((10, 20), dtype='int64')

        self._saved_raw_data = OrderedDict()  # temporary saved raw data
        self._recalled_raw_data_tag = None  # the currently recalled raw data dict key

        # Paused measurement flag
        self.__is_paused = False

        # for fit:
        self.fc = None  # Fit container
        self.signal_fit_data = np.empty((2, 0), dtype=float)  # The x,y data of the fit result
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Fitting
        self.fc = self._fit_logic.make_fit_container('pulsed', '1d')
        self.fc.set_units(['s', 'arb.u.'])

        # Recall saved status variables
        if 'fits' in self._statusVariables and isinstance(self._statusVariables.get('fits'), dict):
            self.fc.load_from_dict(self._statusVariables['fits'])

        # Hand information containers to extraction and analysis logic
        self.pulseextractionlogic()._sequence_information = self._sequence_information

        # Turn off pulse generator
        self.pulse_generator_off()

        # Check and configure fast counter
        binning_constraints = self.fastcounter().get_constraints()['hardware_binwidth_list']
        if self.fast_counter_binwidth not in binning_constraints:
            self.fast_counter_binwidth = binning_constraints[0]
        if self.fast_counter_record_length <= 0:
            self.fast_counter_record_length = 3e-6
        self.fast_counter_off()
        self.set_fast_counter_settings()

        # Check and configure external microwave
        if self.__use_ext_microwave:
            self.microwave_off()
            self.set_microwave_settings(frequency=self.microwave_freq, power=self.microwave_power,
                                        use_ext_microwave=True)

        # initialize arrays for the measurement data
        self._initialize_data_arrays()

        # recalled saved raw data dict key
        self._recalled_raw_data_tag = None
        return

    def on_deactivate(self):
        """ Deactivate the module properly.
        """

        if self.module_state() == 'locked':
            self.stop_pulsed_measurement()

        self._statusVariables['controlled_vals'] = list(self.controlled_vals)
        if len(self.fc.fit_list) > 0:
            self._statusVariables['fits'] = self.fc.save_to_dict()
        return

    ############################################################################
    # Fast counter control methods and properties
    ############################################################################
    @property
    def fast_counter_settings(self):
        settings_dict = dict()
        settings_dict['bin_width_s'] = float(self.__fast_counter_binwidth)
        settings_dict['record_length_s'] = float(self.__fast_counter_record_length)
        settings_dict['number_of_gates'] = int(self.__fast_counter_gates)
        return settings_dict

    @fast_counter_settings.setter
    def fast_counter_settings(self, settings_dict):
        if isinstance(settings_dict, dict):
            self.set_fast_counter_settings(settings_dict)
        return

    @property
    def fastcounter_constraints(self):
        return self.fastcounter().get_constraints()

    def set_fast_counter_settings(self, settings_dict=None, **kwargs):
        """
        Either accept a settings dictionary as positional argument or keyword arguments.
        If both are present both are being used by updating the settings_dict with kwargs.
        The keyword arguments take precedence over the items in settings_dict if there are
        conflicting names.

        @param settings_dict:
        @param kwargs:
        @return:
        """
        # Check if fast counter is running and do nothing if that is the case
        counter_status = self.fastcounter().get_status()
        if not counter_status >= 2 and not counter_status < 0:
            # Determine complete settings dictionary
            if not isinstance(settings_dict, dict):
                settings_dict = kwargs
            else:
                settings_dict.update(kwargs)

            # Set parameters if present
            if 'bin_width_s' in settings_dict:
                self.__fast_counter_binwidth = float(settings_dict['bin_width_s'])
            if 'record_length_s' in settings_dict:
                self.__fast_counter_record_length = float(settings_dict['record_length_s'])
            if 'number_of_gates' in settings_dict:
                if self.fastcounter().is_gated():
                    self.__fast_counter_gates = int(settings_dict['number_of_gates'])
                else:
                    self.__fast_counter_gates = 0

            # Apply the settings to hardware
            self.__fast_counter_binwidth, \
            self.__fast_counter_record_length, \
            self.__fast_counter_gates = self.fastcounter().configure(self.__fast_counter_binwidth,
                                                                     self.__fast_counter_record_length,
                                                                     self.__fast_counter_gates)

            # Make sure the analysis and extraction logic take the correct binning into account
            self.pulseanalysislogic().fast_counter_binwidth = self.__fast_counter_binwidth
            self.pulseextractionlogic().fast_counter_binwidth = self.__fast_counter_binwidth
        else:
            self.log.warning('Fast counter is not idle (status: {0}).\n'
                             'Unable to apply new settings.'.format(counter_status))

        # emit update signal for master (GUI or other logic module)
        self.sigFastCounterSettingsUpdated.emit(
            {'bin_width_s': self.__fast_counter_binwidth,
             'record_length_s': self.__fast_counter_record_length,
             'number_of_gates': self.__fast_counter_gates})
        return self.__fast_counter_binwidth, self.__fast_counter_record_length, self.__fast_counter_gates

    def fast_counter_on(self):
        """Switching on the fast counter

        @return int: error code (0:OK, -1:error)
        """
        return self.fastcounter().start_measure()

    def fast_counter_off(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        return self.fastcounter().stop_measure()

    def toggle_fast_counter(self, switch_on):
        """
        """
        if not isinstance(switch_on, bool):
            return -1

        if switch_on:
            err = self.fast_counter_on()
        else:
            err = self.fast_counter_off()
        return err

    def fast_counter_pause(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        return self.fastcounter().pause_measure()

    def fast_counter_continue(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        return self.fastcounter().continue_measure()

    def fast_counter_pause_continue(self, continue_counter):
        """
        """
        if not isinstance(continue_counter, bool):
            return -1

        if continue_counter:
            err = self.fast_counter_continue()
        else:
            err = self.fast_counter_pause()
        return err
    ############################################################################

    ############################################################################
    # External microwave control methods
    ############################################################################
    @property
    def ext_microwave_settings(self):
        settings_dict = dict()
        settings_dict['power'] = float(self.__microwave_power)
        settings_dict['frequency'] = float(self.__microwave_freq)
        settings_dict['use_ext_microwave'] = bool(self.__use_ext_microwave)
        return settings_dict

    @ext_microwave_settings.setter
    def ext_microwave_settings(self, settings_dict):
        if isinstance(settings_dict, dict):
            self.set_fast_counter_settings(settings_dict)
        return

    def microwave_on(self):
        """
        Turns the external (CW) microwave output on.

        :return int: error code (0:OK, -1:error)
        """
        err = self.microwave().cw_on()
        if err < 0:
            self.log.error('Failed to turn on external CW microwave output.')
        self.sigExtMicrowaveRunningUpdated.emit(self.microwave().get_status()[1])
        return err

    def microwave_off(self):
        """
        Turns the external (CW) microwave output off.

        :return int: error code (0:OK, -1:error)
        """
        err = self.microwave().off()
        if err < 0:
            self.log.error('Failed to turn off external CW microwave output.')
        self.sigExtMicrowaveRunningUpdated.emit(self.microwave().get_status()[1])
        return err

    def toggle_microwave(self, switch_on):
        """
        Turn the external microwave output on/off.

        :param switch_on: bool, turn microwave on (True) or off (False)
        :return int: error code (0:OK, -1:error)
        """
        if not isinstance(switch_on, bool):
            return -1

        if switch_on:
            err = self.microwave_on()
        else:
            err = self.microwave_off()
        return err

    def set_microwave_settings(self, settings_dict=None, **kwargs):
        """
        Apply new settings to the external microwave device.
        Either accept a settings dictionary as positional argument or keyword arguments.
        If both are present both are being used by updating the settings_dict with kwargs.
        The keyword arguments take precedence over the items in settings_dict if there are
        conflicting names.

        @param settings_dict:
        @param kwargs:
        @return:
        """
        # Check if microwave is running and do nothing if that is the case
        if self.fastcounter().get_status()[1]:
            self.log.warning('Microwave device is running.\nUnable to apply new settings.')
        else:
            # Determine complete settings dictionary
            if not isinstance(settings_dict, dict):
                settings_dict = kwargs
            else:
                settings_dict.update(kwargs)

            # Set parameters if present
            if 'power' in settings_dict:
                self.__microwave_power = float(settings_dict['power'])
            if 'frequency' in settings_dict:
                self.__microwave_freq = float(settings_dict['frequency'])
            if 'use_ext_microwave' in settings_dict:
                self.__use_ext_microwave = bool(settings_dict['use_ext_microwave'])

            if self.__use_ext_microwave:
                # Apply the settings to hardware
                self.__microwave_freq, \
                self.__microwave_power, \
                dummy = self.microwave().set_cw(frequency=self.__microwave_freq,
                                                power=self.__microwave_power)

        # emit update signal for master (GUI or other logic module)
        self.sigExtMicrowaveSettingsUpdated.emit({'power': self.__fast_counter_binwidth,
                                                  'frequency': self.__fast_counter_record_length,
                                                  'use_ext_microwave': self.__fast_counter_gates})
        return self.__microwave_freq, self.__microwave_power, self.__use_ext_microwave
    ############################################################################

    ############################################################################
    # Pulse generator control methods
    ############################################################################
    def pulse_generator_on(self):
        """Switching on the pulse generator. """
        err = self.pulsegenerator().pulser_on()
        if err < 0:
            self.log.error('Failed to turn on pulse generator output.')
            self.sigPulserRunningUpdated.emit(False)
        else:
            self.sigPulserRunningUpdated.emit(True)
        return err

    def pulse_generator_off(self):
        """Switching off the pulse generator. """
        err = self.pulsegenerator().pulser_off()
        if err < 0:
            self.log.error('Failed to turn off pulse generator output.')
            self.sigPulserRunningUpdated.emit(True)
        else:
            self.sigPulserRunningUpdated.emit(False)
        return err

    def toggle_pulse_generator(self, switch_on):
        """
        Switch the pulse generator on or off.

        :param switch_on: bool, turn the pulse generator on (True) or off (False)
        :return int: error code (0: OK, -1: error)
        """
        if not isinstance(switch_on, bool):
            return -1

        if switch_on:
            err = self.pulse_generator_on()
        else:
            err = self.pulse_generator_off()
        return err
    ############################################################################

    ############################################################################
    # Measurement control methods
    ############################################################################
    def start_pulsed_measurement(self, stashed_raw_data_tag=''):
        """Start the analysis loop."""
        #FIXME: Describe the idea of how the measurement is intended to be run
        #       and how the used thread principle was used in this method (or
        #       will be use in another method).
        self.sigMeasurementRunningUpdated.emit(True, False)
        with self.threadlock:
            if self.module_state() == 'idle':
                # Lock module state
                self.module_state.lock()

                # Clear previous fits
                self.fc.clear_result()

                # initialize data arrays
                self._initialize_data_arrays()

                # recall stashed raw data
                if stashed_raw_data_tag in self._saved_raw_data:
                    self._recalled_raw_data_tag = stashed_raw_data_tag
                    self.log.info('Starting pulsed measurement with stashed raw data "{0}".'
                                  ''.format(stashed_raw_data_tag))
                else:
                    self._recalled_raw_data_tag = None

                # start microwave source
                if self.__use_ext_microwave:
                    self.microwave_on()
                # start fast counter
                self.fast_counter_on()
                # start pulse generator
                self.pulse_generator_on()

                # initialize analysis_timer
                self.__elapsed_time = 0.0
                self.sigTimerUpdated.emit(self.__elapsed_time, self.__timer_interval)
                self.__initialize_timer()

                # Set starting time and start timer (if present)
                self.__start_time = time.time()
                if self.__analysis_timer is not None:
                    self.__analysis_timer.start()

                # Set measurement paused flag
                self.__is_paused = False
            else:
                self.log.warning('Unable to start pulsed measurement. Measurement already running.')
        return

    def stop_pulsed_measurement(self, stash_raw_data_tag=''):
        """
        Stop the measurement
        """
        # Get raw data and analyze it a last time just before stopping the measurement.
        self._pulsed_analysis_loop()
        with self.threadlock:
            if self.module_state() == 'locked':
                # stopping, disconnecting and removing the timer
                self.__remove_timer()

                # Turn off fast counter
                self.fast_counter_off()
                # Turn off pulse generator
                self.pulse_generator_off()
                # Turn off microwave source
                if self.__use_ext_microwave:
                    self.microwave_off()

                # stash raw data if requested
                if stash_raw_data_tag:
                    self.log.info('Raw data saved with tag "{0}" to continue measurement at a '
                                  'later point.')
                    self._saved_raw_data[stash_raw_data_tag] = self.raw_data.copy()
                self._recalled_raw_data_tag = None

                # Set measurement paused flag
                self.__is_paused = False

                self.module_state.unlock()
                self.sigMeasurementRunningUpdated.emit(False, False)
        return

    def pause_pulsed_measurement(self):
        """
        Pauses the measurement
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                # pausing the timer
                if self.__analysis_timer is not None:
                    self.__analysis_timer.stop()

                self.fast_counter_pause()
                self.pulse_generator_off()
                if self.__use_ext_microwave:
                    self.microwave_off()

                # Set measurement paused flag
                self.__is_paused = True

                self.sigMeasurementRunningUpdated.emit(True, True)
            else:
                self.log.warning('Unable to pause pulsed measurement. No measurement running.')
                self.sigMeasurementRunningUpdated.emit(False, False)
        return

    def continue_pulsed_measurement(self):
        """
        Continues the measurement
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                if self.__use_ext_microwave:
                    self.microwave_on()
                self.fast_counter_continue()
                self.pulse_generator_on()

                # un-pausing the timer
                if self.__analysis_timer is not None:
                    self.__analysis_timer.start()

                # Set measurement paused flag
                self.__is_paused = False

                self.sigMeasurementRunningUpdated.emit(True, False)
            else:
                self.log.warning('Unable to continue pulsed measurement. No measurement running.')
                self.sigMeasurementRunningUpdated.emit(False, False)
        return

    def set_timer_interval(self, interval):
        """
        Change the interval of the measurement analysis timer

        @param int interval: Interval of the timer in s
        """
        with self.threadlock:
            self.__timer_interval = interval
            if self.__analysis_timer is not None:
                if self.__timer_interval > 0:
                    self.__analysis_timer.setInterval(int(1000. * self.__timer_interval))
                else:
                    self.__remove_timer()
            elif self.__timer_interval > 0 and self.module_state() == 'locked':
                self.__initialize_timer()
                if not self.__is_paused:
                    self.__analysis_timer.start()
            self.sigTimerUpdated.emit(self.__elapsed_time, self.__timer_interval)
        return

    def manually_pull_data(self):
        """ Analyse and display the data
        """
        if self.module_state() == 'locked':
            self._pulsed_analysis_loop()
        return

    def _pulsed_analysis_loop(self):
        """ Acquires laser pulses from fast counter,
            calculates fluorescence signal and creates plots.
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                # Update elapsed time
                self.__elapsed_time = time.time() - self.start_time

                # Get counter raw data (including recalled raw data from previous measurement)
                self.raw_data = self.__get_raw_data()

                # extract laser pulses from raw data
                return_dict = self.pulseextractionlogic().extract_laser_pulses(
                    self.raw_data,
                    self.fastcounter.is_gated())
                self.laser_data = return_dict['laser_counts_arr']

                # analyze pulses and get data points for signal array. Also check if extraction
                # worked (non-zero array returned).
                if np.sum(self.laser_data) < 1:
                    tmp_signal = np.zeros(self.laser_data.shape[0])
                    tmp_error = np.zeros(self.laser_data.shape[0])
                else:
                    tmp_signal, tmp_error = self.pulseanalysislogic().analyze_data(self.laser_data)

                # exclude laser pulses to ignore
                if len(self._sequence_information['laser_ignore_list']) > 0:
                    ignore_indices = self._sequence_information['laser_ignore_list']
                    if -1 in ignore_indices:
                        ignore_indices[ignore_indices.index(-1)] = len(ignore_indices) - 1
                    tmp_signal = np.delete(tmp_signal, ignore_indices)
                    tmp_error = np.delete(tmp_error, ignore_indices)

                # order data according to alternating flag
                if self._sequence_information['alternating']:
                    self.signal_data[1] = tmp_signal[::2]
                    self.signal_data[2] = tmp_signal[1::2]
                    self.measurement_error[1] = tmp_error[::2]
                    self.measurement_error[2] = tmp_error[1::2]
                else:
                    self.signal_data[1] = tmp_signal
                    self.measurement_error[1] = tmp_error

                # Compute alternative data array from signal
                self._compute_alt_data()

            # emit signals
            self.sigElapsedTimeUpdated.emit(self.__elapsed_time, self.__timer_interval)
            self.sigMeasurementDataUpdated.emit()
            return

    def __initialize_timer(self):
        """
        Initializes the QTimer controlling the measurement analysis loop.
        No QTimer will be created if self.__timer_interval <= 0.
        """
        if self.__timer_interval > 0:
            self.__analysis_timer = QtCore.QTimer()
            self.__analysis_timer.setSingleShot(False)
            self.__analysis_timer.setInterval(int(1000. * self.__timer_interval))
            self.__analysis_timer.timeout.connect(self._pulsed_analysis_loop,
                                                  QtCore.Qt.QueuedConnection)
        else:
            self.__analysis_timer = None
        return

    def __remove_timer(self):
        """
        Disconnects and removes the QTimer controlling the measurement analysis loop.
        """
        if self.__analysis_timer is not None:
            self.__analysis_timer.stop()
            self.__analysis_timer.timeout.disconnect()
            self.__analysis_timer = None
        return

    def __get_raw_data(self):
        """
        Get the raw count data from the fast counting hardware and perform sanity checks.
        Also add recalled raw data to the newly received data.
        :return numpy.ndarray: The count data (1D for ungated, 2D for gated counter)
        """
        # get raw data from fast counter
        fc_data = netobtain(self.fastcounter().get_data_trace())

        # add old raw data from previous measurements if necessary
        if self._saved_raw_data.get(self._recalled_raw_data_tag) is not None:
            self.log.info('Found old saved raw data with tag "{0}".'
                          ''.format(self._recalled_raw_data_tag))
            if np.sum(fc_data) < 1:
                self.log.warning('Only zeros received from fast counter!\n'
                                 'Using recalled raw data only.')
                fc_data = self._saved_raw_data[self._recalled_raw_data_tag]
            elif self._saved_raw_data[self._recalled_raw_data_tag].shape == fc_data.shape:
                self.log.debug('Recalled raw data has the same shape as current data.')
                fc_data = self._saved_raw_data[self._recalled_raw_data_tag] + fc_data
            else:
                self.log.warning('Recalled raw data has not the same shape as current data.'
                                 '\nDid NOT add recalled raw data to current time trace.')
        elif np.sum(fc_data) < 1:
            self.log.warning('Only zeros received from fast counter!')
            fc_data = np.zeros(fc_data.shape, dtype='int64')
        return fc_data

    # FIXME: Revise everything below
    def set_pulse_sequence_properties(self, controlled_vals, number_of_lasers,
                                      laser_ignore_list, is_alternating):
        if len(controlled_vals) < 1:
            self.log.error('Tried to set empty controlled variables array. This can not work.')
            self.sigPulseSequenceSettingsUpdated.emit(self.controlled_vals,
                                                      self.number_of_lasers,
                                                      self.laser_ignore_list, self.alternating)
            return self.controlled_vals, self.number_of_lasers, \
                   self.laser_ignore_list, self.alternating

        if is_alternating and len(controlled_vals) != (number_of_lasers - len(laser_ignore_list))/2:
            self.log.warning('Number of controlled variable ticks ({0}) does not match the number '
                             'of laser pulses to analyze ({1}).\nSetting number of lasers to {2}.'
                             ''.format(len(controlled_vals),
                                       (number_of_lasers - len(laser_ignore_list))/2,
                                       len(controlled_vals) * 2 + len(laser_ignore_list)))
            number_of_lasers = len(controlled_vals) * 2 + len(laser_ignore_list)
        elif not is_alternating and len(controlled_vals) != (number_of_lasers - len(laser_ignore_list)):
            self.log.warning('Number of controlled variable ticks ({0}) does not match the number '
                             'of laser pulses to analyze ({1}).\nSetting number of lasers to {2}.'
                             ''.format(len(controlled_vals),
                                       number_of_lasers - len(laser_ignore_list),
                                       len(controlled_vals) + len(laser_ignore_list)))
            number_of_lasers = len(controlled_vals) + len(laser_ignore_list)

        self.controlled_vals = controlled_vals
        self.number_of_lasers = number_of_lasers
        self._pulse_extraction_logic.number_of_lasers = number_of_lasers
        self.laser_ignore_list = laser_ignore_list
        self.alternating = is_alternating
        if self._fast_counter_device.is_gated():
            self.set_fast_counter_settings(self.fast_counter_binwidth,
                                           self.fast_counter_record_length)
        # emit update signal for master (GUI or other logic module)
        self.sigPulseSequenceSettingsUpdated.emit(self.controlled_vals,
                                                  self.number_of_lasers,
                                                  self.laser_ignore_list, self.alternating)
        return self.controlled_vals, self.number_of_lasers, \
               self.laser_ignore_list, self.alternating
    ############################################################################

    def analysis_settings_changed(self, analysis_settings):
        """

        @param dict analysis_settings:
        @return:
        """
        with self.threadlock:
            for parameter in analysis_settings:
                self._pulse_analysis_logic.analysis_settings[parameter] = analysis_settings[parameter]

            # forward to the GUI the exact timing
            if 'signal_start_s' in analysis_settings:
                analysis_settings['signal_start_s'] = round(analysis_settings['signal_start_s'] / self.fast_counter_binwidth) * self.fast_counter_binwidth
            if 'signal_end_s' in analysis_settings:
                analysis_settings['signal_end_s'] = round(analysis_settings['signal_end_s'] / self.fast_counter_binwidth) * self.fast_counter_binwidth
            if 'norm_start_s' in analysis_settings:
                analysis_settings['norm_start_s'] = round(analysis_settings['norm_start_s'] / self.fast_counter_binwidth) * self.fast_counter_binwidth
            if 'norm_end_s' in analysis_settings:
                analysis_settings['norm_end_s'] = round(analysis_settings['norm_end_s'] / self.fast_counter_binwidth) * self.fast_counter_binwidth
            self.sigAnalysisSettingsUpdated.emit(analysis_settings)

        return analysis_settings

    def extraction_settings_changed(self, extraction_settings):
        """

        @param dict extraction_settings:
        @return:
        """
        with self.threadlock:
            for parameter in extraction_settings:
                self._pulse_extraction_logic.extraction_settings[parameter] = extraction_settings[parameter]
            self.sigExtractionSettingsUpdated.emit(extraction_settings)
        return extraction_settings

    def _initialize_data_arrays(self):
        """
        Initializing the signal, error, laser and raw data arrays.
        """
        self.signal_plot_x = self.controlled_vals
        self.signal_plot_y = np.zeros(len(self.controlled_vals))
        self.signal_plot_y2 = np.zeros(len(self.controlled_vals))
        self.measuring_error_plot_y = np.zeros(len(self.controlled_vals), dtype=float)
        self.measuring_error_plot_y2 = np.zeros(len(self.controlled_vals), dtype=float)
        number_of_bins = int(self.fast_counter_record_length / self.fast_counter_binwidth)
        self.laser_plot_x = np.arange(1, number_of_bins + 1, dtype=int) * self.fast_counter_binwidth
        self.laser_plot_y = np.zeros(number_of_bins, dtype=int)
        self.signal_second_plot_x = self.controlled_vals
        self.signal_second_plot_y = np.zeros(len(self.controlled_vals))
        self.signal_second_plot_y2 = np.zeros(len(self.controlled_vals))

        self.sigSignalDataUpdated.emit(self.signal_plot_x, self.signal_plot_y, self.signal_plot_y2,
                                       self.measuring_error_plot_y, self.measuring_error_plot_y2,
                                       self.signal_second_plot_x, self.signal_second_plot_y, self.signal_second_plot_y2)
        self.sigLaserDataUpdated.emit(self.laser_plot_x, self.laser_plot_y)
        return

    def save_measurement_data(self, controlled_val_unit='arb.u.', tag=None,
                              with_error=True, save_second_plot=None):
        """ Prepare data to be saved and create a proper plot of the data

        @param str controlled_val_unit: unit of the x axis of the plot
        @param str tag: a filetag which will be included in the filename
        @param bool with_error: select whether errors should be saved/plotted
        @param bool save_second_plot: select wether the second plot (FFT, diff) is saved

        @return str: filepath where data were saved
        """

        filepath = self._save_logic.get_path_for_module('PulsedMeasurement')
        timestamp = datetime.datetime.now()

        #####################################################################
        ####                Save extracted laser pulses                  ####
        #####################################################################

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_laser_pulses'
        else:
            filelabel = 'laser_pulses'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        laser_trace = self.laser_data.astype(int)
        data['Signal (counts)\nLaser'.format()] = laser_trace.transpose()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Bin size (s)'] = self.fast_counter_binwidth
        parameters['laser length (s)'] = self.laser_plot_x.size

        self._save_logic.save_data(data,
                                   timestamp=timestamp,
                                   parameters=parameters,
                                   filepath=filepath,
                                   filelabel=filelabel,
                                   fmt='%d',
                                   delimiter='\t')

        #####################################################################
        ####                Save measurement data                        ####
        #####################################################################

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_pulsed_measurement'
        else:
            filelabel = 'pulsed_measurement'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data['Controlled variable (' + controlled_val_unit + ')'] = self.signal_plot_x
        data['Signal (norm.)'] = self.signal_plot_y

        if self.alternating:
            data['Signal2 (norm.)'] = self.signal_plot_y2
        if with_error:
            data['Error (norm.)'] = self.measuring_error_plot_y
            if self.alternating:
                data['Error2 (norm.)'] = self.measuring_error_plot_y2

        # write the parameters:
        parameters = OrderedDict()
        parameters['approx. measurement time (s)'] = self.elapsed_time
        parameters['Bin size (s)'] = self.fast_counter_binwidth
        parameters['Number of laser pulses'] = self.number_of_lasers
        parameters['Signal start (bin)'] = self._pulse_analysis_logic.signal_start_bin
        parameters['Signal end (bin)'] = self._pulse_analysis_logic.signal_end_bin
        parameters['Normalization start (bin)'] = self._pulse_analysis_logic.norm_start_bin
        parameters['Normalization end (bin)'] = self._pulse_analysis_logic.norm_end_bin
        parameters['Extraction_method'] = self._pulse_extraction_logic.extraction_settings['current_method']
        if self._pulse_extraction_logic.extraction_settings['current_method'] == 'conv_deriv':
            parameters['Standard deviation of gaussian convolution'] = \
                self._pulse_extraction_logic.extraction_settings['conv_std_dev']
        if self._pulse_extraction_logic.extraction_settings['current_method'] == 'threshold':
            parameters['Count threshold'] = self._pulse_extraction_logic.extraction_settings['count_threshold']
            parameters['threshold_tolerance'] = self._pulse_extraction_logic.extraction_settings['threshold_tolerance']
            parameters['min_laser_length'] = self._pulse_extraction_logic.extraction_settings['min_laser_length']
        # Prepare the figure to save as a "data thumbnail"
        plt.style.use(self._save_logic.mpl_qd_style)

        # extract the possible colors from the colorscheme:
        prop_cycle = self._save_logic.mpl_qd_style['axes.prop_cycle']
        colors = {}
        for i, color_setting in enumerate(prop_cycle):
            colors[i] = color_setting['color']

        # scale the x_axis for plotting
        max_val = np.max(self.signal_plot_x)
        scaled_float = units.ScaledFloat(max_val)
        counts_prefix = scaled_float.scale
        x_axis_scaled = self.signal_plot_x / scaled_float.scale_val

        # if nothing is specified, then take the local settings
        if save_second_plot is None:
            save_second_plot = self.save_second_plot

        # Create the figure object
        if save_second_plot:
            fig, (ax1, ax2) = plt.subplots(2, 1)
        else:
            fig, ax1 = plt.subplots()

        if with_error:
            ax1.errorbar(x=x_axis_scaled, y=self.signal_plot_y,
                         yerr=self.measuring_error_plot_y, fmt='-o',
                         linestyle=':', linewidth=0.5, color=colors[0],
                         ecolor=colors[1], capsize=3, capthick=0.9,
                         elinewidth=1.2, label='data trace 1')

            if self.alternating:
                ax1.errorbar(x=x_axis_scaled, y=self.signal_plot_y2,
                             yerr=self.measuring_error_plot_y2, fmt='-D',
                             linestyle=':', linewidth=0.5, color=colors[3],
                             ecolor=colors[4],  capsize=3, capthick=0.7,
                             elinewidth=1.2, label='data trace 2')

        else:
            ax1.plot(x_axis_scaled, self.signal_plot_y, '-o', color=colors[0],
                     linestyle=':', linewidth=0.5, label='data trace 1')

            if self.alternating:
                ax1.plot(x_axis_scaled, self.signal_plot_y2, '-o',
                         color=colors[3], linestyle=':', linewidth=0.5,
                         label='data trace 2')

        # Do not include fit curve if there is no fit calculated.
        if max(self.signal_plot_y_fit) > 0:
            x_axis_fit_scaled = self.signal_plot_x_fit / scaled_float.scale_val
            ax1.plot(x_axis_fit_scaled, self.signal_plot_y_fit,
                     color=colors[2], marker='None', linewidth=1.5,
                     label='fit: {0}'.format(self.fc.current_fit))

            # add then the fit result to the plot:

            # Parameters for the text plot:
            # The position of the text annotation is controlled with the
            # relative offset in x direction and the relative length factor
            # rel_len_fac of the longest entry in one column
            rel_offset = 0.02
            rel_len_fac = 0.011
            entries_per_col = 24

            # create the formatted fit text:
            if hasattr(self.fc.current_fit_result, 'result_str_dict'):
                fit_res = units.create_formatted_output(self.fc.current_fit_result.result_str_dict)
            else:
                self.log.warning('The fit container does not contain any data '
                                 'from the fit! Apply the fit once again.')
                fit_res = ''
            # do reverse processing to get each entry in a list
            entry_list = fit_res.split('\n')
            # slice the entry_list in entries_per_col
            chunks = [entry_list[x:x+entries_per_col] for x in range(0, len(entry_list), entries_per_col)]

            is_first_column = True  # first entry should contain header or \n
            shift = rel_offset

            for column in chunks:

                max_length = max(column, key=len)   # get the longest entry
                column_text = ''

                for entry in column:
                    column_text += entry + '\n'

                column_text = column_text[:-1]  # remove the last new line

                heading = ''
                if is_first_column:
                    heading = 'Fit results:'

                column_text = heading + '\n' + column_text

                ax1.text(1.00 + shift, 0.99, column_text,
                         verticalalignment='top',
                         horizontalalignment='left',
                         transform=ax1.transAxes,
                         fontsize=12)

                # the shift in position of the text is a linear function
                # which depends on the longest entry in the column
                shift += rel_len_fac * len(max_length)

                is_first_column = False

        # handle the save of the fourier Transform
        if save_second_plot:

            # scale the x_axis for plotting
            max_val = np.max(self.signal_second_plot_x)
            scaled_float = units.ScaledFloat(max_val)
            x_axis_prefix = scaled_float.scale
            x_axis_ft_scaled = self.signal_second_plot_x / scaled_float.scale_val

            # since no ft units are provided, make a small work around:
            if controlled_val_unit == 's':
                inverse_cont_var = 'Hz'
            elif controlled_val_unit == 'Hz':
                inverse_cont_var = 's'
            else:
                inverse_cont_var = '(1/{0})'.format(controlled_val_unit)

            if self.second_plot_type == 'Delta':
                x_axis_ft_label = 'controlled variable (' + controlled_val_unit + ')'
                y_axis_ft_label = 'norm. sig (arb. u.)'
                ft_label = ''
            else:
                x_axis_ft_label = 'Fourier Transformed controlled variable (' + x_axis_prefix + inverse_cont_var + ')'
                y_axis_ft_label = 'Fourier amplitude (arb. u.)'
                ft_label = 'FT of data trace 1'

            ax2.plot(x_axis_ft_scaled, self.signal_second_plot_y, '-o',
                     linestyle=':', linewidth=0.5, color=colors[0],
                     label=ft_label)

            ax2.set_xlabel(x_axis_ft_label)
            ax2.set_ylabel(y_axis_ft_label)
            ax2.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2,
                       mode="expand", borderaxespad=0.)

        #FIXME: no fit plot for the alternating graph, use for that graph colors[5]

        ax1.set_xlabel('controlled variable (' + counts_prefix + controlled_val_unit + ')')
        ax1.set_ylabel('norm. sig (arb.u.)')

        fig.tight_layout()
        ax1.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2,
                   mode="expand", borderaxespad=0.)
        # plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2,
        #            mode="expand", borderaxespad=0.)

        self._save_logic.save_data(data, timestamp=timestamp,
                                   parameters=parameters, fmt='%.15e',
                                   filepath=filepath, filelabel=filelabel,
                                   delimiter='\t', plotfig=fig)

        #####################################################################
        ####                Save raw data timetrace                      ####
        #####################################################################

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_raw_timetrace'
        else:
            filelabel = 'raw_timetrace'

        # prepare the data in a dict or in an OrderedDict:

        data = OrderedDict()
        raw_trace = self.raw_data.astype(int)
        data['Signal (counts)'] = raw_trace.transpose()
        # write the parameters:
        parameters = OrderedDict()
        parameters['Is counter gated?'] = self._fast_counter_device.is_gated()
        parameters['Is alternating?'] = self.alternating
        parameters['Bin size (s)'] = self.fast_counter_binwidth
        parameters['Number of laser pulses'] = self.number_of_lasers
        parameters['laser length (s)'] = self.laser_plot_x.size
        parameters['Controlled variable values'] = list(self.controlled_vals)

        self._save_logic.save_data(data, timestamp=timestamp,
                                   parameters=parameters, fmt='%d',
                                   filepath=filepath, filelabel=filelabel,
                                   delimiter='\t')
        return filepath

    def _compute_second_plot(self):
        """ Computing the fourier transform of the data. """

        if self.second_plot_type == 'Delta':
            self.signal_second_plot_x = self.signal_plot_x
            self.signal_second_plot_y = self.signal_plot_y - self.signal_plot_y2
            self.signal_second_plot_y2 = self.signal_plot_y2 - self.signal_plot_y
        else:
            # Do sanity checks:
            if len(self.signal_plot_x) < 2:
                self.log.debug('FFT of measurement could not be calculated. Only '
                               'one data point.')
                self.signal_second_plot_x = np.zeros(1)
                self.signal_second_plot_y = np.zeros(1)
                self.signal_second_plot_y2 = np.zeros(1)
                return

            if self.alternating:
                x_val_dummy, self.signal_second_plot_y2 = units.compute_ft(
                    self.signal_plot_x,
                    self.signal_plot_y2,
                    zeropad_num=0)

            self.signal_second_plot_x, self.signal_second_plot_y = units.compute_ft(
                self.signal_plot_x,
                self.signal_plot_y,
                zeropad_num=self.zeropad,
                window=self.window,
                base_corr=self.base_corr,
                psd=self.psd)
        return


    def do_fit(self, fit_method, x_data=None, y_data=None):
        """Performs the chosen fit on the measured data.

        @param string fit_method: name of the chosen fit method

        @return float array pulsed_fit_x: Array containing the x-values of the fit
        @return float array pulsed_fit_y: Array containing the y-values of the fit
        @return dict fit_result: a dictionary containing the fit result
        """

        # Set current fit
        self.fc.set_current_fit(fit_method)

        if x_data is None or y_data is None:
            x_data = self.signal_plot_x
            y_data = self.signal_plot_y

        self.signal_plot_x_fit, self.signal_plot_y_fit, result = self.fc.do_fit(x_data, y_data)

        fit_name = self.fc.current_fit
        fit_result = self.fc.current_fit_result
        fit_param = self.fc.current_fit_param

        self.sigFitUpdated.emit(fit_name, self.signal_plot_x_fit, self.signal_plot_y_fit,
                                fit_result)

        return self.signal_plot_x_fit, self.signal_plot_y_fit, fit_result
