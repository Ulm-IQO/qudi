# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the Keysight M3202A PXIe AWG device.
(previously Signadyne SD1).

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


import ctypes
import os
import datetime
import numpy as np
from collections import OrderedDict
from core.util.helpers import natural_sort

import sys

if sys.platform == 'win32':
    sys.path.append('C:\Program Files (x86)\Keysight\SD1\Libraries\Python')
elif sys.platform == 'linux':
    sys.path.append('/usr/local/Keysight/SD1')
else:
    raise Exception('Unknown platform, please add path to library.')

import keysightSD1 as ksd1

from core.module import Base
from core.configoption import ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints, SequenceOption


class M3202A(Base, PulserInterface):
    """ Qudi module for the Keysight M3202A PXIe AWG card (1GHz sampling frequency)

    Example config for copy-paste:

    keysight_m3202a:
        module.Class: 'awg.keysight_M3202A.M3202A'
        awg_serial: 0000000000 # here the serial number of current AWG

    """

    # config options
    serial = ConfigOption(name='awg_serial', missing='error')

    __ch_map = {
        'a_ch1': 1,
        'a_ch2': 2,
        'a_ch3': 3,
        'a_ch4': 4
    }

    def on_activate(self):
        self.analog_amplitudes = {}
        self.analog_offsets = {}
        # loaded sequence
        self.last_sequence = None
        # loaded waveforms, channel -> waveform name
        self.loaded_waveforms = {}
        # uploaded waveforms, waveform name -> instrument wfm number
        self.written_waveforms = {}

        self.chcfg = {
            'a_ch1': M3202ChannelCfg(),
            'a_ch2': M3202ChannelCfg(),
            'a_ch3': M3202ChannelCfg(),
            'a_ch4': M3202ChannelCfg(),
        }

        constraints = PulserConstraints()

        constraints.sample_rate.min = 4e8
        constraints.sample_rate.max = 1e9
        constraints.sample_rate.step = 1.0
        constraints.sample_rate.default = 1e9

        constraints.a_ch_amplitude.min = 0
        constraints.a_ch_amplitude.max = 1.5
        constraints.a_ch_amplitude.step = 0.01
        constraints.a_ch_amplitude.default = 1.5
        constraints.a_ch_offset.min = 0
        constraints.a_ch_offset.max = 1.5
        constraints.a_ch_offset.step = 0.01
        constraints.a_ch_offset.default = 0.0
        # FIXME: Enter the proper digital channel low constraints:
        constraints.d_ch_low.min = 0.0
        constraints.d_ch_low.max = 0.0
        constraints.d_ch_low.step = 0.0
        constraints.d_ch_low.default = 0.0
        # FIXME: Enter the proper digital channel high constraints:
        constraints.d_ch_high.min = 0.0
        constraints.d_ch_high.max = 0.0
        constraints.d_ch_high.step = 0.0
        constraints.d_ch_high.default = 0.0

        constraints.waveform_length.min = 30
        constraints.waveform_length.max = 1e9
        constraints.waveform_length.step = 10
        constraints.waveform_length.default = 1000

        # FIXME: Check the proper number for your device
        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 1024
        constraints.waveform_num.step = 1
        constraints.waveform_num.default = 1
        # FIXME: Check the proper number for your device
        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 1
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1
        # FIXME: Check the proper number for your device
        constraints.subsequence_num.min = 0
        constraints.subsequence_num.max = 0
        constraints.subsequence_num.step = 0
        constraints.subsequence_num.default = 0

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65536
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0
        # ToDo: Check how many external triggers are available
        constraints.event_triggers = ['SOFT', 'EXT', 'SOFT_CYCLE', 'EXT_CYCLE']
        constraints.flags = []

        constraints.sequence_steps.min = 1
        constraints.sequence_steps.max = 1024
        constraints.sequence_steps.step = 1
        constraints.sequence_steps.default = 1

        activation_config = OrderedDict()
        activation_config['all'] = frozenset({'a_ch1', 'a_ch2', 'a_ch3', 'a_ch4'})
        activation_config['one'] = frozenset({'a_ch1'})
        activation_config['two'] = frozenset({'a_ch1', 'a_ch2'})
        activation_config['three'] = frozenset({'a_ch1', 'a_ch2', 'a_ch3'})
        constraints.activation_config = activation_config
        # FIXME: additional constraint really necessary?
        constraints.dac_resolution = {'min': 14, 'max': 14, 'step': 1, 'unit': 'bit'}
        constraints.sequence_option = SequenceOption.FORCED

        self._constraints = constraints

        self.awg = ksd1.SD_AOU()
        aouID = self.awg.openWithSerialNumberCompatibility(
            'M3202A', self.serial, ksd1.SD_Compatibility.KEYSIGHT)

        # Check AWG Connection for errors
        if aouID < 0:
            self.awg.close()
            raise Exception('AWG Error: {0} {1}'.format(aouID, ksd1.SD_Error.getErrorMessage(aouID)))

        self.ser = self.awg.getSerialNumber()
        self.model = self.awg.getProductName()
        self.fwver = self.awg.getFirmwareVersion()
        self.hwver = self.awg.getHardwareVersion()
        self.chassis = self.awg.getChassis()
        self.ch_slot = self.awg.getSlot()

        self.reset()

        self.log.info('Keysight AWG Model: {} serial: {} '
                      'FW Ver: {} HW Ver: {} Chassis: {} Slot: {}'
                      ''.format(self.model, self.ser, self.fwver, self.hwver, self.chassis,
                                self.ch_slot))

    def on_deactivate(self):
        self.awg.close()

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        activation_dict = self.get_active_channels()
        active_channels = {chnl for chnl in activation_dict if activation_dict[chnl]}
        for chan in active_channels:
            ch = self.__ch_map[chan]
            self.log.debug('Stop Ch{} {}'.format(ch, self.awg.AWGstop(ch)))
            self.log.debug('Flush Ch{} {}'.format(ch, self.awg.AWGflush(ch)))
            self.log.debug(
                'WaveShape Ch{} {}'.format(
                    ch, self.awg.channelWaveShape(ch, ksd1.SD_Waveshapes.AOU_AWG)))

        self.awg.waveformFlush()

        # loaded sequence
        self.last_sequence = None
        # loaded waveforms, channel -> waveform name
        self.loaded_waveforms = {}
        # uploaded waveforms, waveform name -> instrument wfm number
        self.written_waveforms = {}

        amps = {
            ch: self._constraints.a_ch_amplitude.default
            for ch, en in self.get_active_channels().items() if en}
        offs = {
            ch: self._constraints.a_ch_offset.default
            for ch, en in self.get_active_channels().items() if en}

        self.set_analog_level(amps, offs)
        return 0

    def get_constraints(self):
        """
        Retrieve the hardware constrains from the Pulsing device.

        @return constraints object: object with pulser constraints as attributes.
        """
        return self._constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error)
        """
        if self.last_sequence is None:
            self.log.error('This AWG only supports sequences. Please put the waveform in a sequence and then load it.')
            return -1
        else:
            self.log.debug('StartMultiple {}'.format(self.awg.AWGstartMultiple(0b1111)))
            return 0

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error)
        """
        self.log.debug('StopMultiple {}'.format(self.awg.AWGstopMultiple(0b1111)))
        return 0

    def load_waveform(self, load_dict):
        """ Loads a waveform to the specified channel of the pulsing device.

        @param load_dict:  dict|list, a dictionary with keys being one of the available channel

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """
        if isinstance(load_dict, list):
            new_dict = dict()
            for waveform in load_dict:
                channel = int(waveform.rsplit('_ch', 1)[1])
                new_dict[channel] = waveform
            load_dict = new_dict

        # Get all active channels
        chnl_activation = self.get_active_channels()
        analog_channels = natural_sort(
            chnl for chnl in chnl_activation if chnl.startswith('a') and chnl_activation[chnl])

        # Load waveforms into channels
        for chnl_num, waveform in load_dict.items():
            self.loaded_waveforms[chnl_num] = waveform

        self.last_sequence = None
        return self.get_loaded_assets()

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        @param sequence_name:  dict|list, a dictionary with keys being one of the available channel
        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """
        return self.get_loaded_assets()

    def get_loaded_assets(self):
        """
        Retrieve the currently loaded asset names for each active channel of the device.

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel,
                             string describing the asset type ('waveform' or 'sequence')
        """
        if self.last_sequence is None:
            return self.loaded_waveforms, 'waveform'
        return self.loaded_waveforms, 'sequence'

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)
        """
        self.reset()
        return 0

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): tuple with an interger value of the current status and a corresponding
                             dictionary containing status description for all the possible status
                             variables of the pulse generator hardware.
        """
        status_dic = {
            -1: 'Failed Request or Communication',
            0: 'Device has stopped, but can receive commands',
            1: 'One channel running',
            2: 'Two channels running',
            3: 'Three channels running',
            4: 'Four channels running'
            }

        current_status = 0
        for ch in self.get_active_channels():
            if self.awg.AWGisRunning(self.__ch_map[ch]):
                current_status += 1
        # All the other status messages should have higher integer values then 1.
        return current_status, status_dic

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead retrieve the current
        sample rate directly from the device.
        """
        return self.awg.clockGetFrequency()

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).
        """
        return self.awg.clockSetFrequency(sample_rate, ksd1.SD)

    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if the amplitude value (in Volt peak to peak, i.e. the
                               full amplitude) of a specific channel is desired.
        @param list offset: optional, if the offset value (in Volt) of a specific channel is
                            desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor string
        """
        if amplitude is None:
            amplitude = ['a_ch1', 'a_ch2', 'a_ch3', 'a_ch4']

        if offset is None:
            offset = ['a_ch1', 'a_ch2', 'a_ch3', 'a_ch4']

        ret_amp = {k: self.analog_amplitudes[k] for k in amplitude}
        ret_off = {k: self.analog_offsets[k] for k in offset}

        return ret_amp, ret_off

    def set_analog_level(self, amplitude=None, offset=None):
        """ Set amplitude and/or offset value of the provided analog channel(s).

        @param dict amplitude: dictionary, with key being the channel descriptor string
                               (i.e. 'a_ch1', 'a_ch2') and items being the amplitude values
                               (in Volt peak to peak, i.e. the full amplitude) for the desired
                               channel.
        @param dict offset: dictionary, with key being the channel descriptor string
                            (i.e. 'a_ch1', 'a_ch2') and items being the offset values
                            (in absolute volt) for the desired channel.

        @return (dict, dict): tuple of two dicts with the actual set values for amplitude and
                              offset for ALL channels.
        """
        for ch, ampl in amplitude.items():
            self.awg.channelAmplitude(self.__ch_map[ch], ampl)
            self.analog_amplitudes[ch] = ampl

        for ch, off in offset.items():
            self.awg.channelOffset(self.__ch_map[ch], off)
            self.analog_offsets[ch] = off

        self.log.debug('analog amp: {} offset: {}'
                       ''.format(self.analog_amplitudes, self.analog_offsets))
        return self.analog_amplitudes, self.analog_offsets

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels.

        @param list low: optional, if the low value (in Volt) of a specific channel is desired.
        @param list high: optional, if the high value (in Volt) of a specific channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor strings
                               (i.e. 'd_ch1', 'd_ch2') and items being the values for those
                               channels. Both low and high value of a channel is denoted in volts.
        """
        return {}, {}

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel.

        @param dict low: dictionary, with key being the channel descriptor string
                         (i.e. 'd_ch1', 'd_ch2') and items being the low values (in volt) for the
                         desired channel.
        @param dict high: dictionary, with key being the channel descriptor string
                          (i.e. 'd_ch1', 'd_ch2') and items being the high values (in volt) for the
                          desired channel.

        @return (dict, dict): tuple of two dicts where first dict denotes the current low value and
                              the second dict the high value for ALL digital channels.
                              Keys are the channel descriptor strings (i.e. 'd_ch1', 'd_ch2')
        """
        self.log.warning('no digital levels set')
        return {}, {}

    def get_active_channels(self, ch=None):
        """ Get the active channels of the pulse generator hardware.

        @param list ch: optional, if specific analog or digital channels are needed to be asked
                        without obtaining all the channels.

        @return dict:  where keys denoting the channel string and items boolean expressions whether
                       channel are active or not.
        """
        if ch is None:
            ch = ['a_ch1', 'a_ch2', 'a_ch3', 'a_ch4']
        return {k: True for k in ch}

    def set_active_channels(self, ch=None):
        """ Set the active channels for the pulse generator hardware.

        @param dict ch: dictionary with keys being the analog or digital string generic names for
                        the channels (i.e. 'd_ch1', 'a_ch2') with items being a boolean value.
                        True: Activate channel, False: Deactivate channel

        @return dict: with the actual set values for ALL active analog and digital channels
        """
        ch = ['a_ch1', 'a_ch2', 'a_ch3', 'a_ch4']
        return {k: True for k in ch}

    def write_waveform(self, name, analog_samples, digital_samples, is_first_chunk, is_last_chunk,
                       total_number_of_samples):
        """
        Write a new waveform or append samples to an already existing waveform on the device memory.

        @param name: str, waveform name, human readabla
        @param analog_samples: numpy.ndarray of type float32 containing the voltage samples
        @param digital_samples: numpy.ndarray of type bool containing the marker states
                                (if analog channels are active, this must be the same length as
                                analog_samples)
        @param is_first_chunk: bool, flag indicating if it is the first chunk to write.
                                     If True this method will create a new empty wavveform.
                                     If False the samples are appended to the existing waveform.
        @param is_last_chunk: bool, flag indicating if it is the last chunk to write.
                                    Some devices may need to know when to close the appending wfm.
        @param total_number_of_samples: int, The number of sample points for the entire waveform
                                        (not only the currently written chunk)

        @return: (int, list) number of samples written (-1 indicates failed process) and list of
                             created waveform names
        """
        tstart = datetime.datetime.now()
        self.log.debug('@{} write wfm: {} first: {} last: {} {}'.format(
            datetime.datetime.now() - tstart, name, is_first_chunk, is_last_chunk,
            total_number_of_samples))
        waveforms = list()
        min_samples = 30

        if not (is_first_chunk and is_last_chunk):
            self.log.error('Chunked Write not supported by this device.')
            return -1, waveforms

        # Sanity checks
        if len(analog_samples) == 0:
            self.log.error('No analog samples passed to write_waveform.')
            return -1, waveforms

        if total_number_of_samples < min_samples:
            self.log.error('Unable to write waveform.'
                           '\nNumber of samples to write ({0:d}) is '
                           'smaller than the allowed minimum waveform length ({1:d}).'
                           ''.format(total_number_of_samples, min_samples))
            return -1, waveforms

        # determine active channels
        activation_dict = self.get_active_channels()
        active_channels = {chnl for chnl in activation_dict if activation_dict[chnl]}
        active_analog = natural_sort(chnl for chnl in active_channels if chnl.startswith('a'))

        # Sanity check of channel numbers
        if active_channels != set(analog_samples.keys()).union(set(digital_samples.keys())):
            self.log.error('Mismatch of channel activation and sample array dimensions for '
                           'waveform creation.\nChannel activation is: {0}\nSample arrays have: '
                           ''.format(active_channels,
                                     set(analog_samples.keys()).union(set(digital_samples.keys()))))
            return -1, waveforms

        for a_ch in active_analog:
            a_ch_num = self.__ch_map[a_ch]
            wfm_name = '{0}_ch{1:d}'.format(name, a_ch_num)
            wfm = ksd1.SD_Wave()
            analog_samples[a_ch] = analog_samples[a_ch].astype('float64') / 2

            self.log.debug('wfmobj: {} {} {} min: {} max: {}'.format(
                a_ch, name, wfm_name, np.min(analog_samples[a_ch]), np.max(analog_samples[a_ch])))

            self.log.debug('@{} Before new wfm {}'.format(datetime.datetime.now() - tstart, a_ch))
            wfmid = self._fast_newFromArrayDouble(
                wfm, ksd1.SD_WaveformTypes.WAVE_ANALOG, analog_samples[a_ch])
            self.log.debug('@{} After new wfm {}'.format(datetime.datetime.now() - tstart, a_ch))

            if wfmid < 0:
                self.log.error('Device error when creating waveform {} ch: {}: {} {}'
                               ''.format(wfm_name, a_ch, wfmid, ksd1.SD_Error.getErrorMessage(wfmid)))
                return -1, waveforms

            if len(self.written_waveforms) > 0:
                wfm_nr = max(set(self.written_waveforms.values())) + 1
            else:
                wfm_nr = 1

            self.log.debug('@{} Before loading wfm {} '.format(datetime.datetime.now() - tstart, a_ch))
            written = self.awg.waveformLoad(wfm, wfm_nr)
            self.log.debug('@{} Samples written: {} {} '.format(datetime.datetime.now() - tstart, a_ch, wfm, written))
            if written < 0:
                self.log.error('Device error when uploading waveform {} id: {}: {} {}'
                               ''.format(wfm, wfm_nr, written, ksd1.SD_Error.getErrorMessage(written)))
                return -1, waveforms
            self.written_waveforms[wfm_name] = wfm_nr
            waveforms.append(wfm_name)

        self.log.debug('@{} Finished writing waveforms'.format(datetime.datetime.now() - tstart))
        return total_number_of_samples, waveforms

    def write_sequence(self, name, sequence_parameter_list):
        """
        Write a new sequence on the device memory.

        @param name: str, the name of the waveform to be created/append to
        @param sequence_parameter_list:  list, contains the parameters for each sequence step and
                                        the according waveform names.
        @return: int, number of sequence steps written (-1 indicates failed process)
        """
        steps_written = 0
        wfms_added = {}

        # Check if all waveforms are present on device memory
        avail_waveforms = set(self.get_waveform_names())
        for waveform_tuple, param_dict in sequence_parameter_list:
            if not avail_waveforms.issuperset(waveform_tuple):
                self.log.error('Failed to create sequence "{0}" due to waveforms "{1}" not '
                               'present in device memory.'.format(name, waveform_tuple))
                return -1

        active_analog = natural_sort(chnl for chnl in self.get_active_channels() if chnl.startswith('a'))
        num_tracks = len(active_analog)
        num_steps = len(sequence_parameter_list)

        for a_ch in active_analog:
            self.awg.AWGflush(self.__ch_map[a_ch])
            self.awg.channelWaveShape(self.__ch_map[a_ch], ksd1.SD_Waveshapes.AOU_AWG)

        # Fill in sequence information
        for step, (wfm_tuple, seq_params) in enumerate(sequence_parameter_list, 1):
            # Set waveforms to play
            if num_tracks == len(wfm_tuple):
                for track, waveform in enumerate(wfm_tuple, 1):
                    # Triggers !!!
                    wfm_nr = self.written_waveforms[waveform]
                    if seq_params['wait_for'] == 'SOFT':
                        trig = ksd1.SD_TriggerModes.SWHVITRIG
                        self.log.debug('Ch{} Trig SOFT'.format(track))
                    elif seq_params['wait_for'] == 'EXT':
                        trig = ksd1.SD_TriggerModes.EXTTRIG
                        self.log.debug('Ch{} Trig EXT'.format(track))
                    elif seq_params['wait_for'] == 'SOFT_CYCLE':
                        trig = ksd1.SD_TriggerModes.SWHVITRIG_CYCLE
                        self.log.debug('Ch{} Trig SOFT_CYCLE'.format(track))
                    elif seq_params['wait_for'] == 'EXT_CYCLE':
                        trig = ksd1.SD_TriggerModes.EXTTRIG_CYCLE
                        self.log.debug('Ch{} Trig EXT_CYCLE'.format(track))
                    else:
                        self.log.debug('Ch{} TrigAuto'.format(track))
                        trig = ksd1.SD_TriggerModes.AUTOTRIG
                    cycles = seq_params['repetitions'] + 1
                    prescale = 0
                    delay = 0
                    ret = self.awg.AWGqueueWaveform(track, wfm_nr, trig, delay, cycles, prescale)
                    self.log.debug('Sequence: {} Ch{} {} No{}'.format(
                        name, track, waveform, wfm_nr)
                    )
                    self.log.debug('Sequence Step: {0} Ch{1} No{2} Trig: {3} Del: {4} Rep: {5} Pre: {6} -> {7}'.format(
                        step, track, wfm_nr, trig, delay, cycles, prescale, ret)
                    )
                    if ret < 0:
                        self.log.error('Error queueing wfm: {} {}'.format(ret, ksd1.SD_Error.getErrorMessage(ret)))
                        return steps_written

                    wfms_added[track] = '{0}_{1:d}'.format(name, track)
                steps_written += 1
            else:
                self.log.error(
                    'Unable to write sequence.\nLength of waveform tuple "{0}" does not '
                    'match the number of sequence tracks.'.format(wfm_tuple)
                )
                return -1

        # more setup
        for a_ch in active_analog:
            self.log.debug('QueueConfig {}'.format(
                self.awg.AWGqueueConfig(self.__ch_map[a_ch], 1)))
            self.log.debug('channelAmpliude {}'.format(
                self.awg.channelAmplitude(self.__ch_map[a_ch], self.analog_amplitudes[a_ch])))


        if num_steps == steps_written:
            self.last_sequence = name
            self.loaded_waveforms = wfms_added

        self.set_channel_triggers(active_analog, sequence_parameter_list)

        return steps_written

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        return list(self.written_waveforms.keys())

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        return [self.last_sequence]

    def delete_waveform(self, waveform_name):
        """ Delete the waveform with name "waveform_name" from the device memory.

        @param str waveform_name: The name of the waveform to be deleted
                                  Optionally a list of waveform names can be passed.

        @return list: a list of deleted waveform names.
        """
        return []

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory.

        @param str sequence_name: The name of the sequence to be deleted
                                  Optionally a list of sequence names can be passed.

        @return list: a list of deleted sequence names.
        """
        return []

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Will always return False for pulse generator hardware without interleave.
        """
        return False

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        @return bool: actual interleave status (True: ON, False: OFF)
        """
        return False

    def write(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        return -1

    def query(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        return ''

    def _fast_newFromArrayDouble(self, wfm, waveformType, waveformDataA, waveformDataB=None):
        """ Reimplement newArrayFromDouble() for numpy arrays for massive speed gains.
        Original signature:
        int SD_Wave::newFromArrayDouble(
            int waveformType, double[] waveformDataA, double[] waveformDataB=0));

        @param object wfm: SD1 waveform object
        @param object waveformType: SD1 waveform Type
        @param ndarray waveformDataA: array containing samples
        @param ndarray waveformDataB: optional array containing samples
        @return int: id of waveform or error code
        """

        c_double_p = ctypes.POINTER(ctypes.c_double)
        if len(waveformDataA) > 0 and (waveformDataB is None or len(waveformDataA) == len(waveformDataB)):
            if isinstance(waveformDataA, np.ndarray):
                # print(type(waveformDataA), waveformDataA.dtype)
                waveform_dataA_C = waveformDataA.ctypes.data_as(c_double_p)
                length = len(waveformDataA)
            else:
                waveform_dataA_C = (ctypes.c_double * len(waveformDataA))(*waveformDataA)
                length = waveform_dataA_C._length_

            if waveformDataB is None:
                waveform_dataB_C = ctypes.c_void_p(0)
            else:
                if isinstance(waveformDataB, np.ndarray):
                    waveform_dataB_C = waveformDataB.ctypes.data_as(c_double_p)
                else:
                    waveform_dataB_C = (ctypes.c_double * len(waveformDataB))(*waveformDataB)
            # print('newFromArray DLL', length, type(waveform_dataA_C), type(waveform_dataB_C))

            wfm._SD_Object__handle = wfm._SD_Object__core_dll.SD_Wave_newFromArrayDouble(
                waveformType, length, waveform_dataA_C, waveform_dataB_C)

            return wfm._SD_Object__handle
        else:
            wfm._SD_Object__handle = 0
            return ksd1.SD_Error.INVALID_VALUE

    def set_channel_triggers(self, active_channels, sequence_parameter_list):
        """ Set up triggers and markers according to configuration

        @param list active_channels: active aeg channels
        @param list sequence_parameter_list: liust with all sequence elements

        """
        for ch in active_channels:
            if self.chcfg[ch].enable_trigger:
                trig_err = self.awg.AWGtriggerExternalConfig(
                    self.__ch_map[ch],
                    self.chcfg[ch].trig_source,
                    self.chcfg[ch].trig_behaviour,
                    self.chcfg[ch].trig_sync
                )
                # io is trigger in if trigger enabled
                if self.chcfg[ch].trig_source == 0:
                    self.log.info('IO IN for Ch{} '.format(self.__ch_map[ch]))
                    err = self.awg.triggerIOconfig(ksd1.SD_TriggerDirections.AOU_TRG_IN)
                    if err < 0:
                        self.log.error('Error configuring triggers: {} {}'.format(
                            err, ksd1.SD_Error.getErrorMessage(err)))

                self.log.info('Trig: Ch{} src: {} beh: {} sync: {}'.format(
                    self.__ch_map[ch],
                    self.chcfg[ch].trig_source,
                    self.chcfg[ch].trig_behaviour,
                    self.chcfg[ch].trig_sync,
                    trig_err
                ))

            mark_err = self.awg.AWGqueueMarkerConfig(
                self.__ch_map[ch],
                self.chcfg[ch].mark_mode,
                self.chcfg[ch].mark_pxi,
                self.chcfg[ch].mark_io,
                self.chcfg[ch].mark_value,
                self.chcfg[ch].mark_sync,
                self.chcfg[ch].mark_length,
                self.chcfg[ch].mark_delay
            )

            # I/O connector is a marker *only* if it is not configured as a trigger
            if self.chcfg[ch].mark_mode != ksd1.SD_MarkerModes.DISABLED and self.chcfg[ch].mark_io == 1:
                self.log.info('IO OUT for Ch{} '.format(self.__ch_map[ch]))
                if not (self.chcfg[ch].enable_trigger and self.chcfg[ch].trig_source == 0):
                    err = self.awg.triggerIOconfig(ksd1.SD_TriggerDirections.AOU_TRG_OUT)
                    if err < 0:
                        self.log.error('Error configuring marker: {} {}'.format(
                            err, ksd1.SD_Error.getErrorMessage(err)))
                else:
                    self.log.warning('IO Trigger cfg for ch {} overrides marker cfg!'.format(ch))

            self.log.info('Ch {} mm: {} pxi: {} io: {} val: {}, sync: {} len: {} delay: {} err: {}'.format(
                self.__ch_map[ch],
                self.chcfg[ch].mark_mode,
                self.chcfg[ch].mark_pxi,
                self.chcfg[ch].mark_io,
                self.chcfg[ch].mark_value,
                self.chcfg[ch].mark_sync,
                self.chcfg[ch].mark_length,
                self.chcfg[ch].mark_delay,
                mark_err
                ))
            self.log.debug('QueueSyncMode {}'.format(
                self.awg.AWGqueueSyncMode(self.__ch_map[ch], self.chcfg[ch].queue_sync)))

    def sync_clock(self):
        err = self.awg.clockResetPhase(1, 0, 0.0)
        clk = self.awg.clockIOconfig(1)
        freq = self.awg.clockGetFrequency()
        sfreq = self.awg.clockGetSyncFrequency()
        sfreq2 = self.awg.clockSetFrequency(freq)
        self.log.info('err: {} Clkcfg: {} SyncFreq: {} SyncFreq: {} Freq: {}'.format(err, clk, sfreq, sfreq2, freq))


class M3202ChannelCfg:
    def __init__(self):
        self.enable_trigger = False
        self.trig_source = ksd1.SD_TriggerExternalSources.TRIGGER_EXTERN
        self.trig_behaviour = ksd1.SD_TriggerBehaviors.TRIGGER_RISE
        self.trig_sync = ksd1.SD_SyncModes.SYNC_CLK10

        self.mark_sync = ksd1.SD_SyncModes.SYNC_CLK10
        self.mark_mode = ksd1.SD_MarkerModes.DISABLED
        self.mark_pxi = 0
        self.mark_io = 0
        self.mark_value = 1
        self.mark_length = 10
        self.mark_delay = 0

        self.queue_sync = ksd1.SD_SyncModes.SYNC_CLK10
