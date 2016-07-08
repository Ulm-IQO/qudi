# -*- coding: utf-8 -*-

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
from lmfit import Parameters
import time
import datetime
import matplotlib.pyplot as plt


class ODMRLogic(GenericLogic):

    """This is the Logic class for ODMR."""
    _modclass = 'odmrlogic'
    _modtype = 'logic'
    # declare connectors
    _in = {'odmrcounter': 'ODMRCounterInterface',
           'fitlogic': 'FitLogic',
           'microwave1': 'mwsourceinterface',
           'savelogic': 'SaveLogic',
           'taskrunner': 'TaskRunner'
           }
    _out = {'odmrlogic': 'ODMRLogic'}

    sigNextLine = QtCore.Signal()
    sigOdmrPlotUpdated = QtCore.Signal()
    sigOdmrMatrixUpdated = QtCore.Signal()
    sigOdmrFinished = QtCore.Signal()
    sigOdmrElapsedTimeChanged = QtCore.Signal()
    sigODMRMatrixAxesChanged = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key, config[key]),
                        msgType='status')

        # number of lines in the matrix plot
        self.number_of_lines = 50
        self.threadlock = Mutex()
        self.stopRequested = False
        self._clear_odmr_plots = False

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

        self._mw_device = self.connector['in']['microwave1']['object']
        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._odmr_counter = self.connector['in']['odmrcounter']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        self._taskrunner = self.connector['in']['taskrunner']['object']

        config = self.getConfiguration()
        if 'scanmode' in config and ('sweep' in config['scanmode'] or 'SWEEP' in config['scanmode']):
            self.scanmode = 'SWEEP'
        else:
            self.scanmode = 'LIST'

        # FIXME: that is not a general default parameter!!!
        # default parameters for NV ODMR
        self.MW_trigger_source = 'EXT'
        self.MW_trigger_pol = 'POS'

        self._odmrscan_counter = 0
        self._clock_frequency = 200     # in Hz
        self.fit_function = 'No Fit'
        self.fit_result = ''
        self.fit_models = OrderedDict([
            ('Lorentzian', self._fit_logic.make_lorentzian_model()),
            ('Double Lorentzian', self._fit_logic.make_multiplelorentzian_model(no_of_lor=2)),
            ('Double Lorentzian with fixed splitting', self._fit_logic.make_multiplelorentzian_model(no_of_lor=2)),
            ('N14', self._fit_logic.make_multiplelorentzian_model(no_of_lor=3)),
            ('N15', self._fit_logic.make_multiplelorentzian_model(no_of_lor=2)),
            ('Double Gaussian', self._fit_logic.make_multiplegaussian_model(no_of_gauss=2))
        ])
        self.use_custom_params = {
            'Lorentzian': False,
            'Double Lorentzian': False,
            'Double Lorentzian with fixed splitting': False,
            'N14': False,
            'N15': False,
            'Double Gaussian': False
        }
        # set the prefix, which determines the representation in the viewboxes
        # for the frequencies,  one can choose from the dict obtainable from
        # self.get_unit_prefix_dict(). That is mainly used to save the fitted
        # values with the appropriated magnitude.
        self._freq_prefix = 'M'

        self.mw_frequency = 2870e6  # in Hz
        self.mw_power = -30.        # in dBm
        self.mw_start = 2800e6      # in Hz
        self.mw_stop = 2950e6       # in Hz
        self.mw_step = 2e6          # in Hz

        self.run_time = 10          # in s
        self.elapsed_time = 0       # in s
        self.current_fit_function = 'No Fit'

        self.safeRawData = False  # flag for saving raw data

        # load parameters stored in app state store
        if 'clock_frequency' in self._statusVariables:
            self._clock_frequency = self._statusVariables['clock_frequency']
        if 'mw_frequency' in self._statusVariables:
            self.mw_frequency = self._statusVariables['mw_frequency']
        if 'mw_power' in self._statusVariables:
            self.mw_power = self._statusVariables['mw_power']
        if 'mw_start' in self._statusVariables:
            self.mw_start = self._statusVariables['mw_start']
        if 'mw_stop' in self._statusVariables:
            self.mw_stop = self._statusVariables['mw_stop']
        if 'mw_step' in self._statusVariables:
            self.mw_step = self._statusVariables['mw_step']
        if 'run_time' in self._statusVariables:
            self.run_time = self._statusVariables['run_time']
        if 'safeRawData' in self._statusVariables:
            self.safeRawData = self._statusVariables['safeRawData']

        self.sigNextLine.connect(self._scan_ODMR_line, QtCore.Qt.QueuedConnection)

        # Initalize the ODMR plot and matrix image
        self._mw_frequency_list = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step)
        self.ODMR_fit_x = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step / 10.)
        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()

        # setting to low power and turning off the input during activation
        self.set_frequency(frequency=self.mw_frequency)
        self.set_power(power=self.mw_power)
        self.MW_off()
        self._mw_device.set_ex_trigger(source=self.MW_trigger_source, pol=self.MW_trigger_pol)

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        # save parameters stored in app state store
        self._statusVariables['clock_frequency'] = self._clock_frequency
        self._statusVariables['mw_frequency'] = self.mw_frequency
        self._statusVariables['mw_power'] = self.mw_power
        self._statusVariables['mw_start'] = self.mw_start
        self._statusVariables['mw_stop'] = self.mw_stop
        self._statusVariables['mw_step'] = self.mw_step
        self._statusVariables['run_time'] = self.run_time
        self._statusVariables['safeRawData'] = self.safeRawData

    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = int(clock_frequency)
        # checks if scanner is still running
        if self.getState() == 'locked':
            return -1
        else:
            return 0

    def start_odmr(self):
        """ Starting the ODMR counter. """
        self.lock()
        self._odmr_counter.set_up_odmr_clock(clock_frequency=self._clock_frequency)
        self._odmr_counter.set_up_odmr()

    def kill_odmr(self):
        """ Stopping the ODMR counter. """
        self._odmr_counter.close_odmr()
        self._odmr_counter.close_odmr_clock()
        return 0

    def start_odmr_scan(self):
        """ Starting an ODMR scan. """
        self._clear_odmr_plots = False
        self._odmrscan_counter = 0
        self._StartTime = time.time()
        self.elapsed_time = 0
        self.sigOdmrElapsedTimeChanged.emit()

        self._mw_frequency_list = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step)
        self.ODMR_fit_x = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step / 10.)

        if self.safeRawData:
            # All that is necesarry fo saving of raw data:
            # length of req list
            self._mw_frequency_list_length = int(self._mw_frequency_list.shape[0])
            # time for one line
            self._ODMR_line_time = self._mw_frequency_list_length / self._clock_frequency
            # amout of lines done during run_time
            self._ODMR_line_count = self.run_time / self._ODMR_line_time
            # list used to store the raw data, is saved in seperate file for post prossesing initiallized with -1
            self.ODMR_raw_data = np.full((self._mw_frequency_list_length, self._ODMR_line_count), -1)
            self.logMsg('Raw data saving...', msgType='status', importance=5)
        else:
            self.logMsg('Raw data NOT saved', msgType='status', importance=5)

        self.start_odmr()
        if self.scanmode == 'SWEEP':
            n = self._mw_device.set_sweep(self.mw_start, self.mw_stop, self.mw_step, self.mw_power)
            return_val = n - len(self._mw_frequency_list)
        else:
            return_val = self._mw_device.set_list(self._mw_frequency_list, self.mw_power)

        if return_val != 0:
            self.stopRequested = True
        else:
            if self.scanmode == 'SWEEP':
                self._mw_device.sweep_on()
            else:
                self._mw_device.list_on()

        self._initialize_ODMR_plot()
        self._initialize_ODMR_matrix()
        self.sigNextLine.emit()

    def continue_odmr_scan(self):
        """ """
        self._StartTime = time.time() - self.elapsed_time
        self.start_odmr()
        if self.scanmode == 'SWEEP':
            n = self._mw_device.set_sweep(self.mw_start, self.mw_stop, self.mw_step, self.mw_power)
            return_val = n - len(self._mw_frequency_list)
        else:
            return_val = self._mw_device.set_list(self._mw_frequency_list, self.mw_power)

        if return_val != 0:
            self.stopRequested = True
        else:
            if self.scanmode == 'SWEEP':
                self._mw_device.sweep_on()
            else:
                self._mw_device.list_on()

        self.sigNextLine.emit()

    def stop_odmr_scan(self):
        """ Stop the ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
        return 0

    def _initialize_ODMR_plot(self):
        """ Initializing the ODMR line plot. """
        self.ODMR_plot_x = self._mw_frequency_list
        self.ODMR_plot_y = np.zeros(self._mw_frequency_list.shape)
        self.ODMR_fit_y = np.zeros(self.ODMR_fit_x.shape)

    def _initialize_ODMR_matrix(self):
        """ Initializing the ODMR matrix plot. """
        self.ODMR_plot_xy = np.zeros((self.number_of_lines, len(self._mw_frequency_list)))
        self.sigODMRMatrixAxesChanged.emit()

    def clear_odmr_plots(self):
        """¨Set the option to clear the curret ODMR plot.

        The clear operation has to be performed within the method
        _scan_ODMR_line. This method just sets the tag for that. """
        self._clear_odmr_plots = True

    def _scan_ODMR_line(self):
        """ Scans one line in ODMR

        (from mw_start to mw_stop in steps of mw_step)
        """
        if self.stopRequested:
            with self.threadlock:
                self._mw_device.set_cw(freq=self.mw_frequency, power=self.mw_power)
                self.MW_off()
                self.kill_odmr()
                self.stopRequested = False
                self.unlock()
                self.sigOdmrPlotUpdated.emit()
                self.sigOdmrMatrixUpdated.emit()
                return

        # reset position so every line starts from the same frequency
        if self.scanmode == 'SWEEP':
            self._mw_device.reset_sweep()
        else:
            self._mw_device.reset_listpos()
        new_counts = self._odmr_counter.count_odmr(length=len(self._mw_frequency_list))

        # if during the scan a clearing of the ODMR plots is needed:
        if self._clear_odmr_plots:
            self._odmrscan_counter = 0
            self._initialize_ODMR_plot()
            self._initialize_ODMR_matrix()
            self._clear_odmr_plots = False

        self.ODMR_plot_y = (self._odmrscan_counter * self.ODMR_plot_y + new_counts) / (self._odmrscan_counter + 1)

        # React on the case, when the number of matrix lines have changed during
        # the scan. Essentially, there are three cases which can happen:
        curr_num_lines = np.shape(self.ODMR_plot_xy)[0]
        if curr_num_lines > self.number_of_lines:

            self.ODMR_plot_xy = np.vstack((new_counts, self.ODMR_plot_xy[:self.number_of_lines - 1, :]))

            # It is very necessary that the matrix will be updated BEFORE the
            # axes are adjusted, otherwise, there the display will not fit with
            # the data!
            self.sigOdmrMatrixUpdated.emit()
            self.sigODMRMatrixAxesChanged.emit()
        elif np.shape(self.ODMR_plot_xy)[0] < self.number_of_lines:
            new_matrix = np.zeros((self.number_of_lines, len(self._mw_frequency_list)))
            new_matrix[1:curr_num_lines + 1, :] = self.ODMR_plot_xy
            new_matrix[0, :] = new_counts
            self.ODMR_plot_xy = new_matrix

            # It is very necessary that the matrix will be updated BEFORE the
            # axes are adjusted, otherwise, there the display will not fit with
            # the data!
            self.sigOdmrMatrixUpdated.emit()
            self.sigODMRMatrixAxesChanged.emit()
        else:
            self.ODMR_plot_xy = np.vstack((new_counts, self.ODMR_plot_xy[:-1, :]))
            self.sigOdmrMatrixUpdated.emit()

        if self.safeRawData:
            self.ODMR_raw_data[:, self._odmrscan_counter] = new_counts  # adds the ne odmr line to the overall np.array

        self._odmrscan_counter += 1
        self.elapsed_time = time.time() - self._StartTime
        self.sigOdmrElapsedTimeChanged.emit()
        if self.elapsed_time >= self.run_time:
            self.do_fit(fit_function=self.current_fit_function)
            self.stopRequested = True
            self.sigOdmrFinished.emit()

        self.sigOdmrPlotUpdated.emit()
        self.sigNextLine.emit()

    def set_power(self, power=None):
        """ Forwarding the desired new power from the GUI to the MW source.

        @param float power: power set at the GUI

        @return int: error code (0:OK, -1:error)
        """
        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._mw_device.set_power(power)
            return error_code

    def get_power(self):
        """ Getting the current power from the MW source.

        @return float: current power of the MW source
        """
        power = self._mw_device.get_power()
        return power

    def set_frequency(self, frequency=None):
        """ Forwarding the desired new frequency from the GUI to the MW source.

        @param float frequency: frequency set at the GUI

        @return int: error code (0:OK, -1:error)
        """
        if isinstance(frequency, (int, float)):
            self.mw_frequency = frequency
        else:
            return -1

        if self.getState() == 'locked':
            return -1
        else:
            error_code = self._mw_device.set_frequency(frequency)  # times 1e6 is now done in gui!!
            return error_code

    def get_frequency(self):
        """ Getting the current frequency from the MW source.

        @return float: current frequency of the MW source
        """
        frequency = self._mw_device.get_frequency()  # divided by 1e6 is now done in gui!!
        return frequency

    def MW_on(self):
        """ Switching on the MW source.

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._mw_device.on()
        return error_code

    def MW_off(self):
        """ Switching off the MW source.

        @return int: error code (0:OK, -1:error)
        """
        error_code = self._mw_device.off()
        return error_code

    def get_fit_functions(self):
        """ Returns all fit methods, which are currently implemented for that module.

        @return list: with string entries denoting the names of the fit.
        """

        models = list(self.fit_models.keys())
        models.insert(0, 'No Fit')
        return models

    def do_fit(self, fit_function=None):
        """Performs the chosen fit on the measured data.

        @param string fit_function: name of the chosen fit function

        @return dict: a dictionary with the relevant fit parameters, i.e. the
                      result of the fit
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

        # normalize the frequencies according to the chosen text representation.
        # Those values will be converted to a readable string representation,
        # and not used for further processing!
        freq_norm = self.get_unit_prefix_dict()[self._freq_prefix]

        # write all needed parameters (not rounded!) in this dict:
        param_dict = OrderedDict()

        # CONVENTION:
        # For a good display of the fit parameter, the GUI will assume that the
        # keys in the param_dict are written like:
        #       <what ever comes here>_value = float / int
        #       <what ever comes here>_error = float / int
        #       <what ever comes here>_unit = str
        # Then the GUI can better separate. However that is not obligatory since
        # it will otherwise display just everything.

        kwargs = {
            'axis': self._mw_frequency_list,
            'data': self.ODMR_plot_y,
            'add_parameters': None
        }
        if self.fit_function != 'No Fit' and self.use_custom_params[self.fit_function]:
            kwargs['add_parameters'] = self.fit_models[self.fit_function][1]

        if self.fit_function == 'No Fit':
            self.ODMR_fit_y = np.zeros(self.ODMR_fit_x.shape)
            self.sigOdmrPlotUpdated.emit()  # ist das hier nötig?

        elif self.fit_function == 'Lorentzian':

            result = self._fit_logic.make_lorentzian_fit(**kwargs)
            fitted_function, params = self.fit_models[self.fit_function]
            self.ODMR_fit_y = fitted_function.eval(x=self.ODMR_fit_x, params=result.params)

            cont = result.params['amplitude'].value
            cont /= (-1 * np.pi * result.params['sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont_err = np.sqrt(
                (cont / result.params['amplitude'].value * result.params['amplitude'].stderr) ** 2
                + (cont / result.params['sigma'].value * result.params['sigma'].stderr) ** 2
                + (cont / result.params['c'].value * result.params['c'].stderr) ** 2)
            param_dict = OrderedDict([
                ('Frequency', {
                    'value': np.round(result.params['center'].value / freq_norm, 3),
                    'error': np.round(result.params['center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Linewidth', {
                    'value': np.round(result.params['fwhm'].value / freq_norm, 3),
                    'error': np.round(result.params['fwhm'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Contrast', {
                    'value': np.round(cont * 100, 3),
                    'error': np.round(cont_err * 100, 3),
                    'unit': '%'})
            ])
            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function == 'Double Lorentzian':

            result = self._fit_logic.make_doublelorentzian_fit(**kwargs)
            fitted_function, params = self.fit_models[self.fit_function]
            self.ODMR_fit_y = fitted_function.eval(x=self.ODMR_fit_x, params=result.params)

            cont0 = result.params['lorentz0_amplitude'].value
            cont0 /= (-1 * np.pi * result.params['lorentz0_sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont0_err = np.sqrt(
                (cont0 / result.params['lorentz0_amplitude'].value * result.params['lorentz0_amplitude'].stderr) ** 2
                + (cont0 / result.params['lorentz0_sigma'].value * result.params['lorentz0_sigma'].stderr) ** 2
                + (cont0 / result.params['c'].value * result.params['c'].stderr) ** 2)

            cont1 = result.params['lorentz1_amplitude'].value
            cont1 /= (-1 * np.pi * result.params['lorentz1_sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont1_err = np.sqrt(
                (cont1 / result.params['lorentz1_amplitude'].value * result.params['lorentz1_amplitude'].stderr) ** 2
                + (cont1 / result.params['lorentz1_sigma'].value * result.params['lorentz1_sigma'].stderr) ** 2
                + (cont1 / result.params['c'].value * result.params['c'].stderr) ** 2)

            # create the proper param_dict with the values:
            param_dict = OrderedDict([
                ('Freq. 0', {
                    'value': np.round(result.params['lorentz0_center'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz0_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Linewidth 0', {
                    'value': np.round(result.params['lorentz0_fwhm'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz0_fwhm'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Contrast 0', {
                    'value': np.round(cont0 * 100, 3),
                    'error': np.round(cont0_err * 100, 3),
                    'unit': '%'}),
                ('Freq. 1', {
                    'value': np.round(result.params['lorentz1_center'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz1_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Linewidth 1', {
                    'value': np.round(result.params['lorentz1_fwhm'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz1_fwhm'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Contrast 1', {
                    'value': np.round(cont1 * 100, 3),
                    'error': np.round(cont1_err * 100, 3),
                    'unit': '%'})
            ])
            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function == 'Double Lorentzian with fixed splitting':
            p = Parameters()

            # TODO: insert this in gui config of ODMR
            splitting_from_gui_config = 3.03  # in MHz

            estimate = self._fit_logic.estimate_doublelorentz(self._mw_frequency_list, self.ODMR_plot_y)
            error = estimate[0]
            lorentz0_amplitude = estimate[1]
            lorentz1_amplitude = estimate[2]
            lorentz0_center = estimate[3]
            lorentz1_center = estimate[4]
            lorentz0_sigma = estimate[5]
            lorentz1_sigma = estimate[6]
            offset = estimate[7]

            if lorentz0_center < lorentz1_center:
                p.add('lorentz1_center', expr='lorentz0_center{:+f}'.format(splitting_from_gui_config))
            else:
                splitting_from_gui_config *= -1
                p.add('lorentz1_center', expr='lorentz0_center{:+f}'.format(splitting_from_gui_config))

            kwargs['add_parameters'] = p
            result = self._fit_logic.make_doublelorentzian_fit(**kwargs)
            fitted_function, params = self.fit_models[self.fit_function]
            self.ODMR_fit_y = fitted_function.eval(x=self.ODMR_fit_x, params=result.params)

            cont0 = result.params['lorentz0_amplitude'].value
            cont0 = cont0 / (-1 * np.pi * result.params['lorentz0_sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont0_err = np.sqrt(
                (cont0 / result.params['lorentz0_amplitude'].value * result.params['lorentz0_amplitude'].stderr) ** 2
                + (cont0 / result.params['lorentz0_sigma'].value * result.params['lorentz0_sigma'].stderr) ** 2
                + (cont0 / result.params['c'].value * result.params['c'].stderr) ** 2)

            cont1 = result.params['lorentz1_amplitude'].value
            cont1 = cont1 / (-1 * np.pi * result.params['lorentz1_sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont1_err = np.sqrt(
                (cont1 / result.params['lorentz1_amplitude'].value * result.params['lorentz1_amplitude'].stderr) ** 2
                + (cont1 / result.params['lorentz1_sigma'].value * result.params['lorentz1_sigma'].stderr) ** 2
                + (cont1 / result.params['c'].value * result.params['c'].stderr) ** 2)

            # create the proper param_dict with the values:
            param_dict = OrderedDict([
                ('Freq. 0', {
                    'value': np.round(result.params['lorentz0_center'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz0_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Freq. 1', {
                    'value': np.round(result.params['lorentz1_center'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz1_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Linewidth 0', {
                    'value': np.round(result.params['lorentz0_fwhm'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz0_fwhm'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Linewidth 1', {
                    'value': np.round(result.params['lorentz1_fwhm'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz1_fwhm'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Contrast 0', {
                    'value': np.round(cont0 * 100, 3),
                    'error': np.round(cont0_err * 100, 3),
                    'unit': '%'}),
                ('Contrast 1', {
                    'value': np.round(cont1 * 100, 3),
                    'error': np.round(cont1_err * 100, 3),
                    'unit': '%'})
            ])
            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function == 'N14':
            result = self._fit_logic.make_N14_fit(**kwargs)
            fitted_function, params = self.fit_models[self.fit_function]
            self.ODMR_fit_y = fitted_function.eval(x=self.ODMR_fit_x, params=result.params)

            cont0 = result.params['lorentz0_amplitude'].value
            cont0 = cont0 / (-1 * np.pi * result.params['lorentz0_sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont0_err = np.sqrt(
                (cont0 / result.params['lorentz0_amplitude'].value * result.params['lorentz0_amplitude'].stderr) ** 2
                + (cont0 / result.params['lorentz0_sigma'].value * result.params['lorentz0_sigma'].stderr) ** 2
                + (cont0 / result.params['c'].value * result.params['c'].stderr) ** 2)

            cont1 = result.params['lorentz1_amplitude'].value
            cont1 = cont1 / (-1 * np.pi * result.params['lorentz1_sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont1_err = np.sqrt(
                (cont1 / result.params['lorentz1_amplitude'].value * result.params['lorentz1_amplitude'].stderr) ** 2
                + (cont1 / result.params['lorentz1_sigma'].value * result.params['lorentz1_sigma'].stderr) ** 2
                + (cont1 / result.params['c'].value * result.params['c'].stderr) ** 2)

            cont2 = result.params['lorentz2_amplitude'].value
            cont2 = cont2 / (-1 * np.pi * result.params['lorentz2_sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont2_err = np.sqrt(
                (cont2 / result.params['lorentz1_amplitude'].value * result.params['lorentz1_amplitude'].stderr) ** 2
                + (cont2 / result.params['lorentz1_sigma'].value * result.params['lorentz1_sigma'].stderr) ** 2
                + (cont2 / result.params['c'].value * result.params['c'].stderr) ** 2)

            # create the proper param_dict with the values:
            param_dict = OrderedDict([
                ('Freq. 0', {
                    'value': np.round(result.params['lorentz0_center'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz0_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Freq. 1', {
                    'value': np.round(result.params['lorentz1_center'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz1_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Freq. 2', {
                    'value': np.round(result.params['lorentz2_center'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz2_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Contrast 0', {
                    'value': np.round(cont0 * 100, 3),
                    'error': np.round(cont0_err * 100, 3),
                    'unit': '%'}),
                ('Contrast 1', {
                    'value': np.round(cont1 * 100, 3),
                    'error': np.round(cont1_err * 100, 3),
                    'unit': '%'}),
                ('Contrast 2', {
                    'value': np.round(cont2 * 100, 3),
                    'error': np.round(cont2_err * 100, 3),
                    'unit': '%'})
            ])
            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function == 'N15':
            result = self._fit_logic.make_N15_fit(**kwargs)
            fitted_function, params = self.fit_models[self.fit_function]
            self.ODMR_fit_y = fitted_function.eval(x=self.ODMR_fit_x, params=result.params)

            cont0 = result.params['lorentz0_amplitude'].value
            cont0 = cont0 / (-1 * np.pi * result.params['lorentz0_sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont0_err = np.sqrt(
                (cont0 / result.params['lorentz0_amplitude'].value * result.params['lorentz0_amplitude'].stderr) ** 2
                + (cont0 / result.params['lorentz0_sigma'].value * result.params['lorentz0_sigma'].stderr) ** 2
                + (cont0 / result.params['c'].value * result.params['c'].stderr) ** 2)

            cont1 = result.params['lorentz1_amplitude'].value
            cont1 = cont1 / (-1 * np.pi * result.params['lorentz1_sigma'].value * result.params['c'].value)
            # use gaussian error propagation for error calculation:
            cont1_err = np.sqrt(
                (cont1 / result.params['lorentz1_amplitude'].value * result.params['lorentz1_amplitude'].stderr) ** 2
                + (cont1 / result.params['lorentz1_sigma'].value * result.params['lorentz1_sigma'].stderr) ** 2
                + (cont1 / result.params['c'].value * result.params['c'].stderr) ** 2)

            # create the proper param_dict with the values:
            param_dict = OrderedDict([
                ('Freq. 0', {
                    'value': np.round(result.params['lorentz0_center'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz0_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Freq. 1', {
                    'value': np.round(result.params['lorentz1_center'].value / freq_norm, 3),
                    'error': np.round(result.params['lorentz1_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Contrast 0', {
                    'value': np.round(cont0 * 100, 3),
                    'error': np.round(cont0_err * 100, 3),
                    'unit': '%'}),
                ('Contrast 1', {
                    'value': np.round(cont1 * 100, 3),
                    'error': np.round(cont1_err * 100, 3),
                    'unit': '%'})
            ])
            self.fit_result = self._create_formatted_output(param_dict)

        elif self.fit_function == 'Double Gaussian':
            result = self._fit_logic.make_doublegaussian_fit(**kwargs)
            fitted_function, params = self.fit_models[self.fit_function]
            self.ODMR_fit_y = fitted_function.eval(x=self.ODMR_fit_x, params=result.params)

            cont0 = result.params['gaussian0_amplitude'].value
            cont0 = cont0 / (-1 * np.pi * result.params['gaussian0_sigma'].value * result.params['c'].value)
            cont0_err = np.sqrt(
                (cont0 / result.params['gaussian0_amplitude'].value * result.params['gaussian0_amplitude'].stderr) ** 2
                + (cont0 / result.params['gaussian0_sigma'].value * result.params['gaussian0_sigma'].stderr) ** 2
                + (cont0 / result.params['c'].value * result.params['c'].stderr) ** 2)

            cont1 = result.params['gaussian1_amplitude'].value
            cont1 = cont1 / (-1 * np.pi * result.params['gaussian1_sigma'].value * result.params['c'].value)
            cont1_err = np.sqrt(
                (cont1 / result.params['gaussian1_amplitude'].value * result.params['gaussian1_amplitude'].stderr) ** 2
                + (cont1 / result.params['gaussian1_sigma'].value * result.params['gaussian1_sigma'].stderr) ** 2
                + (cont1 / result.params['c'].value * result.params['c'].stderr) ** 2)

            # create the proper param_dict with the values:
            param_dict = OrderedDict([
                ('Freq. 0', {
                    'value': np.round(result.params['gaussian0_center'].value / freq_norm, 3),
                    'error': np.round(result.params['gaussian0_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Freq. 1', {
                    'value': np.round(result.params['gaussian1_center'].value / freq_norm, 3),
                    'error': np.round(result.params['gaussian1_center'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Linewidth 0', {
                    'value': np.round(result.params['gaussian0_fwhm'].value / freq_norm, 3),
                    'error': np.round(result.params['gaussian0_fwhm'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Linewidth 1', {
                    'value': np.round(result.params['gaussian1_fwhm'].value / freq_norm, 3),
                    'error': np.round(result.params['gaussian1_fwhm'].stderr / freq_norm, 2),
                    'unit': '{0}Hz'.format(self._freq_prefix)}),
                ('Contrast 0', {
                    'value': np.round(cont0 * 100, 3),
                    'error': np.round(cont0_err * 100, 3),
                    'unit': '%'}),
                ('Contrast 1', {
                    'value': np.round(cont1 * 100, 3),
                    'error': np.round(cont1_err * 100, 3),
                    'unit': '%'})
            ])
            self.fit_result = self._create_formatted_output(param_dict)
        else:
            self.logMsg('The Fit Function "{0}" is not implemented to be used in '
                        'the ODMR Logic. Correct that! Fit Call will be '
                        'skipped.'.format(fit_function), msgType='warning')

        return param_dict

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
                output_str += '{0} : {1} {2} \n'.format(
                    entry,
                    param_dict[entry]['value'],
                    param_dict[entry]['unit'])
            else:
                output_str += '{0} : {1} \u00B1 {2} {3} \n'.format(
                    entry,
                    param_dict[entry]['value'],
                    param_dict[entry]['error'],
                    param_dict[entry]['unit'])
        return output_str

    def save_ODMR_Data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Saves the current ODMR data to a file."""

        # three paths to save the raw data (if desired), the odmr scan data and
        # the matrix data.
        filepath = self._save_logic.get_path_for_module(module_name='ODMR')
        filepath2 = self._save_logic.get_path_for_module(module_name='ODMR')
        filepath3 = self._save_logic.get_path_for_module(module_name='ODMR')

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
        data['frequency values (Hz)'] = freq_data
        data['count data'] = count_data
        data2['count data'] = matrix_data  # saves the raw data used in the matrix NOT all only the size of the matrix

        parameters = OrderedDict()
        parameters['Microwave Power (dBm)'] = self.mw_power
        parameters['Run Time (s)'] = self.run_time
        parameters['Start Frequency (Hz)'] = self.mw_start
        parameters['Stop Frequency (Hz)'] = self.mw_stop
        parameters['Step size (Hz)'] = self.mw_step
        parameters['Clock Frequency (Hz)'] = self._clock_frequency
        parameters['Number of matrix lines (#)'] = self.number_of_lines
        parameters['Fit function'] = self.current_fit_function

        i = 0
        for line in self.fit_result.splitlines():
            parameters['Fit result {}'.format(i)] = line
            i += 1

        fig = self.draw_figure(cbar_range=colorscale_range,
                               percentile_range=percentile_range
                               )

        self._save_logic.save_data(
            data,
            filepath,
            parameters=parameters,
            filelabel=filelabel,
            timestamp=timestamp,
            plotfig=fig,
            as_text=True)

        self._save_logic.save_data(
            data2,
            filepath2,
            parameters=parameters,
            filelabel=filelabel2,
            timestamp=timestamp,
            as_text=True)

        self.logMsg('ODMR data saved to:\n{0}'.format(filepath), msgType='status', importance=3)

        if self.safeRawData:
            raw_data = self.ODMR_raw_data  # array cotaining ALL messured data
            data3['count data'] = raw_data  # saves the raw data, ALL of it so keep an eye on performance
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

    def draw_figure(self, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].  
                                 If not supplied then a default of data_min to data_max 
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        freq_data = self.ODMR_plot_x
        count_data = self.ODMR_plot_y
        fit_freq_vals = self.ODMR_fit_x
        fit_count_vals = self.ODMR_fit_y
        matrix_data = self.ODMR_plot_xy

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = [np.min(matrix_data), np.max(matrix_data)]

        # Convert cbar_range to numpy array for division in the SI prefix calculation
        cbar_range = np.array(cbar_range)

        prefix = ['', 'k', 'M', 'G', 'T']
        prefix_index = 0

        # Rescale counts data with SI prefix
        while np.max(count_data) > 1000:
            count_data = count_data / 1000
            fit_count_vals = fit_count_vals / 1000
            prefix_index = prefix_index + 1

        counts_prefix = prefix[prefix_index]

        # Rescale frequency data with SI prefix
        prefix_index = 0

        while np.max(freq_data) > 1000:
            freq_data = freq_data / 1000
            fit_freq_vals = fit_freq_vals / 1000
            prefix_index = prefix_index + 1

        mw_prefix = prefix[prefix_index]

        # Rescale matrix counts data with SI prefix
        prefix_index = 0

        while np.max(matrix_data) > 1000:
            matrix_data = matrix_data / 1000
            cbar_range = cbar_range / 1000
            prefix_index = prefix_index + 1

        cbar_prefix = prefix[prefix_index]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, (ax_mean, ax_matrix) = plt.subplots(nrows=2, ncols=1)

        ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
        ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))

        matrixplot = ax_matrix.imshow(matrix_data,
                                      cmap=plt.get_cmap('inferno'),  # reference the right place in qd
                                      origin='lower',
                                      vmin=cbar_range[0],
                                      vmax=cbar_range[1],
                                      extent=[np.min(freq_data),
                                              np.max(freq_data),
                                              0,
                                              self.number_of_lines
                                              ],
                                      aspect='auto',
                                      interpolation='nearest')

        ax_matrix.set_xlabel('Frequency (' + mw_prefix + 'Hz)')
        ax_matrix.set_ylabel('Scan #')

        # Adjust subplots to make room for colorbar
        fig.subplots_adjust(right=0.8)

        # Add colorbar axis to figure
        cbar_ax = fig.add_axes([0.85, 0.15, 0.02, 0.7])

        # Draw colorbar
        cbar = fig.colorbar(matrixplot, cax=cbar_ax)
        cbar.set_label('Fluorescence (' + cbar_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which=u'both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        return fig

    def perform_odmr_measurement(self, freq_start, freq_step, freq_stop, power,
                                 runtime, fit_function='Lorentzian',
                                 save_after_meas=True, name_tag=''):
        """ An independant method, which can be called by a task with the proper input values
            to perform an odmr measurement.

        @return dict: a parameter container, containing all measurement results
                      of the ODMR measurement.
        """

        while self.getState() != 'idle':
            time.sleep(1)
            print('wait until ready')

        # set all relevant parameter:
        self.mw_start = freq_start
        self.mw_step = freq_step
        self.mw_stop = freq_stop
        self.mw_power = power
        self.run_time = runtime

        # start the scan
        self.start_odmr_scan()

        # check just the state of the optimizer
        while self.getState() != 'idle' and not self.stopRequested:
            time.sleep(1)
            # print('running')

        meas_param = self.do_fit(fit_function=fit_function)

        meas_param['ODMR frequency start (Hz)'] = self.mw_start
        meas_param['ODMR frequency step (Hz)'] = self.mw_step
        meas_param['ODMR frequency stop (Hz)'] = self.mw_stop
        meas_param['ODMR power (dBm)'] = self.mw_power
        meas_param['ODMR run time (s)'] = self.run_time
        meas_param['ODMR measurement saved separetely'] = save_after_meas

        if save_after_meas:
            timestamp = datetime.datetime.now()
            self.save_ODMR_Data(tag=name_tag, timestamp=timestamp)
            meas_param['ODMR measurement saved at time'] = timestamp

        return meas_param
