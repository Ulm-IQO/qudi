# -*- coding: utf-8 -*-
"""
This file contains the implementation of Keysight N90x0 spectrum analyzers.

The main class is ::PyIviSpecAnKeysightN90X0::

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

from . import pyivi_specan
from interface.ivi.specan_extensions.sweep_points import SweepPointsExtensionInterface
from .._ivi_core import Namespace
import visa
from qtpy.QtCore import Signal


class SweepPointsExtension(SweepPointsExtensionInterface):
    """
    Extension for spectrum analyzers supporting to specify the number of sweep points.
    """
    class sweep_coupling(SweepPointsExtensionInterface.sweep_coupling):
        sweep_points_changed = Signal(int)

        @property
        def sweep_points(self):
            """
            Specifies the number of measured points in each sweep.
            """
            return int(self.root.driver_visa.query('SWEEP:POINTS?'))

        @sweep_points.setter
        def sweep_points(self, value):
            self.root.driver_visa.write('SWEEP:POINTS {0:d}'.format(value))
            self.sweep_points_changed.emit(value)


class PyIviSpecAnKeysightN90X0(pyivi_specan.PyIviSpecAn):
    """
    Hardware driver for Keysight N90X0 spectrum analyzers.

    The driver is based on the IVI-COM driver provided by Keysight but it implements further functionality
    not covered by the IVI specifications. We directly use VISA and SCPI commands for it.

    Example configuration:

    esa_n9000:
        module.Class: 'specan.pyivi_specan_keysight_n90x0.PyIviSpecAnKeysightN90X0'
        uri: 'TCP::192.168.0.1::INSTR'
        model: 'N9000A'
        flavour: 'IVI-COM"

    Please see PyIviSpecAn for further explanations of configuration options.
    """
    def on_activate(self):
        super().on_activate()

        # connect to instrument via visa
        self._visa_resource_manager = visa.ResourceManager()
        self.driver_visa = self._visa_resource_manager.open_resource(self.uri)

        # add extension
        class N9000SweepCoupling(self.sweep_coupling.__class__, SweepPointsExtension.sweep_coupling):
            pass

        self.sweep_coupling = Namespace(N9000SweepCoupling)
        del self.__sweep_coupling_cached__

    def on_deactivate(self):
        self.driver_visa.close()
        super().on_deactivate()