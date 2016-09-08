# -*- coding: utf-8 -*-
"""
This file contains the QuDi logic which controls all pulsed measurements.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import time
import datetime
import matplotlib.pyplot as plt

from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic

class PulsedMeasurementLogic(GenericLogic):
    """unstable: Nikolas Tomek
    This is the Logic class for the control of pulsed measurements.
    """
    _modclass = 'PulsedMeasurementLogic'
    _modtype = 'logic'

    ## declare connectors
    _in = {'pulseanalysislogic': 'PulseAnalysisLogic',
           'fitlogic': 'FitLogic',
           'savelogic': 'SaveLogic',
           'fastcounter': 'FastCounterInterface',
           'microwave': 'MWInterface',
           'pulsegenerator': 'PulserInterface',
            }
    _out = {'pulsedmeasurementlogic': 'PulsedMeasurementLogic'}

    signal_time_updated = QtCore.Signal()
    sigSinglePulsesUpdated = QtCore.Signal()
    sigPulseAnalysisUpdated = QtCore.Signal()
    sigMeasuringErrorUpdated = QtCore.Signal()
    sigLoadedAssetUpdated = QtCore.Signal()
    sigUploadAssetComplete = QtCore.Signal()
    sigLoadAssetComplete = QtCore.Signal()
    sigFitUpdated = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))

        # microwave parameters
        self.use_ext_microwave = False
        self.microwave_power = -30.     # dbm  (always in SI!)
        self.microwave_freq = 2870e6    # Hz   (always in SI!)

        # fast counter status variables
        self.fast_counter_status = None     # 0=unconfigured, 1=idle, 2=running, 3=paused, -1=error
        self.fast_counter_gated = None      # gated=True, ungated=False
        self.fast_counter_binwidth = 1e-9   # in seconds

        # parameters of the currently running sequence
        self.measurement_ticks_list = np.array(range(50))
        self.number_of_lasers = 50
        self.sequence_length_s = 100e-6
        self.laser_length_s = 3.e-6
        self.loaded_asset_name = None
        self.alternating = False

        # Pulse generator parameters
        self.current_channel_config_name = None
        self.sample_rate = 25e9

        # setup parameters
        self.laser_trigger_delay_s = 0.7e-6

        # timer for data analysis
        self.analysis_timer = None
        self.timer_interval = 5 # in seconds

        #timer for time
        self.start_time = 0
        self.elapsed_time = 0
        self.elapsed_time_str = '00:00:00:00'
        self.elapsed_sweeps = 0

        # analyze windows for laser pulses
        self.signal_start_bin = 5
        self.signal_width_bin = 200
        self.norm_start_bin = 300
        self.norm_width_bin = 200

        # pulse extraction parameters
        self.conv_std_dev = 10
        self.conv_std_dev_range_min = 1
        self.conv_std_dev_range_max = 500

        # threading
        self.threadlock = Mutex()

        # plot data
        self.signal_plot_x = None
        self.signal_plot_y = None
        self.signal_plot_y2 = None
        self.measuring_error_plot_x = None
        self.measuring_error_plot_y = None
        self.laser_plot_x = None
        self.laser_plot_y = None

        # raw data
        self.laser_data = np.zeros((10, 20))
        self.raw_data = np.zeros((10, 20))
        self.raw_laser_pulse = False

        # for fit:
        self._fit_param = {}
        self.signal_plot_x_fit = None
        self.signal_plot_y_fit = None

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        # get all the connectors:
        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
        self._fast_counter_device = self.connector['in']['fastcounter']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._pulse_generator_device = self.connector['in']['pulsegenerator']['object']
        self._mycrowave_source_device = self.connector['in']['microwave']['object']

        # Recall saved status variables
        if 'signal_start_bin' in self._statusVariables:
            self.signal_start_bin = self._statusVariables['signal_start_bin']
        if 'signal_width_bin' in self._statusVariables:
            self.signal_width_bin = self._statusVariables['signal_width_bin']
        if 'norm_start_bin' in self._statusVariables:
            self.norm_start_bin = self._statusVariables['norm_start_bin']
        if 'norm_width_bin' in self._statusVariables:
            self.norm_width_bin = self._statusVariables['norm_width_bin']
        if 'number_of_lasers' in self._statusVariables:
            self.number_of_lasers = self._statusVariables['number_of_lasers']
        if 'conv_std_dev' in self._statusVariables:
            self.conv_std_dev = self._statusVariables['conv_std_dev']
        if 'laser_trigger_delay_s' in self._statusVariables:
            self.laser_trigger_delay_s = self._statusVariables['laser_trigger_delay_s']
        if 'laser_length_s' in self._statusVariables:
            self.laser_length_s = self._statusVariables['laser_length_s']
        if 'sequence_length_s' in self._statusVariables:
            self.sequence_length_s = self._statusVariables['sequence_length_s']
        if 'measurement_ticks_list' in self._statusVariables:
            self.measurement_ticks_list = np.array(self._statusVariables['measurement_ticks_list'])
        if 'fast_counter_binwidth' in self._statusVariables:
            self.fast_counter_binwidth = self._statusVariables['fast_counter_binwidth']
        if 'microwave_power' in self._statusVariables:
            self.microwave_power = self._statusVariables['microwave_power']
        if 'microwave_freq' in self._statusVariables:
            self.microwave_freq = self._statusVariables['microwave_freq']
        if 'use_ext_microwave' in self._statusVariables:
            self.use_ext_microwave = self._statusVariables['use_ext_microwave']
        if 'current_channel_config_name' in self._statusVariables:
            self.current_channel_config_name = self._statusVariables['current_channel_config_name']
        if 'sample_rate' in self._statusVariables:
            self.sample_rate = self._statusVariables['sample_rate']
        if 'timer_interval' in self._statusVariables:
            self.timer_interval = self._statusVariables['timer_interval']
        if 'alternating' in self._statusVariables:
            self.alternating = self._statusVariables['alternating']

        # Check and configure pulse generator
        avail_activation_configs = self.get_pulser_constraints()['activation_config']
        if self.get_sample_rate() != self.sample_rate:
            self.sample_rate = self.set_sample_rate(self.sample_rate)
        if self.current_channel_config_name not in avail_activation_configs:
            self.current_channel_config_name = list(avail_activation_configs)[0]
        self.set_activation_config(self.current_channel_config_name)
        self.loaded_asset_name = self._pulse_generator_device.get_loaded_asset()

        # Check and configure fast counter
        self.fast_counter_gated = self._fast_counter_device.is_gated()
        binning_constraints = self.get_fastcounter_constraints()['hardware_binwidth_list']
        if self.fast_counter_binwidth not in binning_constraints:
            self.fast_counter_binwidth = binning_constraints[0]
        self.configure_fast_counter()

        # Check and configure external microwave
        if self.use_ext_microwave:
            self.microwave_off()
            self.set_microwave_params(self.microwave_freq, self.microwave_power)

        # initialize arrays for the plot data
        self._initialize_signal_plot()
        self._initialize_laser_plot()
        self._initialize_measuring_error_plot()


    def on_deactivate(self, e):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method activation.
        """

        with self.threadlock:
            if self.getState() != 'idle' and self.getState() != 'deactivated':
                self.stop_pulsed_measurement()

        self._statusVariables['signal_start_bin'] = self.signal_start_bin
        self._statusVariables['signal_width_bin'] = self.signal_width_bin
        self._statusVariables['norm_start_bin'] = self.norm_start_bin
        self._statusVariables['norm_width_bin'] = self.norm_width_bin
        self._statusVariables['number_of_lasers'] = self.number_of_lasers
        self._statusVariables['conv_std_dev'] = self.conv_std_dev
        self._statusVariables['laser_trigger_delay_s'] = self.laser_trigger_delay_s
        self._statusVariables['laser_length_s'] = self.laser_length_s
        self._statusVariables['sequence_length_s'] = self.sequence_length_s
        self._statusVariables['measurement_ticks_list'] = list(self.measurement_ticks_list)
        self._statusVariables['fast_counter_binwidth'] = self.fast_counter_binwidth
        self._statusVariables['microwave_power'] = self.microwave_power
        self._statusVariables['microwave_freq'] = self.microwave_freq
        self._statusVariables['use_ext_microwave'] = self.use_ext_microwave
        self._statusVariables['current_channel_config_name'] = self.current_channel_config_name
        self._statusVariables['sample_rate'] = self.sample_rate
        self._statusVariables['timer_interval'] = self.timer_interval
        self._statusVariables['alternating'] = self.alternating

    ############################################################################
    # Fast counter control methods
    ############################################################################
    def update_fast_counter_status(self):
        """ Captures the fast counter status and update the corresponding class variables
        """
        self.fast_counter_status = self._fast_counter_device.get_status()
        return

    def configure_fast_counter(self):
        """ Configure the fast counter and updates the actually set values in
            the class variables.
        """
        if self.fast_counter_gated:
            record_length_s = self.laser_trigger_delay_s + self.laser_length_s
            number_of_gates = self.number_of_lasers
        else:
            record_length_s = self.laser_trigger_delay_s + self.sequence_length_s
            number_of_gates = 0

        actual_binwidth_s, actual_recordlength_s, actual_numofgates = self._fast_counter_device.configure(self.fast_counter_binwidth , record_length_s, number_of_gates)

        # use the actual parameters returned by the hardware
        self.fast_counter_binwidth = actual_binwidth_s
        self.update_fast_counter_status()
        return

    def set_fc_binning(self, fc_binning):
        """ If the FC binning has be changed in the GUI, inform analysis

        @param float fc_binning: Binning of fast counter in s

        """
        self.fast_counter_binwidth = fc_binning
        self.configure_fast_counter()
        return

    def set_laser_trigger_delay(self, laser_trigger_delay_s):
        """
        Sets the delay between the laser trigger going high and the actual optical laser output
        rising.
        @param laser_trigger_delay_s: float, The delay to set in seconds
        """
        self.laser_trigger_delay_s = laser_trigger_delay_s
        self.configure_fast_counter()
        return

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
        self.update_fast_counter_status()
        return error_code

    def fast_counter_off(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.stop_measure()
        self.update_fast_counter_status()
        return error_code

    def fast_counter_pause(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.pause_measure()
        self.update_fast_counter_status()
        return error_code

    def fast_counter_continue(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.continue_measure()
        self.update_fast_counter_status()
        return error_code
    ############################################################################


    ############################################################################
    # Pulse generator control methods
    ############################################################################
    def pulse_generator_on(self):
        """Switching on the pulse generator. """

        err = self._pulse_generator_device.pulser_on()
        return err

    def pulse_generator_off(self):
        """Switching off the pulse generator. """

        err = self._pulse_generator_device.pulser_off()
        return err

    def get_pulser_constraints(self):
        """ Request the constrains from the pulse generator hardware.

        @return: dict where the keys in it are predefined in the interface.
        """
        return self._pulse_generator_device.get_constraints()

    def set_sample_rate(self, freq_Hz):
        """
        Sets the sampling frequency of the pulse generator device in Hz.
        """
        actual_sample_rate = self._pulse_generator_device.set_sample_rate(freq_Hz)
        return actual_sample_rate

    def get_sample_rate(self):
        """
        Gets the sampling frequency from the pulse generator device in Hz.
        """
        sample_rate = self._pulse_generator_device.get_sample_rate()
        return sample_rate

    def set_activation_config(self, activation_config_name):
        """
        Set a new channel config in the logic and activate the proper channels in the pulse
        generator device.

        @param activation_config: strings representing the channels config as described in the
        constraint dictionary of the hardware.
        @return: error code (0: OK, -1: error)
        """
        avail_activation_configs = self.get_pulser_constraints()['activation_config']
        if activation_config_name not in avail_activation_configs:
            self.log.error('Chosen activation_config "{0}" is not available '
                    'in the pulser constraints. Please select one of the '
                    'following activation_configs:\n{1}'.format(
                        activation_config_name,
                        list(avail_activation_configs)))
            return -1
        config_to_set = avail_activation_configs[activation_config_name]
        channel_activation = self.get_active_channels()
        for chnl in channel_activation:
            if chnl in config_to_set:
                channel_activation[chnl] = True
            else:
                channel_activation[chnl] = False
        err = self.set_active_channels(channel_activation)
        self.current_channel_config_name = activation_config_name
        return err

    def set_active_channels(self, ch=None):
        """ Set the active channels for the pulse generator hardware.

        @param dict ch: dictionary with keys being the string generic analog
                          and digital names and items being its boolean value.

        @return int: error code (0:OK, -1:error)

        Example for possible input:
            ch={'a_ch2': True, 'd_ch1': False, 'd_ch3': True, 'd_ch4': True}
        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1.

        Additionally the variables which hold this values are updated in the
        logic.
        """
        if ch is None:
            ch = {}
        self._pulse_generator_device.set_active_channels(ch)
        return 0

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
        err = self._pulse_generator_device.clear_all()
        self.loaded_asset_name = None
        return err

    def get_interleave(self):
        """ Get the interleave state.

        @return bool, state of the interleave, True=Interleave On, False=OFF
        """
        return self._pulse_generator_device.get_interleave()

    def set_interleave(self, interleave_state=False):
        """ Set the interleave state.

        @param bool interleave_state: If nothing passed, interleave will be switched off.
        """
        err = self._pulse_generator_device.set_interleave(interleave_state)
        return err

    def upload_asset(self, asset_name):
        """ Upload an already sampled Ensemble or Sequence object to the device.
            Does NOT load it into channels.

        @param asset_name: string, name of the ensemble/sequence to upload
        """
        err = self._pulse_generator_device.upload_asset(asset_name)
        self.sigUploadAssetComplete.emit()
        return err

    def upload_sequence(self, seq_name):
        """ Upload a sequence and all its related files

        @param str seq_name: name of the sequence to be uploaded
        """

        current_sequence = self.get_pulse_sequence(seq_name)

        for ensemble_name in current_sequence.get_sampled_ensembles():
            self._pulse_generator_device.upload_asset(ensemble_name)

        self._pulse_generator_device.upload_asset(seq_name)
        self.sigUploadAssetComplete.emit()

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
        if load_dict is None:
            load_dict = {}
        # load asset in channels
        err = self._pulse_generator_device.load_asset(asset_name, load_dict)
        # set the loaded_asset_name variable.
        self.loaded_asset_name = self._pulse_generator_device.get_loaded_asset()
        self.sigLoadAssetComplete.emit()
        return err

    ############################################################################

    ############################################################################
    # External microwave control methods
    ############################################################################
    def microwave_on(self):
        self._mycrowave_source_device.on()
        return

    def microwave_off(self):
        self._mycrowave_source_device.off()
        return

    def set_microwave_params(self, frequency=None, power=None):
        self._mycrowave_source_device.set_cw(freq=frequency, power=power)
        self.microwave_freq = frequency
        self.microwave_power = power
        return

    ############################################################################


    def start_pulsed_measurement(self):
        """Start the analysis thread. """
        #FIXME: Describe the idea of how the measurement is intended to be run
        #       and how the used thread principle was used in this method (or
        #       will be use in another method).

        with self.threadlock:
            if self.getState() == 'idle':
                self.elapsed_time = 0.0
                # initialize plots
                self._initialize_signal_plot()
                self._initialize_laser_plot()
                self._initialize_measuring_error_plot()

                # start microwave generator
                if self.use_ext_microwave:
                    self.microwave_on()

                # start fast counter
                self.fast_counter_on()
                # start pulse generator
                self.pulse_generator_on()

                # set analysis_timer
                self.analysis_timer = QtCore.QTimer()
                self.analysis_timer.setSingleShot(False)
                self.analysis_timer.setInterval(int(1000. * self.timer_interval))
                self.analysis_timer.timeout.connect(self._pulsed_analysis_loop, QtCore.Qt.QueuedConnection)

                self.lock()
                self.start_time = time.time()
                self.analysis_timer.start()
        return

    def _pulsed_analysis_loop(self):
        """ Acquires laser pulses from fast counter,
            calculates fluorescence signal and creates plots.
        """
        with self.threadlock:
            # calculate analysis windows
            sig_start = self.signal_start_bin
            sig_end = self.signal_start_bin + self.signal_width_bin
            norm_start = self.norm_start_bin
            norm_end = self.norm_start_bin + self.norm_width_bin
            conv_std_dev = self.conv_std_dev

            # analyze pulses and get data points for signal plot
            tmp_signal,self.laser_data,self.raw_data,tmp_error = self._pulse_analysis_logic._analyze_data(norm_start,
                                                                                                          norm_end,
                                                                                                          sig_start,
                                                                                                          sig_end,
                                                                                                          self.number_of_lasers,
                                                                                                          conv_std_dev)

            if self.alternating:
                self.signal_plot_y = tmp_signal[::2]
                self.signal_plot_y2 = tmp_signal[1::2]
                self.measuring_error = tmp_error[::2]
            else:
                self.signal_plot_y = tmp_signal
                self.measuring_error = tmp_error

            # recalculate time
            self.elapsed_time = time.time() - self.start_time
            self.elapsed_time_str = ''
            self.elapsed_time_str += str(int(self.elapsed_time)//86400).zfill(2) + ':' # days
            self.elapsed_time_str += str(int(self.elapsed_time)//3600).zfill(2) + ':' # hours
            self.elapsed_time_str += str(int(self.elapsed_time)//60).zfill(2) + ':' # minutes
            self.elapsed_time_str += str(int(self.elapsed_time) % 60).zfill(2) # seconds
            # has to be changed. just for testing purposes

            # emit signals
            self.sigSinglePulsesUpdated.emit()
            self.sigPulseAnalysisUpdated.emit()
            self.sigMeasuringErrorUpdated.emit()
            self.signal_time_updated.emit()
            return

    def get_laserpulse(self, laser_num=0):
        """ Get the laserpulse with the appropriate number.

        @param int num: number of laserpulse, to be displayed, if zero is passed
                        then the sum off all laserpulses is calculated.
        @return: tuple of 1D arrays, first one is x data, second is y data of
                                     currently selected laser.
        """

        if self.raw_laser_pulse:

            if self.fast_counter_gated:
                if laser_num > 0:
                    self.laser_plot_y = self.raw_data[laser_num-1]
                else:
                    self.laser_plot_y = np.sum(self.raw_data,0)
            else:
                self.laser_plot_y = self.raw_data

        else:
            # set laser plot
            if laser_num > 0:
                self.laser_plot_y = self.laser_data[laser_num-1]
            else:
                self.laser_plot_y = np.sum(self.laser_data,0)

        self.laser_plot_x = np.arange(1, len(self.laser_plot_y)+1)

        return self.laser_plot_x, self.laser_plot_y

    def stop_pulsed_measurement(self):
        """ Stop the measurement
          @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                #stopping and disconnecting the timer
                self.analysis_timer.stop()
                self.analysis_timer.timeout.disconnect()
                self.analysis_timer = None

                self.fast_counter_off()
                self.pulse_generator_off()

                if self.use_ext_microwave:
                    self.microwave_off()

                self.sigPulseAnalysisUpdated.emit()
                self.sigMeasuringErrorUpdated.emit()
                self.unlock()

    def pause_pulsed_measurement(self):
        """ Pauses the measurement
          @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                #pausing the timer
                self.analysis_timer.stop()

                self.fast_counter_pause()
                self.pulse_generator_off()

                if self.use_ext_microwave:
                    self.microwave_off()

                self.sigPulseAnalysisUpdated.emit()
                self.sigMeasuringErrorUpdated.emit()
                self.unlock()
        return 0

    def continue_pulsed_measurement(self):
        """ Continues the measurement
          @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            #if self.getState() == 'pause':

            if self.use_ext_microwave:
                self.microwave_on()

            self.fast_counter_continue()
            self.pulse_generator_on()

            #unpausing the timer
            self.analysis_timer.start()

            self.lock()
        return 0

    def set_timer_interval(self, interval):
        """ Change the interval of the timer

        @param int interval: Interval of the timer in s

        """
        with self.threadlock:
            self.timer_interval = interval
            if self.analysis_timer is not None:
                self.analysis_timer.setInterval(int(1000. * self.timer_interval))
        return

    def manually_pull_data(self):
        """ Analyse and display the data
        """
        if self.getState() == 'locked':
            self._pulsed_analysis_loop()
        return

    def set_num_of_lasers(self, num_of_lasers):
        """ Sets the number of lasers needed for the pulse extraction and the fast counter.

        @param int num_of_lasers: Number of laser pulses
        """
        int_num = int(num_of_lasers)
        if int_num < 1:
            self.log.error('Invalid number of laser pulses set in the '
                    'pulsed_measurement_logic! A value of {0} was provided '
                    'but an interger value in the range [1,inf) is '
                    'expected! Set number_of_pulses to '
                    '1.'.format(int_num))
            self.number_of_lasers = 1
        else:
            self.number_of_lasers = int_num

        self.configure_fast_counter()
        return

    def set_laser_length(self, laser_length_s):
        """
        Sets a new laser length for the measurement and reconfigures the fast counter accordingly
        if it is gated.
        @param laser_length_s: float, the laser length in seconds
        @return:
        """
        if laser_length_s > 0.:
            self.laser_length_s = laser_length_s
        else:
            self.log.error('Invalid laser length. Tried to set a value of '
                    '{0}s. Setting laser length to 3000ns instead.'.format(
                        laser_length_s))
            self.laser_length_s = 3e-6

        if self.fast_counter_gated:
            self.configure_fast_counter()

    def set_measurement_ticks_list(self, ticks_array):
        """ Sets the ticks for the x-axis of the pulsed measurement.

        Handle with care to ensure that the number of ticks is the same as the number of
        laser pulses to avoid array mismatch conflicts.

        @param ticks_array: a numpy array containing the ticks
        """
        self.measurement_ticks_list = np.array(ticks_array)
        return

    def _initialize_signal_plot(self):
        '''Initializing the signal line plot.
        '''
        self.signal_plot_x = self.measurement_ticks_list
        self.signal_plot_y = np.zeros(len(self.measurement_ticks_list))
        self.signal_plot_y2 = np.zeros(len(self.measurement_ticks_list))
        return

    def _initialize_laser_plot(self):
        '''Initializing the plot of the laser timetrace.
        '''
        number_of_bins_per_laser=int(self.laser_length_s/(self.fast_counter_binwidth))
        self.laser_plot_x = np.arange(1, number_of_bins_per_laser+1, dtype=int)
        self.laser_plot_y = np.zeros(number_of_bins_per_laser, dtype=int)
        return

    def _initialize_measuring_error_plot(self):
        '''Initializing the plot of the laser timetrace.
        '''
        self.measuring_error_plot_x = self.measurement_ticks_list
        self.measuring_error_plot_y =  np.zeros(len(self.measurement_ticks_list), dtype=float)
        return


    def _save_data(self, tag=None, timestamp=None):

        #####################################################################
        ####                Save extracted laser pulses                  ####
        #####################################################################
        filepath = self._save_logic.get_path_for_module(module_name='PulsedMeasurement')
        if timestamp is None:
            timestamp = datetime.datetime.now()

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_laser_pulses'
        else:
            filelabel = 'laser_pulses'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Signal (counts)': self.laser_data.transpose()}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Bin size (ns)'] = self.fast_counter_binwidth*1e9
        parameters['laser length (ns)'] = self.fast_counter_binwidth*1e9 * self.laser_plot_x.size

        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':')#, as_xml=False, precision=None, delimiter=None)

        #####################################################################
        ####                Save measurement data                        ####
        #####################################################################
        if tag is not None and len(tag) > 0:
            filelabel = tag + '_pulsed_measurement'
        else:
            filelabel = 'pulsed_measurement'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        if self.alternating:
            data = {'Tau (ns), Signal (norm.), Signal2 (norm.)': np.array(
                [self.signal_plot_x, self.signal_plot_y, self.signal_plot_y2]).transpose()}
        else:
            data = {'Tau (ns), Signal (norm.)': np.array(
                [self.signal_plot_x, self.signal_plot_y]).transpose()}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Bin size (ns)'] = self.fast_counter_binwidth*1e9
        parameters['Number of laser pulses'] = self.number_of_lasers
        parameters['Signal start (bin)'] = self.signal_start_bin
        parameters['Signal width (bins)'] = self.signal_width_bin
        parameters['Normalization start (bin)'] = self.norm_start_bin
        parameters['Normalization width (bins)'] = self.norm_width_bin
        parameters['Standard deviation of gaussian convolution'] = self.conv_std_dev

        # Prepare the figure to save as a "data thumbnail"
        plt.style.use(self._save_logic.mpl_qd_style)
        fig, ax1 = plt.subplots()
        ax1.plot(self.signal_plot_x, self.signal_plot_y)
        if self.alternating:
            ax1.plot(self.signal_plot_x, self.signal_plot_y2)
        ax1.set_xlabel('x-axis')
        ax1.set_ylabel('norm. sig (a.u.)')
        # ax1.set_xlim(self.plot_domain)
        # ax1.set_ylim(self.plot_range)
        fig.tight_layout()

        self._save_logic.save_data(data, filepath, parameters=parameters, filelabel=filelabel,
                                   timestamp=timestamp, as_text=True, plotfig=fig, precision=':.6f')
        plt.close(fig)

        #####################################################################
        ####                Save raw data timetrace                      ####
        #####################################################################
        if tag is not None and len(tag) > 0:
            filelabel = tag + '_raw_timetrace'
        else:
            filelabel = 'raw_timetrace'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Signal (counts)': self.raw_data.transpose()}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Is counter gated?'] = self.fast_counter_gated
        parameters['Is alternating?'] = self.alternating
        parameters['Bin size (ns)'] = self.fast_counter_binwidth*1e9
        parameters['Number of laser pulses'] = self.number_of_lasers
        parameters['laser length (ns)'] = self.fast_counter_binwidth*1e9 * self.laser_plot_x.size
        parameters['Measurement Ticks start'] = self.measurement_ticks_list[0]
        parameters['Measurement Ticks increment'] = self.measurement_ticks_list[1] - self.measurement_ticks_list[0]


        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':')#, as_xml=False, precision=None, delimiter=None)
        return

    def compute_fft(self):
        """ Computing the fourier transform of the data.

        @return tuple (fft_x, fft_y):
                    fft_x: the frequencies for the FT
                    fft_y: the FT spectrum

        Pay attention that the return values of the FT have only half of the
        entries compared to the used signal input.

        In general, a window function should be applied to the time domain data
        before calculating the FT, to reduce spectral leakage. The Hann window
        for instance is almost never a bad choice. Use it like:
            y_ft = np.fft.fft(y_signal * np.hanning(len(y_signal)))

        Keep always in mind the relation for the Fourier transform:
            T = delta_t * N_samples
        where delta_t is the distance between the time points and N_samples are
        the amount of points in the time domain. Consequently the sample rate is
            f_samplerate = T / N_samples

        Keep in mind that the FT returns value from 0 to f_samplerate, or
        equivalently -f_samplerate/2 to f_samplerate/2.


        """
        # Make a baseline correction to avoid a constant offset near zero
        # frequencies:
        mean_y = sum(self.signal_plot_y) / len(self.signal_plot_y)
        corrected_y = self.signal_plot_y - mean_y

        # The absolute values contain the fourier transformed y values
        fft_y = np.abs(np.fft.fft(corrected_y))

        # Due to the sampling theorem you can only identify frequencies at half
        # of the sample rate, therefore the FT contains an almost symmetric
        # spectrum (the asymmetry results from aliasing effects). Therefore take
        # the half of the values for the display.
        middle = int((len(corrected_y)+1)//2)

        # sample spacing of x_axis, if x is a time axis than it corresponds to a
        # timestep:
        x_spacing = np.round(self.signal_plot_x[-1] - self.signal_plot_x[-2], 12)

        # use the helper function of numpy to calculate the x_values for the
        # fourier space. That function will handle an occuring devision by 0:
        fft_x = np.fft.fftfreq(len(corrected_y), d=x_spacing)

        return abs(fft_x[:middle]), fft_y[:middle]

    def get_fit_functions(self):
        """Giving the available fit functions

        @return list of strings with all available fit functions

        """
        return ['No Fit', 'Sine', 'Cos_FixedPhase', 'Lorentian (neg)' , 'Lorentian (pos)', 'N14',
                'N15', 'Stretched Exponential', 'Exponential', 'XY8']


    def do_fit(self, fit_function, x_data=None, y_data=None,
               fit_granularity_fact=10):
        """Performs the chosen fit on the measured data.

        @param string fit_function: name of the chosen fit function

        @return float array pulsed_fit_x: Array containing the x-values of the fit
        @return float array pulsed_fit_y: Array containing the y-values of the fit
        @return str array pulsed_fit_result: String containing the fit parameters displayed in a nice form
        @return dict param_dict: a dictionary containing the fit result
        """

        # compute x-axis for fit:
        if x_data is None:
            x_data = self.signal_plot_x

        if y_data is None:
            y_data = self.signal_plot_y

        num_fit_points = int(fit_granularity_fact*len(x_data))
        pulsed_fit_x = np.linspace(start=x_data[0], stop=x_data[-1], num=num_fit_points)
        result = None

        # set the keyword arguments, which will be passed to the fit.
        kwargs = {'axis': x_data,
                  'data': y_data,
                  'add_parameters': None}

        param_dict = OrderedDict()

        if fit_function == 'No Fit':
            pulsed_fit_x = []
            pulsed_fit_y = []

        elif fit_function in ('Sine', 'Cos_FixedPhase'):
            update_dict = {}
            if fit_function == 'Cos_FixedPhase':
                # set some custom defined constraints for this module and for
                # this fit:
                update_dict['phase'] = {'vary': False, 'value': np.pi/2.}
                update_dict['amplitude'] = {'min': 0.0}

                # add to the keywords dictionary
                kwargs['add_parameters'] = update_dict

            result = self._fit_logic.make_sine_fit(**kwargs)
            sine, params = self._fit_logic.make_sine_model()
            pulsed_fit_y = sine.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Contrast'] = {'value': np.abs(2*result.params['amplitude'].value*100),
                                      'error': np.abs(2 * result.params['amplitude'].stderr*100),
                                      'unit' : '%'}
            param_dict['Frequency'] = {'value': result.params['frequency'].value,
                                       'error': result.params['frequency'].stderr,
                                       'unit' : 'Hz'}

            # use proper error propagation formula:
            error_per = 1/(result.params['frequency'].value)**2
            error_per = error_per * result.params['frequency'].stderr

            param_dict['Period'] = {'value': 1/result.params['frequency'].value,
                                    'error': error_per,
                                    'unit' : 's'}
            param_dict['Phase'] = {'value': result.params['phase'].value/np.pi *180,
                                   'error': result.params['phase'].stderr/np.pi *180,
                                   'unit' : '°'}
            param_dict['Offset'] = {'value': result.params['offset'].value,
                                    'error': result.params['offset'].stderr,
                                    'unit' : 'norm. signal'}

        elif fit_function == 'Lorentian (neg)':

            result = self._fit_logic.make_lorentzian_fit(**kwargs)
            lorentzian, params = self._fit_logic.make_lorentzian_model()
            pulsed_fit_y = lorentzian.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Minimum'] = {'value': result.params['center'].value,
                                     'error': result.params['center'].stderr,
                                     'unit' : 's'}
            param_dict['Linewidth'] = {'value': result.params['fwhm'].value,
                                       'error': result.params['fwhm'].stderr,
                                       'unit' : 's'}

            cont = result.params['amplitude'].value
            cont = cont/(-1*np.pi*result.params['sigma'].value*result.params['c'].value)

            # use gaussian error propagation for error calculation:
            cont_err = np.sqrt(
                  (cont / result.params['amplitude'].value * result.params['amplitude'].stderr)**2
                + (cont / result.params['sigma'].value * result.params['sigma'].stderr)**2
                + (cont / result.params['c'].value * result.params['c'].stderr)**2)

            param_dict['Contrast'] = {'value': cont*100,
                                      'error': cont_err*100,
                                      'unit' : '%'}


        elif fit_function == 'Lorentian (pos)':

            result = self._fit_logic.make_lorentzianpeak_fit(**kwargs)
            lorentzian, params = self._fit_logic.make_lorentzian_model()
            pulsed_fit_y = lorentzian.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Maximum'] = {'value': result.params['center'].value,
                                     'error': result.params['center'].stderr,
                                     'unit' : 's'}
            param_dict['Linewidth'] = {'value': result.params['fwhm'].value,
                                       'error': result.params['fwhm'].stderr,
                                       'unit' : 's'}

            cont = result.params['amplitude'].value
            cont = cont/(-1*np.pi*result.params['sigma'].value*result.params['c'].value)
            param_dict['Contrast'] = {'value': cont*100,
                                      'unit' : '%'}

        elif fit_function == 'N14':

            result = self._fit_logic.make_N14_fit(**kwargs)
            fitted_function, params = self._fit_logic.make_multiplelorentzian_model(no_of_lor=3)
            pulsed_fit_y = fitted_function.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Freq. 0'] = {'value': result.params['lorentz0_center'].value,
                                     'error': result.params['lorentz0_center'].stderr,
                                     'unit' : 'Hz'}
            param_dict['Freq. 1'] = {'value': result.params['lorentz1_center'].value,
                                     'error': result.params['lorentz1_center'].stderr,
                                     'unit' : 'Hz'}
            param_dict['Freq. 2'] = {'value': result.params['lorentz2_center'].value,
                                     'error': result.params['lorentz2_center'].stderr,
                                     'unit' : 'Hz'}

            cont0 = result.params['lorentz0_amplitude'].value
            cont0 = cont0/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)

            # use gaussian error propagation for error calculation:
            cont0_err = np.sqrt(
                  (cont0 / result.params['lorentz0_amplitude'].value * result.params['lorentz0_amplitude'].stderr) ** 2
                + (cont0 / result.params['lorentz0_sigma'].value * result.params['lorentz0_sigma'].stderr) ** 2
                + (cont0 / result.params['c'].value * result.params['c'].stderr) ** 2)

            param_dict['Contrast 0'] = {'value': cont0*100,
                                        'error': cont0_err*100,
                                        'unit' : '%'}

            cont1 = result.params['lorentz1_amplitude'].value
            cont1 = cont1/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)

            # use gaussian error propagation for error calculation:
            cont1_err = np.sqrt(
                  (cont1 / result.params['lorentz1_amplitude'].value * result.params['lorentz1_amplitude'].stderr) ** 2
                + (cont1 / result.params['lorentz1_sigma'].value * result.params['lorentz1_sigma'].stderr) ** 2
                + (cont1 / result.params['c'].value * result.params['c'].stderr) ** 2)

            param_dict['Contrast 1'] = {'value': cont1*100,
                                        'error': cont1_err*100,
                                        'unit' : '%'}

            cont2 = result.params['lorentz2_amplitude'].value
            cont2 = cont2/(-1*np.pi*result.params['lorentz2_sigma'].value*result.params['c'].value)

            # use gaussian error propagation for error calculation:
            cont2_err = np.sqrt(
                  (cont2 / result.params['lorentz2_amplitude'].value * result.params['lorentz2_amplitude'].stderr) ** 2
                + (cont2 / result.params['lorentz2_sigma'].value * result.params['lorentz2_sigma'].stderr) ** 2
                + (cont2 / result.params['c'].value * result.params['c'].stderr) ** 2)

            param_dict['Contrast 2'] = {'value': cont2*100,
                                        'error': cont2_err*100,
                                        'unit' : '%'}

        elif fit_function =='N15':

            result = self._fit_logic.make_N15_fit(**kwargs)
            fitted_function, params = self._fit_logic.make_multiplelorentzian_model(no_of_lor=2)
            pulsed_fit_y = fitted_function.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Freq. 0'] = {'value': result.params['lorentz0_center'].value,
                                     'error': result.params['lorentz0_center'].stderr,
                                     'unit' : 'Hz'}
            param_dict['Freq. 1'] = {'value': result.params['lorentz1_center'].value,
                                     'error': result.params['lorentz1_center'].stderr,
                                     'unit' : 'Hz'}

            cont0 = result.params['lorentz0_amplitude'].value
            cont0 = cont0/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)

            # use gaussian error propagation for error calculation:
            cont0_err = np.sqrt(
                  (cont0 / result.params['lorentz0_amplitude'].value * result.params['lorentz0_amplitude'].stderr) ** 2
                + (cont0 / result.params['lorentz0_sigma'].value * result.params['lorentz0_sigma'].stderr) ** 2
                + (cont0 / result.params['c'].value * result.params['c'].stderr) ** 2)

            param_dict['Contrast 0'] = {'value': cont0*100,
                                        'error': cont0_err*100,
                                        'unit' : '%'}

            cont1 = result.params['lorentz1_amplitude'].value
            cont1 = cont1/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)

            # use gaussian error propagation for error calculation:
            cont1_err = np.sqrt(
                  (cont1 / result.params['lorentz1_amplitude'].value * result.params['lorentz1_amplitude'].stderr) ** 2
                + (cont1 / result.params['lorentz1_sigma'].value * result.params['lorentz1_sigma'].stderr) ** 2
                + (cont1 / result.params['c'].value * result.params['c'].stderr) ** 2)

            param_dict['Contrast 1'] = {'value': cont1*100,
                                        'error': cont1_err*100,
                                        'unit' : '%'}

        elif fit_function =='Stretched Exponential':
            self.log.warning('Stretched Exponential not yet implemented.')
            pulsed_fit_x = []
            pulsed_fit_y = []

        elif fit_function =='Exponential':
            self.log.warning('Exponential not yet implemented.')
            pulsed_fit_x = []
            pulsed_fit_y = []

        elif fit_function =='XY8':
            self.log.warning('XY8 not yet implemented')
            pulsed_fit_x = []
            pulsed_fit_y = []
        else:
            self.log.warning('The Fit Function "{0}" is not implemented to '
                    'be used in the Pulsed Measurement Logic. Correct that! '
                    'Fit Call will be skipped and Fit Function will be set '
                    'to "No Fit".'.format(fit_function))
            pulsed_fit_x = []
            pulsed_fit_y = []

        self.signal_plot_x_fit = pulsed_fit_x
        self.signal_plot_y_fit = pulsed_fit_y

        self.sigFitUpdated.emit()

        return pulsed_fit_x, pulsed_fit_y, param_dict, result
