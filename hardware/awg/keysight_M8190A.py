# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the AWG M8195A device.

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

import re
import os
import visa
import time
import numpy as np
from collections import OrderedDict
from fnmatch import fnmatch
from ftplib import FTP


from core.module import Base, ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints

class AWGM8190A(Base, PulserInterface):                                             #Changed name of class to AWGM8190A                             
    """ The hardware class to control Keysight AWG M8195.

    The referred manual used for this implementation:
        Keysight M8195A Arbitrary Waveform Generator Revision 2
    available here:
        http://literature.cdn.keysight.com/litweb/pdf/M8195-91040.pdf
    """

    #configurations of the awg; change of the name

    _modclass = 'awgm8190a'                                                        #Changed name of _modclass to AWGM8190A    
    _modtype = 'hardware'

    # config options

    visa_address = ConfigOption(name='awg_visa_address', missing='error')
    ip_address = ConfigOption(name='ip_address', missing='error')
    awg_timeout = ConfigOption(name='awg_timeout', default=10, missing='warn')
    # root directory on the other pc
    ftp_root_dir = ConfigOption('ftp_root_dir', default='C:\\inetpub\\ftproot',
                                missing='warn')
    user = ConfigOption('ftp_user', 'anonymous', missing='warn')
    passwd = ConfigOption('ftp_passwd', 'anonymous@', missing='warn')

    # to be able to use all the 4 channels of the AWG with the External Memory
    # the sample rate divider has to be set to 4, which reduces the actual
    # sample rate with which the device samples the data. Internally it will
    # always operate at 53-65GS/s, but the data throughput will be divided by
    # the _sample_rate_div.
    _sample_rate_div = 4

    #configurations of the awg

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # AWG5002C has possibility for sequence output, but it was not tested
        # yet. Therefore set it to False. If it is implemented, set it to True!
        self._SEQUENCE_MODE = False
        self.current_loaded_asset = ''
        self.asset_dir = '\\waves'

    def on_activate(self):
        """ Initialisation performed during activation of the module. """

        config = self.getConfiguration()

        # the path to 'pulsed_file_dir' is the root directory for all the
        # pulsed files. I.e. in sub-directories you can find the pulsed block,
        # pulse block ensembles and sequence files (generic building blocks)
        # and in sampled_hardware_files the real files are situated.

        use_default_dir = True

        if 'pulsed_file_dir' in config.keys():
            if os.path.exists(config['pulsed_file_dir']):
                use_default_dir = False
                self.pulsed_file_dir = config['pulsed_file_dir']

        if use_default_dir:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
            self.log.warning('Either no config parameter "pulsed_file_dir" was '
                             'specified in the config for AWGM8195A class as '
                             'directory for the pulsed files or the directory '
                             'does not exist.\nThe default home directory\n'
                             '{0}\nfor pulsed files will be taken instead.'
                             ''.format(self.pulsed_file_dir))

        # here the samples files are stored on host PC:
        self.host_waveform_dir = self._get_dir_for_name('sampled_hardware_files')

        self.connected = False

        # Sec. 6.2 in manual:
        # The recommended way to program the M8195A module is to use the IVI
        # drivers. See documentation of the IVI drivers how to program using
        # IVI drivers. The connection between the IVI-COM driver and the Soft
        # Front Panel is hidden. To address a module therefore the PXI or USB
        # resource string of the module is used. The IVI driver will connect to
        # an already running Soft Front Panel. If the Soft Front Panel is not
        # running, it will automatically start it.

        # Communicate via SCPI commands through the visa interface:
        # Sec. 6.3.1 in the manual:
        # Before sending SCPI commands to the instrument, the Soft Front Panel
        # (AgM8195SFP.exe) must be started. This can be done in the Windows
        # Start menu (Start > All Programs > Keysight M8195 >
        #             Keysight M8195 Soft Front Panel).
        #
        # Sec. 6.3.1.2 in the manual:
        #   - Socket port: 5025 (e.g. TCPIP0::localhost::5025::SOCKET)
        #   - Telnet port: 5024
        #   - HiSLIP: 0 (e.g. TCPIP0::localhost::hislip0::INSTR)
        #   -  VXI-11.3: 0 (e.g. TCPIP0::localhost::inst0::INSTR) # PXI19::0::0::INSTR


        self._rm = visa.ResourceManager()
        try:
            self._awg = self._rm.open_resource(self.visa_address)

            # Set data transfer format (datatype, is_big_endian, container)
            self._awg.values_format.use_binary('f', False, np.array)

            self._awg.timeout = self.awg_timeout * 1000  # should be in ms

            self.connected = True

            mess = self.ask('*IDN?').split(',')
            self._BRAND = mess[0]
            self._MODEL = mess[1]
            self._SERIALNUMBER = mess[2]
            self._FIRMWARE_VERSION = mess[3]

            self.log.info('Load the device model "{0}" from "{1}" with the '
                          'serial number "{2}" and the firmware version "{3}" '
                          'successfully.'.format(self._MODEL, self._BRAND,
                                                 self._SERIALNUMBER,
                                                 self._FIRMWARE_VERSION))

        except:
            self.log.error('VISA address "{0}" not found by the pyVISA '
                           'resource manager.\nCheck the connection by using '
                           'for example "Agilent Connection Expert".'
                           ''.format(self.visa_address))
            return

        self._init_device()



    def on_deactivate(self):
        """ Required tasks to be performed during deactivation of the module. """

        try:
            self._awg.close()
        except:
            self.log.warning('Closing AWG connection using pyvisa failed.')
        self.log.info('Closed connection to AWG')
        self.connected = False

    def _init_device(self):
        """ Run those methods during the initialization process."""

        # Sec. 6.21.2 in manual:
        # To prepare your module for arbitrary waveform generation follow these
        # steps:
        # Set Instrument Mode (number of channels), Memory Sample Rate Divider,
        # and memory usage of the channels (Internal/Extended):
        self.tell(':INSTrument:DACMode FOUR')  # all four channels output
        # set the sample rate divider:
        self.tell(':INST:MEM:EXT:RDIV DIV{0}'.format(self._sample_rate_div))
        self.tell(':FUNC:MODE ARB')             # Set mode to arbitrary
        self.tell(':TRAC1:MMOD EXT')            # select extended Memory Mode
        self.tell(':TRAC2:MMOD EXT')            # for all channels
        self.tell(':TRAC3:MMOD EXT')
        self.tell(':TRAC4:MMOD EXT')

        # Define a segment using the various forms of the
        #       :TRAC[1|2|3|4]:DEF command.
        # Fill the segment with sample values using
        #       :TRAC[1|2|3|4]:DATA.
        # Signal generation starts after calling INIT:IMM.
        # Use the
        #       :TRAC[1|2|3|4]:CAT?
        # query to read the length of a waveform
        # loaded into the memory of a channel.
        # Use the
        #       :TRAC[1|2|3|4]:DEL:ALL
        # command to delete a waveform from the memory of a channel.


        # Set the directory:
        self.tell(':MMEM:CDIR "C:\\inetpub\\ftproot"')

        self.sample_rate = self.get_sample_rate()

        ampl = {'a_ch1': 1.0, 'a_ch2': 1.0, 'a_ch3': 1.0, 'a_ch4': 1.0}

        self.amplitude_list, self.offset_list = self.set_analog_level(amplitude=ampl)
        self.markers_low, self.markers_high = self.get_digital_level()
        self.is_output_enabled = self._is_output_on()
        self.use_sequencer = self.has_sequence_mode()
        self.active_channel = self.get_active_channels()
        self.interleave = self.get_interleave()
        self.current_loaded_asset = ''
        self.current_status = 0


    def get_constraints(self):
        """
        Retrieve the hardware constrains from the Pulsing device.

        @return constraints object: object with pulser constraints as attributes.

        Provides all the constraints (e.g. sample_rate, amplitude,
        total_length_bins, channel_config, ...) related to the pulse generator
        hardware to the caller.

            SEE PulserConstraints CLASS IN pulser_interface.py
            FOR AVAILABLE CONSTRAINTS!!!

        If you are not sure about the meaning, look in other hardware files to
        get an impression. If still additional constraints are needed, then
        they have to be added to the PulserConstraints class.

        Each scalar parameter is an ScalarConstraints object defined in
        cor.util.interfaces. Essentially it contains min/max values as well as
        min step size, default value and unit of the parameter.

        PulserConstraints.activation_config differs, since it contain the
        channel configuration/activation information of the form:
            {<descriptor_str>: <channel_list>,
             <descriptor_str>: <channel_list>,
             ...}

        If the constraints cannot be set in the pulsing hardware (e.g. because
        it might have no sequence mode) just leave it out so that the default
        is used (only zeros).
        """
        constraints = PulserConstraints()

        # The compatible file formats are hardware specific.
        constraints.waveform_format = ['bin8']

        if self._MODEL == 'M8190A':                                         # Changed model of to AWGM8190A   
            constraints.sample_rate.min = 125e6/self._sample_rate_div       # Changed sample rate minimum 125 MSa/s (for the 12 bit resolution range)
            constraints.sample_rate.max = 12e9/self._sample_rate_div        # Changed sample rate maximum 12 GSa/s  (for the 12 bit resolution range)      
            constraints.sample_rate.step = 1.0e7                            # Changed sample rate step 12 GSa/s
            constraints.sample_rate.default = 12e9/self._sample_rate_div    # Changed sample rate default 12 GSa/s  (for the 12 bit resolution range) 
        else:
            self.log.error('The current AWG model has no valid sample rate '
                           'constraints')

        constraints.a_ch_amplitude.min = 0.350      # Channels amplitude control single ended min                        
        constraints.a_ch_amplitude.max = 0.700      # Channels amplitude control single ended max
        #constraints.a_ch_amplitude.step = 0.002    # for AWG8195: actually 1Vpp/2^8=0.0019; for a DAC resolution of 8 bits
        constraints.a_ch_amplitude.step = 1.7090e4  # for AWG8190: actually 0.7Vpp/2^12=0.0019; for DAC resolution of 12 bits (data sheet p. 17)
        constraints.a_ch_amplitude.default = 0.5    # leave 0.5 as default value   

        # for now, no digital/marker channel.
        #FIXME: implement marker channel configuration, not sure about those values:
        # have a look at OutputLowLevel.
        # constraints.d_ch_low.min = -0.98125
        # constraints.d_ch_low.max = -0.01875
        # constraints.d_ch_low.step = 0.00025
        # constraints.d_ch_low.default = 0.98125
        #
        # have a look at OutputHighLevel.
        # constraints.d_ch_high.min = 0.05625
        # constraints.d_ch_high.max = 0.98125
        # constraints.d_ch_high.step = 0.00025
        # constraints.d_ch_high.default = 0.98125

        # leave defaults     

        constraints.sampled_file_length.min = 256                            
        constraints.sampled_file_length.max = 2_000_000_000                 
        constraints.sampled_file_length.step = 256                             
        constraints.sampled_file_length.default = 256       

        # leave defaults   

        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 16_000_000
        constraints.waveform_num.default = 1
        # The sample memory can be split into a maximum of 16 M waveform segments

        # leave defaults           

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
        constraints.trigger_in.min = 0
        constraints.trigger_in.max = 1
        constraints.trigger_in.step = 1
        constraints.trigger_in.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names
        # for the different configurations can be customary chosen.

        activation_config = OrderedDict()

        if self._MODEL == 'M8190A':                                                     # Change model of awg   
            activation_config['all'] = ['a_ch1', 'a_ch2', 'a_ch3', 'a_ch4']             # Leave defaults   
            #FIXME: this awg model supports more channel configuration!
            #       Implement those! But keep in mind that the format of the
            #       file might change for difference configurations.

        constraints.activation_config = activation_config

        # FIXME: additional constraint really necessary?
        constraints.dac_resolution = {'min': 12, 'max': 12, 'step': 1,                  # Changed resolution of DAC to 12 bits for 12G option; leave step at one  
                                      'unit': 'bit'}
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        # Check if AWG is in function generator mode
        # self._activate_awg_mode()


        self.tell(':OUTP1 ON')
        self.tell(':OUTP2 ON')
        self.tell(':OUTP3 ON')
        self.tell(':OUTP4 ON')

        # Sec. 6.4 from manual:
        # In the program it is recommended to send the command for starting
        # data generation (:INIT:IMM) as the last command. This way
        # intermediate stop/restarts (e.g. when changing sample rate or
        # loading a waveform) are avoided and optimum execution performance is
        # achieved.

        # wait until the AWG is actually running
        while not self._is_output_on():
            time.sleep(0.25)

        self.tell(':INIT:IMM')


        self.current_status = 1
        self.is_output_enabled = True
        return self.current_status

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.tell(':ABOR')

        self.tell(':OUTP1 OFF')
        self.tell(':OUTP2 OFF')
        self.tell(':OUTP3 OFF')
        self.tell(':OUTP4 OFF')

        # wait until the AWG has actually stopped
        while self._is_output_on():
            time.sleep(0.25)
        self.current_status = 0
        self.is_output_enabled = False
        return self.current_status


    def _send_file(self, filename):
        """ Sends an already hardware specific waveform file to the pulse
            generators waveform directory.

        @param string filename: The file name of the source file

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """

        filepath = os.path.join(self.host_waveform_dir, filename)

        with FTP(self.ip_address) as ftp:
            ftp.login(self.user, self.passwd) # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.asset_dir)
            with open(filepath, 'rb') as uploaded_file:
                ftp.storbinary('STOR '+filename, uploaded_file)

    def upload_asset(self, asset_name=None):
        """ Upload an already hardware conform file to the device.
            Does NOT load it into channels.

        @param str asset_name: name of the ensemble/sequence to be uploaded

        @return int: error code (0:OK, -1:error)

        If nothing is passed, method will be skipped.
        """
        # check input
        if asset_name is None:
            self.log.warning('No asset name provided for upload!\nCorrect '
                    'that!\nCommand will be ignored.')
            return -1

        # at first delete all the name, which might lead to confusions in the
        # upload procedure:
        self.delete_asset(asset_name)

        # create list of filenames to be uploaded
        upload_names = []
        filelist = os.listdir(self.host_waveform_dir)
        for filename in filelist:

            is_wfm = filename.endswith('.bin8')

            if is_wfm and (asset_name + '_ch') in filename:
                upload_names.append(filename)

        # upload files
        for name in upload_names:
            self._send_file(name)
        return 0

    # Leave defaults for asset              

    def load_asset(self, asset_name, load_dict=None):
        """ Loads a sequence or waveform to the specified channel of the pulsing
            device.

        @param str asset_name: The name of the asset to be loaded

        @param dict load_dict:  a dictionary with keys being one of the
                                available channel numbers and items being the
                                name of the already sampled
                                waveform/sequence files.
                                Examples:   {1: rabi_ch1, 2: rabi_ch2}
                                            {1: rabi_ch2, 2: rabi_ch1}
                                This parameter is optional. If none is given
                                then the channel association is invoked from
                                the sequence generation,
                                i.e. the filename appendix (_ch1, _ch2 etc.)

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """

        if load_dict is None:
            load_dict = {}

        # # set the waveform directory:
        # self.tell(':MMEM:CDIR {0}'.format(r"C:\Users\Name\Documents"))
        #
        # # Get the waveform directory:
        # dir = self.ask(':MMEM:CDIR?')

        path = self.ftp_root_dir + self.asset_dir

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

            if file == asset_name+'_ch1.bin8':
                filepath = os.path.join(path, asset_name + '_ch1.bin8')
                self.log.info(filepath)
                self.tell(':TRAC1:IMP {0}, "{1}", {2}, {3}, {4}, {5}'
                          ''.format(segment,
                                    filepath,
                                    form,
                                    data_type,
                                    marker_flag,
                                    mem_mode))
                self.current_loaded_asset = asset_name
                filename.append(file)

            elif file == asset_name+'_ch2.bin8':
                filepath = os.path.join(path, asset_name + '_ch2.bin8')
                self.log.info(filepath)
                self.tell(':TRAC2:IMP {0}, "{1}", {2}, {3}, {4}, {5}'
                          ''.format(segment,
                                    filepath,
                                    form,
                                    data_type,
                                    marker_flag,
                                    mem_mode))

                self.current_loaded_asset = asset_name
                filename.append(file)

            elif file == asset_name+'_ch3.bin8':
                filepath = os.path.join(path, asset_name + '_ch3.bin8')
                self.log.info(filepath)
                self.tell(':TRAC3:IMP {0}, "{1}", {2}, {3}, {4}, {5}'
                          ''.format(segment,
                                    filepath,
                                    form,
                                    data_type,
                                    marker_flag,
                                    mem_mode))
                self.current_loaded_asset = asset_name
                filename.append(file)

            elif file == asset_name+'_ch4.bin8':
                filepath = os.path.join(path, asset_name + '_ch4.bin8')
                self.log.info(filepath)
                self.tell(':TRAC4:IMP {0}, "{1}", {2}, {3}, {4}, {5}'
                          ''.format(segment,
                                    filepath,
                                    form,
                                    data_type,
                                    marker_flag,
                                    mem_mode))
                self.current_loaded_asset = asset_name
                filename.append(file)

        if load_dict == {} and filename == []:
            self.log.warning('No file and channel provided for load!\n'
                    'Correct that!\nCommand will be ignored.')

        for channel_num in list(load_dict):
            file_name = str(load_dict[channel_num]) + '_ch{0}.bin8'.format(int(channel_num))
            filepath = os.path.join(path, file_name)

            self.tell(':TRAC{0}:IMP {1}, "{2}", {3}, {4}'.format(channel_num,
                                                                 segment,
                                                                 filepath,
                                                                 form,
                                                                 mem_mode))

        if len(load_dict) > 0:
            self.current_loaded_asset = asset_name

        return 0

    # def load_asset(self, asset_name, load_dict=None):
    #     """ Loads a sequence or waveform to the specified channel of the pulsing
    #         device.
    #
    #     @param str asset_name: The name of the asset to be loaded
    #
    #     @param dict load_dict:  a dictionary with keys being one of the
    #                             available channel numbers and items being the
    #                             name of the already sampled
    #                             waveform/sequence files.
    #                             Examples:   {1: rabi_ch1, 2: rabi_ch2}
    #                                         {1: rabi_ch2, 2: rabi_ch1}
    #                             This parameter is optional. If none is given
    #                             then the channel association is invoked from
    #                             the sequence generation,
    #                             i.e. the filename appendix (_ch1, _ch2 etc.)
    #
    #     @return int: error code (0:OK, -1:error)
    #
    #     Unused for digital pulse generators without sequence storage capability
    #     (PulseBlaster, FPGA).
    #     """
    #
    #     if load_dict is None:
    #         load_dict = {}
    #
    #     # # set the waveform directory:
    #     # self.tell(':MMEM:CDIR {0}'.format(r"C:\Users\Name\Documents"))
    #     #
    #     # # Get the waveform directory:
    #     # dir = self.ask(':MMEM:CDIR?')
    #
    #     path = self.host_waveform_dir
    #
    #     # Find all files associated with the specified asset name
    #     file_list = self._get_filenames_on_host()
    #     filename = []
    #
    #     # Be careful which asset_name to specify as the current_loaded_asset
    #     # because a loaded sequence contains also individual waveforms, which
    #     # should not be used as the current asset!!
    #
    #     segment = 1     # the id in the external memory
    #     init_val = 0    # initial value how samples where allocated on device.
    #     offset =  0     # the sample offset
    #
    #     for file in file_list:
    #         if file == asset_name+'_ch1.bin8':
    #             filepath = os.path.join(path, asset_name + '_ch1.bin8')
    #
    #             # not entierly sure why *4, maybe it is due to the divider. But
    #             # this gives the correct size.
    #             size_waveform = os.path.getsize(filepath) * 4
    #             self._length_check(size_waveform)
    #
    #             # at first delete the files from the segment
    #             self.tell(':TRAC1:DEL {0}'.format(segment))
    #             # then define it:
    #             self.tell(':TRAC1:DEF {0}, {1}, {2}'.format(segment,
    #                                                        size_waveform,
    #                                                        init_val))
    #             with open(filepath, 'rb') as f_obj:
    #
    #                 self.tell(':TRAC1:DATA {0},{1},'.format(segment, offset),
    #                           write_val=True, block=f_obj.read())
    #
    #             offset += os.path.getsize(filepath)
    #             self.current_loaded_asset = asset_name
    #             filename.append(file)
    #
    #         elif file == asset_name+'_ch2.bin8':
    #             filepath = os.path.join(path, asset_name + '_ch2.bin8')
    #
    #             # not entierly sure why *4, maybe it is due to the divider. But
    #             # this gives the correct size.
    #             size_waveform = os.path.getsize(filepath) * 4
    #             self._length_check(size_waveform)
    #
    #             # at first delete the files from the segment
    #             self.tell(':TRAC2:DEL {0}'.format(segment))
    #             # then define it:
    #             self.tell(':TRAC2:DEF {0}, {1}, {2}'.format(segment,
    #                                                         size_waveform,
    #                                                         init_val))
    #             with open(filepath, 'rb') as f_obj:
    #
    #                 self.tell(':TRAC2:DATA {0},{1},'.format(segment, offset),
    #                           write_val=True, block=f_obj.read())
    #             self.current_loaded_asset = asset_name
    #             filename.append(file)
    #
    #         elif file == asset_name+'_ch3.bin8':
    #             filepath = os.path.join(path, asset_name + '_ch3.bin8')
    #
    #             # not entierly sure why *4, maybe it is due to the divider. But
    #             # this gives the correct size.
    #             size_waveform = os.path.getsize(filepath) * 4
    #             self._length_check(size_waveform)
    #
    #             # at first delete the files from the segment
    #             self.tell(':TRAC3:DEL {0}'.format(segment))
    #             # then define it:
    #             self.tell(':TRAC3:DEF {0}, {1}, {2}'.format(segment,
    #                                                         size_waveform,
    #                                                         init_val))
    #             with open(filepath, 'rb') as f_obj:
    #
    #                 self.tell(':TRAC3:DATA {0},{1},'.format(segment, offset),
    #                           write_val=True, block=f_obj.read())
    #             self.current_loaded_asset = asset_name
    #             filename.append(file)
    #
    #         elif file == asset_name+'_ch4.bin8':
    #             filepath = os.path.join(path, asset_name + '_ch4.bin8')
    #             # not entierly sure why *4, maybe it is due to the divider. But
    #             # this gives the correct size.
    #             size_waveform = os.path.getsize(filepath) * 4
    #             self._length_check(size_waveform)
    #
    #             # at first delete the files from the segment
    #             self.tell(':TRAC4:DEL {0}'.format(segment))
    #             # then define it:
    #             self.tell(':TRAC4:DEF {0}, {1}, {2}'.format(segment,
    #                                                         size_waveform,
    #                                                         init_val))
    #             with open(filepath, 'rb') as f_obj:
    #
    #                 self.tell(':TRAC4:DATA {0},{1},'.format(segment, offset),
    #                           write_val=True, block=f_obj.read())
    #             self.current_loaded_asset = asset_name
    #             filename.append(file)
    #
    #     if load_dict == {} and filename == []:
    #         self.log.warning('No file and channel provided for load!\n'
    #                 'Correct that!\nCommand will be ignored.')
    #
    #     for channel_num in list(load_dict):
    #         file_name = str(load_dict[channel_num]) + '_ch{0}.bin8'.format(int(channel_num))
    #         filepath = os.path.join(path, file_name)
    #
    #         # not entierly sure why *4, maybe it is due to the divider. But
    #         # this gives the correct size.
    #         size_waveform = os.path.getsize(filepath) * 4
    #         self._length_check(size_waveform)
    #
    #         # at first delete the files from the segment
    #         self.tell(':TRAC{0}:DEL {1}'.format(channel_num, segment))
    #         # then define it:
    #         self.tell(':TRAC{0}:DEF {1}, {2}, {3}'.format(channel_num,
    #                                                       segment,
    #                                                       size_waveform,
    #                                                       init_val))
    #         with open(filepath, 'rb') as f_obj:
    #
    #             self.tell(':TRAC{0}:DATA {1},{2},'.format(channel_num,
    #                                                       segment,
    #                                                       offset),
    #                       write_val=True, block=f_obj.read())
    #             self.current_loaded_asset = asset_name
    #
    #     if len(load_dict) > 0:
    #         self.current_loaded_asset = asset_name
    #
    #     return 0

    # Leave defaults 

    def _length_check(self, size):
        """ Length check of the sequence to guarente the granularity.

        @param int size:
        """

        gran = 64
        if size%gran != 0:
            self.log.warning('The waveform does not fulfil the granularity of'
                             '"{}" and there are "{}" samples to much'
                             ''.format(gran, size%gran))

    def get_loaded_asset(self):
        """ Retrieve the currently loaded asset name of the device.

        @return str: Name of the current asset, that can be either a filename
                     a waveform, a sequence ect.
        """
        return self.current_loaded_asset

    def clear_all(self):
        """ Clears the loaded waveform from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Delete all waveforms and sequences from Hardware memory and clear the
        visual display. Unused for digital pulse generators without sequence
        storage capability (PulseBlaster, FPGA).
        """

        self.tell(':TRAC:DEL:ALL')
        self.current_loaded_asset = ''
        return

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): inter value of the current status with the
                             corresponding dictionary containing status
                             description for all the possible status variables
                             of the pulse generator hardware.
                0 indicates that the instrument has stopped.
                1 indicates that the instrument is waiting for trigger.
                2 indicates that the instrument is running.
               -1 indicates that the request of the status for AWG has failed.
        """
        status_dic = {}
        status_dic[-1] = 'Failed Request or Communication'
        status_dic[0] = 'Device has stopped, but can receive commands.'
        status_dic[1] = 'Device is active and running.'
        # All the other status messages should have higher integer values
        # then 1.

        # ask 3 times
        for _ in range(3):
            try:
                state = int(self.ask(':OUTP1?'))
                break
            except:
                state = -1

        for _ in range(3):
            try:
                state = int(self.ask(':OUTP2?')) | state
                break
            except:
                state = -1

        for _ in range(3):
            try:
                state = int(self.ask(':OUTP3?')) | state
                break
            except:
                state = -1

        for _ in range(3):
            try:
                state = int(self.ask(':OUTP4?')) | state
                break
            except:
                state = -1

        return state, status_dic

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate in a class variable, but instead
        retrieve the current sample rate directly from the device.
        """

        self.sample_rate = float(self.ask(':FREQ:RAST?'))/self._sample_rate_div
        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device.

        Note: After setting the sampling rate of the device, retrieve it again
              for obtaining the actual set value and use that information for
              further processing.
        """
        sample_rate_GHz = (sample_rate * self._sample_rate_div)/1e9
        self.tell(':FREQ:RAST {0:.4G}GHz\n'.format(sample_rate_GHz))
        time.sleep(0.2)
        return self.get_sample_rate()


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

        Note: Do not return a saved amplitude and/or offset value but instead
              retrieve the current amplitude and/or offset directly from the
              device.

        If no entries provided then the levels of all channels where simply
        returned. If no analog channels provided, return just an empty dict.
        Example of a possible input:
            amplitude = [1,4], offset =[1,3]
        to obtain the amplitude of channel 1 and 4 and the offset
            {1: -0.5, 4: 2.0} {}
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
        if amplitude is None:
            amplitude = []
        if offset is None:
            offset = []
        amp = {}
        off = {}

        pattern = re.compile('[0-9]+')

        if (amplitude == []) and (offset == []):

            # since the available channels are not going to change for this
            # device you are asking directly:
            amp['a_ch1'] = float(self.ask(':VOLT1?'))
            amp['a_ch2'] = float(self.ask(':VOLT2?'))
            amp['a_ch3'] = float(self.ask(':VOLT3?'))
            amp['a_ch4'] = float(self.ask(':VOLT4?'))

            off['a_ch1'] = float(self.ask(':VOLT1:OFFS?'))
            off['a_ch2'] = float(self.ask(':VOLT2:OFFS?'))
            off['a_ch3'] = float(self.ask(':VOLT3:OFFS?'))
            off['a_ch4'] = float(self.ask(':VOLT4:OFFS?'))


        else:

            for a_ch in amplitude:
                ch_num = int(re.search(pattern, a_ch).group(0))
                amp[a_ch] = float(self.ask(':VOLT{0}?'.format(ch_num)))

            for a_ch in offset:
                ch_num = int(re.search(pattern, a_ch).group(0))
                off[a_ch] = float(self.ask(':VOLT{0}:OFFS?'.format(ch_num)))

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
        if amplitude is None:
            amplitude = {}
        if offset is None:
            offset = {}

        constraints = self.get_constraints()

        pattern = re.compile('[0-9]+')

        for a_ch in amplitude:
            constr = constraints.a_ch_amplitude

            ch_num = int(re.search(pattern, a_ch).group(0))

            if not(constr.min <= amplitude[a_ch] <= constr.max):
                self.log.warning('Not possible to set for analog channel {0} '
                                 'the amplitude value {1}Vpp, since it is not '
                                 'within the interval [{2},{3}]! Command will '
                                 'be ignored.'
                                 ''.format(a_ch, amplitude[a_ch],
                                           constr.min, constr.max))
            else:
                self.tell(':VOLT{0} {1:.4f}'.format(ch_num, amplitude[a_ch]))

        for a_ch in offset:
            constr = constraints.a_ch_offset

            ch_num = int(re.search(pattern, a_ch).group(0))

            if not(constr.min <= offset[a_ch] <= constr.max):
                self.log.warning('Not possible to set for analog channel {0} '
                                 'the offset value {1}V, since it is not '
                                 'within the interval [{2},{3}]! Command will '
                                 'be ignored.'
                                 ''.format(a_ch, offset[a_ch], constr.min,
                                           constr.max))
            else:
                self.tell(':VOLT{0}:OFFS {1:.4f}'.format(ch_num, offset[a_ch]))

        return self.get_analog_level(amplitude=list(amplitude), offset=list(offset))

    # Leave defaults             

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided channels.

        @param list low: optional, if a specific low value (in Volt) of a
                         channel is desired.
        @param list high: optional, if a specific high value (in Volt) of a
                          channel is desired.

        @return: tuple of two dicts, with keys being the channel number and
                 items being the values for those channels. Both low and high
                 value of a channel is denoted in (absolute) Voltage.

        If no entries provided then the levels of all channels where simply
        returned. If no digital channels provided, return just an empty dict.
        Example of a possible input:
            low = [1,4]
        to obtain the low voltage values of digital channel 1 an 4. A possible
        answer might be
            {1: -0.5, 4: 2.0} {}
        since no high request was performed.

        Note, the major difference to analog signals is that digital signals are
        either ON or OFF, whereas analog channels have a varying amplitude
        range. In contrast to analog output levels, digital output levels are
        defined by a voltage, which corresponds to the ON status and a voltage
        which corresponds to the OFF status (both denoted in (absolute) voltage)

        In general there is not a bijective correspondence between
        (amplitude, offset) for analog and (value high, value low) for digital!
        """

        # no digital channel implemented.
        #FIXME: if marker are implemented, adapt this output
        # use self.ask(':VOLT:HIGH?') and self.ask(':VOLT:LOW?')
        return {}, {}

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

        # no digital channel implemented.
        #FIXME: if marker are implemented, adapt this output
        return {}, {}


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
        if ch is None:
            ch = []

        active_ch = {}

        if ch ==[]:

            # because 0 = False and 1 = True
            active_ch['a_ch1'] = bool(int(self.ask(':OUTP1?')))
            active_ch['a_ch2'] = bool(int(self.ask(':OUTP2?')))
            active_ch['a_ch3'] = bool(int(self.ask(':OUTP3?')))
            active_ch['a_ch4'] = bool(int(self.ask(':OUTP4?')))

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

        return active_ch

    # Leave defaults  

    def set_active_channels(self, ch=None):
        """ Set the active channels for the pulse generator hardware.

        @param dict ch: dictionary with keys being the analog or digital
                          string generic names for the channels with items being
                          a boolean value.

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
        if ch is None:
            ch = {}

        #FIXME: this method seems not to be sensible for this device. Check
        #       whether doing nothing is the right way to do here.
        #
        # for channel in ch:
        #     if 'a_ch' in channel:
        #         ana_chan = int(channel[4:])
        #
        #         # int(True) = 1, int(False) = 0:
        #         self.tell(':OUTP{0} {1}'.format(ana_chan, int(ch[channel])))
        #
        #     if 'd_ch' in channel:
        #         self.log.info('Digital Channel "{0}" is not implemented in the '
        #                       'AWG M8195A series! Command skipped.'
        #                       ''.format(ch[channel]))

        return self.get_active_channels(ch=list(ch))


    def get_uploaded_asset_names(self):
        """ Retrieve the names of all uploaded assets on the device.

        @return list: List of all uploaded asset name strings in the current
                      device directory.

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        uploaded_files = self._get_filenames_on_device()
        name_list = []
        for filename in uploaded_files:
            if fnmatch(filename, '*_ch?.bin8'):
                asset_name = filename.rsplit('_', 1)[0]
                if asset_name not in name_list:
                    name_list.append(asset_name)
        return name_list

    def get_saved_asset_names(self):
        """ Retrieve the names of all sampled and saved assets on the host PC.
        This is no list of the file names.

        @return list: List of all saved asset name strings in the current
                      directory of the host PC.
        """
        # list of all files in the waveform directory ending with .wfm
        file_list = self._get_filenames_on_host()
        # exclude the channel specifier for multiple analog channels and create return list
        saved_assets = []
        for filename in file_list:
            if fnmatch(filename, '*_ch?.bin8'):
                asset_name = filename.rsplit('_', 1)[0]
                if asset_name not in saved_assets:
                    saved_assets.append(asset_name)
        return saved_assets

    def delete_asset(self, asset_name):
        """ Delete all files associated with an asset with the passed
            asset_name from the device memory.

        @param str asset_name: The name of the asset to be deleted
                               Optionally a list of asset names can be passed.

        @return list: a list with strings of the files which were deleted.

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        if not isinstance(asset_name, list):
            asset_name = [asset_name]

        # get all uploaded files
        uploaded_files = self._get_filenames_on_device()

        # list of uploaded files to be deleted
        files_to_delete = []
        # determine files to delete
        for name in asset_name:
            for filename in uploaded_files:
                if fnmatch(filename, name+'_ch?.bin8'):
                    files_to_delete.append(filename)


        # clear the AWG if the deleted asset is the currently loaded asset
        if self.current_loaded_asset == asset_name:
            self.clear_all()
        return files_to_delete

    def set_asset_dir_on_device(self, dir_path):
        """ Change the directory where the assets are stored on the device.

        @param string dir_path: The target directory

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without changeable file structure
        (PulseBlaster, FPGA).
        """

        # check whether the desired directory exists:
        with FTP(self.ip_address) as ftp:
            # login as specified user
            ftp.login(user=self.user, passwd=self.passwd)
            try:
                ftp.cwd(dir_path)
            except:
                self.log.info('Desired directory {0} not found on AWG '
                              'device.\n'
                              'Create new.'.format(dir_path))
                ftp.mkd(dir_path)
        self.asset_dir = dir_path

        return 0

    def get_asset_dir_on_device(self):
        """ Ask for the directory where the assets are stored on the device.

        @return string: The current sequence directory

        Unused for digital pulse generators without changeable file structure
        (PulseBlaster, FPGA).
        """

        return self.asset_directory

    def get_interleave(self):
        """ Check whether Interleave is on in AWG.
        Unused for pulse generator hardware other than an AWG. The AWG M8195A
        Series does not have an interleave mode and this method exists only for
        compability reasons.

        @return bool: will be always False since no interleave functionality
        """

        return False

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        @return bool: actual interleave status (True: ON, False: OFF)

        Note: After setting the interleave of the device, retrieve the
              interleave again and use that information for further processing.

        Unused for pulse generator hardware other than an AWG. The AWG M8195A
        Series does not have an interleave mode and this method exists only for
        compability reasons.
        """
        self.log.warning('Interleave mode not available for the AWG M8195A '
                         'Series!\n'
                         'Method call will be ignored.')
        return self.get_interleave()

    def tell(self, command, wait=True, write_val=False, block=None, check_err=True):
        """Send a command string to the AWG.

        @param command: string containing the command
        @param bool wait: optional, is the wait statement should be skipped.
        @param bool check_err: Perform an error check after each tell

        @return: str: the statuscode of the write command.
        """

        if write_val:
            statuscode = self._awg.write_values(command, block)
            # statuscode =  self._awg.write_binary_values(command, block)
        else:
            statuscode = self._awg.write(command)

        if check_err:
            self._check_for_err()
        if wait:
            self._awg.write('*WAI')

        return statuscode

    # Leave defaults          

    def ask(self, question):
        """ Asks the device a 'question' and receive an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question'
        """

        # cut away the characters\r and \n.
        return self._awg.query(question).strip()

    def reset(self):
        """Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.tell('*RST')

        return 0

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        return self._SEQUENCE_MODE


################################################################################
###                         Non interface methods                            ###
################################################################################

    def _check_for_err(self):
        """ Ask the error status of the device as long as there is no error."""

        err_count = 0
        # Limit the number of maximal error outputs to prevent an inf loop:
        while err_count < 20:
            err, mess = self.ask(':SYSTem:ERRor?').split(',')
            err = int(err)
            if err == 0:
                # no error
                break
            else:
                self.log.warning('Errorcode "{0}": {1}'.format(err, mess))
            err_count += 1

    def _is_output_on(self):
        """
        Aks the AWG if the output is enabled, i.e. if the AWG is running

        @return: bool, (True: output on, False: output off)
        """

        # since output 4 was the last one to be set, assume that all other are
        # already set
        run_state = bool(int(self.ask(':OUTP4?')))
        return run_state


    def _get_dir_for_name(self, name):
        """ Get the path to the pulsed sub-directory 'name'.

        @param str name:  name of the folder
        @return: str, absolute path to the directory with folder 'name'.
        """

        path = os.path.join(self.pulsed_file_dir, name)
        if not os.path.exists(path):
            os.makedirs(os.path.abspath(path))

        return os.path.abspath(path)

    def _get_filenames_on_host(self):
        """ Get the full filenames of all assets saved on the host PC.

        @return: list, The full filenames of all assets saved on the host PC.
        """
        filename_list = [f for f in os.listdir(self.host_waveform_dir) if f.endswith('.bin8')]
        return filename_list

    def _get_filenames_on_device(self):
        """ Get the full filenames of all assets saved on the device.

        @return: list, The full filenames of all assets saved on the device.
        """
        filename_list = []
        with FTP(self.ip_address) as ftp:
            ftp.login(user=self.user, passwd=self.passwd) # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.asset_dir)
            # get only the files from the dir and skip possible directories
            log =[]
            file_list = []
            ftp.retrlines('LIST', callback=log.append)
            for line in log:
                if '<DIR>' not in line:
                    # that is how a potential line is looking like:
                    #   '05-10-16  05:22PM                  292 SSR aom adjusted.seq'
                    # One can see that the first part consists of the date
                    # information. Remove those information and separate then
                    # the first number, which indicates the size of the file,
                    # from the following. That is necessary if the filename has
                    # whitespaces in the name:
                    size_filename = line[18:].lstrip()

                    # split after the first appearing whitespace and take the
                    # rest as filename, remove for safety all trailing
                    # whitespaces:
                    actual_filename = size_filename.split(' ', 1)[1].lstrip()
                    file_list.append(actual_filename)
            for filename in file_list:
                if filename.endswith(('.wfm', '.wfmx', '.mat', '.seq', '.seqx',
                                      '.bin8')):
                    if filename not in filename_list:
                        filename_list.append(filename)
        return filename_list


    def direct_upload(self, channel, asset_name_p):
        """ Direct upload from RAM to the device.

        @param int channel: channel number in the range [1,2,3,4].
        @param object asset_name_p: a reference to the file object pointer in
                                    the RAM containing the binary written data.
                                    E.g. if file object was open with
                                    f=open(xxx) f would be the asset_name_p.

        @return int: error code (0:OK, -1:error)
        """

        # k.tell(':TRAC1:DEF 1, 26624,0')
        # Out[31]: (23, < StatusCode.success: 0 >)
        #
        # f = open(path, 'rb')
        #
        # os.path.getsize(path)
        #
        # k._awg.write_binary_values(':TRAC1:DATA 1,0,', f.read())


        #FIXME: that is not fixed yet


        # select extended Memory Mode
        self.tell(':TRAC1:MMOD EXT')
        self.tell(':TRAC2:MMOD EXT')
        self.tell(':TRAC3:MMOD EXT')
        self.tell(':TRAC4:MMOD EXT')

        segment = 1     # always write in segment 1
        length = len(asset_name_p)
        self.tell(':TRAC{0}:DEF {1},{2},0'.format(channel, segment, length))


        self.tell(':TRAC{0}:DATA {1},0,{2}'.format(channel, segment,
                                                     asset_name_p),
                    write_val=True)

        return 0


"""
Discussion about sampling the waveform for the AWG. This text will move 
eventually to the sampling method, but will stay for the initial start of the
implementation in this file.

The information for the file format are taken from the Keysight M8195 user 
manual, from section 6.21.10 (p. 247), to be found here:

http://literature.cdn.keysight.com/litweb/pdf/M8195-91040.pdf?id=2678487


We will choose the native file format for the M8195 series with is called BIN8:

It is a binary file format (written in small endian), representing an 8bit 
integer and expressing a real value (not complex for iq modulation).

8bit are for each single channel only and contain no parameter header and no
data header. Excerpt from the manual:

BIN8
is the most memory efficient file format for the M8195A without digital markers. 
As a result, the fastest file download can be achieved.
One file contains waveform samples for one channel. The waveform samples can be 
imported to any of the four M8195A channels. Samples consist of binary int8 
values:


   7   |   6   |   5   |   4   |   3   |   2   |   1   |   0   |
----------------------------------------------------------------
  DB7  | DB6   |  DB5  |  DB4  |  DB3  |  DB2  |  DB1  |  DB0  |

DB = Data bit

so to convert a number to a 8bit representation you have to know the amplitude
range. Here it will be -0.5 V to +0.5 V, so 1Vpp. Therefore -0.5V corresponds to
0 and +0.5V to 255 (since 2^8=256). Hence the conversion is done in the 
following way:

x = float number between -0.5V and +0.5V to be converted to int8:

    int8((x + 0.5)*255)

or of an array:

    x_bin = ((x + 0.5)*255).astype('int8')

"""