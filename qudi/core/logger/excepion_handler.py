# -*- coding: utf-8 -*-
"""
This file contains the Qudi logging class.

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

Original version derived from ACQ4, but there shouldn't be much left, maybe
some lines in the exception handler
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

__all__ = ('original_excepthook', 'register_exception_handler')

import sys
import traceback
import functools
import logging


original_excepthook = None
_block_logging = False


def _exception_handler(manager, *args):
    """Exception logging function.

    @param object manager: the qudi manager instance
    @param list args: contents of exception (type, value, backtrace)
    """
    global _block_logging
    # If an error occurs *while* trying to log another exception, disable any further logging to
    # prevent recursion.
    if not _block_logging:
        try:
            _block_logging = True
            # Start by extending recursion depth just a bit. If the error we are catching is due to
            # recursion, we don't want to generate another one here.
            recursion_limit = sys.getrecursionlimit()
            try:
                sys.setrecursionlimit(recursion_limit + 100)
                try:
                    logging.error('', exc_info=args)
                    if args[0] == KeyboardInterrupt:
                        manager.quit()
                except:
                    print('   --------------------------------------------------------------')
                    print('      Error occurred during exception handling')
                    print('   --------------------------------------------------------------')
                    traceback.print_exception(*sys.exc_info())
                # Clear long-term storage of last traceback to prevent memory-hogging. (If an
                # exception occurs while a lot of data is present on the stack, such as when loading
                # large files, the data would ordinarily be kept until the next exception occurs.
                # We would rather release this memory as soon as possible.)
                sys.last_traceback = None
            finally:
                sys.setrecursionlimit(recursion_limit)
        finally:
            _block_logging = False


def register_exception_handler(manager):
    """registers an exception handler

      @param object manager: the manager
    """
    global original_excepthook
    original_excepthook = sys.excepthook
    sys.excepthook = functools.partial(_exception_handler, manager)
