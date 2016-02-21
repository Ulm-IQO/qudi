# -*- coding: utf-8 -*-

"""
This file contains the GUI for control of a Gated Counter.

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

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""
import os
import numpy as np
from collections import OrderedDict

from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui, uic


class GatedCounterMainWindow(QtGui.QMainWindow):
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

    _modclass = 'gatedcountergui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'gatedcounterlogic1': 'GatedCounterLogic'}


    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.initUI,
                         'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.
        """
        self._gc_logic = self.connector['in']['gatedcounterlogic1']['object']

        self._mw = GatedCounterMainWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        self.set_default_view_main_window()

    def deactivation(self, e=None):
        """
        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method initUI.
        """
        self._mw.close()

    def show(self):
        """ Make main window visible and put it above all other windows. """
        # Show the Main Gated Counter GUI:
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def set_default_view_main_window(self):
        self._mw.control_param_DockWidget.setFloating(False)
        self._mw.count_trace_DockWidget.setFloating(False)
        self._mw.histogram_DockWidget.setFloating(False)

        # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(4), self._mw.curr_pos_DockWidget)
        # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.move_rel_DockWidget)
        # self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.move_abs_DockWidget)