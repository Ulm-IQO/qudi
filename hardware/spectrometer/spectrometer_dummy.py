# -*- coding: utf-8 -*-
"""
This module contains fake spectrometer.

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

from core.base import Base
from interface.spectrometer_interface import SpectrometerInterface

from time import strftime, localtime

import time
import numpy as np


class SpectrometerInterfaceDummy(Base,SpectrometerInterface):
    _in = {'fitlogic': 'FitLogic'}
    _out = {'spec': 'SpectrometerInterface'}

    def on_activate(self, e):
        self._fitLogic = self.get_in_connector('fitlogic')
        self.exposure = 0.1

    def on_deactivate(self, e):
        pass

    def recordSpectrum(self,):
        length = 1024

        data = np.empty((2, length), dtype=np.double)
        data[0] = np.arange(730, 750, 20/length)
        data[1] = np.random.uniform(0, 2000, length)

        lorentz, params = self._fitLogic.make_multiplelorentzoffset_model(no_of_functions=4)
        sigma = 0.05
        params.add('l0_amplitude', value=2000)
        params.add('l0_center', value=736.46)
        params.add('l0_sigma', value=1.5*sigma)
        params.add('l1_amplitude', value=5800)
        params.add('l1_center', value=736.545)
        params.add('l1_sigma', value=sigma)
        params.add('l2_amplitude', value=7500)
        params.add('l2_center', value=736.923)
        params.add('l2_sigma', value=sigma)
        params.add('l3_amplitude', value=1000)
        params.add('l3_center', value=736.99)
        params.add('l3_sigma', value=1.5*sigma)
        params.add('offset', value=50000.)

        data[1] += lorentz.eval(x=data[0], params=params)

        time.sleep(self.exposure)
        return data

    def saveSpectrum(self, path, postfix = ''):
        timestr = strftime("%Y%m%d-%H%M-%S_", localtime())
        print( 'Dummy would save to: ' + str(path) + timestr + str(postfix) + ".spe" )

    def getExposure(self):
        return self.exposure

    def setExposure(self, exposureTime):
        self.exposure = exposureTime
