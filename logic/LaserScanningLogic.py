# -*- coding: utf-8 -*-
"""
This file contains the QuDi couner logic class.

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

Copyright (C) 2015 Kay D. Jahnke
Copyright (C) 2015 Alexander Stark
Copyright (C) 2015 Jan M. Binder
"""

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np
import time

class LaserScanningLogic(GenericLogic):
    """This logic module gathers data from a hardware counting device.
    """

    _modclass = 'laserscanninglogic'
    _modtype = 'logic'

    def __init__(self, manager, name, config, **kwargs):
        """ Create LaserScanningLogic object with connectors.
            
          @param object manager: Manager object thath loaded this module
          @param str name: unique module name
          @param dict config: module configuration
          @param dict kwargs: optional parameters
        """
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        super().__init__(manager, name, config, state_actions, **kwargs)

        ## declare connectors
        self.connector['in']['wavemeter1'] = OrderedDict()
        self.connector['in']['wavemeter1']['class'] = 'WavemeterInterface'
        self.connector['in']['wavemeter1']['object'] = None
        
        self.connector['out']['laserscanninglogic'] = OrderedDict()
        self.connector['out']['laserscanninglogic']['class'] = 'LaserScanningLogic'
        
        self.connector['in']['savelogic'] = OrderedDict()
        self.connector['in']['savelogic']['class'] = 'SaveLogic'
        self.connector['in']['savelogic']['object'] = None
        
        self.connector['in']['counterlogic'] = OrderedDict()
        self.connector['in']['counterlogic']['class'] = 'CounterLogic'
        self.connector['in']['counterlogic']['object'] = None
        
        #locking for thread safety
        self.threadlock = Mutex()

        self.logMsg('The following configuration was found.', msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        
        self._wavemeter_timing = 10.
        self._logic_update_timing = 500.
        self._acqusition_start_time = 0
        self.bins = 200
        self.data_index = 0
        self.xmin = 600
        self.xmax = 800
        # internal min and max wavelength determined by the measured wavelength
        self.intern_xmax = -1.0
        self.intern_xmin = 1.0e10
        
                        
    def activation(self, e):
        """ Initialisation performed during activation of the module.
            
          @param object e: Fysom state change event
        """
        self.count_data = []
        self._wavelength_data = []
        
        self.stopRequested = False
        
        self._wavemeter_device = self.connector['in']['wavemeter1']['object']
#        print("Counting device is", self._counting_device)

        self._save_logic = self.connector['in']['savelogic']['object']
        self._counter_logic = self.connector['in']['counterlogic']['object']
        
        # create a new x axis from xmin to xmax with bins points
        self.histogram_axis=np.arange(self.xmin, self.xmax, (self.xmax-self.xmin)/self.bins)
        self.histogram = np.zeros(self.histogram_axis.shape)
        
    
    def save_data(self):
        """ Save the counter trace data and writes it to a file.
        
        @return int: error code (0:OK, -1:error)
        """
        self._saving=False
        self._saving_stop_time=time.time()


        filepath = self._save_logic.get_path_for_module(module_name='Counter')
        filename = time.strftime('%Y-%m-%d_laser_scan_from_%Hh%Mm%Ss.dat')
        
        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Wavelength (nm), Signal (counts/s)':self._data_to_save}        

        # write the parameters:
        parameters = OrderedDict() 
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length       
        
        self._save_logic.save_data(data, filepath, parameters=parameters, 
                                   filename=filename, as_text=True)#, as_xml=False, precision=None, delimiter=None)
                  
        self.logMsg('Laser Scan saved to:\n{0}'.format(filepath), 
                    msgType='status', importance=3)

        #print ('Want to save data of length {0:d}, please implement'.format(len(self._data_to_save)))
        
        return 0

    def start_scanning(self):
        """ Prepare to start counting:
            zero variables, change state and start counting "loop"
        """
        
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._update_data)
        
        self.run()
        
        if not self._counter_logic.getState() is 'locked':
            self._counter_logic.startCount()
        
        if self._counter_logic.get_saving_state():
            self._counter_logic.stop_saving()
            
        self._counter_logic.start_saving()
        self._acqusition_start_time = self._counter_logic._saving_start_time
        
        self._wavemeter_device.start_acqusition()
        
        self.data_index = 0
        self.rawhisto=np.zeros(self.bins)
        self.sumhisto=np.ones(self.bins)*1.0e-10
        
        # start the measuring thread
        self._timer.start(self._logic_update_timing)
        
        return 0
 
    def stop_scanning(self):
        """ Set a flag to request stopping counting.
        """
        # stop the measurement thread
        self._timer.stop()        
        
        self._wavemeter_device.stop_acqusition()
        
        if self._counter_logic.get_saving_state():
            self._counter_logic.save_data()
        
        # set status to idle again
        self.stop()
        
        return 0

    def _update_data(self):
        """ This method gets the count data from the hardware.
            It runs repeatedly in the logic module event loop by being connected
            to sigCountNext and emitting sigCountNext through a queued connection.
        """
        
        current_wavelength = self._wavemeter_device.get_current_wavelength()
        time_stamp = time.time()-self._acqusition_start_time
        
        # only wavelength >200 nm make sense, ignore the rest
        if current_wavelength>200:
            self._wavelength_data.append(np.array([time_stamp,current_wavelength]))
                
        # check if we have a new min or max and save it if so
        if current_wavelength > self.intern_xmax:
            self.intern_xmax=current_wavelength
        if current_wavelength < self.intern_xmin:
            self.intern_xmin=current_wavelength
                        
        # only do something, if there is data to work with
        if len(self._counter_logic._data_to_save)>0:     
            # only work with the new data points (indizees>data)
            for i in self._counter_logic._data_to_save[self.data_index:]:
                self.data_index += 1
                
                # calculate the bin the new wavelength needs to go in
                newbin=np.digitize([current_wavelength],self.histogram_axis)[0]
                # if the bin make no sense, start from the beginning
                if  newbin > len(self.rawhisto)-1:
                    continue
                print (self._counter_logic._data_to_save)
                # sum the counts in rawhisto and count the occurence of the bin in sumhisto
#                self.rawhisto[newbin]+=np.interp(time_stamp, 
#                                                 x=self._counter_logic._data_to_save[0][-max(100,len(self._counter_logic._data_to_save)):], 
#                                                 y=self._counter_logic._data_to_save[1][-max(100,len(self._counter_logic._data_to_save)):])
                self.sumhisto[newbin]+=1.0
                
        
        # the plot data is the summed counts divided by the occurence of the respective bins
        self.histogram=self.rawhisto/self.sumhisto
