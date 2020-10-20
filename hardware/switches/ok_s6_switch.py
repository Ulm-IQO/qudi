# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the FPGA (Opal Kelly XEM6310) based software
defined 8-channel CMOS switch.

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
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from core.util.modules import get_main_dir
from core.util.mutex import Mutex
from interface.switch_interface import SwitchInterface
import numpy as np


class HardwareSwitchFpga(Base, SwitchInterface):
    """
    This is the hardware class for the Spartan-6 (Opal Kelly XEM6310) FPGA based hardware switch.
    The command reference for communicating via the OpalKelly Frontend can be looked up here:

        https://library.opalkelly.com/library/FrontPanelAPI/index.html

    The Frontpanel is basically a C++ interface, where a wrapper was used (SWIG) to access the
    dll library. Be aware that the wrapper is specified for a specific version of python
    (here python 3.4), and it is not guaranteed to be working with other versions.

    Example config for copy-paste:

    fpga_switch:
        module.Class: 'switches.ok_fpga.ok_s6_switch.HardwareSwitchFpga'
        fpga_serial: '143400058N'
        fpga_type: 'XEM6310_LX45'

    """

    # config options
    _serial = ConfigOption('fpga_serial', missing='error')
    # possible type options: XEM6310_LX150, XEM6310_LX45
    _fpga_type = ConfigOption('fpga_type', default='XEM6310_LX45', missing='warn')
    _path_to_bitfile = ConfigOption('path_to_bitfile', default=None, missing='nothing')

    _names_of_states = ConfigOption(name='names_of_states', default=['Off', 'On'], missing='nothing')
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')
    _reset_states = ConfigOption(name='reset_states', default=False, missing='nothing')

    _states = StatusVar(name='states', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._fpga = None
        self._lock = Mutex()
        self._switch_status = dict()
        self._connected = False

    def on_activate(self):
        """ Connect and configure the access to the FPGA.
        """
        # Create an instance of the Opal Kelly FrontPanel. The Frontpanel is a
        # c dll which was wrapped with SWIG for Windows type systems to be
        # accessed with python 3.4. You have to ensure to use the python 3.4
        # version to be able to run the Frontpanel wrapper:
        self._fpga = ok.FrontPanel()

        # TTL output status of the 8 channels
        self._switch_status = {chnl: False for chnl in range(8)}

        self._connected = False

        # Sanity check for fpga_type ConfigOption
        self._fpga_type = self._fpga_type.upper()
        if self._fpga_type not in ('XEM6310_LX45', 'XEM6310_LX150'):
            self.log.error('Unsupported FPGA type "{0}" specified in config. Valid options are '
                           '"XEM6310_LX45" and "XEM6310_LX150".\nAborting module activation.'
                           ''.format(self._fpga_type))
            return

        # connect to the FPGA module
        self._connect()

        if self._hardware_name is None:
            self._hardware_name = 'Opalkelly FPGA Switch'

        if np.shape(self._names_of_states) == (2,):
            self._names_of_states = [list(self._names_of_states)] * self.number_of_switches
        elif np.shape(self._names_of_states) == (self.number_of_switches, 2):
            self._names_of_states = list(self._names_of_states)
        else:
            self.log.error(f'names_of_states must either be a list of two names for the states [low, high] '
                           f'which are applied to all switched or it must be a list '
                           f'of length {self._number_of_switches} with elements of the aforementioned shape.')

        if np.shape(self._names_of_switches) == (self.number_of_switches,):
            self._names_of_switches = list(self._names_of_switches)
        else:
            self._names_of_switches = ['B14', 'B16', 'B12', 'C7', 'D15', 'D10', 'D9', 'D11']

        # initialize channels to saved status if requested
        if self._reset_states:
            self.states = False

        if self._states is None or len(self._states) != self.number_of_switches:
            self.states = [False] * self.number_of_switches
        else:
            self.states = self._states
        return

    def on_deactivate(self):
        """ Deactivate the FPGA.
        """
        if self._connected and self._reset_states:
            self.states = False
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

        if not self._path_to_bitfile:
            # upload the proper hardware switch configuration bitfile to the FPGA
            if self._fpga_type == 'XEM6310_LX45':
                bitfile_name = 'switch_8chnl_withcopy_LX45.bit'
            elif self._fpga_type == 'XEM6310_LX150':
                bitfile_name = 'switch_8chnl_withcopy_LX150.bit'
            else:
                self.log.error('Unsupported FPGA type "{0}" specified in config. Valid options are '
                               '"XEM6310_LX45" and "XEM6310_LX150".\nConnection to FPGA module failed.'
                               ''.format(self._fpga_type))
                return -1
            self._path_to_bitfile = os.path.join(get_main_dir(), 'thirdparty', 'qo_fpga', bitfile_name)

        # Load on the FPGA a configuration file (bit file).
        self.log.debug(f'Using bitfile: {self._path_to_bitfile}')
        self._fpga.ConfigureFPGA(self._path_to_bitfile)

        # Check if the upload was successful and the Opal Kelly FrontPanel is enabled on the FPGA
        if not self._fpga.IsFrontPanelEnabled():
            self.log.error('Opal Kelly FrontPanel is not enabled in FPGA')
            return -1

        self._connected = True
        return 0

    @property
    def name(self):
        return self._hardware_name

    @property
    def states(self):
        with self._lock:
            self._fpga.UpdateWireOuts()
            new_state = int(self._fpga.GetWireOutValue(0x20))
            for chnl in range(self.number_of_switches):
                if new_state & (2 ** chnl) != 0:
                    self._states[chnl] = True
                else:
                    self._states[chnl] = False
            return self._states.copy()

    @states.setter
    def states(self, value):
        if np.isscalar(value):
            self._states = [bool(value)] * self.number_of_switches
        else:
            if len(value) != self.number_of_switches:
                self.log.error(f'The states either have to be a scalar or a list af length {self.number_of_switches}')
                return
            else:
                self._states = [bool(state) for state in value]

        with self._lock:
            # encode channel states
            chnl_state = 0
            for chnl in range(self.number_of_switches):
                if self._states[chnl]:
                    chnl_state += int(2 ** chnl)

            old_states = self._states.copy()
            # apply changes in hardware
            self._fpga.SetWireInValue(0x00, chnl_state)
            self._fpga.UpdateWireIns()

        # check if the state was actually set
        if old_states != self.states:
            self.log.error('Setting of channel states in hardware failed.')

    @property
    def names_of_states(self):
        return self._names_of_states.copy()

    @property
    def names_of_switches(self):
        return self._names_of_switches.copy()

    @property
    def number_of_switches(self):
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

    def get_state(self, index_of_switch):
        if 0 <= index_of_switch < self.number_of_switches:
            return self._states[int(index_of_switch)]
        self.log.error(f'index_of_switch was {index_of_switch} but must be smaller than {self.number_of_switches}.')
        return False

    def set_state(self, index_of_switch, state):
        if 0 <= index_of_switch < self.number_of_switches:
            new_states = self.states
            new_states[int(index_of_switch)] = bool(state)
            self.states = new_states
            return self.get_state(index_of_switch)

        self.log.error(f'index_of_switch was {index_of_switch} but must be smaller than {self.number_of_switches}.')
        return -1
