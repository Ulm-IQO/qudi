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
from qtpy import QtCore, QtGui, QtWidgets
from core.util.modules import get_main_dir


class TaskMainWindow(QtWidgets.QMainWindow):
    """
    Main Window definition for the task GUI.
    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.setWindowTitle('qudi: task runner')
        self.setAcceptDrops(False)

        # Create actions
        icon_path = os.path.join(get_main_dir(), 'artwork', 'icons', 'oxygen', '22x22')
        self.action_start_task = QtWidgets.QAction()
        self.action_start_task.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'media-playback-start.png')))
        self.action_start_task.setText('Start/Resume task')
        self.action_start_task.setToolTip('Start/Resume task')
        self.action_start_task.setEnabled(False)
        self.action_pause_task = QtWidgets.QAction()
        self.action_pause_task.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'media-playback-pause.png')))
        self.action_pause_task.setText('Pause task')
        self.action_pause_task.setToolTip('Pause task')
        self.action_pause_task.setEnabled(False)
        self.action_stop_task = QtWidgets.QAction()
        self.action_stop_task.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'media-playback-stop.png')))
        self.action_stop_task.setText('Stop task')
        self.action_stop_task.setToolTip('Stop task')
        self.action_stop_task.setEnabled(False)
        self.action_quit = QtWidgets.QAction()
        self.action_quit.setIcon(QtGui.QIcon(os.path.join(icon_path, 'application-exit.png')))
        self.action_quit.setText('Close')
        self.action_quit.setToolTip('Close')

        # Create menu bar
        self.menubar = QtWidgets.QMenuBar()
        menu = QtWidgets.QMenu('File')
        menu.addAction(self.action_quit)
        self.menubar.addMenu(menu)
        self.setMenuBar(self.menubar)

        # Create toolbar
        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setOrientation(QtCore.Qt.Horizontal)
        self.toolbar.addAction(self.action_start_task)
        self.toolbar.addAction(self.action_pause_task)
        self.toolbar.addAction(self.action_stop_task)
        self.addToolBar(self.toolbar)

        # Create central widget
        self.task_table_view = QtWidgets.QTableView()
        self.task_table_view.setObjectName('taskTableView')
        self.setCentralWidget(self.task_table_view)
