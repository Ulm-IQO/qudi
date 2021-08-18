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

        # list of the channel names
        self.list_ch_names = ['d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7']

        #create sequence dict
        self.sequence_dict = {}
        #create dict with the channels for constant output
        # label is ch name, value determines state (True = high)
        self.constant_dict = {}
        # create dict with the channels for constant low output
        # label is ch name, value determines state (True = low)
        self.low_dict = {}


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
    

    def set_constant(self,ch):
        """ Recodrs that channel ch needs to output constant high.
        
        @param ch: channel in question

        """
        self.constant_dict[ch] = True

    def set_low(self,ch):
        """ Recodrs that channel ch needs to output constant high.
        
        @param ch: channel in question

        """
        self.low_dict[ch] = True


    def run_sequence(self):
        """Tells the pulser to run the sequence indefinitely."""
        # find duration of longest pattern
        dur = 0
        for key in self.sequence_dict.keys():
            pattern = self.sequence_dict[key]
            ret = self.get_duration(pattern)
            if ret > dur:
                dur = ret
        #expand duration to be multiple of 8
        add = 8 - dur%8
        dur += add
        #set pattern to be constant output for each ch mentioned in constant dict
        for key in self.constant_dict.keys():
            self.sequence_dict[key] = [(dur,1)]
        # set pattern to be constant low output for the rest of the channels
        for ch in self.list_ch_names:
            if not ch in self.sequence_dict.keys():
                self.low_dict[ch] = True # this dict is not used, just for documentation purposes
                self.sequence_dict[key] = [(dur,0)]
        #run the sequence
        self.sigStart.emit(self.sequence_dict,-1)


    def stop_sequence(self):
        """Tells the pulser to stop the sequence."""
        self.sigStop.emit()
    

    def delete_pattern(self,ch):
        """Removes the sequence for the selected channel.

        @param ch: channel for which to remove the pattern.

        """

        # remove entry from sequence
        try:
            self.sequence_dict.pop(ch)
            print('removing sequence')
        except:
            pass
        # remove enty from boolean dict
        try:
            self.constant_dict.pop(ch)
            print('removing constant')
        except:
            pass


    def get_duration(self,pattern):
        """Calculates the duration (in ms) of a given pattern.

        @param pattern: pattern to analyze, needs to be in the form
            [(time,level),(time,level),...], e.g.
            [(1000,1),(500,0)]

        @return dur: integer, duration of the pattern in ms

        """
        dur = 0
        for i in range(len(pattern)):
            dur += pattern[i][0]
        return dur