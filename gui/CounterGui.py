# -*- coding: utf-8 -*-
# Test gui (test)

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg


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
        self._mw.setWindowTitle('qudi: Counter')
        self._mw.resize(800,600)
        self._cw = QtGui.QWidget()
        self._mw.setCentralWidget(self._cw)
        self._l = QtGui.QVBoxLayout()
        self._cw.setLayout(self._l)
        
        self._pw = pg.PlotWidget(name='Plot1')  ## giving the plots names allows us to link their axes together
        self._l.addWidget(self._pw)
        
        self._pw.setLabel('left', 'Value', units='arb. u.')
        self._pw.setLabel('bottom', 'Time', units='s')
        self._pw.setXRange(0, 100)
#        self._pw.setYRange(0, 1e-10)
        
        self._mw.show()
        
        ## Create an empty plot curve to be filled later, set its pen
        self._p1 = self._pw.plot()
        self._p1.setPen((200,200,100))
        
        self._counting_logic = self.connector['in']['counterlogic1']['object']
        print("Counting logic is", self._counting_logic)
        
        
        ## Start a timer to rapidly update the plot in pw
        self._t = QtCore.QTimer()
        self._t.timeout.connect(self.updateData)
        self._t.start(200)
        self.updateData()
#        
#        self._mw.setGeometry(300,300,500,100)
#        self._mw.setWindowTitle('Slow Photon counter')
#        self.cwdget = QtGui.QWidget()
#        self.button = QtGui.QPushButton('Click it!')
#        self.button.clicked.connect(self.handleButton)
#        self.layout = QtGui.QVBoxLayout()
#        self.layout.addWidget(self.button)
#        self.cwdget.setLayout(self.layout)
#        self._mw.setCentralWidget(self.cwdget)
#        self._mw.show()

    def updateData(self):
        n=100
        data = np.random.random(n)
        self._p1.setData(y=data, x=np.arange(1, len(data)+1))
