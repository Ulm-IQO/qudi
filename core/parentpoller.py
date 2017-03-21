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
import signal
import time
from _thread import interrupt_main
from threading import Thread
import logging
logger = logging.getLogger(__name__)

def waitForClose():
    """ Wait for program to close on its own and print some old school meme in the meantime.
    """
    time.sleep(1)
    print('> Mechanic: Somebody set us up the bomb.')
    time.sleep(2)
    print('> CATS: All your base are belong to us.')
    time.sleep(2)
    print('> CATS: You have no chance to survive make your time.')
    time.sleep(2)
    print('> Captain: Take off every \'ZIG\'.')
    time.sleep(2)
    print('> Captain: For great justice.')


class ParentPollerUnix(Thread):
    """ A Unix-specific daemon thread that terminates the program immediately
    when the parent process no longer exists.
    """

    def __init__(self, quitfunction=None):
        """ Create the parentpoller.

            @param callable quitfunction: function to run before exiting
        """
        super().__init__()
        self.daemon = True
        self.quitfunction = quitfunction

    def run(self):
        """ Run the parentpoller.
        """
        # We cannot use os.waitpid because it works only for child processes.
        from errno import EINTR
        while True:
            try:
                if os.getppid() == 1:
                    if hasattr(self.quitfunction, '__call__'):
                        self.quitfunction()
                    waitForClose()
                    os._exit(1)
                time.sleep(1.0)
            except OSError as e:
                if e.errno == EINTR:
                    continue
                raise


class ParentPollerWindows(Thread):
    """ A Windows-specific daemon thread that listens for a special event that
    signals an interrupt and, optionally, terminates the program immediately
    when the parent process no longer exists.
    """

    def __init__(self, quitfunction=None, interrupt_handle=None, parent_handle=None):
        """ Create the poller. At least one of the optional parameters must be
        provided.

        Parameters
        ----------
        interrupt_handle : HANDLE (int), optional
            If provided, the program will generate a Ctrl+C event when this
            handle is signaled.

        parent_handle : HANDLE (int), optional
            If provided, the program will terminate immediately when this
            handle is signaled.
        """
        assert(interrupt_handle or parent_handle)
        super().__init__()
        self.daemon = True
        self.interrupt_handle = interrupt_handle
        self.parent_handle = parent_handle

    def run(self):
        """ Run the poll loop. This method never returns.
        """
        try:
            from _winapi import WAIT_OBJECT_0, INFINITE
        except ImportError:
            from _subprocess import WAIT_OBJECT_0, INFINITE

        # Build the list of handle to listen on.
        handles = []
        if self.interrupt_handle:
            handles.append(self.interrupt_handle)
        if self.parent_handle:
            handles.append(self.parent_handle)
        arch = platform.architecture()[0]
        c_int = ctypes.c_int64 if arch.startswith('64') else ctypes.c_int

        # Listen forever.
        while True:
            result = ctypes.windll.kernel32.WaitForMultipleObjects(
                len(handles),                            # nCount
                (c_int * len(handles))(*handles),        # lpHandles
                False,                                   # bWaitAll
                INFINITE)                                # dwMilliseconds

            if WAIT_OBJECT_0 <= result < len(handles):
                handle = handles[result - WAIT_OBJECT_0]

                if handle == self.interrupt_handle:
                    # check if signal handler is callable
                    # to avoid 'int not callable' error (Python issue #23395)
                    if callable(signal.getsignal(signal.SIGINT)):
                        interrupt_main()

                elif handle == self.parent_handle:
                    if hasattr(self.quitfunction, '__call__'):
                        self.quitfunction()
                    waitForClose()
                    os._exit(1)
            elif result < 0:
                # wait failed, just give up and stop polling.
                logger.critical("Parent poll failed!!!!!")
                return
