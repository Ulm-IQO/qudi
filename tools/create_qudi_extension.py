# -*- coding: utf-8 -*-
"""
This tool creates the folder structure for a qudi extension.

- __init__.py
- gui
  - __init__.py
- logic
  - __init__.py
- hardware
  - __init__.py

It prepares the __init__.py files such that this python package works as
qudi extension.


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
top-level directory of this distribution and at
<https://github.com/Ulm-IQO/qudi/>
"""

import argparse
import os

parser = argparse.ArgumentParser(
    description='Creates folder structure for a qudi extension.')
parser.add_argument('directory', type=str, help='directory for qudi package')
args = parser.parse_args()

if (os.path.exists(args.directory)):
    # the directory exists already
    print('Error: Path {0} already exists.'.format(args.directory))
else:
    # directory doesn't exist. Create folder structure
    os.makedirs(args.directory)
    # place __init__.py
    with open('{0}/__init__.py'.format(args.directory), 'w'):
        pass
    for subdir in ['gui', 'logic', 'hardware']:
        # create subdirectory
        os.makedirs('{0}/{1}'.format(args.directory, subdir))
        # place __init__.py
        with open('{0}/{1}/__init__.py'.format(args.directory, subdir),
                  'w') as f:
            f.write('import pkgutil\n')
            f.write('__path__ = pkgutil.extend_path(__path__, __name__)\n')
    print('Finished creating folder structure for qudi extension.')
    print('')
    print('You can include your extension into qudi by adding its path')
    print('in the configuration file:')
    print('')
    print('[global]')
    print('extensions = [\'{0}\']'.format(
        os.path.abspath(args.directory)))
    print('')
    print('or by defining it in the environment variable PYTHONPATH, e.g.')
    print('')
    print('$ PYTHONPATH="{0}" python qudi/start.py'.format(
        os.path.abspath(args.directory)))
