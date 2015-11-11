# -*- coding: utf-8 -*-


from core.util.customexceptions import InterfaceImplementationError


class PulserInterface():
    """ UNSTABLE: Nikolas Tomek

    Interface class to pass 
    """


    def pulser_on(self):
        """ Switches the pulsing device on. 
        
        @return int: error code (0:OK, -1:error)
        """ 
        raise InterfaceImplementationError('PulserInterface>pulser_on')
        return -1
    
    def pulser_off(self):
        """ Switches the pulsing device off. 
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>pulser_off')
        return -1

    def download_sequence(self, waveform, write_to_file = True):
        """ Brings the numpy arrays containing the samples in the Waveform() object into a format the hardware understands.
        Optionally this is then saved in a file. Afterwards they get downloaded to the Hardware.
        
        @param Waveform() waveform: The raw sampled pulse sequence.
        @param bool write_to_file: Flag to indicate if the samples should be written to a file (True) or uploaded directly to the pulse generator channels (False).
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>download_sequence')
        return -1
        
    def send_file(self, filepath):
        """ Sends an already hardware specific waveform file to the pulse generators waveform directory.
        Unused for digital pulse generators without sequence storage capability (PulseBlaster, FPGA).
        
        @param string filepath: The file path of the source file
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>send_file')
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
        
    def clear_channel(self, channel):
        """ Clears the loaded waveform from the specified channel
        Unused for digital pulse generators without sequence storage capability (PulseBlaster, FPGA).
        
        @param int channel: The channel to be cleared
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>clear_channel')
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
        raise InterfaceImplementationError('PulserInterface>delete_sequence')
        return -1

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return dict: dictionary containing status variables of the pulse generator hardware
        """
        status = {}
        raise InterfaceImplementationError('PulserInterface>get_status')
        return status

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
        
        @return foat: the sample rate returned from the device (-1:error)
        """
        raise InterfaceImplementationError('PulserInterface>set_sampling_rate')
        return -1.
        
    def get_sampling_rate(self):
        """ Get the sampling rate of the pulse generator hardware
        
        @return float: The current sampling rate of the device (in Hz)
        """
        raise InterfaceImplementationError('PulserInterface>get_sampling_rate')
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
        
    def get_amplitude(self, channel):
        """ Get the output amplitude of the pulse generator hardware.
        Unused for purely digital hardware without logic level setting capability (FPGA, etc.).
        
        @param int channel: The channel to be checked
        
        @return float: The peak-to-peak amplitude the channel is set to (in V)
        """
        raise InterfaceImplementationError('PulserInterface>get_amplitude')
        return -1
        
    def set_active_channels(self, digital_channels, analogue_channels = 0):
        """ Set the active channels for the pulse generator hardware.
        
        @param int digital_channels: The number of digital channels
        @param int analogue_channels: The number of analogue channels
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>set_active_channels')
        return -1
        
    def get_active_channels(self):
        """ Get the active channels of the pulse generator hardware.
        
        @return (int, int): number of active channels (analogue, digital)
        """
        raise InterfaceImplementationError('PulserInterface>get_active_channels')
        return (-1, -1)
    
    def set_sequence_directory(self, dir_path):
        """ Change the directory where the sequences are stored on the device.
        Unused for digital pulse generators without sequence storage capability (PulseBlaster, FPGA).
        
        @param string dir_path: The target directory
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>set_sequence_directory')
        return -1
        
    def get_sequence_directory(self):
        """ Ask for the directory where the sequences are stored on the device.
        Unused for digital pulse generators without sequence storage capability (PulseBlaster, FPGA).
        
        @return string: The current sequence directory
        """
        raise InterfaceImplementationError('PulserInterface>get_sequence_directory')
        return ''
        
    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.
        Unused for pulse generator hardware other than an AWG.
        
        @param bool state: The state the interleave should be set to (True: ON, False: OFF)
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>set_interleave')
        return -1
    
    def tell(self, command):
        """ Sends a command string to the device.
        
        @param string question: string containing the command
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>tell')
        return -1
    
    def ask(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.
        
        @param string question: string containing the command
        
        @return string: the answer of the device to the 'question' in a string
        """
        raise InterfaceImplementationError('PulserInterface>ask')
        return ''
        
    def reset(self):
        """Reset the device.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('PulserInterface>reset')
        return -1