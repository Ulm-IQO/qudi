# -*- coding: utf-8 -*-
"""
This file contains the Qudi logging handler objects.

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

__all__ = ('LogSignalHandler', 'LogTableModelHandler', 'qt_message_handler')

import logging
from PySide2 import QtCore

from .records_model import LogRecordsTableModel


class QtSignaller(QtCore.QObject):
    """ Just a bare Qt QObject containing a signal
    """
    sigSignal = QtCore.Signal(object)


class LogSignalHandler(logging.Handler):
    """ Logging handler that emits a Qt signal when a log entry is registered
    """
    def __init__(self, level=logging.NOTSET):
        super().__init__(level=level)
        self.__qt_signaller = QtSignaller()

    @property
    def sigRecordLogged(self):
        return self.__qt_signaller.sigSignal

    def emit(self, record):
        """ Emit a signal when logging.Handler emits a new log record
        """
        self.__qt_signaller.sigSignal.emit(record)


class LogTableModelHandler(logging.Handler):
    """ Logging handler that stores each log record in a QAbstractTableModel.
    """
    def __init__(self, level=logging.INFO, max_records=10000):
        if level < logging.DEBUG:
            level = logging.DEBUG
        super().__init__(level=level)
        self.__qt_signaller = QtSignaller()
        self.table_model = LogRecordsTableModel(max_records=max_records)
        self.__qt_signaller.sigSignal.connect(self.table_model.add_record,
                                              QtCore.Qt.QueuedConnection)

    def emit(self, record):
        """ Store the log record information in the table model
        """
        self.__qt_signaller.sigSignal.emit(record)


def qt_message_handler(msg_type, context, msg):
    """
    A message handler handling Qt5 messages.
    """
    logger = logging.getLogger('Qt')
    if msg_type == QtCore.QtDebugMsg:
        logger.debug(msg)
    elif msg_type == QtCore.QtInfoMsg:
        logger.info(msg)
    elif msg_type == QtCore.QtWarningMsg:
        logger.warning(msg)
    elif msg_type == QtCore.QtCriticalMsg:
        logger.critical(msg)
    else:
        import traceback
        traceback_str = ''.join(traceback.format_stack())
        logger.critical(f'Fatal error occurred: {msg}\nTraceback:\n{traceback_str}')
