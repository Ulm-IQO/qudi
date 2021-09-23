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

from PySide2 import QtCore

from qudi.core.connector import Connector
from qudi.core.module import GuiBase

from .main_window import TaskMainWindow


class TaskRunnerGui(GuiBase):
    """
    TODO: Document
    """

    # declare connectors
    _task_runner = Connector(name='task_runner', interface='TaskRunnerLogic')

    sigStartTask = QtCore.Signal(str, tuple, dict)  # name, args, kwargs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None

    def on_activate(self):
        """Create all UI objects and show the window.
        """
        # Initialize main window and connect task widgets
        taskrunner = self._task_runner()
        self._mw = TaskMainWindow()
        self._mw.initialize_task_widgets(taskrunner.configured_task_types)
        self._mw.sigStartTask.connect(lambda name, kwargs: self.sigStartTask.emit(name, (), kwargs))
        self.sigStartTask.connect(taskrunner.run_task, QtCore.Qt.QueuedConnection)
        self._mw.sigInterruptTask.connect(taskrunner.interrupt_task, QtCore.Qt.QueuedConnection)
        self._mw.sigClosed.connect(self._deactivate_self)
        taskrunner.sigTaskStarted.connect(self._mw.task_started, QtCore.Qt.QueuedConnection)
        taskrunner.sigTaskStateChanged.connect(self._mw.task_state_changed,
                                               QtCore.Qt.QueuedConnection)
        taskrunner.sigTaskFinished.connect(self._mw.task_finished, QtCore.Qt.QueuedConnection)

        # Set current task states
        for task_name, task_state in taskrunner.task_states.items():
            if task_state != 'stopped':
                self._mw.task_started(task_name)
            else:
                self._mw.task_finished(task_name, None, False)
            self._mw.task_state_changed(task_name, task_state)
        # ToDo: Also set task results here

        self._restore_window_geometry(self._mw)
        self.show()

    def show(self):
        """ Make sure that the window is visible and at the top.
        """
        self._mw.show()

    @QtCore.Slot()
    def _deactivate_self(self):
        self._qudi_main.module_manager.deactivate_module(self._meta['name'])

    def on_deactivate(self):
        """ Hide window and stop ipython console.
        """
        self._save_window_geometry(self._mw)
        self._mw.close()
        self._mw.sigStartTask.disconnect()
        self.sigStartTask.disconnect()
        self._mw.sigInterruptTask.disconnect()
        self._mw.sigClosed.disconnect()
        taskrunner = self._task_runner()
        taskrunner.sigTaskStarted.disconnect(self._mw.task_started, QtCore.Qt.QueuedConnection)
        taskrunner.sigTaskStateChanged.disconnect(self._mw.task_state_changed,
                                               QtCore.Qt.QueuedConnection)
        taskrunner.sigTaskFinished.disconnect(self._mw.task_finished, QtCore.Qt.QueuedConnection)
        self._mw = None
