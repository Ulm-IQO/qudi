# -*- coding: utf-8 -*-
"""
This file contains the QuDi module base class.

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

from pyqtgraph.Qt import QtCore
from fysom import Fysom # provides a final state machine
from collections import OrderedDict
import os

class Base(QtCore.QObject, Fysom):
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
    """

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

    def getStatusVariableList(self):
        """Return a list of variable names for variables that can be saved and restored.

          @return list(str): variable names for saving

          Please implement this function when subclassing.
        """
        self.logMsg("Please implement this function.", msgType='warning')
        return list()

    def getStatusVariables(self):
        """ Return a dict of variable names and their content.

          @return dict: variable names and contents.

          Please implement this function when subclassing.
        """
        self.logMsg("Please implement this function.", msgType='warning')
        return dict()

    # Do not replace these in subclasses

    def getState(self):
        """Return the state of the state machine implemented in this class.

          @return str: state of state machine

          Valid return values are: 'deactivated', 'idle', 'running', 'locked', 'blocked'
        """
        return self.current

    def getConfiguration(self):
        """ Return the configration dictionary for this module.

          @return dict: confiuration dictionary

        """
        return self._configuration

    def getConfigDirectory(self):
        """ Return the configuration directory for the manager this module belongs to.

          @return str: path of configuation directory

        """
        return self._manager.configDir

    def logMsg(self, message, **kwargs):
        """Creates a status message method for all child classes.
        
          @param string message: the text of the log message
        """        
        self.sigLogMessage.emit(('{0}.{1}: {2}'.format(self._modclass, self._modtype, message), kwargs))
    
    @staticmethod
    def identify():
        """ Return module id.

          @return dict: id dictionary with modclass and modtype keys.
        """
        return {moduleclass: _class, moduletype: _modtype}
        
    def get_main_dir(self):
        """Returns the absolut path to the directory of the main software.
        
             @return string: path to the main tree of the software
        
        """ 
        mainpath=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
        self.logMsg('Filepath of the main tree was called',importance=0)
        
        return mainpath
 #            print("PAth of Managerfile: ", os.path.abspath(__file__)) 
