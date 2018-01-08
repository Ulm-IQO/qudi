# -*- coding: utf-8 -*-
"""
Control an output channel of the FPGA to use as a TTL switch.

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


import os
import okfrontpanel as ok
from core.module import Base
from core.util.modules import get_main_dir
from core.util.mutex import Mutex
from interface.switch_interface import SwitchInterface


class OkFpgaTtlSwitch(Base, SwitchInterface):

    """Methods to control TTL switch running on OK FPGA.
    """
    _modclass = 'switchinterface'
    _modtype = 'hardware'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lock = Mutex()

    def on_activate(self):
        self.fp = ok.FrontPanel()
        self.fp.GetDeviceCount()
        self.fp.OpenBySerial(self.fp.GetDeviceListSerial(0))
        self.fp.ConfigureFPGA(os.path.join(get_main_dir(), 'thirdparty', 'qo_fpga', 'switch_top.bit'))
        if not self.fp.IsFrontPanelEnabled():
            self.log.error('FrontPanel is not enabled in FPGA switch!')
            return
        else:
            self.reset()
            self.log.info('FPGA connected')

    def on_deactivate(self):
        pass
        # self.fp.

    def reset(self):
        self.fp.SetWireInValue(0x00, 0)
        self.fp.SetWireInValue(0x01, 0)
        self.fp.SetWireInValue(0x02, 0)
        self.fp.SetWireInValue(0x03, 0)
        self.fp.SetWireInValue(0x04, 0)
        self.fp.SetWireInValue(0x05, 0)
        self.fp.SetWireInValue(0x06, 0)
        self.fp.SetWireInValue(0x07, 0)
        self.fp.UpdateWireIns()
        self.log.info('FPGA switch reset')

    def getNumberOfSwitches(self):
        """ There are 8 TTL channels on the OK FPGA.
        Chan   PIN
        ----------
        Ch1    D10
        Ch2    D15
        Ch3    C7
        Ch4    B12
        Ch5    B16
        Ch6    B14
        Ch7    C17
        Ch8    C13

          @return int: number of switches
        """
        return 8

    def getSwitchState(self, channel):
        """ Gives state of switch.

          @param int switchNumber: number of switch

          @return bool: True if on, False if off, None on error
        """
        if channel not in range(0, 8):
            raise KeyError('ERROR: FPGA switch only accepts channel numbers 0..7')
        return self.fp.GetWireInValue(int(channel) + 1)[1] == 1

    def switchOn(self, channel):
        if channel not in range(0, 8):
            raise KeyError('ERROR: FPGA switch only accepts channel numbers 0..7')
        self.fp.SetWireInValue(int(channel) + 1, 1)
        self.fp.UpdateWireIns()

    def switchOff(self, channel):
        if channel not in range(0, 8):
            raise KeyError('ERROR: FPGA switch only accepts channel numbers 0..7')
        self.fp.SetWireInValue(int(channel) + 1, 0)
        self.fp.UpdateWireIns()

    def getCalibration(self, switchNumber, state):
        return 0

    def setCalibration(self, switchNumber, state, value):
        pass

    def getSwitchTime(self, switchNumber):
        return 0.01
