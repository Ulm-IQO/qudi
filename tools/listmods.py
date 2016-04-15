# -*- coding: utf-8 -*-
"""
List types of QuDi python files and theri object properties

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
import sys
import fnmatch
import importlib

sys.path.append(os.getcwd())

from core.base import Base
from gui.guibase import GUIBase
from logic.generic_logic import GenericLogic
from logic.generic_task import InterruptableTask, PrePostTask


def print_connectors(module):
    if len(thing._in) > 0:
        print('  IN:')
        for conn in thing._in:
            print('    {}: {}'.format(conn, thing._in[conn]))
    if len(thing._out) > 0:
        print('  OUT:')
        for conn in thing._out:
            print('    {}: {}'.format(conn, thing._out[conn]))
    print('')
    

path = '.'
if len(sys.argv) > 1:
    path = sys.argv[1]
pyfiles = []

for base in ['hardware', 'logic', 'gui']:
    for dirName, subDirList, fileList in os.walk(os.path.join(path, base)):
        for f in fileList:
            if fnmatch.fnmatch(f, '*.py'):
                dirpath = dirName
                dirpart = ''
                while os.path.split(dirpath)[-1] not in ['hardware', 'logic', 'gui']:
                    splitpath = os.path.split(dirpath)
                    dirpart =  '.' + splitpath[-1] + dirpart
                    dirpath = splitpath[0]
                #print(dirpath, dirpart, f)
                if os.path.splitext(f)[0] == '__init__':
                    pyfiles.append(base + dirpart)
                else:
                    pyfiles.append(base + dirpart + '.' + os.path.splitext(f)[0])

othererror = []
importerror = []
importsuccess = []
for f in pyfiles:
    try:
        mod = importlib.__import__(f, fromlist=['*'])
        importsuccess.append(f)
        thinglist = dir(mod)
        for thingname in thinglist:
            thing = getattr(mod, thingname)
            try:
                if issubclass(thing, GenericLogic) and thingname != 'GenericLogic':
                    print('MODULE ' + f + '.' + thingname)
                    print_connectors(thing)
                elif issubclass(thing, GUIBase) and thingname != 'GUIBase':
                    print('MODULE ' + f + '.' + thingname)
                    print_connectors(thing)
                elif issubclass(thing, InterruptableTask) and thingname != 'InterruptableTask' :
                    print('INTASK ' + f + ' ' + thingname)
                    print(thing.pauseTasks)
                elif issubclass(thing, PrePostTask) and thingname != 'PerPostTask':
                    print('PPTASK ' + f + ' ' + thingname)
                elif issubclass(thing, Base) and thingname != 'Base' and thingname != 'GenericLogic' and thingname != 'GUIBase':
                    print('MODULE ' + f + '.' + thingname)
                    print_connectors(thing)
                else:
                    pass
            except:
                pass
    except ImportError as e:
        importerror.append([f, e])
    except Exception as e:
        othererror.append([f, e])

for e in othererror:
    print(e[0], file=sys.stderr)
    print(e[1], file=sys.stderr)

for e in importerror:
    print(e[0], file=sys.stderr)
    print(e[1], file=sys.stderr)


