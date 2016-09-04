# -*- coding: utf-8 -*-
"""
This file contains the QuDi task runner module.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


from qtpy import QtCore
import importlib

from core.util.models import ListTableModel
from logic.generic_logic import GenericLogic
import logic.generic_task as gt


class TaskListTableModel(ListTableModel):
    """ An extension of the ListTableModel for keeping a task list in a TaskRunner.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headers = ['Task Name', 'Task State', 'Pre/Post actions', 'Pauses',
                        'Needs modules', 'is ok']

    def data(self, index, role):
        """ Get data from model for a given cell. Data can have a role that
        affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return QVariant: data for given cell and role
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
        """ Add a task to the end of the storage list and listen to its signals.

        @param object data: PrePostTask or InterruptableTask to add to list.
        """
        with self.lock:
            n = len(self.storage)
            self.beginInsertRows(QtCore.QModelIndex(), n, n)
            self.storage.append(data)
            self.endInsertRows()
            self.storage[-1]['object'].sigStateChanged.connect(
                lambda x:
                    self.dataChanged.emit(
                        self.index(n, 1),
                        self.index(n, 1)
                        )
                )

class TaskRunner(GenericLogic):
    """ This module keeps a collection of tasks that have varying preconditions,
        postconditions and conflicts and executes these tasks as their given
        conditions allow.
    """
    _modclass = 'TaskRunner'
    _modtype = 'Logic'
    _out = {'runner': 'TaskRunner'}

    sigLoadTasks = QtCore.Signal()
    sigCheckTasks = QtCore.Signal()

    def on_activate(self, e):
        """ Initialise task runner.

        @param object e: Fysom state change notification
        """
        self.model = TaskListTableModel()
        self.model.rowsInserted.connect(self.modelChanged)
        self.model.rowsRemoved.connect(self.modelChanged)
        self.sigLoadTasks.connect(self.loadTasks)
        self.sigCheckTasks.connect(self.checkTasksInModel)
        self._manager.registerTaskRunner(self)
        self.sigLoadTasks.emit()

    def on_deactivate(self, e):
        """ Shut down task runner.

        @param object e: Fysom state change notification
        """
        self._manager.registerTaskRunner(None)

    def loadTasks(self):
        """ Load all tasks specified in the configuration.
            Check dependencies and load necessary modules.
        """
        config = self.getConfiguration()
        if not 'tasks' in config:
            return
        for task in config['tasks']:
            t = {}
            t['ok'] = False
            t['object'] = None
            t['name'] = task
            # print('tsk:', task)
            if not 'module' in config['tasks'][task]:
                self.log.error('No module given for task {}'.format(task))
                continue
            else:
                t['module'] = config['tasks'][task]['module']
                # print('mod:', config['tasks'][task]['module'])

            if 'preposttasks' in config['tasks'][task]:
                t['preposttasks'] = config['tasks'][task]['preposttasks']
            else:
                t['preposttasks'] = []

            if 'pausetasks' in config['tasks'][task]:
                t['pausetasks'] = config['tasks'][task]['pausetasks']
            else:
                t['pausetasks'] = []

            if 'needsmodules' in config['tasks'][task]:
                t['needsmodules'] = config['tasks'][task]['needsmodules']
            else:
                t['needsmodules'] = {}

            if 'config' in config['tasks'][task]:
                t['config'] = config['tasks'][task]['config']
            else:
                t['config'] = {}

            try:
                ref = dict()
                for moddef, mod in t['needsmodules'].items():
                    if mod in self._manager.tree['defined']['logic'] and not mod in self._manager.tree['loaded']['logic']:
                        success = self._manager.startModule('logic', mod)
                        if success < 0:
                            raise Exception('Loading module {} failed.'.format(mod))
                    ref[moddef] = self._manager.tree['loaded']['logic'][mod]
                # print('Attempting to import: logic.tasks.{}'.format(t['module']))
                mod = importlib.__import__('logic.tasks.{}'.format(t['module']), fromlist=['*'])
                # print('loaded:', mod)
                # print('dir:', dir(mod))
                t['object'] = mod.Task(name=t['name'], runner=self,
                        references=ref, config=t['config'])
                if isinstance(t['object'], gt.InterruptableTask) or isinstance(t['object'], gt.PrePostTask):
                    self.model.append(t)
                else:
                    self.log.error('Not a subclass of allowd task classes {}'
                            ''.format(task))
            except:
                self.log.exception('Error while importing module for '
                        'task {}'.format(t['name']))
        self.sigCheckTasks.emit()

    def registerTask(self, task):
        """ Add a task from an external source (i.e. not loaded by task runner) to task runner.

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
            if not 'preposttasks' in task:
                task['preposttasks'] = []
            if not 'pausetasks' in task:
                task['pausetasks'] = []
            task['module'] = None
            task['needsmodules'] = {}
            task['config'] = {}
        except:
            self.log.error('Cannot register task, not a writeable dict.')
            return False

        checklist = ('ok', 'object', 'name')
        for entry in checklist:
            if not entry in task:
                return False
        if (
            isinstance(t['object'], gt.InterruptableTask) or isinstance(t['object'], gt.PrePostTask)
            ):
            self.model.append(t)
        else:
            self.log.error('Not a subclass of allowd task classes {}'.format(
                task))
            return False
        return True

    def checkTasksInModel(self):
        """ Check all loaded tasks for consistency and completeness of dependencies.
        """
        for task in self.model.storage:
            ppok = False
            pok = True
            modok = False

            # check if we require pre/post actions
            if len(task['preposttasks']) == 0:
                ppok = True

            # check if all required pre/post action tasks tasks are present
            for t in self.model.storage:
                if t['name'] in task['preposttasks']:
                    ppok =True

            #check if all required pause tasks are present
            #if len(task['pausetasks']) == 0:
            #    pok = True
            #for ptask in task['pausetasks']:
            #    for t in self.model.storage:
            #        if t['name'] == ptask:
            #            pok = True

            # check if all required moduls are present
            if len(task['needsmodules']) == 0:
                modok = True
            for moddef, mod in task['needsmodules'].items():
                if mod in self._manager.tree['defined']['logic'] and not mod in self._manager.tree['loaded']['logic']:
                    self._manager.startModule('logic', mod)
                if mod in self._manager.tree['loaded']['logic'] and not self._manager.tree['loaded']['logic'][mod].isstate('deactivated'):
                    modok = True
            # print(task['name'], ppok, pok, modok)
            task['ok'] = ppok and pok and modok

    @QtCore.Slot(QtCore.QModelIndex, int, int)
    def modelChanged(self, parent, first, last):
        """ React to model changes (right now debug only) """
        # print('Inserted into task list: {} {}'.format(first, last))
        pass

    def startTaskByIndex(self, index):
        """ Try starting a task identified by its list index.

        @param int index: index of task in task list
        """
        task = self.model.storage[index.row()]
        self.startTask(task)

    def startTaskByName(self, taskname):
        """ Try starting a task identified by its configured name.

        @param str name: name assigned to task
        """
        task = self.getTaskByName(taskname)
        self.startTask(task)

    def startTask(self, task):
        """ Try starting a task identified by its task dictionary

        @param dict task: dictionary that contains all information about task
        """
        # print('runner', QtCore.QThread.currentThreadId())
        if not task['ok']:
            self.log.error('Task {} did not pass all checks for required '
                    'tasks and modules and cannot be run'.format(
                        task['name']))
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
            self.log.error('Task cannot be run: {}'.format(task.name))

    def pauseTaskByIndex(self, index):
        """ Try pausing a task identified by its list index.

        @param int index: index of task in task list
        """
        task = self.model.storage[index.row()]
        self.pauseTask(task)

    def pauseTaskByName(self, taskname):
        """ Try pausing a task identified by its configured name.

        @param str name: name assigned to task
        """
        task = self.getTaskByName(taskname)
        self.pauseTask(task)

    def pauseTask(self, task):
        """ Actually Pause the Task.

        @param obj task: Reference to the task object
        """
        # print('runner', QtCore.QThread.currentThreadId())
        if task['object'].can('pause'):
            task['object'].pause()
        else:
            self.log.error('Task cannot be paused:  {}'.format(task['name']))

    def stopTaskByIndex(self, index):
        """ Try stopping a task identified by its list index.

        @param int index: index of task in task list
        """
        task = self.model.storage[index.row()]
        self.stopTask(task)

    def stopTaskByName(self, taskname):
        """ Try stopping a task identified by its configured name.

        @param str name: name assigned to task
        """
        task = self.getTaskByName(taskname)
        self.stopTask(task)

    def stopTask(self, task):
        # print('runner', QtCore.QThread.currentThreadId())
        if task['object'].can('finish'):
            task['object'].finish()
        else:
            self.log.error('Task cannot be stopped: {}'.format(task['name']))

    def getTaskByName(self, taskname):
        """ Get task dictionary for a given task name.

        @param str name: name of the task

        @return dict: task dictionary
        """
        for task in self.model.storage:
            if task['name'] == taskname:
                return task
        raise KeyError(taskname)

    def getTaskByReference(self, ref):
        """ Get task dictionary by the identity of its task object.
        @param str ref: task object

        @return dict: task dictionary
        """
        for task in self.model.storage:
            if task['object'] is ref:
                return task
        raise KeyError(ref)

    def getModule(self, taskname, modname):
        """ Get a reference to a module that is in a task's requied module list.

        @param str taskname: name of task
        @param str modname: name of module

        @return object: module
        """
        task = self.getTaskByName(taskname)
        if modname in task['needsmodules']:
            return self._manager.tree['loaded']['logic'][modname]
        else:
            raise KeyError(modname)

    def resumePauseTasks(self, ref):
        """ Try resuming all tasks paused by the given task.

        @param task ref: task object for which tasks should be resumed

        @return bool: Whether resuming was sucessful
        """
        return self._resumePauseTasks(self.getTaskByReference(ref))

    def _resumePauseTasks(self, task):
        """ Try resuming all tasks paused by the given task.

        @param dict task: dict for task that should be resumed

        @return bool: whether resuming was successful
        """
        for ptask in task['pausetasks']:
            # print(ptask)
            try:
                for t in self.model.storage:
                    if t['name'] == ptask:
                        if t['object'].can('resume'):
                            t['object'].resume()
                        elif t['object'].isstate('stopped'):
                            pass
                        else:
                            self.log.error('Pausetask {} failed while '
                                    'resuming after stop: {}'.format(
                                        ptask, task['name']))
                            return False
            except:
                self.log.exception('This pausetask {} failed while '
                        'preparing: {}'.format(ptask, task['name']))
                return False
        return True

    def postRunPPTasks(self, ref):
        """ Try executing post action for preposttasks associated with a given task.

        @param task ref: task object

        @return bool: whether post actions were successful
        """
        return self._postRunPPTasks(self.getTaskByReference(ref))

    def _postRunPPTasks(self, task):
        """ Try executing post action for preposttasks associated with a given task.

        @param dict task: task dictionary

        @return bool: whether post actions were successful
        """
        for pptask in task['preposttasks']:
            # print(pptask)
            try:
                for t in self.model.storage:
                    if t['name'] == pptask:
                        if t['object'].can('postrun'):
                            t['object'].postrun()
                        else:
                            self.log.error('Preposttask {} failed while '
                                    'postrunning in: {}'.format(
                                        pptask, task['name']))
                            return False
            except:
                self.log.exception('This preposttask {} failed while '
                        'postrunning in: {}'.format(pptask, task['name']))
                return False
        return True

    def preRunPPTasks(self, ref):
        """ Try running pre action of preposttask associated with given task.

        @param task ref: task object

        @return bool: whether pre tasks were successful
        """
        return self._preRunPPTasks(self.getTaskByReference(ref))

    def _preRunPPTasks(self, task):
        """ Try running pre action of preposttask associated with given task.

        @param dict task: task dictionary

        @return bool: whether pre tasks were successful
        """
        for pptask in task['preposttasks']:
            #print(pptask)
            try:
                for t in self.model.storage:
                    if t['name'] == pptask:
                        if t['object'].can('prerun'):
                            t['object'].prerun()
                        elif  t['object'].isstate('paused'):
                            pass
                        else:
                            self.log.error('Preposttask {} failed while '
                                    'preparing: {}'.format(
                                        pptask, task['name']))
                            return False
            except:
                self.log.exception('This preposttask {} failed while '
                        'preparing: {}'.format(pptask, task['name']))
                return False

    def pausePauseTasks(self, ref):
        """ Try pausing tasks required for starting a given task.

        @param task ref: task object

        @return bool: whether pausing tasks was successful
        """
        return self._pausePauseTasks(self.getTaskByReference(ref))

    def _pausePauseTasks(self, task):
        """ Try pausing tasks required for starting a given task.

        @param dict task: task dictionary

        @return bool: whether pausing tasks was successful
        """
        for ptask in task['pausetasks']:
            #print(ptask)
            try:
                for t in self.model.storage:
                    if t['name'] == ptask:
                        if t['object'].can('pause'):
                            t['object'].pause()
                        elif t['object'].isstate('stopped') or t['object'].isstate('paused'):
                            pass
                        else:
                            self.log.error('Pausetask {} failed while '
                                    'preparing: {}'.format(
                                        ptask, task['name']))
                            return False
            except:
                self.log.exception('This pausetask {} failed while '
                        'preparing: {}'.format(ptask, task['name']))
                return False
        return True

