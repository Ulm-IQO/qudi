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

from core.connector import Connector
from logic.generic_logic import GenericLogic
from core.statusvariable import StatusVar
from collections import OrderedDict
from core.util.helpers import is_integer

# TODO ... I am ugly ... please rework


class MotorLogic(GenericLogic):
    x_motor = Connector(interface='MotorInterface', optional=True)
    y_motor = Connector(interface='MotorInterface', optional=True)
    z_motor = Connector(interface='MotorInterface', optional=True)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # TODO Maybe one could to it similar to Magnet xyz rot interfuse instead of the "_axes" stuff
        #  which store the connector
        if self.x_motor()._name == self.y_motor()._name == self.z_motor()._name:
            assert len(self.x_motor().get_constraints()) == 3
            self._axes = {ax_log: (self.x_motor, ax_hw) for ax_log, ax_hw
                          in zip(('x', 'y', 'z'), self.x_motor().get_constraints().keys())}
            self._unique_motors = [self.x_motor]

        elif self.x_motor()._name == self.y_motor()._name != self.z_motor()._name:
            assert len(self.x_motor().get_constraints()) == 2 and len(self.z_motor().get_constraints()) == 1
            self._axes = {ax_log: (self.x_motor, ax_hw) for ax_log, ax_hw
                          in zip(('x', 'y'), self.x_motor().get_constraints().keys())}
            self._axes['z'] = (self.z_motor, next(iter(self.z_motor().get_constraints())))
            self._unique_motors = [self.x_motor, self.z_motor]

        elif self.x_motor()._name != self.y_motor()._name != self.z_motor()._name:
            assert all([len(mot().get_constraints()) == 1 for mot in (self.x_motor, self.y_motor, self.z_motor)])
            self._axes = {ax_log: (mot, next(iter(mot().get_constraints())))
                          for ax_log, mot in zip(('x', 'y', 'z'), (self.x_motor, self.y_motor, self.z_motor))}
            self._unique_motors = [self.x_motor, self.y_motor, self.z_motor]
        else:
            raise NotImplementedError('The given Stage configuration is not implemented')

    def on_deactivate(self):
        pass
        #self._motor().abort()

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.
        @return dict: dict with constraints for the motor hardware. These
                      constraints will be passed via the logic to the GUI so
                      that proper display elements with boundary conditions
                      could be made.
        """
        return OrderedDict({ax_log: self._axes[ax_log][0]().get_constraints()[self._axes[ax_log][1]]
                            for ax_log in self._axes})

    def move_rel(self, param_dict):
        """
        todo
        """
        for ax, dist in param_dict.items():
            self._axes[ax][0]().move_rel({self._axes[ax][1]: dist})

    def abort(self):
        for motor in self._unique_motors:
            motor().abort()
        # self._axes['z'][0]().abort()
        # self._axes['x'][0]().abort()
        # self._axes['y'][0]().abort()
        # for mot, _ in self._axes.values():
        #     mot().abort() #TODO this stops a 2d motor multiple times ...

    def get_velocity(self):
        """Retrieve velocity of each motor axis"""
        # return {ax_log: ax_hw for ax_log, (mot, ax_hw) in self._axes.items()}
        # return {ax_log: mot().get_velocity(ax_hw) for ax_log, (mot, ax_hw) in self._axes.items()}
        return {ax_log: mot().get_velocity(ax_hw)[ax_hw] for ax_log, (mot, ax_hw) in self._axes.items()}

    def set_velocity(self, param_dict):
        """Set velocity of each motor axis"""
        # todo also in units if this turns out to be helpful
        for ax_log, velocity in param_dict.items():
            self._axes[ax_log][0]().set_velocity({self._axes[ax_log][1]: velocity})

    def get_unit(self, ax_log):
        return self._axes[ax_log][0]().get_constraints()[self._axes[ax_log][1]]['unit']

    def is_ax_log_integer_steps(self, ax_log):
        step = self._axes[ax_log][0]().get_constraints()[self._axes[ax_log][1]]['pos_step']
        try:
            if step.is_integer():
                return True
            else:
                return False
        except AttributeError:  # Since 'int' has no attribute .is_integer()
            return is_integer(step)

    def get_positions(self):
        """Retrieve velocity of each motor axis"""
        # return {ax_log: ax_hw for ax_log, (mot, ax_hw) in self._axes.items()}
        # return {ax_log: mot().get_velocity(ax_hw) for ax_log, (mot, ax_hw) in self._axes.items()}
        return {ax_log: mot().get_pos([ax_hw])[ax_hw] for ax_log, (mot, ax_hw) in self._axes.items()}
