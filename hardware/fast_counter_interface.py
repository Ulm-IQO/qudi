# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware interface for fast counting devices.

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

Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
Copyright (C) 2015 Nikolas Tomek nikolas.tomek@uni-ulm.de
"""

from core.util.customexceptions import InterfaceImplementationError

class FastCounterInterface():
    """
    Interface class to define the controls for fast counting devices.
    """

    def configure(self, bin_width_s, record_length_s, number_of_gates = 0):
        """
        Configuration of the fast counter.
        bin_width_s: Length of a single time bin in the time trace histogram in seconds.
        record_length_s: Total length of the timetrace/each single gate in seconds.
        number_of_gates: Number of gates in the pulse sequence. Ignore for ungated counter.
        Returns the actually set values as tuple
        """
        raise InterfaceImplementationError('FastCounterInterface>configure')
        return (1e-9, 4000e-9, 0)

    def get_status(self):
        """
        Receives the current status of the Fast Counter and outputs it as return value.
        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        raise InterfaceImplementationError('FastCounterInterface>get_status')
        return -1
    
    def start_measure(self):
        """
        Starts the fast counter.
        """
        raise InterfaceImplementationError('FastCounterInterface>start')
        return -1
        
    def stop_measure(self):
        """
        Stops the fast counter.
        """
        raise InterfaceImplementationError('FastCounterInterface>stop')
        return -1
    
    def pause_measure(self):
        """
        Pauses the current measurement if the fast counter is in running state.
        """
        raise InterfaceImplementationError('FastCounterInterface>pause_measure')
        return -1
    
    def continue_measure(self):
        """
        Continues the current measurement if the fast counter is in pause state.
        """
        raise InterfaceImplementationError('FastCounterInterface>continue_measure')
        return -1

    def is_gated(self):
        """
        Boolean return value indicates if the fast counter is a gated counter (TRUE) or not (FALSE).
        """
        raise InterfaceImplementationError('FastCounterInterface>is_gated')
        return -1

    def get_binwidth(self):
        """
        returns the width of a single timebin in the timetrace in seconds
        """
        raise InterfaceImplementationError('FastCounterInterface>get_binwidth')
        return -1
   
    def get_data_trace(self):
        """
        Polls the current timetrace data from the fast counter and returns it as a numpy array (dtype = int64).
        The binning specified by calling configure() must be taken care of in this hardware class.
        A possible overflow of the histogram bins must be caught here and taken care of.
        If the counter is UNgated it will return a 1D-numpy-array with returnarray[timebin_index]
        If the counter is gated it will return a 2D-numpy-array with returnarray[gate_index, timebin_index]
        """
        raise InterfaceImplementationError('FastCounterInterface>get_data_trace')
        return -1

