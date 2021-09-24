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

from functools import partial
from PySide2 import QtCore
from typing import Any, Type, Mapping, List, Dict

from qudi.util.mutex import Mutex
from qudi.core.module import LogicBase
from qudi.core.scripting.moduletask import ModuleTask
from qudi.core.scripting.modulescript import import_module_script
from qudi.core.configoption import ConfigOption


class TaskRunnerLogic(LogicBase):
    """ This module keeps a collection of available ModuleTask subclasses (defined by config) and
    respective initialized instances that can be run.
    Handles module connections to tasks and allows monitoring of task states and results.
    """

    _module_task_configs = ConfigOption(name='module_tasks', default=dict(), missing='warn')

    sigTaskStarted = QtCore.Signal(str)  # task name
    sigTaskStateChanged = QtCore.Signal(str, str)  # task name, task state
    sigTaskFinished = QtCore.Signal(str, object, bool)  # task name, result, success flag
    _sigStartTask = QtCore.Signal(str, dict)  # task name, args, kwargs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = Mutex()
        self._running_tasks = dict()
        self._configured_task_types = dict()
        self._consecutive_activation = False  # Flag indicating consecutive activations

    def on_activate(self) -> None:
        """ Initialise task runner """
        self._running_tasks = dict()
        self._configured_task_types = dict()
        for name, task_cfg in self._module_task_configs.items():
            if name in self._configured_task_types:
                raise KeyError(f'Duplicate task name "{name}" encountered in config')
            module, cls = task_cfg['module.Class'].rsplit('.', 1)
            task = import_module_script(module, cls, reload=self._consecutive_activation)
            if not issubclass(task, ModuleTask):
                raise TypeError('Configured task is not a ModuleTask (sub)class')
            self._configured_task_types[name] = task
        self._sigStartTask.connect(self._run_task, QtCore.Qt.QueuedConnection)
        self._consecutive_activation = True

    def on_deactivate(self) -> None:
        """ Shut down task runner """
        self._sigStartTask.disconnect()
        for task in self._running_tasks.values():
            task.interrupt
        self._configured_task_types = dict()

    @property
    def running_tasks(self) -> List[str]:
        with self._thread_lock:
            return list(self._running_tasks)

    @property
    def task_states(self) -> Dict[str, str]:
        with self._thread_lock:
            states = dict()
            for task_name in self._configured_task_types:
                try:
                    states[task_name] = self._running_tasks[task_name].state
                except KeyError:
                    states[task_name] = 'stopped'
            return states

    @property
    def configured_task_types(self) -> Dict[str, Type[ModuleTask]]:
        return self._configured_task_types.copy()

    def run_task(self, name: str, arguments: Mapping[str, Any]) -> None:
        with self._thread_lock:
            self._sigStartTask.emit(name, dict(arguments))

    def interrupt_task(self, name: str) -> None:
        with self._thread_lock:
            task = self._running_tasks.get(name, None)
            if task is None:
                raise RuntimeError(f'No ModuleTask with name "{name}" running')
            task.interrupt()

    @QtCore.Slot(str, dict)
    def _run_task(self, name: str, arguments: Mapping[str, Any]) -> None:
        with self._thread_lock:
            task = self.__init_task(name)
            self.__set_task_arguments(task, arguments)
            self.__activate_connect_task_modules(name, task)
            self.__move_task_into_thread(name, task)
            self.__connect_task_signals(name, task)
            self.__start_task(name, task)
            self.sigTaskStarted.emit(name)

    def _task_finished_callback(self, name: str) -> None:
        """ Called every time a task finishes """
        with self._thread_lock:
            task = self._running_tasks.get(name, None)
            if task is not None:
                task.sigFinished.disconnect()
                task.sigStateChanged.disconnect()
                task.disconnect_modules()
                thread_manager = self._qudi_main.thread_manager
                thread_manager.quit_thread(task.thread())
                thread_manager.join_thread(task.thread())

    def _thread_finished_callback(self, name: str) -> None:
        with self._thread_lock:
            task = self._running_tasks.pop(name, None)
            if task is not None:
                self.sigTaskFinished.emit(name, task.result, task.success)

    def _task_state_changed_callback(self, state: str, name: str) -> None:
        self.sigTaskStateChanged.emit(name, state)

    def __init_task(self, name: str) -> ModuleTask:
        """ Create a ModuleTask instance """
        try:
            if name in self._running_tasks:
                raise RuntimeError(f'ModuleTask "{name}" is already initialized')
            return self._configured_task_types[name]()
        except:
            self.log.exception(f'Exception during initialization of ModuleTask "{name}":')
            raise

    def __set_task_arguments(self, task: ModuleTask, arguments: Mapping[str, Any]) -> None:
        """ Set arguments for ModuleTask instance """
        try:
            if not (isinstance(arguments, Mapping) and all(isinstance(a, str) for a in arguments)):
                raise TypeError('ModuleTask kwargs must be mapping with str type keys')
            task.kwargs = arguments
        except:
            self.log.exception(f'Exception during setting of arguments for ModuleTask:')
            raise

    def __activate_connect_task_modules(self, name: str, task: ModuleTask) -> None:
        """ Activate and connect all configured module connectors for ModuleTask """
        try:
            module_manager = self._qudi_main.module_manager
            connect_targets = dict()
            for conn_name, module_name in self._module_task_configs[name]['connect'].items():
                module = module_manager[module_name]
                module.activate()
                connect_targets[conn_name] = module.instance
            task.connect_modules(connect_targets)
        except:
            self.log.exception(f'Exception during modules connection for ModuleTask "{name}":')
            task.disconnect_modules()
            raise

    def __move_task_into_thread(self, name: str, task: ModuleTask) -> None:
        """ Create a new QThread via qudi thread manager and move ModuleTask instance into it """
        try:
            thread = self._qudi_main.thread_manager.get_new_thread(name=f'ModuleTask-{name}')
            if thread is None:
                raise RuntimeError(f'Unable to create QThread with name "ModuleTask-{name}"')
        except RuntimeError:
            self.log.exception('Exception during thread creation:')
            raise
        task.moveToThread(thread)
        thread.started.connect(task.run, QtCore.Qt.QueuedConnection)
        thread.finished.connect(partial(self._thread_finished_callback, name=name))

    def __connect_task_signals(self, name: str, task: ModuleTask) -> None:
        task.sigFinished.connect(partial(self._task_finished_callback, name=name),
                                 QtCore.Qt.QueuedConnection)
        task.sigStateChanged.connect(partial(self._task_state_changed_callback, name=name),
                                     QtCore.Qt.QueuedConnection)

    def __start_task(self, name: str, task: ModuleTask) -> None:
        self._running_tasks[name] = task
        task.thread().start()
