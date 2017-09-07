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

import numpy as np
import os
import pyqtgraph as pg

from core.module import Connector
from core.util import units
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from gui.colordefs import QudiPalette as palettedark
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
    gatedcounterlogic1 = Connector(interface='GatedCounterLogic')


    sigStartGatedCounter = QtCore.Signal()
    sigStopGatedCounter = QtCore.Signal()
    sigSettingsChanged = QtCore.Signal(dict)
    # sigPauseContinueGatedCounter = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')
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
        self._counter_logic = self.get_connector('gatedcounterlogic1')

        self._mw = GatedCounterMainWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        self.set_default_view_main_window()

        self._gp = self._mw.gated_count_trace_PlotWidget
        self._gp.setLabel('left', 'Counts', units='counts')
        self._gp.setLabel('bottom', 'Number of Gates', units='#')

        # Create an empty plot curve to be filled later, set its pen
        self._trace1 = self._gp.plot()
        self._trace1.setPen(palette.c1)

        self._hp = self._mw.histogram_PlotWidget
        self._hp.setLabel('left', 'Occurrences', units='#')
        self._hp.setLabel('bottom', 'Counts', units='counts')

        self._histoplot1 = pg.PlotCurveItem()
        self._histoplot1.setPen(palette.c1)
        self._hp.addItem(self._histoplot1)

        # Configure the fit of the data in the main pulse analysis display:
        self._fit_image = pg.PlotCurveItem()
        self._hp.addItem(self._fit_image)

        # setting the x axis length correctly
        self._gp.setXRange(0, self._counter_logic._number_of_gates)

        # Progress display
        self._mw.progress_lcdDisplay.display(0)

        # Setting default parameters
        self._mw.count_length_SpinBox.setValue(self._counter_logic._number_of_gates)
        self._mw.count_per_readout_SpinBox.setValue(self._counter_logic._samples_per_read)

        # Connecting user interactions
        # set at first the action buttons in the tab
        self._mw.start_counter_Action.triggered.connect(self.start_clicked)
        self._mw.stop_counter_Action.triggered.connect(self.stop_clicked)
        self._mw.save_measurement_Action.triggered.connect(self.save_clicked)
        self._mw.actionRestore_Default.triggered.connect(self.set_default_view_main_window)

        # connect now a reaction on a change of the various input widgets:
        self._mw.count_length_SpinBox.editingFinished.connect(self.count_length_changed)
        self._mw.count_per_readout_SpinBox.editingFinished.connect(self.count_per_readout_changed)

        # starting the physical measurement:
        self.sigStartGatedCounter.connect(self._counter_logic.start_count,
                                          QtCore.Qt.QueuedConnection)
        self.sigStopGatedCounter.connect(self._counter_logic.stop_count, QtCore.Qt.QueuedConnection)
        self.sigSettingsChanged.connect(self._counter_logic.set_counter_settings,
                                        QtCore.Qt.QueuedConnection)

        # connect to signals in the logic:
        self._counter_logic.sigCountSettingsChanged.connect(self.update_count_settings)
        self._counter_logic.sigCountStatusChanged.connect(self.update_count_status)
        self._counter_logic.sigCountDataUpdated.connect(self.update_count_data)

        # configuration of the combo widget
        # fit_functions = self._trace_analysis.get_fit_functions()
        # self._mw.fit_methods_ComboBox.addItems(fit_functions)
        #
        # # Push buttons
        # self._mw.fit_PushButton.clicked.connect(self.fit_clicked)


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Disconnect signals
        self._mw.start_counter_Action.triggered.disconnect()
        self._mw.stop_counter_Action.triggered.disconnect()
        self._mw.save_measurement_Action.triggered.disconnect()
        self._mw.actionRestore_Default.triggered.disconnect()

        self._mw.count_length_SpinBox.editingFinished.disconnect()
        self._mw.count_per_readout_SpinBox.editingFinished.disconnect()

        self.sigStartGatedCounter.disconnect()
        self.sigStopGatedCounter.disconnect()
        self.sigSettingsChanged.disconnect()

        self._counter_logic.sigCountSettingsChanged.disconnect()
        self._counter_logic.sigCountStatusChanged.disconnect()
        self._counter_logic.sigCountDataUpdated.disconnect()

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
        self._mw.start_counter_Action.setEnabled(False)
        self._mw.progress_lcdDisplay.display(0)
        self.sigStartGatedCounter.emit()
        return

    def stop_clicked(self):
        """ Handling the Stop button to stop and restart the counter. """
        self._mw.stop_counter_Action.setEnabled(False)
        self.sigStopGatedCounter.emit()
        return

    def update_count_status(self, is_running, is_paused):
        """
        Update the Enabled status of various elements depending on the gated counter status
        """
        if is_running:
            self._mw.start_counter_Action.setEnabled(False)
            self._mw.stop_counter_Action.setEnabled(True)
            self._mw.count_length_SpinBox.setEnabled(False)
            self._mw.count_per_readout_SpinBox.setEnabled(False)
        else:
            self._mw.start_counter_Action.setEnabled(True)
            self._mw.stop_counter_Action.setEnabled(False)
            self._mw.count_length_SpinBox.setEnabled(True)
            self._mw.count_per_readout_SpinBox.setEnabled(True)
        return

    def save_clicked(self):
        """
        Trigger the save routine in the logic. Pass also the chosen filename tag.
        """
        file_desc = self._mw.filetag_LineEdit.text()
        self._counter_logic.save_data(tag=file_desc)
        return

    def count_length_changed(self):
        """
        Handle the change of the count_length and send it to the measurement.
        """
        self.sigSettingsChanged.emit({'number_of_gates': self._mw.count_length_SpinBox.value()})
        return

    def count_per_readout_changed(self):
        """ Handling the change of the oversampling and sending it to the measurement.
        """
        self.sigSettingsChanged.emit({'samples_per_read': self._mw.count_per_readout_SpinBox.value()})
        return

    def update_count_settings(self, settings=None):
        """
        Updates the GUI upon a change of settings in the logic.
        """
        if settings is None:
            settings = dict()

        if 'number_of_gates' in settings:
            self._mw.count_length_SpinBox.setValue(settings['number_of_gates'])
            self._gp.setXRange(0, settings['number_of_gates'])
        if 'samples_per_read' in settings:
            self._mw.count_per_readout_SpinBox.setValue(settings['samples_per_read'])
        return

    def update_count_data(self, count_trace, histogram, histogram_bins, counted_gates):
        """
        Updates the data plots and the progress display.

        @param numpy.ndarray count_trace: The counts per gate
        @param numpy.ndarray histogram: The histogram of the count trace
        @param int counted_gates: The number of already counted gates
        """
        self._trace1.setData(x=np.arange(0, count_trace[0].size), y=count_trace[0])
        self._histoplot1.setData(x=histogram_bins[0], y=histogram[0], stepMode=True, fillLevel=0,
                                 brush=palettedark.c1)
        self._mw.progress_lcdDisplay.display(counted_gates)
        return

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
