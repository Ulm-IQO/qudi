# -*- coding: utf-8 -*-

"""
This file contains the Qudi Predefined Methods for sequence generator

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
import inspect
from collections import OrderedDict
from logic.pulse_objects import PulseBlockElement, PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.sampling_functions import *


"""
General Pulse Creation Procedure:
=================================
- Create at first each PulseBlockElement object
- add all PulseBlockElement object to a list and combine them to a
  PulseBlock object.
- Create all needed PulseBlock object with that idea, that means
  PulseBlockElement objects which are grouped to PulseBlock objects.
- Create from the PulseBlock objects a PulseBlockEnsemble object.
- If needed and if possible, combine the created PulseBlockEnsemble objects
  to the highest instance together in a PulseSequence object.
"""


class PulsedObjectGenerator:
    """

    """
    def __init__(self, pulse_generator_settings, generation_parameters):
        self._pulse_generator_settings = pulse_generator_settings
        self._generation_parameters = generation_parameters
        return

    @classmethod
    def attach_method(cls, method):
        if callable(method) and (inspect.ismethod(method) or inspect.isfunction(method)):
            # Bind the method as an attribute to cls
            setattr(cls, method.__name__, method)
        return

    @property
    def pulse_generator_settings(self):
        return self._pulse_generator_settings

    @pulse_generator_settings.setter
    def pulse_generator_settings(self, settings_dict):
        if isinstance(settings_dict, dict):
            self._pulse_generator_settings = settings_dict
        return

    @property
    def generation_parameters(self):
        return self._generation_parameters

    @generation_parameters.setter
    def generation_parameters(self, settings_dict):
        if isinstance(settings_dict, dict):
            self._generation_parameters = settings_dict
        return

    @property
    def predefined_generate_methods(self):
        names = sorted([name for name in dir(self) if name.startswith('generate_')])
        methods = OrderedDict()
        for name in names:
            methods[name[9:]] = getattr(self, name)
        return methods

    @property
    def predefined_generate_params(self):
        methods = self.predefined_generate_methods
        for method_name, method in methods.items():
            param_dict = dict()
            signature_params = inspect.signature(method).parameters
            for name, param in signature_params.items():
                if param.default is param.empty:
                    param_dict[name] = {'type': None, 'default': None}
                else:
                    param_dict[name] = {'type': type(param.default), 'default': param.default}
            methods[method_name] = param_dict
        return methods

    @property
    def channel_set(self):
        channels = self._pulse_generator_settings.get('activation_config')
        if channels is None:
            channels = ('', set())
        return channels[1]

    @property
    def analog_channels(self):
        return {chnl for chnl in self.channel_set if chnl.startswith('a')}

    @property
    def digital_channels(self):
        return {chnl for chnl in self.channel_set if chnl.startswith('d')}

    @property
    def laser_channel(self):
        return self._generation_parameters.get('laser_channel')

    @property
    def sync_channel(self):
        channel = self._generation_parameters.get('sync_channel')
        return None if channel == '' else channel

    @property
    def gate_channel(self):
        channel = self._generation_parameters.get('gate_channel')
        return None if channel == '' else channel

    @property
    def analog_trigger_voltage(self):
        return self._generation_parameters.get('analog_trigger_voltage')

    @property
    def laser_delay(self):
        return self._generation_parameters.get('laser_delay')

    @property
    def microwave_channel(self):
        channel = self._generation_parameters.get('microwave_channel')
        return None if channel == '' else channel

    @property
    def microwave_frequency(self):
        return self._generation_parameters.get('microwave_frequency')

    @property
    def microwave_amplitude(self):
        return self._generation_parameters.get('microwave_amplitude')

    @property
    def laser_length(self):
        return self._generation_parameters.get('laser_length')

    @property
    def wait_time(self):
        return self._generation_parameters.get('wait_time')

    @property
    def rabi_period(self):
        return self._generation_parameters.get('rabi_period')

    def generate_laser_on(self, name='laser_on', length=3.0e-6):
        """ Generates Laser on.

        @param str name: Name of the PulseBlockEnsemble
        @param float length: laser duration in seconds

        @return object: the generated PulseBlockEnsemble object.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the laser element
        laser_element = self._get_laser_element(length=length, increment=0)
        # Create block and append to created_blocks list
        laser_block = PulseBlock(name=name)
        laser_block.append_element(laser_element)
        created_blocks.append(laser_block)
        # Create block ensemble and append to created_ensembles list
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append_block(block_name=laser_block.name, reps=0)
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_laser_mw_on(self, name='laser_mw_on', length=3.0e-6):
        """ General generation method for laser on and microwave on generation.

        @param string name: Name of the PulseBlockEnsemble to be generated
        @param float length: Length of the PulseBlockEnsemble in seconds

        @return object: the generated PulseBlockEnsemble object.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the laser_mw element
        laser_mw_element = self._get_mw_laser_element(length=length,
                                                      increment=0,
                                                      amp=self.microwave_amplitude,
                                                      freq=self.microwave_frequency,
                                                      phase=0)
        # Create block and append to created_blocks list
        laser_mw_block = PulseBlock(name=name)
        laser_mw_block.append_element(laser_mw_element)
        created_blocks.append(laser_mw_block)
        # Create block ensemble and append to created_ensembles list
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append_block(block_name=laser_mw_block.name, reps=0)
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_idle(self, name='idle', length=3.0e-6):
        """ Generate just a simple idle ensemble.

        @param str name: Name of the PulseBlockEnsemble to be generated
        @param float length: Length of the PulseBlockEnsemble in seconds

        @return object: the generated PulseBlockEnsemble object.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the laser_mw element
        idle_element = self._get_idle_element(length=length, increment=0)
        # Create block and append to created_blocks list
        idle_block = PulseBlock(name=name)
        idle_block.append_element(idle_element)
        created_blocks.append(idle_block)
        # Create block ensemble and append to created_ensembles list
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append_block(block_name=idle_block.name, reps=0)
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_rabi(self, name='rabi', tau_start=10.0e-9, tau_step=10.0e-9, number_of_taus=50):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(number_of_taus) * tau_step

        # create the laser_mw element
        mw_element = self._get_mw_element(length=tau_start,
                                          increment=tau_step,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0)
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        rabi_block.append_element(mw_element)
        rabi_block.append_element(laser_element)
        rabi_block.append_element(delay_element)
        rabi_block.append_element(waiting_element)
        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append_block(block_name=rabi_block.name, reps=number_of_taus - 1)

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append_element(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append_block(block_name=sync_block.name, reps=0)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_taus
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_pulsedodmr(self, name='pulsedODMR', freq_start=2870.0e6, freq_step=0.2e6,
                            num_of_points=50):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # Create frequency array
        freq_array = freq_start + np.arange(num_of_points) * freq_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        pulsedodmr_block = PulseBlock(name=name)
        for mw_freq in freq_array:
            mw_element = self._get_mw_element(length=self.rabi_period / 2,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=mw_freq,
                                              phase=0)
            pulsedodmr_block.append_element(mw_element)
            pulsedodmr_block.append_element(laser_element)
            pulsedodmr_block.append_element(delay_element)
            pulsedodmr_block.append_element(waiting_element)
        created_blocks.append(pulsedodmr_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append_block(block_name=pulsedodmr_block.name, reps=0)

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append_element(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append_block(block_name=sync_block.name, reps=0)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['number_of_lasers'] = num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_ramsey(self, name='ramsey', tau_start=1.0e-6, tau_step=1.0e-6, num_of_points=50,
                        alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
        tau_element = self._get_idle_element(length=tau_start, increment=tau_step)

        # Create block and append to created_blocks list
        ramsey_block = PulseBlock(name=name)
        ramsey_block.append_element(pihalf_element)
        ramsey_block.append_element(tau_element)
        ramsey_block.append_element(pihalf_element)
        ramsey_block.append_element(laser_element)
        ramsey_block.append_element(delay_element)
        ramsey_block.append_element(waiting_element)
        if alternating:
            ramsey_block.append_element(pihalf_element)
            ramsey_block.append_element(tau_element)
            ramsey_block.append_element(pi3half_element)
            ramsey_block.append_element(laser_element)
            ramsey_block.append_element(delay_element)
            ramsey_block.append_element(waiting_element)
        created_blocks.append(ramsey_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append_block(block_name=ramsey_block.name, reps=num_of_points - 1)

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append_element(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append_block(block_name=sync_block.name, reps=0)

        # add metadata to invoke settings later on
        number_of_lasers = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_hahnecho(self, name='hahn_echo', tau_start=1.0e-6, tau_step=1.0e-6,
                          num_of_points=50, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                          increment=0,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0)
        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
        tau_element = self._get_idle_element(length=tau_start, increment=tau_step)

        # Create block and append to created_blocks list
        hahn_block = PulseBlock(name=name)
        hahn_block.append_element(pihalf_element)
        hahn_block.append_element(tau_element)
        hahn_block.append_element(pi_element)
        hahn_block.append_element(tau_element)
        hahn_block.append_element(pihalf_element)
        hahn_block.append_element(laser_element)
        hahn_block.append_element(delay_element)
        hahn_block.append_element(waiting_element)
        if alternating:
            hahn_block.append_element(pihalf_element)
            hahn_block.append_element(tau_element)
            hahn_block.append_element(pi_element)
            hahn_block.append_element(tau_element)
            hahn_block.append_element(pi3half_element)
            hahn_block.append_element(laser_element)
            hahn_block.append_element(delay_element)
            hahn_block.append_element(waiting_element)
        created_blocks.append(hahn_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append_block(block_name=hahn_block.name, reps=num_of_points - 1)

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append_element(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append_block(block_name=sync_block.name, reps=0)

        # add metadata to invoke settings later on
        number_of_lasers = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_HHamp(self, name='hh_amp', spinlock_length=20e-6, amp_start=0.05, amp_step=0.01,
                       num_of_points=50):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get amplitude array for measurement ticks
        amp_array = amp_start + np.arange(num_of_points) * amp_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)

        # Create block and append to created_blocks list
        hhamp_block = PulseBlock(name=name)
        for sl_amp in amp_array:
            sl_element = self._get_mw_element(length=spinlock_length,
                                              increment=0,
                                              amp=sl_amp,
                                              freq=self.microwave_frequency,
                                              phase=90)
            hhamp_block.append_element(pihalf_element)
            hhamp_block.append_element(sl_element)
            hhamp_block.append_element(pihalf_element)
            hhamp_block.append_element(laser_element)
            hhamp_block.append_element(delay_element)
            hhamp_block.append_element(waiting_element)

            hhamp_block.append_element(pi3half_element)
            hhamp_block.append_element(sl_element)
            hhamp_block.append_element(pihalf_element)
            hhamp_block.append_element(laser_element)
            hhamp_block.append_element(delay_element)
            hhamp_block.append_element(waiting_element)
        created_blocks.append(hhamp_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append_block(block_name=hhamp_block.name, reps=0)

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append_element(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append_block(block_name=sync_block.name, reps=0)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = True
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = amp_array
        block_ensemble.measurement_information['units'] = ('V', '')
        block_ensemble.measurement_information['number_of_lasers'] = 2 * num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_HHtau(self, name='hh_tau', spinlock_amp=0.1, tau_start=0.001, tau_step=0.001,
                       num_of_points=50):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
        sl_element = self._get_mw_element(length=tau_start,
                                          increment=tau_step,
                                          amp=spinlock_amp,
                                          freq=self.microwave_frequency,
                                          phase=90)

        # Create block and append to created_blocks list
        hhtau_block = PulseBlock(name=name)
        hhtau_block.append_element(pihalf_element)
        hhtau_block.append_element(sl_element)
        hhtau_block.append_element(pihalf_element)
        hhtau_block.append_element(laser_element)
        hhtau_block.append_element(delay_element)
        hhtau_block.append_element(waiting_element)

        hhtau_block.append_element(pi3half_element)
        hhtau_block.append_element(sl_element)
        hhtau_block.append_element(pihalf_element)
        hhtau_block.append_element(laser_element)
        hhtau_block.append_element(delay_element)
        hhtau_block.append_element(waiting_element)
        created_blocks.append(hhtau_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append_block(block_name=hhtau_block.name, reps=num_of_points - 1)

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append_element(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append_block(block_name=sync_block.name, reps=0)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = True
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['number_of_lasers'] = 2 * num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_HHpol(self, name='hh_pol', spinlock_length=20.0e-6, spinlock_amp=0.1,
                       polarization_steps=50):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get steps array for measurement ticks
        steps_array = np.arange(2 * polarization_steps)

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
        sl_element = self._get_mw_element(length=spinlock_length,
                                          increment=0,
                                          amp=spinlock_amp,
                                          freq=self.microwave_frequency,
                                          phase=90)

        # Create block for "up"-polarization and append to created_blocks list
        up_block = PulseBlock(name=name + '_up')
        up_block.append_element(pihalf_element)
        up_block.append_element(sl_element)
        up_block.append_element(pihalf_element)
        up_block.append_element(laser_element)
        up_block.append_element(delay_element)
        up_block.append_element(waiting_element)
        created_blocks.append(up_block)

        # Create block for "down"-polarization and append to created_blocks list
        down_block = PulseBlock(name=name + '_down')
        down_block.append_element(pi3half_element)
        down_block.append_element(sl_element)
        down_block.append_element(pi3half_element)
        down_block.append_element(laser_element)
        down_block.append_element(delay_element)
        down_block.append_element(waiting_element)
        created_blocks.append(down_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append_block(block_name=up_block.name, reps=polarization_steps - 1)
        block_ensemble.append_block(block_name=down_block.name, reps=polarization_steps - 1)

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append_element(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append_block(block_name=sync_block.name, reps=0)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = steps_array
        block_ensemble.measurement_information['units'] = ('#', '')
        block_ensemble.measurement_information['number_of_lasers'] = 2 * polarization_steps
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_xy8_tau(self, name='xy8_tau', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                         xy8_order=4, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        # calculate "real" start length of tau due to finite pi-pulse length
        real_start_tau = max(0, tau_start - self.rabi_period / 2)

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
        pix_element = self._get_mw_element(length=self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=0)
        piy_element = self._get_mw_element(length=self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=90)
        tauhalf_element = self._get_idle_element(length=real_start_tau / 2, increment=tau_step / 2)
        tau_element = self._get_idle_element(length=real_start_tau, increment=tau_step)

        # Create block and append to created_blocks list
        xy8_block = PulseBlock(name=name)
        xy8_block.append_element(pihalf_element)
        xy8_block.append_element(tauhalf_element)
        for n in range(xy8_order):
            xy8_block.append_element(pix_element)
            xy8_block.append_element(tau_element)
            xy8_block.append_element(piy_element)
            xy8_block.append_element(tau_element)
            xy8_block.append_element(pix_element)
            xy8_block.append_element(tau_element)
            xy8_block.append_element(piy_element)
            xy8_block.append_element(tau_element)
            xy8_block.append_element(piy_element)
            xy8_block.append_element(tau_element)
            xy8_block.append_element(pix_element)
            xy8_block.append_element(tau_element)
            xy8_block.append_element(piy_element)
            xy8_block.append_element(tau_element)
            xy8_block.append_element(pix_element)
            if n != xy8_order - 1:
                xy8_block.append_element(tau_element)
        xy8_block.append_element(tauhalf_element)
        xy8_block.append_element(pihalf_element)
        xy8_block.append_element(laser_element)
        xy8_block.append_element(delay_element)
        xy8_block.append_element(waiting_element)
        if alternating:
            xy8_block.append_element(pihalf_element)
            xy8_block.append_element(tauhalf_element)
            for n in range(xy8_order):
                xy8_block.append_element(pix_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(piy_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(pix_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(piy_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(piy_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(pix_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(piy_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(pix_element)
                if n != xy8_order - 1:
                    xy8_block.append_element(tau_element)
            xy8_block.append_element(tauhalf_element)
            xy8_block.append_element(pi3half_element)
            xy8_block.append_element(laser_element)
            xy8_block.append_element(delay_element)
            xy8_block.append_element(waiting_element)
        created_blocks.append(xy8_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append_block(block_name=xy8_block.name, reps=num_of_points - 1)

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append_element(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append_block(block_name=sync_block.name, reps=0)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_xy8_freq(self, name='xy8_freq', freq_start=0.1e6, freq_step=0.01e6,
                          num_of_points=50, xy8_order=4, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get frequency array for measurement ticks
        freq_array = freq_start + np.arange(num_of_points) * freq_step
        # get tau array from freq array
        tau_array = 1 / (2 * freq_array)
        # calculate "real" tau array (finite pi-pulse length)
        real_tau_array = tau_array - self.rabi_period / 2
        np.clip(real_tau_array, 0, None, real_tau_array)
        # Convert back to frequency in order to account for clipped values
        freq_array = 1 / (2 * (real_tau_array + self.rabi_period / 2))

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
        pix_element = self._get_mw_element(length=self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=0)
        piy_element = self._get_mw_element(length=self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=90)

        # Create block and append to created_blocks list
        xy8_block = PulseBlock(name=name)
        for ii, tau in enumerate(real_tau_array):
            tauhalf_element = self._get_idle_element(length=tau / 2, increment=0)
            tau_element = self._get_idle_element(length=tau, increment=0)
            xy8_block.append_element(pihalf_element)
            xy8_block.append_element(tauhalf_element)
            for n in range(xy8_order):
                xy8_block.append_element(pix_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(piy_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(pix_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(piy_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(piy_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(pix_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(piy_element)
                xy8_block.append_element(tau_element)
                xy8_block.append_element(pix_element)
                if n != xy8_order - 1:
                    xy8_block.append_element(tau_element)
            xy8_block.append_element(tauhalf_element)
            xy8_block.append_element(pihalf_element)
            xy8_block.append_element(laser_element)
            xy8_block.append_element(delay_element)
            xy8_block.append_element(waiting_element)
            if alternating:
                xy8_block.append_element(pihalf_element)
                xy8_block.append_element(tauhalf_element)
                for n in range(xy8_order):
                    xy8_block.append_element(pix_element)
                    xy8_block.append_element(tau_element)
                    xy8_block.append_element(piy_element)
                    xy8_block.append_element(tau_element)
                    xy8_block.append_element(pix_element)
                    xy8_block.append_element(tau_element)
                    xy8_block.append_element(piy_element)
                    xy8_block.append_element(tau_element)
                    xy8_block.append_element(piy_element)
                    xy8_block.append_element(tau_element)
                    xy8_block.append_element(pix_element)
                    xy8_block.append_element(tau_element)
                    xy8_block.append_element(piy_element)
                    xy8_block.append_element(tau_element)
                    xy8_block.append_element(pix_element)
                    if n != xy8_order - 1:
                        xy8_block.append_element(tau_element)
                xy8_block.append_element(tauhalf_element)
                xy8_block.append_element(pi3half_element)
                xy8_block.append_element(laser_element)
                xy8_block.append_element(delay_element)
                xy8_block.append_element(waiting_element)
        created_blocks.append(xy8_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append_block(block_name=xy8_block.name, reps=0)

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append_element(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append_block(block_name=sync_block.name, reps=0)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    ################################################################################################
    #                                   Helper methods                                          ####
    ################################################################################################
    def _get_idle_element(self, length, increment):
        """
        Creates an idle pulse PulseBlockElement

        @param float length: idle duration in seconds
        @param float increment: idle duration increment in seconds

        @return: PulseBlockElement, the generated idle element
        """
        # Create idle element
        return PulseBlockElement(init_length_s=length,
                                 increment_s=increment,
                                 pulse_function={chnl: Idle() for chnl in self.analog_channels},
                                 digital_high={chnl: False for chnl in self.digital_channels})

    def _get_trigger_element(self, length, increment, channels):
        """
        Creates a trigger PulseBlockElement

        @param float length: trigger duration in seconds
        @param float increment: trigger duration increment in seconds
        @param str|list channels: The pulser channel(s) to be triggered.

        @return: PulseBlockElement, the generated trigger element
        """
        if isinstance(channels, str):
            channels = [channels]

        # input params for element generation
        pulse_function = {chnl: Idle() for chnl in self.analog_channels}
        digital_high = {chnl: False for chnl in self.digital_channels}

        # Determine analogue or digital trigger channel and set channels accordingly.
        for channel in channels:
            if channel.startswith('d'):
                digital_high[channel] = True
            else:
                pulse_function[channel] = DC(voltage=self.analog_trigger_voltage)

        # return trigger element
        return PulseBlockElement(init_length_s=length,
                                 increment_s=increment,
                                 pulse_function=pulse_function,
                                 digital_high=digital_high)

    def _get_laser_element(self, length, increment):
        """
        Creates laser trigger PulseBlockElement

        @param float length: laser pulse duration in seconds
        @param float increment: laser pulse duration increment in seconds

        @return: PulseBlockElement, two elements for laser and gate trigger (delay element)
        """
        return self._get_trigger_element(length=length,
                                         increment=increment,
                                         channels=self.laser_channel)

    def _get_laser_gate_element(self, length, increment):
        """
        """
        laser_gate_element = self._get_laser_element(length=length,
                                                     increment=increment)
        if self.gate_channel:
            if self.gate_channel.startswith('d'):
                laser_gate_element.digital_high[self.gate_channel] = True
            else:
                laser_gate_element.pulse_function[self.gate_channel] = DC(
                    voltage=self.analog_trigger_voltage)
        return laser_gate_element

    def _get_delay_element(self):
        """
        Creates an idle element of length of the laser delay

        @return PulseBlockElement: The delay element
        """
        return self._get_idle_element(length=self.laser_delay,
                                      increment=0)

    def _get_delay_gate_element(self):
        """
        Creates a gate trigger of length of the laser delay.
        If no gate channel is specified will return a simple idle element.

        @return PulseBlockElement: The delay element
        """
        if self.gate_channel:
            return self._get_trigger_element(length=self.laser_delay,
                                             increment=0,
                                             channels=self.gate_channel)
        else:
            return self._get_delay_element()

    def _get_sync_element(self):
        """

        """
        return self._get_trigger_element(length=50e-9,
                                         increment=0,
                                         channels=self.sync_channel)

    def _get_mw_element(self, length, increment, amp=None, freq=None, phase=None):
        """
        Creates a MW pulse PulseBlockElement

        @param float length: MW pulse duration in seconds
        @param float increment: MW pulse duration increment in seconds
        @param float freq: MW frequency in case of analogue MW channel in Hz
        @param float amp: MW amplitude in case of analogue MW channel in V
        @param float phase: MW phase in case of analogue MW channel in deg

        @return: PulseBlockElement, the generated MW element
        """
        if self.microwave_channel.startswith('d'):
            mw_element = self._get_trigger_element(
                length=length,
                increment=increment,
                channels=self.microwave_channel)
        else:
            mw_element = self._get_idle_element(
                length=length,
                increment=increment)
            mw_element.pulse_function[self.microwave_channel] = Sin(amplitude=amp,
                                                                    frequency=freq,
                                                                    phase=phase)
        return mw_element

    def _get_multiple_mw_element(self, length, increment, amps=None, freqs=None, phases=None):
        """
        Creates single, double or triple sine mw element.

        @param float length: MW pulse duration in seconds
        @param float increment: MW pulse duration increment in seconds
        @param amps: list containing the amplitudes
        @param freqs: list containing the frequencies
        @param phases: list containing the phases
        @return: PulseBlockElement, the generated MW element
        """
        if isinstance(amps, (int, float)):
            amps = [amps]
        if isinstance(freqs, (int, float)):
            freqs = [freqs]
        if isinstance(phases, (int, float)):
            phases = [phases]

        if self.microwave_channel.startswith('d'):
            mw_element = self._get_trigger_element(
                length=length,
                increment=increment,
                channels=self.microwave_channel)
        else:
            mw_element = self._get_idle_element(
                length=length,
                increment=increment)

            sine_number = min(len(amps), len(freqs), len(phases))

            if sine_number < 2:
                mw_element.pulse_function[self.microwave_channel] = Sin(amplitude=amps[0],
                                                                        frequency=freqs[0],
                                                                        phase=phases[0])
            elif sine_number == 2:
                mw_element.pulse_function[self.microwave_channel] = DoubleSin(amplitude_1=amps[0],
                                                                              amplitude_2=amps[1],
                                                                              frequency_1=freqs[0],
                                                                              frequency_2=freqs[1],
                                                                              phase_1=phases[0],
                                                                              phase_2=phases[1])
            else:
                mw_element.pulse_function[self.microwave_channel] = TripleSin(amplitude_1=amps[0],
                                                                              amplitude_2=amps[1],
                                                                              amplitude_3=amps[2],
                                                                              frequency_1=freqs[0],
                                                                              frequency_2=freqs[1],
                                                                              frequency_3=freqs[2],
                                                                              phase_1=phases[0],
                                                                              phase_2=phases[1],
                                                                              phase_3=phases[2])
        return mw_element

    def _get_mw_laser_element(self, length, increment, amp=None, freq=None, phase=None):
        """

        @param length:
        @param increment:
        @param amp:
        @param freq:
        @param phase:
        @return:
        """
        mw_laser_element = self._get_mw_element(length=length,
                                                increment=increment,
                                                amp=amp,
                                                freq=freq,
                                                phase=phase)
        if self.laser_channel.startswith('d'):
            mw_laser_element.digital_high[self.laser_channel] = True
        else:
            mw_laser_element.pulse_function[self.laser_channel] = DC(
                voltage=self.analog_trigger_voltage)
        return mw_laser_element

    def _get_ensemble_count_length(self, ensemble, created_blocks):
        """

        @param ensemble:
        @param created_blocks:
        @return:
        """
        if self.gate_channel:
            length = self.laser_length + self.laser_delay
        else:
            blocks = {block.name: block for block in created_blocks}
            length = 0.0
            for block_name, reps in ensemble.block_list:
                length += blocks[block_name].init_length_s * (reps + 1)
                length += blocks[block_name].increment_s * ((reps**2 + reps) / 2)
        return length
