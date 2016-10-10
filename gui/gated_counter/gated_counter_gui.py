# -*- coding: utf-8 -*-

"""
This file contains the GUI for control of a Gated Counter.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import os
import numpy as np

from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from gui.colordefs import QudiPalette as palettedark
from core.util import units
import pyqtgraph as pg
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class GatedCounterMainWindow(QtWidgets.QMainWindow):
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

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))

    def on_activate(self, e=None):
        """ Definition and initialisation of the GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self._counter_logic = self.get_in_connector('gatedcounterlogic1')
        self._trace_analysis = self.get_in_connector('traceanalysislogic1')

        self._mw = GatedCounterMainWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        self.set_default_view_main_window()

        self._gp = self._mw.gated_count_trace_PlotWidget
        self._gp.setLabel('left', 'Counts', units='counts/s')
        self._gp.setLabel('bottom', 'Number of Gates', units='#')

        # Create an empty plot curve to be filled later, set its pen
        self._trace1 = self._gp.plot()
        self._trace1.setPen(palette.c1)

        self._hp = self._mw.histogram_PlotWidget
        self._hp.setLabel('left', 'Occurrences', units='#')
        self._hp.setLabel('bottom', 'Counts', units='counts/s')

        self._histoplot1 = pg.PlotCurveItem()
        self._histoplot1.setPen(palette.c1)
        self._hp.addItem(self._histoplot1)


        # Configure the fit of the data in the main pulse analysis display:
        self._fit_image = pg.PlotCurveItem()
        self._hp.addItem(self._fit_image)

        # setting the x axis length correctly
        self._gp.setXRange(0, self._counter_logic.get_count_length())
        self._mw.hist_bins_SpinBox.setRange(1, self._counter_logic.get_count_length())

        # set up the slider with the values of the logic:
        self._mw.hist_bins_Slider.setRange(1,self._counter_logic.get_count_length())
        self._mw.hist_bins_Slider.setSingleStep(1)

        # set the counting mode in the logic:
        self._counter_logic.set_counting_mode('finite-gated')

        # Setting default parameters
        self._mw.count_length_SpinBox.setValue(self._counter_logic.get_count_length())
        self._mw.count_per_readout_SpinBox.setValue(self._counter_logic.get_counting_samples())

        # Connecting user interactions
        # set at first the action buttons in the tab
        self._mw.start_counter_Action.triggered.connect(self.start_clicked)
        self._mw.stop_counter_Action.triggered.connect(self.stop_clicked)
        self._mw.save_measurement_Action.triggered.connect(self.save_clicked)
        self._mw.actionRestore_Default.triggered.connect(self.set_default_view_main_window)

        # that is also the default value of the histogram method in logic
        # important: the set of a value should not trigger a redrawn of the
        # current empty histogram, which is at the start of the program.
        self._mw.hist_bins_SpinBox.setValue(50)
        # connect now a reaction on a change of the various input widgets:
        self._mw.count_length_SpinBox.editingFinished.connect(self.count_length_changed)
        self._mw.count_per_readout_SpinBox.editingFinished.connect(self.count_per_readout_changed)
        self._mw.hist_bins_Slider.valueChanged.connect(self.num_bins_changed)
        self._mw.hist_bins_SpinBox.valueChanged.connect(self.num_bins_changed)
        self._trace_analysis.sigHistogramUpdated.connect(self.update_histogram)


        # starting the physical measurement:
        self.sigStartGatedCounter.connect(self._counter_logic.startCount)
        self.sigStopGatedCounter.connect(self._counter_logic.stopCount)

        # connect to signals in the logic:
        self._counter_logic.sigCounterUpdated.connect(self.update_trace)
        self._counter_logic.sigGatedCounterFinished.connect(self.reset_toolbar_display)

        # configuration of the combo widget
        fit_functions = self._trace_analysis.get_fit_functions()
        self._mw.fit_methods_ComboBox.addItems(fit_functions)

        # Push buttons
        self._mw.fit_PushButton.clicked.connect(self.fit_clicked)


    def on_deactivate(self, e=None):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._mw.close()

    def show(self):
        """ Make main window visible and put it above all other windows. """

        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def set_default_view_main_window(self):
        """ Restore the default view and arrangement of the DockWidgets. """

        self._mw.control_param_DockWidget.setFloating(False)
        self._mw.count_trace_DockWidget.setFloating(False)
        self._mw.histogram_DockWidget.setFloating(False)

        # QtCore.Qt.LeftDockWidgetArea        0x1
        # QtCore.Qt.RightDockWidgetArea       0x2
        # QtCore.Qt.TopDockWidgetArea         0x4
        # QtCore.Qt.BottomDockWidgetArea      0x8
        # QtCore.Qt.AllDockWidgetAreas        DockWidgetArea_Mask
        # QtCore.Qt.NoDockWidgetArea          0

        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(4), self._mw.control_param_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.count_trace_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.histogram_DockWidget)

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter. """

        if self._counter_logic.getState() != 'locked':
            self.sigStartGatedCounter.emit()
            self._mw.start_counter_Action.setEnabled(False)
            self._mw.stop_counter_Action.setEnabled(True)

    def stop_clicked(self):
        """ Handling the Stop button to stop and restart the counter. """

        if self._counter_logic.getState() == 'locked':
            self.sigStopGatedCounter.emit()
            self.reset_toolbar_display()

    def reset_toolbar_display(self):
        """ Run this method after finishing the counting to get initial status
        """

        self._mw.start_counter_Action.setEnabled(True)
        self._mw.stop_counter_Action.setEnabled(False)

    def save_clicked(self):
        """ Trigger the save routine in the logic.
            Pass also the chosen filename.
        """

        file_desc = self._mw.filetag_LineEdit.text()
        if file_desc == '':
            file_desc = 'gated_counter'

        trace_file_desc = file_desc + '_trace'
        self._counter_logic.save_current_count_trace(name_tag=trace_file_desc)

        # histo_file_desc = file_desc + '_histogram'
        # self._trace_analysis.save_histogram(file_desc=histo_file_desc)

    def count_length_changed(self):
        """ Handle the change of the count_length and send it to the measurement.
        """

        self._counter_logic.set_count_length(self._mw.count_length_SpinBox.value())
        self._gp.setXRange(0, self._counter_logic.get_count_length())
        self._mw.hist_bins_Slider.setRange(1, self._counter_logic.get_count_length())
        self._mw.hist_bins_SpinBox.setRange(1, self._counter_logic.get_count_length())

    def count_per_readout_changed(self):
        """ Handling the change of the oversampling and sending it to the measurement.
        """
        self._counter_logic.set_counting_samples(samples=self._mw.count_per_readout_SpinBox.value())

    def update_trace(self):
        """ The function that grabs the data and sends it to the plot. """

        if self._counter_logic.getState() == 'locked':
            self._trace1.setData(x=np.arange(0, self._counter_logic.get_count_length()),
                                 y=self._counter_logic.countdata )

    def update_histogram(self):
        """ Update procedure for the histogram to display the new data. """

        self._histoplot1.setData(x=self._trace_analysis.hist_data[0],
                                 y=self._trace_analysis.hist_data[1],
                                 stepMode=True, fillLevel=0,
                                 brush=palettedark.c1)

    def num_bins_changed(self, num_bins):
        """
        @param int num_bins: Number of bins to be set in the trace.

        This method is executed by both events, the valueChanged of the SpinBox
        and value changed in the Slider. Until now, there appears no infinite
        signal loop. It that occur one day, than this method has to be split
        in two seperate methods.
        """

        self._trace_analysis.set_num_bins_histogram(num_bins)
        self._mw.hist_bins_SpinBox.setValue(num_bins)
        self._mw.hist_bins_Slider.setValue(num_bins)


    def fit_clicked(self):
        """ Do the configured fit and show it in the sum plot """
        self._mw.fit_param_TextEdit.clear()

        current_fit_function = self._mw.fit_methods_ComboBox.currentText()

        fit_x, fit_y, fit_param_dict, fit_result = self._trace_analysis.do_fit(fit_function=current_fit_function)

        self._fit_image.setData(x=fit_x, y=fit_y, pen=pg.mkPen(palette.c2, width=2))

        if len(fit_param_dict) == 0:
            fit_result = 'No Fit parameter passed.'

        else:
            fit_result = units.create_formatted_output(fit_param_dict)
        self._mw.fit_param_TextEdit.setPlainText(fit_result)

        return
