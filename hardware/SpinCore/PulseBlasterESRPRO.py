# -*- coding: utf-8 -*-


import ctypes
import platform
import os
from collections import OrderedDict
from core.Base import Base

class PulseBlasterESRPRO():
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
    """

    def __init__(self,manager, name, config = {}, **kwargs):
        
        state_actions = {'onactivate'   : self.activation,
                         'ondeactivate' : self.deactivation}

        Base.__init__(self, manager, name, configuation=config, 
                      state_actions, **kwargs)
                      
        self._modclass = 'PulseBlasterESRPRO'
        self._modtype = 'hardware'  

        # declare connectors
        self.connector['out']['PulseBlasterESRPRO'] = OrderedDict()
        self.connector['out']['PulseBlasterESRPRO']['class'] = 'PulseBlasterESRPRO'                    

    def activation(self, e):
        """Set should be happen if the hardware is activated. """
        
        # Check the platform architecture:
        arch = platform.architecture()
        if arch == ('32bit', 'WindowsPE'):
            libname = 'spinapi.dll'
        elif arch == ('64bit', 'WindowsPE'):
            libname = 'spinapi64.dll'
        elif arch == ('32bit', 'ELF'):
            folderpath = self.get_main_dir() + '\\hardware\\SpinCore\\'
            libname = os.path.join(folderpath, 'libspinapi.so')
        elif arch == ('64bit', 'ELF'):
            folderpath = self.get_main_dir() + '\\hardware\\SpinCore\\'
            libname = os.path.join(folderpath, 'libspinapi64.so')

        # In Windows load the spinapi library file spinapi.dll from the folder
        # <Windows>/System32/. For Unix systems, the shared object (=so) file
        # muss be within the same directory, where the file is situated.
        self._dll = ctypes.cdll.LoadLibrary(libname)

        self.open_connection()

    def deactivation(self, e):
        """Set what happens if the hardware is deactivated. """
        self.close_connection()
        
    # =========================================================================
    # Below all the low level routines which are wrapped with ctypes which
    # are talking directly to the hardware via the SpinAPI dll library.
    # =========================================================================

    def logMsg(self,msg, importance=5, msgType='status'):
        print(msg,'\nStatus:',msgType)

    def check(self, func_val):
        """ Check routine for the received error codes.

        @param func_val int: return error code of the called function.

        @return int: pass the error code further so that other functions have
                     the possibility to use it.

        Each called function in the dll has an 32-bit return integer, which
        indicates, whether the function was called and finished successfully
        (then func_val = 0) or if any error has occured (func_val < 0). The
        errorcode, which corresponds to the return value can be looked up in
        the file 'errorcodes.h'.
        """

        if not func_val == 0:

            err_str = self.get_error_string()

            self.logMsg('Error in PulseBlaster with errorcode {0}:\n'
                        '{1}'.format(func_val, err_str),
                        msgType='error')
        return func_val
        
    def get_error_string(self): 
        """ Return the most recent error string.
        
        @return string: A string describing the last error is returned. A 
                        string containing "No Error" is returned if the last 
                        function call was successfull.
        
        Anytime a function (such as pb_init(), pb_start_programming(), etc.) 
        encounters an error, this function will return a description of what 
        went wrong.
        """
        self._dll.pb_get_error.restype = ctypes.c_char_p 
            
            # The output value of this function is as decladed above a pointer
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

    def select_board(self,board_num=0):
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
        if not isinstance( board_num, int ):
            self.logMsg('PulseBlaster cannot choose a board, since an integer '
                        'type was expected, but the following value was '
                        'passed:\n{0}'.format(board_num), msgType='error')
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
        
        @return : Return a pointer to a C string containing the version string.
        """
        self._dll.pb_get_firmware_id.restype = ctypes.c_uint

        firmware_id = self._dll.pb_get_firmware_id()        
        
        if firmware_id == 0 :
            self.logMsg('Retrieving the Firmware ID is not a feature of this ' 
                        'board', msgType='status')
        
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
        return self.check(self._dll.pb_close())

    def start_programming(self, program=0):
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
        return self.check(self._dll.pb_start_programming(program))

    def stop_programming(self):
        """ Finishes the programming for a specific onboard devices.
        
        @return int: A negative number is returned on failure, and spinerr is 
                     set to a description of the error. 0 is returned on 
                     success.
        """
        return self.check(self._dll.pb_stop_programming())

    def set_core_clock(self,clock_freq):
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

        # it seems that the spin api has no return value for that funtion
        # there is no get_core_clock method available. Strange.
        self._dll.pb_core_clock.restype = ctypes.c_void_p
        self._dll.pb_core_clock(ctypes.c_double(clock_freq))

    def write_pulse(self, flags, inst, inst_data, length):
        """Instruction programming function for boards without a DDS. 
        
        @param umsigned int flags: Set every bit to one for each flag you want 
                                   to set high
        @param int inst: Specify the instruction you want. Valid instructions 
                         are:
                         Opcode #	Instruction	Meaning of inst_data field
                             0    CONTINUE          Not Used
                             1    STOP              Not Used
                             2    LOOP              Number of desired loops
                             3    END_LOOP          Address of instruction 
                                                    originating loop
                             4    JSR               Address of first 
                                                    instruction in subroutine
                             5    RTS               Not Used
                             6    BRANCH            Address of instruction to 
                                                    branch to
                             7    LONG_DELAY        Number of desired 
                                                    repetitions
                             8    WAIT              Not Used 
        @param int inst_data: Instruction specific data. Internally this is a 
                              20 bit unsigned number, so the largest value that
                              can be passed is 2^20-1 (the largest value 
                              possible for a 20 bit number). See above table 
                              to find out what this means for each instruction. 
        @param double length: Length of this instruction in nanoseconds. 
        
        @return int: The address of the created instruction is returned. This 
                     can be used as the branch address for any branch 
                     instructions. A negative number is returned on failure, 
                     and spinerr is set to a description of the error.
        
        (DDS = Direct Digital Synthesis). The old version of this command was
        'pb_set_clock', which is still valid, but should not be used.
        """

        length = ctypes.c_double(length)        
        
        self.check(self._dll.pb_inst_pbonly(flags,inst,inst_data,length))

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




