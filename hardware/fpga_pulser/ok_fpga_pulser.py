# -*- coding: utf-8 -*-
"""
Use OK FPGA as a digital pulse sequence generator.

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

Copyright (C) 2015 Niko Tomek
Copyright (C) 2015 Lachlan J. Rogers lachlan.rogers@uni-ulm.de
"""

from core.base import Base
from core.util.mutex import Mutex
from hardware.pulser_interface import PulserInterface
import thirdparty.opal_kelly as ok
import time


class OkFpgaPulser(Base, PulserInterface):
    """Methods to control Pulse Generator running on OK FPGA.
    """
    _modclass = 'pulserinterface'
    _modtype = 'hardware'
    _out = {'pulser': 'PulserInterface'}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config,  c_dict)
        self.lock = Mutex()

    def activation(self, e):
        self.fp = ok.FrontPanel()

        # user configurable:
        self.ch_map = {'LASER': 0, 'MW': 1, 'microwave': 1, 'gate': 2, 'sequence': 3}
        self.pulser_channels = 4        # 8 or 4 channels
        self.pulser_frequency = 500     # 500 or 950 MHz
        self.pulse_sequence = [(['LASER'], 4000), ([], 10000), (['LASER'], 1000), ([], 1)]

        # check for specified channel number to be reasonable
        if ((self.pulser_channels != 4) and (self.pulser_channels != 8)):
            print('FPGA Pulser Error! "self.pulser_channels" must be 4 or 8.')
            return
        elif (self.pulser_channels == None):
            print('FPGA Pulser Error! Please specify "self.pulser_channels".')
            return
        # check for specified frequency to be reasonable
        if ((self.pulser_frequency != 950) and (self.pulser_frequency != 500)):
            print('FPGA Pulser Error! "self.pulser_frequency" must be 500 or 950.')
            return
        elif (self.pulser_channels == None):
            print('FPGA Pulser Error! Please specify "self.pulser_frequency".')
            return

    def deactivation(self, e):
        pass

    def connect_fpga(self):
        # connect to FPGA
        num_fpga = self.fp.GetDeviceCount()
        for dev in range(num_fpga):
            if (self.fp.GetDeviceListModel(dev) == 22):
                self.fp.OpenBySerial(self.fp.GetDeviceListSerial(dev))
                break
        
        # upload configuration bitfile to FPGA
        if (self.pulser_channels == 8):
            if (self.pulser_frequency == 950):
                self.fp.ConfigureFPGA(os.path.join(self.get_main_dir(), 'hardware', 'fpga_pulser', 'pulsegen_8chnl_950MHz.bit'))
            else:
                self.fp.ConfigureFPGA(os.path.join(self.get_main_dir(), 'hardware', 'fpga_pulser', 'pulsegen_8chnl_500MHz.bit'))
        else:
            if (self.pulser_frequency == 950):
                self.fp.ConfigureFPGA(os.path.join(self.get_main_dir(), 'hardware', 'fpga_pulser', 'pulsegen_4chnl_950MHz.bit'))
            else:
                self.fp.ConfigureFPGA(os.path.join(self.get_main_dir(), 'hardware', 'fpga_pulser', 'pulsegen_4chnl_500MHz.bit'))

        # Check connection
        if not self.fp.IsFrontPanelEnabled():
            self.logMsg('ERROR: FrontPanel is not enabled in FPGA switch!', msgType='error')
            return
        else:
            self.reset()
            self.logMsg('FPGA connected')

    def high(channels):
        """Set specified channels to high, all others to low."""
        Sequence([[channels, 1024]])

    def sequence(sequence):
        """Run sequence of instructions"""

        #determine total length of the sequence in bytes.
        #expand the sequence with zeros if needed
        totallength = 0 
        numberofzeros = 0
        for step in sequence[0:]:
            totallength = totallength + step[1]
        if (self.pulser_channels == 4):
            if ((totallength % 2) != 0):
                numberofzeros = 1
                totallength = totallength + 1
            if ((totallength % 64) != 0):
                numberofzeros = numberofzeros + 64 - (totallength % 64)
            if (numberofzeros != 0):
                sequence += [([], numberofzeros)]
                print('WARNING: Pulse sequence length is no integer multiple of 256 bit!')
                print('Number of zero-timeslots appended to sequence: ' + str(numberofzeros)) 
            totallength = (totallength + numberofzeros)//2
        else:
            if ((totallength % 32) != 0):
                numberofzeros = 32 - (totallength % 32)
                totallength = totallength + numberofzeros
                sequence += [([], numberofzeros)]
                print('WARNING: Pulse sequence length is no integer multiple of 256 bit!')
                print('Number of zero-timeslots appended to sequence: ' + str(numberofzeros)) 
        
        #repeatedly attempt to send the pulse sequence and start the pulser until it works (due to memory init problems on the OK board)
        repeat = True
        flags = 0
        worked = True
        
        # calculate size of the two bytearrays to be transmitted
        # the biggest part is tranfered in 1024 byte blocks and the rest is transfered in 32 byte blocks
        big_bytesize = (totallength // 1024) * 1024
        small_bytesize = totallength - big_bytesize
        
        seq_arr = bytearray(totallength)
        
        # entry point for sequence array 
        seq_entry = 0
        write_byte = 0
        block_bytes = bytearray() 
        MSB4bit = False
        #run through sequence    
        for step in sequence[0:]:
            channel_encode = Encodechannels(step[0])
            timeslot_cnt = step[1]
            if (self.pulser_channels == 4):
                if MSB4bit:
                    write_byte = write_byte + (channel_encode << 4)
                    block_bytes = bytearray([write_byte])
                    timeslot_cnt = timeslot_cnt - 1
                
                num_of_bytes = timeslot_cnt // 2
                write_byte = (channel_encode << 4) + channel_encode    
                block_bytes = block_bytes + bytearray([write_byte]*num_of_bytes)
                timeslot_cnt = timeslot_cnt - num_of_bytes*2
                
                seq_arr[seq_entry:seq_entry+(step[1]//2)] = block_bytes
                
                if timeslot_cnt == 0:
                    MSB4bit = False
                    write_byte = 0                    
                else:
                    MSB4bit = True
                    write_byte = channel_encode
                seq_entry = seq_entry + step[1]//2
                block_bytes = bytearray()                    
            else:
                num_of_bytes = timeslot_cnt
                write_byte = channel_encode    
                block_bytes = bytearray([write_byte]*num_of_bytes)
                timeslot_cnt = timeslot_cnt - num_of_bytes
                
                seq_arr[seq_entry:seq_entry+step[1]] = block_bytes
                
                write_byte = 0                    
                seq_entry = seq_entry + step[1]
                block_bytes = bytearray()
        
        while repeat:
            # reset FPGA        
            self.fp.SetWireInValue(0x00,0x04)
            self.fp.UpdateWireIns()
            self.fp.SetWireInValue(0x00,0x00)
            self.fp.UpdateWireIns()
            # upload sequence
            if (big_bytesize != 0):
                #enable sequence write mode in FPGA
                self.fp.SetWireInValue(0x00,(255<<24)+2)
                self.fp.UpdateWireIns()
                #write to FPGA DDR2-RAM
                self.fp.WriteToBlockPipeIn(0x80, 1024, seq_arr[0:big_bytesize])
            if (small_bytesize != 0):
                #enable sequence write mode in FPGA
                self.fp.SetWireInValue(0x00,(8<<24)+2)
                self.fp.UpdateWireIns()
                #write to FPGA DDR2-RAM
                self.fp.WriteToBlockPipeIn(0x80, 32, seq_arr[big_bytesize:big_bytesize+small_bytesize])
                
            if (worked):
                print('Pulse sequence upload: completed')
                print('Attempting to start pulser...')
        
            self.fp.SetWireInValue(0x00,0x00)
            self.fp.UpdateWireIns()    
            #start the pulse sequence
            self.fp.SetWireInValue(0x00,0x01)
            self.fp.UpdateWireIns()
            #wait for 600ms
            time.sleep(0.6)
            #get status flags from FPGA
            self.fp.UpdateWireOuts()
            flags = self.fp.GetWireOutValue(0x20)
            #check if the memory readout works.
            if flags != 0:
                worked = False
            else:
                print('DONE! Pulsing in progress.')
                repeat = False
            
    def Encodechannels(channels):
        """creates a binary word representing the state of the channels"""
        bits = 0
        for channel in channels:
            bits = bits | (1<<ch_map[channel])
        return bits
    
    def Light():
        High(['LASER','MW'])
        
    def Stop():
        High([])
        
    def Night():
        High([])
    
    def test():
        High(['LASER'])    
