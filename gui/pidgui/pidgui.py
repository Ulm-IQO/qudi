# -*- coding: utf-8 -*-

"""
This file contains a gui for the pid controller logic.

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


class PIDMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pid_control.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class PIDGui(GUIBase):
    """ GUI to control/monitor a PID device
    """

    pidlogic = Connector(interface='PIDLogic')

    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()

    def on_activate(self):
        """ initialisation of the GUI """

        self._mw = PIDMainWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # Plot labels.
        self._pw = self._mw.trace_PlotWidget

        self.plot1 = self._pw.plotItem
        self.plot1.setLabel(
            'left',
            '<font color={0}>Process Value</font> and <font color={1}>Setpoint</font>'.format(
                palette.c1.name(),
                palette.c2.name()),
             units=self.pidlogic().get_process_unit()[0])
        self.plot1.setLabel('bottom', 'Time', units='s')
        self.plot1.showAxis('right')
        self.plot1.getAxis('right').setLabel(
            'Control Value',
            units=self.pidlogic().get_control_unit()[0],
            color=palette.c3.name())

        self.plot2 = pg.ViewBox()
        self.plot1.scene().addItem(self.plot2)
        self.plot1.getAxis('right').linkToView(self.plot2)
        self.plot2.setXLink(self.plot1)

        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = pg.PlotDataItem(pen=pg.mkPen(palette.c1),#, style=QtCore.Qt.DotLine),
                                       symbol=None
                                       #symbol='o',
                                       #symbolPen=palette.c1,
                                       #symbolBrush=palette.c1,
                                       #symbolSize=3
                                       )

        self._curve3 = pg.PlotDataItem(pen=pg.mkPen(palette.c2),
                                       symbol=None
                                       )

        self._curve2 = pg.PlotDataItem(pen=pg.mkPen(palette.c3),#, style=QtCore.Qt.DotLine),
                                       symbol=None
                                       #symbol='o',
                                       #symbolPen=palette.c3,
                                       #symbolBrush=palette.c3,
                                       #symbolSize=3
                                       )

#        self._curve1 = pg.PlotCurveItem()
#        self._curve1.setPen(palette.c1)

#        self._curve3 = pg.PlotCurveItem()
#        self._curve3.setPen(palette.c2)

#        self._curve2 = pg.PlotCurveItem()
#        self._curve2.setPen(palette.c3)


        self.plot1.addItem(self._curve1)
        self.plot1.addItem(self._curve3)
        self.plot2.addItem(self._curve2)

        self.updateViews()
        self.plot1.vb.sigResized.connect(self.updateViews)

        # setting the x axis length correctly
        self._pw.setXRange(0, self.pidlogic().get_buffer_length() * self.pidlogic().timestep)

        #####################
        # Setting default parameters
        self._mw.P_DoubleSpinBox.setValue(self.pidlogic().get_kp())
        self._mw.I_DoubleSpinBox.setValue(self.pidlogic().get_ki())
        self._mw.D_DoubleSpinBox.setValue(self.pidlogic().get_kd())
        self._mw.setpointDoubleSpinBox.setValue(self.pidlogic().get_setpoint())
        self._mw.manualDoubleSpinBox.setValue(self.pidlogic().get_manual_value())
        self._mw.pidEnabledCheckBox.setChecked(self.pidlogic().get_enabled())

        # make correct button state
        self._mw.start_control_Action.setChecked(self.pidlogic().get_enabled())

        #####################
        # Connecting user interactions
        self._mw.start_control_Action.triggered.connect(self.start_clicked)
        self._mw.record_control_Action.triggered.connect(self.save_clicked)

        self._mw.P_DoubleSpinBox.valueChanged.connect(self.kpChanged)
        self._mw.I_DoubleSpinBox.valueChanged.connect(self.kiChanged)
        self._mw.D_DoubleSpinBox.valueChanged.connect(self.kdChanged)

        self._mw.setpointDoubleSpinBox.valueChanged.connect(self.setpointChanged)
        self._mw.manualDoubleSpinBox.valueChanged.connect(self.manualValueChanged)
        self._mw.pidEnabledCheckBox.toggled.connect(self.pidEnabledChanged)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        #####################
        # starting the physical measurement
        self.sigStart.connect(self.pidlogic().start_loop)
        self.sigStop.connect(self.pidlogic().stop_loop)

        self.pidlogic().sigUpdateDisplay.connect(self.updateData)

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mw.close()

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """

        if self.pidlogic().module_state() != 'idle':
            self._mw.process_value_Label.setText(
                '<font color={0}>{1:,.3f}</font>'.format(
                palette.c1.name(),
                self.pidlogic().history[0, -1]))
            self._mw.control_value_Label.setText(
                '<font color={0}>{1:,.3f}</font>'.format(
                palette.c3.name(),
                self.pidlogic().history[1, -1]))
            self._mw.setpoint_value_Label.setText(
                '<font color={0}>{1:,.3f}</font>'.format(
                palette.c2.name(),
                self.pidlogic().history[2, -1]))
            extra = self.pidlogic().get_extra()
            if 'P' in extra:
                self._mw.labelkP.setText('{0:,.6f}'.format(extra['P']))
            if 'I' in extra:
                self._mw.labelkI.setText('{0:,.6f}'.format(extra['I']))
            if 'D' in extra:
                self._mw.labelkD.setText('{0:,.6f}'.format(extra['D']))
            self._curve1.setData(
                y=self.pidlogic().history[0],
                x=np.arange(0, self.pidlogic().get_buffer_length()) * self.pidlogic().timestep
                )
            self._curve2.setData(
                y=self.pidlogic().history[1],
                x=np.arange(0, self.pidlogic().get_buffer_length()) * self.pidlogic().timestep
                )
            self._curve3.setData(
                y=self.pidlogic().history[2],
                x=np.arange(0, self.pidlogic().get_buffer_length()) * self.pidlogic().timestep
                )

        if self.pidlogic().get_saving_state():
            self._mw.record_control_Action.setText('Save')
        else:
            self._mw.record_control_Action.setText('Start Saving Data')

        if self.pidlogic().module_state() != 'idle':
            self._mw.start_control_Action.setText('Stop')
        else:
            self._mw.start_control_Action.setText('Start')

    def updateViews(self):
    ## view has resized; update auxiliary views to match
        self.plot2.setGeometry(self.plot1.vb.sceneBoundingRect())

        ## need to re-update linked axes since this was called
        ## incorrectly while views had different shapes.
        ## (probably this should be handled in ViewBox.resizeEvent)
        self.plot2.linkedViewChanged(self.plot1.vb, self.plot2.XAxis)

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self.pidlogic().module_state() == 'running':
            self._mw.start_control_Action.setText('Start')
            self.sigStop.emit()
        else:
            self._mw.start_control_Action.setText('Stop')
            self.sigStart.emit()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        if self.pidlogic().get_saving_state():
            self._mw.record_counts_Action.setText('Start Saving Data')
            self.pidlogic().save_data()
        else:
            self._mw.record_counts_Action.setText('Save')
            self.pidlogic().start_saving()

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.pid_trace_DockWidget.show()
        self._mw.pid_parameters_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.pid_trace_DockWidget.setFloating(False)
        self._mw.pid_parameters_DockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.pid_trace_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.pid_parameters_DockWidget)

    def kpChanged(self):
        self.pidlogic().set_kp(self._mw.P_DoubleSpinBox.value())

    def kiChanged(self):
        self.pidlogic().set_ki(self._mw.I_DoubleSpinBox.value())

    def kdChanged(self):
        self.pidlogic().set_kd(self._mw.D_DoubleSpinBox.value())

    def setpointChanged(self):
        self.pidlogic().set_setpoint(self._mw.setpointDoubleSpinBox.value())

    def manualValueChanged(self):
        self.pidlogic().set_manual_value(self._mw.manualDoubleSpinBox.value())

    def pidEnabledChanged(self, state):
        self.pidlogic().set_enabled(state)
