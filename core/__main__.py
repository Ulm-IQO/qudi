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

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

import sys
import os
import argparse
import faulthandler

# if __package__ is None:
#     __package__ = 'core'

# Enable stack trace output for SIGSEGV, SIGFPE, SIGABRT, SIGBUS and SIGILL signals
# -> e.g. for segmentation faults
faulthandler.disable()
faulthandler.enable(all_threads=True)

# parse commandline parameters
parser = argparse.ArgumentParser(prog='start.py')
group = parser.add_mutually_exclusive_group()
group.add_argument('-p', '--profile', action='store_true', help='enables profiler')
group.add_argument('-cg',
                   '--callgraph',
                   action='store_true',
                   help='display dependencies between the methods/modules')
parser.add_argument('-m', '--manhole', action='store_true', help='manhole for debugging purposes')
parser.add_argument(
    '-g', '--no-gui', action='store_true', help='does not load the manager gui module')
parser.add_argument('-c', '--config', default='', help='configuration file')
parser.add_argument('-l', '--logdir', default='', help='log directory')
args = parser.parse_args()

# install logging facility
from .logger import init_rotating_file_handler, get_logger
init_rotating_file_handler(path=args.logdir)
logger = get_logger(__name__)
logger.info('Loading Qudi...')
print('Loading Qudi...')

# Check vital packages for qudi, otherwise qudi will not even start.
from .util import helpers
err_code = helpers.import_check()
if err_code != 0:
    sys.exit(err_code)

# instantiate Qt Application (gui or non-gui)
from qtpy import QtCore
if args.no_gui:
    app = QtCore.QCoreApplication(sys.argv)
else:
    from qtpy import QtWidgets
    app = QtWidgets.QApplication(sys.argv)

# Install the pyzmq ioloop. This has to be done before anything else from tornado is imported.
try:
    from zmq.eventloop import ioloop
    ioloop.install()
except:
    logger.error('Preparing ZMQ failed, probably no IPython possible!')

# Create Manager. This configures devices and creates the main manager window.
# Arguments parsed by argparse are passed to the Manager.
from .manager import Manager
from .watchdog import AppWatchdog
man = Manager(args=args)
watchdog = AppWatchdog(man)

# manhole for debugging stuff inside the app from outside
# if args.manhole:
#     import manhole
#     manhole.install()

# Start Qt event loop unless running in interactive mode
app.exec_()

# first disable our pyqtgraph's cleanup function; won't be needing it.
# try:
#     import pyqtgraph
#     pyqtgraph.setConfigOptions(exitCleanup=False)
# except ImportError:
#     pass

# ToDo: Is the following issue still a thing with qudi?
# in this subprocess we redefine the stdout, therefore on Unix systems we need to handle the opened
# file descriptors, see PEP 446: https://www.python.org/dev/peps/pep-0446/
if sys.platform in ['linux', 'darwin']:
    fd_min, fd_max = 3, 4096
    fd_except = set()
    fd_set = set(range(fd_min, fd_max))

    if sys.platform == 'darwin':
        # trying to close 7 produces an illegal instruction on the Mac.
        fd_except.add(7)

    # remove specified file descriptor
    fd_set = fd_set - fd_except
    for fd in fd_set:
        try:
            os.close(fd)
        except OSError:
            pass

sys.exit(watchdog.exitcode)
