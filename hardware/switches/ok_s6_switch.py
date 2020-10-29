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

    # serial number of the FPGA
    _serial = ConfigOption('fpga_serial', missing='error')

    # Type of the FGPA, possible type options: XEM6310_LX150, XEM6310_LX45
    _fpga_type = ConfigOption('fpga_type', default='XEM6310_LX45', missing='warn')

    # specify the path to the bitfile, if it is not in qudi_main_dir/thirdparty/qo_fpga
    _path_to_bitfile = ConfigOption('path_to_bitfile', default=None, missing='nothing')

    # names_of_switches defines what switches there are, it should be a list of strings
    _names_of_switches = ConfigOption(name='names_of_switches', default=None, missing='nothing')

    # names_of_states defines states for each switch, it can define any number of states greater one per switch.
    # A 2D list of lists defined specific states for each switch
    # and a simple 1D list defines the same states for each of the switches.
    _names_of_states = ConfigOption(name='names_of_states', default=['Off', 'On'], missing='nothing')

    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')

    # if remember_states is True the last state will be restored at reloading of the module
    _remember_states = ConfigOption(name='remember_states', default=False, missing='nothing')

    # StatusVariable for remembering the last state of the hardware
    _states = StatusVar(name='states', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._fpga = None
        self._lock = Mutex()
        self._connected = False

    def on_activate(self):
        """ Connect and configure the access to the FPGA.
        """
        # Create an instance of the Opal Kelly FrontPanel. The Frontpanel is a
        # c dll which was wrapped with SWIG for Windows type systems to be
        # accessed with python 3.4. You have to ensure to use the python 3.4
        # version to be able to run the Frontpanel wrapper:
        self._fpga = ok.FrontPanel()

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

        try:
            if len(self._names_of_switches) == self.number_of_switches and not isinstance(self._names_of_switches, str):
                self._names_of_switches = list(self._names_of_switches)
            else:
                raise TypeError
        except TypeError:
            self._names_of_switches = ['B14', 'B16', 'B12', 'C7', 'D15', 'D10', 'D9', 'D11']

        if isinstance(self._names_of_states, (list, tuple)) \
                and len(self._names_of_states) == len(self._names_of_switches) \
                and isinstance(self._names_of_states[0], (list, tuple)) \
                and len(self._names_of_states[0]) > 1:
            self._names_of_states = {switch: [str(name) for name in self._names_of_states[index]]
                                     for index, switch in enumerate(self._names_of_switches)}
        else:
            self.log.error(f'names_of_states must be a list of length {len(self._names_of_switches)}, '
                           f'with the elements being a list of two or more names for the states.')

        # reset states if requested, otherwise use the saved states
        if not self._remember_states \
                or not isinstance(self._states, dict) \
                or len(self._states) != self.number_of_switches:
            self.states = {name: self._names_of_states[name][0] for name in self._names_of_switches}
        else:
            self.states = self._states

    def on_deactivate(self):
        """ Deactivate the FPGA.
        """
        if self._connected and not self._remember_states:
            self.states = False
        del self._fpga
        self._connected = False
        return

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
    def number_of_switches(self):
        """ Number of switches provided by this hardware is 8.

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

    @property
    def name(self):
        """ Name of the hardware as string.

        The name can either be defined as ConfigOption (name) or it defaults to the name of the hardware module.

        @return str: The name of the hardware
        """
        return self._hardware_name

    @property
    def names_of_states(self):
        """ Names of the states as a dict of lists.

        The keys contain the names for each of the switches and each of switches
        has a list of elements representing the names in the state order.
        The names can be defined by a ConfigOption (names_of_states) or they default to ['Off', 'On'].

        @return dict: A dict of the form {"switch": ["state1", "state2"]}
        """
        return self._names_of_states.copy()

    @property
    def states(self):
        """ The current states the hardware is in.

        The states of the system as a dict consisting of switch names as keys and state names as values.

        @return dict: All the current states of the switches in a state dict of the form {"switch": "state"}
        """
        self._states = dict()
        with self._lock:
            self._fpga.UpdateWireOuts()
            new_state = int(self._fpga.GetWireOutValue(0x20))
            for channel_index in range(self.number_of_switches):
                switch = self._names_of_switches[channel_index]
                if new_state & (2 ** channel_index) != 0:
                    self._states[switch] = self._names_of_states[switch][1]
                else:
                    self._states[switch] = self._names_of_states[switch][0]
            return self._states.copy()

    @states.setter
    def states(self, value):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict value: state dict of the form {"switch": "state"}
        @return: None
        """
        if isinstance(value, dict):
            for switch, state in value.items():
                if switch not in self._names_of_switches:
                    self.log.warning(f'Attempted to set a switch of name "{switch}" but it does not exist.')
                    continue

                states = self.names_of_states[switch]
                if isinstance(state, str):
                    if state not in states:
                        self.log.error(f'"{state}" is not among the possible states: {states}')
                        continue
                    self._states[switch] = state
        else:
            self.log.error(f'attempting to set states as "{value}" while states have be a dict '
                           f'having the switch names as keys and the state names as values.')

        with self._lock:
            # encode channel states
            channel_state = 0
            for channel_index in range(self.number_of_switches):
                switch = self._names_of_switches[channel_index]
                if self._states[switch] == self._names_of_states[switch][1]:
                    channel_state += int(2 ** channel_index)

            old_states = self._states.copy()
            # apply changes in hardware
            self._fpga.SetWireInValue(0x00, channel_state)
            self._fpga.UpdateWireIns()

        # check if the state was actually set
        if old_states != self.states:
            self.log.error('Setting of channel states in hardware failed.')
