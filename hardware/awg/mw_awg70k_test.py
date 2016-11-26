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
import numpy as np
import visa
from ftplib import FTP
from collections import OrderedDict
from fnmatch import fnmatch

from core.base import Base
from interface.microwave_interface import MicrowaveInterface, MicrowaveLimits
from interface.pulser_interface import PulserInterface

class AWG70K(Base, MicrowaveInterface, PulserInterface):
    """

    """
    _modclass = 'awg70k'
    _modtype = 'hardware'

    # declare connectors
    _out = {'pulser': 'PulserInterface',
            'mwsourceawg70k': 'MicrowaveInterface'}

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
        config = self.getConfiguration()

        if 'awg_visa_address' in config.keys():
            self.visa_address = config['awg_visa_address']
        else:
            self.log.error('This is AWG: Did not find >>awg_visa_address<< in configuration.')

        if 'awg_ip_address' in config.keys():
            self.ip_address = config['awg_ip_address']
        else:
            self.log.error('This is AWG: Did not find >>awg_visa_address<< in configuration.')

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']
            if not os.path.exists(self.pulsed_file_dir):
                homedir = self.get_home_dir()
                self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
                self.log.warning('The directory defined in parameter "pulsed_file_dir" in the '
                                 'config for SequenceGeneratorLogic class does not exist!\n'
                                 'The default home directory\n{0}\n will be taken instead.'
                                 ''.format(self.pulsed_file_dir))
        else:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
            self.log.warning('No parameter "pulsed_file_dir" was specified in the config for '
                             'SequenceGeneratorLogic as directory for the pulsed files!\nThe '
                             'default home directory\n{0}\nwill be taken instead.'
                             ''.format(self.pulsed_file_dir))

        if 'ftp_root_dir' in config.keys():
            self.ftp_root_directory = config['ftp_root_dir']
        else:
            self.ftp_root_directory = 'C:\\inetpub\\ftproot'
            self.log.warning('No parameter "ftp_root_dir" was specified in the config for '
                             'tektronix_awg70k as directory for the FTP server root on the AWG!\n'
                             'The default root directory\n{0}\nwill be taken instead.'
                             ''.format(self.ftp_root_directory))

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')
        self.asset_directory = 'waves'

        self.user = 'anonymous'
        self.passwd = 'anonymous@'
        if 'ftp_login' in config.keys() and 'ftp_passwd' in config.keys():
            self.user = config['ftp_login']
            self.passwd = config['ftp_passwd']

        # connect ethernet socket and FTP
        self._rm = visa.ResourceManager()
        if self.visa_address not in self._rm.list_resources():
            self.log.error('VISA address "{0}" not found by the pyVISA resource manager.\nCheck '
                           'the connection by using for example "Agilent Connection Expert".'
                           ''.format(self.visa_address))
        else:
            self.awg = self._rm.open_resource(self.visa_address)
            # Set data transfer format (datatype, is_big_endian, container)
            self.awg.values_format.use_binary('f', False, np.array)
            # set timeout by default to 15 sec
            self.awg.timeout = 15000
        self.ftp = FTP(self.ip_address)
        self.ftp.login(user=self.user, passwd=self.passwd)
        self.ftp.cwd(self.asset_directory)

        self.connected = True

        self.awg_model = self._get_model_ID()[1]
        self.log.debug('Found the following model: {0}'.format(self.awg_model))

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

        self.mw_power = -20.0
        self.mw_frequency = 0.0
        self.mw_list_mode = False
        return

    def on_deactivate(self, e):
        """ Required tasks to be performed during deactivation of the module.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in method activation.
        """

        # Closes the connection to the AWG via ftp and the socket
        try:
            self.awg.close()
        except:
            self.log.warning('Unable to close connection to AWG using pyVISA.')
        self.connected = False
        return

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

    def on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        self.awg.write('AWGC:RUN')
        # wait until the AWG is actually running
        while int(self.awg.query('AWGC:RST?')) == 0:
            time.sleep(0.25)
        self.current_status = 1
        self.is_output_enabled = True
        return self.current_status

    def off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        self.awg.write('AWGC:STOP\n')
        # wait until the AWG has actually stopped
        while int(self.awg.query('AWGC:RST?')) != 0:
            time.sleep(0.25)
        self.current_status = 0
        self.is_output_enabled = False
        # Restore channel activation after using as microwave
        self.set_active_channels(self.active_channel)
        return self.current_status

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        return self.mw_power

    def set_power(self, power=0.):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        amp = 10**((power - 10) / 20)
        if (amp * 2) > 0.5:
            self.log.error('Can not set MW power to {0:.2f}dBm. This exceeds the maximum amplitude '
                           'of the AWG70k.'.format(power))
            return -1
        self.mw_power = power
        self.mw_amplitude = amp
        return 0

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        return self.mw_frequency

    def set_frequency(self, freq=0.):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        constr = self.get_constraints()['sample_rate']
        if freq > constr['max'] / 2:
            self.log.error('Frequency to set {0:.2e}Hz is larger than half the maximum sample rate '
                           '({1:.2e}Hz)'.format(freq, constr['max']))
            return -1
        self.mw_frequency = freq
        return 0

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """
        if freq is not None:
            if self.set_frequency(freq) < 0:
                return -1
        if power is not None:
            if self.set_power(power) < 0:
                return -1
        self.mw_list_mode = False
        # Set function generator mode in AWG
        self.awg.write('INST:MODE FGEN')
        self.awg.write('*WAI')
        # Set sine wave parameters in function generator mode
        self.awg.write('FGEN:CHAN1:TYPE SINE')  # shape
        self.awg.write('FGEN:CHAN1:OFFS 0.0')  # offset voltage
        self.awg.write('FGEN:CHAN1:AMPL {0:.3e}'.format(self.mw_amplitude))  # amplitude
        self.awg.write('FGEN:CHAN1:FREQ {0:.3e}'.format(self.mw_frequency))  # frequency
        self.awg.write('FGEN:CHAN1:PHAS 0.0')  # phase
        self.awg.write('*WAI')
        return 0

    def set_list(self, freq=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """
        constr = self.get_constraints()['sample_rate']
        if freq is not None and type(freq) is list:
            for frequency in freq:
                if frequency > (constr['max'] / 2):
                    self.log.error('Frequency to set {0:.2e}Hz is larger than half the maximum '
                                   'sample rate ({1:.2e}Hz)'.format(frequency, constr['max']))
                    return -1
        if power is not None:
            if self.set_power(power) < 0:
                return -1

        # Set arbitrary waveform generator mode in AWG
        self.mw_list_mode = True
        self.awg.write('INST:MODE AWG')
        self.awg.write('*WAI')
        self.set_sample_rate(constr['max'])
        # Create number of samples array for each frequency. One period for each frequency.
        min_samples = int(self.awg.query('WLIS:WAV:LMIN?'))
        samples_arr = 100 * self.sample_rate / np.array(freq)  # 100 periods
        if samples_arr.min() < min_samples:
            for index, samples in enumerate(samples_arr):
                if samples < min_samples:
                    while samples < min_samples:
                        samples *= 2
                    samples_arr[index] = samples
        samples_arr = np.rint(samples_arr).astype(int)

        # Create sequence emulating the list mode of a MW source
        self.awg.write('SLIS:SEQ:DEL "freq_list"')
        self.awg.write('*WAI')
        self.awg.write('SLIS:SEQ:NEW "freq_list", {0}, 1'.format(len(freq)))
        self.awg.write('*WAI')
        self.awg.write('SLIS:SEQ:EVEN:JTIM "freq_list", IMM'.format(len(freq)))
        # Create waveforms for desired frequencies and assign them to steps in the created sequence
        for index, samples in enumerate(samples_arr):
            waveform_name = 'freq{0}'.format(index)
            time_arr = np.arange(samples) / self.sample_rate
            data = np.sin(time_arr * 2*np.pi * freq[index])
            self.awg.write('WLIS:WAV:NEW "{0}", {1}'.format(waveform_name, samples))
            #self.awg.write('*WAI')
            self.awg.write_values('WLIS:WAV:DATA "{0}",'.format(waveform_name), data)
            #self.awg.write('*WAI')
            # include waveform in sequence
            self.awg.write('SLIS:SEQ:STEP{0}:TASS1:WAV "freq_list", "{1}"'.format(index + 1,
                                                                                  waveform_name))
            self.awg.write('SLIS:SEQ:STEP{0}:EJIN "freq_list", ATR'.format(index + 1))
            self.awg.write('SLIS:SEQ:STEP{0}:EJUM "freq_list", NEXT'.format(index + 1))
            self.awg.write('SLIS:SEQ:STEP{0}:RCO "freq_list", INF'.format(index + 1))
        while int(self.awg.query('*OPC?')) != 1:
            time.sleep(0.25)
        return

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        self.awg.write('SOUR1:CASS:SEQ "freq_list", 1')
        self.awg.write('*WAI')
        self.awg.write('OUTP1:STAT ON')
        if self.awg_model == 'AWG70002A':
            self.awg.write('OUTP2:STAT OFF')
        self.on()
        return 0

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        self.awg.write('SOUR1:CASS:SEQ "freq_list", 1')
        self.awg.write('*WAI')
        self.awg.write('OUTP1:STAT ON')
        if self.awg_model == 'AWG70002A':
            self.awg.write('OUTP2:STAT OFF')
        self.on()
        return 0

    def set_sweep(self, start, stop, step, power):
        """ Sweep from frequency start to frequency sto pin steps of width stop with power.
        """
        freq = np.arange(start, stop, step)
        constr = self.get_constraints()['sample_rate']
        if stop > (constr['max'] / 2) or start > (constr['max'] / 2):
            self.log.error('Frequency to set takes values larger than half the maximum '
                           'sample rate ({0:.2e}Hz)'.format(constr['max']))
            return -1
        if self.set_power(power) < 0:
            return -1

        # Set arbitrary waveform generator mode in AWG
        self.mw_list_mode = True
        self.awg.write('INST:MODE AWG')
        self.awg.write('*WAI')
        self.set_sample_rate(constr['max'])
        # Create number of samples array for each frequency. One period for each frequency.
        min_samples = int(self.awg.query('WLIS:WAV:LMIN?'))
        samples_arr = 100 * self.sample_rate / freq  # 100 periods
        if samples_arr.min() < min_samples:
            for index, samples in enumerate(samples_arr):
                if samples < min_samples:
                    while samples < min_samples:
                        samples *= 2
                    samples_arr[index] = samples
        samples_arr = np.rint(samples_arr).astype(int)

        # Create sequence emulating the list mode of a MW source
        self.awg.write('SLIS:SEQ:DEL "freq_list"')
        self.awg.write('SLIS:SEQ:NEW "freq_list", {0}, 1'.format(len(freq)))
        self.awg.write('SLIS:SEQ:EVEN:JTIM "freq_list", IMM'.format(len(freq)))
        # Create waveforms for desired frequencies and assign them to steps in the created sequence
        waveform_list = []
        for index, samples in enumerate(samples_arr):
            waveform_name = 'freq{0}'.format(index)
            waveform_list.append(waveform_name)
            time_arr = np.arange(samples) / self.sample_rate
            data = self.mw_amplitude * np.sin(time_arr * 2 * np.pi * freq[index])
            self.awg.write('WLIS:WAV:NEW "{0}", {1}'.format(waveform_name, samples))
            self.awg.write_values('WLIS:WAV:DATA "{0}",'.format(waveform_name), data)
        for index, wfm in enumerate(waveform_list):
            # include waveform in sequence
            self.awg.write('SLIS:SEQ:STEP{0}:EJIN "freq_list", ATR'.format(index + 1))
            self.awg.write('SLIS:SEQ:STEP{0}:EJUM "freq_list", NEXT'.format(index + 1))
            self.awg.write('SLIS:SEQ:STEP{0}:RCO "freq_list", INF'.format(index + 1))
            self.awg.write('SLIS:SEQ:STEP{0}:TASS1:WAV "freq_list", "{1}"'.format(index + 1, wfm))
        return

    def reset_sweep(self):
        """ Reset of MW sweep position to start

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def sweep_pos(self, frequency=None):
        """
        """
        pass

    def set_ex_trigger(self, source, pol='POS'):
        """ Set the external trigger for this device with proper polarization.

        @param str source: channel name, where external trigger is expected.
        @param str pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        if source not in ['ATR', 'BTR']:
            self.log.warning('Trigger source with name "{0}" not available in AWG70k.\n'
                             'Choose one of the following: ATR, BTR.'.format(source))
        self.awg.write('TRIG:SEQ:SLOP {0}, ATR'.format(pol))
        self.awg.write('*WAI')
        return

    def get_limits(self):
        """ Return the device-specific limits in a nested dictionary.

          @return MicrowaveLimits: Microwave limits object
        """
        constr = self.get_constraints()
        limits = MicrowaveLimits()
        limits.supported_modes = ('CW', 'LIST', 'SWEEP')

        limits.min_frequency = 10e6
        limits.max_frequency = constr['sample_rate']['max'] / 2

        limits.min_power = 10 + 20 * np.log10(0.001)
        limits.max_power = 10 + 20 * np.log10(0.25)

        limits.list_minstep = 0.001
        limits.list_maxstep = constr['sample_rate']['max'] / 2
        limits.list_maxentries = int(self.awg.query('SLIS:SEQ:STEP:MAX?'))

        limits.sweep_minstep = 0.001
        limits.sweep_maxstep = constr['sample_rate']['max'] / 2
        limits.sweep_maxentries = int(self.awg.query('SLIS:SEQ:STEP:MAX?'))
        return limits

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        self._activate_awg_mode()
        
        self.awg.write('AWGC:RUN')
        # wait until the AWG is actually running
        while int(self.awg.query('AWGC:RST?')) == 0:
            time.sleep(0.25)
        self.current_status = 1
        self.is_output_enabled = True
        return 0

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        self.awg.write('AWGC:STOP')
        # wait until the AWG has actually stopped
        while int(self.awg.query('AWGC:RST?')) != 0:
            time.sleep(0.25)
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
            self.log.warning('No asset name provided for upload!\nCorrect that!\n'
                             'Command will be ignored.')
            return -1
        self._activate_awg_mode()
        # at first delete all the name, which might lead to confusions in the upload procedure:
        self.delete_asset(asset_name)
        # determine which files to transfer
        filelist = self._get_filenames_on_host()
        upload_names = []
        for filename in filelist:
            if filename == asset_name + '.seq':
                upload_names.append(filename)
                break
            elif filename == asset_name + '.seqx':
                upload_names.append(filename)
                break
            elif fnmatch(filename, asset_name + '_ch?.wfm*'):
                upload_names.append(filename)
            elif fnmatch(filename, asset_name + '.wfm*'):
                upload_names.append(filename)
                break
            elif filename == asset_name + '.mat':
                upload_names.append(filename)
                break
        # Transfer files and load into AWG workspace
        for filename in upload_names:
            self._send_file(filename)
            file_path = os.path.join(self.ftp_root_directory, self.asset_directory, filename)
            if filename.endswith('.mat'):
                self.awg.write('MMEM:OPEN:SASS:WAV "{0}"'.format(file_path))
            else:
                self.awg.write('MMEM:OPEN "{0}"'.format(file_path))
            self.awg.query('*OPC?')
        # Wait for the loading to completed
        while int(self.awg.query('*OPC?')) != 1:
            time.sleep(0.2)
        return 0

    def load_asset(self, asset_name, load_dict=None):
        """ Loads a sequence or waveform from the workspace to the specified channel of the pulsing
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
        self._activate_awg_mode()

        # Get all sequence and waveform names currently loaded into AWG workspace
        seq_list = self._get_sequence_names_memory()
        wfm_list = self._get_waveform_names_memory()

        # Check if load_dict is None or an empty dict
        if not load_dict:
            # check if the desired asset is in workspace. Load to channels if that is the case.
            if asset_name in seq_list:
                trac_num = int(self.awg.query('SLIS:SEQ:TRAC? "{0}"'.format(asset_name)))
                for chnl in range(1, trac_num + 1):
                    self.awg.write('SOUR{0}:CASS:SEQ "{1}", {2}'.format(chnl, asset_name, chnl))
            # check if the desired asset is in workspace. Load to channels if that is the case.
            elif asset_name + '_ch1' in wfm_list:
                self.awg.write('SOUR1:CASS:WFM "{0}"'.format(asset_name + '_ch1'))
                if self._get_max_a_channel_number() > 1 and asset_name + '_ch2' in wfm_list:
                    self.awg.write('SOUR2:CASS:WFM "{0}"'.format(asset_name + '_ch2'))
            self.current_loaded_asset = asset_name
        else:
            self.log.error('Loading assets into user defined channels is not yet implemented.\n'
                           'In other words: The "load_dict" parameter of the "load_asset" method '
                           'is not handled yet.')

        # Wait for the loading to completed
        while int(self.awg.query('*OPC?')) != 1:
            time.sleep(0.2)
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
        self._activate_awg_mode()

        self.awg.write('WLIS:WAV:DEL ALL')
        self.awg.write('SLIS:SEQ:DEL ALL')
        while int(self.awg.query('*OPC?')) != 1:
            time.sleep(0.25)
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
        self._activate_awg_mode()

        self.awg.write('CLOCK:SRATE %.4G' % sample_rate)
        while int(self.awg.query('*OPC?')) != 1:
            time.sleep(0.25)
        return_rate = float(self.awg.query('CLOCK:SRATE?'))
        self.sample_rate = return_rate
        return return_rate

    def get_sample_rate(self):
        """ Set the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """
        self._activate_awg_mode()

        return_rate = float(self.awg.query('CLOCK:SRATE?'))
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
        amp = {}
        off = {}

        self._activate_awg_mode()

        chnl_list = ['a_ch' + str(ch_num) for ch_num in range(1, self._get_max_a_channel_number() + 1)]

        pattern = re.compile('[0-9]+')
        # get pp amplitudes
        if amplitude is None:
            for ch_num, chnl in enumerate(chnl_list):
                amp[chnl] = float(self.awg.query('SOUR' + str(ch_num + 1) + ':VOLT:AMPL?'))
        else:
            for chnl in amplitude:
                if chnl in chnl_list:
                    ch_num = int(re.search(pattern, chnl).group(0))
                    amp[chnl] = float(self.awg.query('SOUR' + str(ch_num) + ':VOLT:AMPL?'))
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

        self._activate_awg_mode()

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
                self.awg.write('SOUR{0}:VOLT:AMPL {1}'.format(a_ch, amplitude[a_ch]))
                self.amplitude_list[a_ch] = amplitude[a_ch]
            while int(self.awg.query('*OPC?')) != 1:
                time.sleep(0.25)

        if offset is not None:
            for a_ch in offset:
                self.awg.write('SOUR{0}:VOLT:OFFSET {1}'.format(a_ch, offset[a_ch]))
                self.offset_list[a_ch] = offset[a_ch]
            while int(self.awg.query('*OPC?')) != 1:
                time.sleep(0.25)

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

        self._activate_awg_mode()

        digital_channels = list(range(1, 2 * self._get_max_a_channel_number() + 1))
        analog_channels = [chnl // 2 + chnl % 2 for chnl in digital_channels]
        marker_indices = [((chnl - 1) % 2) + 1 for chnl in digital_channels]

        # get low marker levels
        if low is None:
            for chnl in digital_channels:
                low_val[chnl] = float(self.awg.query('SOUR' + str(analog_channels[chnl-1]) + ':MARK'
                                                     + str(marker_indices[chnl-1]) + ':VOLT:LOW?'))
        else:
            for chnl in low:
                low_val[chnl] = float(self.awg.query('SOUR' + str(analog_channels[chnl-1]) + ':MARK'
                                                     + str(marker_indices[chnl-1]) + ':VOLT:LOW?'))

        # get high marker levels
        if high is None:
            for chnl in digital_channels:
                high_val[chnl] = float(self.awg.query('SOUR' + str(analog_channels[chnl-1])
                                                      + ':MARK' + str(marker_indices[chnl-1])
                                                      + ':VOLT:HIGH?'))
        else:
            for chnl in high:
                high_val[chnl] = float(self.awg.query('SOUR' + str(analog_channels[chnl-1])
                                                      + ':MARK' + str(marker_indices[chnl-1])
                                                      + ':VOLT:HIGH?'))
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

        self._activate_awg_mode()

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

        self._activate_awg_mode()

        active_ch = {}
        for a_ch in range(max_analog_channels):
            active_ch['a_ch' + str(a_ch + 1)] = False
            active_ch['d_ch' + str((2 * a_ch) + 1)] = False
            active_ch['d_ch' + str((2 * a_ch) + 2)] = False

        # check what analog channels are active
        for a_ch in range(1, max_analog_channels + 1):
            if bool(int(self.awg.query('OUTPUT' + str(a_ch) + ':STATE?'))):
                active_ch['a_ch' + str(a_ch)] = True

        # check how many markers are active on each channel, i.e. the DAC resolution
        max_res = constraints['dac_resolution']['max']
        for a_ch in range(max_analog_channels):
            if active_ch['a_ch' + str(a_ch + 1)]:
                digital_mrk = max_res - int(self.awg.query('SOUR' + str(a_ch + 1) + ':DAC:RES?'))
                if digital_mrk > 0:
                    active_ch['d_ch' + str((2 * a_ch) + 1)] = True
                    if digital_mrk == 2:
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

        self._activate_awg_mode()

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
            self.awg.write('SOUR' + str(ach_num) + ':DAC:RES ' + str(dac_res))
            # (de)activate the analog channel
            if new_channels_state[a_ch]:
                self.awg.write('OUTPUT' + str(ach_num) + ':STATE ON')
            else:
                self.awg.write('OUTPUT' + str(ach_num) + ':STATE OFF')

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
            asset_name = None
            if fnmatch(filename, '*_ch?.wfmx'):
                asset_name = filename.rsplit('_', 1)[0]
            elif fnmatch(filename, '*_ch?.wfm'):
                asset_name = filename.rsplit('_', 1)[0]
            elif filename.endswith('.seqx'):
                asset_name = filename[:-5]
            elif filename.endswith('.seq'):
                asset_name = filename[:-4]
            elif filename.endswith('.mat'):
                asset_name = filename[:-4]
            if asset_name is not None and asset_name not in name_list:
                name_list.append(asset_name)
        return name_list

    def get_saved_asset_names(self):
        """ Retrieve the names of all sampled and saved assets on the host PC. This is no list of
        the file names.

        @return list: List of all saved asset name strings in the current directory of the host PC.
        """
        # list of all files in the waveform directory ending with .mat or .WFMX
        file_list = self._get_filenames_on_host()
        # exclude the channel specifier for multiple analog channels and create return list
        name_list = []
        for filename in file_list:
            asset_name = None
            if fnmatch(filename, '*_ch?.wfmx'):
                asset_name = filename.rsplit('_', 1)[0]
            elif fnmatch(filename, '*_ch?.wfm'):
                asset_name = filename.rsplit('_', 1)[0]
            elif filename.endswith('.seqx'):
                asset_name = filename[:-5]
            elif filename.endswith('.seq'):
                asset_name = filename[:-4]
            elif filename.endswith('.mat'):
                asset_name = filename[:-4]
            if asset_name is not None and asset_name not in name_list:
                name_list.append(asset_name)
        return name_list

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
        self._activate_awg_mode()

        # get all uploaded files and asset names in workspace
        uploaded_files = self._get_filenames_on_device()
        wfm_list = self._get_waveform_names_memory()
        seq_list = self._get_sequence_names_memory()

        # Create list of uploaded files to be deleted
        files_to_delete = []
        for name in asset_name:
            for filename in uploaded_files:
                if fnmatch(filename, name + '_ch?.wfm*') or \
                        fnmatch(filename, name + '.wfm*') or \
                        filename.endswith(('.mat', '.seq', '.seqx')):
                    files_to_delete.append(filename)
        # delete files
        with FTP(self.ip_address) as ftp:
            # login as default user anonymous, passwd anonymous@
            ftp.login(user=self.user, passwd=self.passwd)
            ftp.cwd(self.asset_directory)
            for filename in files_to_delete:
                ftp.delete(filename)

        # clear waveforms from AWG workspace
        for wfm in wfm_list:
            for name in asset_name:
                if fnmatch(wfm, name + '_ch?') or wfm == name:
                    self.awg.write('WLIS:WAV:DEL "{0}"'.format(wfm))

        # clear sequences from AWG workspace
        for name in asset_name:
            if name in seq_list:
                self.awg.write('SLIS:SEQ:DEL "{0}"'.format(name))

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
            # login as default user anonymous, passwd anonymous@
            ftp.login(user=self.user, passwd=self.passwd)
            try:
                ftp.cwd(dir_path)
            except:
                self.log.info('Desired directory {0} not found on AWG device.\nCreate new.'
                              ''.format(dir_path))
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
        options = self.awg.query('*OPT?')[1:-2].split(',')
        has_seq_mode = '03' in options
        return has_seq_mode

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)
        @return int: error code (0:OK, -1:error)

        Unused for pulse generator hardware other than an AWG. The AWG 5000
        Series does not have an interleave mode and this method exists only for
        compability reasons.
        """
        if state:
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

    def reset(self):
        """Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.awg.write('*RST')
        self.awg.write('*WAI')
        return 0

    def ask(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        answer = self.awg.query(question).replace('\n', '')
        return answer

    def tell(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        bytes_written, enum_status_code = self.awg.write(command)
        return int(enum_status_code)

    def _init_loaded_asset(self):
        """
        Gets the name of the currently loaded asset from the AWG and sets the attribute accordingly.
        """
        # Check if AWG is still in MW mode (function generator mode)
        self._activate_awg_mode()

        # first get all the channel assets
        a_ch_asset = [self.awg.query('SOUR{0}:CASS?'.format(count))[1:-2]
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
            # login as default user anonymous, passwd anonymous@
            ftp.login(user=self.user, passwd=self.passwd)
            ftp.cwd(self.asset_directory)
            # get only the files from the dir and skip possible directories
            log = []
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
                if filename.split('.')[-1] in ['wfmx', 'mat', 'wfm', 'seq']:
                    if filename not in filename_list:
                        filename_list.append(filename)
        return filename_list

    def _get_filenames_on_host(self):
        """ Get the full filenames of all assets saved on the host PC.

        @return: list, The full filenames of all assets saved on the host PC.
        """
        filename_list = [f for f in os.listdir(self.host_waveform_directory)
                         if f.split('.')[-1] in ['wfmx', 'mat', 'wfm', 'seq']]
        return filename_list

    def _get_model_ID(self):
        """
        @return: a string which represents the model id of the AWG.
        """
        model_id = self.awg.query('*IDN?').replace('\n', '').split(',')
        return model_id

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
        number_of_wfm = int(self.awg.query('WLIS:SIZE?'))
        waveform_list = [None] * number_of_wfm
        for i in range(number_of_wfm):
            wfm_name = self.awg.query('WLIS:NAME? {0}'.format(i + 1))[1:-2]
            waveform_list[i] = wfm_name
        return waveform_list

    def _get_sequence_names_memory(self):
        """
        Gets all sequence names currently loaded into the AWG workspace
        @return: list of names
        """
        number_of_seq = int(self.awg.query('SLIS:SIZE?'))
        sequence_list = [None] * number_of_seq
        for i in range(number_of_seq):
            seq_name = self.awg.query('SLIS:NAME? {0}'.format(i + 1))[1:-2]
            sequence_list[i] = seq_name
        return sequence_list

    def _is_output_on(self):
        """
        Aks the AWG if the output is enabled, i.e. if the AWG is running

        @return: bool, (True: output on, False: output off)
        """
        run_state = bool(int(self.awg.query('AWGC:RST?')))
        return run_state

    def _activate_awg_mode(self):
        """
        Helper method to activate AWG mode if the device is currently in function generator mode.
        """
        # Check if AWG is still in MW mode (function generator mode)
        if self.awg.query('INST:MODE?').replace('\n', '') != 'AWG':
            self.awg.write('INST:MODE AWG')
            self.awg.write('*WAI')
        return
