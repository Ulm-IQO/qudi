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
from .configoption import MissingOption, ConfigOption
from .connector import Connector
from .statusvariable import StatusVar
from core.util.mutex import Mutex
from .config import load, save

import os


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


class Base(QtCore.QObject):
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
    _module_meta = {'base': 'hardware'}  # can be overwritten by subclasses of Base

    _sigPopUpMessage = QtCore.Signal(str, str)
    _sigBalloonMessage = QtCore.Signal(str, str, object)

    def __init__(self, manager, name, config=None, callbacks=None, **kwargs):
        """
        Initialise Base class object and set up its state machine.

        @param object self: the object being initialised
        @param object manager: the manager object that
        @param str name: unique name for this module instance
        @param dict configuration: parameters from the configuration file
        @param dict callbacks: dict specifying functions to be run on state machine transitions
        """
        super().__init__(**kwargs)

        # add module meta objects to avoid cluttering namespace
        self._module_meta = copy.deepcopy(self._module_meta)
        self._module_meta['name'] = name
        self._module_meta['configuration'] = copy.deepcopy(config)
        # Collect meta objects of class and create copies for this instance
        connectors = dict()
        status_vars = dict()
        config_opt = dict()
        for cls in reversed(self.__class__.mro()):
            # Those classes don't have the meta objects we are searching for
            if not issubclass(cls, Base):
                continue
            for attr_name, attr in vars(cls).items():
                if isinstance(attr, Connector):
                    connectors[attr_name] = attr.copy() if attr.name else attr.copy(name=attr_name)
                elif isinstance(attr, StatusVar):
                    status_vars[attr_name] = attr.copy() if attr.name else attr.copy(name=attr_name)
                elif isinstance(attr, ConfigOption):
                    config_opt[attr_name] = attr.copy() if attr.name else attr.copy(name=attr_name)
        self._module_meta['connectors'] = connectors
        self._module_meta['status_variables'] = status_vars
        self._module_meta['config_options'] = config_opt

        if config is None:
            config = dict()
        if callbacks is None:
            callbacks = dict()

        default_callbacks = {'onbeforeactivate': self.__activation_callback,
                             'ondeactivate': self.__deactivation_callback}
        default_callbacks.update(callbacks)
        self.module_state = ModuleStateMachine(parent=self, callbacks=default_callbacks)

        # set instance attributes according to config_option meta objects
        for attr_name, cfg_opt in self._module_meta.get('config_options', dict()).items():
            if cfg_opt.name in config:
                cfg_val = config[cfg_opt.name]
            else:
                if cfg_opt.missing == MissingOption.error:
                    raise Exception('Required variable >>{0}<< not given in configuration.\n'
                                    'Configuration is: {1}'.format(cfg_opt.name, config))
                msg = 'No variable >>{0}<< configured, using default value "{1}" instead.'.format(
                    cfg_opt.name, cfg_opt.default)
                cfg_val = cfg_opt.default
                if cfg_opt.missing == MissingOption.warn:
                    self.log.warning(msg)
                elif cfg_opt.missing == MissingOption.info:
                    self.log.info(msg)
            if cfg_opt.check(cfg_val):
                converted_val = cfg_opt.convert(cfg_val)
                if cfg_opt.constructor_function is None:
                    setattr(self, attr_name, converted_val)
                else:
                    setattr(self, attr_name, cfg_opt.constructor_function(self, converted_val))

        # set instance attributes according to connector meta objects
        for attr_name, conn in self._module_meta.get('connectors', dict()).items():
            setattr(self, attr_name, conn)

        self._manager = manager
        return

    @QtCore.Slot()
    def move_to_manager_thread(self):
        """ Method that will move this module into the main/manager thread.
        """
        if QtCore.QThread.currentThread() != self.thread():
            QtCore.QMetaObject.invokeMethod(self,
                                            'move_to_manager_thread',
                                            QtCore.Qt.BlockingQueuedConnection)
        else:
            self.moveToThread(self._manager.thread())

    @property
    def module_thread(self):
        """ Read-only property returning the current module QThread instance if the module is
        threaded. Returns None otherwise.

        @return QThread: The thread of this module. If module is not threaded: None
        """
        if self._threaded:
            return self.thread()
        return None

    def __activation_callback(self, event=None):
        """
        Restore status variables before activation and invoke on_activate method.

        @param object event: Fysom event object
        """
        # Load status variables from disk only if this module is one of gui, logic or hardware base
        file_path = self.module_status_file_path
        if file_path is not None:
            try:
                variables = load(file_path) if os.path.isfile(file_path) else dict()
            except:
                self.log.exception('Failed to load status variables for module "{0}_{1}_{2}".'
                                   ''.format(self.__class__.__name__,
                                             self._module_meta['base'],
                                             self._module_meta['name']))
                variables = dict()

            # add StatusVar values to instance attributes
            for attr_name, var in self._module_meta['status_variables'].items():
                value = variables.get(var.name, var.default)
                if var.constructor_function is None:
                    setattr(self, attr_name, value)
                else:
                    setattr(self, attr_name, var.constructor_function(self, value))
        # activate
        self.on_activate()

    def __deactivation_callback(self, event=None):
        """
        Invoke on_deactivate method and save status variables afterwards even if deactivation fails.

        @param object event: Fysom event object
        """
        try:
            self.on_deactivate()
        except:
            raise
        finally:
            # save status vars even if deactivation failed
            file_path = self.module_status_file_path
            if file_path is not None:
                # collect StatusVar values into dictionary
                variables = dict()
                for attr_name, var in self._module_meta['status_variables'].items():
                    if hasattr(self, attr_name):
                        value = getattr(self, attr_name)
                        if var.representer_function is None:
                            variables[var.name] = value
                        else:
                            variables[var.name] = var.representer_function(self, value)
                # Save to file if any StatusVars have been found
                if variables:
                    try:
                        save(file_path, variables)
                    except:
                        self.log.exception('Failed to save status variables for module '
                                           '"{0}.{1}.{2}".'.format(self.__class__.__name__,
                                                                   self._module_meta['base'],
                                                                   self._module_meta['name']))

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
    def module_status_file_path(self):
        if self._module_meta.get('base', None) not in ('gui', 'logic', 'hardware'):
            return None
        file_name = 'status-{0}_{1}_{2}.cfg'.format(self.__class__.__name__,
                                                    self._module_meta['base'],
                                                    self._module_meta['name'])
        return os.path.join(self._manager.get_status_dir(), file_name)

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


class LogicBase(Base):
    """
    """
    _threaded = True
    _module_meta = {'base': 'logic'}  # can be overwritten by subclasses

    def __init__(self, *args, **kwargs):
        """
        Initialize a logic module.
        """
        super().__init__(*args, **kwargs)
        self._module_meta['base'] = 'logic'

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
    _threaded = False
    _module_meta = {'base': 'gui'}  # can be overwritten by subclasses

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add windows position StatusVar to module
        stat_var_name = '_{0}__win_pos'.format(self.__class__.__name__)
        if stat_var_name not in self._module_meta['status_variables']:
            stat_var = StatusVar(stat_var_name, None)
            self._module_meta['status_variables'][stat_var_name] = stat_var
            setattr(self, stat_var_name, stat_var)

    def show(self):
        self.log.error('Every GUI module needs to implement the show() method!')

    def _save_window_pos(self, window):
        stat_var_name = '_{0}__win_pos'.format(self.__class__.__name__)
        if hasattr(self, stat_var_name):
            setattr(self, stat_var_name, (window.pos().x(), window.pos().y()))

    def _restore_window_pos(self, window):
        stat_var_name = '_{0}__win_pos'.format(self.__class__.__name__)
        win_pos = getattr(self, stat_var_name, None)
        if win_pos is not None:
            window.move(*win_pos)
