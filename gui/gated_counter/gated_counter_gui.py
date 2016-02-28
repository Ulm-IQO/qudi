# -*- coding: utf-8 -*-

"""
This file contains the GUI for control of a Gated Counter.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""
import os
import numpy as np
from collections import OrderedDict

from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui, uic
from pyqtgraph import PlotCurveItem


class GatedCounterMainWindow(QtGui.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_gated_counter_gui.ui')

        # Load it
        super(GatedCounterMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class GatedCounterGui(GUIBase):
    """ Main GUI for the Gated Counting. """

    _modclass = 'GatedCounterGui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'gatedcounterlogic1': 'GatedCounterLogic',
           'traceanalysislogic1': 'TraceAnalysisLogic'}


    sigStartGatedCounter = QtCore.Signal()
    sigStopGatedCounter = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.initUI,
                         'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self._counter_logic = self.connector['in']['gatedcounterlogic1']['object']
        self._trace_analysis = self.connector['in']['traceanalysislogic1']['object']

        self._mw = GatedCounterMainWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        self.set_default_view_main_window()

        self._gp = self._mw.gated_count_trace_PlotWidget
        self._gp.setLabel('left', 'Counts', units='counts/s')
        self._gp.setLabel('bottom', 'Number of Gates', units='#')

        # Create an empty plot curve to be filled later, set its pen
        self._trace1 = self._gp.plot()
        self._trace1.setPen('g')

        self._hp = self._mw.histogram_PlotWidget

        self._hp.setLabel('left', 'Occurrences', units='#')
        self._hp.setLabel('bottom', 'Counts', units='counts/s')

        self._histoplot1 = PlotCurveItem()
        self._hp.addItem(self._histoplot1)

        # self._histoplot1.setPen('b')
        self._histoplot1.setPen((37,87,238,255))
        # self._histoplot1.  stepMode=True, fillLevel=0, brush=(0,0,255,150)

        # setting the x axis length correctly
        self._gp.setXRange(0, self._counter_logic.get_count_length())
        self._mw.hist_bins_SpinBox.setRange(1, self._counter_logic.get_count_length())

        self._mw.hist_bins_Slider.setRange(1,self._counter_logic.get_count_length())
        self._mw.hist_bins_Slider.setSingleStep(1)

        self._mw.hist_bins_Slider.sliderMoved.connect(self.num_bins_changed)
        self._mw.hist_bins_SpinBox.valueChanged.connect(self.num_bins_changed)

        self._counter_logic.set_counting_mode('finite-gated')
        # Setting default parameters
        self._mw.count_length_SpinBox.setValue(self._counter_logic.get_count_length())
        self._mw.count_per_readout_SpinBox.setValue(self._counter_logic.get_counting_samples())

        # Connecting user interactions
        self._mw.start_counter_Action.triggered.connect(self.start_clicked)

        self._mw.stop_counter_Action.triggered.connect(self.stop_clicked)

        self._mw.save_measurement_Action.triggered.connect(self.save_clicked)

        self._mw.count_length_SpinBox.editingFinished.connect(self.count_length_changed)

        self._mw.count_per_readout_SpinBox.editingFinished.connect(self.count_per_readout_changed)


        # starting the physical measurement
        self.sigStartGatedCounter.connect(self._counter_logic.startCount)
        self.sigStopGatedCounter.connect(self._counter_logic.stopCount)

        self._counter_logic.sigCounterUpdated.connect(self.update_trace)
        self._counter_logic.sigGatedCounterFinished.connect(self.reset_display)

        self._trace_analysis.sigHistogramUpdated.connect(self.update_histogram)

    def deactivation(self, e=None):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method initUI.
        """
        self._mw.close()

    def show(self):
        """ Make main window visible and put it above all other windows. """

        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def set_default_view_main_window(self):
        self._mw.control_param_DockWidget.setFloating(False)
        self._mw.count_trace_DockWidget.setFloating(False)
        self._mw.histogram_DockWidget.setFloating(False)

        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.control_param_DockWidget)
        # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(6), self._mw.count_trace_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.histogram_DockWidget)

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._counter_logic.getState() != 'locked':
            self.sigStartGatedCounter.emit()
            self._mw.start_counter_Action.setEnabled(False)
            self._mw.stop_counter_Action.setEnabled(True)

    def stop_clicked(self):
        if self._counter_logic.getState() == 'locked':
            self.sigStopGatedCounter.emit()
            self.reset_display()

    def reset_display(self):
        self._mw.start_counter_Action.setEnabled(True)
        self._mw.stop_counter_Action.setEnabled(False)

    def save_clicked(self):
        file_desc = self._mw.filename_LineEdit.text()
        if file_desc == '':
            file_desc = 'gated_counter'

        trace_file_desc = file_desc + '_trace'
        self._counter_logic.save_count_trace(file_desc=trace_file_desc)

        # histo_file_desc = file_desc + '_histogram'
        # self._trace_analysis.save_histogram(file_desc=histo_file_desc)

    def count_length_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
#        print ('count_length_changed: {0:d}'.format(self._count_length_display.value()))
        self._counter_logic.set_count_length(self._mw.count_length_SpinBox.value())
        self._gp.setXRange(0, self._counter_logic.get_count_length())
        self._mw.hist_bins_Slider.setRange(1, self._counter_logic.get_count_length())
        self._mw.hist_bins_SpinBox.setRange(1, self._counter_logic.get_count_length())

    def count_per_readout_changed(self):
        """ Handling the change of the oversampling and sending it to the measurement.
        """
        self._counter_logic.set_counting_samples(samples=self._mw.count_per_readout_SpinBox.value())
        # self._gp.setXRange(0, self._counter_logic.get_count_length()/self._counter_logic.get_count_frequency())
    def update_trace(self):
        """ The function that grabs the data and sends it to the plot.
        """

        if self._counter_logic.getState() == 'locked':
            # self._mw.count_value_Label.setText('{0:,.0f}'.format(self._counter_logic.countdata_smoothed[-1]))
            self._trace1.setData(x=np.arange(0, self._counter_logic.get_count_length()),
                                 y=self._counter_logic.countdata )
            # self._curve2.setData(y=self._counter_logic.countdata_smoothed, x=np.arange(0, self._counter_logic.get_count_length())/self._counter_logic.get_count_frequency())

    def update_histogram(self):

        self._histoplot1.setData(x=self._trace_analysis.hist_data[0],
                                 y=self._trace_analysis.hist_data[1],
                                 stepMode=True, fillLevel=0,
                                 brush=(0, 0, 208, 180))



    def num_bins_changed(self, num_bins):
        self._trace_analysis.set_num_bins_histogram(num_bins)
        self._mw.hist_bins_SpinBox.setValue(num_bins)
        self._mw.hist_bins_Slider.setValue(num_bins)