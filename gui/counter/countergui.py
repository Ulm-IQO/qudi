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
    """ FIXME: Please document
    """

    # declare connectors
    counterlogic1 = Connector(interface='CounterLogic')

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._counting_logic = self.counterlogic1()

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = CounterMainWindow()

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.trace_selection_DockWidget.hide()
        self._mw.setDockNestingEnabled(True)


        # Plot labels.
        self._pw = self._mw.counter_trace_PlotWidget

        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('bottom', 'Time', units='s')

        self.curves = []

        for i, ch in enumerate(self._counting_logic.get_channels()):
            if i % 2 == 0:
                # Create an empty plot curve to be filled later, set its pen
                self.curves.append(
                    pg.PlotDataItem(pen=pg.mkPen(palette.c1), symbol=None))
                self._pw.addItem(self.curves[-1])
                self.curves.append(
                    pg.PlotDataItem(pen=pg.mkPen(palette.c2, width=3), symbol=None))
                self._pw.addItem(self.curves[-1])
            else:
                self.curves.append(
                    pg.PlotDataItem(
                        pen=pg.mkPen(palette.c3, style=QtCore.Qt.DotLine),
                        symbol='s',
                        symbolPen=palette.c3,
                        symbolBrush=palette.c3,
                        symbolSize=5))
                self._pw.addItem(self.curves[-1])
                self.curves.append(
                    pg.PlotDataItem(pen=pg.mkPen(palette.c4, width=3), symbol=None))
                self._pw.addItem(self.curves[-1])

        # setting the x axis length correctly
        self._pw.setXRange(
            0,
            self._counting_logic.get_count_length() / self._counting_logic.get_count_frequency()
        )

        #####################
        # Setting default parameters
        self._mw.count_length_SpinBox.setValue(self._counting_logic.get_count_length())
        self._mw.count_freq_SpinBox.setValue(self._counting_logic.get_count_frequency())
        self._mw.oversampling_SpinBox.setValue(self._counting_logic.get_counting_samples())
        self._display_trace = 1
        self._trace_selection = [True, True, True, True]

        #####################
        # Connecting user interactions
        self._mw.start_counter_Action.triggered.connect(self.start_clicked)
        self._mw.record_counts_Action.triggered.connect(self.save_clicked)

        self._mw.count_length_SpinBox.valueChanged.connect(self.count_length_changed)
        self._mw.count_freq_SpinBox.valueChanged.connect(self.count_frequency_changed)
        self._mw.oversampling_SpinBox.valueChanged.connect(self.oversampling_changed)

        if len(self.curves) >= 2:
            self._mw.trace_1_checkbox.setChecked(True)
        else:
            self._mw.trace_1_checkbox.setEnabled(False)
            self._mw.trace_1_radiobutton.setEnabled(False)

        if len(self.curves) >= 4:
            self._mw.trace_2_checkbox.setChecked(True)
        else:
            self._mw.trace_2_checkbox.setEnabled(False)
            self._mw.trace_2_radiobutton.setEnabled(False)

        if len(self.curves) >= 6:
            self._mw.trace_3_checkbox.setChecked(True)
        else:
            self._mw.trace_3_checkbox.setEnabled(False)
            self._mw.trace_3_radiobutton.setEnabled(False)

        if len(self.curves) >= 8:
            self._mw.trace_4_checkbox.setChecked(True)
        else:
            self._mw.trace_4_checkbox.setEnabled(False)
            self._mw.trace_4_radiobutton.setEnabled(False)

        self._mw.trace_1_checkbox.stateChanged.connect(self.trace_selection_changed)
        self._mw.trace_2_checkbox.stateChanged.connect(self.trace_selection_changed)
        self._mw.trace_3_checkbox.stateChanged.connect(self.trace_selection_changed)
        self._mw.trace_4_checkbox.stateChanged.connect(self.trace_selection_changed)

        self._mw.trace_1_radiobutton.setChecked(True)
        self._mw.trace_1_radiobutton.released.connect(self.trace_display_changed)
        self._mw.trace_2_radiobutton.released.connect(self.trace_display_changed)
        self._mw.trace_3_radiobutton.released.connect(self.trace_display_changed)
        self._mw.trace_4_radiobutton.released.connect(self.trace_display_changed)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        #####################
        # starting the physical measurement
        self.sigStartCounter.connect(self._counting_logic.startCount)
        self.sigStopCounter.connect(self._counting_logic.stopCount)

        ##################
        # Handling signals from the logic

        self._counting_logic.sigCounterUpdated.connect(self.updateData)

        # ToDo:
        # self._counting_logic.sigCountContinuousNext.connect()
        # self._counting_logic.sigCountGatedNext.connect()
        # self._counting_logic.sigCountFiniteGatedNext.connect()
        # self._counting_logic.sigGatedCounterFinished.connect()
        # self._counting_logic.sigGatedCounterContinue.connect()

        self._counting_logic.sigCountingSamplesChanged.connect(self.update_oversampling_SpinBox)
        self._counting_logic.sigCountLengthChanged.connect(self.update_count_length_SpinBox)
        self._counting_logic.sigCountFrequencyChanged.connect(self.update_count_freq_SpinBox)
        self._counting_logic.sigSavingStatusChanged.connect(self.update_saving_Action)
        self._counting_logic.sigCountingModeChanged.connect(self.update_counting_mode_ComboBox)
        self._counting_logic.sigCountStatusChanged.connect(self.update_count_status_Action)

        # Throw a deprecation warning pop-up to encourage users to switch to
        # TimeSeriesGui/TimeSeriesReaderLogic
        dialog = QtWidgets.QDialog(self._mw)
        dialog.setWindowTitle('Deprecation warning')
        label1 = QtWidgets.QLabel('Deprecation Warning:')
        label1.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        font = label1.font()
        font.setPointSize(12)
        label1.setFont(font)
        label2 = QtWidgets.QLabel('The modules CounterGui, CounterLogic and '
                                  'NationalInstrumentsXSeries are deprecated for time series '
                                  'streaming (also called "slow counting") and will be removed in '
                                  'the future.\nPlease consider switching to TimeSeriesGui, '
                                  'TimeSeriesReaderLogic and NIXSeriesInStreamer.\nSee default.cfg '
                                  'for a configuration template.')
        label2.setAlignment(QtCore.Qt.AlignVCenter)
        label2.setWordWrap(True)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        button_box.setCenterButtons(True)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label1)
        layout.addWidget(label2)
        layout.addWidget(button_box)
        button_box.accepted.connect(dialog.accept)
        dialog.setLayout(layout)
        dialog.exec()
        return 0

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def on_deactivate(self):
        # FIXME: !
        """ Deactivate the module
        """
        # disconnect signals
        self._mw.start_counter_Action.triggered.disconnect()
        self._mw.record_counts_Action.triggered.disconnect()
        self._mw.count_length_SpinBox.valueChanged.disconnect()
        self._mw.count_freq_SpinBox.valueChanged.disconnect()
        self._mw.oversampling_SpinBox.valueChanged.disconnect()
        self._mw.trace_1_checkbox.stateChanged.disconnect()
        self._mw.trace_2_checkbox.stateChanged.disconnect()
        self._mw.trace_3_checkbox.stateChanged.disconnect()
        self._mw.trace_4_checkbox.stateChanged.disconnect()
        self._mw.restore_default_view_Action.triggered.disconnect()
        self.sigStartCounter.disconnect()
        self.sigStopCounter.disconnect()
        self._counting_logic.sigCounterUpdated.disconnect()
        self._counting_logic.sigCountingSamplesChanged.disconnect()
        self._counting_logic.sigCountLengthChanged.disconnect()
        self._counting_logic.sigCountFrequencyChanged.disconnect()
        self._counting_logic.sigSavingStatusChanged.disconnect()
        self._counting_logic.sigCountingModeChanged.disconnect()
        self._counting_logic.sigCountStatusChanged.disconnect()

        self._mw.close()
        return

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """

        if self._counting_logic.module_state() == 'locked':
            if 0 < self._counting_logic.countdata_smoothed[(self._display_trace-1), -1] < 10:
                self._mw.count_value_Label.setText(
                    '{0:,.6f}'.format(self._counting_logic.countdata_smoothed[(self._display_trace-1), -1]))
            else:
                self._mw.count_value_Label.setText(
                    '{0:,.0f}'.format(self._counting_logic.countdata_smoothed[(self._display_trace-1), -1]))

            x_vals = (
                np.arange(0, self._counting_logic.get_count_length())
                / self._counting_logic.get_count_frequency())

            ymax = -1
            ymin = 2000000000
            for i, ch in enumerate(self._counting_logic.get_channels()):
                self.curves[2 * i].setData(y=self._counting_logic.countdata[i], x=x_vals)
                self.curves[2 * i + 1].setData(y=self._counting_logic.countdata_smoothed[i],
                                               x=x_vals
                                               )
                if ymax < self._counting_logic.countdata[i].max() and self._trace_selection[i]:
                    ymax = self._counting_logic.countdata[i].max()
                if ymin > self._counting_logic.countdata[i].min() and self._trace_selection[i]:
                    ymin = self._counting_logic.countdata[i].min()

            if ymin == ymax:
                ymax += 0.1
            self._pw.setYRange(0.95*ymin, 1.05*ymax)

        if self._counting_logic.get_saving_state():
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
        """ Handling the Start button to stop and restart the counter.
        """
        if self._counting_logic.module_state() == 'locked':
            self._mw.start_counter_Action.setText('Start counter')
            self.sigStopCounter.emit()
        else:
            self._mw.start_counter_Action.setText('Stop counter')
            self.sigStartCounter.emit()
        return self._counting_logic.module_state()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        if self._counting_logic.get_saving_state():
            self._mw.record_counts_Action.setText('Start Saving Data')
            self._mw.count_freq_SpinBox.setEnabled(True)
            self._mw.oversampling_SpinBox.setEnabled(True)
            self._counting_logic.save_data()
        else:
            self._mw.record_counts_Action.setText('Save')
            self._mw.count_freq_SpinBox.setEnabled(False)
            self._mw.oversampling_SpinBox.setEnabled(False)
            self._counting_logic.start_saving()
        return self._counting_logic.get_saving_state()

    ########
    # Input parameters changed via GUI

    def trace_selection_changed(self):
        """ Handling any change to the selection of the traces to display.
        """
        if self._mw.trace_1_checkbox.isChecked():
            self._trace_selection[0] = True
        else:
            self._trace_selection[0] = False
        if self._mw.trace_2_checkbox.isChecked():
            self._trace_selection[1] = True
        else:
            self._trace_selection[1] = False
        if self._mw.trace_3_checkbox.isChecked():
            self._trace_selection[2] = True
        else:
            self._trace_selection[2] = False
        if self._mw.trace_4_checkbox.isChecked():
            self._trace_selection[3] = True
        else:
            self._trace_selection[3] = False

        for i, ch in enumerate(self._counting_logic.get_channels()):
            if self._trace_selection[i]:
                self._pw.addItem(self.curves[2*i])
                self._pw.addItem(self.curves[2*i + 1])
            else:
                self._pw.removeItem(self.curves[2*i])
                self._pw.removeItem(self.curves[2*i + 1])

    def trace_display_changed(self):
        """ Handling of a change in teh selection of which counts should be shown.
        """

        if self._mw.trace_1_radiobutton.isChecked():
            self._display_trace = 1
        elif self._mw.trace_2_radiobutton.isChecked():
            self._display_trace = 2
        elif self._mw.trace_3_radiobutton.isChecked():
            self._display_trace = 3
        elif self._mw.trace_4_radiobutton.isChecked():
            self._display_trace = 4
        else:
            self._display_trace = 1

    def count_length_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
        self._counting_logic.set_count_length(self._mw.count_length_SpinBox.value())
        self._pw.setXRange(
            0,
            self._counting_logic.get_count_length() / self._counting_logic.get_count_frequency()
        )
        return self._mw.count_length_SpinBox.value()

    def count_frequency_changed(self):
        """ Handling the change of the count_frequency and sending it to the measurement.
        """
        self._counting_logic.set_count_frequency(self._mw.count_freq_SpinBox.value())
        self._pw.setXRange(
            0,
            self._counting_logic.get_count_length() / self._counting_logic.get_count_frequency()
        )
        return self._mw.count_freq_SpinBox.value()

    def oversampling_changed(self):
        """ Handling the change of the oversampling and sending it to the measurement.
        """
        self._counting_logic.set_counting_samples(samples=self._mw.oversampling_SpinBox.value())
        self._pw.setXRange(
            0,
            self._counting_logic.get_count_length() / self._counting_logic.get_count_frequency()
        )
        return self._mw.oversampling_SpinBox.value()

    ########
    # Restore default values

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
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.counter_trace_DockWidget
                               )
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8),
                               self._mw.slow_counter_parameters_DockWidget
                               )
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(QtCore.Qt.LeftDockWidgetArea),
                               self._mw.trace_selection_DockWidget
                               )

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.counting_control_ToolBar)
        return 0

    ##########
    # Handle signals from logic

    def update_oversampling_SpinBox(self, oversampling):
        """Function to ensure that the GUI displays the current value of the logic

        @param int oversampling: adjusted oversampling to update in the GUI in bins
        @return int oversampling: see above
        """
        self._mw.oversampling_SpinBox.blockSignals(True)
        self._mw.oversampling_SpinBox.setValue(oversampling)
        self._mw.oversampling_SpinBox.blockSignals(False)
        return oversampling

    def update_count_freq_SpinBox(self, count_freq):
        """Function to ensure that the GUI displays the current value of the logic

        @param float count_freq: adjusted count frequency in Hz
        @return float count_freq: see above
        """
        self._mw.count_freq_SpinBox.blockSignals(True)
        self._mw.count_freq_SpinBox.setValue(count_freq)
        self._pw.setXRange(0, self._counting_logic.get_count_length() / count_freq)
        self._mw.count_freq_SpinBox.blockSignals(False)
        return count_freq

    def update_count_length_SpinBox(self, count_length):
        """Function to ensure that the GUI displays the current value of the logic

        @param int count_length: adjusted count length in bins
        @return int count_length: see above
        """
        self._mw.count_length_SpinBox.blockSignals(True)
        self._mw.count_length_SpinBox.setValue(count_length)
        self._pw.setXRange(0, count_length / self._counting_logic.get_count_frequency())
        self._mw.count_length_SpinBox.blockSignals(False)
        return count_length

    def update_saving_Action(self, start):
        """Function to ensure that the GUI-save_action displays the current status

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
