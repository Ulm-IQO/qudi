# -*- coding: utf-8 -*-

"""
This file contains the Qudi Hardware module NICard class.

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

import PyDAQmx as daq

from core.module import Base, ConfigOption
# from interface.slow_counter_interface import SlowCounterInterface
# from interface.slow_counter_interface import SlowCounterConstraints
# from interface.slow_counter_interface import CountingMode
# from interface.odmr_counter_interface import ODMRCounterInterface
# from interface.confocal_scanner_interface import ConfocalScannerInterface
# from .national_instruments_x_series import NationalInstrumentsXSeries

class NationalInstrumentsMSeries(Base):

    _modtype = 'MultiInterface'
    _modclass = 'NationalInstrumentsMSeries'