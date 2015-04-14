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
        self._app = QtGui.QApplication([])
        self._mw = QtGui.QMainWindow()
        self._mw.setWindowTitle('qudi: Slow Counter')
        self._mw.resize(800,500)
        self._cw = QtGui.QWidget()
        self._mw.setCentralWidget(self._cw)
        self._vbox_layout = QtGui.QVBoxLayout()
        
        self._pw = pg.PlotWidget(name='Counter1')  ## giving the plots names allows us to link their axes together
        self._vbox_layout.addWidget(self._pw)
        
        self._pw.setLabel('left', 'Value', units='counts/s')
        self._pw.setLabel('bottom', 'Time', units='s')        
        self._mw.show()
        
        self._start_stop_button = QtGui.QPushButton('Stop')
        self._start_stop_button.released.connect(self.start_clicked)
        
        self._hbox_layout = QtGui.QHBoxLayout()
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._start_stop_button)
        self._vbox_layout.addLayout(self._hbox_layout)
        
        self._cw.setLayout(self._vbox_layout)
        
        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen('g')
        self._curve2 = self._pw.plot()
        self._curve2.setPen('r', width=4)
        
        self._counting_logic = self.connector['in']['counterlogic1']['object']
        print("Counting logic is", self._counting_logic)
        self._counting_logic.startme()
        self._pw.setXRange(1, self._counting_logic.get_count_length()+1)
        
        
        ## Start a timer to rapidly update the plot in pw
        self._t = QtCore.QTimer()
        self._t.timeout.connect(self.updateData)
        self._t.start(50)
        

    def updateData(self):
        if self._counting_logic.running:
            self._curve1.setData(y=self._counting_logic.countdata, x=np.arange(1, self._counting_logic.get_count_length()+1))
            self._curve2.setData(y=self._counting_logic.countdata_smoothed, x=np.arange(1, self._counting_logic.get_count_length()+1))

    def start_clicked(self):
        if self._counting_logic.running:
            self._start_stop_button.setText('Start')
            self._counting_logic.stopme()
        else:
            self._start_stop_button.setText('Stop')
            self._counting_logic.startme()