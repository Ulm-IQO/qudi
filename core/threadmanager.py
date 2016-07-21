# -*- coding: utf-8 -*-
"""
This file contains the QuDi thread manager class.

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
"""


import logging
logger = logging.getLogger(__name__)
from pyqtgraph.Qt import QtCore
from collections import OrderedDict
from .util.mutex import Mutex


class ThreadManager(QtCore.QAbstractTableModel):
    """ This class keeps track of all the QThreads that are needed somewhere.
    """
    def __init__(self):
        super().__init__()
        self._threads = OrderedDict()
        self.lock = Mutex()
        self.headers = ['Name', 'Thread']

    def newThread(self, name):
        """ Create a new thread with a name, return its object
          @param str name: unique name of thread

          @return QThread: new thred, none if failed
        """
        logger.debug('Creating thread: \"{0}\".'.format(name))
        with self.lock:
            if 'name' in self._threads:
                return None
            row = len(self._threads)
            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self._threads[name] = ThreadItem(name)
            self._threads[name].sigThreadHasQuit.connect(self.cleanupThread)
            self.endInsertRows()
        return self._threads[name].thread

    def quitThread(self, name):
        """Stop event loop of QThread.

          @param str name: unique thread name
        """
        if name in self._threads:
            logger.debug('Quitting thread {0}.'.format(name))
            self._threads[name].thread.quit()
        else:
            logger.debug('You tried quitting a nonexistent thread {0}.'
                    ''.format(name))

    def joinThread(self, name, time=None):
        """Stop event loop of QThread.

          @param str name: unique thread name
          @param int time: timeout for waiting in msec
        """
        if name in self._threads:
            logger.debug('Waiting for thread {0} to end.'.format(name))
            if time is None:
                self._threads[name].thread.wait()
            else:
                self._threads[name].thread.wait(time)
        else:
            logger.debug('You tried waiting for a nonexistent thread {0}.'
                    ''.format(name))

    def cleanupThread(self, name):
        """Remove thread from thread list if it is not running anymore.

          @param str name: unique thread name
        """
        logger.debug('Cleaning up thread {0}.'.format(name))
        if 'name' in self._threads and not self._threads[name].thread.isRunning():
            with self.lock:
                row = self.getItemNumberByKey(name)
                self.beginRemoveRows(QtCore.QModelIndex(), row, row)
                self._threads.pop(name)
                self.endRemoveRows()

    def quitAllThreads(self):
        """Stop event loop of all QThreads.
        """
        logger.debug('Quit all threads.')
        for name in self._threads:
            self._threads[name].thread.quit()

    def getItemByNumber(self, n):
        i = 0
        length = len(self._threads)
        if n < 0 or n >= length:
            raise IndexError
        it = iter(self._threads)
        key = next(it)
        while(i<n):
            key = next(it)
            i += 1
        return key, self._threads[key]

    def getItemNumberByKey(self, key):
        i = 0
        it = iter(self._threads)
        newkey = next(it)
        while(key != newkey):
            newkey = next(it)
            i += 1
        return i

    def rowCount(self, parent = QtCore.QModelIndex()):
        """ Gives the number of threads registered.

          @return int: number of threads
        """
        return len(self._threads)

    def columnCount(self, parent = QtCore.QModelIndex()):
        """ Gives the number of data fields of a thread.

          @return int: number of thread data fields
        """
        return 2

    def flags(self, index):
        """ Determines what can be done with entry cells in the table view.

          @param QModelIndex index: cell fo which the flags are requested

          @return Qt.ItemFlags: actins allowed fotr this cell
        """
        return QtCore.Qt.ItemIsEnabled |  QtCore.Qt.ItemIsSelectable

    def data(self, index,  role):
        """ Get data from model for a given cell. Data can have a role that affects display.

          @param QModelIndex index: cell for which data is requested
          @param ItemDataRole role: role for which data is requested

          @return QVariant: data for given cell and role
        """
        if not index.isValid():
            return None
        elif role == QtCore.Qt.DisplayRole:
            item = self.getItemByNumber(index.row())
            if index.column() == 0:
               return item[1].name
            elif index.column() == 1:
                return item[1].thread
            else:
                return None
        else:
            return None

    def headerData(self, section, orientation, role = QtCore.Qt.DisplayRole):
        """ Data for the table view headers.

          @param int section: number of the column to get header data for
          @param Qt.Orientation: orientation of header (horizontal or vertical)
          @param ItemDataRole: role for which to get data

          @return QVariant: header data for given column and role
        """
        if section < 0 and section > 1:
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        elif orientation != QtCore.Qt.Horizontal:
            return None
        else:
            return self.header[section]

class ThreadItem(QtCore.QObject):
    """ This class represents a QThread.

      @signal str sigThreadHasQuit: sents a signal containig the name of the thread tha has quit
    """
    sigThreadHasQuit = QtCore.Signal(str)

    def __init__(self, name):
        """ Create a ThreadItwm object

          @param str name: unique name of the thread
        """
        super().__init__()
        self.thread = QtCore.QThread()
        self.thread.setObjectName(name)
        self.name = name
        self.thread.finished.connect(self.myThreadHasQuit)

    def myThreadHasQuit(self):
        """ Signal handler for quitting thread.
            Re-emits signal containing the unique thread name.
        """
        self.sigThreadHasQuit.emit(self.name)


