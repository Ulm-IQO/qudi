"""
This file contains the Ni digital trigger Logic module base class.

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

from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import time
import datetime

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.connector import Connector
from core.configoption import ConfigOption
from core.statusvariable import StatusVar

class NIDigitalPWMLogic(GenericLogic):

    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """

    _device = Connector(interface='NIPWMInterface')
    _channel_list = []
    value_matrix = 0
    value=0
    freq=10000
    def __init__(self,config,**kwargs):
        """ Create VoltageScanningLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(config=config,**kwargs)
        self.log.info(self._device)
        # locking for thread safety
        self.threadlock = Mutex()
        self.stopRequested = False


    def on_activate(self):
        self.device=self._device()
        self._channel_list = self.device.get_channel_list()
        self.value_matrix=np.zeros(int(20*10**-3*self.freq))


    def on_deactivate(self):
        self.stop()
        """ Deinitialisation performed during deactivation of the module.
        """


    def value(self):
        self.log.info('output value: ' + str(self.device.value))
        return True

    def set_value(self,value):
        self.value=value

    def pwm_output(self,value=0,channel=-1,frequency=10000):
        self.device.output(value,channel,frequency)
        self.log.info('holding at position '+str(value*90)+'degree')


    def simple_0(self, channel=-1):
        self.device.simple_0(channel=channel)
        self.log.info('holding at position 0 degree')
        return True


    def simple_45(self, channel=-1):
        self.device.simple_45(channel=channel)
        self.log.info('holding at position 45 degree')
        return True


    def simple_90(self, channel=-1):
        self.device.simple_90(channel=channel)
        self.log.info('holding at position 90 degree')
        return True


    def stop(self):
        self.device.stop()

