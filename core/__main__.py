# -*- coding: utf-8 -*-
"""
This file contains the QuDi Manager class.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""


# install logging facility
from .logger import initialize_logger
initialize_logger()
import logging
logger = logging.getLogger(__name__)
logger.info('Loading QuDi...')
print('Loading QuDi...')

if __package__ is None:
    import core
    __package__ = 'core'
else:
    import core

from pyqtgraph.Qt import QtCore

from .manager import Manager
from .parentpoller import ParentPollerWindows, ParentPollerUnix
import numpy as np
import pyqtgraph as pg
import core.util.helpers as helpers
import sys
import os



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
            print('\n  QuDi is closed!  Ciao.')
        QtCore.QCoreApplication.instance().quit()

# Possibility to start the program with additional parameters. In the normal
# command line or the console, you can start the program as
#
#   python start.py --profile --callgraph
#
# where "--profile" enables the usage of a profiler and "--callgraph" gives the
# possibility to display the dependencies between the methods/modules.

if '--profile' in sys.argv:
    profile = True
    sys.argv.pop(sys.argv.index('--profile'))   # remove parameter from argv since it is used now.
else:
    profile = False
if '--callgraph' in sys.argv:
    callgraph = True
    sys.argv.pop(sys.argv.index('--callgraph')) # remove parameter from argv since it is used now.
else:
    callgraph = False
if '--manhole' in sys.argv:
    open_manhole = True
    sys.argv.pop(sys.argv.index('--manhole')) # remove parameter from argv since it is used now.
else:
    open_manhole = False
if '-g' in sys.argv or '--no-gui' in sys.argv:
    app = QtCore.QCoreApplication(sys.argv)
else:
    app = pg.mkQApp()

# Enable stack trace output when a crash is detected
import faulthandler
faulthandler.disable()
faulthandler.enable(all_threads=True)

try:
    # Install the pyzmq ioloop. This has to be done before anything else from
    # tornado is imported.
    from zmq.eventloop import ioloop
    ioloop.install()
except:
    logger.error('Preparing ZMQ failed, probably no IPython possible!')

# Disable garbage collector to improve stability.
# (see pyqtgraph.util.garbage_collector in the doc for more information)
from pyqtgraph.util.garbage_collector import GarbageCollector
gc = GarbageCollector(interval=1.0, debug=False)

# Create Manager. This configures devices and creates the main manager window.
# All additional arguments in sys.argv, which were not used and executed here
# are passed to the main device handler, the Manager.
watchdog = AppWatchdog()
man = Manager(argv=sys.argv[1:])
watchdog.setupParentPoller(man)
man.sigManagerQuit.connect(watchdog.quitApplication)

## for debugging with pdb
#QtCore.pyqtRemoveInputHook()

# manhole for debugging stuff inside the app from outside
if open_manhole:
    import manhole
    manhole.install()

# Start Qt event loop unless running in interactive mode and not using PySide.
interactive = (sys.flags.interactive == 1) and not pg.Qt.USE_PYSIDE

if interactive:
    print("Interactive mode; not starting event loop.")

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
    if profile:
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
    elif callgraph:
        from pycallgraph import PyCallGraph
        from pycallgraph.output import GraphvizOutput
        with PyCallGraph(output=GraphvizOutput()):
            app.exec_()
    elif not man.hasGui:
        app.exec_()
        helpers.exit(watchdog.exitcode)
    else:
        app.exec_()
        # helpers.exit() causes python to exit before Qt has a chance to clean up.
        # This avoids otherwise irritating exit crashes.
        helpers.exit(watchdog.exitcode)

