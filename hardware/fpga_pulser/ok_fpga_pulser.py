# -*- coding: utf-8 -*-
"""
Use OK FPGA as a digital pulse sequence generator.

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

Copyright (C) 2015 Nikolas Tomek nikolas.tomek@uni-ulm.de
Copyright (C) 2015 Lachlan J. Rogers lachlan.j.rogers@quantum.diamonds
"""

from core.base import Base
from core.util.mutex import Mutex
from interface.pulser_interface import PulserInterface
import thirdparty.opal_kelly.ok64 as ok
import time
import os
import numpy as np
from collections import OrderedDict
from fnmatch import fnmatch


class OkFpgaPulser(Base, PulserInterface):
    """Methods to control Pulse Generator running on OK FPGA.

    Chan   PIN
    ----------
    Ch1    A3
    Ch2    C5
    Ch3    D6
    """
    _modclass = 'pulserinterface'
    _modtype = 'hardware'
    _out = {'pulser': 'PulserInterface'}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config,  c_dict)

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']

            if not os.path.exists(self.pulsed_file_dir):

                homedir = self.get_home_dir()
                self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
                self.logMsg('The directory defined in parameter '
                            '"pulsed_file_dir" in the config for '
                            'SequenceGeneratorLogic class does not exist!\n'
                            'The default home directory\n{0}\n will be taken '
                            'instead.'.format(self.pulsed_file_dir),
                            msgType='warning')
        else:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
            self.logMsg('No parameter "pulsed_file_dir" was specified in the '
                        'config for SequenceGeneratorLogic as directory for '
                        'the pulsed files!\nThe default home directory\n{0}\n'
                        'will be taken instead.'.format(self.pulsed_file_dir),
                        msgType='warning')

        if 'fpga_serial' in config.keys():
            self.fpga_serial = config['fpga_serial']
        else:
            self.fpga_serial = ''
            self.logMsg('No parameter "fpga_serial" was specified in the '
                        'config for FPGA pulse generator.', msgType='error')

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')

        self.current_status = -1
        self.sample_rate = 950e6
        self.current_loaded_asset = None
        # self.lock = Mutex()
        self.current_loaded_asset = None

    def activation(self, e):
        self.current_loaded_asset = None
        self.fpga = ok.FrontPanel()
        self._connect_fpga()
        self.sample_rate = self.get_sample_rate()

    def deactivation(self, e):
        self._disconnect_fpga()
        pass

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Pulsing device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints (e.g. sample_rate, amplitude,
        total_length_bins, channel_config, ...) related to the pulse generator
        hardware to the caller.
        The keys of the returned dictionary are the str name for the constraints
        (which are set in this method). No other keys should be invented. If you
        are not sure about the meaning, look in other hardware files to get an
        impression. If still additional constraints are needed, then they have
        to be add to all files containing this interface.
        The items of the keys are again dictionaries which have the generic
        dictionary form:
            {'min': <value>,
             'max': <value>,
             'step': <value>,
             'unit': '<value>'}

        Only the keys 'activation_config' and differs, since it contain the
        channel configuration/activation information.

        If the constraints cannot be set in the pulsing hardware (because it
        might e.g. has no sequence mode) then write just zero to each generic
        dict. Note that there is a difference between float input (0.0) and
        integer input (0).
        ALL THE PRESENT KEYS OF THE CONSTRAINTS DICT MUST BE ASSIGNED!
        """
        constraints = dict()

        # if interleave option is available, then sample rate constraints must
        # be assigned to the output of a function called
        # _get_sample_rate_constraints()
        # which outputs the shown dictionary with the correct values depending
        # on the present mode. The the GUI will have to check again the
        # limitations if interleave was selected.
        constraints['sample_rate'] = {'min': 500e6, 'max': 950e6,
                                      'step': 450e6, 'unit': 'Samples/s'}
        # the stepsize will be determined by the DAC in combination with the
        # maximal output amplitude (in Vpp):
        constraints['a_ch_amplitude'] = {'min': 0, 'max': 0,
                                         'step': 0, 'unit': 'Vpp'}

        constraints['a_ch_offset'] = {'min': 0, 'max': 0,
                                      'step': 0, 'unit': 'V'}

        constraints['d_ch_low'] = {'min': 0, 'max': 0,
                                   'step': 0, 'unit': 'V'}

        constraints['d_ch_high'] = {'min': 3.3, 'max': 3.3,
                                    'step': 0, 'unit': 'V'}

        constraints['sampled_file_length'] = {'min': 256, 'max': 134217728,
                                              'step': 1, 'unit': 'Samples'}

        constraints['digital_bin_num'] = {'min': 0, 'max': 0.0,
                                          'step': 0, 'unit': '#'}

        constraints['waveform_num'] = {'min': 1, 'max': 1,
                                       'step': 0, 'unit': '#'}

        constraints['sequence_num'] = {'min': 0, 'max': 0,
                                       'step': 0, 'unit': '#'}

        constraints['subsequence_num'] = {'min': 0, 'max': 0,
                                          'step': 0, 'unit': '#'}

        # If sequencer mode is enable than sequence_param should be not just an
        # empty dictionary. Insert here in the same fashion like above the
        # parameters, which the device is needing for a creating sequences:
        sequence_param = OrderedDict()
        constraints['sequence_param'] = sequence_param

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names
        # for the different configurations can be customary chosen.

        activation_config = OrderedDict()
        activation_config['all'] = ['d_ch1', 'd_ch2', 'd_ch3', 'd_ch4',
                                    'd_ch5', 'd_ch6', 'd_ch7', 'd_ch8']
        constraints['activation_config'] = activation_config

        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error)
        """
        # start the pulse sequence
        self.fpga.SetWireInValue(0x00, 0x01)
        self.fpga.UpdateWireIns()
        return 0

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error)
        """
        # stop the pulse sequence
        self.fpga.SetWireInValue(0x00, 0x00)
        self.fpga.UpdateWireIns()
        return 0

    def upload_asset(self, asset_name=None):
        """ Upload an already hardware conform file to the device.
            Does NOT load it into channels.

        @param name: string, name of the ensemble/seqeunce to be uploaded

        @return int: error code (0:OK, -1:error)
        """
        # ignore if no asset_name is given
        if asset_name is None:
            self.logMsg('"upload_asset" called with asset_name = None.', msgType='warning')
            return 0

        # check if asset exists
        saved_assets = self.get_saved_asset_names()
        if asset_name not in saved_assets:
            self.logMsg('No asset with name "{0}" found for FPGA pulser.\n'
                    '"upload_asset" call ignored.'.format(asset_name), msgType='error')
            return -1

        # get samples from file
        filepath = os.path.join(self.host_waveform_directory, asset_name+'.fpga')
        with open(filepath, 'rb') as asset_file:
            samples = bytearray(asset_file.read())

        # calculate size of the two bytearrays to be transmitted
        # the biggest part is tranfered in 1024 byte blocks and the rest is transfered in 32 byte blocks
        big_bytesize = (len(samples) // 1024) * 1024
        small_bytesize = len(samples) - big_bytesize

        # try repeatedly to upload the samples to the FPGA RAM
        # stop if the upload was successful
        loop_count = 0
        while True:
            loop_count += 1
            # reset FPGA
            self.fpga.SetWireInValue(0x00,0x04)
            self.fpga.UpdateWireIns()
            self.fpga.SetWireInValue(0x00,0x00)
            self.fpga.UpdateWireIns()
            # upload sequence
            if big_bytesize != 0:
                #enable sequence write mode in FPGA
                self.fpga.SetWireInValue(0x00, (255 << 24)+2)
                self.fpga.UpdateWireIns()
                #write to FPGA DDR2-RAM
                self.fpga.WriteToBlockPipeIn(0x80, 1024, samples[0:big_bytesize])
            if small_bytesize != 0:
                #enable sequence write mode in FPGA
                self.fpga.SetWireInValue(0x00, (8 << 24)+2)
                self.fpga.UpdateWireIns()
                #write to FPGA DDR2-RAM
                self.fpga.WriteToBlockPipeIn(0x80, 32, samples[big_bytesize:big_bytesize+small_bytesize])

            # check if upload was successful
            self.fpga.SetWireInValue(0x00, 0x00)
            self.fpga.UpdateWireIns()
            # start the pulse sequence
            self.fpga.SetWireInValue(0x00, 0x01)
            self.fpga.UpdateWireIns()
            # wait for 600ms
            time.sleep(0.6)
            # get status flags from FPGA
            self.fpga.UpdateWireOuts()
            flags = self.fpga.GetWireOutValue(0x20)
            self.fpga.SetWireInValue(0x00, 0x00)
            self.fpga.UpdateWireIns()
            # check if the memory readout works.
            if flags == 0:
                self.logMsg('Upload of the asset "{0}" to FPGA was successful.\n'
                            'Upload attempts needed: {1}'.format(asset_name, loop_count), msgType='status')
                break
        self.current_loaded_asset = asset_name
        return 0

    def load_asset(self, asset_name, load_dict={}):
        """ Loads a sequence or waveform to the specified channel of the pulsing
            device.

        @param str asset_name: The name of the asset to be loaded

        @param dict load_dict:  a dictionary with keys being one of the
                                available channel numbers and items being the
                                name of the already sampled
                                waveform/sequence files.
                                Examples:   {1: rabi_Ch1, 2: rabi_Ch2}
                                            {1: rabi_Ch2, 2: rabi_Ch1}
                                This parameter is optional. If none is given
                                then the channel association is invoked from
                                the sequence generation,
                                i.e. the filename appendix (_Ch1, _Ch2 etc.)

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        self.logMsg('FPGA pulser has no own storage capability.\n'
                    '"load_asset" call ignored.', msgType='status')
        return 0

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without storage capability
        (PulseBlaster, FPGA).
        """
        return 0

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): tuple with an interger value of the current status
                             and a corresponding dictionary containing status
                             description for all the possible status variables
                             of the pulse generator hardware.
        """
        status_dic = dict()
        status_dic[-1] = 'Failed Request or Failed Communication with device.'
        status_dic[0] = 'Device has stopped, but can receive commands.'
        status_dic[1] = 'Device is active and running.'

        return self.current_status, status_dic

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate in a class variable, but instead
        retrieve the current sample rate directly from the device.
        """
        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device.

        Note: After setting the sampling rate of the device, retrieve it again
              for obtaining the actual set value and use that information for
              further processing.
        """
        if sample_rate == 950e6:
            bitfile_path = os.path.join(self.get_main_dir(), 'hardware', 'fpga_pulser', 'pulsegen_8chnl_950MHz.bit')
        elif sample_rate == 500e6:
            bitfile_path = os.path.join(self.get_main_dir(), 'hardware', 'fpga_pulser', 'pulsegen_8chnl_500MHz.bit')
        else:
            self.logMsg('Setting "{0}" as sample rate for FPGA pulse generator '
                    'is not allowed. Use 950e6 or 500e6 instead.', msgType='error')
            return -1

        self.sample_rate = sample_rate
        self.fpga.ConfigureFPGA(bitfile_path)
        self.logMsg('FPGA pulse generator configured with {}'.format(bitfile_path), msgType='status')
        return 0

    def get_analog_level(self, amplitude=[], offset=[]):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if a specific amplitude value (in Volt
                               peak to peak, i.e. the full amplitude) of a
                               channel is desired.
        @param list offset: optional, if a specific high value (in Volt) of a
                            channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel
                               number and items being the values for those
                               channels. Amplitude is always denoted in
                               Volt-peak-to-peak and Offset in (absolute)
                               Voltage.
        """
        return {}, {}

    def set_analog_level(self, amplitude={}, offset={}):
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
        """

        return {}, {}

    def get_digital_level(self, low=[], high=[]):
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
            low = [1,4]
        to obtain the low voltage values of digital channel 1 an 4. A possible
        answer might be
            {1: -0.5, 4: 2.0} {}
        since no high request was performed.

        The major difference to analog signals is that digital signals are
        either ON or OFF, whereas analog channels have a varying amplitude
        range. In contrast to analog output levels, digital output levels are
        defined by a voltage, which corresponds to the ON status and a voltage
        which corresponds to the OFF status (both denoted in (absolute) voltage)

        In general there is no bijective correspondence between
        (amplitude, offset) and (value high, value low)!
        """
        low_dict = {}
        high_dict = {}
        if low is [] and high is []:
            for channel in range(8):
                low_dict[channel] = 0.0
                high_dict[channel] = 3.3
        else:
            for channel in low:
                low_dict[channel] = 0.0
            for channel in high:
                high_dict[channel] = 3.3
        return low_dict, high_dict

    def set_digital_level(self, low={}, high={}):
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
        self.logMsg('FPGA pulse generator logic level cant be adjusted!', msgType='warning')
        return 0

    def get_active_channels(self, a_ch=[], d_ch=[]):
        """ Get the active channels of the pulse generator hardware.

        @param list a_ch: optional, if specific analog channels are needed to be
                          asked without obtaining all the channels.
        @param list d_ch: optional, if specific digital channels are needed to
                          be asked without obtaining all the channels.

        @return (dict, dict): tuple of two dicts, where keys denoting the
                              channel number and items boolean expressions
                              whether channel are active or not. First dict
                              contains the analog settings, second dict the
                              digital settings. If either digital or analog are
                              not present, return an empty dict.

        Example for an possible input:
            a_ch=[2, 1] d_ch=[2,1,5]
        then the output might look like
            {1: True, 2: False} {1: False, 2: True, 5: False}

        If no parameters are passed to this method all channels will be asked
        for their setting.
        """
        a_ch_dict = {}
        d_ch_dict = {}
        if d_ch is []:
            for channel in range(8):
                d_ch_dict[channel] = True
        else:
            for channel in d_ch:
                d_ch_dict[channel] = True
        return a_ch_dict, d_ch_dict

    def set_active_channels(self, a_ch={}, d_ch={}):
        """ Set the active channels for the pulse generator hardware.

        @param dict a_ch: dictionary with keys being the analog channel numbers
                          and items being boolean values.
        @param dict d_ch: dictionary with keys being the digital channel numbers
                          and items being boolean values.

        @return (dict, dict): tuple of two dicts with the actual set values for
                active channels for analog (a_ch) and digital (d_ch) values.

        If nothing is passed then the command will return two empty dicts.

        Note: After setting the active channels of the device, retrieve them
              again for obtaining the actual set value(s) and use that
              information for further processing.

        Example for possible input:
            a_ch={2: True}, d_ch={1:False, 3:True, 4:True}
        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1.

        The hardware itself has to handle, whether separate channel activation
        is possible.
        """
        d_ch_dict = {1: True, 2: True, 3: True, 4: True, 5: True, 6: True, 7: True, 8: True}
        return {}, d_ch_dict

    def get_loaded_asset(self):
        """ Retrieve the currently loaded asset name of the device.

        @return str: Name of the current asset, that can be either a filename
                     a waveform, a sequence ect.
        """
        return self.current_loaded_asset

    def get_uploaded_asset_names(self):
        """ Retrieve the names of all uploaded assets on the device.

        @return list: List of all uploaded asset name strings in the current
                      device directory. This is no list of the file names.

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        names = []
        return names

    def get_loaded_asset(self):
        """ Retrieve the currently loaded asset name of the device.

        @return str: Name of the current asset, that can be either a filename
                     a waveform, a sequence ect.
        """
        return self.current_loaded_asset

    def get_saved_asset_names(self):
        """ Retrieve the names of all sampled and saved assets on the host PC.
        This is no list of the file names.

        @return list: List of all saved asset name strings in the current
                      directory of the host PC.
        """
        file_list = self._get_filenames_on_host()

        saved_assets = []
        for filename in file_list:
            if filename.endswith('.fpga'):
                asset_name = filename.rsplit('.', 1)[0]
                if asset_name not in saved_assets:
                    saved_assets.append(asset_name)

        return saved_assets

    def delete_asset(self, asset_name):
        """ Delete all files associated with an asset with the passed asset_name from the device memory.

        @param str asset_name: The name of the asset to be deleted
                               Optionally a list of asset names can be passed.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        return 0

    def set_asset_dir_on_device(self, dir_path):
        """ Change the directory where the assets are stored on the device.

        @param str dir_path: The target directory

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without changeable file structure
        (PulseBlaster, FPGA).
        """
        return 0

    def get_asset_dir_on_device(self):
        """ Ask for the directory where the hardware conform files are stored on
            the device.

        @return str: The current file directory

        Unused for digital pulse generators without changeable file structure
        (PulseBlaster, FPGA).
        """
        return ''

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
        return False

    def tell(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def ask(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.
a
        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        return ''

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.fpga.SetWireInValue(0x00, 0x04)
        self.fpga.UpdateWireIns()
        self.fpga.SetWireInValue(0x00, 0x00)
        self.fpga.UpdateWireIns()
        return 0

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for y   es, False for no.
        """
        return False

    def write_samples_to_file(self, name, analog_samples,
                             digital_samples, total_number_of_samples,
                             is_first_chunk, is_last_chunk):
        """
        Appends a sampled chunk of a whole waveform to a file. Create the file
        if it is the first chunk.
        If both flags (is_first_chunk, is_last_chunk) are set to TRUE it means
        that the whole ensemble is written as a whole in one big chunk.

        @param name: string, represents the name of the sampled ensemble
        @param analog_samples: float32 numpy ndarray, contains the
                                       samples for the analog channels that
                                       are to be written by this function call.
        @param digital_samples: bool numpy ndarray, contains the samples
                                      for the digital channels that
                                      are to be written by this function call.
        @param total_number_of_samples: int, The total number of samples in the entire waveform.
                                        Has to be known it advance.
        @param is_first_chunk: bool, indicates if the current chunk is the
                               first write to this file.
        @param is_last_chunk: bool, indicates if the current chunk is the last
                              write to this file.

        @return list: the list contains the string names of the created files for the passed
                      presampled arrays
        """

        # record the name of the created files
        created_files = []

        chunk_length_bins = digital_samples.shape[1]
        channel_number = digital_samples.shape[0]
        if channel_number != 8:
            self.logMsg('FPGA pulse generator needs 8 digital channels. {0} is not allowed!'.format(channel_number), msgType='error')
            return -1

        # encode channels into FPGA samples (bytes)
        # check if the sequence length is an integer multiple of 32 bins
        if is_last_chunk and (total_number_of_samples % 32 != 0):
            # calculate number of zero timeslots to append
            number_of_zeros = 32 - (total_number_of_samples % 32)
            encoded_samples = np.zeros(chunk_length_bins+number_of_zeros, dtype='uint8')
            self.logMsg('FPGA pulse sequence length is no integer multiple of 32 samples. '
                        'Appending {0} zero-samples to the sequence.'.format(number_of_zeros), msgType='warning')
        else:
            encoded_samples = np.zeros(chunk_length_bins, dtype='uint8')

        for channel in range(channel_number):
            encoded_samples[:chunk_length_bins] += (channel+1)*np.uint8(digital_samples[channel])

        del digital_samples # no longer needed

        # append samples to file

        filename = name + '.fpga'
        created_files.append(filename)

        filepath = os.path.join(self.host_waveform_directory, filename)
        with open(filepath, 'ab') as fpgafile:
            fpgafile.write(encoded_samples)

        return created_files

    def write_seq_to_file(self, name, sequence_param):
        """ Write a sequence to file.

        @param str name: name of the sequence to be created
        @param list sequence_param: a list of dict, which contains all the information, which
                                    parameters are to be taken to create a sequence. The dict will
                                    have at least the entry
                                        {'ensemble': [<list_of_sampled_ensemble_name>] }
                                    All other parameters, which can be used in the sequence are
                                    determined in the get_constraints method in the category
                                    'sequence_param'.

        In order to write sequence files a completely new method with respect to
        write_samples_to_file is needed.
        """

        self.logMsg('The FPGA pulsing device does not have a sequence capability!\n'
                    'Method call will be ignored.', msgType='warning')
        return

    def _connect_fpga(self):
        # connect to FPGA by serial number
        self.fpga.OpenBySerial(self.fpga_serial)
        # upload configuration bitfile to FPGA
        self.set_sample_rate(self.sample_rate)

        # Check connection
        if not self.fpga.IsFrontPanelEnabled():
            self.current_status = -1
            self.logMsg('ERROR: FrontPanel is not enabled in FPGA pulse generator!', msgType='error')
            return -1
        else:
            self.current_status = 0
            self.logMsg('FPGA pulse generator connected', msgType='status')
            return 0

    def _disconnect_fpga(self):
        """
        stop FPGA and disconnect
        """
        # set FPGA in reset state
        self.fpga.SetWireInValue(0x00,0x04)
        self.fpga.UpdateWireIns()
        self.current_status = -1
        del self.fpga
        return 0

    def _get_dir_for_name(self, name):
        """ Get the path to the pulsed sub-directory 'name'.

        @param name: string, name of the folder
        @return: string, absolute path to the directory with folder 'name'.
        """

        path = os.path.join(self.pulsed_file_dir, name)
        if not os.path.exists(path):
            os.makedirs(os.path.abspath(path))
        return os.path.abspath(path)

    def _get_filenames_on_host(self):
        """ Get the full filenames of all assets saved on the host PC.

        @return: list, The full filenames of all assets saved on the host PC.
        """
        filename_list = [f for f in os.listdir(self.host_waveform_directory) if f.endswith('.fpga')]
        return filename_list
