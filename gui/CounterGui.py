# -*- coding: utf-8 -*-
# Test gui (test)

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg
import time


class CounterGui(Base):
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        
        self._modclass = 'countergui'
        self._modtype = 'gui'
        ## declare connectors
        self.connector['in']['counterlogic1'] = OrderedDict()
        self.connector['in']['counterlogic1']['class'] = 'counterlogic'
        self.connector['in']['counterlogic1']['object'] = None

        self.logMsg('The following configuration was found.', 
                    messageType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        messageType='status')

    def initUI(self, e=None):
        #QtGui.QApplication.setGraphicsSystem('raster')
        self._counting_logic = self.connector['in']['counterlogic1']['object']
        print("Counting logic is", self._counting_logic)
        
        print(self._counting_logic.get_count_length())
        
        self._app = QtGui.QApplication([])
        self._mw = QtGui.QMainWindow()
        self._mw.setWindowTitle('qudi: Slow Counter')
        self._mw.resize(800,550)
        self._cw = QtGui.QWidget()
        self._mw.setCentralWidget(self._cw)
        
        self._pw = pg.PlotWidget(name='Counter1')  ## giving the plots names allows us to link their axes together
        
        self._pw.setLabel('left', 'Value', units='counts/s')
        self._pw.setLabel('bottom', 'Time', units='#')
                
        self._start_stop_button = QtGui.QPushButton('Stop')
        self._start_stop_button.released.connect(self.start_clicked)
        self._save_button = QtGui.QPushButton('Save')
        self._save_button.released.connect(self.save_clicked)
        
        self._count_length_label = QtGui.QLabel('Count lenght (s):')
        self._count_length_display = QtGui.QSpinBox()
        self._count_length_display.setRange(1,1e6)
        self._count_length_display.valueChanged.connect(self.count_length_changed)
        self._count_length_display.setValue(int(self._counting_logic.get_count_length()))
        
        self._count_frequency_label = QtGui.QLabel('Count frequency (Hz):')
        self._count_frequency_display = QtGui.QSpinBox()
        self._count_frequency_display.setRange(1,1e6)
        self._count_frequency_display.valueChanged.connect(self.count_frequency_changed)
        self._count_frequency_display.setValue(self._counting_logic.get_count_frequency())
        
        self._oversampling_label = QtGui.QLabel('Oversampling (#):')
        self._oversampling_display = QtGui.QSpinBox()
        self._oversampling_display.setRange(1,1e4)
        self._oversampling_display.valueChanged.connect(self.oversampling_changed)
        self._oversampling_display.setValue(self._counting_logic.get_counting_samples())
        
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
        
        
        self._counts_label = QtGui.QLabel('xxx')
        self._counts_label.setFont(QtGui.QFont('Arial', 50, QtGui.QFont.Bold))
        self._hbox_counter = QtGui.QHBoxLayout()
        self._hbox_counter.addStretch(1)
        self._hbox_counter.addWidget(self._counts_label)
#        self._hbox_counter.addStretch(1)
        
        self._vbox_layout = QtGui.QVBoxLayout()
        self._vbox_layout.addLayout(self._hbox_counter)
        self._vbox_layout.addWidget(self._pw)
        self._vbox_layout.addLayout(self._hbox_layout)
        
        self._cw.setLayout(self._vbox_layout)
        self._mw.show()
        
        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen('g')
        self._curve2 = self._pw.plot()
        self._curve2.setPen('r', width=4)
        
        self._pw.setXRange(1, self._counting_logic.get_count_length()+1)
        self._counting_logic.startme()
        
        
        ## Start a timer to rapidly update the plot in pw
        self._t = QtCore.QTimer()
        self._t.timeout.connect(self.updateData)
        self._t.start(50)
        

    def updateData(self):
        if self._counting_logic.running:
            self._counts_label.setText('{0:,.0f}'.format(self._counting_logic.countdata[-1]))
            self._curve1.setData(y=self._counting_logic.countdata, x=np.arange(1, self._counting_logic.get_count_length()+1))
            self._curve2.setData(y=self._counting_logic.countdata_smoothed, x=np.arange(1, self._counting_logic.get_count_length()+1))

    def start_clicked(self):
        if self._counting_logic.running:
            self._start_stop_button.setText('Start')
            self._counting_logic.stopme()
        else:
            self._start_stop_button.setText('Stop')
            self._counting_logic.startme()
    
    def save_clicked(self):
        print ("Saving not implemented yet.")
    
    def count_length_changed(self):
        print ('count_length_changed: {0:d}'.format(self._count_length_display.value()))
        self._counting_logic.set_count_length(self._count_length_display.value())
        self._pw.setXRange(1, self._counting_logic.get_count_length()+1)
        
    def count_frequency_changed(self):
        print ('count_frequency_changed: {0:d}'.format(self._count_frequency_display.value()))
        self._counting_logic.set_count_frequency(self._count_frequency_display.value())
        
    def oversampling_changed(self):
        print ("Oversampling not implemented yet.")