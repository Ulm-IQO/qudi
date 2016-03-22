# -*- coding: utf-8 -*-
"""
This file contains the QuDi logic module base class.

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
from pyqtgraph.Qt import QtCore, QtGui, uic

class TaskGui(GUIBase):
    """ A grephical interface to mofe switches by hand and change their calibration.
    """
    _modclass = 'TaskGui'
    _modtype = 'gui'
    ## declare connectors
    _in = {'tasklogic': 'TaskRunner'}

    sigRunTaskFromList = QtCore.Signal(object)
    sigPauseTaskFromList = QtCore.Signal(object)
    sigStopTaskFromList = QtCore.Signal(object)

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
        self._mw = TaskMainWindow()
        self.restoreWindowPos(self._mw)
        self.logic = self.connector['in']['tasklogic']['object']
        self._mw.taskTableView.setModel(self.logic.model)
        self._mw.taskTableView.clicked.connect(self.setRunToolState)
        self._mw.actionStart_Task.triggered.connect(self.manualStart)
        self._mw.actionPause_Task.triggered.connect(self.manualPause)
        self._mw.actionStop_Task.triggered.connect(self.manualStop)
        self.sigRunTaskFromList.connect(self.logic.startTaskByIndex)
        self.sigPauseTaskFromList.connect(self.logic.pauseTaskByIndex)
        self.sigStopTaskFromList.connect(self.logic.stopTaskByIndex)
        self.logic.model.dataChanged.connect(lambda i1, i2: self.setRunToolState(None, i1))
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

    def manualStart(self):
        selected = self._mw.taskTableView.selectedIndexes()
        if len(selected) >= 1:
            self.sigRunTaskFromList.emit(selected[0])

    def manualPause(self):
        selected = self._mw.taskTableView.selectedIndexes()
        if len(selected) >= 1:
            self.sigPauseTaskFromList.emit(selected[0])

    def manualStop(self):
        selected = self._mw.taskTableView.selectedIndexes()
        if len(selected) >= 1:
            self.sigStopTaskFromList.emit(selected[0])

    def setRunToolState(self, index, index2=None):
        selected = self._mw.taskTableView.selectedIndexes()

        if not index2 is None and selected[0].row() != index2.row():
                return

        if len(selected) >= 1:
            state = self.logic.model.storage[selected[0].row()]['object'].current
            if state == 'stopped':
                self._mw.actionStart_Task.setEnabled(True)
                self._mw.actionStop_Task.setEnabled(False)
                self._mw.actionPause_Task.setEnabled(False)
            elif state == 'running':
                self._mw.actionStart_Task.setEnabled(False)
                self._mw.actionStop_Task.setEnabled(True)
                self._mw.actionPause_Task.setEnabled(True)
            elif state == 'paused':
                self._mw.actionStart_Task.setEnabled(True)
                self._mw.actionStop_Task.setEnabled(False)
                self._mw.actionPause_Task.setEnabled(True)
            else:
                self._mw.actionStart_Task.setEnabled(False)
                self._mw.actionStop_Task.setEnabled(False)
                self._mw.actionPause_Task.setEnabled(False)

class TaskMainWindow(QtGui.QMainWindow):
    """ Helper class for window loaded from UI file.
    """
    def __init__(self):
        """ Create the switch GUI window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_taskgui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

