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

Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
Copyright (C) 2016 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

import time
from ftplib import FTP
from socket import socket, AF_INET, SOCK_STREAM
import numpy as np
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

    def __init__(self, manager, name, config, **kwargs):

        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}

        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        if 'awg_IP_address' in config.keys():
            self.ip_address = config['awg_IP_address']
        else:
            self.logMsg('No IP address parameter "awg_IP_address" found in '
                        'the config for the AWG5002C! Correct that!',
                        msgType='error')

        if 'awg_port' in config.keys():
            self.port = config['awg_port']
        else:
            self.logMsg('No port parameter "awg_port" found in the config for '
                        'the AWG5002C! Correct that!', msgType='error')

        if 'default_sample_rate' in config.keys():
            self.sample_rate = config['default_sample_rate']
        else:
            self.logMsg('No parameter "default_sample_rate" found in the '
                        'config for the AWG5002C! The maximum sample rate is '
                        'used instead.', msgType='warning')
            self.sample_rate = self.get_constraints()['sample_rate'][1]

        if 'awg_ftp_path' in config.keys():
            self.ftp_path = config['awg_ftp_path']
        else:
            self.logMsg('No parameter "awg_ftp_path" found in the config for '
                        'the AWG5002C! State the FTP folder of this device!',
                        msgType='error')

        if 'timeout' in config.keys():
            self._timeout = config['timeout']
        else:
            self.logMsg('No parameter "timeout" found in the config for '
                        'the AWG5002C! Take a default value of 10s.',
                        msgType='error')
            self._timeout = 10

        self.sample_mode = {'matlab': 0, 'wfm-file': 1, 'wfmx-file': 2}
        self.current_sample_mode = self.sample_mode['wfm-file']

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

        # AWG7122c has possibility for sequence output
        self.sequence_mode = True

        self._marker_byte_dict = {0: b'\x00', 1: b'\x01', 2: b'\x02', 3: b'\x03'}

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
        # connect ethernet socket and FTP
        self.soc = socket(AF_INET, SOCK_STREAM)
        self.soc.settimeout(self._timeout)  # set the timeout to 5 seconds
        self.soc.connect((self.ip_address, self.port))
        self.input_buffer = int(2 * 1024)  # buffer length for received text

    def deactivation(self, e):
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

        # Todo: Set values for AWG7122c
        constraints = {}

        # if interleave option is available, then sample rate constraints must
        # be assigned to the output of a function called
        # _get_sample_rate_constraints()
        # which outputs the shown dictionary with the correct values depending
        # on the present mode. The the GUI will have to check again the
        # limitations if interleave was selected.
        constraints['sample_rate'] = self._get_sample_rate_constraints()

        #TODO: Check those values:
        # the stepsize will be determined by the DAC in combination with the
        # maximal output amplitude (in Vpp):
        constraints['a_ch_amplitude'] = {'min': 0.005, 'max': 1.0,
                                         'step': 0.001, 'unit': 'Vpp'}

        #TODO: Check those values:
        constraints['a_ch_offset'] = {'min': -0.5, 'max': 0.5,
                                      'step': 0.01, 'unit': 'V'}

        #TODO: Check those values:
        constraints['d_ch_low'] = {'min': -1, 'max': 2.6,
                                   'step': 0.01, 'unit': 'V'}

        #TODO: Check those values:
        constraints['d_ch_high'] = {'min': -0.9, 'max': 2.7,
                                      'step': 0.01, 'unit': 'V'}

        #TODO: Check those values:
        # for arbitrary waveform generators, this values will be used. The
        # step value corresponds to the waveform granularity.
        constraints['sampled_file_length'] = {'min': 1, 'max': 32e6,
                                              'step': 1, 'unit': 'Samples'}

        # if only digital bins can be saved, then their limitation is different
        # compared to a waveform file
        constraints['digital_bin_num'] = {'min': 0, 'max': 0,
                                          'step': 0, 'unit': '#'}

        #TODO: Check those values:
        constraints['waveform_num'] = {'min': 1, 'max': 32000,
                                       'step': 1, 'unit': '#'}

        #TODO: Check those values:
        constraints['sequence_num'] = {'min': 1, 'max': 4000,
                                       'step': 1, 'unit': '#'}

        #TODO: Check those values:
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
        available_ch['Interleave'] = {'a_ch': 1}
        available_ch['ACH1'] = {'a_ch': 2}
        available_ch['DCH1'] = {'d_ch': 1}
        available_ch['DCH2'] = {'d_ch': 2}
        available_ch['ACH2'] = {'a_ch': 3}
        available_ch['DCH3'] = {'d_ch': 3}
        available_ch['DCH4'] = {'d_ch': 4}
        constraints['available_ch'] = available_ch

        # State all possible DIFFERENT configurations, which the pulsing device
        # may have. That concerns also the display of the chosen channels.
        # Channel configuration for this device, use OrderedDictionaries to
        # keep an order in that dictionary. That is for now the easiest way to
        # determine the channel configuration:
        channel_config = OrderedDict()
        channel_config['conf1'] = ['a_ch', 'd_ch', 'd_ch']
        channel_config['conf2'] = ['a_ch']
        channel_config['conf3'] = ['a_ch', 'a_ch']
        channel_config['conf4'] = ['a_ch', 'd_ch', 'd_ch', 'a_ch', 'd_ch', 'd_ch']
        constraints['channel_config'] = channel_config

        # Now you can choose, how many channel activation pattern exists. You
        # can only use the names, declared in the constraint 'available_ch'!
        activation_map = OrderedDict()
        activation_map['map1'] = ['ACH1', 'DCH1', 'DCH2', 'ACH2', 'DCH3', 'DCH4']
        # Usage of channel 1 only:
        activation_map['map2'] = ['ACH1', 'DCH1', 'DCH2']
        # Usage of channel 2 only:
        activation_map['map3'] = ['ACH2', 'DCH3', 'DCH4']
        # Usage of Interleave configuration with digital channels:
        activation_map['map4'] = ['Interleave', 'DCH1', 'DCH2']
        # Usage of Interleave configuration only:
        activation_map['map5'] = ['Interleave']
        # usage of two analog channels only:
        activation_map['map6'] = ['ACH1', 'ACH2']
        # Usage of one analog channel without digital channel
        activation_map['map7'] = ['ACH1']
        # Usage of one analog channel without digital channel
        activation_map['map8'] = ['ACH2']

        constraints['activation_map'] = activation_map

        # this information seems to be almost redundant but it can be that no
        # channel configuration exists, where not all available channels are
        # present. Therefore this is needed here:
        constraints['available_ch_num'] = {'a_ch': 3, 'd_ch': 4}

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
        #TODO: Check those values:
        if self.interleave:
            return {'min': 12.0e9, 'max': 24.0e9,
                    'step': 4, 'unit': 'Samples/s'}
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
            self.logMsg('No asset name provided for upload!\nCorrect '
                        'that!\nCommand will be ignored.', msgType='warning')
            return -1

        # create list of filenames to be uploaded
        upload_names = []
        if self.current_sample_mode == self.sample_mode['wfm-file']:
            filelist = os.listdir(self.host_waveform_directory)
            for filename in filelist:
                is_wfm = filename.endswith('.wfm')
                if is_wfm and (asset_name + '_ch') in filename:
                    upload_names.append(filename)
        else:
            self.logMsg('Error in file upload:\nInvalid sample mode for '
                        'this device!\nSet a proper one for sample the '
                        'real data.',
                        msgType='error')
            return -1

        # upload files
        for name in upload_names:
            self._send_file(name)
        return 0

    # TODO: test
    def write_chunk_to_file(self, name, analogue_samples_chunk,
                            digital_samples_chunk, total_number_of_samples,
                            is_first_chunk, is_last_chunk, sample_rate,
                            pp_voltage, ):
        """
        Appends a sampled chunk of a whole waveform to a file. Create the file
        if it is the first chunk.

        @param name: string representing the name of the sampled ensemble
        @param analogue_samples_chunk: float32 numpy ndarray containing the
                                       samples for the analogue channels.
        @param digital_samples_chunk: bool numpy ndarray containing the samples
                                      for the digital channels.
        @param total_number_of_samples: The total number of samples in the entire waveform
        @param is_first_chunk: bool indicating if the current chunk is the
                               first write to this file.
        @param is_last_chunk: bool indicating if the current chunk is the last
                              write to this file.
        @return: error code (0: OK, -1: error)
        """

        if self.current_sample_mode == self.sample_mode['wfm-file']:

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


            for channel_index, channel_arr in enumerate(analogue_samples_chunk):

                filename = name+'_ch'+str(channel_index+1) + '.wfm'

                filepath = os.path.join(self.host_waveform_directory,filename)
                with open(filepath, 'wb') as wfm_file:

                    # write the first line, which is the header file:
                    num_bytes = str(len(digital_samples_chunk[channel_index*2])*5)
                    num_digits = str(len(num_bytes))
                    header = str.encode('MAGIC 1000\r\n#'+num_digits+num_bytes)
                    wfm_file.write(header)

                    # now write at once the whole file in binary representation:

                    # convert the presampled numpy array of the analog channels
                    # to a float number represented by 8bits:
                    shape_for_wavetmp = np.shape(channel_arr)[0]
                    wavetmp = np.zeros(shape_for_wavetmp*5,dtype='c')
                    wavetmp = wavetmp.reshape((-1,5))
                    # wavetmp[:,:4] = np.frombuffer(bytes(channel_arr),dtype='c').reshape((-1,4))
                    wavetmp[:,:4] = np.frombuffer(memoryview(channel_arr/4),dtype='c').reshape((-1,4))

                    # The previously created array wavetmp contains one
                    # additional column, where the marker states will be written
                    # into:
                    marker = digital_samples_chunk[channel_index*2] + digital_samples_chunk[channel_index*2+1]*2
                    marker_byte = np.array([self._marker_byte_dict[m] for m in marker], dtype='c')
                    wavetmp[:, -1] = marker_byte

                    # now write everything to file:
                    wfm_file.write(wavetmp.tobytes())

                    # the footer encodes the sample rate, which was used for
                    # that file:
                    footer = str.encode('CLOCK {:16.10E}\r\n'.format(sample_rate))
                    wfm_file.write(footer)

        else:
            self.logMsg('Sample mode not defined for the given pulser hardware.'
                        '\nEither the mode does not exist or the sample mode is'
                        'not assigned properly. Correct that!', msgType='error')

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

        path = self.ftp_path + self.get_file_dir_on_device()


        if load_dict == {}:
            self.logMsg('No file and channel provided for load!\nCorrect '
                        'that!\nCommand will be ignored.', msgType='warning')

        for channel_num in list(load_dict):
            if channel_num == 1 or  channel_num == 2:
                file_name = str(load_dict[channel_num]) + '_ch1.wfm'
                self.tell('SOUR1:FUNC:USER "{1}/{2}"\n'.format(path, file_name))
            elif channel_num == 3:
                file_name = str(load_dict[channel_num]) + '_ch2.wfm'
                self.tell('SOUR2:FUNC:USER "{1}/{2}"\n'.format(path, file_name))

            else:
                self.logMsg('No analog channel with channel number "{0}" '
                            'exists! Check the load '
                            'routine!'.format(channel_num), msgType='error')

        return 0

    def clear_all(self):
        """ Clears the loaded waveform from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Delete all waveforms and sequences from Hardware memory and clear the
        visual display. Unused for digital pulse generators without sequence
        storage capability (PulseBlaster, FPGA).
        """


        self.tell('WLIST:WAVEFORM:DELETE ALL\n')
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
    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate in a class variable, but instead
        retrieve the current sample rate directly from the device.
        """

        self.sample_rate = float(self.ask('SOURCE1:FREQUENCY?\n'))
        return self.sample_rate

    # works!
    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device.

        Note: After setting the sampling rate of the device, retrieve it again
              for obtaining the actual set value and use that information for
              further processing.
        """

        self.tell('SOURCE1:FREQUENCY {0:.4G}MHz\n'.format(sample_rate / 1e6))

        # Here we need to wait, because when the sampling rate is changed AWG is busy
        # and therefore the ask in get_sample_rate will return an empty string.
        time.sleep(0.3)
        return self.get_sample_rate()

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

        amp = {}
        off = {}
        constraints = self.get_constraints()

        if (amplitude == []) and (offset == []):

            # since the available channels are not going to change for this
            # device you are asking directly:
            amp[1] = float(self.ask('SOURCE1:VOLTAGE:AMPLITUDE?'))
            amp[2] = float(self.ask('SOURCE2:VOLTAGE:AMPLITUDE?'))

            off[1] = float(self.ask('SOURCE1:VOLTAGE:OFFSET?'))
            off[2] = float(self.ask('SOURCE2:VOLTAGE:OFFSET?'))

        else:

            #FIXME: include the check for interleave channel and obtain also for
            #       that channel the proper amplitude and offset
            #       Remember channelnumbers were defined like
            #           Interleave = 1
            #           ACH1       = 2
            #           ACH2       = 3
            #       for analog channels.
            for a_ch in amplitude:
                if (a_ch <= constraints['available_ch_num']['a_ch']) and \
                   (a_ch >= 0):
                    amp[a_ch] = float(self.ask('SOURCE{0}:VOLTAGE:AMPLITUDE?'.format(a_ch)))
                else:
                    self.logMsg('The device does not have that much analog '
                                'channels! A channel number "{0}" was passed, '
                                'but only "{1}" channels are available!\n'
                                'Command will be ignored.'.format(a_ch,
                                                                  constraints['available_ch_num']['a_ch']),
                            msgType='warning')

            for a_ch in offset:
                if (a_ch <= constraints['available_ch_num']['a_ch']) and \
                   (a_ch >= 0):
                    off[a_ch] = float(self.ask('SOURCE{0}:VOLTAGE:OFFSET?'.format(a_ch)))
                else:
                    self.logMsg('The device does not have that much analog '
                                'channels! A channel number "{0}" was passed, '
                                'but only "{1}" channels are available!\n'
                                'Command will be ignored.'.format(a_ch,
                                                                  constraints['available_ch_num']['a_ch']),
                            msgType='warning')

        return amp, off


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

        constraints = self.get_constraints()

        #FIXME: include the check for interleave channel and obtain also for
        #       that channel the proper amplitude and offset
        #       Remember channelnumbers were defined like
        #           Interleave = 1
        #           ACH1       = 2
        #           ACH2       = 3
        #       for analog channels.

        for a_ch in amplitude:
            if (a_ch <= constraints['available_ch_num']['a_ch']) and \
               (a_ch >= 0):

                if amplitude[a_ch] < constraints['a_ch_amplitude']['min'] or \
                   amplitude[a_ch] > constraints['a_ch_amplitude']['max']:

                    self.logMsg('Not possible to set for analog channel {0} '
                                'the amplitude value {1}Vpp, since it is not '
                                'within the interval [{2},{3}]! Command will '
                                'be ignored.'.format(a_ch,
                                                     amplitude[a_ch],
                                                     constraints['a_ch_amplitude']['min'],
                                                     constraints['a_ch_amplitude']['max']),
                                msgType='warning')
                else:

                    self.tell('SOURCE{0}:VOLTAGE:AMPLITUDE {1}'.format(a_ch,
                                                                       amplitude[a_ch]))


            else:
                self.logMsg('The device does not support that much analog '
                            'channels! A channel number "{0}" was passed, but '
                            'only "{1}" channels are available!\nCommand will '
                            'be ignored.'.format(a_ch,
                                                 constraints['available_ch_num']['a_ch']),
                            msgType='warning')

        for a_ch in offset:
            if (a_ch <= constraints['available_ch_num']['a_ch']) and \
               (a_ch >= 0):

                if offset[a_ch] < constraints['a_ch_offset']['min'] or \
                   offset[a_ch] > constraints['a_ch_offset']['max']:

                    self.logMsg('Not possible to set for analog channel {0} '
                                'the offset value {1}V, since it is not '
                                'within the interval [{2},{3}]! Command will '
                                'be ignored.'.format(a_ch,
                                                     offset[a_ch],
                                                     constraints['a_ch_offset']['min'],
                                                     constraints['a_ch_offset']['max']),
                                msgType='warning')
                else:
                    self.tell('SOURCE{0}:VOLTAGE:OFFSET {1}'.format(a_ch,
                                                                    offset[a_ch]))

            else:
                self.logMsg('The device does not support that much analog '
                            'channels! A channel number "{0}" was passed, but '
                            'only "{1}" channels are available!\nCommand will '
                            'be ignored.'.format(a_ch,
                                                 constraints['available_ch_num']['a_ch']),
                            msgType='warning')

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
                if (d_ch <= constraints['available_ch_num']['d_ch']) and \
                   (d_ch >= 0):

                    # a fast way to map from a channel list [1, 2, 3, 4] to  a
                    # list like [[1,2], [1,2]]:
                    if (d_ch-2) <= 0:
                        # the conversion to integer is just for safety.
                        low_val[d_ch] = float(self.ask('SOURCE1:MARKER{0}:VOLTAGE:LOW?'.format(int(d_ch))))

                    else:
                        low_val[d_ch] = float(self.ask('SOURCE2:MARKER{0}:VOLTAGE:LOW?'.format(int(d_ch-2))))
                else:
                    self.logMsg('The device does not have that much digital '
                                'channels! A channel number "{0}" was passed, '
                                'but only "{1}" channels are available!\n'
                                'Command will be ignored.'.format(d_ch,
                                                                  constraints['available_ch_num']['d_ch']),
                                msgType='warning')

            for d_ch in high:

                if (d_ch <= constraints['available_ch_num']['d_ch']) and \
                   (d_ch >= 0):

                    # a fast way to map from a channel list [1, 2, 3, 4] to  a
                    # list like [[1,2], [1,2]]:
                    if (d_ch-2) <= 0:
                        # the conversion to integer is just for safety.
                        high_val[d_ch] = float(self.ask('SOURCE1:MARKER{0}:VOLTAGE:HIGH?'.format(int(d_ch))))

                    else:
                        high_val[d_ch] = float(self.ask('SOURCE2:MARKER{0}:VOLTAGE:HIGH?'.format(int(d_ch-2))))
                else:
                    self.logMsg('The device does not have that much digital '
                                'channels! A channel number "{0}" was passed, '
                                'but only "{1}" channels are available!\n'
                                'Command will be ignored.'.format(d_ch,
                                                                  constraints['available_ch_num']['d_ch']),
                                msgType='warning')

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

        constraints = self.get_constraints()

        for d_ch in low:
            if (d_ch <= constraints['available_ch_num']['d_ch']) and \
               (d_ch >=0):

                if low[d_ch] < constraints['d_ch_low']['min'] or \
                   low[d_ch] > constraints['d_ch_low']['max']:

                    self.logMsg('Not possible to set for analog channel {0} '
                                'the amplitude value {1}Vpp, since it is not '
                                'within the interval [{2},{3}]! Command will '
                                'be ignored.'.format(d_ch,
                                                     low[d_ch],
                                                     constraints['d_ch_low']['min'],
                                                     constraints['d_ch_low']['max']),
                                msgType='warning')
                else:

                    # a fast way to map from a channel list [1, 2, 3, 4] to  a
                    # list like [[1,2], [1,2]]:
                    if (d_ch-2) <= 0:
                        self.tell('SOURCE1:MARKER{0}:VOLTAGE:LOW {1}'.format(d_ch, low[d_ch]))
                    else:
                        self.tell('SOURCE2:MARKER{0}:VOLTAGE:LOW {1}'.format(d_ch-2, low[d_ch]))

            else:
                self.logMsg('The device does not support that much digital '
                            'channels! A channel number "{0}" was passed, but '
                            'only "{1}" channels are available!\nCommand will '
                            'be ignored.'.format(d_ch,
                                                 constraints['available_ch_num']['d_ch']),
                            msgType='warning')

        for d_ch in high:
            if (d_ch <= constraints['available_ch_num']['d_ch']) and \
               (d_ch >=0):

                if high[d_ch] < constraints['d_ch_high']['min'] or \
                   high[d_ch] > constraints['d_ch_high']['max']:

                    self.logMsg('Not possible to set for analog channel {0} '
                                'the amplitude value {1}Vpp, since it is not '
                                'within the interval [{2},{3}]! Command will '
                                'be ignored.'.format(d_ch,
                                                     high[d_ch],
                                                     constraints['d_ch_high']['min'],
                                                     constraints['d_ch_high']['max']),
                                msgType='warning')
                else:

                    # a fast way to map from a channel list [1, 2, 3, 4] to  a
                    # list like [[1,2], [1,2]]:
                    if (d_ch-2) <= 0:
                        self.tell('SOURCE1:MARKER{0}:VOLTAGE:HIGH {1}'.format(d_ch, high[d_ch]))
                    else:
                        self.tell('SOURCE2:MARKER{0}:VOLTAGE:HIGH {1}'.format(d_ch-2, high[d_ch]))


            else:
                self.logMsg('The device does not support that much digital '
                            'channels! A channel number "{0}" was passed, but '
                            'only "{1}" channels are available!\nCommand will '
                            'be ignored.'.format(d_ch,
                                                 constraints['available_ch_num']['d_ch']),
                            msgType='warning')

        return self.get_digital_level(low=list(low), high=list(high))


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

        AWG5000 Series instruments support only 14-bit resolution. Therefore
        this command will have no effect on the DAC for these instruments. On
        other devices the deactivation of digital channels increase the DAC
        resolution of the analog channels.
        """

        constraints = self.get_constraints()

        for ana_chan in a_ch:
            if (ana_chan <= constraints['available_ch_num']['a_ch']) and \
               (ana_chan >= 0):

                if a_ch[ana_chan]:
                    state = 'ON'
                else:
                    state = 'OFF'

                self.tell('OUTPUT{0}:STATE {1}'.format(ana_chan, state))


            else:
                self.logMsg('The device does not support that much analog '
                            'channels! A channel number "{0}" was passed, but '
                            'only "{1}" channels are available!\nCommand will '
                            'be ignored.'.format(ana_chan,
                                                 constraints['available_ch_num']['a_ch']),
                            msgType='warning')

        if d_ch != {}:
            self.logMsg('Digital Channel of the AWG5000 series will always be '
                        'active. This configuration cannot be changed.',
                        msgType='status')

            #FIXME: The awg 7000 series has the opportuinity to run only in
            #       analog mode by switching off the digital channels through
            #       changing the DAC resolution
            #       adapt that possibility.

        return self.get_active_channels(a_ch=list(a_ch), d_ch=list(d_ch))


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

        constraints = self.get_constraints()
        active_a_ch = {}
        active_d_ch = {}

        if (a_ch == []) and (d_ch == []):

            # because 0 = False and 1 = True
            active_a_ch[1] = bool(int(self.ask('OUTPUT1:STATE?')))
            active_a_ch[2] = bool(int(self.ask('OUTPUT2:STATE?')))

            # For the AWG5000 series, the resolution of the DAC for the analogue
            # channel is fixed to 14bit. Therefore the digital channels are
            # always active and cannot be deactivated. For other AWG devices the
            # command
            #   self.ask('SOURCE1:DAC:RESOLUTION?'))
            # might be useful from which the active digital channels can be
            # obtained.
            active_d_ch[1] = True
            active_d_ch[2] = True
            active_d_ch[3] = True
            active_d_ch[4] = True
            #FIXME: The awg 7000 series has the opportuinity to run only in
            #       analog mode by switching off the digital channels through
            #       changing the DAC resolution. Adapt that possibility. Look
            #       above in the comment.

        else:
            for ana_chan in a_ch:

                if (ana_chan <= constraints['available_ch_num']['a_ch']) and \
                   (ana_chan >= 0):

                    # because 0 = False and 1 = True
                    active_a_ch[ana_chan] = bool(int(self.ask('OUTPUT{0}:STATE?'.format(ana_chan))))

                else:
                    self.logMsg('The device does not support that much analog '
                                'channels! A channel number "{0}" was passed, '
                                'but only "{1}" channels are available!\n'
                                'Command will be ignored.'.format(ana_chan,
                                                                  constraints['available_ch_num']['a_ch']),
                                msgType='warning')

            for digi_chan in d_ch:

                if (digi_chan <= constraints['available_ch_num']['d_ch']) and \
                   (digi_chan >= 0):

                    active_d_ch[digi_chan] = True
                    #FIXME: The awg 7000 series has the opportuinity to run only in
                    #       analog mode by switching off the digital channels through
                    #       changing the DAC resolution. Adapt that possibility.
                    #       Look above in the comment.

                else:
                    self.logMsg('The device does not support that much digital '
                                'channels! A channel number "{0}" was passed, '
                                'but only "{1}" channels are available!\n'
                                'Command will be ignored.'.format(digi_chan,
                                                                  constraints['available_ch_num']['d_ch']),
                                msgType='warning')

        return active_a_ch, active_d_ch


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
        # exclude the channel specifier for multiple analogue channels and create return list
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
                if fnmatch(filename, name+'_ch?.wfm'):
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
            self.logMsg('Interleave mode can not be set to desired state!\n'
                        , msgType='warning')

        return self.get_interleave()

    # todo: should there also be a class variable which keeps track of this?
    def get_interleave(self):
        """ Check whether Interleave is on in AWG.

        @return bool: True if Interleave is turned on and False if interleave is off,
                      None if non of both
        """

        interleave = self.ask('AWGControl:INTerleave:STAT?\n')
        # TODO: change constraints to allowed values depending on mode

        if interleave == '1':
            return True
        elif interleave == '0':
            return False
        else:
            self.logMsg('State of interleave mode neither 1 nor 0. Returning false.\n',
                        msgType='warning')
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
            self.logMsg('Most propably timeout was reached during querying '
                        'the AWG7122 Series device with the question:\n'
                        '{0}\n'
                        'The question text must be wrong.'.format(question),
                        msgType='error')
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
                    file_list.append(line.rsplit(None, 1)[1])
            for filename in file_list:
                if filename.endswith('.wfm'):
                    if filename not in filename_list:
                        filename_list.append(filename)
        return filename_list

    def _get_filenames_on_host(self):
        """ Get the full filenames of all assets saved on the host PC.

        @return: list, The full filenames of all assets saved on the host PC.
        """
        filename_list = [f for f in os.listdir(self.host_waveform_directory) if f.endswith('.wfm')]
        return filename_list
