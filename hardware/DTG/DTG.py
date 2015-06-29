# -*- coding: utf-8 -*-


import struct
import visa
from collections import OrderedDict
from core.base import Base
from core.util.mutex import Mutex

#the next import is only needed for the FastWrite method
#import DTG_IO 


class DTG(Base):
    """ UNSTABLE: Christoph
    """
    
    def __init__(self,manager, name, config = {}, **kwargs):

        state_actions = {'onactivate'   : self.activation,
                         'ondeactivate' : self.deactivation}

        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        self._modclass = 'DTG'
        self._modtype = 'hardware'

        # declare connectors
        self.connector['out']['DTG'] = OrderedDict()
        self.connector['out']['DTG']['class'] = 'DTG'

        #locking for thread safety
        self.threadlock = Mutex()
                      
        # checking for the right configuration
        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.logMsg("This is DTG: did not find >>gpib_address<< in \
            configuration.", 
                        msgType='error')
        
        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])
        else:
            self._gpib_timeout = 1000
            self.logMsg("This is DTG: did not find >>gpib_timeout<< in \
            configuration. I will set it to 1000 seconds.", 
                        msgType='error')
        
        if 'NumberOfChannels' in config.keys():
            self.NumberOfChannels = int(config['NumberOfChannels'])
        else:
            self.NumberOfChannels = 4
            self.logMsg("This is DTG: did not find >>NumberOfChannels<< in \
            configuration. I will set it to 4 channels.", 
                        msgType='error')
        
        # trying to load the visa connection to the module
        rm = visa.ResourceManager()
        try: 
            self._gpib_connetion = rm.open_resource(self._gpib_address, 
                                              timeout=self._gpib_timeout)
        except:
            self.logMsg("This is DTG: could not connect to the GPIB \
            address >>{}<<.".format(self._gpib_address), 
                        msgType='error')
            raise
            
        self.logMsg("DTG initialised and connected to hardware.", 
                    msgType='status')


    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        self._gpib_connetion.chunk_size = 2**20
        self._ChunkSize = 1000000
        
        self._GroupName = 'Group1[0:' + str(self.NumberOfChannels-1) + ']'  #e.g. 'Group[0:3]' for 4 Channels
        self.ChannelMap = '[?,?]'
        
    
    def deactivation(self, e):
        '''Tasks that are required to be performed during deactivation of the module.
        '''        
        #TODO: disconnect the DTG
        pass


    def run(self):
        """ Running the DTG.
        
        @return bool: status of the DTG (0: not running, 1:running)
        """
        self._gpib_connetion.write('OUTP:STAT:ALL ON')
        self._gpib_connetion.write('TBAS:RUN ON')
        return bool(self._gpib_connetion.ask('TBAS:RUN?'))


    def stop(self):
        """ Stopping the DTG.
        """
        self._gpib_connetion.write('TBAS:RUN OFF')
        
        
    def delete_all_blocks(self):
        """ Deletes all blocks from the DTG.
        """
        self._gpib_connetion.write('BLOC:DEL:ALL')
        

    def set_timebase(self, frequency = None):
        """ Sets the frequency of the DTG. 
        
        @param float power: this frequency (in Hz) is set at the device
        
        @return int: error code (0:OK, -1:error)
        """        
        self._gpib_connetion.write('TBAS:RUN OFF')
        self._gpib_connetion.write('TBAS:SOURce EXTReference') 
        
        if frequency != None:  
            self._gpib_connetion.write('TBAS:FREQ {0:f}'.format(frequency))
            return 0
        else:
            frequency = 1000000000  
            self._gpib_connetion.write('TBAS:FREQ {0:f}'.format(frequency))
            self.logMsg("DTG>setTimeBase: No frequency was given, therefore set to 1GHz.", 
                        msgType='warning')
            return -1


    def get_timebase(self):
        """ Gets the frequency of the DTG.
        
        @return float: current frequency of the DTG
        """
        return float(DTG.ask('TBAS:FREQ?'))


    def write_block(self, name, sequence):
        """Writes a block into the DTG.
        
        @param str name: Name of the sequence
        @param ? sequence: sequence data.
        """
        length = sum([ n for dummy, n in sequence ])                              ######################## ?? 
        self._gpib_connetion.write('BLOC:DEL "' + name + '"')
        self._gpib_connetion.write('BLOC:NEW "' + name + '", {0:d}'.format(length))
        offset = 0
        for channels, length in sequence:
            self._write_step_into_block(name, channels, length, offset)
            offset += length
            
            
    def _write_step_into_block(self, name, channels, length, offset):
        """mainly taken from the old pi3d code
        """
        n = int(length)
        self._gpib_connetion.write('BLOCK:SEL "' + name + '"')
        self._gpib_connetion.write('VECT:BIOF "' + self._GroupName + '"' )
        m = 0
        while m < n:
            k = min(n-m, self._ChunkSize)
            self._gpib_connetion.write('VECT:BDAT {0:d},{1:d},'.format(offset+m, k) + '#{0:d}{1:d}'.format(len(str(k)), k) + self._channels_to_binary(channels)*k)
            m += k
            
            
    def _channels_to_binary(self, channels):
        """taken from old DTG file
        """
        bits = 0
        for channel in channels:
            bits |= 1 << self.ChannelMap[channel]    #those are bitwise-operators here
        return struct.pack('B', bits)