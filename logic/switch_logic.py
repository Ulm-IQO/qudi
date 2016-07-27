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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from collections import OrderedDict
from pyqtgraph.Qt import QtCore

class SwitchLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """
    _modclass = 'switch'
    _modtype = 'logic'
    _out = {'switchlogic': 'SwitchLogic'}

    def __init__(self, config, **kwargs):
        """ Create logic object

          @param dict config: configuration in a dict
          @param dict kwargs: additional parameters as a dict
        """
        super().__init__(config=config, **kwargs)

        # dynamic number of 'in' connectors depending on config
        if 'connect' in config:
            for connector in config['connect']:
                self.connector['in'][connector] = OrderedDict()
                self.connector['in'][connector]['class'] = 'SwitchInterface'
                self.connector['in'][connector]['object'] = None

    def on_activate(self, e):
        """ Prepare logic module for work.

          @param object e: Fysom state change notification
        """
        self.switches = dict()
        for connector in self.connector['in']:
            hwname = self.connector['in'][connector]['object']._name
            self.switches[hwname] = dict()
            for i in range(self.connector['in'][connector]['object'].getNumberOfSwitches()):
                self.switches[hwname][i] = self.connector['in'][connector]['object']

    def on_deactivate(self, e):
        """ Deactivate modeule.

          @param object e: Fysom state change notification
        """
        self.switches = dict()

