# -*- coding: utf-8 -*-
"""
This is just a dummy hardware class to be used with TemplateLogic.

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

from core.module import Base
import time
import numpy as np
from interface.first_test_interface import FirstTestInterface
from interface.second_test_interface import SecondTestInterface


# def interface_decorator(func):
#     return InterfaceMethodReplacement(func)
#


class InterfaceDecorator:

    class InterfaceMethodReplacement(object):
        def __init__(self,  default_callable, obj=None, cls=None, method_type='function'):
            self.obj, self.cls, self.method_type = obj, cls, method_type
            self._default_callable = default_callable
            self._registered = dict()

        def __get__(self, obj=None, cls=None):
            # It is executed when decorated func is referenced as a method: cls.func or obj.func.
            print(obj, cls)
            if self.obj == obj and self.cls == cls:
                return self  # Use the same instance that is already processed by previous call to this __get__().

            method_type = (
                'staticmethod' if isinstance(self._default_callable, staticmethod) else
                'classmethod' if isinstance(self._default_callable, classmethod) else
                'instancemethod'
                # No branch for plain function - correct method_type for it is already set in __init__() defaults.
            )

            self._default_callable = self._default_callable.__get__(obj, cls)
            self.obj = obj
            self.cls = cls
            self.method_type = method_type
            return self
            # return object.__getattribute__(self, '__class__')(
            #     # Use specialized method_decorator (or descendant) instance, don't change current instance attributes - it leads to conflicts.
            #     self._default_callable.__get__(obj, cls), obj, cls,
            #     method_type)  # Use bound or unbound method with this underlying func.

        def __call__(self, *args, **kwargs):
            interface = kwargs.pop('interface', None)
            if interface:
                return self._registered[interface](self.obj, *args, **kwargs)
            return self._default_callable(*args, **kwargs)

        # def __getattribute__(self, attr_name):  # Hiding traces of decoration.
        #     if attr_name in (
        #     '__init__', '__get__', '__call__', '__getattribute__', '_default_callable', '_registered', 'obj', 'cls', 'method_type', 'register'):  # Our known names. '__class__' is not included because is used only with explicit object.__getattribute__().
        #         return object.__getattribute__(self, attr_name)  # Stopping recursion.
        #     # All other attr_names, including auto-defined by system in self, are searched in decorated self.func, e.g.: __module__, __class__, __name__, __doc__, im_*, func_*, etc.
        #     return getattr(self._default_callable,
        #                    attr_name)  # Raises correct AttributeError if name is not found in decorated self.func.
        #
        # def __repr__(self):  # Special case: __repr__ ignores __getattribute__.
        #     return self._default_callable.__repr__()

        def register(self, interface):
            def decorator(func):
                self._registered[interface] = func
                return None
            return decorator

    @staticmethod
    def interface_method(func):
        # def default_func(*args, **kwargs):
        #     return func(*args, **kwargs)
        return InterfaceDecorator.InterfaceMethodReplacement(func)


class MyHardwareClass(Base, FirstTestInterface, SecondTestInterface):
    """
    This is just a dummy hardware class to be used with SimpleDataReaderLogic.
    """
    _modclass = 'MyHardwareClass'
    _modtype = 'hardware'

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.var = 42

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    @InterfaceDecorator.interface_method
    def test(self):
        print('default implementation:', self.var)
        return 0

    @test.register('FirstTestInterface')
    def test1(self):
        """
        """
        print('FirstTestInterface: test called', self.var)
        return 1

    @test.register('SecondTestInterface')
    def test2(self):
        """
        """
        print('SecondTestInterface: test called', self.var)
        return 2

    def derp(self):
        pass
