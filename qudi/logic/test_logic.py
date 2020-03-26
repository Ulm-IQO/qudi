# -*- coding: utf-8 -*-

"""
This file contains a test module.
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

from logic.generic_logic import GenericLogic
from core.connector import Connector
from core.statusvariable import StatusVar


class TestLogic(GenericLogic):
    """ This is the Logic class for testing. """

    # connectors
    firsthardware = Connector(interface='FirstTestInterface')
    secondhardware = Connector(interface='SecondTestInterface')

    testvar = StatusVar(name='testvar', default=None)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        return

    def on_activate(self):
        """	
        Initialisation performed during activation of the module.
        """
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.	
        """
        return

    def call_test1(self):
        return self.firsthardware().test()

    def call_test2(self):
        return self.secondhardware().test()
