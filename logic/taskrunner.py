# -*- coding: utf-8 -*-
"""
This file contains the QuDi task runner.

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
from pyqtgraph.Qt import QtCore
from core.util.models import ListTableModel

class TaskListTableModel(ListTableModel):

    def __init__(self):
        super().__init__()
        self.headers = ['Task Name']

    def data(self, index, role):
        """ Get data from model for a given cell. Data can have a role that affects display.

          @param QModelIndex index: cell for which data is requested
          @param ItemDataRole role: role for which data is requested

          @return QVariant: data for given cell and role
        """
        if not index.isValid():
            return None
        elif role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
               return self.storage[index.row()].name
            else:
                return None
        else:
            return Non

class TaskRunner(GenericLogic):
    """A generic logic interface class.
    """
    _modclass = 'TaskRunner'
    _modtype = 'Logic'
    _out = {'runner': 'TaskRunner'}

    def __init__(self, manager, name, configuation, **kwargs):
        """ Initialzize a logic module.

          @param object manager: Manager object that has instantiated this object
          @param str name: unique module name
          @param dict configuration: module configuration as a dict
          @param dict kwargs: dict of additional arguments
        """
        callbacks = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, configuation, callbacks, **kwargs)

    def activation(self, e):
        self.model = TaskListTableModel()
        self.model.rowsInserted.connect(self.modelChanged)
        self.model.rowsRemoved.connect(self.modelChanged)
        config = self.getConfiguration()
        print(config)

    def deactivation(self, e):
        pass

    @QtCore.pyqtSlot(QtCore.QModelIndex, int, int)
    def modelChanged(self, parent, first, last):
        print('Inserted into task list: {} {}'.format(first, last))

