# -*- coding: utf-8 -*-

"""
This file contains the qudi application watchdog.

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

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

import os
import sys
from qtpy import QtCore
from .parentpoller import ParentPollerWindows, ParentPollerUnix
from .logger import get_logger
from .threadmanager import ThreadManager

logger = get_logger(__name__)


class AppWatchdog(QtCore.QObject):
    """This class periodically runs a function for debugging and handles application exit.
    """
    _sigDoQuit = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self._quit_in_progress = False
        self.exitcode = 0
        # Run python code periodically to allow interactive debuggers to interrupt the qt event loop
        self.__timer = QtCore.QTimer()
        self.__timer.timeout.connect(self.do_nothing)
        self.__timer.start(1000)
        self._sigDoQuit.connect(self.quit_application)

        self.parent_handle = None
        self.interrupt = None
        self.parent_poller = None
        self.setup_parent_poller()
        return

    @QtCore.Slot()
    def do_nothing(self):
        """This function does nothing for debugging purposes.
        """
        x = 0
        for i in range(100):
            x += i
        return

    def setup_parent_poller(self):
        """Set up parent poller to find out when parent process is killed.
        """
        self.parent_handle = int(os.environ.get('QUDI_PARENT_PID') or 0)
        self.interrupt = int(os.environ.get('QUDI_INTERRUPT_EVENT') or 0)
        if sys.platform == 'win32':
            if self.interrupt or self.parent_handle:
                self.parent_poller = ParentPollerWindows(
                    self.quit_proxy, self.interrupt, self.parent_handle)
                self.parent_poller.start()
        elif self.parent_handle:
            self.parent_poller = ParentPollerUnix(self.quit_proxy)
            self.parent_poller.start()
        else:
            logger.warning('Qudi running unsupervised. Restart will not work.')

    def quit_proxy(self):
        """Helper function to emit doQuit signal
        """
        print('Parent process is dead, committing sudoku...')
        self._sigDoQuit.emit()

    def quit_application(self, restart=False):
        """Clean up threads and windows, quit application.

        @param bool restart: flag indicating if the exitcode should indicate a restart
        """
        if restart:
            # exitcode of 42 signals to start.py that this should be restarted
            self.exitcode = 42
        # Need this flag because multiple triggers can call this function during quit.
        if not self._quit_in_progress:
            self._quit_in_progress = True
            self.__timer.stop()
            QtCore.QCoreApplication.instance().processEvents()
            logger.info('Stopping threads...')
            print('Stopping threads...')
            thread_manager = ThreadManager.instance()
            if thread_manager is not None:
                thread_manager.quit_all_threads()
            QtCore.QCoreApplication.instance().processEvents()
            logger.info('Qudi is closed!  Ciao.')
            print('\n  Qudi is closed!  Ciao.')
            QtCore.QCoreApplication.instance().quit()
