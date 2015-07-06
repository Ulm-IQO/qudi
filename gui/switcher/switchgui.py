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

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""
import os
import numpy as np
from collections import OrderedDict
from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui
from .ui_switchgui import Ui_MainWindow
from .ui_switch_widget import Ui_SwitchWidget

class SwitchGui(GUIBase):
    """ A grephical interface to mofe switches by hand and change their calibration.
    """
    _modclass = 'SwitchGui'
    _modtype = 'gui'
    ## declare connectors
    _in = {'laserswitchlogic': 'LaserSwitchLogic'}

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

          @param object e: Fysom state change notice
        """
        self._mw = SwitchWindow()
        lsw =  self.connector['in']['laserswitchlogic']['object']
        for hw in lsw.switches:
            frame = QtGui.QGroupBox(hw[0]['hw']._name, self._mw.scrollAreaWidgetContents)
            frame.setAlignment(QtCore.Qt.AlignLeft)
            frame.setFlat(False)
            self._mw.layout.addWidget(frame)
            layout = QtGui.QVBoxLayout(frame)
            for switch in hw:
                swidget = SwitchWidget(switch)
                layout.addWidget(swidget)
        self.restoreWindowPos(self._mw)
        self.show()
       
    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()
 
    def deactivation(self, e=None):
        """ Hide window and stop ipython console.
          @param object e: Fysom state change notice
        """
        self.saveWindowPos(self._mw)
        self._mw.close()


class SwitchWindow(QtGui.QMainWindow, Ui_MainWindow):
    """ Helper class for window loaded from UI file.
    """
    def __init__(self):
        """ Create the switch GUI window.
        """
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        self.layout = QtGui.QVBoxLayout(self.scrollArea)

class SwitchWidget(QtGui.QWidget, Ui_SwitchWidget):
    """ A widget that shows all data associated to a switch.
    """
    def __init__(self, switch):
        """ Create a switch widget.

          @param dict switch: dict that contains reference to hardware  module as 'hw' and switch number as 'n'.
        """
        QtGui.QWidget.__init__(self)
        self.setupUi(self)
        self.switch = switch
        self.SwitchButton.setChecked( self.switch['hw'].getSwitchState(self.switch['n']) )
        self.calOffVal.setValue( self.switch['hw'].getCalibration(self.switch['n'], 'Off') )
        self.calOnVal.setValue(self.switch['hw'].getCalibration(self.switch['n'], 'On'))
        self.switchTimeLabel.setText('{0}s'.format(self.switch['hw'].getSwitchTime(self.switch['n'])))
        self.SwitchButton.clicked.connect(self.toggleSwitch)

    def toggleSwitch(self):
        """ Invert the state of the switch associated with this widget.
        """
        if self.SwitchButton.isChecked():
            self.switch['hw'].switchOn(self.switch['n'])
        else:
            self.switch['hw'].switchOff(self.switch['n'])

    def switchStateUpdated(self):
        """ Get state of switch from hardware module and adjust checkbox to correct value.
        """
        self.SwitchButton.setChecked(self.switch['hw'].getSwitchState(self.switch['n']))

