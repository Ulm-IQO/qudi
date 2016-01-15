# -*- coding: utf-8 -*-
import os
import sys
import fnmatch
import importlib


sys.path.append(os.getcwd())
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
    except ImportError as e:
        importerror.append([f, e])
    except Exception as e:
        othererror.append([f, e])

for e in othererror:
    print(e[0])
    print(e[1])

for e in importerror:
    print(e[0])
    print(e[1])
