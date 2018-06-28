# -*- coding: utf-8 -*-

"""
This file contains the Qudi Hardware file for the PulseBlaser ESR Pro.

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

import ctypes
import platform
import os
import numpy as np

from interface.switch_interface import SwitchInterface
from interface.pulser_interface import PulserInterface
from core.module import Base, ConfigOption
from core.util.modules import get_main_dir
from core.util.mutex import Mutex


class PulseBlasterESRPRO(Base, SwitchInterface):

#class PulseBlasterESRPRO(Base, PulserInterface):
    """ UNSTABLE: ALEX

    Hardware class to control the PulseBlasterESR-PRO card from SpinCore.

    This file is compatible with the PCI version SP18A of the PulseBlasterESR.
    The wrapped commands based on the 'spinapi.h' header file and can be looked
    up in the SpinAPI Documentation (Version 2013-09-25) on the website:

    http://www.spincore.com/support/spinapi/reference/production/2013-09-25/index.html

    or for an other version (not recommended):
    http://www.spincore.com/support/spinapi/reference/production/2010-07-14/index.html

    The SpinCore programming library spinapi.DLL is written in C and its data
    types correspond to standard C/C++ data types as follows:

            char                    8 bit, byte (or characters in ASCII)
            short int               16 bit signed integer
            unsigned short int      16 bit unsigned integer
            int                     32 bit signed integer
            long int                32 bit signed integer
            unsigned int            32 bit unsigned integer
            unsigned long int       32 bit unsigned integer
            float                   32 bit floating point number
            double                  64 bit floating point number

    Example config:

        pulseblaster:
            module.Class: 'spincore.pulse_blaster_esrpro.PulseBlasterESRPRO'
            #library_file: 'spinapi64.dll' # optional, name of the library file or even whole path to the file

    Dummy config for the pulser interface:

        dummypulser:
            module.Class: 'pulser_dummy.PulserDummy'
    """
    _modclass = 'PulseBlasterESRPRO'
    _modtype = 'hardware'

    _library_path = ConfigOption('library_path', default='', missing='info')

    # the library pointer is saved here
    _dll = None

    PULSE_PROGRAM = 0

    # Defines for different pb_inst instruction types (in _write_pulse called
    # inst_data):
    CONTINUE = 0
    STOP = 1
    LOOP = 2
    END_LOOP = 3
    JSR = 4
    RTS = 5
    BRANCH = 6
    LONG_DELAY = 7
    WAIT = 8
    RTI = 9

    # ON = 6<<21 # not working, even though it is according to docu, strange
    ON = 0xE00000
    ALL_FLAGS_ON = 0x1FFFFF
    ONE_PERIOD = 0x200000
    TWO_PERIOD = 0x400000
    THREE_PERIOD = 0x600000
    FOUR_PERIOD = 0x800000
    FIVE_PERIOD = 0xA00000
    SIX_PERIOD = 0xC00000

    GRAN_MIN = 2   # minimal possible granularity in time, in ns.
    FREQ_MAX = int(1/GRAN_MIN * 1000) # Maximal output frequency in MHz.


    # For switch interface:
    switch_states = {'d_ch1': False, 'd_ch2': False, 'd_ch3': False,
                     'd_ch4': False, 'd_ch5': False, 'd_ch6': False,
                     'd_ch7': False, 'd_ch8': False, 'd_ch9': False,
                     'd_ch10': False, 'd_ch11': False, 'd_ch12': False,
                     'd_ch13': False, 'd_ch14': False, 'd_ch15': False,
                     'd_ch16': False, 'd_ch17': False, 'd_ch18': False,
                     'd_ch19': False, 'd_ch20': False, 'd_ch21': False}


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialization performed during activation of the module. """


        # check at first the config option, whether a correct library was found
        lib_path = ctypes.util.find_library(self._library_path)

        if lib_path is None:
            # Check the platform architecture:
            arch = platform.architecture()
            if arch == ('32bit', 'WindowsPE'):
                libname = 'spinapi.dll'
            elif arch == ('64bit', 'WindowsPE'):
                libname = 'spinapi64.dll'
            elif arch == ('32bit', 'ELF'):
                libname = 'libspinapi.so'
            elif arch == ('64bit', 'ELF'):
                libname ='libspinapi64.so'

            # In Windows load the spinapi library file spinapi.dll from the
            # folder <Windows>/System32/. For Unix systems, the shared object
            # (= *.so) file muss be within the same directory, where the file
            # is situated.

            lib_path = ctypes.util.find_library(libname)

        if lib_path is None:
            self.log.error('No library could be loaded for the PulseBlaster '
                           'card. Please specify the correct path to it in the '
                           'config variable "library_file". If might also be '
                           'that you need to install the PulseBlaster library '
                           'from SpinCore.')
            return -1

        self._dll = ctypes.cdll.LoadLibrary(lib_path)
        self.log.debug('SpinCore library loaded from: {0}'.format(lib_path))
        self.open_connection()

    def on_deactivate(self):
        """ Deinitialization performed during deactivation of the module. """

        self.stop()
        self.close_connection()

    # =========================================================================
    # Below all the low level routines which are wrapped with ctypes which
    # are talking directly to the hardware via the SpinAPI dll library.
    # =========================================================================

    def check(self, func_val):
        """ Check routine for the received error codes.

        @param int func_val: return error code of the called function.

        @return int: pass the error code further so that other functions have
                     the possibility to use it.

        Each called function in the dll has an 32-bit return integer, which
        indicates, whether the function was called and finished successfully
        (then func_val = 0) or if any error has occurred (func_val < 0).
        """

        if func_val < 0:

            err_str = self.get_error_string()

            self.log.error('Error in PulseBlaster with errorcode {0}:\n'
                           '{1}'.format(func_val, err_str))
        return func_val


    def get_error_string(self):
        """ Return the most recent error string.

        @return str: A string describing the last error is returned. A string
                     containing "No Error" is returned if the last function call
                     was successful.

        Anytime a function (such as pb_init(), pb_start_programming(), etc.)
        encounters an error, this function will return a description of what
        went wrong.
        """
        self._dll.pb_get_error.restype = ctypes.c_char_p

        # The output value of this function is as declared above a pointer
        # to an address where the received data is stored as characters
        # (8bit per char). Use the decode method to convert a char to a
        # string.
        return self._dll.pb_get_error().decode()

    def count_boards(self):
        """ Return the number of SpinCore boards present in your system.

        @return int: The number of boards present is returned. -1 is returned
                     on error, and spinerr is set to a description of the
                     error.
        """

        self._dll.pb_count_boards.restype = ctypes.c_int
        return self._dll.pb_count_boards()

    def select_board(self, board_num=0):
        """ Select the proper SpinCore card, if multiple are present.

        @param int board_num: Specifies which board to select. Counting starts
                              at 0.

        If multiple boards from SpinCore Technologies are present in your
        system, this function allows you to select which board to talk to. Once
        this function is called, all subsequent commands (such as pb_init(),
        pb_core_clock(), etc.) will be sent to the selected board. You may
        change which board is selected at any time.
        If you have only one board, it is not necessary to call this function.
        """

        # check whether the input is an integer
        if not isinstance(board_num, int):
            self.log.error('PulseBlaster cannot choose a board, since an '
                           'integer type was expected, but the following value '
                           'was passed:\n{0}'.format(board_num))
        self.check(self._dll.pb_select_board(board_num))

    def get_version(self):
        """Get the version date of this library.

        @return string: A string indicating the version of this library is
                        returned. The version is a string in the form YYYYMMDD.
        """
        self._dll.spinpts_get_version.restype = ctypes.c_char_p
        # .decode converts char into string:
        return self._dll.spinpts_get_version().decode()

    def get_firmware_id(self):
        """Gets the current version of the SpinPTS API being used.

        @return int: Returns the firmware id containing the version string.
        """
        self._dll.pb_get_firmware_id.restype = ctypes.c_uint

        firmware_id = self._dll.pb_get_firmware_id()

        if firmware_id == 0:
            self.log.info('Retrieving the Firmware ID is not a feature of this '
                          'board')

        return firmware_id

    def start(self):
        """ Send a software trigger to the board.

        @return int: A negative number is returned on failure, and spinerr is
                     set to a description of the error. 0 is returned on
                     success.

        This will start execution of a pulse program.It will also trigger a
        program which is currently paused due to a WAIT instruction. Triggering
        can also be accomplished through hardware, please see your board's
        manual for details on how to accomplish this.
        """
        self._dll.pb_start.restype = ctypes.c_int
        return self.check(self._dll.pb_start())

    def stop(self):
        """Stops output of board.

        @return int: A negative number is returned on failure, and spinerr is
                     set to a description of the error. 0 is returned on
                     success.

        Analog output will return to ground, and TTL outputs will either remain
        in the same state they were in when the reset command was received or
        return to ground. This also resets the PulseBlaster so that the
        PulseBlaster Core can be run again using pb_start() or a hardware
        trigger.
        """

        self._dll.pb_stop.restype = ctypes.c_int
        return self.check(self._dll.pb_stop())

    def open_connection(self):
        """Initializes the board.

        @return int: A negative number is returned on failure, and spinerr is
                     set to a description of the error. 0 is returned on
                     success.

        This must be called before any other functions are used which
        communicate with the board. If you have multiple boards installed in
        your system, pb_select_board() may be called first to select which
        board to initialize.
        """
        self.log.debug('Open connection to SpinCore library.')
        return self.check(self._dll.pb_init())

    def close_connection(self):
        """End communication with the board.

        @return: A negative number is returned on failure, and spinerr is set
                 to a description of the error. 0 is returned on success.

        This is generally called as the last line in a program. Once this is
        called, no further communication can take place with the board unless
        the board is reinitialized with pb_init(). However, any pulse program
        that is loaded and running at the time of calling this function will
        continue to run indefinitely.
        """
        self.log.debug('Close connection to SpinCore library.')
        return self.check(self._dll.pb_close())

    def start_programming(self):
        """ Tell the board to start programming one of the onboard devices.

        @ return int: A negative number is returned on failure, and spinerr is
                      set to a description of the error. 0 is returned on
                      success.

        For all the devices, the method of programming follows the following
        form:
            a call to pb_start_programming(), a call to one or more functions
            which transfer the actual data, and a call to
            pb_stop_programming(). Only one device can be programmed at a time.

        There are actually several programming methods possible, but since this
        card has only pulsing outputs, without DDS (Direct Digital Synthesis)
        or RadioProcessor output, the programming will be set by default to
        the PULSE_PROGRAM = 0.
        """

        return self.check(self._dll.pb_start_programming(self.PULSE_PROGRAM))

    def stop_programming(self):
        """ Finishes the programming for a specific onboard devices.

        @return int: A negative number is returned on failure, and spinerr is
                     set to a description of the error. 0 is returned on
                     success.
        """
        return self.check(self._dll.pb_stop_programming())

    def set_core_clock(self, clock_freq):
        """Tell the library what clock frequency the board uses.

        @param int clock_freq: Frequency of the clock in MHz.

        This should be called at the beginning of each program, right after you
        initialize the board with pb_init(). Note that this does not actually
        set the clock frequency, it simply tells the driver what frequency the
        board is using, since this cannot (currently) be autodetected.
        Also note that this frequency refers to the speed at which the
        PulseBlaster core itself runs. On many boards, this is different than
        the value printed on the oscillator. On RadioProcessor devices, the A/D
        converter and the PulseBlaster core operate at the same clock
        frequency.
        """

        # it seems that the spin api has no return value for that funtion, i.e.
        # it cannot be detected whether the value was properly set. There is
        # also no get_core_clock method available. Strange.
        self._dll.pb_core_clock.restype = ctypes.c_void_p
        self._dll.pb_core_clock(ctypes.c_double(clock_freq))

    def _write_pulse(self, flags, inst, inst_data, length):
        """Instruction programming function for boards without a DDS.

        @param unsigned int flags: Set every bit to one for each flag you want
                                   to set high. If 8 channels are addressable
                                   then their bit representation would be
                                       0b00000000   (in python).
                                   where the most right corresponds to ch1 and
                                   the most left to ch8. If you want to
                                   set channel 1,2,3 and 7 to be on, then the
                                   bit word must be
                                       0b01000111
        @param int inst: Specify the instruction you want. Valid instructions
                         are:
                         Opcode#	Instruction	  Meaning of inst_data field
                             0      CONTINUE          Continue
                             1      STOP              Stop
                             2      LOOP              Number of desired loops
                             3      END_LOOP          Address of instruction
                                                      originating loop
                             4      JSR               Address of first
                                                      instruction in subroutine
                             5      RTS               ?
                             6      BRANCH            Address of instruction to
                                                      branch to
                             7      LONG_DELAY        Number of desired
                                                      repetitions
                             8      WAIT              wait until something

                        That means if you choose an operation code, which has
                        a meaning in the inst_data (like e.g. 2 = LOOP) you can
                        specify in the inst_data how the loop should look like,
                        i.e. how many loops have to be done.

        @param int inst_data: Instruction specific data. Internally this is a
                              20 bit unsigned number, so the largest value that
                              can be passed is 2^20-1 (the largest value
                              possible for a 20 bit number). See above table
                              to find out what this means for each instruction.
                              Pass None if the inst_data should be ignored.
        @param double length: Length of this instruction in nanoseconds.

        @return int: a positive number represents the address of the created
                     instruction. This can be used as the branch address for any
                     branch instructions. Other instructions should yield 0 as
                     output. A negative number is returned on failure,
                     and spinerr is set to a description of the error.

        (DDS = Direct Digital Synthesis). The old version of this command was
        'pb_set_clock', which is still valid, but should not be used.

        This function is used to write essentially 'one line' to the pulse
        generator. This 'one line' tells the device what to output for each
        channel during a given time (here called 'length').
        """

        length = ctypes.c_double(length)

        return self.check(self._dll.pb_inst_pbonly(flags, inst, inst_data, length))


    def get_status(self):
        """Read status from the board.

        @return int: Word that indicates the state of the current board like
                     the representation 2^(<bit>), whereas the value of bit is
                        bit 0 - Stopped     (2^0 = 1)
                        bit 1 - Reset       (2^1 = 2)
                        bit 2 - Running     (2^2 = 4)
                        bit 3 - Waiting     (2^3 = 8)
                        bit 4 - Scanning (RadioProcessor boards only, 2^4 = 16)

        Not all boards support this, see your manual. Each bit of the returned
        integer indicates whether the board is in that state. Bit 0 is the
        least significant bit.

        *Note on Reset Bit: The Reset Bit will be true as soon as the board is
                            initialized. It will remain true until a hardware
                            or software trigger occurs, at which point it will
                            stay false until the board is reset again.

        *Note on Activation Levels: The activation level of each bit depends on
                                    the board, please see your product's
                                    manual for details.

        Bits 5-31 are reserved for future use. It should not be assumed that
        these will be set to 0.

        The output is converted to integer representation directly, and not
        bit representation, as it is mentioned in the spinapi documentation.
        """

        self._dll.pb_read_status.restype = ctypes.c_uint32
        #FIXME the usage of a state maschine would be a good idea

        return self._dll.pb_read_status()

    # =========================================================================
    # Below all the higher level routines are situated which use the
    # wrapped routines as a basis to perform the desired task.
    # =========================================================================

    def write_pulse_form(self, sequence_list, clock_freq=500.0, loop=True):
        """ The higher level function, which creates the actual sequences.

        @param list sequence_list: a list with dictionaries. The dictionaries
                                   have the elements 'active_channels' and
                                   'length. The 'active_channels' is
                                   a numpy list, which contains the channel
                                   number, which should be switched on. The
                                   channel numbers start with 0. E.g.

                                   [{'active_channels':[0], 'length': 10000},
                                    {'active_channels':[], 'length': 20000}]
                                    which will switch on

        @param float clock_freq: optional, the clock frequency in MHz, which
                                 should be set to output the signals in that
                                 rate.
        @param bool loop: optional, set if sequence should be looped (so that it
                          runs continuously) or not, default it True.

        @return int: The number of created pulses with the given sequence.

        This method should called with the general sequence_list to program
        the PulseBlaster.
        """

        if clock_freq > self.FREQ_MAX:
            self.log.warning('The maximal value for the clock frequency for '
                             'the PulseBlaster card is {0}MHz, but a value of '
                             '{1} was passed. The clock is set to maximal '
                             'sampling '
                             'frequency.'.format(self.FREQ_MAX, clock_freq))
            clock_freq = 500

        # Catch the case where only one entry in the sequence is present:
        if len(sequence_list) == 1:
            return self.activate_channels(ch_list=sequence_list[0]['active_channels'],
                                          length=sequence_list[0]['length'],
                                          clock_freq=clock_freq,
                                          immediate_start=False)

        self.set_core_clock(clock_freq)
        self.start_programming()
        start_pulse = self._convert_pulse_to_inst(
                            sequence_list[0]['active_channels'],
                            sequence_list[0]['length']
                            )


        # go through each pulse in the sequence and write it to the
        # PulseBlaster.
        for pulse in sequence_list[1:-1]:
            num  = self._convert_pulse_to_inst(pulse['active_channels'],
                                               pulse['length'])
            if num > 4094: # =(2**12 -2)
                self.log.error('Error in PulseCreation: Command {0} exceeds '
                               'the maximal number of commands'.format(num))

        active_channels = sequence_list[-1]['active_channels']
        length = sequence_list[-1]['length']

        # Take the last pulse and extend it by either tell the device to stop
        # after this round and do no infinite looping or branching from out to
        # connect the end with the beginning of the pulse.

        # with the branch or the stop command
        if loop == False:
            bitmask = self._convert_to_bitmask(active_channels)
            num = self._write_pulse(self.ON|bitmask,
                                    inst=self.STOP,
                                    inst_data=None,
                                    length=length)
        else:
            num = self._write_pulse(flags=self.ON|0,
                                    inst=self.BRANCH,
                                    inst_data=start_pulse,
                                    length=length)
        if num > 4094: # =(2**12 -2)
                self.log.error('Error in PulseCreation: Command {0} exceeds '
                               'the maximal number of commands'.format(num))

        self.stop_programming()

        return num


    def _convert_pulse_to_inst(self, active_channels, length):
        """ Convert a pulse of one row to a instructions for the PulseBlaster.

        @param np.array active_channels: the list of active channels like
                                         e.g. [0,4,7]. Note that the channels
                                         start from 0.
        @param float length: length of the current row in ns.

        @return int: The address number num of the created instruction.

        Helper method for write_pulse_form.
        """

        # return bitrepresentation of active channels:
        channel_bitmask = self._convert_to_bitmask(active_channels)

        # Check, whether the length fulfills the minimal granularity (= every
        # pulse has to be dividable by 2ns, which corresponds to a 500MHz
        # output sampling.)
        residual = length % self.GRAN_MIN
        if residual != 0:
            self.log.warning('The length of the pulse does not fulfill the '
                             'granularity of {0}ns. The length is rounded to a '
                             'number, dividable by the granularity! {1}ns were '
                             'dropped.'.format(self.GRAN_MIN, residual))

        length = int(np.round(length/self.GRAN_MIN)) * self.GRAN_MIN

        if length <= 256:
                          # pulses are written in 8 bit words. Save memory if
                          # the length of the pulse is smaller than 256
            num = self._write_pulse(self.ON|channel_bitmask,
                                    inst=self.CONTINUE,
                                    inst_data=None,
                                    length=length)

        elif length > 256:
            # reducing the length of the pulses by repeating them.
            # Try to factorize successively, in order to reducing the total
            # length of the pulse form. Put the subtracted amount into an
            # additional short command if necessary.

            remaining_time = length
            i = 4
            while True:
                value, factor = self._factor(length)

                if value > 4:
                    if factor == 1:
                        num = self._write_pulse(self.ON|channel_bitmask,
                                                inst=self.CONTINUE,
                                                inst_data=None,
                                                length=value)

                    elif factor < 1048576: # = (2**20 + 1)
                        # check if you do not exceed the memory limit. Then
                        # you can use the factorized approach to loop your
                        # pulse forms. Therefore apply a LONG_DELAY instruction
                        num = self._write_pulse(self.ON|channel_bitmask,
                                                inst=self.LONG_DELAY,
                                                inst_data=int(factor),
                                                length=value)
                    else:
                        self.log.error('Error in PulseCreation: Loop counts '
                                       'are {0} in LONG_DELAY instruction and '
                                       'exceedes the maximal possible value of '
                                       '2^20+1 = 1048576.\n'
                                       'Repeat PulseCreation with different '
                                       'parameters!'.format(factor))

                    if i > 4:
                        self._write_pulse(self.ON|channel_bitmask,
                                          inst=self.CONTINUE,
                                          inst_data=None,
                                          length=i)

                    break
                i = i+1
                length = remaining_time - i

        return num

    def _convert_to_bitmask(self, active_channels):
        """ Convert a list of channels into a bitmask.

        @param np.array active_channels: the list of active channels like  e.g.
                                            [0,4,7].
                                         Note that the channels start from 0.

        @return int: The channel-list is converted into a bitmask (an sequence
                     of 1 and 0). The returned integer corresponds to such a
                     bitmask.

        Note that you can get a binary representation of an integer in python
        if you use the command bin(<integer-value>). All higher unneeded digits
        will be dropped, i.e. 0b00100 is turned into 0b100. Examples are
            bin(0) =    0b0
            bin(1) =    0b1
            bin(8) = 0b1000
        Each bit value (read from right to left) corresponds to the fact that a
        channel is on or off. I.e. if you have
            0b001011
        then it would mean that only channel 0, 1 and 3 are switched to on, the
        others are off.

        Helper method for write_pulse_form.
        """
        bits = 0     # that corresponds to: 0b0
        for channel in active_channels:
            # go through each list element and create the digital word out of
            # 0 and 1 that represents the channel configuration. In order to do
            # that a bitwise shift to the left (<< operator) is performed and
            # the current channel configuration is compared with a bitwise OR
            # to check whether the bit was already set. E.g.:
            #   0b1001 | 0b0110: compare element-wise:
            #           1 | 0 => 1
            #           0 | 1 => 1
            #           0 | 1 => 1
            #           1 | 1 => 1
            #                   => 0b1111
            bits = bits | (1 << channel)
        return bits

    def _factor(self, number):
        """ Try to write a number higher than 256 as a product of two numbers.

        @param int number: this number you want to factorize

        @return tuple(2): The first number divides the input value without any
                          residual, the second number tell you how often you
                          have to multiply the first number to get the input
                          value.

        Starting from 256 you try to find a number which will divide the input
        value such that no residue remains. If there is no number, then you
        have found a prime number that is bigger than the number 256. If you
        are below 256, there is no need in factorization and the number is
        passed as it is.
        One of this number must be in the range 1-256 and the other is
        calculated. In the worst case scenario, there are no number within the
        range [1,256] which factorizes the input value.

        """
        div = 256
        while div > 4:
            if number % div == 0:
                return div, number/div
            div -= 1
        return 1, number

    # =========================================================================
    # A bit higher methods for using the card as switch
    # =========================================================================

    def activate_channels(self, ch_list, length=100, clock_freq=500.0,
                          immediate_start=True):
        """ Set specific channels to high, all others to low.

        @param list ch_list: the list of active channels like  e.g. [0,4,7].
                             Note that the channels start from 0. Note, an empty
                             list will set all channels to low.
        @param int length: optional, length of the activated channel output in
                           ns. Since there will be no switching of channels
                           within this mode, the length of the pulsing time can
                           be chosen arbitrary. Here 100ns is the default value.
                           A larger number does not make a lot of sense.
        @param float clock_freq: optional, clock frequency for the board in MHz.
                                 default value is 500.0
        @param bool immediate_start: optional, indicate whether output should
                                     directly be switch on, default is True.

        @return int: the number of created pulse instructions, normally it
                     should output just the number 1.

        This is a high level command mostly used not for pulsing but just rather
        for switching something on or off.

        """

        clock_freq = 500    # in MHz, for just switching the channels on or off,
                            # the clock will not play a role, therefore it is
                            # not a config option in this method.

        self.set_core_clock(clock_freq)
        self.start_programming()
        flags = self.ON | self._convert_to_bitmask(ch_list)
        retval = self._write_pulse(flags=flags, inst=self.STOP, inst_data=0, length=length)
        self.stop_programming()

        if immediate_start:
            self.start()

        return retval


    # =========================================================================
    # Below the Switch interface implementation.
    # =========================================================================

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.

        @return int: number of swiches on this hardware
        """
        return len(self.switch_states)

    def getSwitchState(self, switchNumber):
        """ Gives state of switch.

        @param int switchNumber: number of switch, numbering starts with 0

        @return bool: True if on, False if off, None on error
        """

        return self.switch_states['d_ch{0}'.format(switchNumber+1)]

    def getCalibration(self, switchNumber, state):
        """ Get calibration parameter for switch.

        @param int switchNumber: number of switch for which to get calibration
                                 parameter
        @param str switchState: state ['On', 'Off'] for which to get
                                calibration parameter

        @return str: calibration parameter for switch and state.
        """

        # There is no possibility to calibrate the voltage values for the
        # Pulse Blaster, either it is on at 5.0V or off at 0.0V.
        possible_states = {'On': 5.0, 'Off': 0.0}
        return possible_states[state]

    def setCalibration(self, switchNumber, state, value):
        """ Set calibration parameter for switch.

          @param int switchNumber: number of switch for which to get calibration
                                   parameter
          @param str switchState: state ['On', 'Off'] for which to get
                                  calibration parameter
          @param int value: calibration parameter to be set.

          @return bool: True if succeeds, False otherwise
        """
        self.log.warning('Not possible to set a Switch Voltage for '
                         'PulseBlaster Devices. Command ignored.')
        return True

    def switchOn(self, switchNumber):
        """ Switch on.

        @param int switchNumber: number of switch to be switched, number starts
                                 from zero.

        @return bool: True if succeeds, False otherwise
        """

        self.switch_states['d_ch{0}'.format(switchNumber+1)] = True

        ch_list = [int(entry.replace('d_ch',''))-1 for entry in self.switch_states if self.switch_states[entry]]

        self.activate_channels(ch_list=ch_list, length=100, clock_freq=500.0,
                               immediate_start=True)

        return self.switch_states['d_ch{0}'.format(switchNumber+1)]


    def switchOff(self, switchNumber):
        """ Switch off.

        @param int switchNumber: number of switch to be switched

        @return bool: True if suceeds, False otherwise
        """

        self.switch_states['d_ch{0}'.format(switchNumber+1)] = False

        ch_list = [int(entry.replace('d_ch',''))-1 for entry in self.switch_states if self.switch_states[entry]]

        self.activate_channels(ch_list=ch_list, length=100, clock_freq=500.0,
                               immediate_start=True)

        return self.switch_states['d_ch{0}'.format(switchNumber+1)]

    def getSwitchTime(self, switchNumber):
        """ Give switching time for switch.

        @param int switchNumber: number of switch

        @return float: time needed for switch state change
        """

        # switch time is limited to communication speed to the device,
        # therefore set the average communication time of 1ms as the limitation.
        return 0.001




    # =========================================================================
    # Below the pulser interface implementation.
    # =========================================================================
