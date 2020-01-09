# -*- coding: utf-8 -*-

"""
This file contains the Qudi task base classes.

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
import abc
import sys
import logging
from qtpy import QtCore

from core.meta import TaskMetaclass
from core.util.mutex import Mutex
from fysom import Fysom


class TaskResult(QtCore.QObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = None
        self.success = None

    def update(self, data, success=None):
        self.data = data
        self.success = success

class InterruptableTask(QtCore.QObject, Fysom, metaclass=TaskMetaclass):
    """ This class represents a task in a module that can be safely executed by checking preconditions
        and pausing other tasks that are being executed as well.
        The task can also be paused, given that the preconditions for pausing are met.

        State diagram for InterruptableTask:

        stopped -> starting -----------> running ---------> finishing -*
           ^          |            _______|   ^_________               |
           |<---------*            v                   |               v
           |                   pausing -> paused -> resuming           |
           |                      |                    |               |
           ^                      v                    v               |
           |-------------<--------|----------<---------|--------<-------

        Each state has a transition state that allow for checks, synchronizatuion and for parts of the task
        to influence its own execution via signals.
        This also allows the TaskRunner to be informed about what the task is doing and ensuring that a task
        is executed in the correct thread.
        """
    sigDoStart = QtCore.Signal()
    sigStarted = QtCore.Signal()
    sigNextTaskStep = QtCore.Signal()
    sigDoPause = QtCore.Signal()
    sigPaused = QtCore.Signal()
    sigDoResume = QtCore.Signal()
    sigResumed = QtCore.Signal()
    sigDoFinish = QtCore.Signal()
    sigFinished = QtCore.Signal()
    sigStateChanged = QtCore.Signal(object)

    prePostTasks = {}
    pauseTasks = {}
    requiredModules = []

    def __init__(self, name, runner, references, config, **kwargs):
        """ Create an Interruptable task.
          @param str name: unique task name
          @param object runner: reference to the TaskRunner managing this task
          @param dict references: a dictionary of all required modules
          @param dict config: configuration dictionary
        """
        default_callbacks = {
                'onrun': self._start,
                'onpause': self._pause,
                'onresume': self._resume,
                'onfinish': self._finish
                }
        _stateDict = {
            'initial': 'stopped',
            'events': [
                {'name': 'run',                 'src': 'stopped',   'dst': 'starting'},
                {'name': 'startingFinished',    'src': 'starting',  'dst': 'running'},
                {'name': 'pause',               'src': 'running',   'dst': 'pausing'},
                {'name': 'pausingFinished',     'src': 'pausing',   'dst': 'paused'},
                {'name': 'finish',              'src': 'running',   'dst': 'finishing'},
                {'name': 'finishingFinished',   'src': 'finishing', 'dst': 'stopped'},
                {'name': 'resume',              'src': 'paused',    'dst': 'resuming'},
                {'name': 'resumingFinished',    'src': 'resuming',  'dst': 'running'},
                {'name': 'abort',               'src': 'pausing',   'dst': 'stopped'},
                {'name': 'abort',               'src': 'starting',  'dst': 'stopped'},
                {'name': 'abort',               'src': 'resuming',  'dst': 'stopped'}
            ],
            'callbacks': default_callbacks
        }
        if 'PyQt5' in sys.modules:
            super().__init__(cfg=_stateDict, **kwargs)
        else:
            QtCore.QObject.__init__(self)
            Fysom.__init__(self, _stateDict)

        self.lock = Mutex()
        self.name = name
        self.interruptable = False
        self.success = False
        self.runner = runner
        self.ref = references
        self.config = config

        self.sigDoStart.connect(self._doStart, QtCore.Qt.QueuedConnection)
        self.sigDoPause.connect(self._doPause, QtCore.Qt.QueuedConnection)
        self.sigDoResume.connect(self._doResume, QtCore.Qt.QueuedConnection)
        self.sigDoFinish.connect(self._doFinish, QtCore.Qt.QueuedConnection)
        self.sigNextTaskStep.connect(self._doTaskStep, QtCore.Qt.QueuedConnection)

    @property
    def log(self):
        """
        Returns a logger object
        """
        return logging.getLogger("{0}.{1}".format(
            self.__module__,self.__class__.__name__))

    def onchangestate(self, e):
        """ Fysom callback for state transition.

          @param object e: Fysom state transition description
        """
        self.sigStateChanged.emit(e)

    def _start(self, e):
        """
          @param object e: Fysom state transition description

          @return bool: True if task was started, False otherwise
        """
        self.result = TaskResult()
        if self.checkStartPrerequisites():
            #print('_run', QtCore.QThread.currentThreadId(), self.current)
            self.sigDoStart.emit()
            #print('_runemit', QtCore.QThread.currentThreadId(), self.current)
            return True
        else:
            return False

    def _doStart(self):
        """ Starting prerequisites were met, now do the actual start action.
        """
        try:
            #print('dostart', QtCore.QThread.currentThreadId(), self.current)
            self.runner.pausePauseTasks(self)
            self.runner.preRunPPTasks(self)
            self.startTask()
            self.startingFinished()
            self.sigStarted.emit()
            self.sigNextTaskStep.emit()
        except Exception as e:
            self.log.exception('Exception during task {0}. {1}'.format(
                self.name, e))
            self.result.update(None, False)

    def _doTaskStep(self):
        """ Check for state transitions to pause or stop and execute one step of the task work function.
        """
        try:
            if self.runTaskStep():
                if self.isstate('pausing') and self.checkPausePrerequisites():
                    self.sigDoPause.emit()
                elif self.isstate('finishing'):
                    self.sigDoFinish.emit()
                else:
                    self.sigNextTaskStep.emit()
            else:
                self.finish()
                self.sigDoFinish.emit()
        except Exception as e:
            self.log.exception('Exception during task step {0}. {1}'.format(
                self.name, e))
            self.result.update(None, False)
            self.finish()
            self.sigDoFinish.emit()

    def _pause(self, e):
        """ This does nothing, it is up to the TaskRunner to check that pausing is allowed and triger the next step.
        """
        pass

    def _doPause(self):
        """ Prerequisites for pausing were checked by Task runner and met, so execute the actual pausing action.
        """
        try:
            self.pauseTask()
            self.runner.postRunPPTasks(self)
            self.pausingFinished()
            self.sigPaused.emit()
        except Exception as e:
            self.log.exception('Exception while pausing task {}. '
                    '{}'.format(self.name, e))
            self.result.update(None, False)

    def _resume(self, e):
        """ Trigger resuming action.
        """
        self.sigDoResume.emit()

    def _doResume(self):
        """ Actually execute resuming action.
        """
        try:
            self.runner.preRunPPTasks(self)
            self.resumeTask()
            self.resumingFinished()
            self.sigResumed.emit()
            self.sigNextTaskStep.emit()
        except Exception as e:
            self.log.exception('Exception while resuming task {}. '
                    '{}'.format(self.name, e))
            self.result.update(None, False)

    def _finish(self, e):
        """ Do nothing, it is up to the TaskRunner to trigger the next step.
        """
        pass

    def _doFinish(self):
        """ Actually finish execution.
        """
        self.cleanupTask()
        self.runner.resumePauseTasks(self)
        self.runner.postRunPPTasks(self)
        self.finishingFinished()
        self.sigFinished.emit()

    def checkStartPrerequisites(self):
        """ Check whether this task can be started by checking if all tasks to be paused are either stopped or can be paused.
            Also check custom prerequisites.

          @return bool: True if task can be stated, False otherwise
        """
        for task in self.prePostTasks:
            if not ( isinstance(self.prePostTasks[task], PrePostTask) and self.prePostTasks[task].can('prerun') ):
                self.log('Cannot start task {0} as pre/post task {1} is not in a state to run.'.format(self.name, task), msgType='error')
                return False
        for task in self.pauseTasks:
            if not (isinstance(self.pauseTasks[task], InterruptableTask)
                    and (
                        self.pauseTasks[task].can('pause')
                        or self.pauseTasks[task].isstate('stopped')
                    )):
                self.log('Cannot start task {0} as interruptable task {1} is not stopped or able to pause.'.format(self.name, task), msgType='error')
                return False
        if not self.checkExtraStartPrerequisites():
            return False
        return True

    def checkExtraStartPrerequisites(self):
        """ If your task has extra prerequisites that are not covered by
            checking if a certain task can be paused, overwrite this function
            when sub-classing.

        @return bool: return True if task can be started, False otherwise
        """
        return True

    def checkPausePrerequisites(self):
        """ Check if task is allowed to pause based on external state."""

        try:
            return self.checkExtraPausePrerequisites()
        except Exception as e:
            self.log.exception('Exception while checking pause '
                    'prerequisites for task {}. {}'.format(self.name, e))
            return False

    def checkExtraPausePrerequisites(self):
        """ If yout task has prerequisites for pausing, overwrite this function when subclassing and put the check here.

          @return bool: return True if task can be paused right now, False otherwise
        """
        return True

    def canPause(self):
        """ Check if task can pause based on its own state only.
        """
        return self.interruptable and self.can('pause') and self.checkPausePrerequisites()

    def check_config_key(self, key, default, possible_values=None):
        """ Helper method to check is a key is defined in config and set a default value if not

            @param string key: The key to get or set
            @param object default: The default value if not set
            @param list possible_values: If note None, use the default if the current value is not in this list

            """
        if key not in self.config or self.config[key] is None or \
                (possible_values is not None and self.config[key] not in possible_values):
            self.config[key] = default

    @abc.abstractmethod
    def startTask(self):
        """ Implement the operation to start your task here.
        """
        pass

    @abc.abstractmethod
    def runTaskStep(self):
        """ Implement one work step of your task here.
          @return bool: True if the task should continue running, False if it should finish.
        """
        return False

    @abc.abstractmethod
    def pauseTask(self):
        """ Implement the operations necessary to pause your task here.
        """
        pass

    @abc.abstractmethod
    def resumeTask(self):
        """ Implement the operations necessary to resume your task from being paused here.
        """
        pass

    @abc.abstractmethod
    def cleanupTask(self):
        """ If your task leaves behind any undesired state, take care to remove it in this function.
            It is called after a task has finished.
        """
        pass

class PrePostTask(QtCore.QObject, Fysom, metaclass=TaskMetaclass):
    """ Represents a task that creates the necessary conditions for a different task
        and reverses its own actions afterwards.
    """

    sigPreExecStart = QtCore.Signal()
    sigPreExecFinish = QtCore.Signal()
    sigPostExecStart = QtCore.Signal()
    sigPostExecFinish = QtCore.Signal()
    sigStateChanged = QtCore.Signal(object)

    requiredModules = []

    def __init__(self, name, runner, references, config, **kwargs):
        """ Create a PrePostTask.
          @param str name: unique name of the task
          @param object runner: TaskRunner that manages this task
          @param dict references: contains references to all required modules
          @param dict config: configuration parameter dictionary
        """
        _default_callbacks = {'onprerun': self._pre, 'onpostrun': self._post}
        _stateList = {
            'initial': 'stopped',
            'events': [
                {'name': 'prerun', 'src': 'stopped', 'dst': 'paused'},
                {'name': 'postrun', 'src': 'paused', 'dst': 'stopped'}
            ],
            'callbacks': _default_callbacks
        }
        if 'PyQt5' in sys.modules:
            super().__init__(cfg=_stateList, **kwargs)
        else:
            QtCore.QObject.__init__(self)
            Fysom.__init__(self, _stateList)
        self.lock = Mutex()
        self.name = name
        self.runner = runner
        self.ref = references
        self.config = config

    @property
    def log(self):
        """
        Returns a logger object
        """
        return logging.getLogger("{0}.{1}".format(
            self.__module__,self.__class__.__name__))

    def onchangestate(self, e):
        """ Fysom callback for all state transitions.
          @param object e: Fysom state transition description

          This just emits a signal so external components can react.
        """
        self.sigStateChanged.emit(e)

    @abc.abstractmethod
    def preExecute(self):
        """ This method contains any action that should be done before some task.
            It needs to be overwritten in every subclass.
        """
        pass

    @abc.abstractmethod
    def postExecute(self):
        """ This method needs to undo any actions in preExecute() after a task has been finished.
            It needs to be overwritten in every subclass.
        """
        pass

    def _pre(self, e):
        """ Actually call preExecute with the appropriate safeguards amd emit singals before and afterwards.

          @param object e: Fysom state transition description
        """
        self.sigPreExecStart.emit()
        try:
            self.preExecute()
        except Exception as e:
            self.log.exception('Exception during task {0}. {1}'.format(
                self.name, e))

        self.sigPreExecFinish.emit()

    def _post(self, e):
        """ Actually call postExecute with the appropriate safeguards amd emit singals before and afterwards.

          @param object e: Fysom state transition description
        """
        self.sigPostExecStart.emit()
        try:
            self.postExecute()
        except Exception as e:
            self.log.exception('Exception during task {0}. {1}'.format(
                self.name, e))

        self.sigPostExecFinish.emit()

