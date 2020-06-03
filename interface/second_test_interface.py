# -*- coding: utf-8 -*-

from core.interface import abstract_interface_method
from core.interface import interface_method, abstract_interface_method
from core.meta import InterfaceMetaclass


class SecondTestInterface(metaclass=InterfaceMetaclass):
    """ This interface is used with first_test_interface to demo the use of two interfaces with collision in naming.
    See the documentation how_to_hardware_with_multiple_interfaces.md for more detail.
    """

    @abstract_interface_method
    def test(self):
        """
        This is for testing

        @return int: error code (0:OK, -1:error)
        """
        pass


    @abstract_interface_method
    def another_method(self):
        """
        This is for testing

        @return int: error code (0:OK, -1:error)
        """
        pass