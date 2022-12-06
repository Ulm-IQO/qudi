# -*- coding: utf-8 -*-

"""
Motor management in a grid fashion.

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
import numpy as np


class MotorGridLogic(GenericLogic):
    """
    Handles moves in a grid fashion
    """

    # _grid_idx = StatusVar(default=(0, 0))
    # _grid_vector_1 = StatusVar(default=(0, 0))
    # _grid_vector_2 = StatusVar(default=(0, 0))

    _motor = Connector(interface='MotorInterface')

    _saved_positions = StatusVar(default=dict())

    _fail_save_positions = StatusVar(default=dict())

    def on_activate(self):
        pass


    def on_deactivate(self):
        self._fail_save_positions = self._saved_positions.copy()

    @property
    def positions(self):
        return self._saved_positions

    def move_to(self, device_name):
        self._motor().move_abs(self._saved_positions[device_name])
        self.log.info(f'Move to device {device_name}')

    def save_position(self, device_name):
        self._saved_positions.update({device_name: self._motor().get_pos()})
        self.log.info(f'Saved position for {device_name}')

    def globally_update_position(self, device_name):
        new_pos = self._motor().get_pos()
        old_pos = self._saved_positions[device_name]

        difference = {ax: new_pos[ax] - old_pos[ax] for ax in new_pos}

        for device, position_values in self._saved_positions.items():
            self._saved_positions.update({device: {ax: position_values[ax] + difference[ax] for ax in position_values}})
        self.log.info(f'Globally updated position on {device_name} with difference {difference}')

    def clear_all_positions(self):
        self._saved_positions = dict()

    def delete_position(self, device_name):
        self._saved_positions.pop(device_name)

    def _restore_from_failsaife(self):
        self._saved_positions = self._fail_save_positions.copy()

    def get_closest(self):
        if len(self._saved_positions) == 0:
            raise ValueError
        current_position = self._motor().get_pos()
        closest_device = ''
        min_dist = None
        for device, position_values in self._saved_positions.items():
            dist = np.sqrt(np.sum([(current_position[ax] - position_values[ax])**2 for ax in position_values]))
            if min_dist is None or dist < min_dist:
                min_dist = dist
                closest_device = device
        return closest_device





    # def move_to_grid_pos(self, idx1, idx2):
    #     motor_ax1_dist = (idx1 - self._grid_idx[0]) * self._grid_vector_1[0] + \
    #                      (idx2 - self._grid_idx[1]) * self._grid_vector_2[0]
    #
    #     motor_ax2_dist = (idx1 - self._grid_idx[0]) * self._grid_vector_1[1] + \
    #                      (idx2 - self._grid_idx[1]) * self._grid_vector_2[1]
