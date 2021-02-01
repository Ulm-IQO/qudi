# -*- coding: utf-8 -*-

"""
ToDo: Document

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

from qudi.core.module import LogicBase
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.util.mutex import RecursiveMutex
from qudi.interface.finite_sampling_input_interface import FiniteSamplingInputInterface
from qudi.interface.finite_sampling_output_interface import FiniteSamplingOutputInterface
from qudi.interface.finite_sampling_output_interface import SamplingOutputMode


class FiniteSamplingMicrowaveInterfuse(LogicBase,
                                       FiniteSamplingOutputInterface,
                                       FiniteSamplingInputInterface):
    """
    ToDo: Document
    """

    _microwave = Connector(name='microwave', interface='MicrowaveInterface')
    _data_reader = Connector(name='data_reader', interface='FiniteSamplingInputInterface')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass
