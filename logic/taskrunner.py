# -*- coding: utf-8 -*-
"""
This file contains the QuDi task runner.

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

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from pyqtgraph.Qt import QtCore
from core.util.models import ListTableModel
import logic.generic_task as gt
import importlib

class TaskListTableModel(ListTableModel):

    def __init__(self):
        super().__init__()
        self.headers = ['Task Name', 'Task State', 'Pre/Post actions', 'Pauses', 'Needs modules', 'is ok']

    def data(self, index, role):
        """ Get data from model for a given cell. Data can have a role that affects display.

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
               return str(self.storage[index.row()]['needsmodules'])
            elif index.column() == 5:
               return self.storage[index.row()]['ok']
            else:
                return None
        else:
            return None

    def append(self, data):
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
    """A generic logic interface class.
    """
    _modclass = 'TaskRunner'
    _modtype = 'Logic'
    _out = {'runner': 'TaskRunner'}

    sigLoadTasks = QtCore.Signal()
    sigCheckTasks = QtCore.Signal()

    def __init__(self, manager, name, configuation, **kwargs):
        """ Initialzize a logic module.

          @param object manager: Manager object that has instantiated this object
          @param str name: unique module name
          @param dict configuration: module configuration as a ict
          @param dict kwargs: dict of additional arguments
        """
        callbacks = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, configuation, callbacks, **kwargs)

    def activation(self, e):
        self.model = TaskListTableModel()
        self.model.rowsInserted.connect(self.modelChanged)
        self.model.rowsRemoved.connect(self.modelChanged)
        self.sigLoadTasks.connect(self.loadTasks)
        self.sigCheckTasks.connect(self.checkTasksInModel)
        self._manager.registerTaskRunner(self)
        self.sigLoadTasks.emit()

    def deactivation(self, e):
        self._manager.registerTaskRunner(None)

    def loadTasks(self):
        config = self.getConfiguration()
        if not 'tasks' in config:
            return
        for task in config['tasks']:
            t = {}
            t['ok'] = False
            t['object'] = None
            t['name'] = task
            print('tsk:', task)
            if not 'module' in config['tasks'][task]:
                self.logMsg('No module given for task {}'.format(task), msgType='error')
                continue
            else:
                t['module'] = config['tasks'][task]['module']
                print('mod:', config['tasks'][task]['module'])
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
                        self._manager.startModule('logic', mod)
                    ref[moddef] = self._manager.tree['loaded']['logic'][mod]
                print('Attempting to import: logic.tasks.{}'.format(t['module']))
                mod = importlib.__import__('logic.tasks.{}'.format(t['module']), fromlist=['*'])
                print('loaded:', mod)
                print('dir:', dir(mod))
                t['object'] = mod.Task(t['name'], self, ref, t['config'])
                if isinstance(t['object'], gt.InterruptableTask) or isinstance(t['object'], gt.PrePostTask):
                    self.model.append(t)
                else:
                    self.logMsg('Not a subclass of allowd task classes {}'.format(task), msgType='error')
            except Exception as e:
                self.logExc('Error while importing module for task {}'.format(t['name']), msgType='error')
        self.sigCheckTasks.emit()

    def registerTask(self, task):
        """
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
            self.logMsg('Cannot registerTask, not a wirteable dict.')
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
            self.logMsg('Not a subclass of allowd task classes {}'.format(task), msgType='error')
            return False
        return True

    def checkTasksInModel(self):
        for task in self.model.storage:
            ppok = False
            pok = True
            modok = False

            #check if all required pre/post action tasks tasks are present
            if len(task['preposttasks']) == 0:
                ppok = True
            for pptask in task['preposttasks']:
                for t in self.model.storage:
                    if t['name'] == pptask:
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
            print(task['name'], ppok, pok, modok)
            task['ok'] = ppok and pok and modok

    @QtCore.pyqtSlot(QtCore.QModelIndex, int, int)
    def modelChanged(self, parent, first, last):
        print('Inserted into task list: {} {}'.format(first, last))

    def startTask(self, index):
        print('runner', QtCore.QThread.currentThreadId())
        task = self.model.storage[index.row()]
        if not task['ok']:
            self.logMsg('Task {} did not pass all its checks for required tasks and modules and cannot be run'.format(task['name']), msgType='error')
            return
        if task['object'].can('run'):
            for pptask in task['preposttasks']:
                print(pptask)
                try:
                    for t in self.model.storage:
                        if t['name'] == pptask:
                            if t['object'].can('prerun'):
                                t['object'].prerun()
                            elif  t['object'].isstate('paused'):
                                pass
                            else:
                                self.logMsg('This preposttask {} failed while preparing: {}'.format(pptask, task['name']), msgType='error')
                                return
                except:
                    self.logExc('This preposttask {} failed while preparing: {}'.format(pptask, task['name']), msgType='error')
                    return
            for ptask in task['pausetasks']:
                print(ptask)
                try:
                    for t in self.model.storage:
                        if t['name'] == ptask:
                            if t['object'].can('pause'):
                                t['object'].pause()
                            elif t['object'].isstate('stopped') or t['object'].isstate('paused'):
                                pass
                            else:
                                self.logMsg('This pausetask {} failed while preparing: {}'.format(ptask, task['name']), msgType='error')
                                return
                except:
                    self.logExc('This pausetask {} failed while preparing: {}'.format(ptask, task['name']), msgType='error')
                    return
            task['object'].run()

        elif task['object'].can('resume'):
            for pptask in task['preposttasks']:
                print(pptask)
                try:
                    for t in self.model.storage:
                        if t['name'] == pptask:
                            if t['object'].can('prerun'):
                                t['object'].prerun()
                            else:
                                self.logMsg('This preposttask {} failed while preparing resume in: {}'.format(pptask, task['name']), msgType='error')
                                return
                except:
                    self.logExc('This preposttask {} failed while preparing resume in: {}'.format(pptask, task['name']), msgType='error')
                    return
            task['object'].resume()
        elif task['object'].can('prerun'):
            task['object'].prerun()
        elif task['object'].can('postrun'):
            task['object'].postrun()
        else:
            self.logMsg('This thing cannot be run:  {}'.format(task.name), msgType='error')

    def pauseTask(self, index):
        print('runner', QtCore.QThread.currentThreadId())
        task = self.model.storage[index.row()]
        if task['object'].can('pause'):
            for pptask in task['preposttasks']:
                print(pptask)
                try:
                    for t in self.model.storage:
                        if t['name'] == pptask:
                            if t['object'].can('postrun'):
                                t['object'].postrun()
                            else:
                                self.logMsg('This preposttask {} failed while preparing pause in: {}'.format(pptask, task['name']), msgType='error')
                                return
                except:
                    self.logExc('This preposttask {} failed while preparingpause in: {}'.format(pptask, task['name']), msgType='error')
                    return
            task['object'].pause()
        else:
            self.logMsg('This thing cannot be paused:  {}'.format(task['name']), msgType='error')

    def stopTask(self, index):
        print('runner', QtCore.QThread.currentThreadId())
        task = self.model.storage[index.row()]
        if task['object'].can('finish'):
            for pptask in task['preposttasks']:
                print(pptask)
                try:
                    for t in self.model.storage:
                        if t['name'] == pptask:
                            if t['object'].can('postrun'):
                                t['object'].postrun()
                            else:
                                self.logMsg('This preposttask {} failed while preparing pause in: {}'.format(pptask, task['name']), msgType='error')
                                return
                except:
                    self.logExc('This preposttask {} failed while preparingpause in: {}'.format(pptask, task['name']), msgType='error')
                    return
            for ptask in task['pausetasks']:
                print(ptask)
                try:
                    for t in self.model.storage:
                        if t['name'] == ptask:
                            if t['object'].can('resume'):
                                t['object'].resume()
                            elif t['object'].isstate('stopped'):
                                pass
                            else:
                                self.logMsg('This pausetask {} failed while resuming after stop: {}'.format(ptask, task['name']), msgType='error')
                                return
                except:
                    self.logExc('This pausetask {} failed while preparing: {}'.format(ptask, task['name']), msgType='error')
                    return
            task['object'].finish()
        else:
            self.logMsg('This thing cannot be stopped:  {}'.format(task['name']), msgType='error')

    def getTaskByName(self, taskname):
        for task in self.model.storage:
            if task['name'] == taskname:
                return task
        raise KeyError(taskname)

    def getModule(self, taskname, modname):
        task = self.getTaskByName(taskname)
        if modname in task['needsmodules']:
            return self._manager.tree['loaded']['logic'][modname]
        else:
            raise KeyError(modname)

