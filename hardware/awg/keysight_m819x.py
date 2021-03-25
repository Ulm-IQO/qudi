# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the Keysight M819X AWG series.

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


import visa
import os
import time
import numpy as np
import scipy.interpolate
from fnmatch import fnmatch
from collections import OrderedDict
from abc import abstractmethod
import re

from core.module import Base
from core.configoption import ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints, SequenceOption
from core.util.modules import get_home_dir


class AWGM819X(Base, PulserInterface):
    """
    A hardware module for AWGs of the Keysight M819X series for generating
    waveforms and sequences thereof.
    """

    _visa_address = ConfigOption(name='awg_visa_address', default='TCPIP0::localhost::hislip0::INSTR', missing='warn')
    _awg_timeout = ConfigOption(name='awg_timeout', default=20, missing='warn')
    _pulsed_file_dir = ConfigOption(name='pulsed_file_dir', default=os.path.join(get_home_dir(), 'pulsed_file_dir'),
                                        missing='warn')
    _assets_storage_path = ConfigOption(name='assets_storage_path', default=os.path.join(get_home_dir(), 'saved_pulsed_assets'),
                                       missing='warn')
    _sample_rate_div = ConfigOption(name='sample_rate_div', default=1, missing='warn')
    _dac_amp_mode = None
    _wave_mem_mode = None
    _wave_file_extension = '.bin'
    _wave_transfer_datatype = 'h'

    # explicitly set low/high levels for [[d_ch1_low, d_ch1_high], [d_ch2_low, d_ch2_high], ...]
    _d_ch_level_low_high = ConfigOption(name='d_ch_level_low_high', default=[], missing='nothing')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._BRAND = ''
        self._MODEL = ''
        self._SERIALNUMBER = ''
        self._FIRMWARE_VERSION = ''

        self._sequence_mode = False         # set in on_activate()
        self._debug_check_all_commands = False       # # For development purpose, might slow down

    @property
    @abstractmethod
    def n_ch(self):
        pass

    @property
    @abstractmethod
    def marker_on(self):
        pass

    @property
    @abstractmethod
    def interleaved_wavefile(self):
        pass

    def on_activate(self):
        """Initialisation performed during activation of the module.
        """
        self._rm = visa.ResourceManager()

        self._pulsed_file_dir = self._pulsed_file_dir.replace('/', '\\')    # as expected from awg drier
        self._assets_storage_path = self._assets_storage_path.replace('/', '\\')
        self._create_dir(self._pulsed_file_dir)
        self._create_dir(self._assets_storage_path)

        # connect to awg using PyVISA
        try:
            self.awg = self._rm.open_resource(self._visa_address)
            # set timeout by default to 30 sec
            self.awg.timeout = self._awg_timeout * 1000
        except:
            self.awg = None
            self.log.error('VISA address "{0}" not found by the pyVISA resource manager.\nCheck '
                           'the connection by using for example "Keysight Connection Expert".'
                           ''.format(self._visa_address))
            return

        if self.awg is not None:
            mess = self.query('*IDN?').split(',')
            self._BRAND = mess[0]
            self._MODEL = mess[1]
            self._SERIALNUMBER = mess[2]
            self._FIRMWARE_VERSION = mess[3]

            self.log.info('Load the device model "{0}" from "{1}" with '
                          'serial number "{2}" and firmware version "{3}" '
                          'successfully.'.format(self._MODEL, self._BRAND,
                                                 self._SERIALNUMBER,
                                                 self._FIRMWARE_VERSION))
            self._sequence_mode = 'SEQ' in self.query('*OPT?').split(',')
        self._init_device()

    def on_deactivate(self):
        """ Required tasks to be performed during deactivation of the module. """

        try:
            self.awg.close()
            self.connected = False
        except:
            self.log.warning('Closing AWG connection using pyvisa failed.')
        self.log.info('Closed connection to AWG')

    @abstractmethod
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

        Each scalar parameter is an ScalarConstraints object defined in core.util.interfaces.
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
        pass

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        self._write_output_on()

        # Sec. 6.4 from manual:
        # In the program it is recommended to send the command for starting
        # data generation (:INIT:IMM) as the last command. This way
        # intermediate stop/restarts (e.g. when changing sample rate or
        # loading a waveform) are avoided and optimum execution performance is
        # achieved.

        # wait until the AWG switched the outputs on
        while not self._is_output_on():
            time.sleep(0.25)

        self.write(':INIT:IMM')
        self.write('*WAI')

        # in dynamic mode with external pattern jump, we start by a software trigger
        # subsequent triggers are generated by external control hw
        if self.get_trigger_mode() == "trig" and self.get_dynamic_mode():
            self.send_trigger_event()

        return self.get_status()[0]

    def pulser_off(self):
        """ Switches the pulsing device off.
        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.write(':ABOR')

        # wait until the AWG has actually stopped
        while self._is_awg_running():
            time.sleep(0.25)

        return self.get_status()[0]

    def load_waveform(self, load_dict, to_nextfree_segment=False):
        """ Loads a waveform to the specified channel of the pulsing device.

        @param dict|list load_dict: a dictionary with keys being one of the available channel
                                    index and values being the name of the already written
                                    waveform to load into the channel.
                                    Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                {1: rabi_ch2, 2: rabi_ch1}
                                    If just a list of waveform names is given, the channel
                                    association will be invoked from the channel
                                    suffix '_ch1', '_ch2' etc.

                                        {1: rabi_ch1, 2: rabi_ch2}
                                    or
                                        {1: rabi_ch2, 2: rabi_ch1}

                                    If just a list of waveform names is given,
                                    the channel association will be invoked from
                                    the channel suffix '_ch1', '_ch2' etc. A
                                    possible configuration can be e.g.

                                        ['rabi_ch1', 'rabi_ch2', 'rabi_ch3']

        @return dict: Dictionary containing the actually loaded waveforms per
                      channel.

        For devices that have a workspace (i.e. AWG) this will load the waveform
        from the device workspace into the channel. For a device without mass
        memory, this will make the waveform/pattern that has been previously
        written with self.write_waveform ready to play.

        Please note that the channel index used here is not to be confused with the number suffix
        in the generic channel descriptors (i.e. 'd_ch1', 'a_ch1'). The channel index used here is
        highly hardware specific and corresponds to a collection of digital and analog channels
        being associated to a SINGLE wavfeorm asset.
        """

        self.set_seq_mode('ARB')
        self._delete_all_sequences()  # leave sequence mode

        self.log.debug("Load_waveform call with dict/list {}".format(load_dict))

        load_dict = self._load_list_2_dict(load_dict)

        active_analog = self._get_active_d_or_a_channels(only_analog=True)

        # Check if all channels to load to are active
        channels_to_set = {'a_ch{0:d}'.format(chnl_num) for chnl_num in load_dict}
        if not channels_to_set.issubset(active_analog):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more channels to set are not active.\n'
                           'channels_to_set are: ', channels_to_set, 'and\n'
                           'analog_channels are: ', active_analog)
            return self.get_loaded_assets()

        # Check if all waveforms to load are present on device memory
        if not set(load_dict.values()).issubset(self.get_waveform_names()):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more waveforms to load are missing: {}'.format(
                                                                            set(load_dict.values())
            ))
            return self.get_loaded_assets()

        if load_dict == {}:
            self.log.warning('No file and channel provided for load!\n'
                             'Correct that!\nCommand will be ignored.')
            return self.get_loaded_assets()

        self._load_wave_from_memory(load_dict, to_nextfree_segment=to_nextfree_segment)

        self.set_trigger_mode('cont')
        self.check_dev_error()

        return self.get_loaded_assets()

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param dict|list sequence_name: a dictionary with keys being one of the available channel
                                        index and values being the name of the already written
                                        waveform to load into the channel.
                                        Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                    {1: rabi_ch2, 2: rabi_ch1}
                                        If just a list of waveform names if given, the channel
                                        association will be invoked from the channel
                                        suffix '_ch1', '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """

        if not (set(self.get_loaded_assets()[0].values())).issubset(set([sequence_name])):
            self.log.error('Unable to load sequence into channels.\n'
                           'Make sure to call write_sequence() first.')
            return self.get_loaded_assets()

        self.write_all_ch(':FUNC{}:MODE STS', all_by_one={'m8195a': True})  # activate the sequence mode
        """
        select the first segment in your sequence, before any dynamic sequence selection.
        """
        self.write_all_ch(":STAB{}:SEQ:SEL 0", all_by_one={'m8195a': True})
        self.write_all_ch(":STAB{}:DYN ON", all_by_one={'m8195a': True})

        return 0

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
        active_analog = self._get_active_d_or_a_channels(only_analog=True)
        channel_numbers = self.chstr_2_chnum(active_analog, return_list=True)

        # Get assets per channel
        loaded_assets = dict()
        type_per_ch = []
        is_err = False

        for chnl_num in channel_numbers:

            asset_name = 'ERROR_NAME'

            if self.get_loaded_assets_num(chnl_num, mode='segment') >= 1 \
                and self.get_loaded_assets_num(chnl_num, mode='sequence') == 0:
                # arb mode with at least one waveform

                type_per_ch.append('waveform')
                seg_id_active = int(self.query(':TRAC{}:SEL?'.format(chnl_num)))
                ids_avail = self.get_loaded_assets_id(chnl_num, mode='segment')
                if seg_id_active not in ids_avail:
                    seg_id_active = ids_avail[0]
                    self.log.error("Active segment id {} outside available sequences ({}) for unknown reason."
                                   " Set to segment id to 1.".format(seg_id_active, ids_avail))

                    self.write(':TRAC1:SEL {:d}'.format(seg_id_active))
                    self.write(':TRAC2:SEL {:d}'.format(seg_id_active))

                asset_name = self.get_loaded_asset_name_by_id(chnl_num, seg_id_active, mode='segment')

            elif self.get_loaded_assets_num(chnl_num, mode='segment') >= 1 \
                and self.get_loaded_assets_num(chnl_num, mode='sequence') == 1:
                # seq mode with at least one waveform
                # currently only a single uploaded sequence supported
                type_per_ch.append('sequence')
                asset_name = self.get_loaded_assets_name(chnl_num, mode='sequence')[0]
            elif self.get_loaded_assets_num(chnl_num, mode='segment') == 0 \
                and self.get_loaded_assets_num(chnl_num, mode='sequence') == 0:
                # arb mode but no waveform

                type_per_ch.append('waveform')
                asset_name = ''

            else:
                is_err = True
            """
            if self.get_loaded_assets_num(chnl_num, mode='segment') > 1 \
                and self.get_loaded_assets_num(chnl_num, mode='sequence') == 0:

                self.log.error("Multiple segments, but no sequence defined")
            """
            if self.get_loaded_assets_num(chnl_num, mode='sequence') > 1:
                self.log.error("Multiple sequences defined. Should only be 1.")
                # todo: implement more than 1 sequence

            loaded_assets[chnl_num] = asset_name

        if not all(x == type_per_ch[0] for x in type_per_ch) or not channel_numbers:
            # make sure type is same for all channels
            is_err = True
        if is_err:
            self.log.error('Unable to determine loaded assets.')
            return dict(), ''

        return loaded_assets, type_per_ch[0]   # interface requires same type for all ch

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)
        """

        self.write_all_ch(':TRAC{}:DEL:ALL', all_by_one={'m8195a': True})
        self._flag_segment_table_req_update = True

        return

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): tuple with an integer value of the current status and a corresponding
                             dictionary containing status description for all the possible status
                             variables of the pulse generator hardware.
        """

        status_dic = {-1: 'Failed Request or Communication',
                       0: 'Device has stopped, but can receive commands',
                       1: 'Device is active and running'}

        current_status = -1 if self.awg is None else int(self._is_awg_running())
        # All the other status messages should have higher integer values then 1.

        return current_status, status_dic

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead retrieve the current
        sample rate directly from the device.
        """
        sample_rate = float(self.query(':FREQ:RAST?')) / self._sample_rate_div
        return sample_rate

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """
        sample_rate_GHz = (sample_rate * self._sample_rate_div) / 1e9
        self.write(':FREQ:RAST {0:.4G}GHz\n'.format(sample_rate_GHz))
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)
        time.sleep(0.2)
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

        amp = dict()
        off = dict()

        chnl_list = self._get_all_analog_channels()

        # get pp amplitudes
        if amplitude is None:
            for ch_num, chnl in enumerate(chnl_list, 1):
                amp[chnl] = float(self.query(':VOLT{0:d}?'.format(ch_num)))
        else:
            for chnl in amplitude:
                if chnl in chnl_list:
                    ch_num = self.chstr_2_chnum(chnl)
                    amp[chnl] = float(self.query(':VOLT{0:d}?'.format(ch_num)))
                else:
                    self.log.warning('Get analog amplitude from channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))

        # get voltage offsets
        if offset is None:
            for ch_num, chnl in enumerate(chnl_list):
                ch_num = self.chstr_2_chnum(chnl)
                off[chnl] = float(self.query(':VOLT{0:d}:OFFS?'.format(ch_num)))
        else:
            for chnl in offset:
                if chnl in chnl_list:
                    ch_num = self.chstr_2_chnum(chnl)
                    off[chnl] = float(self.query(':VOLT{0:d}:OFFS?'.format(ch_num)))
                else:
                    self.log.warning('Get analog offset from channel "{0}" failed. '
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
                ch_num = self.chstr_2_chnum(chnl)
                if chnl not in analog_channels:
                    self.log.warning('Channel to set (a_ch{0}) not available in AWG.\nSetting '
                                     'analogue voltage for this channel ignored.'.format(ch_num))
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
                ch_num = self.chstr_2_chnum(chnl)
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
                ch_num = self.chstr_2_chnum(chnl)
                self.write(':VOLT{0} {1:.4f}'.format(ch_num, amp))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.25)

        if offset is not None:
            for chnl, off in offset.items():
                ch_num = self.chstr_2_chnum(chnl)
                self.write(':VOLT{0}:OFFS {1:.4f}'.format(ch_num, off))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.25)
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
            low_val[chnl] = float(
                self.query(self._get_digital_ch_cmd(chnl) + ':LOW?'))
        # get high marker levels
        for chnl in high:
            if chnl not in digital_channels:
                continue
            high_val[chnl] = float(
                self.query(self._get_digital_ch_cmd(chnl) + ':HIGH?'))

        return low_val, high_val

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel.

        @param dict low: dictionary, with key being the channel descriptor string
                         (i.e. 'd_ch1', 'd_ch2') and items being the low values (in volt) for the
                         desired channel.
        @param dict high: dictionary, with key being the channel descriptor string
                          (i.e. 'd_ch1', 'd_ch2') and items being the high values (in volt) for the
                          desired channel.

        @return (dict, dict): tuple of two dicts where first dict denotes the current low value and
                              the second dict the high value for ALL digital channels.
                              Keys are the channel descriptor strings (i.e. 'd_ch1', 'd_ch2')

        If nothing is passed then the command will return the current voltage levels.

        Note: After setting the high and/or low values of the device, use the actual set return
              values for further processing.
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
            if high[key] - low[key] < 0.125:
                self.log.warning('Voltage difference is too small. Reducing low voltage level.')
                low[key] = high[key] - 0.125
            elif high[key] - low[key] > 2.25:
                self.log.warning('Voltage difference is too large. Increasing low voltage level.')
                low[key] = high[key] - 2.25


        # set high marker levels
        for chnl in low and high:
            if chnl not in digital_channels:
                continue

            offs =(high[chnl] + low[chnl])/2
            ampl = high[chnl] - low[chnl]
            self.write(self._get_digital_ch_cmd(chnl) + ':AMPL {}'.format(ampl))
            self.write(self._get_digital_ch_cmd(chnl) + ':OFFS {}'.format(offs))

        return self.get_digital_level()

    @abstractmethod
    def get_active_channels(self, ch=None):
        pass

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
            self.log.error('Trying to (de)activate channels that are not present in M8190A.\n'
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

        self._set_active_ch(new_channels_state)

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
                                    voltage samples normalized to half Vpp (between -1 and 1).
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

        waveforms = []

        # Sanity checks
        if len(analog_samples) == 0:
            self.log.error('No analog samples passed to write_waveform method in M8190A.')
            return -1, waveforms

        min_samples = self.get_constraints().waveform_length.min
        if total_number_of_samples < min_samples:
            self.log.error('Unable to write waveform.\nNumber of samples to write ({0:d}) is '
                           'smaller than the allowed minimum waveform length ({1:d}).'
                           ''.format(total_number_of_samples, min_samples))
            return -1, waveforms

        active_analog = self._get_active_d_or_a_channels(only_analog=True)
        active_channels = set(self.get_active_channels().keys())

        # Sanity check of channel numbers
        if active_channels != set(analog_samples.keys()).union(set(digital_samples.keys())):
            self.log.error('Mismatch of channel activation and sample array dimensions for '
                           'waveform creation.\nChannel activation is: {0}\nSample arrays have: '
                           ''.format(active_channels,
                                     set(analog_samples.keys()).union(set(digital_samples.keys()))))
            return -1, waveforms

        to_segment_id = 1  # pc_hdd mode
        if self._wave_mem_mode == 'awg_segments':
            to_segment_id = -1

        waveforms = self._write_wave_to_memory(name, analog_samples, digital_samples, active_analog,
                                               to_segment_id=to_segment_id)

        self.check_dev_error()

        return total_number_of_samples, waveforms

    def write_sequence(self, name, sequence_parameters):
        """
        Write a new sequence on the device memory.
        In wave_mem_mode == 'pc_hdd' and if elements in the sequence are not available on the AWG yet, they will be
        transferred from the PC.

        @param str name: the name of the waveform to be created/append to
        @param list sequence_parameters: List containing tuples of length 2. Each tuple represents
                                         a sequence step. The first entry of the tuple is a list of
                                         waveform names (str); one for each channel. The second
                                         tuple element is a SequenceStep instance containing the
                                         sequencing parameters for this step.

        @return: int, number of sequence steps written (-1 indicates failed process)
        """

        # Check if device has sequencer option installed
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. Sequencer option not '
                           'installed.')
            return -1

        # Check if all waveforms are present on device memory
        avail_waveforms = set(self.get_waveform_names())
        for waveform_tuple, param_dict in sequence_parameters:
            if not avail_waveforms.issuperset(waveform_tuple):
                self.log.error('Failed to create sequence "{0}" due to waveforms "{1}" not '
                               'present in memory. Try to load them again.'.format(name, waveform_tuple))
                return -1

        num_steps = len(sequence_parameters)

        if self._wave_mem_mode == 'pc_hdd':
            # todo: check whether skips on already loaded waveforms that should be updated
            # check whether this works as intended with <generate_new> mechanism
            # generate new needs to invalidate loaded assets
            loaded_segments_ch1 = self.get_loaded_assets_name(1, mode='segment')
            loaded_segments_ch2 = self.get_loaded_assets_name(2, mode='segment')

            waves_loaded_here = []
            # transfer waveforms in sequence from local pc to segments in awg mem
            for waveform_tuple, param_dict in sequence_parameters:
                # todo: need to handle other than 2 channels?
                waveform_list = []
                waveform_list.append(waveform_tuple[0])
                waveform_list.append(waveform_tuple[1])
                wave_ch1 = self._remove_file_extension(waveform_tuple[0])
                wave_ch2 = self._remove_file_extension(waveform_tuple[1])

                if not (wave_ch1 in loaded_segments_ch1 and
                        wave_ch2 in loaded_segments_ch2) \
                        and not (wave_ch1 in waves_loaded_here and
                        wave_ch2 in waves_loaded_here):

                    self.log.debug("Couldn't find segments {} and {} on device for writing sequence {}. Loading...".format(
                        wave_ch1, wave_ch2, name))
                    self.load_waveform(waveform_list, to_nextfree_segment=True)
                    waves_loaded_here.append(wave_ch1)
                    waves_loaded_here.append(wave_ch2)
                else:
                    self.log.debug("Segments {} and {} already on device for writing sequence {}. Skipping load.".format(
                        wave_ch1, wave_ch2, name))

            self.log.debug("Loading of waveforms for sequence write finished.")
        elif self._wave_mem_mode == 'awg_segments':
            # all segments must be present on device mem already
            pass
        else:
            raise ValueError("Unknown memory mode: {}".format(self._wave_mem_mode))

        """
        8190a manual: When using dynamic sequencing, the arm mode must be set to self-armed 
        and all advancement modes must be set to Auto. 
        Additionally, the trigger mode Gated is not allowed.
        """
        self.write_all_ch(':FUNC{}:MODE STS', all_by_one={'m8195a': True})  # activate the sequence mode
        self.write_all_ch(':STAB{}:RES', all_by_one={'m8195a': True})       # Reset all sequence table entries to default values

        self._delete_all_sequences()
        self._define_new_sequence(name, num_steps)

        # write the actual sequence table
        ctr_steps_written = 0
        goto_in_sequence = False
        for step, (wfm_tuple, seq_step) in enumerate(sequence_parameters, 1):

            index = step - 1

            if seq_step['go_to'] != -1:
                goto_in_sequence = True

            control = self._get_sequence_control_bin(sequence_parameters, index)

            seq_loop_count = 1
            if seq_step.repetitions == -1:
                # this is ugly, limits maximal waiting time. 1 Sa -> approx. 0.3 s
                seg_loop_count = 4294967295  # max value, todo: from constraints
            else:
                seg_loop_count = seq_step.repetitions + 1  # if repetitions = 0 then do it once
            seg_start_offset = 0    # play whole segement from start...
            seg_end_offset = 0xFFFFFFFF     # to end

            self.log.debug("For sequence table step {} with {} reps: control: {}".format(step,
                                                                                         seq_loop_count,
                                                                                         control))

            segment_id_ch1 = self.get_segment_id(self._remove_file_extension(wfm_tuple[0]), 1) \
                if len(wfm_tuple) >= 1 else -1
            segment_id_ch2 = self.get_segment_id(self._remove_file_extension(wfm_tuple[1]), 2) \
                if len(wfm_tuple) == 2 else -1

            try:
                # creates all segments as data entries
                if segment_id_ch1 > -1:
                    # STAB will default to STAB1 on 8190A
                    self.write(':STAB:DATA {0}, {1}, {2}, {3}, {4}, {5}, {6}'
                               .format(index,
                                       control,
                                       seq_loop_count,
                                       seg_loop_count,
                                       segment_id_ch1,
                                       seg_start_offset,
                                       seg_end_offset))
                if segment_id_ch2 > -1:
                    self.write(':STAB2:DATA {0}, {1}, {2}, {3}, {4}, {5}, {6}'
                               .format(index,
                                       control,
                                       seq_loop_count,
                                       seg_loop_count,
                                       segment_id_ch2,
                                       seg_start_offset,
                                       seg_end_offset))

                if segment_id_ch1 + segment_id_ch2 > -1:
                    ctr_steps_written += 1
                    self.log.debug("Writing seqtable entry {}: {}".format(index, step))
                else:
                    self.log.error("Failed while writing seqtable entry {}: {}".format(index, step))

            except Exception as e:
                self.log.error("Unknown error occured while writing to seq table: {}".format(str(e)))

        if goto_in_sequence and self.get_constraints().sequence_order == "LINONLY": # SequenceOrderOption.LINONLY:
            self.log.warning("Found go_to in step of sequence {}. Not supported and ignored.".format(name))

        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)

        return int(ctr_steps_written)

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """

        names = []

        if self._wave_mem_mode == 'pc_hdd':
            names = self.query('MMEM:CAT?').replace('"', '').replace("'", "").split(",")[2::3]
        elif self._wave_mem_mode == 'awg_segments':

            active_analog = self._get_active_d_or_a_channels(only_analog=True)
            channel_numbers = self.chstr_2_chnum(active_analog, return_list=True)

            for chnl_num in channel_numbers:
                names.extend(self.get_loaded_assets_name(chnl_num, 'segment'))
            names = list(set(names)) # make unique

        else:
            raise ValueError("Unknown memory mode: {}".format(self._wave_mem_mode))

        return names

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        sequence_list = list()

        if not self.has_sequence_mode():
            return sequence_list

        if self._wave_mem_mode == 'pc_hdd':
            # get only the files from the dir and skip possible directories
            log = os.listdir(self._assets_storage_path)
            file_list = [line for line in log if not os.path.isdir(line)]

            for filename in file_list:
                if filename.endswith(('.seq', '.seqx', '.sequence')):
                    if filename not in sequence_list:
                        sequence_list.append(self._remove_file_extension(filename))
        elif self._wave_mem_mode == 'awg_segments':
            seqs_ch1 = self.get_loaded_assets_name(1, 'sequence')
            seqs_ch2 = self.get_loaded_assets_name(2, 'sequence')

            if seqs_ch1 != seqs_ch2:
                self.log.error("Sequence tables for ch1/2 seem unaligned! ch1: {} ch2: {}".format(seqs_ch1,
                                                                                                  seqs_ch2))
            return seqs_ch1
        else:
            raise ValueError("Unknown memory mode: {}".format(self._wave_mem_mode))


        return sequence_list

    def delete_waveform(self, waveform_name):
        """ Delete the waveform with name "waveform_name" from the device memory.

        @param str waveform_name: The name of the waveform to be deleted without _ch? postfix.
                                  Optionally a list of waveform names can be passed.

        @return list: a list of deleted waveform names.
        """
        if isinstance(waveform_name, str):
            waveform_name = [waveform_name]

        avail_waveforms = self.get_waveform_names()   # incl _ch?.bin postfix
        deleted_waveforms = list()

        for name in waveform_name:
            name_ch = self._name_with_ch(name, '?')
            for waveform in avail_waveforms:
                if fnmatch(waveform.lower(), name_ch + "{}".format(self._wave_file_extension)):
                    # delete case insensitive from hdd
                    self.write(':MMEM:DEL "{0}"'.format(waveform))
                    deleted_waveforms.append(waveform)

                if fnmatch(waveform, name_ch):
                    # delete from awg memory
                    active_analog = self._get_active_d_or_a_channels(only_analog=True)
                    for ch_str in active_analog:
                        ch_num = self.chstr_2_chnum(ch_str)
                        try:
                            id = self.asset_name_2_id(self._name_with_ch(name, ch_num), ch_num, mode='segment')
                        except ValueError:  # got already deleted
                            continue
                        self.write('TRAC{}:DEL {:d}'.format(ch_num, id))
                        # set to available segment
                        ids_avail = self.get_loaded_assets_id(ch_num)
                        if ids_avail:
                            self.write('TRAC{}:SEL {:d}'.format(ch_num, ids_avail[0]))
                    deleted_waveforms.append(waveform)

            for loaded_waveform in self.get_loaded_assets()[0].values():
                # in pc_hdd mode, avail_waveforms are only on hdd, need to clear the awg mem
                if self._wave_mem_mode == 'pc_hdd' and fnmatch(loaded_waveform, name_ch):
                    self.clear_all()

        return list(set(deleted_waveforms))

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

        # deletes .sequence files from hdd
        for name in sequence_name:
            for sequence in avail_sequences:
                # in pc_hdd mode, no need to delete
                # .sequence files are handled by sequence generator logic
                if fnmatch(sequence, name):
                    # awg_segment mode
                    self._delete_all_sequences()  # all, as currently only support for 1 sequence
                    deleted_sequences.append(name)

            if name in self.get_loaded_assets()[0].values():
                # clear the AWG incl. all waveforms on awg memory and sequence table
                # todo: delete only waveforms in sequence or think about only unloading the sequence
                # while keeping the waveforms
                self.clear_all()
                self.write_all_ch(':STAB{}:RES',
                                  all_by_one={'m8195a': True})  # Reset all sequence table entries to default values
                deleted_sequences.append(name)

        return list(set(deleted_sequences))

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Will always return False for pulse generator hardware without interleave.
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
            self.log.warning('Interleave mode not available for the AWG M819xA '
                             'Series!\n'
                             'Method call will be ignored.')
        return self.get_interleave()

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.write('*RST')
        self.write('*WAI')

        self._flag_segment_table_req_update = True

        return 0

    ################################################################################
    ###                         Non interface methods                            ###
    ################################################################################

    def set_seq_mode(self, mode):
        self.write_all_ch(":FUNC{}:MODE {}", mode, all_by_one={'m8195a': True})

    def _set_dac_resolution(self):
        pass

    def _set_awg_mode(self):
        pass

    def _set_sample_rate_div(self):
        pass

    def _set_dac_amplifier_mode(self):
        pass

    @abstractmethod
    def _write_output_on(self):
        pass

    @abstractmethod
    def _get_digital_ch_cmd(self, d_ch_name):
        pass

    @abstractmethod
    def _get_init_output_levels(self):
        pass

    @abstractmethod
    def _get_sequence_control_bin(self, sequence_parameters, idx_step):
        pass

    def _delete_all_sequences(self):
        # awg8195a has no sequence subsystem and does not need according cmds
        pass

    def _define_new_sequence(self, name, n_steps):
        pass

    def _init_device(self):
        """ Run those methods during the initialization process."""

        self.reset()
        constr = self.get_constraints()

        self.write(':ROSC:SOUR INT')  # Chose source for reference clock

        self._set_awg_mode()

        # General procedure according to Sec. 8.22.6 in AWG8190A manual:
        # To prepare your module for arbitrary waveform generation follow these steps:
        # 1. Select one of the direct modes (precision or speed mode) or one of the interpolated modes ((x3, x12, x24 and x48)

        self._set_dac_resolution()
        self._set_sample_rate_div()
        self.set_seq_mode('ARB')

        # 2. Define one or multiple segments using the various forms of TRAC:DEF
        # done in load_waveform
        # 3. Fill the segments with values and marker data
        # empty at init
        # 4. Select the segment to be output in arbitrary waveform mode using
        self.write(':TRAC1:SEL 1')
        self.write(':TRAC2:SEL 1')

        # Set the waveform directory on the local pc:
        self.write(':MMEM:CDIR "{0}"'.format(self._pulsed_file_dir))

        self.set_sample_rate(constr.sample_rate.default)

        self._set_dac_amplifier_mode()

        init_levels = self._get_init_output_levels()
        self.set_analog_level(amplitude=init_levels['a_ampl'], offset=init_levels['a_offs'])
        self.set_digital_level(low=init_levels['d_ampl_low'], high=init_levels['d_ampl_high'])

        self._segment_table = [[], []]  # [0]: ch1, [1]: ch2. Local, read-only copy of the device segment table
        self._flag_segment_table_req_update = True  # local copy requires update

    def _load_list_2_dict(self, load_dict):

        def _create_load_dict_allch(load_dict):
            waveform = load_dict[0]  # awg8196a: 1 name per segment, no individual name per channel
            new_dict = dict()

            active_analog = self._get_active_d_or_a_channels(only_analog=True)

            for a_ch in active_analog:
                ch_num = self.chstr_2_chnum(a_ch)
                new_dict[ch_num] = waveform

            return new_dict

        if isinstance(load_dict, list):
            new_dict = dict()
            has_ch_ext = True

            for waveform in load_dict:
                pattern = ".*_ch[0-9]+?"
                has_ch_ext = True if re.match(pattern, waveform) is not None else False
                if has_ch_ext:
                    channel = int(waveform.rsplit('_ch', 1)[1][0])
                    new_dict[channel] = waveform
                else:
                    break
            if not has_ch_ext:
                new_dict = _create_load_dict_allch(load_dict)

            return new_dict

        elif isinstance(load_dict, dict):
            return load_dict
        else:
            self.log.error("Load dict of unexpected type: {}".format(type(load_dict)))

    def _load_wave_from_memory(self, load_dict, to_nextfree_segment=False):
        if self._wave_mem_mode == 'pc_hdd':
            path = self._pulsed_file_dir
            offset = 0

            if not to_nextfree_segment:
                self.clear_all()

            for chnl_num, waveform in load_dict.items():
                name = waveform.split('.bin', 1)[0]  # name in front of .bin/.bin8
                filepath = os.path.join(path, waveform)

                data = self.query_bin(':MMEM:DATA? "{0}"'.format(filepath))
                n_samples = len(data)
                if self.interleaved_wavefile:
                    n_samples = int(n_samples / 2)
                segment_id = self.query('TRAC{0:d}:DEF:NEW? {1:d}'.format(chnl_num, n_samples)) \
                             + '_ch{:d}'.format(chnl_num)
                segment_id_per_ch = segment_id.rsplit("_ch", 1)[0]
                self.write_bin(':TRAC{0}:DATA {1}, {2},'.format(chnl_num, segment_id_per_ch, offset), data)
                self.write(':TRAC{0}:NAME {1}, "{2}"'.format(chnl_num, segment_id_per_ch, name))

                self._check_uploaded_wave_name(chnl_num, name, segment_id_per_ch)

                self._flag_segment_table_req_update = True
                self.log.debug("Loading waveform {} of len {} to AWG ch {}, segment {}.".format(
                    name, n_samples, chnl_num, segment_id_per_ch))

        elif self._wave_mem_mode == 'awg_segments':

            if to_nextfree_segment:
                self.log.warning("In awg_segments memory mode, 'to_nextfree_segment' has no effect."
                                 "Loading only marks active, segments need to be written before.")
            # m8195a: 1 name per segment, no individual name per channel

            for chnl_num, waveform in load_dict.items():
                waveform = load_dict[chnl_num]
                name = waveform
                if name.split(',')[0] == name:
                    segment_id = self.asset_name_2_id(name, chnl_num, mode='segment')
                else:
                    segment_id = np.int(name.split(',')[0])
                self.write(':TRAC{0}:SEL {1}'.format(chnl_num, segment_id))


        else:
            raise ValueError("Unknown memory mode: {}".format(self._wave_mem_mode))

    def send_trigger_event(self):
        self.write(":TRIG:BEG")

    def set_trigger_mode(self, mode="cont"):
        """
        Trigger mode according to manual 3.3.
        :param mode: "cont", "trig" or "gate"
        :return:
        """
        if mode is "cont":
            self.write_all_ch(":INIT:CONT{}:STAT ON",  all_by_one={'m8195a': True})
            self.write_all_ch(":INIT:GATE{}:STAT OFF", all_by_one={'m8195a': True})
        elif mode is "trig":
            self.write_all_ch(":INIT:CONT{}:STAT OFF", all_by_one={'m8195a': True})
            self.write_all_ch(":INIT:GATE{}:STAT OFF", all_by_one={'m8195a': True})
        elif mode is "gate":
            self.write_all_ch(":INIT:CONT{}:STAT OFF", all_by_one={'m8195a': True})
            self.write_all_ch(":INIT:GATE{}:STAT ON",  all_by_one={'m8195a': True})
        else:
            self.log.error("Unknown trigger mode: {}".format(mode))

    def get_trigger_mode(self):
        cont = bool(int(self.query_all_ch(":INIT:CONT{}:STAT?", all_by_one={'m8195a': True})))
        gate = bool(int(self.query_all_ch(":INIT:GATE{}:STAT?", all_by_one={'m8195a': True})))

        if cont and not gate:
            return "cont"
        if not cont and not gate:
            return "trig"
        if not cont and gate:
            return "gate"

        self.log.warning("Unexpected trigger mode found. Cont {}, Gate {}".format(
                            cont, gate))
        return ""

    def get_dynamic_mode(self):
        return self.query_all_ch(":STAB{}:DYN?", all_by_one={'m8195a': True})

    def check_dev_error(self):

        has_error_occured = False

        for i in range(30):  # error buffer of device is 30
            raw_str = self.query(':SYST:ERR?', force_no_check=True)
            is_error = not ('0' in raw_str[0])
            if is_error:
                self.log.warn("AWG issued error: {}".format(raw_str))
                has_error_occured = True
            else:
                break

        return has_error_occured

    def _digital_ch_2_internal(self, d_ch_name):
        if d_ch_name not in self.ch_map:
            self.log.error("Don't understand digital channel name: {}".format(d_ch_name))

        return self.ch_map[str(d_ch_name)]

    def _digital_ch_corresponding_analogue_ch(self, d_ch_name):
        int_name = self._digital_ch_2_internal(d_ch_name)
        if '1' in int_name:
            return 'a_ch1'
        elif '2' in int_name:
            return  'a_ch2'
        else:
            raise RuntimeError("Unknown exception. Should only have 1 or 2 in marker name")

    def _analogue_ch_corresponding_digital_chs(self, a_ch_name):
        # return value must be: [sample marker, sync marker]
        return self.ch_map_a2d[a_ch_name]

    @abstractmethod
    def _set_active_ch(self, new_channels_state):
        pass

    @abstractmethod
    def float_to_sample(self, val):
       pass

    def _float_to_int(self, val, n_bits):

        """
        :param val: np.array(dtype=float64) of sampled values from sequencegenerator.sample_pulse_block_ensemble().
                    normed (-1...1) where 1 encodes the full Vpp as set in 'PulsedGui/Pulsegenerator Settings'.
                    If MW ampl in 'PulsedGui/Predefined methods' < as full Vpp, amplitude reduction will be
                    performed digitally (reducing the effective digital resolution in bits).
        :param n_bits: number of bits; sets the highest integer allowed. Eg. 8 bits -> int in [-128, 127]
        :return:    np.array(dtype=int16)
        """

        bitsize = int(2 ** n_bits)
        min_intval = -bitsize / 2
        max_intval = bitsize / 2 - 1

        max_u_samples = 1  # data should be normalized in (-1..1)

        if max(abs(val)) > 1:
            self.log.warning("Samples from sequencegenerator out of range. Normalizing to -1..1. Please change the "
                             "maximum peak to peak Voltage in the Pulse Generator Settings if you want to use a higher "
                             "power.")
            biggest_val = max([abs(np.min(val)), np.max(val)])
            max_u_samples = biggest_val
        # manual 8.22.4 Waveform Data Format in Direct Mode
        # 2 bits LSB reserved for markers
        mapper = scipy.interpolate.interp1d([-max_u_samples, max_u_samples], [min_intval, max_intval])

        return mapper(val)

    def bool_to_sample(self, val_dch_1, val_dch_2, int_type_str='int16'):
        """
        Takes 2 digital sample values from the sequence generator and converts them to int.
        For AWG819x always two digital channels are tied with a single analogue output.
        The resulting int values are used to construct the binary samples.
        :param vals_dch_1: np.ndarray, digital samples from the sequence generator
        :param vals_dch_2: np.ndarray, digital samples from the sequence generator
        :param int_type_str: int type the output is casted to
        :return:
        """

        bit_dch_1 = 0x1 & np.asarray(val_dch_1).astype(int_type_str)
        bit_dch_2 = 0x2 & (np.asarray(val_dch_2).astype(int_type_str) << 1)

        return bit_dch_1 + bit_dch_2

    @abstractmethod
    def _compile_bin_samples(self, analog_samples, digital_samples, ch_num):
        """
        Creates a binary sample output that combines analog and digital samples
        from the sequence generator in the correct format.

        :return binary samples as expected from awg hardware
        """
        pass


    def _name_with_ch(self, name, ch_num):
        """
        Prepares the final wavename with (M8190A) or without (M8195A) channel extension.
        Preserves capital letters.
        Eg. Rabi -> Rabi_ch1
        """
        return name + '_ch' + str(ch_num)

    def _wavename_2_fname(self, wave_name):
        """
        Preserves capital letters. Note that Windows FS can't keep different files with
        equal names except for capital / non capital letters.
        Handled by deleting case insensitive before writing in _write_to_memory().
        :param wave_name:
        :return:
        """
        return str(wave_name + self._wave_file_extension)

    def _fname_2_wavename(self, fname, incl_ch_postfix=True):
        # works for file name with (8190a) and without (8195a) _ch? postfix
        if incl_ch_postfix:
            return fname.split(".")[0]
        else:
            return fname.split("_ch")[0].split(".")[0]

    def _check_uploaded_wave_name(self, ch_num, wave_name, segment_id):

        wave_name_on_dev = self.get_loaded_asset_name_by_id(ch_num, segment_id)
        if wave_name_on_dev != wave_name:
            self.log.warning("Name of waveform altered during upload: {} -> {} Unsupported characters?".format(
                wave_name, wave_name_on_dev
            ))
            return 1

        return 0

    def _write_wave_to_memory(self, name, analog_samples, digital_samples, active_analog, to_segment_id=1):
        """
        :param name:
        :param analog_samples:
        :param digital_samples:
        :param active_analog:
        :param to_segment_id: id of the segment table the wave will be written to. -1: take next free segment.
        :return:
        """
        waveforms = []

        for idx_ch, ch_str in enumerate(active_analog):

            ch_num = self.chstr_2_chnum(ch_str)
            wave_name = self._name_with_ch(name, ch_num)

            comb_samples = self._compile_bin_samples(analog_samples, digital_samples, ch_str)

            t_start = time.time()

            if self._wave_mem_mode == 'pc_hdd':
                # todo: check if working for awg8195a
                if to_segment_id != 1:
                    self.log.warning("In pc_hdd memory mode, 'to_segment_id' has no effect."
                                     "Writing to hdd without setting segment.")

                filename = self._wavename_2_fname(wave_name)
                waveforms.append(filename)

                if idx_ch == 0:
                    # deletes waveform, all channels
                    self.delete_waveform(self._fname_2_wavename(filename, incl_ch_postfix=False))
                self.write_bin(':MMEM:DATA "{0}", '.format(filename), comb_samples)

                self.log.debug("Waveform {} written to {}".format(wave_name, filename))

            elif self._wave_mem_mode == 'awg_segments':

                if wave_name in self.get_loaded_assets_name(ch_num):
                    seg_id_exist = self.asset_name_2_id(wave_name, ch_num, mode='segment')
                    self.write("TRAC{:d}:DEL {}".format(ch_num, seg_id_exist))
                    self.log.debug("Deleting segment {} ch {} for existing wave {}".format(seg_id_exist, ch_num, wave_name))

                segment_id = to_segment_id
                if name.split(',')[0] != name:
                    # todo: this breaks if there is a , in the name without number
                    segment_id = np.int(name.split(',')[0])
                    self.log.warning("Loading wave to specified segment ({}) via name will deprecate.".format(segment_id))
                if segment_id == -1:
                    # to next free segment
                    segment_id = self.query('TRAC{0:d}:DEF:NEW? {1:d}'.format(ch_num, len(analog_samples[ch_str])))
                    # only need the next free id, definition and writing is performed below again
                    # so delete defined segment again
                    self.write("TRAC{:d}:DEL {}".format(ch_num, segment_id))

                segment_id_ch = str(segment_id) + '_ch{:d}'.format(ch_num)
                self.log.debug("Writing wave {} to ch {} segment_id {}".format(wave_name, ch_str, segment_id_ch))

                # delete if the segment is already existing
                loaded_segments_id = self.get_loaded_assets_id(ch_num)
                if str(segment_id) in loaded_segments_id:
                    # clear the segment
                    self.write(':TRAC:DEL {0}'.format(segment_id))

                # define the size of a waveform segment, marker samples do not count. If the channel is sourced from
                # Extended Memory, the same segment is defined on all other channels sourced from Extended Memory.
                # Comb samples written, but len(comb_samples) doesn't know whether interleaved data.
                self.write(':TRAC{0}:DEF {1}, {2}, {3}'.format(int(ch_num), segment_id, len(analog_samples[ch_str]), 0))

                # name the segment
                self.write(':TRAC{0}:NAME {1}, "{2}"'.format(int(ch_num), segment_id, wave_name))  # name the segment
                # upload
                self.write_bin(':TRAC{0}:DATA {1}, {2},'.format(int(ch_num), segment_id, 0), comb_samples)

                self._check_uploaded_wave_name(ch_num, wave_name, segment_id)

                waveforms.append(wave_name)
                self._flag_segment_table_req_update = True

            else:
                raise ValueError("Unknown memory mode: {}".format(self._wave_mem_mode))

            transfer_speed_mbs = (comb_samples.nbytes/(1024*1024))/(time.time() - t_start)
            self.log.debug('Written ({2:.1f} MB/s) to ch={0}: max ampl: {1}'.format(ch_str,
                                                                                analog_samples[ch_str].max(),
                                                                                transfer_speed_mbs))

        return waveforms

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        return self._sequence_mode

    def write(self, command):
        """ Sends a command string to the device.

            @param string command: string containing the command

            @return int: error code (0:OK, -1:error)
        """
        bytes_written, enum_status_code = self.awg.write(command)

        if self._debug_check_all_commands:
            if 0 != self.check_dev_error():
                self.log.warn("Check failed after command: {}".format(command))

        return int(enum_status_code)

    def write_bin(self, command, values):
        """ Sends a command string to the device.

                    @param string command: string containing the command

                    @return int: error code (0:OK, -1:error)
        """
        self.awg.timeout = None
        bytes_written, enum_status_code = self.awg.write_binary_values(command, datatype=self._wave_transfer_datatype, is_big_endian=False,
                                                                       values=values)
        self.awg.timeout = self._awg_timeout * 1000
        return int(enum_status_code)

    def write_all_ch(self, command, *args, all_by_one=None):
        """
        :param command: visa command
        :param all_by_one:  dict, eg. {"m8190a": False, "m8195a": True}. Set true when for
                            the specific device one command, not separate with ch_nums is required.
                            Eg. "TRAC:SEL" instead for "TRAC1:SEL" and "TRAC2:SEL"
                            If device not listed, will default to False.
        :param args:    replacement list which is filled into command
        :return:
        """

        if all_by_one is None:
            all_by_one = {'m8190a': False, 'm8195a': False}

        single_cmd = False
        if self._MODEL.lower() in all_by_one:
            single_cmd = bool(all_by_one[self._MODEL.lower()])

        if single_cmd:
            # replace first braces that, usually to indicate channel
            command = command.replace("{","", 1)
            command = command.replace("}", "", 1)
            self.write(command.format(*args))
        else:
            for a_ch in self._get_all_analog_channels():
                ch_num = self.chstr_2_chnum(a_ch)
                self.write(command.format(ch_num, *args))

    def query_all_ch(self, command, *args, all_by_one=None):
        """
        :param command: visa command
        :param all_by_one:  dict, eg. {"m8190a": False, "m8195a": True}. Set true when for
                            the specific device one command, not separate with ch_nums is required.
                            Eg. "TRAC:SEL" instead for "TRAC1:SEL" and "TRAC2:SEL"
                            If device not listed, will default to False.
        :param args:    replacement list which is filled into command
        :return: response of all channels collapsed to single value if all channels equal
                 error and response of first channel if otherwise
        """

        if all_by_one is None:
            all_by_one = {'m8190a': False, 'm8195a': False}

        single_cmd = False

        if self._MODEL.lower() in all_by_one:
            single_cmd = bool(all_by_one[self._MODEL.lower()])

        if single_cmd:
            # replace first braces that, usually to indicate channel
            command = command.replace("{", "", 1)
            command = command.replace("}", "", 1)

            return self.query(command.format(*args))
        else:
            retlist = []
            for a_ch in self._get_all_analog_channels():
                ch_num = self.chstr_2_chnum(a_ch)
                retlist = self.query(command.format(ch_num, *args))
            collapsed_ret = np.unique(np.asarray(retlist))
            if collapsed_ret.size > 1:
                self.log.error("Unexpected non-identical response on channels: {}".format(retlist))

            return collapsed_ret[0]

    def query(self, question, force_no_check=False):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        ret = self.awg.query(question).strip().strip('"')
        if self._debug_check_all_commands and not force_no_check:
            if 0 != self.check_dev_error():
                self.log.warn("Check failed after query: {}".format(question))

        return ret

    def query_bin(self, question):

        return self.awg.query_binary_values(question, datatype=self._wave_transfer_datatype, is_big_endian=False)

    def _is_awg_running(self):
        """
        Aks the AWG if the AWG is running
        @return: bool, (True: running, False: stoped)
        """
        # 0 No Output is running
        # 1 CH01 is running
        # 2 CH02 is running
        # 4 CH03 is running
        # 8 CH04 is running
        # run_state is sum of these

        run_state = self.query(':STAT:OPER:RUN:COND?')

        if int(run_state) == 0:
            return False
        else:
            return True

    def _is_output_on(self):
        """
        Asks the AWG if the outputs are on
        @return: bool, (True: Outputs are on, False: Outputs are switched off)
        """

        state = 0

        state += int(self.query(':OUTP1?'))
        state += int(self.query(':OUTP2?'))

        if int(state) == 0:
            return False
        else:
            return True

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
        return sorted(largest_config)

    def _get_all_analog_channels(self):
        """
        Helper method to return a sorted list of all technically available analog channel
        descriptors (e.g. ['a_ch1', 'a_ch2'])

        @return list: Sorted list of analog channels
        """
        return [chnl for chnl in self._get_all_channels() if chnl.startswith('a')]

    def _get_active_d_or_a_channels(self, only_analog=False, only_digital=False):
        """
        Helper method to quickly get only digital or analog active channels.
        :return: list: Sorted list of selected a/d channels
        """

        activation_dict = self.get_active_channels()
        active_channels = {chnl for chnl in activation_dict if activation_dict[chnl]}

        active_ch = sorted(chnl for chnl in active_channels)
        active_analog = sorted(chnl for chnl in active_channels if chnl.startswith('a'))
        active_digital = sorted(chnl for chnl in active_channels if chnl.startswith('d'))

        if only_analog:
            active_ch = active_analog
        if only_digital:
            active_ch = active_digital
        if only_analog and only_digital:
            active_ch = []

        return active_ch

    def _get_all_digital_channels(self):
        """
        Helper method to return a sorted list of all technically available digital channel
        descriptors (e.g. ['d_ch1', 'd_ch2'])

        @return list: Sorted list of digital channels
        """
        return [chnl for chnl in self._get_all_channels() if chnl.startswith('d')]

    def _output_levels_by_config(self, d_ampl_low, d_ampl_high):
        if self._d_ch_level_low_high:
            for i in range(len(self._d_ch_level_low_high)):
                ch_idx = i + 1
                low = self._d_ch_level_low_high[i][0]
                high = self._d_ch_level_low_high[i][1]
                ch_str = 'd_ch{:d}'.format(ch_idx)

                if ch_str in d_ampl_low.keys() and ch_str in d_ampl_high.keys():
                    d_ampl_low['d_ch{:d}'.format(ch_idx)] = low
                    d_ampl_high['d_ch{:d}'.format(ch_idx)] = high
        else:
            pass  # use passed (default) values

        self.log.debug("Overriding output levels from config: d_ampl_low: {}, d_ampl_high: {}".format(
                    d_ampl_low, d_ampl_high))

        return d_ampl_low, d_ampl_high

    def update_segment_table(self):
        segment_table_1 = self.read_segment_table(1)
        segment_table_2 = self.read_segment_table(2)
        self._segment_table[0] = segment_table_1
        self._segment_table[1] = segment_table_2

        self._flag_segment_table_req_update = False

        return segment_table_1, segment_table_2

    def get_segment_table(self, ch_num, force_from_local_copy=-1):

        if force_from_local_copy < 0:
            if self._flag_segment_table_req_update:
                self.log.debug("Local segment table seems out-of-date. Fetching.")
                segment_table_1, segment_table_2 = self.update_segment_table()
            else:
                segment_table_1, segment_table_2 = self._segment_table[0], self._segment_table[1]

        else:
            if force_from_local_copy == 1:
                if self._flag_segment_table_req_update:
                    self.log.warning("Forcing out-of-date local segment table that needs update")
                segment_table_1, segment_table_2 = self._segment_table[0], self._segment_table[1]

            elif force_from_local_copy == 0:
                segment_table_1, segment_table_2 = self.update_segment_table()
            else:
                raise ValueError("Unexpected input for force_from_local_copy: {}".format(force_from_local_copy))

        if ch_num == 1:
            return segment_table_1
        elif ch_num == 2:
            return segment_table_2
        else:
            raise ValueError("Unexpected channel number: {}".format(ch_num))

    def read_segment_table(self, ch_num):

        self.log.debug("Reading device segment table for ch {}".format(ch_num))

        names = self.get_loaded_assets_name(ch_num, mode='segment')
        ids = self.get_loaded_assets_id(ch_num, mode='segment')

        zipped = zip(ids, names)
        segment_table = []

        if len(names) != len(ids):
            self.log.error("Segment table on device seems unaligned.")
            return segment_table

        segment_table = [[x,y] for x,y in sorted(zipped)]

        return segment_table

    def get_segment_name(self, seg_id, ch_num):
        # awg 8190a has 2 separate sequencer per channel!

        segment_table = self.get_segment_table(ch_num)

        try:
            idx_id = [row[0] for row in segment_table].index(seg_id)
            name = [row[1] for row in segment_table][idx_id]

        except ValueError:
            self.log.warning("Couldn't find segment id {} in ch {}".format(seg_id, ch_num))
            return ''
        return name

    def get_segment_id(self, segment_waveform_name, ch_num):
        """
        Finds id of a given waveform name.
        :param segment_waveform_name: waveform name without (eg. .bin) extension
        :param ch_num: analog awg channel
        :return: -1 if not found
        """

        segment_table = self.get_segment_table(ch_num)

        try:
            # np.array would allow slicing, but list comprehension probably better performance
            idx_id = [row[1] for row in segment_table].index(segment_waveform_name)
            id = [row[0] for row in segment_table][idx_id]

        except ValueError:
            self.log.warning("Couldn't find waveform {} in ch {}".format(segment_waveform_name, ch_num))
            return -1
        return id

    @abstractmethod
    def _get_loaded_seq_catalogue(self, ch_num):
        pass

    @abstractmethod
    def _get_loaded_seq_name(self, ch_num, idx):
        pass

    def get_loaded_assets_num(self, ch_num, mode='segment'):
        """
        Retrieves the total number of assets uploaded to the awg memory.
        This is not == "loaded_asset" which is the waveform / segment marked active.
        """
        if mode == 'segment':
            raw_str = self.query(':TRAC{:d}:CAT?'.format(ch_num))
        elif mode == 'sequence':
            raw_str = self._get_loaded_seq_catalogue(ch_num)
        else:
            self.log.error("Unknown assets mode: {}".format(mode))
            return 0

        if raw_str.replace(" ","") == "0,0":   # awg response on 8195A without spaces
            return 0
        else:
            splitted = raw_str.rsplit(',')

            return int(len(splitted)/2)

    def get_loaded_assets_id(self, ch_num, mode='segment'):

        if mode == 'segment':
            raw_str = self.query(':TRAC{:d}:CAT?'.format(ch_num))
        elif mode == 'sequence':
            raw_str = self._get_loaded_seq_catalogue(ch_num)
        else:
            self.log.error("Unknown assets mode: {}".format(mode))
            return []
        n_assets = self.get_loaded_assets_num(ch_num, mode)

        if n_assets == 0:
            return []
        else:
            splitted = raw_str.rsplit(',')
            ids = [int(x) for x in splitted[0::2]]

            return ids

    def get_loaded_assets_name(self, ch_num, mode='segment'):
        """
          Retrieves the names of all assets uploaded to the awg memory.
          This is not == "loaded_asset" which is the waveform / segment marked active.
        """

        asset_ids = self.get_loaded_assets_id(ch_num, mode)
        names = []
        for i in asset_ids:

            if mode == 'segment':
                names.append(self.query(':TRAC{:d}:NAME? {:d}'.format(ch_num, i)))
            elif mode == 'sequence':
                names.append(self._get_loaded_seq_name(ch_num, i))
            else:
                self.log.error("Unknown assets mode: {}".format(mode))
                return 0

        return names

    def get_loaded_asset_name_by_id(self, ch_num, id, mode='segment'):
        asset_names = self.get_loaded_assets_name(ch_num, mode)
        asset_ids = self.get_loaded_assets_id(ch_num, mode)

        try:
            idx = asset_ids.index(int(id))
        except ValueError:
            self.log.warning("Couldn't find {} id {} in loaded assetes".format(mode, id))
            return ""

        return asset_names[idx]

    def asset_name_2_id(self, name, ch_num, mode='segment'):
        names = self.get_loaded_assets_name(ch_num, mode)
        idx = names.index(name)

        return self.get_loaded_assets_id(ch_num, mode)[idx]

    def get_sequencer_state(self, ch_num):
        """
        Queries the state of the sequencer.
        :param ch_num: 1 or 2
        :return: state, sequence table id
                 state:
                 0: idle
                 1: waiting for trigger
                 2: running
                 3: waiting for advancement event
        """

        awg_mode = self.query("FUNC{:d}:MODE?".format(ch_num))
        if awg_mode == 'ARB':
            self.log.warning("Sequencer state is undefined in arb mode")
            return 0, 0

        bin_str = "{:b}".format(int(self.query("STAB{:d}:SEQ:STAT?".format(ch_num))))
        state = int(bin_str[0:2], 2)
        if state != 0:
            seq_table_id = int(bin_str[2:], 2)
        else:
            seq_table_id = 0

        return state, seq_table_id

    def set_trig_polarity(self, pol='pos'):
        if pol is "pos":
            self.write(":ARM:TRIG:SLOP POS")
        elif pol is "neg":
            self.write(":ARM:TRIG:SLOP NEG")
        elif pol is "both":
            self.write(":ARM:TRIG:SLOP EITH")

        else:
            self.log.error("Unknown trigger polarity: {}".format(pol))

    def _remove_file_extension(self, filename):
        """
        Removes filename, even if dot in filename.
        eg. rabi.1.bin -> rabi.1
            rabi.1 -> rabi
            rabi -> rabi
        :param filename:
        :return:
        """
        return filename.rsplit('.', 1)[0]

    def _create_dir(self, path):
        if not os.path.exists(path):
            try:
                os.mkdir(path)
                self.log.info("Folder was missing, so created: {}".format(path))
            except Exception as e:
                self.log.warning("Couldn't create folder: {}. {}".format(path, str(e)))

    def sequence_set_start_segment(self, seqtable_id):
        # todo: need to implement? alernatively shuffle sequuence while generating
        raise NotImplementedError

    def chstr_2_chnum(self, chstr, return_list=False):
        """
        Converts a channel name like 'a_ch1' to channel number internally used to address
        this channel in VISA commands. Eg. 'd_ch1' -> 3 on M8195A.
        :param chstr: list of str or str
        :return: list of int or int
        """

        def single_str_2_num(chstr):
            if 'a_ch' in chstr:
                ch_num = int(chstr.rsplit('_ch', 1)[1])
            elif 'd_ch' in chstr:
                # this is M8195A specific
                ch_num = int(chstr.rsplit('_ch', 1)[1]) + 2
                if self._MODEL == 'M8190A':
                    ch_num = None
                    self.log.warning("Returning None from channel string {}. Belongs to analog ch for 8190A".format(chstr))
            else:
                raise ValueError("Unknown channel string: {}".format(chstr))
            return ch_num

        if isinstance(chstr, str):
            chstr = [chstr]

        num_list = [single_str_2_num(s) for s in chstr]

        if len(num_list) == 1 and not return_list:
            return num_list[0]

        return num_list


class AWGM8195A(AWGM819X):
    """ A hardware module for the Keysight M8195A series for generating
          waveforms and sequences thereof.

      Example config for copy-paste:

          awg8195:
              module.Class: 'awg.keysight_M819x.AWGM8195A'
              awg_visa_address: 'TCPIP0::localhost::hislip0::INSTR'
              awg_timeout: 20
              pulsed_file_dir: 'C:/Software/pulsed_files'               # asset directories should be equal
              assets_storage_path: 'C:/Software/saved_pulsed_assets'    # to the ones in sequencegeneratorlogic
              sample_rate_div: 1
              awg_mode: 'MARK'
      """

    awg_mode_cfg = ConfigOption(name='awg_mode', default='MARK', missing='warn')

    _wave_mem_mode = ConfigOption(name='waveform_memory_mode', default='awg_segments', missing='nothing')
    _wave_file_extension = '.bin8'
    _wave_transfer_datatype = 'b'

    _dac_resolution = 8  # fixed 8 bit
    # physical output channel mapping
    ch_map = {'d_ch1': 3, 'd_ch2': 4}   # awg8195a: digital channels are analogue channels, only different config

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._sequence_names = []  # awg8195a can only store a single sequence

        if self._wave_mem_mode == 'pc_hdd':
            self.log.warning("wave_mem_mode pc_hdd is experimental on m8195a")

    @property
    def n_ch(self):
        return 4

    @property
    def awg_mode(self):
        return self.query(':INST:DACM?')

    @property
    def marker_on(self):
        if self.awg_mode == 'MARK' or self.awg_mode == 'DCM':
            return True
        return False

    @property
    def interleaved_wavefile(self):
        """
        Whether wavefroms need to be uploaded in a interleaved intermediate format.
        Not to confuse with interleave mode from get_interleave().
        :return: True/False: need interleaved wavefile?
        """
        return self.marker_on

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

        # The compatible file formats are hardware specific.
        constraints.waveform_format = ['bin8']
        constraints.dac_resolution = {'min': 8, 'max': 8, 'step': 1, 'unit': 'bit'}

        if self._MODEL == 'M8195A':
            constraints.sample_rate.min = 53.76e9 / self._sample_rate_div
            constraints.sample_rate.max = 65.0e9 / self._sample_rate_div
            constraints.sample_rate.step = 1.0e7
            constraints.sample_rate.default = 65.00e9 / self._sample_rate_div
        else:
            self.log.error('The current AWG model has no valid sample rate '
                           'constraints')

        # manual 1.5.4: Depending on the Sample Rate Divider, the 256 sample wide output of the sequencer
        # is divided by 1, 2 or 4.
        constraints.waveform_length.step = 256 / self._sample_rate_div
        constraints.waveform_length.min = 1280  # != p 108 manual, but tested manually ('MARK')
        constraints.waveform_length.max = int(16e9)
        constraints.waveform_length.default = 1280

        # analog channel
        constraints.a_ch_amplitude.min = 0.075   # from soft frontpanel
        constraints.a_ch_amplitude.max = 2
        constraints.a_ch_amplitude.step = 0.0002 # not used anymore
        constraints.a_ch_amplitude.default = 1
        constraints.a_ch_amplitude.default_marker = 1

        # digital channel
        constraints.d_ch_low.min = 0
        constraints.d_ch_low.max = 1
        constraints.d_ch_low.step = 0.0002
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = 0
        constraints.d_ch_high.max = 2
        constraints.d_ch_high.step = 0.0002
        constraints.d_ch_high.default = 1

        # offset
        constraints.a_ch_offset.max = 1
        constraints.a_ch_offset.min = 0
        constraints.a_ch_offset.default = 0
        constraints.a_ch_offset.default_marker = 0.5 # default value if analog channel is used as marker

        # constraints.sampled_file_length.min = 256
        # constraints.sampled_file_length.max = 2_000_000_000
        # constraints.sampled_file_length.step = 256
        # constraints.sampled_file_length.default = 256

        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 16777215
        constraints.waveform_num.default = 1

        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 16777215
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65536
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names
        # for the different configurations can be customary chosen.
        activation_config = OrderedDict()
        if self._MODEL == 'M8195A':
            awg_mode = self.awg_mode
            if awg_mode == 'MARK':
                activation_config['all'] = frozenset({'a_ch1', 'd_ch1', 'd_ch2'})
            elif awg_mode == 'SING':
                activation_config['all'] = frozenset({'a_ch1'})
            elif awg_mode == 'DUAL':
                activation_config['all'] = frozenset({'a_ch1', 'a_ch2'})
            elif awg_mode == 'FOUR':
                activation_config['all'] = frozenset({'a_ch1', 'a_ch2', 'a_ch3', 'a_ch4'})

        constraints.activation_config = activation_config

        return constraints

    def _get_init_output_levels(self):

        constr = self.get_constraints()

        if self.awg_mode == 'MARK':

            a_ampl = {'a_ch1': constr.a_ch_amplitude.default} # peak to peak voltage
            d_ampl_low = {'d_ch1': constr.d_ch_low.default, 'd_ch2': constr.d_ch_low.default}
            d_ampl_high = {'d_ch1': constr.d_ch_high.default, 'd_ch2': constr.d_ch_high.default}
            a_offs = {}

        elif self.awg_mode == 'FOUR':

            a_ampl = {'a_ch1': constr.a_ch_amplitude.default, 'a_ch2': constr.a_ch_amplitude.default,
                      'a_ch3': constr.a_ch_amplitude.default, 'a_ch4': constr.a_ch_amplitude.default}
            a_offs = {'a_ch1': constr.a_ch_offset.default, 'a_ch2': constr.a_ch_offset.default_marker,
                      'a_ch3': constr.a_ch_offset.default_marker, 'a_ch4': constr.a_ch_offset.default_marker}
            d_ampl_low = {}
            d_ampl_high = {}

        else:
            self.log.error('The chosen AWG ({0}) mode is not implemented yet!'.format(self.awg_mode))

        d_ampl_low, d_ampl_high = self._output_levels_by_config(d_ampl_low, d_ampl_high)

        return {'a_ampl': a_ampl, 'a_offs': a_offs,
                'd_ampl_low': d_ampl_low, 'd_ampl_high': d_ampl_high}

    def _set_awg_mode(self):
        # set only on init by config option, not during runtime

        awg_mode = self.awg_mode_cfg
        self.write(':INSTrument:DACMode {0}'.format(awg_mode))

        # see manual 1.5.5
        if awg_mode == 'MARK' or awg_mode == 'SING' or awg_mode == 'DUAL' or awg_mode == 'FOUR':
            self.write_all_ch(':TRAC{}:MMOD EXT')
        else:
            raise ValueError("Unknown mode: {}".format(awg_mode))

        if awg_mode != 'MARK':
            self.log.error("Setting awg mode {} that is currently not supported! "
                           "Be careful and please report bugs and bug fixes back on github.".format(awg_mode))

        if self.awg_mode != awg_mode:
            self.log.error("Setting awg mode failed, is still: {}".format(self.awg_mode))

    def _set_sample_rate_div(self):
        self.write(':INST:MEM:EXT:RDIV DIV{0}'.format(self._sample_rate_div))  # TODO dependent on DACMode

    def _write_output_on(self):
        self.write_all_ch("OUTP{} ON")

    def _compile_bin_samples(self, analog_samples, digital_samples, ch_str):

        interleaved = self.interleaved_wavefile
        self.log.debug("Compiling samples for {}, interleaved: {}".format(ch_str, interleaved))

        a_samples = self.float_to_sample(analog_samples[ch_str])

        if interleaved and ch_str == 'a_ch1':
            d_samples = self.bool_to_sample(digital_samples['d_ch1'], digital_samples['d_ch2'],
                                            int_type_str='int8')
            # the analog and digital samples are stored in the following format: a1, d1, a2, d2, a3, d3, ...
            comb_samples = np.zeros(2 * a_samples.size, dtype=np.int8)
            comb_samples[::2] =  a_samples
            comb_samples[1::2] = d_samples

        else:
            comb_samples = a_samples

        return comb_samples

    def _get_digital_ch_cmd(self, digital_ch_name):
        d_ch_internal = self._digital_ch_2_internal(digital_ch_name)
        return ':VOLT{0:d}'.format(d_ch_internal)

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

        if ch is None:
            ch = []

        active_ch = dict()

        if ch ==[]:

            # because 0 = False and 1 = True
            awg_mode = self.awg_mode

            if awg_mode == 'MARK':
                active_ch['a_ch1'] = bool(int(self.query(':OUTP1?')))
                active_ch['d_ch1'] = bool(int(self.query(':OUTP3?')))
                active_ch['d_ch2'] = bool(int(self.query(':OUTP4?')))
            elif awg_mode == 'SING':
                active_ch['a_ch1'] = bool(int(self.query(':OUTP1?')))
            elif awg_mode == 'DUAL':
                active_ch['a_ch1'] = bool(int(self.query(':OUTP1?')))
                active_ch['a_ch4'] = bool(int(self.query(':OUTP4?')))
            elif awg_mode == 'FOUR':
                active_ch['a_ch1'] = bool(int(self.query(':OUTP1?')))
                active_ch['a_ch2'] = bool(int(self.query(':OUTP2?')))
                active_ch['a_ch3'] = bool(int(self.query(':OUTP3?')))
                active_ch['a_ch4'] = bool(int(self.query(':OUTP4?')))

        else:

            for channel in ch:
                if 'a_ch' in channel:
                    ana_chan = int(channel[4:])
                    active_ch[channel] = bool(int(self.ask(':OUTP{0}?'.format(ana_chan))))

                elif 'd_ch'in channel:
                    self.log.warning('Digital channel "{0}" cannot be '
                                     'activated! Command ignored.'
                                     ''.format(channel))
                    active_ch[channel] = False

        return active_ch

    def _set_active_ch(self, new_channels_state):
        # get lists of all analog channels
        analog_channels = self._get_all_analog_channels()
        digital_channels = self._get_all_digital_channels()

        # Also (de)activate the channels accordingly
        for a_ch in analog_channels:
            ach_num = self.chstr_2_chnum(a_ch)
            # (de)activate the analog channel
            if new_channels_state[a_ch]:
                self.write('OUTP{0:d} ON'.format(ach_num))
            else:
                self.write('OUTP{0:d} OFF'.format(ach_num))

        for d_ch in digital_channels:
            dch_num = self.chstr_2_chnum(d_ch)
            # (de)activate the digital channel
            if new_channels_state[d_ch]:
                self.write('OUTP{0:d} ON'.format(dch_num))
            else:
                self.write('OUTP{0:d} OFF'.format(dch_num))

    def float_to_sample(self, val):

        val_int = self._float_to_int(val, self._dac_resolution)

        return val_int.astype('int8')

    def _define_new_sequence(self, name, num_steps):
        # no storage system for sequences on 8195a
        self._sequence_names = [name]

    def _delete_all_sequences(self):
        # no storage system for sequences on 8195a
        self._sequence_names = []

    def _get_loaded_seq_catalogue(self, ch_num):

        if not self._sequence_names:
            return '0, 0'  # signals no sequence loaded

        # mimic awg8190 format 'sequence_id, length in segments'
        # we don't need the length here, so dummy value
        return '0, -1'

    def _get_loaded_seq_name(self, ch_num, idx):

        if idx > 0:
            self.log.warn("AWG8195A does not support loading of multiple sequences")

        return self._sequence_names[0]

    def _get_sequence_control_bin(self, sequence_parameters, idx_step):

        index = idx_step
        num_steps = len(sequence_parameters)

        if self.awg_mode == 'MARK':
            control = 2 ** 24  # set marker
        elif self.awg_mode == 'FOUR':
            control = 0
        else:
            self.log.error("The AWG mode '{0}' is not implemented yet!".format(self.awg_mode))
            return

        if index == 0:
            control += 2 ** 28  # set start sequence
        if index + 1 == num_steps:
            control += 2 ** 30  # set end sequence

        return control

    def _name_with_ch(self, name, ch_num):
        """
        M8195A has only one wave file for all channels, no channel extension needed.
        """
        return name


class AWGM8190A(AWGM819X):
    """ A hardware module for the Keysight M8190A series for generating
        waveforms and sequences thereof.

    Example config for copy-paste:

        awg8190:
            module.Class: 'awg.keysight_M819x.AWGM8190A'
            awg_visa_address: 'TCPIP0::localhost::hislip0::INSTR'
            awg_timeout: 20
            pulsed_file_dir: 'C:/Software/pulsed_files'               # asset directories should be equal
            assets_storage_path: 'C:/Software/aved_pulsed_assets'     # to the ones in sequencegeneratorlogic
            sample_rate_div: 1
            dac_resolution_bits: 14
    """

    _dac_amp_mode = 'direct'    # see manual 1.2 'options'
    _wave_mem_mode = ConfigOption(name='waveform_memory_mode', default='pc_hdd', missing='nothing')
    _wave_file_extension = '.bin'
    _wave_transfer_datatype = 'h'

    _dac_resolution = ConfigOption(name='dac_resolution_bits', default='14',
                                   missing='warn')  # 8190 supports 12 (speed) or 14 (precision)

    # physical output channel mapping
    ch_map = {'d_ch1': 'MARK1:SAMP', 'd_ch2': 'MARK2:SAMP', 'd_ch3': 'MARK1:SYNC', 'd_ch4': 'MARK2:SYNC'}
    ch_map_a2d = {'a_ch1': ['d_ch1', 'd_ch3'], 'a_ch2': ['d_ch2', 'd_ch4']}     # corresponding marker channels

    @property
    def n_ch(self):
        return 2

    @property
    def marker_on(self):
        # no reason to deactivate any marker for M8190A, as active makers do not impose restrcitions
        return True

    @property
    def interleaved_wavefile(self):
        return False

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

        # The compatible file formats are hardware specific.
        constraints.waveform_format = ['bin']
        constraints.dac_resolution = {'min': 12, 'max': 14, 'step': 2,
                                      'unit': 'bit'}

        if self._MODEL != 'M8190A':
            self.log.error('This driver is for Keysight M8190A only, but detected: {}'.format(
                self._MODEL
            ))

        if self._dac_resolution == 12:
            constraints.sample_rate.min = 125e6 / self._sample_rate_div
            constraints.sample_rate.max = 12e9 / self._sample_rate_div
            constraints.sample_rate.step = 1.0e7
            constraints.sample_rate.default = 12e9 / self._sample_rate_div
        elif self._dac_resolution == 14:
            constraints.sample_rate.min = 125e6 / self._sample_rate_div
            constraints.sample_rate.max = 8e9 / self._sample_rate_div
            constraints.sample_rate.step = 1.0e7
            constraints.sample_rate.default = 8e9 / self._sample_rate_div
        else:
            raise ValueError("Unsupported DAC resolution: {}".format(self._dac_resolution))

        # manual 8.22.3 Waveform Granularity and Size
        if self._dac_resolution == 12:
            constraints.waveform_length.step = 64
            constraints.waveform_length.min = 320
            constraints.waveform_length.default = 320
        elif self._dac_resolution == 14:
            constraints.waveform_length.step = 48
            constraints.waveform_length.min = 240
            constraints.waveform_length.default = 240

        constraints.waveform_length.max = 2147483648  # assumes option -02G

        constraints.a_ch_amplitude.min = 0.1    # from soft frontpanel, single ended min
        constraints.a_ch_amplitude.max = 0.700  # single ended max
        if self._dac_resolution == 12:
            # 0.7Vpp/2^12=0.0019; for DAC resolution of 12 bits (data sheet p. 17)
            constraints.a_ch_amplitude.step = 1.7090e-4
        elif self._dac_resolution == 14:
            constraints.a_ch_amplitude.step = 4.2725e-5
        constraints.a_ch_amplitude.default = 0.500

        constraints.d_ch_low.min = -0.5
        constraints.d_ch_low.max = 1.75
        constraints.d_ch_low.step = 0.0002
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = 0.5  # manual p. 245
        constraints.d_ch_high.max = 1.75
        constraints.d_ch_high.step = 0.0002
        constraints.d_ch_high.default = 1.5

        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 524287 # manual p. 261
        constraints.waveform_num.default = 1

        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 524288 - 1   # manual p. 251
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1

        constraints.sequence_option = SequenceOption.OPTIONAL
        constraints.sequence_order = "LINONLY"  # SequenceOrderOption.LINONLY

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65536
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names
        # for the different configurations can be customary chosen.

        activation_config = OrderedDict()

        if self._MODEL == 'M8190A':
            # all allowed configs
            # digital channels belong to analogue counterparts
            activation_config['all'] = {'a_ch1', 'a_ch2',
                                        'd_ch1', 'd_ch2', 'd_ch3', 'd_ch4'}
            # sample marker are more accurate than sync markers -> lower d_ch numbers
            activation_config['ch1_2mrk'] = {'a_ch1',
                                             'd_ch1', 'd_ch3'}
            activation_config['ch2_2mrk'] = {'a_ch2',
                                             'd_ch2', 'd_ch4'}

        constraints.activation_config = activation_config

        return constraints

    def _get_init_output_levels(self):

        constr = self.get_constraints()

        a_ampl = {'a_ch1': constr.a_ch_amplitude.default, 'a_ch2': constr.a_ch_amplitude.default}

        d_ampl_low = {'d_ch1': constr.d_ch_low.default, 'd_ch2': constr.d_ch_low.default,
                      'd_ch3': constr.d_ch_low.default, 'd_ch4': constr.d_ch_low.default}
        d_ampl_high = {'d_ch1': constr.d_ch_high.default, 'd_ch2': constr.d_ch_high.default,
                       'd_ch3': constr.d_ch_high.default, 'd_ch4': constr.d_ch_high.default}
        d_ampl_low, d_ampl_high = self._output_levels_by_config(d_ampl_low, d_ampl_high)

        a_offs = {}

        return {'a_ampl': a_ampl, 'a_offs': a_offs,
                'd_ampl_low': d_ampl_low, 'd_ampl_high': d_ampl_high}

    def _set_dac_resolution(self):
        if self._dac_resolution == 12:
            self.write(':TRAC1:DWID WSP')
            self.write(':TRAC2:DWID WSP')
        elif self._dac_resolution == 14:
            self.write(':TRAC1:DWID WPR')
            self.write(':TRAC2:DWID WPR')
        else:
            self.log.error("Unsupported DAC resolution: {}.".format(self._dac_resolution))

    def _set_dac_amplifier_mode(self):
        # todo: implement choosing amp mode
        if self._dac_amp_mode != 'direct':
            raise NotImplementedError("Non direct output '{}' not yet implemented."
                                      .format(self._dac_amp_mode))
        self.write(':OUTP1:ROUT DAC')
        self.write(':OUTP2:ROUT DAC')

    def _write_output_on(self):
        self.write_all_ch("OUTP{}:NORM ON")

    def _compile_bin_samples(self, analog_samples, digital_samples, ch_num):

        marker = self.marker_on

        a_samples = self.float_to_sample(analog_samples[ch_num])
        marker_sample = digital_samples[self._analogue_ch_corresponding_digital_chs(ch_num)[0]]
        marker_sync = digital_samples[self._analogue_ch_corresponding_digital_chs(ch_num)[1]]
        d_samples = self.bool_to_sample(marker_sample, marker_sync, int_type_str='int16')
        if marker:
            comb_samples = a_samples + d_samples
        else:
            comb_samples = a_samples

        return comb_samples

    def _get_digital_ch_cmd(self, digital_ch_name):
        d_ch_internal = self._digital_ch_2_internal(digital_ch_name)
        return ':{}:VOLT'.format(d_ch_internal)

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

        if ch is None:
            ch = []

        active_ch = dict()

        if ch == []:
            active_ch['a_ch1'] = bool(int(self.query(':OUTP1:NORM?')))
            active_ch['a_ch2'] = bool(int(self.query(':OUTP2:NORM?')))

            # marker channels are active if corresponding analogue channel on
            active_ch['d_ch1'] = active_ch[self._digital_ch_corresponding_analogue_ch('d_ch1')]
            active_ch['d_ch2'] = active_ch[self._digital_ch_corresponding_analogue_ch('d_ch2')]
            active_ch['d_ch3'] = active_ch[self._digital_ch_corresponding_analogue_ch('d_ch3')]
            active_ch['d_ch4'] = active_ch[self._digital_ch_corresponding_analogue_ch('d_ch4')]

        else:
            for channel in ch:
                if 'a_ch' in channel:
                    ana_chan = int(channel[4:])
                    active_ch[channel] = bool(int(self.ask(':OUTP{0}:NORM?'.format(ana_chan))))

                elif 'd_ch' in channel:
                    active_ch[channel] = active_ch[self._digital_ch_corresponding_analogue_ch(channel)]

        return active_ch

    def _set_active_ch(self, new_channels_state):

        # get lists of all analog channels
        analog_channels = self._get_all_analog_channels()
        digital_channels = self._get_all_digital_channels()
        current_channel_state = self.get_active_channels()

        # awg 8190: no own channels, digital channels belong to analogue ones
        # iterate digital channels and activate if corresponding analogue is on
        for chnl in current_channel_state.copy():
            if chnl.startswith('d_'):
                if new_channels_state[self._digital_ch_corresponding_analogue_ch(chnl)]:
                    new_channels_state[chnl] = True
                else:
                    new_channels_state[chnl] = False

        # Also (de)activate the channels accordingly
        # awg8190a: digital channels belong to analogue ones
        for a_ch in analog_channels:
            ach_num = self.chstr_2_chnum(a_ch)
            # (de)activate the analog channel
            if new_channels_state[a_ch]:
                self.write('OUTP{0:d}:NORM ON'.format(ach_num))
            else:
                self.write('OUTP{0:d}:NORM OFF'.format(ach_num))

    def float_to_sample(self, val):

        val_int = self._float_to_int(val, self._dac_resolution)
        shiftbits = 16 - self._dac_resolution  # 2 for marker, dac: 12 -> 2, dac: 14 -> 4

        return val_int.astype('int16') << shiftbits

    def _delete_all_sequences(self):

        self.write_all_ch(':SEQ{}:DEL:ALL')

    def _define_new_sequence(self, name, n_steps):

        seq_id_ch1 = int(self.query(":SEQ1:DEF:NEW? {:d}".format(n_steps)))
        seq_id_ch2 = int(self.query(":SEQ2:DEF:NEW? {:d}".format(n_steps)))
        if seq_id_ch1 != seq_id_ch2:
            self.log.warning("Sequence tables for channels seem not aligned.")
        self.write(":SEQ1:NAME {:d}, '{}'".format(seq_id_ch1, name))
        self.write(":SEQ2:NAME {:d}, '{}'".format(seq_id_ch2, name))

    def _get_loaded_seq_catalogue(self, ch_num):
        return self.query(':SEQ{:d}:CAT?'.format(ch_num))

    def _get_loaded_seq_name(self, ch_num, idx):
        """
        :param ch_num:
        :param idx: 0,1,2. Not the sequenceId = seqtable id of first element in sequence
        :return:
        """
        seq_id = self.get_loaded_assets_id(ch_num, 'sequence')[idx]
        return self.query(':SEQ{:d}:NAME? {:d}'.format(ch_num, seq_id))

    def _get_sequence_control_bin(self, sequence_parameters, idx_step):

        index = idx_step
        wfm_tuple, seq_step = sequence_parameters[index]
        num_steps = len(sequence_parameters)

        try:
            next_step = sequence_parameters[index + 1][1]
        except IndexError:
            next_step = None

        control = 0

        if index == 0:
            control = 0x1 << 28  # bit 28 (=0x10000000): mark as sequence start
        if index + 1 == num_steps:
            control = 0x1 << 30  # bit 30: mark as sequence end

        # in use case with external pattern jump, every segment with an address
        # defines a "sequence" (as defined in Keysight manual)
        if 'pattern_jump_address' in seq_step:
            control = 0x1 << 28
        if next_step:
            if 'pattern_jump_address' in next_step:
                control = 0x1 << 30

        control += 0x1 << 24  # always enable markers

        return control

