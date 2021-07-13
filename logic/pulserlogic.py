#-*- coding: utf-8 -*-


"""
This file contains the Qudi logic file for a pulsing device.

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

from core.connector import Connector
from logic.generic_logic import GenericLogic


class PulserLogic(GenericLogic):
    """
    Logic module for the Pulse Streamer.

    Example config for copy paste:

    pulserlogic:
        module.Class: 'pulserlogic.PulserLogic'
        connect:
            pulsestreamer: 'pulsestreamer'
    
    """
    
    #declare connector
    pulsestreamer = Connector(interface='PulseStreamer')

    #signal to hardware
    sigStart = QtCore.Signal(dict,int)
    sigStop = QtCore.Signal()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def on_activate(self):
        self._pulser = self.pulsestreamer()

        #connect signals to hardware file
        self.sigStart.connect(self._pulser.run_sequence)
        self.sigStop.connect(self._pulser.stop_sequence)

        #create sequence dict
        self.sequence_dict = {}

    def on_deactivate(self):
        pass

    def store_pattern(self,ch,pattern):
        """Stores the pattern in a dict.
        
        @param ch: name of the channel for the pattern.
            Names are either 'd0' ... 'd7' or 'a0', 'a1'.
        
        @param pattern: pattern that will be streamed on the output channel.
            Need to be a list of tupels like this: [(1000,1) , (1000,0)]
            First number is time in ns, second number is TTL-level (high or low).

        """
        self.sequence_dict[ch] = pattern
    
    def run_sequence(self):
        """Tells the pulser to run the sequence indefinitely."""
        self.sigStart.emit(self.sequence_dict,-1)

    def stop_sequence(self):
        """Tells the pulser to stop the sequence."""
        self.sigStop.emit()