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

import copy
import logging
import os
import qtpy
import sys
from fysom import Fysom  # provides a final state machine
from collections import OrderedDict
from enum import Enum
from qtpy import QtCore


class StatusVar:
    """ This class defines a status variable that is loaded before activation
        and saved after deactivation.
    """
    def __init__(self, name=None, default=None, *, var_name=None):
        self.var_name = var_name
        if name is None:
            self.name = var_name
        else:
            self.name = name

        self.default = default

    def copy(self, **kwargs):
        """ Create a new instance of StatusVar with copied and updated values.

            @param kwargs: Additional or overridden parameters for the constructor of this class
        """
        newargs = {}
        newargs['name'] = copy.copy(self.name)
        newargs['default'] = copy.copy(self.default)
        newargs['var_name'] = copy.copy(self.var_name)
        newargs.update(kwargs)
        return StatusVar(**newargs)

    def type_check(self, check_this):
        return True

class MissingOption(Enum):
    """ Representation for missing ConfigOption """
    error = -3
    warn = -2
    info = -1
    nothing = 0

class ConfigOption:
    """ This class represents a configuration entry in the config file that is loaded before
        module initalisation.
    """
    def __init__(self, name=None, default=None, *, var_name=None, missing='nothing'):
        """ Create a ConfigOption object.

            @param name
            @param default
            @param var_name
            @param missing
        """
        self.missing = MissingOption[missing]
        self.var_name = var_name
        if name is None:
            self.name = var_name
        else:
            self.name = name

        self.default = default

    def copy(self, **kwargs):
        """ Create a new instance of ConfigOption with copied values and update

            @param kwargs: extra arguments or overrides for the constructor of this class
        """
        newargs = {}
        newargs['name'] = copy.copy(self.name)
        newargs['default'] = copy.copy(self.default)
        newargs['var_name'] = copy.copy(self.var_name)
        newargs['missing'] = copy.copy(self.missing.name)
        newargs.update(kwargs)
        return ConfigOption(**newargs)


class Connector:
    """ A connector where another module can be connected """

    def __init__(self, *, name=None, interface_name=None):
        """
            @param name: name of the connector
            @param interface_name: name of the interface for this connector
        """
        self.name = name
        self.ifname = interface_name
        self.obj = None

    #def __repr__(self):
    #    return '<{0}: name={1}, interface={2}, object={3}>'.format(self.__class__, self.name, self.ifname, self.obj)

    def copy(self, **kwargs):
        """ Create a new instance of Connector with copied values and update """
        newargs = {}
        newargs['name'] = copy.copy(self.name)
        newargs['interface_name'] = copy.copy(self.ifname)
        newargs.update(kwargs)
        return Connector(**newargs)


class ModuleMeta(type(QtCore.QObject)):
    """
    Metaclass for Qudi modules
    """

    def __new__(mcs, name, bases, attrs):
        """
        Collect declared Connectors, ConfigOptions and StatusVars into dictionaries.

            @param mcs: class
            @param name: name of class
            @param bases: list of base classes of class
            @param attrs: attributes of class

            @return: new class with collected connectors
        """

        # collect meta info in dicts
        connectors = OrderedDict()
        config_options = OrderedDict()
        status_vars = OrderedDict()

        # Accumulate Connector, ConfigOption and StatusVar info from parent classes
        for base in reversed(bases):
            if hasattr(base, '_connectors'):
                connectors.update(copy.deepcopy(base._connectors))
            if hasattr(base, '_config_options'):
                config_options.update(copy.deepcopy(base._config_options))
            if hasattr(base, '_stat_var'):
                status_vars.update(copy.deepcopy(base._stat_var))

        # Collect this classes Connector and ConfigOption and StatusVar into dictionaries
        for key, value in attrs.items():
            if isinstance(value, Connector):
                connectors[key] = value.copy(name=key)
            elif isinstance(value, ConfigOption):
                config_options[key] = value.copy(var_name=key)
            elif isinstance(value, StatusVar):
                status_vars[key] = value.copy(var_name=key)

        attrs.update(connectors)
        attrs.update(config_options)
        attrs.update(status_vars)

        # create a new class with the new dictionaries
        new_class = super().__new__(mcs, name, bases, attrs)
        new_class._conn = connectors
        new_class._config_options = config_options
        new_class._stat_vars = status_vars

        return new_class


class BaseMixin(Fysom, metaclass=ModuleMeta):
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

    _modclass = 'base'
    _modtype = 'base'
    _connectors = dict()

    # do not copy declaration of trigger(self, event, *args, **kwargs), just apply Slot decorator
    trigger = QtCore.Slot(str, result=bool)(Fysom.trigger)

    # signals
    sigStateChanged = QtCore.Signal(object)  # (module name, state change)

    def __init__(self, manager, name, config=None, callbacks=None, **kwargs):
        """ Initialise Base class object and set up its state machine.

          @param object self: tthe object being initialised
          @param object manager: the manager object that
          @param str name: unique name for this object
          @param dict configuration: parameters from the configuration file
          @param dict callbacks: dictionary specifying functions to be run
                                 on state machine transitions

        """
        if config is None:
            config = {}
        if callbacks is None:
            callbacks = {}

        default_callbacks = {
            'onactivate': self.__load_status_vars_activate,
            'ondeactivate': self.__save_status_vars_deactivate
            }
        default_callbacks.update(callbacks)

        # State machine definition
        # the abbrivations for the event list are the following:
        #   name:   event name,
        #   src:    source state,
        #   dst:    destination state
        _baseStateList = {
            'initial': 'deactivated',
            'events': [
                {'name': 'activate',    'src': 'deactivated',   'dst': 'idle'},
                {'name': 'deactivate',  'src': 'idle',          'dst': 'deactivated'},
                {'name': 'deactivate',  'src': 'running',       'dst': 'deactivated'},
                {'name': 'deactivate',  'src': 'locked',       'dst': 'deactivated'},
                {'name': 'run',         'src': 'idle',          'dst': 'running'},
                {'name': 'stop',        'src': 'running',       'dst': 'idle'},
                {'name': 'lock',        'src': 'idle',          'dst': 'locked'},
                {'name': 'lock',        'src': 'running',       'dst': 'locked'},
                {'name': 'unlock',      'src': 'locked',        'dst': 'idle'},
                {'name': 'runlock',     'src': 'locked',        'dst': 'running'},
            ],
            'callbacks': default_callbacks
        }

        # Initialise state machine:
        super().__init__(cfg=_baseStateList, **kwargs)

        # add connectors
        self.connectors = OrderedDict()
        for cname, con in self._conn.items():
            self.connectors[con.name] = OrderedDict()
            self.connectors[con.name]['class'] = con.ifname
            self.connectors[con.name]['object'] = None

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
            setattr(self, opt.var_name, cfg_val)

        # add status var defaults
        for vname, var in self._stat_vars.items():
            setattr(self, var.var_name, var.default)

        self._manager = manager
        self._name = name
        self._configuration = config
        self._statusVariables = OrderedDict()
        # self.sigStateChanged.connect(lambda x: print(x.event, x.fsm._name))

    def __load_status_vars_activate(self, event):
        """ Restore status variables before activation.

            @param e: Fysom event
        """
        # add status vars
        for vname, var in self._stat_vars.items():
            if var.name in self._statusVariables and var.type_check(self._statusVariables[var.name]):
                setattr(self, var.var_name, self._statusVariables[var.name])
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
                    self._statusVariables[var.name] = getattr(self, var.var_name)

    def _build_event(self, event):
        """
        Overrides fysom _build_event to wrap on_activate and on_deactivate to
        catch and log exceptios.
        """
        base_event = super()._build_event(event)
        if (event in ['activate', 'deactivate']):
            if (event == 'activate'):
                noun = 'activation'
            else:
                noun = 'deactivation'
            def wrap_event(*args, **kwargs):
                self.log.debug('{0} in thread {1}'.format(
                    noun.capitalize(),
                    QtCore.QThread.currentThreadId()))
                try:
                    base_event(*args, **kwargs)
                except:
                    self.log.exception('Error during {0}'.format(noun))
                    return False
                return True
            return wrap_event
        else:
            return base_event

    @property
    def log(self):
        """
        Returns a logger object
        """
        return logging.getLogger("{0}.{1}".format(
            self.__module__, self.__class__.__name__))

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

    # Do not replace these in subclasses
    def onchangestate(self, e):
        """ Fysom callback for state transition.

        @param object e: Fysom state transition description
        """
        self.sigStateChanged.emit(e)

    def getStatusVariables(self):
        """ Return a dict of variable names and their content representing
            the module state for saving.

        @return dict: variable names and contents.

        """
        return self._statusVariables

    def setStatusVariables(self, variableDict):
        """ Give a module a dict of variable names and their content
            representing the module state.

          @param OrderedDict dict: variable names and contents.

        """
        if not isinstance(variableDict, (dict, OrderedDict)):
            self.log.error('Did not pass a dict or OrderedDict to '
                           'setStatusVariables in {0}.'.format(
                               self.__class__.__name__))
            return
        self._statusVariables = variableDict

    def getState(self):
        """Return the state of the state machine implemented in this class.

          @return str: state of state machine

          Valid return values are: 'deactivated', 'idle', 'running', 'locked',
                                   'blocked'
        """
        return self.current

    def getConfiguration(self):
        """ Return the configration dictionary for this module.

          @return dict: confiuration dictionary

        """
        return self._configuration

    def getConfigDirectory(self):
        """ Return the configuration directory for the manager this module
            belongs to.

          @return str: path of configuration directory

        """
        return self._manager.configDir

    @staticmethod
    def identify():
        """ Return module id.

          @return dict: id dictionary with modclass and modtype keys.
        """
        return {moduleclass: _class, moduletype: _modtype}

    def get_main_dir(self):
        """ Returns the absolut path to the directory of the main software.

             @return string: path to the main tree of the software

        """
        mainpath = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".."))
        return mainpath

    def get_home_dir(self):
        """ Returns the path to the home directory, which should definitely
            exist.
            @return string: absolute path to the home directory
        """
        return os.path.abspath(os.path.expanduser('~'))

    def get_connector(self, connector_name):
        """ Return module connected to the given named connector.
          @param str connector_name: name of the connector

          @return obj: module that is connected to the named connector
        """
        obj = self.connectors[connector_name]['object']
        if (obj is None):
            raise TypeError('No module connected')
        return obj


class Base(QtCore.QObject, BaseMixin):
    pass
