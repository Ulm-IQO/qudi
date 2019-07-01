# -*- coding: utf-8 -*-

import abc
from core.util.interfaces import InterfaceMetaclass
from core.util.interfaces import interface_method


class FirstTestInterface(metaclass=InterfaceMetaclass):
    """
    """

    _modclass = 'FirstTestInterface'
    _modtype = 'interface'

    @interface_method
    def test(self):
        """
        This is for testing

        @return int: error code (0:OK, -1:error)
        """
        pass
