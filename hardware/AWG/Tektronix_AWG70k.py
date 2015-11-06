# -*- coding: utf-8 -*-
"""
Created on Fri Aug 21 12:31:16 2015

@author: s_ntomek
"""

from socket import socket, AF_INET, SOCK_STREAM
from ftplib import FTP
from io import StringIO
import time
from collections import OrderedDict
from core.base import Base
from core.util.mutex import Mutex
import numpy as np
import hdf5storage
import copy


class AWG(Base):
    """ UNSTABLE: Nikolas
    """
    _modclass = 'AWG'
    _modtype = 'hardware'
    
    # declare connectors
    _out = {'AWG': 'AWG'}

    def __init__(self,manager, name, config = {}, **kwargs):

        state_actions = {'onactivate'   : self.activation,
                         'ondeactivate' : self.deactivation}

        Base.__init__(self, manager, name, config, state_actions, **kwargs)
        
        if 'awg_IP_address' in config.keys():
            self.ip_address = config['awg_IP_address']
        else:
            self.logMsg("This is AWG: Did not find >>awg_IP_address<< in configuration.", msgType='error')
            
        if 'awg_port' in config.keys():
            self.port = config['awg_port']
        else:
            self.logMsg("This is AWG: Did not find >>awg_port<< in configuration.", msgType='error')
        
        self.max_samplerate = 50e9
        self.samplerate = 25e9
        self.amplitude = 0.25
        self.loaded_sequence = None
        self.use_sequencer = False
        
        self.waveform_directory_awg = ''
        self.waveform_directory_host = ''

    
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        # connect ethernet socket and FTP        
#        self.soc = socket(AF_INET, SOCK_STREAM)
#        self.soc.connect((self.ip_address, self.port))
#        self.ftp = FTP(self.ip_address)
#        self.ftp.login()
#        self.ftp.cwd('/waves') # hardcoded default folder
#        
#        self.input_buffer = int(2 * 1024)
#        
        self.connected = True
        
    
    def deactivation(self, e):
        '''Tasks that are required to be performed during deactivation of the module.
        '''        
        # Closes the connection to the AWG via ftp and the socket
#        self.tell('\n')
#        self.soc.close()
#        self.ftp.close()

        self.connected = False
        pass
    
    def _write_to_matfile(self, sequence):
        matcontent = {}
        sample_arr, marker1_arr, marker2_arr = self._sample_sequence(sequence)
            
        matcontent[u'Waveform_Name_1'] = sequence.name # each key must be a unicode string
        matcontent[u'Waveform_Data_1'] = sample_arr[0]
        matcontent[u'Waveform_M1_1'] = marker1_arr[0]
        matcontent[u'Waveform_M2_1'] = marker2_arr[0]
        matcontent[u'Waveform_Sampling_Rate_1'] = self.samplerate
        matcontent[u'Waveform_Amplitude_1'] = self.amplitude
        
        if marker1_arr.shape[0] == 2:
            matcontent[u'Waveform_Name_2'] = sequence.name + '_Ch2'
            matcontent[u'Waveform_Data_2'] = sample_arr[1]
            matcontent[u'Waveform_M1_2'] = marker1_arr[1]
            matcontent[u'Waveform_M2_2'] = marker2_arr[1]
            matcontent[u'Waveform_Sampling_Rate_2'] = self.samplerate
            matcontent[u'Waveform_Amplitude_2'] = self.amplitude
        
        hdf5storage.write(matcontent, '.', name+'.mat', matlab_compatible=True)
        return
        
        
    def generate_sampled_sequence(self, sequence):
        self._write_to_matfile(sequence)            
        return
    
    
    def _refine_sequence(self, sequence):
        sequence_ch1 = copy.deepcopy(sequence)
        sequence_ch2 = copy.deepcopy(sequence)
        for block, reps in sequence_ch1.block_list:
            for element in block.element_list:
                element.pulse_function = element.pulse_function[0]
                element.marker_active = element.markers_on[0:2]
                for key in element.parameters.keys():
                    entry_length = len(element.parameters[key])
                    element.parameters[key] = element.parameters[key][0:entry_length//2]
        for block, reps in sequence_ch2.block_list:
            for element in block.element_list:
                element.pulse_function = element.pulse_function[1]
                element.marker_active = element.markers_on[2:4]
                for key in element.parameters.keys():
                    entry_length = len(element.parameters[key])
                    element.parameters[key] = element.parameters[key][entry_length//2:entry_length]
        return sequence_ch1, sequence_ch2
    
    
    
    def _sample_sequence(self, sequence):
        """ Calculates actual sample points given a Sequence.
        """
        arr_len = np.round(sequence.length_bins*1.01)
        chnl_num = sequence.analogue_channels
    
        sample_arr = np.empty([chnl_num, arr_len])
        marker1_arr = np.zeros([chnl_num, arr_len], dtype = bool)
        marker2_arr = np.zeros([chnl_num, arr_len], dtype = bool)          

        entry = 0
        bin_offset = 0
        for block, reps in sequence.block_list:
            for rep_no in range(reps+1):
                temp_sample_arr, temp_marker1_arr, temp_marker2_arr = self._sample_block(block, rep_no, bin_offset)
                temp_len = temp_sample_arr.shape[1]
                sample_arr[:, entry:temp_len+entry] = temp_sample_arr
                marker1_arr[:, entry:temp_len+entry] = temp_marker1_arr
                marker2_arr[:, entry:temp_len+entry] = temp_marker2_arr
                entry += temp_len
                if sequence.rotating_frame:
                    bin_offset = entry
        # slice the sample array to cut off uninitialized entrys at the end
        return sample_arr[:, :entry], marker1_arr[:, :entry], marker2_arr[:, :entry]
    
            
    def _sample_block(self, block, iteration_no = 0, bin_offset = 0):
        """ Calculates actual sample points given a Block.
        """
        chnl_num = block.analogue_channels
        block_length_bins = block.init_length_bins + (block.increment_bins * iteration_no)
        arr_len = np.round(block_length_bins*1.01)
        sample_arr = np.empty([chnl_num ,arr_len])
        marker1_arr = np.zeros([chnl_num, arr_len], dtype = bool)
        marker2_arr = np.zeros([chnl_num, arr_len], dtype = bool)
        entry = 0
        bin_offset_temp = bin_offset
        for block_element in block.element_list:
            temp_sample_arr, temp_marker1_arr, temp_marker2_arr = self._sample_block_element(block_element, iteration_no, bin_offset_temp)
            temp_len = temp_sample_arr.shape[1]
            sample_arr[:, entry:temp_len+entry] = temp_sample_arr
            marker1_arr[:, entry:temp_len+entry] = temp_marker1_arr
            marker2_arr[:, entry:temp_len+entry] = temp_marker2_arr
            entry += temp_len
            bin_offset_temp = bin_offset + entry
        # slice the sample array to cut off uninitialized entrys at the end
        return sample_arr[:, :entry], marker1_arr[:, :entry], marker2_arr[:, :entry]
            

    def _sample_block_element(self, block_element, iteration_no = 0, bin_offset = 0):
        """ Calculates actual sample points given a Block_Element.
        """
        chnl_num = block_element.analogue_channels
        parameters = block_element.parameters
        init_length_bins = block_element.init_length_bins
        increment_bins = block_element.increment_bins
        markers_on = block_element.markers_on
        pulse_function = block_element.pulse_function
            
        element_length_bins = init_length_bins + (iteration_no*increment_bins)
        sample_arr = np.empty([chnl_num, element_length_bins])
        marker1_arr = np.empty([chnl_num, element_length_bins], dtype = bool)
        marker2_arr = np.empty([chnl_num, element_length_bins], dtype = bool)
        time_arr = (bin_offset + np.arange(element_length_bins)) / self.samplerate

        for i, func_name in enumerate(pulse_function):
            sample_arr[i] = self._math_function(func_name, time_arr, parameters[i])
            marker1_arr[i] = np.full(element_length_bins, markers_on[0+i], dtype = bool)
            marker2_arr[i] = np.full(element_length_bins, markers_on[1+i], dtype = bool)
            
        return sample_arr, marker1_arr, marker2_arr
    
    
    def download_waveform(self, waveform_name):
        pass
    
    def delete_waveform_from_awg(self, waveform_name):
        pass
        
    def delete_waveform_from_host(self, waveform_name):
        pass
    
    def change_waveform_directory_awg(self, dir_path):
        self.waveform_directory_awg = dir_path
        pass
    
    def change_waveform_directory_host(self, dir_path):
        self.waveform_directory_host = dir_path
        return
    
    
    def _math_function(self, func_name, time_arr, parameters={}):
        """ actual mathematical function of the block_elements.
        parameters is a dictionary
        """
        if func_name == 'DC':
            amp = parameters['amplitude'][0]
            result_arr = np.full(len(time_arr), amp)
            
        elif func_name == 'idle':
            result_arr = np.zeros(len(time_arr))
            
        elif func_name == 'sin':
            amp = parameters['amplitude'][0]
            freq = parameters['frequency'][0]
            phase = 180*np.pi * parameters['phase'][0]
            result_arr = amp * np.sin(2*np.pi * freq * time_arr + phase)
            
        elif func_name == 'doublesin':
            amp1 = parameters['amplitude'][0]
            amp2 = parameters['amplitude'][1]
            freq1 = parameters['frequency'][0]
            freq2 = parameters['frequency'][1]
            phase1 = 180*np.pi * parameters['phase'][0]
            phase2 = 180*np.pi * parameters['phase'][1]
            result_arr = amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1) 
            result_arr += amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2)
            
        elif func_name == 'triplesin':
            amp1 = parameters['amplitude'][0]
            amp2 = parameters['amplitude'][1]
            amp3 = parameters['amplitude'][2]
            freq1 = parameters['frequency'][0]
            freq2 = parameters['frequency'][1]
            freq3 = parameters['frequency'][2]
            phase1 = 180*np.pi * parameters['phase'][0]
            phase2 = 180*np.pi * parameters['phase'][1]
            phase3 = 180*np.pi * parameters['phase'][2]
            result_arr = amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1) 
            result_arr += amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2)
            result_arr += amp3 * np.sin(2*np.pi * freq3 * time_arr + phase3)
            
        return result_arr
    
    def delete(self, filelist):
        
        for filename in filelist:
            self.ftp.delete(filename)
        return
    
    def delete_all(self):
        
        filelist = self.ftp.mlsd()
        for filename in filelist:
            self.ftp.delete(filename)
        return
        
    def tell(self, command):
        """Send a command string to the AWG."""
        if not command.endswith('\n'): # I always forget the line feed.
            command += '\n'
        command = bytes(command, 'UTF-8') # In Python 3.x the socket send command only accepts byte type arrays and no str
        self.soc.connect((self.ip_address, self.port))
        self.soc.send(command)
        self.soc.close()
        return
        
    def ask(self, question):
        """Asks the AWG a 'question' and receive and return an answer from AWG.
        @param: question: string which has to have a proper format to be able
                            to receive an answer.
        @return: the answer of the AWG to the 'question' in a string
        """
        if not question.endswith('\n'): # I always forget the line feed.
            question += '\n'
        question = bytes(question, 'UTF-8') # In Python 3.x the socket send command only accepts byte type arrays and no str
        self.soc.connect((self.ip_address, self.port))
        self.soc.send(question)    
        time.sleep(1)                   # you need to wait until AWG generating
                                        # an answer.
        message = self.soc.recv(self.input_buffer)  # receive an answer
        message = message.decode('UTF-8') # decode bytes into a python str
        message = message.replace('\n','')      # cut away the characters\r and \n.
        message = message.replace('\r','')
        self.soc.close()
        return message
    
    def run(self):
        self.soc.connect((self.ip_address, self.port))
        self.soc.send('AWGC:RUN\n')
        self.soc.close()
        
    def stop(self):
        self.soc.connect((self.ip_address, self.port))
        self.soc.send('AWGC:STOP\n')
        self.soc.close()
        
    def get_status(self):
        """ Asks the current state of the AWG.
        @return: an integer with the following meaning: 
                0 indicates that the instrument has stopped.
                1 indicates that the instrument is waiting for trigger.
                2 indicates that the instrument is running.
               -1 indicates that the request of the status for AWG has failed.
                """
        self.soc.connect((self.ip_address, self.port))
        self.soc.send('AWGC:RSTate?\n') # send at first a command to request.
        time.sleep(1)                   # you need to wait until AWG generating
                                        # an answer.
        message = self.soc.recv(self.input_buffer)  # receive an answer
        self.soc.close()
        # the output message contains always the string '\r\n' at the end. Use
        # the split command to get rid of this
        try:
            return int(message.split('\r\n',1)[0])
        except:
            # if nothing comes back than the output should be marked as error
            return -1
            
    def get_sequencer_mode(self, output_as_int=False):
        """ Asks the AWG which sequencer mode it is using. It can be either in 
        Hardware Mode or in Software Mode. The optional variable output_as_int
        sets if the returned value should be either an integer number or string.
        
        @param: output_as_int: optional boolean variable to set the output
        @return: an string or integer with the following meaning:
                'HARD' or 0 indicates Hardware Mode
                'SOFT' or 1 indicates Software Mode
                'Error' or -1 indicates a failure of request
        """
        self.soc.connect((self.ip_address, self.port))
        self.soc.send('AWGControl:SEQuencer:TYPE?\n')
        time.sleep(1)
        message = self.soc.recv(self.input_buffer)
        self.soc.close()
        if output_as_int == True:
            if 'HARD' in message:
                return 0
            elif 'SOFT' in message:
                return 1
            else:
                return -1
        else:
            if 'HARD' in message:
                return 'Hardware-Sequencer'
            elif 'SOFT' in message:
                return 'Software-Sequencer'
            else:
                return 'Request-Error'
                
    def set_Interleave(self, state=False):
        """Turns Interleave of the AWG on or off.
            @param state: A Boolean, defines if Interleave is turned on or off, Default=False
        """
        self.soc.connect((self.ip_address, self.port))
        if(state):
            print('interleave is on')
            self.soc.send('AWGC:INT:STAT 1\n')
        else:
            print('interleave is off')
            self.soc.send('AWGC:INT:STAT 0\n')
        self.soc.close()
        return    
    
    def set_output(self, state, channel=3):
        """Set the output state of specified channels.
        
        @param state:  on : 'on', 1 or True; off : 'off', 0 or False
        @param channel: integer,   1 : channel 1; 2 : channel 2; 3 : both (default)
        
        """
        #TODO: AWG.set_output: implement swap
        look_up = {'on' : 1, 1 : 1, True : 1,
                   'off' : 0, 0 : 0, False : 0
                  }
        self.soc.connect((self.ip_address, self.port))
        if channel & 1 == 1:
            self.soc.send('OUTP1 %i\n' % look_up[state])
        if channel & 2 == 2:
            self.soc.send('OUTP2 %i\n' % look_up[state])
        self.soc.close()
        return
        
    def set_mode(self, mode):
        """Change the output mode.

        @param  mode: Options for mode (case-insensitive):
        continuous - 'C'
        triggered  - 'T'
        gated      - 'G'
        sequence   - 'S'
        
        """
        look_up = {'C' : 'CONT',
                   'T' : 'TRIG',
                   'G' : 'GAT' ,
                   'E' : 'ENH' , 
                   'S' : 'SEQ'
                  }
        self.soc.connect((self.ip_address, self.port))
        self.soc.send('AWGC:RMOD %s\n' % look_up[mode.upper()])
        self.soc.close()
        return
        
    def set_sample(self, frequency):
        """Set the output sampling rate.
        
        @param frequency: sampling rate [GHz] - min 5.0E-05 GHz, max 24.0 GHz 
        """
        self.soc.connect((self.ip_address, self.port))
        self.soc.send('SOUR:FREQ %.4GGHz\n' % frequency)
        self.soc.close()
        return
        
    def set_amp(self, voltage, channel=3):
        """Set output peak-to-peak voltage of specified channel.
        
        @param voltage: output Vpp [V] - min 0.05 V, max 2.0 V, step 0.001 V
        @param channel:  1 : channel 1; 2 : channel 2; 3 : both (default)
        
        """
        self.soc.connect((self.ip_address, self.port))
        if channel & 1 == 1:
            self.soc.send('SOUR1:VOLT %.4GV\n' % voltage)
        if channel & 2 == 2:
            self.soc.send('SOUR2:VOLT %.4GV\n' % voltage)
        self.soc.close()
        return
    
    def set_jump_timing(self, synchronous = False):
        """Sets control of the jump timing in the AWG to synchoronous or asynchronous.
        If the Jump timing is set to asynchornous the jump occurs as quickly as possible 
        after an event occurs (e.g. event jump tigger), if set to synchornous 
        the jump is made after the current waveform is output. The default value is asynchornous
        
        @param synchronous: Bool, if True the jump timing will be set to synchornous, 
        if False the jump timing will be set to asynchronous
        """
        self.soc.connect((self.ip_address, self.port))
        if(synchronous):
            self.soc.send('EVEN:JTIM SYNC\n')
        else:
            self.soc.send('EVEN:JTIM ASYNC\n')
        self.soc.close()
        return
            
    def load(self, filename, channel=1, cwd=None):
        """Load sequence or waveform file into RAM, preparing it for output.
        
        Waveforms and single channel sequences can be assigned to each or both
        channels. Double channel sequences must be assigned to channel 1.
        The AWG's file system is case-sensitive.
        
        @param filename:  *.SEQ or *.WFM file name in AWG's CWD
        @param channel: 1 : channel 1 (default); 2 : channel 2; 3 : both
        @param cwd: filepath where the waveform to be loaded is stored. Default: 'C:\InetPub\ftproot\waves'
        """
        if cwd is None:
            cwd = 'C:\\InetPub\\ftproot\\waves' # default
        self.soc.connect((self.ip_address, self.port))
        if channel & 1 == 1:
            self.soc.send('SOUR1:FUNC:USER "%s/%s"\n' % (cwd, filename))
        if channel & 2 == 2:
            self.soc.send('SOUR2:FUNC:USER "%s/%s"\n' % (cwd, filename))
        self.soc.close()
        return
    
    def clear_AWG(self):
        """ Delete all waveforms and sequences from Hardware memory and clear the visual display """
        self.soc.connect((self.ip_address, self.port))
        self.soc.send('WLIS:WAV:DEL ALL\n')
        self.soc.close()
        return
    
    def reset(self):
        """Reset the AWG."""
        self.soc.connect((self.ip_address, self.port))
        self.soc.send('*RST\n')
        self.soc.close()
        return

    def max_samplerate(self):
        return_val = self.max_samplerate
        return return_val