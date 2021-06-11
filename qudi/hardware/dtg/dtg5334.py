# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the Tektronix DTG 5334.

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

import time
import pyvisa as visa
import numpy as np

from qudi.util.helpers import natural_sort
from qudi.core.configoption import ConfigOption
from qudi.interface.pulser_interface import PulserInterface, PulserConstraints, SequenceOption


class DTG5334(PulserInterface):
    """ Tektronix DTG 5334

    Example config for copy-paste:

    pulser_dtg:
        module.Class: 'dtg.dtg5334.DTG5334'
        visa_address: 'GPIB0::12::INSTR'

    """

    visa_address = ConfigOption('visa_address', missing='error')

    ch_map = {
        'd_ch1': ('A', 1),
        'd_ch2': ('A', 2),
        'd_ch3': ('B', 1),
        'd_ch4': ('B', 2),
        'd_ch5': ('C', 1),
        'd_ch6': ('C', 2),
        'd_ch7': ('D', 1),
        'd_ch8': ('D', 2)
    }

    modules_map = {
        -1: 'No module',
        1: 'DTGM10',
        2: 'DTGM20',
        3: 'DTGM30',
        4: 'DTGM31',
        5: 'DTGM31',
        6: 'DTGM32'
    }

    stb_values = {
        0: 'Wat'
    }

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.current_loaded_assets = {}

        # connect to DTG
        self._rm = visa.ResourceManager()

        self.dtg = self._rm.open_resource(self.visa_address)

        # set timeout by default to 15 sec
        self.dtg.timeout = 15000

        self.connected = True

        self._mfg, self._model, self._serial, self._fw , self._version = self._get_id()
        self.log.debug('Found the following model: {0} {1} {2} {3} {4}'.format(
            self._mfg, self._model, self._serial, self._fw, self._version))
        self._modules = self._get_modules()
        self.log.debug('Found the following modules: {0}'.format(self._modules))

        self.current_loaded_assets = {}
        self.current_loaded_asset_type = ''
        self.waveform_names = set()
        self.sequence_names = set()

    def on_deactivate(self):
        """ Required tasks to be performed during deactivation of the module.
        """
        # Closes the connection to the DTG
        try:
            self.dtg.close()
        except:
            self.log.debug('Closing DTG connection using pyvisa failed.')
        self.log.info('Closed connection to DTG')
        self.connected = False
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
        # Example for configuration with default values:
        constraints = PulserConstraints()

        constraints.sample_rate.min = 50e3
        constraints.sample_rate.max = 3.35e9
        constraints.sample_rate.step = 1e3
        constraints.sample_rate.default = 12.0e9

        constraints.a_ch_amplitude.min = 0.0
        constraints.a_ch_amplitude.max = 0.0
        constraints.a_ch_amplitude.step = 0.0
        constraints.a_ch_amplitude.default = 0.0

        constraints.a_ch_offset.min = 0.0
        constraints.a_ch_offset.max = 0.0
        constraints.a_ch_offset.step = 0.0
        constraints.a_ch_offset.default = 0.0

        constraints.d_ch_low.min = -2.0
        constraints.d_ch_low.max = 2.44
        constraints.d_ch_low.step = 0.05
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = -1.0
        constraints.d_ch_high.max = 2.47
        constraints.d_ch_high.step = 0.05
        constraints.d_ch_high.default = 2.4

        constraints.waveform_length.min = 80
        constraints.waveform_length.max = 64800000
        constraints.waveform_length.step = 1
        constraints.waveform_length.default = 80

        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 32000
        constraints.waveform_num.step = 1
        constraints.waveform_num.default = 1

        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 8000
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1

        constraints.subsequence_num.min = 1
        constraints.subsequence_num.max = 4000
        constraints.subsequence_num.step = 1
        constraints.subsequence_num.default = 1

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65539
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0

        constraints.event_triggers = ['A', 'B']
        constraints.flags = list()

        constraints.sequence_steps.min = 0
        constraints.sequence_steps.max = 8000
        constraints.sequence_steps.step = 1
        constraints.sequence_steps.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe UNAMBIGUOUSLY the
        # channels. Here all possible channel configurations are stated, where only the generic
        # names should be used. The names for the different configurations can be customary chosen.
        activation_conf = dict()
        activation_conf['A'] = frozenset({'d_ch1', 'd_ch2'})
        activation_conf['B'] = frozenset({'d_ch3', 'd_ch4'})
        activation_conf['C'] = frozenset({'d_ch5', 'd_ch6'})
        activation_conf['D'] = frozenset({'d_ch7', 'd_ch8'})
        activation_conf['AB'] = frozenset({'d_ch1', 'd_ch2', 'd_ch3', 'd_ch4'})
        activation_conf['ABC'] = frozenset({'d_ch1', 'd_ch2', 'd_ch3', 'd_ch4', 'd_ch5', 'd_ch6'})
        activation_conf['all'] = frozenset(
            {'d_ch1', 'd_ch2', 'd_ch3', 'd_ch4', 'd_ch5', 'd_ch6', 'd_ch7', 'd_ch8'})
        constraints.activation_config = activation_conf
        constraints.sequence_option = SequenceOption.FORCED
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write('OUTP:STAT:ALL ON;*WAI')
        self.dtg.write('TBAS:RUN ON')
        state = 0 if int(self.dtg.query('TBAS:RUN?')) == 1 else -1
        return state

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write('OUTP:STAT:ALL OFF;*WAI')
        self.dtg.write('TBAS:RUN OFF')
        state = 0 if int(self.dtg.query('TBAS:RUN?')) == 0 else -1
        return state

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

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """
        pass

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param sequence_name:  dict|list, a dictionary with keys being one of the available channel
                                      index and values being the name of the already written
                                      waveform to load into the channel.
                                      Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                  {1: rabi_ch2, 2: rabi_ch1}
                                      If just a list of waveform names if given, the channel
                                      association will be invoked from the channel
                                      suffix '_ch1', '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """
        pass

    def get_loaded_assets(self):
        """
        Retrieve the currently loaded asset names for each active channel of the device.

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel,
                             string describing the asset type ('waveform' or 'sequence')
        """
        return self.current_loaded_assets, self.current_loaded_asset_type

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write('GROUP:DEL:ALL;*WAI')
        self.dtg.write('BLOC:DEL:ALL;*WAI')
        self.current_loaded_assets = {}
        return 0

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): tuple with an integer value of the current status and a corresponding
                             dictionary containing status description for all the possible status
                             variables of the pulse generator hardware.
        """
        status = 0
        return status, self.stb_values

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead retrieve the current
        sample rate directly from the device.
        """
        return float(self.dtg.query('TBAS:FREQ?'))

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """
        self.dtg.write('TBAS:FREQ {0:e}'.format(sample_rate))
        return self.get_sample_rate()

    def get_analog_level(self, amplitude=None, offset=None):
        """ Device has no analog channels.
        """
        return {}, {}

    def set_analog_level(self, amplitude=None, offset=None):
        """ Device has no analog channels.
        """
        return {}, {}

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels.

        @param list low: optional, if the low value (in Volt) of a specific channel is desired.
        @param list high: optional, if the high value (in Volt) of a specific channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor strings
                               (i.e. 'd_ch1', 'd_ch2') and items being the values for those
                               channels. Both low and high value of a channel is denoted in volts.

        Note: Do not return a saved low and/or high value but instead retrieve
              the current low and/or high value directly from the device.
        """
        if low is None:
            low = self.get_constraints().activation_config['all']
        if high is None:
            high = self.get_constraints().activation_config['all']

        ch_low = {
            chan:
                float(
                    self.dtg.query('PGEN{0}:CH{1}:LOW?'.format(
                        *(self.ch_map[chan])
                    ))
                )
            for chan in low
        }

        ch_high = {
            chan:
                float(
                    self.dtg.query('PGEN{0}:CH{1}:HIGH?'.format(
                        *(self.ch_map[chan])
                    ))
                )
            for chan in high
        }

        return ch_high, ch_low

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

        If nothing is passed then the command will return the current voltage levels.

        Note: After setting the high and/or low values of the device, use the actual set return
              values for further processing.
        """
        if low is None:
            low = {}
        if high is None:
            high = {}

        for chan, level in low.items():
            gen, gen_ch = self.ch_map[chan]
            self.dtg.write('PGEN{0}:CH{1}:LOW {2}'.format(gen, gen_ch, level))

        for chan, level in high.items():
            gen, gen_ch = self.ch_map[chan]
            self.dtg.write('PGEN{0}:CH{1}:HIGH {2}'.format(gen, gen_ch, level))

        return self.get_digital_level()

    def get_active_channels(self, ch=None):
        """ Get the active channels of the pulse generator hardware.

        @param list ch: optional, if specific analog or digital channels are needed to be asked
                        without obtaining all the channels.

        @return dict:  where keys denoting the channel string and items boolean expressions whether
                       channel are active or not.

        If no parameter (or None) is passed to this method all channel states will be returned.
        """
        if ch is None:
            chan_list = self.get_constraints().activation_config['all']
        active_ch = {chan: 1 for chan in chan_list}

        return active_ch

    def set_active_channels(self, ch=None):
        """
        Set the active/inactive channels for the pulse generator hardware.
        The state of ALL available analog and digital channels will be returned
        (True: active, False: inactive).
        The actually set and returned channel activation must be part of the available
        activation_configs in the constraints.
        You can also activate/deactivate subsets of available channels but the resulting
        activation_config must still be valid according to the constraints.
        If the resulting set of active channels can not be found in the available
        activation_configs, the channel states must remain unchanged.

        @param dict ch: dictionary with keys being the analog or digital string generic names for
                        the channels (i.e. 'd_ch1', 'a_ch2') with items being a boolean value.
                        True: Activate channel, False: Deactivate channel

        @return dict: with the actual set values for ALL active analog and digital channels

        If nothing is passed then the command will simply return the unchanged current state.

        Note: After setting the active channels of the device, use the returned dict for further
              processing.

        Example for possible input:
            ch={'a_ch2': True, 'd_ch1': False, 'd_ch3': True, 'd_ch4': True}
        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1. All other available channels will remain unchanged.
        """
        for chan, state in ch.items():
            gen, gen_ch = self.ch_map[chan]
            b_state = 1 if state else 0
            self.dtg.write('PGEN{0}:CH{1}:OUTP {2}'.format(gen, gen_ch, b_state))

        return self.get_active_channels()

    def write_waveform(self, name, analog_samples, digital_samples, is_first_chunk, is_last_chunk,
                       total_number_of_samples):
        """
        Write a new waveform or append samples to an already existing waveform on the device memory.
        The flags is_first_chunk and is_last_chunk can be used as indicator if a new waveform should
        be created or if the write process to a waveform should be terminated.

        NOTE: All sample arrays in analog_samples and digital_samples must be of equal length!

        @param str name: the name of the waveform to be created/append to
        @param dict analog_samples: keys are the generic analog channel names (i.e. 'a_ch1') and
                                    values are 1D numpy arrays of type float32 containing the
                                    voltage samples.
        @param dict digital_samples: keys are the generic digital channel names (i.e. 'd_ch1') and
                                     values are 1D numpy arrays of type bool containing the marker
                                     states.
        @param bool is_first_chunk: Flag indicating if it is the first chunk to write.
                                    If True this method will create a new empty wavveform.
                                    If False the samples are appended to the existing waveform.
        @param bool is_last_chunk:  Flag indicating if it is the last chunk to write.
                                    Some devices may need to know when to close the appending wfm.
        @param int total_number_of_samples: The number of sample points for the entire waveform
                                            (not only the currently written chunk)

        @return (int, list): Number of samples written (-1 indicates failed process) and list of
                             created waveform names
        """
        # check input
        if not name:
            self.log.error('Please specify a name for waveform creation.')
            return -1

        min_samples = 960
        longest_channel = max([len(v) for k, v in digital_samples.items()])
        print('Loading block with', longest_channel, 'samples')
        if longest_channel < min_samples:
            self.log.error('Minimum waveform length for DTG5334 series is {0} samples.\n'
                           'Direct waveform creation for {1} failed.'.format(min_samples, name))
            return -1

        # determine active channels
        activation_dict = self.get_active_channels()
        active_chnl = [chnl for chnl in activation_dict if activation_dict[chnl]]
        active_digital = [chnl for chnl in active_chnl if 'd_ch' in chnl]
        active_digital.sort()
        print(active_digital)

        # Sanity check of channel numbers
        if set(active_digital) != set(digital_samples.keys()):
            self.log.error(
                'Mismatch of channel activation and sample array dimensions for direct '
                'write.\nChannel activation is: {}.\n'
                'Sample arrays have: {}.'
                ''.format(active_digital, list(digital_samples.keys())))
            return -1

        self._block_new(name, longest_channel)
        self.log.debug(self.dtg.query('BLOC:SEL?'))
        written = self._block_write(name, digital_samples)
        print(written)
        self.current_loaded_assets = {int(ch.split('_ch')[1]): name for ch in active_digital}
        self.current_loaded_asset_type = 'waveform'
        self.waveform_names.add(name)

        return max(written), [name]

    def write_sequence(self, name, sequence_parameters):
        """
        Write a new sequence on the device memory.

        @param name: str, the name of the waveform to be created/append to
        @param sequence_parameters: dict, dictionary containing the parameters for a sequence

        @return: int, number of sequence steps written (-1 indicates failed process)
        """
        num_steps = len(sequence_parameters)

        # Check if sequence already exists and delete if necessary.
        #if sequence_name in self._get_sequence_names_memory():
        #    self.dtg.write('BLOC:DEL "{0}"'.format(sequence_name))
        self._set_sequence_length(num_steps)
        for line_nr, (wfms, params) in enumerate(sequence_parameters):
            print(line_nr, params)
            go_to = '' if params['go_to'] <= 0 else params['go_to']
            jump_to = '' if params['event_jump_to'] <= 0 else params['event_jump_to']
            reps = 0 if params['repetitions'] <= 0 else params['repetitions']
            self._set_sequence_line(
                line_nr,
                '{0}'.format(line_nr + 1),
                0,
                params['name'][0].rsplit('.')[0],
                reps,
                jump_to,
                go_to
            )

        # Wait for everything to complete
        while int(self.dtg.query('*OPC?')) != 1:
            time.sleep(0.2)

        self.sequence_names.add(name)
        return 0

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        return list(natural_sort(self.waveform_names))

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        return list(natural_sort(self.sequence_names))

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

        Unused for pulse generator hardware other than an AWG.
        """
        return False

    def write(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write(command)

    def query(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        return self.dtg.query(question)

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write('*RST')

    def _get_id(self):
        result = self.dtg.query('*IDN?')
        version = self.dtg.query('SYSTEM:VERSION?')
        ret = result.replace('\n', '').split(',')
        ret.append(version.replace('\n', ''))
        return ret

    def _get_modules(self):
        a = self.modules_map[int(self.dtg.query('PGENA:ID?'))]
        b = self.modules_map[int(self.dtg.query('PGENB:ID?'))]
        c = self.modules_map[int(self.dtg.query('PGENC:ID?'))]
        d = self.modules_map[int(self.dtg.query('PGEND:ID?'))]
        return [a, b, c, d]

    def _is_output_on(self):
        return int(self.dtg.query('TBAS:RUN?')) == 1

    def _block_length(self, name):
        return int(self.dtg.query('BLOC:LENG? "{0}"'.format(name)))

    def _block_exists(self, name):
        return self._block_length(name) != -1

    def _block_delete(self, name):
        self.dtg.write('BLOC:DEL "{0}"'.format(name))

    def _block_new(self, name, length):
        if self._block_exists(name):
            self._block_delete(name)

        self.dtg.write('BLOC:NEW "{0}", {1}'.format(name, length))
        self.dtg.query('*OPC?')
        self.dtg.write('BLOC:SEL "{0}"'.format(name))
        self.dtg.query('*OPC?')

    def _block_write(self, name, digital_samples):
        written = []
        self.dtg.write('BLOC:SEL "{0}"'.format(name))

        for ch, data in sorted(digital_samples.items()):
            written.append(self._channel_write_binary(ch, data))

        self.dtg.query('*OPC?')
        return written

    def _channel_write(self, channel, data):
        c = self.ch_map[channel]
        max_blocksize = 500
        dlen = len(data)
        written = 0
        start = 0

        # when there is more than 1MB of data to transfer, split it up
        print('Starting chunked transfer')
        while dlen >= max_blocksize:
            end = start + max_blocksize
            datstr = ''.join(map(lambda x: str(int(x)), data[start:end]))
            print(channel, 'loop', dlen, len(datstr))
            self.dtg.write('PGEN{0}:CH{1}:DATA {2},{3},"{4}"'.format(
                c[0], c[1], start, end - start, datstr))
            self.dtg.query('*OPC?')
            written += end - start
            dlen -= end - start
            start = end

        end = start + dlen
        if dlen > 0:
            datstr = ''.join(map(lambda x: str(int(x)), data[start:end]))
            print(channel, 'last', len(datstr))
            self.dtg.write(
                'PGEN{0}:CH{1}:DATA {2},{3},"{4}"'.format(
                    c[0], c[1], start, end - start, datstr)
            )
            self.dtg.query('*OPC?')
            written += end - start
        return written

    def _channel_write_binary(self, channel, data):
        c = self.ch_map[channel]
        max_blocksize = 8 * 800
        dlen = len(data)
        written = 0
        start = 0

        # when there is more than 1MB of data to transfer, split it up
        while dlen >= max_blocksize - 8:
            end = start + max_blocksize
            bytestr = np.packbits(np.fliplr(np.reshape(data[start:end], (-1, 8))))
            print(channel, '->', c, 'start', start, 'end', end, 'len', dlen, 'packed', len(bytestr))
            #print(bytestr)
            self.dtg.write_binary_values(
                'PGEN{0}:CH{1}:BDATA {2},{3},'.format(c[0], c[1], start, end - start),
                bytestr,
                datatype='B'
            )
            print(self.dtg.query('*OPC?'))
            written += end - start
            dlen -= end - start
            start = end

        end = start + dlen
        if dlen > 0:
            to_pad = 8 - dlen % 8 if dlen % 8 != 0 else 0

            padded_bytes = np.packbits(
                np.fliplr(
                    np.reshape(
                        np.pad(data[start:end], (0, to_pad), 'constant'),
                        (-1, 8)
                    )
                )
            )
            #print(padded_bytes)
            print(channel, '-->', c, 'start', start, 'end', end,
                  'len', dlen, 'padded', len(padded_bytes))
            self.dtg.write_binary_values(
                'PGEN{0}:CH{1}:BDATA {2},{3},'.format(c[0], c[1], start, end - start),
                padded_bytes,
                datatype='B'
            )
            print(self.dtg.query('*OPC?'))
            written += end - start
        return written

    def _get_sequence_line(self, line_nr):
        fields = self.dtg.query('SEQ:DATA? {0}'.format(line_nr)).split(', ')
        print(fields)
        label, trigger, block, repeat, jump, goto = fields
        return (
            label.strip('"'),
            int(trigger),
            block.strip('"'),
            int(repeat),
            jump.strip('"'),
            goto.strip('"')
        )

    def _set_sequence_line(self, line_nr, label, trigger, block, repeat, jump, goto):
        print(line_nr, label, trigger, block, repeat, jump, goto)
        self.dtg.write('SEQ:DATA {0}, "{1}", {2}, "{3}", {4}, "{5}", "{6}"'.format(
            line_nr, label, trigger, block, repeat, jump, goto
        ))

    def _get_sequence_length(self):
        return int(self.dtg.query('SEQ:LENG?'))

    def _set_sequence_length(self, length):
        self.dtg.write('SEQ:LENG {0}'.format(length))

    def _get_sequencer_mode(self):
        return self.dtg.query('TBAS:SMODE?')
