# -*- coding: utf-8 -*-

"""
Buffers a hardware switch's state.

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

from core.module import Base
from interface.switch_interface import SwitchInterface
from core.configoption import ConfigOption
from core.connector import Connector
from qtpy import QtCore


class SwitchBufferInterfuse(Base, SwitchInterface):
    """ Methods to control slow (mechanical) laser switching devices.
    This interfuse in particular combines two switches into one.
    """

    # connectors for the switches to be combined
    switch = Connector(interface='SwitchInterface')

    # buffer timing
    _buffer_timing = ConfigOption(name='buffer_timing', default=0.1, missing='warn')
    
    _sig_start_buffer = QtCore.Signal()

    def on_activate(self):
        """ Activate the module and fill status variables.
        """
        self._new_states = None
        self._sig_start_buffer.connect(self._worker, QtCore.Qt.QueuedConnection)
        self._sig_start_buffer.emit()

    def on_deactivate(self):
        """ Deactivate the module and clean up.
        """
        self._sig_start_buffer.disconnect(self._worker)
    
    def _worker(self):
        if self._new_states is not None:
            try:
                self.switch().states = self._new_states
            finally:
                self._new_states = None
        self._states = self.switch().states

        QtCore.QTimer.singleShot(int(self._buffer_timing * 1e3), self._worker)

    @property
    def number_of_switches(self):
        """ Number of switches provided by this hardware.

        @return int: number of switches
        """
        return self.switch().number_of_switches

    @property
    def name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        return self.switch().name

    @property
    def names_of_states(self):
        """ Names of the states as a dict of lists.

        The keys contain the names for each of the switches and each of switches
        has a list of elements representing the names in the state order.
        The switch names might be extended by the name of the hardware as a prefix if extend_hardware_name is True.

        @return dict: A dict of the form {"switch": ["state1", "state2"]}
        """
        return self.switch().names_of_states

    @property
    def states(self):
        """ The current states the hardware is in.

        The states of the system as a dict consisting of switch names as keys and state names as values.
        The switch names might be extended by the name of the hardware as a prefix if extend_hardware_name is True.

        @return dict: All the current states of the switches in a state dict of the form {"switch": "state"}
        """
        return self._states

    @states.setter
    def states(self, value):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.
        The switch names might need to be extended by the name of the hardware as a prefix
        if extend_hardware_name is True.

        @param dict value: state dict of the form {"switch": "state"}
        @return: None
        """
        self._new_states = value