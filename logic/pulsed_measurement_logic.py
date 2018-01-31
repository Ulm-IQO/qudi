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

    # status vars
    fast_counter_record_length = StatusVar(default=3.e-6)
    sequence_length_s = StatusVar(default=100e-6)
    fast_counter_binwidth = StatusVar(default=1e-9)
    microwave_power = StatusVar(default=-30.0)
    microwave_freq = StatusVar(default=2870e6)
    use_ext_microwave = StatusVar(default=False)
    current_channel_config_name = StatusVar(default='')
    sample_rate = StatusVar(default=25e9)
    analogue_amplitude = StatusVar(default=dict())
    interleave_on = StatusVar(default=False)
    timer_interval = StatusVar(default=5)
    alternating = StatusVar(default=False)
    show_raw_data = StatusVar(default=False)
    show_laser_index = StatusVar(default=0)

    # fourier transform status var:
    zeropad = StatusVar(default=0)
    psd = StatusVar(default=False)
    window = StatusVar(default='none')
    base_corr = StatusVar(default=True)
    save_ft = StatusVar(default=True)

    # signals
    sigSignalDataUpdated = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray,
                                         np.ndarray, np.ndarray, np.ndarray,
                                         np.ndarray, np.ndarray)
    sigLaserDataUpdated = QtCore.Signal(np.ndarray, np.ndarray)
    sigLaserToShowUpdated = QtCore.Signal(int, bool)
    sigElapsedTimeUpdated = QtCore.Signal(float, str)
    sigFitUpdated = QtCore.Signal(str, np.ndarray, np.ndarray, object)
    sigMeasurementRunningUpdated = QtCore.Signal(bool, bool)
    sigPulserRunningUpdated = QtCore.Signal(bool)
    sigFastCounterSettingsUpdated = QtCore.Signal(float, float)
    sigPulseSequenceSettingsUpdated = QtCore.Signal(np.ndarray, int, float, list, bool)
    sigPulseGeneratorSettingsUpdated = QtCore.Signal(float, str, dict, bool)
    sigUploadAssetComplete = QtCore.Signal(str)
    sigUploadedAssetsUpdated = QtCore.Signal(list)
    sigLoadedAssetUpdated = QtCore.Signal(str)
    sigExtMicrowaveSettingsUpdated = QtCore.Signal(float, float, bool)
    sigExtMicrowaveRunningUpdated = QtCore.Signal(bool)
    sigTimerIntervalUpdated = QtCore.Signal(float)
    sigAnalysisSettingsUpdated = QtCore.Signal(dict)
    sigAnalysisMethodsUpdated = QtCore.Signal(dict)
    sigExtractionSettingsUpdated = QtCore.Signal(dict)
    sigExtractionMethodsUpdated = QtCore.Signal(dict)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        # microwave parameters
        self.use_ext_microwave = False
        self.microwave_power = -30.     # dbm  (always in SI!)
        self.microwave_freq = 2870e6    # Hz   (always in SI!)

        # fast counter status variables
        self.fast_counter_status = None     # 0=unconfigured, 1=idle, 2=running, 3=paused, -1=error
        self.fast_counter_gated = None      # gated=True, ungated=False
        self.fast_counter_binwidth = 1e-9   # in seconds
        self.fast_counter_record_length = 3.e-6     # in seconds

        # parameters of the currently running sequence
        self.controlled_vals = np.array(range(50), dtype=float)
        self.laser_ignore_list = []
        self.number_of_lasers = 50
        self.sequence_length_s = 100e-6
        self.loaded_asset_name = ''
        self.alternating = False

        # Pulse generator parameters
        self.current_channel_config_name = ''
        self.sample_rate = 25e9
        self.analogue_amplitude = dict()
        self.interleave_on = False

        # timer for data analysis
        self.analysis_timer = None
        self.timer_interval = 5  # in seconds. A value <= 0 means no timer.

        #timer for time
        self.start_time = 0
        self.elapsed_time = 0
        self.elapsed_time_str = '00:00:00:00'

        # threading
        self.threadlock = Mutex()

        # plot data
        self.signal_plot_x = np.array([])
        self.signal_plot_y = np.array([])
        self.signal_plot_y2 = np.array([])
        self.signal_fft_x = np.array([])
        self.signal_fft_y = np.array([])
        self.signal_fft_y2 = np.array([])
        self.measuring_error_plot_x = np.array([])
        self.measuring_error_plot_y = np.array([])
        self.measuring_error_plot_y2 = np.array([])
        self.laser_plot_x = np.array([])
        self.laser_plot_y = np.array([])


        # raw data
        self.laser_data = np.zeros((10, 20))
        self.raw_data = np.zeros((10, 20))
        self.show_raw_data = False
        self.show_laser_index = 0
        self.saved_raw_data = OrderedDict()  # temporary saved raw data
        self.recalled_raw_data = None  # the currently recalled raw data to add

        # for fit:
        self.fc = None  # Fit container
        self.signal_plot_x_fit = np.arange(10, dtype=float)
        self.signal_plot_y_fit = np.zeros(len(self.signal_plot_x_fit), dtype=float)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # get all the connectors:
        self._pulse_analysis_logic = self.get_connector('pulseanalysislogic')
        self._pulse_extraction_logic = self.get_connector('pulseextractionlogic')
        self._fast_counter_device = self.get_connector('fastcounter')
        self._save_logic = self.get_connector('savelogic')
        self._fit_logic = self.get_connector('fitlogic')
        self._pulse_generator_device = self.get_connector('pulsegenerator')
        self._mycrowave_source_device = self.get_connector('microwave')

        # Fitting
        self.fc = self._fit_logic.make_fit_container('pulsed', '1d')
        self.fc.set_units(['s', 'arb.u.'])

        # Recall saved status variables
        if 'number_of_lasers' in self._statusVariables:
            self.number_of_lasers = self._statusVariables['number_of_lasers']
            self._pulse_extraction_logic.number_of_lasers = self.number_of_lasers
        if 'controlled_vals' in self._statusVariables:
            self.controlled_vals = np.array(self._statusVariables['controlled_vals'])
        if 'fits' in self._statusVariables and isinstance(self._statusVariables['fits'], dict):
            self.fc.load_from_dict(self._statusVariables['fits'])

        # Check and configure pulse generator
        self.pulse_generator_off()
        self.loaded_asset_name = str(self._pulse_generator_device.get_loaded_asset())
        avail_activation_configs = self.get_pulser_constraints().activation_config
        if self.current_channel_config_name not in avail_activation_configs:
            self.current_channel_config_name = list(avail_activation_configs)[0]
        if len(self.analogue_amplitude)==0:
            self.analogue_amplitude, dummy = self._pulse_generator_device.get_analog_level()
        if self.interleave_on is None:
            self.interleave_on = self._pulse_generator_device.get_interleave()
        # FIXME: Analog level and interleave
        self.set_pulse_generator_settings(self.sample_rate, self.current_channel_config_name,
                                          self.analogue_amplitude, self.interleave_on)

        # Check and configure fast counter
        self.fast_counter_gated = self._fast_counter_device.is_gated()
        binning_constraints = self.get_fastcounter_constraints()['hardware_binwidth_list']
        if self.fast_counter_binwidth not in binning_constraints:
            self.fast_counter_binwidth = binning_constraints[0]
        if self.fast_counter_record_length is None or self.fast_counter_record_length <= 0:
            self.fast_counter_record_length = 3e-6
        self.configure_fast_counter()
        self.fast_counter_off()
        self._pulse_analysis_logic.fast_counter_binwidth = self.fast_counter_binwidth
        # Check and configure external microwave
        if self.use_ext_microwave:
            self.microwave_on_off(False)
            self.set_microwave_params(self.microwave_freq, self.microwave_power,
                                      self.use_ext_microwave)

        # initialize arrays for the plot data
        self._initialize_plots()

        # recalled saved raw data
        self.recalled_raw_data = None
        return

    def on_deactivate(self):
        """ Deactivate the module properly.
        """

        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            self.stop_pulsed_measurement()

        self._statusVariables['number_of_lasers'] = self.number_of_lasers
        self._statusVariables['controlled_vals'] = list(self.controlled_vals)
        if len(self.fc.fit_list) > 0:
            self._statusVariables['fits'] = self.fc.save_to_dict()
        return

    def request_init_values(self):
        """

        @return:
        """
        self.sigMeasurementRunningUpdated.emit(False, False)
        self.sigPulserRunningUpdated.emit(False)
        self.sigExtMicrowaveRunningUpdated.emit(False)
        self.sigFastCounterSettingsUpdated.emit(self.fast_counter_binwidth,
                                                self.fast_counter_record_length)
        self.sigPulseSequenceSettingsUpdated.emit(self.controlled_vals,
                                                  self.number_of_lasers, self.sequence_length_s,
                                                  self.laser_ignore_list, self.alternating)
        self.sigPulseGeneratorSettingsUpdated.emit(self.sample_rate,
                                                   self.current_channel_config_name,
                                                   self.analogue_amplitude, self.interleave_on)
        self.sigExtMicrowaveSettingsUpdated.emit(self.microwave_freq, self.microwave_power,
                                                 self.use_ext_microwave)
        self.sigLaserToShowUpdated.emit(self.show_laser_index, self.show_raw_data)
        self.sigElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_time_str)
        self.sigTimerIntervalUpdated.emit(self.timer_interval)
        self.sigAnalysisMethodsUpdated.emit(self._pulse_analysis_logic.analysis_methods)
        self.sigExtractionMethodsUpdated.emit(self._pulse_extraction_logic.extraction_methods)
        self.sigAnalysisSettingsUpdated.emit(self._pulse_analysis_logic.analysis_settings)
        self.sigExtractionSettingsUpdated.emit(self._pulse_extraction_logic.extraction_settings)
        self.sigLoadedAssetUpdated.emit(self.loaded_asset_name)
        self.sigUploadedAssetsUpdated.emit(self._pulse_generator_device.get_uploaded_asset_names())
        self.sigSignalDataUpdated.emit(self.signal_plot_x, self.signal_plot_y, self.signal_plot_y2,
                                       self.measuring_error_plot_y, self.measuring_error_plot_y2,
                                       self.signal_fft_x, self.signal_fft_y, self.signal_fft_y2)
        #self.sigFitUpdated.emit('No Fit', self.signal_plot_x_fit, self.signal_plot_y_fit,
        #                        {})
        self.sigLaserDataUpdated.emit(self.laser_plot_x, self.laser_plot_y)
        return

    ############################################################################
    # Fast counter control methods
    ############################################################################
    def configure_fast_counter(self):
        """
        Configure the fast counter and updates the actually set values in the class variables.
        """
        # Check if fast counter is running and do nothing if that is the case
        if self.fast_counter_status is None:
            self.fast_counter_status = self._fast_counter_device.get_status()
        if self.fast_counter_status >= 2 or self.fast_counter_status < 0:
            return self.fast_counter_binwidth, self.fast_counter_record_length, self.number_of_lasers

        if self.fast_counter_gated:
            number_of_gates = self.number_of_lasers
        else:
            number_of_gates = 0

        actual_binwidth_s, actual_recordlength_s, actual_numofgates = self._fast_counter_device.configure(self.fast_counter_binwidth , self.fast_counter_record_length, number_of_gates)
        # use the actual parameters returned by the hardware
        self.fast_counter_binwidth = actual_binwidth_s
        self.fast_counter_record_length = actual_recordlength_s
        # update fast counter status variable
        self.fast_counter_status = self._fast_counter_device.get_status()
        return actual_binwidth_s, actual_recordlength_s, actual_numofgates

    def set_fast_counter_settings(self, bin_width_s, record_length_s):
        """

        @param bin_width_s:
        @param record_length_s:
        @return:
        """
        # get hardware constraints
        fc_constraints = self.get_fastcounter_constraints()
        # check and set bin width
        self.fast_counter_binwidth = bin_width_s
        # check and set record length
        self.fast_counter_record_length = record_length_s
        self.fast_counter_binwidth, self.fast_counter_record_length, num_of_gates = self.configure_fast_counter()
        # if self.fast_counter_gated:
        #    self.number_of_lasers = num_of_gates

        # Make sure the analysis logic takes the correct binning into account
        self._pulse_analysis_logic.fast_counter_binwidth = bin_width_s

        # emit update signal for master (GUI or other logic module)
        self.sigFastCounterSettingsUpdated.emit(self.fast_counter_binwidth,
                                                self.fast_counter_record_length)
        return self.fast_counter_binwidth, self.fast_counter_record_length

    def set_pulse_sequence_properties(self, controlled_vals, number_of_lasers,
                                      sequence_length_s, laser_ignore_list, is_alternating):
        if len(controlled_vals) < 1:
            self.log.error('Tried to set empty controlled variables array. This can not work.')
            self.sigPulseSequenceSettingsUpdated.emit(self.controlled_vals,
                                                      self.number_of_lasers, self.sequence_length_s,
                                                      self.laser_ignore_list, self.alternating)
            return self.controlled_vals, self.number_of_lasers, self.sequence_length_s, \
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
        self.sequence_length_s = sequence_length_s
        self.laser_ignore_list = laser_ignore_list
        self.alternating = is_alternating
        if self.fast_counter_gated:
            self.set_fast_counter_settings(self.fast_counter_binwidth,
                                           self.fast_counter_record_length)
        # emit update signal for master (GUI or other logic module)
        self.sigPulseSequenceSettingsUpdated.emit(self.controlled_vals,
                                                  self.number_of_lasers, self.sequence_length_s,
                                                  self.laser_ignore_list, self.alternating)
        return self.controlled_vals, self.number_of_lasers, self.sequence_length_s, \
               self.laser_ignore_list, self.alternating

    def get_fastcounter_constraints(self):
        """ Request the constrains from the hardware, in order to pass them
            to the GUI if necessary.

        @return: dict where the keys in it are predefined in the interface.
        """
        return self._fast_counter_device.get_constraints()

    def fast_counter_on(self):
        """Switching on the fast counter

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.start_measure()
        self.fast_counter_status = self._fast_counter_device.get_status()
        return error_code

    def fast_counter_off(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.stop_measure()
        self.fast_counter_status = self._fast_counter_device.get_status()
        return error_code

    def fast_counter_pause(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.pause_measure()
        self.fast_counter_status = self._fast_counter_device.get_status()
        return error_code

    def fast_counter_continue(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.continue_measure()
        self.fast_counter_status = self._fast_counter_device.get_status()
        return error_code

    ############################################################################


    ############################################################################
    # Pulse generator control methods
    ############################################################################
    def pulse_generator_on(self):
        """Switching on the pulse generator. """
        err = self._pulse_generator_device.pulser_on()
        self.sigPulserRunningUpdated.emit(True)
        return err

    def pulse_generator_off(self):
        """Switching off the pulse generator. """
        err = self._pulse_generator_device.pulser_off()
        self.sigPulserRunningUpdated.emit(False)
        return err

    def get_pulser_constraints(self):
        """ Request the constrains from the pulse generator hardware.

        @return: dict where the keys in it are predefined in the interface.
        """
        return self._pulse_generator_device.get_constraints()

    def set_pulse_generator_settings(self, sample_rate_Hz, activation_config_name, amplitude_dict, use_interleave=None):
        """

        @param sample_rate_Hz:
        @param activation_config_name:
        @param amplitude_dict:
        @param use_interleave:
        @return:
        """
        # Check if pulser is already running and do nothing if that is the case.
        pg_status, status_dict = self._pulse_generator_device.get_status()
        if pg_status > 0:
            return self.sample_rate, self.current_channel_config_name, self.analogue_amplitude, self.interleave_on

        # get hardware constraints
        pulser_constraints = self.get_pulser_constraints()

        # check and set interleave
        if use_interleave is not None:
            if self._pulse_generator_device.get_interleave() != use_interleave:
                self.interleave_on = self._pulse_generator_device.set_interleave(use_interleave)

        # check and set sample rate
        samplerate_constr = pulser_constraints.sample_rate
        if sample_rate_Hz > samplerate_constr.max or sample_rate_Hz < samplerate_constr.min:
            self.log.warning('Desired sample rate of {0:.0e} Hz not within pulse generator '
                             'constraints. Setting {1:.0e} Hz instead.'
                             ''.format(sample_rate_Hz, samplerate_constr.max))
            sample_rate_Hz = samplerate_constr.max
        self.sample_rate = self._pulse_generator_device.set_sample_rate(sample_rate_Hz)

        # check and set activation_config
        config_constr = pulser_constraints.activation_config
        if activation_config_name not in config_constr:
            new_config_name = list(config_constr.keys())[0]
            self.log.warning('Desired activation config "{0}" is no part of the pulse generator '
                             'constraints. Using "{1}" instead.'
                             ''.format(activation_config_name, new_config_name))
            activation_config_name = new_config_name
        activation_config = config_constr[activation_config_name]
        if self.interleave_on:
            analog_channels_to_activate = [chnl for chnl in activation_config if 'a_ch' in chnl]
            if len(analog_channels_to_activate) != 1:
                self.log.warning('When interleave mode is used only one analog channel can be '
                                 'active in pulse generator. Falling back to an allowed activation'
                                 ' config.')
        channel_activation = self.get_active_channels()
        for chnl in channel_activation:
            if chnl in activation_config:
                channel_activation[chnl] = True
            else:
                channel_activation[chnl] = False
        new_activation_dict = self._pulse_generator_device.set_active_channels(channel_activation)
        new_activation = [chnl for chnl in new_activation_dict if new_activation_dict[chnl]]
        tmp_config_name = None
        if new_activation.sort() != activation_config.sort():
            for config_name in config_constr:
                if config_constr[config_name].sort() == new_activation:
                    tmp_config_name = config_name
                    break
        else:
            tmp_config_name = activation_config_name
        self.current_channel_config_name = tmp_config_name

        # check and set analogue amplitude dict
        amplitude_constr = pulser_constraints.a_ch_amplitude
        for chnl in amplitude_dict:
            if amplitude_dict[chnl] > amplitude_constr.max or amplitude_dict[chnl] < amplitude_constr.min:
                self.log.error('Desired analogue voltage of {0} V for channel "{1}" is not within '
                               'pulse generator constraints. Using min voltage {2} V instead to '
                               'avoid damage.'
                               ''.format(amplitude_dict[chnl], chnl, amplitude_constr.min))
                amplitude_dict[chnl] = amplitude_constr.min
        self.analogue_amplitude, dummy = self._pulse_generator_device.set_analog_level(amplitude=amplitude_dict)
        # emit update signal for master (GUI or other logic module)
        self.sigPulseGeneratorSettingsUpdated.emit(self.sample_rate,
                                                   self.current_channel_config_name,
                                                   self.analogue_amplitude, self.interleave_on)

        return self.sample_rate, self.current_channel_config_name, self.analogue_amplitude, self.interleave_on

    def get_active_channels(self):
        """ Get the currently active channels from the pulse generator hardware.

        @return dict: dictionary with keys being the channel string generic
                      names and items being boolean values.

        Additionally the variables which hold this values are updated in the
        logic.
        """
        active_channels = self._pulse_generator_device.get_active_channels()
        return active_channels

    def clear_pulser(self):
        """ Delete all loaded files in the device's current memory. """
        self.pulse_generator_off()
        err = self._pulse_generator_device.clear_all()
        self.loaded_asset_name = ''
        self.sigLoadedAssetUpdated.emit(self.loaded_asset_name)
        return err

    def get_interleave(self):
        """ Get the interleave state.

        @return bool, state of the interleave, True=Interleave On, False=OFF
        """
        return self._pulse_generator_device.get_interleave()

    def upload_asset(self, asset_name):
        """ Upload an already sampled Ensemble or Sequence object to the device.
            Does NOT load it into channels.

        @param asset_name: string, name of the ensemble/sequence to upload
        """
        err = self._pulse_generator_device.upload_asset(asset_name)
        uploaded_assets = self._pulse_generator_device.get_uploaded_asset_names()
        self.sigUploadAssetComplete.emit(asset_name)
        self.sigUploadedAssetsUpdated.emit(uploaded_assets)
        return err

    def has_sequence_mode(self):
        """ Retrieve from the hardware, whether sequence mode is present or not.

        @return bool: Sequence mode present = True, no sequence mode = False
        """
        return self._pulse_generator_device.has_sequence_mode()

    def load_asset(self, asset_name, load_dict=None):
        """ Loads a sequence or waveform to the specified channel of the pulsing device.
        Emmits a signal that the current sequence/ensemble (asset) has changed.

        @param Object asset_name: The name of the asset to be loaded
        @param dict load_dict:  a dictionary with keys being one of the available channel numbers
                                and items being the name of the already sampled waveform/sequence
                                files. Examples:
                                    {1: rabi_Ch1, 2: rabi_Ch2}
                                    {1: rabi_Ch2, 2: rabi_Ch1}
                                This parameter is optional. If an empty dict is given then the
                                channel association should be invoked from the sequence generation,
                                i.e. the filename appendix (_Ch1, _Ch2 etc.). Note that is not in
                                general an ambigous procedure!

        @return int: error code (0:OK, -1:error)
        """
        # stop the pulser hardware output if it is running
        self.pulse_generator_off()
        # load asset in channels
        err = self._pulse_generator_device.load_asset(asset_name, load_dict)
        # set the loaded_asset_name variable.
        self.loaded_asset_name = self._pulse_generator_device.get_loaded_asset()
        self.sigLoadedAssetUpdated.emit(self.loaded_asset_name)
        return err

    def direct_write_ensemble(self, ensemble_name, analog_samples, digital_samples):
        """

        @param ensemble_name:
        @param analog_samples:
        @param digital_samples:
        @return:
        """
        err = self._pulse_generator_device.direct_write_ensemble(ensemble_name,
                                                                 analog_samples, digital_samples)
        uploaded_assets = self._pulse_generator_device.get_uploaded_asset_names()
        self.sigUploadAssetComplete.emit(ensemble_name)
        self.sigUploadedAssetsUpdated.emit(uploaded_assets)
        return err

    def direct_write_sequence(self, sequence_name, sequence_params):
        """

        @param sequence_name:
        @param sequence_params:
        @return:
        """
        err = self._pulse_generator_device.direct_write_sequence(sequence_name, sequence_params)
        uploaded_assets = self._pulse_generator_device.get_uploaded_asset_names()
        self.sigUploadAssetComplete.emit(sequence_name)
        self.sigUploadedAssetsUpdated.emit(uploaded_assets)
        return err

    ############################################################################

    ############################################################################
    # External microwave control methods
    ############################################################################
    def microwave_on_off(self, switch_on):
        """

        @param switch_on:
        @return:
        """
        if switch_on:
            err_code = self._mycrowave_source_device.cw_on()
            if err_code == -1:
                self._mycrowave_source_device.off()
                self.log.error('Failed to turn on CW microwave source.')
                self.sigExtMicrowaveRunningUpdated.emit(False)
            else:
                self.sigExtMicrowaveRunningUpdated.emit(True)
        else:
            err_code = self._mycrowave_source_device.off()
            if err_code == -1:
                self.log.error('Failed to turn off CW microwave source.')
            else:
                self.sigExtMicrowaveRunningUpdated.emit(False)
        return

    def set_microwave_params(self, frequency=None, power=None, use_ext_mw=None):
        if frequency is not None:
            self.microwave_freq = frequency
        if power is not None:
            self.microwave_power = power
        if use_ext_mw is not None:
            self.use_ext_microwave = use_ext_mw
        if self.use_ext_microwave:
            self.microwave_freq, \
            self.microwave_power, \
            dummy = self._mycrowave_source_device.set_cw(frequency=frequency, power=power)
        self.sigExtMicrowaveSettingsUpdated.emit(self.microwave_freq, self.microwave_power,
                                                 self.use_ext_microwave)
        return

    ############################################################################


    def start_pulsed_measurement(self, stashed_raw_data_tag=None):
        """Start the analysis thread. """
        #FIXME: Describe the idea of how the measurement is intended to be run
        #       and how the used thread principle was used in this method (or
        #       will be use in another method).
        self.sigMeasurementRunningUpdated.emit(True, False)
        if self.show_laser_index > self.number_of_lasers:
            self.set_laser_to_show(0, self.show_raw_data)
        if stashed_raw_data_tag == '':
            stashed_raw_data_tag = None
        with self.threadlock:
            if self.module_state() == 'idle':
                self.module_state.lock()
                self.elapsed_time = 0.0
                self.elapsed_time_str = '00:00:00:00'
                self.sigElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_time_str)
                # Clear previous fits
                self.fc.clear_result()
                # initialize plots
                self._initialize_plots()

                # recall stashed raw data
                if stashed_raw_data_tag is None:
                    self.recalled_raw_data = None
                elif stashed_raw_data_tag in self.saved_raw_data:
                    self.recalled_raw_data = self.saved_raw_data[stashed_raw_data_tag]
                    self.log.info('Starting pulsed measurement with stashed raw data "{0}".'
                                  ''.format(stashed_raw_data_tag))
                else:
                    self.recalled_raw_data = None

                # start microwave generator
                if self.use_ext_microwave:
                    self.microwave_on_off(True)

                # start fast counter
                self.fast_counter_on()
                # start pulse generator
                self.pulse_generator_on()

                self.start_time = time.time()

                # set analysis_timer
                if self.timer_interval > 0:
                    self.analysis_timer = QtCore.QTimer()
                    self.analysis_timer.setSingleShot(False)
                    self.analysis_timer.setInterval(int(1000. * self.timer_interval))
                    self.analysis_timer.timeout.connect(self._pulsed_analysis_loop, QtCore.Qt.QueuedConnection)
                    self.analysis_timer.start()
                else:
                    self.analysis_timer = None
        return

    def _pulsed_analysis_loop(self):
        """ Acquires laser pulses from fast counter,
            calculates fluorescence signal and creates plots.
        """
        with self.threadlock:
            if self.module_state() == 'locked':

                # get raw data from fast counter
                fc_data = netobtain(self._fast_counter_device.get_data_trace())

                # add old raw data from previous measurements if necessary
                if self.recalled_raw_data is not None:
                    self.log.info('Found old saved raw data. Sum of timebins: {0}'
                                  ''.format(np.sum(self.recalled_raw_data)))
                    if np.sum(fc_data) < 1.0:
                        self.log.warning('Only zeros received from fast counter!\n'
                                         'Only using old raw data.')
                        self.raw_data = self.recalled_raw_data
                    elif self.recalled_raw_data.shape == fc_data.shape:
                        self.log.debug('Saved raw data has same shape as current data.')
                        self.raw_data = self.recalled_raw_data + fc_data
                    else:
                        self.log.warning('Saved raw data has not the same shape as current data.\n'
                                         'Did NOT add old raw data to current timetrace.')
                        self.raw_data = fc_data
                elif np.sum(fc_data) < 1.0:
                    self.log.warning('Only zeros received from fast counter!')
                    self.raw_data = np.zeros(fc_data.shape, dtype=int)
                else:
                    self.raw_data = fc_data

                # extract laser pulses from raw data
                return_dict = self._pulse_extraction_logic.extract_laser_pulses(self.raw_data,
                                                                                self.fast_counter_gated)
                self.laser_data = return_dict['laser_counts_arr']

                # analyze pulses and get data points for signal plot. Also check if extraction
                # worked (non-zero array returned).
                if np.sum(self.laser_data) < 1:
                    tmp_signal = np.zeros(self.laser_data.shape[0])
                    tmp_error = np.zeros(self.laser_data.shape[0])
                else:
                    tmp_signal, tmp_error = self._pulse_analysis_logic.analyze_data(self.laser_data)
                # exclude laser pulses to ignore
                if len(self.laser_ignore_list) > 0:
                    ignore_indices = self.laser_ignore_list
                    if -1 in ignore_indices:
                        ignore_indices[ignore_indices.index(-1)] = len(ignore_indices) - 1
                    tmp_signal = np.delete(tmp_signal, ignore_indices)
                    tmp_error = np.delete(tmp_error, ignore_indices)
                # order data according to alternating flag
                if self.alternating:
                    self.signal_plot_y = tmp_signal[::2]
                    self.signal_plot_y2 = tmp_signal[1::2]
                    self.measuring_error_plot_y = tmp_error[::2]
                    self.measuring_error_plot_y2 = tmp_error[1::2]
                else:
                    self.signal_plot_y = tmp_signal
                    self.measuring_error_plot_y = tmp_error

                # set laser to show
                self.set_laser_to_show(self.show_laser_index, self.show_raw_data)

                # Compute FFT of signal
                self._compute_fft()

            # recalculate time
            self.elapsed_time = time.time() - self.start_time
            self.elapsed_time_str = ''
            self.elapsed_time_str += str(int(self.elapsed_time)//86400).zfill(2) + ':' # days
            self.elapsed_time_str += str((int(self.elapsed_time)//3600) % 24).zfill(2) + ':' # hours
            self.elapsed_time_str += str((int(self.elapsed_time)//60) % 60).zfill(2) + ':' # minutes
            self.elapsed_time_str += str(int(self.elapsed_time) % 60).zfill(2) # seconds

            # emit signals
            self.sigElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_time_str)
            self.sigSignalDataUpdated.emit(self.signal_plot_x, self.signal_plot_y,
                                           self.signal_plot_y2, self.measuring_error_plot_y,
                                           self.measuring_error_plot_y2, self.signal_fft_x,
                                           self.signal_fft_y, self.signal_fft_y2)
            return

    def set_laser_to_show(self, laser_index, show_raw_data):
        """

        @param laser_index:
        @param show_raw_data:

        @return:

        """
        self.show_raw_data = show_raw_data
        self.show_laser_index = laser_index
        if show_raw_data:
            if self.fast_counter_gated:
                if laser_index > 0:
                    self.laser_plot_y = self.raw_data[laser_index - 1]
                else:
                    self.laser_plot_y = np.sum(self.raw_data, 0)
            else:
                self.laser_plot_y = self.raw_data
        else:
            if laser_index > 0:
                self.laser_plot_y = self.laser_data[laser_index - 1]
            else:
                self.laser_plot_y = np.sum(self.laser_data, 0)


        self.laser_plot_x = np.arange(1, len(self.laser_plot_y) + 1) * self.fast_counter_binwidth

        self.sigLaserToShowUpdated.emit(self.show_laser_index, self.show_raw_data)
        self.sigLaserDataUpdated.emit(self.laser_plot_x, self.laser_plot_y)
        return self.laser_plot_x, self.laser_plot_y

    def stop_pulsed_measurement(self, stash_raw_data_tag=None):
        """ Stop the measurement
          @return int: error code (0:OK, -1:error)
        """
        if stash_raw_data_tag == '':
            stash_raw_data_tag = None
        with self.threadlock:
            if self.module_state() == 'locked':
                #stopping and disconnecting the timer
                if self.analysis_timer is not None:
                    self.analysis_timer.stop()
                    self.analysis_timer.timeout.disconnect()
                    self.analysis_timer = None

                self.fast_counter_off()
                self.pulse_generator_off()
                if self.use_ext_microwave:
                    self.microwave_on_off(False)

                # save raw data if requested
                if stash_raw_data_tag is not None:
                    self.log.info('sum of raw data with tag "{0}" to be saved for next measurement:'
                                  ' {1}'.format(stash_raw_data_tag, np.sum(self.raw_data.copy())))
                    self.saved_raw_data[stash_raw_data_tag] = self.raw_data.copy()
                self.recalled_raw_data = None

                self.module_state.unlock()
                self.sigMeasurementRunningUpdated.emit(False, False)
        return

    def pause_pulsed_measurement(self):
        """ Pauses the measurement
          @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                #pausing the timer
                if self.analysis_timer is not None:
                    self.analysis_timer.stop()

                self.fast_counter_pause()
                self.pulse_generator_off()
                if self.use_ext_microwave:
                    self.microwave_on_off(False)

                self.sigMeasurementRunningUpdated.emit(True, True)
        return 0

    def continue_pulsed_measurement(self):
        """ Continues the measurement
          @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                if self.use_ext_microwave:
                    self.microwave_on_off(True)
                self.fast_counter_continue()
                self.pulse_generator_on()

                #unpausing the timer
                if self.analysis_timer is not None:
                    self.analysis_timer.start()

                self.sigMeasurementRunningUpdated.emit(True, False)
        return 0

    def set_timer_interval(self, interval):
        """ Change the interval of the timer

        @param int interval: Interval of the timer in s

        """
        with self.threadlock:
            self.timer_interval = interval
            if self.analysis_timer is not None:
                if self.timer_interval > 0:
                    self.analysis_timer.setInterval(int(1000. * self.timer_interval))
                else:
                    self.analysis_timer = None
            self.sigTimerIntervalUpdated.emit(self.timer_interval)
        return

    def manually_pull_data(self):
        """ Analyse and display the data
        """
        if self.module_state() == 'locked':
            self._pulsed_analysis_loop()
        return

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

    def _initialize_plots(self):
        """
        Initializing the signal, error and laser plot data.
        """
        self.signal_plot_x = self.controlled_vals
        self.signal_plot_y = np.zeros(len(self.controlled_vals))
        self.signal_plot_y2 = np.zeros(len(self.controlled_vals))
        self.measuring_error_plot_y = np.zeros(len(self.controlled_vals), dtype=float)
        self.measuring_error_plot_y2 = np.zeros(len(self.controlled_vals), dtype=float)
        number_of_bins = int(self.fast_counter_record_length / self.fast_counter_binwidth)
        self.laser_plot_x = np.arange(1, number_of_bins + 1, dtype=int) * self.fast_counter_binwidth
        self.laser_plot_y = np.zeros(number_of_bins, dtype=int)
        self.signal_fft_x = self.controlled_vals
        self.signal_fft_y = np.zeros(len(self.controlled_vals))
        self.signal_fft_y2 = np.zeros(len(self.controlled_vals))

        self.sigSignalDataUpdated.emit(self.signal_plot_x, self.signal_plot_y, self.signal_plot_y2,
                                       self.measuring_error_plot_y, self.measuring_error_plot_y2,
                                       self.signal_fft_x, self.signal_fft_y, self.signal_fft_y2)
        self.sigLaserDataUpdated.emit(self.laser_plot_x, self.laser_plot_y)
        return

    def save_measurement_data(self, controlled_val_unit='arb.u.', tag=None,
                              with_error=True, save_ft=None):
        """ Prepare data to be saved and create a proper plot of the data

        @param str controlled_val_unit: unit of the x axis of the plot
        @param str tag: a filetag which will be included in the filename
        @param bool with_error: select whether errors should be saved/plotted

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
            parameters['threshold_tolerance_bins'] =\
                self._pulse_extraction_logic.extraction_settings['threshold_tolerance_bins']
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
        if save_ft is None:
            save_ft = self.save_ft

        # Create the figure object
        if save_ft:
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
        if save_ft:

            # scale the x_axis for plotting
            max_val = np.max(self.signal_fft_x)
            scaled_float = units.ScaledFloat(max_val)
            x_axis_prefix = scaled_float.scale
            x_axis_ft_scaled = self.signal_fft_x / scaled_float.scale_val

            ax2.plot(x_axis_ft_scaled, self.signal_fft_y, '-o',
                     linestyle=':', linewidth=0.5, color=colors[0],
                     label='FT of data trace 1')

            # since no ft units are provided, make a small work around:
            if controlled_val_unit == 's':
                inverse_cont_var = 'Hz'
            elif controlled_val_unit == 'Hz':
                inverse_cont_var = 's'
            else:
                inverse_cont_var = '(1/{0})'.format(controlled_val_unit)

            ax2.set_xlabel('Fourier Transformed controlled variable (' + x_axis_prefix + inverse_cont_var + ')')
            ax2.set_ylabel('Fourier amplitude (arb.u.)')
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
        parameters['Is counter gated?'] = self.fast_counter_gated
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

    def _compute_fft(self):
        """ Computing the fourier transform of the data. """

        # Do sanity checks:
        if len(self.signal_plot_x) < 2:
            self.log.debug('FFT of measurement could not be calculated. Only '
                           'one data point.')
            self.signal_fft_x = np.zeros(1)
            self.signal_fft_y = np.zeros(1)
            self.signal_fft_y2 = np.zeros(1)
            return

        if self.alternating:
            x_val_dummy, self.signal_fft_y2 = units.compute_ft(
                self.signal_plot_x,
                self.signal_plot_y2,
                zeropad_num=0)

        self.signal_fft_x, self.signal_fft_y = units.compute_ft(
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
