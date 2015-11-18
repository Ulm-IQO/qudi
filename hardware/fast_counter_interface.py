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
"""

#####################################################
#                                                   #
#HARDWARE INTERFACE CURRENTLY NOT WORKING - ALEX S. #
#                                                   #
#####################################################


from core.util.customexceptions import InterfaceImplementationError

class FastCounterInterface():
    """ UNSTABLE: Alex Stark 
     Interface class to define the controls for fast counting devices. """
    
    
    def configure(self):
        """ Initialize and open the connection to the Fast Counter and configure it."""
        
        raise InterfaceImplementationError('FastCounterInterface>configure')
        return -1
        
    
    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as return value."""
        
        raise InterfaceImplementationError('FastCounterInterface>get_status')
        return -1
    
    def start_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>start')
        return -1
        
    def stop_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>stop')
        return -1
    
    def pause_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>pause_measure')
        return -1
    
    def continue_measure(self):
        
        raise InterfaceImplementationError('FastCounterInterface>continue_measure')
        return -1

    def is_gated(self):
        
        raise InterfaceImplementationError('FastCounterInterface>is_gated')
        return -1
   
    def get_data_trace(self):
        
        raise InterfaceImplementationError('FastCounterInterface>get_data_trace')
        return -1
      
#    def get_data_laserpulses(self):
#        """ To extract the laser pulses, a general routine should be written."""
#        
#        raise InterfaceImplementationError('FastCounterInterface>get_data_laserpulses')
#        return -1
        
#    def save_raw_trace(self,path):
#        """A fast way of saving the raw data directly."""
#        
#        raise InterfaceImplementationError('FastCounterInterface>save_raw_trace')
#        return -1
#        
#    def save_raw_laserpulses(self,path):
#        """A fast way of saving the raw data directly."""
#        
#        raise InterfaceImplementationError('FastCounterInterface>save_raw_laserpulses')
#        return -1