# -*- coding: utf-8 -*-
# Test gui (test)

from gui.GUIBase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
import time


class LaserScanningGui(GUIBase):
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
        self.connector['in']['laserscanninglogic1'] = OrderedDict()
        self.connector['in']['laserscanninglogic1']['class'] = 'LaserScanningLogic'
        self.connector['in']['laserscanninglogic1']['object'] = None
        
        self.connector['in']['savelogic'] = OrderedDict()
        self.connector['in']['savelogic']['class'] = 'SaveLogic'
        self.connector['in']['savelogic']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """

        self._scanning_logic = self.connector['in']['laserscanninglogic1']['object']
#        print("Counting logic is", self._counting_logic)
        self._save_logic = self.connector['in']['savelogic']['object']
                
        # setting up the window
        self._mw = QtGui.QMainWindow()
        self._mw.setWindowTitle('qudi: Laser Scanning')
        self._mw.setGeometry(1000,30,800,550)
        self._cw = QtGui.QWidget()
        self._mw.setCentralWidget(self._cw)
        
        # creating a plot in pyqtgraph and configuring it
        self._pw = pg.PlotWidget(name='Counter1')  ## giving the plots names allows us to link their axes together
        self._plot_item = self._pw.plotItem
        
        ## create a new ViewBox, link the right axis to its coordinate system
        self._right_axis = pg.ViewBox()
        self._plot_item.showAxis('right')
        self._plot_item.scene().addItem(self._right_axis)
        self._plot_item.getAxis('right').linkToView(self._right_axis)
        self._right_axis.setXLink(self._plot_item)
        
        # handle resizing of any of the elements
        self._update_plot_views()
        self._plot_item.vb.sigResized.connect(self._update_plot_views)
        
        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('right', 'Number of Points', units='#')
        self._pw.setLabel('bottom', 'Wavelength', units='nm')
                
        # defining buttons
        self._start_stop_button = QtGui.QPushButton('Start')
        self._start_stop_button.setFixedWidth(50)
        self._start_stop_button.clicked.connect(self.start_clicked)
        self._save_button = QtGui.QPushButton('Save Histogram')
        self._save_button.setFixedWidth(120)
        self._save_button.clicked.connect(self.save_clicked)
        
        # defining the parameters to edit
        self._bins_label = QtGui.QLabel('Bins (#):')
        self._bins_display = QtGui.QSpinBox()
        self._bins_display.setRange(1,1e4)
        self._bins_display.setValue(self._scanning_logic.get_bins())
        self._bins_display.editingFinished.connect(self.recalculate_histogram)
        
        self._min_wavelength_label = QtGui.QLabel('Min (nm):')
        self._min_wavelength_display = QtGui.QSpinBox()
        self._min_wavelength_display.setRange(1,1e6)
        self._min_wavelength_display.setValue(self._scanning_logic.get_min_wavelength())
        self._min_wavelength_display.editingFinished.connect(self.recalculate_histogram)
        
        self._max_wavelength_label = QtGui.QLabel('Max (nm):')
        self._max_wavelength_display = QtGui.QSpinBox()
        self._max_wavelength_display.setRange(1,1e4)
        self._max_wavelength_display.setValue(self._scanning_logic.get_max_wavelength())
        self._max_wavelength_display.editingFinished.connect(self.recalculate_histogram)
        
        # creating a layout for the parameters to live in and aranging it nicely
        self._hbox_layout = QtGui.QHBoxLayout()
        self._hbox_layout.addWidget(self._bins_label)
        self._hbox_layout.addWidget(self._bins_display)
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._min_wavelength_label)
        self._hbox_layout.addWidget(self._min_wavelength_display)
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._max_wavelength_label)
        self._hbox_layout.addWidget(self._max_wavelength_display)
        self._hbox_layout.addStretch(1)
        self._hbox_layout.addWidget(self._save_button)
        self._hbox_layout.addWidget(self._start_stop_button)
        
        # creating the label for the current counts and right alignment
        self._wavelength_label = QtGui.QLabel('xxx')
        self._wavelength_label.setFont(QtGui.QFont('Arial', 60, QtGui.QFont.Bold))
        self._hbox_counter = QtGui.QHBoxLayout()
        self._hbox_counter.addStretch(1)
        self._hbox_counter.addWidget(self._wavelength_label)
        
        # creating the labels for the auto ranges
        self._auto_min_label = QtGui.QLabel('Minimum: xxx.xxxxxx (nm)   ')
        self._auto_max_label = QtGui.QLabel('Maximum: xxx.xxxxxx (nm)   ')
        self._set_auto_range = QtGui.QPushButton('Set Auto Range')
        self._set_auto_range.setFixedWidth(150)
        self._set_auto_range.clicked.connect(self.set_auto_range)
        self._ghz_x_axis = QtGui.QCheckBox('Display frequency')
        
        self._hbox_auto_range = QtGui.QHBoxLayout()
        self._hbox_auto_range.addWidget(self._auto_min_label)
        self._hbox_auto_range.addWidget(self._auto_max_label)
        self._hbox_auto_range.addWidget(self._set_auto_range)
        self._hbox_auto_range.addStretch(1)
        self._hbox_auto_range.addWidget(self._ghz_x_axis)
        
        # combining the layouts with the plot
        self._vbox_layout = QtGui.QVBoxLayout()
        self._vbox_layout.addLayout(self._hbox_counter)
        self._vbox_layout.addLayout(self._hbox_auto_range)
        self._vbox_layout.addWidget(self._pw)
        self._vbox_layout.addLayout(self._hbox_layout)
        
        # applying all the GUI elements to the window
        self._cw.setLayout(self._vbox_layout)
        self._mw.show()
        
        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen({'color': '0F0', 'width': 2})
        
        self._curve2 =pg.PlotCurveItem() 
        self._curve2.setPen({'color': 'F00', 'width': 1})
        
        self._right_axis.addItem(self._curve2)
        
        self._save_PNG = True
        
        self._scanning_logic.sig_data_updated.connect(self.updateData)
        
    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """
        self._wavelength_label.setText('{0:,.5f} nm'.format(self._scanning_logic.current_wavelength))
        self._auto_min_label.setText('Minimum: {0:3.6f} (nm)   '.format(self._scanning_logic.intern_xmin))
        self._auto_max_label.setText('Maximum: {0:3.6f} (nm)   '.format(self._scanning_logic.intern_xmax))
        if self._ghz_x_axis.isChecked():
            self._pw.setLabel('bottom', 'Relative Frequency', units='Hz')
            x_axis = 3.0e17/(self._scanning_logic.histogram_axis) \
            - 6.0e17/(self._scanning_logic.get_max_wavelength() + self._scanning_logic.get_min_wavelength())
        else:
            self._pw.setLabel('bottom', 'Wavelength', units='nm')
            x_axis = self._scanning_logic.histogram_axis
        self._curve1.setData(y=self._scanning_logic.histogram, x=x_axis)
        self._curve2.setData(y=self._scanning_logic.sumhisto, x=x_axis)

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._scanning_logic.getState() is 'running':
            self._start_stop_button.setText('Start')
            self._scanning_logic.stop_scanning()
        else:
            self._start_stop_button.setText('Stop')
            self._scanning_logic.start_scanning()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
                
        filepath = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filename = filepath + time.strftime('\\%Y-%m-%d_laser_scan_from_%Hh%Mm%Ss')
                
        exporter = pg.exporters.SVGExporter(self._pw.plotItem)
        exporter.export(filename+'.svg')
            
        if self._save_PNG:
            exporter = pg.exporters.ImageExporter(self._pw.plotItem)
            exporter.export(filename+'.png')              
        
        self._scanning_logic.save_data()
            
    def recalculate_histogram(self):
        self._scanning_logic.recalculate_histogram(\
        bins=self._bins_display.value(),\
        xmin=self._min_wavelength_display.value(),\
        xmax=self._max_wavelength_display.value())
        
    def set_auto_range(self):
        self._min_wavelength_display.setValue(self._scanning_logic.intern_xmin)
        self._max_wavelength_display.setValue(self._scanning_logic.intern_xmax)
        self.recalculate_histogram()
        
    ## Handle view resizing 
    def _update_plot_views(self):
        ## view has resized; update auxiliary views to match
        self._right_axis.setGeometry(self._plot_item.vb.sceneBoundingRect())
        
        ## need to re-update linked axes since this was called
        ## incorrectly while views had different shapes.
        ## (probably this should be handled in ViewBox.resizeEvent)
        self._right_axis.linkedViewChanged(self._plot_item.vb, self._right_axis.XAxis)
