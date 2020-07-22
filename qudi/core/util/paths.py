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

# ToDo: Throw errors around for non-existent directories

import os
import sys

__all__ = ('get_appdata_dir', 'get_default_config_dir', 'get_default_log_dir', 'get_home_dir',
           'get_main_dir', 'get_userdata_dir', 'get_artwork_dir')


def get_main_dir():
    """ Returns the absolute path to the directory of the main software.

    @return string: path to the main tree of the software
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


def get_artwork_dir():
    """ Returns the absolute path to the qudi artwork directory

    @return string: path to the artwork directory of qudi
    """
    return os.path.join(get_main_dir(), 'core', 'artwork')


def get_home_dir():
    """ Returns the path to the home directory, which should definitely exist.

    @return str: absolute path to the home directory
    """
    return os.path.abspath(os.path.expanduser('~'))


def get_userdata_dir(create_missing=False):
    """ Returns the path to the qudi subfolder in the user home directory. This path should be used
     for exposed user data like config files etc.

    @return str: absolute path to the home directory
    """
    path = os.path.join(get_home_dir(), 'qudi')
    # Create directory if desired. Will throw an exception if path returned by get_home_dir() is
    # non-existent (which should never happen).
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_appdata_dir(create_missing=False):
    """ Get the system specific application data directory.

    @return str: path to appdata directory
    """
    if sys.platform == 'win32':
        # resolves to "C:\Documents and Settings\<UserName>\Application Data" on XP and
        # "C:\Users\<UserName>\AppData\Roaming" on win7 and newer
        path = os.path.join(os.environ['APPDATA'], 'qudi')
    elif sys.platform == 'darwin':
        path = os.path.abspath(os.path.expanduser('~/Library/Preferences/qudi'))
    else:
        path = os.path.abspath(os.path.expanduser('~/.local/qudi'))

    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.makedirs(path)
    return path


def get_default_config_dir(create_missing=False):
    """ Get the system specific application data directory.

    @return str: path to appdata directory
    """
    path = os.path.join(get_userdata_dir(create_missing), 'config')
    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path


def get_default_log_dir(create_missing=False):
    """ Get the system specific application log directory.

    @return str: path to default logging directory
    """
    # FIXME: This needs to be properly done for linux systems
    path = os.path.join(get_userdata_dir(create_missing), 'log')
    # Create path if desired.
    if create_missing and not os.path.exists(path):
        os.mkdir(path)
    return path
