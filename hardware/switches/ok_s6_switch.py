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
from core.util.mutex import RecursiveMutex
from interface.switch_interface import SwitchInterface


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
        fpga_type: 'XEM6310_LX45'  # optional
        path_to_bitfile: <file path>  # optional
        name: 'OpalKelly FPGA Switch'  # optional
        remember_states: True  # optional
        switches:               # optional
            B14: ['Off', 'On']
            B16: ['Off', 'On']
            B12: ['Off', 'On']
             C7: ['Off', 'On']
            D15: ['Off', 'On']
            D10: ['Off', 'On']
             D9: ['Off', 'On']
            D11: ['Off', 'On']
    """

    # config options
    # serial number of the FPGA
    _serial = ConfigOption('fpga_serial', missing='error')
    # Type of the FGPA, possible type options: XEM6310_LX150, XEM6310_LX45
    _fpga_type = ConfigOption('fpga_type', default='XEM6310_LX45', missing='warn')
    # specify the path to the bitfile, if it is not in qudi_main_dir/thirdparty/qo_fpga
    _path_to_bitfile = ConfigOption('path_to_bitfile', default=None, missing='nothing')
    # customize available switches in config. Each switch needs a tuple of 2 state names.
    _switches = ConfigOption(
        name='switches',
        default={s: ('Off', 'On') for s in ('B14', 'B16', 'B12', 'C7', 'D15', 'D10', 'D9', 'D11')},
        missing='nothing'
    )
    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default='OpalKelly FPGA Switch', missing='nothing')
    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=False, missing='nothing')

    # StatusVariable for remembering the last state of the hardware
    _states = StatusVar(name='states', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._fpga = None
        self._lock = RecursiveMutex()
        self._connected = False

    def on_activate(self):
        """ Connect and configure the access to the FPGA.
        """
        self._switches = self._chk_refine_available_switches(self._switches)

        # Create an instance of the Opal Kelly FrontPanel
        self._fpga = ok.FrontPanel()
        # Sanity check for fpga_type ConfigOption
        self._fpga_type = self._fpga_type.upper()
        if self._fpga_type not in ('XEM6310_LX45', 'XEM6310_LX150'):
            raise NameError('Unsupported FPGA type "{0}" specified in config. Valid options are '
                            '"XEM6310_LX45" and "XEM6310_LX150".\nAborting module activation.'
                            ''.format(self._fpga_type))
        # connect to the FPGA module
        self._connect()

        # reset states if requested, otherwise use the saved states
        if self._remember_states and isinstance(self._states, dict) and \
                set(self._states) == set(self._switches):
            self._states = {switch: self._states[switch] for switch in self._switches}
            self.states = self._states
        else:
            self._states = dict()
            self.states = {switch: states[0] for switch, states in self._switches.items()}

    def on_deactivate(self):
        """ Deactivate the FPGA.
        """
        del self._fpga
        self._connected = False

    def _connect(self):
        """ Connect host PC to FPGA module with the specified serial number.
        The serial number is defined by the mandatory ConfigOption fpga_serial.
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
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        return self._switches.copy()

    @property
    def states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        with self._lock:
            self._fpga.UpdateWireOuts()
            new_state = int(self._fpga.GetWireOutValue(0x20))
            self._states = dict()
            for channel_index, (switch, valid_states) in enumerate(self.available_states):
                if new_state & (1 << channel_index):
                    self._states[switch] = valid_states[1]
                else:
                    self._states[switch] = valid_states[0]
            return self._states.copy()

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        assert isinstance(state_dict, dict), \
            f'Property "state" must be dict type. Received: {type(state_dict)}'
        assert all(switch in self.available_states for switch in state_dict), \
            f'Invalid switch name(s) encountered: {tuple(state_dict)}'
        assert all(isinstance(state, str) for state in state_dict.values()), \
            f'Invalid switch state(s) encountered: {tuple(state_dict.values())}'

        with self._lock:
            # determine desired state of ALL switches
            new_states = self._states.copy()
            new_states.update(state_dict)
            # encode states into a single int
            new_channel_state = 0
            for channel_index, (switch, state) in enumerate(new_states.items()):
                if state == self.available_states[switch][1]:
                    new_channel_state |= 1 << channel_index

            # apply changes in hardware
            self._fpga.SetWireInValue(0x00, new_channel_state)
            self._fpga.UpdateWireIns()
            # Check for success
            assert self.states == new_states, 'Setting of channel states failed'

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        assert switch in self.available_states, 'Invalid switch name "{0}"'.format(switch)
        return self.states[switch]

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        self.states = {switch: state}

    @staticmethod
    def _chk_refine_available_switches(switch_dict):
        """ See SwitchInterface class for details

        @param dict switch_dict:
        @return dict:
        """
        refined = super()._chk_refine_available_switches(switch_dict)
        assert len(refined) == 8, 'Exactly 8 switches or None must be specified in config'
        assert all(len(s) == 2 for s in refined.values()), 'Switches can only take exactly 2 states'
        return refined
