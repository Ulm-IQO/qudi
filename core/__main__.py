# -*- coding: utf-8 -*-
"""
Main ACQ4 invocation script
Copyright 2010  Luke Campagnola
Distributed under MIT/X11 license. See license.txt for more infomation.
"""

print("Loading QuDi...")
if __package__ is None:
    import core
    __package__ = 'core'
from pyqtgraph.Qt import QtGui, QtCore

from .Manager import *
import numpy as np

# Pull some args out
if "--profile" in sys.argv:
    profile = True
    sys.argv.pop(sys.argv.index('--profile'))
else:
    profile = False
if "--callgraph" in sys.argv:
    callgraph = True
    sys.argv.pop(sys.argv.index('--callgraph'))
else:
    callgraph = False


## Enable stack trace output when a crash is detected
import faulthandler
faulthandler.disable()
faulthandler.enable(all_threads=True)

## Initialize Qt
app = pg.mkQApp()

## Disable garbage collector to improve stability. 
## (see pyqtgraph.util.garbage_collector for more information)
from pyqtgraph.util.garbage_collector import GarbageCollector
gc = GarbageCollector(interval=1.0, debug=False)

## Create Manager. This configures devices and creates the main manager window.
man = Manager(argv=sys.argv[1:])

## for debugging with pdb
#QtCore.pyqtRemoveInputHook()

## Start Qt event loop unless running in interactive mode.
import pyqtgraph as pg
interactive = (sys.flags.interactive == 1) and not pg.Qt.USE_PYSIDE

## Run python code periodically to allow interactive debuggers to interrupt
## the qt event loop
timer = QtCore.QTimer()
def donothing(*args):
    #print "-- beat --"
    x = 0
    for i in range(0, 100):
        x += i
timer.timeout.connect(donothing)
timer.start(1000)

if interactive:
    print("Interactive mode; not starting event loop.")
    
    ## import some things useful on the command line
    import numpy as np

    ### Use CLI history and tab completion
    import atexit
    import os
    historyPath = os.path.expanduser("~/.pyhistory")
    try:
        import readline
    except ImportError:
        print("Module readline not available.")
    else:
        import rlcompleter
        readline.parse_and_bind("tab: complete")
        if os.path.exists(historyPath):
            readline.read_history_file(historyPath)
    def save_history(historyPath=historyPath):
        try:
            import readline
        except ImportError:
            print("Module readline not available.")
        else:
            readline.write_history_file(historyPath)
    atexit.register(save_history)
else:
    if profile:
        import cProfile
        cProfile.run('app.exec_()', sort='cumulative')  
        # pg.exit() causes python to exit before Qt has
        # a chance to clean up.
        # this avoids otherwise irritating exit crashes.
        pg.exit()

    elif callgraph:
        from pycallgraph import PyCallGraph
        from pycallgraph.output import GraphvizOutput
        with PyCallGraph(output=GraphvizOutput()):
            app.exec_()
    else:
        app.exec_()
        # pg.exit() causes python to exit before Qt has a chance to clean up. 
        # this avoids otherwise irritating exit crashes.
        pg.exit()

