# -*- coding: utf-8 -*-
"""
Mutex.py - Stand-in extension of Qt's QMutex and QRecursiveMutex classes.

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
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more information.
"""

__all__ = ['Mutex', 'RecursiveMutex']

from PySide2.QtCore import QMutex as _QMutex
from PySide2.QtCore import QRecursiveMutex as _QRecursiveMutex
from typing import Optional, Union


_RealNumber = Union[int, float]


class Mutex(_QMutex):
    """ Extends QMutex which serves as access serialization between threads.

    This class provides:
    * Drop-in replacement for threading.Lock
    * Context management (enter/exit)
    """

    def acquire(self, blocking: Optional[bool] = True, timeout: Optional[_RealNumber] = -1) -> bool:
        """ Mimics threading.Lock.acquire() to allow this class as a drop-in replacement.

        @param bool blocking: If True, this method will be blocking (indefinitely or for up to
                              <timeout> seconds) until the mutex has been locked. If False this
                              method will return immediately independent of the ability to lock.
        @param float timeout: Timeout in seconds specifying the maximum wait time for the mutex to
                              be able to lock. Negative numbers correspond to infinite wait time.
                              This parameter is ignored for <blocking> == False.
        """
        if blocking:
            # Convert to milliseconds for QMutex
            return self.tryLock(max(-1, int(timeout * 1000)))
        return self.tryLock()

    def release(self) -> None:
        """ Mimics threading.Lock.release() to allow this class as a drop-in replacement.
        """
        self.unlock()

    def __enter__(self):
        """ Enter context.

        @return Mutex: this mutex
        """
        self.lock()
        return self

    def __exit__(self, *args):
        """ Exit context.

        @param args: context arguments (type, value, traceback)
        """
        self.unlock()


# Compatibility workaround for PySide2 vs. PySide6. In PySide2 we need to use QMutex with an
# initializer argument to construct a recursive mutex but in PySide6 we need to subclass
# QRecursiveMutex. Check if QRecursiveMutex class has all API members (indicating it's PySide6).
if all(hasattr(_QRecursiveMutex, attr) for attr in ('lock', 'unlock', 'tryLock')):
    class RecursiveMutex(_QRecursiveMutex):
        """ Extends QRecursiveMutex which serves as access serialization between threads.

        This class provides:
        * Drop-in replacement for threading.Lock
        * Context management (enter/exit)

        NOTE: A recursive mutex is much more expensive than using a regular mutex. So consider
        refactoring your code to use a simple mutex before using this object.
        """

        def acquire(self, blocking: Optional[bool] = True,
                    timeout: Optional[_RealNumber] = -1) -> bool:
            """ Mimics threading.Lock.acquire() to allow this class as a drop-in replacement.

            @param bool blocking: If True, this method will be blocking (indefinitely or for up to
                                  <timeout> seconds) until the mutex has been locked. If False this
                                  method will return immediately independent of the ability to lock.
            @param float timeout: Timeout in seconds specifying the maximum wait time for the mutex to
                                  be able to lock. Negative numbers correspond to infinite wait time.
                                  This parameter is ignored for <blocking> == False.
            """
            if blocking:
                # Convert to milliseconds for QMutex
                return self.tryLock(max(-1, int(timeout * 1000)))
            return self.tryLock()

        def release(self) -> None:
            """ Mimics threading.Lock.release() to allow this class as a drop-in replacement.
            """
            self.unlock()

        def __enter__(self):
            """ Enter context.

            @return RecursiveMutex: this mutex
            """
            self.lock()
            return self

        def __exit__(self, *args):
            """ Exit context.

            @param args: context arguments (type, value, traceback)
            """
            self.unlock()
else:
    class RecursiveMutex(Mutex):
        """ Extends QRecursiveMutex which serves as access serialization between threads.

        This class provides:
        * Drop-in replacement for threading.Lock
        * Context management (enter/exit)

        NOTE: A recursive mutex is much more expensive than using a regular mutex. So consider
        refactoring your code to use a simple mutex before using this object.
        """
        def __init__(self):
            super().__init__(_QMutex.Recursive)
