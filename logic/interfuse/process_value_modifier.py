# -*- coding: utf-8 -*-

"""
This file contains the Qudi interfuse between a process value and a process value.
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

from core.connector import Connector
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from logic.generic_logic import GenericLogic
from interface.process_interface import ProcessInterface


class ProcessValueModifier(GenericLogic, ProcessInterface):
    """ This interfuse can be used to modify a process value on the fly. It needs a 2D array to interpolate
    General form : [[x_0, y_0], [x_1, y_1], ... , [x_n, y_n]]
    Example : [[0,0], [1,10]]
    With this example, the value 0.5 read from the hardware would be transformed to 5 sent to the logic.

    process_value_modifier:
        module.Class: 'interfuse.process_value_modifier.ProcessValueModifier'
        connect:
            hardware: 'processdummy'
            calibration_file: 'PATH/process_modifier.calib'
            force_calibration_from_file: False

    This calibration is stored and remembered as a status variable. If this variable is None, the calibration
    can be read from a simple file with two columns :
    # X Y
    0   0
    1   10
    """

    hardware = Connector(interface='ProcessInterface')

    _calibration = StatusVar(default=None)
    _calibration_file = ConfigOption('calibration_file', None)
    _force_calibration_from_file = ConfigOption('force_calibration_from_file', False)
    _interpolated_function = None

    _new_unit = ConfigOption('new_unit', None)

    def on_activate(self):
        """ Activate module.
        """
        self._hardware = self.hardware()

        if self._force_calibration_from_file and self._calibration_file is None:
            self.log.error('Loading from calibration is enforced but no calibration file has been'
                           'given.')
        if self._force_calibration_from_file or (self._calibration is None and self._calibration_file is not None):
            self.log.info('Loading from calibration file.')
            calibration = np.loadtxt(self._calibration_file)
            self.update_calibration(calibration)
        else:
            self.update_calibration()

    def on_deactivate(self):
        """ Deactivate module.
        """
        pass

    def update_calibration(self, calibration=None):
        """ Construct the interpolated function from the calibration data

        calibration (optional) 2d array : A new calibration to set

        """
        if calibration is not None:
            self._calibration = calibration
        if self._calibration is None:
            self._interpolated_function = lambda x: x
        else:
            self._interpolated_function = interp1d(self._calibration[:, 0], self._calibration[:, 1])

    def reset_to_identity(self):
        """ Reset the calibration data to use identity """
        self._calibration = None
        self.update_calibration()

    def get_process_value(self):
        """ Return the process value modified
        """
        if self._interpolated_function is not None:
            return float(self._interpolated_function(self._hardware.get_process_value()))
        else:
            self.log.error('No calibration was found, please set the process value modifier data first.')
            return 0

    def get_process_unit(self):
        """ Return the process unit
        """
        if self._new_unit is not None:
            return self._new_unit
        else:
            return self._hardware.get_process_unit()

