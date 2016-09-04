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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from core.base import Base
from interface.pulser_interface import PulserInterface
import thirdparty.opal_kelly.ok64 as ok
import time
import os
from collections import OrderedDict


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

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']

            if not os.path.exists(self.pulsed_file_dir):

                homedir = self.get_home_dir()
                self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
                self.log.warning('The directory defined in parameter '
                            '"pulsed_file_dir" in the config for '
                            'SequenceGeneratorLogic class does not exist!\n'
                            'The default home directory\n{0}\n will be taken '
                            'instead.'.format(self.pulsed_file_dir))
        else:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
            self.log.warning('No parameter "pulsed_file_dir" was specified '
                    'in the config for SequenceGeneratorLogic as directory '
                    'for the pulsed files!\nThe default home directory\n{0}\n'
                    'will be taken instead.'.format(self.pulsed_file_dir))

        if 'fpga_serial' in config.keys():
            self.fpga_serial = config['fpga_serial']
        else:
            self.fpga_serial = ''
            self.log.error('No parameter "fpga_serial" was specified in the '
                        'config for FPGA pulse generator.')

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')

        self.current_status = -1
        self.sample_rate = 950e6
        self.current_loaded_asset = None
        # self.lock = Mutex()
        self.current_loaded_asset = None

    def on_activate(self, e):
        self.current_loaded_asset = None
        self.fpga = ok.FrontPanel()
        self._connect_fpga()
        self.sample_rate = self.get_sample_rate()

    def on_deactivate(self, e):
        self._disconnect_fpga()

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

        # The file formats are hardware specific. The sequence_generator_logic will need this
        # information to choose the proper output format for waveform and sequence files.
        constraints['waveform_format'] = 'fpga'
        constraints['sequence_format'] = None

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
            self.log.warning('"upload_asset" called with asset_name = None.')
            return 0

        # check if asset exists
        saved_assets = self.get_saved_asset_names()
        if asset_name not in saved_assets:
            self.log.error('No asset with name "{0}" found for FPGA pulser.\n'
                    '"upload_asset" call ignored.'.format(asset_name))
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
                self.log.info('Upload of the asset "{0}" to FPGA was '
                        'successful.\nUpload attempts needed: {1}'.format(
                            asset_name, loop_count))
                break
        self.current_loaded_asset = asset_name
        return 0

    def load_asset(self, asset_name, load_dict=None):
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
        if load_dict is None:
            load_dict = {}
        self.log.info('FPGA pulser has no own storage capability.\n'
                    '"load_asset" call ignored.')
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
            bitfile_path = os.path.join(self.get_main_dir(), 'thirdparty', 'qo_fpga', 'pulsegen_8chnl_950MHz.bit')
        elif sample_rate == 500e6:
            bitfile_path = os.path.join(self.get_main_dir(), 'thirdparty', 'qo_fpga', 'pulsegen_8chnl_500MHz.bit')
        else:
            self.log.error('Setting "{0}" as sample rate for FPGA pulse '
                    'generator is not allowed. Use 950e6 or 500e6 instead.')
            return -1

        self.sample_rate = sample_rate
        self.fpga.ConfigureFPGA(bitfile_path)
        self.log.info('FPGA pulse generator configured with {}'.format(
            bitfile_path))
        return 0

    def get_analog_level(self, amplitude=None, offset=None):
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
        if amplitude is None:
            amplitude = []
        if offset is None:
            offset = []
        return {}, {}

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
        """
        if amplitude is None:
            amplitude = {}
        if offset is None:
            offset = {}

        return {}, {}

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
        if low is None:
            low = []
        if high is None:
            high = []
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
            low = {}
        if high is None:
            high = {}
        self.log.warning('FPGA pulse generator logic level cannot be '
                'adjusted!')
        return 0

    def get_active_channels(self,  ch=None):
        if ch is None:
            ch = {}
        d_ch_dict = {}
        if len(ch) < 1:
            for chnr in range(8):
                d_ch_dict['d_ch{}'.format(chnr+1)] = True
        else:
            for channel in ch:
                d_ch_dict[channel] = True
        return d_ch_dict

    def set_active_channels(self, ch=None):
        if ch is None:
            ch = {}
        d_ch_dict = {
            'd_ch1': True,
            'd_ch2': True,
            'd_ch3': True,
            'd_ch4': True,
            'd_ch5': True,
            'd_ch6': True,
            'd_ch7': True,
            'd_ch8': True}
        return d_ch_dict

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

    def _connect_fpga(self):
        # connect to FPGA by serial number
        self.fpga.OpenBySerial(self.fpga_serial)
        # upload configuration bitfile to FPGA
        self.set_sample_rate(self.sample_rate)

        # Check connection
        if not self.fpga.IsFrontPanelEnabled():
            self.current_status = -1
            self.log.error('ERROR: FrontPanel is not enabled in FPGA pulse '
                    'generator!')
            return -1
        else:
            self.current_status = 0
            self.log.info('FPGA pulse generator connected')
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
