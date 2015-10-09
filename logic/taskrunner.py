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
        self.headers = ['Task Name', 'Task State']

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
            else:
                return None
        else:
            return None

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
        self.sigLoadTasks.emit()

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
                t['modules'] = config['tasks'][task]['needsmodules']
            else:
                t['modules'] = {}
            try:
                print('Attempting to import: logic.tasks.{}'.format(t['module']))
                mod = importlib.__import__('logic.tasks.{}'.format(t['module']), fromlist=['*'])
                print('loaded:', mod)
                print('dir:', dir(mod))
                t['object'] = mod.Task(t['name'], self)
                if isinstance(t['object'], gt.InterruptableTask) or isinstance(t['object'], gt.PrePostTask):
                    self.model.append(t)
                else:
                    self.logMsg('Not a subclass of allowd task classes {}'.format(task), msgType='error')
            except Exception as e:
                self.logExc('Error while importing module for task {}'.format(t['name']), msgType='error')
        self.sigCheckTasks.emit()

    def checkTasksInModel(self):
        for task in self.model.storage:
            for pptask in task['preposttasks']:
                print(pptask)
            for ptask in task['pausetasks']:
                print(ptask)
            for mod in task['needsmodules']:
                print(mod)

    def deactivation(self, e):
        pass

    @QtCore.pyqtSlot(QtCore.QModelIndex, int, int)
    def modelChanged(self, parent, first, last):
        print('Inserted into task list: {} {}'.format(first, last))

    def runTask(self, index):
        print('runner', QtCore.QThread.currentThreadId())
        task = self.model.storage[index.row()]['object']
        if task.can('run'):
            task.run()
        elif task.can('resume'):
            task.resume()
        elif task.can('prerun'):
            task.prerun()
        elif task.can('postrun'):
            task.postrun()
        else:
            self.logMsg('This thing cannot be run:  {}'.format(task.name), msgType='error')

    def pauseTask(self, index):
        print('runner', QtCore.QThread.currentThreadId())
        task = self.model.storage[index.row()]['object']
        if task.can('pause'):
            task.pause()
        else:
            self.logMsg('This thing cannot be paused:  {}'.format(task.name), msgType='error')

    def stopTask(self, index):
        print('runner', QtCore.QThread.currentThreadId())
        task = self.model.storage[index.row()]['object']
        if task.can('finish'):
            task.finish()
        else:
            self.logMsg('This thing cannot be stopped:  {}'.format(task.name), msgType='error')

