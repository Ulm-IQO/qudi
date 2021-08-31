# -*- coding: utf-8 -*-
"""
This file contains the Qudi task runner module.

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

import importlib
from PySide2 import QtCore
from typing import Any, Optional, Sequence, Iterable, Mapping

from qudi.util.models import ListTableModel
from qudi.core.module import LogicBase
from qudi.core.scripting.moduletask import ModuleTask
from qudi.core.scripting.modulescript import ModuleScriptsDictTableModel
from qudi.core.configoption import ConfigOption


class TaskInstanceListTableModel(ListTableModel):
    """ An extension of the ListTableModel for keeping ModuleTask instances.
    """
    def __init__(self):
        super().__init__(header='Task Name')
        # super().__init__(header=['Task Name', 'Current State', 'Result', 'Involved Modules'])

    def data(self, index: QtCore.QModelIndex, role: QtCore.Qt.ItemDataRole) -> Any:
        """ Get data from model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return object: data for given cell and role
        """
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            name, task = self[index.row()]
            if index.column() == 0:
                return name
            elif index.column() == 1:
                return task.state
            elif index.column() == 2:
                return task.result
            elif index.column() == 3:
                return list(task.connected_modules.values())
        return None

    @QtCore.Slot()
    def _state_changed_callback(self) -> None:
        """ Is called upon sigStateChanged signal emit of any ModuleTask instance.
        """
        task = self.sender()
        row = self._storage.index(task)
        index = self.index(row, 1)
        self.dataChanged.emit(index, index)

    @QtCore.Slot()
    def _finished_callback(self) -> None:
        """ Is called upon sigFinished signal emit of any ModuleTask instance.
        """
        task = self.sender()
        row = self._storage.index(task)
        index = self.index(row, 2)
        self.dataChanged.emit(index, index)

    def insert(self, n: int, task: ModuleTask) -> None:
        """ Extend model insert
        """
        super().insert(n, task)
        task.sigStateChanged.connect(self._state_changed_callback)
        task.sigFinished.connect(self._finished_callback)

    def append(self, task: ModuleTask) -> None:
        super().append(task)
        task.sigStateChanged.connect(self._state_changed_callback)
        task.sigFinished.connect(self._finished_callback)

    def pop(self, n: int) -> ModuleTask:
        task = super().pop(n)
        task.sigStateChanged.disconnect(self._state_changed_callback)
        task.sigFinished.disconnect(self._finished_callback)
        return task

    def extend(self, seq: Sequence[ModuleTask]) -> None:
        old_len = len(self)
        super().extend(seq)
        for task in self[old_len:]:
            task.sigStateChanged.connect(self._state_changed_callback)
            task.sigFinished.connect(self._finished_callback)

    def __delitem__(self, key):
        self[key].sigStateChanged.disconnect(self._state_changed_callback)
        self[key].sigFinished.disconnect(self._finished_callback)
        super().__delitem__(key)

    def __setitem__(self, key, value):
        self[key].sigStateChanged.disconnect(self._state_changed_callback)
        self[key].sigFinished.disconnect(self._finished_callback)
        super().__setitem__(key, value)
        value.sigStateChanged.connect(self._state_changed_callback)
        value.sigFinished.connect(self._finished_callback)


class TaskRunner(LogicBase):
    """ This module keeps a collection of available ModuleTask subclasses (defined by config) and
    respective initialized instances that can be run.
    Handles module connections to tasks and allows monitoring of task states and results.
    """

    _module_task_configs = ConfigOption(name='module_tasks', default=dict(), missing='warn')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_class_model = None
        self.task_instance_model = None
        self._task_cfg_names = dict()

    def on_activate(self):
        """ Initialise task runner.
        """
        self.task_class_model = ModuleScriptsDictTableModel(self._module_task_configs)
        self.task_instance_model = TaskInstanceListTableModel()
        self._task_cfg_names = dict()

    def on_deactivate(self):
        """ Shut down task runner.
        """
        self.task_class_model = None
        self.task_instance_model = None

    def initialize_task(self, name: str) -> None:
        task = self.task_class_model[name]()
        thread = self._qudi_main.thread_manager.get_new_thread(name=f'ModuleTask {task.id}')
        task.moveToThread(thread)
        self.task_instance_model.append(task)
        self._task_cfg_names[task.id] = name
        thread.start()
        task.sigFinished.connect(self._task_finished_callback, QtCore.Qt.QueuedConnection)

    def remove_task(self, index: int) -> None:
        task = self.task_instance_model[index]
        if task.running:
            raise RuntimeError(f'Unable to remove task "{task.id}". It is still running.')
        del self.task_instance_model[index]
        del self._task_cfg_names[task.id]
        thread_name = f'ModuleTask {task.id}'
        thread_manager = self._qudi_main.thread_manager
        thread_manager.quit_thread(thread_name)
        thread_manager.join_thread(thread_name)
        task.sigFinished.disconnect(self._task_finished_callback)

    @QtCore.Slot(int, object, object)
    def set_task_arguments(self, index: int, args: Optional[Iterable[Any]] = None,
                           kwargs: Optional[Mapping[str, Any]] = None) -> None:
        """ Try setting the arguments for a task identified by its list index.
        """
        task = self.task_instance_model[index]
        if task.running:
            raise RuntimeError(f'Unable to set arguments for task "{task.id}" while it is running.')
        if args is not None:
            task.args = args
        if kwargs is not None:
            task.kwargs = kwargs

    @QtCore.Slot(int)
    def start_task(self, index: int) -> None:
        """ Try starting a task identified by its list index.
        """
        task = self.task_instance_model[index]
        if task.running:
            raise RuntimeError(f'Unable to start task "{task.id}". It is still running.')
        cfg_name = self._task_cfg_names[task.id]
        self._connect_activate_task_modules(task, self._module_task_configs[cfg_name]['connect'])
        QtCore.QMetaObject.invokeMethod(task, 'run', QtCore.Qt.QueuedConnection)

    @QtCore.Slot(int)
    def interrupt_task(self, index: int) -> None:
        """ Try interrupting a task identified by its list index.
        """
        self.task_instance_model[index].interrupt()

    def _connect_activate_task_modules(self, task: ModuleTask, config: Mapping[str, str]) -> None:
        """ Connect a ModuleTask to configured modules and activates them as well.
        """
        module_manager = self._qudi_main.module_manager
        module_connections = dict()
        for conn_name, module_name in config.items():
            module = module_manager[module_name]
            module.activate()
            module_connections[conn_name] = module.instance
        task.connect_modules(module_connections)

    @QtCore.Slot(object, bool, str)
    def _task_finished_callback(self, result: Any, success: bool, task_id: str) -> None:
        """ Called every time a task finishes.
        """
        task = self.sender()
        task.disconnect_modules()
