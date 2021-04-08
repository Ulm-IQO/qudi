# -*- coding: utf-8 -*-

"""
This file contains the Qudi Predefined Methods for continuous dynamical decoupling sequences

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



class ContDDPredefinedGenerator(PredefinedGeneratorBase):
    """

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_HHphase_tau(self, name='HH_Phase', amp_hh=0.5, tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                             xy8_order=4, alternating=True):
        """
        Continuous dynamical decoupling with XY8 like phase changes.
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
        pix_element = self._get_mw_element(length=tau_start,
                                           increment=tau_step,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=0)
        piy_element = self._get_mw_element(length=tau_start,
                                           increment=tau_step,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=90)
        # Create block and append to created_blocks list
        hhphase_block = PulseBlock(name=name)
        hhphase_block.append(pihalf_element)
        for n in range(xy8_order):
            hhphase_block.append(pix_element)
            hhphase_block.append(piy_element)
            hhphase_block.append(pix_element)
            hhphase_block.append(piy_element)
            hhphase_block.append(piy_element)
            hhphase_block.append(pix_element)
            hhphase_block.append(piy_element)
            hhphase_block.append(pix_element)
        hhphase_block.append(pihalf_element)
        hhphase_block.append(laser_element)
        hhphase_block.append(delay_element)
        hhphase_block.append(waiting_element)
        if alternating:
            hhphase_block.append(pihalf_element)
            for n in range(xy8_order):
                hhphase_block.append(pix_element)
                hhphase_block.append(piy_element)
                hhphase_block.append(pix_element)
                hhphase_block.append(piy_element)
                hhphase_block.append(piy_element)
                hhphase_block.append(pix_element)
                hhphase_block.append(piy_element)
                hhphase_block.append(pix_element)
            hhphase_block.append(pi3half_element)
            hhphase_block.append(laser_element)
            hhphase_block.append(delay_element)
            hhphase_block.append(waiting_element)
        created_blocks.append(hhphase_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((hhphase_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_HHphase_N(self, name='HH_Phase_N', amp_hh=0.05, tau=0.5e-6, order_start=4, order_step=1,
                           num_of_points=50, alternating=True):
        """
        Continuous dynamical decoupling with XY8 like phase changes.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get order array
        order_array = order_start + np.arange(num_of_points) * order_step

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
        pix_element = self._get_mw_element(length=tau,
                                           increment=0,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=0)
        piy_element = self._get_mw_element(length=tau,
                                           increment=0,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=90)

        # Create block and append to created_blocks list
        hhphase_block = PulseBlock(name=name)
        for xy8_order in order_array:
            hhphase_block.append(pihalf_element)
            for n in range(xy8_order):
                hhphase_block.append(pix_element)
                hhphase_block.append(piy_element)
                hhphase_block.append(pix_element)
                hhphase_block.append(piy_element)
                hhphase_block.append(piy_element)
                hhphase_block.append(pix_element)
                hhphase_block.append(piy_element)
                hhphase_block.append(pix_element)
            hhphase_block.append(pihalf_element)
            hhphase_block.append(laser_element)
            hhphase_block.append(delay_element)
            hhphase_block.append(waiting_element)
            if alternating:
                hhphase_block.append(pihalf_element)
                for n in range(xy8_order):
                    hhphase_block.append(pix_element)
                    hhphase_block.append(piy_element)
                    hhphase_block.append(pix_element)
                    hhphase_block.append(piy_element)
                    hhphase_block.append(piy_element)
                    hhphase_block.append(pix_element)
                    hhphase_block.append(piy_element)
                    hhphase_block.append(pix_element)
                hhphase_block.append(pi3half_element)
                hhphase_block.append(laser_element)
                hhphase_block.append(delay_element)
                hhphase_block.append(waiting_element)
        created_blocks.append(hhphase_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((hhphase_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = order_array
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('HHXY8 order', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_rot_echo_tau(self, name='rot_echo', amp_hh=0.05, tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                              order=4, alternating=True):
        """
        Rotary echo - continuous dynamical decoupling with 0/180 phase changes.
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
        pix_element = self._get_mw_element(length=tau_start,
                                           increment=tau_step,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=0)
        piy_element = self._get_mw_element(length=tau_start,
                                           increment=tau_step,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=180)

        # Create block and append to created_blocks list
        rotecho_block = PulseBlock(name=name)
        rotecho_block.append(pihalf_element)
        for n in range(order):
            rotecho_block.append(pix_element)
            rotecho_block.append(piy_element)
        rotecho_block.append(pihalf_element)
        rotecho_block.append(laser_element)
        rotecho_block.append(delay_element)
        rotecho_block.append(waiting_element)
        if alternating:
            rotecho_block.append(pihalf_element)
            for n in range(order):
                rotecho_block.append(pix_element)
                rotecho_block.append(piy_element)
            rotecho_block.append(pi3half_element)
            rotecho_block.append(laser_element)
            rotecho_block.append(delay_element)
            rotecho_block.append(waiting_element)
        created_blocks.append(rotecho_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((rotecho_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_rot_echo_N(self, name='rot_echo_N', amp_hh=0.05, tau=0.5e-6, order_start=4, order_step=1,
                            num_of_points=50, alternating=True):
        """
        Rotary echo - continuous dynamical decoupling with 0/180 phase changes.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get order array
        order_array = order_start + np.arange(num_of_points) * order_step

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
        pix_element = self._get_mw_element(length=tau,
                                           increment=0,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=0)
        piy_element = self._get_mw_element(length=tau,
                                           increment=0,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=180)
        # Create block and append to created_blocks list
        rot_echo_tau = PulseBlock(name=name)
        for order in order_array:
            rot_echo_tau.append(pihalf_element)
            for n in range(order):
                rot_echo_tau.append(pix_element)
                rot_echo_tau.append(piy_element)
            rot_echo_tau.append(pihalf_element)
            rot_echo_tau.append(laser_element)
            rot_echo_tau.append(delay_element)
            rot_echo_tau.append(waiting_element)
            if alternating:
                rot_echo_tau.append(pihalf_element)
                for n in range(order):
                    rot_echo_tau.append(pix_element)
                    rot_echo_tau.append(piy_element)
                rot_echo_tau.append(pi3half_element)
                rot_echo_tau.append(laser_element)
                rot_echo_tau.append(delay_element)
                rot_echo_tau.append(waiting_element)
        created_blocks.append(rot_echo_tau)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((rot_echo_tau.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = order_array
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('order', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences
