# -*- coding: utf-8 -*-


import ctypes
import sys
import os











class PulseBlasterESRPRO():
    """ UNSTABLE: ALEX

    Hardware class to control the PulseBlasterESR-PRO card from SpinCore.

    This file is compatible with the PCI version SP18A of the PulseBlasterESR.
    The wrapped commands based on the 'spinapi.h' header file and can be looked
    up in the SpinAPI Documentation on the website:

    http://www.spincore.com/support/spinapi/reference/production/2013-09-25/index.html

    or for an other version (not recommended):
    http://www.spincore.com/support/spinapi/reference/production/2010-07-14/index.html
    """

#http://www.bkprecision.com/support/downloads/function-and-arbitrary-waveform-generator-guidebook.html

    def __init__(self):


        # Load the spinapi.dll from the folder <Windows>/System32/

        # Load the spinapi library file spinapi.dll from the folder
        # <Windows>/System32/



        # Check the platform architecture:
        arch = sys.platform.architecture()
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

        self._dll = ctypes.cdll.LoadLibrary(libname)


        self.initialize()





    # =========================================================================
    # Below are all the low level routines which are wrapped with ctypes which
    # are talking directly to the hardware via the SpinAPI dll library.
    # =========================================================================

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

            self._dll.pb_get_error.restype = ctypes.c_char_p
            err_str = self._dll.pb_get_error()


            self.logMsg('Error in PulseBlaster with errorcode {0}:\n'
                        '{1}'.format(func_val, err_str),
                        msgType='error')
        return func_val

    def count_boards(self):
        """ Return the number of SpinCore boards present in your system.

        @return int: The number of boards present is returned. -1 is returned
                     on error, and spinerr is set to a description of the
                     error.
        """

        self._dll.pb_count_boards.restype = ctypes.c_int
        return self._dll.pb_count_boards

    def select_board(self,board_num):
        """ Select the proper SpinCore card, if multiple are present.

        @param int board_num: Specifies which board to select. Counting starts at 0.

        If multiple boards from SpinCore Technologies are present in your
        system, this function allows you to select which board to talk to. Once
        this function is called, all subsequent commands (such as pb_init(),
        pb_core_clock(), etc.) will be sent to the selected board. You may
        change which board is selected at any time.
        If you have only one board, it is not necessary to call this function.
        """

        self.check(self._dll.pb_select_board)

    def get_version(self):
        """Get the version of this library. 
        
        @return string: A string indicating the version of this library is 
                        returned. The version is a string in the form YYYYMMDD. 
        """
        self._dll.spinpts_get_version.restype = ctypes.c_char_p
        return self._dll.spinpts_get_version()

    def get_firmware_id(self):
        """Gets the current version of the SpinPTS API being used. 
        
        @return : Returns a pointer to a C string containing the version string."""
        self._dll.pb_get_firmware_id.restype = ctypes.c_uint
        return self._dll.pb_get_firmware_id()

    def start(self):
        self._dll.pb_start()


    def initialize(self):
        """Initializes the board. 
        
        @return int: A negative number is returned on failure, and spinerr is 
                     set to a description of the error. 0 is returned on 
                     success.
        """
        val = self.check(self._dll.pb_init())
        return val

    def close_connection(self):
        self._dll.pb_close()

    def start_programming(self):
        self._dll.pb_start_programming()

    def stop_programming(self):
        self._dll.pb_stop_programming()

    def set_clock(self):
        self._dll.pb_set_clock()

    def write_pulse(self):
        self._dll.pb_inst_pbonly()

    def pb_read_status(self):
        self._dll.pb_read_status.restype = ctypes.c_uint32
        status = self._dll.pb_read_status()

#        # convert to reversed binary string
#        # convert to binary string, and remove 0b
#        status = bin(status)[2:]
#        # reverse string
#        status = status[::-1]
#        # pad to make sure we have enough bits!
#        status = status + "0000"
#
#        return {"stopped":bool(int(status[0])),"reset":bool(int(status[1])),"running":bool(int(status[2])), "waiting":bool(int(status[3]))}



    def set_core_clock(self,clock_freq):
        """Tell the library what clock frequency the board uses.
        
        @return int: Frequency of the clock in MHz. 
        
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

        self._dll.pb_core_clock.restype = ctypes.c_void_p
         
        return self._dll.pb_core_clock(ctypes.c_double(clock_freq)) # returns void, so ignore return value.
    # =========================================================================
    # Below are all the higher level routines are situated which use the
    # wrapped routines as a basis to perform the desired task.
    # =========================================================================




