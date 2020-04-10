# -*- coding: utf-8 -*-

"""
This file contains the Qudi counter gui.

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

from core.connector import Connector
from core.mapper import Mapper
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class CounterMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_slow_counter.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class CounterGui(GUIBase):
    """ Module class of the GUI  """

    counterlogic1 = Connector(interface='CounterLogic')

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._mw = CounterMainWindow()
        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.trace_selection_DockWidget.hide()
        self._mw.setDockNestingEnabled(True)

        self.init_plot()

        # Map views to models - This map the value of the logic attribute to the the value of the GUI view
        self.mapper = Mapper()
        self.mapper.add_mapping(self._mw.count_length_SpinBox, self.counterlogic1(), 'get_count_length',
                                model_property_notifier=self.counterlogic1().sigCountLengthChanged,
                                model_setter='set_count_length',
                                widget_property_notifier='editingFinished')

        self.mapper.add_mapping(self._mw.count_freq_SpinBox, self.counterlogic1(), 'get_count_frequency',
                                model_property_notifier=self.counterlogic1().sigCountFrequencyChanged,
                                model_setter='set_count_frequency', widget_property_notifier='editingFinished')

        self.mapper.add_mapping(self._mw.oversampling_SpinBox, self.counterlogic1(), 'get_counting_samples',
                                model_property_notifier=self.counterlogic1().sigCountingSamplesChanged,
                                model_setter='set_counting_samples', widget_property_notifier='editingFinished')

        self.counterlogic1().sigRangeChanged.connect(self.update_range)

        self._display_trace = 1
        self._trace_selection = [True, True, True, True]

        # Connecting user interactions
        self._mw.start_counter_Action.triggered.connect(self.start_clicked)
        self._mw.record_counts_Action.triggered.connect(self.save_clicked)

        number_channel = len(self._counting_logic.get_channels())
        for i in range(1, 5):
            if number_channel >= i:
                getattr(self._mw, 'trace_{}_checkbox'.format(i)).setChecked(True)
            else:
                getattr(self._mw, 'trace_{}_checkbox'.format(i)).setChecked(False)
                getattr(self._mw, 'trace_{}_radiobutton'.format(i)).setChecked(False)

            getattr(self._mw, 'trace_{}_checkbox'.format(i)).stateChanged.connect(self.trace_selection_changed)
            getattr(self._mw, 'trace_{}_radiobutton'.format(i)).released.connect(self.trace_display_changed)

        self._mw.trace_1_radiobutton.setChecked(True)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        ##################
        # Handling signals from the logic
        self._counting_logic.sigCounterUpdated.connect(self.update_data)

        # ToDo:
        # self._counting_logic.sigCountContinuousNext.connect()
        # self._counting_logic.sigCountGatedNext.connect()
        # self._counting_logic.sigCountFiniteGatedNext.connect()
        # self._counting_logic.sigGatedCounterFinished.connect()
        # self._counting_logic.sigGatedCounterContinue.connect()

        self.counterlogic1().sigSavingStatusChanged.connect(self.update_saving_Action)
        self.counterlogic1().sigCountingModeChanged.connect(self.update_counting_mode_ComboBox)
        self.counterlogic1().sigCountStatusChanged.connect(self.update_count_status_Action)

    def init_plot(self):
        """ Initialize the plot at activation """
        self._pw = self._mw.counter_trace_PlotWidget

        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('bottom', 'Time', units='s')

        self.curves = []

        for i, ch in enumerate(self._counting_logic.get_channels()):
            # Create an empty plot curve to be filled later, set its pen
            if i % 2 == 0:  # Change style every two line to see better
                self.curves.append(pg.PlotDataItem(pen=pg.mkPen(palette.c1), symbol=None))
                self.curves.append(pg.PlotDataItem(pen=pg.mkPen(palette.c2, width=3), symbol=None))
            else:
                self.curves.append(pg.PlotDataItem(pen=pg.mkPen(palette.c3, style=QtCore.Qt.DotLine),
                                                   symbol='s', symbolPen=palette.c3, symbolBrush=palette.c3,
                                                   symbolSize=5))
                self.curves.append(pg.PlotDataItem(pen=pg.mkPen(palette.c4, width=3), symbol=None))
            self._pw.addItem(self.curves[-2])
            self._pw.addItem(self.curves[-1])

        self.update_range()

    def update_range(self):
        """ Set the x range of the plot to show correctly """
        self._pw.setXRange(0, self._counting_logic.get_count_length() / self._counting_logic.get_count_frequency())

    def show(self):
        """ Make window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        """ Deactivate the module """
        self._mw.close()
        self.mapper.clear_mapping()

        # Disconnect listeners from logic properly
        self.counterlogic1().sigRangeChanged.disconnect(self.update_range)
        self.counterlogic1().sigCounterUpdated.disconnect(self.update_data)
        self.counterlogic1().sigSavingStatusChanged.disconnect(self.update_saving_Action)
        self.counterlogic1().sigCountingModeChanged.disconnect(self.update_counting_mode_ComboBox)
        self.counterlogic1().sigCountStatusChanged.disconnect(self.update_count_status_Action)

    def update_data(self):
        """ The function that grabs the data and sends it to the plot """

        if self.counterlogic1().module_state() == 'locked':
            if 0 < self.counterlogic1().countdata_smoothed[(self._display_trace-1), -1] < 10:
                self._mw.count_value_Label.setText(
                    '{0:,.6f}'.format(self.counterlogic1().countdata_smoothed[(self._display_trace-1), -1]))
            else:
                self._mw.count_value_Label.setText(
                    '{0:,.0f}'.format(self.counterlogic1().countdata_smoothed[(self._display_trace-1), -1]))

            x_vals = (
                np.arange(0, self.counterlogic1().get_count_length())
                / self.counterlogic1().get_count_frequency())

            ymax = -1
            ymin = 2000000000
            for i, ch in enumerate(self.counterlogic1().get_channels()):
                self.curves[2 * i].setData(y=self.counterlogic1().countdata[i], x=x_vals)
                self.curves[2 * i + 1].setData(y=self.counterlogic1().countdata_smoothed[i],
                                               x=x_vals
                                               )
                if ymax < self.counterlogic1().countdata[i].max() and self._trace_selection[i]:
                    ymax = self.counterlogic1().countdata[i].max()
                if ymin > self.counterlogic1().countdata[i].min() and self._trace_selection[i]:
                    ymin = self.counterlogic1().countdata[i].min()

            if ymin == ymax:
                ymax += 0.1
            self._pw.setYRange(0.95*ymin, 1.05*ymax)

        if self.counterlogic1().get_saving_state():
            self._mw.record_counts_Action.setText('Save')
            self._mw.count_freq_SpinBox.setEnabled(False)
            self._mw.oversampling_SpinBox.setEnabled(False)
        else:
            self._mw.record_counts_Action.setText('Start Saving Data')
            self._mw.count_freq_SpinBox.setEnabled(True)
            self._mw.oversampling_SpinBox.setEnabled(True)

        if self._counting_logic.module_state() == 'locked':
            self._mw.start_counter_Action.setText('Stop counter')
            self._mw.start_counter_Action.setChecked(True)
        else:
            self._mw.start_counter_Action.setText('Start counter')
            self._mw.start_counter_Action.setChecked(False)
        return 0

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.  """
        if self.counterlogic1().module_state() == 'locked':
            self._mw.start_counter_Action.setText('Start counter')
            self.counterlogic1().stopCount()
        else:
            self._mw.start_counter_Action.setText('Stop counter')
            self.counterlogic1().startCount()
        return self.counterlogic1().module_state()

    def save_clicked(self):
        """ Handling the save button to save the data into a file. """
        if self.counterlogic1().get_saving_state():
            self._mw.record_counts_Action.setText('Start Saving Data')
            self._mw.count_freq_SpinBox.setEnabled(True)
            self._mw.oversampling_SpinBox.setEnabled(True)
            self.counterlogic1().save_data()
        else:
            self._mw.record_counts_Action.setText('Save')
            self._mw.count_freq_SpinBox.setEnabled(False)
            self._mw.oversampling_SpinBox.setEnabled(False)
            self.counterlogic1().start_saving()
        return self.counterlogic1().get_saving_state()

    ########
    # Input parameters changed via GUI

    def trace_selection_changed(self):
        """ Handling any change to the selection of the traces to display. """
        for i in range(4):
            self._trace_selection[i] = getattr(self._mw, 'trace_{}_checkbox'.format(i+1)).isChecked()

        for i in range(len(self.counterlogic1().get_channels())):
            if self._trace_selection[i]:
                self._pw.addItem(self.curves[2*i])
                self._pw.addItem(self.curves[2*i + 1])
            else:
                self._pw.removeItem(self.curves[2*i])
                self._pw.removeItem(self.curves[2*i + 1])

    def trace_display_changed(self):
        """ Handling of a change in the selection of which counts should be shown. """
        display_trace = None
        for i in range(1, 5):
            if getattr(self._mw, 'trace_{}_radiobutton'.format(i)).isChecked():
                display_trace = i
        self._display_trace = display_trace if display_trace is not None else 1

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.counter_trace_DockWidget.show()
        # self._mw.slow_counter_control_DockWidget.show()
        self._mw.slow_counter_parameters_DockWidget.show()
        self._mw.trace_selection_DockWidget.hide()

        # re-dock any floating dock widgets
        self._mw.counter_trace_DockWidget.setFloating(False)
        self._mw.slow_counter_parameters_DockWidget.setFloating(False)
        self._mw.trace_selection_DockWidget.setFloating(True)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.counter_trace_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.slow_counter_parameters_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(QtCore.Qt.LeftDockWidgetArea),
                               self._mw.trace_selection_DockWidget)

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea, self._mw.counting_control_ToolBar)

    ##########
    # Handle signals from logic
    def update_saving_Action(self, start):
        """ Function to ensure that the GUI-save_action displays the current status

        @param bool start: True if the measurment saving is started
        @return bool start: see above
        """
        if start:
            self._mw.record_counts_Action.setText('Save')
            self._mw.count_freq_SpinBox.setEnabled(False)
            self._mw.oversampling_SpinBox.setEnabled(False)
        else:
            self._mw.record_counts_Action.setText('Start Saving Data')
            self._mw.count_freq_SpinBox.setEnabled(True)
            self._mw.oversampling_SpinBox.setEnabled(True)
        return start

    def update_count_status_Action(self, running):
        """Function to ensure that the GUI-save_action displays the current status

        @param bool running: True if the counting is started
        @return bool running: see above
        """
        if running:
            self._mw.start_counter_Action.setText('Stop counter')
        else:
            self._mw.start_counter_Action.setText('Start counter')
        return running

    # TODO:
    def update_counting_mode_ComboBox(self):
        self.log.warning('Not implemented yet')
        return 0

    # TODO:
    def update_smoothing_ComboBox(self):
        self.log.warning('Not implemented yet')
        return 0
