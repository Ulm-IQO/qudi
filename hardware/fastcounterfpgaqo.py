# -*- coding: utf-8 -*-


from hardware.fastcounterinterface import FastCounterInterface
from collections import OrderedDict
from core.base import Base
import numpy as np
import ok
import struct

class fastcounterfpgaqo(Base, FastCounterInterface):
    
    def __init__(self, manager, name, config = {}, **kwargs):
        
        Base.__init__(self, manager, name, 
                      configuation=config, callback_dict = {})
        self._modclass = 'fastcounterfpgaqo'
        self._modtype = 'hardware'
        
        ## declare connectors        
        self.connector['out']['counter'] = OrderedDict()
        self.connector['out']['counter']['class'] = 'FastCounterInterface'
        
        if 'fpgacounter_serial' in config.keys():
            self._fpga_serial=config['fpgacounter_serial']
        else:
            self.logMsg('No serial number defined for fpga counter',
                        msgType='warning')
                        
        self._fpga = ok.FrontPanel()
        
        self._binwidth_bins = 1
        self._gate_length_bins = 8192
        self._number_of_gates = 1
        self._histogram_size = 3000
    
        self._connect()
     
    def _connect(self):
        if not self._fpga.GetDeviceCount():
            self.logMsg('No FPGA connected to host PC', msgType='error')
            return -1
        self._fpga.OpenBySerial(self._fpga_serial)
        self._fpga.ConfigureFPGA('fastcounter_top.bit')
        if not self._fpga.IsFrontPanelEnabled():
            self.logMsg('Opal Kelly FrontPanel is not enabled in FPGA', msgType='warning')
            return -1
        else:
            self._fpga.SetWireInValue(0x00,0xC0000000)
            self._fpga.UpdateWireIns()
        return 0
 
    def configure(self, gate_length_ns, number_of_gates, bin_width_ns):
        self._binwidth_bins = int(np.rint(bin_width_ns * 950 / 1000))
        self._gate_length_bins = int(np.rint(gate_length_ns * 950 / 1000))
        self._number_of_gates = number_of_gates
        self._histogram_size =  number_of_gates * 8192
        self._fpga.SetWireInValue(0x00,0x40000000 + self._histogram_size)
        self._fpga.UpdateWireIns()
        self.count_data = np.zeros([number_of_gates, 8192])
        
    def start_measure(self):
        self.count_data = np.zeros([self._number_of_gates, 8192])
        self._fpga.SetWireInValue(0x00,self._histogram_size)
        self._fpga.UpdateWireIns()
        return
        
    def get_single_data_trace(self):
        data_buffer = bytearray(self._histogram_size*4)
        self._fpga.SetWireInValue(0x00,0x20000000 + self._histogram_size)
        self._fpga.UpdateWireIns()
        self._fpga.SetWireInValue(0x00,self._histogram_size)
        self._fpga.UpdateWireIns()
        self._fpga.ReadFromBlockPipeOut(0xA0, 1024, data_buffer)
        buffer_encode = np.array(struct.unpack("<"+"L"*self._histogram_size, data_buffer))
        if self._binwidth_bins != 1:
            buffer_encode = buffer_encode[:(buffer_encode.size // self._binwidth_bins) * self._binwidth_bins].reshape(-1, self._binwidth_bins).sum(axis=1)
            
        self.count_data = buffer_encode.reshape(-1, self._number_of_gates)
        return
        
        
    def stop_measure(self):
        self._fpga.SetWireInValue(0x00,0x40000000 + self._histogram_size)
        self._fpga.UpdateWireIns()
        return 0
        
    def pause_measure(self):
        self.stop_measure()
            
        return 0
        
    def continue_measure(self):
        self.start_measure()
        
    def is_gated(self):
        return True
        
    def get_data_trace(self):
        return self.count_data
                
        