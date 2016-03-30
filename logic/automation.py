# -*- coding: utf-8 -*-
"""
Execution tree for auto measurements

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

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from collections import OrderedDict
from pyqtgraph.Qt import QtCore
import numpy as np


class ExecutionTreeModel(QtCore.QAbstractItemModel):
    """ Hold a tree of different task parts. """
    def __init__(self):
        super().__init__()
        self.rootItem = ExecTreeItem()

    def rowCount(self, parent = QtCore.QModelIndex()):

    def columnCount(self, parent = QtCore.QModelIndex()):

    def flags(self, index): 

    def data(self, index, role):

    def headerData(self, section, orientation, role = QtCore.Qt.DisplayRole):

    def index(self, row, column, parent = QtCore.QModelIndex()):

    def parent(self, index):

class ExecTreeItem():
    def 
    
class ExecutionResultStack:
    """ Hold the results of task execution"""
    def __init__(self, parent):
        self.parentItem = parent
        self.childItem = None

    def childCount(self):

    def columnCount(self):

    def data(self, column)

    def insertChildren(self, position, count, columns):

    def insertColumns(self, position, columns):

    def removeChildren(self, position, count):

    def removeColumns(self, position, columns):

    def childNumber(self):

    def setData(self, column, value):

class AutomationLogic(GenericLogic):        
    """ Logic module agreggating multiple hardware switches.
    """
    _modclass = 'AutomationLogic'
    _modtype = 'logic'
    _in = {'taskrunner': 'TaskRunner'}
    _out = {'automationlogic': 'SimpleDataLogic'}
        
    sigRepeat = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        """ Create logic object
          
          @param object manager: reference to module Manager
          @param str name: unique module name
          @param dict config: configuration in a dict
          @param dict kwargs: additional parameters as a dict
        """
        ## declare actions for state transitions
        state_actions = { 'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

    def activation(self, e):
        """ Prepare logic module for work.

          @param object e: Fysom state change notification
        """
        self._taskrunner = self.connector['in']['taskrunner']['object']
        self.execTree = ExecutionTreeModel()

    def deactivation(self, e):
        """ Deactivate modeule.

          @param object e: Fysom state change notification
        """
        pass


