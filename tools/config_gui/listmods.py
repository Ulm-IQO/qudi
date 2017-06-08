# -*- coding: utf-8 -*-
"""
List types of Qudi python files and their object properties

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
import sys
import fnmatch
import inspect
import importlib

from qtpy import QtCore, QtWidgets

class Module(QtCore.QObject):
    """ This class represents a Qudi module.
    """

    sigAddModule = QtCore.Signal(object)

    def __init__(self, path, name, ref, connections, interfaces, options, stat_vars):
        super().__init__()
        self.path = path
        if path.startswith('hardware'):
            self.base = 'hardware'
        elif path.startswith('logic'):
            self.base = 'logic'
        elif path.startswith('gui'):
            self.base = 'gui'
        else:
            self.base = ''
        self.connections = connections
        self.interfaces = interfaces
        self.reference = ref
        self.options = options
        self.stat_vars = stat_vars

    def addModule(self):
        """ Add this module to the config.
        """
        self.sigAddModule.emit(self)

    def print_connectors(self):
        if len(self.connections) > 0:
            print('  IN:')
            for cname, conn in self.connections.items():
                print('    {}: {}'.format(conn.name, conn.ifname))
            print('')

    def print_interfaces(self):
        print('  IF:')
        for interface in self.interfaces:
            print('    {}'.format(interface))
        print('')

    def print_options(self):
        if len(self.options) > 0:
            print('  OPT:')
            for oname, opt in self.options.items():
                print('    {}: {}'.format(opt.name, opt.default))
            print('')

    def print_vars(self):
        if len(self.stat_vars) > 0:
            print('  VAR:')
            for vname, var in self.stat_vars.items():
                print('    {}: {}'.format(var.name, var.default))
            print('')

    def print_all(self):
        self.print_connectors()
        self.print_interfaces()
        self.print_options()
        self.print_vars()


def find_pyfiles(path):
    """ Find all python files in a path that qualify as qudi modules and return in pyton module form"""
    pyfiles = []

    for base in ['hardware', 'logic', 'gui', 'interface']:
        for dirName, subDirList, fileList in os.walk(os.path.join(path, base)):
            for f in fileList:
                if fnmatch.fnmatch(f, '*.py'):
                    dirpath = dirName
                    dirpart = ''
                    while os.path.split(dirpath)[-1] not in ['hardware', 'logic', 'gui', 'interface']:
                        splitpath = os.path.split(dirpath)
                        dirpart =  '.' + splitpath[-1] + dirpart
                        dirpath = splitpath[0]
                    #print(dirpath, dirpart, f)
                    if os.path.splitext(f)[0] == '__init__':
                        pyfiles.append(base + dirpart)
                    else:
                        pyfiles.append(base + dirpart + '.' + os.path.splitext(f)[0])
    return pyfiles

def check_qudi_modules(filelist):
    from core.module import Base
    from core.util.interfaces import InterfaceMetaclass
    from gui.guibase import GUIBase
    from logic.generic_logic import GenericLogic
    from logic.generic_task import InterruptableTask, PrePostTask

    othererror = []
    importerror = []
    importsuccess = []
    modules = {
        'hardware': {},
        'logic': {},
        'gui': {},
        'interface': {},
        'itask': {},
        'pptask':{}
    }
    for f in filelist:
        try:
            mod = importlib.__import__(f, fromlist=['*'])
            importsuccess.append(f)
            thinglist = dir(mod)
            for thingname in thinglist:
                path = '{}.{}'.format(f, thingname)
                thing = getattr(mod, thingname)
                try:
                    if not inspect.isclass(thing):
                        continue
                    if issubclass(thing, GenericLogic) and thingname != 'GenericLogic':
                        modules['logic'][path] = Module(
                            path,
                            thingname,
                            thing,
                            thing._conn,
                            [thingname],
                            thing._config_options,
                            thing._stat_vars
                            )
                    elif issubclass(thing, GUIBase) and thingname != 'GUIBase':
                        modules['gui'][path] = Module(
                            path,
                            thingname,
                            thing,
                            thing._conn,
                            [thingname],
                            thing._config_options,
                            thing._stat_vars
                            )
                    elif issubclass(thing, InterruptableTask) and thingname != 'InterruptableTask' :
                        modules['itask'][path] = {'pause': [i for i in thing.pauseTasks]}
                    elif issubclass(thing, PrePostTask) and thingname != 'PerPostTask':
                        modules['pptask'][path] = {}
                    elif (issubclass(thing, Base)
                        and thingname != 'Base'
                        and thingname != 'GenericLogic'
                        and thingname != 'GUIBase'
                        ):
                        modules['hardware'][path] = Module(
                            path,
                            thingname,
                            thing,
                            thing._conn,
                            [thingname],
                            thing._config_options,
                            thing._stat_vars
                            )
                    elif (f.startswith('interface')
                        and not issubclass(thing, Base)
                        and issubclass(thing.__class__, InterfaceMetaclass)
                        ):
                        modules['interface'][path] = thing
                    else:
                        pass
                except Exception as e:
                    pass
        except ImportError as e:
            importerror.append([f, e])
        except Exception as e:
            othererror.append([f, e])

    for base in ['hardware', 'logic', 'gui']:
        for modpath, module in modules[base].items():
            for ifname, interface in modules['interface'].items():
                n = ifname.split('.')[-1]
                try:
                    if issubclass(module.reference, interface):
                        module.interfaces.append(n)
                except AttributeError as e:
                    print('Interface {1} subclass check failed for {0}'
                        ''.format(module.reference, interface))

    return modules, importsuccess, importerror, othererror


if __name__ == '__main__':
    path = '.'
    if len(sys.argv) > 1:
        path = sys.argv[1]
    sys.path.append(os.getcwd())
    files = find_pyfiles(path)
    # print(files)
    m, i_s, ie, oe = check_qudi_modules(files)

    for k, v in m['hardware'].items():
        print('MODULE {}'.format(k))
        v.print_all()

    for k, v in m['logic'].items():
        print('MODULE {}'.format(k))
        v.print_all()

    for k, v in m['gui'].items():
        print('MODULE {}'.format(k))
        v.print_all()

    for k, v in m['pptask'].items():
        print('PPTASK {}'.format(k))

    for k, v in m['itask'].items():
        print('ITASK {}'.format(k))
        for pt in v['pause']:
            print('  pause {}'.format(pt))

    for k, v in m['interface'].items():
        print('INTERFACE {}'.format(k))

    if len(oe) > 0 or len(ie) > 0:
        print('\n==========  ERRORS:  ===========', file=sys.stderr)
        for e in oe:
            print(e[0], file=sys.stderr)
            print(e[1], file=sys.stderr)

        for e in ie:
            print(e[0], file=sys.stderr)
            print(e[1], file=sys.stderr)
