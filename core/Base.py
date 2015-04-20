# -*- coding: utf-8 -*-
"""
Base class for all loadable modules

* Ensure that the program will not die during the load of modules in any case,
  and therefore do nothing!!!
* Initialise modules
* Provides a self identification of the used module
* Output redirection (instead of print)
* Provides a self de-initialization of the used module
* Reload the module with code changes
* Get your own configuration (for save)
* Get name of status variables
* Get status variables
* Reload module data (from saved variables)
* Pyro interconnection
"""

from pyqtgraph.Qt import QtCore
from fysom import Fysom # provides a final state machine
from collections import OrderedDict

class Base(QtCore.QObject, Fysom):
    sigStateChanged = QtCore.Signal(str, object)  #(module name, state change)
    sigLogMessage = QtCore.Signal(object)
    _modclass = 'base'
    _modtype = 'base'

    def __init__(self, manager, name, configuration = {}, callbacks = {}, **kwargs):
        """ Initialise Base class object and set up its state machine.

          @param object self: tthe object being initialised
          @param object manager: the manager object that 
          @param str name: unique name for this object
          @param dict configuration: parameters from the configuration file
          @param dict callbacks: dictionary specifying functions to be run on state machine transitions

        """

        # Qt signal/slot capabilities
        QtCore.QObject.__init__(self)
        
        # State machine definition
        _baseStateList = {
            'initial': 'deactivated',
            'events': [
                {'name': 'activate',    'src': 'deactivated',   'dst': 'idle' },
                {'name': 'deactivate',  'src': 'idle',          'dst': 'deactivated' },
                {'name': 'deactivate',  'src': 'running',       'dst': 'deactivated' },
                {'name': 'run',         'src': 'idle',          'dst': 'running' },
                {'name': 'stop',        'src': 'running',       'dst': 'idle' },
                {'name': 'lock',        'src': 'idle',          'dst': 'locked' },
                {'name': 'lock',        'src': 'running',       'dst': 'locked' },
                {'name': 'block',       'src': 'idle',          'dst': 'blocked' },
                {'name': 'block',       'src': 'running',       'dst': 'blocked' },
                {'name': 'locktoblock', 'src': 'locked',        'dst': 'blocked' },
                {'name': 'unlock',      'src': 'locked',        'dst': 'idle' },
                {'name': 'unblock',     'src': 'blocked',       'dst': 'idle' },
                {'name': 'runlock',     'src': 'locked',        'dst': 'running' },
                {'name': 'runblock',    'src': 'blocked',       'dst': 'running' }
            ],
            'callbacks': callbacks
        }
        # the abbrivations for the event list are the following:
        #   name:   event name,
        #   src:    source state,
        #   dst:    destination state        
        
        
        # Initialise state machine:
        Fysom.__init__(self, _baseStateList)
        
        # add connection base
        self.connector = OrderedDict()
        self.connector['in'] = OrderedDict()
        self.connector['out'] = OrderedDict()

        self._manager = manager
        self._name = name
        self._configuration = configuration

    def activate(self):
        self.logMsg("Please implement this function.", msgType='status')

    def deactivate(self):
        self.logMsg("Please implement this function.", msgType='status')

    def getStatusVariableList(self):
        self.logMsg("Please implement this function.", msgType='status')
        return list()

    def getStatusVariables(self):
        self.logMsg("Please implement this function.", msgType='status')
        return dict()

    # Do not replace these in subclasses

    def getState(self):
        return self.current

    def getConfguration(self):
        return self._configuration

    def logMsg(self, message, **kwargs):
        """Creates a status message method for all child classes.
        
          @param string message: the text of the log message
        """        
        self.sigLogMessage.emit(('{0}.{1}: {2}'.format(self._modclass, self._modtype, message), kwargs))
    
    @staticmethod
    def identify():
        return {moduleclass: _class, moduletype: _modtype}
