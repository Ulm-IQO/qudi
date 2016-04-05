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
    """
    _modclass = 'odmrlogic'
    _modtype = 'logic'
    ## declare connectors
    _in = {'odmrcounter': 'ODMRCounterInterface',
           'fitlogic': 'FitLogic',
           'microwave1': 'mwsourceinterface',
           'savelogic': 'SaveLogic',
           'taskrunner': 'TaskRunner'
            }
    _out = {'odmrlogic': 'ODMRLogic'}

    signal_next_line = QtCore.Signal()
    signal_ODMR_plot_updated = QtCore.Signal()
    signal_ODMR_matrix_updated = QtCore.Signal()
    signal_ODMR_finished = QtCore.Signal()
    signal_ODMR_elapsedtime_changed = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        #number of lines in the matrix plot
        self.NumberofLines = 50
        self.threadlock = Mutex()
        self.stopRequested = False

    def activation(self, e):
        """ Initialisation performed during activation of the module. """

        self._MW_device = self.connector['in']['microwave1']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._ODMR_counter = self.connector['in']['odmrcounter']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        self._taskrunner = self.connector['in']['taskrunner']['object']

        # default parameers for NV ODMR
        self.MW_trigger_source = 'EXT'
        self.MW_trigger_pol = 'POS'

        self._odmrscan_counter = 0
        self._clock_frequency = 200
        self.fit_function = 'No Fit'
        self.fit_result = ''

        self.MW_frequency = 2870.    #in MHz
        self.MW_power = -30.         #in dBm
        self.MW_start = 2800.        #in MHz
        self.MW_stop = 2950.         #in MHz
        self.MW_step = 2.            #in MHz

        self.RunTime = 10
        self.ElapsedTime = 0
        self.current_fit_function = 'No Fit'

        self.safeRawData = False #flag for saving raw data

        # load parameters stored in app state store
        if 'MW_trigger_source' in self._statusVariables:
            self.MW_trigger_source = self._statusVariables['MW_trigger_source']
        if 'MW_trigger_pol' in self._statusVariables:
            self.MW_trigger_pol = self._statusVariables['MW_trigger_pol']
        if 'clock_frequency' in self._statusVariables:
            self._clock_frequency = self._statusVariables['clock_frequency']
        if 'MW_frequency' in self._statusVariables:
            self.MW_frequency = self._statusVariables['MW_frequency']
        if 'MW_power' in self._statusVariables:
            self.MW_power = self._statusVariables['MW_power']
        if 'MW_start' in self._statusVariables:
            self.MW_start = self._statusVariables['MW_start']
        if 'MW_stop' in self._statusVariables:
            self.MW_stop = self._statusVariables['MW_stop']
        if 'MW_step' in self._statusVariables:
            self.MW_step = self._statusVariables['MW_step']
        if 'RunTime' in self._statusVariables:
            self.RunTime = self._statusVariables['RunTime']
        if 'safeRawData' in self._statusVariables:
            self.safeRawData = self._statusVariables['safeRawData']

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
        self._MW_device.set_ex_trigger(source = self.MW_trigger_source, pol = self.MW_trigger_pol)

    def deactivation(self, e):
        """ Perform required deactivation. """
        # save parameters stored in app state store
        self._statusVariables['MW_trigger_source'] = self.MW_trigger_source
        self._statusVariables['MW_trigger_pol'] = self.MW_trigger_pol
        self._statusVariables['clock_frequency'] = self._clock_frequency
        self._statusVariables['MW_frequency'] = self.MW_frequency
        self._statusVariables['MW_power'] = self.MW_power
        self._statusVariables['MW_start'] = self.MW_start
        self._statusVariables['MW_stop'] = self.MW_stop
        self._statusVariables['MW_step'] = self.MW_step
        self._statusVariables['RunTime'] = self.RunTime
        self._statusVariables['safeRawData'] = self.safeRawData
        #self._statusVariables['ODMR_plot_x'] = self.ODMR_plot_x
        #self._statusVariables['ODMR_plot_y'] = self.ODMR_plot_y
        #self._statusVariables['ODMR_plot_xy'] = self.ODMR_plot_xy
        #self._statusVariables['ODMR_fit_x'] = self.ODMR_fit_x
        #self._statusVariables['ODMR_fit_y'] = self.ODMR_fit_y
        #self._statusVariables['current_fit_function'] = self.current_fit_function
        #self._statusVariables['fit_results'] = self.fit_results

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
        """ Starting the ODMR counter. """
        self.lock()
        self._ODMR_counter.set_up_odmr_clock(clock_frequency = self._clock_frequency)
        self._ODMR_counter.set_up_odmr()

    def kill_ODMR(self):
        """ Stopping the ODMR counter. """

        self._ODMR_counter.close_odmr()
        self._ODMR_counter.close_odmr_clock()
        return 0

    def start_ODMR_scan(self):
        """ Starting an ODMR scan. """
        self._odmrscan_counter = 0
        self._StartTime = time.time()
        self.ElapsedTime = 0
        self.signal_ODMR_elapsedtime_changed.emit()

        self._MW_frequency_list = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step)
        self.ODMR_fit_x = np.arange(self.MW_start, self.MW_stop+self.MW_step, self.MW_step/10.)

        if self.safeRawData:

            # All that is necesarry fo saving of raw data:

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

        # sleep to wait for learn/list mode
        #time.sleep(5.0)

        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()

        self.signal_next_line.emit()


    def stop_ODMR_scan(self):
        """ Stop the ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        # self.save_ODMR_Data()
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
        return 0


    def _initialize_ODMR_plot(self):
        """ Initializing the ODMR line plot. """
        self.ODMR_plot_x = self._MW_frequency_list
        self.ODMR_plot_y = np.zeros(self._MW_frequency_list.shape)
        self.ODMR_fit_y = np.zeros(self.ODMR_fit_x.shape)


    def _initialize_ODMR_matrix(self):
        """ Initializing the ODMR matrix plot. """
        self.ODMR_plot_xy = np.zeros( (self.NumberofLines, len(self._MW_frequency_list)) )


    def _scan_ODMR_line(self):
        """ Scans one line in ODMR

        (from MW_start to MW_stop in steps of MW_step)
        """
        if self.stopRequested:
            with self.threadlock:
                self._MW_device.set_cw(freq=self.MW_frequency, power=self.MW_power)
                self.MW_off()
                self.kill_ODMR()
                self.stopRequested = False
                self.unlock()
                self.signal_ODMR_plot_updated.emit()
                self.signal_ODMR_matrix_updated.emit()
                return

        # reset position so every line starts from the same frequency
        self._MW_device.reset_listpos()

        new_counts = self._ODMR_counter.count_odmr(length=len(self._MW_frequency_list))

        # ######################## this is a quick and dirty fix due to a missing trigger;
        # index = self._odmrscan_counter % len(new_counts)
        # #print(index)
        # if index != 0:
        #     new_counts=np.hstack((new_counts[len(new_counts)-index:],new_counts[:-index]))
        # ######################## end of quick and dirty fix

        self.ODMR_plot_y = ( self._odmrscan_counter * self.ODMR_plot_y + new_counts ) / (self._odmrscan_counter + 1)
        self.ODMR_plot_xy = np.vstack( (new_counts, self.ODMR_plot_xy[:-1, :]) )

        if self.safeRawData:
            self.ODMR_raw_data[:,self._odmrscan_counter] = new_counts  # adds the ne odmr line to the overall np.array

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
        """ Forwarding the desired new power from the GUI to the MW source.

        @param float power: power set at the GUI

        @return int: error code (0:OK, -1:error)
        """
        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._MW_device.set_power(power)
            return error_code

    def get_power(self):
        """ Getting the current power from the MW source.

        @return float: current power off the MW source
        """
        power = self._MW_device.get_power()
        return power

    def set_frequency(self, frequency = None):
        """ Forwarding the desired new frequency from the GUI to the MW source.

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
        """ Getting the current frequency from the MW source.

        @return float: current frequency off the MW source
        """
        frequency = self._MW_device.get_frequency()/1e6 #divided by 1e6 to get freq in MHz
        return frequency

    def MW_on(self):
        """ Switching on the MW source.

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._MW_device.on()
        return error_code

    def MW_off(self):
        """ Switching off the MW source.

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._MW_device.off()
        return error_code

    def do_fit(self, fit_function=None):
        """Performs the chosen fit on the measured data.

        @param string fit_function: name of the chosen fit function
        """
        self.fit_function = fit_function

        # You have to know during implementation, how many parameters you are
        # expecting. That can of course be retrieved from the model of the fit
        # like:
        #   model, params = self._fit_logic.make_lorentzian_model()

        # specify here, locally for the ODMR module, which parameters you assign
        # to which values (again you have to know how the parameters are called
        # in the fit logic, the fitlogic does not have to find that out. That is
        # the concept of our logic structure, i.e. the lowest one is the
        # 'dumbest' but the most general one)

        # this dict will be passed to the formatting method
        param_dict = OrderedDict()

        if self.fit_function == 'No Fit':
            self.ODMR_fit_y = np.zeros(self.ODMR_fit_x.shape)
            self.signal_ODMR_plot_updated.emit()  #ist das hier nötig?
        elif self.fit_function == 'Lorentzian':

            result = self._fit_logic.make_lorentzian_fit(axis=self._MW_frequency_list,
                                                         data=self.ODMR_plot_y,
                                                         add_parameters=None)
            lorentzian, params = self._fit_logic.make_lorentzian_model()
            self.ODMR_fit_y = lorentzian.eval(x=self.ODMR_fit_x, params=result.params)

            # create the proper param_dict with the values:
            param_dict['Frequency'] = {'value': np.round(result.params['center'].value, 3),
                                       'error': np.round(result.params['center'].stderr, 2),
                                       'unit' : 'MHz'}
            param_dict['Linewidth'] = {'value': np.round(result.params['fwhm'].value, 3),
                                       'error': np.round(result.params['fwhm'].stderr, 2),
                                       'unit' : 'MHz'}
            param_dict['Contrast'] = {'value': np.round((result.params['amplitude'].value/(-1*np.pi*result.params['sigma'].value*result.params['c'].value)), 3)*100,
                                      'unit' : '%'}

            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function =='Double Lorentzian':
            result = self._fit_logic.make_doublelorentzian_fit(axis=self._MW_frequency_list,
                                                               data=self.ODMR_plot_y,
                                                               add_parameters=None)
            double_lorentzian, params=self._fit_logic.make_multiplelorentzian_model(no_of_lor=2)
            self.ODMR_fit_y = double_lorentzian.eval(x=self.ODMR_fit_x, params=result.params)

            # create the proper param_dict with the values:
            param_dict['Freq. 0'] = {'value': np.round(result.params['lorentz0_center'].value, 3),
                                     'error': np.round(result.params['lorentz0_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Linewidth 0'] = {'value': np.round(result.params['lorentz0_fwhm'].value, 3),
                                         'error': np.round(result.params['lorentz0_fwhm'].stderr, 2),
                                         'unit' : 'MHz'}
            param_dict['Contrast 0'] = {'value': np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100,
                                        'unit' : '%'}
            param_dict['Freq. 1'] = {'value': np.round(result.params['lorentz1_center'].value, 3),
                                     'error': np.round(result.params['lorentz1_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Linewidth 1'] = {'value': np.round(result.params['lorentz1_fwhm'].value, 3),
                                         'error': np.round(result.params['lorentz1_fwhm'].stderr, 2),
                                         'unit' : 'MHz'}
            param_dict['Contrast 1'] = {'value': np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100,
                                        'unit' : '%'}

            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function =='Double Lorentzian with fixed splitting':
            p = Parameters()

            #TODO: insert this in gui config of ODMR
            splitting_from_gui_config = 3.03 #in MHz

            error,              \
            lorentz0_amplitude, \
            lorentz1_amplitude, \
            lorentz0_center,    \
            lorentz1_center,    \
            lorentz0_sigma,     \
            lorentz1_sigma,     \
            offset              = self._fit_logic.estimate_doublelorentz(self._MW_frequency_list,
                                                                         self.ODMR_plot_y)

            if lorentz0_center < lorentz1_center:
                p.add('lorentz1_center', expr='lorentz0_center{:+f}'.format(splitting_from_gui_config))
            else:
                splitting_from_gui_config *= -1
                p.add('lorentz1_center', expr='lorentz0_center{:+f}'.format(splitting_from_gui_config))

            result = self._fit_logic.make_doublelorentzian_fit(axis=self._MW_frequency_list,
                                                               data=self.ODMR_plot_y,
                                                               add_parameters=p)
            double_lorentzian, params=self._fit_logic.make_multiplelorentzian_model(no_of_lor=2)
            self.ODMR_fit_y = double_lorentzian.eval(x=self.ODMR_fit_x, params=result.params)

            # create the proper param_dict with the values:
            param_dict['Freq. 0'] = {'value': np.round(result.params['lorentz0_center'].value, 3),
                                     'error': np.round(result.params['lorentz0_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Freq. 1'] = {'value': np.round(result.params['lorentz1_center'].value, 3),
                                     'error': np.round(result.params['lorentz1_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Linewidth 0'] = {'value': np.round(result.params['lorentz0_fwhm'].value, 3),
                                         'error': np.round(result.params['lorentz0_fwhm'].stderr, 2),
                                         'unit' : 'MHz'}
            param_dict['Linewidth 1'] = {'value': np.round(result.params['lorentz1_fwhm'].value, 3),
                                         'error': np.round(result.params['lorentz1_fwhm'].stderr, 2),
                                         'unit' : 'MHz'}
            param_dict['Contrast 0'] = {'value': np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100,
                                        'unit' : '%'}
            param_dict['Contrast 1'] = {'value': np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100,
                                        'unit' : '%'}

            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function =='N14':
            result = self._fit_logic.make_N14_fit(axis=self._MW_frequency_list,
                                                  data=self.ODMR_plot_y,
                                                  add_parameters=None)
            fitted_funciton, params = self._fit_logic.make_multiplelorentzian_model(no_of_lor=3)
            self.ODMR_fit_y = fitted_funciton.eval(x=self.ODMR_fit_x,
                                                   params=result.params)

            # create the proper param_dict with the values:
            param_dict['Freq. 0'] = {'value': np.round(result.params['lorentz0_center'].value, 3),
                                     'error': np.round(result.params['lorentz0_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Freq. 1'] = {'value': np.round(result.params['lorentz1_center'].value, 3),
                                     'error': np.round(result.params['lorentz1_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Freq. 2'] = {'value': np.round(result.params['lorentz2_center'].value, 3),
                                     'error': np.round(result.params['lorentz2_center'].stderr, 2),
                                     'unit' : 'MHz'}

            param_dict['Contrast 0'] = {'value': np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)), 3)*100,
                                        'unit' : '%'}
            param_dict['Contrast 1'] = {'value': np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)), 3)*100,
                                        'unit' : '%'}
            param_dict['Contrast 2'] = {'value': np.round((result.params['lorentz2_amplitude'].value/(-1*np.pi*result.params['lorentz2_sigma'].value*result.params['c'].value)), 3)*100,
                                        'unit' : '%'}

            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function == 'N15':
            result = self._fit_logic.make_N15_fit(axis=self._MW_frequency_list,
                                                  data=self.ODMR_plot_y,
                                                  add_parameters=None)
            fitted_funciton, params = self._fit_logic.make_multiplelorentzian_model(no_of_lor=2)
            self.ODMR_fit_y = fitted_funciton.eval(x=self.ODMR_fit_x,
                                                   params=result.params)

            # create the proper param_dict with the values:
            param_dict['Freq. 0'] = {'value': np.round(result.params['lorentz0_center'].value, 3),
                                     'error': np.round(result.params['lorentz0_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Freq. 1'] = {'value': np.round(result.params['lorentz1_center'].value, 3),
                                     'error': np.round(result.params['lorentz1_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Contrast 0'] = {'value': np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)), 3)*100,
                                        'unit' : '%'}
            param_dict['Contrast 1'] = {'value': np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)), 3)*100,
                                        'unit' : '%'}

            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function == 'Double Gaussian':
            result = self._fit_logic.make_doublegaussian_fit(axis=self._MW_frequency_list,
                                                             data=self.ODMR_plot_y,
                                                             add_parameters=None, estimator='odmr_dip')
            double_gaussian, params=self._fit_logic.make_multiplegaussian_model(no_of_gauss=2)
            self.ODMR_fit_y = double_gaussian.eval(x=self.ODMR_fit_x,
                                                   params=result.params)

            # create the proper param_dict with the values:
            param_dict['Freq. 0'] = {'value': np.round(result.params['gaussian0_center'].value, 3),
                                     'error': np.round(result.params['gaussian0_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Freq. 1'] = {'value': np.round(result.params['gaussian1_center'].value, 3),
                                     'error': np.round(result.params['gaussian1_center'].stderr, 2),
                                     'unit' : 'MHz'}


            param_dict['Linewidth 0'] = {'value': np.round(result.params['gaussian0_fwhm'].value, 3),
                                         'error': np.round(result.params['gaussian0_fwhm'].stderr, 2),
                                         'unit' : 'MHz'}
            param_dict['Linewidth 1'] = {'value': np.round(result.params['gaussian1_fwhm'].value, 3),
                                         'error': np.round(result.params['gaussian1_fwhm'].stderr, 2),
                                         'unit' : 'MHz'}
            param_dict['Contrast 0'] = {'value': np.round((result.params['gaussian0_amplitude'].value/(-1*np.pi*result.params['gaussian0_sigma'].value*result.params['c'].value)),3)*100,
                                        'unit' : '%'}
            param_dict['Contrast 1'] = {'value': np.round((result.params['gaussian1_amplitude'].value/(-1*np.pi*result.params['gaussian1_sigma'].value*result.params['c'].value)),3)*100,
                                        'unit' : '%'}

            self.fit_result = self._create_formatted_output(param_dict)
        else:
            self.logMsg('The Fit Function "{0}" is not implemented to be used in '
                        'the ODMR Logic. Correct that! Fit Call will be '
                        'skipped.'.format(fit_function), msgType='warning')


    def _create_formatted_output(self, param_dict):
        """ Display a parameter set nicely.

        @param dict param: with two needed keywords 'value' and 'unit' and one
                           optional keyword 'error'. Add the proper items to the
                           specified keywords.

        @return str: a sting list, which is nicely formatted.
        """
        output_str = ''
        for entry in param_dict:
            if param_dict[entry].get('error') is None:
                output_str += '{0} : {1} {2} \n'.format(entry,
                                                        param_dict[entry]['value'],
                                                        param_dict[entry]['unit'])
            else:
                output_str += '{0} : {1} \u00B1 {2} {3} \n'.format(entry,
                                                                   param_dict[entry]['value'],
                                                                   param_dict[entry]['error'],
                                                                   param_dict[entry]['unit'])
        return output_str

    def save_ODMR_Data(self, tag=None, timestamp=None):
        """ Saves the current ODMR data to a file. """

        # three paths to save the raw data (if desired), the odmr scan data and
        # the matrix data.
        filepath = self._save_logic.get_path_for_module(module_name='ODMR')
        filepath2 = self._save_logic.get_path_for_module(module_name='ODMR')
        filepath3 = self._save_logic.get_path_for_module(module_name='ODMR')

        if timestamp is None:
            timestamp = datetime.datetime.now()

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_ODMR_data'
            filelabel2 = tag + '_ODMR_data_matrix'
            filelabel3 = tag + '_ODMR_data_raw'
        else:
            filelabel = 'ODMR_data'
            filelabel2 = 'ODMR_data_matrix'
            filelabel3 = 'ODMR_data_raw'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data2 = OrderedDict()
        data3 = OrderedDict()
        freq_data = self.ODMR_plot_x
        count_data = self.ODMR_plot_y
        matrix_data = self.ODMR_plot_xy  # the data in the matrix plot
        data['frequency values (MHz)'] = freq_data
        data['count data'] = count_data
        data2['count data'] = matrix_data  #saves the raw data used in the matrix NOT all only the size of the matrix

        parameters = OrderedDict()
        parameters['Microwave Power (dBm)'] = self.MW_power
        parameters['Runtime (s)'] = self.RunTime
        parameters['Start Frequency (MHz)'] = self.MW_start
        parameters['Stop Frequency (MHz)'] = self.MW_stop
        parameters['Step size (MHz)'] = self.MW_step
        parameters['Clock Frequency (Hz)'] = self._clock_frequency
        parameters['Number of matrix lines (#)'] = self.NumberofLines
        parameters['Fit function'] = self.current_fit_function

        i = 0
        for line in self.fit_result.splitlines():
            parameters['Fit result {}'.format(i)] = line
            i += 1

        if self.safeRawData:
            raw_data = self.ODMR_raw_data  # array cotaining ALL messured data
            data3['count data'] = raw_data  #saves the raw data, ALL of it so keep an eye on performance
            self._save_logic.save_data(
                data3,
                filepath3,
                parameters=parameters,
                filelabel=filelabel3,
                timestamp=timestamp,
                as_text=True)

            self.logMsg('Raw data succesfully saved', msgType='status', importance=7)
        else:
            self.logMsg('Raw data is NOT saved', msgType='status', importance=7)

        self._save_logic.save_data(
            data,
            filepath,
            parameters=parameters,
            filelabel=filelabel,
            timestamp=timestamp,
            as_text=True)

        self._save_logic.save_data(
            data2,
            filepath2,
            parameters=parameters,
            filelabel=filelabel2,
            timestamp=timestamp,
            as_text=True)

        self.logMsg('ODMR data saved to:\n{0}'.format(filepath), msgType='status', importance=3)
