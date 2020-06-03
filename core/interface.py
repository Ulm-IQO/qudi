# -*- coding: utf-8 -*-
"""
Decorators and objects used for qudi interfaces

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
top-level directory of this distribution and at
<https://github.com/Ulm-IQO/qudi/>
"""

from abc import abstractmethod


class InterfaceMethod:
    """
    This object can serve as a replacement (via decorator "@interface_method") for qudi interface
    methods.
    It is possible to register several callables, each associated to a unique interface class name.
    The registered callables can all be called using the decorated method name and adding the
    keyword argument 'interface' to specify which registered interface to use.
    If the 'interface' keyword is omitted or the interface is not registered, the call will default
    to using the callable decorated by "@interface_method".

    This object is compatible with the abc.abstractmethod decorator.
    If it is declared as abstractmethod, you have to register at least one callable with an
    interface to count as "implemented".
    """

    _latest_unregistered_instances = dict()

    def __new__(cls, default_callable, is_abstractmethod=False):
        func_name = default_callable.__name__
        if func_name not in cls._latest_unregistered_instances:
            cls._latest_unregistered_instances[func_name] = super(InterfaceMethod, cls).__new__(cls)
        return cls._latest_unregistered_instances[func_name]

    def __init__(self, default_callable, is_abstractmethod=False):
        self._obj = None
        self._name = default_callable.__name__
        if is_abstractmethod:
            self._default_callable = abstractmethod(default_callable)
        else:
            self._default_callable = default_callable
        self.registered = dict()

    def __get__(self, obj=None, cls=None):
        # It is executed when this instance is referenced as a method
        if obj is not None and obj is not self._obj:
            self._default_callable = self._default_callable.__get__(obj, cls)
            for interface in self.registered:
                self.registered[interface] = self.registered[interface].__get__(obj, cls)
            self._obj = obj
        return self

    def __call__(self, *args, **kwargs):
        if self.__isabstractmethod__:
            raise NotImplementedError('No methods registered on abstractmethod {0}.'
                                      ''.format(self.default_callable.__name__))
        elif self.registered:
            raise Exception('No keyword given for call to overloaded interface method. '
                            'Valid keywords are: {0}'.format(tuple(self.registered)))
        return self._default_callable(*args, **kwargs)

    def __getitem__(self, key):
        if key not in self.registered:
            raise KeyError('No method registered for interface "{0}".'.format(key))
        return self.registered[key]

    def register(self, interface):
        """
        Decorator to register a callable to be used as overloaded function associated with a given
        interface class name <interface>.

        Example usage in a hardware module:

            @MyInterfaceClass.my_overloaded_method.register('MyInterfaceClass')
            def some_arbitrary_name1(self, *args, **kwargs):
                # Do something
                return

            @MyInterfaceClass.my_overloaded_method.register('MyOtherInterfaceClass')
            def some_arbitrary_name2(self, *args, **kwargs):
                # Do something else
                return

        @param str interface: Name of the interface class the decorated method is associated to
        @return: Decorator
        """
        def decorator(func):
            self.registered[interface] = func
            self.__isabstractmethod__ = False
            InterfaceMethod._latest_unregistered_instances.pop(self._name, None)
            return func
        return decorator

    # def __repr__(self):
    #     # Mock representer of bound default callable (will be bound method).
    #     return self._default_callable.__repr__()

    # Makes this object compatible with abc.abstractmethod
    @property
    def __isabstractmethod__(self):
        if hasattr(self._default_callable, '__isabstractmethod__'):
            return self._default_callable.__isabstractmethod__
        return False

    @__isabstractmethod__.setter
    def __isabstractmethod__(self, flag):
        if hasattr(self, '__isabstractmethod__'):
            self._default_callable.__isabstractmethod__ = bool(flag)


class ScalarConstraint:
    """
    Constraint definition for a scalar variable hardware parameter.
    """
    def __init__(self, min=0.0, max=0.0, step=0.0, default=0.0, unit=''):
        # allowed minimum value for parameter
        self.min = min
        # allowed maximum value for parameter
        self.max = max
        # allowed step size for parameter value changes (for spinboxes etc.)
        self.step = step
        # the default value for the parameter
        self.default = default
        # the unit of the parameter value(optional)
        self.unit = unit
        return


def abstract_interface_method(func):
    """
    Decorator to replace a simple interface method with an InterfaceMethod object instance that can
    register multiple method implementations by the same name and associate each with an interface.
    This enables a quasi-overloading of interface methods.
    Is compatible with abc.abstractmethod.

    @param callable func: The callable to be decorated
    @return InterfaceMethod: Instance of InterfaceMethod to replace the decorated callable
    """
    return InterfaceMethod(default_callable=func, is_abstractmethod=True)


def interface_method(func):
    """
    Decorator to replace a simple interface method with an InterfaceMethod object instance that can
    register multiple method implementations by the same name and associate each with an interface.
    This enables a quasi-overloading of interface methods.
    Is compatible with abc.abstractmethod.

    @param callable func: The callable to be decorated
    @return InterfaceMethod: Instance of InterfaceMethod to replace the decorated callable
    """
    return InterfaceMethod(default_callable=func)
