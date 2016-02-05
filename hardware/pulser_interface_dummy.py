# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware interface dummy for pulsing devices.

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

from core.base import Base
from hardware.pulser_interface import PulserInterface
import os
import numpy as np
import hdf5storage
from hardware.WFMX_header import WFMX_header
import struct

class PulserInterfaceDummy(Base, PulserInterface):
    """
    Interface class to pass

    Be careful in adjusting the method names in that class, since some of them
    are also connected to the mwsourceinterface (to give the AWG the possibility
    to act like a microwave source).
    """
    _modclass = 'PulserInterfaceDummy'
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
        self.current_sample_mode = self.sample_mode['wfmx-file']

        self.awg_waveform_directory = '/waves'

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']

            if not os.path.exists(self.pulsed_file_dir):

                homedir = self.get_home_dir()
                self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files\\')
                self.logMsg('The directort defined in "pulsed_file_dir" in the'
                        'config for SequenceGeneratorLogic class does not '
                        'exist!\nThe default home directory\n{0}\n will be '
                        'taken instead.'.format(self.pulsed_file_dir), msgType='warning')
        else:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files\\')
            self.logMsg('No directory with the attribute "pulsed_file_dir"'
                        'is defined for the SequenceGeneratorLogic!\nThe '
                        'default home directory\n{0}\n will be taken '
                        'instead.'.format(self.pulsed_file_dir), msgType='warning')

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')

        # self.host_waveform_directory = 'C:\\Users\\astark\\Dropbox\\Doctorwork\\Software\\QuDi\\trunk\\waveforms\\'
        # self.host_waveform_directory = 'C:\\'

        self.connected = False
        self.amplitude = 0.25
        self.sample_rate = 25e9
        self.uploaded_asset_list = []
        self.current_loaded_asset = None
        self.is_output_enabled = True

        self.pp_voltage = 0.25

        # settings for remote access on the AWG PC
        self.sequence_directory = '\\waves'

        # AWG5002C has possibility for sequence output
        self.use_sequencer = True

        self.active_channel = (2,4)
        self.interleave = False

        self.current_status =  0    # that means off, not running.

        self._marker_byte_dict = { 0:b'\x00',1:b'\x01', 2:b'\x02', 3:b'\x03'}

    def activation(self, e):
        self.connected = True


    def deactivation(self, e):
        self.connected = False

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Pulsing device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints (e.g. sample_rate, amplitude,
        total_length_bins, channel_config, ...) related to the pulse generator
        hardware to the caller.
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        and the key 'channel_map' indicates all possible combinations in usage
        for this device.

        The possible keys in the constraint are defined here in the interface
        file. If the hardware does not support the values for the constraints,
        then insert just None.
        If you are not sure about the meaning, look in other hardware files
        to get an impression.
        """


        constraints = {}
        # (min, max, incr) in samples/second:
        constraints['sample_rate'] = (10.0e6, 600.0e6, 1)
        # (min, max, res) in Volt-peak-to-peak:
        constraints['amplitude_analog'] = (0.02, 4.5, 0.001)
        # (min, max, res, range_min, range_max)
        # min, max and res are in Volt, range_min and range_max in
        # Volt-peak-to-peak:
        constraints['amplitude_digital'] = (-2.0, 5.4, 0.01, 0.2, 7.4)
        # (min, max, granularity) in samples for one waveform:
        constraints['waveform_length'] = (1, 32400000, 1)
        # (min, max, inc) in number of waveforms in system
        constraints['waveform_number'] = (1, 32000, 1)
        # (min, max, inc) number of subsequences within a sequence:
        constraints['subsequence_number'] = (1, 8000, 1)
        # number of possible elements within a sequence
        constraints['sequence_elements'] = (1, 4000, 1)
        # (min, max, incr) in Samples:
        constraints['total_length_bins'] = (1, 32e6, 1)
        # (analogue, digital) possible combination in given channels:
        constraints['channel_config'] = [(0,1), (0,2), (0,3), (0,4), (0,5),
                                         (0,6), (0,7), (0,8), (1,2), (2,4)]
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:stopped, -1:error, 1:running)
        """
        self.current_status = 1
        return self.current_status

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:stopped, -1:error, 1:running)
        """
        self.current_status = 0
        return self.current_status

    def _write_to_file(self, name, ana_samples, digi_samples, sample_rate,
                       pp_voltage):
        if self.current_sample_mode == self.sample_mode['matlab']:
            matcontent = {}
            matcontent[u'Waveform_Name_1'] = name # each key must be a unicode string
            matcontent[u'Waveform_Data_1'] = ana_samples[0]
            matcontent[u'Waveform_Sampling_Rate_1'] = sample_rate
            matcontent[u'Waveform_Amplitude_1'] = pp_voltage

            if ana_samples.shape[0] == 2:
                matcontent[u'Waveform_Name_1'] = name + '_Ch1'
                matcontent[u'Waveform_Name_2'] = name + '_Ch2'
                matcontent[u'Waveform_Data_2'] = ana_samples[1]
                matcontent[u'Waveform_Sampling_Rate_2'] = sample_rate
                matcontent[u'Waveform_Amplitude_2'] = pp_voltage

            if digi_samples.shape[0] >= 1:
                matcontent[u'Waveform_M1_1'] = digi_samples[0]
            if digi_samples.shape[0] >= 2:
                matcontent[u'Waveform_M2_1'] = digi_samples[1]
            if digi_samples.shape[0] >= 3:
                matcontent[u'Waveform_M1_2'] = digi_samples[2]
            if digi_samples.shape[0] >= 4:
                matcontent[u'Waveform_M2_2'] = digi_samples[3]

            # create file in current directory
            filename = name +'.mat'
            hdf5storage.write(matcontent, '.', filename, matlab_compatible=True)
            # check if file already exists and overwrite it
            if os.path.isfile(self.host_waveform_directory + filename):
                os.remove(self.host_waveform_directory + filename)
            os.rename(os.getcwd() + '\\' + name +'.mat', self.host_waveform_directory + filename)
        elif self.current_sample_mode == self.sample_mode['wfmx-file']:
            # create WFMX header and save each line of text in a list. Delete the temporary .xml file afterwards.
            header_obj = WFMX_header(sample_rate, pp_voltage, 0, digi_samples.shape[1])
            header_obj.create_xml_file()
            with open('header.xml','r') as header:
                header_lines = header.readlines()
            os.remove('header.xml')

            for channel_number in range(ana_samples.shape[0]):
                print(ana_samples.shape[0])
                # create .WFMX-file for each channel.
                filepath = self.host_waveform_directory + name + '_Ch' + str(channel_number+1) + '.WFMX'
                with open(filepath, 'wb') as wfmxfile:
                    # write header
                    for line in header_lines:
                        wfmxfile.write(bytes(line, 'UTF-8'))
                    # append analogue samples in binary format. One sample is 4 bytes (np.float32).
                    # write in chunks if array is very big to avoid large temporary copys in memory
                    print(ana_samples.shape[1]//1e6)
                    number_of_full_chunks = int(ana_samples.shape[1]//1e6)
                    print('number of 1e6-sample-chunks: ' + str(number_of_full_chunks))
                    for i in range(number_of_full_chunks):
                        start_ind = i*1e6
                        stop_ind = (i+1)*1e6
                        wfmxfile.write(ana_samples[channel_number][start_ind:stop_ind])
                    # write rest
                    rest_start_ind = number_of_full_chunks*1e6
                    print('rest size: ' + str(ana_samples.shape[1]-rest_start_ind))
                    wfmxfile.write(ana_samples[channel_number][rest_start_ind:])
                    # create the byte values corresponding to the marker states (\x01 for marker 1, \x02 for marker 2, \x03 for both)
                    print('number of digital channels: ' + str(digi_samples.shape[0]))
                    if digi_samples.shape[0] <= (2*channel_number):
                        # no digital channels to write for this analogue channel
                        pass
                    elif digi_samples.shape[0] == (2*channel_number + 1):
                        # one digital channels to write for this analogue channel
                        for i in range(number_of_full_chunks):
                            start_ind = i*1e6
                            stop_ind = (i+1)*1e6
                            # append digital samples in binary format. One sample is 1 byte (np.uint8).
                            wfmxfile.write(digi_samples[2*channel_number][start_ind:stop_ind])
                        # write rest of digital samples
                        rest_start_ind = number_of_full_chunks*1e6
                        wfmxfile.write(digi_samples[2*channel_number][rest_start_ind:])
                    elif digi_samples.shape[0] >= (2*channel_number + 2):
                        # two digital channels to write for this analogue channel
                        for i in range(number_of_full_chunks):
                            start_ind = i*1e6
                            stop_ind = (i+1)*1e6
                            temp_markers = np.add(np.left_shift(digi_samples[2*channel_number + 1][start_ind:stop_ind].astype('uint8'),1), digi_samples[2*channel_number][start_ind:stop_ind])
                            # append digital samples in binary format. One sample is 1 byte (np.uint8).
                            wfmxfile.write(temp_markers)
                        # write rest of digital samples
                        rest_start_ind = number_of_full_chunks*1e6
                        temp_markers = np.add(np.left_shift(digi_samples[2*channel_number + 1][rest_start_ind:].astype('uint8'),1), digi_samples[2*channel_number][rest_start_ind:])
                        wfmxfile.write(temp_markers)

        elif self.current_sample_mode == self.sample_mode['wfm-file']:

            # IMPORTANT: These numbers build the header in the wfm file. Needed
            # by the device program to understand wfm file. If it is wrong,
            # AWG will not be able to understand the written file.

            # The pure waveform has the number 1000, idicating that it is a
            # *.wfm file. For sequence mode e.g. the number would be 3001 or
            # 3002, depending on the number of channels in the sequence mode.
            # (The last number indicates the channel numbers).
            # Next line after the header tells the number of bins of the
            # waveform file.
            # After this number a 14bit binary representation of the channel
            # and the marker are followed.




            for channel_index, channel_arr in enumerate(ana_samples):

                filename = name+'_ch'+str(channel_index+1) + '.wfm'

                with open(self.host_waveform_directory + filename, 'wb') as wfm_file:

                    num_bytes = str(len(digi_samples[channel_index*2])*5)
                    num_digits = str(len(num_bytes))
                    header = str.encode('MAGIC 1000\r\n#'+num_digits+num_bytes)

                    wfm_file.write(header)

                    # for value_index, value in enumerate(channel_arr):
                    #     byte_val = struct.pack('f',value)   # convert float to byte
                    #                                         # representation
                    #
                    #
                    #
                    #     marker1 = digi_samples[channel_index*2][value_index]
                    #     [value_index]
                    #
                    #     byte_marker = struct.pack('f',marker1+marker2)
                    #
                    #     wfm_file.write(byte_marker+byte_val)

                    shape_for_wavetmp = np.shape(channel_arr)[0]
                    wavetmp = np.zeros(shape_for_wavetmp*5,dtype='c')
                    wavetmp = wavetmp.reshape((-1,5))
                    # wavetmp[:,:4] = np.frombuffer(bytes(channel_arr),dtype='c').reshape((-1,4))
                    wavetmp[:,:4] = np.frombuffer(memoryview(channel_arr/4),dtype='c').reshape((-1,4))

                    # marker1 =
                    # marker2 = digi_samples[channel_index*2+1]

                    # marker = np.zeros(len(marker1),dtype='c')

                    #FIXME: This is a very very ugly and inefficient way of
                    #       appending the marker array. A much nicer way
                    #       should be implemented!!!

                    marker = digi_samples[channel_index*2] + digi_samples[channel_index*2+1]*2

                    marker_byte = np.array([self._marker_byte_dict[m] for m in marker], dtype='c')
                    # for index in range(len(marker1)):
                    #     test_val = marker1[index] + marker2[index]
                    #     if marker1[index] and marker2[index]:
                    #         wavetmp[index,-1] = b'\x03'
                    #     elif marker1[index] and not marker2[index]:
                    #         wavetmp[index,-1] = b'\x01'
                    #     elif not marker1[index] and marker2[index]:
                    #         wavetmp[index,-1] = b'\x02'
                    #     else:
                    #         wavetmp[index,-1] = b'\x00'

                    # [marker]



                    # wavetmp[:,-1] = np.repeat(marker,len(wavetmp))
                    wavetmp[:,-1] = marker_byte

                    wfm_file.write(wavetmp.tobytes())

                    footer = str.encode('CLOCK {:16.10E}\r\n'.format(sample_rate))
                    wfm_file.write(footer)



        else:
            self.logMsg('Sample mode not defined for the given pulser hardware.'
                        '\nEither the mode does not exist or the sample mode is'
                        'not assigned properly. Correct that!', msgType='error')

        return 0

    def write_chunk_to_file(self, name, analogue_samples_chunk,
                            digital_samples_chunk, is_first_chunk,
                            is_last_chunk):
        """
        Appends a sampled chunk of a whole waveform to a file. Create the file
        if it is the first chunk.

        @param name: string representing the name of the sampled ensemble
        @param analogue_samples_chunk: float32 numpy ndarray containing the
                                       samples for the analogue channels.
        @param digital_samples_chunk: bool numpy ndarray containing the samples
                                      for the digital channels.
        @param is_first_chunk: bool indicating if the current chunk is the
                               first write to this file.
        @param is_last_chunk: bool indicating if the current chunk is the last
                              write to this file.
        @return: error code (0: OK, -1: error)
        """
        # if it is the first chunk, create the .WFMX file with header.
        if is_first_chunk:
            # create header
            header_obj = WFMX_header(self.sample_rate, self.pp_voltage, 0,
                                     digital_samples_chunk.shape[1])

            header_obj.create_xml_file()
            with open('header.xml','r') as header:
                header_lines = header.readlines()
            os.remove('header.xml')
            # create .WFMX-file for each channel.
            for channel_number in range(analogue_samples_chunk.shape[0]):
                filepath = self.host_waveform_directory + name + '_Ch' + str(channel_number+1) + '.WFMX'
                with open(filepath, 'wb') as wfmxfile:
                    # write header
                    for line in header_lines:
                        wfmxfile.write(bytes(line, 'UTF-8'))

        # append analogue samples to the .WFMX files of each channel. Write
        # digital samples in temporary files.
        for channel_number in range(analogue_samples_chunk.shape[0]):
            # append analogue samples chunk to .WFMX file
            filepath = self.host_waveform_directory + name + '_Ch' + str(channel_number+1) + '.WFMX'
            with open(filepath, 'ab') as wfmxfile:
                # append analogue samples in binary format. One sample is 4
                # bytes (np.float32). Write in chunks if array is very big to
                # avoid large temporary copys in memory
                number_of_full_chunks = int(analogue_samples_chunk.shape[1]//1e6)
                print('number of 1e6-sample-chunks: ' + str(number_of_full_chunks))
                for i in range(number_of_full_chunks):
                    start_ind = i*1e6
                    stop_ind = (i+1)*1e6
                    wfmxfile.write(analogue_samples_chunk[channel_number][start_ind:stop_ind])
                # write rest
                rest_start_ind = number_of_full_chunks*1e6
                print('rest size: ' + str(analogue_samples_chunk.shape[1]-rest_start_ind))
                wfmxfile.write(analogue_samples_chunk[channel_number][rest_start_ind:])

            # create the byte values corresponding to the marker states
            # (\x01 for marker 1, \x02 for marker 2, \x03 for both)
            # and write them into a temporary file
            filepath = self.host_waveform_directory + name + '_Ch' + str(channel_number+1) + '_digi' + '.tmp'
            with open(filepath, 'ab') as tmpfile:
                if digital_samples_chunk.shape[0] <= (2*channel_number):
                    # no digital channels to write for this analogue channel
                    pass
                elif digital_samples_chunk.shape[0] == (2*channel_number + 1):
                    # one digital channels to write for this analogue channel
                    for i in range(number_of_full_chunks):
                        start_ind = i*1e6
                        stop_ind = (i+1)*1e6
                        # append digital samples in binary format. One sample
                        # is 1 byte (np.uint8).
                        tmpfile.write(digital_samples_chunk[2*channel_number][start_ind:stop_ind])
                    # write rest of digital samples
                    rest_start_ind = number_of_full_chunks*1e6
                    tmpfile.write(digital_samples_chunk[2*channel_number][rest_start_ind:])
                elif digital_samples_chunk.shape[0] >= (2*channel_number + 2):
                    # two digital channels to write for this analogue channel
                    for i in range(number_of_full_chunks):
                        start_ind = i*1e6
                        stop_ind = (i+1)*1e6
                        temp_markers = np.add(np.left_shift(digital_samples_chunk[2*channel_number + 1][start_ind:stop_ind].astype('uint8'),1), digital_samples_chunk[2*channel_number][start_ind:stop_ind])
                        # append digital samples in binary format. One sample
                        # is 1 byte (np.uint8).
                        tmpfile.write(temp_markers)
                    # write rest of digital samples
                    rest_start_ind = number_of_full_chunks*1e6
                    temp_markers = np.add(np.left_shift(digital_samples_chunk[2*channel_number + 1][rest_start_ind:].astype('uint8'),1), digital_samples_chunk[2*channel_number][rest_start_ind:])
                    tmpfile.write(temp_markers)

        # append the digital sample tmp file to the .WFMX file and delete the
        # .tmp files if it was the last chunk to write.
        if is_last_chunk:
            for channel_number in range(analogue_samples_chunk.shape[0]):
                tmp_filepath = self.host_waveform_directory + name + '_Ch' + str(channel_number+1) + '_digi' + '.tmp'
                wfmx_filepath = self.host_waveform_directory + name + '_Ch' + str(channel_number+1) + '.WFMX'
                with open(wfmx_filepath, 'ab') as wfmxfile:
                    with open(tmp_filepath, 'rb') as tmpfile:
                        # read and write files in max. 64kB chunks to reduce
                        # memory usage
                        while True:
                            tmp_data = tmpfile.read(65536)
                            if not tmp_data:
                                break
                            wfmxfile.write(tmp_data)
                # delete tmp file
                os.remove(tmp_filepath)
        return 0

    def download_waveform(self, waveform, write_to_file = True):
        """ Convert the pre-sampled numpy array to a specific hardware file.

        @param Waveform() waveform: The raw sampled pulse sequence.
        @param bool write_to_file: Flag to indicate if the samples should be
                                   written to a file (= True) or uploaded
                                   directly to the pulse generator channels
                                   (= False).

        @return int: error code (0:OK, -1:error)

        Brings the numpy arrays containing the samples in the Waveform() object
        into a format the hardware understands. Optionally this is then saved
        in a file. Afterwards they get downloaded to the Hardware.
        """

        # append to the loaded sequence list.
        self._write_to_file(waveform.name, waveform.analogue_samples,
                            waveform.digital_samples, waveform.sample_rate,
                            waveform.pp_voltage)

        if waveform.name not in self.uploaded_asset_list:
            self.uploaded_asset_list.append(waveform.name)
        return 0

    def send_file(self, filepath):
        """ Sends an already hardware specific waveform file to the pulse
            generators waveform directory.

        @param string filepath: The file path of the source file

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """

        return 0

    def load_asset(self, asset_name, channel=None):
        """ Loads a sequence or waveform to the specified channel of the pulsing device.

        @param str asset_name: The name of the asset to be loaded
        @param int channel: The channel for the sequence to be loaded into if
                            not already specified in the sequence itself

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        if asset_name in self.uploaded_asset_list:
            self.current_loaded_asset = asset_name
        return 0

    def clear_all(self):
        """ Clears all loaded waveform from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without storage capability
        (PulseBlaster, FPGA).
        """
        self.current_loaded_file = None

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

        return (self.current_status, status_dic)

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return foat: the sample rate returned from the device (-1:error)
        """
        self.sample_rate = sample_rate
        return self.sample_rate

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """

        return self.sample_rate

    def set_pp_voltage(self, channel, voltage):
        """ Set the peak-to-peak voltage of the pulse generator hardware
        analogue channels. Unused for purely digital hardware without logic
        level setting capability (DTG, FPGA, etc.).

        @param int channel: The channel to be reconfigured
        @param float voltage: The peak-to-peak amplitude the channel should be
                              set to (in V)

        @return int: error code (0:OK, -1:error)
        """
        self.amplitude = voltage
        return 0

    def get_pp_voltage(self, channel):
        """ Get the peak-to-peak voltage of the pulse generator hardware
            analogue channels.

        @param int channel: The channel to be checked

        @return float: The peak-to-peak amplitude the channel is set to (in V)

        Unused for purely digital hardware without logic level setting
        capability (FPGA, etc.).
        """
        return self.amplitude

    def set_active_channels(self, d_ch=0, a_ch=0):
        """ Set the active channels for the pulse generator hardware.

        @param int d_ch: number of active digital channels
        @param int a_ch: number of active analogue channels

        @return int: error code (0:OK, -1:error)
        """
        self.active_channel = (a_ch, d_ch)
        return 0

    def get_active_channels(self):
        """ Get the active channels of the pulse generator hardware.

        @return (int, int): number of active channels (analogue, digital)
        """

        return self.active_channel

    def get_sequence_names(self):
        """ Retrieve the names of all downloaded sequences on the device.

        @return list: List of sequence name strings

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """

        return self.uploaded_asset_list

    def delete_sequence(self, seq_name):
        """ Delete a sequence with the passed seq_name from the device memory.

        @param str seq_name: The name of the sequence to be deleted

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """

        if seq_name in self.uploaded_asset_list:
            self.uploaded_asset_list.remove(seq_name)
            if seq_name == self.current_loaded_file:
                self.clear_channel()
        return 0

    def set_sequence_directory(self, dir_path):
        """ Change the directory where the sequences are stored on the device.

        @param string dir_path: The target directory

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        self.sequence_directory = dir_path
        return 0

    def get_sequence_directory(self):
        """ Ask for the directory where the sequences are stored on the device.

        @return string: The current sequence directory

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        return self.sequence_directory

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to (True: ON, False: OFF)

        @return int: error code (0:OK, -1:error)

        Unused for pulse generator hardware other than an AWG.
        """

        # no interleave is possible
        return self.interleave

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Unused for pulse generator hardware other than an AWG.
        """

        return self.interleave


    def tell(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """

        self.logMsg('It is so nice that you talk to me and told me "{0}", as '
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
        """Reset the device.

        @return int: error code (0:OK, -1:error)
        """

        return 0


    def _get_dir_for_name(self, name):
        """ Get the path to the pulsed sub-directory 'name'.

        @param name: string, name of the folder
        @return: string, absolute path to the directory with folder 'name'.
        """

        path = self.pulsed_file_dir + name
        if not os.path.exists(path):
            os.makedirs(os.path.abspath(path))

        return os.path.abspath(path) + '\\'