# -*- coding: utf-8 -*-


"""
This file contains the Qudi hardware interface for the Swabian Instruments Pulse Streamer.

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


import pulsestreamer as ps

from core.configoption import ConfigOption
from core.module import Base



class PulseStreamer(Base):
    """Methods to control the Swabian Instruments Pulse Streamer 8/2

    Example config for copy-paste:

    pulsestreamer:
        module.Class: 'swabian_instruments.pulsestreamer_pi3.PulseStreamer'
        pulsestreamer_ip: '169.254.8.2'

    """

    _pulsestreamer_ip = ConfigOption(name='pulsestreamer_ip', default='192.168.202.200', missing='warn')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        try:
            self.pulser = ps.PulseStreamer(self._pulsestreamer_ip)
        except:
            print('Pulse Streamer could not be found.')

    def on_deactivate(self):
        self.pulser.reset() #resets pulse streamer
        del self.pulser #get rid of the object

    def run_sequence(self,sequence_dict,n_runs=-1):
        """
        Creates a pulse sequence specified by sequence_dict, uploads it to the pulsestreamer and starts it immediately.

        @param sequence_dict: Dict that contains the patterns for each channel.

            The dict should look like the following:

            {
                'd0' : pattern_ch0,
                'd1' : pattern_ch1,
                ...
                'd7' : pattern_ch7,
                'a0' : pattern_a0,
                'a1' : pattern_a1
            }

            where pattern_ch1 is an array of tupels, e.g. [(1000,1) , (1000,0)].
            First number is time in ns, second number is TTL-level (high or low).

        @param n_runs: number of times the sequence will be repeated. Putting -1 will loop indefinitely.

        """

        #sequence object is created
        sequence = self.pulser.createSequence()

        #map patterns to output channel
        #all patterns will be padded with zeros to match the length of the longest one.
        for key in sequence_dict.keys():
            num_ch = int(key[1])
            pattern = sequence_dict[key]
            if key[0] == 'd': #digital outputs
                sequence.setDigital(num_ch, pattern)
            if key[0] == 'a': #analog outputs
                sequence.setAnalog(num_ch, pattern)

        #closes sequences that might still be running. Otherwise upload speed could be reduced.
        self.pulser.forceFinal()
        # runs the sequence n_runs times
        self.pulser.stream(sequence, n_runs)
    
    def stop_sequence(self):
        """Sets all outputs to zero."""
        self.pulser.constant() #sets all outputs to zero