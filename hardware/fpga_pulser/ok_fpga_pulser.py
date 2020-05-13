# -*- coding: utf-8 -*-
"""
Use OK FPGA as a digital pulse sequence generator.

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

from core.module import Base
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from core.util.modules import get_main_dir
from interface.pulser_interface import PulserInterface, PulserConstraints, SequenceOption
import okfrontpanel as ok
import numpy as np
import time
import os
from collections import OrderedDict


class OkFpgaPulser(Base, PulserInterface):
    """ Methods to control Pulse Generator running on OK FPGA.

    Chan   PIN
    ----------
    Ch1    A3
    Ch2    C5
    Ch3    D6
    Ch4    B6
    Ch5    C7
    Ch6    B8
    Ch7    D9
    Ch8    C9

    Example config for copy-paste:

    fpga_pulser_ok:
        module.Class: 'fpga_fastcounter.fast_pulser_qo.OkFpgaPulser'
        fpga_serial: '143400058N'
        fpga_type: 'XEM6310_LX150'

    """
    _fpga_serial = ConfigOption(name='fpga_serial', missing='error')
    _fpga_type = ConfigOption(name='fpga_type', default='XEM6310_LX150', missing='warn')

    __current_waveform = StatusVar(name='current_waveform', default=np.zeros(32, dtype='uint8'))
    __current_waveform_name = StatusVar(name='current_waveform_name', default='')
    __sample_rate = StatusVar(name='sample_rate', default=950e6)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.__current_status = -1
        self.__currently_loaded_waveform = ''  # loaded and armed waveform name
        self.__samples_written = 0
        self._fp3support = False
        self.fpga = None  # Reference to the OK FrontPanel instance

    def on_activate(self):
        self.__samples_written = 0
        self.__currently_loaded_waveform = ''
        self.fpga = ok.FrontPanel()
        self._connect_fpga()
        self.set_sample_rate(self.__sample_rate)

    def on_deactivate(self):
        self._disconnect_fpga()

    @__current_waveform.representer
    def _convert_current_waveform(self, waveform_bytearray):
        return np.frombuffer(waveform_bytearray, dtype='uint8')

    @__current_waveform.constructor
    def _recover_current_waveform(self, waveform_nparray):
        return bytearray(waveform_nparray.tobytes())

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
            {<descriptor_str>: <channel_set>,
             <descriptor_str>: <channel_set>,
             ...}

        If the constraints cannot be set in the pulsing hardware (e.g. because it might have no
        sequence mode) just leave it out so that the default is used (only zeros).
        """
        constraints = PulserConstraints()

        constraints.sample_rate.min = 500e6
        constraints.sample_rate.max = 950e6
        constraints.sample_rate.step = 450e6
        constraints.sample_rate.default = 950e6

        constraints.a_ch_amplitude.min = 0.0
        constraints.a_ch_amplitude.max = 0.0
        constraints.a_ch_amplitude.step = 0.0
        constraints.a_ch_amplitude.default = 0.0

        constraints.a_ch_offset.min = 0.0
        constraints.a_ch_offset.max = 0.0
        constraints.a_ch_offset.step = 0.0
        constraints.a_ch_offset.default = 0.0

        constraints.d_ch_low.min = 0.0
        constraints.d_ch_low.max = 0.0
        constraints.d_ch_low.step = 0.0
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = 3.3
        constraints.d_ch_high.max = 3.3
        constraints.d_ch_high.step = 0.0
        constraints.d_ch_high.default = 3.3

        constraints.waveform_length.min = 1024
        constraints.waveform_length.max = 134217728
        constraints.waveform_length.step = 1
        constraints.waveform_length.default = 1024

        # the name a_ch<num> and d_ch<num> are generic names, which describe UNAMBIGUOUSLY the
        # channels. Here all possible channel configurations are stated, where only the generic
        # names should be used. The names for the different configurations can be customary chosen.
        activation_config = OrderedDict()
        activation_config['all'] = frozenset(
            {'d_ch1', 'd_ch2', 'd_ch3', 'd_ch4', 'd_ch5', 'd_ch6', 'd_ch7', 'd_ch8'})
        constraints.activation_config = activation_config

        constraints.sequence_option = SequenceOption.NON
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error)
        """
        self.__current_status = 1
        return self.write(0x01)

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error)
        """
        self.__current_status = 0
        return self.write(0x00)

    def load_waveform(self, load_dict):
        """ Loads a waveform to the specified channel of the pulsing device.
        For devices that have a workspace (i.e. AWG) this will load the waveform from the device
        workspace into the channel.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param dict|list load_dict: a dictionary with keys being one of the available channel
                                    index and values being the name of the already written
                                    waveform to load into the channel.
                                    Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                {1: rabi_ch2, 2: rabi_ch1}
                                    If just a list of waveform names if given, the channel
                                    association will be invoked from the channel
                                    suffix '_ch1', '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """
        # Since only one waveform can be present at a time check if only a single name is given
        if isinstance(load_dict, list):
            waveforms = list(set(load_dict))
        elif isinstance(load_dict, dict):
            waveforms = list(set(load_dict.values()))
        else:
            self.log.error('Method load_waveform expects a list of waveform names or a dict.')
            return self.get_loaded_assets()[0]

        if len(waveforms) != 1:
            self.log.error('FPGA pulser expects exactly one waveform name for load_waveform.')
            return self.get_loaded_assets()[0]

        waveform = waveforms[0]
        if waveform != self.__current_waveform_name:
            self.log.error('No waveform by the name "{0}" generated for FPGA pulser.\n'
                           'Only one waveform at a time can be held.'.format(waveform))
            return self.get_loaded_assets()[0]

        # calculate size of the two bytearrays to be transmitted. The biggest part is tranfered
        # in 1024 byte blocks and the rest is transfered in 32 byte blocks
        big_bytesize = (len(self.__current_waveform) // 1024) * 1024
        small_bytesize = len(self.__current_waveform) - big_bytesize

        # try repeatedly to upload the samples to the FPGA RAM
        # stop if the upload was successful
        loop_count = 0
        while True:
            loop_count += 1
            # reset FPGA
            self.reset()
            # upload sequence
            if big_bytesize != 0:
                # enable sequence write mode in FPGA
                self.write((255 << 24) + 2)
                # write to FPGA DDR2-RAM
                self.fpga.WriteToBlockPipeIn(0x80, 1024, self.__current_waveform[0:big_bytesize])
            if small_bytesize != 0:
                # enable sequence write mode in FPGA
                self.write((8 << 24) + 2)
                # write to FPGA DDR2-RAM
                self.fpga.WriteToBlockPipeIn(0x80, 32, self.__current_waveform[big_bytesize:])

            # check if upload was successful
            self.write(0x00)
            # start the pulse sequence
            self.__current_status = 1
            self.write(0x01)
            # wait for 600ms
            time.sleep(0.6)
            # get status flags from FPGA
            flags = self.query()
            self.__current_status = 0
            self.write(0x00)
            # check if the memory readout works.
            if flags == 0:
                self.log.info('Loading of waveform "{0}" to FPGA was successful.\n'
                              'Upload attempts needed: {1}'.format(waveform, loop_count))
                self.__currently_loaded_waveform = waveform
                break
            if loop_count == 10:
                self.log.error('Unable to upload waveform to FPGA.\n'
                               'Abort loading after 10 failed attempts.')
                self.reset()
                break
        return self.get_loaded_assets()[0]

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param dict|list sequence_name: a dictionary with keys being one of the available channel
                                        index and values being the name of the already written
                                        waveform to load into the channel.
                                        Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                    {1: rabi_ch2, 2: rabi_ch1}
                                        If just a list of waveform names if given, the channel
                                        association will be invoked from the channel
                                        suffix '_ch1', '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """
        self.log.warning('FPGA digital pulse generator has no sequencing capabilities.\n'
                         'load_sequence call ignored.')
        return dict()

    def get_loaded_assets(self):
        """
        Retrieve the currently loaded asset names for each active channel of the device.
        The returned dictionary will have the channel numbers as keys.
        In case of loaded waveforms the dictionary values will be the waveform names.
        In case of a loaded sequence the values will be the sequence name appended by a suffix
        representing the track loaded to the respective channel (i.e. '<sequence_name>_1').

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel,
                             string describing the asset type ('waveform' or 'sequence')
        """
        asset_type = 'waveform' if self.__currently_loaded_waveform else None
        asset_dict = {chnl_num: self.__currently_loaded_waveform for chnl_num in range(1, 9)}
        return asset_dict, asset_type

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)
        """
        self.pulser_off()
        self.__currently_loaded_waveform = ''
        self.__current_waveform_name = ''
        # just for good measures, write and load a empty waveform
        self.__current_waveform = bytearray(np.zeros(32))
        self.__samples_written = 32
        self.load_waveform([self.__current_waveform_name])
        return 0

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): tuple with an integer value of the current status
                             and a corresponding dictionary containing status
                             description for all the possible status variables
                             of the pulse generator hardware.
        """
        status_dic = dict()
        status_dic[-1] = 'Failed Request or Failed Communication with device.'
        status_dic[0] = 'Device has stopped, but can receive commands.'
        status_dic[1] = 'Device is active and running.'

        return self.__current_status, status_dic

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """
        return self.__sample_rate

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """
        if self.__current_status == 1:
            self.log.error('Can`t change the sample rate while the FPGA is running.')
            return self.__sample_rate

        # Round sample rate either to 500MHz or 950MHz since no other values are possible.
        if sample_rate < 725e6:
            self.__sample_rate = 500e6
            bitfile_name = 'pulsegen_8chnl_500MHz_{0}.bit'.format(self._fpga_type.split('_')[1])
        else:
            self.__sample_rate = 950e6
            bitfile_name = 'pulsegen_8chnl_950MHz_{0}.bit'.format(self._fpga_type.split('_')[1])

        bitfile_path = os.path.join(get_main_dir(), 'thirdparty', 'qo_fpga', bitfile_name)

        self.fpga.ConfigureFPGA(bitfile_path)
        self.log.info('FPGA pulse generator configured with {0}'.format(bitfile_path))

        if self.fpga.IsFrontPanel3Supported():
            self._fp3support = True
        else:
            self._fp3support = False
            self.log.warning('FrontPanel3 is not supported. '
                             'Please check if the FPGA is directly connected by USB3.')
        self.__current_status = 0
        return self.__sample_rate

    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if the amplitude value (in Volt peak to peak, i.e. the
                               full amplitude) of a specific channel is desired.
        @param list offset: optional, if the offset value (in Volt) of a specific channel is
                            desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor string
                               (i.e. 'a_ch1') and items being the values for those channels.
                               Amplitude is always denoted in Volt-peak-to-peak and Offset in volts.

        Note: Do not return a saved amplitude and/or offset value but instead retrieve the current
              amplitude and/or offset directly from the device.

        If nothing (or None) is passed then the levels of all channels will be returned. If no
        analog channels are present in the device, return just empty dicts.

        Example of a possible input:
            amplitude = ['a_ch1', 'a_ch4'], offset = None
        to obtain the amplitude of channel 1 and 4 and the offset of all channels
            {'a_ch1': -0.5, 'a_ch4': 2.0} {'a_ch1': 0.0, 'a_ch2': 0.0, 'a_ch3': 1.0, 'a_ch4': 0.0}
        """
        self.log.warning('The FPGA has no analog channels.')
        return dict(), dict()

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

        If nothing is passed then the command will return the current amplitudes/offsets.

        Note: After setting the amplitude and/or offset values of the device, use the actual set
              return values for further processing.
        """
        self.log.warning('The FPGA has no analog channels.')
        return dict(), dict()

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels.

        @param list low: optional, if the low value (in Volt) of a specific channel is desired.
        @param list high: optional, if the high value (in Volt) of a specific channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor strings
                               (i.e. 'd_ch1', 'd_ch2') and items being the values for those
                               channels. Both low and high value of a channel is denoted in volts.

        Note: Do not return a saved low and/or high value but instead retrieve
              the current low and/or high value directly from the device.

        If nothing (or None) is passed then the levels of all channels are being returned.
        If no digital channels are present, return just an empty dict.

        Example of a possible input:
            low = ['d_ch1', 'd_ch4']
        to obtain the low voltage values of digital channel 1 an 4. A possible answer might be
            {'d_ch1': -0.5, 'd_ch4': 2.0} {'d_ch1': 1.0, 'd_ch2': 1.0, 'd_ch3': 1.0, 'd_ch4': 4.0}
        Since no high request was performed, the high values for ALL channels are returned (here 4).
        """
        if low:
            low_dict = {chnl: 0.0 for chnl in low}
        else:
            low_dict = {'d_ch{0:d}'.format(chnl + 1): 0.0 for chnl in range(8)}

        if high:
            high_dict = {chnl: 3.3 for chnl in high}
        else:
            high_dict = {'d_ch{0:d}'.format(chnl + 1): 3.3 for chnl in range(8)}

        return low_dict, high_dict

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
        self.log.warning('FPGA pulse generator logic level cannot be adjusted!')
        return self.get_digital_level()

    def get_active_channels(self,  ch=None):
        """ Get the active channels of the pulse generator hardware.

        @param list ch: optional, if specific analog or digital channels are needed to be asked
                        without obtaining all the channels.

        @return dict:  where keys denoting the channel string and items boolean expressions whether
                       channel are active or not.

        Example for an possible input (order is not important):
            ch = ['a_ch2', 'd_ch2', 'a_ch1', 'd_ch5', 'd_ch1']
        then the output might look like
            {'a_ch2': True, 'd_ch2': False, 'a_ch1': False, 'd_ch5': True, 'd_ch1': False}

        If no parameter (or None) is passed to this method all channel states will be returned.
        """
        if ch:
            d_ch_dict = {chnl: True for chnl in ch}
        else:
            d_ch_dict = {'d_ch1': True,
                         'd_ch2': True,
                         'd_ch3': True,
                         'd_ch4': True,
                         'd_ch5': True,
                         'd_ch6': True,
                         'd_ch7': True,
                         'd_ch8': True}
        return d_ch_dict

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
        self.log.warning('The channels of the FPGA are always active.')
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
        if self.__current_status != 0:
            self.log.error('FPGA is not idle, so the waveform can`t be written at this time.')
            return -1, list()

        if analog_samples:
            self.log.error('FPGA pulse generator is purely digital and does not support waveform '
                           'generation with analog samples.')
            return -1, list()
        if not digital_samples:
            if total_number_of_samples > 0:
                self.log.warning('No samples handed over for waveform generation.')
                return -1, list()
            else:
                self.__current_waveform = bytearray(np.zeros(32))
                self.__samples_written = 32
                self.__current_waveform_name = ''
                return 0, list()

        # Initialize waveform array if this is the first chunk to write
        # Also append zero-timebins to waveform if the length is no integer multiple of 32
        if is_first_chunk:
            self.__samples_written = 0
            self.__current_waveform_name = name
            if total_number_of_samples % 32 != 0:
                number_of_zeros = 32 - (total_number_of_samples % 32)
                self.__current_waveform = np.zeros(total_number_of_samples + number_of_zeros,
                                                   dtype='uint8')
                self.log.warning('FPGA pulse sequence length is no integer multiple of 32 samples.'
                                 '\nAppending {0:d} zero-samples to the sequence.'
                                 ''.format(number_of_zeros))
            else:
                self.__current_waveform = np.zeros(total_number_of_samples, dtype='uint8')

        # Determine which part of the waveform array should be written
        chunk_length = len(digital_samples[list(digital_samples)[0]])
        write_end_index = self.__samples_written + chunk_length

        # Encode samples for each channel in bit mask and create waveform array
        for chnl, samples in digital_samples.items():
            # get channel index in range 0..7
            chnl_ind = int(chnl.rsplit('ch', 1)[1]) - 1
            # Represent bool values as np.uint8
            uint8_samples = samples.view('uint8')
            # left shift 0/1 values to bit position corresponding to channel index
            np.left_shift(uint8_samples, chnl_ind, out=uint8_samples)
            # Add samples to waveform array
            np.add(self.__current_waveform[self.__samples_written:write_end_index],
                   uint8_samples,
                   out=self.__current_waveform[self.__samples_written:write_end_index])

        # Convert numpy array to bytearray
        self.__current_waveform = bytearray(self.__current_waveform.tobytes())

        # increment the current write index
        self.__samples_written += chunk_length
        return chunk_length, [self.__current_waveform_name]

    def write_sequence(self, name, sequence_parameters):
        """
        Write a new sequence on the device memory.

        @param str name: the name of the waveform to be created/append to
        @param dict sequence_parameters: dictionary containing the parameters for a sequence

        @return: int, number of sequence steps written (-1 indicates failed process)
        """
        self.log.warning('FPGA digital pulse generator has no sequencing capabilities.\n'
                         'write_sequence call ignored.')
        return -1

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        waveform_names = list()
        if self.__current_waveform_name != '' and self.__current_waveform_name is not None:
            waveform_names = [self.__current_waveform_name]
        return waveform_names

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        return list()

    def delete_waveform(self, waveform_name):
        """ Delete the waveform with name "waveform_name" from the device memory.

        @param str waveform_name: The name of the waveform to be deleted
                                  Optionally a list of waveform names can be passed.

        @return list: a list of deleted waveform names.
        """
        return list()

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory.

        @param str sequence_name: The name of the sequence to be deleted
                                  Optionally a list of sequence names can be passed.

        @return list: a list of deleted sequence names.
        """
        return list()

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

        Note: After setting the interleave of the device, retrieve the
              interleave again and use that information for further processing.

        Unused for pulse generator hardware other than an AWG.
        """
        if state:
            self.log.error('No interleave functionality available in FPGA pulser.\n'
                           'Interleave state is always False.')
        return False

    def write(self, command):
        """ Sends a command string to the device.

        @param str command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        if not isinstance(command, int):
            return -1
        self.fpga.SetWireInValue(0x00, command)
        self.fpga.UpdateWireIns()
        return 0

    def query(self, question=None):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param str question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        self.fpga.UpdateWireOuts()
        return self.fpga.GetWireOutValue(0x20)

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.write(0x04)
        self.write(0x00)
        return 0

    def _connect_fpga(self):
        # connect to FPGA by serial number
        self.fpga.OpenBySerial(self._fpga_serial)
        # upload configuration bitfile to FPGA
        self.set_sample_rate(self.__sample_rate)

        # Check connection
        if not self.fpga.IsFrontPanelEnabled():
            self.current_status = -1
            self.log.error('ERROR: FrontPanel is not enabled in FPGA pulse generator!')
            self.__current_status = -1
            return self.__current_status
        else:
            self.current_status = 0
            self.log.info('FPGA pulse generator connected')
            return self.__current_status

    def _disconnect_fpga(self):
        """
        stop FPGA and disconnect
        """
        # set FPGA in reset state
        self.write(0x04)
        self.__current_status = -1
        del self.fpga
        return self.__current_status
