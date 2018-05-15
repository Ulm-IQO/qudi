# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for AWG70000 Series.

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

from core.util.modules import get_home_dir
import os
import time
import re
import visa
import numpy as np
from socket import socket, AF_INET, SOCK_STREAM
from ftplib import FTP
from collections import OrderedDict
from fnmatch import fnmatch

from core.module import Base, ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints


class AWG70K(Base, PulserInterface):
    """

    """
    _modclass = 'awg70k'
    _modtype = 'hardware'

    # config options
    _visa_address = ConfigOption('awg_visa_address', missing='error')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # connect ethernet socket
        self._rm = visa.ResourceManager()
        if self._visa_address not in self._rm.list_resources():
            self.log.error('VISA address "{0}" not found by the pyVISA resource manager.\nCheck '
                           'the connection by using for example "Agilent Connection Expert".'
                           ''.format(self._visa_address))
        else:
            self.awg = self._rm.open_resource(self._visa_address)
            # Set data transfer format (datatype, is_big_endian, container)
            self.awg.values_format.use_binary('f', False, np.array)
            # set timeout by default to 15 sec
            self.awg.timeout = 15000

        self.awg_model = self._get_model_ID()[1]
        self.log.debug('Found the following awg model: {0}'.format(self.awg_model))

        self.current_status = 0

    def on_deactivate(self):
        """ Required tasks to be performed during deactivation of the module.
        """
        # Closes the connection to the AWG
        try:
            self.awg.close()
        except:
            self.log.debug('Closing AWG connection using pyvisa failed.')
        self.log.info('Closed connection to AWG')
        return

    def get_constraints(self):
        """
        Retrieve the hardware constrains from the Pulsing device.

        @return constraints object: object with pulser constraints as attributes.

        Provides all the constraints (e.g. sample_rate, amplitude, total_length_bins,
        channel_config, ...) related to the pulse generator hardware to the caller.

            SEE PulserConstraints CLASS IN pulser_interface.py FOR AVAILABLE CONSTRAINTS!!!

        If you are not sure about the meaning, look in other hardware files to get an impression.
        If still additional constraints are needed, then they have to be added to the
        PulserConstraints class.

        Each scalar parameter is an ScalarConstraints object defined in cor.util.interfaces.
        Essentially it contains min/max values as well as min step size, default value and unit of
        the parameter.

        PulserConstraints.activation_config differs, since it contain the channel
        configuration/activation information of the form:
            {<descriptor_str>: <channel_list>,
             <descriptor_str>: <channel_list>,
             ...}

        If the constraints cannot be set in the pulsing hardware (e.g. because it might have no
        sequence mode) just leave it out so that the default is used (only zeros).
        """
        constraints = PulserConstraints()

        if self.awg_model == 'AWG70002A':
            constraints.sample_rate.min = 1.5e3
            constraints.sample_rate.max = 25.0e9
            constraints.sample_rate.step = 5.0e2
            constraints.sample_rate.default = 25.0e9
        elif self.awg_model == 'AWG70001A':
            constraints.sample_rate.min = 3.0e3
            constraints.sample_rate.max = 50.0e9
            constraints.sample_rate.step = 1.0e3
            constraints.sample_rate.default = 50.0e9

        constraints.a_ch_amplitude.min = 0.25
        constraints.a_ch_amplitude.max = 0.5
        constraints.a_ch_amplitude.step = 0.001
        constraints.a_ch_amplitude.default = 0.5
        # FIXME: Enter the proper digital channel low constraints:
        constraints.d_ch_low.min = 0.0
        constraints.d_ch_low.max = 0.0
        constraints.d_ch_low.step = 0.0
        constraints.d_ch_low.default = 0.0
        # FIXME: Enter the proper digital channel high constraints:
        constraints.d_ch_high.min = 0.0
        constraints.d_ch_high.max = 1.4
        constraints.d_ch_high.step = 0.1
        constraints.d_ch_high.default = 1.4

        constraints.sampled_file_length.min = 1
        constraints.sampled_file_length.max = 8000000000
        constraints.sampled_file_length.step = 1
        constraints.sampled_file_length.default = 1

        # FIXME: Check the proper number for your device
        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 32000
        constraints.waveform_num.step = 1
        constraints.waveform_num.default = 1
        # FIXME: Check the proper number for your device
        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 4000
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1
        # FIXME: Check the proper number for your device
        constraints.subsequence_num.min = 1
        constraints.subsequence_num.max = 8000
        constraints.subsequence_num.step = 1
        constraints.subsequence_num.default = 1

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65536
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0
        # ToDo: Check how many external triggers are available
        constraints.trigger_in.min = 0
        constraints.trigger_in.max = 2
        constraints.trigger_in.step = 1
        constraints.trigger_in.default = 0

        constraints.event_jump_to.min = 0
        constraints.event_jump_to.max = 8000
        constraints.event_jump_to.step = 1
        constraints.event_jump_to.default = 0

        constraints.go_to.min = 0
        constraints.go_to.max = 8000
        constraints.go_to.step = 1
        constraints.go_to.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe UNAMBIGUOUSLY the
        # channels. Here all possible channel configurations are stated, where only the generic
        # names should be used. The names for the different configurations can be customary chosen.
        activation_config = OrderedDict()
        if self.awg_model == 'AWG70002A':
            activation_config['all'] = {'a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3', 'd_ch4'}
            # Usage of both channels but reduced markers (higher analog resolution)
            activation_config['ch1_2mrk_ch2_1mrk'] = {'a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3'}
            activation_config['ch1_2mrk_ch2_0mrk'] = {'a_ch1', 'd_ch1', 'd_ch2', 'a_ch2'}
            activation_config['ch1_1mrk_ch2_2mrk'] = {'a_ch1', 'd_ch1', 'a_ch2', 'd_ch3', 'd_ch4'}
            activation_config['ch1_0mrk_ch2_2mrk'] = {'a_ch1', 'a_ch2', 'd_ch3', 'd_ch4'}
            activation_config['ch1_1mrk_ch2_1mrk'] = {'a_ch1', 'd_ch1', 'a_ch2', 'd_ch3'}
            activation_config['ch1_0mrk_ch2_1mrk'] = {'a_ch1', 'a_ch2', 'd_ch3'}
            activation_config['ch1_1mrk_ch2_0mrk'] = {'a_ch1', 'd_ch1', 'a_ch2'}
            # Usage of channel 1 only:
            activation_config['ch1_2mrk'] = {'a_ch1', 'd_ch1', 'd_ch2'}
            # Usage of channel 2 only:
            activation_config['ch2_2mrk'] = {'a_ch2', 'd_ch3', 'd_ch4'}
            # Usage of only channel 1 with one marker:
            activation_config['ch1_1mrk'] = {'a_ch1', 'd_ch1'}
            # Usage of only channel 2 with one marker:
            activation_config['ch2_1mrk'] = {'a_ch2', 'd_ch3'}
            # Usage of only channel 1 with no marker:
            activation_config['ch1_0mrk'] = {'a_ch1'}
            # Usage of only channel 2 with no marker:
            activation_config['ch2_0mrk'] = {'a_ch2'}
        elif self.awg_model == 'AWG70001A':
            activation_config['all'] = {'a_ch1', 'd_ch1', 'd_ch2'}
            # Usage of only channel 1 with one marker:
            activation_config['ch1_1mrk'] = {'a_ch1', 'd_ch1'}
            # Usage of only channel 1 with no marker:
            activation_config['ch1_0mrk'] = {'a_ch1'}

        constraints.activation_config = activation_config

        # FIXME: additional constraint really necessary?
        constraints.dac_resolution = {'min': 8, 'max': 10, 'step': 1, 'unit': 'bit'}
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        # Check if AWG is in function generator mode
        # self._activate_awg_mode()

        # do nothing if AWG is already running
        if not self._is_output_on():
            self.write('AWGC:RUN')
            # wait until the AWG is actually running
            while not self._is_output_on():
                time.sleep(0.25)
            self.current_status = 1
        return self.current_status

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        # do nothing if AWG is already idle
        if self._is_output_on():
            self.write('AWGC:STOP')
            # wait until the AWG has actually stopped
            while self._is_output_on():
                time.sleep(0.25)
            self.current_status = 0
        return self.current_status

    def write_waveform(self, name, analog_samples, digital_samples, is_first_chunk, is_last_chunk):
        """
        Write a new waveform or append samples to an already existing waveform on the device memory.
        The flags is_first_chunk and is_last_chunk can be used as indicator if a new waveform should
        be created or if the write process to a waveform should be terminated.

        @param name: str, the name of the waveform to be created/append to
        @param analog_samples: numpy.ndarray of type float32 containing the voltage samples
        @param digital_samples: numpy.ndarray of type bool containing the marker states
                                (if analog channels are active, this must be the same length as
                                analog_samples)
        @param is_first_chunk: bool, flag indicating if it is the first chunk to write.
                                     If True this method will create a new empty wavveform.
                                     If False the samples are appended to the existing waveform.
        @param is_last_chunk: bool, flag indicating if it is the last chunk to write.
                                    Some devices may need to know when to close the appending wfm.

        @return: (int, list) number of samples written (-1 indicates failed process) and list of
                             created waveform names
        """
        waveforms = list()

        # Sanity checks
        if len(analog_samples) > 0:
            number_of_samples = len(analog_samples[list(analog_samples)[0]])
        elif len(digital_samples) > 0:
            number_of_samples = len(digital_samples[list(digital_samples)[0]])
        else:
            self.log.error('No analog or digital samples passed to write_waveform method in dummy '
                           'pulser.')
            return -1, waveforms

        min_samples = int(self.query('WLIS:WAV:LMIN?'))
        if number_of_samples < min_samples:
            self.log.error('Unable to write waveform.\nNumber of samples to write ({0:d}) is '
                           'smaller than the allowed minimum waveform length ({1:d}).'
                           ''.format(number_of_samples, min_samples))
            return -1, waveforms

        for chnl, samples in analog_samples.items():
            if len(samples) != number_of_samples:
                self.log.error('Unable to write waveform.\nUnequal length of sample arrays for '
                               'different channels.')
                return -1, waveforms
        for chnl, samples in digital_samples.items():
            if len(samples) != number_of_samples:
                self.log.error('Unable to write waveform.\nUnequal length of sample arrays for '
                               'different channels.')
                return -1, waveforms

        # determine active channels
        activation_dict = self.get_active_channels()
        active_channels = {chnl for chnl in activation_dict if activation_dict[chnl]}
        active_analog = sorted(chnl for chnl in active_channels if chnl.startswith('a'))

        # Sanity check of channel numbers
        if active_channels != set(analog_samples.keys()).union(set(digital_samples.keys())):
            self.log.error('Mismatch of channel activation and sample array dimensions for '
                           'waveform creation.\nChannel activation is: {0}\nSample arrays have: '
                           ''.format(active_channels,
                                     set(analog_samples.keys()).union(set(digital_samples.keys()))))
            return -1, waveforms

        # Write waveforms. One for each analog channel.
        for a_ch in active_analog:
            # Get the integer analog channel number
            a_ch_num = int(a_ch.split('ch')[-1])
            # Get the digital channel specifiers belonging to this analog channel markers
            mrk_ch_1 = 'd_ch{0:d}'.format(a_ch_num * 2 - 1)
            mrk_ch_2 = 'd_ch{0:d}'.format(a_ch_num * 2)

            start = time.time()
            # Encode marker information in an array of bytes (uint8). Avoid intermediate copies!!!
            if mrk_ch_1 in digital_samples and mrk_ch_2 in digital_samples:
                mrk_bytes = digital_samples[mrk_ch_2].view('uint8')
                tmp_bytes = digital_samples[mrk_ch_1].view('uint8')
                np.left_shift(mrk_bytes, 7, out=mrk_bytes)
                np.left_shift(tmp_bytes, 6, out=tmp_bytes)
                np.add(mrk_bytes, tmp_bytes, out=mrk_bytes)
                # Free some memory
                del tmp_bytes
                del digital_samples[mrk_ch_1]
            elif mrk_ch_1 in digital_samples:
                mrk_bytes = digital_samples[mrk_ch_1].view('uint8')
                np.left_shift(mrk_bytes, 6, out=mrk_bytes)
            else:
                mrk_bytes = None
            print('Prepare digital channel data: {0}'.format(time.time()-start))

            # Create waveform name string
            wfm_name = '{0}_ch{1:d}'.format(name, a_ch_num)

            # Check if waveform already exists and delete if necessary.
            if wfm_name in self.get_waveform_names():
                self.delete_waveform(wfm_name)

            # Write WFMX file for waveform
            start = time.time()
            self.write_wfmx(filename=wfm_name,
                            analog_samples=analog_samples[a_ch],
                            digital_samples=mrk_bytes,
                            is_first_chunk=is_first_chunk,
                            is_last_chunk=is_last_chunk)
            print('Write WFMX file: {0}'.format(time.time() - start))

            # Delete samples data after writing to free up memory
            del analog_samples[a_ch], mrk_bytes
            del digital_samples[mrk_ch_2]

            # transfer waveform to AWG and load into workspace
            self._send_waveform(filename=wfm_name)
            self.write('MMEM:OPEN "{0}"'.format(os.path.join(self._ftp_path, wfm_name + '.wfmx')))
            # Wait for everything to complete
            while int(self.query('*OPC?')) != 1:
                time.sleep(0.25)

            # Append created waveform name to waveform list
            waveforms.append(wfm_name)
        return number_of_samples, waveforms

    def write_sequence(self, name, sequence_parameter_list):
        """
        Write a new sequence on the device memory.

        @param name: str, the name of the waveform to be created/append to
        @param sequence_parameter_list: list, contains the parameters for each sequence step and
                                        the according waveform names.

        @return: int, number of sequence steps written (-1 indicates failed process)
        """
        # Check if device has sequencer option installed
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. Sequencer option not '
                           'installed.')
            return -1

        # Check if all waveforms are present on device memory
        avail_waveforms = set(self.get_waveform_names())
        for waveform_tuple, param_dict in sequence_parameter_list:
            if not avail_waveforms.issuperset(waveform_tuple):
                self.log.error('Failed to create sequence "{0}" due to waveforms "{1}" not '
                               'present in device memory.'.format(name, waveform_tuple))
                return -1

        trig_dict = {-1: 'OFF', 0: 'OFF', 1: 'ATR', 2: 'BTR'}
        active_analog = sorted(chnl for chnl in self.get_active_channels() if chnl.startswith('a'))
        num_tracks = len(active_analog)
        num_steps = len(sequence_params)

        # Create new sequence and set jump timing to immediate.
        # Delete old sequence by the same name if present.
        self._generate_sequence(name=name, steps=num_steps, tracks=num_tracks)

        # Fill in sequence information
        for step, (wfm_tuple, seq_params) in enumerate(sequence_parameter_list):
            # Set waveforms to play
            if num_tracks == len(wfm_tuple):
                for track, waveform in enumerate(wfm_tuple):
                    self.write('SLIS:SEQ:STEP{0:d}:TASS{1:d}:WAV "{2}", "{3}"'.format(
                        step + 1, track + 1, name, waveform))
            else:
                self.log.error('Unable to write sequence.\nLength of waveform tuple "{0}" does not '
                               'match the number of sequence tracks.'.format(waveform_tuple))
                return -1

            # Set event trigger
            jumpto = str(seq_params['event_jump_to']) if seq_params['event_jump_to'] > 0 else 'NEXT'
            self.write('SLIS:SEQ:STEP{0:d}:EJUM "{1}", {2}'.format(step + 1, name, jumpto))
            if seq_params['repetitions'] > 0:
                self.write('SLIS:SEQ:STEP{0:d}:EJIN "{1}", {2}'.format(step + 1, name, 'OFF'))
            else:
                self.write('SLIS:SEQ:STEP{0:d}:EJIN "{1}", {2}'.format(step + 1, name, 'ATR'))

            # Set repetitions
            repeat = str(seq_params['repetitions']) if seq_params['repetitions'] > 0 else 'INF'
            self.write('SLIS:SEQ:STEP{0:d}:RCO "{1}", {2}'.format(step + 1, name, repeat))

            # Set go_to parameter
            goto = str(seq_params['go_to']) if seq_params['go_to'] > 0 else 'NEXT'
            self.write('SLIS:SEQ:STEP{0:d}:GOTO "{1}", {2}'.format(step + 1, name, goto))

        # Wait for everything to complete
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)
        return num_steps

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        try:
            query_return = self.query('WLIS:LIST?')
        except visa.VisaIOError:
            query_return = None
            self.log.error('Unable to read waveform list from device. VisaIOError occured.')
        waveform_list = sorted(query_return.split(',')) if query_return else list()
        return waveform_list

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        sequence_list = list()

        if not self.has_sequence_mode():
            return sequence_list

        try:
            number_of_seq = int(self.query('SLIS:SIZE?'))
            for ii in range(number_of_seq):
                sequence_list.append(self.query('SLIS:NAME? {0:d}'.format(ii + 1)))
        except visa.VisaIOError:
            self.log.error('Unable to read sequence list from device. VisaIOError occured.')
        return sequence_list

    def delete_waveform(self, waveform_name):
        """ Delete the waveform with name "waveform_name" from the device memory.

        @param str waveform_name: The name of the waveform to be deleted
                                  Optionally a list of waveform names can be passed.

        @return list: a list of deleted waveform names.
        """
        if isinstance(waveform_name, str):
            waveform_name = [waveform_name]

        avail_waveforms = self.get_waveform_names()
        deleted_waveforms = list()
        for waveform in waveform_name:
            if waveform in avail_waveforms:
                self.write('WLIS:WAV:DEL "{0}"'.format(waveform))
                deleted_waveforms.append(waveform)
        return deleted_waveforms

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory.

        @param str sequence_name: The name of the sequence to be deleted
                                  Optionally a list of sequence names can be passed.

        @return list: a list of deleted sequence names.
        """
        if isinstance(sequence_name, str):
            sequence_name = [sequence_name]

        avail_sequences = self.get_sequence_names()
        deleted_sequences = list()
        for sequence in sequence_name:
            if sequence in avail_sequences:
                self.write('SLIS:SEQ:DEL "{0}"'.format(sequence))
                deleted_sequences.append(sequence)
        return deleted_sequences

    def load_waveform(self, load_dict):
        """ Loads a waveform to the specified channel of the pulsing device.
        For devices that have a workspace (i.e. AWG) this will load the waveform from the device
        workspace into the channel.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param load_dict:  dict|list, a dictionary with keys being one of the available channel
                                      index and values being the name of the already written
                                      waveform to load into the channel.
                                      Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                  {1: rabi_ch2, 2: rabi_ch1}
                                      If just a list of waveform names if given, the channel
                                      association will be invoked from the channel
                                      suffix '_ch1', '_ch2' etc.

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel, string describing the asset
                             type ('waveform' or 'sequence')
        """
        if isinstance(load_dict, list):
            new_dict = dict()
            for waveform in load_dict:
                channel = int(waveform.rsplit('_ch', 1)[1])
                new_dict[channel] = waveform
            load_dict = new_dict

        # Get all active channels
        chnl_activation = self.get_active_channels()
        analog_channels = sorted(
            chnl for chnl in chnl_activation if chnl.startswith('a') and chnl_activation[chnl])

        # Check if all channels to load to are active
        channels_to_set = {'a_ch{0:d}'.format(chnl_num) for chnl_num in load_dict}
        if not channels_to_set.issubset(analog_channels):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more channels to set are not active.')
            return self.get_loaded_assets()

        # Check if all waveforms to load are present on device memory
        if not set(load_dict.values()).issubset(self.get_waveform_names()):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more waveforms to load are missing on device memory.')
            return self.get_loaded_assets()

        # Load waveforms into channels
        for chnl_num, waveform in load_dict.items():
            self.write('SOUR{0:d}:CASS:WAV "{1}"'.format(chnl_num, waveform))
            while self.query('SOUR{0:d}:CASS?'.format(chnl_num)) != waveform:
                time.sleep(0.1)

        return self.get_loaded_assets()

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.

        @param sequence_name:  str, name of the sequence to load

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel, string describing the asset
                             type ('waveform' or 'sequence')
        """
        if sequence_name not in self.get_sequence_names():
            self.log.error('Unable to load sequence.\n'
                           'Sequence to load is missing on device memory.')
            return self.get_loaded_assets()

        # Get all active channels
        chnl_activation = self.get_active_channels()
        analog_channels = sorted(
            chnl for chnl in chnl_activation if chnl.startswith('a') and chnl_activation[chnl])

        # Check if number of sequence tracks matches the number of analog channels
        trac_num = int(self.query('SLIS:SEQ:TRAC? "{0}"'.format(sequence_name)))
        if trac_num != len(analog_channels):
            self.log.error('Unable to load sequence.\nNumber of tracks in sequence to load does '
                           'not match the number of active analog channels.')
            return self.get_loaded_assets()

        # Load sequence
        for chnl in range(1, trac_num + 1):
            self.write('SOUR{0:d}:CASS:SEQ "{1}", {2:d}'.format(chnl, sequence_name, chnl))
            while self.query('SOUR{0:d}:CASS?'.format(chnl))[1:-2] != '{0},{1:d}'.format(
                    sequence_name, chnl):
                time.sleep(0.2)

        return self.get_loaded_assets()

    def get_loaded_assets(self):
        """ Retrieve the currently loaded asset names for each active channel of the device.
        The returned dictionary will have the channel numbers as keys.
        In case of loaded waveforms the dictionary values will be the waveform names.
        In case of a loaded sequence the values will be the sequence name appended by a suffix
        representing the track loaded to the respective channel (i.e. '<sequence_name>_1').

        @return (dict, str): Dictionary with keys being the channel number and values being the respective
        asset loaded into the channel, string describing the asset type ('waveform' or 'sequence')
        """
        # Get all active channels
        chnl_activation = self.get_active_channels()
        channel_numbers = sorted(int(chnl.split('_ch')[1]) for chnl in chnl_activation if
                                 chnl.startswith('a') and chnl_activation[chnl])

        # Get assets per channel
        loaded_assets = dict()
        current_type = None
        for chnl_num in channel_numbers:
            # Ask AWG for currently loaded waveform or sequence. The answer for a waveform will
            # look like '"waveformname"\n' and for a sequence '"sequencename,1"\n'
            # (where the number is the current track)
            asset_name = self.query('SOUR1:CASS?')
            # Figure out if a sequence or just a waveform is loaded by splitting after the comma
            splitted = asset_name.rsplit(',', 1)
            # If the length is 2 a sequence is loaded and if it is 1 a waveform is loaded
            asset_name = splitted[0]
            if len(splitted) > 1:
                if current_type is not None and current_type != 'sequence':
                    self.log.error('Unable to determine loaded assets.')
                    return dict(), ''
                current_type = 'sequence'
            else:
                if current_type is not None and current_type != 'waveform':
                    self.log.error('Unable to determine loaded assets.')
                    return dict(), ''
                current_type = 'waveform'
            loaded_assets[chnl_num] = asset_name

        return loaded_assets, current_type

    def clear_all(self):
        """ Clears all loaded waveform from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without storage capability
        (PulseBlaster, FPGA).
        """
        self.write('WLIS:WAV:DEL ALL')
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)
        if self.has_sequence_mode():
            self.write('SLIS:SEQ:DEL ALL')
            while int(self.query('*OPC?')) != 1:
                time.sleep(0.25)
        return 0

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): inter value of the current status with the
                             corresponding dictionary containing status
                             description for all the possible status variables
                             of the pulse generator hardware
        """
        status_dic = {}
        status_dic[-1] = 'Failed Request or Communication'
        status_dic[0] = 'Device has stopped, but can receive commands.'
        status_dic[1] = 'Device is active and running.'
        # All the other status messages should have higher integer values
        # then 1.
        return self.current_status, status_dic

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware

        @param float sample_rate: The sample rate to be set (in Hz)

        @return foat: the sample rate returned from the device (-1:error)
        """
        # Check if AWG is in function generator mode
        # self._activate_awg_mode()

        self.write('CLOCK:SRATE %.4G' % sample_rate)
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)
        time.sleep(1)
        self.get_sample_rate()
        return self.sample_rate

    def get_sample_rate(self):
        """ Set the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """
        return_rate = float(self.query('CLOCK:SRATE?'))
        self.sample_rate = return_rate
        return self.sample_rate

    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if a specific amplitude value (in Volt
                               peak to peak, i.e. the full amplitude) of a
                               channel is desired.
        @param list offset: optional, if a specific high value (in Volt) of a
                            channel is desired.

        @return dict: with keys being the generic string channel names and items
                      being the values for those channels. Amplitude is always
                      denoted in Volt-peak-to-peak and Offset in (absolute)
                      Voltage.

        Note: Do not return a saved amplitude and/or offset value but instead
              retrieve the current amplitude and/or offset directly from the
              device.

        If no entries provided then the levels of all channels where simply
        returned. If no analog channels provided, return just an empty dict.
        Example of a possible input:
            amplitude = ['a_ch1','a_ch4'], offset =[1,3]
        to obtain the amplitude of channel 1 and 4 and the offset
            {'a_ch1': -0.5, 'a_ch4': 2.0} {'a_ch1': 0.0, 'a_ch3':-0.75}
        since no high request was performed.

        The major difference to digital signals is that analog signals are
        always oscillating or changing signals, otherwise you can use just
        digital output. In contrast to digital output levels, analog output
        levels are defined by an amplitude (here total signal span, denoted in
        Voltage peak to peak) and an offset (a value around which the signal
        oscillates, denoted by an (absolute) voltage).

        In general there is no bijective correspondence between
        (amplitude, offset) and (value high, value low)!
        """
        amp = dict()
        off = dict()

        chnl_list = self._get_all_analog_channels()

        # get pp amplitudes
        if amplitude is None:
            for ch_num, chnl in enumerate(chnl_list):
                amp[chnl] = float(self.query('SOUR{0:d}:VOLT:AMPL?'.format(ch_num + 1)))
        else:
            for chnl in amplitude:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    amp[chnl] = float(self.query('SOUR{0:d}:VOLT:AMPL?'.format(ch_num)))
                else:
                    self.log.warning('Get analog amplitude from AWG70k channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))

        # get voltage offsets
        if offset is None:
            for ch_num, chnl in enumerate(chnl_list):
                off[chnl] = 0.0
        else:
            for chnl in offset:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    off[chnl] = 0.0
                else:
                    self.log.warning('Get analog offset from AWG70k channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))
        return amp, off

    def set_analog_level(self, amplitude=None, offset=None):
        """ Set amplitude and/or offset value of the provided analog channel.

        @param dict amplitude: dictionary, with key being the channel and items
                               being the amplitude values (in Volt peak to peak,
                               i.e. the full amplitude) for the desired channel.
        @param dict offset: dictionary, with key being the channel and items
                            being the offset values (in absolute volt) for the
                            desired channel.

        @return (dict, dict): tuple of two dicts with the actual set values for
                              amplitude and offset.

        If nothing is passed then the command will return two empty dicts.

        Note: After setting the analog and/or offset of the device, retrieve
              them again for obtaining the actual set value(s) and use that
              information for further processing.

        The major difference to digital signals is that analog signals are
        always oscillating or changing signals, otherwise you can use just
        digital output. In contrast to digital output levels, analog output
        levels are defined by an amplitude (here total signal span, denoted in
        Voltage peak to peak) and an offset (a value around which the signal
        oscillates, denoted by an (absolute) voltage).

        In general there is no bijective correspondence between
        (amplitude, offset) and (value high, value low)!
        """
        # Check the inputs by using the constraints...
        constraints = self.get_constraints()
        # ...and the available analog channels
        analog_channels = self._get_all_analog_channels()

        # amplitude sanity check
        if amplitude is not None:
            for chnl in amplitude:
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                if chnl not in analog_channels:
                    self.log.warning('Channel to set (a_ch{0}) not available in AWG.\nSetting '
                                     'analogue voltage for this channel ignored.'.format(chnl))
                    del amplitude[chnl]
                if amplitude[chnl] < constraints.a_ch_amplitude.min:
                    self.log.warning('Minimum Vpp for channel "{0}" is {1}. Requested Vpp of {2}V '
                                     'was ignored and instead set to min value.'
                                     ''.format(chnl, constraints.a_ch_amplitude.min,
                                               amplitude[chnl]))
                    amplitude[chnl] = constraints.a_ch_amplitude.min
                elif amplitude[chnl] > constraints.a_ch_amplitude.max:
                    self.log.warning('Maximum Vpp for channel "{0}" is {1}. Requested Vpp of {2}V '
                                     'was ignored and instead set to max value.'
                                     ''.format(chnl, constraints.a_ch_amplitude.max,
                                               amplitude[chnl]))
                    amplitude[chnl] = constraints.a_ch_amplitude.max
        # offset sanity check
        if offset is not None:
            for chnl in offset:
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                if chnl not in analog_channels:
                    self.log.warning('Channel to set (a_ch{0}) not available in AWG.\nSetting '
                                     'offset voltage for this channel ignored.'.format(chnl))
                    del offset[chnl]
                if offset[chnl] < constraints.a_ch_offset.min:
                    self.log.warning('Minimum offset for channel "{0}" is {1}. Requested offset of '
                                     '{2}V was ignored and instead set to min value.'
                                     ''.format(chnl, constraints.a_ch_offset.min, offset[chnl]))
                    offset[chnl] = constraints.a_ch_offset.min
                elif offset[chnl] > constraints.a_ch_offset.max:
                    self.log.warning('Maximum offset for channel "{0}" is {1}. Requested offset of '
                                     '{2}V was ignored and instead set to max value.'
                                     ''.format(chnl, constraints.a_ch_offset.max,
                                               offset[chnl]))
                    offset[chnl] = constraints.a_ch_offset.max

        amp = dict()
        off = dict()

        if amplitude is not None:
            for a_ch in amplitude:
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                self.write('SOUR{0:d}:VOLT:AMPL {1}'.format(ch_num, amplitude[a_ch]))
                amp[a_ch] = amplitude[a_ch]
            while int(self.query('*OPC?')) != 1:
                time.sleep(0.25)

        if offset is not None:
            for a_ch in offset:
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                self.write('SOUR{0:d}:VOLT:OFFSET {1}'.format(ch_num, offset[a_ch]))
                off[a_ch] = offset[a_ch]
            while int(self.query('*OPC?')) != 1:
                time.sleep(0.25)
        return amp, off

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided channels.

        @param list low: optional, if a specific low value (in Volt) of a
                         channel is desired.
        @param list high: optional, if a specific high value (in Volt) of a
                          channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel
                               number and items being the values for those
                               channels. Both low and high value of a channel is
                               denoted in (absolute) Voltage.

        Note: Do not return a saved low and/or high value but instead retrieve
              the current low and/or high value directly from the device.

        If no entries provided then the levels of all channels where simply
        returned. If no digital channels provided, return just an empty dict.

        Example of a possible input:
            low = ['d_ch1', 'd_ch4']
        to obtain the low voltage values of digital channel 1 an 4. A possible
        answer might be
            {'d_ch1': -0.5, 'd_ch4': 2.0} {}
        since no high request was performed.

        The major difference to analog signals is that digital signals are
        either ON or OFF, whereas analog channels have a varying amplitude
        range. In contrast to analog output levels, digital output levels are
        defined by a voltage, which corresponds to the ON status and a voltage
        which corresponds to the OFF status (both denoted in (absolute) voltage)

        In general there is no bijective correspondence between
        (amplitude, offset) and (value high, value low)!
        """
        # TODO: Test with multiple channel AWG
        low_val = {}
        high_val = {}

        digital_channels = self._get_all_digital_channels()

        if low is None:
            low = digital_channels
        if high is None:
            high = digital_channels

        # get low marker levels
        for chnl in low:
            if chnl not in digital_channels:
                continue
            d_ch_number = int(chnl.rsplit('_ch', 1)[1])
            a_ch_number = (1 + d_ch_number) // 2
            marker_index = 2 - (d_ch_number % 2)
            low_val[chnl] = float(
                self.query('SOUR{0:d}:MARK{1:d}:VOLT:LOW?'.format(a_ch_number, marker_index)))
        # get high marker levels
        for chnl in digital_channels:
            if chnl not in digital_channels:
                continue
            d_ch_number = int(chnl.rsplit('_ch', 1)[1])
            a_ch_number = (1 + d_ch_number) // 2
            marker_index = 2 - (d_ch_number % 2)
            high_val[chnl] = float(
                self.query('SOUR{0:d}:MARK{1:d}:VOLT:HIGH?'.format(a_ch_number, marker_index)))

        return low_val, high_val

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel.

        @param dict low: dictionary, with key being the channel and items being
                         the low values (in volt) for the desired channel.
        @param dict high: dictionary, with key being the channel and items being
                         the high values (in volt) for the desired channel.

        @return (dict, dict): tuple of two dicts where first dict denotes the
                              current low value and the second dict the high
                              value.

        If nothing is passed then the command will return two empty dicts.

        Note: After setting the high and/or low values of the device, retrieve
              them again for obtaining the actual set value(s) and use that
              information for further processing.

        The major difference to analog signals is that digital signals are
        either ON or OFF, whereas analog channels have a varying amplitude
        range. In contrast to analog output levels, digital output levels are
        defined by a voltage, which corresponds to the ON status and a voltage
        which corresponds to the OFF status (both denoted in (absolute) voltage)

        In general there is no bijective correspondence between
        (amplitude, offset) and (value high, value low)!
        """
        if low is None:
            low = dict()
        if high is None:
            high = dict()

        #If you want to check the input use the constraints:
        constraints = self.get_constraints()

        for d_ch, value in low.items():
            #FIXME: Tell the device the proper digital voltage low value:
            # self.tell('SOURCE1:MARKER{0}:VOLTAGE:LOW {1}'.format(d_ch, low[d_ch]))
            pass

        for d_ch, value in high.items():
            #FIXME: Tell the device the proper digital voltage high value:
            # self.tell('SOURCE1:MARKER{0}:VOLTAGE:HIGH {1}'.format(d_ch, high[d_ch]))
            pass
        return self.get_digital_level()

    def get_active_channels(self, ch=None):
        """ Get the active channels of the pulse generator hardware.

        @param list ch: optional, if specific analog or digital channels are
                        needed to be asked without obtaining all the channels.

        @return dict:  where keys denoting the channel number and items boolean
                       expressions whether channel are active or not.

        Example for an possible input (order is not important):
            ch = ['a_ch2', 'd_ch2', 'a_ch1', 'd_ch5', 'd_ch1']
        then the output might look like
            {'a_ch2': True, 'd_ch2': False, 'a_ch1': False, 'd_ch5': True, 'd_ch1': False}

        If no parameters are passed to this method all channels will be asked
        for their setting.
        """
        # If you want to check the input use the constraints:
        constraints = self.get_constraints()
        max_res = constraints.dac_resolution['max']

        digital_channels = self._get_all_digital_channels()
        analog_channels = self._get_all_analog_channels()

        active_ch = dict()
        for ch_num, a_ch in enumerate(analog_channels):
            ch_num = ch_num + 1
            # check what analog channels are active
            active_ch[a_ch] = bool(int(self.query('OUTPUT{0:d}:STATE?'.format(ch_num))))
            # check how many markers are active on each channel, i.e. the DAC resolution
            if active_ch[a_ch]:
                digital_mrk = max_res - int(self.query('SOUR{0:d}:DAC:RES?'.format(ch_num)))
                if digital_mrk == 2:
                    active_ch['d_ch{0:d}'.format(ch_num * 2)] = True
                    active_ch['d_ch{0:d}'.format(ch_num * 2 - 1)] = True
                elif digital_mrk == 1:
                    active_ch['d_ch{0:d}'.format(ch_num * 2)] = False
                    active_ch['d_ch{0:d}'.format(ch_num * 2 - 1)] = True
                else:
                    active_ch['d_ch{0:d}'.format(ch_num * 2)] = False
                    active_ch['d_ch{0:d}'.format(ch_num * 2 - 1)] = False
            else:
                active_ch['d_ch{0:d}'.format(ch_num * 2)] = False
                active_ch['d_ch{0:d}'.format(ch_num * 2 - 1)] = False

        # return either all channel information or just the one asked for.
        if ch is not None:
            chnl_to_delete = [chnl for chnl in active_ch if chnl not in ch]
            for chnl in chnl_to_delete:
                del active_ch[chnl]
        return active_ch

    def set_active_channels(self, ch=None):
        """ Set the active channels for the pulse generator hardware.

        @param dict ch: dictionary with keys being the analog or digital
                          string generic names for the channels with items being
                          a boolean value.current_loaded_asset

        @return dict: with the actual set values for active channels for analog
                      and digital values.

        If nothing is passed then the command will return an empty dict.

        Note: After setting the active channels of the device, retrieve them
              again for obtaining the actual set value(s) and use that
              information for further processing.

        Example for possible input:
            ch={'a_ch2': True, 'd_ch1': False, 'd_ch3': True, 'd_ch4': True}
        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1.

        The hardware itself has to handle, whether separate channel activation
        is possible.
        """
        current_channel_state = self.get_active_channels()

        if ch is None:
            return current_channel_state

        if not set(current_channel_state).issuperset(ch):
            self.log.error('Trying to (de)activate channels that are not present in AWG70k.\n'
                           'Setting of channel activation aborted.')
            return current_channel_state

        # Determine new channel activation states
        new_channels_state = current_channel_state.copy()
        for chnl in ch:
            new_channels_state[chnl] = ch[chnl]

        # check if the channels to set are part of the activation_config constraints
        constraints = self.get_constraints()
        new_active_channels = {chnl for chnl in new_channels_state if new_channels_state[chnl]}
        if new_active_channels not in constraints.activation_config.values():
            self.log.error('activation_config to set ({0}) is not allowed according to constraints.'
                           ''.format(new_active_channels))
            return current_channel_state

        # get lists of all analog channels
        analog_channels = self._get_all_analog_channels()

        # calculate dac resolution for each analog channel and set it in hardware.
        # Also (de)activate the analog channels accordingly
        max_res = constraints.dac_resolution['max']
        for a_ch in analog_channels:
            ach_num = int(a_ch.rsplit('_ch', 1)[1])
            # determine number of markers for current a_ch
            if new_channels_state['d_ch{0:d}'.format(2 * ach_num - 1)]:
                marker_num = 2 if new_channels_state['d_ch{0:d}'.format(2 * ach_num)] else 1
            else:
                marker_num = 0
            # set DAC resolution for this channel
            dac_res = max_res - marker_num
            self.write('SOUR{0:d}:DAC:RES {1:d}'.format(ach_num, dac_res))
            # (de)activate the analog channel
            if new_channels_state[a_ch]:
                self.write('OUTPUT{0:d}:STATE ON'.format(ach_num))
            else:
                self.write('OUTPUT{0:d}:STATE OFF'.format(ach_num))

        return self.get_active_channels()

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Unused for pulse generator hardware other than an AWG.
        """

        return False

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        @return bool: actual interleave status (True: ON, False: OFF)

        Note: After setting the interleave of the device, retrieve the
              interleave again and use that information for further processing.

        Unused for pulse generator hardware other than an AWG.
        """
        if state:
            self.log.warning('Interleave mode not available for the AWG 70000 Series!\n'
                             'Method call will be ignored.')
        return False

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        options = self.query('*OPT?')[1:-2].split(',')
        return '03' in options

    def reset(self):
        """Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.write('*RST')
        self.write('*WAI')
        return 0

    def query(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        answer = self.awg.query(question)
        answer = answer.strip()
        answer = answer.rstrip('\n')
        answer = answer.rstrip()
        answer = answer.strip('"')
        return answer

    def write(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        bytes_written, enum_status_code = self.awg.write(command)
        return int(enum_status_code)

    def _generate_sequence(self, name, steps, tracks=1):
        """
        Generate a new sequence 'name' having 'steps' number of steps and 'tracks' number of tracks

        @param str name: Name of the sequence which should be generated
        @param int steps: Number of steps
        @param int track: Number of tracks

        @return 0
        """
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        if name in self.get_sequence_names():
            self.delete_sequence(name)
        self.write('SLIS:SEQ:NEW "{0}", {1:d}, {2:d}'.format(name, steps, tracks))
        self.write('SLIS:SEQ:EVEN:JTIM "{0}", IMM'.format(name))
        return 0

    def _add_waveform2sequence(self, sequence_name, waveform_name, step, track, repeat):
        """
        Add the waveform 'waveform_name' to position 'step' in the sequence 'sequence_name' and
        repeat it 'repeat' times

        @param str sequence_name: Name of the sequence which should be editted
        @param str waveform_name: Name of the waveform which should be added
        @param int step: Position of the added waveform
        @param int track: track which should be editted
        @param int repeat: number of repetition of added waveform

        @return 0
        """
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        self.write('SLIS:SEQ:STEP{0:d}:TASS{1:d}:WAV "{2}", "{3}"'.format(
            step, track, sequence_name, waveform_name))
        self.write('SLIST:SEQUENCE:STEP{0:d}:RCOUNT "{1}", {2}'.format(step, sequence_name, repeat))
        return 0

    def _load_sequence(self, sequencename, track=1):
        """Load sequence file into RAM.

        @param sequencename:  Name of the sequence to load
        @param int track: Number of track to load

        return 0
        """
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        self.write('SOURCE1:CASSET:SEQUENCE "{0}", {1:d}'.format(sequencename, track))
        return 0

    def _make_sequence_continuous(self, sequencename):
        """
        Usually after a run of a sequence the output stops. Many times it is desired that the full
        sequence is repeated many times. This is achieved here by setting the 'jump to' value of
        the last element to 'First'

        @param sequencename: Name of the sequence which should be made continous

        @return int last_step: The step number which 'jump to' has to be set to 'First'
        """
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        last_step = int(self.query('SLIS:SEQ:LENG? "{0}"'.format(sequencename)))
        self.write('SLIS:SEQ:STEP{0:d}:GOTO "{1}",  FIRST'.format(last_step, sequencename))
        return last_step

    def _force_jump_sequence(self, final_step, channel=1):
        """
        This command forces the sequencer to jump to the specified step per channel. A
        force jump does not require a trigger event to execute the jump.
        For two channel instruments, if both channels are playing the same sequence, then
        both channels jump simultaneously to the same sequence step.

        @param channel: determines the channel number. If omitted, interpreted as 1
        @param final_step: Step to jump to. Possible options are
            FIRSt - This enables the sequencer to jump to first step in the sequence.
            CURRent - This enables the sequencer to jump to the current sequence step,
            essentially starting the current step over.
            LAST - This enables the sequencer to jump to the last step in the sequence.
            END - This enables the sequencer to go to the end and play 0 V until play is
            stopped.
            <NR1> - This enables the sequencer to jump to the specified step, where the
            value is between 1 and 16383.

        """
        self.write('SOURCE{0:d}:JUMP:FORCE {1}'.format(channel, final_step))
        return

    def _get_model_ID(self):
        """
        @return: a string which represents the model id of the AWG.
        """
        model_id = self.query('*IDN?').split(',')
        return model_id

    def _get_all_channels(self):
        """
        Helper method to return a sorted list of all technically available channel descriptors
        (e.g. ['a_ch1', 'a_ch2', 'd_ch1', 'd_ch2'])

        @return list: Sorted list of channels
        """
        configs = self.get_constraints().activation_config
        if 'all' in configs:
            largest_config = configs['all']
        else:
            largest_config = list(configs.values())[0]
            for config in configs.values():
                if len(largest_config) < len(config):
                    largest_config = config
        return sorted(largest_config)

    def _get_all_analog_channels(self):
        """
        Helper method to return a sorted list of all technically available analog channel
        descriptors (e.g. ['a_ch1', 'a_ch2'])

        @return list: Sorted list of analog channels
        """
        return [chnl for chnl in self._get_all_channels() if chnl.startswith('a')]

    def _get_all_digital_channels(self):
        """
        Helper method to return a sorted list of all technically available digital channel
        descriptors (e.g. ['d_ch1', 'd_ch2'])

        @return list: Sorted list of digital channels
        """
        return [chnl for chnl in self._get_all_channels() if chnl.startswith('d')]

    def _is_output_on(self):
        """
        Aks the AWG if the output is enabled, i.e. if the AWG is running

        @return: bool, (True: output on, False: output off)
        """
        return bool(int(self.query('AWGC:RST?')))
