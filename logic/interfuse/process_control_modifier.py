# -*- coding: utf-8 -*-

"""
This file contains the Qudi interfuse between a process control and a process control.
---

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
import numpy as np
from scipy.interpolate import interp1d

from core.module import Connector, ConfigOption, StatusVar
from logic.generic_logic import GenericLogic
from interface.process_control_interface import ProcessControlInterface


class ProcessControlModifier(GenericLogic, ProcessControlInterface):
    """ This interfuse can be used to modifiy a process control on the fly. It needs a 2D array to interpolate
    General form : [[x_0, y_0], [x_1, y_1], ... , [x_n, y_n]]
    Example : [[0,0], [1,10]]
    With this example, the value 0.5 sent from the logic would be transformed to 5 sent to the hardware.



    This calibration is stored and remembered as a status variable. If this variable is None, the calibration
    can be read from a simple file with two columns :
    # X Y
    0   0
    1   10
    """

    _modclass = 'ProcessValueModifier'
    _modtype = 'interfuse'

    hardware = Connector(interface='ProcessControlInterface')

    _calibration = StatusVar(default=None)
    _calibration_file = ConfigOption('calibration_file', None)
    _force_calibration_from_file = ConfigOption('force_calibration_from_file', False)
    _interpolated_function = None
    _interpolated_function_reversed = None

    _new_unit = ConfigOption('new_unit', None)

    _last_control_value = None

    def on_activate(self):
        """ Activate module.
        """
        self._hardware = self.hardware()

        if self._calibration is None or self._force_calibration_from_file:
            if self._calibration_file is not None:
                self.log.warning('No calibration can be found from previous sessions, loading from calibration file.')
                calibration = np.loadtxt(self._calibration_file)
                self._update(calibration)
            else:
                self.log.warning('No calibration can be found from previous sessions, no calibration file has been'
                                 'given. Please update calibration before using')
        else:
            self._update()

    def on_deactivate(self):
        """ Deactivate module.
        """
        pass

    def _update(self, calibration=None):
        """ Construct the interpolated function from the calibration data

        calibration (optional) 2d array : A new calibration to set

        """
        if calibration is not None:
            self._calibration = calibration
        self._interpolated_function = interp1d(self._calibration[:, 0], self._calibration[:, 1])
        self._interpolated_function_reversed = interp1d(self._calibration[:, 1], self._calibration[:, 0])

        if self._last_control_value is not None:
            self.set_control_value(self._last_control_value)
        
    def get_control_value(self):
        """ Return the original control value
        """
        if self._interpolated_function_reversed is not None:
            return self._interpolated_function_reversed(self._hardware.get_control_value())
        else:
            self.log.error('No calibration was found, please set the control value modifier data first.')

    def set_control_value(self, value):
        """ Set the control value modified
        """
        if self._interpolated_function is not None:
            self._hardware.set_control_value(self._interpolated_function(value))
        else:
            self.log.error('No calibration was found, please set the control value modifier data first.')

    def get_control_unit(self):
        """ Return the process unit
        """
        if self._new_unit is not None:
            return self._new_unit
        else:
            return self._hardware.get_control_unit()

    def get_control_limits(self):
        """ Return limits within which the controlled value can be set as a tuple of (low limit, high limit)
        """
        mini, maxi = self._hardware.get_control_limits()
        mini = float(self._interpolated_function_reversed(mini))
        maxi = float(self._interpolated_function_reversed(maxi))
        return mini, maxi
