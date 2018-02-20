# -*- coding: utf-8 -*-

"""
This file contains a gui to show data from a simple data source.

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

from core.module import Connector
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic


class SimpleMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_implanter_controller_gui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class ImplanterControllerLogic(GUIBase):
    """ FIXME: Please document
    """
    _modclass = 'implantergui'
    _modtype = 'gui'

    ## declare connectors
    implanter_controller_logic = Connector(interface='ImplanterControllerLogic')

    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._implanter_logic = self.get_connector('implanter_controller_logic')

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = SimpleMainWindow()

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # Plot labels.
        self._pw = self._mw.trace_PlotWidget

        self.plot1 = self._pw.plotItem
        self.plot1.setLabel('left', 'Some Value', units='some unit', color='#00ff00')
        self.plot1.setLabel('bottom', 'Number of values', units='some unit')
        self.plot2 = self._pw.plotItem
        self.plot2.setLabel('right', 'Smooth Value', units='some unit', color='#ff0000')

        self.curvearr = []
        self.smootharr = []
        colorlist = (palette.c1, palette.c2, palette.c3, palette.c4, palette.c5, palette.c6)

        ## Create an empty plot curve to be filled later, set its pen
        self.curve=self.plot1.plot()
        self.curve.setPen(colorlist[0])
        self.smooth=self.plot2.plot()
        self.smooth.setPen(colorlist[1], width=2)

        # make correct button state
        self._mw.startAction.setChecked(False)

        #####################
        # Connecting user interactions
        self._mw.startAction.triggered.connect(self.start_clicked)
        self._mw.recordAction.triggered.connect(self.save_clicked)

        #####################
        # starting the physical measurement
        self.sigStart.connect(self._implanter_logic.startMeasure)
        self.sigStop.connect(self._implanter_logic.stopMeasure)

        self._implanter_logic.sigRepeat.connect(self.updateData)

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        # FIXME: !
        self._mw.close()

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """

        self._mw.current_value_Label.setText('{0:,.6f}'.format(self._implanter_logic.current_data))

        self.curve.setData(
            y=self._implanter_logic.data_buffer,
            x=self._implanter_logic.time_buffer
            )
        self.smooth.setData(
            y=self._implanter_logic.data_smooth,
            x=self._implanter_logic.time_buffer
            )

        if self._implanter_logic.module_state() == 'locked':
            self._mw.startAction.setText('Stop')
        else:
            self._mw.startAction.setText('Start')

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._implanter_logic.module_state() == 'locked':
            self._mw.startAction.setText('Start')
            self.sigStop.emit()
        else:
            self._mw.startAction.setText('Stop')
            self.sigStart.emit()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        return
