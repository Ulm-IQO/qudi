# -*- coding: utf-8 -*-
"""
Mutex.py -  Stand-in extension of Qt's QMutex class

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

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

from qtpy import QtCore
import traceback
import logging
logger = logging.getLogger(__name__)


class Mutex(QtCore.QMutex):
    """Extends QMutex (which serves as access serialization between threads).

    This class provides:
    * Warning messages when a mutex stays locked for a long time.
      (if initialized with debug=True)
    * Drop-in replacement for threading.Lock
    * Context management (enter/exit)
    """

    def __init__(self, *args, **kargs):
        if kargs.get('recursive', False):
            args = (QtCore.QMutex.Recursive,)
        QtCore.QMutex.__init__(self, *args)
        self.mutex = QtCore.QMutex()  # for serializing access to self.tb
        self.tb = []
        self.debug = kargs.pop('debug', False)  # True to enable debugging functions

    def tryLock(self, timeout=None, id=None):
        """ Try to lock  the mutex.

            @param int timeout: give up after this many milliseconds
            @param id: debug id

            @return bool: whether locking succeeded
        """
        if timeout is None:
            locked = QtCore.QMutex.tryLock(self)
        else:
            locked = QtCore.QMutex.tryLock(self, timeout)

        if self.debug and locked:
            self.mutex.lock()
            try:
                if id is None:
                    self.tb.append(''.join(traceback.format_stack()[:-1]))
                else:
                    self.tb.append("  " + str(id))
            finally:
                self.mutex.unlock()
        return locked

    def lock(self, id=None):
        """ Lock mutex. Will try again every 5 seconds.

            @param id: debug id
        """
        c = 0
        wait_time = 5000  # in ms
        while True:
            if self.tryLock(wait_time, id):
                break
            c += 1
            if self.debug:
                self.mutex.lock()
                try:
                    logger.debug('Waiting for mutex lock ({:.1} sec).'
                                 'Traceback follows:'.format(c*wait_time/1000.))
                    logger.debug(''.join(traceback.format_stack()))
                    if len(self.tb) > 0:
                        logger.debug('Mutex is currently locked from: {0}\n'.format(self.tb[-1]))
                    else:
                        logger.debug('Mutex is currently locked from [???]')
                finally:
                    self.mutex.unlock()

    def unlock(self):
        """ Unlock mutex.
        """
        QtCore.QMutex.unlock(self)
        if self.debug:
            self.mutex.lock()
            try:
                if len(self.tb) > 0:
                    self.tb.pop()
                else:
                    raise Exception("Attempt to unlock mutex before it has been locked")
            finally:
                self.mutex.unlock()

    def acquire(self, blocking=True):
        """Mimics threading.Lock.acquire() to allow this class as a drop-in replacement.
        """
        return self.tryLock()

    def release(self):
        """Mimics threading.Lock.release() to allow this class as a drop-in replacement.
        """
        self.unlock()

    def depth(self):
        """ Depth of traceback.

            @return int: depth of traceback
        """
        self.mutex.lock()
        n = len(self.tb)
        self.mutex.unlock()
        return n

    def traceback(self):
        """ Get traceback.

            @return list: traceback
        """
        self.mutex.lock()
        try:
            ret = self.tb[:]
        finally:
            self.mutex.unlock()
        return ret

    def __exit__(self, *args):
        """ Exit context.
        
            @param args: context arguments
        """
        self.unlock()

    def __enter__(self):
        """ Enter context.
        
            @param args: context arguments

            @return QMutex: this mutex
        """
        self.lock()
        return self


class RecursiveMutex(Mutex):
    """ Mutex that can be taken recursively.
    """
    def __init__(self, **kwds):
        kwds['recursive'] = True
        Mutex.__init__(self, **kwds)
