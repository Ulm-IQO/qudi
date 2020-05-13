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
from interface.first_test_interface import FirstTestInterface
from interface.second_test_interface import SecondTestInterface
from core.interface import interface_method


class MyHardwareClass(Base, SecondTestInterface, FirstTestInterface):
    """
    This is just a dummy hardware class to be used with SimpleDataReaderLogic.
    """

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.var = 42

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    ################################################################################################
    # You can either use the interface method decorator concept like this:
    ################################################################################################
    @interface_method
    def test(self):
        print('Default implementation: test called', self.var)
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

    @interface_method
    def another_method(self):
        print('Default implementation: another_method called', self.var)
        return 0

    @another_method.register('FirstTestInterface')
    def test3(self):
        """
        """
        print('FirstTestInterface: another_method called', self.var)
        return 1

    @interface_method
    def third_method(self):
        print('Default implementation: third_method called', self.var)
        return 0

    @third_method.register('SecondTestInterface')
    def test4(self):
        """
        """
        print('SecondTestInterface: third_method called', self.var)
        return 2

    ################################################################################################
    # ... or like this:
    ################################################################################################
    # # @SecondTestInterface.test.register('FirstTestInterface') would also work
    # @FirstTestInterface.test.register('FirstTestInterface')
    # def test1(self):
    #     """
    #     """
    #     print('FirstTestInterface: test called', self.var)
    #     return 1
    #
    # # @FirstTestInterface.test.register('SecondTestInterface') would also work
    # @SecondTestInterface.test.register('SecondTestInterface')
    # def test2(self):
    #     """
    #     """
    #     print('SecondTestInterface: test called', self.var)
    #     return 2

    # @FirstTestInterface.something_else.register('FirstTestInterface')
    # def derp(self):
    #     print('YUPP!!!')

    ################################################################################################
    # Or you can just override the interface method alltogether:
    ################################################################################################
    # def test(self):
    #     print('I have taken over both interfaces... you have no power here!')
    #     return 'YOU DIED!'
