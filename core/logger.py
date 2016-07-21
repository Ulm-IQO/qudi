# -*- coding: utf-8 -*-
"""
This file contains the QuDi logging class.

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
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

Original version derived from ACQ4, but there shouldn't be much left, maybe
some lines in the exception handler
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""


import logging
import logging.handlers
import sys
import traceback
import functools
from pyqtgraph.Qt import QtCore
import pyqtgraph.debug as pgdebug


def printExc(msg='', indent=4, prefix='|', msgType='error'):
    """Prints an error message followed by an indented exception backtrace

      @param string msg: message to be logged
      @param int indent: indentation depth in characters
      @param string prefix: prefix for backtrace lines
      @param string msgType: type of message (user, status, warning, error)

    (This function is intended to be called within except: blocks)
    """
    pgdebug.printExc(msg, indent, prefix)


class QtLogFormatter(logging.Formatter):
    """Formatter used with QtLogHandler.

      Converts the log record into a dictionary with the following keys:
        - name: logger name
        - message: the message
        - timestamp: the creation time of the log record
        - level: log level
      Optional if an exception is logged:
        - exception: dictionary with keys:
          - message: the message
          - traceback: a traceback
    """

    def format(self, record):
        """Formatting function

          @param object record: :logging.LogRecord:
        """
        entry = {
                'name': record.name,
                'message': record.message,
                'timestamp': self.formatTime(record,
                    datefmt="%Y-%m-%d %H:%M:%S"),
                'level': record.levelname
        }
        # add exception information if available
        if record.exc_info is not None:
            entry['exception'] = {
                    'message': traceback.format_exception(
                        *record.exc_info)[-1][:-1],
                    'traceback': traceback.format_exception(
                        *record.exc_info)[:-1]
                    }

        return entry


class QtLogHandler(QtCore.QObject, logging.Handler):
    """Log handler for displaying log records in a QT gui.

      For each log record the Qt signal sigLoggedMessage is emitted
      with a dictionary as parameter. The keys of this dictionary are:
        - name: logger name
        - message: the message
        - timestamp: the creation time of the log record
        - level: log level
      Optional if an exception is logged:
        - exception: dictionary with keys:
          - message: the message
          - traceback: a traceback

      @param object parent: parent of QObject, defaults to None
      @param int level: log level, defaults to NOTSET
    """

    sigLoggedMessage = QtCore.Signal(object)
    """signal emitted for each log record"""

    def __init__(self, parent=None, level=0):
        QtCore.QObject.__init__(self, parent)
        logging.Handler.__init__(self, level)
        self.setFormatter(QtLogFormatter())

    def emit(self, record):
        """Emit function of handler.

          Formats the log record and emits :sigLoggedMessage:

          @param object record: :logging.LogRecord:
        """
        record = self.format(record)
        if record: self.sigLoggedMessage.emit(record)


def initialize_logger():
    """sets up the logger including a console, file and qt handler
    """
    # initialize logger
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    logging.addLevelName(logging.CRITICAL, 'critical')
    logging.addLevelName(logging.ERROR, 'error')
    logging.addLevelName(logging.WARNING, 'warning')
    logging.addLevelName(logging.INFO, 'info')
    logging.addLevelName(logging.DEBUG, 'debug')
    logging.addLevelName(logging.NOTSET, 'not set')
    logging.captureWarnings(True)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # set level of stream handler which logs to stderr
    logger.handlers[0].setLevel(logging.WARNING)

    # add file logger (inherits level)
    rotating_file_handler = logging.handlers.RotatingFileHandler(
        'qudi.log', backupCount=5)
    rotating_file_handler.setFormatter(logging.Formatter(
        "%(name)s %(levelname)s %(asctime)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"))
    rotating_file_handler.doRollover()
    logger.addHandler(rotating_file_handler)

    # add Qt log handler
    qt_log_handler = QtLogHandler()
    qt_log_handler.setLevel(logging.INFO)
    logger.addHandler(qt_log_handler)




# global variables used by exception handler
original_excepthook = None
blockLogging = False

def _exception_handler(manager, *args):
    """Exception logging function.

      @param object manager: the manager
      @param list args: contents of exception (type, value, backtrace)
    """
    global blockLogging
    # If an error occurs *while* trying to log another exception, disable
    # any further logging to prevent recursion.
    if not blockLogging:
        try:
            blockLogging = True
            ## Start by extending recursion depth just a bit.
            ## If the error we are catching is due to recursion, we
            ## don't want to generate another one here.
            recursionLimit = sys.getrecursionlimit()
            try:
                sys.setrecursionlimit(recursionLimit+100)
                try:
                    logging.error('Unhandled exception: ', exc_info=args)
                    if args[0] == KeyboardInterrupt:
                        manager.quit()
                except Exception:
                    print('   ------------------------------------------'
                            '--------------------')
                    print('      Error occurred during exception '
                            'handling')
                    print('   ------------------------------------------'
                            '--------------------')
                    traceback.print_exception(*sys.exc_info())
                # Clear long-term storage of last traceback to prevent
                # memory-hogging.
                # (If an exception occurs while a lot of data is present
                # on the stack, such as when loading large files, the
                # data would ordinarily be kept until the next exception
                # occurs. We would rather release this memory
                # as soon as possible.)
                sys.last_traceback = None
            finally:
                sys.setrecursionlimit(recursionLimit)
        finally:
            blockLogging = False


def register_exception_handler(manager):
    """registers an exception handler

      @param object manager: the manager
    """
    global original_excepthook
    original_excepthook = sys.excepthook
    sys.excepthook = functools.partial(_exception_handler, manager)

