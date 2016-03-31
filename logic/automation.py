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

Copyright (C) 2016 Jan M. Binder jan.binder@uni-ulm.de
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
        self.rootItem = ExecTreeItem(None, 'root')

    def _getItem(self, index):
        if not index.isValid():
            return index.internalPointer()
        return self.rootItem

    def data(self, index, role):
        if not index.isValid():
            return None
        if role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            return None
        return self._getItem(index).data(index.column())

    def headerData(self, section, orientation, role = QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.rootItem.data(section)
        return None

    def index(self, row, column, parent = QtCore.QModelIndex()):
        #if not parent.isValid() and parent.column() =! 0:
        if False:
            return QtCore.QModelIndex()
        item = self._getItem(parent).child(row)
        if item is not None:
            return self.createIndex(row, column, item)
        return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        citem = self._getItem(index)
        pitem = citem.parent()
        if pitem is self.rootItem:
            return QModelIndex()
        return self.createIndex(pitem.childNumber(), 0, pitem)

    def rowCount(self, parent = QtCore.QModelIndex()):
        return self._getItem(parent).childCount()

    def columnCount(self, parent = QtCore.QModelIndex()):
        return self.rootItem.columnCount()

    def flags(self, index): 
        if index.isValid():
            return  QtCore.Qt.ItemIsEditable | QtCore.QAbstractItemModel.flags(index)
        return 0
    
    def setData(self, index, value, role=QtCore.Qt.EditRole):
        pass
        

    def setHeaderData(self, section, orientation, value, role=QtCore.Qt.EditRole):
        pass

    def insertColumns(self, position, columns, parent):
        self.beginInsertColumns(parent, position, position + columns - 1)
        success = self.rootItem.insertColumns(position, columns)
        self.endInsertColumns()
        return success

    def removeColumns(self, position, columns, parent):
        self.beginRemoveColumns(parent, position, position + columns - 1)
        success = self.rootItem.removeColumns(position, columns)
        self.endemoveColumns()

        if self.rootItem.columnCount() == 0:
            self.removeRows(0, self.rowCount())
        return success

    def insertRows(self, position, rows, parent):
        pass

    def removeRows(self, position, rows, parent):
        pass

class ExecTreeItem:

    def __init__(self, parent, dat):
        self.parentItem = parent
        self.childItems = []
        self.datastore = dat

    def child(self, number):
        return self.childItems[number]

    def parent(self):
        return self.parentItem

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return 1

    def data(self, column):
        return self.datastore

    def setData(self, column, value):
        if position < 0 or position >= len(self.childItems):
            return False
        self.data = value
        return True

    def insertChildren(self, position, count, columns):
        if position < 0 or position > len(self.childItems):
            return False
        for row in range(count):
            item = ExecTreeItem(self, None)
            self.childItems.insert(position, item)
        return True

    def removeChildren(self, position, count):
        if position < 0 or position + count > len(self.childItems):
            return False
        for row in range(count):
            childItems.pop(position)
        return True

    def insertColumns(self, position, columns):
        return False

    def removeColumns(self, position, columns):
        return False

    def childNumber(self):
        if self.parentItem is not None:
            return self.parentItem.childItems.index(self)
        return 0

class AutomationLogic(GenericLogic):        
    """ Logic module agreggating multiple hardware switches.
    """
    _modclass = 'AutomationLogic'
    _modtype = 'logic'
    _in = {'taskrunner': 'TaskRunner'}
    _out = {'automationlogic': 'AutomationLogic'}
        
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
        self.model = ExecutionTreeModel()

    def deactivation(self, e):
        """ Deactivate modeule.

          @param object e: Fysom state change notification
        """
        pass


