# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the FPGA based fast counter.

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
from core.module import Base, ConfigOption
from core.util.modules import get_main_dir
from core.util.mutex import Mutex
from interface.switch_interface import SwitchInterface


class HardwareSwitchFpga(Base, SwitchInterface):
    """
    This is the hardware class for the Spartan-6 (Opal Kelly XEM6310) FPGA based hardware switch.
    The command reference for communicating via the OpalKelly Frontend can be looked up here:

        https://library.opalkelly.com/library/FrontPanelAPI/index.html

    The Frontpanel is basically a C++ interface, where a wrapper was used (SWIG) to access the
    dll library. Be aware that the wrapper is specified for a specific version of python
    (here python 3.4), and it is not guaranteed to be working with other versions.
    """
    _modclass = 'HardwareSwitchFpga'
    _modtype = 'hardware'

    # config options
    _serial = ConfigOption('fpga_serial', missing='error')

    def on_activate(self):
        """ Connect and configure the access to the FPGA.
        """
        # Create an instance of the Opal Kelly FrontPanel. The Frontpanel is a
        # c dll which was wrapped with SWIG for Windows type systems to be
        # accessed with python 3.4. You have to ensure to use the python 3.4
        # version to be able to run the Frontpanel wrapper:
        self._fpga = ok.FrontPanel()

        # threading
        self.threadlock = Mutex()

        # TTL output status of the 8 channels
        self._switch_status = {1: False, 2: False, 3: False, 4: False,
                              5: False, 6: False, 7: False, 8: False}
        self._connected = False

        # connect to the FPGA module
        self._connect()
        return

    def on_deactivate(self):
        """ Deactivate the FPGA.
        """
        self.reset()
        del self._fpga
        self._connected = False
        return

    def _connect(self):
        """
        Connect host PC to FPGA module with the specified serial number.
        """
        # check if a FPGA is connected to this host PC. That method is used to
        # determine also how many devices are available.
        if not self._fpga.GetDeviceCount():
            self.log.error('No FPGA connected to host PC or FrontPanel.exe is running.')
            return -1

        # open a connection to the FPGA with the specified serial number
        self._fpga.OpenBySerial(self._serial)

        # upload the proper hardware switch configuration bitfile to the FPGA
        bitfile_name = 'switch_8chnl_withcopy_LX150.bit'
        # Load on the FPGA a configuration file (bit file).
        self._fpga.ConfigureFPGA(os.path.join(get_main_dir(), 'thirdparty', 'qo_fpga',
                                              bitfile_name))

        # Check if the upload was successful and the Opal Kelly FrontPanel is enabled on the FPGA
        if not self._fpga.IsFrontPanelEnabled():
            self.log.error('Opal Kelly FrontPanel is not enabled in FPGA')
            return -1
        else:
            self._fpga.SetWireInValue(0x00, 0x00000000)
            self._fpga.UpdateWireIns()

        self._switch_status = {0: False, 1: False, 2: False, 3: False,
                               4: False, 5: False, 6: False, 7: False}
        self._connected = True
        return 0

    def getNumberOfSwitches(self):
        """ There are 8 TTL channels on the OK FPGA.
        Chan   PIN
        ----------
        Ch1    B14
        Ch2    B16
        Ch3    B12
        Ch4    C7
        Ch5    D15
        Ch6    D10
        Ch7    D9
        Ch8    D11

        @return int: number of switches
        """
        return 8

    def getSwitchState(self, channel):
        """ Gives state of switch.

          @param int channel: number of switch channel

          @return bool: True if on, False if off, None on error
        """
        if channel not in self._switch_status:
            self.log.error('FPGA switch only accepts channel numbers 0..7. Asked for channel {0}.'
                           ''.format(channel))
            return None
        self._get_all_states()
        return self._switch_status[channel]

    def switchOn(self, channel):
        with self.threadlock:
            if channel not in self._switch_status:
                self.log.error('FPGA switch only accepts channel numbers 0..7. Asked for channel '
                               '{0}.'.format(channel))
                return

            # determine new channels status
            new_state = self._switch_status.copy()
            new_state[channel] = True

            # encode channel states
            chnl_state = 0
            for chnl in list(new_state):
                if new_state[chnl]:
                    chnl_state += int(2 ** chnl)

            # apply changes in hardware
            self._fpga.SetWireInValue(0x00, chnl_state)
            self._fpga.UpdateWireIns()

            # get new state from hardware
            actual_state = self._get_all_states()
            if new_state != actual_state:
                self.log.error('Setting of channel states in hardware failed.')
            return

    def switchOff(self, channel):
        with self.threadlock:
            if channel not in self._switch_status:
                self.log.error('FPGA switch only accepts channel numbers 0..7. Asked for channel '
                               '{0}.'.format(channel))
                return

            # determine new channels status
            new_state = self._switch_status.copy()
            new_state[channel] = False

            # encode channel states
            chnl_state = 0
            for chnl in list(new_state):
                if new_state[chnl]:
                    chnl_state += int(2 ** chnl)

            # apply changes in hardware
            self._fpga.SetWireInValue(0x00, chnl_state)
            self._fpga.UpdateWireIns()

            # get new state from hardware
            actual_state = self._get_all_states()
            if new_state != actual_state:
                self.log.error('Setting of channel states in hardware failed.')
            return

    def reset(self):
        """
        Reset TTL outputs to zero
        """
        with self.threadlock:
            if not self._connected:
                return
            self._fpga.SetWireInValue(0x00, 0)
            self._fpga.UpdateWireIns()
            self._switch_status = {0: False, 1: False, 2: False, 3: False,
                                   4: False, 5: False, 6: False, 7: False}
        return

    def getCalibration(self, switchNumber, state):
        return -1

    def setCalibration(self, switchNumber, state, value):
        return True

    def getSwitchTime(self, switchNumber):
        """ Give switching time for switch.

          @param int switchNumber: number of switch

          @return float: time needed for switch state change
        """
        return 100.0e-3

    def _get_all_states(self):
        self._fpga.UpdateWireOuts()
        new_state = int(self._fpga.GetWireOutValue(0x20))
        for chnl in list(self._switch_status):
            if new_state & (2 ** chnl) != 0:
                self._switch_status[chnl] = True
            else:
                self._switch_status[chnl] = False
        return self._switch_status
