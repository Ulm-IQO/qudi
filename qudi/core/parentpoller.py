# -*- coding: utf-8 -*-
"""
Parent poller mechanism from IPython.

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

Copyright (c) 2015 IPython Development Team.
See documentation/BSDLicense_IPython.md for details.
Also distributable under the terms of the Modified BSD License.
"""
import ctypes
import os
import platform
# import signal
import time
# from _thread import interrupt_main
from threading import Thread
import logging
logger = logging.getLogger(__name__)


# def waitForClose():
#     """ Wait for program to close on its own and print some old school meme in the meantime.
#     """
#     time.sleep(1)
#     print('> Mechanic: Somebody set us up the bomb.')
#     time.sleep(2)
#     print('> CATS: All your base are belong to us.')
#     time.sleep(2)
#     print('> CATS: You have no chance to survive make your time.')
#     time.sleep(2)
#     print('> Captain: Take off every \'ZIG\'.')
#     time.sleep(2)
#     print('> Captain: For great justice.')


class ParentPollerUnix(Thread):
    """ A Unix-specific daemon thread that terminates the program immediately
    when the parent process no longer exists.
    """

    def __init__(self, quit_function=None):
        """ Create the parentpoller.

            @param callable quitfunction: function to run before exiting
        """
        if quit_function is None:
            pass
        elif not callable(quit_function):
            raise TypeError('argument quit_function must be a callable.')
        super().__init__()
        self.daemon = True
        self.quit_function = quit_function

    def run(self):
        """ Run the parentpoller.
        """
        # We cannot use os.waitpid because it works only for child processes.
        from errno import EINTR
        while True:
            try:
                if os.getppid() == 1:
                    if self.quit_function is None:
                        logger.critical('Parent process died!')
                    else:
                        logger.critical('Parent process died! Qudi shutting down...')
                        self.quit_function()
                    return
            except OSError as e:
                if e.errno == EINTR:
                    continue
                raise
            time.sleep(1)


class ParentPollerWindows(Thread):
    """ A Windows-specific daemon thread that listens for a special event that signals an interrupt
    and, optionally, terminates the program immediately when the parent process no longer exists.
    """

    def __init__(self, parent_handle, quit_function=None):
        """ Create the parent poller.

        @param callable quit_function: Function to call for shutdown if parent process is dead.
        @param int parent_handle: The program will terminate immediately when this handle is
                                  signaled.
        """
        if quit_function is None:
            pass
        elif not callable(quit_function):
            raise TypeError('argument quit_function must be a callable.')
        super().__init__()
        self.daemon = True
        self.quit_function = quit_function
        self.parent_handle = parent_handle

    def run(self):
        """ Run the poll loop. This method never returns.
        """
        try:
            from _winapi import WAIT_OBJECT_0, INFINITE
        except ImportError:
            from _subprocess import WAIT_OBJECT_0, INFINITE

        # Build the list of handle to listen on.
        handle_list = [self.parent_handle]
        arch = platform.architecture()[0]
        c_int = ctypes.c_int64 if arch.startswith('64') else ctypes.c_int

        # Listen forever.
        while True:
            result = ctypes.windll.kernel32.WaitForMultipleObjects(
                len(handle_list),                           # nCount
                (c_int * len(handle_list))(*handle_list),   # lpHandles
                False,                                      # bWaitAll
                10000)                                      # dwMilliseconds

            if result >= len(handle_list):
                # Nothing happened. Probably timed out.
                continue
            elif result < WAIT_OBJECT_0:
                # wait failed, just give up and stop polling.
                logger.critical("Parent poll failed!!!!!")
                return
            else:
                handle = handle_list[result - WAIT_OBJECT_0]
                if handle == self.parent_handle:
                    if self.quit_function is None:
                        logger.critical('Parent process died!')
                    else:
                        logger.critical('Parent process died! Qudi shutting down...')
                        self.quit_function()
                    return

