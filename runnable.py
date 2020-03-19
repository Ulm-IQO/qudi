#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
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

import subprocess
import ctypes
import sys
import os


if sys.platform == 'win32':
    def create_interrupt_event():
        """Create an interrupt event handle.

        The parent process should call this to create the
        interrupt event that is passed to the child process. It should store
        this handle and use it with ``send_interrupt`` to interrupt the child
        process.
        """

        # Create a security attributes struct that permits inheritance of the
        # handle by new processes.
        # FIXME: We can clean up this mess by requiring pywin32 for IPython.
        class SECURITY_ATTRIBUTES(ctypes.Structure):
            """ MS Windows security attributes """
            _fields_ = [("nLength", ctypes.c_int),
                        ("lpSecurityDescriptor", ctypes.c_void_p),
                        ("bInheritHandle", ctypes.c_int)]

        sa = SECURITY_ATTRIBUTES()
        sa_p = ctypes.pointer(sa)
        sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        sa.lpSecurityDescriptor = 0
        sa.bInheritHandle = 1
        return ctypes.windll.kernel32.CreateEventA(sa_p,  # lpEventAttributes
                                                   False,  # bManualReset
                                                   False,  # bInitialState
                                                   '')  # lpName

    def send_interrupt(interrupt_handle):
        """ Sends an interrupt event using the specified handle.
        """
        ctypes.windll.kernel32.SetEvent(interrupt_handle)


def main():
    """
    """
    myenv = os.environ.copy()

    if sys.platform == 'win32':
        # Create a Win32 event for interrupting the kernel and store it in an environment variable.
        interrupt_event = create_interrupt_event()
        myenv["QUDI_INTERRUPT_EVENT"] = str(interrupt_event)
        try:
            from _winapi import DuplicateHandle, GetCurrentProcess
            from _winapi import DUPLICATE_SAME_ACCESS, CREATE_NEW_PROCESS_GROUP
        except ImportError:
            from _subprocess import DuplicateHandle, GetCurrentProcess
            from _subprocess import DUPLICATE_SAME_ACCESS, CREATE_NEW_PROCESS_GROUP
        pid = GetCurrentProcess()
        handle = DuplicateHandle(pid, pid, pid, 0, True, DUPLICATE_SAME_ACCESS)
        myenv['QUDI_PARENT_PID'] = str(int(handle))
    else:
        myenv['QUDI_PARENT_PID'] = str(os.getpid())

    argv = [sys.executable, '-m', 'core'] + sys.argv[1:]
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    while True:
        process = subprocess.Popen(argv,
                                   close_fds=False,
                                   env=myenv,
                                   stdin=sys.stdin,
                                   stdout=sys.stdout,
                                   stderr=sys.stderr,
                                   shell=False)
        try:
            retval = process.wait()
            if retval == 0:
                break
            elif retval == 42:
                print('Restarting...')
                continue
            elif retval == 2:
                # invalid commandline argument
                break
            elif retval == -6:
                # called if QFatal occurs
                break
            elif retval == 4:
                print('Import Error: Qudi could not be started due to missing packages.')
                sys.exit(retval)
            else:
                print('Unexpected return value {0}. Exiting.'.format(retval))
                sys.exit(retval)
        except KeyboardInterrupt:
            print('Keyboard Interrupt, quitting!')
            break
        except:
            process.kill()
            process.wait()
            raise


if __name__ == '__main__':
    main()
