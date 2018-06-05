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

Distributed under the MIT license, see documentation/MITLicense.md.
PyQtGraph - Scientific Graphics and GUI Library for Python
www.pyqtgraph.org
Copyright:
  2012  University of North Carolina at Chapel Hill
        Luke Campagnola    <luke.campagnola@gmail.com>
"""

import os
import sys
import atexit

# use setuptools parse_version if available and use distutils LooseVersion as
# fallback
try:
    from pkg_resources import parse_version
except ImportError:
    from distutils.version import LooseVersion as parse_version

has_pyqtgraph = False
try:
    import pyqtgraph
    has_pyqtgraph = True
except ImportError:
    pass

import importlib
import logging
logger = logging.getLogger(__name__)

# Optional function for exiting immediately (with some manual teardown)


def exit(exitcode=0):
    """
    Causes python to exit without garbage-collecting any objects, and thus
    avoids calling object destructor methods. This is a sledgehammer
    workaround for a variety of bugs in PyQt and Pyside that cause crashes
    on exit.

    This function does the following in an attempt to 'safely' terminate
    the process:

    * Invoke atexit callbacks
    * Close all open file handles
    * os._exit()

    Note: there is some potential for causing damage with this function if you
    are using objects that _require_ their destructors to be called (for
    example, to properly terminate log files, disconnect from devices, etc).
    Situations like this are probably quite rare, but use at your own risk.

    @param int exitcode: system exit code
    """

    if has_pyqtgraph:
        # first disable our pyqtgraph's cleanup function; won't be needing it.
        pyqtgraph.setConfigOptions(exitCleanup=False)

    # invoke atexit callbacks
    atexit._run_exitfuncs()

    # close file handles
    fd_min = 3
    fd_max = 4096
    fd_except = set()

    fd_set = set(range(fd_min, fd_max))

    # in this subprocess we redefine the stdout, therefore on Unix systems we
    # need to handle the opened file descriptors, see PEP 446:
    #       https://www.python.org/dev/peps/pep-0446/
    if sys.platform in ['linux', 'darwin']:

        if sys.platform == 'darwin':
            # trying to close 7 produces an illegal instruction on the Mac.
            fd_except.add(7)

        # remove specified file descriptor
        fd_set = fd_set - fd_except

        close_fd(fd_set)

    os._exit(exitcode)


def close_fd(fd_set):
    """ Close routine for file descriptor

    @param set fd_set: set of integers indicating the file descriptors which
                       should be closed (or at least tried to close).
    """
    for fd in fd_set:
        try:
            os.close(fd)
        except OSError:
            pass


def import_check():
    """ Checks whether all the necessary modules are present upon start of qudi.

    @return: int, error code either 0 or 4.

    Check also whether some recommended packages exists. Return err_code=0 if
    all vital packages are installed and err_code=4 if vital packages are
    missing. Make a warning about missing packages. Check versions.
    """
    # encode like: (python-package-name, repository-name, version)
    vital_pkg = [('ruamel.yaml','ruamel.yaml', None),
                 ('fysom','fysom', '2.1.4')]
    opt_pkg = [('rpyc','rpyc', None),
               ('pyqtgraph','pyqtgraph', None),
               ('git','gitpython', None)]


    def check_package(pkg_name, repo_name, version, optional=False):
        """
        Checks if a package is installed and if so whether it is new enough.

        @param: pkg_name : str, package name
        @param: repo_name : str, repository name
        @param: version : str, required version number
        @param: optional : bool, indicates whether a package is optional
        @return: int, error code either 0 or 4.
        """
        try:
            module = importlib.import_module(pkg_name)
        except ImportError:
            if (optional):
                additional_text = 'It is recommended to have this package installed. '
            else:
                additional_text = ''
            logger.error(
                'No Package "{0}" installed! {2}Perform e.g.\n\n'
                '    pip install {1}\n\n'
                'in the console to install the missing package.'.format(
                    pkg_name,
                    repo_name,
                    additional_text
                    ))
            return 4
        if (version is not None):
            # get package version number
            try:
                module_version = module.__version__
            except AttributeError:
                logger.warning('Package "{0}" does not have a __version__ '
                               'attribute. Ignoring version check!'.format(
                                   pkg_name))
                return 0
            # compare version number
            if (parse_version(module_version) < parse_version(version)):
                logger.error(
                    'Installed package "{0}" has version {1}, but version '
                    '{2} is required. Upgrade e.g. with \n\n'
                    '    pip install --upgrade {3}\n\n'
                    'in the console to upgrade to newest version.'.format(
                        pkg_name,
                        module_version,
                        version,
                        repo_name))
                return 4
        return 0


    err_code = 0
    # check required packages
    for pkg_name, repo_name, version in vital_pkg:
        err_code = err_code | check_package(pkg_name, repo_name, version)

    # check qt
    try:
        from qtpy.QtCore import Qt
    except ImportError:
        logger.error('No Qt bindungs detected! Perform e.g.\n\n'
                     '    pip install PyQt5\n\n'
                     'in the console to install the missing package.')
        err_code = err_code | 4

    # check optional packages
    for pkg_name, repo_name, version in opt_pkg:
        check_package(pkg_name, repo_name, version, True)

    return err_code
