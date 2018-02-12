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

class MenuItem:

    def __init__(self, menu, children=None, actions=None):
        if children is None:
            children = {}
        if actions is None:
            actions = {}
        self.menu = menu
        self.children = children
        self.actions = actions

class ModMenu(QtWidgets.QMenu):
    """ This class represents the module selection menu.
    """

    def __init__(self, modules):
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

        self.hwmenuitems = MenuItem(self.hwmenu)
        self.logicmenuitems = MenuItem(self.logicmenu)
        self.guimenuitems = MenuItem(self.guimenu)

        for module_path, module in sorted(modules['hardware'].items()):
            self.build_submenu(self.hwmenuitems, module_path, module)

        for module_path, module in sorted(modules['logic'].items()):
            self.build_submenu(self.logicmenuitems, module_path, module)

        for module_path, module in sorted(modules['gui'].items()):
            self.build_submenu(self.guimenuitems, module_path, module)

    def build_submenu(self, menu_item, modpath, module) :
        """ Create a submenu from a module list, a module path and a module definition.

            @param dict mlist: module list dict
            @param str modpath: Qudi module path
            @param dict moddef: module definition dict
        """
        k_parts = modpath.split('.')
        child_item = menu_item
        if len(k_parts) > 3:
            for part in k_parts[1:-2]:
                if part in menu_item.children:
                    child_item = menu_item.children[part]
                else:
                    new_menu = menu_item.menu.addMenu(part)
                    menu_item.children[part] = MenuItem(new_menu)
                    child_item = menu_item.children[part]

        action = child_item.menu.addAction(k_parts[-2] + ' ' + k_parts[-1])
        child_item.actions[k_parts[-2] + ' ' + k_parts[-1]] = action
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

