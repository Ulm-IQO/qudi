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
"""

from core.base import Base
from hardware.pulser_interface import PulserInterface

class PulserInterfaceDummy(Base, PulserInterface):
    """ UNSTABLE: Alex Stark

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

        self.connected = False
        self.amplitude = 0.25
        self.sample_rate = 10.0e6
        self.uploaded_sequence_list = []
        self.current_loaded_file = None
        self.is_output_enabled = True

        # settings for remote access on the AWG PC
        self.sequence_directory = '/waves'

        # AWG5002C has possibility for sequence output
        self.use_sequencer = True
        self.sequence_directory = '/waves'

        self.active_channel = (2,4)
        self.interleave = False

        self.current_status =  0    # that means off, not running.

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
        constraints['channel_config'] = [(1,2), (2,4)]
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

    def download_sequence(self, waveform, write_to_file = True):
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
        if waveform.name not in self.loaded_sequence:
            self.uploaded_sequence_list.append(waveform.name)
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

    def load_sequence(self, seq_name, channel=None):
        """ Loads a sequence to the specified channel of the pulsing device.

        @param str seq_name: The name of the sequence to be loaded
        @param int channel: The channel for the sequence to be loaded into if
                            not already specified in the sequence itself

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        if seq_name in self.uploaded_sequence_list:
            self.current_loaded_file = seq_name
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
        """ Set the peak-to-peak voltage of the pulse generator hardware analogue channels.
        Unused for purely digital hardware without logic level setting capability (DTG, FPGA, etc.).

        @param int channel: The channel to be reconfigured
        @param float amplitude: The peak-to-peak amplitude the channel should be set to (in V)

        @return int: error code (0:OK, -1:error)
        """
        self.amplitude = voltage
        return 0

    def get_pp_voltage(self, channel):
        """ Get the peak-to-peak voltage of the pulse generator hardware analogue channels.

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

        return self.uploaded_sequence_list

    def delete_sequence(self, seq_name):
        """ Delete a sequence with the passed seq_name from the device memory.

        @param str seq_name: The name of the sequence to be deleted

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """

        if seq_name in self.uploaded_sequence_list:
            self.uploaded_sequence_list.remove(seq_name)
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

        @param string question: string containing the command

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


