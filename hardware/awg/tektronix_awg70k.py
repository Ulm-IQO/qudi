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

import os
import time
import re
from socket import socket, AF_INET, SOCK_STREAM
from ftplib import FTP
from collections import OrderedDict
from fnmatch import fnmatch

from core.base import Base
from interface.pulser_interface import PulserInterface

class AWG70K(Base, PulserInterface):
    """

    """
    _modclass = 'awg70k'
    _modtype = 'hardware'

    # declare connectors
    _out = {'pulser': 'PulserInterface'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        if 'awg_IP_address' in config.keys():
            self.ip_address = config['awg_IP_address']
        else:
            self.log.error('This is AWG: Did not find >>awg_IP_address<< in '
                         'configuration.')

        if 'awg_port' in config.keys():
            self.port = config['awg_port']
        else:
            self.log.error('This is AWG: Did not find >>awg_port<< in '
                         'configuration.')

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
            self.log.warning('No parameter "pulsed_file_dir" was specified in '
                    'the config for SequenceGeneratorLogic as directory for '
                    'the pulsed files!\nThe default home directory\n{0}\n'
                    'will be taken instead.'.format(self.pulsed_file_dir))

        if 'ftp_root_dir' in config.keys():
            self.ftp_root_directory = config['ftp_root_dir']
        else:
            self.ftp_root_directory = 'C:\\inetpub\\ftproot'
            self.log.warning('No parameter "ftp_root_dir" was specified in '
                    'the config for tektronix_awg70k as directory for '
                    'the FTP server root on the AWG!\nThe default root '
                    'directory\n{0}\nwill be taken instead.'.format(
                        self.ftp_root_directory))

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')

        self.user = 'anonymous'
        self.passwd = 'anonymous@'
        if 'ftp_login' in config.keys() and 'ftp_passwd' in config.keys():
            self.user = config['ftp_login']
            self.passwd = config['ftp_passwd']


    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        # connect ethernet socket and FTP
        self.soc = socket(AF_INET, SOCK_STREAM)
        self.soc.settimeout(7)
        try:
            self.soc.connect((self.ip_address, self.port))
        except socket.timeout:
            self.log.error("couldn't establish a socket connection within 7 seconds.")
        self.log.warning(self.ip_address)

        # input buffer
        self.input_buffer = int(2 * 1024)

        self.asset_directory = 'waves'

        self.ftp = FTP(self.ip_address)
        self.ftp.login(user=self.user, passwd=self.passwd)
        self.ftp.cwd(self.asset_directory)

        self.connected = True

        self.awg_model = self._get_model_ID()[1]
        self.log.info('Found the following model: %s', self.awg_model)

        self.sample_rate = self.get_sample_rate()
        self.amplitude_list, self.offset_list = self.get_analog_level()
        self.markers_low, self.markers_high = self.get_digital_level()

        self.is_output_enabled = self._is_output_on()
        self.use_sequencer = self.has_sequence_mode()

        self.active_channel = self.get_active_channels()

        self.interleave = self.get_interleave()

        self.current_loaded_asset = None
        self._init_loaded_asset()

        self.current_status = 0

    def on_deactivate(self, e):
        """ Required tasks to be performed during deactivation of the module.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in method activation.
        """

        # Closes the connection to the AWG via ftp and the socket
        self.tell('\n')
        self.soc.close()
        self.ftp.close()

        self.connected = False
        pass

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
        constraints = dict()
        # if interleave option is available, then sample rate constraints must be assigned to the
        # output of a function called _get_sample_rate_constraints() which outputs the shown
        # dictionary with the correct values depending on the present mode. The the GUI will have
        # to check again the limitations if interleave was selected.
        if self.awg_model == 'AWG70002A':
            constraints['sample_rate'] = {'min': 1.5e3, 'max': 25.0e9, 'step': 1,
                                          'unit': 'Samples/s'}
        elif self.awg_model == 'AWG70001A':
            constraints['sample_rate'] = {'min': 1.5e3, 'max': 50.0e9, 'step': 1,
                                          'unit': 'Samples/s'}

        # The file formats are hardware specific. The sequence_generator_logic will need this
        # information to choose the proper output format for waveform and sequence files.
        constraints['waveform_format'] = 'wfmx'
        constraints['sequence_format'] = 'seqx'

        # the stepsize will be determined by the DAC in combination with the
        # maximal output amplitude (in Vpp):
        constraints['a_ch_amplitude'] = {'min': 0.25, 'max': 0.5, 'step': 0.001, 'unit': 'Vpp'}
        # FIXME: additional constraints
        constraints['dac_resolution'] = {'min': 8, 'max': 10, 'step': 1, 'unit': 'bit'}
        #FIXME: Enter the proper offset constraints:
        constraints['a_ch_offset'] = {'min': 0.0, 'max': 0.0, 'step': 0.0, 'unit': 'V'}
        #FIXME: Enter the proper digital channel low constraints:
        constraints['d_ch_low'] = {'min': 0.0, 'max': 0.0, 'step': 0.0, 'unit': 'V'}
        #FIXME: Enter the proper digital channel high constraints:
        constraints['d_ch_high'] = {'min': 0.0, 'max': 0.0, 'step': 0.0, 'unit': 'V'}
        # for arbitrary waveform generators, this values will be used. The step value corresponds
        # to the waveform granularity.
        constraints['sampled_file_length'] = {'min': 1, 'max': 8e9, 'step': 1, 'unit': 'Samples'}
        # if only digital bins can be saved, then their limitation is different compared to a
        # waveform file
        constraints['digital_bin_num'] = {'min': 0, 'max': 0, 'step': 0, 'unit': '#'}
        #FIXME: Check the proper number for your device
        constraints['waveform_num'] = {'min': 1, 'max': 32000, 'step': 1, 'unit': '#'}
        #FIXME: Check the proper number for your device
        constraints['sequence_num'] = {'min': 1, 'max': 4000, 'step': 1, 'unit': '#'}
        #FIXME: Check the proper number for your device
        constraints['subsequence_num'] = {'min': 1, 'max': 8000, 'step': 1, 'unit': '#'}

        # If sequencer mode is enable than sequence_param should be not just an empty dictionary.
        # Insert here in the same fashion like above the parameters, which the device is needing
        # for a creating sequences:
        sequence_param = OrderedDict()
        constraints['sequence_param'] = sequence_param

        # the name a_ch<num> and d_ch<num> are generic names, which describe UNAMBIGUOUSLY the
        # channels. Here all possible channel configurations are stated, where only the generic
        # names should be used. The names for the different configurations can be customary chosen.
        activation_config = OrderedDict()

        if self.awg_model == 'AWG70002A':
            activation_config['all'] = ['a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3', 'd_ch4']
            # Usage of both channels but reduced markers (higher analog resolution)
            activation_config['ch1_2mrk_ch2_1mrk'] = ['a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3']
            activation_config['ch1_2mrk_ch2_0mrk'] = ['a_ch1', 'd_ch1', 'd_ch2', 'a_ch2']
            activation_config['ch1_1mrk_ch2_2mrk'] = ['a_ch1', 'd_ch1', 'a_ch2', 'd_ch3', 'd_ch4']
            activation_config['ch1_0mrk_ch2_2mrk'] = ['a_ch1', 'a_ch2', 'd_ch3', 'd_ch4']
            activation_config['ch1_1mrk_ch2_1mrk'] = ['a_ch1', 'd_ch1', 'a_ch2', 'd_ch3']
            activation_config['ch1_0mrk_ch2_1mrk'] = ['a_ch1', 'a_ch2', 'd_ch3']
            activation_config['ch1_1mrk_ch2_0mrk'] = ['a_ch1', 'd_ch1', 'a_ch2']
            # Usage of channel 1 only:
            activation_config['ch1_2mrk'] = ['a_ch1', 'd_ch1', 'd_ch2']
            # Usage of channel 2 only:
            activation_config['ch2_2mrk'] = ['a_ch2', 'd_ch3', 'd_ch4']
            # Usage of only channel 1 with one marker:
            activation_config['ch1_1mrk'] = ['a_ch1', 'd_ch1']
            # Usage of only channel 2 with one marker:
            activation_config['ch2_1mrk'] = ['a_ch2', 'd_ch3']
            # Usage of only channel 1 with no marker:
            activation_config['ch1_0mrk'] = ['a_ch1']
            # Usage of only channel 2 with no marker:
            activation_config['ch2_0mrk'] = ['a_ch2']
        elif self.awg_model == 'AWG70001A':
            activation_config['all'] = ['a_ch1', 'd_ch1', 'd_ch2']
            # Usage of only channel 1 with one marker:
            activation_config['ch1_1mrk'] = ['a_ch1', 'd_ch1']
            # Usage of only channel 1 with no marker:
            activation_config['ch1_0mrk'] = ['a_ch1']

        constraints['activation_config'] = activation_config
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.tell('AWGC:RUN\n')
        # wait until the AWG is actually running
        while int(self.ask('AWGC:RST?')) == 0:
            time.sleep(1)
        self.current_status = 1
        self.is_output_enabled = True
        return 0

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.tell('AWGC:STOP\n')
        # wait until the AWG has actually stopped
        while int(self.ask('AWGC:RST?')) != 0:
            time.sleep(1)
        self.current_status = 0
        self.is_output_enabled = False
        return 0

    def upload_asset(self, asset_name=None):
        """ Upload an already hardware conform file to the device.
            Does NOT load it into channels.

        @param str name: name of the ensemble/sequence to be uploaded

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

        filelist = self._get_filenames_on_host()
        upload_names = []
        for filename in filelist:
            is_wfmx = filename.endswith('.wfmx')
            is_mat = filename.endswith(asset_name+'.mat')
            if is_wfmx and (asset_name + '_ch') in filename:
                upload_names.append(filename)
            elif is_mat:
                upload_names.append(filename)
                break
        # Transfer files
        for filename in upload_names:
            self._send_file(filename)
        return 0

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

        # Find all files associated with the specified asset name
        file_list = self._get_filenames_on_device()

        # find all assets with file type .mat and .WFMX and name "asset_name"
        # FIXME: Also include .SEQX later on
        active_analog = [chnl for chnl in list(self.active_channel) if 'a_ch' in chnl and self.active_channel[chnl]]
        filename = []
        for file in file_list:
            if file == asset_name + '.mat':
                filename.append(file)
                break
            else:
                pattern = re.compile('[0-9]+')
                for chnl in active_analog:
                    ch_num = int(re.search(pattern, chnl).group(0))
                    if file == asset_name + '_ch' + str(ch_num) + '.wfmx':
                        filename.append(file)

        # Check if something could be found
        if len(filename) == 0:
            self.log.error('No files associated with asset "{0}" were found on AWG70k. Load to '
                           'channels failed!'.format(asset_name))
            return -1

        # Check if multiple file formats for a single asset_name are present and issue warning
        tmp = filename[0].rsplit('.', 1)[1]
        for name in filename:
            if not name.endswith(tmp):
                self.log.error('Multiple file formats associated with the asset "{0}" were found '
                               'on AWG70k. Load to channels failed!'.format(asset_name))
                return -1

        # Check if the number of found files matches the number of active channels
        if len(active_analog) != len(filename):
            self.log.error('The number of found waveforms ({0}) does not match the number of '
                           'active AWG channels ({1}).'.format(len(filename), len(active_analog)))
            return -1

        self.log.info('The following files associated with the asset "{0}" were found on AWG70k:\n'
                      '{1}'.format(asset_name, filename))

        # load files in AWG workspace
        timeout = self.soc.gettimeout()
        self.soc.settimeout(None)
        for asset in filename:
            file_path = os.path.join(self.ftp_root_directory, self.asset_directory, asset)
            if asset.endswith('.mat'):
                self.tell('MMEM:OPEN:SASS:WAV "%s"\n' % file_path)
            else:
                self.tell('MMEM:OPEN "%s"\n' % file_path)
            self.ask('*OPC?\n')
        self.soc.settimeout(timeout)

        # simply use the channel association of the filenames if no load_dict is given
        if load_dict == {}:
            for asset in filename:
                # load waveforms into channels.
                # Get the channel to upload
                pattern = re.compile('[0-9]+')
                d_channel_num = int(re.search(pattern, asset).group(0))
                # upload channel
                name = asset_name + '_ch' + str(d_channel_num)
                self.tell('SOUR' + str(d_channel_num) + ':CASS:WAV "%s"\n' % name)
        else:
            for key in load_dict:
                asset = load_dict[key]
                if 'a_ch' + str(key) not in active_analog:
                    self.log.error('Channel number {0} is not active in AWG.\n'
                                   'Loading of asset "{1}" failed.'.format(key, asset))
                self.tell('SOUR' + str(key) + ':CASS:WAV "%s"\n' % asset)
        while int(self.ask('*OPC?\n')) != 1:
            time.sleep(1)
        self.current_loaded_asset = asset_name
        return 0

    def get_loaded_asset(self):
        """ Retrieve the currently loaded asset name of the device.

        @return str: Name of the current asset, that can be either a filename
                     a waveform, a sequence ect.
        """
        return self.current_loaded_asset

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
            ftp.login(user=self.user,passwd=self.passwd) # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.asset_directory)
            with open(filepath, 'rb') as uploaded_file:
                ftp.storbinary('STOR '+filename, uploaded_file)
        return 0

    def clear_all(self):
        """ Clears the loaded waveform from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Delete all waveforms and sequences from Hardware memory and clear the
        visual display. Unused for digital pulse generators without sequence
        storage capability (PulseBlaster, FPGA).
        """
        self.tell('WLIS:WAV:DEL ALL\n')
        while int(self.ask('*OPC?\n')) != 1:
            time.sleep(1)
        self.current_loaded_asset = None
        return 0

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

        return self.current_status, status_dic

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware

        @param float sample_rate: The sample rate to be set (in Hz)

        @return foat: the sample rate returned from the device (-1:error)
        """
        self.tell('CLOCK:SRATE %.4G\n' % sample_rate)
        while int(self.ask('*OPC?\n')) != 1:
            time.sleep(1)
        return_rate = float(self.ask('CLOCK:SRATE?\n'))
        self.sample_rate = return_rate
        return return_rate

    def get_sample_rate(self):
        """ Set the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """
        return_rate = float(self.ask('CLOCK:SRATE?\n'))
        self.sample_rate = return_rate
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
        # FIXME: Test with multiple channel AWG
        amp = {}
        off = {}

        chnl_list = ['a_ch' + str(ch_num) for ch_num in range(1, self._get_max_a_channel_number() + 1)]

        pattern = re.compile('[0-9]+')
        # get pp amplitudes
        if amplitude is None:
            for ch_num, chnl in enumerate(chnl_list):
                amp[chnl] = float(self.ask('SOURCE' + str(ch_num + 1) + ':VOLTAGE:AMPLITUDE?'))
        else:
            for chnl in amplitude:
                if chnl in chnl_list:
                    ch_num = int(re.search(pattern, chnl).group(0))
                    amp[chnl] = float(self.ask('SOURCE' + str(ch_num) + ':VOLTAGE:AMPLITUDE?'))
                else:
                    self.log.warning('Get analog amplitude from AWG70k channel "{0}" failed. '
                                     'Channel non-existent.'.format(str(chnl)))

        # get voltage offsets
        if offset is None:
            for ch_num, chnl in enumerate(chnl_list):
                off[chnl] = 0.0
        else:
            for chnl in offset:
                if chnl in chnl_list:
                    ch_num = int(re.search(pattern, chnl).group(0))
                    off[chnl] = 0.0
                else:
                    self.log.warning('Get analog offset from AWG70k channel "{0}" failed. '
                                     'Channel non-existent.'.format(str(chnl)))

        self.amplitude_list = amp
        self.offset_list = off
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
        # Check the inputs by using the constraints...
        constraints = self.get_constraints()
        # ...and the channel numbers
        num_of_channels = self._get_max_a_channel_number()

        # amplitude sanity check
        pattern = re.compile('[0-9]+')
        if amplitude is not None:
            for chnl in amplitude:
                ch_num = int(re.search(pattern, chnl).group(0))
                if ch_num > num_of_channels or ch_num < 1:
                    self.log.warning('Channel to set (a_ch{0}) not available in AWG.\nSetting '
                                     'analogue voltage for this channel ignored.'.format(chnl))
                    del amplitude[chnl]
                if amplitude[chnl] < constraints['a_ch_amplitude']['min']:
                    self.log.warning('Minimum Vpp for channel "{0}" is {1}. Requested Vpp of {2}V '
                                     'was ignored and instead set to min value.'
                                     ''.format(chnl, constraints['a_ch_amplitude']['min'],
                                               amplitude[chnl]))
                    amplitude[chnl] = constraints['a_ch_amplitude']['min']
                elif amplitude[chnl] > constraints['a_ch_amplitude']['max']:
                    self.log.warning('Maximum Vpp for channel "{0}" is {1}. Requested Vpp of {2}V '
                                     'was ignored and instead set to max value.'
                                     ''.format(chnl, constraints['a_ch_amplitude']['max'],
                                               amplitude[chnl]))
                    amplitude[chnl] = constraints['a_ch_amplitude']['max']
        # offset sanity check
        if offset is not None:
            for chnl in offset:
                ch_num = int(re.search(pattern, chnl).group(0))
                if ch_num > num_of_channels or ch_num < 1:
                    self.log.warning('Channel to set (a_ch{0}) not available in AWG.\nSetting '
                                     'offset voltage for this channel ignored.'.format(chnl))
                    del offset[chnl]
                if offset[chnl] < constraints['a_ch_offset']['min']:
                    self.log.warning('Minimum offset for channel "{0}" is {1}. Requested offset of '
                                     '{2}V was ignored and instead set to min value.'
                                     ''.format(chnl, constraints['a_ch_offset']['min'],
                                               offset[chnl]))
                    offset[chnl] = constraints['a_ch_offset']['min']
                elif offset[chnl] > constraints['a_ch_offset']['max']:
                    self.log.warning('Maximum offset for channel "{0}" is {1}. Requested offset of '
                                     '{2}V was ignored and instead set to max value.'
                                     ''.format(chnl, constraints['a_ch_offset']['max'],
                                               offset[chnl]))
                    offset[chnl] = constraints['a_ch_offset']['max']

        if amplitude is not None:
            for a_ch in amplitude:
                self.tell('SOURCE{0}:VOLTAGE:AMPLITUDE {1}'.format(a_ch, amplitude[a_ch]))
                self.amplitude_list[a_ch] = amplitude[a_ch]
            while int(self.ask('*OPC?\n')) != 1:
                time.sleep(1)

        if offset is not None:
            for a_ch in offset:
                self.tell('SOURCE{0}:VOLTAGE:OFFSET {1}'.format(a_ch, offset[a_ch]))
                self.offset_list[a_ch] = offset[a_ch]
            while int(self.ask('*OPC?\n')) != 1:
                time.sleep(1)

        return self.amplitude_list, self.offset_list

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
        # FIXME: Test with multiple channel AWG
        low_val = {}
        high_val = {}

        digital_channels = list(range(1, 2 * self._get_max_a_channel_number() + 1))
        analog_channels = [chnl // 2 + chnl % 2 for chnl in digital_channels]
        marker_indices = [((chnl - 1) % 2) + 1 for chnl in digital_channels]

        # get low marker levels
        if low is None:
            for chnl in digital_channels:
                low_val[chnl] = float(self.ask('SOURCE' + str(analog_channels[chnl-1]) + ':MARKER'
                                               + str(marker_indices[chnl-1]) + ':VOLTAGE:LOW?'))
        else:
            for chnl in low:
                low_val[chnl] = float(self.ask('SOURCE' + str(analog_channels[chnl-1]) + ':MARKER'
                                               + str(marker_indices[chnl-1]) + ':VOLTAGE:LOW?'))

        # get high marker levels
        if high is None:
            for chnl in digital_channels:
                high_val[chnl] = float(self.ask('SOURCE' + str(analog_channels[chnl-1]) + ':MARKER'
                                               + str(marker_indices[chnl-1]) + ':VOLTAGE:HIGH?'))
        else:
            for chnl in high:
                high_val[chnl] = float(self.ask('SOURCE' + str(analog_channels[chnl-1]) + ':MARKER'
                                               + str(marker_indices[chnl-1]) + ':VOLTAGE:HIGH?'))

        self.markers_high = high_val
        self.markers_low = low_val
        return low_val, high_val

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel.

        @param dict low: dictionary, with key being the channel and items being
                         the low values (in volt) for the desired channel.
        @param dict high: dictionary, with key being the channel and items being
                         the high values (in volt) for the desired channel.

        If nothing is passed then the command is being ignored.

        Note, the major difference to analog signals is that digital signals are
        either ON or OFF, whereas analog channels have a varying amplitude
        range. In contrast to analog output levels, digital output levels are
        defined by a voltage, which corresponds to the ON status and a voltage
        which corresponds to the OFF status (both denoted in (absolute) voltage)

        In general there is not a bijective correspondence between
        (amplitude, offset) for analog and (value high, value low) for digital!
        """
        if low is None:
            low = {}
        if high is None:
            high = {}

        #If you want to check the input use the constraints:
        constraints = self.get_constraints()

        for d_ch in low:
            #FIXME: Tell the device the proper digital voltage low value:
            # self.tell('SOURCE1:MARKER{0}:VOLTAGE:LOW {1}'.format(d_ch, low[d_ch]))
            pass

        for d_ch in high:
            #FIXME: Tell the device the proper digital voltage high value:
            # self.tell('SOURCE1:MARKER{0}:VOLTAGE:HIGH {1}'.format(d_ch, high[d_ch]))
            pass

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
        max_analog_channels = self._get_max_a_channel_number()
        active_ch = {}
        for a_ch in range(max_analog_channels):
            active_ch['a_ch' + str(a_ch + 1)] = False
            active_ch['d_ch' + str((2 * a_ch) + 1)] = False
            active_ch['d_ch' + str((2 * a_ch) + 2)] = False

        # check what analog channels are active
        for a_ch in range(1, max_analog_channels + 1):
            if bool(int(self.ask('OUTPUT' + str(a_ch) + ':STATE?\n'))):
                active_ch['a_ch' + str(a_ch)] = True

        # check how many markers are active on each channel, i.e. the DAC resolution
        max_res = constraints['dac_resolution']['max']
        for a_ch in range(self._get_max_a_channel_number()):
            if active_ch['a_ch' + str(a_ch + 1)]:
                digital_mrk = max_res - int(self.ask('SOURCE' + str(a_ch + 1) + ':DAC:RESOLUTION?\n'))
                if digital_mrk == 1:
                    active_ch['d_ch' + str((2 * a_ch) + 1)] = True
                elif digital_mrk == 2:
                    active_ch['d_ch' + str((2 * a_ch) + 2)] = True

        self.active_channel = active_ch
        # return either all channel information or just the one asked for.
        if ch is None:
            return_ch = active_ch
        else:
            return_ch = dict()
            for channel in ch:
                return_ch[channel] = active_ch[channel]
        return return_ch

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

        AWG5000 Series instruments support only 14-bit resolution. Therefore
        this command will have no effect on the DAC for these instruments. On
        other devices the deactivation of digital channels increase the DAC
        resolution of the analog channels.
        """
        if ch is None:
            return {}

        constraints = self.get_constraints()

        new_channels_state = self.active_channel.copy()
        for chnl in ch:
            if chnl in self.active_channel:
                new_channels_state[chnl] = ch[chnl]
            else:
                self.log.error('Trying to (de)activate channel "{0}". This channel is not present '
                               'in AWG. Setting channels aborted.'.format(chnl))
                return {}

        # check if the channels to set are part of the activation_config constraints
        new_active_channels = [chnl for chnl in new_channels_state if new_channels_state[chnl]]
        new_active_channels.sort()
        active_channels_ok = False
        for conf in constraints['activation_config']:
            if sorted(constraints['activation_config'][conf]) == new_active_channels:
                active_channels_ok = True
        if not active_channels_ok:
            self.log.error('activation_config to set ({0}) is not allowed according to constraints.'
                           ''.format(new_active_channels))
            return {}

        # get lists of all digital and analog channels separately
        a_chan = [chnl for chnl in new_channels_state if 'a_ch' in chnl]
        d_chan = [chnl for chnl in new_channels_state if 'd_ch' in chnl]

        # calculate dac resolution for each analog channel and set it in hardware.
        # Also (de)activate the analog channels accordingly
        num_pattern = re.compile('[0-9]+')
        max_res = constraints['dac_resolution']['max']
        for a_ch in a_chan:
            ach_num = int(re.search(num_pattern, a_ch).group(0))
            # determine number of markers for current a_ch
            if new_channels_state['d_ch' + str(2 * ach_num - 1)]:
                if new_channels_state['d_ch' + str(2 * ach_num)]:
                    marker_num = 2
                else:
                    marker_num = 1
            else:
                marker_num = 0
            # set DAC resolution for this channel
            dac_res = max_res - marker_num
            self.tell('SOURCE' + str(ach_num) + ':DAC:RESOLUTION ' + str(dac_res) + '\n')
            # (de)activate the analog channel
            if new_channels_state[a_ch]:
                self.tell('OUTPUT' + str(ach_num) + ':STATE ON\n')
            else:
                self.tell('OUTPUT' + str(ach_num) + ':STATE OFF\n')

        self.active_channel = new_channels_state
        return self.active_channel

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
            if fnmatch(filename, '*_ch?.wfmx'):
                asset_name = filename.rsplit('_', 1)[0]
                if asset_name not in name_list:
                    name_list.append(asset_name)
            elif fnmatch(filename, '*.mat'):
                asset_name = filename.rsplit('.', 1)[0]
                if asset_name not in name_list:
                    name_list.append(asset_name)
        return name_list

    def get_saved_asset_names(self):
        """ Retrieve the names of all sampled and saved assets on the host PC.
        This is no list of the file names.

        @return list: List of all saved asset name strings in the current
                      directory of the host PC.
        """
        # list of all files in the waveform directory ending with .mat or .WFMX
        file_list = self._get_filenames_on_host()
        # exclude the channel specifier for multiple analog channels and create return list
        saved_assets = []
        for filename in file_list:
            if fnmatch(filename, '*_ch?.wfmx'):
                asset_name = filename.rsplit('_', 1)[0]
                if asset_name not in saved_assets:
                    saved_assets.append(asset_name)
            elif fnmatch(filename, '*.mat'):
                asset_name = filename.rsplit('.', 1)[0]
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
                if fnmatch(filename, name+'_ch?.wfmx') or fnmatch(filename, name+'.mat'):
                    files_to_delete.append(filename)

        # delete files
        with FTP(self.ip_address) as ftp:
            ftp.login(user=self.user, passwd=self.passwd) # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.asset_directory)
            for filename in files_to_delete:
                ftp.delete(filename)

        # clear waveforms from AWG workspace
        wfm_list = self._get_waveform_names_memory()
        for wfm in wfm_list:
            for name in asset_name:
                if fnmatch(wfm, name + '_ch?'):
                    self.tell('WLIS:WAV:DEL "{0}"'.format(wfm))
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
            ftp.login(user=self.user,passwd=self.passwd) # login as default user anonymous, passwd anonymous@
            try:
                ftp.cwd(dir_path)
            except:
                self.log.info('Desired directory {0} not found on AWG '
                        'device.\n'
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
        return False

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)
        @return int: error code (0:OK, -1:error)

        Unused for pulse generator hardware other than an AWG. The AWG 5000
        Series does not have an interleave mode and this method exists only for
        compability reasons.
        """
        self.log.warning('Interleave mode not available for the AWG 70000 Series!\n'
                         'Method call will be ignored.')
        return False

    def get_interleave(self):
        """ Check whether Interleave is on in AWG.
        Unused for pulse generator hardware other than an AWG. The AWG 70000
        Series does not have an interleave mode and this method exists only for
        compability reasons.

        @return bool: will be always False since no interleave functionality
        """
        return False

    def tell(self, command):
        """Send a command string to the AWG.

        @param command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        if not command.endswith('\n'):
            command += '\n'
        command = bytes(command, 'UTF-8') # In Python 3.x the socket send command only accepts byte type arrays and no str
        self.soc.send(command)
        return 0

    def ask(self, question):
        """Asks the device a 'question' and receive and return an answer from device.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question'
        """
        if not question.endswith('\n'):
            question += '\n'
        question = bytes(question, 'UTF-8') # In Python 3.x the socket send command only accepts byte type arrays and no str
        self.soc.send(question)
        message = self.soc.recv(self.input_buffer)  # receive an answer
        message = message.decode('UTF-8') # decode bytes into a python str
        message = message.replace('\n','')      # cut away the characters\r and \n.
        message = message.replace('\r','')
        return message

    def reset(self):
        """Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.tell('*RST\n')
        return 0

    def _init_loaded_asset(self):
        """
        Gets the name of the currently loaded asset from the AWG and sets the attribute accordingly.
        """
        # rework starts here
        # first get all the channel assets
        a_ch_asset = [self.ask('SOUR' + str(count) + ":CASS?\n").replace('"', '')
                      for count in range(1, self._get_max_a_channel_number() + 1)]
        tmp_list = [a_ch.split('_ch') for a_ch in a_ch_asset]
        a_ch_asset = [ele[0] for ele in filter(lambda x: len(x) == 2, tmp_list)]

        # the case
        if len(a_ch_asset) != 0:
            all_same = True
            for asset in a_ch_asset:
                if asset != a_ch_asset[0]:
                    all_same = False
                    break
            if all_same:
                self.current_loaded_asset = a_ch_asset[0]
            else:
                self.log.error("In _init_loaded_asset: The case of differing asset names is not "
                               "yet handled")
                self.current_loaded_asset = None
        else:
            self.current_loaded_asset = None
        return self.current_loaded_asset

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
            ftp.login(user=self.user,passwd=self.passwd) # login as default user anonymous, passwd anonymous@
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
                if (filename.endswith('.wfmx') or filename.endswith('.mat')):
                    if filename not in filename_list:
                        filename_list.append(filename)
        return filename_list

    def _get_filenames_on_host(self):
        """ Get the full filenames of all assets saved on the host PC.

        @return: list, The full filenames of all assets saved on the host PC.
        """
        filename_list = [f for f in os.listdir(self.host_waveform_directory) if (f.endswith('.wfmx') or f.endswith('.mat'))]
        return filename_list

    def _get_model_ID(self):
        """
        @return: a string which represents the model id of the AWG.
        """
        id = self.ask('*IDN?\n').split(',')
        return id

    def _get_max_a_channel_number(self):
        """
        @return: Returns an integer which represents the number of analog
                 channels.
        """
        config = self.get_constraints()['activation_config']
        largest_list = config[max(config, key=config.get)]
        lst = [kk for kk in largest_list if 'a_ch' in kk]
        analog_channel_lst = [w.replace('a_ch', '') for w in lst]
        max_number_of_channels = max(map(int, analog_channel_lst))
        return max_number_of_channels

    def _get_waveform_names_memory(self):
        """
        Gets all waveform names currently loaded into the AWG workspace
        @return: list of names
        """
        number_of_wfm = int(self.ask('WLIS:SIZE?'))
        waveform_list = [None] * number_of_wfm
        for i in range(number_of_wfm):
            wfm_name = self.ask('WLIS:NAME? {0}'.format(i + 1))[1:-1]
            waveform_list[i] = wfm_name
        return waveform_list

    def _is_output_on(self):
        """
        Aks the AWG if the output is enabled, i.e. if the AWG is running

        @return: bool, (True: output on, False: output off)
        """
        run_state = bool(int(self.ask('AWGC:RST?')))
        return run_state