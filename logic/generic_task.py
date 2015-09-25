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

class TaskResult(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.data = None
        self.success = None

    def updata(self, data, success=None):
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

    prePostTasks = {}
    pauseTasks = {}
    requiredModules = {}

    def __init__(self, name, runner, args=[], kwargs={}):
        QtCore.QObject.__init__(self)
        _default_callbacks = {'run': self._run, 'pause': self._pause, 'resume': self._resume, 'finish': self._finish}
        _stateDict = {
            'initial': 'stopped',
            'events': [
                {'name': 'run', 'src': 'stopped', 'dst': 'starting'},
                {'name': 'startingFinished', 'src': 'starting', 'dst': 'running'},
                {'name': 'pause', 'src': 'running', 'dst': 'pausing'},
                {'name': 'pausingFinished', 'src': 'pausing', 'dst': 'paused'},
                {'name': 'finish', 'src': 'running', 'dst': 'finishing'},
                {'name': 'finishingFinished', 'src': 'finishing', 'dst': 'stopped'},
                {'name': 'resume', 'src': 'paused', 'dst': 'resuming'}
                {'name': 'resumingFinished', 'src': 'resuming', 'dst': 'running'}
            ],
            'callbacks': _default_callbacks
        }
        Fysom.__init__(self, _stateDict)
        self.lock = Mutex()
        self.name = name
        self.args = args
        self.interruptable = False
        self.success = False
        self.taskRunner = runner

        self.sigDoStart.connect(self._doStart, QtCore.Qt.QueuedConnection)
        self.sigDoPause.connect(self._doPause, QtCore.Qt.QueuedConnection)
        self.sigDoResume.connect(self._doResume, QtCore.Qt.QueuedConnection)
        self.sigDoFinish.connect(self._doFinish, QtCore.Qt.QueuedConnection)
        self.sigNextTaskStep.connect(self._doTaskStep, QtCore.Qt.QueuedConnection)

    def _run(self, e):
        self.result = TaskResult()
        if self.checkStartPrerequisites():
            self.sigDoStart.emit()
        else:
            return False

    def _doStart(self):
        try:
            for task in prePostTasks:
                prePostTasks[task].prerun()
            for task in pauseTasks:
                if not pauseTasks[task].isstate('stopped') and pauseTasks[task].can('pause'):
                    pauseTasks[task].pause()
            self.startTask()
            self.startingFinished()
            self.sigStarted.emit()
        except Exception as e:
            runner.logMsg('Exception during task {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)
    
    def _doTaskStep(self):
        try:
            if self.runTaskStep():
                if self.isstate('pausing'):
                    self.sigDoPause.emit()
                else:
                    self.sigNextTaskStep.emit()
            else:
                self.finish()
        except Exception as e:
            runner.logMsg('Exception during task step {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)
            self.finish()
                
    def _pause(self, e):
        try:
            if self.checkPausePrerequisites():
                self.sigDoPause.emit()
            else:
                self.sigNextTaskStep.emit()
                return False
        except Exception as e:
            runner.logMsg('Exception while preparing pause of task {}. {}'.format(self.name, e), msgType='error')
            self.result.update(None, False)

    def _doPause(self):
        try:
            self.pauseTask()
            self.pausingFinished()
            self.sigPaused.emit()
        except Exception as e:
            runner.logMsg('Exception while pausing task {}. {}'.format(self.name, e), msgType='error')
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
        self.sigDoFinish.emit()

    def _doFinish(self):
        result.update(self.result, self.success)
        self.sigFinished.emit()

    def checkStartPrerequisites(self):
        for task in prePostTasks:
            if not ( isinstance(prePostTasks[task], PrePostTask) and prePostTasks[task].can('prerun') ):
                self.log('Cannot start task {} as pre/post task {} is not in a state to run.'.format(self.name, task), msgType='error')
                return False
        for task in pauseTasks:
            if not (isinstance(pauseTasks[task], InterruptibleTask)
                    and ( 
                        pauseTasks[task].can('pause')
                        or pauseTasks[task].isstate('stopped')
                    )):
                self.log('Cannot start task {} as interruptable task {} is not stopped or able to pause.'.format(self.name, task), msgType='error')
                return False
        if not checkExtraStartPrerequisites():
            return False
        return True

    def checkExtraStartPrerequisites(self):
        return True

    def checkPausePrerequisites(self):
    def checkExtraPausePrerequisites(self):

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

    def __init__(self, name, function, args=[]):
        QtCore.QObject.__init__()
        _default_callbacks = {'prerun': self.preExecute, 'postrun': self.postExecute}
        _stateList = {
            'initial': 'stopped',
            'events': [
                {'name': 'prerun', 'src': 'stopped', 'dst': 'paused'},
                {'name': 'postrun', 'src': 'paused', 'dst': 'stopped'}
            ],
            'callbacks': _default_callbacks
        }
        Fysom.__init__()
        self.lock = Mutex()
        self.name = name
        self.func = function
        self.args = args

    def preExecute(self):
        self.sigPreExecStart.emit()

        self.sigPreExecFinish.emit()

    def postExecute(self):
        self.sigPostExecStart.emit()

        self.sigPostExecFinish.emit()

    def canPause():
        return False
