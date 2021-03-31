# -*- coding: utf-8 -*-

"""
This file contains the Qudi Predefined Methods for dynamical decoupling sequences

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
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from logic.pulsed.sampling_functions import DDMethods



class DDPredefinedGenerator(PredefinedGeneratorBase):
    """

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        tau_pspacing_start = self.tau_2_pulse_spacing(tau_start)

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        # Use a 180 deg phase shifted pulse as 3pihalf pulse if microwave channel is analog
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
        tauhalf_element = self._get_idle_element(length=tau_pspacing_start / 2, increment=tau_step / 2)
        tau_element = self._get_idle_element(length=tau_pspacing_start, increment=tau_step)

        # Create block and append to created_blocks list
        xy8_block = PulseBlock(name=name)
        xy8_block.append(pihalf_element)
        xy8_block.append(tauhalf_element)
        for n in range(xy8_order):
            xy8_block.append(pix_element)
            xy8_block.append(tau_element)
            xy8_block.append(piy_element)
            xy8_block.append(tau_element)
            xy8_block.append(pix_element)
            xy8_block.append(tau_element)
            xy8_block.append(piy_element)
            xy8_block.append(tau_element)
            xy8_block.append(piy_element)
            xy8_block.append(tau_element)
            xy8_block.append(pix_element)
            xy8_block.append(tau_element)
            xy8_block.append(piy_element)
            xy8_block.append(tau_element)
            xy8_block.append(pix_element)
            if n != xy8_order - 1:
                xy8_block.append(tau_element)
        xy8_block.append(tauhalf_element)
        xy8_block.append(pihalf_element)
        xy8_block.append(laser_element)
        xy8_block.append(delay_element)
        xy8_block.append(waiting_element)
        if alternating:
            xy8_block.append(pihalf_element)
            xy8_block.append(tauhalf_element)
            for n in range(xy8_order):
                xy8_block.append(pix_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(pix_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(pix_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(pix_element)
                if n != xy8_order - 1:
                    xy8_block.append(tau_element)
            xy8_block.append(tauhalf_element)
            xy8_block.append(pi3half_element)
            xy8_block.append(laser_element)
            xy8_block.append(delay_element)
            xy8_block.append(waiting_element)
        created_blocks.append(xy8_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((xy8_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_dd_tau_scan(self, name='dd_tau_scan', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                             dd_type=DDMethods.XY8, dd_order=1, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        # calculate "real" start length of tau due to finite pi-pulse length
        real_start_tau = max(0, tau_start - self.rabi_period / 2)
        start_tau_pspacing = self.tau_2_pulse_spacing(tau_start)
        #self.log.debug("So far tau_start: {}, new: {}".format(real_start_tau, start_tau_pspacing))

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        # define a function to create phase shifted pi pulse elements
        def pi_element_function(xphase):
            return self._get_mw_element(length=self.rabi_period / 2,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=xphase)

        # Use a 180 deg phase shifted pulse as 3pihalf pulse if microwave channel is analog
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
        tauhalf_element = self._get_idle_element(length=start_tau_pspacing / 2, increment=tau_step / 2)
        tau_element = self._get_idle_element(length=start_tau_pspacing, increment=tau_step)


        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)
        dd_block.append(pihalf_element)
        for n in range(dd_order):
            # create the DD sequence for a single order
            for pulse_number in range(dd_type.suborder):
                dd_block.append(tauhalf_element)
                dd_block.append(pi_element_function(dd_type.phases[pulse_number]))
                dd_block.append(tauhalf_element)
        dd_block.append(pihalf_element)
        dd_block.append(laser_element)
        dd_block.append(delay_element)
        dd_block.append(waiting_element)
        if alternating:
            dd_block.append(pihalf_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element)
                    dd_block.append(pi_element_function(dd_type.phases[pulse_number]))
                    dd_block.append(tauhalf_element)
            dd_block.append(pi3half_element)
            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)
        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
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
        tau_pspacing_array = self.tau_2_pulse_spacing(tau_array)

        # old transformation to "real tau"
        real_tau_array = tau_array - self.rabi_period / 2
        np.clip(real_tau_array, 0, None, real_tau_array)

        # Convert back to frequency in order to account for clipped values
        freq_array_old = 1 / (2 * (real_tau_array + self.rabi_period / 2))
        freq_array = 1 / (2 * (self.tau_2_pulse_spacing(tau_pspacing_array, inverse=True)))

        self.log.debug("So far tau: {}, \nnew: {}".format(real_tau_array, tau_pspacing_array))
        self.log.debug("So far freq: {}, \nnew: {}".format(freq_array_old, freq_array))

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        # Use a 180 deg phase shifted pulse as 3pihalf pulse if microwave channel is analog
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
        for ii, tau in enumerate(tau_pspacing_array):
            tauhalf_element = self._get_idle_element(length=tau / 2, increment=0)
            tau_element = self._get_idle_element(length=tau, increment=0)
            xy8_block.append(pihalf_element)
            xy8_block.append(tauhalf_element)
            for n in range(xy8_order):
                xy8_block.append(pix_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(pix_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(pix_element)
                xy8_block.append(tau_element)
                xy8_block.append(piy_element)
                xy8_block.append(tau_element)
                xy8_block.append(pix_element)
                if n != xy8_order - 1:
                    xy8_block.append(tau_element)
            xy8_block.append(tauhalf_element)
            xy8_block.append(pihalf_element)
            xy8_block.append(laser_element)
            xy8_block.append(delay_element)
            xy8_block.append(waiting_element)
            if alternating:
                xy8_block.append(pihalf_element)
                xy8_block.append(tauhalf_element)
                for n in range(xy8_order):
                    xy8_block.append(pix_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(piy_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(pix_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(piy_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(piy_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(pix_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(piy_element)
                    xy8_block.append(tau_element)
                    xy8_block.append(pix_element)
                    if n != xy8_order - 1:
                        xy8_block.append(tau_element)
                xy8_block.append(tauhalf_element)
                xy8_block.append(pi3half_element)
                xy8_block.append(laser_element)
                xy8_block.append(delay_element)
                xy8_block.append(waiting_element)
        created_blocks.append(xy8_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((xy8_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_dd_freq_scan(self, name='dd_freq_scan', freq_start=0.1e6, freq_step=0.01e6, num_of_points=50,
                              dd_type=DDMethods.XY8, dd_order=1, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get frequency array for measurement ticks
        freq_array = freq_start + np.arange(num_of_points) * freq_step
        # get tau array from freq array
        tau_array = 1 / (2 * freq_array)
        tau_phys_array = self.tau_2_pulse_spacing(tau_array)

        # old transformation to "real tau"
        real_tau_array = tau_array - self.rabi_period / 2
        np.clip(real_tau_array, 0, None, real_tau_array)

        # Convert back to frequency in order to account for clipped values
        freq_array_old = 1 / (2 * (real_tau_array + self.rabi_period / 2))
        freq_array = 1 / (2 * (self.tau_2_pulse_spacing(tau_phys_array, inverse=True)))

        self.log.debug("So far tau: {}, \nnew: {}".format(real_tau_array, tau_phys_array))
        self.log.debug("So far freq: {}, \nnew: {}".format(freq_array_old, freq_array))

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)

        # define a function to create phase shifted pi pulse elements
        def pi_element_function(xphase):
            return self._get_mw_element(length=self.rabi_period / 2,
                                        increment=0,
                                        amp=self.microwave_amplitude,
                                        freq=self.microwave_frequency,
                                        phase=xphase)

        # Use a 180 deg phase shifted pulse as 3pihalf pulse if microwave channel is analog
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
        dd_block = PulseBlock(name=name)
        for ii, tau in enumerate(tau_phys_array):
            tauhalf_element = self._get_idle_element(length=tau / 2, increment=0)
            tau_element = self._get_idle_element(length=tau, increment=0)
            dd_block.append(pihalf_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element)
                    dd_block.append(pi_element_function(dd_type.phases[pulse_number]))
                    dd_block.append(tauhalf_element)
            dd_block.append(pihalf_element)
            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)
            if alternating:
                dd_block.append(pihalf_element)
                for n in range(dd_order):
                    # create the DD sequence for a single order
                    for pulse_number in range(dd_type.suborder):
                        dd_block.append(tauhalf_element)
                        dd_block.append(pi_element_function(dd_type.phases[pulse_number]))
                        dd_block.append(tauhalf_element)
                dd_block.append(pi3half_element)
                dd_block.append(laser_element)
                dd_block.append(delay_element)
                dd_block.append(waiting_element)
        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    ################################################################################################
    #                             Generation methods for sequences                                 #
    ################################################################################################
