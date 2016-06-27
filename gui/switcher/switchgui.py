# -*- coding: utf-8 -*-
"""
This file contains the QuDi console GUI module.

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
import os
import numpy as np
from collections import OrderedDict
from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui, uic

class SwitchGui(GUIBase):
    """ A grephical interface to mofe switches by hand and change their calibration.
    """
    _modclass = 'SwitchGui'
    _modtype = 'gui'
    ## declare connectors
    _in = {'switchlogic': 'SwitchLogic'}

    def __init__(self, manager, name, config, **kwargs):
        """ Create the switch control GUI.

          @param object manager: Manager object that this module was loaded from
          @param str name: Unique module name
          @param dict config: Module configuration
          @param dict kwargs: Optional arguments as a dict
        """
        c_dict = {'onactivate': self.initUI, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)

    def initUI(self, e=None):
        """Create all UI objects and show the window.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self._mw = SwitchMainWindow()
        lsw =  self.connector['in']['switchlogic']['object']
        # For each switch that the logic has, add a widget to the GUI to show its state
        for hw in lsw.switches:
            frame = QtGui.QGroupBox(hw, self._mw.scrollAreaWidgetContents)
            frame.setAlignment(QtCore.Qt.AlignLeft)
            frame.setFlat(False)
            self._mw.layout.addWidget(frame)
            layout = QtGui.QVBoxLayout(frame)
            for switch in lsw.switches[hw]:
                swidget = SwitchWidget(switch, lsw.switches[hw][switch])
                layout.addWidget(swidget)

        self.restoreWindowPos(self._mw)
        self.show()

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def deactivation(self, e=None):
        """ Hide window and stop ipython console.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self.saveWindowPos(self._mw)
        self._mw.close()


class SwitchMainWindow(QtGui.QMainWindow):
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
        self.layout = QtGui.QVBoxLayout(self.scrollArea)

class SwitchWidget(QtGui.QWidget):
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

