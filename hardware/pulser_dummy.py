# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware dummy for pulsing devices.

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

Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
Copyright (C) 2015 Nikolas Tomek nikolas.tomek@uni-ulm.de
"""

import os
import numpy as np
from collections import OrderedDict
from fnmatch import fnmatch

import hdf5storage

from core.base import Base
from interface.pulser_interface import PulserInterface
from hardware.awg.WFMX_header import WFMX_header


class PulserDummy(Base, PulserInterface):
    """ Dummy class for  PulseInterface

    Be careful in adjusting the method names in that class, since some of them
    are also connected to the mwsourceinterface (to give the AWG the possibility
    to act like a microwave source).
    """
    _modclass = 'PulserDummy'
    _modtype = 'hardware'
    # connectors
    _out = {'pulser': 'PulserInterface'}


    def __init__(self, manager, name, config, **kwargs):
        state_actions = {'onactivate'   : self.activation,
                         'ondeactivate' : self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        self.logMsg('Dummy Pulser: I will simulate an AWG :) !',
                    msgType='status')

        # a dictionary with all the possible sample modes assigned to a number:
        self.sample_mode = {'matlab':0, 'wfm-file':1, 'wfmx-file':2}
        self.current_sample_mode = self.sample_mode['wfm-file']

        self.awg_waveform_directory = '/waves'

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

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')

        self.connected = False
        self.sample_rate = 25e9
        self.amplitude_list = {1: 1, 2: 1, 3: 1} # for each analog channel one value
        self.offset_list = {1: 0, 2: 0, 3: 0}

        # Deactivate all channels at first:
        a_ch = {1: False, 2: False, 3: False}
        d_ch = {1: False, 2: False, 3: False, 4: False,
                5: False, 6: False, 7: False, 8: False}
        self.active_channel = (a_ch, d_ch)

        self.digital_high_list = {1: 5, 2: 5, 2: 5, 4: 5,
                                  5: 5, 6: 5, 7: 5, 8: 5}
        self.digital_low_list = {1: 0, 2: 0, 3: 0, 4: 0,
                                 5: 0, 6: 0, 7: 0, 8: 0}

        self.uploaded_assets_list = []
        self.uploaded_files_list = []
        self.current_loaded_asset = None
        self.is_output_enabled = True

        # settings for remote access on the AWG PC
        self.asset_directory = 'waves'
        self.use_sequencer = True
        self.interleave = False

        self.current_status = 0    # that means off, not running.
        self._marker_byte_dict = { 0:b'\x00',1:b'\x01', 2:b'\x02', 3:b'\x03'}
        # self.pp_voltage = 0.5

    def activation(self, e):
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

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """

        self.connected = False

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
        constraints = dict()

        # if interleave option is available, then sample rate constraints must
        # be assigned to the output of a function called
        # _get_sample_rate_constraints()
        # which outputs the shown dictionary with the correct values depending
        # on the present mode. The the GUI will have to check again the
        # limitations if interleave was selected.
        constraints['sample_rate']  = self._get_sample_rate_constraints()
        # the stepsize will be determined by the DAC in combination with the
        # maximal output amplitude (in Vpp):
        constraints['a_ch_amplitude'] = {'min': 0.02, 'max': 2.0,
                                         'step': 0.001, 'unit': 'Vpp'}

        constraints['a_ch_offset'] = {'min': -1.0, 'max': 1.0,
                                      'step': 0.001, 'unit': 'V'}

        constraints['d_ch_low'] = {'min': -1.0, 'max': 4.0,
                                   'step': 0.01, 'unit': 'V'}

        constraints['d_ch_high'] = {'min': 0.0, 'max': 5.0,
                                    'step': 0.0, 'unit': 'V'}

        constraints['sampled_file_length'] = {'min': 80, 'max': 64.8e6,
                                              'step': 1, 'unit': 'Samples'}

        constraints['digital_bin_num'] = {'min': 0, 'max': 0.0,
                                          'step': 0, 'unit': '#'}

        constraints['waveform_num'] = {'min': 1, 'max': 32000,
                                       'step': 1, 'unit': '#'}

        constraints['sequence_num'] = {'min': 1, 'max': 8000,
                                       'step': 1, 'unit': '#'}

        constraints['subsequence_num'] = {'min': 1, 'max': 4000,
                                          'step': 1, 'unit': '#'}

        # If sequencer mode is enable than sequence_param should be not just an
        # empty dictionary.
        sequence_param = OrderedDict()
        sequence_param['reps'] = {'min': 0, 'max': 65536, 'step': 1,
                                  'unit': '#'}
        sequence_param['trigger_wait'] = {'min': False, 'max': True, 'step': 1,
                                          'unit': 'bool'}
        sequence_param['event_jump_to'] = {'min': -1, 'max': 8000, 'step': 1,
                                           'unit': 'row'}
        sequence_param['go_to'] = {'min': 0, 'max': 8000, 'step': 1,
                                   'unit': 'row'}
        constraints['sequence_param'] = sequence_param

        # For the channel configuration, three information has to be set!
        #   First is the 'personal' or 'assigned' channelnumber (can be chosen)
        #   by yourself.
        #   Second is whether the specified channel is an analog or digital
        #   channel
        #   Third is the channel number, which is assigned to that channel name.
        #
        # So in summary:
        #       configuration: channel-name, channel-type, channelnumber
        # That configuration takes place here. A Setting for an AWG type
        # configuration, where 2 analog and 4 digital channels are available.
        available_ch = OrderedDict()
        available_ch['Interleave'] = {'a_ch': 1}
        available_ch['ACH1'] = {'a_ch': 1}
        available_ch['DCH1'] = {'d_ch': 1}
        available_ch['DCH2'] = {'d_ch': 2}
        available_ch['ACH2'] = {'a_ch': 2}
        available_ch['DCH3'] = {'d_ch': 3}
        available_ch['DCH4'] = {'d_ch': 4}
        available_ch['DCH5'] = {'d_ch': 5}
        available_ch['DCH6'] = {'d_ch': 6}
        available_ch['DCH7'] = {'d_ch': 7}
        available_ch['DCH8'] = {'d_ch': 8}
        constraints['available_ch'] = available_ch

        # State all possible DIFFERENT configurations, which the pulsing device
        # may have. That concerns also the display of the chosen channels.
        # Channel configuration for this device, use OrderedDictionaries to
        # keep an order in that dictionary. That is for now the easiest way to
        # determine the channel configuration:
        channel_config = OrderedDict()
        channel_config['conf1'] = ['a_ch', 'd_ch', 'd_ch']
        channel_config['conf2'] = ['a_ch', 'd_ch', 'd_ch', 'a_ch', 'd_ch', 'd_ch']
        channel_config['conf3'] = ['d_ch', 'd_ch', 'd_ch', 'd_ch',
                                   'd_ch', 'd_ch', 'd_ch', 'd_ch']
        channel_config['conf4'] = ['a_ch']
        channel_config['conf5'] = ['a_ch', 'a_ch']
        constraints['channel_config'] = channel_config

        # Now you can choose, how many channel activation pattern exists:
        activation_map = OrderedDict()
        activation_map['map1'] = ['ACH1', 'DCH1', 'DCH2', 'ACH2', 'DCH3', 'DCH4']
        # Usage of channel 1 only:
        activation_map['map2'] = ['ACH1', 'DCH1', 'DCH2']
        # Usage of channel 2 only:
        activation_map['map3'] = ['ACH2', 'DCH3', 'DCH4']
        # Usage of Interleave mode:
        activation_map['map4'] = ['Interleave', 'DCH1', 'DCH2']
        # make only digital channels visible:
        activation_map['map5'] = ['DCH1', 'DCH2', 'DCH3', 'DCH4',
                                  'DCH5', 'DCH6', 'DCH7', 'DCH8']
        activation_map['map6'] = ['ACH1']
        activation_map['map7'] = ['ACH2']
        activation_map['map8'] = ['ACH1', 'ACH2']

        constraints['activation_map'] = activation_map

        # this information seems to be almost redundant but it can be that no
        # channel configuration exists, where not all available channels are
        # present. Therefore this is needed here:
        constraints['available_ch_num'] = {'a_ch': 3, 'd_ch': 8}

        # number of independent channels on which you can load or upload
        # separately the created files. It does not matter how the channels
        # are looking like.
        constraints['independent_ch'] = 2

        return constraints

    def _get_sample_rate_constraints(self):
        """ If sample rate changes during Interleave mode, then it has to be
            adjusted for that state.

        @return dict: with keys 'min', 'max':, 'step' and 'unit' and the
                      assigned values for that keys.
        """
        if self.interleave:
            return {'min': 12.0e9, 'max': 24.0e9,
                    'step': 4, 'unit': 'Samples/s'}
        else:
            return {'min': 10.0e6, 'max': 12.0e9,
                    'step': 4, 'unit': 'Samples/s'}

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:stopped, -1:error, 1:running)
        """
        self.current_status = 1
        self.logMsg('PulserDummy: Switch on the Output.', msgType='status')
        return self.current_status

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:stopped, -1:error, 1:running)
        """
        self.current_status = 0
        self.logMsg('PulserDummy: Switch off the Output.', msgType='status')
        return self.current_status

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

        if self.current_sample_mode == self.sample_mode['matlab']:
            #FIXME: chunkwise write to a .mat file not supported by the used
            #       hdf5storage package. This package is inefficient anyway and
            #       needs a replacement if .mat files should be supported.

            # check if chunkwise write is requested and issue warning if this is the case.
            # Do not write to file then.
            if (not is_first_chunk) and (not is_last_chunk):
                self.logMsg('Chunkwise write for sample mode matlab not supported.'
                            'Nothing was written to file.', msgType='error')
                return -1
            else:
                matcontent = {}
                matcontent[u'Waveform_Name_1'] = name # each key must be a unicode string
                matcontent[u'Waveform_Data_1'] = analog_samples[0]
                matcontent[u'Waveform_Sampling_Rate_1'] = self.sample_rate
                matcontent[u'Waveform_Amplitude_1'] = self.pp_voltage

                if analog_samples.shape[0] == 2:
                    matcontent[u'Waveform_Name_1'] = name + '_Ch1'
                    matcontent[u'Waveform_Name_2'] = name + '_Ch2'
                    matcontent[u'Waveform_Data_2'] = analog_samples[1]
                    matcontent[u'Waveform_Sampling_Rate_2'] = self.sample_rate
                    matcontent[u'Waveform_Amplitude_2'] = self.pp_voltage

                if digital_samples.shape[0] >= 1:
                    matcontent[u'Waveform_M1_1'] = digital_samples[0]
                if digital_samples.shape[0] >= 2:
                    matcontent[u'Waveform_M2_1'] = digital_samples[1]
                if digital_samples.shape[0] >= 3:
                    matcontent[u'Waveform_M1_2'] = digital_samples[2]
                if digital_samples.shape[0] >= 4:
                    matcontent[u'Waveform_M2_2'] = digital_samples[3]

                # create file in current directory
                filename = name +'.mat'
                created_files.append(filename)
                hdf5storage.write(matcontent, '.', filename, matlab_compatible=True)
                # check if file already exists and overwrite it
                if os.path.isfile(os.path.join(self.host_waveform_directory, filename)):
                    os.remove(os.path.join(self.host_waveform_directory, filename))
                os.rename(os.getcwd() + name +'.mat', os.path.join(self.host_waveform_directory,
                                                                   filename))

        elif self.current_sample_mode == self.sample_mode['wfmx-file']:
            # The overhead of the write process in bytes.
            # Making this value bigger will result in a faster write process
            # but consumes more memory
            write_overhead_bytes = 1024*1024*256 # 256 MB
            # The overhead of the write process in number of samples
            write_overhead = write_overhead_bytes//4

            # if it is the first chunk, create the .WFMX file with header.
            if is_first_chunk:
                for channel_number in range(analog_samples.shape[0]):
                    # create header
                    header_obj = WFMX_header(self.sample_rate,
                                             self.amplitude_list[channel_number+1],
                                             0,
                                             int(total_number_of_samples))

                    header_obj.create_xml_file()
                    with open('header.xml','r') as header:
                        header_lines = header.readlines()
                    os.remove('header.xml')
                    # create .WFMX-file for each channel.
                    filename = name + '_Ch' + str(channel_number+1) + '.WFMX'
                    created_files.append(filename)

                    filepath = os.path.join(self.host_waveform_directory, filename)
                    with open(filepath, 'wb') as wfmxfile:
                        # write header
                        for line in header_lines:
                            wfmxfile.write(bytes(line, 'UTF-8'))

            # append analog samples to the .WFMX files of each channel. Write
            # digital samples in temporary files.
            for channel_number in range(analog_samples.shape[0]):
                # append analog samples chunk to .WFMX file
                filepath = os.path.join(self.host_waveform_directory,
                                        name + '_Ch' + str(channel_number+1) + '.WFMX')

                with open(filepath, 'ab') as wfmxfile:
                    # append analog samples in binary format. One sample is 4
                    # bytes (np.float32). Write in chunks if array is very big to
                    # avoid large temporary copys in memory
                    number_of_full_chunks = int(analog_samples.shape[1]//write_overhead)
                    for i in range(number_of_full_chunks):
                        start_ind = i*write_overhead
                        stop_ind = (i+1)*write_overhead
                        wfmxfile.write(analog_samples[channel_number][start_ind:stop_ind])
                    # write rest
                    rest_start_ind = number_of_full_chunks*write_overhead
                    wfmxfile.write(analog_samples[channel_number][rest_start_ind:])

                # create the byte values corresponding to the marker states
                # (\x01 for marker 1, \x02 for marker 2, \x03 for both)
                # and write them into a temporary file
                filepath = os.path.join(self.host_waveform_directory,
                                        name + '_Ch' + str(channel_number+1) + '_digi' + '.tmp')

                with open(filepath, 'ab') as tmpfile:
                    if digital_samples.shape[0] <= (2*channel_number):
                        # no digital channels to write for this analog channel
                        pass
                    elif digital_samples.shape[0] == (2*channel_number + 1):
                        # one digital channels to write for this analog channel
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
                        # two digital channels to write for this analog channel
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
                for channel_number in range(analog_samples.shape[0]):
                    tmp_filepath = os.path.join(self.host_waveform_directory,
                                                name + '_Ch' + str(channel_number+1) + '_digi' + '.tmp')

                    wfmx_filepath = os.path.join(self.host_waveform_directory,
                                                 name + '_Ch' + str(channel_number+1) + '.WFMX')
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

        elif self.current_sample_mode == self.sample_mode['wfm-file']:

            # IMPORTANT: These numbers build the header in the wfm file. Needed
            # by the device program to understand wfm file. If it is wrong,
            # AWG will not be able to understand the written file.

            # The pure waveform has the number 1000, indicating that it is a
            # *.wfm file. For sequence mode e.g. the number would be 3001 or
            # 3002, depending on the number of channels in the sequence mode.
            # (The last number indicates the channel numbers).
            # Next line after the header tells the number of bins of the
            # waveform file.
            # After this number a 14bit binary representation of the channel
            # and the marker are followed.


            for channel_index, channel_arr in enumerate(analog_samples):

                filename = name + '_ch' + str(channel_index + 1) + '.wfm'

                created_files.append(filename)

                filepath = os.path.join(self.host_waveform_directory, filename)

                # delete any previous file by just open it for writing process:
                if is_first_chunk:
                    with open(filepath, 'wb') as f:
                        pass

                with open(filepath, 'ab') as wfm_file:

                    if is_first_chunk:
                        # write the first line, which is the header file, if first chunk is passed:
                        num_bytes = str(len(digital_samples[channel_index * 2]) * 5)
                        num_digits = str(len(num_bytes))
                        header = str.encode('MAGIC 1000\r\n#' + num_digits + num_bytes)
                        wfm_file.write(header)

                    # now write at once the whole file in binary representation:

                    # convert the presampled numpy array of the analog channels
                    # to a float number represented by 8bits:
                    shape_for_wavetmp = np.shape(channel_arr)[0]
                    wavetmp = np.zeros(shape_for_wavetmp * 5, dtype='c')
                    wavetmp = wavetmp.reshape((-1, 5))

                    wavetmp[:, :4] = np.frombuffer(memoryview(channel_arr / 4), dtype='c').reshape(
                        (-1, 4))

                    # The previously created array wavetmp contains one additional column, where
                    # the marker states will be written into:
                    marker = digital_samples[channel_index * 2] + digital_samples[
                                                                      channel_index * 2 + 1] * 2
                    marker_byte = np.array([self._marker_byte_dict[m] for m in marker], dtype='c')
                    wavetmp[:, -1] = marker_byte

                    # now write everything to file:
                    wfm_file.write(wavetmp.tobytes())

                    if is_last_chunk:
                        # the footer encodes the sample rate, which was used for that file:
                        footer = str.encode('CLOCK {:16.10E}\r\n'.format(self.get_sample_rate()))
                        wfm_file.write(footer)

        else:
            self.logMsg('Sample mode not defined for the given pulser hardware.'
                        '\nEither the mode does not exist or the sample mode is'
                        'not assigned properly. Correct that!', msgType='error')

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

        filename = name + '.seq'
        filepath = os.path.join(self.host_waveform_directory, filename)

        with open(filepath, 'wb') as seq_file:

            # write the header:
            # determine the used channels according to how much files where created:
            channels = len(sequence_param[0]['name'])
            lines = len(sequence_param)
            seq_file.write('MAGIC 300{0:d}\r\n'.format(channels).encode('UTF-8'))
            seq_file.write('LINES {0:d}\r\n'.format(lines).encode('UTF-8'))

            # write main part:
            # in this order: 'waveform_name', repeat, wait, Goto, ejump
            for seq_param_dict in sequence_param:

                repeat = seq_param_dict['reps']
                trigger_wait = seq_param_dict['trigger_wait']
                go_to = seq_param_dict['go_to']
                event_jump_to = seq_param_dict['event_jump_to']

                # for one channel:
                if len(seq_param_dict['name']) == 1:
                    seq_file.write(
                        '"{0}", {1:d}, {2:d}, {3:d}, {4:d}\r\n'.format(seq_param_dict['name'][0],
                                                                       repeat,
                                                                       trigger_wait,
                                                                       go_to,
                                                                       event_jump_to).encode(
                            'UTF-8'))
                # for two channel:
                else:
                    seq_file.write('"{0}", "{1}", {2:d}, {3:d}, {4:d}, {5:d}\r\n'.format(
                        seq_param_dict['name'][0],
                        seq_param_dict['name'][1],
                        repeat,
                        trigger_wait,
                        go_to,
                        event_jump_to).encode('UTF-8'))

            # write the footer:
            table_jump = 'TABLE_JUMP' + 16 * ' 0,' + '\r\n'
            logic_jump = 'LOGIC_JUMP -1, -1, -1, -1,\r\n'
            jump_mode = 'JUMP_MODE TABLE\r\n'
            jump_timing = 'JUMP_TIMING ASYNC\r\n'
            strobe_option = 'STROBE 0\r\n'

            footer = table_jump + logic_jump + jump_mode + jump_timing + strobe_option

            seq_file.write(footer.encode('UTF-8'))

    def upload_asset(self, asset_name=None):
        """ Upload an already hardware conform file to the device.
            Does NOT load it into channels.

        @param name: string, name of the ensemble/seqeunce to be uploaded

        @return int: error code (0:OK, -1:error)

        If nothing is passed, method will be skipped.
        """
        if asset_name is None:
            self.logMsg('No asset name provided for upload!\nCorrect '
                        'that!\nCommand will be ignored.', msgType='warning')
            return -1

        saved_files = self._get_filenames_on_host()

        for filename in saved_files:
            if filename not in self.uploaded_files_list:
                if (asset_name+'.seq') in filename:
                    self.uploaded_files_list.append(filename)
                elif fnmatch(filename, asset_name+'_ch?.wfm'):
                    self.uploaded_files_list.append(filename)
                elif fnmatch(filename, asset_name+'_ch?.WFMX'):
                    self.uploaded_files_list.append(filename)
                elif fnmatch(filename, asset_name+'.mat'):
                    self.uploaded_files_list.append(filename)

        if asset_name not in self.uploaded_assets_list:
            self.uploaded_assets_list.append(asset_name)
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
        if asset_name in self.uploaded_assets_list:
            self.current_loaded_asset = asset_name
        return 0

    def clear_all(self):
        """ Clears all loaded waveform from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without storage capability
        (PulseBlaster, FPGA).
        """
        self.current_loaded_asset = None

        return

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

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate in a class variable, but instead
        retrieve the current sample rate directly from the device.
        """

        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device.

        Note: After setting the sampling rate of the device, retrieve it again
              for obtaining the actual set value and use that information for
              further processing.
        """

        self.sample_rate = sample_rate
        return self.sample_rate

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

        ampl = {}
        off = {}

        if (amplitude == []) and (offset == []):

            for a_ch in self.amplitude_list:
                ampl[a_ch] = self.amplitude_list[a_ch]

            for a_ch in self.offset_list:
                off[a_ch] = self.offset_list[a_ch]

        else:
            for a_ch in amplitude:
                ampl[a_ch] = self.amplitude_list[a_ch]

            for a_ch in offset:
                off[a_ch] = self.offset_list[a_ch]

        return ampl, off

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

        for a_ch in amplitude:
            self.amplitude_list[a_ch] = amplitude[a_ch]

        for a_ch in offset:
            self.offset_list[a_ch] = offset[a_ch]

        return self.get_analog_level(amplitude=list(amplitude), offset=list(offset))

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

        low_val = {}
        high_val = {}

        if (low == []) and (high == []):

            for d_ch in self.digital_low_list:
                low_val[d_ch] = self.digital_low_list[d_ch]

            for d_ch in self.digital_high_list:
                high_val[d_ch] = self.digital_high_list[d_ch]

        else:
            for d_ch in low:
                low_val[d_ch] = self.digital_low_list[d_ch]

            for d_ch in high:
                high_val[d_ch] = self.digital_high_list[d_ch]

        return low_val, high_val

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

        for d_ch in low:
            self.digital_low_list[d_ch] = low[d_ch]

        for d_ch in high:
            self.digital_high_list[d_ch] = high[d_ch]

        return self.get_digital_level(low=list(low), high=list(high))

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

        active_a_ch = {}
        active_d_ch = {}

        if (a_ch == []) and (d_ch == []):
            active_a_ch = self.active_channel[0]
            active_d_ch = self.active_channel[1]
        else:
            for ana_chan in a_ch:
                active_a_ch[ana_chan] = self.active_channel[0][ana_chan]
            for digi_chan in d_ch:
                active_d_ch[digi_chan] = self.active_channel[1][digi_chan]

        return active_a_ch, active_d_ch

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
        for channel in a_ch:
            self.active_channel[0][channel] = a_ch[channel]

        for channel in d_ch:
            self.active_channel[1][channel] = d_ch[channel]

        return self.get_active_channels(a_ch=list(a_ch), d_ch=list(d_ch))

    def get_uploaded_assets_names(self):
        """ Retrieve the names of all uploaded assets on the device.

        @return list: List of all uploaded asset name strings in the current
                      device directory. This is no list of the file names.

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        return self.uploaded_assets_list

    def get_saved_assets_names(self):
        """ Retrieve the names of all sampled and saved assets on the host PC.
        This is no list of the file names.

        @return list: List of all saved asset name strings in the current
                      directory of the host PC.
        """

        # list of all files in the waveform directory ending with .mat or .WFMX
        file_list = self._get_filenames_on_host()

        # exclude the channel specifier for multiple analog channels and create return list
        saved_assets = []
        for name in file_list:
            if fnmatch(name, '*_Ch?.WFMX') or fnmatch(name, '*_ch?.wfm'):
                asset_name = name.rsplit('_', 1)[0]
                if asset_name not in saved_assets:
                    saved_assets.append(asset_name)
            elif fnmatch(name, '*.mat'):
                asset_name = name.rsplit('.', 1)[0]
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
        if asset_name in self.uploaded_assets_list:
            self.uploaded_assets_list.remove(asset_name)
            if asset_name == self.current_loaded_asset:
                self.clear_all()

        files_to_delete = []
        for filename in self.uploaded_files_list:
            if fnmatch(filename, asset_name+'.mat') or fnmatch(filename, asset_name+'_Ch?.WFMX') or fnmatch(filename, asset_name+'_ch?.wfm'):
                files_to_delete.append(filename)

        for filename in files_to_delete:
            self.uploaded_files_list.remove(filename)
        return 0

    def set_sequence_directory(self, dir_path):
        """ Change the directory where the assets are stored on the device.

        @param string dir_path: The target directory

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without changeable file structure
        (PulseBlaster, FPGA).
        """
        self.asset_directory = dir_path
        return 0

    def get_asset_dir_on_device(self):
        """ Ask for the directory where the hardware conform files are stored on
            the device.

        @return string: The current file directory

        Unused for digital pulse generators without changeable file structure
        (PulseBlaster, FPGA).
        """
        return self.asset_directory

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Unused for pulse generator hardware other than an AWG.
        """

        return self.interleave

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        @return bool: actual interleave status (True: ON, False: OFF)

        Note: After setting the interleave of the device, retrieve the
              interleave again and use that information for further processing.

        Unused for pulse generator hardware other than an AWG.
        """

        self.interleave = state
        return self.get_interleave()

    def tell(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """

        self.logMsg('It is so nice that you talk to me and told me "{0}"; as '
                    'a dummy it is very dull out here! :) '.format(command),
                    msgType='status')

        return 0

    def ask(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """

        self.logMsg("Dude, I'm a dummy! Your question '{0}' is way to "
                    "complicated for me :D !".format(question),
                    msgType='status')

        return 'I am a dummy!'

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.logMsg('Dummy cannot be reseted!', msgType='status')

        return 0

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        return True

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
        filename_list = [f for f in os.listdir(self.host_waveform_directory) if (f.endswith('.WFMX') or f.endswith('.mat') or f.endswith('.wfm'))]
        return filename_list
