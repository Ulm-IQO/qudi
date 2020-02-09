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


from qtpy import QtCore
import importlib

from core.util.models import ListTableModel
from core.module import LogicBase
import core.task as gt


class TaskListTableModel(ListTableModel):
    """ An extension of the ListTableModel for keeping a task list in a TaskRunner.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = ['Task Name',
                        'Task State',
                        'Pre/Post actions',
                        'Pauses',
                        'Needs modules',
                        'is ok']

    def data(self, index, role):
        """
        Get data from model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return object: data for given cell and role
        """
        if not index.isValid():
            return None
        elif role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return self.storage[index.row()]['name']
            elif index.column() == 1:
                return self.storage[index.row()]['object'].current
            elif index.column() == 2:
                return str(self.storage[index.row()]['preposttasks'])
            elif index.column() == 3:
                return str(self.storage[index.row()]['pausetasks'])
            elif index.column() == 4:
                return str(list(self.storage[index.row()]['needsmodules']))
            elif index.column() == 5:
                return self.storage[index.row()]['ok']
            else:
                return None
        else:
            return None

    def append(self, data):
        """
        Add a task to the end of the storage list and listen to its signals.

        @param object data: PrePostTask or InterruptableTask to add to list.
        """
        with self.lock:
            n = len(self.storage)
            self.beginInsertRows(QtCore.QModelIndex(), n, n)
            self.storage.append(data)
            self.endInsertRows()
            self.storage[-1]['object'].sigStateChanged.connect(
                lambda x: self.dataChanged.emit(self.index(n, 1), self.index(n, 1)))


class TaskRunner(LogicBase):
    """
    This module keeps a collection of tasks that have varying preconditions, postconditions and
    conflicts and executes these tasks as their given conditions allow.
    """

    sigLoadTasks = QtCore.Signal()
    sigCheckTasks = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None

    def on_activate(self):
        """ Initialise task runner.
        """
        self.model = TaskListTableModel()
        self.model.rowsInserted.connect(self.model_changed)
        self.model.rowsRemoved.connect(self.model_changed)
        self.sigLoadTasks.connect(self.load_tasks)
        self.sigCheckTasks.connect(self.check_tasks_in_model)
        self._manager.register_task_runner(self)
        self.sigLoadTasks.emit()

    def on_deactivate(self):
        """ Shut down task runner.
        """
        self._manager.register_task_runner(None)

    def load_tasks(self):
        """
        Load all tasks specified in the configuration.
        Check dependencies and load necessary modules.
        """
        if 'tasks' not in self._configuration:
            return
        if self._configuration['tasks'] is None:
            return
        for task in self._configuration['tasks']:
            t = {'ok': False, 'object': None, 'name': task}
            if 'module' not in self._configuration['tasks'][task]:
                self.log.error('No module given for task {0}'.format(task))
                continue
            else:
                t['module'] = self._configuration['tasks'][task]['module']

            if 'preposttasks' in self._configuration['tasks'][task]:
                t['preposttasks'] = self._configuration['tasks'][task]['preposttasks']
            else:
                t['preposttasks'] = list()

            if 'pausetasks' in self._configuration['tasks'][task]:
                t['pausetasks'] = self._configuration['tasks'][task]['pausetasks']
            else:
                t['pausetasks'] = list()

            if 'needsmodules' in self._configuration['tasks'][task]:
                t['needsmodules'] = self._configuration['tasks'][task]['needsmodules']
            else:
                t['needsmodules'] = dict()

            if 'config' in self._configuration['tasks'][task]:
                t['config'] = self._configuration['tasks'][task]['config']
            else:
                t['config'] = dict()

            try:
                ref = dict()
                for mod_def, mod in t['needsmodules'].items():
                    if self._manager.is_module_configured(mod) and not self._manager.is_module_active(mod):
                        if self._manager.start_module('logic', mod) < 0:
                            raise Exception('Loading module {0} failed.'.format(mod))
                    ref[mod_def] = self._manager.tree['loaded']['logic'][mod]
                mod = importlib.__import__('logic.tasks.{0}'.format(t['module']), fromlist=['*'])
                t['object'] = mod.Task(name=t['name'],
                                       runner=self,
                                       references=ref,
                                       config=t['config'])
                if isinstance(t['object'], gt.InterruptableTask) or isinstance(t['object'],
                                                                               gt.PrePostTask):
                    self.model.append(t)
                else:
                    self.log.error('Not a subclass of allowed task classes {}'.format(task))
            except:
                self.log.exception('Error while importing module for task {}'.format(t['name']))
        self.sigCheckTasks.emit()

    def register_task(self, task):
        """
        Add a task from an external source (i.e. not loaded by task runner) to task runner.

        @param dict task: dictionary describing a task to register

        @return bool: whether registering tasks succeeded

        task: dict
            bool ok: loading checks passed
            obj object: refernece to task object
            str name: unoque name of task
            str module: module name of task module
            [str] preposttasks: pre/post execution tasks for this task
            [str] pausetasks: this stuff needs to be paused before task can run
            dict needsmodules: task needs these modules
            dict config: extra configuration
        """
        try:
            if 'preposttasks' not in task:
                task['preposttasks'] = list()
            if 'pausetasks' not in task:
                task['pausetasks'] = list()
            task['module'] = None
            task['needsmodules'] = dict()
            task['config'] = dict()
        except:
            self.log.error('Cannot register task, not a writeable dict.')
            return False

        if not all(key in task for key in ('ok', 'object', 'name')):
            return False

        if isinstance(task['object'], gt.InterruptableTask) or isinstance(task['object'],
                                                                          gt.PrePostTask):
            self.model.append(task)
        else:
            self.log.error('Not a subclass of allowed task classes {0}'.format(task))
            return False
        return True

    def check_tasks_in_model(self):
        """ Check all loaded tasks for consistency and completeness of dependencies.
        """
        for task in self.model.storage:
            prepost_ok = False
            pause_ok = True
            modules_ok = False

            # check if we require pre/post actions
            if len(task['preposttasks']) == 0:
                prepost_ok = True
            else:
                # check if all required pre/post action tasks are present
                for t in self.model.storage:
                    if t['name'] in task['preposttasks']:
                        prepost_ok = True

            #check if all required pause tasks are present
            #if len(task['pausetasks']) == 0:
            #    pause_ok = True
            #for ptask in task['pausetasks']:
            #    for t in self.model.storage:
            #        if t['name'] == ptask:
            #            pause_ok = True

            # check if all required modules are present
            if len(task['needsmodules']) == 0:
                modules_ok = True
            else:
                for moddef, mod in task['needsmodules'].items():
                    if self._manager.is_module_configured(mod):
                        if self._manager.is_module_active(mod):
                            modules_ok = True
                        else:
                            self._manager.start_module(mod)

            task['ok'] = prepost_ok and pause_ok and modules_ok

    @QtCore.Slot(QtCore.QModelIndex, int, int)
    def model_changed(self, parent, first, last):
        """ React to model changes (right now debug only) """
        # print('Inserted into task list: {} {}'.format(first, last))
        pass

    @QtCore.Slot(object)
    def start_task_by_index(self, index):
        """
        Try starting a task identified by its list index.

        @param int index: index of task in task list
        """
        task = self.model.storage[index.row()]
        self.start_task(task)

    @QtCore.Slot(str)
    def start_task_by_name(self, task_name):
        """
        Try starting a task identified by its configured name.

        @param str task_name: name assigned to task
        """
        task = self.get_task_by_name(task_name)
        self.start_task(task)

    def start_task(self, task):
        """
        Try starting a task identified by its task dictionary

        @param dict task: dictionary that contains all information about task
        """
        if not task['ok']:
            self.log.error('Task {} did not pass all checks for required tasks and modules and '
                           'cannot be run'.format(task['name']))
            return
        if task['object'].can('run'):
            task['object'].run()
        elif task['object'].can('resume'):
            task['object'].resume()
        elif task['object'].can('prerun'):
            task['object'].prerun()
        elif task['object'].can('postrun'):
            task['object'].postrun()
        else:
            self.log.error('Task cannot be run: {0}'.format(task.name))

    @QtCore.Slot(object)
    def pause_task_by_index(self, index):
        """
        Try pausing a task identified by its list index.

        @param int index: index of task in task list
        """
        task = self.model.storage[index.row()]
        self.pause_task(task)

    @QtCore.Slot(str)
    def pause_task_by_name(self, task_name):
        """
        Try pausing a task identified by its configured name.

        @param str task_name: name assigned to task
        """
        task = self.get_task_by_name(task_name)
        self.pause_task(task)

    def pause_task(self, task):
        """
        Actually Pause the Task.

        @param obj task: Reference to the task object
        """
        if task['object'].can('pause'):
            task['object'].pause()
        else:
            self.log.error('Task cannot be paused:  {0}'.format(task['name']))

    @QtCore.Slot(object)
    def stop_task_by_index(self, index):
        """
        Try stopping a task identified by its list index.

        @param int index: index of task in task list
        """
        task = self.model.storage[index.row()]
        self.stop_task(task)

    @QtCore.Slot(str)
    def stop_task_by_name(self, task_name):
        """
        Try stopping a task identified by its configured name.

        @param str task_name: name assigned to task
        """
        task = self.get_task_by_name(task_name)
        self.stop_task(task)

    def stop_task(self, task):
        if task['object'].can('finish'):
            task['object'].finish()
        else:
            self.log.error('Task cannot be stopped: {0}'.format(task['name']))

    def get_task_by_name(self, task_name):
        """
        Get task dictionary for a given task name.

        @param str task_name: name of the task

        @return dict: task dictionary
        """
        for task in self.model.storage:
            if task['name'] == task_name:
                return task
        raise KeyError(task_name)

    def get_task_by_reference(self, ref):
        """
        Get task dictionary by the identity of its task object.

        @param object ref: task object

        @return dict: task dictionary
        """
        for task in self.model.storage:
            if task['object'] is ref:
                return task
        raise KeyError(ref)

    def get_module(self, task_name, modname):
        """
        Get a reference to a module that is in a task's required module list.

        @param str task_name: name of task
        @param str modname: name of module

        @return object: module
        """
        task = self.get_task_by_name(task_name)
        if modname in task['needsmodules']:
            return self._manager.tree['loaded']['logic'][modname]
        else:
            raise KeyError(modname)

    def resume_pause_tasks(self, ref):
        """
        Try resuming all tasks paused by the given task.

        @param task ref: task object for which tasks should be resumed

        @return bool: Whether resuming was successful
        """
        return self._resume_pause_tasks(self.get_task_by_reference(ref))

    def _resume_pause_tasks(self, task):
        """
        Try resuming all tasks paused by the given task.

        @param dict task: dict for task that should be resumed

        @return bool: whether resuming was successful
        """
        for pause_task in task['pausetasks']:
            try:
                for t in self.model.storage:
                    if t['name'] == pause_task:
                        if t['object'].can('resume'):
                            t['object'].resume()
                        elif t['object'].isstate('stopped'):
                            pass
                        else:
                            self.log.error('Pausetask {} failed while resuming after stop: {}'
                                           ''.format(pause_task, task['name']))
                            return False
            except:
                self.log.exception(
                    'This pausetask {} failed while preparing: {}'.format(pause_task, task['name']))
                return False
        return True

    def post_run_prepost_tasks(self, ref):
        """
        Try executing post action for prepost tasks associated with a given task.

        @param task ref: task object

        @return bool: whether post actions were successful
        """
        return self._post_run_prepost_tasks(self.get_task_by_reference(ref))

    def _post_run_prepost_tasks(self, task):
        """
        Try executing post action for prepost tasks associated with a given task.

        @param dict task: task dictionary

        @return bool: whether post actions were successful
        """
        for prepost_task in task['preposttasks']:
            try:
                for t in self.model.storage:
                    if t['name'] == prepost_task:
                        if t['object'].can('postrun'):
                            t['object'].postrun()
                        else:
                            self.log.error('Preposttask {} failed while postrunning in: {}'
                                           ''.format(prepost_task, task['name']))
                            return False
            except:
                self.log.exception('This preposttask {} failed while postrunning in: {}'
                                   ''.format(prepost_task, task['name']))
                return False
        return True

    def pre_run_prepost_tasks(self, ref):
        """
        Try running pre action of prepost task associated with given task.

        @param task ref: task object

        @return bool: whether pre tasks were successful
        """
        return self._pre_run_prepost_tasks(self.get_task_by_reference(ref))

    def _pre_run_prepost_tasks(self, task):
        """
        Try running pre action of prepost task associated with given task.

        @param dict task: task dictionary

        @return bool: whether pre tasks were successful
        """
        for prepost_task in task['preposttasks']:
            try:
                for t in self.model.storage:
                    if t['name'] == prepost_task:
                        if t['object'].can('prerun'):
                            t['object'].prerun()
                        elif t['object'].isstate('paused'):
                            pass
                        else:
                            self.log.error('Preposttask {} failed while preparing: {}'
                                           ''.format(prepost_task, task['name']))
                            return False
            except:
                self.log.exception('This preposttask {} failed while preparing: {}'
                                   ''.format(prepost_task, task['name']))
                return False

    def pause_pause_tasks(self, ref):
        """
        Try pausing tasks required for starting a given task.

        @param task ref: task object

        @return bool: whether pausing tasks was successful
        """
        return self._pause_pause_tasks(self.get_task_by_reference(ref))

    def _pause_pause_tasks(self, task):
        """
        Try pausing tasks required for starting a given task.

        @param dict task: task dictionary

        @return bool: whether pausing tasks was successful
        """
        for pause_task in task['pausetasks']:
            try:
                for t in self.model.storage:
                    if t['name'] == pause_task:
                        if t['object'].can('pause'):
                            t['object'].pause()
                        elif t['object'].isstate('stopped') or t['object'].isstate('paused'):
                            pass
                        else:
                            self.log.error('Pausetask {} failed while preparing: {}'
                                           ''.format(pause_task, task['name']))
                            return False
            except:
                self.log.exception('This pausetask {} failed while preparing: {}'
                                   ''.format(pause_task, task['name']))
                return False
        return True
