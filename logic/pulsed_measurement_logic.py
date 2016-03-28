# -*- coding: utf-8 -*-
"""
This file contains the QuDi logic which controlls all pulsed measurements.

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

Copyright (C) 2015 Nikolas Tomek nikolas.tomek@uni-ulm.de
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
from lmfit import Parameters
import numpy as np
import time
import datetime

class PulsedMeasurementLogic(GenericLogic):
    """unstable: Nikolas Tomek
    This is the Logic class for the control of pulsed measurements.
    """
    _modclass = 'PulsedMeasurementLogic'
    _modtype = 'logic'

    ## declare connectors
    _in = {'optimizer1': 'OptimizerLogic',
           'scannerlogic': 'ConfocalLogic',
           'pulseanalysislogic': 'PulseAnalysisLogic',
           'fitlogic': 'FitLogic',
           'savelogic': 'SaveLogic',
           'fastcounter': 'FastCounterInterface',
           'microwave': 'MWInterface',
           'pulsegenerator': 'PulserInterfae',
            }
    _out = {'pulsedmeasurementlogic': 'PulsedMeasurementLogic'}

    signal_time_updated = QtCore.Signal()
    sigSinglePulsesUpdated = QtCore.Signal()
    sigPulseAnalysisUpdated = QtCore.Signal()
    sigMeasuringErrorUpdated = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions,
                              **kwargs)

        self.logMsg('The following configuration was found.', msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        # microwave parameters
        self.microwave_power = -30.     # dbm  (always in SI!)
        self.microwave_freq = 2870e6    # Hz   (always in SI!)

        # fast counter status variables
        self.fast_counter_status = None     # 0=unconfigured, 1=idle, 2=running, 3=paused, -1=error
        self.fast_counter_gated = None      # gated=True, ungated=False
        self.fast_counter_binwidth = 1e-9   # in seconds

        # parameters of the currently running sequence
        self.tau_array = np.array(range(50))
        self.number_of_lasers = 50
        self.sequence_length_s = 100e-6

        # setup parameters
        self.aom_delay_s = 0.7e-6
        self.laser_length_s = 3.e-6

        # timer for data analysis
        self.timer = None
        self.confocal_optimize_timer = None
        self.odmr_optimize_timer = None
        self.timer_interval = 5 # in seconds
        self.confocal_optimize_timer_interval= 11 # in seconds
        self.odmr_optimize_timer_interval = 0.5 # in seconds

        #timer for time
        self.start_time = 0
        self.elapsed_time = 0
        self.elapsed_time_str = '00:00:00:00'
        self.elapsed_sweeps = 0

        # analyze windows for laser pulses
        self.signal_start_bin = 5
        self.signal_width_bin = 200
        self.norm_start_bin = 5
        self.norm_width_bin = 200

        # threading
        self.threadlock = Mutex()
        self.stopRequested = False

        # plot data
        self.signal_plot_x = None
        self.signal_plot_y = None
        self.laser_plot_x = None
        self.laser_plot_y = None

        # raw data
        self.laser_data = np.zeros((10, 20))
        self.raw_data = np.zeros((10, 20))
        self.raw_laser_pulse=False

        # these parameters have to be set if specific channel activation or
        # deactivation is needed.
        self.active_analog = {}
        self.active_digital = {}


    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        # get all the connectors:
        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
        self._fast_counter_device = self.connector['in']['fastcounter']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._optimizer_logic = self.connector['in']['optimizer1']['object']
        self._confocal_logic = self.connector['in']['scannerlogic']['object']

        print("Confocal Logic is", self._confocal_logic)
        self._pulse_generator_device = self.connector['in']['pulsegenerator']['object']
        self._mycrowave_source_device = self.connector['in']['microwave']['object']

        self.fast_counter_gated = self._fast_counter_device.is_gated()
        self.update_fast_counter_status()
        self._initialize_signal_plot()
        self._initialize_laser_plot()
        self._initialize_measuring_error_plot()

        pulser_constr = self._pulse_generator_device.get_constraints()


    def deactivation(self, e):
        with self.threadlock:
            if self.getState() != 'idle' and self.getState() != 'deactivated':
                self.stop_pulsed_measurement()


    def update_fast_counter_status(self):
        """ Captures the fast counter status and update the corresponding class variables
        """

        self.fast_counter_status = self._fast_counter_device.get_status()
        return

    def configure_fast_counter(self):
        """ Configure the fast counter and updates the actually set values in
            the class variables.
        """

        if self.fast_counter_gated:
            record_length_s = self.aom_delay_s + self.laser_length_s
            number_of_gates = self.number_of_lasers
        elif not self.fast_counter_gated:
            record_length_s = self.aom_delay_s + self.sequence_length_s
            number_of_gates = 0
        actual_binwidth_s, actual_recordlength_s, actual_numofgates = self._fast_counter_device.configure(self.fast_counter_binwidth, record_length_s, number_of_gates)
        self.fast_counter_binwidth = actual_binwidth_s
        return

    def start_pulsed_measurement(self):
        """Start the analysis thread. """
        #FIXME: Describe the idea of how the measurement is intended to be run
        #       and how the used thread principle was used in this method (or
        #       will be use in another method).

        with self.threadlock:
            if self.getState() == 'idle':
                self.update_fast_counter_status()

                #self._do_confocal_optimize()
                # initialize plots
                self._initialize_signal_plot()
                self._initialize_laser_plot()


                # start microwave generator
                # self.microwave_on()

                # start fast counter
                self.fast_counter_on()
                # start pulse generator
                self.pulse_generator_on()

                # set timer
                self.timer = QtCore.QTimer()
                self.timer.setSingleShot(False)
                self.timer.setInterval(int(1000. * self.timer_interval))
                self.timer.timeout.connect(self._pulsed_analysis_loop)

                #FIXME: a proper confocal optimizer has to be implemented. But
                #       the QtCore.QTimer method is a good starting point.
                # start analysis loop and set lock to indicate a running measurement
                # self.confocal_optimize_timer = QtCore.QTimer()
                # self.confocal_optimize_timer.setSingleShot(False)
                # self.confocal_optimize_timer.setInterval(int(1000. * self.confocal_optimize_timer_interval))
                # self.confocal_optimize_timer.timeout.connect(self._do_confocal_optimize)

                #FIXME: a proper ODMR optimizer has to be implemented. But the
                #       QtCore.QTimer method is a good starting point.
                # self.odmr_optimize_timer = QtCore.QTimer()
                # self.odmr_optimize_timer.setSingleShot(False)
                # self.odmr_optimize_timer.setInterval(int(1000. * self.odmr_optimize_timer_interval))
                # self.odmr_optimize_timer.timeout.connect(self._do_odmr_optimize)


                self.lock()
                self.start_time = time.time()
                self.timer.start()
                # self.confocal_optimize_timer.start()
                # self.odmr_optimize_timer.start()
        return

    def change_fc_binning_for_pulsed_analysis(self,fc_binning):

        self.tau_array = np.array(range(self.number_of_lasers))*fc_binning
        self.signal_plot_x = self.tau_array
        self.fast_counter_binwidth=fc_binning
        self.configure_fast_counter()


        pass


    def _pulsed_analysis_loop(self):
        """ Acquires laser pulses from fast counter,
            calculates fluorescence signal and creates plots.
        """

        with self.threadlock:
            # calculate analysis windows
            sig_start = self.signal_start_bin
            sig_end = self.signal_start_bin + self.signal_width_bin
            norm_start = self.norm_start_bin
            norm_end = self.norm_start_bin + self.norm_width_bin

            # analyze pulses and get data points for signal plot

            self.signal_plot_y, \
            self.laser_data,    \
            self.raw_data,      \
            self.measuring_error,\
            self.is_gated        = self._pulse_analysis_logic._analyze_data(norm_start,
                                                                            norm_end,
                                                                            sig_start,
                                                                            sig_end,
                                                                            self.number_of_lasers)
            # set x-axis of signal plot


            # recalculate time
            self.elapsed_time = time.time() - self.start_time
            self.elapsed_time_str = ''
            self.elapsed_time_str += str(int(self.elapsed_time)//86400).zfill(2) + ':' # days
            self.elapsed_time_str += str(int(self.elapsed_time)//3600).zfill(2) + ':' # hours
            self.elapsed_time_str += str(int(self.elapsed_time)//60).zfill(2) + ':' # minutes
            self.elapsed_time_str += str(int(self.elapsed_time) % 60).zfill(2) # seconds
            # has to be changed. just for testing purposes



            # emit signals
            self.sigSinglePulsesUpdated.emit()
            self.sigPulseAnalysisUpdated.emit()
            self.sigMeasuringErrorUpdated.emit()
            self.signal_time_updated.emit()

    def get_laserpulse(self, laser_num=0):
        """ Get the laserpulse with the appropriate number.

        @param int num: number of laserpulse, to be displayed, if zero is passed
                        then the sum off all laserpulses is calculated.
        @return: tuple of 1D arrays, first one is x data, second is y data of
                                     currently selected laser.
        """

        if self.raw_laser_pulse:

            if self.is_gated:
                if laser_num > 0:
                    self.laser_plot_y = self.raw_data[laser_num-1]
                else:
                    self.laser_plot_y = np.sum(self.raw_data,0)
            else:
                self.laser_plot_y = self.raw_data

        else:
            # set laser plot
            if laser_num > 0:
                self.laser_plot_y = self.laser_data[laser_num-1]
            else:
                self.laser_plot_y = np.sum(self.laser_data,0)

        self.laser_plot_x = np.arange(1, len(self.laser_plot_y)+1)

        return self.laser_plot_x, self.laser_plot_y

    def stop_pulsed_measurement(self):
        """ Stop the measurement
          @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':

                #stopping and disconnecting all the timers
                self.timer.stop()
                self.timer.timeout.disconnect()
                self.timer = None

                #FIXME: a proper confocal optimizer has to be implemented. But
                #       the QtCore.QTimer method is a good starting point.
                # self.confocal_optimize_timer.stop()
                # self.confocal_optimize_timer.timeout.disconnect()
                # self.confocal_optimize_timer = None

                #FIXME: a proper ODMR optimizer has to be implemented. But the
                #       QtCore.QTimer method is a good starting point.
                # self.odmr_optimize_timer.stop()
                # self.odmr_optimize_timer.timeout.disconnect()
                # self.odmr_optimize_timer = None

                self.fast_counter_off()

                # self.microwave_off()

                self.pulse_generator_off()
                self.sigPulseAnalysisUpdated.emit()
                self.sigMeasuringErrorUpdated.emit()
                self.unlock()

    def pause_pulsed_measurement(self):
        """ Pauses the measurement
          @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':

                #pausing all the timers
                print (self.timer)
                print (self.confocal_optimize_timer)
                print (self.odmr_optimize_timer)
                self.timer.stop()
                self.confocal_optimize_timer.stop()
                self.odmr_optimize_timer.stop()
                print (self.timer)
                print (self.confocal_optimize_timer)
                print (self.odmr_optimize_timer)


                self.fast_counter_off()

                # self.microwave_off()

                self.pulse_generator_off()
                self.sigPulseAnalysisUpdated.emit()
                self.sigMeasuringErrorUpdated.emit()
                self.unlock()
        return 0

    def continue_pulsed_measurement(self):
        """ Continues the measurement
          @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            #if self.getState() == 'pause':
                self.update_fast_counter_status()

                #pausing all the timers
                self.timer.start()
                # self.confocal_optimize_timer.start()
                # self.odmr_optimize_timer.start()

                self.fast_counter_on()
                # self.microwave_on()
                self.pulse_generator_on()
#                self.sigPulseAnalysisUpdated.emit()
#                self.sigMeasuringErrorUpdated.emit()
                self.lock()
        return 0

    def change_timer_interval(self, interval):
        with self.threadlock:
            self.timer_interval = interval
            if self.timer != None:
                self.timer.setInterval(int(1000. * self.timer_interval))
        return

    def change_confocal_optimize_timer_interval(self, interval):
        with self.threadlock:
            self.confocal_optimize_timer_interval = interval
            if self.confocal_optimize_timer != None:
                print ('changing refocus timer')
                self.confocal_optimize_timer.setInterval(int(1000. * self.confocal_optimize_timer_interval))
            else:
                print('never mind')
        return

    def change_odmr_optimize_timer_interval(self, interval):
        with self.threadlock:
            self.odmr_optimize_timer_interval = interval
            if self.odmr_optimize_timer != None:
                self.odmr_optimize_timer.setInterval(1000. * self.odmr_optimize_timer_interval)
        return


    def manually_pull_data(self):
        if self.getState() == 'locked':
            self._pulsed_analysis_loop()

    def set_num_of_lasers(self, num_of_lasers):
        """ Set the number of laser pulses.

        @param int num_of_lasers: number of expected laser pulsed. Number must
                                  be greater then zero.

        The number of laser pulses is quite necessary to configure some fast
        counting hardware and to make the pulse extraction work properly.
        """

        if num_of_lasers < 1:
            self.logMsg('Invalid number of laser pulses set in the '
                        'pulsed_measurement_logic! A value of {0} was provided '
                        'but an interger value in the range [0,inf) is '
                        'expected! Set number_of_pulses to '
                        '1.'.format(num_of_lasers), msgType='error')
            num_of_lasers = 1

        self.number_of_lasers = num_of_lasers

    def get_num_of_lasers(self):
        """ Retrieve the set number of laser pulses.
        @return: int, number of laser pulses
        """
        return self.number_of_lasers


    def _initialize_signal_plot(self):
        '''Initializing the signal line plot.
        '''
        self.signal_plot_x = self.tau_array
        self.signal_plot_y = np.zeros(self.number_of_lasers, dtype=float)


    def _initialize_laser_plot(self):
        '''Initializing the plot of the laser timetrace.
        '''

        print (self.laser_length_s)
        number_of_bins_per_laser=int(self.laser_length_s/(self.fast_counter_binwidth))
        print('number_of_bins_per_laser',number_of_bins_per_laser)
        self.laser_plot_x = np.arange(1, number_of_bins_per_laser+1, dtype=int)
        self.laser_plot_y = np.zeros(number_of_bins_per_laser, dtype=int)

    def _initialize_measuring_error_plot(self):
        '''Initializing the plot of the laser timetrace.
        '''
        self.measuring_error_plot_x = self.tau_array
        self.measuring_error_plot_y =  np.zeros(self.number_of_lasers, dtype=float)


    def _save_data(self, tag=None, timestamp=None):
        #####################################################################
        ####                Save extracted laser pulses                  ####
        #####################################################################
        filepath = self._save_logic.get_path_for_module(module_name='PulsedMeasurement')
        if timestamp is None:
            timestamp = datetime.datetime.now()

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_laser_pulses'
        else:
            filelabel = 'laser_pulses'

        # prepare the data in a dict or in an OrderedDict:
        temp_arr = np.empty([self.laser_data.shape[1], self.laser_data.shape[0]+1])
        temp_arr[:,1:] = self.laser_data.transpose()
        temp_arr[:,0] = self.laser_plot_x
        data = OrderedDict()
        data = {'Time (ns), Signal (counts)': temp_arr}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Bin size (ns)'] = self.fast_counter_binwidth*1e9
        parameters['laser length (ns)'] = self.fast_counter_binwidth*1e9 * self.laser_plot_x.size

        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':.6f')#, as_xml=False, precision=None, delimiter=None)

        #####################################################################
        ####                Save measurement data                        ####
        #####################################################################
        if tag is not None and len(tag) > 0:
            filelabel = tag + '_pulsed_measurement'
        else:
            filelabel = 'pulsed_measurement'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Tau (ns), Signal (normalized)':np.array([self.signal_plot_x, self.signal_plot_y]).transpose()}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Bin size (ns)'] = self.fast_counter_binwidth*1e9
        parameters['Number of laser pulses'] = self.number_of_lasers
        parameters['Signal start (bin)'] = self.signal_start_bin
        parameters['Signal width (bins)'] = self.signal_width_bin
        parameters['Normalization start (bin)'] = self.norm_start_bin
        parameters['Normalization width (bins)'] = self.norm_width_bin


        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':.6f')#, as_xml=False, precision=None, delimiter=None)

        #####################################################################
        ####                Save raw data timetrace                      ####
        #####################################################################
        if tag is not None and len(tag) > 0:
            filelabel = tag + '_raw_timetrace'
        else:
            filelabel = 'raw_timetrace'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Signal (counts)': self.raw_data.transpose()}

        # write the parameters:
        parameters = OrderedDict()
        parameters['Is counter gated?'] = self.fast_counter_gated
        parameters['Bin size (ns)'] = self.fast_counter_binwidth*1e9
        parameters['Number of laser pulses'] = self.number_of_lasers
        parameters['laser length (ns)'] = self.fast_counter_binwidth*1e9 * self.laser_plot_x.size
        parameters['Tau start'] = self.tau_array[0]
        parameters['Tau increment'] = self.tau_array[1] - self.tau_array[0]


        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':')#, as_xml=False, precision=None, delimiter=None)
        return

#    def get_tau_list(self):
#        """Get the list containing all tau values in ns for the current measurement.
#
#        @return numpy array: tau_vector_ns
#        """
#        return self._tau_vector_ns
#
#
#    def get_number_of_laser_pulses(self):
#        """Get the number of laser pulses for the current measurement.
#
#        @return int: number_of_laser_pulses
#        """
#        return self._number_of_laser_pulses
#
#
#    def get_laser_length(self):
#        """Get the laser pulse length in ns for the current measurement.
#
#        @return float: laser_length_ns
#        """
#        laser_length_ns = self._laser_length_bins * self._binwidth_ns
#        return laser_length_ns
#
#
#    def get_binwidth(self):
#        """Get the binwidth of the fast counter in ns for the current measurement.
#
#        @return float: binwidth_ns
#        """
#        return self._binwidth_ns


    def pulse_generator_on(self):
        """Switching on the pulse generator.
        """

        self._pulse_generator_device.set_active_channels(self.active_analog, self.active_digital)
        self._pulse_generator_device.pulser_on()
        return 0


    def pulse_generator_off(self):
        """Switching off the pulse generator.
        """

        self._pulse_generator_device.pulser_off()
        self._pulse_generator_device.set_active_channels(self.active_analog, self.active_digital)
        # time.sleep(0.1)
        return 0


    def fast_counter_on(self):
        """Switching on the fast counter

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.start_measure()
        return error_code


    def fast_counter_off(self):
        """Switching off the fast counter

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._fast_counter_device.stop_measure()
        return error_code

    def microwave_on(self):
        # self._mycrowave_source_device.set_cw(freq=self.microwave_freq, power=self.microwave_power)
        # self._mycrowave_source_device.on()
        return

    def microwave_off(self):
        # self._mycrowave_source_device.off()
        return

    def compute_fft(self):
        # FiXME: This is the first implementation. I am sure there are better options

        # subtract baseline
        mean_y=sum(self.signal_plot_y)/len(self.signal_plot_y)
        corrected_y=self.signal_plot_y-mean_y

        #FIXME: Not sure if real or imaginary part is the better choice here
        fft_y=np.abs((np.fft.fft(corrected_y)).real)

        # Take just the positive values

        middle = round(corrected_y.shape[-1]/2)
        fft_x = np.fft.fftfreq(corrected_y.shape[-1])

        return fft_x[:middle],fft_y[:middle]


    def do_fit(self,fit_function):
        """Performs the chosen fit on the measured data.

        @param string fit_function: name of the chosen fit function
        """
        pulsed_fit_x = self.compute_x_for_fit(self.signal_plot_x[0],self.signal_plot_x[-1],1000)

        if fit_function == 'No Fit':
            pulsed_fit_x=[]
            pulsed_fit_y = []
            fit_result = 'No Fit'
            return pulsed_fit_x, pulsed_fit_y, fit_result

        elif fit_function == 'Rabi Decay':
            result = self._fit_logic.make_sine_fit(axis=self.signal_plot_x, data=self.signal_plot_y, add_parameters=None)

            ##### get the rabi fit parameters
            rabi_amp = result[0].params['amplitude'].value
            rabi_amp_error= result[0].params['amplitude'].stderr
            rabi_freq = result[0].params['omega'].value
            rabi_freq_error = result[0].params['omega'].stderr
            rabi_offset = result[0].params['offset'].value
            rabi_offset_error = result[0].params['offset'].stderr
            rabi_decay = result[0].params['decay'].value
            rabi_decay_error = result[0].params['decay'].stderr
            rabi_shift = result[0].params['shift'].value
            rabi_shift_error = result[0].params['shift'].stderr

            pulsed_fit_y = rabi_amp * np.sin(np.multiply(pulsed_fit_x,1/rabi_freq*2*np.pi)+rabi_shift)*np.exp(np.multiply(pulsed_fit_x,-rabi_decay))+rabi_offset

            fit_result = str('Contrast: ' + str(np.abs(2*rabi_amp)) + " + " + str(rabi_amp_error) + "\n" +
                             'Period [ns]: ' + str(rabi_freq) + " + " + str(rabi_freq_error) + "\n" +
                             'Offset: ' + str(rabi_offset) + " + " + str(rabi_offset_error) + "\n" +
                             'Decay [ns]: ' + str(rabi_decay) + " + " + str(rabi_decay_error) + "\n" +
                             'Shift [rad]: ' + str(rabi_shift) + " + " + str(rabi_shift_error) + "\n")

            return pulsed_fit_x, pulsed_fit_y, fit_result



        elif fit_function == 'Lorentian (neg)':
            result = self._fit_logic.make_lorentzian_fit(axis=self.signal_plot_x, data=self.signal_plot_y, add_parameters=None)
            lorentzian,params=self._fit_logic.make_lorentzian_model()
            pulsed_fit_y = lorentzian.eval(x=pulsed_fit_x, params=result.params)

            fit_result = (   'Minimum : ' + str(np.round(result.params['center'].value,3)) + u" \u00B1 "
                                + str(np.round(result.params['center'].stderr,2)) + ' [ns]' + '\n'
                                + 'linewidth : ' + str(np.round(result.params['fwhm'].value,3)) + u" \u00B1 "
                                + str(np.round(result.params['fwhm'].stderr,2)) + ' [ns]' + '\n'
                                + 'contrast : ' + str(np.round((result.params['amplitude'].value/(-1*np.pi*result.params['sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                )
            return pulsed_fit_x, pulsed_fit_y, fit_result


        elif fit_function == 'Lorentian (pos)':
            result = self._fit_logic.make_lorentzian_peak_fit(axis=self.signal_plot_x, data=self.signal_plot_y, add_parameters=None)
            lorentzian,params=self._fit_logic.make_lorentzian_model()
            pulsed_fit_y = lorentzian.eval(x=pulsed_fit_x, params=result.params)
            fit_result = (   'Maximum : ' + str(np.round(result.params['center'].value,3)) + u" \u00B1 "
                                + str(np.round(result.params['center'].stderr,2)) + ' [ns]' + '\n'
                                + 'linewidth : ' + str(np.round(result.params['fwhm'].value,3)) + u" \u00B1 "
                                + str(np.round(result.params['fwhm'].stderr,2)) + ' [ns]' + '\n'
                                + 'contrast : ' + str(np.abs(np.round((result.params['amplitude'].value/(-1*np.pi*result.params['sigma'].value*result.params['c'].value)),3))*100) + '[%]'
                                )
            return pulsed_fit_x, pulsed_fit_y, fit_result

        elif fit_function =='N14':
            result = self._fit_logic.make_N14_fit(axis=self.signal_plot_x, data=self.signal_plot_y, add_parameters=None)
            fitted_function, params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=3)
            pulsed_fit_y = fitted_function.eval(x=pulsed_fit_x, params=result.params)
            fit_result = (   'f_0 : ' + str(np.round(result.params['lorentz0_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz0_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'f_1 : ' + str(np.round(result.params['lorentz1_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz1_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'f_2 : ' + str(np.round(result.params['lorentz2_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz2_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'con_0 : ' + str(np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                + '  ,  con_1 : ' + str(np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                + '  ,  con_2 : ' + str(np.round((result.params['lorentz2_amplitude'].value/(-1*np.pi*result.params['lorentz2_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                )
            return pulsed_fit_x, pulsed_fit_y, fit_result

        elif fit_function =='N15':
            result = self._fit_logic.make_N15_fit(axis=self.signal_plot_x, data=self.signal_plot_y, add_parameters=None)
            fitted_function,params=self._fit_logic.make_multiple_lorentzian_model(no_of_lor=2)
            pulsed_fit_y = fitted_function.eval(x=pulsed_fit_x, params=result.params)
            fit_result = (   'f_0 : ' + str(np.round(result.params['lorentz0_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz0_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'f_1 : ' + str(np.round(result.params['lorentz1_center'].value,3)) + u" \u00B1 "
                                +  str(np.round(result.params['lorentz1_center'].stderr,2)) + ' [MHz]' + '\n'
                                + 'con_0 : ' + str(np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                + '  ,  con_1 : ' + str(np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
                                )
            return pulsed_fit_x, pulsed_fit_y, fit_result

        elif fit_function =='Stretched Exponential':
            fit_result = ('Stretched Exponential not yet implemented')
            return pulsed_fit_x, pulsed_fit_x, fit_result

        elif fit_function =='Exponential':
            fit_result = ('Exponential not yet implemented')
            return pulsed_fit_x, pulsed_fit_x, fit_result

        elif fit_function =='XY8':
            fit_result = ('XY8 not yet implemented')
            return pulsed_fit_x, pulsed_fit_x, fit_result


    def compute_x_for_fit(self, x_start, x_end, number_of_points):

        step = (x_end-x_start)/(number_of_points-1)

        x_for_fit = np.arange(x_start,x_end,step)

        return x_for_fit

    def _do_confocal_optimize(self):
        """ Does a refocus. """

        self.logMsg('Confocal Optimizing needs to be implemented properly with'
                    'tasks!\nNo confocal optimization performed.',
                    msgType='warning')
        # self.pause_pulsed_measurement()
        #self.getTaskRunner().startTaskByName('default-confocal-refocus')
        # self.continue_pulsed_measurement()
        pass


    def _do_odmr_optimize(self):
        """ Does a refocus. """

        self.logMsg('ODMR Optimizing needs to be implemented properly with'
                    'tasks!\nNo ODMR optimization performed.',
                    msgType='warning')
        #self.getTaskRunner().startTaskByName('default-odmr-refocus')
        pass


