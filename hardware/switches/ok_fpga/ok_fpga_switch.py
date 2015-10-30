# -*- coding: utf-8 -*-
"""
Control an output channel of the FPGA to use as a TTL switch.

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

Copyright (C) 2015 Niko Tomek
Copyright (C) 2015 Lachlan J. Rogers lachlan.rogers@uni-ulm.de
"""

from core.base import Base
from core.util.mutex import Mutex
from hardware.switches.switch_interface import SwitchInterface
import thirdparty.opal_kelly as ok

class OkFpgaTtlSwitch(Base, SwitchInterface):
    """Methods to control TTL switch running on OK FPGA.
    """
    _modclass = 'switchinterface'
    _modtype = 'hardware'
    _out = {'switch': 'SwitchInterface'}
    
    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config,  c_dict)
        self.lock = Mutex()

    def activation(self, e):
        self.fp = ok.FrontPanel()
        self.fp.GetDeviceCount()
        self.fp.OpenBySerial(self.fp.GetDeviceListSerial(0))
        self.fp.ConfigureFPGA('switch_top.bit')
        if not self.fp.IsFrontPanelEnabled():
            self.logMsg('ERROR: FrontPanel is not enabled in FPGA switch!', msgType='error')
            return
        else:
            self.reset()
            self.logMsg('FPGA connected')

    def deactivation(self, e):
        pass
        #self.fp.
        
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
        self.logMsg('FPGA switch reset')
    
    def getNumberOfSwitches(self):
        """ There are 8 TTL channels on the OK FPGA.

          @return int: number of switches
        """
        return 8

    def getSwitchState(self, channel):
        """ Gives state of switch.

          @param int switchNumber: number of switch

          @return bool: True if on, False if off, None on error
        """
       return self.fp.GetWireInValue(int(channel) + 1) == 1

    def switchOn(self, channel):
        if channel > 7 or channel < 0:
            self.logMsg('ERROR: FPGA switch only accepts channel numbers 0..7', msgType='error')
            return
        self.fp.SetWireInValue(int(channel) + 1, 1)
        self.fp.UpdateWireIns()

    def switchOff(self, channel):
        if channel > 7 or channel < 0:
            self.logMsg('ERROR: FPGA switch only accepts channel numbers 0..7', msgType='error')
            return
        self.fp.SetWireInValue(int(channel) + 1, 0)
        self.fp.UpdateWireIns()

    def getCalibration(self, switchNumber, state):
        return 0

    def setCalibration(self, switchNumber, state, value):
        pass

    def getSwitchTime(self, switchNumber):
        return 0.01
