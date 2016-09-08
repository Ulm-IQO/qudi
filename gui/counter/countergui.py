# -*- coding: utf-8 -*-

"""
This file contains the QuDi counter gui.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
import pyqtgraph as pg
import os

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic

from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette


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
    _modclass = 'countergui'
    _modtype = 'gui'

    # declare connectors
    _in = {'counterlogic1': 'CounterLogic'}

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self, e):
        """ Definition and initialisation of the GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self._counting_logic = self.connector['in']['counterlogic1']['object']

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = CounterMainWindow()

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # Plot labels.
        self._pw = self._mw.counter_trace_PlotWidget

        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('bottom', 'Time', units='s')

        # Create an empty plot curve to be filled later, set its pen
        self._curve1 = pg.PlotDataItem(pen=pg.mkPen(palette.c1),#, style=QtCore.Qt.DotLine),
                                       symbol=None
                                       #symbol='o',
                                       #symbolPen=palette.c1,
                                       #symbolBrush=palette.c1,
                                       #symbolSize=5
                                       )
        self._curve2 = pg.PlotDataItem(pen=pg.mkPen(palette.c2, width=3), symbol=None)

        self._pw.addItem(self._curve1)
        self._pw.addItem(self._curve2)

        # TODO: This is pretty bad, to directly inquire about the HW device from the GUI via the
        #       logic.  There needs to be a much better way to do this!
        if hasattr(self._counting_logic._counting_device, '_photon_source2'):
            if self._counting_logic._counting_device._photon_source2 is not None:
                self._curve3 = pg.PlotDataItem(pen=pg.mkPen(palette.c3, style=QtCore.Qt.DotLine),
                                               symbol='s',
                                               symbolPen=palette.c3,
                                               symbolBrush=palette.c3,
                                               symbolSize=5
                                               )
                self._curve4 = pg.PlotDataItem(pen=pg.mkPen(palette.c4, width=3), symbol=None)

                self._pw.addItem(self._curve3)
                self._pw.addItem(self._curve4)

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

        #####################
        # Connecting user interactions
        self._mw.start_counter_Action.triggered.connect(self.start_clicked)
        self._mw.record_counts_Action.triggered.connect(self.save_clicked)

        self._mw.count_length_SpinBox.valueChanged.connect(self.count_length_changed)
        self._mw.count_freq_SpinBox.valueChanged.connect(self.count_frequency_changed)
        self._mw.oversampling_SpinBox.valueChanged.connect(self.oversampling_changed)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        #####################
        # starting the physical measurement
        self.sigStartCounter.connect(self._counting_logic.startCount)
        self.sigStopCounter.connect(self._counting_logic.stopCount)

        self._counting_logic.sigCounterUpdated.connect(self.updateData)

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self, e):
        # FIXME: !
        """ Deactivate the module

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._mw.close()

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """

        if self._counting_logic.getState() == 'locked':
            self._mw.count_value_Label.setText(
                '{0:,.0f}'.format(self._counting_logic.countdata_smoothed[-1])
            )

            x_vals = (np.arange(0, self._counting_logic.get_count_length())
                      / self._counting_logic.get_count_frequency()
                      )

            self._curve1.setData(y=self._counting_logic.countdata, x=x_vals)
            self._curve2.setData(y=self._counting_logic.countdata_smoothed, x=x_vals)

            # TODO: This is pretty bad, to directly inquire about the HW device from the GUI via
            #       the logic.  There needs to be a much better way to do this!
            if hasattr(self._counting_logic._counting_device, '_photon_source2'):
                if self._counting_logic._counting_device._photon_source2 is not None:
                    self._curve3.setData(y=self._counting_logic.countdata2,
                                         x=x_vals
                                         )
                    self._curve4.setData(y=self._counting_logic.countdata_smoothed2,
                                         x=x_vals
                                         )

        if self._counting_logic.get_saving_state():
            self._mw.record_counts_Action.setText('Save')
            self._mw.count_freq_SpinBox.setEnabled(False)
            self._mw.oversampling_SpinBox.setEnabled(False)
        else:
            self._mw.record_counts_Action.setText('Start Saving Data')
            self._mw.count_freq_SpinBox.setEnabled(True)
            self._mw.oversampling_SpinBox.setEnabled(True)

        if self._counting_logic.getState() == 'locked':
            self._mw.start_counter_Action.setText('Stop counter')
        else:
            self._mw.start_counter_Action.setText('Start counter')

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._counting_logic.getState() == 'locked':
            self._mw.start_counter_Action.setText('Start counter')
            self.sigStopCounter.emit()
        else:
            self._mw.start_counter_Action.setText('Stop counter')
            self.sigStartCounter.emit()

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

    def count_length_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
#        print ('count_length_changed: {0:d}'.format(self._count_length_display.value()))
        self._counting_logic.set_count_length(self._mw.count_length_SpinBox.value())
        self._pw.setXRange(
            0,
            self._counting_logic.get_count_length() / self._counting_logic.get_count_frequency()
        )

    def count_frequency_changed(self):
        """ Handling the change of the count_frequency and sending it to the measurement.
        """
#        print ('count_frequency_changed: {0:d}'.format(self._mw.count_freq_SpinBox.value()))
        self._counting_logic.set_count_frequency(self._mw.count_freq_SpinBox.value())
        self._pw.setXRange(
            0,
            self._counting_logic.get_count_length() / self._counting_logic.get_count_frequency()
        )

    def oversampling_changed(self):
        """ Handling the change of the oversampling and sending it to the measurement.
        """
        self._counting_logic.set_counting_samples(samples=self._mw.oversampling_SpinBox.value())
        self._pw.setXRange(
            0,
            self._counting_logic.get_count_length() / self._counting_logic.get_count_frequency()
        )

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.counter_trace_DockWidget.show()
        # self._mw.slow_counter_control_DockWidget.show()
        self._mw.slow_counter_parameters_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.counter_trace_DockWidget.setFloating(False)
        self._mw.slow_counter_parameters_DockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.counter_trace_DockWidget
                               )
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8),
                               self._mw.slow_counter_parameters_DockWidget
                               )

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.counting_control_ToolBar)
