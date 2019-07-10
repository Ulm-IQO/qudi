# -*- coding: utf-8 -*-

import abc
from core.interface import interface_method, abstract_interface_method
from core.meta import InterfaceMetaclass


class FirstTestInterface(metaclass=InterfaceMetaclass):
    """
    """

    _modclass = 'FirstTestInterface'
    _modtype = 'interface'

    @abstract_interface_method
    def test(self):
        """
        This is for testing

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abstract_interface_method
    def third_method(self):
        """
        This is for testing

        @return int: error code (0:OK, -1:error)
        """
        pass
