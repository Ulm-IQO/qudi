# -*- coding: utf-8 -*-

from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui, uic
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg
import os

# Rather than import the ui*.py file here, the ui*.ui file itself is loaded by uic.loadUI in the QtGui classes below.

class SimpleMainWindow(QtGui.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_simpledata_gui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class SimpleDataGui(GUIBase):
    """ FIXME: Please document
    """
    _modclass = 'simplegui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'simplelogic': 'SimpleDataLogic'}

    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)
        self.logMsg('The following configuration was found.', msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        self._simple_logic = self.connector['in']['simplelogic']['object']
        
        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = SimpleMainWindow()
                
        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
                
        # Plot labels.
        self._pw = self._mw.trace_PlotWidget
        
        self.plot1 = self._pw.plotItem
        self.plot1.setLabel('left', 'Some Value', units='some unit', color='#00ff00')
        self.plot1.setLabel('bottom', 'Number of values', units='some unit')

        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = self.plot1.plot()
        self._curve1.setPen('g')

        # make correct button state
        self._mw.startAction.setChecked(False)

        #####################
        # Connecting user interactions
        self._mw.startAction.triggered.connect(self.start_clicked)
        self._mw.recordAction.triggered.connect(self.save_clicked)

        #####################
        # starting the physical measurement
        self.sigStart.connect(self._simple_logic.startMeasure)
        self.sigStop.connect(self._simple_logic.stopMeasure)

        self._simple_logic.sigRepeat.connect(self.updateData)
        
    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def deactivation(self, e):
        # FIXME: !
        self._mw.close()

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """
        self._curve1.setData(
            y=self._simple_logic.buf,
            x=np.arange(0, len(self._simple_logic.buf))
            )

        if self._simple_logic.getState() == 'locked':
            self._mw.startAction.setText('Stop')
        else:            
            self._mw.startAction.setText('Start')

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._simple_logic.getState() == 'locked':
            self._mw.startAction.setText('Start')
            self.sigStop.emit()
        else:
            self._mw.startAction.setText('Stop')
            self.sigStart.emit()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        return 
