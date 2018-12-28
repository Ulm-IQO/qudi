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
import copy
import time
import datetime
import matplotlib.pyplot as plt

from core.module import Connector, ConfigOption, StatusVar
from core.util.mutex import Mutex
from core.util.network import netobtain
from core.util import units
from logic.generic_logic import GenericLogic
from logic.pulsed.pulse_extractor import PulseExtractor
from logic.pulsed.pulse_analyzer import PulseAnalyzer


class PulsedMeasurementLogic(GenericLogic):
    """
    This is the Logic class for the control of pulsed measurements.
    """
    _modclass = 'PulsedMeasurementLogic'
    _modtype = 'logic'

    ## declare connectors
    fitlogic = Connector(interface='FitLogic')
    savelogic = Connector(interface='SaveLogic')
    fastcounter = Connector(interface='FastCounterInterface')
    microwave = Connector(interface='MWInterface')
    pulsegenerator = Connector(interface='PulserInterface')

    # Config options
    # Optional additional paths to import from
    extraction_import_path = ConfigOption(name='additional_extraction_path', default=None)
    analysis_import_path = ConfigOption(name='additional_analysis_path', default=None)
    # Optional file type descriptor for saving raw data to file
    _raw_data_save_type = ConfigOption(name='raw_data_save_type', default='text')

    # status variables
    # ext. microwave settings
    __microwave_power = StatusVar(default=-30.0)
    __microwave_freq = StatusVar(default=2870e6)
    __use_ext_microwave = StatusVar(default=False)

    # fast counter settings
    __fast_counter_record_length = StatusVar(default=3.0e-6)
    __fast_counter_binwidth = StatusVar(default=1.0e-9)
    __fast_counter_gates = StatusVar(default=0)

    # measurement timer settings
    __timer_interval = StatusVar(default=5)

    # Pulsed measurement settings
    _invoke_settings_from_sequence = StatusVar(default=False)
    _number_of_lasers = StatusVar(default=50)
    _controlled_variable = StatusVar(default=list(range(50)))
    _alternating = StatusVar(default=False)
    _laser_ignore_list = StatusVar(default=list())
    _data_units = StatusVar(default=('s', ''))
    _data_labels = StatusVar(default=('Tau', 'Signal'))

    # PulseExtractor settings
    extraction_parameters = StatusVar(default=None)
    analysis_parameters = StatusVar(default=None)

    # Container to store measurement information about the currently loaded sequence
    _measurement_information = StatusVar(default=dict())
    # Container to store information about the sampled waveform/sequence currently loaded
    _sampling_information = StatusVar(default=dict())

    # alternative signal computation settings:
    _alternative_data_type = StatusVar(default=None)
    zeropad = StatusVar(default=0)
    psd = StatusVar(default=False)
    window = StatusVar(default='none')
    base_corr = StatusVar(default=True)

    # notification signals for master module (i.e. GUI)
    sigMeasurementDataUpdated = QtCore.Signal()
    sigTimerUpdated = QtCore.Signal(float, int, float)
    sigFitUpdated = QtCore.Signal(str, np.ndarray, object, bool)
    sigMeasurementStatusUpdated = QtCore.Signal(bool, bool)
    sigPulserRunningUpdated = QtCore.Signal(bool)
    sigExtMicrowaveRunningUpdated = QtCore.Signal(bool)
    sigExtMicrowaveSettingsUpdated = QtCore.Signal(dict)
    sigFastCounterSettingsUpdated = QtCore.Signal(dict)
    sigMeasurementSettingsUpdated = QtCore.Signal(dict)
    sigAnalysisSettingsUpdated = QtCore.Signal(dict)
    sigExtractionSettingsUpdated = QtCore.Signal(dict)
    # Internal signals
    sigStartTimer = QtCore.Signal()
    sigStopTimer = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        # timer for measurement
        self.__analysis_timer = None
        self.__start_time = 0
        self.__elapsed_time = 0
        self.__elapsed_sweeps = 0  # FIXME: unused

        # threading
        self._threadlock = Mutex()

        # measurement data
        self.signal_data = np.empty((2, 0), dtype=float)
        self.signal_alt_data = np.empty((2, 0), dtype=float)
        self.measurement_error = np.empty((2, 0), dtype=float)
        self.laser_data = np.zeros((10, 20), dtype='int64')
        self.raw_data = np.zeros((10, 20), dtype='int64')

        self._saved_data = OrderedDict()  # temporary saved raw data
        self._current_saved_data_tag = None  # the currently recalled raw data dict key

        # Paused measurement flag
        self.__is_paused = False

        # for fit:
        self.fc = None  # Fit container
        self.fit_result = None
        self.alt_fit_result = None
        self.signal_fit_data = np.empty((2, 0), dtype=float)  # The x,y data of the fit result
        self.signal_fit_alt_data = np.empty((2, 0), dtype=float)
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Create an instance of PulseExtractor
        self._pulseextractor = PulseExtractor(pulsedmeasurementlogic=self)
        self._pulseanalyzer = PulseAnalyzer(pulsedmeasurementlogic=self)

        # QTimer must be created here instead of __init__ because otherwise the timer will not run
        # in this logic's thread but in the manager instead.
        self.__analysis_timer = QtCore.QTimer()
        self.__analysis_timer.setSingleShot(False)
        self.__analysis_timer.setInterval(round(1000. * self.__timer_interval))
        self.__analysis_timer.timeout.connect(self._pulsed_analysis_loop,
                                              QtCore.Qt.QueuedConnection)

        # Fitting
        self.fc = self.fitlogic().make_fit_container('pulsed', '1d')
        self.fc.set_units(self._data_units)

        # Recall saved status variables
        if 'fits' in self._statusVariables and isinstance(self._statusVariables.get('fits'), dict):
            self.fc.load_from_dict(self._statusVariables['fits'])

        # Turn off pulse generator
        self.pulse_generator_off()

        # Check and configure fast counter
        binning_constraints = self.fastcounter().get_constraints()['hardware_binwidth_list']
        if self.__fast_counter_binwidth not in binning_constraints:
            self.__fast_counter_binwidth = binning_constraints[0]
        if self.__fast_counter_record_length <= 0:
            self.__fast_counter_record_length = 3e-6
        self.fast_counter_off()
        self.set_fast_counter_settings()

        # Check and configure external microwave
        if self.__use_ext_microwave:
            self.microwave_off()
            self.set_microwave_settings(frequency=self.__microwave_freq,
                                        power=self.__microwave_power,
                                        use_ext_microwave=True)

        # Convert controlled variable list into numpy.ndarray
        self._controlled_variable = np.array(self._controlled_variable, dtype=float)

        # initialize arrays for the measurement data
        self._initialize_data_arrays()

        # recalled saved raw data dict key
        self._current_saved_data_tag = None

        # Connect internal signals
        self.sigStartTimer.connect(self.__analysis_timer.start, QtCore.Qt.QueuedConnection)
        self.sigStopTimer.connect(self.__analysis_timer.stop, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        if self.module_state() == 'locked':
            self.stop_pulsed_measurement()

        self._statusVariables['_controlled_variable'] = list(self._controlled_variable)
        if len(self.fc.fit_list) > 0:
            self._statusVariables['fits'] = self.fc.save_to_dict()

        self.extraction_parameters = self._pulseextractor.full_settings_dict
        self.analysis_parameters = self._pulseanalyzer.full_settings_dict

        self.__analysis_timer.timeout.disconnect()
        self.sigStartTimer.disconnect()
        self.sigStopTimer.disconnect()
        return

    ############################################################################
    # Fast counter control methods and properties
    ############################################################################
    @property
    def fast_counter_settings(self):
        settings_dict = dict()
        settings_dict['bin_width'] = float(self.__fast_counter_binwidth)
        settings_dict['record_length'] = float(self.__fast_counter_record_length)
        settings_dict['number_of_gates'] = int(self.__fast_counter_gates)
        settings_dict['is_gated'] = bool(self.fastcounter().is_gated())
        return settings_dict

    @fast_counter_settings.setter
    def fast_counter_settings(self, settings_dict):
        if isinstance(settings_dict, dict):
            self.set_fast_counter_settings(settings_dict)
        return

    @property
    def fast_counter_constraints(self):
        return self.fastcounter().get_constraints()

    @QtCore.Slot(dict)
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
            if 'bin_width' in settings_dict:
                self.__fast_counter_binwidth = float(settings_dict['bin_width'])
            if 'record_length' in settings_dict:
                self.__fast_counter_record_length = float(settings_dict['record_length'])
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
        else:
            self.log.warning('Fast counter is not idle (status: {0}).\n'
                             'Unable to apply new settings.'.format(counter_status))

        # emit update signal for master (GUI or other logic module)
        self.sigFastCounterSettingsUpdated.emit(self.fast_counter_settings)
        return self.fast_counter_settings

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

    @QtCore.Slot(bool)
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

    @QtCore.Slot(bool)
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
    # External microwave control methods and properties
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
            self.set_microwave_settings(settings_dict)
        return

    @property
    def ext_microwave_constraints(self):
        return self.microwave().get_limits()

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

    @QtCore.Slot(bool)
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

    @QtCore.Slot(dict)
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
        if self.microwave().get_status()[1]:
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
        self.sigExtMicrowaveSettingsUpdated.emit({'power': self.__microwave_power,
                                                  'frequency': self.__microwave_freq,
                                                  'use_ext_microwave': self.__use_ext_microwave})
        return self.__microwave_freq, self.__microwave_power, self.__use_ext_microwave
    ############################################################################

    ############################################################################
    # Pulse generator control methods and properties
    ############################################################################
    @property
    def pulse_generator_constraints(self):
        return self.pulsegenerator().get_constraints()

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

    @QtCore.Slot(bool)
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
    # Measurement control methods and properties
    ############################################################################
    @property
    def measurement_settings(self):
        settings_dict = dict()
        settings_dict['invoke_settings'] = bool(self._invoke_settings_from_sequence)
        settings_dict['controlled_variable'] = np.array(self._controlled_variable,
                                                        dtype=float).copy()
        settings_dict['number_of_lasers'] = int(self._number_of_lasers)
        settings_dict['laser_ignore_list'] = list(self._laser_ignore_list).copy()
        settings_dict['alternating'] = bool(self._alternating)
        settings_dict['units'] = self._data_units
        settings_dict['labels'] = self._data_labels
        return settings_dict

    @measurement_settings.setter
    def measurement_settings(self, settings_dict):
        if isinstance(settings_dict, dict):
            self.set_measurement_settings(settings_dict)
        return

    @property
    def measurement_information(self):
        return self._measurement_information

    @measurement_information.setter
    def measurement_information(self, info_dict):
        # Check if mandatory params to invoke settings are missing and set empty dict in that case.
        mand_params = ('number_of_lasers',
                       'controlled_variable',
                       'laser_ignore_list',
                       'alternating',
                       'counting_length')
        if not isinstance(info_dict, dict) or not all(param in info_dict for param in mand_params):
            self.log.debug('The set measurement_information did not contain all the necessary '
                           'information or was not a dict. Setting empty dict.')
            self._measurement_information = dict()
            return

        # Set measurement_information dict
        self._measurement_information = info_dict.copy()

        # invoke settings if needed
        if self._invoke_settings_from_sequence and self._measurement_information:
            self._apply_invoked_settings()
            self.sigMeasurementSettingsUpdated.emit(self.measurement_settings)
        return

    @property
    def sampling_information(self):
        return self._sampling_information

    @sampling_information.setter
    def sampling_information(self, info_dict):
        if isinstance(info_dict, dict):
            self._sampling_information = info_dict
        else:
            self._sampling_information = dict()
        return

    @property
    def timer_interval(self):
        return float(self.__timer_interval)

    @timer_interval.setter
    def timer_interval(self, value):
        if isinstance(value, (int, float)):
            self.set_timer_interval(value)
        return

    @property
    def alternative_data_type(self):
        return str(self._alternative_data_type)

    @alternative_data_type.setter
    def alternative_data_type(self, alt_data_type):
        if isinstance(alt_data_type, str) or alt_data_type is None:
            self.set_alternative_data_type(alt_data_type)
        return

    @property
    def analysis_methods(self):
        return self._pulseanalyzer.analysis_methods

    @property
    def extraction_methods(self):
        return self._pulseextractor.extraction_methods

    @property
    def analysis_settings(self):
        return self._pulseanalyzer.analysis_settings

    @analysis_settings.setter
    def analysis_settings(self, settings_dict):
        if isinstance(settings_dict, dict):
            self.set_analysis_settings(settings_dict)
        return

    @property
    def extraction_settings(self):
        return self._pulseextractor.extraction_settings

    @extraction_settings.setter
    def extraction_settings(self, settings_dict):
        if isinstance(settings_dict, dict):
            self.set_extraction_settings(settings_dict)
        return

    @QtCore.Slot(dict)
    def set_analysis_settings(self, settings_dict=None, **kwargs):
        """
        Apply new analysis settings.
        Either accept a settings dictionary as positional argument or keyword arguments.
        If both are present both are being used by updating the settings_dict with kwargs.
        The keyword arguments take precedence over the items in settings_dict if there are
        conflicting names.

        @param settings_dict:
        @param kwargs:
        @return:
        """
        # Determine complete settings dictionary
        if not isinstance(settings_dict, dict):
            settings_dict = kwargs
        else:
            settings_dict.update(kwargs)

        for key in settings_dict:
            if key in ['signal_start', 'signal_end', 'norm_start', 'norm_end']:
                num_bins_fast = round(settings_dict[key]/self.fast_counter_settings['bin_width'])
                settings_dict[key] = num_bins_fast * self.fast_counter_settings['bin_width']

        # Use threadlock to update settings during a running measurement
        with self._threadlock:
            self._pulseanalyzer.analysis_settings = settings_dict
            self.sigAnalysisSettingsUpdated.emit(self.analysis_settings)
        return

    @QtCore.Slot(dict)
    def set_extraction_settings(self, settings_dict=None, **kwargs):
        """
        Apply new analysis settings.
        Either accept a settings dictionary as positional argument or keyword arguments.
        If both are present both are being used by updating the settings_dict with kwargs.
        The keyword arguments take precedence over the items in settings_dict if there are
        conflicting names.

        @param settings_dict:
        @param kwargs:
        @return:
        """
        # Determine complete settings dictionary
        if not isinstance(settings_dict, dict):
            settings_dict = kwargs
        else:
            settings_dict.update(kwargs)

        # Use threadlock to update settings during a running measurement
        with self._threadlock:
            self._pulseextractor.extraction_settings = settings_dict
            self.sigExtractionSettingsUpdated.emit(self.extraction_settings)
        return

    @QtCore.Slot(dict)
    def set_measurement_settings(self, settings_dict=None, **kwargs):
        """
        Apply new measurement settings.
        Either accept a settings dictionary as positional argument or keyword arguments.
        If both are present both are being used by updating the settings_dict with kwargs.
        The keyword arguments take precedence over the items in settings_dict if there are
        conflicting names.

        @param settings_dict:
        @param kwargs:
        @return:
        """
        # Determine complete settings dictionary
        if not isinstance(settings_dict, dict):
            settings_dict = kwargs
        else:
            settings_dict.update(kwargs)

        # Check if invoke_settings flag has changed
        if 'invoke_settings' in settings_dict:
            self._invoke_settings_from_sequence = bool(settings_dict.get('invoke_settings'))

        # Invoke settings if measurement_information is present and flag is set
        if self._invoke_settings_from_sequence:
            if self._measurement_information:
                self._apply_invoked_settings()
        else:
            # Apply settings that can be changed while a measurement is running
            with self._threadlock:
                if 'units' in settings_dict:
                    self._data_units = settings_dict.get('units')
                    self.fc.set_units(self._data_units)
                if 'labels' in settings_dict:
                    self._data_labels = list(settings_dict.get('labels'))

            if self.module_state() == 'idle':
                # Get all other parameters if present
                if 'controlled_variable' in settings_dict:
                    self._controlled_variable = np.array(settings_dict.get('controlled_variable'),
                                                         dtype=float)
                if 'number_of_lasers' in settings_dict:
                    self._number_of_lasers = int(settings_dict.get('number_of_lasers'))
                    if self.fastcounter().is_gated():
                        self.set_fast_counter_settings(number_of_gates=self._number_of_lasers)
                if 'laser_ignore_list' in settings_dict:
                    self._laser_ignore_list = sorted(settings_dict.get('laser_ignore_list'))
                if 'alternating' in settings_dict:
                    self._alternating = bool(settings_dict.get('alternating'))

        # Perform sanity checks on settings
        self._measurement_settings_sanity_check()

        # emit update signal for master (GUI or other logic module)
        self.sigMeasurementSettingsUpdated.emit(self.measurement_settings)
        return self.measurement_settings

    @QtCore.Slot(bool, str)
    def toggle_pulsed_measurement(self, start, stash_raw_data_tag=''):
        """
        Convenience method to start/stop measurement

        @param bool start: Start the measurement (True) or stop the measurement (False)
        """
        if start:
            self.start_pulsed_measurement(stash_raw_data_tag)
        else:
            self.stop_pulsed_measurement(stash_raw_data_tag)
        return

    @QtCore.Slot(str)
    def start_pulsed_measurement(self, stashed_raw_data_tag=''):
        """Start the analysis loop."""
        self.sigMeasurementStatusUpdated.emit(True, False)

        # Check if measurement settings need to be invoked
        if self._invoke_settings_from_sequence:
            if self._measurement_information:
                self._apply_invoked_settings()
                self.sigMeasurementSettingsUpdated.emit(self.measurement_settings)
            else:
                # abort measurement if settings could not be invoked
                self.log.error('Unable to invoke measurement settings.\nThis feature can only be '
                               'used when creating the pulse sequence via predefined methods.\n'
                               'Aborting measurement start.')
                self.set_measurement_settings(invoke_settings=False)
                self.sigMeasurementStatusUpdated.emit(False, False)
                return

        with self._threadlock:
            if self.module_state() == 'idle':
                # Lock module state
                self.module_state.lock()

                # Clear previous fits
                self.do_fit('No Fit', False)
                self.do_fit('No Fit', True)

                # initialize data arrays
                self._initialize_data_arrays()

                # recall stashed raw data
                if stashed_raw_data_tag in self._saved_data:
                    self._current_saved_data_tag = stashed_raw_data_tag
                    self.log.info('Starting pulsed measurement with stashed raw data "{0}".'
                                  ''.format(stashed_raw_data_tag))
                else:
                    self._current_saved_data_tag = None

                # start microwave source
                if self.__use_ext_microwave:
                    self.microwave_on()
                # start fast counter
                self.fast_counter_on()
                # start pulse generator
                self.pulse_generator_on()

                # initialize analysis_timer
                self.__elapsed_time = 0.0
                self.sigTimerUpdated.emit(self.__elapsed_time,
                                          self.__elapsed_sweeps,
                                          self.__timer_interval)

                # Set starting time and start timer (if present)
                self.__start_time = time.time()
                self.sigStartTimer.emit()

                # Set measurement paused flag
                self.__is_paused = False
            else:
                self.log.warning('Unable to start pulsed measurement. Measurement already running.')
        return

    @QtCore.Slot(str)
    def stop_pulsed_measurement(self, stash_raw_data_tag=''):
        """
        Stop the measurement
        """
        # Get raw data and analyze it a last time just before stopping the measurement.
        try:
            self._pulsed_analysis_loop()
        except:
            pass

        with self._threadlock:
            if self.module_state() == 'locked':
                # stopping the timer
                self.sigStopTimer.emit()
                # Turn off fast counter
                self.fast_counter_off()
                # Turn off pulse generator
                self.pulse_generator_off()
                # Turn off microwave source
                if self.__use_ext_microwave:
                    self.microwave_off()

                # stash raw data if requested
                if stash_raw_data_tag:
                    #self.log.info('Raw data saved with tag "{0}" to continue measurement at a '
                    #              'later point.'.format(stash_raw_data_tag))
                    self._saved_data[stash_raw_data_tag] = {'raw': self.raw_data.copy()}
                self._current_saved_data_tag = None

                # Set measurement paused flag
                self.__is_paused = False

                self.module_state.unlock()
                self.sigMeasurementStatusUpdated.emit(False, False)
        return

    @QtCore.Slot(bool)
    def toggle_measurement_pause(self, pause):
        """
        Convenience method to pause/continue measurement

        @param bool pause: Pause the measurement (True) or continue the measurement (False)
        """
        if pause:
            self.pause_pulsed_measurement()
        else:
            self.continue_pulsed_measurement()
        return

    @QtCore.Slot()
    def pause_pulsed_measurement(self):
        """
        Pauses the measurement
        """
        with self._threadlock:
            if self.module_state() == 'locked':
                # pausing the timer
                if self.__analysis_timer.isActive():
                    # stopping the timer
                    self.sigStopTimer.emit()

                self.fast_counter_pause()
                self.pulse_generator_off()
                if self.__use_ext_microwave:
                    self.microwave_off()

                # Set measurement paused flag
                self.__is_paused = True

                self.sigMeasurementStatusUpdated.emit(True, True)
            else:
                self.log.warning('Unable to pause pulsed measurement. No measurement running.')
                self.sigMeasurementStatusUpdated.emit(False, False)
        return

    @QtCore.Slot()
    def continue_pulsed_measurement(self):
        """
        Continues the measurement
        """
        with self._threadlock:
            if self.module_state() == 'locked':
                if self.__use_ext_microwave:
                    self.microwave_on()
                self.fast_counter_continue()
                self.pulse_generator_on()

                # un-pausing the timer
                if not self.__analysis_timer.isActive():
                    self.sigStartTimer.emit()

                # Set measurement paused flag
                self.__is_paused = False

                self.sigMeasurementStatusUpdated.emit(True, False)
            else:
                self.log.warning('Unable to continue pulsed measurement. No measurement running.')
                self.sigMeasurementStatusUpdated.emit(False, False)
        return

    @QtCore.Slot(float)
    @QtCore.Slot(int)
    def set_timer_interval(self, interval):
        """
        Change the interval of the measurement analysis timer

        @param int|float interval: Interval of the timer in s
        """
        with self._threadlock:
            self.__timer_interval = interval
            if self.__timer_interval > 0:
                self.__analysis_timer.setInterval(int(1000. * self.__timer_interval))
                if self.module_state() == 'locked' and not self.__is_paused:
                    self.sigStartTimer.emit()
            else:
                self.sigStopTimer.emit()

            self.sigTimerUpdated.emit(self.__elapsed_time, self.__elapsed_sweeps,
                                      self.__timer_interval)
        return

    @QtCore.Slot(str)
    def set_alternative_data_type(self, alt_data_type):
        """

        @param alt_data_type:
        @return:
        """
        with self._threadlock:
            if alt_data_type != self.alternative_data_type:
                self.do_fit('No Fit', True)
            if alt_data_type == 'Delta' and not self._alternating:
                if self._alternative_data_type == 'Delta':
                    self._alternative_data_type = None
                self.log.error('Can not set "Delta" as alternative data calculation if measurement is '
                               'not alternating.\n'
                               'Setting to previous type "{0}".'.format(self.alternative_data_type))
            elif alt_data_type == 'None':
                self._alternative_data_type = None
            else:
                self._alternative_data_type = alt_data_type

            self._compute_alt_data()
            self.sigMeasurementDataUpdated.emit()
        return

    @QtCore.Slot()
    def manually_pull_data(self):
        """ Analyse and display the data
        """
        if self.module_state() == 'locked':
            self._pulsed_analysis_loop()
        return

    @QtCore.Slot(str)
    @QtCore.Slot(str, bool)
    def do_fit(self, fit_method, use_alternative_data=False, data=None):
        """
        Performs the chosen fit on the measured data.

        @param str fit_method: name of the fit method to use
        @param bool use_alternative_data: Flag indicating if the signal data (False) or the
                                          alternative signal data (True) should be fitted.
                                          Ignored if data is given as parameter
        @param 2D numpy.ndarray data: the x and y data points for the fit (shape=(2,X))

        @return (2D numpy.ndarray, result object): the resulting fit data and the fit result object
        """
        # Set current fit
        self.fc.set_current_fit(fit_method)

        if data is None:
            data = self.signal_alt_data if use_alternative_data else self.signal_data
            update_fit_data = True
        else:
            update_fit_data = False

        x_fit, y_fit, result = self.fc.do_fit(data[0], data[1])

        fit_data = np.array([x_fit, y_fit])

        if update_fit_data:
            if use_alternative_data:
                self.signal_fit_alt_data = fit_data
                self.alt_fit_result = copy.deepcopy(self.fc.current_fit_result)
                self.sigFitUpdated.emit(self.fc.current_fit, self.signal_fit_alt_data,
                                        self.alt_fit_result, use_alternative_data)
            else:
                self.signal_fit_data = fit_data
                self.fit_result = copy.deepcopy(self.fc.current_fit_result)
                self.sigFitUpdated.emit(self.fc.current_fit, self.signal_fit_data, self.fit_result,
                                        use_alternative_data)
        return fit_data, self.fc.current_fit_result

    def _apply_invoked_settings(self):
        """
        """
        if not isinstance(self._measurement_information, dict) or not self._measurement_information:
            self.log.warning('Can\'t invoke measurement settings from sequence information '
                             'since no measurement_information container is given.')
            return

        # First try to set parameters that can be changed during a running measurement
        if 'units' in self._measurement_information:
            with self._threadlock:
                self._data_units = self._measurement_information.get('units')
                self.fc.set_units(self._data_units)
        if 'labels' in self._measurement_information:
            with self._threadlock:
                self._data_labels = list(self._measurement_information.get('labels'))

        # Check if a measurement is running and apply following settings if this is not the case
        if self.module_state() == 'locked':
            return

        if 'number_of_lasers' in self._measurement_information:
            self._number_of_lasers = int(self._measurement_information.get('number_of_lasers'))
        else:
            self.log.error('Unable to invoke setting for "number_of_lasers".\n'
                           'Measurement information container is incomplete/invalid.')
            return

        if 'laser_ignore_list' in self._measurement_information:
            self._laser_ignore_list = sorted(self._measurement_information.get('laser_ignore_list'))
        else:
            self.log.error('Unable to invoke setting for "laser_ignore_list".\n'
                           'Measurement information container is incomplete/invalid.')
            return

        if 'alternating' in self._measurement_information:
            self._alternating = bool(self._measurement_information.get('alternating'))
        else:
            self.log.error('Unable to invoke setting for "alternating".\n'
                           'Measurement information container is incomplete/invalid.')
            return

        if 'controlled_variable' in self._measurement_information:
            self._controlled_variable = np.array(
                self._measurement_information.get('controlled_variable'), dtype=float)
        else:
            self.log.error('Unable to invoke setting for "controlled_variable".\n'
                           'Measurement information container is incomplete/invalid.')
            return

        if 'counting_length' in self._measurement_information:
            fast_counter_record_length = self._measurement_information.get('counting_length')
        else:
            self.log.error('Unable to invoke setting for "counting_length".\n'
                           'Measurement information container is incomplete/invalid.')
            return

        if self.fastcounter().is_gated():
            self.set_fast_counter_settings(number_of_gates=self._number_of_lasers,
                                           record_length=fast_counter_record_length)
        else:
            self.set_fast_counter_settings(record_length=fast_counter_record_length)
        return

    def _measurement_settings_sanity_check(self):
        number_of_analyzed_lasers = self._number_of_lasers - len(self._laser_ignore_list)
        if len(self._controlled_variable) < 1:
            self.log.error('Tried to set empty controlled variables array. This can not work.')

        if self._alternating and (number_of_analyzed_lasers // 2) != len(self._controlled_variable):
            self.log.error('Half of the number of laser pulses to analyze ({0}) does not match the '
                           'number of controlled_variable ticks ({1:d}).'
                           ''.format(number_of_analyzed_lasers // 2,
                                     len(self._controlled_variable)))
        elif not self._alternating and number_of_analyzed_lasers != len(self._controlled_variable):
            self.log.error('Number of laser pulses to analyze ({0:d}) does not match the number of '
                           'controlled_variable ticks ({1:d}).'
                           ''.format(number_of_analyzed_lasers, len(self._controlled_variable)))

        if self.fastcounter().is_gated() and self._number_of_lasers != self.__fast_counter_gates:
            self.log.error('Gated fast counter gate number differs from number of laser pulses '
                           'configured in measurement settings.')
        return

    def _pulsed_analysis_loop(self):
        """ Acquires laser pulses from fast counter,
            calculates fluorescence signal and creates plots.
        """
        with self._threadlock:
            if self.module_state() == 'locked':
                # Update elapsed time
                self.__elapsed_time = time.time() - self.__start_time

                self._extract_laser_pulses()

                tmp_signal, tmp_error = self._analyze_laser_pulses()

                # exclude laser pulses to ignore
                if len(self._laser_ignore_list) > 0:
                    # Convert relative negative indices into absolute positive indices
                    while self._laser_ignore_list[0] < 0:
                        neg_index = self._laser_ignore_list[0]
                        self._laser_ignore_list[0] = len(tmp_signal) + neg_index
                        self._laser_ignore_list.sort()

                    tmp_signal = np.delete(tmp_signal, self._laser_ignore_list)
                    tmp_error = np.delete(tmp_error, self._laser_ignore_list)

                # order data according to alternating flag
                if self._alternating:
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
            self.sigTimerUpdated.emit(self.__elapsed_time, self.__elapsed_sweeps,
                                      self.__timer_interval)
            self.sigMeasurementDataUpdated.emit()
            return

    def _extract_laser_pulses(self):
        # Get counter raw data (including recalled raw data from previous measurement)
        self._fetch_raw_data()

        # extract laser pulses from raw data
        return_dict = self._pulseextractor.extract_laser_pulses(self.raw_data)
        self.laser_data = return_dict['laser_counts_arr']
        return

    def _analyze_laser_pulses(self):
        # analyze pulses and get data points for signal array. Also check if extraction
        # worked (non-zero array returned).
        if self.laser_data.any():
            tmp_signal, tmp_error = self._pulseanalyzer.analyse_laser_pulses(
                self.laser_data)
        else:
            tmp_signal = np.zeros(self.laser_data.shape[0])
            tmp_error = np.zeros(self.laser_data.shape[0])
        return tmp_signal, tmp_error

    def _fetch_raw_data(self):
        """
        Get the raw count data from the fast counting hardware and perform sanity checks.
        Also add recalled raw data to the newly received data.
        """
        # get raw data from fast counter
        fc_data = netobtain(self.fastcounter().get_data_trace())

        # add old raw data from previous measurements if necessary
        if self._saved_data.get(self._current_saved_data_tag) is not None:
            self.log.info('Found old saved raw data with tag "{0}".'
                          ''.format(self._current_saved_data_tag))
            if not fc_data.any():
                self.log.warning('Only zeros received from fast counter!\n'
                                 'Using recalled raw data only.')
                fc_data = self._saved_data[self._current_saved_data_tag]['raw']
            elif self._saved_data[self._current_saved_data_tag].shape == fc_data.shape:
                self.log.debug('Recalled raw data has the same shape as current data.')
                fc_data = self._saved_data[self._current_saved_data_tag]['raw'] + fc_data
            else:
                self.log.warning('Recalled raw data has not the same shape as current data.'
                                 '\nDid NOT add recalled raw data to current time trace.')
        elif not fc_data.any():
            self.log.warning('Only zeros received from fast counter!')
            fc_data = np.zeros(fc_data.shape, dtype='int64')
        self.raw_data = fc_data


    def _initialize_data_arrays(self):
        """
        Initializing the signal, error, laser and raw data arrays.
        """
        # Determine signal array dimensions
        signal_dim = 3 if self._alternating else 2

        self.signal_data = np.zeros((signal_dim, len(self._controlled_variable)), dtype=float)
        self.signal_data[0] = self._controlled_variable

        self.signal_alt_data = np.zeros((signal_dim, len(self._controlled_variable)), dtype=float)
        self.signal_alt_data[0] = self._controlled_variable

        self.measurement_error = np.zeros((signal_dim, len(self._controlled_variable)), dtype=float)
        self.measurement_error[0] = self._controlled_variable

        number_of_bins = int(self.__fast_counter_record_length / self.__fast_counter_binwidth)
        laser_length = number_of_bins if self.__fast_counter_gates > 0 else 500
        self.laser_data = np.zeros((self._number_of_lasers, laser_length), dtype='int64')

        if self.__fast_counter_gates > 0:
            self.raw_data = np.zeros((self._number_of_lasers, number_of_bins), dtype='int64')
        else:
            self.raw_data = np.zeros(number_of_bins, dtype='int64')

        self.sigMeasurementDataUpdated.emit()
        return

    # FIXME: Revise everything below

    ############################################################################
    @QtCore.Slot(str, bool)
    def save_measurement_data(self, tag=None, with_error=True):
        """
        Prepare data to be saved and create a proper plot of the data

        @param str tag: a filetag which will be included in the filename
        @param bool with_error: select whether errors should be saved/plotted

        @return str: filepath where data were saved
        """
        filepath = self.savelogic().get_path_for_module('PulsedMeasurement')
        timestamp = datetime.datetime.now()

        #####################################################################
        ####                Save extracted laser pulses                  ####
        #####################################################################
        if tag:
            filelabel = tag + '_laser_pulses'
        else:
            filelabel = 'laser_pulses'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        laser_trace = self.laser_data
        data['Signal (counts)'] = laser_trace.transpose()

        # write the parameters:
        parameters = OrderedDict()
        parameters['bin width (s)'] = self.__fast_counter_binwidth
        parameters['record length (s)'] = self.__fast_counter_record_length
        parameters['gated counting'] = self.fast_counter_settings['is_gated']
        parameters['extraction parameters'] = self.extraction_settings

        self.savelogic().save_data(data,
                                   timestamp=timestamp,
                                   parameters=parameters,
                                   filepath=filepath,
                                   filelabel=filelabel,
                                   filetype='text',
                                   fmt='%d',
                                   delimiter='\t')

        #####################################################################
        ####                Save measurement data                        ####
        #####################################################################
        if tag:
            filelabel = tag + '_pulsed_measurement'
        else:
            filelabel = 'pulsed_measurement'

        # prepare the data in a dict or in an OrderedDict:
        header_str = 'Controlled variable'
        if self._data_units[0]:
            header_str += '({0})'.format(self._data_units[0])
        header_str += '\tSignal'
        if self._data_units[1]:
            header_str += '({0})'.format(self._data_units[1])
        if self._alternating:
            header_str += '\tSignal2'
            if self._data_units[1]:
                header_str += '({0})'.format(self._data_units[1])
        if with_error:
            header_str += '\tError'
            if self._data_units[1]:
                header_str += '({0})'.format(self._data_units[1])
            if self._alternating:
                header_str += '\tError2'
                if self._data_units[1]:
                    header_str += '({0})'.format(self._data_units[1])
        data = OrderedDict()
        if with_error:
            data[header_str] = np.vstack((self.signal_data, self.measurement_error[1:])).transpose()
        else:
            data[header_str] = self.signal_data.transpose()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Approx. measurement time (s)'] = self.__elapsed_time
        parameters['Measurement sweeps'] = self.__elapsed_sweeps
        parameters['Number of laser pulses'] = self._number_of_lasers
        parameters['Laser ignore indices'] = self._laser_ignore_list
        parameters['alternating'] = self._alternating
        parameters['analysis parameters'] = self.analysis_settings
        parameters['extraction parameters'] = self.extraction_settings
        parameters['fast counter settings'] = self.fast_counter_settings

        # Prepare the figure to save as a "data thumbnail"
        plt.style.use(self.savelogic().mpl_qd_style)

        # extract the possible colors from the colorscheme:
        prop_cycle = self.savelogic().mpl_qd_style['axes.prop_cycle']
        colors = {}
        for i, color_setting in enumerate(prop_cycle):
            colors[i] = color_setting['color']

        # scale the x_axis for plotting
        max_val = np.max(self.signal_data[0])
        scaled_float = units.ScaledFloat(max_val)
        counts_prefix = scaled_float.scale
        x_axis_scaled = self.signal_data[0] / scaled_float.scale_val

        # Create the figure object
        if self._alternative_data_type and self._alternative_data_type != 'None':
            fig, (ax1, ax2) = plt.subplots(2, 1)
        else:
            fig, ax1 = plt.subplots()

        if with_error:
            ax1.errorbar(x=x_axis_scaled, y=self.signal_data[1],
                         yerr=self.measurement_error[1], fmt='-o',
                         linestyle=':', linewidth=0.5, color=colors[0],
                         ecolor=colors[1], capsize=3, capthick=0.9,
                         elinewidth=1.2, label='data trace 1')

            if self._alternating:
                ax1.errorbar(x=x_axis_scaled, y=self.signal_data[2],
                             yerr=self.measurement_error[2], fmt='-D',
                             linestyle=':', linewidth=0.5, color=colors[3],
                             ecolor=colors[4],  capsize=3, capthick=0.7,
                             elinewidth=1.2, label='data trace 2')
        else:
            ax1.plot(x_axis_scaled, self.signal_data[1], '-o', color=colors[0],
                     linestyle=':', linewidth=0.5, label='data trace 1')

            if self._alternating:
                ax1.plot(x_axis_scaled, self.signal_data[2], '-o',
                         color=colors[3], linestyle=':', linewidth=0.5,
                         label='data trace 2')

        # Do not include fit curve if there is no fit calculated.
        if self.signal_fit_data.size != 0 and np.sum(self.signal_fit_data[1]) > 0:
            x_axis_fit_scaled = self.signal_fit_data[0] / scaled_float.scale_val
            ax1.plot(x_axis_fit_scaled, self.signal_fit_data[1],
                     color=colors[2], marker='None', linewidth=1.5,
                     label='fit')

            # add then the fit result to the plot:

            # Parameters for the text plot:
            # The position of the text annotation is controlled with the
            # relative offset in x direction and the relative length factor
            # rel_len_fac of the longest entry in one column
            rel_offset = 0.02
            rel_len_fac = 0.011
            entries_per_col = 24

            # create the formatted fit text:
            if hasattr(self.fit_result, 'result_str_dict'):
                result_str = units.create_formatted_output(self.fit_result.result_str_dict)
            else:
                result_str = ''
            # do reverse processing to get each entry in a list
            entry_list = result_str.split('\n')
            # slice the entry_list in entries_per_col
            chunks = [entry_list[x:x+entries_per_col] for x in range(0, len(entry_list), entries_per_col)]

            is_first_column = True  # first entry should contain header or \n

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

                ax1.text(1.00 + rel_offset, 0.99, column_text,
                         verticalalignment='top',
                         horizontalalignment='left',
                         transform=ax1.transAxes,
                         fontsize=12)

                # the rel_offset in position of the text is a linear function
                # which depends on the longest entry in the column
                rel_offset += rel_len_fac * len(max_length)

                is_first_column = False

        # handle the save of the alternative data plot
        if self._alternative_data_type and self._alternative_data_type != 'None':

            # scale the x_axis for plotting
            max_val = np.max(self.signal_alt_data[0])
            scaled_float = units.ScaledFloat(max_val)
            x_axis_prefix = scaled_float.scale
            x_axis_ft_scaled = self.signal_alt_data[0] / scaled_float.scale_val

            # since no ft units are provided, make a small work around:
            if self._alternative_data_type == 'FFT':
                if self._data_units[0] == 's':
                    inverse_cont_var = 'Hz'
                elif self._data_units[0] == 'Hz':
                    inverse_cont_var = 's'
                else:
                    inverse_cont_var = '(1/{0})'.format(self._data_units[0])
                x_axis_ft_label = 'FT {0} ({1}{2})'.format(
                    self._data_labels[0], x_axis_prefix, inverse_cont_var)
                y_axis_ft_label = 'FT({0}) (arb. u.)'.format(self._data_labels[1])
                ft_label = 'FT of data trace 1'
            else:
                if self._data_units[0]:
                    x_axis_ft_label = '{0} ({1}{2})'.format(self._data_labels[0], x_axis_prefix,
                                                            self._data_units[0])
                else:
                    x_axis_ft_label = '{0}'.format(self._data_labels[0])
                if self._data_units[1]:
                    y_axis_ft_label = '{0} ({1})'.format(self._data_labels[1], self._data_units[1])
                else:
                    y_axis_ft_label = '{0}'.format(self._data_labels[1])

                ft_label = '{0} of data traces'.format(self._alternative_data_type)

            ax2.plot(x_axis_ft_scaled, self.signal_alt_data[1], '-o',
                     linestyle=':', linewidth=0.5, color=colors[0],
                     label=ft_label)
            if self._alternating and len(self.signal_alt_data) > 2:
                ax2.plot(x_axis_ft_scaled, self.signal_alt_data[2], '-D',
                         linestyle=':', linewidth=0.5, color=colors[3],
                         label=ft_label.replace('1', '2'))

            ax2.set_xlabel(x_axis_ft_label)
            ax2.set_ylabel(y_axis_ft_label)
            ax2.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2,
                       mode="expand", borderaxespad=0.)

            if self.signal_fit_alt_data.size != 0 and np.sum(self.signal_fit_alt_data[1]) > 0:
                x_axis_fit_scaled = self.signal_fit_alt_data[0] / scaled_float.scale_val
                ax2.plot(x_axis_fit_scaled, self.signal_fit_alt_data[1],
                         color=colors[2], marker='None', linewidth=1.5,
                         label='secondary fit')

                # add then the fit result to the plot:

                # Parameters for the text plot:
                # The position of the text annotation is controlled with the
                # relative offset in x direction and the relative length factor
                # rel_len_fac of the longest entry in one column
                rel_offset = 0.02
                rel_len_fac = 0.011
                entries_per_col = 24

                # create the formatted fit text:
                if hasattr(self.alt_fit_result, 'result_str_dict'):
                    result_str = units.create_formatted_output(self.alt_fit_result.result_str_dict)
                else:
                    result_str = ''
                # do reverse processing to get each entry in a list
                entry_list = result_str.split('\n')
                # slice the entry_list in entries_per_col
                chunks = [entry_list[x:x+entries_per_col] for x in range(0, len(entry_list), entries_per_col)]

                is_first_column = True  # first entry should contain header or \n

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

                    ax2.text(1.00 + rel_offset, 0.99, column_text,
                             verticalalignment='top',
                             horizontalalignment='left',
                             transform=ax2.transAxes,
                             fontsize=12)

                    # the rel_offset in position of the text is a linear function
                    # which depends on the longest entry in the column
                    rel_offset += rel_len_fac * len(max_length)

                    is_first_column = False

        ax1.set_xlabel(
            '{0} ({1}{2})'.format(self._data_labels[0], counts_prefix, self._data_units[0]))
        if self._data_units[1]:
            ax1.set_ylabel('{0} ({1})'.format(self._data_labels[1], self._data_units[1]))
        else:
            ax1.set_ylabel('{0}'.format(self._data_labels[1]))

        fig.tight_layout()
        ax1.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2,
                   mode="expand", borderaxespad=0.)
        # plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2,
        #            mode="expand", borderaxespad=0.)

        self.savelogic().save_data(data, timestamp=timestamp,
                                   parameters=parameters, fmt='%.15e',
                                   filepath=filepath, filelabel=filelabel, filetype='text',
                                   delimiter='\t', plotfig=fig)

        #####################################################################
        ####                Save raw data timetrace                      ####
        #####################################################################
        filelabel = 'raw_timetrace' if not tag else tag + '_raw_timetrace'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        raw_trace = self.raw_data.astype('int64')
        data['Signal(counts)'] = raw_trace.transpose()
        # write the parameters:
        parameters = OrderedDict()
        parameters['bin width (s)'] = self.__fast_counter_binwidth
        parameters['record length (s)'] = self.__fast_counter_record_length
        parameters['gated counting'] = self.fast_counter_settings['is_gated']
        parameters['Number of laser pulses'] = self._number_of_lasers
        parameters['alternating'] = self._alternating
        parameters['Controlled variable'] = list(self.signal_data[0])

        self.savelogic().save_data(data, timestamp=timestamp,
                                   parameters=parameters, fmt='%d',
                                   filepath=filepath, filelabel=filelabel,
                                   filetype=self._raw_data_save_type,
                                   delimiter='\t')
        return filepath

    def _compute_alt_data(self):
        """
        Performing transformations on the measurement data (e.g. fourier transform).
        """
        if self._alternative_data_type == 'Delta' and len(self.signal_data) == 3:
            self.signal_alt_data = np.empty((2, self.signal_data.shape[1]), dtype=float)
            self.signal_alt_data[0] = self.signal_data[0]
            self.signal_alt_data[1] = self.signal_data[1] - self.signal_data[2]
        elif self._alternative_data_type == 'FFT' and self.signal_data.shape[1] >= 2:
            fft_x, fft_y = units.compute_ft(x_val=self.signal_data[0],
                                            y_val=self.signal_data[1],
                                            zeropad_num=self.zeropad,
                                            window=self.window,
                                            base_corr=self.base_corr,
                                            psd=self.psd)
            self.signal_alt_data = np.empty((len(self.signal_data), len(fft_x)), dtype=float)
            self.signal_alt_data[0] = fft_x
            self.signal_alt_data[1] = fft_y
            for dim in range(2, len(self.signal_data)):
                dummy, self.signal_alt_data[dim] = units.compute_ft(x_val=self.signal_data[0],
                                                                    y_val=self.signal_data[dim],
                                                                    zeropad_num=self.zeropad,
                                                                    window=self.window,
                                                                    base_corr=self.base_corr,
                                                                    psd=self.psd)
        else:
            self.signal_alt_data = np.zeros(self.signal_data.shape, dtype=float)
            self.signal_alt_data[0] = self.signal_data[0]
        return



