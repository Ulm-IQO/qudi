# -*- coding: utf-8 -*-

"""
This file contains the QuDi GUI module base class.

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

import time

from core.base import Base
from hardware.pulser_interface import PulserInterface

class AWG5002C(Base, PulserInterface):
    """ Unstable and in contruction, Alex Stark    """

    _modclass = 'awg5002c'
    _modtype = 'hardware'

    # declare connectors
    _out = {'awg5002c': 'awg5002c'}

    def __init__(self, manager, name, config = {}, **kwargs):

        state_actions = {'onactivate'   : self.activation,
                         'ondeactivate' : self.deactivation}

        super(AWG5002C, self).__init__(self, manager, name, config, state_actions, **kwargs)

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
            self.samplingrate = config['default_sample_rate']
        else:
            self.logMsg('No parameter "default_sample_rate" found in the '
                        'config for the AWG5002C! The maximum sample rate is '
                        'used instead.', msgType='warning')
            self.samplingrate = self.get_constraints()['sample_rate'][1]


        self.connected = False
        self.amplitude = 0.25
        self.loaded_sequence = None
        self.is_output_enabled = True

        # settings for remote access on the AWG PC
        self.sequence_directory = '/waves'

        # AWG5002C has possibility for sequence output
        self.use_sequencer = True


    def activation(self, e):
        """ Initialisation performed during activation of the module. """
        self.connected = True

    def deactivation(self, e):
        self.connected = False
        pass


    def get_constraints(self):
        """ Retrieve the hardware constrains from the AWG.

        @return: dict with the hardware constraints.
        """
        constraints = {}
        # (min, max, incr) in samples/second:
        constraints['sample_rate'] = (10.0e6, 600.0e6, 1)
        # (min, max, res) in Volt-peak-to-peak:
        constraints['amplitude_analog'] = (0.02, 4.5, 0.001)
        # (min, max, res, range_min, range_max)
        # min, max and res are in Volt, range_min and range_max in
        # Volt-peak-to-peak:
        constraints['amplitude_digital'] = (-1.0, 2.7, 0.01, 0.1, 3.7)
        # (min, max, granularity) in samples for one waveform:
        constraints['waveform_length'] = (1, 32400000, 1)
        # (min, max, inc) in number of waveforms in system
        constraints['waveform_number'] = (1, 32000, 1)
        # (min, max, inc) number of subsequences within a sequence:
        constraints['subsequence_number'] = (1, 8000, 1)
        # (min, max, incr) in Samples:
        constraints['total_length_bins'] = (0, 32e6, 0)
        # (analogue, digital) possible combination in given channels:
        constraints['channel_config'] = [(1,0), (1,1), (1,2), (2,0), (2,1), (2,2), (2,3), (2,4)]
        return constraints



    # =========================================================================
    # Below all the low level routines which are needed for the communication
    # and establishment of a connection.
    # ========================================================================


    def tell(self, command):
        """Send a command string to the AWG.

        @param command: string containing the command
        @return int: error code (0:OK, -1:error)
        """
        if not command.endswith('\n'):
            command += '\n'

        # In Python 3.x the socket send command only accepts byte type arrays
        # and no str
        command = bytes(command, 'UTF-8')
        self.soc.connect((self.ip_address, self.port))
        self.soc.send(command)
        self.soc.close()
        return 0

    def ask(self, question):
        """ Asks the device a 'question' and receive an answer from the device.

        @param string question: string containing the command
        @return string: the answer of the device to the 'question'
        """
        if not question.endswith('\n'):
            question += '\n'

        # In Python 3.x the socket send command only accepts byte type arrays
        #  and no str.
        question = bytes(question, 'UTF-8')
        self.soc.connect((self.ip_address, self.port))
        self.soc.send(question)
        time.sleep(0.5) # you need to wait until AWG generating an answer.

        message = self.soc.recv(self.input_buffer)  # receive an answer
        message = message.decode('UTF-8') # decode bytes into a python str
        message = message.replace('\n','')      # cut away the characters\r and \n.
        message = message.replace('\r','')
        self.soc.close()
        return message

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)
        @return int: error code (0:OK, -1:error)

        Unused for pulse generator hardware other than an AWG. The AWG 5000
        Series does not have an interleave mode and this method exists only for
        compability reasons.
        """
        self.logMsg('Interleave mode not available for this AWG! Method call '
                    'will be ignored.', msgType='warning')
        return 0

    def reset(self):
        """Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.soc.connect((self.ip_address, self.port))
        self.soc.send('*RST\n')
        self.soc.close()
        return 0





    # =========================================================================
    # Below all the higher level routines are situated which use the
    # wrapped routines as a basis to perform the desired task.
    # =========================================================================