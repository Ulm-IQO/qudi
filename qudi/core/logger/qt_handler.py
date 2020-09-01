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
"""

__all__ = ('LogSignalHandler', 'qt_message_handler')

import logging
from PySide2 import QtCore


class QtSignaller(QtCore.QObject):
    """Just a bare Qt QObject handling a signal
    """
    sigSignal = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)


class LogSignalHandler(logging.Handler):
    """Logging handler that emits a Qt signal when a log entry is registered
    """

    def __init__(self, level=0):
        super().__init__(level=level)
        self.__qt_signaller = QtSignaller()

    @property
    def sigMessageLogged(self):
        return self.__qt_signaller.sigSignal

    def emit(self, record):
        """
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
        logger.critical('Fatal error occurred: {0}\nTraceback:\n{1}'
                        ''.format(msg, ''.join(traceback.format_stack())))
        # global man
        # if man is not None:
        #     logger.critical('Asking manager to quit.')
        #     try:
        #         man.quit()
        #         QtCore.QCoreApplication.instance().processEvents()
        #     except:
        #         logger.exception('Manager failed quitting.')
