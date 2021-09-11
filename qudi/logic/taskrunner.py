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
from uuid import uuid4
from PySide2 import QtCore, QtWidgets
from typing import Any, Optional, Sequence, Iterable, Mapping, Tuple, Union

from qudi.util.mutex import Mutex
from qudi.core.module import LogicBase
from qudi.core.scripting.moduletask import ModuleTask
from qudi.core.scripting.modulescript import import_module_script
from qudi.core.configoption import ConfigOption


class ModuleTasksTableModel(QtCore.QAbstractTableModel):
    """ An extension of the ListTableModel for keeping ModuleTask instances """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._headers = ('Task Name', 'Current State', 'Result', 'Involved Modules')
        self._names = list()
        self._tasks = list()

    def rowCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        """ Gives the number of stored items (rows) """
        return len(self._names)

    def columnCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        """ Gives the number of data fields (columns) """
        return 4

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        """ Determines what can be done with entry cells in the table view """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index: QtCore.QModelIndex,
             role: QtCore.Qt.ItemDataRole) -> Union[str, None]:
        """ Get data from model for a given cell. Data can have a role that affects display. """
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            name, task = self._task_from_index(index.row())
            if index.column() == 0:
                return name
            elif index.column() == 1:
                return task.state
            elif index.column() == 2:
                return str(task.result)
            elif index.column() == 3:
                return '\n'.join(task.connected_modules.values())
        return None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation,
                   role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole) -> Union[str, None]:
        """ Data for the table view headers """
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._headers[section]
        return None

    def add_task(self, name: str, task: ModuleTask) -> None:
        if name in self._names:
            raise KeyError(f'ModuleTask with name "{name}" already added.')
        row = self.rowCount()
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self._names.append(name)
        self._tasks.append(task)
        task.sigStateChanged.connect(self._state_changed_callback)
        task.sigFinished.connect(self._finished_callback)
        self.endInsertRows()

    def remove_task(self, name: str) -> None:
        row = self._names.index(name)
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        del self._names[row]
        task = self._tasks.pop(row)
        task.sigStateChanged.disconnect()
        task.sigFinished.disconnect()
        self.endRemoveRows()

    def clear_tasks(self) -> None:
        self.beginResetModel()
        for task in self._tasks:
            task.sigStateChanged.disconnect()
            task.sigFinished.disconnect()
        self._names = list()
        self._tasks = list()
        self.endResetModel()

    def task_from_index(self, index: int) -> Tuple[str, ModuleTask]:
        """ """
        return self._names[index], self._tasks[index]

    def index_from_name(self, name: str) -> int:
        """ """
        return self._names.index(name)

    @QtCore.Slot()
    def _state_changed_callback(self) -> None:
        """ Is called upon sigStateChanged signal emit of any ModuleTask instance.
        """
        task = self.sender()
        row = self._tasks.index(task)
        index = self.index(row, 1)
        self.dataChanged.emit(index, index)

    @QtCore.Slot()
    def _finished_callback(self) -> None:
        """ Is called upon sigFinished signal emit of any ModuleTask instance.
        """
        task = self.sender()
        row = self._tasks.index(task)
        index = self.index(row, 2)
        self.dataChanged.emit(index, index)


class TaskRunner(LogicBase):
    """ This module keeps a collection of available ModuleTask subclasses (defined by config) and
    respective initialized instances that can be run.
    Handles module connections to tasks and allows monitoring of task states and results.
    """

    _module_task_configs = ConfigOption(name='module_tasks', default=dict(), missing='warn')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_instances_model = None
        self.configured_task_types = None

    def on_activate(self) -> None:
        """ Initialise task runner """
        self.task_instances_model = ModuleTasksTableModel(parent=self)
        self.configured_task_types = dict()
        for name, task_cfg in self._module_task_configs.items():
            if name in self.configured_task_types:
                raise KeyError(f'Duplicate task name "{name}" encountered in config')
            module, cls = task_cfg['module.Class'].rsplit('.', 1)
            task = import_module_script(module, cls, reload=False)
            if not isinstance(task, ModuleTask):
                raise TypeError('Configured task is not a ModuleTask (sub)class')
            self.configured_task_types[name] = task

    def on_deactivate(self) -> None:
        """ Shut down task runner """
        try:
            self.task_instances_model.clear_tasks()
        finally:
            self.task_instances_model = None
            self.configured_task_types = None

    def _initialize_task(self, name: str):
        task = self.configured_task_types[name]


    @QtCore.Slot()
    def test(self):
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(self, 'test', QtCore.Qt.BlockingQueuedConnection)
            return
        self.start_task_by_index(0)
        self.set_task_arguments()

    @QtCore.Slot(int)
    def start_task_by_index(self, index: int) -> None:
        """ Try starting a task identified by its list index """
        name, task = self.tasks_model.task_from_index(index)
        if task.running:
            raise RuntimeError(f'Unable to start task "{name}". It is still running.')
        self._start_task_thread(name, task)
        self._connect_activate_task_modules(name, task)
        task.sigFinished.connect(self._task_finished_callback, QtCore.Qt.QueuedConnection)
        QtCore.QMetaObject.invokeMethod(task, 'run', QtCore.Qt.QueuedConnection)

    @QtCore.Slot(str)
    def start_task_by_name(self, name: str) -> None:
        """ Try starting a task identified by its name """
        index = self.tasks_model.index_from_name(name)
        return self.start_task_by_index(index)

    def start_task(self, task_id: Union[str, int]) -> None:
        """ Convenience method for starting a task either by name or by index """
        if isinstance(task_id, str):
            return self.start_task_by_name(task_id)
        else:
            return self.start_task_by_index(task_id)

    @QtCore.Slot(int)
    def interrupt_task_by_index(self, index: int) -> None:
        """ Try interrupting a task identified by its list index.
        """
        name, task = self.tasks_model.task_from_index(index)
        task.interrupt()

    @QtCore.Slot(str)
    def interrupt_task_by_name(self, name: str) -> None:
        """ Try interrupting a task identified by its name """
        index = self.tasks_model.index_from_name(name)
        return self.interrupt_task_by_index(index)

    def interrupt_task(self, task_id: Union[str, int]) -> None:
        """ Convenience method for interrupting a task either by name or by index """
        if isinstance(task_id, str):
            return self.interrupt_task_by_name(task_id)
        else:
            return self.interrupt_task_by_index(task_id)

    @QtCore.Slot(int, object, object)
    def set_task_arguments_by_index(self, index: int, args: Optional[Iterable[Any]] = None,
                                    kwargs: Optional[Mapping[str, Any]] = None) -> None:
        """ Try setting the arguments for a task identified by its list index """
        name, task = self.tasks_model.task_from_index(index)
        if task.running:
            raise RuntimeError(f'Unable to set arguments for task "{name}" while it is running.')
        if args is not None:
            task.args = args
        if kwargs is not None:
            task.kwargs = kwargs

    @QtCore.Slot(str, object, object)
    def set_task_arguments_by_name(self, name: str, args: Optional[Iterable[Any]] = None,
                                   kwargs: Optional[Mapping[str, Any]] = None) -> None:
        """ Try setting the arguments for a task identified by its name """
        index = self.tasks_model.index_from_name(name)
        return self.set_task_arguments_by_index(index)

    def set_task_arguments(self, task_id: Union[str, int], args: Optional[Iterable[Any]] = None,
                           kwargs: Optional[Mapping[str, Any]] = None) -> None:
        """ Convenience method for setting the task arguments either by name or by index """
        if isinstance(task_id, str):
            return self.set_task_arguments_by_name(task_id)
        else:
            return self.set_task_arguments_by_index(task_id)

    def _connect_activate_task_modules(self, name: str, task: ModuleTask) -> None:
        """  """
        module_manager = self._qudi_main.module_manager
        connect_targets = dict()
        for conn_name, module_name in self._module_task_configs[name]['connect'].items():
            module = module_manager[module_name]
            module.activate()
            connect_targets[conn_name] = module.instance
        task.connect_modules(connect_targets)

    def _start_task_thread(self, name: str, task: ModuleTask) -> None:
        """  """
        thread = self._qudi_main.thread_manager.get_new_thread(name=f'ModuleTask-{name}')
        task.moveToThread(thread)
        thread.start()

    def _stop_task_thread(self, task: ModuleTask) -> None:
        thread_manager = self._qudi_main.thread_manager
        thread_manager.quit_thread(task.thread())
        thread_manager.join_thread(task.thread())
        task.moveToThread(self.thread())

    @QtCore.Slot(object, bool)
    def _task_finished_callback(self, result: Any, success: bool) -> None:
        """ Called every time a task finishes.
        """
        task = self.sender()
        task.sigFinished.disconnect(self._task_finished_callback)
        task.disconnect_modules()
        self._stop_task_thread(task)
