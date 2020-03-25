# -*- coding: utf-8 -*-
"""
This file contains the Qudi Manager class.

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

__version__ = '0.9'
__all__ = ('cleanup_handlers',
           'file_handler',
           'get_handler',
           'get_logger',
           'init_rotating_file_handler',
           'original_excepthook',
           'register_exception_handler',
           'register_handler',
           'signal_handler',
           'unregister_handler',
           )

import os
import logging
from logging.handlers import RotatingFileHandler
from qtpy import QtCore
from qudi.core.logger.qt_handler import LogSignalHandler, qt_message_handler
from qudi.core.logger.excepion_handler import original_excepthook, register_exception_handler

# global variables
_handlers = dict()

# initialize logging module
logging.basicConfig(format="%(message)s", level=logging.INFO)
logging.addLevelName(logging.CRITICAL, 'critical')
logging.addLevelName(logging.ERROR, 'error')
logging.addLevelName(logging.WARNING, 'warning')
logging.addLevelName(logging.INFO, 'info')
logging.addLevelName(logging.DEBUG, 'debug')
logging.addLevelName(logging.NOTSET, 'not set')
logging.captureWarnings(True)

# Get root logger and set default level to INFO
_root_logger = logging.getLogger()
if len(_root_logger.handlers) > 1:
    for handler in _root_logger.handlers[1:]:
        _root_logger.removeHandler(handler)
_root_logger.setLevel(logging.INFO)

# set level of stream handler which logs to stderr
_root_logger.handlers[0].setLevel(logging.WARNING)

# Instantiate Qt signal log handler and register it to logger
signal_handler = LogSignalHandler(level=logging.DEBUG)
_root_logger.addHandler(signal_handler)

# Instantiate rotating file handler
file_handler = None

# Register Qt5 message handler
QtCore.qInstallMessageHandler(qt_message_handler)

for logger_name in ('core', 'gui', 'logic', 'hardware'):
    logging.getLogger(logger_name).setLevel(logging.DEBUG)


def register_handler(name, handler, silent=False):
    global _handlers
    if name in _handlers:
        if silent:
            unregister_handler(name)
        else:
            raise KeyError('Unable to register new logging handler. Handler by name "{0}" '
                           'already registered.'.format(name))
    logging.getLogger().addHandler(handler)
    _handlers[name] = handler
    return


def unregister_handler(handler_name, silent=False):
    global _handlers
    if handler_name in _handlers:
        logging.getLogger().removeHandler(_handlers[handler_name])
        del _handlers[handler_name]
    elif not silent:
        raise KeyError('Unable to unregister logging handler. No handler by name "{0}" '
                       'registered.'.format(handler_name))
    return


def cleanup_handlers():
    global _handlers
    if len(_root_logger.handlers) > 1:
        for handler in _root_logger.handlers[1:]:
            if handler is qt_handler or handler is signal_handler:
                continue
            _root_logger.removeHandler(handler)


def get_handler(name):
    return _handlers.get(name, None)


def get_logger(name=None):
    return logging.getLogger(name) if name is not None else logging.getLogger()


def init_rotating_file_handler(path='', filename='qudi.log', level=None, max_bytes=10485760,
                               backup_count=5):
    global file_handler
    # Remove file handler if it has already been registered
    if file_handler is not None:
        file_handler.doRollover()
        _root_logger.removeHandler(file_handler)
        file_handler = None

    if level is None:
        level = logging.DEBUG
    filepath = os.path.join(path, filename)
    # Start new file if
    do_rollover = os.path.exists(filepath) and os.stat(filepath).st_size > 0
    file_handler = RotatingFileHandler(filepath,
                                       maxBytes=max_bytes,
                                       backupCount=backup_count)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s',
                                                datefmt="%Y-%m-%d %H:%M:%S"))
    file_handler.setLevel(level)
    if do_rollover:
        file_handler.doRollover()
    _root_logger.addHandler(file_handler)
