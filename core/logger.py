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

import time
import traceback
import sys
import os
import logging

import pyqtgraph.debug as pgdebug
import pyqtgraph.configfile as configfile
from pyqtgraph.Qt import QtCore
from .util.mutex import Mutex

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

LEVEL_THREAD = 25
LEVEL_USER = 22
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

def user(msg, *args, **kwargs):
    logger.log(LEVEL_USER, msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)


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

          @param object manager: instance of the Manager class that this logger
                                 belongs to.
        """
        super().__init__(**kwargs)
        self.manager = manager
        self.msgCount = 0
        self.logCount = 0
        self.logFile = None

        # initialize logger
        logging.basicConfig(format="%(message)s", level=logging.INFO)
        logger = logging.getLogger(LOGGER_NAME)
        logging.addLevelName(logging.CRITICAL, 'critical')
        logging.addLevelName(logging.ERROR, 'error')
        logging.addLevelName(logging.WARNING, 'warning')
        logging.addLevelName(LEVEL_THREAD, 'thread')
        logging.addLevelName(LEVEL_USER, 'user')
        logging.addLevelName(logging.INFO, 'status')
        logging.addLevelName(logging.DEBUG, 'debug')
        logging.addLevelName(logging.NOTSET, 'not set')
        logger.setLevel(logging.INFO)

        # add Qt log handler
        self._qt_log_handler = QtLogHandler(self)
        logger.addHandler(self._qt_log_handler)
        # add file logger
        self._rotating_file_handler = logging.handlers.RotatingFileHandler(
            'qudi.log', backupCount=5)
        self._rotating_file_handler.setFormatter(logging.Formatter(
            "%(levelname)s %(asctime)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"))
        self._rotating_file_handler.doRollover()
        logger.addHandler(self._rotating_file_handler)

        # Start a new temp log file, destroying anything left over from the
        # last session.
        configfile.writeConfigFile('', self.fileName())
        self.lock = Mutex()
        exceptionHandling.register(self.exceptionCallback)

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

    # Called indirectly when logMsg is called from a non-gui thread
    def queuedLogMsg(self, args):
        """Deferred message logging function.

          @param list args: arguments for logMsg()
        """
        #print(args)
        self.logMsg(args[0], **args[1])

    def print_logMsg(self, msg, **kwargs):
        """Print message to stdout and log it.

          @param list kwargs: paamteers for logMsg()
        """
        print(msg)
        self.logMsg(msg, **kwargs)

    def logMsg(self, msg, importance=5, msgType='status', **kwargs):
        """Function for adding messages to log.

          @param string msg: the text of the log message
          @param string msgTypes: user, status, error, warning (status is default)
          @param int importance: 0-9 (0 is low importance, 9 is high, 5 is default)
          @param tuple exception: a tuple (type, exception, traceback) as
                                  returned by 'sys.exc_info()'
          @param list(string) docs: a list of strings where documentation
                                    related to the message can be found
          @param list(string) reasons: a list of reasons (as strings) for the message
          @paam list traceback: a list of formatted callstack/trackback objects
              (formatting a traceback/callstack returns a list of strings),
              usually looks like
              [['line 1', 'line 2', 'line3'], ['line1', 'line2']]

           Feel free to add your own keyword arguments.
           These will be saved in the log.txt file,
           but will not affect the content or way that messages are displayed.
        """
        currentDir = None

        now = str(time.strftime('%Y.%m.%d %H:%M:%S'))
        self.msgCount += 1
        name = 'LogEntry_' + str(self.msgCount)
        entry = {
            #'docs': None,
            #'reasons': None,
            'message': msg,
            'timestamp': now,
            'importance': importance,
            'msgType': msgType,
            #'exception': exception,
            'id': self.msgCount,
        }
        for k in kwargs:
            entry[k] = kwargs[k]

        self.processEntry(entry)

        # Allow exception to override values in the entry
        if entry.get('exception', None) is not None and 'msgType' in entry['exception']:
            entry['msgType'] = entry['exception']['msgType']

        self.saveEntry({name:entry})
        self.sigLoggedMessage.emit(entry)

    def logExc(self, *args, **kwargs):
        """Calls logMsg, but adds in the current exception and callstack.

          @param list args: arguments for logMsg()
          @param dict kwargs: dictionary containing exception information.

        Must be called within an except block, and should only be called if the
        exception is not re-raised.
        Unhandled exceptions, or exceptions that reach the top of the callstack
        are automatically logged, so logging an exception that will be
        re-raised can cause the exception to be logged twice.
        Takes the same arguments as logMsg.
        """
        kwargs['exception'] = sys.exc_info()
        kwargs['traceback'] = traceback.format_stack()[:-2] + ["------- exception caught ---------->\n"]
        self.logMsg(*args, **kwargs)

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
        #lines = (traceback.format_stack()[:-skip]
            #+ ["  ---- exception caught ---->\n"]
            #+ traceback.format_tb(sys.exc_info()[2])
            #+ traceback.format_exception_only(*sys.exc_info()[:2]))
        #print topTraceback
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

    def fileName(self):
        """Get file name of log file.

          @return string: path to log file
        """
        ## return the log file currently used
        if self.logFile is None:
            return "tempLog.txt"
        else:
            return self.logFile.name()

    def getLogDir(self):
        """Get log directory.

          @return string: path to log directory
        """
        return None

    def saveEntry(self, entry):
        """Append log entry to log file.

          @param dict entry: log file entry
        """
        with self.lock:
            configfile.appendConfigFile(entry, self.fileName())

