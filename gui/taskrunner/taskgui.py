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

from core.connector import Connector
from core.gui.guibase import GUIBase
from qtpy import QtCore
from .taskwindow import TaskMainWindow


class TaskGui(GUIBase):
    """
    TODO: Document
    """

    # declare connectors
    tasklogic = Connector(interface='TaskRunner')

    sigRunTaskFromList = QtCore.Signal(object)
    sigPauseTaskFromList = QtCore.Signal(object)
    sigStopTaskFromList = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None

    def on_activate(self):
        """Create all UI objects and show the window.
        """
        self._mw = TaskMainWindow()
        self._mw.task_table_view.setModel(self.tasklogic().model)
        self._mw.task_table_view.clicked.connect(self.set_run_tool_state)
        self._mw.action_start_task.triggered.connect(self.manual_start)
        self._mw.action_pause_task.triggered.connect(self.manual_pause)
        self._mw.action_stop_task.triggered.connect(self.manual_stop)
        self.sigRunTaskFromList.connect(self.tasklogic().start_task_by_index)
        self.sigPauseTaskFromList.connect(self.tasklogic().pause_task_by_index)
        self.sigStopTaskFromList.connect(self.tasklogic().stop_task_by_index)
        self.tasklogic().model.dataChanged.connect(lambda i1, i2: self.set_run_tool_state(None, i1))
        self.restore_window_pos(self._mw)
        self.show()

    def show(self):
        """ Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def on_deactivate(self):
        """ Hide window and stop ipython console.
        """
        self.sigRunTaskFromList.disconnect()
        self.sigPauseTaskFromList.disconnect()
        self.sigStopTaskFromList.disconnect()
        self.save_window_pos(self._mw)
        self._mw.close()

    def manual_start(self):
        selected = self._mw.task_table_view.selectedIndexes()
        if len(selected) >= 1:
            self.sigRunTaskFromList.emit(selected[0])

    def manual_pause(self):
        selected = self._mw.task_table_view.selectedIndexes()
        if len(selected) >= 1:
            self.sigPauseTaskFromList.emit(selected[0])

    def manual_stop(self):
        selected = self._mw.task_table_view.selectedIndexes()
        if len(selected) >= 1:
            self.sigStopTaskFromList.emit(selected[0])

    def set_run_tool_state(self, index, index2=None):
        selected = self._mw.task_table_view.selectedIndexes()
        try:
            if index2 is not None and selected[0].row() != index2.row():
                return
        except:
            return

        if len(selected) >= 1:
            state = self.tasklogic().model.storage[selected[0].row()]['object'].current
            if state == 'stopped':
                self._mw.action_start_task.setEnabled(True)
                self._mw.action_stop_task.setEnabled(False)
                self._mw.action_pause_task.setEnabled(False)
            elif state == 'running':
                self._mw.action_start_task.setEnabled(False)
                self._mw.action_stop_task.setEnabled(True)
                self._mw.action_pause_task.setEnabled(True)
            elif state == 'paused':
                self._mw.action_start_task.setEnabled(True)
                self._mw.action_stop_task.setEnabled(False)
                self._mw.action_pause_task.setEnabled(True)
            else:
                self._mw.action_start_task.setEnabled(False)
                self._mw.action_stop_task.setEnabled(False)
                self._mw.action_pause_task.setEnabled(False)
