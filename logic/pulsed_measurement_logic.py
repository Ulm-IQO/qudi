# -*- coding: utf-8 -*-
"""
This file contains the QuDi logic which controls all pulsed measurements.

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

Copyright (C) 2015-2016 Nikolas Tomek nikolas.tomek@uni-ulm.de
Copyright (C) 2015-2016 Alexander Stark alexander.stark@uni-ulm.de
Copyright (C) 2015-2016 Simon Schmitt simon.schmitt@uni-ulm.de
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
        self.measurement_ticks_list = np.array(range(50))
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
        self.norm_start_bin = 300
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

        self._pulse_generator_device = self.connector['in']['pulsegenerator']['object']
        self._mycrowave_source_device = self.connector['in']['microwave']['object']

        self.fast_counter_gated = self._fast_counter_device.is_gated()
        self.update_fast_counter_status()
        self._initialize_signal_plot()
        self._initialize_laser_plot()
        self._initialize_measuring_error_plot()

        if 'signal_start_bin' in self._statusVariables:
            self.signal_start_bin = self._statusVariables['signal_start_bin']
        if 'signal_width_bin' in self._statusVariables:
            self.signal_width_bin = self._statusVariables['signal_width_bin']
        if 'norm_start_bin' in self._statusVariables:
            self.norm_start_bin = self._statusVariables['norm_start_bin']
        if 'norm_width_bin' in self._statusVariables:
            self.norm_width_bin = self._statusVariables['norm_width_bin']
        if 'number_of_lasers' in self._statusVariables:
            self.number_of_lasers = self._statusVariables['number_of_lasers']
        if 'aom_delay_s' in self._statusVariables:
            self.aom_delay_s = self._statusVariables['aom_delay_s']
        if 'laser_length_s' in self._statusVariables:
            self.laser_length_s = self._statusVariables['laser_length_s']


    def deactivation(self, e):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method activation.
        """

        with self.threadlock:
            if self.getState() != 'idle' and self.getState() != 'deactivated':
                self.stop_pulsed_measurement()

        self._statusVariables['signal_start_bin'] = self.signal_start_bin
        self._statusVariables['signal_width_bin'] = self.signal_width_bin
        self._statusVariables['norm_start_bin'] = self.norm_start_bin
        self._statusVariables['norm_width_bin'] = self.norm_width_bin
        self._statusVariables['number_of_lasers'] = self.number_of_lasers
        self._statusVariables['aom_delay_s'] = self.aom_delay_s
        self._statusVariables['laser_length_s'] = self.laser_length_s

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
            number_of_gates = int(self.number_of_lasers)
        elif not self.fast_counter_gated:
            record_length_s = self.aom_delay_s + self.sequence_length_s
            number_of_gates = 0
        #Fixme: Should we use the information of the actual values?
        actual_binwidth_s, actual_recordlength_s, actual_numofgates = self._fast_counter_device.configure(self.fast_counter_binwidth , record_length_s, number_of_gates)
        #self.fast_counter_binwidth = actual_binwidth_s
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
        """ If the FC binning has be changed in the GUI, inform analysis

        @param float fc_binning: Binning of fast counter in s

        """
        self.fast_counter_binwidth=fc_binning
        self.configure_fast_counter()
        return


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

            return

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

    def get_fastcounter_constraints(self):
        """ Request the constrains from the hardware, in order to pass them
            to the GUI if necessary.

        @return: dict where the keys in it are predefined in the interface.
        """

        return self._fast_counter_device.get_constraints()


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
        """ Change the interval of the timer

        @param int interval: Interval of the timer in s

        """
        with self.threadlock:
            self.timer_interval = interval
            if self.timer != None:
                self.timer.setInterval(int(1000. * self.timer_interval))
        return

    def change_confocal_optimize_timer_interval(self, interval):
        """ Change the timer interval for confocal refocus

        @param int interval: Interval of the timer in s

        """
        with self.threadlock:
            self.confocal_optimize_timer_interval = interval
            if self.confocal_optimize_timer != None:
                print ('changing refocus timer')
                self.confocal_optimize_timer.setInterval(int(1000. * self.confocal_optimize_timer_interval))
            else:
                print('never mind')
        return

    def change_odmr_optimize_timer_interval(self, interval):
        """ Change the timer interval for odmr refocus

        @param int interval: Interval of the timer in s

        """
        with self.threadlock:
            self.odmr_optimize_timer_interval = interval
            if self.odmr_optimize_timer != None:
                self.odmr_optimize_timer.setInterval(1000. * self.odmr_optimize_timer_interval)
        return


    def manually_pull_data(self):
        """ Analyse and display the data
        """
        if self.getState() == 'locked':
            self._pulsed_analysis_loop()
        return

    def set_num_of_lasers(self, num_of_lasers):
        """ Sets the number of lasers needed for the pulse extraction and the fast counter.

        @param int num_of_lasers: Number of laser pulses
        """
        if num_of_lasers < 1:
            self.logMsg('Invalid number of laser pulses set in the '
                        'pulsed_measurement_logic! A value of {0} was provided '
                        'but an interger value in the range [0,inf) is '
                        'expected! Set number_of_pulses to '
                        '1.'.format(num_of_lasers), msgType='error')
            self.number_of_lasers = 1
        else:
            self.number_of_lasers = num_of_lasers
        return

    def get_num_of_lasers(self):
        """ Retrieve the set number of laser pulses.
        @return: int, number of laser pulses
        """
        return self.number_of_lasers

    def set_measurement_ticks_list(self, ticks_array):
        """ Sets the ticks for the x-axis of the pulsed measurement.

        Handle with care to ensure that the number of ticks is the same as the number of
        laser pulses to avoid array mismatch conflicts.

        @param ticks_array: a numpy array containing the ticks
        """
        self.measurement_ticks_list = np.array(ticks_array)
        return

    def get_measurement_ticks_list(self):
        """ Retrieve the set measurement_ticks_list, i.e. the x-axis of the measurement.
        @return: list, list of the x-axis ticks
        """
        return self.measurement_ticks_list


    def _initialize_signal_plot(self):
        '''Initializing the signal line plot.
        '''
        self.signal_plot_x = self.measurement_ticks_list
        self.signal_plot_y = np.zeros(self.measurement_ticks_list.size, dtype=float)
        return


    def _initialize_laser_plot(self):
        '''Initializing the plot of the laser timetrace.
        '''
        number_of_bins_per_laser=int(self.laser_length_s/(self.fast_counter_binwidth))
        self.laser_plot_x = np.arange(1, number_of_bins_per_laser+1, dtype=int)
        self.laser_plot_y = np.zeros(number_of_bins_per_laser, dtype=int)
        return

    def _initialize_measuring_error_plot(self):
        '''Initializing the plot of the laser timetrace.
        '''
        self.measuring_error_plot_x = self.measurement_ticks_list
        self.measuring_error_plot_y =  np.zeros(self.number_of_lasers, dtype=float)
        return


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
        parameters['Measurement Ticks start'] = self.measurement_ticks_list[0]
        parameters['Measurement Ticks increment'] = self.measurement_ticks_list[1] - self.measurement_ticks_list[0]


        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp,
                                   as_text=True, precision=':')#, as_xml=False, precision=None, delimiter=None)
        return

#    def get_measurement_ticks_list(self):
#        """Get the list containing all tau values in ns for the current measurement.
#
#        @return numpy array: tau_vector_ns
#        """
#        return self.measurement_ticks_list
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
        """Switching on the pulse generator. """

        self._pulse_generator_device.pulser_on()
        return 0


    def pulse_generator_off(self):
        """Switching off the pulse generator. """

        self._pulse_generator_device.pulser_off()
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
        """ Computing the fourier transform of the data.

        @return tuple (fft_x, fft_y):
                    fft_x: the frequencies for the FT
                    fft_y: the FT spectrum

        Pay attention that the return values of the FT have only half of the
        entries compared to the used signal input.

        In general, a window function should be applied to the time domain data
        before calculating the FT, to reduce spectral leakage. The Hann window
        for instance is almost never a bad choice. Use it like:
            y_ft = np.fft.fft(y_signal * np.hanning(len(y_signal)))

        Keep always in mind the relation for the Fourier transform:
            T = delta_t * N_samples
        where delta_t is the distance between the time points and N_samples are
        the amount of points in the time domain. Consequently the sample rate is
            f_samplerate = T / N_samples

        Keep in mind that the FT returns value from 0 to f_samplerate, or
        equivalently -f_samplerate/2 to f_samplerate/2.


        """
        # Make a baseline correction to avoid a constant offset near zero
        # frequencies:
        mean_y = sum(self.signal_plot_y) / len(self.signal_plot_y)
        corrected_y = self.signal_plot_y - mean_y

        # The absolute values contain the fourier transformed y values
        fft_y = np.abs(np.fft.fft(corrected_y))

        # Due to the sampling theorem you can only identify frequencies at half
        # of the sample rate, therefore the FT contains an almost symmetric
        # spectrum (the asymmetry results from aliasing effects). Therefore take
        # the half of the values for the display.
        middle = int((len(corrected_y)+1)//2)

        # sample spacing of x_axis, if x is a time axis than it corresponds to a
        # timestep:
        x_spacing = np.round(self.signal_plot_x[-1] - self.signal_plot_x[-2], 12)

        # use the helper function of numpy to calculate the x_values for the
        # fourier space. That function will handle an occuring devision by 0:
        fft_x = np.fft.fftfreq(len(corrected_y), d=x_spacing)

        return abs(fft_x[:middle]), fft_y[:middle]

    def get_fit_functions(self):
        """Giving the available fit functions

        @return list of strings with all available fit functions

        """
        return ['No Fit', 'Sine', 'Cos_FixedPhase', 'Lorentian (neg)' , 'Lorentian (pos)', 'N14',
                'N15', 'Stretched Exponential', 'Exponential', 'XY8']


    def do_fit(self, fit_function):
        """Performs the chosen fit on the measured data.

        @param string fit_function: name of the chosen fit function

        @return float array pulsed_fit_x: Array containing the x-values of the fit
        @return float array pulsed_fit_y: Array containing the y-values of the fit
        @return str array pulsed_fit_result: String containing the fit parameters displayed in a nice form
        """
        pulsed_fit_x = self.compute_x_for_fit(self.signal_plot_x[0], self.signal_plot_x[-1],1000)

        param_dict = OrderedDict()

        if fit_function == 'No Fit':
            pulsed_fit_x = []
            pulsed_fit_y = []
            fit_result = 'No Fit'
            return pulsed_fit_x, pulsed_fit_y, fit_result

        elif fit_function == 'Sine' or 'Cos_FixedPhase':
            update_dict = {}
            if fit_function == 'Cos_FixedPhase':
                update_dict['phase'] = {'vary': False, 'value': np.pi/2.}
                update_dict['amplitude'] = {'min': 0.0}
            result = self._fit_logic.make_sine_fit(axis=self.signal_plot_x,
                                                   data=self.signal_plot_y,
                                                   add_parameters=update_dict)
            sine, params = self._fit_logic.make_sine_model()
            pulsed_fit_y = sine.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Contrast'] = {'value': np.round(np.abs(2*result.params['amplitude'].value*100), 2),
                                      'error': np.round(2 * result.params['amplitude'].stderr*100, 2),
                                      'unit' : '%'}
            param_dict['Frequency'] = {'value': np.round(result.params['frequency'].value/1e6, 3),
                                       'error': np.round(result.params['frequency'].stderr/1e6, 3),
                                       'unit' : 'MHz'}
            # use proper error propagation formula:
            error_per = 1/(result.params['frequency'].value/1e9)**2 * result.params['frequency'].stderr/1e9
            param_dict['Period'] = {'value': np.round(1/(result.params['frequency'].value/1e9), 2),
                                    'error': np.round(error_per, 2),
                                    'unit' : 'ns'}
            param_dict['Offset'] = {'value': np.round(result.params['offset'].value, 3),
                                    'error': np.round(result.params['offset'].stderr, 2),
                                    'unit' : 'norm. signal'}
            param_dict['Phase'] = {'value': np.round(result.params['phase'].value/np.pi *180, 3),
                                   'error': np.round(result.params['phase'].stderr/np.pi *180, 2),
                                   'unit' : '°'}

            fit_result = self._create_formatted_output(param_dict)

            return pulsed_fit_x, pulsed_fit_y, fit_result

        elif fit_function == 'Lorentian (neg)':

            result = self._fit_logic.make_lorentzian_fit(axis=self.signal_plot_x,
                                                         data=self.signal_plot_y,
                                                         add_parameters=None)
            lorentzian, params = self._fit_logic.make_lorentzian_model()
            pulsed_fit_y = lorentzian.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Minimum'] = {'value': np.round(result.params['center'].value, 3),
                                     'error': np.round(result.params['center'].stderr, 2),
                                     'unit' : 'ns'}
            param_dict['Linewidth'] = {'value': np.round(result.params['fwhm'].value, 3),
                                       'error': np.round(result.params['fwhm'].stderr, 2),
                                       'unit' : 'ns'}

            cont = result.params['amplitude'].value
            cont = cont/(-1*np.pi*result.params['sigma'].value*result.params['c'].value)
            param_dict['Contrast'] = {'value': np.round(cont*100, 3),
                                      'unit' : '%'}

            fit_result = self._create_formatted_output(param_dict)

            return pulsed_fit_x, pulsed_fit_y, fit_result


        elif fit_function == 'Lorentian (pos)':

            result = self._fit_logic.make_lorentzianpeak_fit(axis=self.signal_plot_x,
                                                             data=self.signal_plot_y,
                                                             add_parameters=None)
            lorentzian, params=self._fit_logic.make_lorentzian_model()
            pulsed_fit_y = lorentzian.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Maximum'] = {'value': np.round(result.params['center'].value, 3),
                                     'error': np.round(result.params['center'].stderr, 2),
                                     'unit' : 'ns'}
            param_dict['Linewidth'] = {'value': np.round(result.params['fwhm'].value, 3),
                                       'error': np.round(result.params['fwhm'].stderr, 2),
                                       'unit' : 'ns'}

            cont = result.params['amplitude'].value
            cont = cont/(-1*np.pi*result.params['sigma'].value*result.params['c'].value)
            param_dict['Contrast'] = {'value': np.round(cont*100, 3),
                                      'unit' : '%'}

            fit_result = self._create_formatted_output(param_dict)

            # fit_result = (   'Maximum : ' + str(np.round(result.params['center'].value,3)) + u" \u00B1 "
            #                     + str(np.round(result.params['center'].stderr,2)) + ' [ns]' + '\n'
            #                     + 'linewidth : ' + str(np.round(result.params['fwhm'].value,3)) + u" \u00B1 "
            #                     + str(np.round(result.params['fwhm'].stderr,2)) + ' [ns]' + '\n'
            #                     + 'contrast : ' + str(np.abs(np.round((result.params['amplitude'].value/(-1*np.pi*result.params['sigma'].value*result.params['c'].value)),3))*100) + '[%]'
            #                     )
            return pulsed_fit_x, pulsed_fit_y, fit_result

        elif fit_function =='N14':
            result = self._fit_logic.make_N14_fit(axis=self.signal_plot_x,
                                                  data=self.signal_plot_y,
                                                  add_parameters=None)
            fitted_function, params=self._fit_logic.make_multiplelorentzian_model(no_of_lor=3)
            pulsed_fit_y = fitted_function.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Freq. 0'] = {'value': np.round(result.params['lorentz0_center'].value, 3),
                                     'error': np.round(result.params['lorentz0_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Freq. 1'] = {'value': np.round(result.params['lorentz1_center'].value, 3),
                                     'error': np.round(result.params['lorentz1_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Freq. 2'] = {'value': np.round(result.params['lorentz2_center'].value, 3),
                                     'error': np.round(result.params['lorentz2_center'].stderr, 2),
                                     'unit' : 'MHz'}

            cont0 = result.params['lorentz0_amplitude'].value
            cont0 = cont0/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)
            param_dict['Contrast 0'] = {'value': np.round(cont0*100, 3),
                                        'unit' : '%'}

            cont1 = result.params['lorentz1_amplitude'].value
            cont1 = cont1/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)
            param_dict['Contrast 1'] = {'value': np.round(cont1*100, 3),
                                        'unit' : '%'}

            cont2 = result.params['lorentz2_amplitude'].value
            cont2 = cont2/(-1*np.pi*result.params['lorentz2_sigma'].value*result.params['c'].value)
            param_dict['Contrast 2'] = {'value': np.round(cont2*100, 3),
                                        'unit' : '%'}

            fit_result = self._create_formatted_output(param_dict)

            # fit_result = (   'f_0 : ' + str(np.round(result.params['lorentz0_center'].value,3)) + u" \u00B1 "
            #                     +  str(np.round(result.params['lorentz0_center'].stderr,2)) + ' [MHz]' + '\n'
            #                     + 'f_1 : ' + str(np.round(result.params['lorentz1_center'].value,3)) + u" \u00B1 "
            #                     +  str(np.round(result.params['lorentz1_center'].stderr,2)) + ' [MHz]' + '\n'
            #                     + 'f_2 : ' + str(np.round(result.params['lorentz2_center'].value,3)) + u" \u00B1 "
            #                     +  str(np.round(result.params['lorentz2_center'].stderr,2)) + ' [MHz]' + '\n'
            #                     + 'con_0 : ' + str(np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
            #                     + '  ,  con_1 : ' + str(np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
            #                     + '  ,  con_2 : ' + str(np.round((result.params['lorentz2_amplitude'].value/(-1*np.pi*result.params['lorentz2_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
            #                     )
            return pulsed_fit_x, pulsed_fit_y, fit_result

        elif fit_function =='N15':
            result = self._fit_logic.make_N15_fit(axis=self.signal_plot_x,
                                                  data=self.signal_plot_y,
                                                  add_parameters=None)
            fitted_function,params=self._fit_logic.make_multiplelorentzian_model(no_of_lor=2)
            pulsed_fit_y = fitted_function.eval(x=pulsed_fit_x, params=result.params)

            param_dict['Freq. 0'] = {'value': np.round(result.params['lorentz0_center'].value, 3),
                                     'error': np.round(result.params['lorentz0_center'].stderr, 2),
                                     'unit' : 'MHz'}
            param_dict['Freq. 1'] = {'value': np.round(result.params['lorentz1_center'].value, 3),
                                     'error': np.round(result.params['lorentz1_center'].stderr, 2),
                                     'unit' : 'MHz'}

            cont0 = result.params['lorentz0_amplitude'].value
            cont0 = cont0/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)
            param_dict['Contrast 0'] = {'value': np.round(cont0*100, 3),
                                        'unit' : '%'}

            cont1 = result.params['lorentz1_amplitude'].value
            cont1 = cont1/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)
            param_dict['Contrast 1'] = {'value': np.round(cont1*100, 3),
                                        'unit' : '%'}

            fit_result = self._create_formatted_output(param_dict)

            # fit_result = (   'f_0 : ' + str(np.round(result.params['lorentz0_center'].value,3)) + u" \u00B1 "
            #                     +  str(np.round(result.params['lorentz0_center'].stderr,2)) + ' [MHz]' + '\n'
            #                     + 'f_1 : ' + str(np.round(result.params['lorentz1_center'].value,3)) + u" \u00B1 "
            #                     +  str(np.round(result.params['lorentz1_center'].stderr,2)) + ' [MHz]' + '\n'
            #                     + 'con_0 : ' + str(np.round((result.params['lorentz0_amplitude'].value/(-1*np.pi*result.params['lorentz0_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
            #                     + '  ,  con_1 : ' + str(np.round((result.params['lorentz1_amplitude'].value/(-1*np.pi*result.params['lorentz1_sigma'].value*result.params['c'].value)),3)*100) + '[%]'
            #                     )
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

    def compute_width_of_errorbars(self):
        """calculate optimal beam width for the error bars

        @return float beamwidth: Computed width of the errorbars
        """
        beamwidth = 1e99
        for i in range(len(self.measurement_ticks_list)-1):
            width = self.measurement_ticks_list[i+1] - self.measurement_ticks_list[i]
            width = width/3
            if width <= beamwidth:
                beamwidth = width
        return beamwidth

    def compute_x_for_fit(self, x_start, x_end, number_of_points):
        """compute the number of x-ticks for the fit

        @param float x_start: smallest vvalue for x
        @param float x_end: largest value for x
        @param float number_of_points: number of x-ticks

        @return float array x_for_fit: Array containing the x-ticks for the fit
        """
        step = (x_end-x_start)/(number_of_points-1)

        x_for_fit = np.arange(x_start,x_end,step)

        return x_for_fit

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


