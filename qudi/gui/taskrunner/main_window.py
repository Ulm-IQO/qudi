# -*- coding: utf-8 -*-
"""
This file contains the QMainWindow class for the task GUI.

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
from typing import Any, Mapping, Dict, Type, Callable
from PySide2 import QtCore, QtGui, QtWidgets

from qudi.util.paths import get_artwork_dir
from qudi.core.scripting.moduletask import ModuleTask

from .taskwidget import TaskWidget


class TaskMainWindow(QtWidgets.QMainWindow):
    """
    Main Window definition for the task GUI.
    """

    sigStartTask = QtCore.Signal(str, dict)  # task name, call parameters
    sigInterruptTask = QtCore.Signal(str)  # task name
    sigClosed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('qudi: Taskrunner')

        # Create actions
        icon_path = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '22x22')
        self.action_quit = QtWidgets.QAction()
        self.action_quit.setIcon(QtGui.QIcon(os.path.join(icon_path, 'application-exit.png')))
        self.action_quit.setText('Close')
        self.action_quit.setToolTip('Close')
        self.action_quit.triggered.connect(self.close)

        # Create menu bar
        self.menubar = QtWidgets.QMenuBar()
        menu = QtWidgets.QMenu('File')
        menu.addAction(self.action_quit)
        self.menubar.addMenu(menu)
        self.setMenuBar(self.menubar)

        # Create central container widget for ModuleTask widgets
        # self.scroll_area = QtWidgets.QScrollArea()
        self.task_widgets = dict()
        self.tasks_layout = QtWidgets.QVBoxLayout()
        widget = QtWidgets.QWidget()
        widget.setLayout(self.tasks_layout)
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(widget)
        scroll_area.setWidgetResizable(True)
        self.setCentralWidget(scroll_area)

        # # Create toolbar
        # self.toolbar = QtWidgets.QToolBar()
        # self.toolbar.setOrientation(QtCore.Qt.Horizontal)
        # self.toolbar.addAction(self.action_start_task)
        # self.toolbar.addAction(self.action_pause_task)
        # self.toolbar.addAction(self.action_stop_task)
        # self.addToolBar(self.toolbar)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        super().closeEvent(event)
        self.sigClosed.emit()

    def initialize_task_widgets(self, tasks: Mapping[str, Type[ModuleTask]]) -> None:
        # Delete old task widgets
        self._clear_task_widgets()

        # Create new task widgets
        for ii, (task_name, task_type) in enumerate(tasks.items()):
            groupbox = QtWidgets.QGroupBox(task_name)
            font = groupbox.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 2)
            groupbox.setFont(font)
            widget = TaskWidget(task_type=task_type)
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(widget)
            groupbox.setLayout(layout)
            widget.sigStartTask.connect(self._get_start_task_callback(task_name))
            widget.sigInterruptTask.connect(self._get_interrupt_task_callback(task_name))
            self.tasks_layout.addWidget(groupbox)
            self.task_widgets[task_name] = widget

    @QtCore.Slot(str)
    def task_started(self, name: str) -> None:
        self.task_widgets[name].task_started()

    @QtCore.Slot(str, str)
    def task_state_changed(self, name: str, state: str) -> None:
        self.task_widgets[name].task_state_changed(state)

    @QtCore.Slot(str, object, bool)
    def task_finished(self, name: str, result: Any, success: bool) -> None:
        self.task_widgets[name].task_finished(result, success)

    def _clear_task_widgets(self) -> None:
        """ Helper method to disconnect and delete all TaskWidgets and remove them from layout """
        for widget in reversed(self.task_widgets):
            groupbox = widget.parent()
            widget.sigStartTask.disconnect()
            widget.sigInterruptTask.disconnect()
            self.tasks_layout.removeWidget(groupbox)
            groupbox.setParent(None)
            groupbox.deleteLater()
        self.task_widgets = dict()

    def _get_start_task_callback(self, task_name: str) -> Callable[[Dict[str, Any]], None]:

        def callback(parameters: Dict[str, Any]) -> None:
            self.sigStartTask.emit(task_name, parameters)

        return callback

    def _get_interrupt_task_callback(self, task_name: str) -> Callable[[], None]:

        def callback() -> None:
            self.sigInterruptTask.emit(task_name)

        return callback
