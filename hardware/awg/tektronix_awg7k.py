# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for AWG7000 Series.

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
from ftplib import FTP
from collections import OrderedDict

from core.util.modules import get_home_dir
from core.util.helpers import natural_sort
from core.module import Base
from core.configoption import ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints, SequenceOption


class AWG7k(Base, PulserInterface):
    """ A hardware module for the Tektronix AWG7000 series for generating
        waveforms and sequences thereof.

    Example config for copy-paste:

    pulser_awg7000:
        module.Class: 'awg.tektronix_awg7k.AWG7k'
        awg_visa_address: 'TCPIP::10.42.0.211::INSTR'
        awg_ip_address: '10.42.0.211'
        timeout: 60
        # tmp_work_dir: 'C:\\Software\\qudi_pulsed_files' # optional
        # ftp_root_dir: 'C:\\inetpub\\ftproot' # optional, root directory on AWG device
        # ftp_login: 'anonymous' # optional, the username for ftp login
        # ftp_passwd: 'anonymous@' # optional, the password for ftp login

    """

    # config options
    _tmp_work_dir = ConfigOption(name='tmp_work_dir',
                                 default=os.path.join(get_home_dir(), 'pulsed_files'),
                                 missing='warn')
    _visa_address = ConfigOption(name='awg_visa_address', missing='error')
    _ip_address = ConfigOption(name='awg_ip_address', missing='error')
    _ftp_dir = ConfigOption(name='ftp_root_dir', default='C:\\inetpub\\ftproot', missing='warn')
    _username = ConfigOption(name='ftp_login', default='anonymous', missing='warn')
    _password = ConfigOption(name='ftp_passwd', default='anonymous@', missing='warn')
    _visa_timeout = ConfigOption(name='timeout', default=30, missing='nothing')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # Get an instance of the visa resource manager
        self._rm = visa.ResourceManager()

        self.awg = None  # This variable will hold a reference to the awg visa resource

        self.ftp_working_dir = 'waves'  # subfolder of FTP root dir on AWG disk to work in

        self.installed_options = list()  # will hold the encoded installed options available on awg
        self._internal_ch_state = {
            'a_ch1': False,
            'a_ch2': False,
        }
        self._written_sequences = []  # Helper variable since written sequences can not be queried
        self._loaded_sequences = []  # Helper variable since a loaded sequence can not be queried :(
        self._marker_byte_dict = {0: b'\x00', 1: b'\x01', 2: b'\x02', 3: b'\x03'}
        self._event_triggers = {'OFF': 'OFF', 'ON': 'ON'}

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Create work directory if necessary
        if not os.path.exists(self._tmp_work_dir):
            os.makedirs(os.path.abspath(self._tmp_work_dir))

        try:
            self.awg = self._rm.open_resource(
                self._visa_address,
            )
            # set timeout by default to 30 sec
            self.awg.timeout = self._visa_timeout * 1000
        except:
            self.awg = None
            self.log.error(
                'VISA address "{0}" not found by the pyVISA resource manager.\nCheck '
                'the connection by using for example "Agilent Connection Expert".'
                ''.format(self._visa_address))

        # try connecting to AWG using FTP protocol
        with FTP(self._ip_address) as ftp:
            ftp.login(user=self._username, passwd=self._password)
            ftp.cwd(self.ftp_working_dir)
            self.log.debug('FTP working dir: {0}'.format(ftp.pwd()))

        idn = self.query('*IDN?').split(',')
        self.mfg, self.model, self.ser, self.fw_ver = idn

        # Options of AWG7000 series:
        #              Option 01: Memory expansion to 64,8 MSamples (Million points)
        #              Option 06: Interleave and extended analog output bandwidth
        #              Option 08: Fast sequence switching
        #              Option 09: Subsequence and Table Jump

        self.installed_options = self.query('*OPT?').split(',')
        # TODO: inclulde proper routine to check and change zeroing functionality

        self.log.info('Found {} {} Serial: {} FW: {} options: {}'.format(
            self.mfg, self.model, self.ser, self.fw_ver, self.installed_options
        ))
        # Set current directory on AWG
        self.write('MMEM:CDIR "{0}"'.format(os.path.join(self._ftp_dir, self.ftp_working_dir)))
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Closes the connection to the AWG
        try:
            self.awg.close()
        except:
            self.log.debug('Closing AWG connection using pyvisa failed.')
        self.log.info('Closed connection to AWG')
        return

    # =========================================================================
    # Below all the Pulser Interface routines.
    # =========================================================================

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
        # TODO: Check values for AWG7122c
        constraints = PulserConstraints()

        if self.model == 'AWG7122C':
            if self.get_interleave():
                constraints.sample_rate.min = 12.0e9
                constraints.sample_rate.max = 24.0e9
                constraints.sample_rate.step = 5.0e2
                constraints.sample_rate.default = 24.0e9
            else:
                constraints.sample_rate.min = 10.0e6
                constraints.sample_rate.max = 12.0e9
                constraints.sample_rate.step = 10.0e6
                constraints.sample_rate.default = 12.0e9

        elif self.model == 'AWG7082C':
            if self.get_interleave():
                constraints.sample_rate.min = 8.0e9
                constraints.sample_rate.max = 16.0e9
                constraints.sample_rate.step = 5.0e2
                constraints.sample_rate.default = 16.0e9
            else:
                constraints.sample_rate.min = 10.0e6
                constraints.sample_rate.max = 8.0e9
                constraints.sample_rate.step = 10.0e6
                constraints.sample_rate.default = 8.0e9

        elif self.model == 'AWG7052':
            constraints.sample_rate.min = 10.0e6
            constraints.sample_rate.max = 5.0e9
            constraints.sample_rate.step = 10.0e6 # <=== not sure
            constraints.sample_rate.default = 5.0e9

        if '02' in self.installed_options or self._has_interleave():
            constraints.a_ch_amplitude.max = 1.0
            constraints.a_ch_amplitude.step = 0.001
            constraints.a_ch_amplitude.default = 1.0
        else:
            constraints.a_ch_amplitude.max = 2.0
            constraints.a_ch_amplitude.step = 0.001
            constraints.a_ch_amplitude.default = 2.0

        if self._zeroing_enabled():
            constraints.a_ch_amplitude.min = 0.25
        else:
            constraints.a_ch_amplitude.min = 0.5

        constraints.d_ch_low.min = -1.4
        constraints.d_ch_low.max = 0.9
        constraints.d_ch_low.step = 0.01
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = -0.9
        constraints.d_ch_high.max = 1.4
        constraints.d_ch_high.step = 0.01
        constraints.d_ch_high.default = 1.4
        
        if self.model == 'AWG7052':
            constraints.waveform_length.min = 960
            constraints.waveform_length.step = 64
            constraints.waveform_length.default = 960
        else:
            if self.get_interleave():
                constraints.waveform_length.min = 1920
                constraints.waveform_length.step = 8
            else:
                constraints.waveform_length.min = 960
                constraints.waveform_length.step = 4
            constraints.waveform_length.default = 1920

        if '01' in self.installed_options:
            constraints.waveform_length.max = 64800000
        else:
            constraints.waveform_length.max = 32400000

        if self.model == 'AWG7052':
            constraints.waveform_num.min = 1
            constraints.waveform_num.max = 16000
            constraints.waveform_num.step = 1
            constraints.waveform_num.default = 1
        else:
            constraints.waveform_num.min = 1
            constraints.waveform_num.max = 32000
            constraints.waveform_num.step = 1
            constraints.waveform_num.default = 1

        # there doesn't seem to be something like number of sequences according to the technical reference
        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 16000
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1

        constraints.subsequence_num.min = 1
        constraints.subsequence_num.max = 8000
        constraints.subsequence_num.step = 1
        constraints.subsequence_num.default = 1

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65536
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0

        # Device has only one trigger and no flags
        constraints.event_triggers = ['ON']
        constraints.flags = list()

        if self.model == 'AWG7052':
            constraints.sequence_steps.min = 0
            constraints.sequence_steps.max = 4000
            constraints.sequence_steps.step = 1
            constraints.sequence_steps.default = 0
        else:
            constraints.sequence_steps.min = 0
            constraints.sequence_steps.max = 8000
            constraints.sequence_steps.step = 1
            constraints.sequence_steps.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe UNAMBIGUOUSLY the
        # channels. Here all possible channel configurations are stated, where only the generic
        # names should be used. The names for the different configurations can be customary chosen.
        activation_config = OrderedDict()
        activation_config['all'] = frozenset({'a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3', 'd_ch4'})
        # Usage of channel 1 only:
        activation_config['A1_M1_M2'] = frozenset({'a_ch1', 'd_ch1', 'd_ch2'})
        # Usage of channel 2 only:
        activation_config['A2_M3_M4'] = frozenset({'a_ch2', 'd_ch3', 'd_ch4'})
        # Only both analog channels
        activation_config['Two_Analog'] = frozenset({'a_ch1', 'a_ch2'})
        # Usage of one analog channel without digital channel
        activation_config['Analog1'] = frozenset({'a_ch1'})
        # Usage of one analog channel without digital channel
        activation_config['Analog2'] = frozenset({'a_ch2'})
        constraints.activation_config = activation_config

        if self._has_sequence_mode():
            constraints.sequence_option = SequenceOption.OPTIONAL
        else:
            constraints.sequence_option = SequenceOption.NON

        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        # Get all active channels
        chnl_activation = self.get_active_channels()
        channel_numbers = sorted(int(chnl.split('_ch')[1]) for chnl in chnl_activation if
                                 chnl.startswith('a') and chnl_activation[chnl])
        # do nothing if AWG is already running
        if not self._is_output_on():
            for ch in channel_numbers:
                self.write('OUTPUT{0}:STATE ON'.format(ch))
            self.write('AWGC:RUN')
            # wait until the AWG is actually running
            while not self._is_output_on():
                time.sleep(0.2)
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
                time.sleep(0.2)
        return self.get_status()[0]

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

        @return dict: Dictionary containing the actually loaded waveforms per channel.
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
            self.log.error('Unable to load all waveforms into channels.\n'
                           'One or more channels to set are not active.')
            return self.get_loaded_assets()

        # Check if all waveforms to load are present on device memory
        if not set(load_dict.values()).issubset(self.get_waveform_names()):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more waveforms to load are missing on device memory.')
            return self.get_loaded_assets()

        # Load waveforms into channels
        for chnl_num, waveform in load_dict.items():
            # load into channel
            self.write('SOUR{0:d}:WAV "{1}"'.format(chnl_num, waveform))
            while self.query('SOUR{0:d}:WAV?'.format(chnl_num)) != waveform:
                time.sleep(0.1)

        self.set_mode('C')
        return self.get_loaded_assets()

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param sequence_name:  dict|list, a dictionary with keys being one of the available channel
                                      index and values being the name of the already written
                                      waveform to load into the channel.
                                      Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                  {1: rabi_ch2, 2: rabi_ch1}
                                      If just a list of waveform names if given, the channel
                                      association will be invoked from the channel
                                      suffix '_ch1', '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """
        if sequence_name not in self.get_sequence_names():
            self.log.error('Unable to load sequence.\n'
                           'Sequence to load is missing on device memory.')
            return self.get_loaded_assets()

        # set the AWG to the event jump mode:
        self.write('AWGC:EVENT:JMODE EJUMP')
        self.set_mode('S')

        self._loaded_sequences = [sequence_name]
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

        run_mode = self.query('AWGC:RMOD?')
        if run_mode == 'CONT':
            current_type = 'waveform'
            for chnl_num in channel_numbers:
                loaded_assets[chnl_num] = self.query('SOUR{0}:WAV?'.format(chnl_num))

        elif run_mode == 'SEQ':
            current_type = 'sequence'
            for chnl_num in channel_numbers:
                if len(self._loaded_sequences) > 0:
                    loaded_assets[chnl_num] = self._loaded_sequences[0]

        return loaded_assets, current_type

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)
        """
        self.write('WLIS:WAV:DEL ALL')
        if '09' in self.installed_options:
            self.write('SLIS:SUBS:DEL ALL')
        self.write('SEQUENCE:LENGTH 0')
        self._written_sequences = []
        self._loaded_sequences = []
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
                      1: 'Device is active and running',
                      2: 'Device is waiting for trigger.'}
        current_status = -1 if self.awg is None else int(self.query('AWGC:RST?'))
        return current_status, status_dic

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead retrieve the current
        sample rate directly from the device.
        """
        return float(self.query('SOUR1:FREQ?'))

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """
        self.write('SOUR1:FREQ {0:.4G}MHz\n'.format(sample_rate / 1e6))
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.1)
        # Here we need to wait, because when the sampling rate is changed AWG is busy
        # and therefore the ask in get_sample_rate will return an empty string.
        time.sleep(1)
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
        # FIXME: No sanity checking done here with constraints
        amp = dict()
        off = dict()

        chnl_list = self._get_all_analog_channels()

        # get pp amplitudes
        if amplitude is None:
            for ch_num, chnl in enumerate(chnl_list):
                amp[chnl] = float(self.query('SOUR{0:d}:VOLT:AMPL?'.format(ch_num + 1)))
        else:
            for chnl in amplitude:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    amp[chnl] = float(self.query('SOUR{0:d}:VOLT:AMPL?'.format(ch_num)))
                else:
                    self.log.warning('Get analog amplitude from AWG7122c channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))

        # get voltage offsets
        no_offset = '02' in self.installed_options or '06' in self.installed_options
        if offset is None:
            for ch_num, chnl in enumerate(chnl_list):
                off[chnl] = 0.0 if no_offset else float(
                    self.query('SOUR{0:d}:VOLT:OFFS?'.format(ch_num + 1)))
        else:
            for chnl in offset:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    off[chnl] = 0.0 if no_offset else float(
                        self.query('SOUR{0:d}:VOLT:OFFS?'.format(ch_num)))
                else:
                    self.log.warning('Get analog offset from AWG7122c channel "{0}" failed. '
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
            for a_ch in amplitude:
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                self.write('SOUR{0:d}:VOLT:AMPL {1}'.format(ch_num, amplitude[a_ch]))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.1)

        no_offset = '02' in self.installed_options or '06' in self.installed_options
        if offset is not None and not no_offset:
            for a_ch in offset:
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                self.write('SOUR{0:d}:VOLT:OFFSET {1}'.format(ch_num, offset[a_ch]))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.1)
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
        ret_low = {}
        ret_high = {}

        if low is None:
            low = {}

        if high is None:
            high = {}

        # If you want to check the input use the constraints:
        # constraints = self.get_constraints()

        digital_channels = self._get_all_digital_channels()

        # set low marker levels
        for ch, level in low.items():
            if ch not in digital_channels:
                continue
            d_ch_number = int(ch.rsplit('_ch', 1)[1])
            a_ch_number = (1 + d_ch_number) // 2
            marker_index = 2 - (d_ch_number % 2)
            self.write('SOUR{0:d}:MARK{1:d}:VOLT:LOW {2}'.format(a_ch_number, marker_index, level))
            ret_low[ch] = float(
                self.query('SOUR{0:d}:MARK{1:d}:VOLT:LOW?'.format(a_ch_number, marker_index)))

        # set high marker levels
        for ch, level in high.items():
            if ch not in digital_channels:
                continue
            d_ch_number = int(ch.rsplit('_ch', 1)[1])
            a_ch_number = (1 + d_ch_number) // 2
            marker_index = 2 - (d_ch_number % 2)
            self.write('SOUR{0:d}:MARK{1:d}:VOLT:HIGH {2}'.format(a_ch_number, marker_index, level))
            ret_high[ch] = float(
                self.query('SOUR{0:d}:MARK{1:d}:VOLT:HIGH?'.format(a_ch_number, marker_index)))

        return ret_low, ret_high

    def get_active_channels(self, ch=None):
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
        # If you want to check the input use the constraints:
        # constraints = self.get_constraints()

        analog_channels = self._get_all_analog_channels()

        active_ch = dict()
        for ch_num, a_ch in enumerate(analog_channels):
            ch_num = ch_num + 1
            # check what analog channels are active
            if self._is_output_on():
                active_ch[a_ch] = bool(int(self.query('OUTPUT{0:d}:STATE?'.format(ch_num))))
            else:
                active_ch[a_ch] = self._internal_ch_state[a_ch]
            # check how many markers are active on each channel, i.e. the DAC resolution
            if active_ch[a_ch]:
                digital_mrk = 10 - int(self.query('SOUR{0:d}:DAC:RES?'.format(ch_num)))
                if digital_mrk == 2:
                    active_ch['d_ch{0:d}'.format(ch_num * 2)] = True
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
            self.log.error('Trying to (de)activate channels that are not present in AWG.\n'
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
        for a_ch in analog_channels:
            ach_num = int(a_ch.rsplit('_ch', 1)[1])
            # determine number of markers for current a_ch
            if new_channels_state['d_ch{0:d}'.format(2 * ach_num)]:
                marker_num = 2
            else:
                marker_num = 0
            # set DAC resolution for this channel
            dac_res = 10 - marker_num
            self.write('SOUR{0:d}:DAC:RES {1:d}'.format(ach_num, dac_res))
            # (de)activate the analog channel
            if new_channels_state[a_ch]:
                self.write('OUTPUT{0:d}:STATE ON'.format(ach_num))
            else:
                self.write('OUTPUT{0:d}:STATE OFF'.format(ach_num))
            self._internal_ch_state[a_ch] = new_channels_state[a_ch]
        return self.get_active_channels()

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
        constraints = self.get_constraints()

        if len(analog_samples) == 0:
            self.log.error('No analog samples passed to write_waveform method in awg7k.')
            return -1, waveforms

        if total_number_of_samples < constraints.waveform_length.min:
            self.log.error('Unable to write waveform.\n'
                           'Number of samples to write ({0:d}) is '
                           'smaller than the allowed minimum waveform length ({1:d}).'
                           ''.format(total_number_of_samples, constraints.waveform_length.min))
            return -1, waveforms
        if total_number_of_samples > constraints.waveform_length.max:
            self.log.error('Unable to write waveform.\n'
                           'Number of samples to write ({0:d}) is '
                           'greater than the allowed maximum waveform length ({1:d}).'
                           ''.format(total_number_of_samples, constraints.waveform_length.max))
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
            a_ch_num = int(a_ch.rsplit('ch', 1)[1])
            # Get the digital channel specifiers belonging to this analog channel markers
            mrk_ch_1 = 'd_ch{0:d}'.format(a_ch_num * 2 - 1)
            mrk_ch_2 = 'd_ch{0:d}'.format(a_ch_num * 2)

            start = time.time()
            # Encode marker information in an array of bytes (uint8). Avoid intermediate copies!!!
            if mrk_ch_1 in digital_samples and mrk_ch_2 in digital_samples:
                mrk_bytes = digital_samples[mrk_ch_2].view('uint8')
                tmp_bytes = digital_samples[mrk_ch_1].view('uint8')
                # Marker bits live in the LSB of the byte, as opposed to the AWG70k
                np.left_shift(mrk_bytes, 1, out=mrk_bytes)
                np.left_shift(tmp_bytes, 0, out=tmp_bytes)
                np.add(mrk_bytes, tmp_bytes, out=mrk_bytes)
            else:
                mrk_bytes = None
            self.log.debug('Prepare digital channel data: {0}'.format(time.time() - start))

            # Create waveform name string
            wfm_name = '{0}_ch{1:d}'.format(name, a_ch_num)

            # Write WFM file for waveform
            start = time.time()
            self._write_wfm(filename=wfm_name,
                            analog_samples=analog_samples[a_ch],
                            marker_bytes=mrk_bytes,
                            is_first_chunk=is_first_chunk,
                            is_last_chunk=is_last_chunk,
                            total_number_of_samples=total_number_of_samples)

            self.log.debug('Write WFM file: {0}'.format(time.time() - start))

            # transfer waveform to AWG and load into workspace
            start = time.time()
            self._send_file(filename=wfm_name + '.wfm')
            self.log.debug('Send WFM file: {0}'.format(time.time() - start))

            start = time.time()
            self.write('MMEM:IMP "{0}","{1}",WFM'.format(wfm_name, wfm_name + '.wfm'))
            # Wait for everything to complete
            while int(self.query('*OPC?')) != 1:
                time.sleep(0.2)
            # Just to make sure
            while wfm_name not in self.get_waveform_names():
                time.sleep(0.2)
            self.log.debug('Load WFM file into workspace: {0}'.format(time.time() - start))

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
        self.write('SEQ:LENG 0')
        self.write('SEQ:LENG {0:d}'.format(num_steps))

        # Fill in sequence information
        for step, (wfm_tuple, seq_params) in enumerate(sequence_parameter_list, 1):
            # Set waveforms to play
            if num_tracks == len(wfm_tuple):
                for track, waveform in enumerate(wfm_tuple, 1):
                    self.sequence_set_waveform(waveform, step, track)
            else:
                self.log.error('Unable to write sequence.\n'
                               'Length of waveform tuple "{0}" does not '
                               'match the number of sequence tracks.'.format(wfm_tuple))
                return -1

            # Set event jump trigger
            self.sequence_set_event_jump(step, seq_params['event_jump_to'])
            # Set wait trigger
            self.sequence_set_wait_trigger(step, seq_params['wait_for'])
            # Set repetitions
            self.sequence_set_repetitions(step, seq_params['repetitions'])
            # Set go_to parameter
            self.sequence_set_goto(step, seq_params['go_to'])
            # Set flag states

        # Wait for everything to complete
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)

        self._written_sequences = [name]
        return num_steps

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        wfm_list_len = int(self.query('WLIS:SIZE?'))
        wfm_list = list()
        for index in range(wfm_list_len):
            wfm_list.append(self.query('WLIS:NAME? {0:d}'.format(index)))
        return natural_sort(wfm_list)

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """

        return self._written_sequences

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
        return natural_sort(deleted_waveforms)

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory.

        @param str sequence_name: The name of the sequence to be deleted
                                  Optionally a list of sequence names can be passed.

        @return list: a list of deleted sequence names.
        """
        self.write('SEQUENCE:LENGTH 0')
        return list()

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Will always return False for pulse generator hardware without interleave.
        """
        if self._has_interleave():
            return bool(int(self.query('AWGC:INT:STAT?')))
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
        if not isinstance(state, bool):
            return self.get_interleave()

        # if the interleave state should not be changed from the current state, do nothing.
        if state is self.get_interleave():
            return state

        if self._has_interleave():
            self.write('AWGC:INT:STAT {0:d}'.format(int(state)))
            while int(self.query('*OPC?')) != 1:
                time.sleep(0.1)
        return self.get_interleave()

    def write(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        bytes_written, enum_status_code = self.awg.write(command)
        return int(enum_status_code)

    def query(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        answer = self.awg.query(question)
        answer = answer.strip()
        answer = answer.rstrip('\n')
        answer = answer.rstrip()
        answer = answer.strip('"')
        return answer

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.write('*RST')
        self.write('*WAI')
        return 0

    def set_lowpass_filter(self, a_ch, cutoff_freq):
        """ Set a lowpass filter to the analog channels of the AWG.

        @param int a_ch: To which channel to apply, either 1 or 2.
        @param cutoff_freq: Cutoff Frequency of the lowpass filter in Hz.
        """
        if a_ch not in (1, 2):
            return
        self.write('OUTPUT{0:d}:FILTER:LPASS:FREQUENCY {1:f}MHz'.format(a_ch, cutoff_freq / 1e6))

    def set_jump_timing(self, synchronous=False):
        """Sets control of the jump timing in the AWG.

        @param bool synchronous: if True the jump timing will be set to synchornous, otherwise the
                                 jump timing will be set to asynchronous.

        If the Jump timing is set to asynchornous the jump occurs as quickly as possible after an
        event occurs (e.g. event jump tigger), if set to synchornous the jump is made after the
        current waveform is output. The default value is asynchornous.
        """
        timing = 'SYNC' if synchronous else 'ASYNC'
        self.write('EVEN:JTIM {0}'.format(timing))

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
                   'S': 'SEQ'}
        self.write('AWGC:RMOD {0!s}'.format(look_up[mode.upper()]))

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
        if self._has_sequence_mode():
            message = self.query('AWGC:SEQ:TYPE?')
            if 'HARD' in message:
                return 0 if output_as_int else 'Hardware-Sequencer'
            elif 'SOFT' in message:
                return 1 if output_as_int else 'Software-Sequencer'
        return -1 if output_as_int else 'Request-Error'

    def _delete_file(self, filename):
        """

        @param str filename: The full filename to delete from FTP cwd
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

    def _get_all_channels(self):
        """
        Helper method to return a sorted list of all technically available channel descriptors
        (e.g. ['a_ch1', 'a_ch2', 'd_ch1', 'd_ch2'])

        @return list: Sorted list of channels
        """
        avail_channels = ['a_ch1', 'd_ch1', 'd_ch2']
        if not self.get_interleave():
            avail_channels.extend(['a_ch2', 'd_ch3', 'd_ch4'])
        return natural_sort(avail_channels)

    def _get_all_analog_channels(self):
        """
        Helper method to return a sorted list of all technically available analog channel
        descriptors (e.g. ['a_ch1', 'a_ch2'])

        @return list: Sorted list of analog channels
        """
        return natural_sort(chnl for chnl in self._get_all_channels() if chnl.startswith('a'))

    def _get_all_digital_channels(self):
        """
        Helper method to return a sorted list of all technically available digital channel
        descriptors (e.g. ['d_ch1', 'd_ch2'])

        @return list: Sorted list of digital channels
        """
        return natural_sort(chnl for chnl in self._get_all_channels() if chnl.startswith('d'))

    def _is_output_on(self):
        """
        Aks the AWG if the output is enabled, i.e. if the AWG is running

        @return bool: True: output on, False: output off
        """
        return bool(int(self.query('AWGC:RST?')))

    def _zeroing_enabled(self):
        """
        Checks if the zeroing option is enabled. Only available on devices with option '06'.

        @return bool: True: enabled, False: disabled
        """
        if self._has_interleave():
            return bool(int(self.query('AWGC:INT:ZER?')))
        return False

    def _has_interleave(self):
        """ Check if the device has the interleave option installed

            @return bool: device has interleave option
        """
        return '06' in self.installed_options

    def _write_wfm(self, filename, analog_samples, marker_bytes, is_first_chunk, is_last_chunk,
                   total_number_of_samples):
        """
        Appends a sampled chunk of a whole waveform to a wfm-file. Create the file
        if it is the first chunk.
        If both flags (is_first_chunk, is_last_chunk) are set to TRUE it means
        that the whole ensemble is written as a whole in one big chunk.

        @param filename: string, represents the name of the sampled waveform
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
        """
        # The memory overhead of the tmp file write/read process in bytes.
        tmp_bytes_overhead = 104857600  # 100 MB
        tmp_samples = tmp_bytes_overhead // 5
        if tmp_samples > len(analog_samples):
            tmp_samples = len(analog_samples)

        if not filename.endswith('.wfm'):
            filename += '.wfm'
        wfm_path = os.path.join(self._tmp_work_dir, filename)

        # if it is the first chunk, create the WFM file with header.
        if is_first_chunk:
            with open(wfm_path, 'wb') as wfm_file:
                # write the first line, which is the header file, if first chunk is passed:
                num_bytes = str(int(total_number_of_samples * 5))
                num_digits = str(len(num_bytes))
                header = 'MAGIC 1000\r\n#{0}{1}'.format(num_digits, num_bytes)
                wfm_file.write(header.encode())

        # For the WFM file format unfortunately we need to write the digital sampels together
        # with the analog samples. Therefore we need a temporary copy of all samples for each
        # analog channel.
        write_array = np.zeros(tmp_samples, dtype='float32, uint8')

        # Consecutively prepare and write chunks of maximal size tmp_bytes_overhead to file
        samples_written = 0
        with open(wfm_path, 'ab') as wfm_file:
            while samples_written < len(analog_samples):
                write_end = samples_written + write_array.size
                # Prepare tmp write array
                write_array['f0'] = analog_samples[samples_written:write_end]
                if marker_bytes is not None:
                    write_array['f1'] = marker_bytes[samples_written:write_end]
                # Write to file
                wfm_file.write(write_array)
                # Increment write counter
                samples_written = write_end
                # Reduce write array size if
                if 0 < total_number_of_samples - samples_written < write_array.size:
                    write_array.resize(total_number_of_samples - samples_written)

        del write_array

        # append footer if it's the last chunk to write
        if is_last_chunk:
            # the footer encodes the sample rate, which was used for that file:
            footer = 'CLOCK {0:16.10E}\r\n'.format(self.get_sample_rate())
            with open(wfm_path, 'ab') as wfm_file:
                wfm_file.write(footer.encode())
        return

    def sequence_set_waveform(self, waveform_name, step, track):
        """
        Set the waveform 'waveform_name' to position 'step' in the sequence 'sequence_name'.

        @param str waveform_name: Name of the waveform which should be added
        @param int step: Position of the added waveform
        @param int track: track which should be editted

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        self.write('SEQ:ELEM{0:d}:WAV{1} "{2}"'.format(step, track, waveform_name))
        return 0

    def sequence_set_repetitions(self, step, repeat=1):
        """
        Set the repetition counter of sequence "sequence_name" at step "step" to "repeat".
        A repeat value of -1 denotes infinite repetitions; 0 means the step is played once.

        @param int step: Sequence step to be edited
        @param int repeat: number of repetitions. (-1: infinite, 0: once, 1: twice, ...)

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1
        if repeat < 0:
            self.write('SEQ:ELEM{0:d}:LOOP:INFINITE ON'.format(step))
        else:
            self.write('SEQ:ELEM{0:d}:LOOP:INFINITE OFF'.format(step))
            self.write('SEQ:ELEM{0:d}:LOOP:COUNT {1:d}'.format(step, repeat + 1))
        return 0

    def sequence_set_goto(self, step, goto=-1):
        """

        @param int step:
        @param int goto:

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        if goto > 0:
            goto = str(int(goto))
            self.write('SEQ:ELEM{0:d}:GOTO:STATE ON'.format(step))
            self.write('SEQ:ELEM{0:d}:GOTO:INDEX {1}'.format(step, goto))
        else:
            self.write('SEQ:ELEM{0:d}:GOTO:STATE OFF'.format(step))
        return 0

    def sequence_set_event_jump(self, step, jumpto=0):
        """
        Set the event trigger input of the specified sequence step and the jump_to destination.

        @param int step: Sequence step to be edited
        @param str trigger: Trigger string specifier. ('OFF', 'A', 'B' or 'INT')
        @param int jumpto: The sequence step to jump to. 0 or -1 is interpreted as next step

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        # Set event_jump_to if event trigger is enabled
        if jumpto > 0:
            self.write('SEQ:ELEM{0:d}:JTAR:TYPE INDEX'.format(step))
            self.write('SEQ:ELEM{0:d}:JTAR:INDEX {1}'.format(step, jumpto))
        return 0

    def sequence_set_wait_trigger(self, step, trigger='OFF'):
        """
        Make a certain sequence step wait for a trigger to start playing.

        @param int step: Sequence step to be edited
        @param str trigger: Trigger string specifier. ('OFF', 'A', 'B' or 'INT')

        @return int: error code
        """
        if not self._has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. '
                           'Sequencer option not installed.')
            return -1

        trigger = self._event_triggers.get(trigger)
        if trigger is None:
            self.log.error('Invalid trigger specifier "{0}".\n'
                           'Please choose one of: "OFF", "ON"')
            return -1

        if trigger != 'OFF':
            self.write('SEQ:ELEM{0:d}:TWAIT ON'.format(step))
        else:
            self.write('SEQ:ELEM{0:d}:TWAIT OFF'.format(step))

        return 0

    def make_sequence_continuous(self):
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

        last_step = int(self.query('SEQ:LENG?'))
        err = self.sequence_set_goto(last_step, 1)
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

    def get_errors(self):
        """
        Get all errors from the device and log them.

        @return bool: whether any error was found
        """
        next_err = True
        has_error = False
        while next_err:
            err = self.query('SYST:ERR?').split(',')
            if int(err[0]) == 0:
                next_err = False
            else:
                self.log.error('{0} error: {1} {2}'.format(self.model, err[0], err[1]))
                has_error = True

        return has_error

    def _has_sequence_mode(self):
        if self.model == 'AWG7052':
            # the Tek AWG model 7052 does support sequencing even without the option '08'
            # from measurement results it looks kind of "fast" too
            # can be used for T1 and correlation spectroscopy
            return True
        else:
            return '08' in self.installed_options
