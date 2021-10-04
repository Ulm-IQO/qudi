# -*- coding: utf-8 -*-

"""
This file contains a task class to run with qudi module dependencies as well as various
helper classes to run and manage these tasks.

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

__all__ = ['ModuleTask', 'ModuleTaskStateMachine']


from fysom import Fysom, Canceled
from PySide2 import QtCore
from typing import Mapping, Any, Optional, Callable, Union

from qudi.core.scripting.modulescript import ModuleScript, ModuleScriptInterrupted


class ModuleTaskStateMachine(Fysom, QtCore.QObject):
    """ Finite state machine for ModuleTask.
    State diagram for this FSM:

        stopped ---------> starting ---------> running
           ^                  |                   |
           |                  |                   v
           |                  --------------> finishing
           |                                      |
           |                                      |
           -------------------<--------------------
    """
    # do not copy declaration of trigger(self, event, *args, **kwargs), just apply Slot decorator
    trigger = QtCore.Slot(str, result=bool)(Fysom.trigger)

    def __init__(self, callbacks: Mapping[str, Callable[[Any], Union[None, bool]]],
                 parent: Optional[QtCore.QObject] = None):
        # State machine definition
        # the abbreviations for the event list are the following:
        #   name:   event name,
        #   src:    source state,
        #   dst:    destination state
        fsm_cfg = {'initial'  : 'stopped',
                   'events'   : [{'name': 'start', 'src': 'stopped', 'dst': 'starting'},
                                 {'name': 'run', 'src': 'starting', 'dst': 'running'},
                                 {'name': 'finish', 'src': 'running', 'dst': 'finishing'},
                                 {'name': 'terminate', 'src': 'finishing', 'dst': 'stopped'},
                                 {'name': 'skip_run', 'src': 'starting', 'dst': 'finishing'}],
                   'callbacks': dict() if callbacks is None else callbacks}

        # Initialise state machine:
        super().__init__(parent=parent, cfg=fsm_cfg)

    @QtCore.Slot()
    def start(self) -> None:
        super().start()

    @QtCore.Slot()
    def run(self) -> None:
        super().run()

    @QtCore.Slot()
    def finish(self) -> None:
        super().finish()

    @QtCore.Slot()
    def terminate(self) -> None:
        super().terminate()

    @QtCore.Slot()
    def skip_run(self) -> None:
        super().skip_run()


class ModuleTask(ModuleScript):
    """ Extends parent ModuleScript class with more functionality like setup and cleanup.
    Includes a finite state machine for better monitoring and control.

    The only part that can be interrupted are the _run() and _setup methods.
    The implementations must occasionally call _check_interrupt() to raise an exception at that
    point if an interrupt is requested. This should happen at points where _cleanup() can
    properly terminate the task afterwards.
    """

    sigStateChanged = QtCore.Signal(str)  # new state name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up state machine
        fsm_callbacks = {'on_starting': self.__starting_callback,
                         'on_running': self.__running_callback,
                         'on_finishing': self.__finishing_callback,
                         'on_stopped': self.__stopped_callback}
        self._state_machine = ModuleTaskStateMachine(callbacks=fsm_callbacks, parent=self)

    @property
    def state(self):
        return self._state_machine.current

    @QtCore.Slot()
    def run(self) -> None:
        """ Kick-off state machine and start task execution.

        DO NOT OVERRIDE IN SUBCLASS!
        """
        if self.running:
            self.log.error(
                f'Unable to run. Task is already running or has been interrupted immediately.'
            )
        else:
            self._state_machine.start()

    # Implement _setup and _cleanup in subclass if needed. By default they will simply do nothing.
    # You MUST in any case implement _run in a subclass (see: ModuleScript._run).
    def _setup(self) -> None:
        """ Optional setup procedure to be performed before _run() is called.
        Raising an exception in here will cause the task to directly call _cleanup() and skip the
        _run() call.
        Access (keyword) arguments via self.(kw)args.
        Can NOT be interrupted.

        Implement in subclass.
        """
        pass

    def _cleanup(self) -> None:
        """ Optional cleanup procedure to be performed after _setup() and _run() have been called.
        This method will be called even if _setup() or _run() have raised an exception.
        Access (keyword) arguments via self.(kw)args.
        Can NOT be interrupted.

        Implement in subclass.
        """
        pass

    # Callbacks for FSM below. Ignore this part unless you know what you are doing!
    def __starting_callback(self, event: Any) -> None:
        """ FSM startup callback. This will call _setup and set status flags accordingly.
        Resets last task result. Handles task interrupts during execution of _setup method.
        """
        self.log.debug(f'Running setup')
        self.sigStateChanged.emit(event.dst)
        self.result = None
        with self._thread_lock:
            self._interrupted = False
            self._success = False
            self._running = True
        skip_run = True
        try:
            self._check_interrupt()
            self._setup()
            self._check_interrupt()
            skip_run = False
        except ModuleScriptInterrupted:
            self.log.info(f'Setup interrupted')
        except:
            self.log.exception('Exception during setup:')
            raise
        finally:
            if skip_run:
                self._state_machine.skip_run()
            else:
                self._state_machine.run()

    def __running_callback(self, event: Any) -> None:
        """ FSM callback to execute the mein task _run method. Sets success flag and task result.
        Handles task interrupts during execution of _run method.
        """
        self.log.debug(f'Running main method with\n\targs: {self.args}\n\tkwargs: {self.kwargs}.')
        self.sigStateChanged.emit(event.dst)
        try:
            self._check_interrupt()
            self.result = self._run(*self.args, **self.kwargs)
            with self._thread_lock:
                self._success = True
        except ModuleScriptInterrupted:
            self.log.info(f'Main run method interrupted')
        except:
            self.log.exception('Exception during main run method:')
            raise
        finally:
            self._state_machine.finish()

    def __finishing_callback(self, event: Any) -> None:
        """ FSM callback to always call _cleanup method in the end regardless of task success.
        Handles task interrupts during execution of _run method.
        """
        self.log.debug(f'Running cleanup')
        self.sigStateChanged.emit(event.dst)
        try:
            self._cleanup()
        except ModuleScriptInterrupted:
            self.log.info('Cleanup interrupted')
        except:
            self.log.exception('Exception during cleanup:')
            raise
        finally:
            self._state_machine.terminate()

    def __stopped_callback(self, event: Any) -> None:
        """ FSM callback to emit a finished Qt signal and reset the running flag after the task has
        been terminated.
        """
        self.log.debug(f'ModuleTask "{self.__class__.__name__}" has been terminated.')
        self.sigStateChanged.emit(event.dst)
        with self._thread_lock:
            self._running = False
        self.sigFinished.emit()
