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

import time
import copy
import numpy as np
from core.module import Connector, ConfigOption, StatusVar
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class NV:
    def __init__(self, anchor, shift=(0, 0, 0), label='', **kwargs):
        self._anchor = np.zeros(3, dtype=float)
        self.anchor = anchor
        self._shift = np.array(shift, dtype=float)
        self.label = label

        self.odmr_freq = kwargs.get('odmr_freq')
        self.rabi_period = kwargs.get('rabi_period')
        self.t2 = kwargs.get('t2')
        self.t1 = kwargs.get('t1')
        return

    @property
    def position(self):
        return self._anchor + self._shift

    @position.setter
    def position(self, new_pos):
        if len(new_pos) == 3:
            self._shift = np.array(new_pos, dtype=float) - self._anchor
        else:
            raise ValueError('Position must be a triplet of float or int values.')
        return

    @property
    def anchor(self):
        return self._anchor

    @anchor.setter
    def anchor(self, new_pos):
        if len(new_pos) == 3:
            self._anchor = np.array(new_pos, dtype=float)
        else:
            raise ValueError('Anchor must be a triplet of float or int values.')
        return

    @property
    def shift(self):
        return self._shift

    @anchor.setter
    def shift(self, new_shift):
        if len(new_shift) == 3:
            self._shift = np.array(new_shift, dtype=float)
        else:
            raise ValueError('Sample shift must be a triplet of float or int values.')
        return

    @property
    def x(self):
        return self.position[0]

    @x.setter
    def x(self, x_pos):
        self._shift[0] = x_pos - self._anchor[0]
        return

    @property
    def y(self):
        return self._position[1]

    @y.setter
    def y(self, y_pos):
        self._shift[1] = y_pos - self._anchor[1]
        return

    @property
    def z(self):
        return self._position[2]

    @z.setter
    def z(self, z_pos):
        self._shift[2] = z_pos - self._anchor[2]
        return

    def get_dict_repr(self):
        repr_dict = vars(self).copy()
        del repr_dict['_anchor']
        del repr_dict['_shift']
        repr_dict['anchor'] = self.anchor
        repr_dict['shift'] = self.shift
        return repr_dict


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

    # StatusVars
    refocus_interval = StatusVar(name='refocus_interval', default=300)
    odmr = StatusVar(name='odmr', default={'runtime': 60, 'fit': None, 'start': 2.65e9,
                                           'stop': 3.15e9, 'step': 2.0e6, 'power': -20.0})
    rabi = StatusVar(name='rabi', default={'runtime': 60, 'fit': None, 'start': 10.0e-9,
                                           'step': 10.0e-9, 'points': 50})
    hahnecho = StatusVar(name='hahnecho', default={'runtime': 600, 'fit': None, 'start': 1e-6,
                                                   'step': 1e-6, 'points': 20, 'alternating': True})
    xy8 = StatusVar(name='xy8', default={'runtime': 600, 'fit': None, 'start': 500e-9, 'order': 4,
                                         'step': 10e-9, 'points': 40, 'alternating': True})
    nv_list = StatusVar(name='nv_list', default=list())

    def __init__(self, config, **kwargs):
        """ Create PulsedMasterLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        return

    def on_deactivate(self):
        """
        """
        return

    @nv_list.respresenter
    def get_nv_dict_repr(self, val):
        return [nv.get_dict_repr() for nv in val]

    @nv_list.constructor
    def create_nv_list(self, val):
        return [NV(**dict_repr) for dict_repr in val]

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

    @property
    def pulsed_fits(self):
        return list(self.pulsedmasterlogic().fit_container.fit_list)

    @property
    def odmr_fits(self):
        return list(self.odmrlogic().fc.fit_list)

    @property
    def nv_labels(self):
        return [nv.label for nv in self.nv_list]

    #######################################################################
    ###                             NV methods                          ###
    #######################################################################
    def add_nv(self, label='', position=None):
        if position is None:
            position = self.confocallogic().get_position()
        self.nv_list.append(NV(anchor=position, label=label))
        return

    def remove_nv(self, index):
        if isinstance(index, str):
            for i, nv in enumerate(self.nv_list):
                if nv.label == index:
                    index = i
                    break
        if isinstance(index, int):
            if 0 <= index < len(self.nv_list):
                del self.nv_list[index]
        return

    def set_sample_shift(self, shift):
        shift = np.array(shift, dtype=float)
        for nv in self.nv_list:
            nv.shift = shift
        return

    def add_sample_shift(self, shift):
        shift = np.array(shift, dtype=float)
        for nv in self.nv_list:
            nv.shift = nv.shift + shift
        return

    #######################################################################
    ###                   High level measurement methods                ###
    #######################################################################
    def characterize_nv(self, label):
        nv = None
        if isinstance(label, int):
            nv = self.nv_list[label]
            label = nv.label if nv.label else str(label)
        elif isinstance(label, str):
            for i, nv_inst in enumerate(self.nv_list):
                if nv_inst.label == label:
                    nv = nv_inst
                    break
        else:
            self.log.error('NV label must be either str or int.')
            return

        if nv is None:
            self.log.error('NV with label "{0}" not found.')
            return

        self.move_to(nv.position)
        self.refocus()
        odmr_result = self.measure_odmr(label)
        if np.abs(odmr_result['contrast'].value) < 3:
            self.log.error('ODMR contrast below 3%! Aborting "characterize_nv" execution.')
            return
        nv.odmr_freq = odmr_result['center'].value
        self.mw_frequency = nv.odmr_freq

        self.refocus()
        rabi_result = self.measure_rabi(label)
        nv.rabi_period = 1/rabi_result['frequency'].value
        self.rabi_period = nv.rabi_period

        self.refocus()
        hahn_result = self.measure_hahnecho(label)
        nv.t2 = hahn_result['lifetime'].value

        xy8_result = self.measure_xy8(label)
        return odmr_result, rabi_result, hahn_result, xy8_result

    #######################################################################
    ###                        Confocal methods                         ###
    #######################################################################
    def move_to(self, position):
        err_code = self.confocallogic().set_position('optimizer', *position)
        if err_code != 0:
            self.log.error('Move to "{0}" failed. Scanner busy.'.format(position))
        return

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
    def measure_odmr(self, label='', **kwargs):
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
        fit_result = copy.deepcopy(self.odmrlogic().fc.current_fit_param)
        savetag = 'autoODMR_{0}'.format(label) if label else 'autoODMR'
        self.odmrlogic().save_odmr_data(tag=savetag, percentile_range=[1.0, 99.0])
        return fit_result

    #######################################################################
    ###                    Pulsed measurement methods                   ###
    #######################################################################
    def measure_pulsedodmr(self, label='', **kwargs):
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
        if 'rabi_period' in kwargs:
            self.rabi_period = kwargs['rabi_period']

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

        fit_result = copy.deepcopy(self.fit_pulsed(self.odmr_fit))
        savetag = 'autoPulsedODMR_{0}'.format(label) if label else 'autoPulsedODMR'
        self.pulsedmasterlogic().save_measurement_data(tag=savetag, with_error=True)
        return fit_result

    def measure_rabi(self, label='', **kwargs):
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

        fit_result = copy.deepcopy(self.fit_pulsed(self.rabi_fit))
        savetag = 'autoRabi_{0}'.format(label) if label else 'autoRabi'
        self.pulsedmasterlogic().save_measurement_data(tag=savetag, with_error=True)
        return fit_result

    def measure_hahnecho(self, label='', **kwargs):
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
        if 'rabi_period' in kwargs:
            self.rabi_period = kwargs['rabi_period']

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

        fit_result = copy.deepcopy(self.fit_pulsed(self.hahn_fit))
        savetag = 'autoHahnEcho_{0}'.format(label) if label else 'autoHahnEcho'
        self.pulsedmasterlogic().save_measurement_data(tag=savetag, with_error=True)
        return fit_result

    def measure_xy8(self, label='', **kwargs):
        """
        """
        if 'start' in kwargs:
            self.xy8_start = kwargs['start']
        if 'step' in kwargs:
            self.xy8_step = kwargs['step']
        if 'order' in kwargs:
            self.xy8_order = kwargs['order']
        if 'points' in kwargs:
            self.xy8_points = kwargs['points']
        if 'alternating' in kwargs:
            self.xy8_alternating = kwargs['alternating']
        if 'amplitude' in kwargs:
            self.mw_amplitude = kwargs['amplitude']
        if 'rabi_period' in kwargs:
            self.rabi_period = kwargs['rabi_period']

        param_dict = dict()
        param_dict['name'] = 'xy8'
        param_dict['tau_start'] = self.xy8_start
        param_dict['tau_step'] = self.xy8_step
        param_dict['xy8_order'] = self.xy8_order
        param_dict['num_of_points'] = self.xy8_points
        param_dict['alternating'] = self.xy8_alternating

        self.generate_predefined_sequence('xy8_tau', param_dict)
        self.sample_ensemble('xy8', with_load=True)

        self.pulsedmasterlogic().set_measurement_settings(invoke_settings=True)

        self.turn_on_pulsed_measurement()

        start_time = time.time()
        last_refocus = time.time()
        while time.time()-start_time < self.xy8_runtime:
            if self.refocus_interval > 0:
                current_time = time.time()
                if current_time-last_refocus >= self.refocus_interval:
                    self.refocus()
                    last_refocus = time.time()
                    start_time += last_refocus-current_time
            time.sleep(0.5)

        self.turn_off_pulsed_measurement()

        fit_result = copy.deepcopy(self.fit_pulsed(self.xy8_fit))
        savetag = 'autoXY8_{0}'.format(label) if label else 'autoXY8'
        self.pulsedmasterlogic().save_measurement_data(tag=savetag, with_error=True)
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
