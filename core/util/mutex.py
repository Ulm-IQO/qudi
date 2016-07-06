# -*- coding: utf-8 -*-
"""
Mutex.py -  Stand-in extension of Qt's QMutex class

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

from pyqtgraph.Qt import QtCore
import traceback
import collections


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
        self.l = QtCore.QMutex()  # for serializing access to self.tb
        self.tb = []
        self.debug = kargs.pop('debug', False) # True to enable debugging functions

    def tryLock(self, timeout=None, id=None):
        if timeout is None:
            locked = QtCore.QMutex.tryLock(self)
        else:
            locked = QtCore.QMutex.tryLock(self, timeout)

        if self.debug and locked:
            self.l.lock()
            try:
                if id is None:
                    self.tb.append(''.join(traceback.format_stack()[:-1]))
                else:
                    self.tb.append("  " + str(id))
                #print 'trylock', self, len(self.tb)
            finally:
                self.l.unlock()
        return locked
        
    def lock(self, id=None):
        c = 0
        waitTime = 5000  # in ms
        while True:
            if self.tryLock(waitTime, id):
                break
            c += 1
            if self.debug:
                self.l.lock()
                try:
                    print("Waiting for mutex lock ({:.1} sec). Traceback follows:".format(c*waitTime/1000.))
                    traceback.print_stack()
                    if len(self.tb) > 0:
                        print("Mutex is currently locked from:\n", self.tb[-1])
                    else:
                        print("Mutex is currently locked from [???]")
                finally:
                    self.l.unlock()
        #print 'lock', self, len(self.tb)

    def unlock(self):
        QtCore.QMutex.unlock(self)
        if self.debug:
            self.l.lock()
            try:
                #print 'unlock', self, len(self.tb)
                if len(self.tb) > 0:
                    self.tb.pop()
                else:
                    raise Exception("Attempt to unlock mutex before it has been locked")
            finally:
                self.l.unlock()

    def acquire(self, blocking=True):
        """Mimics threading.Lock.acquire() to allow this class as a drop-in replacement.
        """
        return self.tryLock()
        
    def release(self): 
        """Mimics threading.Lock.release() to allow this class as a drop-in replacement.
        """
        self.unlock()

    def depth(self):
        self.l.lock()
        n = len(self.tb)
        self.l.unlock()
        return n

    def traceback(self):
        self.l.lock()
        try:
            ret = self.tb[:]
        finally:
            self.l.unlock()
        return ret

    def __exit__(self, *args):
        self.unlock()

    def __enter__(self):
        self.lock()
        return self


class RecursiveMutex(Mutex):
    def __init__(self, **kwds):
        kwds['recursive'] = True
        Mutex.__init__(self, **kwds)


class MutexLocker:
    def __init__(self, lock):
        #print self, "lock on init",lock, lock.depth()
        self.lock = lock
        self.lock.lock()
        self.unlockOnDel = True

    def unlock(self):
        #print self, "unlock by req",self.lock, self.lock.depth()
        self.lock.unlock()
        self.unlockOnDel = False


    def relock(self):
        #print self, "relock by req",self.lock, self.lock.depth()
        self.lock.lock()
        self.unlockOnDel = True

    def __del__(self):
        if self.unlockOnDel:
            #print self, "Unlock by delete:", self.lock, self.lock.depth()
            self.lock.unlock()
        #else:
            #print self, "Skip unlock by delete", self.lock, self.lock.depth()

    def __exit__(self, *args):
        if self.unlockOnDel:
            self.unlock()

    def __enter__(self):
        return self

    def mutex(self):
        return self.lock

#import functools
#def methodWrapper(fn, self, *args, **kargs):
    #print repr(fn), repr(self), args, kargs
    #obj = self.__wrapped_object__()
    #return getattr(obj, fn)(*args, **kargs)
    
##def WrapperClass(clsName, parents, attrs):
    ##for parent in parents:
        ##for name in dir(parent):
            ##attr = getattr(parent, name)
            ##if callable(attr) and name not in attrs:
                ##attrs[name] = functools.partial(funcWrapper, name)
    ##return type(clsName, parents, attrs)

#def WrapperClass(name, bases, attrs):
    #for n in ['__getattr__', '__setattr__', '__getitem__', '__setitem__']:
        #if n not in attrs:
            #attrs[n] = functools.partial(methodWrapper, n)
    #return type(name, bases, attrs)

#class WrapperClass(type):
    #def __new__(cls, name, bases, attrs):
        #fakes = []
        #for n in ['__getitem__', '__setitem__']:
            #if n not in attrs:
                #attrs[n] = lambda self, *args: getattr(self, n)(*args)
                #fakes.append(n)
        #print fakes
        #typ = type(name, bases, attrs)
        #typ.__faked_methods__ = fakes
        #return typ
    
    #def __init__(self, name, bases, attrs):
        #print self.__faked_methods__
        #for n in self.__faked_methods__:
            #self.n = None
        
    
    
#class ThreadsafeWrapper(object):
    #def __init__(self, obj):
        #self.__TSW_object__ = obj
        
    #def __wrapped_object__(self):
        #return self.__TSW_object__
    

class ThreadsafeWrapper(object):
    """Wrapper that makes access to any object thread-safe (within reasonable limits).

       Mostly tested for wrapping lists, dicts, etc.
       NOTE: Do not instantiate directly; use threadsafe(obj) instead.
    - all method calls and attribute/item accesses are protected by mutex
    - optionally, attribute/item accesses may return protected objects
    - can be manually locked for extended operations
    """
    def __init__(self, obj, recursive=False, reentrant=True):
        """
        If recursive is True, then sub-objects accessed from obj are wrapped threadsafe as well.
        If reentrant is True, then the object can be locked multiple times from the same thread."""

        self.__TSOwrapped_object__ = obj
            
        if reentrant:
            self.__TSOwrap_lock__ = Mutex(QtCore.QMutex.Recursive)
        else:
            self.__TSOwrap_lock__ = Mutex()
        self.__TSOrecursive__ = recursive
        self.__TSOreentrant__ = reentrant
        self.__TSOwrapped_objs__ = {}

    def lock(self, id=None):
        self.__TSOwrap_lock__.lock(id=id)
        
    def tryLock(self, timeout=None, id=None):
        self.__TSOwrap_lock__.tryLock(timeout=timeout, id=id)
        
    def unlock(self):
        self.__TSOwrap_lock__.unlock()
        
    def unwrap(self):
        return self.__TSOwrapped_object__

    def __safe_call__(self, fn, *args, **kargs):
        obj = self.__wrapped_object__()
        ret = getattr(obj, fn)(*args, **kargs)
        return self.__wrap_object__(ret)

    def __getattr__(self, attr):
        #try:
            #return object.__getattribute__(self, attr)
        #except AttributeError:
        with self.__TSOwrap_lock__:
            val = getattr(self.__wrapped_object__(), attr)
            #if callable(val):
                #return self.__wrap_object__(val)
            return self.__wrap_object__(val)

    def __setattr__(self, attr, val):
        if attr[:5] == '__TSO':
            #return object.__setattr__(self, attr, val)
            self.__dict__[attr] = val
            return
        with self.__TSOwrap_lock__:
            return setattr(self.__wrapped_object__(), attr, val)
            
    def __wrap_object__(self, obj):
        if not self.__TSOrecursive__:
            return obj
        if obj.__class__ in [int, float, str, str, tuple]:
            return obj
        if id(obj) not in self.__TSOwrapped_objs__:
            self.__TSOwrapped_objs__[id(obj)] = threadsafe(obj, recursive=self.__TSOrecursive__, reentrant=self.__TSOreentrant__)
        return self.__TSOwrapped_objs__[id(obj)]
        
    def __wrapped_object__(self):
        #if isinstance(self.__TSOwrapped_object__, weakref.ref):
            #return self.__TSOwrapped_object__()
        #else:
        return self.__TSOwrapped_object__
    
def mkMethodWrapper(name):
    return lambda self, *args, **kargs: self.__safe_call__(name, *args, **kargs)    
    
def threadsafe(obj, *args, **kargs):
    """Return a thread-safe wrapper around obj. (see ThreadsafeWrapper)
    args and kargs are passed directly to ThreadsafeWrapper.__init__()
    This factory function is necessary for wrapping special methods (like __getitem__)"""

    if type(obj) in [int, float, str, str, tuple, type(None), bool]:
        return obj
    clsName = 'Threadsafe_' + obj.__class__.__name__
    attrs = {}
    ignore = set(['__new__', '__init__', '__class__', '__hash__', '__getattribute__', '__getattr__', '__setattr__'])
    for n in dir(obj):
        if not n.startswith('__') or n in ignore:
            continue
        v = getattr(obj, n)
        if isinstance(v, collections.Callable):
            attrs[n] = mkMethodWrapper(n)
    typ = type(clsName, (ThreadsafeWrapper,), attrs)
    return typ(obj, *args, **kargs)
        
    
if __name__ == '__main__':
    d = {'x': 3, 'y': [1,2,3,4], 'z': {'a': 3}, 'w': (1,2,3,4)}
    t = threadsafe(d, recursive=True, reentrant=False)
