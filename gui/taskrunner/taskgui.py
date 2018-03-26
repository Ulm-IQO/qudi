# -*- coding: utf-8 -*-
"""
This file contains the Qudi task runner GUI.

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


class TaskGui(GUIBase):
    """ A grephical interface to mofe switches by hand and change their calibration.
    """
    _modclass = 'TaskGui'
    _modtype = 'gui'
    ## declare connectors
    tasklogic = Connector(interface='TaskRunner')

    sigRunTaskFromList = QtCore.Signal(object)
    sigPauseTaskFromList = QtCore.Signal(object)
    sigStopTaskFromList = QtCore.Signal(object)

    def on_activate(self):
        """Create all UI objects and show the window.
        """
        self._mw = TaskMainWindow()
        self.restoreWindowPos(self._mw)
        self.logic = self.tasklogic()
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

    def on_deactivate(self):
        """ Hide window and stop ipython console.
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
        try:
            if index2 is not None and selected[0].row() != index2.row():
                return
        except:
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

class TaskMainWindow(QtWidgets.QMainWindow):
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

