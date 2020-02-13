# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the Keysight M8195A PXIe AWG device.

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


import visa
import os
import time
import numpy as np
from fnmatch import fnmatch
from collections import OrderedDict

from core.module import Base
from core.configoption import ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints


class AWGM8195A(Base, PulserInterface):
    """ A hardware module for the Keysight M8195A series for generating
        waveforms and sequences thereof.

    Example config for copy-paste:

        myawg:
            module.Class: 'awg.keysight_M8195A.AWGM8195A'
            awg_visa_address: 'TCPIP0::localhost::hislip0::INSTR'
            awg_timeout: 20
            pulsed_file_dir: 'C:\\Software\\pulsed_files'
            awg_mode: 'MARK'
            sample_rate_div: 1

    """

    _modclass = 'awgm8195a'
    _modtype = 'hardware'

    # config options
    _visa_address = ConfigOption(name='awg_visa_address', default='TCPIP0::localhost::hislip0::INSTR', missing='warn')
    _awg_timeout = ConfigOption(name='awg_timeout', default=20, missing='warn')
    _pulsed_file_dir = ConfigOption(name='pulsed_file_dir', missing='warn')
    _awg_mode = ConfigOption(name='awg_mode', default='MARK', missing='warn')
    _sample_rate_div = ConfigOption(name='sample_rate_div', default=1, missing='warn')
    # debug = []


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._BRAND = ''
        self._MODEL = ''
        self._SERIALNUMBER = ''
        self._FIRMWARE_VERSION = ''

        self._sequence_mode = False
        self.current_loaded_asset = ''
        self.active_channel = dict()

    def on_activate(self):
        """Initialisation performed during activation of the module.
        """

        use_default_dir = True
        self._rm = visa.ResourceManager()

        if not self._pulsed_file_dir:
            homedir = self.get_home_dir()
            self._pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
            self.log.warning('Either no config parameter "pulsed_file_dir" was '
                             'specified in the config for AWGM8195A class as '
                             'directory for the pulsed files or the directory '
                             'does not exist.\nThe default home directory\n'
                             '{0}\nfor pulsed files will be taken instead.'
                             ''.format(self._pulsed_file_dir))

        # connect to awg using PyVISA
        try:
            self.awg = self._rm.open_resource(self._visa_address)
            # set timeout by default to 30 sec
            self.awg.timeout = self._awg_timeout * 1000
        except:
            self.awg = None
            self.log.error('VISA address "{0}" not found by the pyVISA resource manager.\nCheck '
                           'the connection by using for example "Keysight Connection Expert".'
                           ''.format(self._visa_address))
            return

        if self.awg is not None:
            mess = self.query('*IDN?').split(',')
            self._BRAND = mess[0]
            self._MODEL = mess[1]
            self._SERIALNUMBER = mess[2]
            self._FIRMWARE_VERSION = mess[3]

            self.log.info('Load the device model "{0}" from "{1}" with the '
                          'serial number "{2}" and the firmware version "{3}" '
                          'successfully.'.format(self._MODEL, self._BRAND,
                                                 self._SERIALNUMBER,
                                                 self._FIRMWARE_VERSION))
            self._sequence_mode  = 'SEQ' in self.query('*OPT?').split(',')
        self._init_device()

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

    def _init_device(self):
        """ Run those methods during the initialization process.
        Here configured for CH 1 Waveform and CH3/CH4 Marker
        """

        self.reset()
        self.write(':OUTP:ROSC:SOUR SCLK1') #Chose source for reference clock
        self.write(':OUTP:ROSC:SCD 200') # Set clock divier to 200, so that the ref clock has 10 MHz
        # Sec. 6.21.2 in manual:
        # To prepare your module for arbitrary waveform generation follow these
        # steps:
        # Set Instrument Mode (number of channels), Memory Sample Rate Divider,
        # and memory usage of the channels (Internal/Extended):
        self.write(':INSTrument:DACMode {0}'.format(self._awg_mode))
        # set the sample rate divider:
        self.write(':INST:MEM:EXT:RDIV DIV{0}'.format(self._sample_rate_div))
        self.write(':FUNC:MODE ARB')             # Set mode to arbitrary
        self.write(':TRAC1:MMOD EXT')            # select extended Memory Mode

        # Set the directory:
        self.write(':MMEM:CDIR "{0}"'.format(self._pulsed_file_dir))

        self.sample_rate = self.get_sample_rate()

        # ampl = {'a_ch1': 1.0, 'a_ch2': 1.0, 'a_ch3': 1.0, 'a_ch4': 1.0}
        ampl = {'a_ch1': 1.0}
        d_ampl_low = {'d_ch1': 0.5, 'd_ch2': 0}
        d_ampl_high = {'d_ch1': 1.5, 'd_ch2': 1}          #TODO catch from config/settings

        self.amplitude_list, self.offset_list = self.set_analog_level(amplitude=ampl)
        self.markers_low, self.markers_high = self.set_digital_level(low=d_ampl_low, high=d_ampl_high)
        self.is_output_enabled = self._is_awg_running()
        self.use_sequencer = self.has_sequence_mode()
        self.active_channel = self.get_active_channels()
        self.interleave = self.get_interleave()
        self.current_loaded_asset = ''
        self.current_status = 0

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

        # The compatible file formats are hardware specific.
        constraints.waveform_format = ['bin8']

        if self._MODEL == 'M8195A':
            constraints.sample_rate.min = 53.76e9 / self._sample_rate_div
            constraints.sample_rate.max = 65.0e9 / self._sample_rate_div
            constraints.sample_rate.step = 1.0e7
            constraints.sample_rate.default = 65.00e9 / self._sample_rate_div
        else:
            self.log.error('The current AWG model has no valid sample rate '
                           'constraints')

        # constraints.waveform_length.min = self.__min_waveform_length
        # constraints.waveform_length.max = self.__max_waveform_length
        constraints.waveform_length.step = 256
        constraints.waveform_length.default = 1280

        # constraints.waveform_length.step = 1    # step is 256 but the import function repeats the waveform until
        #                                         # granularity is fullfilled, may lead to memory issues, set to 256 if
        #                                         # longer waveforms have to be uploaded.
        # constraints.waveform_length.default = 1 # min length is 1280 but this is also handled by the import

        constraints.a_ch_amplitude.min = 0.075
        constraints.a_ch_amplitude.max = 1.0  # corresponds to 1Vpp, 50Ohm terminated
        constraints.a_ch_amplitude.step = 0.0002
        constraints.a_ch_amplitude.default = 0.5

        constraints.d_ch_low.min = 0
        constraints.d_ch_low.max = 1
        constraints.d_ch_low.step = 0.0002
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = 0
        constraints.d_ch_high.max = 2
        constraints.d_ch_high.step = 0.0002
        constraints.d_ch_high.default = 1

        # constraints.sampled_file_length.min = 256
        # constraints.sampled_file_length.max = 2_000_000_000
        # constraints.sampled_file_length.step = 256
        # constraints.sampled_file_length.default = 256

        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 16_000_000
        constraints.waveform_num.default = 1
        # The sample memory can be split into a maximum of 16 M waveform segments

        # FIXME: Check the proper number for your device
        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 4000
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65536
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0

        # ToDo: Check how many external triggers are available
        # constraints.trigger_in.min = 0
        # constraints.trigger_in.max = 1
        # constraints.trigger_in.step = 1
        # constraints.trigger_in.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names
        # for the different configurations can be customary chosen.
        activation_config = OrderedDict()
        if self._MODEL == 'M8195A':
            awg_mode = self.query(':INST:DACM?')
            if awg_mode == 'MARK':
                activation_config['all'] = {'a_ch1', 'd_ch1', 'd_ch2'}
            elif awg_mode == 'SING':
                activation_config['all'] = {'a_ch1'}
            elif awg_mode == 'DUAL':
                activation_config['all'] = {'a_ch1', 'a_ch2'}
            elif awg_mode == 'FOUR':
                activation_config['all'] = {'a_ch1', 'a_ch2', 'a_ch3', 'a_ch4'}

        constraints.activation_config = activation_config

        # FIXME: additional constraint really necessary?
        constraints.dac_resolution = {'min': 8, 'max': 8, 'step': 1, 'unit': 'bit'}

        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        self.write(':OUTP1 ON')
        self.write(':OUTP2 ON')
        self.write(':OUTP3 ON')
        self.write(':OUTP4 ON')

        # Sec. 6.4 from manual:
        # In the program it is recommended to send the command for starting
        # data generation (:INIT:IMM) as the last command. This way
        # intermediate stop/restarts (e.g. when changing sample rate or
        # loading a waveform) are avoided and optimum execution performance is
        # achieved.

        # wait until the AWG switched the outputs on
        while not self._is_output_on():
            time.sleep(0.25)

        self.write(':INIT:IMM')
        self.write('*WAI')

        self.current_status = 1
        self.is_output_enabled = True
        return self.current_status

    def pulser_off(self):
        """ Switches the pulsing device off.
        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.write(':ABOR')

        self.write(':OUTP1 OFF')
        self.write(':OUTP2 OFF')
        self.write(':OUTP3 OFF')
        self.write(':OUTP4 OFF')

        # wait until the AWG has actually stopped
        while self._is_awg_running():
            time.sleep(0.25)

        self.current_status = 0
        self.is_output_enabled = False
        return self.current_status

    def load_waveform(self, load_dict):
        """ Loads a waveform to the specified channel of the pulsing device.

        @param dict|list load_dict: a dictionary with keys being one of the available channel
                                    index and values being the name of the already written
                                    waveform to load into the channel.
                                    Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                {1: rabi_ch2, 2: rabi_ch1}
                                    If just a list of waveform names is given, the channel
                                    association will be invoked from the channel
                                    suffix '_ch1', '_ch2' etc.

                                        {1: rabi_ch1, 2: rabi_ch2}
                                    or
                                        {1: rabi_ch2, 2: rabi_ch1}

                                    If just a list of waveform names is given,
                                    the channel association will be invoked from
                                    the channel suffix '_ch1', '_ch2' etc. A
                                    possible configuration can be e.g.

                                        ['rabi_ch1', 'rabi_ch2', 'rabi_ch3']

        @return dict: Dictionary containing the actually loaded waveforms per
                      channel.

        For devices that have a workspace (i.e. AWG) this will load the waveform
        from the device workspace into the channel. For a device without mass
        memory, this will make the waveform/pattern that has been previously
        written with self.write_waveform ready to play.

        Please note that the channel index used here is not to be confused with the number suffix
        in the generic channel descriptors (i.e. 'd_ch1', 'a_ch1'). The channel index used here is
        highly hardware specific and corresponds to a collection of digital and analog channels
        being associated to a SINGLE wavfeorm asset.
        """

        if isinstance(load_dict, list):
            new_dict = dict()
            for waveform in load_dict:
                channel = int(waveform[-6])
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
                           'One or more channels to set are not active.\n'
                           'channels_to_set are: ', channels_to_set, 'and\n'
                           'analog_channels are: ', analog_channels)
            return self.get_loaded_assets()

        # Check if all waveforms to load are present on device memory
        if not set(load_dict.values()).issubset(self.get_waveform_names()):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more waveforms to load are missing on device memory.')
            return self.get_loaded_assets()

        if load_dict == {}:
            self.log.warning('No file and channel provided for load!\n'
                             'Correct that!\nCommand will be ignored.')
            return self.get_loaded_assets()

        self.clear_all()
        path = self._pulsed_file_dir
        offset = 0

        for chnl_num, waveform in load_dict.items():
            name = waveform.split('.bin8', 1)[0]
            print('name is', name)
            filepath = os.path.join(path, waveform)
            print('021', self.query(':SYST:ERR?'))
            data = self.query_bin(':MMEM:DATA? "{0}"'.format(filepath))
            print('022', self.query(':SYST:ERR?'))
            if chnl_num == 1 and (self._awg_mode == 'MARK' or self._awg_mode == 'DCM'):
                samples = len(data)//2
            print('samples is', samples)
            segment_id = self.query('TRAC1:DEF:NEW? {0:d}, 5'.format(samples))
            self.write_bin(':TRAC{0}:DATA {1}, {2},'.format(chnl_num, segment_id, offset), data)
            print('023', self.query(':SYST:ERR?'))
            self.write(':TRAC{0}:NAME {1}, "{2}"'.format(chnl_num, segment_id, name))
            print('024', self.query(':SYST:ERR?'))

        return self.get_loaded_assets()

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


        # # set the waveform directory:
        # self.tell(':MMEM:CDIR {0}'.format(r"C:\Users\Name\Documents"))
        #
        # # Get the waveform directory:
        # dir = self.ask(':MMEM:CDIR?')

        path = self._pulsed_file_dir + self.sequence_dir

        # Find all files associated with the specified asset name
        file_list = self._get_filenames_on_device()
        filename = []

        self.clear_all()

        # Be careful which asset_name to specify as the current_loaded_asset
        # because a loaded sequence contains also individual waveforms, which
        # should not be used as the current asset!!

        segment = 1     # the id in the external memory
        form = 'BIN8'   # the file format used
        data_type = 'IONLY'
        marker_flag = 'OFF'
        mem_mode = 'ALEN'   # specify how the samples are allocated in memory

        for file in file_list:

            if file == sequence_name+'_ch1.bin8':
                filepath = os.path.join(path, sequence_name + '_ch1.bin8')
                self.log.info(filepath)
                self.tell(':TRAC1:IMP {0}, "{1}", {2}, {3}, {4}, {5}'
                          ''.format(segment,
                                    filepath,
                                    form,
                                    data_type,
                                    marker_flag,
                                    mem_mode))
                self.current_loaded_asset = sequence_name
                filename.append(file)

            elif file == sequence_name+'_ch2.bin8':
                filepath = os.path.join(path, sequence_name + '_ch2.bin8')
                self.log.info(filepath)
                self.tell(':TRAC2:IMP {0}, "{1}", {2}, {3}, {4}, {5}'
                          ''.format(segment,
                                    filepath,
                                    form,
                                    data_type,
                                    marker_flag,
                                    mem_mode))

                self.current_loaded_asset = sequence_name
                filename.append(file)

            elif file == sequence_name+'_ch3.bin8':
                filepath = os.path.join(path, sequence_name + '_ch3.bin8')
                self.log.info(filepath)
                self.tell(':TRAC3:IMP {0}, "{1}", {2}, {3}, {4}, {5}'
                          ''.format(segment,
                                    filepath,
                                    form,
                                    data_type,
                                    marker_flag,
                                    mem_mode))
                self.current_loaded_asset = sequence_name
                filename.append(file)

            elif file == sequence_name+'_ch4.bin8':
                filepath = os.path.join(path, asset_name + '_ch4.bin8')
                self.log.info(filepath)
                self.tell(':TRAC4:IMP {0}, "{1}", {2}, {3}, {4}, {5}'
                          ''.format(segment,
                                    filepath,
                                    form,
                                    data_type,
                                    marker_flag,
                                    mem_mode))
                self.current_loaded_asset = sequence_name
                filename.append(file)

        return 0

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
        #TODO implement properly

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
            print('001', self.query(':SYST:ERR?'))
            if not self.query(':TRAC:CAT?') == '0,0':
                print('002', self.query(':SYST:ERR?'))
                asset_name = self.query(':TRAC:NAME? 1')
                print('003', self.query(':SYST:ERR?'))
            # # Figure out if a sequence or just a waveform is loaded by splitting after the comma
            # splitted = asset_name.rsplit(',', 1)
            # # If the length is 2 a sequence is loaded and if it is 1 a waveform is loaded
            # asset_name = splitted[0]
            # if len(splitted) > 1:
            #     if current_type is not None and current_type != 'sequence':
            #         self.log.error('Unable to determine loaded assets.')
            #         return dict(), ''
            #     current_type = 'sequence'
            #     asset_name += '_' + splitted[1]
            # else:
            #     if current_type is not None and current_type != 'waveform':
            #         self.log.error('Unable to determine loaded assets.')
            #         return dict(), ''
            #     current_type = 'waveform'
                current_type = 'waveform'
                loaded_assets[chnl_num] = asset_name

        return loaded_assets, current_type

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without storage capability
        (PulseBlaster, FPGA).
        """

        self.write(':TRAC:DEL:ALL')

        return 0

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): inter value of the current status with the
                             corresponding dictionary containing status
                             description for all the possible status variables
                             of the pulse generator hardware
        """

        status_dic = {-1: 'Failed Request or Communication',
                       0: 'Device has stopped, but can receive commands',
                       1: 'Device is active and running'}

        current_status = -1 if self.awg is None else int(self._is_awg_running())
        # All the other status messages should have higher integer values then 1.

        return current_status, status_dic

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead retrieve the current
        sample rate directly from the device.
        """
        self.sample_rate = float(self.query(':FREQ:RAST?')) / self._sample_rate_div
        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """
        sample_rate_GHz = (sample_rate * self._sample_rate_div) / 1e9
        self.write(':FREQ:RAST {0:.4G}GHz\n'.format(sample_rate_GHz))
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)
        time.sleep(0.2)
        return self.get_sample_rate()

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

        amp = dict()
        off = dict()

        chnl_list = self._get_all_analog_channels()

        # get pp amplitudes
        if amplitude is None:
            for ch_num, chnl in enumerate(chnl_list, 1):
                amp[chnl] = float(self.query(':VOLT{0:d}?'.format(ch_num)))
        else:
            for chnl in amplitude:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    amp[chnl] = float(self.query(':VOLT{0:d}?'.format(ch_num)))
                else:
                    self.log.warning('Get analog amplitude from M8195A channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))

        # get voltage offsets
        if offset is None:
            for ch_num, chnl in enumerate(chnl_list):
                off[chnl] = 0.0
        else:
            for chnl in offset:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    off[chnl] = float(self.query(':VOLT{0:d}:OFFS?'.format(ch_num)))
                else:
                    self.log.warning('Get analog offset from M8195A channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))
        return amp, off

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
                                     'analogue voltage for this channel ignored.'.format(ch_num))
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

        if amplitude is not None:
            for chnl, amp in amplitude.items():
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                self.write(':VOLT{0} {1:.4f}'.format(ch_num, amp))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.25)

        if offset is not None:
            for chnl, off in offset.items():
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                self.write(':VOLT{0}:OFFS {1:.4f}'.format(ch_num, off))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.25)
        return self.get_analog_level()


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
            d_ch_number = int(chnl.rsplit('_ch', 1)[1]) + 2
            low_val[chnl] = float(
                self.query(':VOLT{0:d}:LOW?'.format(d_ch_number)))
        # get high marker levels
        for chnl in high:
            if chnl not in digital_channels:
                continue
            d_ch_number = int(chnl.rsplit('_ch', 1)[1]) + 2
            high_val[chnl] = float(
                self.query(':VOLT{0:d}:HIGH?'.format(d_ch_number)))

        return low_val, high_val


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
            low = self.get_digital_level()[0]
        if high is None:
            high = self.get_digital_level()[1]

        #If you want to check the input use the constraints:
        constraints = self.get_constraints()
        digital_channels = self._get_all_digital_channels()

        # Check the constraints for marker high level
        for key in high:
            if high[key] < constraints.d_ch_high.min:
                self.log.warning('Voltages for digital values are too small for high. Setting to minimum value')
                high[key] = constraints.d_ch_high.min
            elif high[key] > constraints.d_ch_high.max:
                self.log.warning('Voltages for digital values are too high for high. Setting to maximum value')
                high[key] = constraints.d_ch_high.max

        # Check the constraints for marker low level
        for key in low:
            if low[key] < constraints.d_ch_low.min:
                self.log.warning('Voltages for digital values are too small for low. Setting to minimum value')
                low[key] = constraints.d_ch_low.min
            elif low[key] > constraints.d_ch_low.max:
                self.log.warning('Voltages for digital values are too high for low. Setting to maximum value')
                low[key] = constraints.d_ch_low.max

        # Check the difference between marker high and low
        for key in high:
            if high[key] - low[key] < 0.125:
                self.log.warning('Voltage difference is too small. Reducing low voltage level.')
                low[key] = high[key] - 0.125
            elif high[key] - low[key] > 1.0:
                self.log.warning('Voltage difference is too large. Increasing low voltage level.')
                low[key] = high[key] - 1.0


        # set high marker levels
        for chnl in low and high:
            if chnl not in digital_channels:
                continue
            d_ch_number = int(chnl.rsplit('_ch', 1)[1]) + 2
            offs =(high[chnl] + low[chnl])/2
            ampl = high[chnl] - low[chnl]
            self.write(':VOLT{0:d}:AMPL {1}'.format(d_ch_number, ampl))
            self.write(':VOLT{0:d}:OFFS {1}'.format(d_ch_number, offs))


        return self.get_digital_level()


    def get_active_channels(self, ch=None, set_ac=False):
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
        # analog_channels = self._get_all_analog_channels()
        #
        # active_ch = dict()
        # for ch_num, a_ch in enumerate(analog_channels, 1):
        #     # check what analog channels are active
        #     active_ch[a_ch] = bool(int(self.query(':OUTP{0}?'.format(ch_num))))
        #
        # # return either all channel information or just the one asked for.
        # if ch is not None:
        #     chnl_to_delete = [chnl for chnl in active_ch if chnl not in ch]
        #     for chnl in chnl_to_delete:
        #         del active_ch[chnl]

        if ch is None:
            ch = []

        active_ch = dict()

        if ch ==[]:

            # because 0 = False and 1 = True
            awg_mode = self.query(':INST:DACM?')
            self.log.debug('awg mode is {0}'.format(awg_mode))
            if awg_mode == 'MARK':
                active_ch['a_ch1'] = bool(int(self.query(':OUTP1?')))
                active_ch['d_ch1'] = bool(int(self.query(':OUTP3?')))
                active_ch['d_ch2'] = bool(int(self.query(':OUTP4?')))
            elif awg_mode == 'SING':
                active_ch['a_ch1'] = bool(int(self.query(':OUTP1?')))
            elif awg_mode == 'DUAL':
                active_ch['a_ch1'] = bool(int(self.query(':OUTP1?')))
                active_ch['a_ch4'] = bool(int(self.query(':OUTP4?')))
            elif awg_mode == 'FOUR':
                active_ch['a_ch1'] = bool(int(self.query(':OUTP1?')))
                active_ch['a_ch2'] = bool(int(self.query(':OUTP2?')))
                active_ch['a_ch3'] = bool(int(self.query(':OUTP3?')))
                active_ch['a_ch4'] = bool(int(self.query(':OUTP4?')))

        else:

            for channel in ch:
                if 'a_ch' in channel:
                    ana_chan = int(channel[4:])
                    active_ch[channel] = bool(int(self.ask(':OUTP{0}?'.format(ana_chan))))

                elif 'd_ch'in channel:
                    self.log.warning('Digital channel "{0}" cannot be '
                                     'activated! Command ignored.'
                                     ''.format(channel))
                    active_ch[channel] = False

        if set_ac:
            self.active_channel = active_ch
        else:
            if self.active_channel == dict():
                self.active_channel = active_ch
            else:
                active_ch = self.active_channel

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
        current_channel_state = self.get_active_channels()

        if ch is None:
            return current_channel_state

        if not set(current_channel_state).issuperset(ch):
            self.log.error('Trying to (de)activate channels that are not present in M8195A.\n'
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
        digital_channels = self._get_all_digital_channels()

        # Also (de)activate the channels accordingly
        for a_ch in analog_channels:
            ach_num = int(a_ch.rsplit('_ch', 1)[1])
            # (de)activate the analog channel
            if new_channels_state[a_ch]:
                self.write('OUTP{0:d} ON'.format(ach_num))
            else:
                self.write('OUTP{0:d} OFF'.format(ach_num))

        for d_ch in digital_channels:
            dch_num = int(d_ch.rsplit('_ch', 1)[1])+2
            # (de)activate the digital channel
            if new_channels_state[d_ch]:
                self.write('OUTP{0:d} ON'.format(dch_num))
            else:
                self.write('OUTP{0:d} OFF'.format(dch_num))

        return self.get_active_channels(set_ac=True)


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

        waveforms = list()

        # Sanity checks
        if len(analog_samples) == 0:
            self.log.error('No analog samples passed to write_waveform method in M8195A.')
            return -1, waveforms

        min_samples = 1280
        if total_number_of_samples < min_samples:
            self.log.error('Unable to write waveform.\nNumber of samples to write ({0:d}) is '
                           'smaller than the allowed minimum waveform length ({1:d}).'
                           ''.format(total_number_of_samples, min_samples))
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

        #TODO Atm this solution is for 1 analog channel with 2 marker

        marker = True #TODO should be set in conf...

        for channel_index, channel_number in enumerate(active_analog):

            self.log.info('Max ampl, ch={0}: {1}'.format(channel_number, analog_samples[channel_number].max()))


            a_samples = (((analog_samples[channel_number] + 1)/ 2 * 255) - 128).astype('int8') #TODO check if real values are ok (e.g. if 0 = 0)
            # a_samples = (analog_samples[channel_number]*127).astype('int8')
            if marker and channel_number == 'a_ch1':
                d_samples = digital_samples['d_ch1'].astype('int8')+2*digital_samples['d_ch2'].astype('int8')
                interleaved_samples = np.zeros(2*a_samples.size, dtype=np.int8)
                interleaved_samples[::2] = a_samples
                interleaved_samples[1::2] = d_samples
                # filename = name + '_ch' + str(channel_index + 1) + '_' + str(len(interleaved_samples)//2) + '.bin8'
            else:
                interleaved_samples = a_samples
                # filename = name + '_ch' + str(channel_index + 1) + '_' + str(len(interleaved_samples)) + '.bin8'
            filename = name + '_ch' + str(channel_index + 1) + '.bin8'
            waveforms.append(filename)

            print('009', self.query(':SYST:ERR?'))
            if name in self.query('MMEM:CAT?'):
                print('011', self.query(':SYST:ERR?'))
                self.write(':MMEM:DEL "{0}"'.format(filename))
                print('007', self.query(':SYST:ERR?'))
            print('010', self.query(':SYST:ERR?'))
            self.write_bin(':MMEM:DATA "{0}", '.format(filename), interleaved_samples)
            print('008', self.query(':SYST:ERR?'))

        return total_number_of_samples, waveforms


    def write_sequence(self, name, sequence_parameters):
        """
        Write a new sequence on the device memory.

        @param str name: the name of the waveform to be created/append to
        @param dict sequence_parameters: dictionary containing the parameters for a sequence

        @return: int, number of sequence steps written (-1 indicates failed process)
        """

        # Check if device has sequencer option installed
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. Sequencer option not '
                           'installed.')
            return -1

        # Check if all waveforms are present on device memory
        avail_waveforms = set(self.get_waveform_names())
        for waveform_tuple, param_dict in sequence_parameters:
            if not avail_waveforms.issuperset(waveform_tuple):
                self.log.error('Failed to create sequence "{0}" due to waveforms "{1}" not '
                               'present in device memory.'.format(name, waveform_tuple))
                return -1

        active_analog = natural_sort(chnl for chnl in self.get_active_channels() if chnl.startswith('a'))
        num_tracks = len(active_analog)
        num_steps = len(sequence_parameters)








        pass


    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        waveform_list = list()

        # get only the files from the dir and skip possible directories
        log = os.listdir(self._pulsed_file_dir)
        file_list = list()

        for line in log:
            file_list.append(line)
        for filename in file_list:
            if filename.endswith(('.wfm', '.wfmx', '.mat', '.bin8')):
                waveform_list.append(filename)
        return waveform_list


    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        sequence_list = list()

        if not self.has_sequence_mode():
            return sequence_list

        # get only the files from the dir and skip possible directories
        log = os.listdir(self._pulsed_file_dir)
        file_list = list()

        for line in log:
            file_list.append(line)
        for filename in file_list:
            if filename.endswith(('.seq', '.seqx')):
                if filename not in sequence_list:
                    sequence_list.append(filename)
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

        for name in waveform_name:
            for waveform in avail_waveforms:
                if fnmatch(waveform, name+'_ch?.bin8'): #TODO delete the files
                    deleted_waveforms.append(waveform)


        # clear the AWG if the deleted asset is the currently loaded asset
        if self.current_loaded_asset == waveform_name:
            self.clear_all()
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
            for sequence in avail_sequences:
                if fnmatch(sequence, name+'_ch?.bin8'):
                    deleted_sequences.append(sequence)


        # clear the AWG if the deleted asset is the currently loaded asset
        if self.current_loaded_asset == sequence_name:
            self.clear_all()
        return deleted_sequences


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
        self.log.warning('Interleave mode not available for the AWG M8195A '
                         'Series!\n'
                         'Method call will be ignored.')
        return self.get_interleave()


    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.write('*RST')
        self.write('*WAI')
        return 0

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        return self._sequence_mode

    ################################################################################
    ###                         Non interface methods                            ###
    ################################################################################

    def write(self, command):
        """ Sends a command string to the device.

            @param string command: string containing the command

            @return int: error code (0:OK, -1:error)
        """
        bytes_written, enum_status_code = self.awg.write(command)
        return int(enum_status_code)

    def write_bin(self, command, values):
        """ Sends a command string to the device.

                    @param string command: string containing the command

                    @return int: error code (0:OK, -1:error)
        """
        self.awg.timeout = None
        bytes_written, enum_status_code = self.awg.write_binary_values(command, datatype='b', is_big_endian=False,
                                                                       values=values)
        self.awg.timeout = self._awg_timeout * 1000
        return int(enum_status_code)

    def query(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        return self.    awg.query(question).strip().strip('"')

    def query_bin(self, question):

        return self.awg.query_binary_values(question, datatype='b', is_big_endian=False)

    def _is_awg_running(self):
        """
        Aks the AWG if the AWG is running
        @return: bool, (True: running, False: stoped)
        """
        # 0 No Output is running
        # 1 CH01 is running
        # 2 CH02 is running
        # 4 CH03 is running
        # 8 CH04 is running
        # run_state is sum of these

        run_state = self.query(':STAT:OPER:RUN:COND?')

        if int(run_state) == 0:
            return False
        else:
            return True

    def _is_output_on(self):
        """
        Asks the AWG if the outputs are on
        @return: bool, (True: Outputs are on, False: Outputs are switched off)
        """

        state = 0

        state += int(self.query(':OUTP1?'))
        state += int(self.query(':OUTP2?'))
        state += int(self.query(':OUTP3?'))
        state += int(self.query(':OUTP4?'))

        if int(state) == 0:
            return False
        else:
            return True


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