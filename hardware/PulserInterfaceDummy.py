# -*- coding: utf-8 -*-

from core.base import Base
from hardware.PulserInterface import PulserInterface
from collections import OrderedDict
import time
from core.util.customexceptions import InterfaceImplementationError


class PulserInterfaceDummy(Base, PulserInterface):
    """ UNSTABLE: Alex Stark 

    Interface class to pass 

    Be careful in adjusting the method names in that class, since some of them
    are also connected to the mwsourceinterface (to give the AWG the possibility
    to act like a microwave source).
    """
    
    def __init__(self, manager, name, config, **kwargs):
        state_actions = {'onactivate'   : self.activation,
                         'ondeactivate' : self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)
        
        self._modclass = 'PulserInterface'
        self._modtype = 'hardware'

        self.connector['out']['pulsegenerator'] = OrderedDict()
        self.connector['out']['pulsegenerator']['class'] = 'PulserInterfaceDummy'
        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')

    def activation(self, e):
        pass
    
    def deactivation(self, e):
        pass

    def on(self):
        """ Switches on any preconfigured pulsing source on. 
        
        @return int: error code (0:OK, -1:error)
        """ 
        raise InterfaceImplementationError('PulserInterface>on')
        return -1
    
    def off(self):
        """ Switches off any pulsing device off. 
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>off')
        return -1

    def generate_pulse_form(self):
        """ Generates from a given general pulse pattern a single PulseBlock 
        (for PulseBlaser, DTG, FPGA) or a waveform (AWG)
        which is in general a pure file and contains only instructions without a
        sequence or a loop like structure.

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('PulserInterface>generate_pulse_form')
        return -1

    def generate_sequence(self):
        """ Generates from a given general sequence a combination of PulseBlocks
        which are already created. 
        That sequence is a pattern how the already created PulseBlocks 
        (for PulseBlaser, DTG, FPGA) or a waveform (AWG) are arranged together
        enabling a repeatable and loop-like structure. That modus is only 
        possible for PulseBlaser, DTG and AWG. The FPGA has not such an option,
        yet.
        
        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('PulserInterface>generate_sequence')
        return -1

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('PulserInterface>get_status')
        return -1

    def configure(self):
        """ Initialize and open the connection to the Pulser and configure it."""
        
        raise InterfaceImplementationError('PulserInterface>configure')
        return -1
