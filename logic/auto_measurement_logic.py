# -*- coding: utf-8 -*-
"""
Automatic measurement scripts

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

import os
import time
import numpy as np
from core.module import Connector, ConfigOption, StatusVar
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class AutoMeasurementLogic(GenericLogic):
    """
    """
    _modclass = 'automeasurementlogic'
    _modtype = 'logic'

    # declare connectors
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')
    odmrlogic = Connector(interface='ODMRLogic')
    confocallogic = Connector(interface='ConfocalLogic')
    optimizerlogic = Connector(interface='OptimizerLogic')

    def __init__(self, config, **kwargs):
        """ Create PulsedMasterLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)

        # Dictionary servings as status register
        self.status_dict = dict()

        # Measurement parameters
        # ODMR
        self.odmr_runtime = 60
        self.odmr_fit = 'Lorentzian dip'
        self.odmr_start = 2.6e9
        self.odmr_stop = 3.1e9
        self.odmr_step = 2.0e6
        self.odmr_power = -20.0

        # Rabi
        self.rabi_start = 10e-9
        self.rabi_step = 10e-9
        self.rabi_points = 50
        self.rabi_fit = 'sine_decay'
        self.rabi_runtime = 120

        # Hahn echo
        self.hahn_start = 1e-6
        self.hahn_step = 1e-6
        self.hahn_points = 20
        self.hahn_alternating = False
        self.hahn_fit = ''
        self.hahn_runtime = 600

        # General parameters
        self.refocus_interval = 300
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Initialize status register
        self.status_dict = {'sampling_ensemble_busy': False,
                            'sampling_sequence_busy': False,
                            'sampload_busy': False,
                            'loading_busy': False,
                            'pulser_running': False,
                            'measurement_running': False,
                            'microwave_running': False,
                            'predefined_generation_busy': False,
                            'fitting_busy': False}
        return

    def on_deactivate(self):
        """
        """
        return

    #######################################################################
    ###                           Properties                            ###
    #######################################################################
    @property
    def mw_amplitude(self):
        return self.pulsedmasterlogic().generation_parameters.get('microwave_amplitude')

    @mw_amplitude.setter
    def mw_amplitude(self, amp):
        self.pulsedmasterlogic().set_generation_parameters(microwave_amplitude=amp)
        return

    @property
    def rabi_period(self):
        return self.pulsedmasterlogic().generation_parameters.get('rabi_period')

    @rabi_period.setter
    def rabi_period(self, period):
        self.pulsedmasterlogic().set_generation_parameters(rabi_period=period)
        return

    @property
    def mw_frequency(self):
        return self.pulsedmasterlogic().generation_parameters.get('microwave_frequency')

    @mw_frequency.setter
    def mw_frequency(self, freq):
        self.pulsedmasterlogic().set_generation_parameters(microwave_frequency=freq)
        return

    @property
    def laser_length(self):
        return self.pulsedmasterlogic().generation_parameters.get('laser_length')

    @laser_length.setter
    def laser_length(self, length):
        self.pulsedmasterlogic().set_generation_parameters(laser_length=length)
        return

    #######################################################################
    ###                         Refocus methods                         ###
    #######################################################################
    def refocus(self):
        if self.pulsedmasterlogic().status_dict['measurement_running']:
            old_asset = self.pulsedmasterlogic().loaded_asset
            self.pause_pulsed_measurement()
        else:
            old_asset = None

        scanner_pos = self.confocallogic().get_position()
        self.load_ensemble('laser_on')
        self.toggle_pulse_generator(True)
        self.optimizerlogic().start_refocus(scanner_pos, 'confocalgui')
        while self.optimizerlogic().module_state() != 'locked':
            time.sleep(0.1)
        while self.optimizerlogic().module_state() == 'locked':
            time.sleep(0.2)
        time.sleep(2)
        self.toggle_pulse_generator(False)

        if old_asset is not None:
            if old_asset[1] == 'PulseBlockEnsemble':
                self.load_ensemble(old_asset[0])
            else:
                self.load_sequence(old_asset[0])
            self.continue_pulsed_measurement()
        return

    #######################################################################
    ###                    ODMR measurement methods                     ###
    #######################################################################
    def measure_odmr(self, **kwargs):
        """
        """
        if 'start' in kwargs:
            self.odmr_start = kwargs['start']
        if 'stop' in kwargs:
            self.odmr_stop = kwargs['stop']
        if 'step' in kwargs:
            self.odmr_step = kwargs['step']
        if 'power' in kwargs:
            self.odmr_power = kwargs['power']

        self.odmr_start, self.odmr_stop, self.odmr_step, self.odmr_power = self.odmrlogic().set_sweep_parameters(
            start=self.odmr_start, stop=self.odmr_stop, step=self.odmr_step, power=self.odmr_power)
        self.odmr_runtime = self.odmrlogic().set_runtime(self.odmr_runtime)

        self.odmrlogic().start_odmr_scan()
        while self.odmrlogic().module_state() == 'idle':
            time.sleep(0.2)
        while self.odmrlogic().module_state() == 'locked':
            time.sleep(1)
        time.sleep(1)
        self.odmrlogic().do_fit(fit_function=self.odmr_fit)
        fit_result = self.odmrlogic().fc.current_fit_param
        self.odmrlogic().save_odmr_data(tag='autoODMR', percentile_range=[1.0, 99.0])
        return fit_result

    #######################################################################
    ###                    Pulsed measurement methods                   ###
    #######################################################################
    def measure_pulsedodmr(self, **kwargs):
        """
        """
        if 'start' in kwargs:
            self.odmr_start = kwargs['start']
        if 'stop' in kwargs:
            self.odmr_stop = kwargs['stop']
        if 'step' in kwargs:
            self.odmr_step = kwargs['step']
        if 'power' in kwargs:
            self.odmr_power = kwargs['power']

        param_dict = dict()
        param_dict['name'] = 'pulsedODMR'
        param_dict['freq_start'] = self.odmr_start
        param_dict['freq_step'] = self.odmr_step
        param_dict['num_of_points'] = int(
            np.rint((self.odmr_stop - self.odmr_start) / self.odmr_step)) + 1

        self.generate_predefined_sequence('pulsedodmr', param_dict)
        self.sample_ensemble('pulsedODMR', with_load=True)

        self.pulsedmasterlogic().set_measurement_settings(invoke_settings=True)

        self.turn_on_pulsed_measurement()

        start_time = time.time()
        last_refocus = time.time()
        while time.time()-start_time < self.odmr_runtime:
            if self.refocus_interval > 0:
                current_time = time.time()
                if current_time-last_refocus >= self.refocus_interval:
                    self.refocus()
                    last_refocus = time.time()
                    start_time += last_refocus-current_time
            time.sleep(0.5)

        self.turn_off_pulsed_measurement()

        fit_result = self.fit_pulsed(self.odmr_fit)
        self.pulsedmasterlogic().save_measurement_data(tag='autoPulsedODMR', with_error=True)
        return fit_result

    def measure_rabi(self, **kwargs):
        """
        """
        if 'start' in kwargs:
            self.rabi_start = kwargs['start']
        if 'step' in kwargs:
            self.rabi_step = kwargs['step']
        if 'points' in kwargs:
            self.rabi_points = kwargs['points']
        if 'amplitude' in kwargs:
            self.mw_amplitude = kwargs['amplitude']

        param_dict = dict()
        param_dict['name'] = 'rabi'
        param_dict['tau_start'] = self.rabi_start
        param_dict['tau_step'] = self.rabi_step
        param_dict['number_of_taus'] = self.rabi_points

        self.generate_predefined_sequence('rabi', param_dict)
        self.sample_ensemble('rabi', with_load=True)

        self.pulsedmasterlogic().set_measurement_settings(invoke_settings=True)

        self.turn_on_pulsed_measurement()

        start_time = time.time()
        last_refocus = time.time()
        while time.time()-start_time < self.rabi_runtime:
            if self.refocus_interval > 0:
                current_time = time.time()
                if current_time-last_refocus >= self.refocus_interval:
                    self.refocus()
                    last_refocus = time.time()
                    start_time += last_refocus-current_time
            time.sleep(0.5)

        self.turn_off_pulsed_measurement()

        fit_result = self.fit_pulsed(self.rabi_fit)
        self.pulsedmasterlogic().save_measurement_data(tag='autoRabi', with_error=True)
        return fit_result

    def measure_hahnecho(self, **kwargs):
        """
        """
        if 'start' in kwargs:
            self.hahn_start = kwargs['start']
        if 'step' in kwargs:
            self.hahn_step = kwargs['step']
        if 'points' in kwargs:
            self.hahn_points = kwargs['points']
        if 'alternating' in kwargs:
            self.hahn_alternating = kwargs['alternating']
        if 'amplitude' in kwargs:
            self.mw_amplitude = kwargs['amplitude']

        param_dict = dict()
        param_dict['name'] = 'hahn_echo'
        param_dict['tau_start'] = self.hahn_start
        param_dict['tau_step'] = self.hahn_step
        param_dict['num_of_points'] = self.hahn_points
        param_dict['alternating'] = self.hahn_alternating

        self.generate_predefined_sequence('hahnecho', param_dict)
        self.sample_ensemble('hahn_echo', with_load=True)

        self.pulsedmasterlogic().set_measurement_settings(invoke_settings=True)

        self.turn_on_pulsed_measurement()

        start_time = time.time()
        last_refocus = time.time()
        while time.time()-start_time < self.hahn_runtime:
            if self.refocus_interval > 0:
                current_time = time.time()
                if current_time-last_refocus >= self.refocus_interval:
                    self.refocus()
                    last_refocus = time.time()
                    start_time += last_refocus-current_time
            time.sleep(0.5)

        self.turn_off_pulsed_measurement()

        fit_result = self.fit_pulsed(self.hahn_fit)
        self.pulsedmasterlogic().save_measurement_data(tag='autoHahnEcho', with_error=True)
        return fit_result

    #######################################################################
    ###                          Helper methods                         ###
    #######################################################################
    def turn_on_pulsed_measurement(self):
        self.pulsedmasterlogic().toggle_pulsed_measurement(True)
        while not self.pulsedmasterlogic().status_dict['measurement_running']:
            time.sleep(0.2)
        return

    def turn_off_pulsed_measurement(self):
        self.pulsedmasterlogic().toggle_pulsed_measurement(False)
        while self.pulsedmasterlogic().status_dict['measurement_running']:
            time.sleep(0.2)
        return

    def pause_pulsed_measurement(self):
        self.pulsedmasterlogic().toggle_pulsed_measurement(False, 'paused_measurement')
        while self.pulsedmasterlogic().status_dict['measurement_running']:
            time.sleep(0.2)
        return

    def continue_pulsed_measurement(self):
        self.pulsedmasterlogic().toggle_pulsed_measurement(True, 'paused_measurement')
        while self.pulsedmasterlogic().status_dict['measurement_running']:
            time.sleep(0.2)
        return

    def generate_predefined_sequence(self, name, params):
        self.pulsedmasterlogic().generate_predefined_sequence(name, params)
        while self.pulsedmasterlogic().status_dict['predefined_generation_busy']:
            time.sleep(0.2)
        return

    def sample_ensemble(self, name, with_load=False):
        self.pulsedmasterlogic().sample_ensemble(name, with_load=with_load)
        if with_load:
            while self.pulsedmasterlogic().status_dict['sampload_busy']:
                time.sleep(0.2)
        else:
            while self.pulsedmasterlogic().status_dict['sampling_ensemble_busy']:
                time.sleep(0.2)
        return

    def sample_sequence(self, name, with_load=False):
        self.pulsedmasterlogic().sample_sequence(name, with_load=with_load)
        if with_load:
            while self.pulsedmasterlogic().status_dict['sampload_busy']:
                time.sleep(0.2)
        else:
            while self.pulsedmasterlogic().status_dict['sampling_sequence_busy']:
                time.sleep(0.2)
        return

    def load_ensemble(self, name):
        self.pulsedmasterlogic().load_ensemble(name)
        while self.pulsedmasterlogic().status_dict['loading_busy']:
            time.sleep(0.2)
        return

    def load_sequence(self, name):
        self.pulsedmasterlogic().load_sequence(name)
        while self.pulsedmasterlogic().status_dict['loading_busy']:
            time.sleep(0.2)
        return

    def toggle_pulse_generator(self, switch_on):
        self.pulsedmasterlogic().toggle_pulse_generator(switch_on)
        if switch_on:
            while not self.pulsedmasterlogic().status_dict['pulser_running']:
                time.sleep(0.2)
        else:
            while self.pulsedmasterlogic().status_dict['pulser_running']:
                time.sleep(0.2)
        time.sleep(3)
        return

    def fit_pulsed(self, fit_function):
        self.pulsedmasterlogic().do_fit(fit_function)
        while self.pulsedmasterlogic().status_dict['fitting_busy']:
            time.sleep(0.2)
        return self.pulsedmasterlogic().fit_container.current_fit_param
