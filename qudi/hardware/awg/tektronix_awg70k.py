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
import visa
import numpy as np

from collections import OrderedDict
from ftplib import FTP
from lxml import etree as ET

from core.module import Base
from core.configoption import ConfigOption
from core.util.modules import get_home_dir
from core.util.helpers import natural_sort
from interface.pulser_interface import PulserInterface, PulserConstraints, SequenceOption


class AWG70K(Base, PulserInterface):
    """ A hardware module for the Tektronix AWG70000 series for generating
        waveforms and sequences thereof.

    Example config for copy-paste:

    pulser_awg70000:
        module.Class: 'awg.tektronix_awg70k.AWG70k'
        awg_visa_address: 'TCPIP::10.42.0.211::INSTR'
        awg_ip_address: '10.42.0.211'
        timeout: 60
        # tmp_work_dir: 'C:\\Software\\qudi_pulsed_files' # optional
        # ftp_root_dir: 'C:\\inetpub\\ftproot' # optional, root directory on AWG device
        # ftp_login: 'anonymous' # optional, the username for ftp login
        # ftp_passwd: 'anonymous@' # optional, the password for ftp login

    """

    # config options
    _visa_address = ConfigOption(name='awg_visa_address', missing='error')
    _ip_address = ConfigOption(name='awg_ip_address', missing='error')
    _visa_timeout = ConfigOption(name='timeout', default=30, missing='nothing')
    _tmp_work_dir = ConfigOption(name='tmp_work_dir',
                                 default=os.path.join(get_home_dir(), 'pulsed_files'),
                                 missing='warn')
    _ftp_dir = ConfigOption(name='ftp_root_dir', default='C:\\inetpub\\ftproot', missing='warn')
    _username = ConfigOption(name='ftp_login', default='anonymous', missing='warn')
    _password = ConfigOption(name='ftp_passwd', default='anonymous@', missing='warn')

    # translation dict from qudi trigger descriptor to device command
    __event_triggers = {'OFF': 'OFF', 'A': 'ATR', 'B': 'BTR', 'INT': 'INT'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get an instance of the visa resource manager
        self._rm = visa.ResourceManager()

        self.awg = None  # This variable will hold a reference to the awg visa resource
        self.awg_model = ''  # String describing the model

        self.ftp_working_dir = 'waves'  # subfolder of FTP root dir on AWG disk to work in

        self.__max_seq_steps = 0
        self.__max_seq_repetitions = 0
        self.__min_waveform_length = 0
        self.__max_waveform_length = 0
        self.__installed_options = list()
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Create work directory if necessary
        if not os.path.exists(self._tmp_work_dir):
            os.makedirs(os.path.abspath(self._tmp_work_dir))

        # connect to awg using PyVISA
        if self._visa_address not in self._rm.list_resources():
            self.awg = None
            self.log.error('VISA address "{0}" not found by the pyVISA resource manager.\nCheck '
                           'the connection by using for example "Agilent Connection Expert".'
                           ''.format(self._visa_address))
        else:
            self.awg = self._rm.open_resource(self._visa_address)
            # set timeout by default to 30 sec
            self.awg.timeout = self._visa_timeout * 1000

        # try connecting to AWG using FTP protocol
        with FTP(self._ip_address) as ftp:
            ftp.login(user=self._username, passwd=self._password)
            ftp.cwd(self.ftp_working_dir)

        if self.awg is not None:
            self.awg_model = self.query('*IDN?').split(',')[1]
        else:
            self.awg_model = ''

        # Query some constraints from the device and stash them in order to avoid redundant queries.
        self.__max_seq_steps = int(self.query('SLIS:SEQ:STEP:MAX?'))
        self.__max_seq_repetitions = int(self.query('SLIS:SEQ:STEP:RCO:MAX?'))
        self.__min_waveform_length = int(self.query('WLIS:WAV:LMIN?'))
        self.__max_waveform_length = int(self.query('WLIS:WAV:LMAX?'))

        self.__installed_options = self.query('*OPT?').split(',')
        return

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

        if self.awg_model == 'AWG70002A':
            constraints.sample_rate.min = 1.5e3
            constraints.sample_rate.max = 25.0e9
            constraints.sample_rate.step = 5.0e2
            constraints.sample_rate.default = 25.0e9
        elif self.awg_model == 'AWG70001A':
            constraints.sample_rate.min = 1.49e3
            constraints.sample_rate.max = 50.0e9
            constraints.sample_rate.step = 10
            constraints.sample_rate.default = 50.0e9

        constraints.a_ch_amplitude.min = 0.25
        constraints.a_ch_amplitude.max = 0.5
        constraints.a_ch_amplitude.step = 0.0001
        constraints.a_ch_amplitude.default = 0.5

        constraints.d_ch_low.min = -1.4
        constraints.d_ch_low.max = 0.9
        constraints.d_ch_low.step = 0.1e-3
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = -0.9
        constraints.d_ch_high.max = 1.4
        constraints.d_ch_high.step = 0.1e-3
        constraints.d_ch_high.default = 1.4
        # constraints.d_ch_difference.max = 1.4
        # constraints.d_ch_difference.min = 0.5

        constraints.waveform_length.min = self.__min_waveform_length
        constraints.waveform_length.max = self.__max_waveform_length
        if self.awg_model == 'AWG70002A':
            constraints.waveform_length.step = 1
            constraints.waveform_length.default = 1
        elif self.awg_model == 'AWG70001A':
            constraints.waveform_length.step = 2
            constraints.waveform_length.default = 2

        # FIXME: Check the proper number for your device
        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 32000
        constraints.waveform_num.step = 1
        constraints.waveform_num.default = 1
        # FIXME: Check the proper number for your device
        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 4000
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1
        # FIXME: Check the proper number for your device
        constraints.subsequence_num.min = 1
        constraints.subsequence_num.max = 8000
        constraints.subsequence_num.step = 1
        constraints.subsequence_num.default = 1

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = self.__max_seq_repetitions
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0
        # ToDo: Check how many external triggers are available
        constraints.event_triggers = ['OFF', 'A', 'B', 'INT']
        constraints.flags = ['A', 'B', 'C', 'D']

        constraints.sequence_steps.min = 0
        constraints.sequence_steps.max = self.__max_seq_steps
        constraints.sequence_steps.step = 1
        constraints.sequence_steps.default = 0

        # constraints.seqence_tracks.max = int(self.query('SLISt:SEQuence:TRACk:MAX?'))

        # the name a_ch<num> and d_ch<num> are generic names, which describe UNAMBIGUOUSLY the
        # channels. Here all possible channel configurations are stated, where only the generic
        # names should be used. The names for the different configurations can be customary chosen.
        activation_config = OrderedDict()
        if self.awg_model == 'AWG70002A':
            activation_config['all'] = frozenset(
                {'a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3', 'd_ch4'})
            # Usage of both channels but reduced markers (higher analog resolution)
            activation_config['ch1_2mrk_ch2_1mrk'] = frozenset(
                {'a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3'})
            activation_config['ch1_2mrk_ch2_0mrk'] = frozenset({'a_ch1', 'd_ch1', 'd_ch2', 'a_ch2'})
            activation_config['ch1_1mrk_ch2_2mrk'] = frozenset(
                {'a_ch1', 'd_ch1', 'a_ch2', 'd_ch3', 'd_ch4'})
            activation_config['ch1_0mrk_ch2_2mrk'] = frozenset({'a_ch1', 'a_ch2', 'd_ch3', 'd_ch4'})
            activation_config['ch1_1mrk_ch2_1mrk'] = frozenset({'a_ch1', 'd_ch1', 'a_ch2', 'd_ch3'})
            activation_config['ch1_0mrk_ch2_1mrk'] = frozenset({'a_ch1', 'a_ch2', 'd_ch3'})
            activation_config['ch1_1mrk_ch2_0mrk'] = frozenset({'a_ch1', 'd_ch1', 'a_ch2'})
            # Usage of channel 1 only:
            activation_config['ch1_2mrk'] = frozenset({'a_ch1', 'd_ch1', 'd_ch2'})
            # Usage of channel 2 only:
            activation_config['ch2_2mrk'] = frozenset({'a_ch2', 'd_ch3', 'd_ch4'})
            # Usage of only channel 1 with one marker:
            activation_config['ch1_1mrk'] = frozenset({'a_ch1', 'd_ch1'})
            # Usage of only channel 2 with one marker:
            activation_config['ch2_1mrk'] = frozenset({'a_ch2', 'd_ch3'})
            # Usage of only channel 1 with no marker:
            activation_config['ch1_0mrk'] = frozenset({'a_ch1'})
            # Usage of only channel 2 with no marker:
            activation_config['ch2_0mrk'] = frozenset({'a_ch2'})
        elif self.awg_model == 'AWG70001A':
            activation_config['all'] = frozenset({'a_ch1', 'd_ch1', 'd_ch2'})
            # Usage of only channel 1 with one marker:
            activation_config['ch1_1mrk'] = frozenset({'a_ch1', 'd_ch1'})
            # Usage of only channel 1 with no marker:
            activation_config['ch1_0mrk'] = frozenset({'a_ch1'})

        constraints.activation_config = activation_config
        if self._has_sequence_mode():
            constraints.sequence_option = SequenceOption.OPTIONAL
        else:
            constraints.sequence_option = SequenceOption.NON

        # FIXME: additional constraint really necessary?
        constraints.dac_resolution = {'min': 8, 'max': 10, 'step': 1, 'unit': 'bit'}
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        # do nothing if AWG is already running
        if not self._is_output_on():
            self.write('AWGC:RUN')
            # wait until the AWG is actually running
            while not self._is_output_on():
                time.sleep(0.25)
        return self.get_status()[0]

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        # do nothing if AWG is already idle
        if self._is_output_on():
            self.write('AWGC:STOP')
            # wait until the AWG has actually stopped
            while self._is_output_on():
                time.sleep(0.25)
        return self.get_status()[0]

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
            self.log.error('No analog samples passed to write_waveform method in awg70k.')
            return -1, waveforms

        min_samples = int(self.query('WLIS:WAV:LMIN?'))
        if total_number_of_samples < min_samples:
            self.log.error('Unable to write waveform.\nNumber of samples to write ({0:d}) is '
                           'smaller than the allowed minimum waveform length ({1:d}).'
                           ''.format(total_number_of_samples, min_samples))
            return -1, waveforms

        # determine active channels
        activation_dict = self.get_active_channels()
        active_channels = {chnl for chnl in activation_dict if activation_dict[chnl]}
        active_analog = natural_sort(chnl for chnl in active_channels if chnl.startswith('a'))

        # Sanity check of channel numbers
        if active_channels != set(analog_samples.keys()).union(set(digital_samples.keys())):
            self.log.error('Mismatch of channel activation and sample array dimensions for '
                           'waveform creation.\nChannel activation is: {0}\nSample arrays have: '
                           ''.format(active_channels,
                                     set(analog_samples.keys()).union(set(digital_samples.keys()))))
            return -1, waveforms

        # Write waveforms. One for each analog channel.
        for a_ch in active_analog:
            # Get the integer analog channel number
            a_ch_num = int(a_ch.split('ch')[-1])
            # Get the digital channel specifiers belonging to this analog channel markers
            mrk_ch_1 = 'd_ch{0:d}'.format(a_ch_num * 2 - 1)
            mrk_ch_2 = 'd_ch{0:d}'.format(a_ch_num * 2)

            start = time.time()
            # Encode marker information in an array of bytes (uint8). Avoid intermediate copies!!!
            if mrk_ch_1 in digital_samples and mrk_ch_2 in digital_samples:
                mrk_bytes = digital_samples[mrk_ch_2].view('uint8')
                tmp_bytes = digital_samples[mrk_ch_1].view('uint8')
                np.left_shift(mrk_bytes, 1, out=mrk_bytes)
                np.add(mrk_bytes, tmp_bytes, out=mrk_bytes)
            elif mrk_ch_1 in digital_samples:
                mrk_bytes = digital_samples[mrk_ch_1].view('uint8')
            else:
                mrk_bytes = None
            self.log.debug('Prepare digital channel data: {0}'.format(time.time()-start))

            # Create waveform name string
            wfm_name = '{0}_ch{1:d}'.format(name, a_ch_num)

            # Check if waveform already exists and delete if necessary.
            if wfm_name in self.get_waveform_names():
                self.delete_waveform(wfm_name)

            # Write WFMX file for waveform
            start = time.time()
            self._write_wfmx(filename=wfm_name,
                             analog_samples=analog_samples[a_ch],
                             marker_bytes=mrk_bytes,
                             is_first_chunk=is_first_chunk,
                             is_last_chunk=is_last_chunk,
                             total_number_of_samples=total_number_of_samples)
            self.log.debug('Write WFMX file: {0}'.format(time.time() - start))

            # transfer waveform to AWG and load into workspace
            start = time.time()
            self._send_file(filename=wfm_name + '.wfmx')
            self.log.debug('Send WFMX file: {0}'.format(time.time() - start))

            start = time.time()
            self.write('MMEM:OPEN "{0}"'.format(os.path.join(
                self._ftp_dir, self.ftp_working_dir, wfm_name + '.wfmx')))
            # Wait for everything to complete
            timeout_old = self.awg.timeout
            # increase this time so that there is no timeout for loading longer sequences
            # which might take some minutes
            self.awg.timeout = 5e6
            # the answer of the *opc-query is received as soon as the loading is finished
            opc = int(self.query('*OPC?'))
            # Just to make sure
            while wfm_name not in self.get_waveform_names():
                time.sleep(0.25)

            # reset the timeout
            self.awg.timeout = timeout_old
            self.log.debug('Load WFMX file into workspace: {0}'.format(time.time() - start))

            # Append created waveform name to waveform list
            waveforms.append(wfm_name)
        return total_number_of_samples, waveforms

    def write_sequence(self, name, sequence_parameter_list):
        """
        Write a new sequence on the device memory.

        @param name: str, the name of the waveform to be created/append to
        @param sequence_parameter_list: list, contains the parameters for each sequence step and
                                        the according waveform names.

        @return: int, number of sequence steps written (-1 indicates failed process)
        """
        # Check if device has sequencer option installed
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. Sequencer option not '
                           'installed.')
            return -1

        # Check if all waveforms are present on device memory
        avail_waveforms = set(self.get_waveform_names())
        for waveform_tuple, param_dict in sequence_parameter_list:
            if not avail_waveforms.issuperset(waveform_tuple):
                self.log.error('Failed to create sequence "{0}" due to waveforms "{1}" not '
                               'present in device memory.'.format(name, waveform_tuple))
                return -1

        active_analog = natural_sort(chnl for chnl in self.get_active_channels() if chnl.startswith('a'))
        num_tracks = len(active_analog)
        num_steps = len(sequence_parameter_list)

        # Create new sequence and set jump timing to immediate.
        # Delete old sequence by the same name if present.
        self.new_sequence(name=name, steps=num_steps)

        # Fill in sequence information
        for step, (wfm_tuple, seq_step) in enumerate(sequence_parameter_list, 1):
            # Set waveforms to play
            if num_tracks == len(wfm_tuple):
                for track, waveform in enumerate(wfm_tuple, 1):
                    self.sequence_set_waveform(name, waveform, step, track)
            else:
                self.log.error('Unable to write sequence.\nLength of waveform tuple "{0}" does not '
                               'match the number of sequence tracks.'.format(waveform_tuple))
                return -1

            # Set event jump trigger
            if seq_step.event_trigger != 'OFF':
                self.sequence_set_event_jump(name,
                                             step,
                                             seq_step.event_trigger,
                                             seq_step.event_jump_to)
            # Set wait trigger
            if seq_step.wait_for != 'OFF':
                self.sequence_set_wait_trigger(name, step, seq_step.wait_for)
            # Set repetitions
            if seq_step.repetitions != 0:
                self.sequence_set_repetitions(name, step, seq_step.repetitions)
            # Set go_to parameter
            if seq_step.go_to > 0:
                if seq_step.go_to <= num_steps:
                    self.sequence_set_goto(name, step, seq_step.go_to)
                else:
                    self.log.error('Assigned "go_to = {0}" is larger than the number of steps '
                                   '"{1}".'.format(seq_step.go_to, num_steps))
                    return -1
            # Set flag states
            self.sequence_set_flags(name, step, seq_step.flag_trigger, seq_step.flag_high)

        # Wait for everything to complete
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)
        return num_steps

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        try:
            query_return = self.query('WLIS:LIST?')
        except visa.VisaIOError:
            query_return = None
            self.log.error('Unable to read waveform list from device. VisaIOError occured.')
        waveform_list = natural_sort(query_return.split(',')) if query_return else list()
        return waveform_list

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        sequence_list = list()

        if not self._has_sequence_mode():
            return sequence_list

        try:
            number_of_seq = int(self.query('SLIS:SIZE?'))
            for ii in range(number_of_seq):
                sequence_list.append(self.query('SLIS:NAME? {0:d}'.format(ii + 1)))
        except visa.VisaIOError:
            self.log.error('Unable to read sequence list from device. VisaIOError occurred.')
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
        for waveform in waveform_name:
            if waveform in avail_waveforms:
                self.write('WLIS:WAV:DEL "{0}"'.format(waveform))
                deleted_waveforms.append(waveform)
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
            if sequence in avail_sequences:
                self.write('SLIS:SEQ:DEL "{0}"'.format(sequence))
                deleted_sequences.append(sequence)
        return deleted_sequences

    def load_waveform(self, load_dict):
        """ Loads a waveform to the specified channel of the pulsing device.
        For devices that have a workspace (i.e. AWG) this will load the waveform from the device
        workspace into the channel.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param load_dict:  dict|list, a dictionary with keys being one of the available channel
                                      index and values being the name of the already written
                                      waveform to load into the channel.
                                      Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                  {1: rabi_ch2, 2: rabi_ch1}
                                      If just a list of waveform names if given, the channel
                                      association will be invoked from the channel
                                      suffix '_ch1', '_ch2' etc.

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel, string describing the asset
                             type ('waveform' or 'sequence')
        """
        if isinstance(load_dict, list):
            new_dict = dict()
            for waveform in load_dict:
                channel = int(waveform.rsplit('_ch', 1)[1])
                new_dict[channel] = waveform
            load_dict = new_dict

        # Get all active channels
        chnl_activation = self.get_active_channels()
        analog_channels = natural_sort(
            chnl for chnl in chnl_activation if chnl.startswith('a') and chnl_activation[chnl])

        # Check if all channels to load to are active
        channels_to_set = {'a_ch{0:d}'.format(chnl_num) for chnl_num in load_dict}
        if not channels_to_set.issubset(analog_channels):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more channels to set are not active.')
            return self.get_loaded_assets()

        # Check if all waveforms to load are present on device memory
        if not set(load_dict.values()).issubset(self.get_waveform_names()):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more waveforms to load are missing on device memory.')
            return self.get_loaded_assets()

        # Load waveforms into channels
        for chnl_num, waveform in load_dict.items():
            self.write('SOUR{0:d}:CASS:WAV "{1}"'.format(chnl_num, waveform))
            while self.query('SOUR{0:d}:CASS?'.format(chnl_num)) != waveform:
                time.sleep(0.1)

        return self.get_loaded_assets()

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.

        @param sequence_name:  str, name of the sequence to load

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel, string describing the asset
                             type ('waveform' or 'sequence')
        """
        if sequence_name not in self.get_sequence_names():
            self.log.error('Unable to load sequence.\n'
                           'Sequence to load is missing on device memory.')
            return self.get_loaded_assets()

        # Get all active channels
        chnl_activation = self.get_active_channels()
        analog_channels = natural_sort(
            chnl for chnl in chnl_activation if chnl.startswith('a') and chnl_activation[chnl])

        # Check if number of sequence tracks matches the number of analog channels
        trac_num = int(self.query('SLIS:SEQ:TRAC? "{0}"'.format(sequence_name)))
        if trac_num != len(analog_channels):
            self.log.error('Unable to load sequence.\nNumber of tracks in sequence to load does '
                           'not match the number of active analog channels.')
            return self.get_loaded_assets()

        # Load sequence
        for chnl in range(1, trac_num + 1):
            self.write('SOUR{0:d}:CASS:SEQ "{1}", {2:d}'.format(chnl, sequence_name, chnl))
            while self.query('SOUR{0:d}:CASS?'.format(chnl)) != '{0},{1:d}'.format(
                    sequence_name, chnl):
                time.sleep(0.2)

        return self.get_loaded_assets()

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
            asset_name = self.query('SOUR1:CASS?')
            # Figure out if a sequence or just a waveform is loaded by splitting after the comma
            splitted = asset_name.rsplit(',', 1)
            # If the length is 2 a sequence is loaded and if it is 1 a waveform is loaded
            asset_name = splitted[0]
            if len(splitted) > 1:
                if current_type is not None and current_type != 'sequence':
                    self.log.error('Unable to determine loaded assets.')
                    return dict(), ''
                current_type = 'sequence'
                asset_name += '_' + splitted[1]
            else:
                if current_type is not None and current_type != 'waveform':
                    self.log.error('Unable to determine loaded assets.')
                    return dict(), ''
                current_type = 'waveform'
            loaded_assets[chnl_num] = asset_name

        return loaded_assets, current_type

    def clear_all(self):
        """ Clears all loaded waveform from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without storage capability
        (PulseBlaster, FPGA).
        """
        self.write('WLIS:WAV:DEL ALL')
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)
        if self._has_sequence_mode():
            self.write('SLIS:SEQ:DEL ALL')
            while int(self.query('*OPC?')) != 1:
                time.sleep(0.25)
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
        current_status = -1 if self.awg is None else int(self._is_output_on())
        # All the other status messages should have higher integer values then 1.
        return current_status, status_dic

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware

        @param float sample_rate: The sample rate to be set (in Hz)

        @return foat: the sample rate returned from the device (-1:error)
        """
        # Check if AWG is in function generator mode
        # self._activate_awg_mode()

        self.write('CLOCK:SRATE %.4G' % sample_rate)
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)
        time.sleep(1)
        return self.get_sample_rate()

    def get_sample_rate(self):
        """ Set the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """
        return_rate = float(self.query('CLOCK:SRATE?'))
        return return_rate

    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if a specific amplitude value (in Volt
                               peak to peak, i.e. the full amplitude) of a
                               channel is desired.
        @param list offset: optional, if a specific high value (in Volt) of a
                            channel is desired.

        @return dict: with keys being the generic string channel names and items
                      being the values for those channels. Amplitude is always
                      denoted in Volt-peak-to-peak and Offset in (absolute)
                      Voltage.

        Note: Do not return a saved amplitude and/or offset value but instead
              retrieve the current amplitude and/or offset directly from the
              device.

        If no entries provided then the levels of all channels where simply
        returned. If no analog channels provided, return just an empty dict.
        Example of a possible input:
            amplitude = ['a_ch1','a_ch4'], offset =[1,3]
        to obtain the amplitude of channel 1 and 4 and the offset
            {'a_ch1': -0.5, 'a_ch4': 2.0} {'a_ch1': 0.0, 'a_ch3':-0.75}
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
        amp = dict()
        off = dict()

        chnl_list = self._get_all_analog_channels()

        # get pp amplitudes
        if amplitude is None:
            for ch_num, chnl in enumerate(chnl_list, 1):
                amp[chnl] = float(self.query('SOUR{0:d}:VOLT:AMPL?'.format(ch_num)))
        else:
            for chnl in amplitude:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    amp[chnl] = float(self.query('SOUR{0:d}:VOLT:AMPL?'.format(ch_num)))
                else:
                    self.log.warning('Get analog amplitude from AWG70k channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))

        # get voltage offsets
        if offset is None:
            for ch_num, chnl in enumerate(chnl_list):
                off[chnl] = 0.0
        else:
            for chnl in offset:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    off[chnl] = float(self.query('SOUR{0:d}:VOLT:OFFS?'.format(ch_num)))
                else:
                    self.log.warning('Get analog offset from AWG70k channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))
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
                                     'analogue voltage for this channel ignored.'.format(chnl))
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
                self.write('SOUR{0:d}:VOLT:AMPL {1}'.format(ch_num, amp))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.25)

        if offset is not None:
            for chnl, off in offset.items():
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                self.write('SOUR{0:d}:VOLT:OFFSET {1}'.format(ch_num, off))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.25)
        return self.get_analog_level()

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
            low = ['d_ch1', 'd_ch4']
        to obtain the low voltage values of digital channel 1 an 4. A possible
        answer might be
            {'d_ch1': -0.5, 'd_ch4': 2.0} {}
        since no high request was performed.

        The major difference to analog signals is that digital signals are
        either ON or OFF, whereas analog channels have a varying amplitude
        range. In contrast to analog output levels, digital output levels are
        defined by a voltage, which corresponds to the ON status and a voltage
        which corresponds to the OFF status (both denoted in (absolute) voltage)

        In general there is no bijective correspondence between
        (amplitude, offset) and (value high, value low)!
        """
        # TODO: Test with multiple channel AWG
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
            d_ch_number = int(chnl.rsplit('_ch', 1)[1])
            a_ch_number = (1 + d_ch_number) // 2
            marker_index = 2 - (d_ch_number % 2)
            low_val[chnl] = float(
                self.query('SOUR{0:d}:MARK{1:d}:VOLT:LOW?'.format(a_ch_number, marker_index)))
        # get high marker levels
        for chnl in high:
            if chnl not in digital_channels:
                continue
            d_ch_number = int(chnl.rsplit('_ch', 1)[1])
            a_ch_number = (1 + d_ch_number) // 2
            marker_index = 2 - (d_ch_number % 2)
            high_val[chnl] = float(
                self.query('SOUR{0:d}:MARK{1:d}:VOLT:HIGH?'.format(a_ch_number, marker_index)))

        return low_val, high_val

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
            if high[key] - low[key] < 0.5:
                self.log.warning('Voltage difference is too small. Reducing low voltage level.')
                low[key] = high[key] - 0.5
            elif high[key] - low[key] > 1.4:
                self.log.warning('Voltage difference is too large. Increasing low voltage level.')
                low[key] = high[key] - 1.4

        # set high marker levels
        for chnl in high:
            if chnl not in digital_channels:
                continue
            d_ch_number = int(chnl.rsplit('_ch', 1)[1])
            a_ch_number = (1 + d_ch_number) // 2
            marker_index = 2 - (d_ch_number % 2)
            self.write('SOUR{0:d}:MARK{1:d}:VOLT:HIGH {2}'.format(a_ch_number, marker_index, high[chnl]))
        # set low marker levels
        for chnl in low:
            if chnl not in digital_channels:
                continue
            d_ch_number = int(chnl.rsplit('_ch', 1)[1])
            a_ch_number = (1 + d_ch_number) // 2
            marker_index = 2 - (d_ch_number % 2)
            self.write('SOUR{0:d}:MARK{1:d}:VOLT:LOW {2}'.format(a_ch_number, marker_index, low[chnl]))

        return self.get_digital_level()

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
        # constraints = self.get_constraints()

        analog_channels = self._get_all_analog_channels()

        active_ch = dict()
        for ch_num, a_ch in enumerate(analog_channels, 1):
            # check what analog channels are active
            active_ch[a_ch] = bool(int(self.query('OUTPUT{0:d}:STATE?'.format(ch_num))))
            # check how many markers are active on each channel, i.e. the DAC resolution
            if active_ch[a_ch]:
                digital_mrk = 10 - int(self.query('SOUR{0:d}:DAC:RES?'.format(ch_num)))
                if digital_mrk == 2:
                    active_ch['d_ch{0:d}'.format(ch_num * 2)] = True
                    active_ch['d_ch{0:d}'.format(ch_num * 2 - 1)] = True
                elif digital_mrk == 1:
                    active_ch['d_ch{0:d}'.format(ch_num * 2)] = False
                    active_ch['d_ch{0:d}'.format(ch_num * 2 - 1)] = True
                else:
                    active_ch['d_ch{0:d}'.format(ch_num * 2)] = False
                    active_ch['d_ch{0:d}'.format(ch_num * 2 - 1)] = False
            else:
                active_ch['d_ch{0:d}'.format(ch_num * 2)] = False
                active_ch['d_ch{0:d}'.format(ch_num * 2 - 1)] = False

        # return either all channel information or just the one asked for.
        if ch is not None:
            chnl_to_delete = [chnl for chnl in active_ch if chnl not in ch]
            for chnl in chnl_to_delete:
                del active_ch[chnl]
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
            self.log.error('Trying to (de)activate channels that are not present in AWG70k.\n'
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

        # calculate dac resolution for each analog channel and set it in hardware.
        # Also (de)activate the analog channels accordingly
        max_res = constraints.dac_resolution['max']
        for a_ch in analog_channels:
            ach_num = int(a_ch.rsplit('_ch', 1)[1])
            # determine number of markers for current a_ch
            if new_channels_state['d_ch{0:d}'.format(2 * ach_num - 1)]:
                marker_num = 2 if new_channels_state['d_ch{0:d}'.format(2 * ach_num)] else 1
            else:
                marker_num = 0
            # set DAC resolution for this channel
            dac_res = max_res - marker_num
            self.write('SOUR{0:d}:DAC:RES {1:d}'.format(ach_num, dac_res))
            # (de)activate the analog channel
            if new_channels_state[a_ch]:
                self.write('OUTPUT{0:d}:STATE ON'.format(ach_num))
            else:
                self.write('OUTPUT{0:d}:STATE OFF'.format(ach_num))

        return self.get_active_channels()

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
        if state:
            self.log.warning('Interleave mode not available for the AWG 70000 Series!\n'
                             'Method call will be ignored.')
        return False

    def reset(self):
        """Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.write('*RST')
        self.write('*WAI')
        return 0

    def query(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        return self.awg.query(question).strip().rstrip('\n').rstrip().strip('"')

    def write(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        bytes_written, enum_status_code = self.awg.write(command)
        return int(enum_status_code)

    def new_sequence(self, name, steps):
        """
        Generate a new sequence 'name' having 'steps' number of steps with immediate (async.) jump
        timing.

        @param str name: Name of the sequence which should be generated
        @param int steps: Number of steps

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        if name in self.get_sequence_names():
            self.delete_sequence(name)
        self.write('SLIS:SEQ:NEW "{0}", {1:d}'.format(name, steps))
        self.write('SLIS:SEQ:EVEN:JTIM "{0}", IMM'.format(name))
        return 0

    def sequence_set_waveform(self, sequence_name, waveform_name, step, track):
        """
        Set the waveform 'waveform_name' to position 'step' in the sequence 'sequence_name'.

        @param str sequence_name: Name of the sequence which should be editted
        @param str waveform_name: Name of the waveform which should be added
        @param int step: Position of the added waveform
        @param int track: track which should be editted

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        self.write('SLIS:SEQ:STEP{0:d}:TASS{1:d}:WAV "{2}", "{3}"'.format(step,
                                                                          track,
                                                                          sequence_name,
                                                                          waveform_name))
        return 0

    def sequence_set_repetitions(self, sequence_name, step, repeat=0):
        """
        Set the repetition counter of sequence "sequence_name" at step "step" to "repeat".
        A repeat value of -1 denotes infinite repetitions; 0 means the step is played once.

        @param str sequence_name: Name of the sequence to be edited
        @param int step: Sequence step to be edited
        @param int repeat: number of repetitions. (-1: infinite, 0: once, 1: twice, ...)

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1
        repeat = 'INF' if repeat < 0 else str(int(repeat + 1))
        self.write('SLIS:SEQ:STEP{0:d}:RCO "{1}", {2}'.format(step, sequence_name, repeat))
        return 0

    def sequence_set_goto(self, sequence_name, step, goto=-1):
        """

        @param str sequence_name:
        @param int step:
        @param int goto:

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        goto = str(int(goto)) if goto > 0 else 'NEXT'
        self.write('SLIS:SEQ:STEP{0:d}:GOTO "{1}", {2}'.format(step, sequence_name, goto))
        return 0

    def sequence_set_event_jump(self, sequence_name, step, trigger='OFF', jumpto=0):
        """
        Set the event trigger input of the specified sequence step and the jump_to destination.

        @param str sequence_name: Name of the sequence to be edited
        @param int step: Sequence step to be edited
        @param str trigger: Trigger string specifier. ('OFF', 'A', 'B' or 'INT')
        @param int jumpto: The sequence step to jump to. 0 or -1 is interpreted as next step

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        trigger = self.__event_triggers.get(trigger)
        if trigger is None:
            self.log.error('Invalid trigger specifier "{0}".\n'
                           'Please choose one of: "OFF", "A", "B", "INT"')
            return -1

        self.write('SLIS:SEQ:STEP{0:d}:EJIN "{1}", {2}'.format(step, sequence_name, trigger))
        # Set event_jump_to if event trigger is enabled
        if trigger != 'OFF':
            jumpto = 'NEXT' if jumpto <= 0 else str(int(jumpto))
            self.write('SLIS:SEQ:STEP{0:d}:EJUM "{1}", {2}'.format(step, sequence_name, jumpto))
        return 0

    def sequence_set_wait_trigger(self, sequence_name, step, trigger='OFF'):
        """
        Make a certain sequence step wait for a trigger to start playing.

        @param str sequence_name: Name of the sequence to be edited
        @param int step: Sequence step to be edited
        @param str trigger: Trigger string specifier. ('OFF', 'A', 'B' or 'INT')

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        trigger = self.__event_triggers.get(trigger)
        if trigger is None:
            self.log.error('Invalid trigger specifier "{0}".\n'
                           'Please choose one of: "OFF", "A", "B", "INT"')
            return -1

        self.write('SLIS:SEQ:STEP{0:d}:WINP "{1}", {2}'.format(step, sequence_name, trigger))
        return 0

    def sequence_set_flags(self, sequence_name, step, flags_t=None, flags_h=None):
        """
        Set the flags in "flags" to HIGH (trigger=False) during the sequence step or let the flags
        send out a fixed duration trigger pulse (trigger=True). All other flags are set to LOW.

        @param str sequence_name: Name of the sequence to be edited
        @param int step: Sequence step to be edited
        @param list flags_t: List of flag trigger specifiers to be active during this sequence step, if both options are
                             selected, the flag is set to trigger (PULS)
        @param list flags_h: List of flag high specifiers to be active during this sequence step

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        for flag in ('A', 'B', 'C', 'D'):
            if flag in flags_t:
                state = 'PULS'
            elif flag in flags_h:
                state = 'HIGH'
            else:
                state = 'LOW'

            self.write('SLIS:SEQ:STEP{0:d}:TFL1:{1}FL "{2}",{3}'.format(step,
                                                                        flag,
                                                                        sequence_name,
                                                                        state))
        return 0

    def make_sequence_continuous(self, sequencename):
        """
        Usually after a run of a sequence the output stops. Many times it is desired that the full
        sequence is repeated many times. This is achieved here by setting the 'jump to' value of
        the last element to 'First'

        @param sequencename: Name of the sequence which should be made continous

        @return int last_step: The step number which 'jump to' has to be set to 'First'
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        last_step = int(self.query('SLIS:SEQ:LENG? "{0}"'.format(sequencename)))
        err = self.sequence_set_goto(sequencename, last_step, 1)
        if err < 0:
            last_step = err
        return last_step

    def force_jump_sequence(self, final_step, channel=1):
        """
        This command forces the sequencer to jump to the specified step per channel. A
        force jump does not require a trigger event to execute the jump.
        For two channel instruments, if both channels are playing the same sequence, then
        both channels jump simultaneously to the same sequence step.

        @param channel: determines the channel number. If omitted, interpreted as 1
        @param final_step: Step to jump to. Possible options are
            FIRSt - This enables the sequencer to jump to first step in the sequence.
            CURRent - This enables the sequencer to jump to the current sequence step,
            essentially starting the current step over.
            LAST - This enables the sequencer to jump to the last step in the sequence.
            END - This enables the sequencer to go to the end and play 0 V until play is
            stopped.
            <NR1> - This enables the sequencer to jump to the specified step, where the
            value is between 1 and 16383.

        """
        self.write('SOURCE{0:d}:JUMP:FORCE {1}'.format(channel, final_step))
        return

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
        return natural_sort(largest_config)

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

    def _is_output_on(self):
        """
        Aks the AWG if the output is enabled, i.e. if the AWG is running

        @return: bool, (True: output on, False: output off)
        """
        return bool(int(self.query('AWGC:RST?')))

    def _get_filenames_on_device(self):
        """

        @return list: filenames found in <ftproot>\\waves
        """
        filename_list = list()
        with FTP(self._ip_address) as ftp:
            ftp.login(user=self._username, passwd=self._password)
            ftp.cwd(self.ftp_working_dir)
            # get only the files from the dir and skip possible directories
            log = list()
            ftp.retrlines('LIST', callback=log.append)
            for line in log:
                if '<DIR>' not in line:
                    # that is how a potential line is looking like:
                    #   '05-10-16  05:22PM                  292 SSR aom adjusted.seq'
                    # The first part consists of the date information. Remove this information and
                    # separate the first number, which indicates the size of the file. This is
                    # necessary if the filename contains whitespaces.
                    size_filename = line[18:].lstrip()
                    # split after the first appearing whitespace and take the rest as filename.
                    # Remove for safety all trailing and leading whitespaces:
                    filename = size_filename.split(' ', 1)[1].strip()
                    filename_list.append(filename)
        return filename_list

    def _delete_file(self, filename):
        """

        @param str filename:
        """
        if filename in self._get_filenames_on_device():
            with FTP(self._ip_address) as ftp:
                ftp.login(user=self._username, passwd=self._password)
                ftp.cwd(self.ftp_working_dir)
                ftp.delete(filename)
        return

    def _send_file(self, filename):
        """

        @param filename:
        @return:
        """
        # check input
        if not filename:
            self.log.error('No filename provided for file upload to awg!\nCommand will be ignored.')
            return -1

        filepath = os.path.join(self._tmp_work_dir, filename)
        if not os.path.isfile(filepath):
            self.log.error('No file "{0}" found in "{1}". Unable to upload!'
                           ''.format(filename, self._tmp_work_dir))
            return -1

        # Delete old file on AWG by the same filename
        self._delete_file(filename)

        # Transfer file
        with FTP(self._ip_address) as ftp:
            ftp.login(user=self._username, passwd=self._password)
            ftp.cwd(self.ftp_working_dir)
            with open(filepath, 'rb') as file:
                ftp.storbinary('STOR ' + filename, file)
        return 0

    def _write_wfmx(self, filename, analog_samples, marker_bytes, is_first_chunk, is_last_chunk,
                    total_number_of_samples):
        """
        Appends a sampled chunk of a whole waveform to a wfmx-file. Create the file
        if it is the first chunk.
        If both flags (is_first_chunk, is_last_chunk) are set to TRUE it means
        that the whole ensemble is written as a whole in one big chunk.

        @param name: string, represents the name of the sampled ensemble
        @param analog_samples: dict containing float32 numpy ndarrays, contains the
                                       samples for the analog channels that
                                       are to be written by this function call.
        @param marker_bytes: np.ndarray containing bool numpy ndarrays, contains the samples
                                      for the digital channels that
                                      are to be written by this function call.
        @param total_number_of_samples: int, The total number of samples in the
                                        entire waveform. Has to be known in advance.
        @param is_first_chunk: bool, indicates if the current chunk is the
                               first write to this file.
        @param is_last_chunk: bool, indicates if the current chunk is the last
                              write to this file.

        @return list: the list contains the string names of the created files for the passed
                      presampled arrays
        """
        # The memory overhead of the tmp file write/read process in bytes. Only used if wfmx file is
        # written in chunks in order to avoid excessive memory usage.
        tmp_bytes_overhead = 16777216  # 16 MB

        if not filename.endswith('.wfmx'):
            filename += '.wfmx'
        wfmx_path = os.path.join(self._tmp_work_dir, filename)
        tmp_path = os.path.join(self._tmp_work_dir, 'digital_tmp.bin')

        # if it is the first chunk, create the .WFMX file with header.
        if is_first_chunk:
            # create header
            header = self._create_xml_header(total_number_of_samples, marker_bytes is not None)
            # write header
            with open(wfmx_path, 'wb') as wfmxfile:
                wfmxfile.write(header.encode('utf8'))
            # Check if a tmp digital samples file is present and delete it if necessary.
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)

        # append analog samples to the .WFMX file.
        # Write digital samples in temporary file if not the entire samples are passed at once.
        with open(wfmx_path, 'ab') as wfmxfile:
            # append analog samples in binary format. One sample is 4 bytes (np.float32).
            wfmxfile.write(analog_samples)

        # Write digital samples to tmp file if chunkwise writing is used and it's not the last chunk
        if not is_last_chunk and marker_bytes is not None:
            with open(tmp_path, 'ab') as tmp_file:
                tmp_file.write(marker_bytes)

        # If this is the last chunk, write digital samples from tmp file to wfmx file (if present)
        # and also append the currently passed digital samples to wfmx file.
        # Read from tmp file in chunks of tmp_bytes_overhead in order to avoid too much memory
        # overhead.
        if is_last_chunk and marker_bytes is not None:
            with open(wfmx_path, 'ab') as wfmxfile:
                # Copy over digital samples from tmp file. Delete tmp file afterwards.
                if os.path.isfile(tmp_path):
                    with open(tmp_path, 'rb') as tmp_file:
                        while True:
                            tmp = tmp_file.read(tmp_bytes_overhead)
                            if not tmp:
                                break
                            wfmxfile.write(tmp)
                    os.remove(tmp_path)
                # Append current digital samples array to wfmx file
                wfmxfile.write(marker_bytes)
        return

    def _create_xml_header(self, number_of_samples, markers_active):
        """
        This function creates an xml file containing the header for the wfmx-file format using
        etree.
        """
        hdr = ET.Element('DataFile', offset='XXXXXXXXX', version='0.1')
        dsc = ET.SubElement(hdr, 'DataSetsCollection', xmlns='http://www.tektronix.com')
        datasets = ET.SubElement(dsc, 'DataSets', version='1', xmlns='http://www.tektronix.com')
        datadesc = ET.SubElement(datasets, 'DataDescription')
        sub_elem = ET.SubElement(datadesc, 'NumberSamples')
        sub_elem.text = str(int(number_of_samples))
        sub_elem = ET.SubElement(datadesc, 'SamplesType')
        sub_elem.text = 'AWGWaveformSample'
        sub_elem = ET.SubElement(datadesc, 'MarkersIncluded')
        sub_elem.text = 'true' if markers_active else 'false'
        sub_elem = ET.SubElement(datadesc, 'NumberFormat')
        sub_elem.text = 'Single'
        sub_elem = ET.SubElement(datadesc, 'Endian')
        sub_elem.text = 'Little'
        sub_elem = ET.SubElement(datadesc, 'Timestamp')
        sub_elem.text = '2014-10-28T12:59:52.9004865-07:00'
        prodspec = ET.SubElement(datasets, 'ProductSpecific', name='')
        sub_elem = ET.SubElement(prodspec, 'ReccSamplingRate', units='Hz')
        sub_elem.text = str(self.get_sample_rate())
        sub_elem = ET.SubElement(prodspec, 'ReccAmplitude', units='Volts')
        sub_elem.text = '0.5'
        sub_elem = ET.SubElement(prodspec, 'ReccOffset', units='Volts')
        sub_elem.text = '0'
        sub_elem = ET.SubElement(prodspec, 'SerialNumber')
        sub_elem = ET.SubElement(prodspec, 'SoftwareVersion')
        sub_elem.text = '4.0.0075'
        sub_elem = ET.SubElement(prodspec, 'UserNotes')
        sub_elem = ET.SubElement(prodspec, 'OriginalBitDepth')
        sub_elem.text = 'Floating'
        sub_elem = ET.SubElement(prodspec, 'Thumbnail')
        sub_elem = ET.SubElement(prodspec, 'CreatorProperties', name='Basic Waveform')
        sub_elem = ET.SubElement(hdr, 'Setup')

        xml_header = ET.tostring(hdr, encoding='unicode')
        xml_header = xml_header.replace('><', '>\r\n<')

        # Calculates the length of the header and replace placeholder with actual number
        xml_header = xml_header.replace('XXXXXXXXX', str(len(xml_header)).zfill(9))
        return xml_header

    def _has_sequence_mode(self):
        return '03' in self.__installed_options
