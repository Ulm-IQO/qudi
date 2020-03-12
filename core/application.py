# -*- coding: utf-8 -*-
"""
This file contains the Qudi Manager class.

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

import sys
import os
import argparse
import faulthandler


class Qudi:
    """

    """
    def __init__(self, no_gui=False, log_dir=''):
        self.log = None
        self.app = None
        self.manager = None
        self.watchdog = None
        self.no_gui = bool(no_gui)
        self.log_dir = str(log_dir)

    def run(self):
        """

        @return:
        """
        # add qudi to PATH
        qudi_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if qudi_path not in sys.path:
            sys.path.insert(1, qudi_path)
        # Enable stack trace output for SIGSEGV, SIGFPE, SIGABRT, SIGBUS and SIGILL signals
        # -> e.g. for segmentation faults
        faulthandler.disable()
        faulthandler.enable(all_threads=True)

        # install logging facility
        from .logger import init_rotating_file_handler, get_logger
        init_rotating_file_handler(path=self.log_dir)
        self.log = get_logger(__name__)
        self.log.info('Loading Qudi...')
        print('Loading Qudi...')

        # Check Qt API
        from qtpy import API_NAME
        self.log.info('Used Qt API: {0}'.format(API_NAME))
        print('Used Qt API: {0}'.format(API_NAME))

        # Check vital packages for qudi, otherwise qudi will not even start.
        from .util import helpers
        err_code = helpers.import_check()
        if err_code != 0:
            self.exit(err_code)

        # instantiate Qt Application (gui or non-gui)
        if self.no_gui:
            from qtpy import QtCore
            self.app = QtCore.QCoreApplication(sys.argv)
        else:
            from qtpy import QtWidgets
            self.app = QtWidgets.QApplication(sys.argv)

        # Install the pyzmq ioloop.
        # This has to be done before anything else from tornado is imported.
        try:
            from zmq.eventloop import ioloop
            ioloop.install()
        except:
            self.log.error('Preparing ZMQ failed, probably no IPython possible!')

        # Create Manager. This configures devices and creates the main manager window.
        # Arguments parsed by argparse are passed to the Manager.
        from .manager import Manager
        from .watchdog import AppWatchdog
        self.manager = Manager(no_gui=self.no_gui)
        self.watchdog = AppWatchdog()
        self.manager.sigManagerQuit.connect(self.watchdog.quit_application)

        # manhole for debugging stuff inside the app from outside
        # if args.manhole:
        #     import manhole
        #     manhole.install()

        # first disable our pyqtgraph's cleanup function; won't be needing it.
        # try:
        #     import pyqtgraph
        #     pyqtgraph.setConfigOptions(exitCleanup=False)
        # except ImportError:
        #     pass

        # Start Qt event loop unless running in interactive mode
        self.app.exec_()

        # ToDo: Is the following issue still a thing with qudi?
        # in this subprocess we redefine the stdout, therefore on Unix systems we need to handle
        # the opened file descriptors, see PEP 446: https://www.python.org/dev/peps/pep-0446/
        if sys.platform in ('linux', 'darwin'):
            fd_min, fd_max = 3, 4096
            fd_set = set(range(fd_min, fd_max))

            if sys.platform == 'darwin':
                # trying to close 7 produces an illegal instruction on the Mac.
                fd_set.remove(7)

            # remove specified file descriptor
            for fd in fd_set:
                try:
                    os.close(fd)
                except OSError:
                    pass

        # Exit application
        self.exit(self.watchdog.exitcode)

    def exit(self, exit_code):
        sys.exit(exit_code)
