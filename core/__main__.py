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

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

print('Loading QuDi...')
if __package__ is None:
    import core
    __package__ = 'core'
else:
    import core
    
from pyqtgraph.Qt import QtGui, QtCore

from .Manager import Manager
import numpy as np
import pyqtgraph as pg
import sys


class AppWatchdog(QtCore.QObject):
    """This class periodically runs a function for debugging and handles
      application exit.
    """

    def __init__(self):
        super().__init__()
        self.alreadyQuit = False
        # Run python code periodically to allow interactive debuggers to interrupt
        # the qt event loop
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.donothing)
        self.timer.start(1000)

    def donothing(self):
        """This function does nothing for debugging purposes.
        """
        #print('-- beat -- thread:', QtCore.QThread.currentThreadId())
        x = 0
        for i in range(0, 100):
            x += i

    def quitApplication(self, manager):
        """Clean up threads and windows, quit application.

          @param object manager: manager belonging to this application

        """
        if not self.alreadyQuit:    # Need this because multiple triggers can 
                                    # call this function during quit.
            self.alreadyQuit = True
            self.timer.stop()
            manager.logger.print_logMsg("Closing windows..", msgType='status')
            QtGui.QApplication.instance().closeAllWindows()
            QtGui.QApplication.instance().processEvents()
            manager.logger.print_logMsg("Stopping threads..", msgType='status')
            manager.tm.quitAllThreads()
            QtGui.QApplication.instance().processEvents()
            print("\n  QuDi is closed!  Ciao.")
        QtGui.QApplication.quit()

# Possibility to start the program with additional parameters. In the normal 
# command line or the console, you can start the program as
#
#   python start.py --profile --callgraph
#
# where "--profile" enables the usage of a profiler and "--callgraph" gives the
# possibility to display the dependencies between the methods/modules.

if "--profile" in sys.argv:
    profile = True
    sys.argv.pop(sys.argv.index('--profile'))   # remove parameter from argv
                                                # since it is used now.
else:
    profile = False
if "--callgraph" in sys.argv:
    callgraph = True
    sys.argv.pop(sys.argv.index('--callgraph')) # remove parameter from argv
                                                # since it is used now.
else:
    callgraph = False


# Enable stack trace output when a crash is detected
import faulthandler
faulthandler.disable()
faulthandler.enable(all_threads=True)


# Disable garbage collector to improve stability. 
# (see pyqtgraph.util.garbage_collector in the doc for more information)
from pyqtgraph.util.garbage_collector import GarbageCollector
gc = GarbageCollector(interval=1.0, debug=False)

# Create Manager. This configures devices and creates the main manager window.
# All additional arguments in sys.argv, which were not used and executed here
# are passed to the main device handler, the Manager.
man = Manager(argv=sys.argv[1:])
watchdog = AppWatchdog()
man.sigManagerQuit.connect(watchdog.quitApplication)

## for debugging with pdb
#QtCore.pyqtRemoveInputHook()

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
        import cProfile
        cProfile.run('core.app.exec_()', sort='cumulative')  
        # pg.exit() causes python to exit before Qt has
        # a chance to clean up.
        # This avoids otherwise irritating exit crashes.
        pg.exit()

    elif callgraph:
        from pycallgraph import PyCallGraph
        from pycallgraph.output import GraphvizOutput
        with PyCallGraph(output=GraphvizOutput()):
            core.app.exec_()
    else:
        core.app.exec_()
        # pg.exit() causes python to exit before Qt has a chance to clean up. 
        # This avoids otherwise irritating exit crashes.
        pg.exit()

