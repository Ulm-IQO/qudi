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
import datetime

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


class ImplanterGUI(GUIBase):
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
            self.log.debug('{0}: {1}'.format(key, config[key]))

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._implanter_logic = self.implanter_controller_logic()
        self._mw = SimpleMainWindow()

        self._mw.ontimedoubleSpinBox.setValue(self._implanter_logic.low_time)
        self._mw.offtimedoubleSpinBox.setValue(self._implanter_logic.high_time)
        #self._mw.offtimedoubleSpinBox.set

        #####################
        # Connecting user interactions
        self._mw.startAction.triggered.connect(self.start_clicked)
        self._mw.ontimedoubleSpinBox.editingFinished.connect(self.update_ontime)
        self._mw.offtimedoubleSpinBox.editingFinished.connect(self.update_offtime)

        #####################
        # starting the physical measurement
        self.sigStart.connect(self._implanter_logic.startMeasure)
        self.sigStop.connect(self._implanter_logic.stopMeasure)

        self._implanter_logic.sigLoop.connect(self.update_countdown)
        self._implanter_logic.sigFinished.connect(self.cd_finished)

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

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._mw.startAction.isChecked():
            self._mw.startAction.setText('Stop')
            self._mw.ontimedoubleSpinBox.setEnabled(False)
            self._mw.offtimedoubleSpinBox.setEnabled(False)
            self._mw.repeatcheckBox.setEnabled(False)
            self.sigStart.emit()
        else:
            self.sigStop.emit()

    def update_countdown(self):
        self._mw.statusBar().showMessage(
            'Countdown: {0}'.format(
                self._implanter_logic.starttime - datetime.datetime.now()
            )
        )

    def cd_finished(self):
        self._mw.startAction.setText('Start')
        self._mw.startAction.setChecked(False)
        self._mw.ontimedoubleSpinBox.setEnabled(True)
        self._mw.offtimedoubleSpinBox.setEnabled(True)
        self._mw.repeatcheckBox.setEnabled(True)

    def update_ontime(self):
        self._implanter_logic.high_time = self._mw.ontimedoubleSpinBox.value()

    def update_offtime(self):
        self._implanter_logic.low_time = self._mw.offtimedoubleSpinBox.value()
