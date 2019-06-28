# -*- coding: utf-8 -*-

import abc
from core.util.interfaces import InterfaceMetaclass


class SecondTestInterface(metaclass=InterfaceMetaclass):
    """
    """

    _modclass = 'SecondTestInterface'
    _modtype = 'interface'

    @abc.abstractmethod
    def test(self):
        """
        This is for testing

        @return int: error code (0:OK, -1:error)
        """
        pass
