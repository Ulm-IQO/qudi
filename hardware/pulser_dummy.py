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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import os
from collections import OrderedDict
from fnmatch import fnmatch

from core.base import Base
from interface.pulser_interface import PulserInterface


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

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))

        self.log.info('Dummy Pulser: I will simulate an AWG :) !')

        self.awg_waveform_directory = '/waves'

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
            self.log.warning('No parameter "pulsed_file_dir" was specified '
                    'in the config for SequenceGeneratorLogic as directory '
                    'for the pulsed files!\nThe default home directory\n'
                    '{0}\n'
                    'will be taken instead.'.format(self.pulsed_file_dir))

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')

        self.compatible_waveform_format = 'wfm' # choose one of 'wfm', 'wfmx' or 'fpga'
        self.compatible_sequence_format = 'seq' # choose one of 'seq' or 'seqx'

        self.connected = False
        self.sample_rate = 25e9

        # Deactivate all channels at first:
        ch = {'a_ch1': False, 'a_ch2': False, 'a_ch3': False,
              'd_ch1': False, 'd_ch2': False, 'd_ch3': False, 'd_ch4': False,
              'd_ch5': False, 'd_ch6': False, 'd_ch7': False, 'd_ch8': False}
        self.active_channel = ch

        # for each analog channel one value
        self.amplitude_list = {'a_ch1': 1, 'a_ch2': 1, 'a_ch3': 1}
        self.offset_list = {'a_ch1': 0, 'a_ch2': 0, 'a_ch3': 0}

        # for each digital channel one value
        self.digital_high_list = {'d_ch1': 5, 'd_ch2': 5, 'd_ch3': 5, 'd_ch4': 5,
                                  'd_ch5': 5, 'd_ch6': 5, 'd_ch7': 5, 'd_ch8': 5}
        self.digital_low_list = {'d_ch1': 0, 'd_ch2': 0, 'd_ch3': 0, 'd_ch4': 0,
                                 'd_ch5': 0, 'd_ch6': 0, 'd_ch7': 0, 'd_ch8': 0}

        self.uploaded_assets_list = []
        self.uploaded_files_list = []
        self.current_loaded_asset = None
        self.is_output_enabled = True

        # settings for remote access on the AWG PC
        self.asset_directory = 'waves'
        self.use_sequencer = True
        self.interleave = False

        self.current_status = 0    # that means off, not running.

    def on_activate(self, e):
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

    def on_deactivate(self, e):
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

        # if interleave option is available, then sample rate constraints must
        # be assigned to the output of a function called
        # _get_sample_rate_constraints()
        # which outputs the shown dictionary with the correct values depending
        # on the present mode. The the GUI will have to check again the
        # limitations if interleave was selected.
        constraints['sample_rate']  = self._get_sample_rate_constraints()

        # The file formats are hardware specific. The sequence_generator_logic will need this
        # information to choose the proper output format for waveform and sequence files.
        constraints['waveform_format'] = self.compatible_waveform_format
        constraints['sequence_format'] = self.compatible_sequence_format

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
        sequence_param['repetitions'] = {'min': 0, 'max': 65536, 'step': 1,
                                         'unit': '#'}
        sequence_param['trigger_wait'] = {'min': False, 'max': True, 'step': 1,
                                          'unit': 'bool'}
        sequence_param['event_jump_to'] = {'min': -1, 'max': 8000, 'step': 1,
                                           'unit': 'row'}
        sequence_param['go_to'] = {'min': 0, 'max': 8000, 'step': 1,
                                   'unit': 'row'}
        constraints['sequence_param'] = sequence_param

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names
        # for the different configurations can be customary chosen.

        activation_config = OrderedDict()
        activation_config['config1'] = ['a_ch2', 'd_ch1', 'd_ch2', 'a_ch3', 'd_ch3', 'd_ch4']
        # Usage of channel 1 only:
        activation_config['config2'] = ['a_ch2', 'd_ch1', 'd_ch2']
        # Usage of channel 2 only:
        activation_config['config3'] = ['a_ch3', 'd_ch3', 'd_ch4']
        # Usage of Interleave mode:
        activation_config['config4'] = ['a_ch1', 'd_ch1', 'd_ch2']
        # Usage of only digital channels:
        activation_config['config5'] = ['d_ch1', 'd_ch2', 'd_ch3', 'd_ch4',
                                        'd_ch5', 'd_ch6', 'd_ch7', 'd_ch8']
        # Usage of only one analog channel:
        activation_config['config6'] = ['a_ch1']
        activation_config['config7'] = ['a_ch2']
        activation_config['config8'] = ['a_ch3']
        # Usage of only the analog channels:
        activation_config['config9'] = ['a_ch2', 'a_ch3']

        constraints['activation_config'] = activation_config

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
        self.log.info('PulserDummy: Switch on the Output.')
        return self.current_status

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:stopped, -1:error, 1:running)
        """
        self.current_status = 0
        self.log.info('PulserDummy: Switch off the Output.')
        return self.current_status

    def upload_asset(self, asset_name=None):
        """ Upload an already hardware conform file to the device.
            Does NOT load it into channels.

        @param name: string, name of the ensemble/seqeunce to be uploaded

        @return int: error code (0:OK, -1:error)

        If nothing is passed, method will be skipped.
        """
        if asset_name is None:
            self.log.warning('No asset name provided for upload!\n'
                    'Correct that!\n'
                    'Command will be ignored.')
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

    def get_loaded_asset(self):
        """ Retrieve the currently loaded asset name of the device.

        @return str: Name of the current asset, that can be either a filename
                     a waveform, a sequence ect.
        """
        return self.current_loaded_asset

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

    def get_active_channels(self, ch=[]):
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

        active_ch = {}

        if ch == []:
            active_ch = self.active_channel

        else:
            for channel in ch:
                active_ch[channel] = self.active_channel[channel]

        return active_ch

    def set_active_channels(self, ch={}):
        """ Set the active channels for the pulse generator hardware.

        @param dict ch: dictionary with keys being the analog or digital
                          string generic names for the channels with items being
                          a boolean value.current_loaded_asset

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

        The hardware itself has to handle, whether separate channel activation
        is possible.
        """
        for channel in ch:
            self.active_channel[channel] = ch[channel]

        return self.get_active_channels(ch=list(ch))

    def get_uploaded_asset_names(self):
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

        self.log.info('It is so nice that you talk to me and told me "{0}"; '
                'as a dummy it is very dull out here! :) '.format(command))

        return 0

    def ask(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """

        self.log.info('Dude, I\'m a dummy! Your question \'{0}\' is way to '
                    'complicated for me :D !'.format(question))

        return 'I am a dummy!'

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('Dummy cannot be reseted!')

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

    def _get_num_a_ch(self):
        """ Retrieve the number of available analog channels.

        @return int: number of analog channels.
        """
        config = self.get_constraints()['activation_config']

        all_a_ch = []
        for conf in config:

            # extract all analog channels from the config
            curr_ach = [entry for entry in config[conf] if 'a_ch' in entry]

            # append all new analog channels to a temporary array
            for a_ch in curr_ach:
                if a_ch not in all_a_ch:
                    all_a_ch.append(a_ch)

        # count the number of entries in that array
        return len(all_a_ch)

    def _get_num_d_ch(self):
        """ Retrieve the number of available digital channels.

        @return int: number of digital channels.
        """
        config = self.get_constraints()['activation_config']

        all_d_ch = []
        for conf in config:

            # extract all digital channels from the config
            curr_d_ch = [entry for entry in config[conf] if 'd_ch' in entry]

            # append all new analog channels to a temporary array
            for d_ch in curr_d_ch:
                if d_ch not in all_d_ch:
                    all_d_ch.append(d_ch)

        # count the number of entries in that array
        return len(all_d_ch)
