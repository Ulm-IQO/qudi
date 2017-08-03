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
import qtpy
from qtpy import QtCore
from .FysomAdapter import Fysom  # provides a final state machine
from collections import OrderedDict

import os
import sys


class Base(QtCore.QObject, Fysom):
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

    sigStateChanged = QtCore.Signal(object)  # (module name, state change)
    _modclass = 'base'
    _modtype = 'base'
    _in = dict() # legacy
    _connectors = dict()

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
            'onactivate': lambda e: self.on_activate(),
            'ondeactivate': lambda e: self.on_deactivate()
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
        if qtpy.PYQT4 or qtpy.PYSIDE:
            QtCore.QObject.__init__(self)
            Fysom.__init__(self, _baseStateList)
        else:
            super().__init__(cfg=_baseStateList, **kwargs)

        # add connection base
        self.connectors = OrderedDict()
        for con in self._connectors:
            self.connectors[con] = OrderedDict()
            self.connectors[con]['class'] = self._connectors[con]
            self.connectors[con]['object'] = None
        # legacy (deprecated soon)
        for con in self._in:
            self.connectors[con] = OrderedDict()
            self.connectors[con]['class'] = self._in[con]
            self.connectors[con]['object'] = None

        self._manager = manager
        self._name = name
        self._configuration = config
        self._statusVariables = OrderedDict()
        # self.sigStateChanged.connect(lambda x: print(x.event, x.fsm._name))

    def __getattr__(self, name):
        """
        Attribute getter.

        We'll reimplement it here because otherwise only __getattr__ of the
        first base class (QObject) is called and the second base class is
        never looked up.
        Here we look up the first base class first and if the attribute is
        not found, we'll look into the second base class.
        """
        try:
            return QtCore.QObject.__getattr__(self, name)
        except AttributeError:
            pass
        return Fysom.__getattr__(self, name)

    @property
    def log(self):
        """
        Returns a logger object
        """
        return logging.getLogger("{0}.{1}".format(
            self.__module__, self.__class__.__name__))

    @QtCore.Slot(result=bool)
    def _wrap_activation(self):
        self.log.debug('Activation in thread {0}'.format(QtCore.QThread.currentThreadId()))
        try:
            self.activate()
        except:
            self.log.exception('Error during activation')
            return False
        return True

    @QtCore.Slot(result=bool)
    def _wrap_deactivation(self):
        self.log.debug('Deactivation in thread {0}'.format(QtCore.QThread.currentThreadId()))
        try:
            self.deactivate()
        except:
            self.log.exception('Error during activation:')
            return False
        return True

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

