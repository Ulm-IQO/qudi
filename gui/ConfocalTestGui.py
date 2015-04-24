# -*- coding: utf-8 -*-
# Test gui (test)

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg


class ConfocalTestGui(Base):
    signal_start_scan = QtCore.Signal()
    signal_stop_scan = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        
        self._modclass = 'ConfocalTestGui'
        self._modtype = 'gui'
        
        ## declare connectors
        self.connector['in']['confocallogic1'] = OrderedDict()
        self.connector['in']['confocallogic1']['class'] = 'ConfocalTestLogic'
        self.connector['in']['confocallogic1']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """

        self._scanning_logic = self.connector['in']['confocallogic1']['object']
        print("Scanning logic is", self._scanning_logic)
                
        # setting up the window
        self._mw = QtGui.QMainWindow()
        self._mw.setWindowTitle('qudi: Counter Test GUI')
        self._mw.setGeometry(1400,650,400,400)
        self._cw = QtGui.QWidget()
        self._mw.setCentralWidget(self._cw)
        
        # defining buttons
        self._start_stop_button = QtGui.QPushButton('Start Scan')
        self._start_stop_button.clicked.connect(self.start_clicked)
        
        # defining the parameters to edit
        self._x_label = QtGui.QLabel('x:')
        self._x_display = QtGui.QSpinBox()
        self._x_display.setRange(0,1e3)
        self._x_display.setValue(10)
        self._x_display.valueChanged.connect(self.x_changed)
        
        self._y_label = QtGui.QLabel('y:')
        self._y_display = QtGui.QSpinBox()
        self._y_display.setRange(0,1e3)
        self._y_display.setValue(10)
        self._y_display.valueChanged.connect(self.x_changed)
        
        self._z_label = QtGui.QLabel('z:')
        self._z_display = QtGui.QSpinBox()
        self._z_display.setRange(0,1e3)
        self._z_display.setValue(10)
        self._z_display.valueChanged.connect(self.x_changed)
        
        self._a_label = QtGui.QLabel('a:')
        self._a_display = QtGui.QSpinBox()
        self._a_display.setRange(0,1e3)
        self._a_display.setValue(10)
        self._a_display.valueChanged.connect(self.x_changed)
                
        # creating a layout for the parameters to live in and aranging it nicely
        self._hbox_layout = QtGui.QHBoxLayout()
        self._hbox_layout.addWidget(self._x_label)
        self._hbox_layout.addWidget(self._x_display)
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._y_label)
        self._hbox_layout.addWidget(self._y_display)
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._z_label)
        self._hbox_layout.addWidget(self._z_display)
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._a_label)
        self._hbox_layout.addWidget(self._a_display)
        
        # funny gifs
        self.movie_screen = QtGui.QLabel()  
#        self.movie_screen.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.movie_screen.setFixedHeight(200)
        self.movie_screen.setFixedWidth(200)
        self.movie_screen.setAlignment(QtCore.Qt.AlignCenter)
        self.movie_screen.setStyleSheet('QLabel {background-color: white; color: red;}')
        # Add the QMovie object to the label
        self.idle_movie = QtGui.QMovie('artwork/idle_smiley.gif', QtCore.QByteArray(), self)
        self.idle_movie.setCacheMode(QtGui.QMovie.CacheAll)
        self.idle_movie.setSpeed(100)
#        self.idle_movie.setBackgroundColor(QtGui.QColor(255,255,255))
        self.idle_movie.start()
        self.active_movie = QtGui.QMovie('artwork/active_smiley.gif', QtCore.QByteArray(), self)
        self.active_movie.setCacheMode(QtGui.QMovie.CacheAll)
        self.active_movie.setSpeed(100)
        self.active_movie.start()
        self.movie_screen.setMovie(self.idle_movie)
        
        self._hbox_layout_icon = QtGui.QHBoxLayout()
        self._hbox_layout_icon.addStretch(1)
        self._hbox_layout_icon.addWidget(self.movie_screen)
        self._hbox_layout_icon.addStretch(1)
        
        
        # kombining the layouts with the plot
        self._vbox_layout = QtGui.QVBoxLayout()
        self._vbox_layout.addLayout(self._hbox_layout)
        self._vbox_layout.addWidget(self._start_stop_button)
        self._vbox_layout.addStretch(1)
        self._vbox_layout.addLayout(self._hbox_layout_icon)
        
        # applying all the GUI elements to the window
        self._cw.setLayout(self._vbox_layout)
        self._mw.show()
        
        # starting the physical measurement
        self._scanning_logic.start_scanner()
        self.signal_start_scan.connect(self._scanning_logic.start_scanning)
        self.signal_stop_scan.connect(self._scanning_logic.stop_scanning)
        self._scanning_logic.signal_scan_updated.connect(self.update_state)
#
#
#        self._counting_logic.sigCounterUpdated.connect(self.updateData)
        

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._scanning_logic.running:
            self._start_stop_button.setText('Start Scan')
            self.signal_stop_scan.emit()
        else:
            self._start_stop_button.setText('Stop Scan')
            self.signal_start_scan.emit()


    def update_state(self):
        """ Displaying the state.
        """
        if self._scanning_logic.running:
            self.movie_screen.setStyleSheet('QLabel {background-color: white; color: red;}')
            self.movie_screen.setMovie(self.active_movie)
        else:
            self.movie_screen.setStyleSheet('QLabel {background-color: white; color: red;}')
            self.movie_screen.setMovie(self.idle_movie)
            
    
    def x_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
        print ('x_changed: {0:d},{1:d},{2:d},{3:d}'.format(self._x_display.value(), 
                                         self._y_display.value(), 
                                         self._z_display.value(), 
                                         self._a_display.value()))
        self._scanning_logic.go_to_pos(self._x_display.value(),
                                       self._y_display.value(),
                                       self._z_display.value(),
                                       self._a_display.value())
