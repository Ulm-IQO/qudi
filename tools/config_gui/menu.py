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

Copyright (C) 2016 Jan M. Binder jan.binder@uni-ulm.de
"""
import os
from qtpy import QtCore, QtWidgets
import listmods

class ModMenu(QtWidgets.QMenu):

    def __init__(self):
        super().__init__()
        self.logicmenu = QtWidgets.QMenu('Logic')
        self.guimenu = QtWidgets.QMenu('Gui')
        self.hwmenu = QtWidgets.QMenu('Hardware')
        self.addMenu(self.logicmenu)
        self.addMenu(self.guimenu)
        self.addMenu(self.hwmenu)

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

        modules = listmods.find_pyfiles(os.getcwd())
        m, i_s, ie, oe = listmods.check_qudi_modules(modules)

        for k,v in m['hardware'].items():
            self.build_submenu(self.hwmenuitems, k)
            
        for k,v in m['logic'].items():
            self.build_submenu(self.logicmenuitems, k)

        for k,v in m['gui'].items():
            self.build_submenu(self.guimenuitems, k)

    def build_submenu(self, mlist, mod) :
        k_parts = mod.split('.')
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
        mlist['actions'][k_parts[-2] + ' ' + k_parts[-1]] = mlist['menu'].addAction(k_parts[-2] + ' ' + k_parts[-1])
 
