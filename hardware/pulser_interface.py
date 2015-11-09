# -*- coding: utf-8 -*-


from core.util.customexceptions import InterfaceImplementationError


class PulserInterface():
    """ UNSTABLE: Alex Stark, Nikolas Tomek

    Interface class to pass 

    Be careful in adjusting the method names in that class, since some of them
    are also connected to the mwsourceinterface (to give the AWG the possibility
    to act like a microwave source).
    """


    def pulser_on(self):
        """ Switches the pulsing device on. 
        
        @return int: error code (0:OK, -1:error)
        """ 
        raise InterfaceImplementationError('PulserInterface>on')
        return -1
    
    def pulser_off(self):
        """ Switches the pulsing device off. 
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>off')
        return -1

    def download_sequence(self, sequence, write_to_file = True):
        """ Generates from a given general Pulse_Sequence object a hardware specific sampled sequence (analogue and/or digital).
        These samples are then organized in a hardware specific data format and optionally saved in a file. Afterwards they get downloaded to the Hardware.
        
        @param Pulse_Sequence() sequence: The abstract Pulse_Sequence object to be sampled
        @param bool write_to_file: Flag to indicate if the samples should be written to a file (True) or uploaded directly to the pulse generator channels (False).
        
        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('PulserInterface>generate_sequence')
        return -1

    def load_sequence(self, seq_name, channel = None):
        """ Loads a sequence to the specified channel
        Unused for digital pulse generators without sequence storage capability (PulseBlaster, FPGA).
        
        @param str seq_name: The name of the sequence to be loaded
        @param int channel: The channel for the sequence to be loaded into if not already specified in the sequence itself
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>load_sequence')
        return -1
        
    def get_sequence_names(self):
        """ Used to get the names of all downloaded sequences on the device.
        Unused for digital pulse generators without sequence storage capability (PulseBlaster, FPGA).
        
        @return list: List of sequence name strings
        """
        names = []
        raise InterfaceImplementationError('PulserInterface>get_sequence_names')
        return names
        
    def delete_sequence(self, seq_name):
        """ Used to delete a sequence from the device memory.
        Unused for digital pulse generators without sequence storage capability (PulseBlaster, FPGA).
        
        @param str seq_name: The name of the sequence to be deleted
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>get_sequence_names')
        return -1

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return dict: dictionary containing status variables of the pulse generator hardware
        """
        status = {}
        raise InterfaceImplementationError('PulserInterface>get_status')
        return status

#    def configure(self):
#        """ Initialize and open the connection to the Pulser and configure it."""
#        
#        raise InterfaceImplementationError('PulserInterface>configure')
#        return -1

    def get_constraints(self):
        """ provides all the constraints (sampling_rate, amplitude, total_length_bins, channel_config, ...) 
        related to the pulse generator hardware to the caller. 
        Each constraint is a tuple of the form (min_value, max_value, stepsize).
        
        @return dict: dictionary holding the constraints for the sequence generation and GUI
        """
        constraints = {}
        raise InterfaceImplementationError('PulserInterface>get_constraints')
        return constraints
    
    def set_sampling_rate(self, sampling_rate):
        """ Set the sampling rate of the pulse generator hardware
        
        @param float sampling_rate: The sampling rate to be set (in Hz)
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>set_sampling_rate')
        return -1
        
    def set_amplitude(self, channel, amplitude):
        """ Set the output amplitude of the pulse generator hardware.
        Unused for purely digital hardware without logic level setting capability (DTG, FPGA, etc.).
        
        @param int channel: The channel to be reconfigured
        @param float amplitude: The peak-to-peak amplitude the channel should be set to (in V)
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>set_amplitude')
        return -1
        
    def set_active_channels(self, digital_channels, analogue_channels = 0):
        """ Set the active channels for the pulse generator hardware.
        
        @param int digital_channels: The number of digital channels
        @param int analogue_channels: The number of analogue channels
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>set_active_channels')
        return -1