# -*- coding: utf-8 -*-

import abc
from core.util.interfaces import InterfaceMetaclass


class FirstTestInterface(metaclass=InterfaceMetaclass):
    """
    """

    _modclass = 'FirstTestInterface'
    _modtype = 'interface'

    @abc.abstractmethod
    def test(self):
        """
        This is for testing

        @return int: error code (0:OK, -1:error)
        """
        pass
