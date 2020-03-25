# -*- coding: utf-8 -*-
"""
This file contains the Qudi remotemodules object manager class.

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

import logging
import weakref
from functools import partial
from qudi.core.util.mutex import RecursiveMutex
from qtpy import QtCore

logger = logging.getLogger(__name__)


class ThreadManager(QtCore.QAbstractListModel):
    """ This class keeps track of all the QThreads that are needed somewhere.

    Using this class is thread-safe.
    """
    _instance = None
    _lock = RecursiveMutex()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None or cls._instance() is None:
                obj = super().__new__(cls, *args, **kwargs)
                cls._instance = weakref.ref(obj)
                return obj
            raise Exception('Only one ThreadManager instance per process possible (Singleton). '
                            'Please use ThreadManager.instance() to get a reference to the already '
                            'created instance.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._threads = list()
        self._thread_names = list()

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                return None
            return cls._instance()

    @property
    def thread_names(self):
        with self._lock:
            return self._thread_names.copy()

    def get_new_thread(self, name):
        """ Create and return a new QThread with objectName <name>

        @param str name: unique name of thread

        @return QThread: new thread, none if failed
        """
        with self._lock:
            logger.debug('Creating thread: "{0}".'.format(name))
            if name in self._thread_names:
                return None
            thread = QtCore.QThread()
            thread.setObjectName(name)
            self.register_thread(thread)
            return thread

    @QtCore.Slot(QtCore.QThread)
    def register_thread(self, thread):
        """ Add QThread to ThreadManager.

        @param QtCore.QThread thread: thread to register with unique objectName
        """
        with self._lock:
            name = thread.objectName()
            if name in self._thread_names:
                if self.get_thread_by_name(name) is thread:
                    return None
                raise Exception('Different thread with name "{0}" already registered in '
                                'ThreadManager'.format(name))

            row = len(self._threads)
            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self._threads.append(thread)
            self._thread_names.append(name)
            thread.finished.connect(
                partial(self.unregister_thread, name=name), QtCore.Qt.QueuedConnection)
            self.endInsertRows()

    @QtCore.Slot(str)
    @QtCore.Slot(QtCore.QThread)
    def unregister_thread(self, name):
        """ Remove thread from ThreadManager.

        @param str name: unique thread name
        """
        with self._lock:
            if isinstance(name, QtCore.QThread):
                name = name.objectName()
            if name in self._thread_names:
                index = self._thread_names.index(name)
                if self._threads[index].isRunning():
                    self.quit_thread(name)
                    return
                logger.debug('Cleaning up thread {0}.'.format(name))
                self.beginRemoveRows(QtCore.QModelIndex(), index, index)
                del self._threads[index]
                del self._thread_names[index]
                self.endRemoveRows()

    @QtCore.Slot(str)
    @QtCore.Slot(QtCore.QThread)
    def quit_thread(self, name):
        """ Stop event loop of QThread.

        @param str name: unique thread name
        """
        with self._lock:
            if isinstance(name, QtCore.QThread):
                thread = name
            else:
                thread = self.get_thread_by_name(name)
            if thread is None:
                logger.debug('You tried quitting a nonexistent thread {0}.'.format(name))
            else:
                logger.debug('Quitting thread {0}.'.format(name))
                thread.quit()

    @QtCore.Slot(str)
    @QtCore.Slot(str, int)
    @QtCore.Slot(QtCore.QThread)
    @QtCore.Slot(QtCore.QThread, int)
    def join_thread(self, name, time=None):
        """ Wait for stop of QThread event loop.

        @param str name: unique thread name
        @param int time: timeout for waiting in msec
        """
        with self._lock:
            if isinstance(name, QtCore.QThread):
                thread = name
            else:
                thread = self.get_thread_by_name(name)
            if thread is None:
                logger.debug('You tried waiting for a nonexistent thread {0}.'.format(name))
            else:
                logger.debug('Waiting for thread {0} to end.'.format(name))
                if time is None:
                    thread.wait()
                else:
                    thread.wait(time)

    @QtCore.Slot()
    @QtCore.Slot(int)
    def quit_all_threads(self, thread_timeout=10000):
        """ Stop event loop of all QThreads.
        """
        with self._lock:
            logger.debug('Quit all threads.')
            for thread in self._threads:
                thread.quit()
                if not thread.wait(int(thread_timeout)):
                    logger.error('Waiting for thread {0} timed out.'.format(thread.objectName()))

    def get_thread_by_name(self, name):
        """ Get registered QThread instance by its objectName

        @param str name: objectName of the QThread to return
        @return QThread: The registered thread object
        """
        with self._lock:
            try:
                index = self._thread_names.index(name)
                return self._threads[index]
            except ValueError:
                return None

    # QAbstractListModel interface methods follow below
    def rowCount(self, parent=None, *args, **kwargs):
        """
        Gives the number of threads registered.

        @return int: number of threads
        """
        with self._lock:
            return len(self._threads)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """
        Data for the list view header.

        @param int section: column/row index to get header data for
        @param QtCore.Qt.Orientation orientation: orientation of header (horizontal or vertical)
        @param QtCore.ItemDataRole role: data access role

        @return str: header data for given column/row and role
        """
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal and section == 0:
            return 'Thread Name'
        return None

    def data(self, index, role):
        """
        Get data from model for a given cell. Data can have a role that affects display.

        @param QtCore.QModelIndex index: cell for which data is requested
        @param QtCore.Qt.ItemDataRole role: data access role of request

        @return QVariant: data for given cell and role
        """
        with self._lock:
            row = index.row()
            if index.isValid() and role == QtCore.Qt.DisplayRole and 0 <= row < len(self._threads):
                if index.column() == 0:
                    return self._thread_names[row]
            return None

    def flags(self, index):
        """ Determines what can be done with entry cells in the table view.

          @param QModelIndex index: cell fo which the flags are requested

          @return Qt.ItemFlags: actins allowed fotr this cell
        """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
