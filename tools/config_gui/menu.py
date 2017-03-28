# -*- coding: utf-8 -*-
"""

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
from qtpy import QtCore, QtWidgets

class ModuleObject(QtCore.QObject):
    """ This class represents a Qudi module.
    """

    sigAddModule = QtCore.Signal(object)

    def __init__(self, path, conn):
        super().__init__()
        self.path = path
        self.conn = conn

    def addModule(self):
        """ Add this module to the config.
        """
        self.sigAddModule.emit(self)

class ModMenu(QtWidgets.QMenu):
    """ This class represents the module selection menu.
    """

    def __init__(self, m):
        """ Create new menu from module tree.

            @param dict m: module tree
        """
        super().__init__()

        self.modules = []

        self.hwmenu = QtWidgets.QMenu('Hardware')
        self.logicmenu = QtWidgets.QMenu('Logic')
        self.guimenu = QtWidgets.QMenu('Gui')
        self.addMenu(self.hwmenu)
        self.addMenu(self.logicmenu)
        self.addMenu(self.guimenu)

        self.hwmenuitems = {
            'menu': self.hwmenu,
            'children': {},
            'actions': {}
        }
        self.logicmenuitems = {
            'menu': self.logicmenu,
            'children': {},
            'actions': {}
        }
        self.guimenuitems = {
            'menu': self.guimenu,
            'children': {},
            'actions': {}
        }

        for k,v in sorted(m['hardware'].items()):
            self.build_submenu(self.hwmenuitems, k, v)

        for k,v in sorted(m['logic'].items()):
            self.build_submenu(self.logicmenuitems, k, v)

        for k,v in sorted(m['gui'].items()):
            self.build_submenu(self.guimenuitems, k, v)

    def build_submenu(self, mlist, modpath, moddef) :
        """ Create a submenu from a module list, a module path and a module definition.

            @param dict mlist: module list dict
            @param str modpath: Qudi module path
            @param dict moddef: module definition dict
        """
        k_parts = modpath.split('.')
        if len(k_parts) > 3:
            for part in k_parts[1:-2]:
                if part in mlist['children']:
                    mlist = mlist['children'][part]
                else:
                    menu = mlist['menu'].addMenu(part)
                    mlist['children'][part] = {
                        'menu': menu,
                        'children': {},
                        'actions': {}
                        }
                    mlist = mlist['children'][part]
        action = mlist['menu'].addAction(k_parts[-2] + ' ' + k_parts[-1])
        mlist['actions'][k_parts[-2] + ' ' + k_parts[-1]] = action
        module = ModuleObject(modpath, moddef['conn'])
        action.triggered.connect(module.addModule)
        self.modules.append(module)

    def hasModule(self, modpath):
        """ Return whther module with given path is present
        
            @param str modpath: Qudi module path

            @return bool: wether a module has the given path
        """
        return modpath in (x.path for x in self.modules)

    def getModule(self, modpath):
        """ Get module corresponding to module path.

            @prarm str modpath: Qudi module path

            @return ModuleObject: module object
        """
        return next(x for x in self.modules if x.path == modpath)

