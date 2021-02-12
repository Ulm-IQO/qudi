# -*- coding: utf-8 -*-

"""
This file contains the Qudi dummy hardware file to mimic a CW microwave device via
ProcessControlInterface.

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

from qudi.core.configoption import ConfigOption
from qudi.hardware.dummy.finite_sampling_io_dummy import FiniteSamplingIODummy, SimulationMode
from qudi.hardware.dummy.process_control_dummy import ProcessSetpointDummy


class OdmrScannerDummy(FiniteSamplingIODummy):
    """ A dummy class to emulate a microwave ODMR scanner.

    Example config for copy-paste:

    odmr_scanner_dummy:
        module.Class: 'dummy.microwave_dummy.OdmrScannerDummy'

    """
    _sample_rate_limits = ConfigOption(name='sample_rate_limits', default=(0.1, 1e6))
    _frame_size_limits = ConfigOption(name='frame_size_limits', default=(2, 1e5))
    _input_channel_units = ConfigOption(name='input_channel_units',
                                        default={'Photon Counts': 'c/s', 'Photodiode': 'V'})
    _output_channel_units = ConfigOption(name='output_channel_units', default={'Frequency': 'Hz'})
    _simulation_mode = ConfigOption(name='simulation_mode',
                                    default='ODMR',
                                    constructor=lambda x: SimulationMode[x.upper()])


class CwMicrowaveDummy(ProcessSetpointDummy):
    """ A dummy class to emulate a CW microwave source with adjustable power and frequency.

    Example config for copy-paste:

    cw_microwave_dummy:
        module.Class: 'dummy.microwave_dummy.CwMicrowaveDummy'
    """

    _setpoint_channels = ConfigOption(
        name='setpoint_channels',
        default={'Power': {'unit': 'dBm', 'limits': (-120.0, 30.0), 'dtype': float},
                 'Frequency': {'unit': 'Hz', 'limits': (100.0e3, 20.0e9), 'dtype': float}}
    )
