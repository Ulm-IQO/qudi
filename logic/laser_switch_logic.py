# -*- coding: utf-8 -*-
"""
Aggregate multiple switches.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from collections import OrderedDict
from pyqtgraph.Qt import QtCore

class LaserSwitchLogic(GenericLogic):        
    """ Logic module agreggating multiple hardware switches.
    """
    _modclass = 'laserswitch'
    _modtype = 'logic'
        
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = { 'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)
        ## declare connectors
        self.connector['out']['laserswitchlogic'] = OrderedDict()
        self.connector['out']['laserswitchlogic']['class'] = 'laserswitchlogic'

        if 'connect' in config:
            for connector in config['connect']:
                self.connector['in'][connector] = OrderedDict()
                self.connector['in'][connector]['class'] = 'LaserSwitchInterface'
                self.connector['in'][connector]['object'] = None
        

    def activation(self, e):
        self.switches = list()
        for connector in self.connector['in']:
            switchHW = list()
            for i in range(self.connector['in'][connector]['object'].getNumberOfSwitches()):
                switchHW.append({
                    'hw': self.connector['in'][connector]['object'],
                    'n': i
                    })
            self.switches.append(switchHW)

    def deactivation(self, e):
        pass
