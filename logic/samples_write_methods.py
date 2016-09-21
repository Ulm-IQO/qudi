# -*- coding: utf-8 -*-

"""
This file contains the Qudi methods to create hardware compatible files out of sampled pulse
sequences or pulse ensembles.

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
import numpy as np
from collections import OrderedDict
from lxml import etree as ET


class SamplesWriteMethods():
    """
    Collection of write-to-file methods used to create hardware compatible files for the pulse
    generator out of sample arrays.
    """
    def __init__(self):
        # If you want to define a new file format, make a new method and add the
        # reference to this method to the _write_to_file dictionary:
        self._write_to_file = OrderedDict()
        self._write_to_file['wfm'] = self._write_wfm
        self._write_to_file['wfmx'] = self._write_wfmx
        self._write_to_file['seq'] = self._write_seq
        self._write_to_file['seqx'] = self._write_seqx
        self._write_to_file['fpga'] = self._write_fpga
        return

    def _write_wfmx(self, name, analog_samples, digital_samples, total_number_of_samples,
                    is_first_chunk, is_last_chunk):
        """
        Appends a sampled chunk of a whole waveform to a wfmx-file. Create the file
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
        @param total_number_of_samples: int, The total number of samples in the
                                        entire waveform. Has to be known it advance.
        @param is_first_chunk: bool, indicates if the current chunk is the
                               first write to this file.
        @param is_last_chunk: bool, indicates if the current chunk is the last
                              write to this file.

        @return list: the list contains the string names of the created files for the passed
                      presampled arrays
        """
        # record the name of the created files
        created_files = []

        # The overhead of the write process in bytes.
        # Making this value bigger will result in a faster write process
        # but consumes more memory
        write_overhead_bytes = 1024*1024*256 # 256 MB
        # The overhead of the write process in number of samples
        write_overhead_samples = write_overhead_bytes//4

        # analyze the activation_config and extract analogue and digital channel numbers
        ana_chnl_numbers = [int(chnl.split('ch')[-1]) for chnl in self.activation_config if
                            'a_ch' in chnl]
        digi_chnl_numbers = [int(chnl.split('ch')[-1]) for chnl in self.activation_config if
                            'd_ch' in chnl]

        # if it is the first chunk, create the .WFMX file with header.
        if is_first_chunk:
            # create header
            self._create_xml_file(total_number_of_samples, self.temp_dir)
            # read back the header xml-file and delete it afterwards
            temp_file = os.path.join(self.temp_dir, 'header.xml')
            with open(temp_file, 'r') as header:
                header_lines = header.readlines()
            os.remove(temp_file)

            # create wfmx-file for each analog channel
            for channel in ana_chnl_numbers:
                filename = name + '_ch' + str(channel) + '.wfmx'
                created_files.append(filename)

                filepath = os.path.join(self.waveform_dir, filename)

                with open(filepath, 'wb') as wfmxfile:
                    # write header
                    for line in header_lines:
                        wfmxfile.write(bytes(line, 'UTF-8'))

        # append analog samples to the .WFMX files of each channel. Write
        # digital samples in temporary files.
        for i, channel in enumerate(ana_chnl_numbers):
            # append analog samples chunk to .WFMX file
            filepath = os.path.join(self.waveform_dir, name + '_ch' + str(channel) + '.wfmx')
            with open(filepath, 'ab') as wfmxfile:
                # append analog samples in binary format. One sample is 4
                # bytes (np.float32). Write in chunks if array is very big to
                # avoid large temporary copys in memory
                number_of_full_chunks = int(analog_samples.shape[1]//write_overhead_samples)
                for start_ind in np.arange(0, number_of_full_chunks * write_overhead_samples,
                                           write_overhead_samples):
                    stop_ind = start_ind+write_overhead_samples
                    wfmxfile.write(analog_samples[i][start_ind:stop_ind])
                # write rest
                rest_start_ind = number_of_full_chunks*write_overhead_samples
                wfmxfile.write(analog_samples[i][rest_start_ind:])

            # create the byte values corresponding to the marker states
            # (\x01 for marker 1, \x02 for marker 2, \x03 for both)
            # and write them into a temporary file
            filepath = os.path.join(self.temp_dir, name + '_ch' + str(channel) + '_digi' + '.tmp')
            with open(filepath, 'ab') as tmpfile:
                if (channel*2)-1 not in digi_chnl_numbers and channel*2 not in digi_chnl_numbers:
                    # no digital channels to write for this analog channel
                    pass
                elif (channel*2)-1 in digi_chnl_numbers and channel*2 not in digi_chnl_numbers:
                    # Only marker one is active for this channel
                    digi_chnl_index = digi_chnl_numbers.index((channel * 2) - 1)
                    for start_ind in np.arange(0, number_of_full_chunks * write_overhead_bytes,
                                               write_overhead_bytes):
                        stop_ind = start_ind + write_overhead_bytes
                        # append digital samples in binary format. One sample
                        # is 1 byte (np.uint8).
                        tmpfile.write(digital_samples[digi_chnl_index][start_ind:stop_ind])
                    # write rest of digital samples
                    rest_start_ind = number_of_full_chunks * write_overhead_bytes
                    tmpfile.write(digital_samples[digi_chnl_index][rest_start_ind:])
                elif (channel*2)-1 not in digi_chnl_numbers and channel*2 in digi_chnl_numbers:
                    # Only marker two is active for this channel
                    digi_chnl_index = digi_chnl_numbers.index(channel * 2)
                    for start_ind in np.arange(0, number_of_full_chunks * write_overhead_bytes,
                                               write_overhead_bytes):
                        stop_ind = start_ind + write_overhead_bytes
                        # append digital samples in binary format. One sample
                        # is 1 byte (np.uint8).
                        tmpfile.write(np.left_shift(
                            digital_samples[digi_chnl_index][start_ind:stop_ind].astype('uint8'),
                            1))
                    # write rest of digital samples
                    rest_start_ind = number_of_full_chunks * write_overhead_bytes
                    tmpfile.write(np.left_shift(
                        digital_samples[digi_chnl_index][rest_start_ind:].astype('uint8'), 1))
                else:
                    # Both markers are active for this channel
                    digi_chnl_index = digi_chnl_numbers.index(channel * 2)
                    for start_ind in np.arange(0, number_of_full_chunks * write_overhead_bytes,
                                               write_overhead_bytes):
                        stop_ind = start_ind + write_overhead_bytes
                        # append digital samples in binary format. One sample
                        # is 1 byte (np.uint8).
                        tmpfile.write(np.add(np.left_shift(
                            digital_samples[digi_chnl_index][start_ind:stop_ind].astype('uint8'),
                            1), digital_samples[digi_chnl_index - 1][start_ind:stop_ind]))
                    # write rest of digital samples
                    rest_start_ind = number_of_full_chunks * write_overhead_bytes
                    tmpfile.write(np.add(np.left_shift(
                        digital_samples[digi_chnl_index][rest_start_ind:].astype('uint8'), 1),
                                         digital_samples[digi_chnl_index - 1][rest_start_ind:]))

        # append the digital sample tmp file to the .WFMX file and delete the
        # .tmp files if it was the last chunk to write.
        if is_last_chunk:
            for channel in ana_chnl_numbers:
                tmp_filepath = os.path.join(self.temp_dir, name + '_ch' + str(channel) + '_digi' + '.tmp')
                wfmx_filepath = os.path.join(self.waveform_dir, name + '_ch' + str(channel) + '.WFMX')
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
        return created_files


    # TODO: Implement chunkwise writing
    # FIXME: This method seems to be in an early state and could be inefficient when larger
    # waveforms are written. Several temporary copys of the sample arrays are created.
    def _write_wfm(self, name, analog_samples, digital_samples, total_number_of_samples,
                    is_first_chunk, is_last_chunk):
        """
        Appends a sampled chunk of a whole waveform to a wfm-file. Create the file
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
        @param total_number_of_samples: int, The total number of samples in the
                                        entire waveform. Has to be known it advance.
        @param is_first_chunk: bool, indicates if the current chunk is the
                               first write to this file.
        @param is_last_chunk: bool, indicates if the current chunk is the last
                              write to this file.

        @return list: the list contains the string names of the created files for the passed
                      presampled arrays
        """
        # record the name of the created files
        created_files = []

        # analyze the activation_config and extract analogue and digital channel numbers
        ana_chnl_numbers = [int(chnl.split('ch')[-1]) for chnl in self.activation_config if
                            'a_ch' in chnl]
        digi_chnl_numbers = [int(chnl.split('ch')[-1]) for chnl in self.activation_config if
                             'd_ch' in chnl]

        # dict for marker creation
        _marker_byte_dict = {0: b'\x00', 1: b'\x01', 2: b'\x02', 3: b'\x03'}

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
        for channel_index, channel_number in enumerate(ana_chnl_numbers):

            filename = name + '_ch' + str(channel_number) + '.wfm'

            created_files.append(filename)

            filepath = os.path.join(self.waveform_dir, filename)

            with open(filepath, 'ab') as wfm_file:
                if is_first_chunk:
                    # write the first line, which is the header file, if first chunk is passed:
                    num_bytes = str(int(digital_samples.shape[1] * 5))
                    num_digits = str(len(num_bytes))
                    header = str.encode('MAGIC 1000\r\n#' + num_digits + num_bytes)
                    wfm_file.write(header)

                # now write at once the whole file in binary representation:

                # convert the presampled numpy array of the analog channels
                # to a float number represented by 8bits:
                shape_for_wavetmp = analog_samples.shape[1]
                wavetmp = np.zeros(shape_for_wavetmp * 5, dtype='c')
                wavetmp = wavetmp.reshape((-1, 5))
                wavetmp[:, :4] = np.frombuffer(memoryview(analog_samples[channel_index] / 4),
                                               dtype='c').reshape((-1, 4))

                # The previously created array wavetmp contains one additional column, where
                # the marker states will be written into:
                # check if for this analogue channel markers are specified
                if (channel_number * 2 - 1) not in digi_chnl_numbers and (
                    channel_number * 2) not in digi_chnl_numbers:
                    # no digital channels to write for this analog channel
                    marker = np.zeros(digital_samples.shape[1], dtype='int32')
                elif (channel_number * 2 - 1) in digi_chnl_numbers and (
                    channel_number * 2) not in digi_chnl_numbers:
                    # Only marker one is active for this channel
                    digi_index = digi_chnl_numbers.index(channel_number * 2 - 1)
                    marker = digital_samples[digi_index].astype('int32')
                elif (channel_number * 2 - 1) not in digi_chnl_numbers and (
                    channel_number * 2) in digi_chnl_numbers:
                    # Only marker two is active for this channel
                    digi_index = digi_chnl_numbers.index(channel_number * 2)
                    marker = digital_samples[digi_index] * 2
                else:
                    # Both markers are active for this channel
                    marker = digital_samples[channel_index * 2] + digital_samples[
                                                                      channel_index * 2 + 1] * 2

                marker_byte = np.array([_marker_byte_dict[m] for m in marker], dtype='c')
                wavetmp[:, -1] = marker_byte

                # now write everything to file:
                wfm_file.write(wavetmp.tobytes())

                if is_last_chunk:
                    # the footer encodes the sample rate, which was used for that file:
                    footer = str.encode('CLOCK {0:16.10E}\r\n'.format(self.sample_rate))
                    wfm_file.write(footer)
        return created_files

    def _write_fpga(self, name, analog_samples, digital_samples, total_number_of_samples,
                    is_first_chunk, is_last_chunk):
        """
        Appends a sampled chunk of a whole waveform to a fpga-file. Create the file
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
        @param total_number_of_samples: int, The total number of samples in the
                                        entire waveform. Has to be known it advance.
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
        # FIXME: Also allow for single channel to be specified. Set all others to zero.
        if channel_number != 8:
            self.log.error('FPGA pulse generator needs 8 digital channels. '
                    '{0} is not allowed!'.format(channel_number))
            return -1

        # encode channels into FPGA samples (bytes)
        # check if the sequence length is an integer multiple of 32 bins
        if is_last_chunk and (total_number_of_samples % 32 != 0):
            # calculate number of zero timeslots to append
            number_of_zeros = 32 - (total_number_of_samples % 32)
            encoded_samples = np.zeros(chunk_length_bins + number_of_zeros, dtype='uint8')
            self.log.warning('FPGA pulse sequence length is no integer '
                    'multiple of 32 samples. Appending {0} zero-samples to '
                    'the sequence.'.format(number_of_zeros))
        else:
            encoded_samples = np.zeros(chunk_length_bins, dtype='uint8')

        for channel in range(channel_number):
            encoded_samples[:chunk_length_bins] += (2 ** channel) * np.uint8(
                digital_samples[channel])

        del digital_samples  # no longer needed

        # append samples to file
        filename = name + '.fpga'
        created_files.append(filename)

        filepath = os.path.join(self.waveform_dir, filename)
        with open(filepath, 'wb') as fpgafile:
            fpgafile.write(encoded_samples)

        return created_files

    def _write_seq(self, name, sequence_param):
        """
        Write a sequence to a seq-file.

        @param str name: name of the sequence to be created
        @param list sequence_param: a list of dict, which contains all the information, which
                                    parameters are to be taken to create a sequence. The dict will
                                    have at least the entry
                                        {'name': [<list_of_sampled_file_names>] }
                                    All other parameters, which can be used in the sequence are
                                    determined in the get_constraints method in the category
                                    'sequence_param'.

        In order to write sequence files a completely new method with respect to
        write_samples_to_file is needed.

        for AWG5000/7000 Series the following parameter will be used (are also present in the
        hardware constraints for the pulser):
            { 'name' : [<list_of_str_names>],
              'repetitions' : 0=infinity reps; int_num in [1:65536],
              'trigger_wait' : 0=False or 1=True,
              'go_to': 0=Nothing happens; int_num in [1:8000]
              'event_jump_to' : -1=to next; 0= nothing happens; int_num in [1:8000]
        """
        filename = name + '.seq'
        filepath = os.path.join(self.waveform_dir, filename)

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
                repeat = seq_param_dict['repetitions']
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

    # TODO: Implement this method.
    def _write_seqx(self, name, analog_samples, digital_samples, total_number_of_samples,
                   is_first_chunk, is_last_chunk):
        """
        Write a sequence to a seqx-file.

        @param str name: name of the sequence to be created
        @param list sequence_param: a list of dict, which contains all the information, which
                                    parameters are to be taken to create a sequence. The dict will
                                    have at least the entry
                                        {'name': [<list_of_sampled_file_names>] }
                                    All other parameters, which can be used in the sequence are
                                    determined in the get_constraints method in the category
                                    'sequence_param'.

        In order to write sequence files a completely new method with respect to
        write_samples_to_file is needed.

        for AWG5000/7000 Series the following parameter will be used (are also present in the
        hardware constraints for the pulser):
            { 'name' : [<list_of_str_names>],
              'repetitions' : 0=infinity reps; int_num in [1:65536],
              'trigger_wait' : 0=False or 1=True,
              'go_to': 0=Nothing happens; int_num in [1:8000]
              'event_jump_to' : -1=to next; 0= nothing happens; int_num in [1:8000]
        """
        pass

    def _create_xml_file(self, number_of_samples, temp_dir=''):
        """
        This function creates an xml file containing the header for the wfmx-file format using
        etree.
        """
        root = ET.Element('DataFile', offset='xxxxxxxxx', version="0.1")
        DataSetsCollection = ET.SubElement(root, 'DataSetsCollection',
                                           xmlns="http://www.tektronix.com")
        DataSets = ET.SubElement(DataSetsCollection, 'DataSets', version="1",
                                 xmlns="http://www.tektronix.com")
        DataDescription = ET.SubElement(DataSets, 'DataDescription')
        NumberSamples = ET.SubElement(DataDescription, 'NumberSamples')
        NumberSamples.text = str(int(number_of_samples))
        SamplesType = ET.SubElement(DataDescription, 'SamplesType')
        SamplesType.text = 'AWGWaveformSample'
        MarkersIncluded = ET.SubElement(DataDescription, 'MarkersIncluded')
        MarkersIncluded.text = 'true'
        NumberFormat = ET.SubElement(DataDescription, 'NumberFormat')
        NumberFormat.text = 'Single'
        Endian = ET.SubElement(DataDescription, 'Endian')
        Endian.text = 'Little'
        Timestamp = ET.SubElement(DataDescription, 'Timestamp')
        Timestamp.text = '2014-10-28T12:59:52.9004865-07:00'
        ProductSpecific = ET.SubElement(DataSets, 'ProductSpecific', name="")
        ReccSamplingRate = ET.SubElement(ProductSpecific, 'ReccSamplingRate', units="Hz")
        ReccSamplingRate.text = str(self.sample_rate)
        ReccAmplitude = ET.SubElement(ProductSpecific, 'ReccAmplitude', units="Volts")
        ReccAmplitude.text = str(0.5)
        ReccOffset = ET.SubElement(ProductSpecific, 'ReccOffset', units="Volts")
        ReccOffset.text = str(0)
        SerialNumber = ET.SubElement(ProductSpecific, 'SerialNumber')
        SoftwareVersion = ET.SubElement(ProductSpecific, 'SoftwareVersion')
        SoftwareVersion.text = '4.0.0075'
        UserNotes = ET.SubElement(ProductSpecific, 'UserNotes')
        OriginalBitDepth = ET.SubElement(ProductSpecific, 'OriginalBitDepth')
        OriginalBitDepth.text = 'EightBit'
        Thumbnail = ET.SubElement(ProductSpecific, 'Thumbnail')
        CreatorProperties = ET.SubElement(ProductSpecific, 'CreatorProperties',
                                          name='Basic Waveform')
        Setup = ET.SubElement(root, 'Setup')

        filepath = os.path.join(temp_dir, 'header.xml')

        ##### This command creates the first version of the file
        tree = ET.ElementTree(root)
        tree.write(filepath, pretty_print=True, xml_declaration=True)

        # Calculates the length of the header:
        # 40 is subtracted since the first line of the above created file has a length of 39 and is
        # not included later and the last endline (\n) is also not neccessary.
        # The for loop is needed to give a nine digit length: xxxxxxxxx
        length_of_header = ''
        size = str(os.path.getsize(filepath) - 40)

        for ii in range(9 - len(size)):
            length_of_header += '0'
        length_of_header += size

        # The header length is written into the file
        # The first line is not included since it is redundant
        # Also the last endline (\n) is excluded
        text = open(filepath, "U").read()
        text = text.replace("xxxxxxxxx", length_of_header)
        text = bytes(text, 'UTF-8')
        f = open(filepath, "wb")
        f.write(text[39:-1])
        f.close()
