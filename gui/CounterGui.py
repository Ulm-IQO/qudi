# -*- coding: utf-8 -*-
# Test gui (test)

from gui.GUIBase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg


class CounterGui(GUIBase):
    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()
    _modclass = 'countergui'
    _modtype = 'gui'

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        super().__init__(
                    manager,
                    name,
                    config,
                    c_dict)
        ## declare connectors
        self.connector['in']['counterlogic1'] = OrderedDict()
        self.connector['in']['counterlogic1']['class'] = 'CounterLogic'
        self.connector['in']['counterlogic1']['object'] = None

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
                
        # setting up the window
        self._mw = QtGui.QMainWindow()
        self._mw.setWindowTitle('qudi: Slow Counter')
        self._mw.setGeometry(1000,30,800,550)
        self._cw = QtGui.QWidget()
        self._mw.setCentralWidget(self._cw)
        
        # creating a plot in pyqtgraph and configuring it
        self._pw = pg.PlotWidget(name='Counter1')  ## giving the plots names allows us to link their axes together        
        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('bottom', 'Time', units='s')
                
        # defining buttons
        self._start_stop_button = QtGui.QPushButton('Start')
        self._start_stop_button.setFixedWidth(50)
        self._start_stop_button.clicked.connect(self.start_clicked)
        self._save_button = QtGui.QPushButton('Start Saving Data')
        self._save_button.setFixedWidth(120)
        self._save_button.clicked.connect(self.save_clicked)
        
        # defining the parameters to edit
        self._count_length_label = QtGui.QLabel('Count lenght (#):')
        self._count_length_display = QtGui.QSpinBox()
        self._count_length_display.setRange(1,1e6)
        self._count_length_display.setValue(self._counting_logic.get_count_length())
        self._count_length_display.valueChanged.connect(self.count_length_changed)
        
        self._count_frequency_label = QtGui.QLabel('Count frequency (Hz):')
        self._count_frequency_display = QtGui.QSpinBox()
        self._count_frequency_display.setRange(1,1e6)
        self._count_frequency_display.setValue(self._counting_logic.get_count_frequency())
        self._count_frequency_display.valueChanged.connect(self.count_frequency_changed)
        
        oversampling_tooltip = 'If bigger than 1, the number of samples is averaged over the given number and then displayed. \nUse for extremely fast counting, since all the raw data is saved. \nTimestamps in oversampling interval are all equal to the averaging time.'
        self._oversampling_label = QtGui.QLabel('Oversampling (#):')
        self._oversampling_label.setToolTip(oversampling_tooltip)
        self._oversampling_display = QtGui.QSpinBox()
        self._oversampling_display.setToolTip(oversampling_tooltip)
        self._oversampling_display.setRange(1,1e4)
        self._oversampling_display.setValue(self._counting_logic.get_counting_samples())
        self._oversampling_display.valueChanged.connect(self.oversampling_changed)
        
        # creating a layout for the parameters to live in and aranging it nicely
        self._hbox_layout = QtGui.QHBoxLayout()
        self._hbox_layout.addWidget(self._count_length_label)
        self._hbox_layout.addWidget(self._count_length_display)
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._count_frequency_label)
        self._hbox_layout.addWidget(self._count_frequency_display)
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._oversampling_label)
        self._hbox_layout.addWidget(self._oversampling_display)
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._save_button)
        self._hbox_layout.addWidget(self._start_stop_button)
        self._control_widget = QtGui.QWidget()
        self._control_widget.setLayout(self._hbox_layout)
        
        # creating the label for the current counts and right alignment
        self._counts_label = QtGui.QLabel('xxx')
        self._counts_label.setFont(QtGui.QFont('Arial', 60, QtGui.QFont.Bold))
        self._hbox_counter = QtGui.QHBoxLayout()
        self._hbox_counter.addStretch(1)
        self._hbox_counter.addWidget(self._counts_label)
        self._count_widget = QtGui.QWidget()
        self._count_widget.setLayout(self._hbox_counter)
        
        # set up GUI with dock widgets
        self._counts_dock_widget = QtGui.QDockWidget()
        self._counts_dock_widget.setWidget(self._count_widget)
        self._counts_dock_widget.setWindowTitle("Slow Counter Counts")
        self._counts_dock_widget.setSizePolicy(QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.MinimumExpanding)
        self._counts_dock_widget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self._counts_dock_widget.setFeatures(QtGui.QDockWidget.AllDockWidgetFeatures)
        self._mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._counts_dock_widget)
        
        self._plot_dock_widget = QtGui.QDockWidget()
        self._plot_dock_widget.setWidget(self._pw)
        self._plot_dock_widget.setWindowTitle("Slow Counter Plot")
        self._plot_dock_widget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self._plot_dock_widget.setFeatures(QtGui.QDockWidget.AllDockWidgetFeatures)
        self._mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._plot_dock_widget)
        
        self._control_dock_widget = QtGui.QDockWidget()
        self._control_dock_widget.setWidget(self._control_widget)
        self._control_dock_widget.setWindowTitle("Slow Counter Control")
        self._control_dock_widget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self._control_dock_widget.setFeatures(QtGui.QDockWidget.AllDockWidgetFeatures)
        self._mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._control_dock_widget)

       
        # showing all the GUI elements to the window
        self._mw.setDockNestingEnabled(True)
        self._cw.hide()
        self._mw.show()
        
        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen('g')
        self._curve2 = self._pw.plot()
        self._curve2.setPen('r', width=4)
        
        # setting the x axis length correctly
        self._pw.setXRange(0, self._counting_logic.get_count_length()/self._counting_logic.get_count_frequency())
        
        # starting the physical measurement
        # self._counting_logic.startme()
        self.sigStartCounter.connect(self._counting_logic.startCount)
        self.sigStopCounter.connect(self._counting_logic.stopCount)

        ## Start a timer to rapidly update the plot in pw
        #self._t = QtCore.QTimer()
        #self._t.timeout.connect(self.updateData)
        #self._t.start(50)

        self._counting_logic.sigCounterUpdated.connect(self.updateData)
        
    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """
            
        if self._counting_logic.getState() == 'locked':
            self._counts_label.setText('{0:,.0f}'.format(self._counting_logic.countdata_smoothed[-1]))
            self._curve1.setData(y=self._counting_logic.countdata, x=np.arange(0, self._counting_logic.get_count_length())/self._counting_logic.get_count_frequency())
            self._curve2.setData(y=self._counting_logic.countdata_smoothed, x=np.arange(0, self._counting_logic.get_count_length())/self._counting_logic.get_count_frequency())

        if self._counting_logic.get_saving_state():
            self._save_button.setText('Save')
            self._count_frequency_display.setEnabled(False)
            self._oversampling_display.setEnabled(False)
        else:
            self._save_button.setText('Start Saving Data')
            self._count_frequency_display.setEnabled(True)
            self._oversampling_display.setEnabled(True)
            
        if self._counting_logic.getState() == 'locked':
            self._start_stop_button.setText('Stop')
        else:            
            self._start_stop_button.setText('Start')
            
            
    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._counting_logic.getState() == 'locked':
            self._start_stop_button.setText('Start')
            self.sigStopCounter.emit()
        else:
            self._start_stop_button.setText('Stop')
            self.sigStartCounter.emit()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        if self._counting_logic.get_saving_state():
            self._save_button.setText('Start Saving Data')
            self._count_frequency_display.setEnabled(True)
            self._oversampling_display.setEnabled(True)
            self._counting_logic.save_data()
        else:
            self._save_button.setText('Save')
            self._count_frequency_display.setEnabled(False)
            self._oversampling_display.setEnabled(False)
            self._counting_logic.start_saving()
    
    def count_length_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
#        print ('count_length_changed: {0:d}'.format(self._count_length_display.value()))
        self._counting_logic.set_count_length(self._count_length_display.value())
        self._pw.setXRange(0, self._counting_logic.get_count_length()/self._counting_logic.get_count_frequency())
        
    def count_frequency_changed(self):
        """ Handling the change of the count_frequency and sending it to the measurement.
        """
#        print ('count_frequency_changed: {0:d}'.format(self._count_frequency_display.value()))
        self._counting_logic.set_count_frequency(self._count_frequency_display.value())
        self._pw.setXRange(0, self._counting_logic.get_count_length()/self._counting_logic.get_count_frequency())
        
    def oversampling_changed(self):
        """ Handling the change of the oversampling and sending it to the measurement.
        """
        self._counting_logic.set_counting_samples(samples=self._oversampling_display.value())
        self._pw.setXRange(0, self._counting_logic.get_count_length()/self._counting_logic.get_count_frequency())
