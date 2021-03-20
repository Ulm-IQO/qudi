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

import os
import copy
import logging
from abc import abstractmethod
from uuid import uuid4
from fysom import Fysom  # provides a finite state machine
from PySide2 import QtCore

from qudi.core.configoption import MissingOption
from qudi.core.statusvariable import StatusVar
from qudi.core.paths import get_appdata_dir
from qudi.core.config import load, save
from qudi.core.meta import ModuleMeta
from qudi.core.logger import get_logger


def get_module_app_data_path(cls_name, module_base, module_name):
    file_name = 'status-{0}_{1}_{2}.cfg'.format(cls_name, module_base, module_name)
    return os.path.join(get_appdata_dir(), file_name)


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
        self.__uuid = uuid4()

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

    @property
    def uuid(self):
        return self.__uuid

    @QtCore.Slot()
    def activate(self):
        super().activate()

    @QtCore.Slot()
    def deactivate(self):
        super().deactivate()


class Base(QtCore.QObject, metaclass=ModuleMeta):
    """ Base class for all loadable modules

    * Ensure that the program will not die during the load of modules
    * Initialize modules
    * Provides a self identification of the used module
    * per-module logging facility
    * Provides a self de-initialization of the used module
    * Get your own configuration (for save)
    * Get name of status variables
    * Get status variables
    * Reload module data (from saved variables)
    """
    _threaded = False
    _module_meta = dict()  # Will be populated by metaclass

    # FIXME: This __new__ implementation has the sole purpose to circumvent a known PySide2(6) bug.
    #  See https://bugreports.qt.io/browse/PYSIDE-1434 for more details.
    def __new__(cls, *args, **kwargs):
        abstract = getattr(cls, '__abstractmethods__', frozenset())
        if abstract:
            raise TypeError(f'Can\'t instantiate abstract class "{cls.__name__}" '
                            f'with abstract methods {set(abstract)}')
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, qudi_main_weakref, name, config=None, callbacks=None, **kwargs):
        """ Initialise Base instance. Set up its state machine and initialize ConfigOption meta
        attributes from given config.

        @param object self: the object being initialised
        @param str name: unique name for this module instance
        @param dict configuration: parameters from the configuration file
        @param dict callbacks: dict specifying functions to be run on state machine transitions
        """
        super().__init__(**kwargs)

        if config is None:
            config = dict()
        if callbacks is None:
            callbacks = dict()

        # Keep weak reference to qudi main instance
        self.__qudi_main_weakref = qudi_main_weakref

        # Create logger instance for module
        self.__logger = get_logger(f'{self.__module__}.{self.__class__.__name__}')

        # Create a copy of the _module_meta class dict and attach it to the created instance
        self._module_meta = copy.deepcopy(self._module_meta)
        # Add additional meta info to _module_meta dict
        self._module_meta['name'] = name
        self._module_meta['configuration'] = copy.deepcopy(config)

        # set instance attributes according to config_option meta objects
        for attr_name, cfg_opt in self._module_meta['config_options'].items():
            if cfg_opt.name in config:
                cfg_val = copy.deepcopy(config[cfg_opt.name])
            else:
                if cfg_opt.missing == MissingOption.error:
                    raise ValueError(
                        f'Required ConfigOption "{cfg_opt.name}" not given in configuration.\n'
                        f'Configuration is: {config}'
                    )
                msg = f'No ConfigOption >>{cfg_opt.name}<< configured, using default value ' \
                      f'"{cfg_opt.default}" instead.'
                cfg_val = copy.deepcopy(cfg_opt.default)
                if cfg_opt.missing == MissingOption.warn:
                    self.log.warning(msg)
                elif cfg_opt.missing == MissingOption.info:
                    self.log.info(msg)
            if cfg_opt.check(cfg_val):
                cfg_val = cfg_opt.convert(cfg_val)
                if cfg_opt.constructor_function is not None:
                    cfg_val = cfg_opt.constructor_function(self, cfg_val)
                setattr(self, attr_name, cfg_val)

        # set instance attributes according to connector meta objects
        for attr_name, conn in self._module_meta['connectors'].items():
            setattr(self, attr_name, conn)

        # Initialize module FSM
        default_callbacks = {'onbeforeactivate': self.__activation_callback,
                             'ondeactivate'    : self.__deactivation_callback}
        default_callbacks.update(callbacks)
        self.module_state = ModuleStateMachine(parent=self, callbacks=default_callbacks)
        return

    @QtCore.Slot()
    def move_to_main_thread(self):
        """ Method that will move this module into the main/manager thread.
        """
        if QtCore.QThread.currentThread() != self.thread():
            QtCore.QMetaObject.invokeMethod(self,
                                            'move_to_manager_thread',
                                            QtCore.Qt.BlockingQueuedConnection)
        else:
            self.moveToThread(QtCore.QCoreApplication.instance().thread())

    @property
    def module_thread(self):
        """ Read-only property returning the current module QThread instance if the module is
        threaded. Returns None otherwise.

        @return QThread: The thread of this module. If module is not threaded: None
        """
        if self._threaded:
            return self.thread()
        return None

    @property
    def _qudi_main(self):
        qudi_main = self.__qudi_main_weakref()
        if qudi_main is None:
            raise RuntimeError(
                'Unexpected missing qudi main instance. It has either been deleted or garbage '
                'collected.'
            )
        return qudi_main

    def __activation_callback(self, event=None):
        """ Restore status variables before activation and invoke on_activate method.

        @param object event: Fysom event object
        """
        self._load_status_variables()
        self.on_activate()

    def __deactivation_callback(self, event=None):
        """ Invoke on_deactivate method and save status variables afterwards even if deactivation
        fails.

        @param object event: Fysom event object
        """
        try:
            self.on_deactivate()
        except:
            raise
        finally:
            # save status variables even if deactivation failed
            self._dump_status_variables()

    @property
    def log(self):
        """ Returns the module logger instance
        """
        return self.__logger

    @property
    def is_module_threaded(self):
        """ Returns whether the module shall be started in its own thread.
        """
        return self._threaded

    def _load_status_variables(self):
        """ Load status variables from app data directory on disc.
        """
        # Load status variables from app data directory
        class_name = self.__class__.__name__
        name = self._module_meta['name']
        base = self._module_meta['base']
        file_path = get_module_app_data_path(class_name, base, name)
        try:
            variables = load(file_path) if os.path.isfile(file_path) else dict()
        except:
            variables = dict()
            self.log.exception(
                f'Failed to load status variables for module "{class_name}_{base}_{name}".'
            )

        # Set instance attributes according to StatusVar meta objects
        try:
            for attr_name, var in self._module_meta['status_variables'].items():
                value = variables.get(var.name, copy.deepcopy(var.default))
                if var.constructor_function is not None:
                    value = var.constructor_function(self, value)
                setattr(self, attr_name, value)
        except:
            self.log.exception(
                f'Error while settings status variables in module "{class_name}_{base}_{name}".'
            )

    def _dump_status_variables(self):
        """ Dump status variables to app data directory on disc.

        This method can also be used to manually dump status variables independent of the automatic
        dump during module deactivation.
        """
        class_name = self.__class__.__name__
        name = self._module_meta['name']
        base = self._module_meta['base']
        file_path = get_module_app_data_path(class_name, base, name)
        # collect StatusVar values into dictionary
        variables = dict()
        try:
            for attr_name, var in self._module_meta['status_variables'].items():
                if hasattr(self, attr_name):
                    value = getattr(self, attr_name)
                    if not isinstance(value, StatusVar):
                        if var.representer_function is not None:
                            value = var.representer_function(self, value)
                        variables[var.name] = value
        except:
            self.log.exception(
                f'Error while collecting status variables from module "{class_name}_{base}_{name}".'
            )

        # Save to file if any StatusVars have been found
        if variables:
            try:
                save(file_path, variables)
            except:
                self.log.exception(
                    f'Failed to save status variables for module "{class_name}.{base}.{name}".'
                )

    def _send_balloon_message(self, title, message, time=None, icon=None):
        qudi_main = self.__qudi_main_weakref()
        if qudi_main is None:
            return
        if qudi_main.gui is None:
            log = get_logger('balloon-message')
            log.warning('{0}:\n{1}'.format(title, message))
            return
        qudi_main.gui.balloon_message(title, message, time, icon)

    def _send_pop_up_message(self, title, message):
        qudi_main = self.__qudi_main_weakref()
        if qudi_main is None:
            return
        if qudi_main.gui is None:
            log = get_logger('pop-up-message')
            log.warning('{0}:\n{1}'.format(title, message))
            return
        qudi_main.gui.pop_up_message(title, message)

    @abstractmethod
    def on_activate(self):
        """ Method called when module is activated. Must be implemented by actual qudi module.
        """
        raise NotImplementedError(f'Please implement and specify the activation method for '
                                  f'{self.__class__.__name__}.')

    @abstractmethod
    def on_deactivate(self):
        """ Method called when module is deactivated. Must be implemented by actual qudi module.
        """
        raise NotImplementedError(f'Please implement and specify the deactivation method '
                                  f'{self.__class__.__name__}.')


class LogicBase(Base):
    """
    """
    _threaded = True


class GuiBase(Base):
    """This is the GUI base class. It provides functions that every GUI module should have.
    """
    _threaded = False
    __window_geometry = StatusVar(name='_GuiBase__window_geometry', default=None)

    @abstractmethod
    def show(self):
        raise NotImplementedError('Every GUI module needs to implement the show() method!')

    def _save_window_geometry(self, window):
        try:
            self.__window_geometry = window.saveGeometry().toHex().data().decode()
        except:
            self.log.exception('Unable to save window geometry:')
            self.__window_geometry = None

    def _restore_window_geometry(self, window):
        if isinstance(self.__window_geometry, str):
            try:
                encoded = QtCore.QByteArray(self.__window_geometry.encode('utf-8'))
                window.restoreGeometry(QtCore.QByteArray.fromHex(encoded))
            except:
                self.log.exception('Unable to restore window geometry:')
