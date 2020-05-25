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
import weakref
import importlib
from enum import Enum
from qtpy import QtCore

from qudi.core.meta import TaskMetaclass
from qudi.core.util.mutex import Mutex, RecursiveMutex
from qudi.core.connector import Connector
from fysom import Fysom

logger = logging.getLogger(__name__)


class ModuleScript(QtCore.QRunnable, QtCore.QObject):
    """

    """
    # Declare modules to control.
    # _my_module_conn = Connector(interface='MyModuleClassName', name='my_module')

    sigFinished = QtCore.Signal(object, bool)

    def __init__(self, *args, conn_modules, fn=None, **kwargs):
        super().__init__()
        # Create connectors and connect them to module instances
        for attr, conn in self.module_connectors().items():
            name = attr if conn.name is None else conn.name
            if name not in conn_modules and not conn.optional:
                raise Exception(
                    'Module connection "{0}" not configured for QudiScript.'.format(name))
            new_conn = conn.copy(name=name)
            setattr(self, attr, new_conn)
            new_conn.connect(conn_modules[name])
        # Set function as _run bound method
        if callable(fn):
            self._run = fn.__get__(self)
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.success = None

    @classmethod
    def module_connectors(cls):
        connectors = dict()
        for c in reversed(cls.mro()[:-1]):
            connectors.update(
                {attr: val for attr, val in vars(c).items() if isinstance(val, Connector)})
        return connectors

    @property
    def log(self):
        """ Returns a logger object """
        return logging.getLogger('{0}.{1}'.format(self.__module__, self.__class__.__name__))

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.run()
        return self.result, self.success

    @QtCore.Slot()
    def run(self):
        if self.can_run():
            try:
                self.result = self._run(*self.args, **self.kwargs)
                self.success = True
            except:
                self.result = None
                self.success = False
                self.log.exception('Something went wrong while executing ModuleScript "{0}":'
                                   ''.format(self.__class__.__name__))
        else:
            self.result = None
            self.success = False
        self.sigFinished.emit(self.result, self.success)
        return

    def can_run(self):
        return True

    @abc.abstractmethod
    def _run(self, *args, **kwargs):
        pass


class ScriptRunner(QtCore.QObject):
    """
    ToDo: Document
    """

    _instance = None  # Only class instance created will be stored here as weakref
    _lock = RecursiveMutex()

    sigScriptsChanged = QtCore.Signal(dict)
    sigScriptFinished = QtCore.Signal(str, object, bool)

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None or cls._instance() is None:
                obj = super().__new__(cls, *args, **kwargs)
                cls._instance = weakref.ref(obj)
                return obj
            raise Exception('ScriptRunner is a singleton. An instance has already been created in '
                            'this process. Please use ScriptRunner.instance() instead.')

    def __init__(self, *args, qudi_main, **kwargs):
        super().__init__(*args, **kwargs)
        self._qudi_main_ref = weakref.ref(qudi_main, self._qudi_main_ref_dead_callback)
        self._scripts = dict()
        self._async_running = set()
        self.thread_pool = QtCore.QThreadPool.globalInstance()

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                return None
            return cls._instance()

    @property
    def script_names(self):
        with self._lock:
            return tuple(self._scripts)

    @property
    def scripts(self):
        with self._lock:
            return self._scripts.copy()

    def remove_script(self, script_name, ignore_missing=False, emit_change=True):
        with self._lock:
            if script_name not in self._scripts:
                if not ignore_missing:
                    logger.error('No script with name "{0}" registered. Unable to remove script.'
                                 ''.format(script_name))
                return
            if script_name in self._async_running:
                logger.warning('Script "{0}" about to be removed is still running in thread pool.'
                               ''.format(script_name))
                self._scripts[script_name].abort()
            self._scripts[script_name].sigFinished.disconnect()
            del self._scripts[script_name]
            if emit_change:
                self.sigScriptsChanged.emit(self.scripts)

    def add_script(self, name, configuration, allow_overwrite=False, emit_change=True):
        with self._lock:
            if not isinstance(name, str) or not name:
                raise TypeError('Script name must be non-empty str type')

            if allow_overwrite:
                self.remove_script(name, ignore_missing=True)
            elif name in self._scripts:
                logger.error('Script with name "{0}" already registered. '
                             'Unable to add script of same name.'.format(name))
                return
            module, class_name = configuration.get('module.Class').rsplit('.', 1)
            mod = importlib.import_module('script.{0}'.format(module))
            importlib.reload(mod)

            script_cls = getattr(mod, class_name)
            if isinstance(script_cls, ModuleScript):
                script = script_cls(conn_modules=modules, fn=fn)
            elif callable(script_cls):
                script = ModuleScript(conn_modules=modules, fn=fn)
            else:
                raise Exception(
                    'Imported object is neither a ModuleScript subclass nor a callable.')

            script.sigFinished.connect(
                lambda result, success: self._script_finished_callback(name, result, success))
            self._scripts[name] = script
            if emit_change:
                self.sigManagedModulesChanged.emit(self.modules)

    @QtCore.Slot(str, object, bool)
    def _script_finished_callback(self, script_name, result, success):
        with self._lock:
            if script_name in self._async_running:
                self._async_running.remove(script_name)
        self.sigScriptFinished.emit(script_name, result, success)

    def activate_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error('No module named "{0}" found in managed qudi modules. '
                             'Module activation aborted.'.format(module_name))
                return
            return self._modules[module_name].activate()

    def deactivate_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error('No module named "{0}" found in managed qudi modules. '
                             'Module deactivation aborted.'.format(module_name))
                return
            return self._modules[module_name].deactivate()

    def reload_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error('No module named "{0}" found in managed qudi modules. '
                             'Module reload aborted.'.format(module_name))
                return
            return self._modules[module_name].reload()

    def clear_module_status(self, module_name):
        # ToDo: implement together with module Base class
        pass

    def start_all_modules(self):
        with self._lock:
            for module in self._modules.values():
                module.activate()

    def stop_all_modules(self):
        with self._lock:
            for module in self._modules.values():
                module.deactivate()

    def _module_ref_dead_callback(self, dead_ref, module_name):
        with self._lock:
            self.remove_module(module_name, ignore_missing=True)

    def _qudi_main_ref_dead_callback(self):
        logger.error('Qudi main reference no longer valid. This should never happen. Tearing down '
                     'ModuleManager.')
        self.clear()


class TaskState(Enum):
    stopped = 0
    starting = 1
    running = 2
    pausing = 3
    paused = 4
    resuming = 5
    finishing = 6


class TaskStateMachine(Fysom):
    """
    ToDo: Document
    """

    def __init__(self, parent, callbacks=None, **kwargs):
        if callbacks is None:
            callbacks = dict()

        # State machine definition
        # the abbreviations for the event list are the following:
        #   name:   event name,
        #   src:    source state,
        #   dst:    destination state
        fsm_cfg = {
            'initial': 'stopped',
            'events': [
                {'name': 'run',                 'src': 'stopped',   'dst': 'starting'},
                {'name': 'startup_complete',    'src': 'starting',  'dst': 'running'},
                {'name': 'pause',               'src': 'running',   'dst': 'pausing'},
                {'name': 'pausing_complete',    'src': 'pausing',   'dst': 'paused'},
                {'name': 'finish',              'src': 'running',   'dst': 'finishing'},
                {'name': 'finishing_complete',  'src': 'finishing', 'dst': 'stopped'},
                {'name': 'resume',              'src': 'paused',    'dst': 'resuming'},
                {'name': 'resuming_complete',   'src': 'resuming',  'dst': 'running'},
                {'name': 'abort',               'src': 'pausing',   'dst': 'stopped'},
                {'name': 'abort',               'src': 'starting',  'dst': 'stopped'},
                {'name': 'abort',               'src': 'resuming',  'dst': 'stopped'}
            ],
            'callbacks': callbacks}

        # Initialise state machine:
        super().__init__(cfg=fsm_cfg, **kwargs)
        self.__parent = parent

    def __call__(self):
        """
        Returns the current state.
        """
        return TaskState[self.current]

    def _build_event(self, event):
        """
        Overrides Fysom _build_event to wrap on_activate and on_deactivate to catch and log
        exceptions.

        @param str event: Event name to build the Fysom event for

        @return function: The event handler used by Fysom for the given event
        """
        base_event = super()._build_event(event)
        if event in ('run', 'pause', 'resume', 'finish', 'abort'):
            def wrap_event(*args, **kwargs):
                try:
                    base_event(*args, **kwargs)
                except:
                    self.__parent.log.exception(
                        'Error while trying to {0} task "{1}"'.format(event, self.__parent.name))
                    return False
                return True
            return wrap_event
        return base_event


class InterruptableTask(QtCore.QObject, metaclass=TaskMetaclass):
    """
    This class represents a task in a module that can be safely executed by checking
    preconditions and pausing other tasks that are being executed as well.
    The task can also be paused, given that the preconditions for pausing are met.

    State diagram for InterruptableTask:

        stopped -> starting -----------> running ---------> finishing -*
           ^          |            _______|   ^_________               |
           |<---------*            v                   |               v
           |                   pausing -> paused -> resuming           |
           |                      |                    |               |
           ^                      v                    v               |
           |-------------<--------|----------<---------|--------<-------

    Each state has a transition state that allow for checks, synchronization and for parts of the
    task to influence its own execution via signals.
    This also allows the TaskRunner to be informed about what the task is doing and ensuring that a
    task is executed in the correct thread.
    """
    sigAbort = QtCore.Signal()
    sigStarted = QtCore.Signal()
    sigNextTaskStep = QtCore.Signal()
    sigDoPause = QtCore.Signal()
    sigPaused = QtCore.Signal()
    sigDoResume = QtCore.Signal()
    sigResumed = QtCore.Signal()
    sigDoFinish = QtCore.Signal()
    sigFinished = QtCore.Signal()
    sigStateChanged = QtCore.Signal(TaskState, TaskState)  # new state, old state

    scripts = dict()

    def __init__(self, name, runner, references, config, **kwargs):
        """ Create an Interruptable task.
          @param str name: unique task name
          @param object runner: reference to the TaskRunner managing this task
          @param dict references: a dictionary of all required modules
          @param dict config: configuration dictionary
        """
        super().__init__(**kwargs)
        fsm_callbacks = {'onchangestate': self._state_change_callback,
                         # 'onrun': self._start,
                         # 'onpause': self._pause,
                         # 'onresume': self._resume,
                         # 'onfinish': self._finish
                         }

        self.task_state = TaskStateMachine(parent=self, callbacks=fsm_callbacks)

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
        return logging.getLogger('{0}.{1}'.format(self.__module__, self.__class__.__name__))

    def _state_change_callback(self, e):
        """ Fysom callback for state transition.

          @param object e: Fysom state transition description
        """
        old = TaskState[e.src]
        new = TaskState[e.dst]
        if old != new:
            self.sigStateChanged.emit(new, old)

    def _startup_callback(self, e):
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

    @abc.abstractmethod
    def task_preparation(self):
        pass

    @abc.abstractmethod
    def task_cleanup(self):
        pass

    def _doStart(self):
        """ Starting prerequisites were met, now do the actual start action.
        """
        try:
            #print('dostart', QtCore.QThread.currentThreadId(), self.current)
            self.runner.pause_pause_tasks(self)
            self.runner.pre_run_prepost_tasks(self)
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
            self.runner.post_run_prepost_tasks(self)
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
            self.runner.pre_run_prepost_tasks(self)
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
        self.runner.resume_pause_tasks(self)
        self.runner.post_run_prepost_tasks(self)
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

