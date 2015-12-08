# -*- coding: utf-8 -*-
"""
A hardware module for acessing the Measurement Systems TSYS01 temperature
sensor chip via SPI.

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

Copyright (C) 2015 Jan M. Binder <jan.binder@uni-ulm.de>
"""

from hardware.fast_counter_interface import FastCounterInterface
import numpy as np
from collections import OrderedDict
import thirdparty.stuttgart_counter.TimeTagger as tt
from core.base import Base
from core.util.mutex import Mutex
from pyqtgraph.Qt import QtCore

class FastCounterFPGAPi3(Base, FastCounterInterface):
    _modclass = 'fastcounterfpgapi3'
    _modtype = 'hardware'

    ## declare connectors
    _out = {'counter': 'FastCounterInterface'}
    
    signal_get_data_next = QtCore.Signal()
    
    def __init__(self, manager, name, config = {}, **kwargs):
        callback_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, callback_dict)

    def activation(self, e):
        config = self.getConfiguration()
        if 'fpgacounter_serial' in config.keys():
            self._fpgacounter_serial=config['fpgacounter_serial']
        else:
            self.logMsg('No serial number defined for fpga counter', msgType='warning')
                        
        tt._Tagger_setSerial(self._fpgacounter_serial)
        
        self._binwidth = 1
        self._record_length = 4000
        self._N_read = 1
        
        self.channel_apd_1 = int(1) 
        self.channel_apd_0 = int(1) 
        self.channel_detect = int(2)
        self.channel_sequence = int(6) 
        self.configure()
        
    def deactivation(self, e):
        pass

    def configure(self, N_read, record_length, bin_width):
        
        self._N_read = N_read
        self._record_length = record_length
        self._binwidth = bin_width
        self.n_bins = int(self._record_length / self._bin_width)
        
        self.pulsed = tt.Pulsed(
            self.n_bins,
            int(np.round(self._bin_width*1000)),
            self._N_read,
            self.channel_apd_0,
            self.channel_detect,
            self.channel_sequence
        )
        
    def start_measure(self):
        self.lock()
        self.pulsed.start()
        return 0
        
    def stop_measure(self):
        self.pulsed.stop()
        self.unlock()
        return 0
        
    def pause_measure(self):
        self.stop_measure()
        return 0
        
    def continue_measure(self):
        self.start_measure()
        return 0
        
    def is_gated(self):
        return True
        
    def get_data_trace(self):
        return self.pulsed.getData() 
                
