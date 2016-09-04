# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware module for AWG7000 Series.

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

import time
from ftplib import FTP
from socket import socket, AF_INET, SOCK_STREAM
import os
from collections import OrderedDict
from fnmatch import fnmatch

from core.base import Base
from interface.pulser_interface import PulserInterface


# todo: add in squencing a method which changes from dynamic to jump in order to get triggers for odmr
class AWG7122C(Base, PulserInterface):
    """ Unstable and in construction, Jochen Scheuer    """

    _modclass = 'awg7122c'
    _modtype = 'hardware'

    # declare connectors
    # _out = {'awg5002c': 'PulserInterface'}
    _out = {'pulser': 'PulserInterface'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        if 'awg_IP_address' in config.keys():
            self.ip_address = config['awg_IP_address']
        else:
            self.log.error('No IP address parameter "awg_IP_address" found '
                    'in the config for the AWG7122C! Correct that!')

        if 'awg_port' in config.keys():
            self.port = config['awg_port']
        else:
            self.log.error('No port parameter "awg_port" found in the config '
                    'for the AWG5002C! Correct that!')

        if 'default_sample_rate' in config.keys():
            self.sample_rate = config['default_sample_rate']
        else:
            self.log.warning('No parameter "default_sample_rate" found in '
                    'the config for the AWG7122C! The maximum sample rate is '
                    'used instead.')
            self.sample_rate = self.get_constraints()['sample_rate'][1]

        if 'awg_ftp_path' in config.keys():
            self.ftp_path = config['awg_ftp_path']
        else:
            self.log.error('No parameter "awg_ftp_path" found in the config '
                    'for the AWG7122C! State the FTP folder of this device!')

        if 'timeout' in config.keys():
            self._timeout = config['timeout']
        else:
            self.log.warning('No parameter "timeout" found in the config for '
                    'the AWG7122C! Take a default value of 10s.')
            self._timeout = 10

        self.connected = False

        self.loaded_sequence = None
        self.is_output_enabled = True

        # settings for remote access on the AWG PC
        self.asset_directory = '\\waves'

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

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')

        # AWG7122c has possibility for sequence output
        self.sequence_mode = True

        self.current_loaded_asset = None

        self._marker_byte_dict = {0: b'\x00', 1: b'\x01', 2: b'\x02', 3: b'\x03'}

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self.connected = True
        # connect ethernet socket and FTP
        self.soc = socket(AF_INET, SOCK_STREAM)
        self.soc.settimeout(self._timeout)  # set the timeout to 5 seconds
        self.soc.connect((self.ip_address, self.port))
        self.input_buffer = int(2 * 1024)  # buffer length for received text

        #OPtions of AWG7000 series:
        #              Option 01: Memory expansion to 64,8 M points (Million points)
        #              Option 06: Interleave and extended analog output bandwidth
        #              Option 08: Fast sequence switching
        #              Option 09: Subsequence and Table Jump

        self.AWG_options=self.ask('*Opt?')
        self.interleave = self.get_interleave()

        #Todo: inclulde proper routine to check and change
        zeroing_int = int(self.ask('AWGControl:INTerleave:ZERoing?'))
        if zeroing_int == 0:
            self.zeroing = False
        elif zeroing_int == 1:
            self.zeroing = True

        #Set current directory on AWG
        self.tell('MMEMORY:CDIRECTORY "{0}"\n'.format(self.ftp_path+self.asset_directory))

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self.connected = False
        self.soc.close()

    # =========================================================================
    # Below all the Pulser Interface routines.
    # =========================================================================

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Pulsing device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints (e.g. sample_rate, amplitude,
        total_length_bins, channel_config, ...) related to the pulse generator
        hardware to the caller.
        The keys of the returned dictionary are the str name for the constraints
        (which are set in this method).

                    NO OTHER KEYS SHOULD BE INVENTED!

        If you are not sure about the meaning, look in other hardware files to
        get an impression. If still additional constraints are needed, then they
        have to be added to all files containing this interface.

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


        # Todo: Set values for AWG7122c
        constraints = {}

        # if interleave option is available, then sample rate constraints must
        # be assigned to the output of a function called
        # _get_sample_rate_constraints()
        # which outputs the shown dictionary with the correct values depending
        # on the present mode. The the GUI will have to check again the
        # limitations if interleave was selected.
        constraints['sample_rate'] = self._get_sample_rate_constraints()

        # The file formats are hardware specific. The sequence_generator_logic will need this
        # information to choose the proper output format for waveform and sequence files.
        constraints['waveform_format'] = 'wfm'
        constraints['sequence_format'] = 'seq'

        #checked
        # the stepsize will be determined by the DAC in combination with the
        # maximal output amplitude (in Vpp):
        if self.zeroing:
            constraints['a_ch_amplitude'] = {'min': 0.25, 'max': 1.0,
                                             'step': 0.001, 'unit': 'Vpp'}
        else:
            constraints['a_ch_amplitude'] = {'min': 0.5, 'max': 1.0,
                                             'step': 0.001, 'unit': 'Vpp'}
        #checked
        constraints['a_ch_offset'] = {'min': 0.0, 'max': 0.0,
                                      'step': 0.0, 'unit': 'V'}

        #checked
        constraints['d_ch_low'] = {'min': -1.4, 'max': 0.9,
                                   'step': 0.01, 'unit': 'V'}

        #checked
        constraints['d_ch_high'] = {'min': -0.9, 'max': 1.4,
                                      'step': 0.01, 'unit': 'V'}

        #checked
        # for arbitrary waveform generators, this values will be used. The
        # step value corresponds to the waveform granularity.
        if '01' in self.AWG_options:
            constraints['sampled_file_length'] = {'min': 1, 'max': 64.8e6,
                                                  'step': 1, 'unit': 'Samples'}
        else:
            constraints['sampled_file_length'] = {'min': 1, 'max': 32e6,
                                                  'step': 1, 'unit': 'Samples'}

        # if only digital bins can be saved, then their limitation is different
        # compared to a waveform file
        constraints['digital_bin_num'] = {'min': 0, 'max': 0,
                                          'step': 0, 'unit': '#'}

        #checked
        constraints['waveform_num'] = {'min': 1, 'max': 32000,
                                       'step': 1, 'unit': '#'}

        #checked
        constraints['sequence_num'] = {'min': 1, 'max': 16000,
                                       'step': 1, 'unit': '#'}

        #TODO: Check those values: (Cannot find it) => Checked (Alex)
        #      Can be found in the compiled html file under the section 'File and Record Format'
        #      or search for 'subsequences'. The number here should be alright.
        constraints['subsequence_num'] = {'min': 1, 'max': 8000,
                                          'step': 1, 'unit': '#'}

        # If sequencer mode is enable than sequence_param should be not just an
        # empty dictionary. Insert here in the same fashion like above the parameters, which the
        # device is needing for a creating sequences:
        sequence_param = OrderedDict()
        sequence_param['repetitions'] = {'min': 0, 'max': 65536, 'step': 1, 'unit': '#'}
        sequence_param['trigger_wait'] = {'min': False, 'max': True, 'step': 1,
                                          'unit': 'bool'}
        sequence_param['event_jump_to'] = {'min': -1, 'max': 8000, 'step': 1,
                                           'unit': 'row'}
        sequence_param['go_to'] = {'min': 0, 'max': 8000, 'step': 1,
                                   'unit': 'row'}
        constraints['sequence_param'] = sequence_param

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names
        # for the different configurations can be customary chosen.

        activation_config = OrderedDict()
        activation_config['All'] = ['a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3', 'd_ch4']
        # Usage of channel 1 only:
        activation_config['A1_M1_M2'] = ['a_ch1', 'd_ch1', 'd_ch2']
        # Usage of channel 2 only:
        activation_config['A2_M3_M4'] = ['a_ch2', 'd_ch3', 'd_ch4']
        # Usage of Interleave configuration with digital channels:
        activation_config['Interleave_M1_M2'] = ['a_ch1', 'd_ch1', 'd_ch2']
        # Usage of Interleave configuration only:
        activation_config['Interleave_only'] = ['a_ch1']
        # usage of two analog channels only:
        activation_config['Two_Analog'] = ['a_ch1', 'a_ch2']
        # Usage of one analog channel without digital channel
        activation_config['Analog1'] = ['a_ch1']
        # Usage of one analog channel without digital channel
        activation_config['Analog2'] = ['a_ch2']

        constraints['activation_config'] = activation_config

        return constraints


    def _get_sample_rate_constraints(self):
        """ If sample rate changes during Interleave mode, then it has to be
            adjusted for that state.

        @return dict: with keys 'min', 'max':, 'step' and 'unit' and the
                      assigned values for that keys.
        """
        #checked
        if self.interleave:
            return {'min': 12.0e9, 'max': 24.0e9,
                    'step': 8, 'unit': 'Samples/s'}
        else:
            return {'min': 10.0e6, 'max': 12.0e9,
                    'step': 4, 'unit': 'Samples/s'}

    # works!
    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.tell('AWGC:RUN\n')

        return self.get_status()[0]

    # works!
    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        self.tell('AWGC:STOP\n')

        return self.get_status()[0]

    # TODO: works, but is this hardcoded ch2 really a good idea?
    # Todo: The generation of a wfm has to be done before!
    # Fixme: If interleave only use first channel - works anyways because ch2 is ignored in interleave.

    def upload_asset(self, asset_name=None):
        """ Upload an already hardware conform file to the device.
        Does NOT load into channels.

        @param: str asset_name: The name of the asset to be uploaded to the AWG

        @return int: error code (0:OK, -1:error)
        """

        if asset_name is None:
            self.log.warning('No asset name provided for upload!\nCorrect '
                    'that!\nCommand will be ignored.')
            return -1

        # at first delete all the name, which might lead to confusions in the
        # upload procedure:
        self.delete_asset(asset_name)

        # create list of filenames to be uploaded
        upload_names = []
        filelist = os.listdir(self.host_waveform_directory)
        for filename in filelist:
            is_wfm = filename.endswith('.wfm')
            if is_wfm and (asset_name + '_ch') in filename:
                upload_names.append(filename)
            if (asset_name + '.seq') in filename:
                upload_names.append(filename)

        # upload files
        for name in upload_names:
            self._send_file(name)
        return 0

    # TODO: test
    def _send_file(self, filename):
        """ Sends an already hardware specific waveform file to the pulse
            generators waveform directory.

        @param string filename: The file name of the source file

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """

        filepath = os.path.join(self.host_waveform_directory, filename)

        with FTP(self.ip_address) as ftp:
            ftp.login() # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.asset_directory)
            with open(filepath, 'rb') as uploaded_file:
                ftp.storbinary('STOR '+filename, uploaded_file)
        pass

    #TODO: That should actually 'just' load the channels into the AWG and not upload to the device.
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
        path = self.ftp_path + self.get_asset_dir_on_device()

        # Find all files associated with the specified asset name
        file_list = self._get_filenames_on_device()
        filename = []

        if (asset_name + '.seq') in file_list:
            file_name = asset_name + '.seq'

            # self.tell('MMEMORY:IMPORT "{0}","{1}",SEQ \n'.format(asset_name , asset_name + '.seq'))
            self.tell('SOUR1:FUNC:USER "%s/%s"\n' % (path, file_name))
            # self.tell('SOUR1:FUNC:USER "{0}/{1}"\n'.format(path, file_name))
            # set the AWG to the event jump mode:
            self.tell('AWGCONTROL:EVENT:JMODE EJUMP')

            self.current_loaded_asset = asset_name
        else:

            for file in file_list:

                if file == asset_name + '_ch1.wfm':
                    #load into workspace
                    self.tell('MMEMORY:IMPORT "{0}","{1}",WFM \n'.format(asset_name +'_ch1', asset_name + '_ch1.wfm'))
                    #load into channel
                    self.tell('SOUR1:WAVEFORM "{0}"\n'.format(asset_name + '_ch1'))
                    print("Ch1 loaded",asset_name)
                    filename.append(file)
                elif file == asset_name + '_ch2.wfm':
                    self.tell('MMEMORY:IMPORT "{0}","{1}",WFM \n'.format(asset_name + '_ch2', asset_name + '_ch2.wfm'))
                    self.tell('SOUR2:WAVEFORM "{0}"\n'.format(asset_name + '_ch2'))
                    print("Ch2 loaded",asset_name)
                    filename.append(file)

            if load_dict == {} and filename == []:
                self.log.warning('No file and channel provided for load!\n'
                        'Correct that!\nCommand will be ignored.')

        for channel_num in list(load_dict):
            print("in load dict")
            #asset_name = str(load_dict[channel_num])
            #self.tell('MMEMORY:IMPORT "{0}","{1}",WFM \n'.format(asset_name + '_ch{0}'.format(int(channel_num)), asset_name + '_ch{0}.wfm'.format(int(channel_num))))
            #self.tell('SOUR1:WAVEFORM "{0}"\n'.format(asset_name + '_ch{0}'.format(int(channel_num))))

        #if len(list(load_dict)) > 0:
        self.current_loaded_asset = asset_name

        return 0



        # file_list = self._get_filenames_on_device()
        # filename = []
        #
        # for file in file_list:
        #     if file == asset_name+'_ch1.wfm' or file == asset_name+'_ch2.wfm':
        #         filename.append(file)
        #
        #
        # # Check if something could be found
        # if len(filename) == 0:
        #     self.log.error('No files associated with asset {0} were found on AWG7122c.'
        #                 'Load to channels failed!'.format(asset_name)
        #                 )        #         if asset.split("_")[-1][:3] == 'ch1':
        #             self.tell('SOUR1:WAVEFORM "{0}"\n'.format(asset[:-4]))
        #         if asset.split("_")[-1][:3] == 'ch2':
        #             self.tell('SOUR2:WAVEFORM "{0}"\n'.format(asset[:-4]))
        #         self.current_loaded_asset = asset_name
        # else:
        #     for channel in load_dict:
        #     return -1
        #
        # self.log.info('The following files associated with the asset {0} were found on AWG7122c:\n'
        #             '"{1}"'.format(asset_name, filename))
        #
        # # load files in AWG Waveform list
        # for asset in filename:
        #     if asset.endswith('.wfm'):
        #         self.tell('MMEMORY:IMPORT "{0}","{1}",WFM \n'.format(asset[:-4], asset))
        #     else:
        #         self.log.error('Could not load asset {0} to AWG7122c:\n'
        #             '"{1}"'.format(asset_name, filename))
        #
        # file_path = self.ftp_path + self.get_asset_dir_on_device()
        # # simply use the channel association of the filenames if no load_dict is given
        # if load_dict == {}:
        #     for asset in filename:
        #         # load waveforms into channels as given in filename

        #         # load waveforms into channels
        #         name = load_dict[channel]
        #         self.tell('SOUR'+str(channel)+':FUNC:USER "{0}/{1}"\n'.format(file_path, name))
        #     self.current_loaded_asset = name
        #
        # return 0

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


        self.tell('WLIST:WAVEFORM:DELETE ALL\n')
        self.current_loaded_asset = None
        return

    # works!
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
        # the possible status of the AWG have the following meaning:
        status_dic[-1] = 'Failed Request or Communication with device.'
        status_dic[0] = 'Instrument has stopped.'
        status_dic[1] = 'Instrument is running.'
        status_dic[2] = 'Instrument is waiting for trigger.'

        # save the status dictionary is a class variable for later access.
        self.status_dic = status_dic

        # Keep in mind that the received integer number for the running status
        # is 2 for this specific AWG5000 series device. Therefore a received
        # message of 2 should be converted to a integer status variable of 1:

        try:
            message = int(self.ask('AWGC:RSTate?\n'))
        except:
            # if nothing comes back than the output should be marked as error
            return -1

        if message == 2:
            return (1, status_dic)
        elif message == 1:
            return (2, status_dic)
        else:
            return (message, status_dic)

    # works!
    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware

        @param float sample_rate: The sample rate to be set (in Hz)

        @return foat: the sample rate returned from the device (-1:error)
        """

        self.tell('SOURCE1:FREQUENCY {0:.4G}MHz\n'.format(sample_rate / 1e6))

        # Here we need to wait, because when the sampling rate is changed AWG is busy
        # and therefore the ask in get_sample_rate will return an empty string.
        time.sleep(0.3)
        return self.get_sample_rate()

    # works!
    def get_sample_rate(self):
        """ Set the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """

        self.sample_rate = float(self.ask('SOURCE1:FREQUENCY?\n'))
        return self.sample_rate


    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if a specific amplitude value (in Volt
                               peak to peak, i.e. the full amplitude) of a
                               channel is desired.
        @param list offset: optional, if a specific high value (in Volt) of a
                            channel is desired.

        @return: ({}, {}): tuple of two dicts, with keys being the channel
                           number and items being the values for those channels.
                           Amplitude is always denoted in Volt-peak-to-peak and
                           Offset in (absolute) Voltage.

        If no entries provided then the levels of all channels where simply
        returned. If no analog channels provided, return just an empty dict.
        Example of a possible input:
            amplitude = [1,4], offset =[1,3]
        to obtain the amplitude of channel 1 and 4 and the offset
            {1: -0.5, 4: 2.0} {}
        since no high request was performed.

        Note, the major difference to digital signals is that analog signals are
        always oscillating or changing signals, otherwise you can use just
        digital output. In contrast to digital output levels, analog output
        levels are defined by an amplitude (here total signal span, denoted in
        Voltage peak to peak) and an offset (denoted by an (absolute) voltage).
        """
        if amplitude is None:
            amplitude = []
        if offset is None:
            offset = []

        amp = {}
        off = {}
        constraints = self.get_constraints()

        if (amplitude == []) and (offset == []):

            # since the available channels are not going to change for this
            # device you are asking directly:
            amp['a_ch1'] = float(self.ask('SOURCE1:VOLTAGE:AMPLITUDE?'))
            amp['a_ch2'] = float(self.ask('SOURCE2:VOLTAGE:AMPLITUDE?'))

            if '02' in self.AWG_options or '06' in self.AWG_options:
                #In option 2 and 6 this can not be set
                off['a_ch1'] = float(0.0)
                off['a_ch2'] = float(0.0)
            else:
                off['a_ch1'] = float(self.ask('SOURCE1:VOLTAGE:OFFSET?'))
                off['a_ch2'] = float(self.ask('SOURCE2:VOLTAGE:OFFSET?'))

        else:

            #FIXME: include the check for interleave channel and obtain also for
            #       that channel the proper amplitude and offset
            #       Remember channelnumbers were defined like
            #           Interleave = 1
            #           ACH1       = 2
            #           ACH2       = 3
            #       for analog channels.
            for a_ch in amplitude:
                if (a_ch <= self._get_num_a_ch()) and \
                   (a_ch >= 0):
                    amp[a_ch] = float(self.ask('SOURCE{0}:VOLTAGE:AMPLITUDE?'.format(a_ch)))
                else:
                    self.log.warning('The device does not have that much '
                            'analog channels! A channel number "{0}" was '
                            'passed, but only "{1}" channels are available!\n'
                            'Command will be ignored.'.format(
                                a_ch, self._get_num_a_ch()))

            for a_ch in offset:
                if (a_ch <= self._get_num_a_ch()) and \
                   (a_ch >= 0):
                    off[a_ch] = float(self.ask('SOURCE{0}:VOLTAGE:OFFSET?'.format(a_ch)))
                else:
                    self.log.warning('The device does not have that much '
                            'analog channels! A channel number "{0}" was '
                            'passed, but only "{1}" channels are available!\n'
                            'Command will be ignored.'.format(
                                a_ch, self._get_num_a_ch()))

        return amp, off


    def set_analog_level(self, amplitude=None, offset=None):
        """ Set amplitude and/or offset value of the provided analog channel.

        @param dict amplitude: dictionary, with key being the channel and items
                               being the amplitude values (in Volt peak to peak,
                               i.e. the full amplitude) for the desired channel.
        @param dict offset: dictionary, with key being the channel and items
                            being the offset values (in absolute volt) for the
                            desired channel.

        If nothing is passed then the command is being ignored.

        Note, the major difference to digital signals is that analog signals are
        always oscillating or changing signals, otherwise you can use just
        digital output. In contrast to digital output levels, analog output
        levels are defined by an amplitude (here total signal span, denoted in
        Voltage peak to peak) and an offset (denoted by an (absolute) voltage).

        In general there is not a bijective correspondence between
        (amplitude, offset) for analog and (value high, value low) for digital!
        """
        if amplitude is None:
            amplitude = {}
        if offset is None:
            offset = {}

        constraints = self.get_constraints()

        #FIXME: include the check for interleave channel and obtain also for
        #       that channel the proper amplitude and offset
        #       Remember channelnumbers were defined like
        #           Interleave = 1
        #           ACH1       = 2
        #           ACH2       = 3
        #       for analog channels.

        for a_ch in amplitude:
            if (a_ch <= self._get_num_a_ch()) and \
               (a_ch >= 0):

                if amplitude[a_ch] < constraints['a_ch_amplitude']['min'] or \
                   amplitude[a_ch] > constraints['a_ch_amplitude']['max']:

                    self.log.warning('Not possible to set for analog channel '
                            '{0} the amplitude value {1}Vpp, since it is not '
                            'within the interval [{2},{3}]! Command will '
                            'be ignored.'.format(
                                a_ch,
                                amplitude[a_ch],
                                constraints['a_ch_amplitude']['min'],
                                constraints['a_ch_amplitude']['max']))
                else:

                    self.tell('SOURCE{0}:VOLTAGE:AMPLITUDE {1}'.format(a_ch,
                                                                       amplitude[a_ch]))


            else:
                self.log.warning('The device does not support that much '
                        'analog channels! A channel number "{0}" was passed, '
                        'but only "{1}" channels are available!\n'
                        'Command will be ignored.'.format(
                            a_ch,
                            self._get_num_a_ch()))

        for a_ch in offset:
            if (a_ch <= self._get_num_a_ch()) and \
               (a_ch >= 0):

                if offset[a_ch] < constraints['a_ch_offset']['min'] or \
                   offset[a_ch] > constraints['a_ch_offset']['max']:

                    self.log.warning('Not possible to set for analog channel '
                            '{0} the offset value {1}V, since it is not '
                            'within the interval [{2},{3}]! Command will '
                            'be ignored.'.format(
                                a_ch,
                                offset[a_ch],
                                constraints['a_ch_offset']['min'],
                                constraints['a_ch_offset']['max']))
                else:
                    self.tell('SOURCE{0}:VOLTAGE:OFFSET {1}'.format(a_ch,
                                                                    offset[a_ch]))

            else:
                self.log.warning('The device does not support that much '
                        'analog channels! A channel number "{0}" was passed, '
                        'but only "{1}" channels are available!\n'
                        'Command will be ignored.'.format(
                            a_ch,
                            self._get_num_a_ch()))

        return self.get_analog_level(amplitude=list(amplitude), offset=list(offset))

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
        if low is None:
            low = []
        if high is None:
            high = []

        low_val = {}
        high_val = {}

        constraints = self.get_constraints()

        if (low == []) and (high == []):

            low_val[1] =  float(self.ask('SOURCE1:MARKER1:VOLTAGE:LOW?'))
            high_val[1] = float(self.ask('SOURCE1:MARKER1:VOLTAGE:HIGH?'))
            low_val[2] =  float(self.ask('SOURCE1:MARKER2:VOLTAGE:LOW?'))
            high_val[2] = float(self.ask('SOURCE1:MARKER2:VOLTAGE:HIGH?'))
            low_val[3] =  float(self.ask('SOURCE2:MARKER1:VOLTAGE:LOW?'))
            high_val[3] = float(self.ask('SOURCE2:MARKER1:VOLTAGE:HIGH?'))
            low_val[4] =  float(self.ask('SOURCE2:MARKER2:VOLTAGE:LOW?'))
            high_val[4] = float(self.ask('SOURCE2:MARKER2:VOLTAGE:HIGH?'))

        else:

            for d_ch in low:
                if (d_ch <= self._get_num_d_ch()) and \
                   (d_ch >= 0):

                    # a fast way to map from a channel list [1, 2, 3, 4] to  a
                    # list like [[1,2], [1,2]]:
                    if (d_ch-2) <= 0:
                        # the conversion to integer is just for safety.
                        low_val[d_ch] = float(self.ask('SOURCE1:MARKER{0}:VOLTAGE:LOW?'.format(int(d_ch))))

                    else:
                        low_val[d_ch] = float(self.ask('SOURCE2:MARKER{0}:VOLTAGE:LOW?'.format(int(d_ch-2))))
                else:
                    self.log.warning('The device does not have that much '
                            'digital channels! A channel number "{0}" was '
                            'passed, but only "{1}" channels are available!\n'
                            'Command will be ignored.'.format(
                                d_ch, self._get_num_d_ch()))

            for d_ch in high:

                if (d_ch <= self._get_num_d_ch()) and \
                   (d_ch >= 0):

                    # a fast way to map from a channel list [1, 2, 3, 4] to  a
                    # list like [[1,2], [1,2]]:
                    if (d_ch-2) <= 0:
                        # the conversion to integer is just for safety.
                        high_val[d_ch] = float(self.ask('SOURCE1:MARKER{0}:VOLTAGE:HIGH?'.format(int(d_ch))))

                    else:
                        high_val[d_ch] = float(self.ask('SOURCE2:MARKER{0}:VOLTAGE:HIGH?'.format(int(d_ch-2))))
                else:
                    self.log.warning('The device does not have that much '
                            'digital channels! A channel number "{0}" was '
                            'passed, but only "{1}" channels are available!\n'
                            'Command will be ignored.'.format(
                                d_ch,
                                self._get_num_d_ch()))

        return low_val, high_val

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

        if ch == []:
            #FIXME: check the output of the interleave
            active_ch['a_ch1'] = True
            # because 0 = False and 1 = True
            active_ch['a_ch2'] = bool(int(self.ask('OUTPUT1:STATE?')))
            active_ch['a_ch3'] = bool(int(self.ask('OUTPUT2:STATE?')))

            # For the AWG5000 series, the resolution of the DAC for the analog
            # channel is fixed to 14bit. Therefore the digital channels are
            # always active and cannot be deactivated. For other AWG devices the
            # command
            #   self.ask('SOURCE1:DAC:RESOLUTION?'))
            # might be useful from which the active digital channels can be
            # obtained.
            active_ch['d_ch1'] = False
            active_ch['d_ch2'] = False
            active_ch['d_ch3'] = False
            active_ch['d_ch4'] = False



        else:
            for channel in ch:

                if 'a_ch' in channel:

                    ana_chan = int(channel[4:])

                    if (ana_chan <= self._get_num_a_ch()) and \
                            (ana_chan >= 0):

                        # because 0 = False and 1 = True

                        if ana_chan == 1:

                            #FIXME: check for interleave output turned on
                            active_ch[channel] = bool(int(self.ask('OUTPUT{0}:STATE?'.format(ana_chan))))

                        else:

                            active_ch[channel] = bool(int(self.ask('OUTPUT{0}:STATE?'.format(ana_chan-1))))

                    else:
                        self.log.warning('The device does not support that '
                                'many analog channels! A channel number '
                                '"{0}" was passed, but only "{1}" channels '
                                'are available!\n'
                                'Command will be ignored.'.format(
                                    ana_chan,
                                    self._get_num_a_ch()))
                elif 'd_ch' in channel:

                    digi_chan = int(channel[4:])

                    if (digi_chan <= self._get_num_d_ch()) and \
                            (digi_chan >= 0):

                        active_ch[channel] = False



                    else:
                        self.log.warning('The device does not support that '
                                'many digital channels! A channel number '
                                '"{0}" was passed, but only "{1}" channels '
                                'are available!\n'
                                'Command will be ignored.'.format(
                                    digi_chan,
                                    self._get_num_d_ch()))

        return active_ch

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

        AWG5000 Series instruments support only 14-bit resolution. Therefore
        this command will have no effect on the DAC for these instruments. On
        other devices the deactivation of digital channels increase the DAC
        resolution of the analog channels.
        """
        if ch is None:
            ch = {}

        for channel in ch:

            chan = int(channel[4:])

            if 'a_ch' in channel:

                if (chan <= self._get_num_a_ch()) and \
                        (chan >= 0):

                    if ch[channel]:
                        state = 'ON'
                    else:
                        state = 'OFF'

                    #FIXME: make a proper check for interleave channel
                    if chan == 1:
                        self.tell('OUTPUT{0}:STATE {1}'.format(chan, state))
                    else:
                        self.tell('OUTPUT{0}:STATE {1}'.format(chan-1, state))
            else:

                # self.log.warning('The device does not support that much analog '
                #             'channels! A channel number "{0}" was passed, but '
                #             'only "{1}" channels are available!\nCommand will '
                #             'be ignored.'.format(chan,
                #                                  self._get_num_a_ch())
                #             )

                # adjust the DAC resolution accordingly
                # if ch[channel]:
                #     self.tell('SOURCE1:DAC:RESOLUTION ' + str(10 - chan) + '\n')
                #     self.tell('SOURCE2:DAC:RESOLUTION ' + str(10 - chan) + '\n')
                if ch[channel]:
                    state = 'ON'
                else:
                    state = 'OFF'

                if chan == 1:
                    self.tell('OUTPUT{0}:STATE {1}'.format(chan, state))
                else:
                    self.tell('OUTPUT{0}:STATE {1}'.format(chan - 1, state))

        # if d_ch != {}:
        #     self.log.info('Digital Channel of the AWG5000 series will always be '
        #                 'active. This configuration cannot be changed.'
        #                 )

        return self.get_active_channels(ch=list(ch))


    def get_uploaded_asset_names(self):
        """ Retrieve the names of all uploaded assets on the device.

        @return list: List of all uploaded asset name strings in the current
                      device directory. This is no list of the file names.

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        uploaded_files = self._get_filenames_on_device()
        name_list = []
        for filename in uploaded_files:
            if fnmatch(filename, '*_ch?.wfm'):
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
            if fnmatch(filename, '*_ch?.wfm'):
                asset_name = filename.rsplit('_', 1)[0]
                if asset_name not in saved_assets:
                    saved_assets.append(asset_name)
        return saved_assets


    def delete_asset(self, asset_name):
        """ Delete all files associated with an asset with the passed asset_name from the device memory.

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
                if fnmatch(filename, name+'_ch?.wfm'):
                    files_to_delete.append(filename)
                elif fnmatch(filename, name+'.seq'):
                    files_to_delete.append(filename)

        # delete files
        with FTP(self.ip_address) as ftp:
            ftp.login() # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.asset_directory)
            for filename in files_to_delete:
                ftp.delete(filename)

        # clear the AWG if the deleted asset is the currently loaded asset
        # if self.current_loaded_asset == asset_name:
        #     self.clear_all()
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
            ftp.login() # login as default user anonymous, passwd anonymous@

            try:
                ftp.cwd(dir_path)
            except:
                self.log.info('Desired directory {0} not found on AWG device.\n'
                        'Create new.'.format(dir_path))
                ftp.mkd(dir_path)

        self.asset_directory = dir_path
        return 0

    def get_asset_dir_on_device(self):
        """ Ask for the directory where the assets are stored on the device.

        @return string: The current sequence directory

        Unused for digital pulse generators without changeable file structure
        (PulseBlaster, FPGA).
        """

        return self.asset_directory

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        return self.sequence_mode

    #works!
    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)
        @return bool state: State of interleave by using get_interleave()

        """

        if state == False:
            self.tell('AWGControl:INTerleave:STAT 0\n')
        elif state == True:
            self.tell('AWGControl:INTerleave:STAT 1\n')
        else:
            self.log.warning('Interleave mode cannot be set to desired '
                    'state!')

        return self.get_interleave()

    # todo: should there also be a class variable which keeps track of this?
    def get_interleave(self):
        """ Check whether Interleave is on in AWG.

        @return bool: True if Interleave is turned on and False if interleave is off,
                      None if non of both
        """

        interleave_val = self.ask('AWGControl:INTerleave:STAT?\n')
        # TODO: change constraints to allowed values depending on mode

        if interleave_val == '1':
            self.interleave=True
            return True
        elif interleave_val == '0':
            self.interleave=False
            return False
        else:
            self.log.warning('State of interleave mode neither 1 nor 0. '
                    'Returning false.')
            return None

    # works
    def tell(self, command):
        """Send a command string to the AWG.

        @param command: string containing the command
        @return int: error code (0:OK, -1:error)
        """

        # check whether the return character was placed at the end. Otherwise
        # the communication will stuck:
        if not command.endswith('\n'):
            command += '\n'

        # In Python 3.x the socket send command only accepts byte type arrays
        # and no str
        command = bytes(command, 'UTF-8')
        self.soc.send(command)
        return 0

    # works
    def ask(self, question):
        """ Asks the device a 'question' and receive an answer from it.

        @param string question: string containing the command
        @return string: the answer of the device to the 'question'
        """
        if not question.endswith('\n'):
            question += '\n'

        # In Python 3.x the socket send command only accepts byte type arrays
        #  and no str.
        question = bytes(question, 'UTF-8')
        self.soc.send(question)
        time.sleep(0.3)  # you need to wait until AWG generating an answer.
        # This number was determined experimentally.
        try:
            message = self.soc.recv(self.input_buffer)  # receive an answer
            message = message.decode('UTF-8')  # decode bytes into a python str
        except OSError:
            self.log.error('Most propably timeout was reached during '
                    'querying the AWG7122 Series device with the question:\n'
                    '{0}\n'
                    'The question text must be wrong.'.format(question))
            message = str(-1)

        message = message.replace('\n', '')  # cut away the characters\r and \n.
        message = message.replace('\r', '')

        return message

    # todo:test
    def reset(self):
        """Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.tell('*RST\n')

        return 0

    # =========================================================================
    # Below all the low level routines which are needed for the communication
    # and establishment of a connection.
    # ========================================================================

    def set_lowpass_filter(self, a_ch, cutoff_freq):
        """ Set a lowpass filter to the analog channels of the AWG.

        @param int a_ch: To which channel to apply, either 1 or 2.
        @param cutoff_freq: Cutoff Frequency of the lowpass filter in Hz.
        """
        if a_ch == 1:
            self.tell('OUTPUT1:FILTER:LPASS:FREQUENCY {0:f}MHz\n'.format(cutoff_freq / 1e6))
        elif a_ch == 2:
            self.tell('OUTPUT2:FILTER:LPASS:FREQUENCY {0:f}MHz\n'.format(cutoff_freq / 1e6))

    def set_jump_timing(self, synchronous=False):
        """Sets control of the jump timing in the AWG.

        @param bool synchronous: if True the jump timing will be set to
                                 synchornous, otherwise the jump timing will be
                                 set to asynchronous.

        If the Jump timing is set to asynchornous the jump occurs as quickly as
        possible after an event occurs (e.g. event jump tigger), if set to
        synchornous the jump is made after the current waveform is output. The
        default value is asynchornous.
        """
        if (synchronous):
            self.tell('EVEN:JTIM SYNC\n')
        else:
            self.tell('EVEN:JTIM ASYNC\n')

    def set_mode(self, mode):
        """Change the output mode of the AWG5000 series.

        @param str mode: Options for mode (case-insensitive):
                            continuous - 'C'
                            triggered  - 'T'
                            gated      - 'G'
                            sequence   - 'S'

        """

        look_up = {'C': 'CONT',
                   'T': 'TRIG',
                   'G': 'GAT',
                   'E': 'ENH',
                   'S': 'SEQ'
                   }
        self.tell('AWGC:RMOD %s\n' % look_up[mode.upper()])

    # works
    def get_sequencer_mode(self, output_as_int=False):
        """ Asks the AWG which sequencer mode it is using.

        @param: bool output_as_int: optional boolean variable to set the output
        @return: str or int with the following meaning:
                'HARD' or 0 indicates Hardware Mode
                'SOFT' or 1 indicates Software Mode
                'Error' or -1 indicates a failure of request

        It can be either in Hardware Mode or in Software Mode. The optional
        variable output_as_int sets if the returned value should be either an
        integer number or string.
        """

        message = self.ask('AWGControl:SEQuencer:TYPE?\n')
        if output_as_int == True:
            if 'HARD' in message:
                return 0
            elif 'SOFT' in message:
                return 1
            else:
                return -1
        else:
            if 'HARD' in message:
                return 'Hardware-Sequencer'
            elif 'SOFT' in message:
                return 'Software-Sequencer'
            else:
                return 'Request-Error'

    # =========================================================================
    # Below all the higher level routines are situated which use the
    # wrapped routines as a basis to perform the desired task.
    # =========================================================================

    def _get_dir_for_name(self, name):
        """ Get the path to the pulsed sub-directory 'name'.

        @param name: string, name of the folder
        @return: string, absolute path to the directory with folder 'name'.
        """

        path = os.path.join(self.pulsed_file_dir, name)
        if not os.path.exists(path):
            os.makedirs(os.path.abspath(path))

        return os.path.abspath(path)

    def _get_filenames_on_device(self):
        """ Get the full filenames of all assets saved on the device.

        @return: list, The full filenames of all assets saved on the device.
        """
        filename_list = []
        with FTP(self.ip_address) as ftp:
            ftp.login() # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.asset_directory)
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
                if filename.endswith('.wfm') or filename.endswith('.seq'):
                    if filename not in filename_list:
                        filename_list.append(filename)
        return filename_list

    def _get_filenames_on_host(self):
        """ Get the full filenames of all assets saved on the host PC.

        @return: list, The full filenames of all assets saved on the host PC.
        """
        filename_list = [f for f in os.listdir(self.host_waveform_directory) if f.endswith('.wfm')]
        return filename_list

    def _get_num_a_ch(self):
        """ Retrieve the number of available analog channels.

        @return int: number of analog channels.
        """
        config = self.get_constraints()['activation_config']

        all_a_ch = []
        for conf in config:

            # extract all analog channels from the config
            curr_a_ch = [entry for entry in config[conf] if 'a_ch' in entry]

            # append all new analog channels to a temporary array
            for a_ch in curr_a_ch:
                if a_ch not in all_a_ch:
                    all_a_ch.append(a_ch)

        # count the number of entries in that array
        return len(all_a_ch)

    def _get_num_d_ch(self):
        """ Retrieve the number of available digital channels.

        @return int: number of digital channels.
        """
        config = self.get_constraints()['activation_config']

        all_d_ch = []
        for conf in config:

            # extract all digital channels from the config
            curr_d_ch = [entry for entry in config[conf] if 'd_ch' in entry]

            # append all new analog channels to a temporary array
            for d_ch in curr_d_ch:
                if d_ch not in all_d_ch:
                    all_d_ch.append(d_ch)

        # count the number of entries in that array
        return len(all_d_ch)
