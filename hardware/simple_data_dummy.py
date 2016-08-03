# -*- coding: utf-8 -*-
"""
Dummy implementation for simple data acquisition.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from core.base import Base
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
from interface.simple_data_interface import SimpleDataInterface
import numpy as np
import time

class SimpleDummy(Base, SimpleDataInterface):
    """
    """
    _modclass = 'simple'
    _modtype = 'hardware'

    # connectors
    _out = {'simple': 'Simple'}

    def on_activate(self, e):
        pass

    def on_deactivate(self, e):
        pass

    def getData(self):
        time.sleep(0.1)
        return [int(np.random.poisson(5)), int(np.random.poisson(10)), int(np.random.poisson(30))]

    def getChannels(self):
        time.sleep(0.1)
        return 3
