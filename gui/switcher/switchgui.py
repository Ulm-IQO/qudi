# -*- coding: utf-8 -*-
"""
This file contains the Qudi console GUI module.

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

from core.module import Connector
from gui.guibase import GUIBase
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic


class SwitchGui(GUIBase):
    """ A grephical interface to mofe switches by hand and change their calibration.
    """
    _modclass = 'SwitchGui'
    _modtype = 'gui'
    ## declare connectors
    switchlogic = Connector(interface='SwitchLogic')

    def on_activate(self):
        """Create all UI objects and show the window.
        """
        self._mw = SwitchMainWindow()
        lsw =  self.get_connector('switchlogic')
        # For each switch that the logic has, add a widget to the GUI to show its state
        for hw in lsw.switches:
            frame = QtWidgets.QGroupBox(hw, self._mw.scrollAreaWidgetContents)
            frame.setAlignment(QtCore.Qt.AlignLeft)
            frame.setFlat(False)
            self._mw.layout.addWidget(frame)
            layout = QtWidgets.QVBoxLayout(frame)
            for switch in lsw.switches[hw]:
                swidget = SwitchWidget(switch, lsw.switches[hw][switch])
                layout.addWidget(swidget)

        self.restoreWindowPos(self._mw)
        self.show()

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def on_deactivate(self):
        """ Hide window and stop ipython console.
        """
        self.saveWindowPos(self._mw)
        self._mw.close()


class SwitchMainWindow(QtWidgets.QMainWindow):
    """ Helper class for window loaded from UI file.
    """
    def __init__(self):
        """ Create the switch GUI window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_switchgui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

        # Add layout that we want to fill
        self.layout = QtWidgets.QVBoxLayout(self.scrollArea)

class SwitchWidget(QtWidgets.QWidget):
    """ A widget that shows all data associated to a switch.
    """
    def __init__(self, switch, hwobject):
        """ Create a switch widget.

          @param dict switch: dict that contains reference to hardware  module as 'hw' and switch number as 'n'.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_switch_widget.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)

        # get switch states from the logic and put them in the GUI elements
        self.switch = switch
        self.hw = hwobject
        self.SwitchButton.setChecked( self.hw.getSwitchState(self.switch) )
        self.calOffVal.setValue( self.hw.getCalibration(self.switch, 'Off') )
        self.calOnVal.setValue(self.hw.getCalibration(self.switch, 'On'))
        self.switchTimeLabel.setText('{0}s'.format(self.hw.getSwitchTime(self.switch)))
        # connect button
        self.SwitchButton.clicked.connect(self.toggleSwitch)

    def toggleSwitch(self):
        """ Invert the state of the switch associated with this widget.
        """
        if self.SwitchButton.isChecked():
            self.hw.switchOn(self.switch)
        else:
            self.hw.switchOff(self.switch)

    def switchStateUpdated(self):
        """ Get state of switch from hardware module and adjust checkbox to correct value.
        """
        self.SwitchButton.setChecked(self.hw.getSwitchState(self.switch))

