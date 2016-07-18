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

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

import traceback
import sys
import logging

import pyqtgraph.debug as pgdebug
from pyqtgraph.Qt import QtCore

## install global exception handler for others to hook into.
import pyqtgraph.exceptionHandling as exceptionHandling
exceptionHandling.setTracebackClearing(True)

global LOG
LOG = None

global blockLogging
blockLogging = False

global original_excepthook
original_excepthook = sys.excepthook

def printExc(msg='', indent=4, prefix='|', msgType='error'):
    """Print an error message followed by an indented exception backtrace

      @param string msg: message to be logged
      @param int indent: indentation depth in characters
      @param string prefix: prefix for backtrace lines
      @param string msgType: type of message (user, status, warning, error)

    (This function is intended to be called within except: blocks)
    """
    pgdebug.printExc(msg, indent, prefix)

LEVEL_STATUS = 25
LEVEL_THREAD = 24
LOGGER_NAME = 'qudi'

logger = logging.getLogger(LOGGER_NAME)

def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def thread(msg, *args, **kwargs):
    logger.log(LEVEL_THREAD, msg, *args, **kwargs)

def status(msg, *args, **kwargs):
    logger.log(LEVEL_STATUS, msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def exception(msg, *args, **kwargs):
    logger.exception(msg, *args, **kwargs)

class QtLogFormatter(logging.Formatter):
    def processEntry(self, entry):
        """Convert excpetion into serializable form.

            @param dict entry: log file entry
        """
        ## pre-processing common to saveEntry and displayEntry
        ## convert exc_info to serializable dictionary
        if entry.get('exception', None) is not None:
            exc_info = entry.pop('exception')
            entry['exception'] = self.exceptionToDict(*exc_info,
                                        topTraceback=entry.get('traceback', []))
        else:
            entry['exception'] = None

    def exceptionToDict(self, exType, exc, tb, topTraceback):
        """Convert exception object to dictionary.

          @param exType: exception type
          @param exc: exception object
          @param tb: traceback object
          @param topTraceback: ??

          @return dict: dictionary containing traceback and exception information
        """
        excDict = {}
        excDict['message'] = traceback.format_exception(exType, exc, tb)[-1][:-1]
        excDict['traceback'] = topTraceback + traceback.format_exception(exType, exc, tb)[:-1]
        if hasattr(exc, 'docs'):
            if len(exc.docs) > 0:
                excDict['docs'] = exc.docs
        if hasattr(exc, 'reasons'):
            if len(exc.reasons) > 0:
                excDict['reasons'] = exc.reasons
        if hasattr(exc, 'kwargs'):
            for k in exc.kwargs:
                excDict[k] = exc.kwargs[k]
        if hasattr(exc, 'oldExc'):
            excDict['oldExc'] = self.exceptionToDict(*exc.oldExc, topTraceback=[])
        return excDict

    def format(self, record):
        entry = {
            'message': record.msg,
            'timestamp': self.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S"),
            'importance': 5,
            'msgType': record.levelname,
            'exception': record.exc_info,
            'id': 1, # message count: remove?
            }
        self.processEntry(entry)
        return entry


class QtLogHandler(logging.Handler):
    def __init__(self, logger, **kwargs):
        super().__init__(**kwargs)
        self.setFormatter(QtLogFormatter())
        self._logger = logger

    def emit(self, record):
        record = self.format(record)
        if record: self._logger.sigLoggedMessage.emit(record)


class Logger(QtCore.QObject):
    """Class that does all the log handling in QuDi."""

    sigLoggedMessage = QtCore.Signal(object)

    def __init__(self, manager, **kwargs):
        """Create a logger instance for a manager object.

          @param object manager: instance of the Manager class that this
                                 logger belongs to.
        """
        super().__init__(**kwargs)
        self.manager = manager

        # initialize logger
        logging.basicConfig(format="%(message)s", level=LEVEL_STATUS)
        logger = logging.getLogger(LOGGER_NAME)
        logging.addLevelName(logging.CRITICAL, 'critical')
        logging.addLevelName(logging.ERROR, 'error')
        logging.addLevelName(logging.WARNING, 'warning')
        logging.addLevelName(LEVEL_STATUS, 'status')
        logging.addLevelName(LEVEL_THREAD, 'thread')
        logging.addLevelName(logging.INFO, 'status')
        logging.addLevelName(logging.DEBUG, 'debug')
        logging.addLevelName(logging.NOTSET, 'not set')
        logger.setLevel(logging.INFO)

        # stream handler
        #streamhandler = logging.StreamHandler(stream=sys.stdout)
        #streamhandler.setFormatter(logging.Formatter("%(message)s"))
        #streamhandler.setLevel(LEVEL_STATUS)
        #logger.addHandler(streamhandler)
        # add Qt log handler
        self._qt_log_handler = QtLogHandler(self)
        self._qt_log_handler.setLevel(logging.INFO)
        logger.addHandler(self._qt_log_handler)
        # add file logger
        self._rotating_file_handler = logging.handlers.RotatingFileHandler(
            'qudi.log', backupCount=5)
        self._rotating_file_handler.setFormatter(logging.Formatter(
            "%(levelname)s %(asctime)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"))
        self._rotating_file_handler.doRollover()
        logger.addHandler(self._rotating_file_handler)

    def exceptionCallback(self, *args):
        """Exception logging function.

          @param list args: contents of exception (typt, value, backtrace)
        """
        # Called whenever there is an unhandled exception.
        # unhandled exceptions generate an error message by default, but this
        # can be overridden.
        global blockLogging
        # If an error occurs *while* trying to log another exception, disable
        # any further logging to prevent recursion.
        if not blockLogging:
            try:
                blockLogging = True
                ex_type, ex_value, ex_traceback = args
                error('Unexpected error: ', exc_info=args)
                self.logMsg('Unexpected error: ', exception=args,
                            msgType='error')
                print(ex_type)
                if ex_type == KeyboardInterrupt:
                    self.manager.quit()
            except:
                print('Error: Exception could no be logged.')
                original_excepthook(*sys.exc_info())
            finally:
                blockLogging = False
