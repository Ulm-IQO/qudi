# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware file for AWG5000 Series.

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
from ftplib import FTP
from socket import socket, AF_INET, SOCK_STREAM


from core.base import Base
from hardware.pulser_interface import PulserInterface

class AWG5002C(Base, PulserInterface):
    """ Unstable and in contruction, Alex Stark    """

    _modclass = 'awg5002c'
    _modtype = 'hardware'

    # declare connectors
    _out = {'awg5002c': 'PulserInterface'}

    def __init__(self, manager, name, config, **kwargs):

        state_actions = {'onactivate'   : self.activation,
                         'ondeactivate' : self.deactivation}

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
            self.samplingrate = config['default_sample_rate']
        else:
            self.logMsg('No parameter "default_sample_rate" found in the '
                        'config for the AWG5002C! The maximum sample rate is '
                        'used instead.', msgType='warning')
            self.samplingrate = self.get_constraints()['sample_rate'][1]

        if 'awg_ftp_path' in config.keys():
            self.ftp_path = config['awg_ftp_path']
        else:
            self.logMsg('No parameter "awg_ftp_path" found in the config for '
                        'the AWG5002C! State the FTP folder of this device!',
                        msgType='error')


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
        # connect ethernet socket and FTP
        self.soc = socket(AF_INET, SOCK_STREAM)
        self.soc.settimeout(5)  # set the timeout to 5 seconds
        self.soc.connect((self.ip_address, self.port))
        self.input_buffer = int(2 * 1024)   # buffer length for received text

    def deactivation(self, e):
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
        Each constraint is a tuple of the form (min_value, max_value, stepsize).
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

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.tell('AWGC:RUN\n')

        return self.get_status()[0]

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        self.tell('AWGC:STOP\n')

        return self.get_status()[0]

    #FIXME: implement method: download_sequence

    #FIXME: implement method: send_file

    def load_sequence(self, seq_name, channel=None):
        """ Loads a sequence to the specified channel of the pulsing device.

        @param str seq_name: The name of the sequence to be loaded
        @param int channel: The channel for the sequence to be loaded into if
                            not already specified in the sequence itself

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA). Waveforms and single channel sequences can be
        assigned to each or both channels. Double channel sequences must be
        assigned to channel 1. The AWG's file system is case-sensitive.
        """

        path = self.ftp_path + self.get_sequence_directory()

        if channel is None or channel == 1:
            self.tell('SOUR1:FUNC:USER "{0}/{1}"\n'.format(path, seq_name))
        elif channel == 2:
            self.tell('SOUR2:FUNC:USER "{0}/{1}"\n'.format(path, seq_name))
        else:
            self.logMsg('Channel number was expected to be 1 or 2 but a '
                        'parameter "{0}" was passed.'.format(channel),
                        msgType='error')
            return -1

        return 0

    def clear_channel(self, channel=None):
        """ Clears the loaded waveform from the specified channel.

        @param int channel: The channel to be cleared. If no channel is passed
                            all the channels will be cleared.

        @return int: error code (0:OK, -1:error)

        Delete all waveforms and sequences from Hardware memory and clear the
        visual display.
        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        self.logMsg('Right now there is no possibility in clearing specific '
                    'channels in the AWG5000 Series. Therefore this command '
                    'will clear all the channels at once.',
                    msgType='warning')

        # if channel is None:
        self.tell('WLIST:WAVEFORM:DELETE ALL\n')
        return


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

        if message==2:
            return (1, status_dic)
        elif message ==1:
            return (2, status_dic)
        else:
            return (message, status_dic)

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware

        @param float sample_rate: The sample rate to be set (in Hz)

        @return foat: the sample rate returned from the device (-1:error)
        """

        self.tell('SOURCE1:FREQUENCY {0:.4G}MHz\n'.format(sample_rate/1e6))

        return self.get_sample_rate()


    def get_sample_rate(self):
        """ Set the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)
        """

        self.sample_rate = float(self.ask('SOURCE1:FREQUENCY?\n'))
        return self.sample_rate

    def set_amplitude(self, channel, amplitude):
        """ Set the output amplitude of the pulse generator hardware.

        @param int channel: The channel to be reconfigured
        @param float amplitude: The peak-to-peak amplitude the channel should
                                be set to (in V)

        @return int: error code (0:OK, -1:error)

        Unused for purely digital hardware without logic level setting
        capability (DTG, FPGA, etc.).
        """

        # TODO: Actually change the amplitude
        self.amplitude = amplitude
        return 0

    def get_amplitude(self, channel):
        """ Get the output amplitude of the pulse generator hardware.

        @param int channel: The channel to be checked

        @return float: The peak-to-peak amplitude the channel is set to (in V)

        Unused for purely digital hardware without logic level setting
        capability (FPGA, etc.).
        """
        # TODO: Actually ask for the amplitude
        return self.amplitude

    def set_active_channels(self, d_ch=2, a_ch=0):
        """ Set the active channels for the pulse generator hardware.

        @param int d_ch: The number of digital channels
        @param int a_ch: optional, the number of analogue channels

        @return int: error code (0:OK, -1:error)

        AWG5000 Series instruments support only 14-bit resolution. Therefore
        this command will have no effect for these instruments.
        """

        self.logMsg('Digital Channel of the AWG5000 series will always be '
                    'active. This configuration cannot be changed.',
                    msgType='status')

        if a_ch == 2:
            self.tell('OUTPUT2:STATE ON\n')
            active_a_ch = self.get_active_channels()[1]

        elif a_ch ==1:
            self.tell('OUTPUT1:STATE ON\n')
            self.tell('OUTPUT2:STATE OFF\n')
            active_a_ch = self.get_active_channels()[1]
        else:
            self.tell('OUTPUT1:STATE OFF\n')

        if active_a_ch == a_ch:
            return 0
        else:
            self.logMsg('Activation of the desired analogue channels not '
                        'possible!\nMaybe no valid waveform(s) is loaded into '
                        'the channels, or the waveform for the second channel '
                        'is not valid (due to a different length).\n'
                        'Correct that!', msgType='error')
            return -1


    def get_active_channels(self):
        """ Get the active channels of the pulse generator hardware.

        @return (int, int): number of active channels (analogue, digital)
        """

        analogue_channels = int(self.ask('OUTPUT1:STATE?\n')) + \
                            int(self.ask('OUTPUT2:STATE?\n'))

        # For the AWG5000 series, the resolution of the DAC for the analogue
        # channel is fixed to 14bit. Therefore the digital channels are always
        # active and cannot be deactivated, by setting the DAC by 1bit per
        # channel higher. The following construction will give always 2 since
        # 30-14-14 =2:
        digital_channels =30 - int(self.ask('SOURCE1:DAC:RESOLUTION?\n')) -\
                               int(self.ask('SOURCE2:DAC:RESOLUTION?\n'))

        return (analogue_channels, digital_channels)

    def get_sequence_names(self):
        """ Retrieve the names of all downloaded sequences on the device.

        @return list: List of sequence name strings

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """

        with FTP(self.ip_address) as ftp:
            ftp.login() # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.sequence_directory)

            # get only the files from the dir and skip possible directories
            log =[]
            file_list = []
            ftp.retrlines('LIST', callback=log.append)
            for line in log:
                if not '<DIR>' in line:
                    file_list.append(line.rsplit(None, 1)[1])
        return file_list

    def delete_sequence(self, seq_name):
        """ Delete a sequence with the passed seq_name from the device memory.

        @param str seq_name: The full name of the file to be deleted.
                             Optionally a list of file names can be passed.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """
        if not isinstance(seq_name, list):
            seq_name = [seq_name]

        file_list = self.get_sequence_names()

        with FTP(self.ip_address) as ftp:
            ftp.login() # login as default user anonymous, passwd anonymous@
            ftp.cwd(self.sequence_directory)

            for entry in seq_name:
                if entry in file_list:
                    ftp.delete(entry)

        return 0

    def set_sequence_directory(self, dir_path):
        """ Change the directory where the sequences are stored on the device.

        @param string dir_path: The target directory

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
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

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)
        @return int: error code (0:OK, -1:error)

        Unused for pulse generator hardware other than an AWG. The AWG 5000
        Series does not have an interleave mode and this method exists only for
        compability reasons.
        """
        self.logMsg('Interleave mode not available for the AWG 5000 Series!\n'
                    'Method call will be ignored.', msgType='warning')
        return 0

    def get_interleave(self):
        """ Check whether Interleave is on in AWG.
        Unused for pulse generator hardware other than an AWG. The AWG 5000
        Series does not have an interleave mode and this method exists only for
        compability reasons.

        @return bool: will be always False since no interleave functionality
        """

        return False

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
        time.sleep(0.3) # you need to wait until AWG generating an answer.
                        # This number was determined experimentally.
        try:
            message = self.soc.recv(self.input_buffer)  # receive an answer
            message = message.decode('UTF-8')   # decode bytes into a python str
        except OSError:
            self.logMsg('Most propably timeout was reached during querying '
                        'the AWG5000 Series device with the question:\n'
                        '{0}\n'
                        'The question text must be wrong.'.format(question),
                        msgType='error')
            message = str(-1)

        message = message.replace('\n','')  # cut away the characters\r and \n.
        message = message.replace('\r','')

        return message

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
        if a_ch ==1:
            self.tell('OUTPUT1:FILTER:LPASS:FREQUENCY {0:f}MHz\n'.format(cutoff_freq/1e6) )
        elif a_ch ==2:
            self.tell('OUTPUT2:FILTER:LPASS:FREQUENCY {0:f}MHz\n'.format(cutoff_freq/1e6) )

    def set_jump_timing(self, synchronous = False):
        """Sets control of the jump timing in the AWG.

        @param bool synchronous: if True the jump timing will be set to
                                 synchornous, otherwise the jump timing will be
                                 set to asynchronous.

        If the Jump timing is set to asynchornous the jump occurs as quickly as
        possible after an event occurs (e.g. event jump tigger), if set to
        synchornous the jump is made after the current waveform is output. The
        default value is asynchornous.
        """
        if(synchronous):
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

        look_up = {'C' : 'CONT',
                   'T' : 'TRIG',
                   'G' : 'GAT' ,
                   'E' : 'ENH' ,
                   'S' : 'SEQ'
                  }
        self.tell('AWGC:RMOD %s\n' % look_up[mode.upper()])


    def get_sequencer_mode(self,output_as_int=False):
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