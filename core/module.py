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
from fysom import Fysom  # provides a final state machine
from collections import OrderedDict

from qtpy import QtCore
from .meta import ModuleMeta
from .configoption import MissingOption
from .connector import Connector


class ModuleStateMachine(QtCore.QObject, Fysom):
    """
    FIXME
    """
    # do not copy declaration of trigger(self, event, *args, **kwargs), just apply Slot decorator
    trigger = QtCore.Slot(str, result=bool)(Fysom.trigger)

    # signals
    sigStateChanged = QtCore.Signal(object)  # (module name, state change)

    def __init__(self, parent, callbacks=None, **kwargs):
        self._parent = parent
        if callbacks is None:
            callbacks = {}

        # State machine definition
        # the abbreviations for the event list are the following:
        #   name:   event name,
        #   src:    source state,
        #   dst:    destination state
        _baseStateList = {
            'initial': 'deactivated',
            'events': [
                {'name': 'activate', 'src': 'deactivated', 'dst': 'idle'},
                {'name': 'deactivate', 'src': 'idle', 'dst': 'deactivated'},
                {'name': 'deactivate', 'src': 'running', 'dst': 'deactivated'},
                {'name': 'deactivate', 'src': 'locked', 'dst': 'deactivated'},
                {'name': 'run', 'src': 'idle', 'dst': 'running'},
                {'name': 'stop', 'src': 'running', 'dst': 'idle'},
                {'name': 'lock', 'src': 'idle', 'dst': 'locked'},
                {'name': 'lock', 'src': 'running', 'dst': 'locked'},
                {'name': 'unlock', 'src': 'locked', 'dst': 'idle'},
                {'name': 'runlock', 'src': 'locked', 'dst': 'running'},
            ],
            'callbacks': callbacks
        }

        # Initialise state machine:
        super().__init__(parent=parent, cfg=_baseStateList, **kwargs)

    def __call__(self):
        """
        Returns the current state.
        """
        return self.current

    def _build_event(self, event):
        """
        Overrides fysom _build_event to wrap on_activate and on_deactivate to
        catch and log exceptios.
        """
        base_event = super()._build_event(event)
        if event in ['activate', 'deactivate']:
            if event == 'activate':
                noun = 'activation'
            else:
                noun = 'deactivation'

            def wrap_event(*args, **kwargs):
                self._parent.log.debug('{0} in thread {1}'.format(
                    noun.capitalize(),
                    QtCore.QThread.currentThreadId()))
                try:
                    base_event(*args, **kwargs)
                except:
                    self._parent.log.exception('Error during {0}'.format(noun))
                    return False
                return True

            return wrap_event
        else:
            return base_event

    def onchangestate(self, e):
        """ Fysom callback for state transition.

        @param object e: Fysom state transition description
        """
        self.sigStateChanged.emit(e)


class BaseMixin(metaclass=ModuleMeta):
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

    def __init__(self, manager, name, config=None, callbacks=None, **kwargs):
        """ Initialise Base class object and set up its state machine.

          @param object self: the object being initialised
          @param object manager: the manager object that
          @param str name: unique name for this object
          @param dict configuration: parameters from the configuration file
          @param dict callbacks: dictionary specifying functions to be run
                                 on state machine transitions

        """
        super().__init__(**kwargs)

        if config is None:
            config = {}
        if callbacks is None:
            callbacks = {}

        default_callbacks = {
            'onactivate': self.__load_status_vars_activate,
            'on_before_deactivate': self.__call_deactivate_callback,
            'ondeactivate': self.__save_status_vars_deactivate
            }
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
                    raise Exception(
                        'Required variable >> {0} << not given in configuration.\n'
                        'Configuration is: {1}'.format(opt.name, config))
                elif opt.missing == MissingOption.warn:
                    self.log.warning(
                        'No variable >> {0} << configured, using default value {1} instead.'
                         ''.format(opt.name, opt.default))
                elif opt.missing == MissingOption.info:
                    self.log.info(
                        'No variable >> {0} << configured, using default value {1} instead.'
                         ''.format(opt.name, opt.default))
                cfg_val = opt.default
            if opt.check(cfg_val):
                converted_val = opt.convert(cfg_val)
                if opt.constructor_function is None:
                    setattr(self, opt.var_name, converted_val)
                else:
                    setattr(self, opt.var_name, opt.constructor_function(self, converted_val))

        self._manager = manager
        self._name = name
        self._configuration = config
        self._statusVariables = OrderedDict()
        self._callbacks_before_deactivate = []

    def __load_status_vars_activate(self, event):
        """ Restore status variables before activation.

            @param e: Fysom event
        """
        # add status vars
        for vname, var in self._stat_vars.items():
            sv = self._statusVariables
            svar = sv[var.name] if var.name in sv else var.default

            if var.constructor_function is None:
                setattr(self, var.var_name, svar)
            else:
                setattr(self, var.var_name, var.constructor_function(self, svar))

        # activate
        self.on_activate()

    def __save_status_vars_deactivate(self, event):
        """ Save status variables after deactivation.

            @param e: Fysom event
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
                        self._statusVariables[var.name] = getattr(self, var.var_name)
                    else:
                        self._statusVariables[var.name] = var.representer_function(
                                                            self,
                                                            getattr(self, var.var_name))

    def add_deactivation_callback(self, cb):
        """ Method to properly add a callback that will be called before deactivation """
        self._callbacks_before_deactivate.append(cb)

    def __call_deactivate_callback(self, event):
        """ Method called before deactivation to call cleanup callbacks of the module"""
        for cb in self._callbacks_before_deactivate:
            cb()

    @property
    def log(self):
        """
        Returns a logger object
        """
        return logging.getLogger("{0}.{1}".format(
            self.__module__, self.__class__.__name__))

    @property
    def is_module_threaded(self):
        """
        Returns whether the module shall be started in a thread.
        """
        return self._threaded

    def on_activate(self):
        """ Method called when module is activated. If not overridden
            this method returns an error.

        """
        self.log.error('Please implement and specify the activation method '
                         'for {0}.'.format(self.__class__.__name__))

    def on_deactivate(self):
        """ Method called when module is deactivated. If not overridden
            this method returns an error.
        """
        self.log.error('Please implement and specify the deactivation '
                         'method {0}.'.format(self.__class__.__name__))

    def getStatusVariables(self):
        """ Return a dict of variable names and their content representing
            the module state for saving.

        @return dict: variable names and contents.

        @deprecated declare and use StatusVar class variables directly
        """
        warnings.warn('getStatusVariables is deprecated and will be removed in future versions. Use '
                      'StatusVar instead.', DeprecationWarning)
        return self._statusVariables

    def setStatusVariables(self, variableDict):
        """ Give a module a dict of variable names and their content
            representing the module state.

          @param OrderedDict dict: variable names and contents.

          @deprecated declare and use StatusVar class variables
        """
        warnings.warn('setStatusVariables is deprecated and will be removed in future versions. Use '
                      'StatusVar instead.', DeprecationWarning)
        if not isinstance(variableDict, (dict, OrderedDict)):
            self.log.error('Did not pass a dict or OrderedDict to '
                           'setStatusVariables in {0}.'.format(
                               self.__class__.__name__))
            return
        self._statusVariables = variableDict

    def getConfiguration(self):
        """ Return the configration dictionary for this module.

          @return dict: confiuration dictionary
          @deprecated declare and use ConfigOption class variables directly
        """
        warnings.warn('getConfiguration is deprecated and will be removed in future versions. Use '
                      'ConfigOptions instead.', DeprecationWarning)
        return self._configuration

    def get_connector(self, connector_name):
        """ Return module connected to the given named connector.
          @param str connector_name: name of the connector

          @return obj: module that is connected to the named connector
          @deprecated instead of get_connector(connector_name) just use connector_name(). Enabled by using Connector
                objects as class variables
        """
        warnings.warn('get_connector is deprecated and will be removed in future versions. Use '
                      'Connector() callable instead.', DeprecationWarning)
        if connector_name in self.connectors:
            connector = self.connectors[connector_name]
            # new style legacy connector
            if isinstance(connector, Connector):
                return connector()
            # legacy legacy connector
            elif isinstance(connector, dict):
                obj = connector['object']
                if obj is None:
                    raise TypeError('No module connected')
                return obj
            else:
                raise Exception(
                    'Entry {0} in connector dict is of wrong type {1}.'
                    ''.format(connector_name, type(connector)))
        else:
            raise Exception(
                'Connector {0} does not exist.'
                ''.format(connector_name))


class Base(QtCore.QObject, BaseMixin):
    pass
