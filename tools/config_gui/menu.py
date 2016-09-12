# -*- coding: utf-8 -*-
"""

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
from qtpy import QtCore, QtWidgets

class ModuleObject(QtCore.QObject):

    sigAddModule = QtCore.Signal(object)

    def __init__(self, path, conn_in, conn_out):
        super().__init__()
        self.path = path
        self.conn_in = conn_in
        self.conn_out = conn_out

    def addModule(self):
        self.sigAddModule.emit(self)

class ModMenu(QtWidgets.QMenu):

    def __init__(self, m):
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
        module = ModuleObject(modpath, moddef['in'], moddef['out'])
        action.triggered.connect(module.addModule)
        self.modules.append(module)

    def hasModule(self, modpath):
        return modpath in (x.path for x in self.modules)

    def getModule(self, modpath):
        return next(x for x in self.modules if x.path == modpath)

