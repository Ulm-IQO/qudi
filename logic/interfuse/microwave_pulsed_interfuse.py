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
import time

from core.module import Connector, ConfigOption
from core.util.helpers import natural_sort
from logic.generic_logic import GenericLogic
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import TriggerEdge, MicrowaveMode, MicrowaveLimits
from logic.pulsed.pulse_objects import SequenceStep
from logic.pulsed.pulse_objects import PulseBlock, PulseSequence, PulseBlockEnsemble, PulseBlockElement
from logic.pulsed.sampling_functions import SamplingFunctions


class MicrowavePulsedInterfuse(GenericLogic, MicrowaveInterface):
    """
    Interfuse to enable the use of AWG hardware with the MicrowaveInterface via PulsedMasterLogic.
    """

    _modclass = 'MicrowavePulsedInterfuse'
    _modtype = 'interfuse'

    _max_waveform_length = ConfigOption(name='max_waveform_length', default=None, missing='warn')
    _event_trigger = ConfigOption(name='event_trigger', missing='error')
    _wait_timeout = ConfigOption(name='wait_timeout', default=120, missing='warn')

    pulsedmaster = Connector(interface='PulsedMasterLogic')

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
        self._cw_waveforms = list()
        self._list_waveforms = list()
        self._list_sequence = None
        return

    def on_deactivate(self):
        pass

    @property
    def is_running(self):
        return self.pulsedmaster().status_dict['pulser_running']

    @property
    def current_mode(self):
        return self.__current_mode.name.lower()

    @property
    def microwave_channel(self):
        return self.pulsedmaster().generation_parameters['microwave_channel']

    @property
    def laser_channel(self):
        return self.pulsedmaster().generation_parameters['laser_channel']

    @property
    def pulsed_measurement_running(self):
        return self.pulsedmaster().status_dict['measurement_running']

    def off(self):
        """
        Switches off any microwave output.
        Must return AFTER the device is actually stopped.

        @return int: error code (0:OK, -1:error)
        """
        if not self.is_running:
            return 0
        if self.pulsed_measurement_running:
            self.log.error('Unable to stop ODMR measurement. Pulsed measurement in progress.')
            return -1
        self.pulsedmaster().toggle_pulse_generator(False)
        return self._wait_until_pulser_stopped()

    def pulser_on(self):
        if self.is_running:
            return 0
        if self.pulsed_measurement_running:
            self.log.error('Unable to start ODMR measurement. Pulsed measurement in progress.')
            return -1
        self.pulsedmaster().toggle_pulse_generator(True)
        return self._wait_until_pulser_started()

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
        if self.is_running or self.pulsed_measurement_running:
            self.log.error('Unable to turn on CW mode microwave output. AWG is already running.')
            return -1

        # Enable CW mode if not already set. Write waveforms if not present
        if not self._cw_waveforms or self.__current_mode != MicrowaveMode.CW:
            self.set_cw()
        if not self._cw_waveforms:
            return -1

        # Load waveforms into AWG channels and start AWG
        loaded_asset, asset_type = self.pulsedmaster().loaded_asset
        if loaded_asset != 'mw_interfuse_cw' or asset_type != 'PulseBlockEnsemble':
            self.pulsedmaster().load_ensemble('mw_interfuse_cw')
            if self._wait_until_loaded() < 0:
                return -1
        return self.pulser_on()

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
        # Create new waveform if needed
        if frequency is not None or power is not None or not self._cw_waveforms:
            err = self._create_sine_ensemble(name='mw_interfuse_cw',
                                             frequency=frequency,
                                             amplitude=self.dbm_to_volts(power))
            if not err:
                self.pulsedmaster().sample_ensemble('mw_interfuse_cw')
                self._wait_until_ensemble_sampled()
                self._cw_waveforms = self.pulsedmaster().saved_pulse_block_ensembles[
                    'mw_interfuse_cw'].sampling_information['waveforms']
        return self._cw_parameters['frequency'], self._cw_parameters['power'], self.current_mode

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        # Throw error if AWG is running
        if self.is_running or self.pulsed_measurement_running:
            self.log.error('Unable to turn on LIST mode microwave output. AWG is already running.')
            return -1

        # Enable LIST mode if not already set. Write waveforms/sequences if not present
        if not self._list_waveforms or self._list_sequence is None or self.__current_mode != MicrowaveMode.LIST:
            self.set_list()
        if not self._list_waveforms or self._list_sequence is None:
            return -1

        # Load waveforms into AWG channels and start AWG
        loaded_asset, asset_type = self.pulsedmaster().loaded_asset
        if loaded_asset != 'mw_interfuse_list' or asset_type != 'PulseSequence':
            self.pulsedmaster().load_sequence(self._list_sequence)
            if self._wait_until_loaded() < 0:
                return -1
        return self.pulser_on()

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

        # Create sequence
        # Create new waveform if needed
        if self.__current_mode != MicrowaveMode.LIST or frequency is not None or power is not None or not self._list_sequence:
            err = self._create_list_sequence(
                name='mw_interfuse_list',
                frequency_list=self._list_parameters['frequency'],
                amplitude=self.dbm_to_volts(self._list_parameters['power']))
            if err:
                self.log.error('Error while writing sequence for microwave list mode in AWG.')
            else:
                self.pulsedmaster().sample_sequence('mw_interfuse_list')
                self._wait_until_sequence_sampled()
                self._list_waveforms = self.pulsedmaster().saved_pulse_sequences[
                    'mw_interfuse_list'].sampling_information['waveforms']
                self._list_sequence = 'mw_interfuse_list'

        self.__current_mode = MicrowaveMode.LIST
        return self._list_parameters['frequency'], self._list_parameters[
            'power'], self.current_mode

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        # Throw error if AWG is running
        if self.is_running or self.pulsed_measurement_running:
            self.log.error('Unable to turn on SWEEP mode microwave output. AWG is already running.')
            return -1

        # Enable SWEEP mode if not already set. Write waveforms/sequences if not present
        if not self._list_waveforms or self._list_sequence is None or self.__current_mode != MicrowaveMode.SWEEP:
            self.set_sweep()
        if not self._list_waveforms or self._list_sequence is None:
            return -1

        # Load waveforms into AWG channels and start AWG
        loaded_asset, asset_type = self.pulsedmaster().loaded_asset
        if loaded_asset != 'mw_interfuse_list' or asset_type != 'PulseSequence':
            self.pulsedmaster().load_sequence(self._list_sequence)
            if self._wait_until_loaded() < 0:
                return -1
        return self.pulser_on()

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

        # Adjust stop frequency according to step size
        start = self._sweep_parameters['start']
        stop = self._sweep_parameters['stop']
        step = self._sweep_parameters['step']
        points = int(round((stop - start) / step)) + 1
        freq_list = [i * step + start for i in range(points)]
        self._sweep_parameters['stop'] = freq_list[-1]

        # Create sequence
        if self.__current_mode != MicrowaveMode.SWEEP or start is not None or stop is not None or step is not None or power is not None or not self._list_sequence:
            err = self._create_list_sequence(
                name='mw_interfuse_list',
                frequency_list=freq_list,
                amplitude=self.dbm_to_volts(self._sweep_parameters['power']))
            if err:
                self.log.error('Error while writing sequence for microwave sweep mode in AWG.')
            else:
                self.pulsedmaster().sample_sequence('mw_interfuse_list')
                self._wait_until_sequence_sampled()
                self._list_waveforms = self.pulsedmaster().saved_pulse_sequences[
                    'mw_interfuse_list'].sampling_information['waveforms']
                self._list_sequence = 'mw_interfuse_list'

        self.__current_mode = MicrowaveMode.SWEEP
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
        self.log.debug('Setting trigger polarity and timing not supported by mw-awg interfuse.')
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
        awg_constraints = self.pulsedmaster().pulse_generator_constraints

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

    def _create_sine_ensemble(self, name, frequency, amplitude):
        """

        @param str name: Name tag of the waveform to write
        @param float frequency: The frequency of the sine wave in Hz
        @param float amplitude: The amplitude of the sine wave in V

        @return list: List of written waveform names now residing in AWG memory
        """
        # Read device settings
        settings = self.pulsedmaster().pulse_generator_settings
        sampling_rate = settings['sample_rate']
        pp_amp = settings['analog_levels'][0][self.microwave_channel]

        # Sanity checking
        if 2 * frequency > sampling_rate:
            self.log.warning('Undersampling warning:\nAWG sampling rate ({0:.3e} Hz) is less than '
                             'twice the desired sine wave frequency to sample ({1:.3e} Hz).'
                             ''.format(sampling_rate, frequency))
        if 2 * amplitude > pp_amp:
            self.log.warning('Amplitude warning:\nAWG peak-to-peak amplitude ({0:.3e} V) is less '
                             'than the desired sine wave peak-to-peak amplitude to sample '
                             '({1:.3e} V).'.format(pp_amp, 2 * amplitude))

        # Calculate waveform length
        min_length = self.pulsedmaster().pulse_generator_constraints.waveform_length.min
        waveform_len_s = 100. / frequency
        waveform_len_bins = int(round(waveform_len_s * sampling_rate))
        while waveform_len_bins < min_length:
            waveform_len_bins += int(round(waveform_len_s * sampling_rate))
            waveform_len_s = waveform_len_bins / sampling_rate
        granularity = self.pulsedmaster().pulse_generator_constraints.waveform_length.step
        if (waveform_len_bins % granularity) != 0:
            waveform_len_bins += granularity - (waveform_len_bins % granularity)
            waveform_len_s = waveform_len_bins / sampling_rate
        if self._max_waveform_length and self._max_waveform_length < waveform_len_bins:
            self.log.error('Exceeding max waveform length.')
            return True

        # Create PulseBlockEnsemble
        self.pulsedmaster().delete_block_ensemble(name)
        self.pulsedmaster().delete_pulse_block(name)
        pulse_function = {chnl: SamplingFunctions.Idle() for chnl in
                          self.pulsedmaster().analog_channels}
        pulse_function[self.microwave_channel] = SamplingFunctions.Sin(amplitude=amplitude,
                                                                       frequency=frequency,
                                                                       phase=0)
        digital_high = {chnl: False for chnl in self.pulsedmaster().digital_channels}
        digital_high[self.laser_channel] = True

        element = PulseBlockElement(init_length_s=waveform_len_s,
                                    increment_s=0,
                                    pulse_function=pulse_function,
                                    digital_high=digital_high,
                                    laser_on=True)
        block = PulseBlock(name=name)
        block.append(element)
        self.pulsedmaster().save_pulse_block(block)
        ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        ensemble.append((block.name, 0))
        self.pulsedmaster().save_block_ensemble(ensemble)
        # while ensemble.name not in self.pulsedmaster().saved_pulse_block_ensembles:
        #     time.sleep(0.01)
        return False

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
        if self._list_sequence:
            self.pulsedmaster().delete_sequence(self._list_sequence)
        for ens in self._list_waveforms:
            self.pulsedmaster().delete_block_ensemble(ens)
        time.sleep(2)
        self._list_waveforms = list()
        self._list_sequence = None

        # Create new waveforms and sequence steps
        sequence = PulseSequence(name=name, rotating_frame=False)
        for ii, freq in enumerate(frequency_list):
            wfm_name = '{0}_{1:d}'.format(name, ii)
            self._create_sine_ensemble(name=wfm_name, frequency=freq, amplitude=amplitude)

            # Append sequence step
            seq_step = SequenceStep(wfm_name)
            seq_step.repetitions = -1
            seq_step.event_trigger = self._event_trigger
            seq_step.go_to = -1
            seq_step.event_jump_to = -1
            if ii == len(frequency_list) - 1:
                seq_step.go_to = 1
                seq_step.event_jump_to = 1

            sequence.append(seq_step)
            # Append the first element twice due to counting issues with qudi
            if ii == 0:
                sequence.append(seq_step)

        self.pulsedmaster().save_sequence(sequence)
        # while sequence.name not in self.pulsedmaster().saved_pulse_sequences:
        #     time.sleep(0.01)
        return False

    def _wait_until_pulser_stopped(self):
        start = time.time()
        while self.is_running:
            time.sleep(0.2)
            if (time.time() - start) >= self._wait_timeout:
                self.log.error('Unable to stop pulser. Operation timed out.')
                return -1
        return 0

    def _wait_until_pulser_started(self):
        start = time.time()
        while not self.is_running:
            time.sleep(0.2)
            if (time.time() - start) >= self._wait_timeout:
                self.log.error('Unable to start pulser. Operation timed out.')
                return -1
        return 0

    def _wait_until_loaded(self):
        start = time.time()
        while self.pulsedmaster().status_dict['loading_busy']:
            time.sleep(0.25)
            if (time.time() - start) >= self._wait_timeout:
                self.log.error('Unable to load asset into pulse generator. Operation timed out.')
                return -1
        return 0

    def _wait_until_ensemble_sampled(self):
        start = time.time()
        while self.pulsedmaster().status_dict['sampling_ensemble_busy']:
            time.sleep(0.1)
            if (time.time() - start) >= self._wait_timeout:
                self.log.error('Unable to sample PulseBlockEnsemble. Operation timed out.')
                return -1
        return 0

    def _wait_until_sequence_sampled(self):
        start = time.time()
        while self.pulsedmaster().status_dict['sampling_sequence_busy']:
            time.sleep(0.1)
            if (time.time() - start) >= self._wait_timeout:
                self.log.error('Unable to sample PulseSequence. Operation timed out.')
                return -1
        return 0

    def _wait_until_sampled_loaded(self):
        start = time.time()
        while self.pulsedmaster().status_dict['sampload_busy']:
            time.sleep(0.2)
            if (time.time() - start) >= self._wait_timeout:
                self.log.error('Unable to sample and load asset for pulse generator. '
                               'Operation timed out.')
                return -1
        return 0

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
