# -*- coding: utf-8 -*-

"""
This file contains the Qudi interfuse to provide a MicrowaveInterface using AWG hardware.

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

import numpy as np
import re

from core.module import Connector, ConfigOption
from core.util.helpers import natural_sort
from logic.generic_logic import GenericLogic
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import TriggerEdge, MicrowaveMode, MicrowaveLimits
from logic.pulsed.pulse_objects import SequenceStep


class MicrowaveAwgInterfuse(GenericLogic, MicrowaveInterface):
    """
    Interfuse to enable the use of AWG hardware with the MicrowaveInterface.

    This interfuse connects the ODMR logic with a slowcounter and a microwave
    device.
    """

    _modclass = 'MicrowaveAwgInterfuse'
    _modtype = 'interfuse'

    _microwave_channel = ConfigOption(name='microwave_channel', default='a_ch1', missing='warn')
    _laser_channel = ConfigOption(name='laser_channel', default='d_ch1', missing='warn')
    _max_waveform_length = ConfigOption(name='max_waveform_length', default=None, missing='warn')
    _event_trigger = ConfigOption(name='event_trigger', missing='error')

    awg = Connector(interface='PulserInterface')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.__current_mode = MicrowaveMode.CW
        self._cw_parameters = {'frequency': 2.87e9, 'power': 0}
        self._sweep_parameters = {'start': 2.77e9, 'stop': 2.97e9, 'step': 1e6, 'power': 0}
        self._list_parameters = {'frequency': [2.87e9], 'power': 0}

        self._cw_waveforms = list()
        self._list_waveforms = list()
        self._list_sequence = None
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module."""
        # Check microwave and laser channel
        if not self._microwave_channel.startswith('a_ch'):
            self.log.error(
                'AWG channel to use as microwave channel must be analog channel of form "a_ch<n>".')
        if not self._laser_channel.startswith('d_ch'):
            self.log.error(
                'AWG channel to use as laser channel must be digital channel of form "d_ch<n>".')

        mw_channel_invalid = True
        laser_channel_invalid = True
        for channel_set in self.awg().get_constraints().activation_config.values():
            if self._microwave_channel in channel_set:
                mw_channel_invalid = False
            if self._laser_channel in channel_set:
                laser_channel_invalid = False
        if mw_channel_invalid:
            self.log.error('AWG channel "{0}" to use as microwave channel not found in available '
                           'activation configs.'.format(self._microwave_channel))
        if laser_channel_invalid:
            self.log.error('AWG channel "{0}" to use as laser channel not found in available '
                           'activation configs.'.format(self._laser_channel))
        return

    def on_deactivate(self):
        pass

    @property
    def is_running(self):
        return self.awg().get_status()[0] > 0

    @property
    def current_mode(self):
        return self.__current_mode.name.lower()

    def off(self):
        """
        Switches off any microwave output.
        Must return AFTER the device is actually stopped.

        @return int: error code (0:OK, -1:error)
        """
        self.awg().pulser_off()
        return -1 if self.is_running else 0

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        return self.current_mode, self.is_running

    def get_power(self):
        """
        Gets the microwave output power for the currently active mode.

        @return float: the output power in dBm
        """
        if self.__current_mode == MicrowaveMode.CW:
            return self._cw_parameters['power']
        elif self.__current_mode == MicrowaveMode.LIST:
            return self._list_parameters['power']
        elif self.__current_mode == MicrowaveMode.SWEEP:
            return self._sweep_parameters['power']
        raise ValueError('Unknown microwave source mode.')

    def get_frequency(self):
        """
        Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode.
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.

        @return [float, list]: frequency(s) currently set for this device in Hz
        """
        if self.__current_mode == MicrowaveMode.CW:
            return self._cw_parameters['frequency']
        elif self.__current_mode == MicrowaveMode.LIST:
            return self._list_parameters['frequency']
        elif self.__current_mode == MicrowaveMode.SWEEP:
            return [self._sweep_parameters['start'],
                    self._sweep_parameters['stop'],
                    self._sweep_parameters['step']]
        raise ValueError('Unknown microwave source mode.')

    def cw_on(self):
        """
        Switches on cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        # Throw error if AWG is running
        if self.is_running:
            self.log.error('Unable to turn on CW mode microwave output. AWG is already running.')
            return -1

        # Enable CW mode if not already set. Write waveforms if not present
        if not self._cw_waveforms or self.__current_mode != MicrowaveMode.CW:
            self.set_cw()
        if not self._cw_waveforms:
            return -1

        # Load waveforms into AWG channels and start AWG
        loaded_waveforms = self.awg().load_waveform(self._cw_waveforms)
        err_code = self.awg().pulser_on()
        return err_code if loaded_waveforms else -1

    def set_cw(self, frequency=None, power=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm

        @return tuple(float, float, str): with the relation
            current frequency in Hz,
            current power in dBm,
            current mode
        """
        if frequency is not None:
            self._cw_parameters['frequency'] = float(frequency)
        if power is not None:
            self._cw_parameters['power'] = float(power)
        self.__current_mode = MicrowaveMode.CW
        self._cw_waveforms = self._create_sine_waveform(name='mw_interfuse_cw',
                                                        frequency=frequency,
                                                        amplitude=self.dbm_to_volts(power))
        return self._cw_parameters['frequency'], self._cw_parameters['power'], self.current_mode

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        # Throw error if AWG is running
        if self.is_running:
            self.log.error('Unable to turn on LIST mode microwave output. AWG is already running.')
            return -1

        # Enable LIST mode if not already set. Write waveforms/sequences if not present
        if not self._list_waveforms or self._list_sequence is None or self.__current_mode != MicrowaveMode.LIST:
            self.set_list()
        if not self._list_waveforms or self._list_sequence is None:
            return -1

        # Load sequences into AWG channels and start AWG
        loaded_sequence = self.awg().load_sequence(self._list_sequence)
        err_code = self.awg().pulser_on()
        return err_code if loaded_sequence else -1

    def set_list(self, frequency=None, power=None):
        """
        Configures the device for list-mode and optionally sets frequencies and/or power

        @param list frequency: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return list, float, str: current frequencies in Hz, current power in dBm, current mode
        """
        if frequency is not None:
            self._list_parameters['frequency'] = list(frequency)
        if power is not None:
            self._list_parameters['power'] = float(power)
        self.__current_mode = MicrowaveMode.LIST

        # Create sequence
        err = self._create_list_sequence(
            name='mw_interfuse_list',
            frequency_list=self._list_parameters['frequency'],
            amplitude=self.dbm_to_volts(self._list_parameters['power']))
        if err:
            self.log.error('Error while writing sequence for microwave list mode in AWG.')
        return self._list_parameters['frequency'], self._list_parameters[
            'power'], self.current_mode

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        # Throw error if AWG is running
        if self.is_running:
            self.log.error('Unable to turn on SWEEP mode microwave output. AWG is already running.')
            return -1

        # Enable SWEEP mode if not already set. Write waveforms/sequences if not present
        if not self._list_waveforms or self._list_sequence is None or self.__current_mode != MicrowaveMode.SWEEP:
            self.set_sweep()
        if not self._list_waveforms or self._list_sequence is None:
            return -1

        # Load sequences into AWG channels and start AWG
        loaded_sequence = self.awg().load_sequence(self._list_sequence)
        err_code = self.awg().pulser_on()
        return err_code if loaded_sequence else -1

    def set_sweep(self, start=None, stop=None, step=None, power=None):
        """
        Configures the device for sweep-mode and optionally sets frequency start/stop/step
        and/or power

        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """
        if start is not None:
            self._sweep_parameters['start'] = float(start)
        if stop is not None:
            self._sweep_parameters['stop'] = float(stop)
        if step is not None:
            self._sweep_parameters['step'] = float(step)
        if power is not None:
            self._sweep_parameters['power'] = float(power)
        self.__current_mode = MicrowaveMode.SWEEP

        # Adjust stop frequency according to step size
        start = self._sweep_parameters['start']
        stop = self._sweep_parameters['stop']
        step = self._sweep_parameters['step']
        points = int(round((stop - start) / step)) + 1
        freq_list = [i * step + start for i in range(points)]
        self._sweep_parameters['stop'] = freq_list[-1]

        # Create sequence
        err = self._create_list_sequence(
            name='mw_interfuse_list',
            frequency_list=freq_list,
            amplitude=self.dbm_to_volts(self._sweep_parameters['power']))
        if err:
            self.log.error('Error while writing sequence for microwave sweep mode in AWG.')
        return self._sweep_parameters['start'], self._sweep_parameters['stop'], \
               self._sweep_parameters['step'], self._sweep_parameters['power'], self.current_mode

    def reset_listpos(self):
        """
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        pass

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        pass

    def set_ext_trigger(self, pol, timing):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)
        @param timing: estimated time between triggers

        @return object, float: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING],
            trigger timing as queried from device
        """
        self.log.warning('Setting trigger polarity and timing not supported by mw-awg interfuse.')
        return TriggerEdge.RISING, timing

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time corresponding to the
        frequency switching speed.
        """
        self.log.error('Software triggering currently not supported by PulserInterface.')
        return -1

    def get_limits(self):
        """ Return the device-specific limits in a nested dictionary.

          @return MicrowaveLimits: Microwave limits object
        """
        awg_constraints = self.awg().get_constraints()

        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST, MicrowaveMode.SWEEP)
        limits.min_frequency = awg_constraints.sample_rate.min / 2
        limits.max_frequency = awg_constraints.sample_rate.max / 2
        limits.min_power = self.volts_to_dbm(awg_constraints.a_ch_amplitude.step / 2)
        limits.max_power = self.volts_to_dbm(awg_constraints.a_ch_amplitude.max / 2)
        limits.list_minstep = 0.1
        limits.list_maxstep = limits.max_frequency
        limits.list_maxentries = awg_constraints.sequence_steps.max
        limits.sweep_minstep = 0.1
        limits.sweep_maxentries = awg_constraints.sequence_steps.max
        limits.sweep_maxstep = limits.max_frequency
        return limits

    def _create_sine_waveform(self, name, frequency, amplitude):
        """

        @param str name: Name tag of the waveform to write
        @param float frequency: The frequency of the sine wave in Hz
        @param float amplitude: The amplitude of the sine wave in V

        @return list: List of written waveform names now residing in AWG memory
        """
        # Read device settings and states
        sampling_rate = self.awg().get_sample_rate()
        pp_amp = self.awg().get_analog_level()[0][self._microwave_channel]
        channel_states = self.awg().get_active_channels()
        active_analog = natural_sort(
            chnl for chnl, state in channel_states.items() if state and chnl.startswith('a'))
        active_digital = natural_sort(
            chnl for chnl, state in channel_states.items() if state and chnl.startswith('d'))
        available_waveforms = self.awg().get_waveform_names()

        # Sanity checking
        if 2 * frequency > sampling_rate:
            self.log.warning('Undersampling warning:\nAWG sampling rate ({0:.3e} Hz) is less than '
                             'twice the desired sine wave frequency to sample ({1:.3e} Hz).'
                             ''.format(sampling_rate, frequency))
        if 2 * amplitude > pp_amp:
            self.log.warning('Amplitude warning:\nAWG peak-to-peak amplitude ({0:.3e} V) is less '
                             'than the desired sine wave peak-to-peak amplitude to sample '
                             '({1:.3e} V).'.format(pp_amp, 2 * amplitude))
        if self._microwave_channel not in active_analog:
            self.log.error(
                'Microwave channel "{0}" not active in AWG.'.format(self._microwave_channel))
            return list()
        if self._laser_channel not in active_digital:
            self.log.error(
                'Laser channel "{0}" not active in AWG.'.format(self._laser_channel))
            return list()

        # Calculate waveform
        waveform_len_s = 1000. / frequency
        waveform_len_bins = int(round(waveform_len_s * sampling_rate))
        granularity = self.awg().get_constraints().waveform_length.step
        if (waveform_len_bins % granularity) != 0:
            waveform_len_bins += granularity - (waveform_len_bins % granularity)
        if self._max_waveform_length and self._max_waveform_length < waveform_len_bins:
            self.log.error('Exceeding max waveform length.')
            return list()
        analog_samples = {
            chnl: np.zeros(waveform_len_bins, dtype='float32') for chnl in active_analog}
        digital_samples = {
            chnl: np.zeros(waveform_len_bins, dtype='bool') for chnl in active_digital}

        time_arr = np.arange(waveform_len_bins, dtype='float64') / sampling_rate
        samples_arr = 2 * amplitude / pp_amp * np.sin(2 * np.pi * frequency * time_arr)
        analog_samples[self._microwave_channel] = samples_arr.astype('float32')
        digital_samples[self._laser_channel][:] = True

        # Write waveform. Delete old waveform if present.
        for wfm in available_waveforms:
            if re.match(r'\b{0}_ch\d+\b'.format(name), wfm):
                self.awg().delete_waveform(wfm)
        samples_written, waveforms_written = self.awg().write_waveform(
            name=name,
            analog_samples=analog_samples,
            digital_samples=digital_samples,
            is_first_chunk=True, is_last_chunk=True,
            total_number_of_samples=waveform_len_bins)

        if samples_written != waveform_len_bins:
            self.log.error('Error while writing waveform "{0}" to AWG.'.format(name))
            return list()
        return waveforms_written

    def _create_list_sequence(self, name, frequency_list, amplitude):
        """
        Create waveforms and sequence from a list of frequencies with a common amplitude,

        @param str name: Name tag for the sequence
        @param list frequency_list: List of frequencies. The length of the list will determine
                                    the number of sequence steps.
        @param float amplitude: The amplitude of the sine for each sequence step waveform.

        @return bool: Error indicator (True: error, False: OK)
        """
        # Delete old waveforms and sequences
        for wfm in self._list_waveforms:
            self.awg().delete_waveform(wfm)
        self._list_waveforms = list()
        if self._list_sequence:
            self.awg().delete_sequence(self._list_sequence)
        self._list_sequence = None

        # Create new waveforms and sequence steps
        sequence_params = list()
        for ii, freq in enumerate(frequency_list):
            wfm_name = '{0}_{1:d}'.format(name, ii)
            created_waveforms = self._create_sine_waveform(name=wfm_name,
                                                           frequency=freq,
                                                           amplitude=amplitude)
            # If waveform creation failed, delete all already created waveforms and abort
            if not created_waveforms:
                for wfm in self._list_waveforms:
                    self.awg().delete_waveform(wfm)
                self._list_waveforms = list()
                break

            # Extend list upon successful creation
            self._list_waveforms.extend(created_waveforms)

            # Append sequence step
            seq_step = SequenceStep(wfm_name)
            seq_step.repetitions = -1
            seq_step.event_trigger = self._event_trigger
            seq_step.go_to = -1
            seq_step.event_jump_to = -1
            if ii == len(frequency_list) - 1:
                seq_step.go_to = 1
                seq_step.event_jump_to = 1

            sequence_params.append((created_waveforms.copy(), seq_step))
            # Append the first element twice due to counting issues with qudi
            if ii == 0:
                sequence_params.append((created_waveforms.copy(), seq_step))

        if not self._list_waveforms:
            return True

        # Write sequence
        steps_written = self.awg().write_sequence('mw_interfuse_list', sequence_params)
        if steps_written != len(frequency_list) + 1:
            return True
        self._list_sequence = 'mw_interfuse_list'
        return False

    @staticmethod
    def dbm_to_volts(value):
        """
        Convert power in dBm of a sine wave in a 50ohm system to equivalent amplitude in volts.

        @param float value: The power of a sine wave in dBm
        @return float: The corresponding amplitude of a sine wave in volts
        """
        return 10**((value - 10) / 20)

    @staticmethod
    def volts_to_dbm(value):
        """
        Convert amplitude of a sine wave in a 50ohm system to power in dBm.

        @param float value: amplitude of a sine wave in volts
        @return float: The corresponding power of a sine wave in dBm
        """
        return 10 + 20 * np.log10(value)
