# -*- coding: utf-8 -*-
"""
This package provides the qudi logging facility. It facilitates Pythonic logging by joining Qt log
into native Python logging. Also installs a logging handler that emits a Qt Signal to tap into
every time a log event is registered.
Automatically installs all important logging handlers for qudi to work but also allows for
registering (and removal) of additional handlers.
Installs a rotating log file handler to write log messages to disk.

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

__all__ = ('clear_handlers',
           'get_handler',
           'get_file_handler',
           'get_logger',
           'get_record_table_model',
           'get_signal_handler',
           'get_stderr_handler',
           'init_record_model_handler',
           'init_rotating_file_handler',
           'register_handler',
           'set_log_level',
           'unregister_handler',
           )

import os
import logging
from logging.handlers import RotatingFileHandler
from PySide2.QtCore import qInstallMessageHandler

from .handlers import LogSignalHandler, LogTableModelHandler, qt_message_handler


# global variables
# Keep track of all handlers that have been registered to the qudi
_handlers = dict()
# default handlers for qudi root logger
_signal_handler = None
_file_handler = None
_stream_handler = None
_table_model_handler = None
# The qudi root logger for all loggers created with this module API
_qudi_root_logger = None

# Register Qt message handler
qInstallMessageHandler(qt_message_handler)

# initialize logging module
logging.basicConfig(format="%(message)s", level=logging.WARNING)
logging.addLevelName(logging.CRITICAL, 'critical')
logging.addLevelName(logging.ERROR, 'error')
logging.addLevelName(logging.WARNING, 'warning')
logging.addLevelName(logging.INFO, 'info')
logging.addLevelName(logging.DEBUG, 'debug')
logging.addLevelName(logging.NOTSET, 'not set')
logging.captureWarnings(True)

# set level of stream handler which logs to stderr
if len(logging.getLogger().handlers) < 1:
    _stream_handler = logging.StreamHandler()
    logging.getLogger().addHandler(_stream_handler)
else:
    _stream_handler = logging.getLogger().handlers[0]
_stream_handler.setLevel(logging.WARNING)

# Create qudi root logger
_qudi_root_logger = logging.getLogger('qudi')
_qudi_root_logger.setLevel(logging.INFO)
# _qudi_root_logger.propagate = False

# Create and register signal handler in root logger
_signal_handler = LogSignalHandler()
logging.getLogger().addHandler(_signal_handler)


def register_handler(name, handler, silent=False):
    global _handlers
    if name in _handlers:
        if silent:
            unregister_handler(name)
        else:
            raise KeyError(f'Unable to register new logging handler. Handler by name "{name}" '
                           f'already registered.')
    logging.getLogger().addHandler(handler)
    _handlers[name] = handler


def unregister_handler(name, silent=False):
    global _handlers
    handler = _handlers.pop(name, None)
    if handler is None:
        if not silent:
            raise KeyError(
                f'Unable to unregister logging handler. No handler registered by name "{name}".'
            )
    else:
        logging.getLogger().removeHandler(handler)


def clear_handlers():
    global _handlers
    root_logger = logging.getLogger()
    for name in tuple(_handlers):
        root_logger.removeHandler(_handlers.pop(name))


def get_handler(name):
    return _handlers.get(name, None)


def get_logger(name):
    return _qudi_root_logger.getChild(name.split('qudi.', 1)[-1])


def set_log_level(level):
    _signal_handler.setLevel(level)
    _qudi_root_logger.setLevel(level)
    if _table_model_handler is not None:
        _table_model_handler.setLevel(level)
    if _file_handler is not None:
        _file_handler.setLevel(level)


def get_record_table_model():
    return None if _table_model_handler is None else _table_model_handler.table_model


def get_signal_handler():
    return _signal_handler


def get_stderr_handler():
    return _stream_handler


def get_file_handler():
    return _file_handler


def init_record_model_handler():
    global _table_model_handler

    if _table_model_handler is not None:
        logging.getLogger().removeHandler(_table_model_handler)
        _table_model_handler = None

    _table_model_handler = LogTableModelHandler()
    _table_model_handler.setLevel(_qudi_root_logger.level)
    logging.getLogger().addHandler(_table_model_handler)


def init_rotating_file_handler(path='', filename='qudi.log', max_bytes=1024**3, backup_count=5):
    global _file_handler

    # Remove file handler if it has already been registered
    if _file_handler is not None:
        _file_handler.doRollover()
        logging.getLogger().removeHandler(_file_handler)
        _file_handler = None

    filepath = os.path.join(path, filename)
    # Start new file if old logfiles exist
    do_rollover = os.path.exists(filepath) and os.stat(filepath).st_size > 0
    _file_handler = RotatingFileHandler(filepath, maxBytes=max_bytes, backupCount=backup_count)
    _file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s',
                                                datefmt="%Y-%m-%d %H:%M:%S"))
    _file_handler.setLevel(_qudi_root_logger.level)
    if do_rollover:
        _file_handler.doRollover()
    logging.getLogger().addHandler(_file_handler)
