# -*- coding: utf-8 -*-
"""
This module contains fake spectrometer.

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

Copyright (C) 2015 Jan Binder, jan.binder@uni-ulm.de
"""

from core.base import Base
from hardware.spectrometer_interface import SpectrometerInterface
from collections import OrderedDict
from core.util.mutex import Mutex

from pyqtgraph.Qt import QtCore

import random
import time
import numpy as np

class SpectrometerInterfaceDummy(Base,SpectrometerInterface):
    _in = {'fitlogic': 'FitLogic'}
    _out = {'spec': 'SpectrometerInterface'}

    def __init__(self, manager, name, configuration):
        cb = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self,manager,name,configuration, cb)

    def activation(self, e):
        self._fitLogic = self.connector['in']['fitlogic']['object']
        self.exposure = 0.1

    def deactivation(self, e):
        pass

    def recordSpectrum(self,):
        length = 1024

        data = np.empty((2, length), dtype=np.double)
        data[0] = np.arange(730, 750, 20/length)
        data[1] = np.random.uniform(0, 200, length)

        lorentians, params = self._fitLogic.make_multiple_lorentzian_model(no_of_lor=4)
        sigma = 0.05
        params.add('lorentz0_amplitude', value=2000)
        params.add('lorentz0_center', value=736.46)
        params.add('lorentz0_sigma', value=1.5*sigma)
        params.add('lorentz1_amplitude', value=5800)
        params.add('lorentz1_center', value=736.545)
        params.add('lorentz1_sigma', value=sigma)
        params.add('lorentz2_amplitude', value=7500)
        params.add('lorentz2_center', value=736.923)
        params.add('lorentz2_sigma', value=sigma)
        params.add('lorentz3_amplitude', value=1000)
        params.add('lorentz3_center', value=736.99)
        params.add('lorentz3_sigma', value=1.5*sigma)
        params.add('c', value=50000.)

        data[1] += lorentians.eval(x=data[0], params=params)

        time.sleep(self.exposure)
        return data

    def getExposure(self):
        return self.exposure

    def setExposure(self, exposureTime):
        self.exposure = exposureTime
