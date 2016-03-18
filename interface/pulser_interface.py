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
Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
"""


from core.util.customexceptions import InterfaceImplementationError

class PulserInterface():
    """ UNSTABLE: Nikolas Tomek

    This is the Interface class to define the abstract controls and
    communication with all pulsing devices.
    """

    _modtype = 'PulserInterface'
    _modclass = 'interface'

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

        # Example for configuration with default values:
        constraints = {}

        # if interleave option is available, then sample rate constraints must
        # be assigned to the output of a function called
        # _get_sample_rate_constraints()
        # which outputs the shown dictionary with the correct values depending
        # on the present mode. The the GUI will have to check again the
        # limitations if interleave was selected.
        constraints['sample_rate'] = {'min': 0.0, 'max': 0.0,
                                      'step': 0.0, 'unit': 'Samples/s'}

        # the stepsize will be determined by the DAC in combination with the
        # maximal output amplitude (in Vpp):
        constraints['a_ch_amplitude'] = {'min': 0.0, 'max': 0.0,
                                         'step': 0.0, 'unit': 'Vpp'}
        constraints['a_ch_offset'] = {'min': 0.0, 'max': 0.0,
                                      'step': 0.0, 'unit': 'V'}
        constraints['d_ch_low'] = {'min': 0.0, 'max': 0.0,
                                   'step': 0.0, 'unit': 'V'}
        constraints['d_ch_high'] = {'min': 0.0, 'max': 0.0,
                                    'step': 0.0, 'unit': 'V'}
        constraints['sampled_file_length'] = {'min': 0, 'max': 0,
                                              'step': 0, 'unit': 'Samples'}
        constraints['digital_bin_num'] = {'min': 0, 'max': 0,
                                          'step': 0, 'unit': '#'}
        constraints['waveform_num'] = {'min': 0, 'max': 0,
                                       'step': 0, 'unit': '#'}
        constraints['sequence_num'] = {'min': 0, 'max': 0,
                                       'step': 0, 'unit': '#'}
        constraints['subsequence_num'] = {'min': 0, 'max': 0,
                                          'step': 0, 'unit': '#'}

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
        channel_config['conf1'] = ['a_ch', 'd_ch', 'd_ch']
        channel_config['conf2'] = ['a_ch', 'd_ch', 'd_ch', 'a_ch', 'd_ch', 'd_ch']
        constraints['channel_config'] = channel_config

        # Now you can choose, how many channel activation pattern exists. You
        # can only use the names, declared in the constraint 'available_ch'!
        activation_map = OrderedDict()
        activation_map['map1'] = ['ACH1', 'DCH1', 'DCH2', 'ACH2', 'DCH3', 'DCH4']
        # Usage of channel 1 only:
        activation_map['map2'] = ['ACH1', 'DCH1', 'DCH2']
        # Usage of channel 2 only:
        activation_map['map3'] = ['ACH2', 'DCH3', 'DCH4']
        constraints['activation_map'] = activation_map

        # this information seems to be almost redundant but it can be that no
        # channel configuration exists, where not all available channels are
        # present. Therefore this is needed here:
        constraints['available_ch_num'] = {'a_ch': 2, 'd_ch': 4}

        # number of independent channels on which you can load or upload
        # separately the created files. It does not matter how the channels
        # are looking like.
        constraints['independent_ch'] = 2
        """

        raise InterfaceImplementationError('PulserInterface>get_constraints')
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>pulser_on')
        return -1

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>pulser_off')
        return -1

    def upload_asset(self, name):
        """ Upload an already hardware conform file to the device.
            Does NOT load it into channels.

        @param name: string, name of the asset to upload

        @return int: error code (0:OK, -1:error)

        If nothing is passed, method will be skipped.
        """
        raise InterfaceImplementationError('PulserInterface>upload_asset')
        return -1

    def load_asset(self, load_dict={}):
        """" Load an already hardware conform file, which was transferred to the
            device on the with the provided name to the specified channel.

        @param: dict load_dict: a dictionary with keys being one of the
                                available channel numbers and items being the
                                name of the already sampled
                                Pulse_Block_Ensemble.

        @return int: error code (0:OK, -1:error)

        Example:
            If the Pulse_Block_Ensemble with name 'my-funny-stuff' is going to
            be loaded on channel 1 and 2 then it has to be passed like:
                upload_dict = {1: 'my-funny-stuff', 2: 'my-funny-stuff'}
            The pulse device should choose the proper file (which belongs to
            channel 1 and 2) and load it.
            You can e.g. also load just the file on channel two with:
                upload_dict = {2: 'my-funny-stuff'}

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA). Waveforms and single channel sequences can be
        assigned to each or both channels. Double channel sequences must be
        assigned to channel 1. The AWG's file system is case-sensitive.
        """
        raise InterfaceImplementationError('PulserInterface>load_asset')
        return -1

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without storage capability
        (PulseBlaster, FPGA).
        """
        raise InterfaceImplementationError('PulserInterface>clear_all')
        return -1

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

        raise InterfaceImplementationError('PulserInterface>get_status')
        return (-1, status_dic)

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (-1:error)
        """
        raise InterfaceImplementationError('PulserInterface>set_sampling_rate')
        return -1.

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """
        raise InterfaceImplementationError('PulserInterface>get_sampling_rate')
        return -1

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
        raise InterfaceImplementationError('PulserInterface>get_a_ch_amplitude')
        return -1

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

        raise InterfaceImplementationError('PulserInterface>set_a_ch_amplitude')
        return -1

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

        raise InterfaceImplementationError('PulserInterface>get_a_ch_offset')
        return -1

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

        raise InterfaceImplementationError('PulserInterface>set_a_ch_offset')
        return -1



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
        """
        raise InterfaceImplementationError('PulserInterface>set_active_channels')
        return {}, {}

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
        raise InterfaceImplementationError('PulserInterface>get_active_channels')
        return [-1], [-1]

    def get_uploaded_asset_names(self):
        """ Retrieve the names of all uploaded assets on the device.

        @return list: List of all uploaded asset name strings in the current
                      device directory.

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        names = []
        raise InterfaceImplementationError('PulserInterface>get_uploaded_assets_names')
        return names

    def get_saved_asset_names(self):
        """ Retrieve the names of all sampled and saved files on the host PC.

        @return list: List of all saved asset name strings in the current
                      directory of the host PC.
        """
        names = []
        raise InterfaceImplementationError('PulserInterface>get_sequence_names')
        return names

    def delete_asset(self, asset_name):
        """ Delete an asset with the passed asset_name from the device memory.

        @param str asset_name: The name of the sequence to be deleted
                               Optionally a list of file names can be passed.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        raise InterfaceImplementationError('PulserInterface>delete_sequence')
        return -1

    def set_asset_dir_on_device(self, dir_path):
        """ Change the directory where the assets are stored on the device.

        @param string dir_path: The target directory

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without changeable file structure
        (PulseBlaster, FPGA).
        """
        raise InterfaceImplementationError('PulserInterface>set_sequence_directory')
        return -1

    def get_asset_dir_on_device(self):
        """ Ask for the directory where the hardware conform files are stored on
            the device.

        @return string: The current file directory

        Unused for digital pulse generators without changeable file structure
        (PulseBlaster, FPGA).
        """
        raise InterfaceImplementationError('PulserInterface>get_sequence_directory')
        return ''

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        @return int: error code (0:OK, -1:error)

        Unused for pulse generator hardware other than an AWG.
        """
        raise InterfaceImplementationError('PulserInterface>set_interleave')
        return -1

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Unused for pulse generator hardware other than an AWG.
        """

        raise InterfaceImplementationError('PulserInterface>set_interleave')
        return -1

    def tell(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>tell')
        return -1

    def ask(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        raise InterfaceImplementationError('PulserInterface>ask')
        return ''

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>reset')
        return -1

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        raise InterfaceImplementationError('PulserInterface>has_sequence_mode')
        return -1

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
        @param total_number_of_samples: int, The total number of samples in the entire waveform.
                                        Has to be known it advance.
        @param is_first_chunk: bool, indicates if the current chunk is the
                               first write to this file.
        @param is_last_chunk: bool, indicates if the current chunk is the last
                              write to this file.

        @return: error code (0: OK, -1: error)
        """
        raise InterfaceImplementationError('PulserInterface>write_to_file')
        return -1