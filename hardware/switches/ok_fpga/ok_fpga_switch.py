# -*- coding: utf-8 -*-
"""
Control the Radiant Dyes flip mirror driver through the serial interface.

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
import ok

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

        self.xem = ok.FrontPanel()

        self.xem.GetDeviceCount()
        self.xem.OpenBySerial(self.xem.GetDeviceListSerial(0))
        self.xem.ConfigureFPGA('switch_top.bit')
        if not self.xem.IsFrontPanelEnabled():
            print('ERROR: FrontPanel is not enabled in FPGA switch!')
            return
        else:
            reset()
            print('FPGA connected')
        return


    def deactivation(self, e):
        self.inst.close()
    
    def getNumberOfSwitches(self):
        """ There are 8 TTL channels on the OK FPGA.

          @return int: number of switches
        """
        return 8

    def getSwitchState(self, switchNumber):
        """ Gives state of switch.

          @param int switchNumber: number of switch

          @return bool: True if on, False if off, None on error
        """
        pass


    def reset(self):
        self.xem.SetWireInValue(0x00, 0)
        self.xem.SetWireInValue(0x01, 0)
        self.xem.SetWireInValue(0x02, 0)
        self.xem.SetWireInValue(0x03, 0)
        self.xem.SetWireInValue(0x04, 0)
        self.xem.SetWireInValue(0x05, 0)
        self.xem.SetWireInValue(0x06, 0)
        self.xem.SetWireInValue(0x07, 0)
        self.xem.UpdateWireIns()
        print('FPGA switch reset')
        return
        

    def switchOn(self, channel):
        if (channel >= 9) or (channel <= 0):
            print('ERROR: FPGA switch only accepts channel numbers 1..8')
            return
        self.xem.SetWireInValue(int(channel), 1)
        self.xem.UpdateWireIns()
        print('Channel ' + str(int(channel)) + ' switched on')
        return
        
    def switchOff(self, channel):
        if (channel >= 9) or (channel <= 0):
            print('ERROR: FPGA switch only accepts channel numbers 1..8')
            return
        self.xem.SetWireInValue(int(channel), 0)
        self.xem.UpdateWireIns()
        print('Channel ' + str(int(channel)) + ' switched off')
        return
    
