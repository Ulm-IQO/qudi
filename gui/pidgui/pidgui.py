# -*- coding: utf-8 -*-
# Test gui (test)

from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui, uic
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg
import os

# Rather than import the ui*.py file here, the ui*.ui file itself is loaded by uic.loadUI in the QtGui classes below.

class PIDMainWindow(QtGui.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pid_control.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class PIDGui(GUIBase):
    """ FIXME: Please document
    """
    _modclass = 'pidgui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'pidlogic': 'PIDLogic'}

    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI, 'ondeactivate': self.deactivation}
        super().__init__(
                    manager,
                    name,
                    config,
                    c_dict)

        self.logMsg('The following configuration was found.', msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        self._pid_logic = self.connector['in']['pidlogic']['object']
        
        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = PIDMainWindow()
                
        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
                
        # Plot labels.
        self._pw = self._mw.trace_PlotWidget

        self._pw.setLabel('left', 'Process Value', units='unit')
        self._pw.setLabel('right', 'Conteol Value', units='unit')
        self._pw.setLabel('bottom', 'Time', units='s')

        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen('g')
        self._curve2 = self._pw.plot()
        self._curve2.setPen('r', width=4)
        self._curve3 = self._pw.plot()
        self._curve3.setPen('b', width=2)

        # setting the x axis length correctly
        self._pw.setXRange(0, self._pid_logic.getBufferLength()*self._pid_logic.timestep)
        
        #####################
        # Setting default parameters
        self._mw.P_DoubleSpinBox.setValue( self._pid_logic.kP )
        self._mw.I_DoubleSpinBox.setValue( self._pid_logic.kI )
        self._mw.D_DoubleSpinBox.setValue( self._pid_logic.kD )

        # make correct button state
        self._mw.start_control_Action.setChecked(self._pid_logic.enable or self._pid_logic.countdown >= 0)

        #####################
        # Connecting user interactions
        self._mw.start_control_Action.triggered.connect(self.start_clicked)
        self._mw.record_control_Action.triggered.connect(self.save_clicked)

        self._mw.P_DoubleSpinBox.valueChanged.connect( self.kPChanged )
        self._mw.I_DoubleSpinBox.valueChanged.connect( self.kIChanged )
        self._mw.D_DoubleSpinBox.valueChanged.connect( self.kDChanged )
            
        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        #####################
        # starting the physical measurement
        self.sigStart.connect(self._pid_logic.startLoop)
        self.sigStop.connect(self._pid_logic.stopLoop)

        self._pid_logic.sigNewValue.connect(self.updateData)
        
    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def deactivation(self, e):
        # FIXME: !
        self._mw.close()

    def updateData(self, value):
        """ The function that grabs the data and sends it to the plot.
        """
            
        if self._pid_logic.enable:
            self._mw.process_value_Label.setText('{0:,.3f}'.format(self._pid_logic.history[0, -1]))
            self._mw.control_value_Label.setText('{0:,.3f}'.format(self._pid_logic.history[1, -1]))
            self._mw.setpoint_value_Label.setText('{0:,.3f}'.format(self._pid_logic.history[2, -1]))
            self._curve1.setData(y=self._pid_logic.history[0], x=np.arange(0, self._pid_logic.getBufferLength()) * self._pid_logic.timestep)
            self._curve2.setData(y=self._pid_logic.history[1], x=np.arange(0, self._pid_logic.getBufferLength()) * self._pid_logic.timestep)
            self._curve3.setData(y=self._pid_logic.history[2], x=np.arange(0, self._pid_logic.getBufferLength()) * self._pid_logic.timestep)

        if self._pid_logic.getSavingState():
            self._mw.record_control_Action.setText('Save')
        else:
            self._mw.record_control_Action.setText('Start Saving Data')
            
        if self._pid_logic.enable:
            self._mw.start_control_Action.setText('Stop')
        else:            
            self._mw.start_control_Action.setText('Start')
            
            
    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._pid_logic.enable:
            self._mw.start_control_Action.setText('Start')
            self.sigStop.emit()
        else:
            self._mw.start_control_Action.setText('Stop')
            self.sigStart.emit()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        if self._pid_logic.getSavingState():
            self._mw.record_counts_Action.setText('Start Saving Data')
            self._pid_logic.saveData()
        else:
            self._mw.record_counts_Action.setText('Save')
            self._pid_logic.startSaving()
    
    def kPChanged(self):
        self._pid_logic.kP = self._mw.P_DoubleSpinBox.value()

    def kIChanged(self):
        self._pid_logic.kI = self._mw.I_DoubleSpinBox.value()

    def kDChanged(self):
        self._pid_logic.kD = self._mw.D_DoubleSpinBox.value()

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.pid_trace_DockWidget.show()
        self._mw.pid_parameters_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.pid_trace_DockWidget.setFloating(False)
        self._mw.pid_parameters_DockWidget.setFloating(False)
        
        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.pid_trace_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.pid_parameters_DockWidget)
