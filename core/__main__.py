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

# Enable stack trace output for SIGSEGV, SIGFPE, SIGABRT, SIGBUS,
# and SIGILL signals
# -> e.g. for segmentation faults
import faulthandler
faulthandler.disable()
faulthandler.enable(all_threads=True)


# parse commandline parameters
import argparse
parser = argparse.ArgumentParser(prog='start.py')
group = parser.add_mutually_exclusive_group()
group.add_argument('-p', '--profile', action='store_true',
        help='enables profiler')
group.add_argument('-cg', '--callgraph', action='store_true',
        help='display dependencies between the methods/modules')
parser.add_argument('-m', '--manhole', action='store_true',
        help='manhole for debugging purposes')
parser.add_argument('-g', '--no-gui', action='store_true',
        help='does not load the manager gui module')
parser.add_argument('-c', '--config', default='', help='configuration file')
args = parser.parse_args()


# install logging facility
from .logger import initialize_logger
initialize_logger()
import logging
logger = logging.getLogger(__name__)
logger.info('Loading Qudi...')
print('Loading Qudi...')


# this loads Qt and makes sure the API version is right with PyQt4
if __package__ is None:
    import core
    __package__ = 'core'
else:
    import core


# define a global variable for the manager
man = None


# install logging facility for Qt errors
import qtpy
from qtpy import QtCore
def qt_message_handler(msgType, msg):
    """
    A message handler handling Qt messages.
    """
    logger = logging.getLogger('Qt')
    if qtpy.PYQT4 or qtpy.PYSIDE:
        msg = msg.decode('utf-8')
    if msgType == QtCore.QtDebugMsg:
        logger.debug(msg)
    elif msgType == QtCore.QtWarningMsg:
        logger.warning(msg)
    elif msgType == QtCore.QtCriticalMsg:
        logger.critical(msg)
    else:
        import traceback
        logger.critical('Fatal error occurred: {0}\n'
                'Traceback:\n'
                '{1}'.format(msg, ''.join(traceback.format_stack())))
        global man
        if man is not None:
            logger.critical('Asking manager to quit.')
            try:
                man.quit()
                QtCore.QCoreApplication.instance().processEvents()
            except:
                logger.exception('Manager failed quitting.')

if qtpy.PYQT4 or qtpy.PYSIDE:
    QtCore.qInstallMsgHandler(qt_message_handler)
else:
    def qt5_message_handler(msgType, context, msg):
        qt_message_handler(msgType, msg)
    QtCore.qInstallMessageHandler(qt5_message_handler)


# instantiate Qt Application (gui or non-gui)
if args.no_gui:
    app = QtCore.QCoreApplication(sys.argv)
else:
    from qtpy import QtWidgets
    app = QtWidgets.QApplication(sys.argv)


# Install the pyzmq ioloop. This has to be done before anything else from
# tornado is imported.
try:
    from zmq.eventloop import ioloop
    ioloop.install()
except:
    logger.error('Preparing ZMQ failed, probably no IPython possible!')


# Disable standard garbage collector and run it from the event loop to
# improve stability.
# (see garbage_collector in the doc for more information)
from .garbage_collector import GarbageCollector
gc = GarbageCollector(interval=1.0, debug=False)


# define a watchdog for our application
from .parentpoller import ParentPollerWindows, ParentPollerUnix


class AppWatchdog(QtCore.QObject):
    """This class periodically runs a function for debugging and handles
      application exit.
    """
    sigDoQuit = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self.alreadyQuit = False
        self.hasGui = False
        self.exitcode = 0
        # Run python code periodically to allow interactive debuggers to interrupt
        # the qt event loop
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.donothing)
        self.timer.start(1000)
        self.sigDoQuit.connect(self.quitApplication)

    def donothing(self):
        """This function does nothing for debugging purposes.
        """
        #print('-- beat -- thread:', QtCore.QThread.currentThreadId())
        x = 0
        for i in range(0, 100):
            x += i

    def setupParentPoller(self, manager):
        self.parent_handle = int(os.environ.get('QUDI_PARENT_PID') or 0)
        self.interrupt = int(os.environ.get('QUDI_INTERRUPT_EVENT') or 0)
        if sys.platform == 'win32':
            if self.interrupt or self.parent_handle:
                self.poller = ParentPollerWindows(lambda: self.quitProxy(manager), self.interrupt, self.parent_handle)
        elif self.parent_handle:
            self.poller = ParentPollerUnix(lambda: self.quitProxy(manager))
        self.poller.start()

    def quitProxy(self, obj):
        print('Parent process is daed, committing sudoku...')
        self.sigDoQuit.emit(obj)

    def quitApplication(self, manager, restart = False):
        """Clean up threads and windows, quit application.

          @param object manager: manager belonging to this application

        """
        if restart:
            # exitcode of 42 signals to start.py that this should be restarted
            self.exitcode = 42
        if not self.alreadyQuit:    # Need this because multiple triggers can
                                    # call this function during quit.
            self.alreadyQuit = True
            self.timer.stop()
            logger.info('Closing windows...')
            print('Closing windows...')
            if manager.hasGui:
                manager.gui.closeWindows()
            QtCore.QCoreApplication.instance().processEvents()
            logger.info('Stopping threads...')
            print('Stopping threads...')
            manager.tm.quitAllThreads()
            QtCore.QCoreApplication.instance().processEvents()
            logger.info('Qudi is closed!  Ciao.')
            print('\n  Qudi is closed!  Ciao.')
        QtCore.QCoreApplication.instance().quit()


# Create Manager. This configures devices and creates the main manager window.
# Arguments parsed by argparse are passed to the Manager.
from .manager import Manager
watchdog = AppWatchdog()
man = Manager(args=args)
watchdog.setupParentPoller(man)
man.sigManagerQuit.connect(watchdog.quitApplication)

## for debugging with pdb
#QtCore.pyqtRemoveInputHook()

# manhole for debugging stuff inside the app from outside
if args.manhole:
    import manhole
    manhole.install()


# Start Qt event loop unless running in interactive mode and not using PySide.
import core.util.helpers as helpers
interactive = (sys.flags.interactive == 1) and not qtpy.PYSIDE

if interactive:
    logger.info('Interactive mode; not starting event loop.')
    print('Interactive mode; not starting event loop.')

    # import some modules which might be useful on the command line
    import numpy as np

    # Use CLI history and tab completion
    import atexit
    import os
    historyPath = os.path.expanduser("~/.pyhistory")
    try:
        import readline
    except ImportError:
        print("Import Error in __main__: Module readline not available.")
    else:
        import rlcompleter
        readline.parse_and_bind("tab: complete")
        if os.path.exists(historyPath):
            readline.read_history_file(historyPath)

    def save_history(historyPath=historyPath):
        try:
            import readline
        except ImportError:
            print("Import Error in __main__: Module readline not available.")
        else:
            readline.write_history_file(historyPath)
    atexit.register(save_history)
else:
    # non-interactive, start application in different modes
    if args.profile:
        # with profiler
        import cProfile, pstats
        from io import StringIO
        pr = cProfile.Profile()
        pr.enable()
        # ... do something ...
        app.exec_()
        pr.disable()
        s = StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
        # helpers.exit() causes python to exit before Qt has
        # a chance to clean up.
        # This avoids otherwise irritating exit crashes.
        helpers.exit(watchdog.exitcode)
    elif args.callgraph:
        # with callgraph
        from pycallgraph import PyCallGraph
        from pycallgraph.output import GraphvizOutput
        with PyCallGraph(output=GraphvizOutput()):
            app.exec_()
    elif not man.hasGui:
        # without gui
        app.exec_()
        helpers.exit(watchdog.exitcode)
    else:
        # start regular
        app.exec_()
        # helpers.exit() causes python to exit before Qt has a chance to
        # clean up.
        # This avoids otherwise irritating exit crashes.
        helpers.exit(watchdog.exitcode)

