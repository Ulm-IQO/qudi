# -*- coding: utf-8 -*-
"""
This file contains the Qudi module base class.

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

import logging
import warnings
import copy
from fysom import Fysom  # provides a finite state machine
from collections import OrderedDict

from qtpy import QtCore
from .meta import ModuleMeta
from .configoption import MissingOption
from .connector import Connector
from core.util.mutex import Mutex


class ModuleStateMachine(Fysom, QtCore.QObject):
    """
    FIXME
    """
    # do not copy declaration of trigger(self, event, *args, **kwargs), just apply Slot decorator
    trigger = QtCore.Slot(str, result=bool)(Fysom.trigger)

    # signals
    sigStateChanged = QtCore.Signal(object)  # Fysom event

    def __init__(self, callbacks=None, parent=None, **kwargs):
        if callbacks is None:
            callbacks = dict()

        # State machine definition
        # the abbreviations for the event list are the following:
        #   name:   event name,
        #   src:    source state,
        #   dst:    destination state
        fsm_cfg = {'initial': 'deactivated',
                   'events': [{'name': 'activate', 'src': 'deactivated', 'dst': 'idle'},
                              {'name': 'deactivate', 'src': 'idle', 'dst': 'deactivated'},
                              {'name': 'deactivate', 'src': 'running', 'dst': 'deactivated'},
                              {'name': 'deactivate', 'src': 'locked', 'dst': 'deactivated'},
                              {'name': 'run', 'src': 'idle', 'dst': 'running'},
                              {'name': 'stop', 'src': 'running', 'dst': 'idle'},
                              {'name': 'lock', 'src': 'idle', 'dst': 'locked'},
                              {'name': 'lock', 'src': 'running', 'dst': 'locked'},
                              {'name': 'unlock', 'src': 'locked', 'dst': 'idle'},
                              {'name': 'runlock', 'src': 'locked', 'dst': 'running'}],
                   'callbacks': callbacks}

        # Initialise state machine:
        super().__init__(parent=parent, cfg=fsm_cfg, **kwargs)
        # QtCore.QObject.__init__(self, parent)
        # Fysom.__init__(self, cfg=fsm_cfg, **kwargs)

    def __call__(self):
        """
        Returns the current state.
        """
        return self.current

    def _build_event(self, event):
        """
        Overrides Fysom _build_event to wrap on_activate and on_deactivate to catch and log
        exceptions.

        @param str event: Event name to build the Fysom event for

        @return function: The event handler used by Fysom for the given event
        """
        base_event = super()._build_event(event)
        if event in ('activate', 'deactivate'):
            noun = 'activation' if event == 'activate' else 'deactivation'

            def wrap_event(*args, **kwargs):
                self.parent().log.debug(
                    '{0} in thread "{1}"'.format(noun.capitalize(),
                                                 QtCore.QThread.currentThread().objectName()))
                try:
                    base_event(*args, **kwargs)
                except:
                    self.parent().log.exception('Error during {0}'.format(noun))
                    return False
                return True

            return wrap_event
        return base_event

    def onchangestate(self, e):
        """
        Fysom callback for all state transitions.

        @param object e: Fysom event object passed through all state transition callbacks
        """
        self.sigStateChanged.emit(e)

    @QtCore.Slot()
    def activate(self):
        super().activate()

    @QtCore.Slot()
    def deactivate(self):
        super().deactivate()


class Base(QtCore.QObject, metaclass=ModuleMeta):
    """
    Base class for all loadable modules

    * Ensure that the program will not die during the load of modules in any case,
      and therefore do nothing!!!
    * Initialize modules
    * Provides a self identification of the used module
    * Output redirection (instead of print)
    * Provides a self de-initialization of the used module
    * Reload the module with code changes
    * Get your own configuration (for save)
    * Get name of status variables
    * Get status variables
    * Reload module data (from saved variables)
    """
    _threaded = False
    _connectors = dict()

    _sigPopUpMessage = QtCore.Signal(str, str)
    _sigBalloonMessage = QtCore.Signal(str, str, object)

    def __init__(self, manager, name, config=None, callbacks=None, **kwargs):
        """
        Initialise Base class object and set up its state machine.

        @param object self: the object being initialised
        @param object manager: the manager object that
        @param str name: unique name for this object
        @param dict configuration: parameters from the configuration file
        @param dict callbacks: dict specifying functions to be run on state machine transitions
        """
        super().__init__(**kwargs)

        if config is None:
            config = dict()
        if callbacks is None:
            callbacks = dict()

        default_callbacks = {'onbeforeactivate': self.__load_status_vars_activate,
                             'ondeactivate': self.__save_status_vars_deactivate}
        default_callbacks.update(callbacks)

        self.module_state = ModuleStateMachine(parent=self, callbacks=default_callbacks)

        # add connectors
        self.connectors = OrderedDict()
        for cname, con in self._conn.items():
            self.connectors[con.name] = con

        # add connection base (legacy)
        for con in self._connectors:
            self.connectors[con] = OrderedDict()
            self.connectors[con]['class'] = self._connectors[con]
            self.connectors[con]['object'] = None

        # add config options
        for oname, opt in self._config_options.items():
            if opt.name in config:
                cfg_val = config[opt.name]
            else:
                if opt.missing == MissingOption.error:
                    raise Exception('Required variable >> {0} << not given in configuration.\n'
                                    'Configuration is: {1}'.format(opt.name, config))
                elif opt.missing == MissingOption.warn:
                    self.log.warning('No variable >> {0} << configured, using default value {1} '
                                     'instead.'.format(opt.name, opt.default))
                elif opt.missing == MissingOption.info:
                    self.log.info('No variable >> {0} << configured, using default value {1} '
                                  'instead.'.format(opt.name, opt.default))
                cfg_val = opt.default
            if opt.check(cfg_val):
                converted_val = opt.convert(cfg_val)
                if opt.constructor_function is None:
                    setattr(self, opt.var_name, converted_val)
                else:
                    setattr(self, opt.var_name, opt.constructor_function(self, converted_val))

        # Enable pop-up and balloon messages by establishing a queued connection to manager if qudi
        # runs in headless mode (pop-up must run in main thread)
        if manager.has_gui:
            self._sigPopUpMessage.connect(manager.pop_up_message, QtCore.Qt.QueuedConnection)
            self._sigBalloonMessage.connect(manager.balloon_message, QtCore.Qt.QueuedConnection)

        self._manager = manager
        self._name = name
        self._configuration = config
        self._status_variables = OrderedDict()

    @QtCore.Slot()
    def move_to_manager_thread(self):
        """

        @return:
        """
        if QtCore.QThread.currentThread() != self.thread():
            QtCore.QMetaObject.invokeMethod(self,
                                            'move_to_manager_thread',
                                            QtCore.Qt.BlockingQueuedConnection)
        else:
            self.moveToThread(self._manager.thread())

    @property
    def module_thread(self):
        if self._threaded:
            return self.thread()
        return None

    def __load_status_vars_activate(self, event=None):
        """
        Restore status variables before activation and invoke on_activate method.

        @param object event: Fysom event object
        """
        # add status vars
        for vname, var in self._stat_vars.items():
            sv = self._status_variables
            svar = sv[var.name] if var.name in sv else var.default

            if var.constructor_function is None:
                setattr(self, var.var_name, svar)
            else:
                setattr(self, var.var_name, var.constructor_function(self, svar))

        # activate
        self.on_activate()

    def __save_status_vars_deactivate(self, event=None):
        """
        Invoke on_deactivate method and save status variables afterwards even if deactivation fails.

        @param object event: Fysom event object
        """
        try:
            self.on_deactivate()
        except Exception as e:
            raise e
        finally:
            # save status vars even if deactivation failed
            for vname, var in self._stat_vars.items():
                if hasattr(self, var.var_name):
                    if var.representer_function is None:
                        self._status_variables[var.name] = getattr(self, var.var_name)
                    else:
                        self._status_variables[var.name] = var.representer_function(
                                                            self,
                                                            getattr(self, var.var_name))

    @property
    def log(self):
        """
        Returns a logger object
        """
        return logging.getLogger('{0}.{1}'.format(self.__module__, self.__class__.__name__))

    @property
    def is_module_threaded(self):
        """
        Returns whether the module shall be started in a thread.
        """
        return self._threaded

    @property
    def status_variables(self):
        """
        Returns a deepcopy of the protected status_variable dict with variable names and data
        representing the module state for saving.

        DO NOT try to use this property to alter or set status variables.
        Use StatusVar instances from inside the module and do not alter status variables from any
        external module.

        @return dict: dict with variable names and contents
        """
        return copy.deepcopy(self._status_variables)

    @status_variables.setter
    def status_variables(self, var_dict):
        """
        Give the module a dict of variable names and their content representing the module state.

        DO NOT try to use this property to alter or set status variables.
        Use StatusVar instances from inside the module and do not alter status variables from any
        external module.

        @param OrderedDict var_dict: variable names and contents
        """
        if not isinstance(var_dict, dict):
            self.log.error('Did not pass a dict or OrderedDict to setStatusVariables in {0}.'
                           ''.format(self.__class__.__name__))
            return
        self._status_variables = var_dict

    def on_activate(self):
        """
        Method called when module is activated. If not overridden this method returns an error.
        """
        self.log.error('Please implement and specify the activation method for {0}.'
                       ''.format(self.__class__.__name__))

    def on_deactivate(self):
        """
        Method called when module is deactivated. If not overridden this method returns an error.
        """
        self.log.error('Please implement and specify the deactivation method {0}.'
                       ''.format(self.__class__.__name__))

    def pop_up_message(self, title, message):
        if not isinstance(title, str) or not isinstance(message, str):
            self.log.error('Pop-Up notifications require str type title and message parameters.')
            return
        if self._manager.has_gui:
            self._sigPopUpMessage.emit(title, message)
        else:
            self.log.warning('{0}:\n{1}'.format(title, message))
        return

    def balloon_message(self, title, message, time=None):
        if not isinstance(title, str) or not isinstance(message, str):
            self.log.error('Balloon notifications require str type title and message parameters.')
            return
        if self._manager.has_gui:
            self._sigBalloonMessage.emit(title, message, time)
        else:
            self.log.warning('{0}:\n{1}'.format(title, message))
        return


class LogicBase(Base):
    """

    """
    _threaded = True

    def __init__(self, *args, **kwargs):
        """
        Initialize a logic module.
        """
        super().__init__(*args, **kwargs)
        self.task_lock = Mutex()  # FIXME: What's this? Is it needed?

    # FIXME: exposing this seems like a great opportunity to shoot yourself in the foot.
    #  Is it really needed? If the reference to task_runner is really needed and must be protected
    #  by a Mutex, then the manager should handle safe access. (maybe a manager property?)
    def get_task_runner(self):
        """
        Get a reference to the task runner module registered in the manager.
        If there is no registered task runner, an exception is raised.

        @return object: reference to task runner
        """
        with self._manager.lock:
            if self._manager.task_runner is not None:
                return self._manager.task_runner
            else:
                raise Exception('Tried to access task runner without loading one!')


class GuiBase(Base):
    """This is the GUI base class. It provides functions that every GUI module should have.
    """
    def show(self):
        warnings.warn('Every GUI module needs to re-implement the show() function!')

    def save_window_pos(self, window):
        self._status_variables['__win_pos_x'] = window.pos().x()
        self._status_variables['__win_pos_y'] = window.pos().y()

    def restore_window_pos(self, window):
        if '__win_pos_x' in self._status_variables and '__win_pos_y' in self._status_variables:
            window.move(self._status_variables['__win_pos_x'],
                        self._status_variables['__win_pos_y'])
