# -*- coding: utf-8 -*-
"""
Aggregate multiple switches.

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
from collections import OrderedDict


class SwitchLogic(GenericLogic):
    """ Logic module aggregating multiple hardware switches.
    """

    def __init__(self, config, **kwargs):
        """ Create logic object

          @param dict config: configuration in a dict
          @param dict kwargs: additional parameters as a dict
        """
        super().__init__(config=config, **kwargs)

        # dynamic number of 'in' connectors depending on config
        if 'connect' in config:
            for connector in config['connect']:
                self.connectors[connector] = OrderedDict()
                self.connectors[connector]['class'] = 'SwitchInterface'
                self.connectors[connector]['object'] = None

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self.switches = dict()
        for connector in self.connectors:
            hwname = self.get_connector(connector)._name
            self.switches[hwname] = dict()
            for i in range(self.get_connector(connector).getNumberOfSwitches()):
                self.switches[hwname][i] = self.get_connector(connector)

    def on_deactivate(self):
        """ Deactivate modeule.
        """
        self.switches = dict()

