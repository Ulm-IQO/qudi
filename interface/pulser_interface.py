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
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        and the key 'channel_map' indicates all possible combinations
        (analogue, digital) in usage for this device.

        The possible keys in the constraint are defined here in the interface
        file. If the hardware does not support the values for the constraints,
        then insert just None.
        If you are not sure about the meaning, look in other hardware files
        to get an impression.
        """
        constraints = {}
        constraints['sample_rate']          = (None, None, None)
        constraints['amplitude_analog']     = (None, None, None)
        constraints['amplitude_digital']    = (None, None, None)
        constraints['waveform_length']      = (None, None, None)
        constraints['waveform_number']      = (None, None, None)
        constraints['subsequence_elements'] = (None, None, None)
        constraints['sequence_elements']    = (None, None, None)
        constraints['total_length_bins']    = (None, None, None)
        constraints['channel_config']       = [(None, None), (None, None)]
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

    #FIXME: That method needs to be carefully investigated to be used also for
    #       pulsing devices without analogue channels!
    def write_chunk_to_file(self, name, analogue_samples_chunk,
                            digital_samples_chunk, total_number_of_samples,
                            is_first_chunk, is_last_chunk, sample_rate,
                            pp_voltage):
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
        raise InterfaceImplementationError('PulserInterface>write_chunk_to_file')
        return -1

    def upload_asset(self, name):
        """ Waveform or sequence with name "name" gets uploaded to the Hardware.

        @param str name: The name of the sequence/waveform to be transferred

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>upload_asset')
        return -1

    def load_asset(self, asset_name, channel=None):
        """ Loads a sequence or waveform to the specified channel of the pulsing
            device.

        @param str asset_name: The name of the asset to be loaded
        @param int channel: The channel for the sequence to be loaded into if
                            not already specified in the sequence itself

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
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

    def set_pp_voltage(self, channel, voltage):
        """ Set the peak-to-peak voltage of the pulse generator hardware
        analogue channels.

        @param int channel: The channel to be reconfigured
        @param float voltage: The peak-to-peak amplitude the channel should be
                              set to (in V)

        @return int: error code (0:OK, -1:error)

        Unused for purely digital hardware without logic level setting
        capability (DTG, FPGA, etc.).
        """
        raise InterfaceImplementationError('PulserInterface>set_pp_voltage')
        return -1

    def get_pp_voltage(self, channel):
        """ Get the peak-to-peak voltage of the pulse generator hardware
        analogue channels.

        @param int channel: The channel to be checked

        @return float: The peak-to-peak amplitude the channel is set to (in V)

        Unused for purely digital hardware without logic level setting
        capability (FPGA, etc.).
        """
        raise InterfaceImplementationError('PulserInterface>get_pp_voltage')
        return -1

    def set_active_channels(self, d_ch=0, a_ch=0):
        """ Set the active channels for the pulse generator hardware.

        @param int d_ch: number of active digital channels
        @param int a_ch: number of active analogue channels

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>set_active_channels')
        return -1

    def get_active_channels(self):
        """ Get the active channels of the pulse generator hardware.

        @return (int, int): number of active channels (analogue, digital)
        """
        raise InterfaceImplementationError('PulserInterface>get_active_channels')
        return (-1, -1)

    def get_uploaded_assets_names(self):
        """ Retrieve the names of all uploaded assets on the device.

        @return list: List of asset name strings

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        names = []
        raise InterfaceImplementationError('PulserInterface>get_uploaded_assets_names')
        return names

    def get_saved_assets_names(self):
        """ Retrieve the names of all sampled and saved sequences on the host PC.

        @return list: List of sequence name strings
        """
        names = []
        raise InterfaceImplementationError('PulserInterface>get_sequence_names')
        return names

    def delete_sequence(self, seq_name):
        """ Delete a sequence with the passed seq_name from the device memory.

        @param str seq_name: The name of the sequence to be deleted

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        raise InterfaceImplementationError('PulserInterface>delete_sequence')
        return -1

    def set_sequence_directory(self, dir_path):
        """ Change the directory where the sequences are stored on the device.

        @param string dir_path: The target directory

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        raise InterfaceImplementationError('PulserInterface>set_sequence_directory')
        return -1

    def get_sequence_directory(self):
        """ Ask for the directory where the sequences are stored on the device.

        @return string: The current sequence directory

        Unused for digital pulse generators without sequence storage capability
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