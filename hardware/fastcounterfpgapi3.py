
from hardware.fastcounterinterface import FastCounterInterface
import numpy as np
from collections import OrderedDict
import TimeTagger as tt
from core.Base import Base
from core.util.Mutex import Mutex
from pyqtgraph.Qt import QtCore

class fastcounterfpgapi3(Base, FastCounterInterface):
    
    signal_get_data_next = QtCore.Signal()
    
    def __init__(self, manager, name, config = {}, **kwargs):
        
        Base.__init__(self, manager, name, 
                      configuation=config, callback_dict = {})
        self._modclass = 'fastcounterfpgapi3'
        self._modtype = 'mwsource'
        
        ## declare connectors        
        self.connector['out']['counter'] = OrderedDict()
        self.connector['out']['counter']['class'] = 'FastCounterInterface'
        
        if 'fpgacounter_serial' in config.keys():
            self._fpgacounter_serial=config['fpgacounter_serial']
        else:
            self.logMsg('No serial number defined for fpga counter',
                        msgType='warning')
                        
        self.fastcounter = tt
                        
        self.fastcounter._Tagger_setSerial(self.fpgacounter_serial)
        
        self._binwidth = 1
        self._record_length = 4000
        self._N_read = 1
        
        self.channel_apd_1 = int(1) 
        self.channel_apd_0 = int(-1) 
        self.channel_detect = int(2)
        self.channel_sequence = int(6) 
        
        self.threadlock = Mutex()
        
        self.stopRequested = False
        
    def configure(self,N_read,record_length,bin_width):
        
        self._N_read = N_read
        self._record_length = record_length
        self._binwidth = bin_width
        self.n_bins = int(self._record_length / self._bin_width)
        
        self.signal_get_data_next.connect(self.get_single_data_trace, QtCore.Qt.QueuedConnection)
    
        self.pulsed = self.fastcounter.Pulsed(self.n_bins, int(np.round(self._bin_width*1000)), self._N_read, self.channel_apd_0, self.channel_detect, self.channel_sequence)
        
        self.count_data = np.zeros((2,2)) 
        
    def start_measure(self):
        
        self.count_data = np.zeros((2,2)) 
        
        self.lock()
        
        self.signal_start_scanning.emit()
        
    def get_single_data_trace(self):
        
        if self.stopRequested:
            with self.threadlock:
                self.stopRequested = False
                self.unlock()
                return
        
        self.count_data = self.count_data + self.pulsed.getData()
        
        self.signal_get_data_next.emit()
        
        
    def stop_measure(self):
        
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
            
        return 0
        
    def pause_measure(self):
        
        self.stop_measure()
            
        return 0
        
    def continue_measure(self):
        
        self.lock()
        
        self.signal_get_data_next.emit()
        
    def is_gated(self):
        
        return 1
        
    def get_data_trace(self):
        
        return self.count_data
                
        