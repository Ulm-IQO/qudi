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
from core.util.interfaces import interface_method


class MyHardwareClass(Base, SecondTestInterface, FirstTestInterface):
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

    # @interface_method
    # def test(self):
    #     return super().test()
    #
    @FirstTestInterface.test.register('FirstTestInterface')
    def test1(self):
        """
        """
        print('FirstTestInterface: test called', self.var)
        return 1

    @SecondTestInterface.test.register('SecondTestInterface')
    def test2(self):
        """
        """
        print('SecondTestInterface: test called', self.var)
        return 2

    def derp(self):
        pass
