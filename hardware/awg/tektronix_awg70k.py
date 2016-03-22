# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware interface for pulsing devices.

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
"""

import os
import time
from socket import socket, AF_INET, SOCK_STREAM
from ftplib import FTP
import numpy as np
from collections import OrderedDict
from fnmatch import fnmatch

import hdf5storage

from core.base import Base
from interface.pulser_interface import PulserInterface
from hardware.awg.WFMX_header import WFMX_header

class AWG70K(Base, PulserInterface):
    """ UNSTABLE: Nikolas
    """
    _modclass = 'awg70k'
    _modtype = 'hardware'

    # declare connectors
    _out = {'pulser': 'PulserInterface'}

    def __init__(self,manager, name, config = {}, **kwargs):

        state_actions = {'onactivate'   : self.activation,
                         'ondeactivate' : self.deactivation}

        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        if 'awg_IP_address' in config.keys():
            self.ip_address = config['awg_IP_address']
        else:
            self.logMsg('This is AWG: Did not find >>awg_IP_address<< in '
                        'configuration.', msgType='error')

        if 'awg_port' in config.keys():
            self.port = config['awg_port']
        else:
            self.logMsg('This is AWG: Did not find >>awg_port<< in '
                        'configuration.', msgType='error')

        self.sample_mode = {'matlab':0, 'wfm-file':1, 'wfmx-file':2}
        if 'use_matlab_format' in config.keys():
            self.current_sample_mode = self.sample_mode['matlab']
        else:
            self.current_sample_mode = self.sample_mode['wfmx-file']

        self.sample_rate = 25e9

        self.amplitude_list = {1: 0.5, 2: 0.5}      # for each analog channel one value, the pp-voltage
        self.offset_list = {1: 0, 2: 0, 3: 0, 4: 0} # for each analog channel one value, the offset voltage

        self.current_loaded_asset = None
        self.is_output_enabled = True

        self.use_sequencer = False

        self.asset_directory = '/waves/'

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

        if 'ftp_root_dir' in config.keys():
            self.ftp_root_directory = config['ftp_root_dir']
        else:
            self.ftp_root_directory = 'C:/inetpub/ftproot'
            self.logMsg('No parameter "ftp_root_dir" was specified in the '
                        'config for tektronix_awg70k as directory for '
                        'the FTP server root on the AWG!\nThe default root directory\n{0}\n'
                        'will be taken instead.'.format(self.ftp_root_directory),
                        msgType='warning')

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')

        a_ch = {1: False, 2: False}
        d_ch = {1: False, 2: False, 3: False, 4: False}
        self.active_channel = (a_ch, d_ch)
        self.interleave = False

        self.current_status =  0


    def activation(self, e):
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
        self.soc.settimeout(3)
        self.soc.connect((self.ip_address, self.port))
        self.ftp = FTP(self.ip_address)
        self.ftp.login()
        self.ftp.cwd(self.asset_directory)

        self.input_buffer = int(2 * 1024)

        self.connected = True


    def deactivation(self, e):
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

        Only the keys 'channel_config', 'available channels', 'available_ch_num'
        'activation_map' and 'independent_ch' differ.

        If the constraints cannot be set in the pulsing hardware (because it
        might e.g. has no sequence mode) then write just zero to each generic
        dict. Note that there is a difference between float input (0.0) and
        integer input (0).
        ALL THE PRESENT KEYS OF THE CONSTRAINTS DICT MUST BE ASSIGNED!
        """

        constraints = {}
        # if interleave option is available, then sample rate constraints must
        # be assigned to the output of a function called
        # _get_sample_rate_constraints()
        # which outputs the shown dictionary with the correct values depending
        # on the present mode. The the GUI will have to check again the
        # limitations if interleave was selected.
        constraints['sample_rate'] = {'min': 1.5e3, 'max': 25.0e9,
                                      'step': 1, 'unit': 'Samples/s'}

        # the stepsize will be determined by the DAC in combination with the
        # maximal output amplitude (in Vpp):
        constraints['a_ch_amplitude'] = {'min': 0.25, 'max': 0.5,
                                         'step': 0.001, 'unit': 'Vpp'}

        #FIXME: Enter the proper offset constraints:
        constraints['a_ch_offset'] = {'min': 0.0, 'max': 0.0,
                                      'step': 0.0, 'unit': 'V'}

        #FIXME: Enter the proper digital channel low constraints:
        constraints['d_ch_low'] = {'min': 0.0, 'max': 0.0,
                                   'step': 0.0, 'unit': 'V'}

        #FIXME: Enter the proper digital channel high constraints:
        constraints['d_ch_high'] = {'min': 0.0, 'max': 0.0,
                                    'step': 0.0, 'unit': 'V'}

        # for arbitrary waveform generators, this values will be used. The
        # step value corresponds to the waveform granularity.
        constraints['sampled_file_length'] = {'min': 1, 'max': 8e9,
                                              'step': 1, 'unit': 'Samples'}

        # if only digital bins can be saved, then their limitation is different
        # compared to a waveform file
        constraints['digital_bin_num'] = {'min': 0, 'max': 0,
                                          'step': 0, 'unit': '#'}

        #FIXME: Check the proper number for your device
        constraints['waveform_num'] = {'min': 1, 'max': 32000,
                                       'step': 1, 'unit': '#'}

        #FIXME: Check the proper number for your device
        constraints['sequence_num'] = {'min': 1, 'max': 4000,
                                       'step': 1, 'unit': '#'}

        #FIXME: Check the proper number for your device
        constraints['subsequence_num'] = {'min': 1, 'max': 8000,
                                          'step': 1, 'unit': '#'}

        # For the channel configuration, three information has to be set!
        #   First is the 'personal' or 'assigned' channelnumber (can be chosen)
        #   by yourself.
        #   Second is whether the specified channel is an analog or digital
        #   channel
        #   Third is the channel number, which is assigned to that channel name.
        #
        # So in summary:
        #       configuration: channel-name, channel-type, channelnumber
        # That configuration takes place here:
        available_ch = OrderedDict()
        available_ch['ACH1'] = {'a_ch': 1}
        available_ch['DCH1'] = {'d_ch': 1}
        available_ch['DCH2'] = {'d_ch': 2}
        available_ch['ACH2'] = {'a_ch': 2}
        available_ch['DCH3'] = {'d_ch': 3}
        available_ch['DCH4'] = {'d_ch': 4}
        constraints['available_ch'] = available_ch

        # State all possible DIFFERENT configurations, which the pulsing device
        # may have. That concerns also the display of the chosen channels.
        # Channel configuration for this device, use OrderedDictionaries to
        # keep an order in that dictionary. That is for now the easiest way to
        # determine the channel configuration:
        channel_config = OrderedDict()
        channel_config['conf1'] = ['a_ch', 'd_ch', 'd_ch', 'a_ch', 'd_ch', 'd_ch']
        channel_config['conf2'] = ['a_ch', 'd_ch', 'd_ch', 'a_ch', 'd_ch']
        channel_config['conf3'] = ['a_ch', 'd_ch', 'd_ch', 'a_ch']
        channel_config['conf4'] = ['a_ch', 'd_ch', 'a_ch', 'd_ch', 'd_ch']
        channel_config['conf5'] = ['a_ch', 'a_ch', 'd_ch', 'd_ch']
        channel_config['conf6'] = ['a_ch', 'd_ch', 'a_ch', 'd_ch']
        channel_config['conf7'] = ['a_ch', 'd_ch', 'a_ch']
        channel_config['conf8'] = ['a_ch', 'a_ch', 'd_ch']
        channel_config['conf9'] = ['a_ch', 'a_ch']
        channel_config['conf10'] = ['a_ch', 'd_ch']
        channel_config['conf11'] = ['a_ch']

        constraints['channel_config'] = channel_config

        # Now you can choose, how many channel activation pattern exists. You
        # can only use the names, declared in the constraint 'available_ch'!
        activation_map = OrderedDict()
        activation_map['all'] = ['ACH1', 'DCH1', 'DCH2', 'ACH2', 'DCH3', 'DCH4']
        # Usage of both channels but reduced markers (higher analogue resolution)
        activation_map['ch1_2mrk_ch2_1mrk'] = ['ACH1', 'DCH1', 'DCH2', 'ACH2', 'DCH3']
        activation_map['ch1_2mrk_ch2_0mrk'] = ['ACH1', 'DCH1', 'DCH2', 'ACH2']
        activation_map['ch1_1mrk_ch2_2mrk'] = ['ACH1', 'DCH1', 'ACH2', 'DCH3', 'DCH4']
        activation_map['ch1_0mrk_ch2_2mrk'] = ['ACH1', 'ACH2', 'DCH3', 'DCH4']
        activation_map['ch1_1mrk_ch2_1mrk'] = ['ACH1', 'DCH1', 'ACH2', 'DCH3']
        activation_map['ch1_0mrk_ch2_1mrk'] = ['ACH1', 'ACH2', 'DCH3']
        activation_map['ch1_1mrk_ch2_0mrk'] = ['ACH1', 'DCH1', 'ACH2']
        # Usage of channel 1 only:
        activation_map['ch1_2mrk'] = ['ACH1', 'DCH1', 'DCH2']
        # Usage of channel 2 only:
        activation_map['ch2_2mrk'] = ['ACH2', 'DCH3', 'DCH4']
        # Usage of only channel 1 with one marker:
        activation_map['ch1_1mrk'] = ['ACH1', 'DCH1']
        # Usage of only channel 2 with one marker:
        activation_map['ch2_1mrk'] = ['ACH2', 'DCH3']
        # Usage of only channel 1 with no marker:
        activation_map['ch1_0mrk'] = ['ACH1']
        # Usage of only channel 2 with no marker:
        activation_map['ch2_0mrk'] = ['ACH2']
        constraints['activation_map'] = activation_map

        # this information seems to be almost redundant but it can be that no
        # channel configuration exists, where not all available channels are
        # present. Therefore this is needed here:
        constraints['available_ch_num'] = {'a_ch': 2, 'd_ch': 4}

        # number of independent channels on which you can load or upload
        # separately the created files. It does not matter how the channels
        # are looking like.
        constraints['independent_ch'] = 2

        return constraints

    #FIXME: hdf5storage package is inefficient regarding memory usage and speed.
    #       Better dont use it for now until a better package is found. Use .WFMX instead.
    #       Once a better solution is found a case differentiation has to be implemented.
    def write_to_file(self, name, analogue_samples,
                            digital_samples, total_number_of_samples,
                            is_first_chunk, is_last_chunk):
        """
        Appends a sampled chunk of a whole waveform to a file. Create the file
        if it is the first chunk.
        If both flags (is_first_chunk, is_last_chunk) are set to TRUE it means
        that the whole ensemble is written as a whole in one big chunk.

        @param name: string, represents the name of the sampled ensemble
        @param analogue_samples: float32 numpy ndarray, contains the
                                       samples for the analogue channels that
                                       are to be written by this function call.
        @param digital_samples: bool numpy ndarray, contains the samples
                                      for the digital channels that
                                      are to be written by this function call.
        @param total_number_of_samples: int, The total number of samples in the
                                        entire waveform. Has to be known it advance.
        @param is_first_chunk: bool, indicates if the current chunk is the
                               first write to this file.
        @param is_last_chunk: bool, indicates if the current chunk is the last
                              write to this file.

        @return: error code (0: OK, -1: error)
        """

        # The overhead of the write process in bytes.
        # Making this value bigger will result in a faster write process
        # but consumes more memory
        write_overhead_bytes = 1024*1024*256 # 256 MB
        # The overhead of the write process in number of samples
        write_overhead = write_overhead_bytes//4

        if self.current_sample_mode != self.sample_mode['wfmx-file']:
            self.logMsg('Sample mode for this device not supported.'
                        'Using WFMX instead.',
                        msgType='warning')

        # if it is the first chunk, create the .WFMX file with header.
        if is_first_chunk:
            for channel_number in range(analogue_samples.shape[0]):
                # create header
                header_obj = WFMX_header(self.sample_rate, self.amplitude_list[channel_number+1], 0,
                                         int(total_number_of_samples))

                header_obj.create_xml_file()
                with open('header.xml','r') as header:
                    header_lines = header.readlines()
                os.remove('header.xml')
                # create .WFMX-file for each channel.
                filepath = os.path.join(self.host_waveform_directory, name + '_Ch' + str(channel_number+1) + '.WFMX')
                with open(filepath, 'wb') as wfmxfile:
                    # write header
                    for line in header_lines:
                        wfmxfile.write(bytes(line, 'UTF-8'))

        # append analogue samples to the .WFMX files of each channel. Write
        # digital samples in temporary files.
        for channel_number in range(analogue_samples.shape[0]):
            # append analogue samples chunk to .WFMX file
            filepath = os.path.join(self.host_waveform_directory, name + '_Ch' + str(channel_number+1) + '.WFMX')
            with open(filepath, 'ab') as wfmxfile:
                # append analogue samples in binary format. One sample is 4
                # bytes (np.float32). Write in chunks if array is very big to
                # avoid large temporary copys in memory
                number_of_full_chunks = int(analogue_samples.shape[1]//write_overhead)
                for i in range(number_of_full_chunks):
                    start_ind = i*write_overhead
                    stop_ind = (i+1)*write_overhead
                    wfmxfile.write(analogue_samples[channel_number][start_ind:stop_ind])
                # write rest
                rest_start_ind = number_of_full_chunks*write_overhead
                wfmxfile.write(analogue_samples[channel_number][rest_start_ind:])

            # create the byte values corresponding to the marker states
            # (\x01 for marker 1, \x02 for marker 2, \x03 for both)
            # and write them into a temporary file
            filepath = os.path.join(self.host_waveform_directory, name + '_Ch' + str(channel_number+1) + '_digi' + '.tmp')
            with open(filepath, 'ab') as tmpfile:
                if digital_samples.shape[0] <= (2*channel_number):
                    # no digital channels to write for this analogue channel
                    pass
                elif digital_samples.shape[0] == (2*channel_number + 1):
                    # one digital channels to write for this analogue channel
                    for i in range(number_of_full_chunks):
                        start_ind = i*write_overhead
                        stop_ind = (i+1)*write_overhead
                        # append digital samples in binary format. One sample
                        # is 1 byte (np.uint8).
                        tmpfile.write(digital_samples[2*channel_number][start_ind:stop_ind])
                    # write rest of digital samples
                    rest_start_ind = number_of_full_chunks*write_overhead
                    tmpfile.write(digital_samples[2*channel_number][rest_start_ind:])
                elif digital_samples.shape[0] >= (2*channel_number + 2):
                    # two digital channels to write for this analogue channel
                    for i in range(number_of_full_chunks):
                        start_ind = i*write_overhead
                        stop_ind = (i+1)*write_overhead
                        temp_markers = np.add(np.left_shift(digital_samples[2*channel_number + 1][start_ind:stop_ind].astype('uint8'),1), digital_samples[2*channel_number][start_ind:stop_ind])
                        # append digital samples in binary format. One sample
                        # is 1 byte (np.uint8).
                        tmpfile.write(temp_markers)
                    # write rest of digital samples
                    rest_start_ind = number_of_full_chunks*write_overhead
                    temp_markers = np.add(np.left_shift(digital_samples[2*channel_number + 1][rest_start_ind:].astype('uint8'),1), digital_samples[2*channel_number][rest_start_ind:])
                    tmpfile.write(temp_markers)

        # append the digital sample tmp file to the .WFMX file and delete the
        # .tmp files if it was the last chunk to write.
        if is_last_chunk:
            for channel_number in range(analogue_samples.shape[0]):
                tmp_filepath = os.path.join(self.host_waveform_directory, name + '_Ch' + str(channel_number+1) + '_digi' + '.tmp')
                wfmx_filepath = os.path.join(self.host_waveform_directory, name + '_Ch' + str(channel_number+1) + '.WFMX')
                with open(wfmx_filepath, 'ab') as wfmxfile:
                    with open(tmp_filepath, 'rb') as tmpfile:
                        # read and write files in max. write_overhead_bytes chunks to reduce
                        # memory usage
                        while True:
                            tmp_data = tmpfile.read(write_overhead_bytes)
                            if not tmp_data:
                                break
                            wfmxfile.write(tmp_data)
                # delete tmp file
                os.remove(tmp_filepath)
        return 0

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.tell('AWGC:RUN\n')
        self.current_status = 1
        return 0

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.tell('AWGC:STOP\n')
        self.current_status = 0
        return 0

    def upload_asset(self, asset_name=None):
        """ Upload an already hardware conform file to the device.
            Does NOT load it into channels.

        @param name: string, name of the ensemble/seqeunce to be uploaded

        @return int: error code (0:OK, -1:error)

        If nothing is passed, method will be skipped.
        """
        # check input
        if asset_name is None:
            self.logMsg('No asset name provided for upload!\nCorrect '
                        'that!\nCommand will be ignored.', msgType='warning')
            return -1

        filelist = os.listdir(self.host_waveform_directory)
        upload_names = []
        for filename in filelist:
            is_wfmx = filename.endswith('.WFMX')
            is_mat = filename.endswith(asset_name+'.mat')
            if is_wfmx and (asset_name + '_Ch') in filename:
                upload_names.append(filename)
            elif is_mat:
                upload_names.append(filename)
                break
        # Transfer files
        for filename in upload_names:
            self._send_file(filename)

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

        # Find all files associated with the specified asset name
        with FTP(self.ip_address) as ftp:
            ftp.login() # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.asset_directory)
            # get only the files from the dir and skip possible directories
            log =[]
            file_list = []
            filename = []
            ftp.retrlines('LIST', callback=log.append)
        for line in log:
            if not '<DIR>' in line:
                file_list.append(line.rsplit(None, 1)[1])

        # find all assets wit file type .mat and .WFMX and name "asset_name"
        # FIXME: Also include .SEQX later on
        for file in file_list:
            if file == asset_name+'.mat':
                filename.append(file)
            elif file == asset_name+'_Ch1.WFMX':
                filename.append(file)
            elif file == asset_name+'_Ch2.WFMX':
                filename.append(file)

        # Check if something could be found
        if len(filename) == 0:
            self.logMsg('No files associated with asset "{0}" were found on AWG70k.'
                        'Load to channels failed!'.format(asset_name),
                        msgType='error')
            return -1

        # Check if multiple file formats for a single asset_name are present and issue warning
        tmp = filename[0][-4:]
        for name in filename:
            if not name.endswith(tmp):
                self.logMsg('Multiple file formats associated with the asset "{0}" were found on AWG70k.'
                            'Load to channels failed!'.format(asset_name),
                        msgType='error')
                return -1

        self.logMsg('The following files associated with the asset "{0}" were found on AWG70k:\n'
                    '"{1}"'.format(asset_name, filename), msgType='status')

        # load files in AWG workspace
        for asset in filename:
            file_path  = os.path.join(self.ftp_root_directory, self.asset_directory + asset)
            if asset.endswith('.mat'):
                self.tell('MMEM:OPEN:SASS:WAV "%s"\n' % file_path)
            else:
                self.tell('MMEM:OPEN "%s"\n' % file_path)
            self.ask('*OPC?\n')

        # simply use the channel association of the filenames if no load_dict is given
        if load_dict == {}:
            for asset in filename:
                # load waveforms into channels
                name = asset_name + '_Ch1'
                self.tell('SOUR1:CASS:WAV "%s"\n' % name)
                name = asset_name + '_Ch2'
                self.tell('SOUR2:CASS:WAV "%s"\n' % name)
                self.current_loaded_asset = asset_name
                # self.soc.settimeout(3)
        else:
            for channel in load_dict:
                # load waveforms into channels
                name = load_dict[channel]
                self.tell('SOUR'+str(channel)+':CASS:WAV "%s"\n' % name)
            self.current_loaded_asset = asset_name

        return 0

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

    def clear_all(self):
        """ Clears the loaded waveform from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Delete all waveforms and sequences from Hardware memory and clear the
        visual display. Unused for digital pulse generators without sequence
        storage capability (PulseBlaster, FPGA).
        """
        self.tell('WLIS:WAV:DEL ALL\n')
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
        time.sleep(3)
        return_rate = float(self.ask('CLOCK:SRATE?\n'))
        self.sample_rate = return_rate
        return return_rate

    def get_sample_rate(self):
        """ Set the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """
        return self.sample_rate

    def get_analog_level(self, amplitude=[], offset=[]):
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

        #FIXME: implement this method properly for this AWG type. Exploit of
        #       having now the possibility to set individual or a group of
        #       channels to the desired value. If in doubt, look at the
        #       hardware file of AWG5000 series.


        amp = {}
        off = {}

        #If you want to check the input use the constraints:
        constraints = self.get_constraints()

        if (amplitude == []) and (offset == []):
            # since the available channels are not going to change for this
            # device you are asking directly:
            #FIXME: Implement here the proper ask routine:
            amp = self.amplitude_list
            off = self.offset_list

        else:
            for a_ch in amplitude:
                #FIXME: Implement here the proper ask routine:
                amp[a_ch] = self.amplitude_list[a_ch]
            for a_ch in offset:
                #FIXME: Implement here the proper ask routine:
                off[a_ch] = self.offset_list[a_ch]

        return amp, off

    def set_analog_level(self, amplitude={}, offset={}):
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

        #If you want to check the input use the constraints:
        constraints = self.get_constraints()

        for a_ch in amplitude:
            self.amplitude_list[a_ch] = amplitude[a_ch]
            #FIXME: Tell the device the proper amplitude:
            # self.tell('SOURCE{0}:VOLTAGE:AMPLITUDE {1}'.format(a_ch, amplitude[a_ch]))
            pass

        for a_ch in offset:
            self.offset_list[a_ch] = offset[a_ch]
            #FIXME: Tell the device the proper offset:
            # self.tell('SOURCE{0}:VOLTAGE:OFFSET {1}'.format(a_ch, offset[a_ch]))
            pass

    def get_digital_level(self, low=[], high=[]):
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

        low_val = {}
        high_val = {}

        #If you want to check the input use the constraints:
        constraints = self.get_constraints()

        if (low == []) and (high == []):
            # since the available channels are not going to change for this
            # device you are asking directly:

            #FIXME: Implement here the proper ask routine:
            # low_val[1] =  float(self.ask('SOURCE1:MARKER1:VOLTAGE:LOW?'))
            low_val[1] = 0.0
            low_val[2] = 0.0
            low_val[3] = 0.0
            low_val[4] = 0.0

            # high_val[1] = float(self.ask('SOURCE1:MARKER1:VOLTAGE:HIGH?'))
            high_val[1] = 2.5
            high_val[2] = 2.5
            high_val[3] = 2.5
            high_val[4] = 2.5
        else:
            for d_ch in low:
                #FIXME: Implement here the proper ask routine:
                low_val[d_ch] = 0.0
            for d_ch in high:
                #FIXME: Implement here the proper ask routine:
                high_val[d_ch] = 2.5

        return low_val, high_val


    def set_digital_level(self, low={}, high={}):
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


    def set_active_channels(self, a_ch={}, d_ch={}):
        """ Set the active channels for the pulse generator hardware.

        @param dict a_ch: dictionary with keys being the analog channel numbers
                          and items being boolean values.
        @param dict d_ch: dictionary with keys being the digital channel numbers
                          and items being boolean values.

        @return int: error code (0:OK, -1:error)

        Example for possible input:
            a_ch={2: True}, d_ch={1:False, 3:True, 4:True}
        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1.

        The hardware itself has to handle, whether separate channel activation
        is possible.

        AWG5000 Series instruments support only 14-bit resolution. Therefore
        this command will have no effect on the DAC for these instruments. On
        other devices the deactivation of digital channels increase the DAC
        resolution of the analog channels.
        """

        #If you want to check the input use the constraints:
        constraints = self.get_constraints()

        # update active channels variable
        for channel in a_ch:
            self.active_channel[0][channel] = a_ch[channel]
        for channel in d_ch:
            self.active_channel[1][channel] = d_ch[channel]

        # create marker list for the 4 available markers
        marker_on = []
        for digi_ch in self.active_channel[1].keys():
            marker_on.append(self.active_channel[1][digi_ch])

        # count the markers per channel
        ch1_marker = marker_on[0:2].count(True)
        ch2_marker = marker_on[2:4].count(True)

        # adjust the DAC resolution accordingly
        self.tell('SOURCE1:DAC:RESOLUTION ' + str(10-ch1_marker) + '\n')
        self.tell('SOURCE2:DAC:RESOLUTION ' + str(10-ch2_marker) + '\n')

        # switch on channels accordingly
        if self.active_channel[0][1]:
            self.tell('OUTPUT1:STATE ON\n')
        else:
            self.tell('OUTPUT1:STATE OFF\n')

        if self.active_channel[0][2]:
            self.tell('OUTPUT2:STATE ON\n')
        else:
            self.tell('OUTPUT2:STATE OFF\n')

        return 0

    def get_active_channels(self, a_ch=[], d_ch=[]):
        """ Get the active channels of the pulse generator hardware.

        @param list a_ch: optional, if specific analog channels are needed to be
                          asked without obtaining all the channels.
        @param list d_ch: optional, if specific digital channels are needed to
                          be asked without obtaining all the channels.

        @return tuple of two dicts, where keys denoting the channel number and
                items boolean expressions whether channel are active or not.
                First dict contains the analog settings, second dict the digital
                settings. If either digital or analog are not present, return
                an empty dict.

        Example for an possible input:
            a_ch=[2, 1] d_ch=[2,1,5]
        then the output might look like
            {1: True, 2: False} {1: False, 2: True, 5: False}

        If no parameters are passed to this method all channels will be asked
        for their setting.
        """

        #If you want to check the input use the constraints:
        constraints = self.get_constraints()
        active_a_ch = {}
        active_d_ch = {}

        # check how many markers are active on each channel, i.e. the DAC resolution
        ch1_markers = 10-int(self.ask('SOURCE1:DAC:RESOLUTION?\n'))
        ch2_markers = 10-int(self.ask('SOURCE2:DAC:RESOLUTION?\n'))

        if ch1_markers == 0:
            active_d_ch[1] = False
            active_d_ch[2] = False
        elif ch1_markers == 1:
            active_d_ch[1] = True
            active_d_ch[2] = False
        else:
            active_d_ch[1] = True
            active_d_ch[2] = True

        if ch2_markers == 0:
            active_d_ch[3] = False
            active_d_ch[4] = False
        elif ch1_markers == 1:
            active_d_ch[3] = True
            active_d_ch[4] = False
        else:
            active_d_ch[3] = True
            active_d_ch[4] = True

        # check what analogue channels are active
        if bool(int(self.ask('OUTPUT1:STATE?\n'))):
            active_a_ch[1] = True
        else:
            active_a_ch[1] = False

        if bool(int(self.ask('OUTPUT2:STATE?\n'))):
            active_a_ch[2] = True
        else:
            active_a_ch[2] = False

        # return either all channel information of just the one asked for.
        if (a_ch == []) and (d_ch == []):
            return_a_ch = active_a_ch
            return_d_ch = active_d_ch
        else:
            return_a_ch = {}
            return_d_ch = {}
            for ana_chan in a_ch:
                return_a_ch[ana_chan] = active_a_ch[ana_chan]
            for digi_chan in d_ch:
                return_d_ch[digi_chan] = active_d_ch[digi_chan]

        return return_a_ch, return_d_ch

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
            if fnmatch(filename, '*_Ch?.WFMX'):
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
        # exclude the channel specifier for multiple analogue channels and create return list
        saved_assets = []
        for filename in file_list:
            if fnmatch(filename, '*_Ch?.WFMX'):
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

        @return int: error code (0:OK, -1:error)

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
                if fnmatch(filename, name+'_Ch?.WFMX') or fnmatch(filename, name+'.mat'):
                    files_to_delete.append(filename)

        # delete files
        with FTP(self.ip_address) as ftp:
            ftp.login() # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.asset_directory)
            for filename in files_to_delete:
                ftp.delete(filename)

        # clear the AWG if the deleted asset is the currently loaded asset
        if self.current_loaded_asset == asset_name:
            self.clear_all()
        return 0

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
                self.logMsg('Desired directory {0} not found on AWG device.\n'
                            'Create new.'.format(dir_path), msgType='status')
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
        self.logMsg('Interleave mode not available for the AWG 70000 Series!\n'
                    'Method call will be ignored.', msgType='warning')
        return 0

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
        time.sleep(0.1)                 # you need to wait until AWG generating
                                        # an answer.
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
                    file_list.append(line.rsplit(None, 1)[1])
            for filename in file_list:
                if (filename.endswith('.WFMX') or filename.endswith('.mat')):
                    if filename not in filename_list:
                        filename_list.append(filename)
        return filename_list

    def _get_filenames_on_host(self):
        """ Get the full filenames of all assets saved on the host PC.

        @return: list, The full filenames of all assets saved on the host PC.
        """
        filename_list = [f for f in os.listdir(self.host_waveform_directory) if (f.endswith('.WFMX') or f.endswith('.mat'))]
        return filename_list