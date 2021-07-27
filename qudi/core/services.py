# -*- coding: utf-8 -*-
"""
This file contains the Qudi tools for remote module sharing via rpyc server.

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

__all__ = ('RemoteModulesService', 'QudiNamespaceService')

import rpyc
import weakref
import numpy as np
from functools import wraps
from inspect import signature, isfunction, ismethod

from qudi.util.mutex import Mutex
from qudi.util.models import DictTableModel
from qudi.util.network import netobtain
from qudi.core.logger import get_logger

logger = get_logger(__name__)


class _SharedModulesModel(DictTableModel):
    """ Derived dict model for GUI display elements
    """
    def __init__(self):
        super().__init__(headers='Shared Module')

    def data(self, index, role):
        """ Get data from model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return QVariant: data for given cell and role
        """
        data = super().data(index, role)
        if data is None:
            return None
        # second column returns weakref.ref object
        if index.column() == 1:
            data = data()
        return data


class RemoteModulesService(rpyc.Service):
    """ An RPyC service that has a module list.
    """
    ALIASES = ['RemoteModules']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = Mutex()
        self.shared_modules = _SharedModulesModel()

    def share_module(self, module):
        with self._thread_lock:
            if module.name in self.shared_modules:
                logger.warning(f'Module "{module.name}" already shared')
                return
            self.shared_modules[module.name] = weakref.ref(module)
            weakref.finalize(module, self.remove_shared_module, module.name)

    def remove_shared_module(self, module):
        with self._thread_lock:
            name = module if isinstance(module, str) else module.name
            self.shared_modules.pop(name, None)

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client connected to remote modules service from [{host}]:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing
        """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client [{host}]:{port:d} disconnected from remote modules service')

    def exposed_get_module_instance(self, name, activate=False):
        """ Return reference to a module in the shared module list.

        @param str name: unique module name

        @return object: reference to the module
        """
        with self._thread_lock:
            try:
                module = self.shared_modules.get(name, None)()
            except TypeError:
                logger.error(f'Client requested a module ("{name}") that is not shared.')
                return None
            if activate:
                if not module.activate():
                    logger.error(f'Unable to share requested module "{name}" with client. Module '
                                 f'can not be activated.')
                    return None
            return module.instance

    def exposed_get_available_module_names(self):
        """ Returns the currently shared module names independent of the current module state.

        @return tuple: Names of the currently shared modules
        """
        with self._thread_lock:
            return tuple(self.shared_modules)

    def exposed_get_loaded_module_names(self):
        """ Returns the currently shared module names for all modules that have been loaded
        (instantiated).

        @return tuple: Names of the currently shared and loaded modules
        """
        with self._thread_lock:
            all_modules = {name: ref() for name, ref in self.shared_modules.items()}
            return tuple(name for name, mod in all_modules.items() if
                         mod is not None and mod.instance is not None)

    def exposed_get_active_module_names(self):
        """ Returns the currently shared module names for all modules that are active.

        @return tuple: Names of the currently shared active modules
        """
        with self._thread_lock:
            all_modules = {name: ref() for name, ref in self.shared_modules.items()}
            return tuple(
                name for name, mod in all_modules.items() if mod is not None and mod.is_active
            )


class QudiNamespaceService(rpyc.Service):
    """ An RPyC service providing a namespace dict containing references to all active qudi module
    instances as well as a reference to the qudi application itself.
    """
    ALIASES = ['QudiNamespace']

    def __init__(self, *args, qudi, **kwargs):
        super().__init__(*args, **kwargs)
        self.__qudi_ref = weakref.ref(qudi)
        self._notifier_callbacks = dict()

        self.test = Test(111, 222)
        self.test_wrapper = ModuleRpycProxy(self.test)

    @property
    def _qudi(self):
        qudi = self.__qudi_ref()
        if qudi is None:
            raise RuntimeError('Dead qudi application reference encountered')
        return qudi

    @property
    def _module_manager(self):
        manager = self._qudi.module_manager
        if manager is None:
            raise RuntimeError('No module manager initialized in qudi application')
        return manager

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        try:
            self._notifier_callbacks[conn] = rpyc.async_(conn.root.modules_changed)
        except AttributeError:
            pass
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client connected to local module service from [{host}]:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing
        """
        self._notifier_callbacks.pop(conn, None)
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client [{host}]:{port:d} disconnected from local module service')

    def notify_module_change(self):
        logger.debug('Local module server has detected a module state change and sends async '
                     'notifier signals to all clients')
        for callback in self._notifier_callbacks.values():
            callback()

    def exposed_get_namespace_dict(self):
        """ Returns the instances of the currently active modules as well as a reference to the
        qudi application itself.

        @return dict: Names (keys) and object references (values)
        """
        # self._module_wrappers = {name: mod.instance for name, mod in self._module_manager.items() if mod.is_active}
        # self._module_wrappers['qudi'] = self._qudi
        mods = {name: mod.instance for name, mod in self._module_manager.items() if mod.is_active}
        mods['qudi'] = self._qudi
        mods['test_wrapper'] = self.test_wrapper
        return mods


class Test:
    def __init__(self, a=42, b=96):
        self.a = a
        self.b = b
        self.arr = np.random.rand(100)
        self.test = Test2()

    def __call__(self):
        print(type(self.arr))
        print(self.arr)

    def set_arr(self, new_arr=0):
        """ Yep, that's it

        @param numpy.ndarray new_arr: This is an array
        """
        print(type(new_arr))
        self.arr = new_arr


class Test2:
    def __init__(self, a=42, b=96):
        self.a = a
        self.b = b
        self.arr = np.random.rand(100)

    def __call__(self):
        print(type(self.arr))
        print(self.arr)

    def set_arr(self, new_arr):
        print(type(new_arr))
        self.arr = new_arr


class ModuleRpycProxy:
    """ Instances of this class serve as proxies for objects containing attributes of type
    OverloadedAttribute. It can be used to hide the overloading mechanism by fixing the overloaded
    attribute access key in a OverloadProxy instance. This allows for interfacing an overloaded
    attribute in the object represented by this proxy by normal "pythonic" means without the
    additional key-mapping lookup usually required by OverloadedAttribute.

    Heavily inspired by this python recipe under PSF License:
    https://code.activestate.com/recipes/496741-object-proxying/
    """

    __slots__ = ['_obj_ref', '__weakref__']

    def __init__(self, obj):
        object.__setattr__(self, '_obj_ref', weakref.ref(obj))

    # proxying (special cases)
    def __getattribute__(self, name):
        obj = object.__getattribute__(self, '_obj_ref')()
        attr = getattr(obj, name)
        if not name.startswith('__') and ismethod(attr) or isfunction(attr):
            sig = signature(attr)
            if len(sig.parameters) > 0:

                @wraps(attr)
                def wrapped(*args, **kwargs):
                    sig.bind(*args, **kwargs)
                    args = [netobtain(arg) for arg in args]
                    kwargs = {name: netobtain(arg) for name, arg in kwargs.items()}
                    return attr(*args, **kwargs)

                wrapped.__signature__ = sig
                return wrapped
        return attr

    def __delattr__(self, name):
        obj = object.__getattribute__(self, '_obj_ref')()
        return delattr(obj, name)

    def __setattr__(self, name, value):
        obj = object.__getattribute__(self, '_obj_ref')()
        return setattr(obj, name, netobtain(value))

    # factories
    _special_names = (
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__', '__contains__',
        '__delitem__', '__delslice__', '__div__', '__divmod__', '__eq__', '__float__',
        '__floordiv__', '__ge__', '__getitem__', '__getslice__', '__gt__', '__hash__', '__hex__',
        '__iadd__', '__iand__', '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__',
        '__imod__', '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__', '__long__',
        '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__', '__neg__', '__oct__', '__or__',
        '__pos__', '__pow__', '__radd__', '__rand__', '__rdiv__', '__rdivmod__', '__reduce__',
        '__reduce_ex__', '__repr__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__',
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__',
        '__rxor__', '__setitem__', '__setslice__', '__sub__', '__truediv__', '__xor__', 'next',
        '__str__', '__nonzero__'
    )

    @classmethod
    def _create_class_proxy(cls, theclass):
        """ creates a proxy for the given class
        """

        def make_method(method_name):

            def method(self, *args, **kw):
                obj = object.__getattribute__(self, '_obj_ref')()
                args = [netobtain(arg) for arg in args]
                kw = {key: netobtain(val) for key, val in kw.items()}
                return getattr(obj, method_name)(*args, **kw)

            return method

        # Add all special names to this wrapper class if they are present in the original class
        namespace = dict()
        for name in cls._special_names:
            if hasattr(theclass, name):
                namespace[name] = make_method(name)

        return type(f'{cls.__name__}({theclass.__name__})', (cls,), namespace)

    def __new__(cls, obj, *args, **kwargs):
        """ creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are passed to this
        class' __init__, so deriving classes can define an __init__ method of their own.

        note: _class_proxy_cache is unique per class (each deriving class must hold its own cache)
        """
        theclass = cls._create_class_proxy(obj.__class__)
        return object.__new__(theclass)
