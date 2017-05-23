# -*- coding: utf-8 -*-
"""
Execution tree for auto measurements

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
import pyqtgraph.configfile as configfile

from collections import OrderedDict
from core.module import Connector
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class TreeItem:
    """ Item in a TreeModel.
    """
    def __init__(self, data, parent=None):
        """ Create TreeItem.

            @param data object: data stored in TreeItem
            @param parent Treeitem: parent of this item
        """
        self.parentItem = parent
        self.itemData = data
        self.childItems = []

    def appendChild(self, item):
        """ Append child node to tree item.

            @param item :
        """
        self.childItems.append(item)

    def child(self, row):
        """ Get child item for specific index

            @param row int: row index for child item

            @return : child item in given row
        """
        return self.childItems[row]

    def childCount(self):
        """ Get number of children.

            @return int: number of children
        """
        return len(self.childItems)

    def columnCount(self):
        """ Return number of columns.

            @return int: number of columns in data
        """
        return len(self.itemData)

    def data(self, column):
        """ Get data from a given column.

            @para, column int: column index

            @return : data stored in column
        """
        try:
            return self.itemData[column]
        except IndexError:
            return None

    def parent(self):
        """ Get parent item.

            @return TreeItem: parent item
        """
        return self.parentItem

    def row(self):
        """ Get our own row index.

            @return int: row index in parent item
        """
        if self.parentItem:
            return self.parentItem.childItems.index(self)

        return 0


class TreeModel(QtCore.QAbstractItemModel):
    """ A tree model for storing TreeItems in a tree structure.
    """
    def __init__(self, parent=None):
        """ Create a TreeModel.

            @param parent TreeModel: parent model
        """
        super(TreeModel, self).__init__(parent)
        self.rootItem = TreeItem(("Title", "Summary"))

    def columnCount(self, parent):
        """ Return number of columns.

            @param parent TreeModel: prent model
        """
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def data(self, index, role):
        """ Retrieve data from model.

            @param index QModelIndex: index of data
            @param role QtRole: role for data
        """
        if not index.isValid():
            return None

        if role != QtCore.Qt.DisplayRole:
            return None

        item = index.internalPointer()

        return item.data(index.column())

    def flags(self, index):
        """ Get flags for item at index.

            @param index QModelIndex: index for item

            @return flags: Qt model flags
        """
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        """ Header for this model.

            @param section QModelIndex: index for header data
            @param orientation: header orientation
            @param role: Qt role for header
        """
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.rootItem.data(section)

        return None

    def index(self, row, column, parent):
        """ Make QModelIndex from row and column number.

            @param row int: row number
            @param column int: column number
            @param parent QAbstractModel: model parent

            @return QModelIndex: index for item at position
        """
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        """ Get parent index for item at index.

            @param index QModelIndex: index for item

            @return QModelIndex: index for parent
        """
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QtCore.QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent):
        """ Return number of rows in model.

            @return int: number of rowa
        """
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def loadExecTree(self, tree, parent=None):
        """ Load a tree from a nested dictionary into the model.

            @param tree dict: dictionary tree to be loaded
            @param parent TreeItem: root item for loaded tree
        """
        if not isinstance(parent, TreeItem):
            self.rootItem = TreeItem(("Title", "Summary"))
            self.recursiveLoad(tree, self.rootItem)
        else:
            self.recursiveLoad(tree, parent)

    def recursiveLoad(self, tree, parent):
        """ Recursively load a tree from a nested dictionary into the model.

            @param tree dict: dictionary for (sub)tree to be loaded
            @param parent TreeItem: root item for loaded (sub)tree
        """
        for key,value in tree.items():
            if isinstance(value, OrderedDict):
                newchild = TreeItem([key, 'branch'], parent)
                parent.appendChild(newchild)
                self.recursiveLoad(value, newchild)
            else:
                newchild = TreeItem([key, 'leaf'], parent)
                parent.appendChild(newchild)

    def recursiveSave(self, parent):
        """ Save TreeModel into nested dict.

            @param parent TreeItem: parent item

            @return dict: dictionary containing tree
        """
        if parent.childCount() > 0:
            retdict = OrderedDict()
            for i in range(parent.childCount()):
                key = parent.child(i).itemData[0]
                retdict[key] = self.recursiveSave(parent.child(i))
            return retdict
        else:
            return parent.itemData[0]

class AutomationLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """
    _modclass = 'AutomationLogic'
    _modtype = 'logic'
    
    taskrunner = Connector(interface_name='TaskRunner')

    sigRepeat = QtCore.Signal()

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._taskrunner = self.get_connector('taskrunner')
        #stuff = "a\txyz\n    b\tx\n    c\ty\n        d\tw\ne\tm\n"
        #tr = OrderedDict([
        #    ('a', OrderedDict([
        #        ('f', OrderedDict([
        #            ('g', 5)
        #        ])),
        #        ('h', 'letrole'),
        #    ])),
        #    ('b', 1),
        #    ('c', 2),
        #    ('d', 3),
        #    ('e', 4)
        #])
        self.model = TreeModel()
        #self.model.loadExecTree(tr)
        self.loadAutomation('auto.cfg')

    def on_deactivate(self):
        """ Deactivate modeule.
        """
        print(self.model.recursiveSave(self.model.rootItem))


    def loadAutomation(self, path):
        """ Load automation config into model.

            @param path str: file path
        """
        if os.path.isfile(path):
            configdict = configfile.readConfigFile(path)
            self.model.loadExecTree(configdict)

