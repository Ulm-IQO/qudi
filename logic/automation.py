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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import os
from collections import OrderedDict
from qtpy import QtCore
import pyqtgraph.configfile as configfile

from logic.generic_logic import GenericLogic


class TreeItem:
    def __init__(self, data, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return len(self.itemData)

    def data(self, column):
        try:
            return self.itemData[column]
        except IndexError:
            return None

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)

        return 0


class TreeModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None):
        super(TreeModel, self).__init__(parent)
        self.rootItem = TreeItem(("Title", "Summary"))

    def columnCount(self, parent):
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def data(self, index, role):
        if not index.isValid():
            return None

        if role != QtCore.Qt.DisplayRole:
            return None

        item = index.internalPointer()

        return item.data(index.column())

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.rootItem.data(section)

        return None

    def index(self, row, column, parent):
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
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QtCore.QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def loadExecTree(self, tree, parent=None):
        if not isinstance(parent, TreeItem):
            self.rootItem = TreeItem(("Title", "Summary"))
            self.recursiveLoad(tree, self.rootItem)
        else:
            self.recursiveLoad(tree, parent)

    def recursiveLoad(self, tree, parent):
        for key,value in tree.items():
            if isinstance(value, OrderedDict):
                newchild = TreeItem([key, 'branch'], parent)
                parent.appendChild(newchild)
                self.recursiveLoad(value, newchild)
            else:
                newchild = TreeItem([key, 'leaf'], parent)
                parent.appendChild(newchild)

    def recursiveSave(self, parent):
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
    _in = {'taskrunner': 'TaskRunner'}
    _out = {'automationlogic': 'AutomationLogic'}

    sigRepeat = QtCore.Signal()

    def on_activate(self, e):
        """ Prepare logic module for work.

          @param object e: Fysom state change notification
        """
        self._taskrunner = self.connector['in']['taskrunner']['object']
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

    def on_deactivate(self, e):
        """ Deactivate modeule.

          @param object e: Fysom state change notification
        """
        print(self.model.recursiveSave(self.model.rootItem))


    def loadAutomation(self, path):
        if os.path.isfile(path):
            configdict = configfile.readConfigFile(path)
            self.model.loadExecTree(configdict)
