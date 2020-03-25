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

import sys
import argparse
from qudi.core.application import Qudi


# Make icons work on non-X11 platforms, import a custom theme
if sys.platform == 'win32':
    try:
        import ctypes
        myappid = 'quantumoptics.quantumdiamond.mainapp'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        raise
    except:
        print('SetCurrentProcessExplicitAppUserModelID failed! This is probably not Microsoft '
              'Windows!')

# parse commandline parameters
parser = argparse.ArgumentParser(prog='python -m qudi')
group = parser.add_mutually_exclusive_group()
parser.add_argument(
    '-g', '--no-gui', action='store_true', help='does not load the manager gui module')
parser.add_argument('-c', '--config', default=None, help='configuration file')
parser.add_argument('-l', '--logdir', default='', help='log directory')
# group.add_argument('-p', '--profile', action='store_true', help='enables profiler')
# parser.add_argument('-m', '--manhole', action='store_true', help='manhole for debugging purposes')
# group.add_argument(
#     '-cg', '--callgraph', action='store_true', help='display methods/modules dependency graph')
args = parser.parse_args()

app = Qudi(no_gui=args.no_gui, log_dir=args.logdir, config_file=args.config)
app.run()
