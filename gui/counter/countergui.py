# -*- coding: utf-8 -*-
# Test gui (test)

from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui, uic
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg
import os

# Rather than import the ui*.py file here, the ui*.ui file itself is loaded by uic.loadUI in the QtGui classes below.

class CounterMainWindow(QtGui.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_slow_counter.ui')

        # Load it
        super(CounterMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class CounterGui(GUIBase):
    """ FIXME: Please document
    """
    _modclass = 'countergui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'counterlogic1': 'CounterLogic'}

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI, 'ondeactivate': self.deactivation}
        super().__init__(
                    manager,
                    name,
                    config,
                    c_dict)

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        self._counting_logic = self.connector['in']['counterlogic1']['object']
        
        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = CounterMainWindow()
                
        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
                
        # Plot labels.
        self._pw = self._mw.counter_trace_PlotWidget

        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('bottom', 'Time', units='s')

        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen('g')
        self._curve2 = self._pw.plot()
        self._curve2.setPen('r', width=4)

        if self._counting_logic._counting_device._photon_source2 is not None:
            self._curve3 = self._pw.plot()
            self._curve3.setPen('b')
            self._curve4 = self._pw.plot()
            self._curve4.setPen('b', width=4)
        
        # setting the x axis length correctly
        self._pw.setXRange(0, self._counting_logic.get_count_length()/self._counting_logic.get_count_frequency())
        
        #####################
        # Setting default parameters
        self._mw.count_length_SpinBox.setValue( self._counting_logic.get_count_length() )
        self._mw.count_freq_SpinBox.setValue( self._counting_logic.get_count_frequency() )
        self._mw.oversampling_SpinBox.setValue( self._counting_logic.get_counting_samples() )

        #####################
        # Connecting user interactions
        self._mw.start_counter_Action.triggered.connect(self.start_clicked)
        self._mw.record_counts_Action.triggered.connect(self.save_clicked)

        self._mw.count_length_SpinBox.valueChanged.connect( self.count_length_changed )
        self._mw.count_freq_SpinBox.valueChanged.connect( self.count_frequency_changed )
        self._mw.oversampling_SpinBox.valueChanged.connect( self.oversampling_changed )
            
        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        #####################
        # starting the physical measurement
        self.sigStartCounter.connect(self._counting_logic.startCount)
        self.sigStopCounter.connect(self._counting_logic.stopCount)

        self._counting_logic.sigCounterUpdated.connect(self.updateData)
        
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
            
        if self._counting_logic.getState() == 'locked':
            self._mw.count_value_Label.setText('{0:,.0f}'.format(self._counting_logic.countdata_smoothed[-1]))
            self._curve1.setData(y=self._counting_logic.countdata, x=np.arange(0, self._counting_logic.get_count_length())/self._counting_logic.get_count_frequency())
            self._curve2.setData(y=self._counting_logic.countdata_smoothed, x=np.arange(0, self._counting_logic.get_count_length())/self._counting_logic.get_count_frequency())

            if self._counting_logic._counting_device._photon_source2 is not None:
                self._curve3.setData(
                                y=self._counting_logic.countdata2,
                                x=np.arange(
                                    0,
                                    self._counting_logic.get_count_length())/self._counting_logic.get_count_frequency()
                                )
                self._curve4.setData(
                                y=self._counting_logic.countdata_smoothed2,
                                x=np.arange(
                                    0,
                                    self._counting_logic.get_count_length())/self._counting_logic.get_count_frequency()
                                )

        if self._counting_logic.get_saving_state():
            self._mw.record_counts_Action.setText('Save')
            self._mw.count_freq_SpinBox.setEnabled(False)
            self._mw.oversampling_SpinBox.setEnabled(False)
        else:
            self._mw.record_counts_Action.setText('Start Saving Data')
            self._mw.count_freq_SpinBox.setEnabled(True)
            self._mw.oversampling_SpinBox.setEnabled(True)
            
        if self._counting_logic.getState() == 'locked':
            self._mw.start_counter_Action.setText('Stop')
        else:            
            self._mw.start_counter_Action.setText('Start')
            
            
    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._counting_logic.getState() == 'locked':
            self._mw.start_counter_Action.setText('Start')
            self.sigStopCounter.emit()
        else:
            self._mw.start_counter_Action.setText('Stop')
            self.sigStartCounter.emit()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        if self._counting_logic.get_saving_state():
            self._mw.record_counts_Action.setText('Start Saving Data')
            self._mw.count_freq_SpinBox.setEnabled(True)
            self._mw.oversampling_SpinBox.setEnabled(True)
            self._counting_logic.save_data()
        else:
            self._mw.record_counts_Action.setText('Save')
            self._mw.count_freq_SpinBox.setEnabled(False)
            self._mw.oversampling_SpinBox.setEnabled(False)
            self._counting_logic.start_saving()
    
    def count_length_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
#        print ('count_length_changed: {0:d}'.format(self._count_length_display.value()))
        self._counting_logic.set_count_length(self._mw.count_length_SpinBox.value())
        self._pw.setXRange(0, self._counting_logic.get_count_length()/self._counting_logic.get_count_frequency())
        
    def count_frequency_changed(self):
        """ Handling the change of the count_frequency and sending it to the measurement.
        """
#        print ('count_frequency_changed: {0:d}'.format(self._mw.count_freq_SpinBox.value()))
        self._counting_logic.set_count_frequency(self._mw.count_freq_SpinBox.value())
        self._pw.setXRange(0, self._counting_logic.get_count_length()/self._counting_logic.get_count_frequency())
        
    def oversampling_changed(self):
        """ Handling the change of the oversampling and sending it to the measurement.
        """
        self._counting_logic.set_counting_samples(samples=self._mw.oversampling_SpinBox.value())
        self._pw.setXRange(0, self._counting_logic.get_count_length()/self._counting_logic.get_count_frequency())

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.counter_trace_DockWidget.show()
        self._mw.slow_counter_control_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.counter_trace_DockWidget.setFloating(False)
        self._mw.slow_counter_control_DockWidget.setFloating(False)
        
        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.counter_trace_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.slow_counter_control_DockWidget)
