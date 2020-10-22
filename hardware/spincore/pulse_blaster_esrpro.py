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
import numpy as np
from collections import OrderedDict

from interface.switch_interface import SwitchInterface
from interface.pulser_interface import PulserInterface
from interface.pulser_interface import PulserConstraints

from core.module import Base
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from core.util.network import netobtain


class PulseBlasterESRPRO(Base, SwitchInterface, PulserInterface):
    """ Hardware class to control the PulseBlasterESR-PRO card from SpinCore.

    This file is compatible with the PCI version SP18A of the PulseBlasterESR.
    The wrapped commands based on the 'spinapi.h' and the 'pulseblaster.h'
    header file and can be looked up in the SpinAPI Documentation
    (Version 2013-09-25) on the website:

    http://www.spincore.com/support/spinapi/reference/production/2013-09-25/index.html

    The recommended version for the manual is the PDF file from SpinCore:
        http://www.spincore.com/CD/PulseBlasterESR/SP4/PBESR-Pro_Manual.pdf

    Another manual describes the functions a bit better:
        http://spincore.com/CD/PulseBlasterESR/SP1/PBESR_Manual.pdf

    The SpinCore programming library (spinapi.dll, spinapi64.dll, libspinapi.so 
    or libspinapi64.so) is written in C and its data types correspond to 
    standard C/C++ data types as follows:

            char                    8 bit, byte (or characters in ASCII)
            short int               16 bit signed integer
            unsigned short int      16 bit unsigned integer
            int                     32 bit signed integer
            long int                32 bit signed integer
            unsigned int            32 bit unsigned integer
            unsigned long int       32 bit unsigned integer
            float                   32 bit floating point number
            double                  64 bit floating point number

    Example config for copy-paste:

        pulseblaster:
            module.Class: 'spincore.pulse_blaster_esrpro.PulseBlasterESRPRO'
            clock_frequency: 500e6 # in Hz
            min_instr_len: 5    # number of clock cycles for minimal instruction
            debug_mode: False   # optional, to set the debug mode on or off.
            use_smart_pulse_creation: False # optinal, default is false, try to
                                            # optimize the memory used on the device.
            #library_file: 'spinapi64.dll'  # optional, name of the library file
                                            # or  whole path to the file

    Remark to the config values:
        library_file: if the library does not lay in the default directory of
                      your OS (for windows it is 'C:/Windows/System32'), then
                      you need to specify the path.
        clock_frequency: the Spincore board contains a oscillator crystal, which
                         is attached to it and whose value cannot be determined
                         by the hardware. This number should be specified on the
                         board. The PulseBlasterESR-PRO can have the values
                         [300e6, 400e6, 500e6]. Select the correct one!
        min_instr_len:  number of clock cycles for minimal instruction, default
                        is 5. Normally it is 5 but for some boards it is 6 or
                        for old boards it might be even 7. This corresponds to
                        a minimal instruction length of
                            (1/clock_frequency)*min_instr_len
        channel_delays: Specify the delay of some channels to correct it automatically
                         by this module. For example :
                          channel_delays:
                                '0': 200-9
                                '2': 500-9
                         tell the card the line 0 and 2 have a delay of 200 ns and 500 ns respectively
                         so that the pulse are emitted sooner relatively to other channels.
                         The first line is 0 and the last is 20.
    """

    _library_path = ConfigOption('library_path', default='', missing='info')

    # The clock freqency which is necessary for the board.
    _clock_freq = ConfigOption('clock_frequency', default=500e6, missing='warn')
    # in clock cycles:
    _min_instr_len = ConfigOption('min_instr_len', default=6, missing='warn')

    _debug_mode = ConfigOption('debug_mode', default=False)

    _use_smart_pulse_creation = ConfigOption('use_smart_pulse_creation', default=False)

    _channel_delays = ConfigOption('channel_delays', default=[])

    # the library pointer is saved here
    _lib = None

    PULSE_PROGRAM = 0

    # Defines for different pb_inst instruction types (in _write_pulse called
    # inst_data).
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

    # Special consideration of the ESR-PRO short pulse feature must be taken
    # when programming or operating this board. For signals of instruction time
    # greater than 10 ns, the short pulse feature must be disabled by setting
    # output bits 21-23 to HIGH at all times
    # ON = 0xE00000  # = 7<<21, in order to have '0b111000000000000000000000'

    # The Short Pulse feature utilizes the upper three bits of the instruction
    # flag output bits (bits 21 to 23) to control the number of clock cycles.

    # Flags for Spin API  | Bits 21-23  | Clock periods | Pulse length (ns) @ 500MHz
    #                       # 000       |       -       | Always low
    ONE_PERIOD = 0x200000   # 001       |       1       | 2
    TWO_PERIOD = 0x400000   # 010       |       2       | 4
    THREE_PERIOD = 0x600000 # 011       |       3       | 6
    FOUR_PERIOD = 0x800000  # 100       |       4       | 8
    FIVE_PERIOD = 0xA00000  # 101       |       5       | 10
    ON = 0xE00000           # 111       |      > 5      | No short pulse

    # The length of the short pulse cannot be shorter than 10ns, however, with 
    # the instruction flags above, it can be specified how many clock cycles are
    # set to HIGH within the minimal instruction length from the beginning. 
    # All other clock cycles of the 10ns pulse will be set to LOW.
    # Otherwise, if the length of the pulse is greater than 10ns the ON flag 
    # needs to be specified.
    #
    # This instruction might only be used for some old boards
    SIX_PERIOD = 0xC00000   # 110 => used for some old boards
    #
    # To understand the usage of those flags, please refer to the manual on
    # p. 28, Fig. 16 (for the manual version 2017/09/04).
    #
    # NOTE: The short pulse flags are not used in this file, but are implemented 
    #       for potential future use.

    # Useful Constants for Output Pattern and Control Word, max size is 24bits
    ALL_FLAGS_ON = 0x1FFFFF   # set bits 0-20 to 1
    ALL_FLAGS_OFF = 0x0

    STATUS_DICT = {1: 'Stopped',
                   2: 'Reset',
                   4: 'Running',
                   8: 'Waiting',
                   16: 'Scanning'}

    # For switch interface:
    switch_states = {'d_ch1': False, 'd_ch2': False, 'd_ch3': False,
                     'd_ch4': False, 'd_ch5': False, 'd_ch6': False,
                     'd_ch7': False, 'd_ch8': False, 'd_ch9': False,
                     'd_ch10': False, 'd_ch11': False, 'd_ch12': False,
                     'd_ch13': False, 'd_ch14': False, 'd_ch15': False,
                     'd_ch16': False, 'd_ch17': False, 'd_ch18': False,
                     'd_ch19': False, 'd_ch20': False, 'd_ch21': False}

    # Make a channel state dict, which indicates the current channel activation
    channel_states = switch_states.copy()


    #FIXME: implement a way to store already create waveforms
    # _current_pb_waveform_name = StatusVar(name='current_pb_waveform_name',
    #                                       default='')
    # _current_pb_waveform = StatusVar(name='current_pb_waveform',
    #                                  default={'active_channels':[],
    #                                           'length': self.LEN_MIN})

    # @_current_pb_waveform.representer
    # def _convert_current_waveform(self, waveform_bytearray):
    #     """ Specify how to handle waveform, so that it can be saved. """
    #     return np.frombuffer(waveform_bytearray, dtype='uint8')

    # @_current_pb_waveform.constructor
    # def _recover_current_waveform(self, waveform_nparray):
    #     """ Specify how to construct the waveform from saved file. """
    #     return bytearray(waveform_nparray.tobytes())


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialization performed during activation of the module. """

        # minimal possible granularity in time, in s.
        self.GRAN_MIN = 1/self._clock_freq
        # minimal possible length of a single pulse/instruction in s:
        self.LEN_MIN = self.GRAN_MIN*self._min_instr_len
        self.SAMPLE_RATE = self._clock_freq # sample frequency in Hz.

        # For pulser interface:
        self._current_pb_waveform_name = ''
        self._current_pb_waveform_theoretical = [{'active_channels': [], 'length': self.LEN_MIN}]
        self._current_pb_waveform = [{'active_channels': [], 'length': self.LEN_MIN}]


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

        self._lib = ctypes.cdll.LoadLibrary(lib_path)
        self.log.debug('SpinCore library loaded from: {0}'.format(lib_path))
        self.open_connection()

        # For waveform creation:
        self._currently_loaded_waveform = ''  # loaded and armed waveform name

        self._current_activation_config = list(self.get_constraints().activation_config['4_ch'])
        self._current_activation_config.sort()

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

            # Catch a very specific error code, which is not proviced by the 
            # documentation. The error text of this error value appears only in 
            # the debug mode. Return the required error message.
            if func_val == -91 and err_str == '':

                err_str = ('Instruction length is shorter then the minimal '
                           'allowed length! Dependant on your device, it '
                           'should be at least 5-7 clock cycles. Check the '
                           'manual for more information.')

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

        self._lib.pb_get_error.restype = ctypes.c_char_p

        # The output value of this function is as declared above a pointer
        # to an address where the received data is stored as characters
        # (8bit per char). Use the decode method to convert a char to a
        # string.
        return self._lib.pb_get_error().decode('utf8')

    def count_boards(self):
        """ Return the number of SpinCore boards present in your system.

        @return int: The number of boards present is returned. -1 is returned
                     on error, and spinerr is set to a description of the
                     error.
        """

        self._lib.pb_count_boards.restype = ctypes.c_int

        return self._lib.pb_count_boards()

    def select_board(self, board_num=0):
        """ Select the proper SpinCore card, if multiple are present.

        @param int board_num: Specifies which board to select. Counting starts
                              at 0.

        @return int: the selected board number or -1 for an error.

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
            return

        self.check(self._lib.pb_select_board(board_num))

    def set_debug_mode(self, value):
        """ Set the debug mode.

        @param bool value: State to set the debug mode to.

        @return: the current debug mode.
        """

        self._debug_mode = value
        self._lib.pb_set_debug(int(value))  # convert to 0=False or 1=True.
        return self._debug_mode

    def get_debug_mode(self):
        """ Retrieve whether debug mode is set.

        @return bool: the current debug mode
        """
        return self._debug_mode

    def get_version(self):
        """Get the version date of this library.

        @return string: A string indicating the version of this library is
                        returned. The version is a string in the form YYYYMMDD.
        """

        # .decode converts char into string:
        self._lib.pb_get_version.restype = ctypes.c_char_p
        return self._lib.pb_get_version().decode('utf-8')

    def get_firmware_id(self):
        """Gets the current version of the SpinPTS API being used.

        @return int: Returns the firmware id containing the version string.
        """
        self._lib.pb_get_firmware_id.restype = ctypes.c_uint

        firmware_id = self._lib.pb_get_firmware_id()

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
        return self.check(self._lib.pb_start())

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

        return self.check(self._lib.pb_stop())

    def reset_device(self):
        """ Stops the output of board and resets the PulseBlaster Core.

        @return int: A negative number is returned on failure, and spinerr is
                     set to a description of the error.
                     0 is returned on success.

        This also resets the PulseBlaster Core so that the board can be run
        again using self.start() or a hardware trigger.
        """

        return self.check(self._lib.pb_reset())

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
        ret_val = self.check(self._lib.pb_init())
        self._set_core_clock(self.SAMPLE_RATE)
        return ret_val

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
        return self.check(self._lib.pb_close())

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

        return self.check(self._lib.pb_start_programming(self.PULSE_PROGRAM))

    def stop_programming(self):
        """ Finishes the programming for a specific onboard devices.

        @return int: A negative number is returned on failure, and spinerr is
                     set to a description of the error. 0 is returned on
                     success.
        """

        return self.check(self._lib.pb_stop_programming())

    def _set_core_clock(self, clock_freq):
        """ Tell the library what clock frequency the board uses.

        @param float clock_freq: Frequency of the clock in Hz.

        This should be called at the beginning of each program, right after you
        initialize the board with pb_init().

        NOTE: This does not actually set the clock frequency!
              It simply tells the driver what frequency the board is using,
              since this cannot (currently) be autodetected.

        Also note that this frequency refers to the speed at which the
        PulseBlaster core itself runs. On many boards, this is different than
        the value printed on the oscillator. On RadioProcessor devices, the A/D
        converter and the PulseBlaster core operate at the same clock
        frequency.
        """

        clock_freq = clock_freq/1e6

        clock = ctypes.c_double(clock_freq)

        return self._lib.pb_core_clock(clock)

    def _write_pulse(self, flags, inst, inst_data, length):
        """Instruction programming function for boards without a DDS.

        @param unsigned int flags: It is essentialy an integer number
                                   corresponding to a bit representation of the
                                   channel settings. Set every bit to one for
                                   each flag you want to set high. If 8 channels
                                   are addressable then their bit representation
                                   would be
                                       0b00000000   (in python).
                                       => int(0b00000000)= 0 is the number you
                                          would specify
                                   where the most right corresponds to ch1 and
                                   the most left to ch8. If you want to set
                                   channel 1,2,3 and 7 to be on, then the bit
                                   word must be
                                       0b01000111
                                       => int(0b01000111) = 71
                                    so the flags=71 will perform the job above.
                                   Valid values are from 0x0 (=0) to 0xFFFFFF
                                   (=)
        @param int inst: Specify the instruction you want. Valid instructions
                         are:
        Opcode# 	Instruction  Inst_data          Meaning of inst_data field
             0      CONTINUE     Ignored                      Program execution continues to next
                                                              instruction
             1      STOP         Ignored                      Stop execution of program.
             2      LOOP         Number of desired loops.     Specify beginning of a loop. Execution
                                 This number must be          continues to next instruction.
                                 greater than or equal to 1.
             3      END_LOOP     Address of beginning of      Specify end of a loop.
                                 originating loop
             4      JSR          Address of first subroutine  Program execution jumps to beginning
                                 instruction.                 of a subroutine.
             5      RTS          Ignored                      Program execution returns to
                                                              instruction after JSR was called.

             6      BRANCH       Address of next instruction  Program execution continues at
                                                              specific instruction.
             7      LONG_DELAY   Desired multiplication       For long interval instructions.
                                 factor for the “Delay Count”  Executes length of pulse given in the
                                 field. This value must be    time field multiplied by the value
                                 greater than or equal to 2.  in the data field.

             8      WAIT         Ignored                      Program execution stops and waits for
                                                              software or hardware trigger.

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
        @param double length: Length of this instruction in seconds.

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

        # the function call expects nanoseconds as units
        #print("Length : {} ns - Channels : {:b} - Inst data : {}".format(int(length*1e9), int(flags), inst_data))
        length = ctypes.c_double(length*1e9)

        self._lib.pb_inst_pbonly.argtype = [ctypes.c_int, ctypes.c_int,
                                            ctypes.c_int, ctypes.c_double]

        return self.check(self._lib.pb_inst_pbonly(flags, inst, inst_data, length))

    def get_status_bit(self):
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

        self._lib.pb_read_status.restype = ctypes.c_uint32

        return self._lib.pb_read_status()

    def get_status_message(self):
        """ Read status message from the board.

        Not all boards support this, see your manual. The returned string will
        either have the board's status or an error message.

        @return str: containing the status message of the board.
        """
        self._lib.pb_status_message.restype = ctypes.c_char_p

        return self._lib.pb_status_message().decode('utf8')

    # =========================================================================
    # Below all the higher level routines are situated which use the
    # wrapped routines as a basis to perform the desired task.
    # =========================================================================

    def write_pulse_form(self, sequence_list, loop=True):
        """ The higher level function, which creates the actual sequences.

        @param list sequence_list: a list with dictionaries. The dictionaries
                                   have the elements 'active_channels' and
                                   'length. The 'active_channels' is
                                   a numpy list, which contains the channel
                                   number, which should be switched on. The
                                   channel numbers start with 0. E.g.

                                   [{'active_channels':[0], 'length': 10e-6},
                                    {'active_channels':[], 'length': 20e-6}]
                                    which will switch on

        @param bool loop: optional, set if sequence should be looped (so that it
                          runs continuously) or not, default it True.

        @return int: The number of created pulses with the given sequence.

        This method should called with the general sequence_list to program
        the PulseBlaster.
        """

        # Catch the case where only one entry in the sequence is present:
        if len(sequence_list) == 1:
            return self.activate_channels(ch_list=sequence_list[0]['active_channels'],
                                          length=sequence_list[0]['length'],
                                          immediate_start=False)

        self.start_programming()
        start_pulse = self._convert_pulse_to_inst(
                            sequence_list[0]['active_channels'],
                            sequence_list[0]['length'])

        # go through each pulse in the sequence and write it to the
        # PulseBlaster.
        for pulse in sequence_list[1:-1]:
            num = self._convert_pulse_to_inst(pulse['active_channels'],
                                              pulse['length'])
            if num > 4094:# =(2**12 -2)
                self.log.error('Error in PulseCreation: Command {0} exceeds '
                               'the maximal number of commands'.format(num))

        active_channels = sequence_list[-1]['active_channels']
        length = sequence_list[-1]['length']

        # Take the last pulse and tell either the device to stop after this
        # round and do no infinite looping or branching from out to
        # connect the end with the beginning of the pulse.

        bitmask = self._convert_to_bitmask(active_channels)

        # For some old models, long delay is not an option so smart_pulse_creation is needed
        # Let's cut the last pulse in two if it's too long.
        if self._use_smart_pulse_creation and length > 256*self.GRAN_MIN:
            self._convert_pulse_to_inst(active_channels, length-128*self.GRAN_MIN)
            length = 128*self.GRAN_MIN
        length = np.round(np.round(length / self.GRAN_MIN + 0.01) * self.GRAN_MIN, 12)
        # with the branch or the stop command
        if loop:
            num = self._write_pulse(flags=self.ON | bitmask,
                                    inst=self.BRANCH,
                                    inst_data=start_pulse,
                                    length=length)
        else:
            num = self._write_pulse(flags=self.ON | bitmask,
                                    inst=self.STOP,
                                    inst_data=None,
                                    length=length)

        if num > 4094:  # =(2**12 -2)
            self.log.error('Error in PulseCreation: Command {0} exceeds '
                           'the maximal number of commands'.format(num))

        self.stop_programming()

        return num

    def _convert_pulse_to_inst(self, active_channels, length):
        """ Convert a pulse of one row to a instructions for the PulseBlaster.

        @param np.array active_channels: the list of active channels like
                                         e.g. [0,4,7]. Note that the channels
                                         start from 0.
        @param float length: length of the current row in s.

        @return int: The address number num of the created instruction.

        Helper method for write_pulse_form.
        """

        # return bit representation of active channels:
        channel_bitmask = self._convert_to_bitmask(active_channels)

        # # Check, whether the length fulfills the minimal granularity:
        old_length = length

        length = np.round(np.round(length/self.GRAN_MIN+0.01) * self.GRAN_MIN, 12)
        # the +0.01 moves the critical point by this value and avoids ambiguity
        # at number divided by the sample rate (Note: the +0.01 does not remove
        # the ambiguity, it is just shifted by this value. It is assume that an
        # entry of 13.0 is much more likely than 13.01).


        residual = old_length - length
        if not np.isclose(residual, 0.0, atol=1e-12):
            self.log.warning('The length of the pulse does not fulfill the '
                             'granularity of {0:.2e}s. The length is rounded '
                             'to a number, dividable by the granularity! '
                             '{1:.2e}s were dropped.'
                             ''.format(self.GRAN_MIN, residual))

        # an algorithm to utilize the long delay possibility of the pulse
        # blaster.

        if self._use_smart_pulse_creation:

            # If the clock is 500MHz, then the time resolution is 2ns. However, the
            # minimal length of every instruction is usually not a clock cycle, but
            # more (can range from 5-7 clock cycles).
            # A step of 2ns will be represented by one bit, i.e. by using 8bit a
            # time of 2ns * 2^8 = 512ns can be sampled in one data word. Internally,
            # this will be the time frame of the data processing. This procedure
            # enables to run the data processing 8 times slower, and only the fast
            # multiplexer, which combines and outputs the 8bit word, needs to run at
            # the fast clock speed of 500MHz. This prevents errors and is more
            # stable for the data processing.

            if length <= 256*self.GRAN_MIN:

                # pulses are written in 8 bit words. Save memory if the length of
                # the pulse is smaller than 256
                num = self._write_pulse(flags=self.ON | channel_bitmask,
                                        inst=self.CONTINUE,
                                        inst_data=None,
                                        length=length)

            elif length > 256*self.GRAN_MIN:
                # reducing the length of the pulses by repeating them.
                # Try to factorize successively, in order to reducing the total
                # length of the pulse form. Put the subtracted amount into an
                # additional short command if necessary.

                remaining_time = length
                i = 4
                while True:

                    num_clock_cycles = int(length/self.GRAN_MIN)
                    value, factor = self._factor(num_clock_cycles)

                    if value > 4:
                        if factor == 1:
                            num = self._write_pulse(flags=self.ON | channel_bitmask,
                                                    inst=self.CONTINUE,
                                                    inst_data=None,
                                                    length=value*self.GRAN_MIN)

                        elif factor < 1048576: # = (2**20 + 1)
                            # check if you do not exceed the memory limit. Then
                            # you can use the factorized approach to loop your
                            # pulse forms. Therefore apply a LONG_DELAY instruction
                            num = self._write_pulse(flags=self.ON | channel_bitmask,
                                                    inst=self.LONG_DELAY,
                                                    inst_data=int(factor),
                                                    length=value*self.GRAN_MIN)
                        else:
                            self.log.error('Error in PulseCreation: Loop counts '
                                           'are {0} in LONG_DELAY instruction and '
                                           'exceedes the maximal possible value of '
                                           '2^20+1 = 1048576.\n'
                                           'Repeat PulseCreation with different '
                                           'parameters!'.format(factor))

                        if i > 4:
                            self._write_pulse(flags=self.ON | channel_bitmask,
                                              inst=self.CONTINUE,
                                              inst_data=None,
                                              length=i*self.GRAN_MIN)

                        break
                    i = i+1
                    length = remaining_time - i*self.GRAN_MIN
        else:
            num = self._write_pulse(flags=self.ON | channel_bitmask,
                                    inst=self.CONTINUE,
                                    inst_data=None,
                                    length=length)
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
                return div, number//div
            div -= 1
        return 1, number

    def _correct_sequence_for_delays(self, sequence):
        """ Take a sequence and modify it to take into account delays

        For example the sequence
        [{'active_channels': [0], 'length': 50e-09},
        {'active_channels': [], 'length': 1500e-09},
        {'active_channels': [2], 'length': 500-09},
        {'active_channels': [], 'length': 1500e-09}]

        will be converted, for a delay of 200 ns on channel 0 and 500 ns on channel 2, to :
        [{'active_channels': [], 'length': 1050e-09},
        {'active_channels': [2], 'length': 500-09},
        {'active_channels': [], 'length': 1800e-09}
        {'active_channels': [0], 'length': 50e-09},
        {'active_channels': [], 'length': 150e-09}]

        In this example, the pulse on channel 2 is sent sooner and the pulse on channel 0
        is sent at the end to affect the system at t=0

        @param sequence : the theoretical sequence to correct

        @return corrected_sequence : the sequence taking the delays into account
        """
        # If no delay is specified, skip the whole process
        if len(self._channel_delays) == 0:
            return sequence

        # construct a table with delay of each channel
        delays = np.zeros(21)
        for entry in self._channel_delays:
            delays[int(entry)] = self._channel_delays[entry]

        # First let's construct the array that encode the pulses as :
        # {'channel': single channel, 'direction': toggle direction, 'time': time of event}
        # the event based approach misses the always on channels
        last_state = set(sequence[-1]['active_channels'])
        always_on = set(sequence[-1]['active_channels'])
        time = 0
        events = []
        for pulse in sequence[:]:
            new_state = set(pulse['active_channels'])
            always_on &= new_state
            toggle_on = new_state - last_state
            toggle_off = last_state - new_state
            for channel in toggle_on:
                events.append({'channel': channel, 'direction': True, 'time': time})
            for channel in toggle_off:
                events.append({'channel': channel, 'direction': False, 'time': time})
            time += pulse['length']
            last_state = new_state
        total_time = time

        # Let's move the events around the cycle
        for event in events:
            event['time'] -= delays[event['channel']]
            event['time'] %= total_time

        # Sort the array by event time
        events = sorted(events, key=lambda x: x['time'])

        # iterate over every change to find the state at the end, to have it at the beginning
        last_state = set()
        for event in events:
            if event['direction']:
                last_state |= {event['channel']}
            else:
                last_state -= {event['channel']}

        # Let's construct back the sequence
        corrected_sequence = []
        time = 0
        state = last_state
        for event in events:
            duration = event['time'] - time
            # add the pulse between last event an this event (so use the last state)
            corrected_sequence.append({'active_channels': list(state | always_on), 'length': duration})
            if event['direction']:
                state |= {event['channel']}
            else:
                state -= {event['channel']}
            time += duration

        # We need to add the last pulse manually
        corrected_sequence.append({'active_channels': list(state | always_on), 'length': total_time-time})

        # Let's treat the short pulses we created
        delta_time = 0
        for pulse in corrected_sequence:
            if pulse['length'] == 0 or pulse['length'] < self.LEN_MIN/1e3:  # is zero with rounding error
                corrected_sequence.remove(pulse)
            elif pulse['length'] < self.LEN_MIN/2:
                corrected_sequence.remove(pulse)
                self.log.info("Delay correction of the pulse blaster has created a pulse too short."
                              "The pulse is {0} ns with a minimum of {1} ns in th state {2}."
                               "Pulses shorter than half the minimum are dropped.".format(
                    pulse['length']*1e9, self.LEN_MIN*1e9, pulse['active_channels']
                ))
                delta_time -= pulse['length']
            elif self.LEN_MIN/2 <= pulse['length'] < self.LEN_MIN:
                self.log.info("Delay correction of the pulse blaster has created a pulse too short."
                          "The pulse is {0} ns with a minimum of {1} ns in th state {2}."
                          "This pulse has been rounded to {1} ns.".format(
                    pulse['length'] * 1e9, self.LEN_MIN * 1e9, pulse['active_channels']
                ))
                delta_time += self.LEN_MIN - pulse['length']
                pulse['length'] = self.LEN_MIN
        if delta_time > 0:
            self.log.warning("Delay correction has induced an overtime of {0} ns. The total length is now"
                                " {1} s. This may need to be accounted in the acquisition.".format(
                delta_time*1e9, total_time+delta_time))

        return corrected_sequence

    # =========================================================================
    # A bit higher methods for using the card as switch
    # =========================================================================

    def activate_channels(self, ch_list, length=100e-9, immediate_start=True):
        """ Set specific channels to high, all others to low.

        @param list ch_list: the list of active channels like  e.g. [0,4,7].
                             Note that the channels start from 0. Note, an empty
                             list will set all channels to low.
        @param int length: optional, length of the activated channel output in
                           s. Since there will be no switching of channels
                           within this mode, the length of the pulsing time can
                           be chosen arbitrary. Here 100e-9s is the default value.
                           A larger number does not make a lot of sense.

        @param bool immediate_start: optional, indicate whether output should
                                     directly be switch on, default is True.

        @return int: the number of created pulse instructions, normally it
                     should output just the number 1.

        This is a high level command mostly used not for pulsing but just rather
        for switching something on or off.

        """

        bitmask = self._convert_to_bitmask(ch_list)

        self.start_programming()
        retval = self._write_pulse(flags=self.ON | bitmask,
                                   inst=self.BRANCH,
                                   inst_data=0,
                                   length=length)
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

    def getSwitchState(self, switch_num):
        """ Gives state of switch.

        @param int switch_num: number of switch, numbering starts with 0

        @return bool: True if on, False if off, None on error
        """

        return self.switch_states['d_ch{0}'.format(switch_num+1)]

    def getCalibration(self, switch_num, switch_state):
        """ Get calibration parameter for switch.

        @param int switch_num: number of switch for which to get calibration
                                 parameter
        @param str switch_state: state ['On', 'Off'] for which to get
                                calibration parameter

        @return str: calibration parameter for switch and state.
        """

        # There is no possibility to calibrate the voltage values for the
        # Pulse Blaster, either it is on at 5.0V or off at 0.0V.
        possible_states = {'On': 3.3, 'Off': 0.0}
        return possible_states[switch_state]

    def setCalibration(self, switch_num, switch_state, value):
        """ Set calibration parameter for switch.

          @param int switch_num: number of switch for which to get calibration
                                   parameter
          @param str switch_state: state ['On', 'Off'] for which to get
                                   calibration parameter
          @param int value: calibration parameter to be set.

          @return bool: True if succeeds, False otherwise
        """
        self.log.warning('Not possible to set a Switch Voltage for '
                         'PulseBlaster Devices. Command ignored.')
        return True

    def switchOn(self, switch_num):
        """ Switch on.

        @param int switch_num: number of switch to be switched, number starts
                               from zero.

        @return bool: True if succeeds, False otherwise
        """

        self.switch_states['d_ch{0}'.format(switch_num+1)] = True

        ch_list = [int(entry.replace('d_ch', ''))-1 for entry in self.switch_states if self.switch_states[entry]]

        self.activate_channels(ch_list=ch_list, length=100, immediate_start=True)

        return self.switch_states['d_ch{0}'.format(switch_num+1)]

    def switchOff(self, switch_num):
        """ Switch off.

        @param int switch_num: number of switch to be switched

        @return bool: True if suceeds, False otherwise
        """

        self.switch_states['d_ch{0}'.format(switch_num+1)] = False

        ch_list = [int(entry.replace('d_ch', ''))-1 for entry in self.switch_states if self.switch_states[entry]]

        self.activate_channels(ch_list=ch_list, length=100, immediate_start=True)

        return self.switch_states['d_ch{0}'.format(switch_num+1)]

    def getSwitchTime(self, switch_num):
        """ Give switching time for switch.

        @param int switch_num: number of switch

        @return float: time needed for switch state change
        """

        # switch time is limited to communication speed to the device,
        # therefore set the average communication time of 1ms as the limitation.
        return 0.001

    # =========================================================================
    # Below the pulser interface implementation.
    # =========================================================================

    def get_constraints(self):
        """Retrieve the hardware constrains from the Pulsing device.

        @return constraints object: object with pulser constraints as
                                    attributes.

        Provides all the constraints (e.g. sample_rate, amplitude,
        total_length_bins, channel_config, ...) related to the pulse generator
        hardware to the caller.

            SEE PulserConstraints CLASS IN pulser_interface.py FOR AVAILABLE
            CONSTRAINTS!!!

        If you are not sure about the meaning, look in other hardware files to
        get an impression. If still additional constraints are needed, then they
        have to be added to the PulserConstraints class.

        Each scalar parameter is an ScalarConstraints object defined in
        core.util.interfaces. Essentially it contains min/max values as well as
        min_step_size, default_value and unit of the parameter.

        PulserConstraints.activation_config differs, since it contain the
        channel configuration/activation information of the form:

            {<descriptor_str>: <channel_set>,
             <descriptor_str>: <channel_set>,
             ...}

        If the constraints cannot be set in the pulsing hardware (e.g. because
        it might have no sequence mode) just leave it out so that the default is
        used (only zeros).

        # Example for configuration with default values:
        constraints = PulserConstraints()

        constraints.sample_rate.min = 10.0e6
        constraints.sample_rate.max = 12.0e9
        constraints.sample_rate.step = 10.0e6
        constraints.sample_rate.default = 12.0e9

        constraints.a_ch_amplitude.min = 0.02
        constraints.a_ch_amplitude.max = 2.0
        constraints.a_ch_amplitude.step = 0.001
        constraints.a_ch_amplitude.default = 2.0

        constraints.a_ch_offset.min = -1.0
        constraints.a_ch_offset.max = 1.0
        constraints.a_ch_offset.step = 0.001
        constraints.a_ch_offset.default = 0.0

        constraints.d_ch_low.min = -1.0
        constraints.d_ch_low.max = 4.0
        constraints.d_ch_low.step = 0.01
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = 0.0
        constraints.d_ch_high.max = 5.0
        constraints.d_ch_high.step = 0.01
        constraints.d_ch_high.default = 5.0

        constraints.waveform_length.min = 80
        constraints.waveform_length.max = 64800000
        constraints.waveform_length.step = 1
        constraints.waveform_length.default = 80

        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 32000
        constraints.waveform_num.step = 1
        constraints.waveform_num.default = 1

        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 8000
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1

        constraints.subsequence_num.min = 1
        constraints.subsequence_num.max = 4000
        constraints.subsequence_num.step = 1
        constraints.subsequence_num.default = 1

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65539
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0

        constraints.event_triggers = ['A', 'B']
        constraints.flags = ['A', 'B', 'C', 'D']

        constraints.sequence_steps.min = 0
        constraints.sequence_steps.max = 8000
        constraints.sequence_steps.step = 1
        constraints.sequence_steps.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names for
        # the different configurations can be customary chosen.

        activation_conf = OrderedDict()
        activation_conf['yourconf'] = frozenset(
            {'a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3', 'd_ch4'})
        activation_conf['different_conf'] = frozenset({'a_ch1', 'd_ch1', 'd_ch2'})
        activation_conf['something_else'] = frozenset({'a_ch2', 'd_ch3', 'd_ch4'})
        constraints.activation_config = activation_conf
        """
        constraints = PulserConstraints()
        constraints.sample_rate.min = self._clock_freq
        constraints.sample_rate.max = self._clock_freq
        constraints.step = 0.0
        constraints.unit = 'Hz'

        constraints.d_ch_low.min = 0.0
        constraints.d_ch_low.max = 0.0
        constraints.d_ch_low.step = 0.0
        constraints.d_ch_low.default = 0.0
        constraints.d_ch_low.unit = 'V'

        # it is a LVTTL standard with 3.3V as the logical one
        constraints.d_ch_high.min = 3.3
        constraints.d_ch_high.max = 3.3
        constraints.d_ch_high.step = 3.3
        constraints.d_ch_high.default = 3.3
        constraints.d_ch_high.unit = 'V'

        # Minimum instruction time in clock cycles specified in the config,
        # translates for 6 clock cycles to 12ns at 500MHz.
        constraints.waveform_length.min = self._min_instr_len
        constraints.waveform_length.max = 2**20-1
        constraints.waveform_length.step = 1
        constraints.waveform_length.default = 128

        activation_config = OrderedDict()
        activation_config['4_ch'] = frozenset({'d_ch1', 'd_ch2', 'd_ch3', 'd_ch4'})
        activation_config['all'] = frozenset({'d_ch1', 'd_ch2', 'd_ch3', 'd_ch4',
                                              'd_ch5', 'd_ch6', 'd_ch7', 'd_ch8',
                                              'd_ch9', 'd_ch10', 'd_ch11', 'd_ch12',
                                              'd_ch13', 'd_ch14', 'd_ch15', 'd_ch16',
                                              'd_ch17', 'd_ch18', 'd_ch19', 'd_ch20',
                                              'd_ch21'})

        constraints.activation_config = activation_config

        return constraints


    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error)
        """
        return self.start()

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error)
        """
        return self.stop()

    def load_waveform(self, load_dict):
        """ Loads a waveform to the specified channel of the pulsing device.

        @param dict|list load_dict: a dictionary with keys being one of the
                                    available channel index and values being the
                                    name of the already written waveform to load
                                    into the channel. Examples:

                                        {1: rabi_ch1, 2: rabi_ch2}
                                    or
                                        {1: rabi_ch2, 2: rabi_ch1}

                                    If just a list of waveform names if given,
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
        """

        # Since only one waveform can be present at a time check if only a
        # single name is given
        if isinstance(load_dict, list):
            waveforms = list(set(load_dict))
        elif isinstance(load_dict, dict):
            waveforms = list(set(load_dict.values()))
        else:
            self.log.error('Method load_waveform expects a list of waveform '
                           'names or a dict.')
            return self.get_loaded_assets()

        if len(waveforms) != 1:
            self.log.error('PulseBlaster expects exactly one waveform name for '
                           'load_waveform.')
            return self.get_loaded_assets()

        waveform = waveforms[0]
        if waveform != self._current_pb_waveform_name:
            self.log.error('No waveform by the name "{0}" generated for '
                           'PulseBlaster.\n'
                           'Only one waveform at a time can be '
                           'held.'.format(waveform))
            return self.get_loaded_assets()

        self.write_pulse_form(self._current_pb_waveform)
        self._currently_loaded_waveform = waveform

        return self.get_loaded_assets()[0]

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready
            for playback.

        @param dict|list sequence_name: a dictionary with keys being one of the
                                        available channel index and values being
                                        the name of the already written waveform
                                        to load into the channel. Examples:

                                            {1: rabi_ch1, 2: rabi_ch2} or
                                            {1: rabi_ch2, 2: rabi_ch1}

                                        If just a list of waveform names if
                                        given, the channel association will be
                                        invoked from the channel suffix '_ch1',
                                        '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per
                      channel.

        For devices that have a workspace (i.e. AWG) this will load the sequence
        from the device workspace into the channels. For a device without mass
        memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.
        """

        self.log.warning('PulseBlaster digital pulse generator has no '
                         'sequencing capabilities.\n'
                         'load_sequence call ignored.')
        return {}

    def get_loaded_assets(self):
        """ Retrieve the currently loaded asset names for each active channel
            of the device.

        @return (dict, str): Dictionary with keys being the channel number and
                             values being the respective asset loaded into the
                             channel, string describing the asset type
                             ('waveform' or 'sequence')

        The returned dictionary will have the channel numbers as keys. In case
        of loaded waveforms the dictionary values will be the waveform names. In
        case of a loaded sequence the values will be the sequence name appended
        by a suffix representing the track loaded to the respective channel
        (i.e. '<sequence_name>_1').
        """

        asset_type = 'waveform' if self._currently_loaded_waveform else None

        asset_dict = {}
        for index, entry in enumerate(self._current_activation_config):
            # asset_dict[index+1] = '{0}_'.format(self._current_pb_waveform_name, entry.replace('d_',''))
            asset_dict[index+1] = self._current_pb_waveform_name
        return asset_dict, asset_type

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)
        """

        self._currently_loaded_waveform = ''
        self._current_pb_waveform_name = ''
        self._current_pb_waveform = [{'active_channels': [], 'length': self.LEN_MIN}]
        self._current_pb_waveform_theoretical = [{'active_channels': [], 'length': self.LEN_MIN}]
        return 0

    def get_status(self):
        """ Retrieves the status of the pulsing hardware.

        @return (int, dict): tuple with an integer value of the current status
                             and a corresponding dictionary containing status
                             description for all the possible status variables
                             of the pulse generator hardware.
        """
        num = self.get_status_bit()
        if num in [0, 1, 2]:
            state = 0
        else:
            state = 1

        status_dict = {0: 'Idle', 1: 'Running'}

        return state, status_dict

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead
        retrieve the current sample rate directly from the device.
        """
        return self.SAMPLE_RATE

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually
        set return value for further processing.
        """

        self.log.warning('Sample rate cannot be changed in the PulseBlaster.'
                         'Ignore the command.')

        return self.get_sample_rate()

    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if the amplitude value (in Volt peak to
                               peak, i.e. the full amplitude) of a specific
                               channel is desired.
        @param list offset: optional, if the offset value (in Volt) of a
                            specific channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel
                               descriptor string (i.e. 'a_ch1') and items being
                               the values for those channels. Amplitude is
                               always denoted in Volt-peak-to-peak and Offset
                               in volts.

        Note: Do not return a saved amplitude and/or offset value but instead
              retrieve the current amplitude and/or offset directly from the
              device.

        If nothing (or None) is passed then the levels of all channels will be
        returned. If no analog channels are present in the device, return just
        empty dicts.

        Example of a possible input:

            amplitude = ['a_ch1', 'a_ch4'], offset = None

        to obtain the amplitude of channel 1 and 4 and the offset of all
        channels

            {'a_ch1': -0.5, 'a_ch4': 2.0}
            {'a_ch1': 0.0, 'a_ch2': 0.0, 'a_ch3': 1.0, 'a_ch4': 0.0}

        """
        return dict(), dict()

    def set_analog_level(self, amplitude=None, offset=None):
        """ Set amplitude and/or offset value of the provided analog channel(s).

        @param dict amplitude: dictionary, with key being the channel descriptor
                               string (i.e. 'a_ch1', 'a_ch2') and items being
                               the amplitude values (in Volt peak to peak, i.e.
                               the full amplitude) for the desired channel.
        @param dict offset: dictionary, with key being the channel descriptor
                            string (i.e. 'a_ch1', 'a_ch2') and items being the
                            offset values (in absolute volt) for the desired
                            channel.

        @return (dict, dict): tuple of two dicts with the actual set values for
                              amplitude and offset for ALL channels.

        If nothing is passed then the command will return the current
        amplitudes/offsets.

        Note: After setting the amplitude and/or offset values of the device,
              use the actual set return values for further processing.
        """
        return {}, {}

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels.

        @param list low: optional, if the low value (in Volt) of a specific
                         channel is desired.
        @param list high: optional, if the high value (in Volt) of a specific
                          channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel
                               descriptor strings (i.e. 'd_ch1', 'd_ch2') and
                               items being the values for those channels. Both
                               low and high value of a channel is denoted in
                               volts.

        Note: Do not return a saved low and/or high value but instead retrieve
              the current low and/or high value directly from the device.

        If nothing (or None) is passed then the levels of all channels are being
        returned. If no digital channels are present, return just an empty dict.

        Example of a possible input:

            low = ['d_ch1', 'd_ch4']

        to obtain the low voltage values of digital channel 1 an 4. A possible
        answer might be

            {'d_ch1': -0.5, 'd_ch4': 2.0}
            {'d_ch1': 1.0, 'd_ch2': 1.0, 'd_ch3': 1.0, 'd_ch4': 4.0}

        Since no high request was performed, the high values for ALL channels
        are returned (here 4).
        """
        if low:
            low_dict = {chnl: 0.0 for chnl in low}
        else:
            low_dict = {'d_ch{0:d}'.format(chnl + 1): 0.0 for chnl in range(21)}

        if high:
            high_dict = {chnl: 3.3 for chnl in high}
        else:
            high_dict = {'d_ch{0:d}'.format(chnl + 1): 5.0 for chnl in range(21)}

        return low_dict, high_dict

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel.

        @param dict low: dictionary, with key being the channel descriptor
                         string (i.e. 'd_ch1', 'd_ch2') and items being the low
                         values (in volt) for the desired channel.
        @param dict high: dictionary, with key being the channel descriptor
                          string (i.e. 'd_ch1', 'd_ch2') and items being the
                          high values (in volt) for the desired channel.

        @return (dict, dict): tuple of two dicts where first dict denotes the
                              current low value and the second dict the high
                              value for ALL digital channels. Keys are the
                              channel descriptor strings (i.e. 'd_ch1', 'd_ch2')

        If nothing is passed then the command will return the current voltage
        levels.

        Note: After setting the high and/or low values of the device, use the
              actual set return values for further processing.
        """
        self.log.warning('PulseBlaster pulse generator logic level cannot be '
                         ' adjusted! Ignore the command.')
        return self.get_digital_level()

    def get_active_channels(self,  ch=None):
        """ Get the active channels of the pulse generator hardware.

        @param list ch: optional, if specific analog or digital channels are
                        needed to be asked without obtaining all the channels.

        @return dict: where keys denoting the channel string and items boolean
                      expressions whether channel are active or not.

        Example for an possible input (order is not important):

            ch = ['a_ch2', 'd_ch2', 'a_ch1', 'd_ch5', 'd_ch1']

        then the output might look like

            {'a_ch2': True, 'd_ch2': False, 'a_ch1': False, 'd_ch5': True,
             'd_ch1': False}

        If no parameter (or None) is passed to this method all channel states
        will be returned.
        """

        if ch is None:
            ch = list(self.channel_states.keys())

        active_ch = {}
        for channel in ch:
            active_ch[channel] = channel in self._current_activation_config

        return active_ch

    def set_active_channels(self, ch=None):
        """ Set the active channels for the pulse generator hardware.

        @param dict ch: dictionary with keys being the analog or digital string
                        generic names for the channels (i.e. 'd_ch1', 'a_ch2')
                        with items being a boolean value. True: Activate
                        channel, False: Deactivate channel

        @return dict: with the actual set values for ALL active analog and
                      digital channels

        If nothing is passed then the command will simply return the unchanged
        current state.

        Note: After setting the active channels of the device, use the returned
              dict for further processing.

        Example for possible input:

            ch={'a_ch2': True, 'd_ch1': False, 'd_ch3': True, 'd_ch4': True}

        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1.

        The hardware itself has to handle, whether separate channel activation
        is possible.
        """

        if ch is None:
            ch = {}

        # save activation in case it cannot be set correctly
        old_activation = self.channel_states.copy()

        for channel in ch:
            self.channel_states[channel] = ch[channel]

        active_channel_set = {chnl for chnl, is_active in self.channel_states.items() if is_active}

        if active_channel_set not in self.get_constraints().activation_config.values():
            self.log.error('Channel activation to be set not found in constraints.\n'
                           'Channel activation unchanged.')
            self.channel_states = old_activation
        else:
            self._current_activation_config = active_channel_set

        return self.get_active_channels(ch=list(ch))

    def write_waveform(self, name, analog_samples, digital_samples,
                       is_first_chunk, is_last_chunk, total_number_of_samples):
        """ Write a new waveform or append samples to an already existing
            waveform on the device memory.

        @param str name: the name of the waveform to be created/append to
        @param numpy.ndarray analog_samples: array of type float32 containing
                                             the voltage samples
        @param numpy.ndarray digital_samples: array of type bool containing the
                                               marker states (if analog channels
                                               are active, this must be the same
                                               length as analog_samples)
        @param bool is_first_chunk: flag indicating if it is the first chunk to
                                    write. If True this method will create a new
                                    empty waveform. If False the samples are
                                    appended to the existing waveform.
        @param bool is_last_chunk: flag indicating if it is the last chunk to
                                   write. Some devices may need to know when to
                                   close the appending waveform file.
        @param int total_number_of_samples: The number of sample points for the
                                            entire waveform (not only the
                                            currently written chunk)

        @return (int, list): number of samples written (-1 indicates failed
                             process) and list of created waveform names.

        The flags is_first_chunk and is_last_chunk can be used as indicator,
        if a new waveform should be created or if the write process to a
        waveform should be terminated.

        """
        analog_samples = netobtain(analog_samples)
        digital_samples = netobtain(digital_samples)

        #FIXME: Remove those, after debug process is finished.
        self._name = name
        self._analog_samples = analog_samples
        self._digital_samples = digital_samples
        self._total_number_of_samples = total_number_of_samples
        self._is_first_chunk = is_first_chunk
        self._is_last_chunk = is_last_chunk

        if analog_samples:
            self.log.error('PulseBlaster is purely digital and does not '
                           'support waveform generation with analog samples.')
            return -1, list()

        if not digital_samples:
            if total_number_of_samples > 0:
                self.log.warning('No samples handed over for waveform '
                                 'generation! Pass to the function '
                                 '"write_waveform" digital samples!')
                return -1, list()

            else:
                self._current_pb_waveform_theoretical = [{'active_channels': [], 'length': self.LEN_MIN}]
                self._current_pb_waveform = [{'active_channels': [], 'length': self.LEN_MIN}]
                self._current_pb_waveform_name = ''
                return 0, list()

        # Determine the length of one of the waveform arrays, all should be the
        # same length.
        chan = list(digital_samples)
        chan.sort()
        chunk_length = len(digital_samples[chan[0]])

        # assume that the number of channels are specified correct from the
        # instance, which called this method.
        self._current_activation_config = chan

        if is_first_chunk:
            self._current_pb_waveform_theoretical = self._convert_sample_to_pb_sequence(digital_samples)

            self._current_pb_waveform_name = name

        else:

            pb_waveform_temp = self._convert_sample_to_pb_sequence(digital_samples)

            # check if last of existing waveform is the same as the first one of
            # the coming one, then combine them,
            if self._current_pb_waveform_theoretical[-1]['active_channels'] == pb_waveform_temp[0]['active_channels']:
                self._current_pb_waveform_theoretical[-1]['length'] += pb_waveform_temp[0]['length']
                pb_waveform_temp.pop(0)

            self._current_pb_waveform_theoretical.extend(pb_waveform_temp)

        # convert at first the separate waveforms for each channel to a matrix

        if is_last_chunk:
            self._current_pb_waveform = self._correct_sequence_for_delays(self._current_pb_waveform_theoretical)
            self.write_pulse_form(self._current_pb_waveform)
            self.log.debug('Waveform written in PulseBlaster with name "{0}" '
                           'and a total length of {1} sequence '
                           'entries.'.format(self._current_pb_waveform_name,
                                              len(self._current_pb_waveform) ))

        return chunk_length, [self._current_pb_waveform_name]

    def _convert_sample_to_pb_sequence(self, digital_samples):
        """ Helper method to create a pulse blaster sequence.

        @param numpy.ndarray digital_samples: array of type bool containing the
                                              marker states (if analog channels
                                              are active, this must be the same
                                              length as analog_samples)

        @return list: a sequence list with dictionaries formated for the generic
                      method 'write_pulse_form. The dictionaries have the
                      elements 'active_channels' and 'length. The
                      'active_channels' is a list, which contains the channel
                      number, which should be switched on. The channel numbers
                      start with 0. The 'length' entry contains the length of
                      the 'active_channels' in ns. E.g.

                        [{'active_channels':[0], 'length': 10e-6},
                         {'active_channels':[], 'length': 20e-6}]

                      which will switch on channel 0 for 10us on and switch all
                      channels off for 20us.
        """

        ch_list = list(digital_samples)
        ch_list.sort()
        num_ch = len(ch_list)

        # take on of the channel and obtain the channel length
        num_entries = len(digital_samples[ch_list[0]])

        last_sequence_dict = None
        pb_sequence_list = list()

        for index in range(num_entries):

            # create at first a temporary array, with the minimal granularity
            # length. The sampling freq is fixed anyway and cannot be changed.
            temp_sequence_dict = {'active_channels': [],
                                  'length': self.GRAN_MIN}

            for ch_name in ch_list:

                if digital_samples[ch_name][index]:
                    temp_sequence_dict['active_channels'].append(int(ch_name.replace('d_ch', ''))-1)

            # compare it with the last array if present

            # if not present start to count
            if last_sequence_dict is None:
                last_sequence_dict = temp_sequence_dict

            else:

                 # if present and the same channels, accumulate length
                if temp_sequence_dict['active_channels'] == last_sequence_dict['active_channels']:
                    last_sequence_dict['length'] += temp_sequence_dict['length']

                # if present and not the same channels, append last array to
                # sequence array
                else:
                    # increase length by 1%, to remove the ambiguity for the
                    # comparison
                    if last_sequence_dict['length']*1.01 < self.LEN_MIN:
                        self.log.warning('Current waveform contains a pulse of '
                                         'length {0:.2f}ns, which is smaller '
                                         'than the minimal allowed length of '
                                         '{1:.2f}ns! Pulse sequence might '
                                         'most probably look unexpected. '
                                         'Increase the length of the smallest '
                                         'pulse!'
                                         ''.format(last_sequence_dict['length']*1e9,
                                                   self.LEN_MIN*1e9))

                    pb_sequence_list.append(last_sequence_dict)

                    # and temporary array becomes last array for the next round
                    last_sequence_dict = temp_sequence_dict

        # do not forget to add the last sequence
        pb_sequence_list.append(last_sequence_dict)

        return pb_sequence_list

    def write_sequence(self, name, sequence_parameters):
        """
        Write a new sequence on the device memory.

        @param str name: the name of the waveform to be created/append to
        @param dict sequence_parameters: dictionary containing the parameters
                                         for a sequence

        @return: int, number of sequence steps written (-1 indicates failed
                 process)
        """
        self.log.warning('PulseBlaster digital pulse generator has no '
                         'sequencing capabilities.\n'
                         'write_sequence call ignored.')
        return -1

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device
                      workspace.
        """

        #FIXME: That seems not to be right. Docstring does not match with output.
        return [self._current_pb_waveform_name]

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device
                      workspace.
        """
        return list()


    def delete_waveform(self, waveform_name):
        """Delete the waveform with name "waveform_name" from the device memory.

        @param str waveform_name: The name of the waveform to be deleted
                                  Optionally a list of waveform names can be
                                  passed.

        @return list: a list of deleted waveform names.
        """
        self.log.info('PulserBlaster does not has any waveform, skip delete '
                      'command.')
        return list()

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory.

        @param str sequence_name: The name of the sequence to be deleted
                                  Optionally a list of sequence names can be passed.

        @return list: a list of deleted sequence names.
        """
        return list()

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
            self.log.error('No interleave functionality available in '
                           'PulseBlaster.\n'
                           'Interleave state is always False.')
        return False

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        return self.reset_device()

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        return False
