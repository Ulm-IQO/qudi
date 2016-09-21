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
import importlib

def print_connectors(moduledict):
    for k,v in moduledict.items():
        if k == 'in' and len(v) > 0:
            print('  IN:')
            for conn in moduledict['in']:
                print('    {}: {}'.format(conn[0], conn[1]))
        if k == 'out' and len(v) > 0:
            print('  OUT:')
            for conn in moduledict['out']:
                print('    {}: {}'.format(conn[0], conn[1]))
    print('')

def find_pyfiles(path):
    """ Find all python files in a path that qualify as qudi modules and return in pyton module form"""
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
    return pyfiles

def check_qudi_modules(filelist):
    from core.base import Base
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
        'itask': {},
        'pptask':{}
    }
    for f in filelist:
        try:
            mod = importlib.__import__(f, fromlist=['*'])
            importsuccess.append(f)
            thinglist = dir(mod)
            for thingname in thinglist:
                thing = getattr(mod, thingname)
                try:
                    if issubclass(thing, GenericLogic) and thingname != 'GenericLogic':
                        d = {}
                        d['in'] = [(i,v) for i,v in thing._in.items()]
                        d['out'] = [(i,v) for i,v in thing._out.items()]
                        modules['logic']['{}.{}'.format(f, thingname)] = d
                    elif issubclass(thing, GUIBase) and thingname != 'GUIBase':
                        d = {}
                        d['in'] = [(i,v) for i,v in thing._in.items()]
                        d['out'] = [(i,v) for i,v in thing._out.items()]
                        modules['gui']['{}.{}'.format(f, thingname)] = d
                    elif issubclass(thing, InterruptableTask) and thingname != 'InterruptableTask' :
                        modules['itask']['{}.{}'.format(f, thingname)] = {'pause': [i for i in thing.pauseTasks]}
                    elif issubclass(thing, PrePostTask) and thingname != 'PerPostTask':
                        modules['pptask']['{}.{}'.format(f, thingname)] = {}
                    elif issubclass(thing, Base) and thingname != 'Base' and thingname != 'GenericLogic' and thingname != 'GUIBase':
                        d = {}
                        d['in'] = [(i,v) for i,v in thing._in.items()]
                        d['out'] = [(i,v) for i,v in thing._out.items()]
                        modules['hardware']['{}.{}'.format(f, thingname)] = d
                    else:
                        pass
                except:
                    pass
        except ImportError as e:
            importerror.append([f, e])
        except Exception as e:
            othererror.append([f, e])
    return modules, importsuccess, importerror, othererror


if __name__ == '__main__':
    path = '.'
    if len(sys.argv) > 1:
        path = sys.argv[1]
    sys.path.append(os.getcwd())
    files = find_pyfiles(path)
    m, i_s, ie, oe = check_qudi_modules(files)

    for k,v in m['hardware'].items():
        print('MODULE {}'.format(k))
        print_connectors(v)

    for k,v in m['logic'].items():
        print('MODULE {}'.format(k))
        print_connectors(v)

    for k,v in m['gui'].items():
        print('MODULE {}'.format(k))
        print_connectors(v)

    for k,v in m['pptask'].items():
        print('PPTASK {}'.format(k))
    
    for k,v in m['itask'].items():
        print('ITASK {}'.format(k))
        for pt in v['pause']:
            print('  pause {}'.format(pt))

    if len(oe) > 0 or len(ie) > 0:
        print('\n==========  ERRORS:  ===========', file=sys.stderr)
        for e in oe:
            print(e[0], file=sys.stderr)
            print(e[1], file=sys.stderr)

        for e in ie:
            print(e[0], file=sys.stderr)
            print(e[1], file=sys.stderr)
