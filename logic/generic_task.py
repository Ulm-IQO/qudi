# -*- coding: utf-8 -*-
"""
This file contains the QuDi logic module base class.

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

from core.util.customexceptions import InterfaceImplementationError
from core.util.mutex import Mutex
from pyqtgraph.Qt import QtCore
from fysom import Fysom

class TaskResult(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.data = None
        self.success = None

    def update(self, data, success=None):
        self.data = data
        self.success = success

class InterruptableTask(QtCore.QObject, Fysom):
    """ This class represents a task in a module that can be safely executed by checking preconditions
        and pausing other tasks that are being executed as well.
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
    requiredModules = {}

    def __init__(self, name, runner, **kwargs):
        QtCore.QObject.__init__(self)
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
                {'name': 'abort',               'src': 'pausing',   'dst': 'stopped'}
            ],
            'callbacks': default_callbacks
        }
        Fysom.__init__(self, _stateDict)
        self.lock = Mutex()
        self.name = name
        self.interruptable = False
        self.success = False
        self.taskRunner = runner

        self.sigDoStart.connect(self._doStart, QtCore.Qt.QueuedConnection)
        self.sigDoPause.connect(self._doPause, QtCore.Qt.QueuedConnection)
        self.sigDoResume.connect(self._doResume, QtCore.Qt.QueuedConnection)
        self.sigDoFinish.connect(self._doFinish, QtCore.Qt.QueuedConnection)
        self.sigNextTaskStep.connect(self._doTaskStep, QtCore.Qt.QueuedConnection)

    def onchangestate(self, e):
        """ Fysom callback for state transition.

          @param object e: Fysom state transition description
        """
        self.sigStateChanged.emit(e)

    def _start(self, e):
        self.result = TaskResult()
        if self.checkStartPrerequisites():
            print('_run', QtCore.QThread.currentThreadId(), self.current)
            self.sigDoStart.emit()
            print('_runemit', QtCore.QThread.currentThreadId(), self.current)
            return True
        else:
            return False

    def _doStart(self):
        try:
            print('dostart', QtCore.QThread.currentThreadId(), self.current)
            for task in self.prePostTasks:
                self.prePostTasks[task].prerun()
            for task in self.pauseTasks:
                if not self.pauseTasks[task].isstate('stopped') and self.pauseTasks[task].can('pause'):
                    self.pauseTasks[task].pause()
            self.startTask()
            self.startingFinished()
            self.sigStarted.emit()
            self.sigNextTaskStep.emit()
        except Exception as e:
            self.taskRunner.logMsg('Exception during task {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)
    
    def _doTaskStep(self):
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
        except Exception as e:
            self.taskRunner.logMsg('Exception during task step {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)
            self.finish()
                
    def _pause(self, e):
        pass

    def _doPause(self):
        try:
            self.pauseTask()
            self.pausingFinished()
            self.sigPaused.emit()
        except Exception as e:
            self.taskRunner.logMsg('Exception while pausing task {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)
        
    def _resume(self, e):
            self.sigDoResume.emit()

    def _doResume(self):
        try:
            self.resumeTask()
            self.resumingFinished()
            self.sigResumed.emit()
            self.sigNextTaskStep.emit()
        except Exception as e:
            self.logMsg('Exception while resuming task {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)

    def _finish(self, e):
        pass

    def _doFinish(self):
        self.result.update(self._result, self.success)
        self.cleanupTask()
        self.finishingFinished()
        self.sigFinished.emit()

    def checkStartPrerequisites(self):
        for task in self.prePostTasks:
            if not ( isinstance(self.prePostTasks[task], PrePostTask) and self.prePostTasks[task].can('prerun') ):
                self.log('Cannot start task {} as pre/post task {} is not in a state to run.'.format(self.name, task), msgType='error')
                return False
        for task in self.pauseTasks:
            if not (isinstance(self.pauseTasks[task], InterruptibleTask)
                    and ( 
                        self.pauseTasks[task].can('pause')
                        or self.pauseTasks[task].isstate('stopped')
                    )):
                self.log('Cannot start task {} as interruptable task {} is not stopped or able to pause.'.format(self.name, task), msgType='error')
                return False
        if not self.checkExtraStartPrerequisites():
            return False
        return True

    def checkExtraStartPrerequisites(self):
        return True

    def checkPausePrerequisites(self):
        try:
            return self.checkExtraPausePrerequisites()
        except Exception as e:
            self.logMsg('Exception while checking pause prerequisites for task {}. {}'.format(self.name, e), msgType='error')
            return False

    def checkExtraPausePrerequisites(self):
        return True

    def canPause(self):
        return self.interruptable and self.can('pause') and self.checkPausePrerequisites()

    def startTask(self):
        raise InterfaceImplementationError('startTask needs to be implemented in subclasses!')

    def runTaskStep(self):
        raise InterfaceImplementationError('runTaskStep needs to be implemented in subclasses!')
        return False

    def pauseTask(self):
        raise InterfaceImplementationError('pauseTask may need to be implemented in subclasses!')

    def resumeTask(self):
        raise InterfaceImplementationError('resumeTask may need to be implemented in subclasses!')

    def cleanupTask(self):
        raise InterfaceImplementationError('cleanupTask needs to be implemented in subclasses!')

class PrePostTask(QtCore.QObject, Fysom):

    sigPreExecStart = QtCore.Signal()
    sigPreExecFinish = QtCore.Signal()
    sigPostExecStart = QtCore.Signal()
    sigPostExecFinish = QtCore.Signal()
    sigStateChanged = QtCore.Signal(object)

    def __init__(self, name, runner, *args, **kwargs):
        QtCore.QObject.__init__(self)
        _default_callbacks = {'onprerun': self._pre, 'onpostrun': self._post}
        _stateList = {
            'initial': 'stopped',
            'events': [
                {'name': 'prerun', 'src': 'stopped', 'dst': 'paused'},
                {'name': 'postrun', 'src': 'paused', 'dst': 'stopped'}
            ],
            'callbacks': _default_callbacks
        }
        Fysom.__init__(self, _stateList)
        self.lock = Mutex()
        self.name = name
        self.args = args

    def onchangestate(self, e):
        """ Fysom callback for state transition.

          @param object e: Fysom state transition description
        """
        self.sigStateChanged.emit(e)

    def preExecute(self):
        raise InterfaceImplementationError('preExecute may need to be implemented in subclasses!')

    def postExecute(self):
        raise InterfaceImplementationError('preExecute may need to be implemented in subclasses!')

    def _pre(self, e):
        self.sigPreExecStart.emit()
        try:
            self.preExecute()
        except Exception as e:
            self.taskRunner.logMsg('Exception during task {}. {}'.format(self.name, e), msgType='error')

        self.sigPreExecFinish.emit()

    def _post(self, e):
        self.sigPostExecStart.emit()
        try:
            self.postExecute()
        except Exception as e:
            self.taskRunner.logMsg('Exception during task {}. {}'.format(self.name, e), msgType='error')

        self.sigPostExecFinish.emit()
        
