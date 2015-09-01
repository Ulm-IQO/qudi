# -*- coding: utf-8 -*-
# unstable: Christoph Müller

"""
This file contains the QuDi Logic module base class.

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

Copyright (C) 2015 Christoph Müller christoph-2.mueller@uni-ulm.de
Copyright (C) 2015 Florian S. Frank florian.frank@uni-ulm.de
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
from lmfit import Parameters
import time
import datetime

class ODMRLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Logic class for ODMR.
    known issue: after running odmr device stay in cw mode, despide gui displaying off (Matze)
    """
    _modclass = 'odmrlogic'
    _modtype = 'logic'
    ## declare connectors
    _in = {'odmrcounter': 'ODMRCounterInterface',
            'fitlogic': 'FitLogic',
            'microwave1': 'mwsourceinterface',
            'savelogic': 'SaveLogic'
            }
    _out = {'odmrlogic': 'ODMRLogic'}

    signal_next_line = QtCore.Signal()
    signal_ODMR_plot_updated = QtCore.Signal()
    signal_ODMR_matrix_updated = QtCore.Signal()
    signal_ODMR_finished = QtCore.Signal()
    signal_ODMR_elapsedtime_changed = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        self.MW_trigger_source = 'EXT'
        self.MW_trigger_pol = 'POS'

        self._odmrscan_counter = 0
        self._clock_frequency = 200
        self.fit_function = 'No Fit'
        self.fit_result = ([])

        self.MW_frequency = 2870.    #in MHz
        self.MW_power = -30.         #in dBm
        self.MW_start = 2800.        #in MHz
        self.MW_stop = 2950.         #in MHz
        self.MW_step = 2.            #in MHz

        self.RunTime = 10
        self.ElapsedTime = 0
        self.current_fit_function = 'No Fit'

        #number of lines in the matrix plot
        self.NumberofLines = 50

        self.threadlock = Mutex()

        self.stopRequested = False
        
        self.safeRawData = int(0) #flag for saving raw data


    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        self._MW_device = self.connector['in']['microwave1']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._ODMR_counter = self.connector['in']['odmrcounter']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self.signal_next_line.connect(self._scan_ODMR_line, QtCore.Qt.QueuedConnection)

        # Initalize the ODMR plot and matrix image
        self._MW_frequency_list = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step)
        self.ODMR_fit_x = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step/10.)
        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()

        #setting to low power and turning off the input during activation
        self.set_frequency(frequency = self.MW_frequency)
        self.set_power(power = self.MW_power)
        self.MW_off()
        self._MW_device.trigger(source = self.MW_trigger_source, pol = self.MW_trigger_pol)


    def deactivation(self, e):
        '''Tasks that are required to be performed during deactivation of the module.
        '''
        #deconnecting from the MW-source
        pass


    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """

        self._clock_frequency = int(clock_frequency)
        #checks if scanner is still running
        if self.getState() == 'locked':
            return -1
        else:
            return 0


    def start_ODMR(self):
        '''Starting the ODMR counter.
        '''
        self.lock()
        self._ODMR_counter.set_up_odmr_clock(clock_frequency = self._clock_frequency)
        self._ODMR_counter.set_up_odmr()


    def kill_ODMR(self):
        '''Stopping the ODMR counter.
        '''
        self._ODMR_counter.close_odmr()
        self._ODMR_counter.close_odmr_clock()
        return 0


    def start_ODMR_scan(self):
        '''Starting an ODMR scan.
        '''
        self._odmrscan_counter = 0
        self._StartTime = time.time()
        self.ElapsedTime = 0
        self.signal_ODMR_elapsedtime_changed.emit()

        self._MW_frequency_list = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step)
        self.ODMR_fit_x = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step/10.)
        
        if self.safeRawData == 1:
            '''
            All that is necesarry fo saving of raw data
            '''        
            self._MW_frequency_list_length=int(self._MW_frequency_list.shape[0])  #length of req list    
            self._ODMR_line_time= self._MW_frequency_list_length /  self._clock_frequency # time for one line 
            self._ODMR_line_count= self.RunTime / self._ODMR_line_time # amout of lines done during runtime
        
            self.ODMR_raw_data = np.full((self._MW_frequency_list_length , self._ODMR_line_count),-1)#list used to store the raw data, is saved in seperate file for post prossesing initiallized with -1
            self.logMsg('Raw data saving...',msgType='status', importance=5)
            
        else:
            self.logMsg('Raw data NOT saved',msgType='status', importance=5)
            
        self.start_ODMR()

        self._MW_device.set_list(self._MW_frequency_list*1e6, self.MW_power)  #times 1e6 to have freq in Hz
        self._MW_device.list_on()

        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()

        self.signal_next_line.emit()


    def stop_ODMR_scan(self):
        """Stop the ODMR scan
        @return int: error code (0:OK, -1:error)
        """
        # self.save_ODMR_Data()
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
        return 0


    def _initialize_ODMR_plot(self):
        '''Initializing the ODMR line plot.
        '''
        self.ODMR_plot_x = self._MW_frequency_list
        self.ODMR_plot_y = np.zeros(self._MW_frequency_list.shape)
        self.ODMR_fit_y = np.zeros(self.ODMR_fit_x.shape)


    def _initialize_ODMR_matrix(self):
        '''Initializing the ODMR matrix plot.
        '''
        self.ODMR_plot_xy = np.zeros( (self.NumberofLines, len(self._MW_frequency_list)) )


    def _scan_ODMR_line(self):
        '''Scans one line in ODMR.
        (from MW_start to MW_stop in steps of MW_step)
        '''
        if self.stopRequested:
            with self.threadlock:
                self.MW_off()
                self._MW_device.set_cw(f=self.MW_frequency,power=self.MW_power)
                self.kill_ODMR()
                self.stopRequested = False
                self.unlock()
                self.signal_ODMR_plot_updated.emit()
                self.signal_ODMR_matrix_updated.emit()
                return

        self._MW_device.reset_listpos()
        new_counts = self._ODMR_counter.count_odmr(length=len(self._MW_frequency_list))


        self.ODMR_plot_y = ( self._odmrscan_counter * self.ODMR_plot_y + new_counts ) / (self._odmrscan_counter + 1)
        self.ODMR_plot_xy = np.vstack( (new_counts, self.ODMR_plot_xy[:-1, :]) )
        
        if self.safeRawData == 1:
            self.ODMR_raw_data[:,self._odmrscan_counter] = new_counts# adds the ne odmr line to the overall np.array
        
        
        self._odmrscan_counter += 1

        self.ElapsedTime = time.time() - self._StartTime
        self.signal_ODMR_elapsedtime_changed.emit()
        if self.ElapsedTime >= self.RunTime:
            self.do_fit(fit_function = self.current_fit_function)
            self.stopRequested = True
            self.signal_ODMR_finished.emit()

        self.signal_ODMR_plot_updated.emit()
        self.signal_ODMR_matrix_updated.emit()
        self.signal_next_line.emit()


    def set_power(self, power = None):
        """Forwarding the desired new power from the GUI to the MW source.

        @param float power: power set at the GUI

        @return int: error code (0:OK, -1:error)
        """
        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._MW_device.set_power(power)
            return error_code


    def get_power(self):
        """Getting the current power from the MW source.

        @return float: current power off the MW source
        """
        power = self._MW_device.get_power()
        return power


    def set_frequency(self, frequency = None):
        """Forwarding the desired new frequency from the GUI to the MW source.

        @param float frequency: frequency set at the GUI

        @return int: error code (0:OK, -1:error)
        """

        if isinstance(frequency,(int, float)):
            self.MW_frequency = frequency
        else:
            return -1

        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._MW_device.set_frequency(frequency*1e6) #times 1e6 to have freq in Hz
            return error_code


    def get_frequency(self):
        """Getting the current frequency from the MW source.

        @return float: current frequency off the MW source
        """
        frequency = self._MW_device.get_frequency()/1e6 #divided by 1e6 to get freq in MHz
        return frequency


    def MW_on(self):
        """Switching on the MW source.

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._MW_device.on()
        return error_code


    def MW_off(self):
        """Switching off the MW source.

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._MW_device.off()
        return error_code


    def do_fit(self, fit_function = None):
        '''Performs the chosen fit on the measured data.

        @param string fit_function: name of the chosen fit function
        '''
        self.fit_function = fit_function

        if self.fit_function == 'No Fit':
            self.ODMR_fit_y = np.zeros(self.ODMR_fit_x.shape)
            self.signal_ODMR_plot_updated.emit()#ist das hier nötig?

        elif self.fit_function == 'Lorentzian':
            result = self._fit_logic.make_lorentzian_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=None)
            lorentzian,params=self._fit_logic.make_lorentzian_model()
            self.ODMR_fit_y = lorentzian.eval(x=self.ODMR_fit_x, params=result.params)
            self.fit_result = (   'frequency : ' + str(np.round(result.params['center'].value,3)) + u" \u00B1 "
                                + str(np.round(result.params['center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'linewidth : ' + str(np.round(result.params['fwhm'].value,3)) + u" \u00B1 "
                                + str(np.round(result.params['fwhm'].stderr,2)) + ' [MHz]' + '\n'
                                + 'contrast : ' + str(np.round((result.params['amplitude'].value/(-1*np.pi*result.params['sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                )



        elif self.fit_function =='Double Lorentzian':
            result = self._fit_logic.make_double_lorentzian_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=None)
            double_lorentzian,params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=2)
            self.ODMR_fit_y = double_lorentzian.eval(x=self.ODMR_fit_x, params=result.params)
            self.fit_result = (   'f_0 : ' + str(np.round(result.params['lorentz0_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz0_center'].stderr,2)) + ' [MHz]'
                                + '  ,  lw_0 : ' + str(np.round(result.params['lorentz0_fwhm'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz0_fwhm'].stderr,2)) + ' [MHz]'  + '\n'
                                + 'f_1 : ' + str(np.round(result.params['lorentz1_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz1_center'].stderr,2)) + ' [MHz]'
                                + '  ,  lw_1 : ' + str(np.round(result.params['lorentz1_fwhm'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz1_fwhm'].stderr,2)) + ' [MHz]' + '\n'
                                + 'con_0 : ' + str(np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                + '  ,  con_1 : ' + str(np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                )



        elif self.fit_function =='Double Lorentzian with fixed splitting':
            p=Parameters()
#            TODO: insert this in gui config of ODMR
            splitting_from_gui_config=3.03 #in MHz

            error, lorentz0_amplitude,lorentz1_amplitude, lorentz0_center,lorentz1_center, lorentz0_sigma,lorentz1_sigma, offset = self._fit_logic.estimate_double_lorentz(self._MW_frequency_list,self.ODMR_plot_y)

            if lorentz0_center<lorentz1_center:
                p.add('lorentz1_center',expr='lorentz0_center{:+f}'.format(splitting_from_gui_config))
            else:
                splitting_from_gui_config*=-1
                p.add('lorentz1_center',expr='lorentz0_center{:+f}'.format(splitting_from_gui_config))

            result = self._fit_logic.make_double_lorentzian_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=p)
            double_lorentzian,params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=2)
            self.ODMR_fit_y = double_lorentzian.eval(x=self.ODMR_fit_x, params=result.params)
            self.fit_result = (   'f_0 : ' + str(np.round(result.params['lorentz0_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz0_center'].stderr,2)) + ' [MHz]'
                                + '  ,  lw_0 : ' + str(np.round(result.params['lorentz0_fwhm'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz0_fwhm'].stderr,2)) + ' [MHz]'  + '\n'
                                + 'f_1 : ' + str(np.round(result.params['lorentz1_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz1_center'].stderr,2)) + ' [MHz]'
                                + '  ,  lw_1 : ' + str(np.round(result.params['lorentz1_fwhm'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz1_fwhm'].stderr,2)) + ' [MHz]' + '\n'
                                + 'con_0 : ' + str(np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                + '  ,  con_1 : ' + str(np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                )

        elif self.fit_function =='N14':
            result = self._fit_logic.make_N14_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=None)
            fitted_funciton,params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=3)
            self.ODMR_fit_y = fitted_funciton.eval(x=self.ODMR_fit_x, params=result.params)
            self.fit_result = (   'f_0 : ' + str(np.round(result.params['lorentz0_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz0_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'f_1 : ' + str(np.round(result.params['lorentz1_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz1_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'f_2 : ' + str(np.round(result.params['lorentz2_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz2_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'con_0 : ' + str(np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                + '  ,  con_1 : ' + str(np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                + '  ,  con_2 : ' + str(np.round((result.params['lorentz2_amplitude'].value/(-1*np.pi*result.params['lorentz2_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                )

        elif self.fit_function =='N15':
            result = self._fit_logic.make_N15_fit(axis=self._MW_frequency_list, data=self.ODMR_plot_y, add_parameters=None)
            fitted_funciton,params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=2)
            self.ODMR_fit_y = fitted_funciton.eval(x=self.ODMR_fit_x, params=result.params)
            self.fit_result = (   'f_0 : ' + str(np.round(result.params['lorentz0_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz0_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'f_1 : ' + str(np.round(result.params['lorentz1_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz1_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'con_0 : ' + str(np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                + '  ,  con_1 : ' + str(np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                )


    def save_ODMR_Data(self):
        """ Saves the current ODMR data to a file.
        """
        filepath = self._save_logic.get_path_for_module(module_name='ODMR')
        filelabel = 'ODMR_data'
        filepath2 = self._save_logic.get_path_for_module(module_name='ODMR')
        filelabel2 = 'ODMR_data_matrix'
        filepath3 = self._save_logic.get_path_for_module(module_name='ODMR')
        filelabel3 = 'ODMR_data_raw'
        timestamp = datetime.datetime.now()

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data2=OrderedDict()
        data3=OrderedDict()
        freq_data = self.ODMR_plot_x
        count_data = self.ODMR_plot_y
        matrix_data=self.ODMR_plot_xy # the data in the matix plot 
        data['frequency values (MHz)'] = freq_data
        data['count data'] = count_data
        #data['frequency values (MHz)'] = freq_data
        data2['count data'] = matrix_data #saves the raw data used in the matrix NOT all only the size of the matrix

        parameters = OrderedDict()
        parameters['Microwave Power (dBm)'] = self.MW_power
        parameters['Runtime (s)'] = self.RunTime
        parameters['Star Frequency (MHz)'] = self.MW_start
        parameters['Stop Frequency (MHz)'] = self.MW_stop
        parameters['Step size (MHz)'] = self.MW_step
        
        if self.safeRawData == 1:        
            raw_data=self.ODMR_raw_data # array cotaining ALL messured data
            data3['count data'] = raw_data #saves the raw data, ALL of it so keep an eye on performance 
            self._save_logic.save_data(data3, filepath3, parameters=parameters,
                                   filelabel=filelabel3, timestamp=timestamp, as_text=True)
            self.logMsg('Raw data succesfully saved',msgType='status', importance=7)
            
        else:
            self.logMsg('Raw data is NOT saved',msgType='status', importance=7)
               
        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp, as_text=True)#, as_xml=False, precision=None, delimiter=None)
                                   
        self._save_logic.save_data(data2, filepath2, parameters=parameters,
                                   filelabel=filelabel2, timestamp=timestamp, as_text=True)#, as_xml=False, precision=None, delimiter=None)

        self.logMsg('ODMR data saved to:\n{0}'.format(filepath),
                    msgType='status', importance=3)
