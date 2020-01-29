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

__all__ = ('get_appdata_dir', 'get_home_dir', 'get_main_dir')

import os
import sys


def get_main_dir():
    """ Returns the absolut path to the directory of the main software.

         @return string: path to the main tree of the software

    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


def get_home_dir():
    """
    Returns the path to the home directory, which should definitely exist.

    @return str: absolute path to the home directory
    """
    return os.path.abspath(os.path.expanduser('~'))


def get_appdata_dir():
    """
    Get the system specific application data directory.

    @return str: path to appdata directory
    """
    if sys.platform == 'win32':
        # resolves to "C:\Documents and Settings\<UserName>\Application Data" on XP and
        # "C:\Users\<UserName>\AppData\Roaming" on win7 and newer
        return os.path.join(os.environ['APPDATA'], 'qudi')
    elif sys.platform == 'darwin':
        return os.path.abspath(os.path.expanduser('~/Library/Preferences/qudi'))
    else:
        return os.path.abspath(os.path.expanduser('~/.local/qudi'))
