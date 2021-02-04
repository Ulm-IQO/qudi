# -*- coding: utf-8 -*-

"""
Motor management.

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

from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qudi.core.statusvariable import StatusVar


class MotorLogic(LogicBase):
    _motor = Connector(name='motor', interface='MotorInterface')
    _motor_velocity = StatusVar(name='motor_velocity', default=250)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Store references to connected modules
        self._motor().set_velocity({'x': self._motor_velocity, 'y': self._motor_velocity})
        self.constraints = self.get_constraints()

    def on_deactivate(self):
        self._motor().abort()

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.
        @return dict: dict with constraints for the motor hardware. These
                      constraints will be passed via the logic to the GUI so
                      that proper display elements with boundary conditions
                      could be made.
        """
        constraints = self._motor().get_constraints()
        return constraints

    def move_rel(self, param_dict):
        """
        todo
        """
        if 'unit' in param_dict:
            if param_dict['unit'] == 'step':
                return self._motor().move_rel(param_dict)
            elif param_dict['unit'] == 'm':
                try:
                    param_dict['x'] = int(round(param_dict['x'] / self.constraints['x']['resolution']))
                    print(param_dict['x'])
                except KeyError:
                    pass
                try:
                    param_dict['y'] = int(round(param_dict['y'] / self.constraints['y']['resolution']))
                except KeyError:
                    pass
                return self._motor().move_rel(param_dict)
        else:
            return self._motor().move_rel(param_dict)

    def abort(self):
        return self._motor().abort()

    def get_position(self):
        """Retrieve position of each motor axis"""
        param_dict = self._motor().get_pos()
        return param_dict

    def get_status(self):
        """Retrieve status of each motor axis"""
        param_dict = self._motor().get_status()
        return param_dict

    def get_velocity(self):
        """Retrieve velocity of each motor axis"""
        param_dict = self._motor().get_velocity()
        return param_dict

    def set_velocity(self, param_dict):
        """Set velocity of each motor axis"""
        # todo also in units if this turns out to be helpful
        return self._motor().set_velocity(param_dict)
