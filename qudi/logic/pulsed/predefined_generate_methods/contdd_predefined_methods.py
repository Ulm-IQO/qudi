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

    def generate_HH_Phase(self, name='HH_Phase', amp_hh=0.5, freq_hahn=0.1e6, freq_step=0.01e6,
                          num_of_points=50, xy8_order=4, alternating=True):
        """
        Continuous dynamical decoupling with XY8 like phase changes, x-axis - frequency
        freq_hahn and freq_step relate to the time between phase changes
        amp_hh is the amplitude for the continuous drive, Rabi freq should be around the middle of the frequency range
        xy8_order relates to the number of repetitions in the same manner to the standard xy8 sequence
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get amplitude array for measurement ticks
        freq_array = freq_hahn + np.arange(num_of_points) * freq_step

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

        # Create block and append to created_blocks list
        HH_Phase = PulseBlock(name=name)
        for freq_hh in freq_array:
            hahn_period = 1 / (2 * freq_hh)
            pix_element = self._get_mw_element(length=hahn_period / 1,
                                               increment=0,
                                               amp=amp_hh,
                                               freq=self.microwave_frequency,
                                               phase=0)
            piy_element = self._get_mw_element(length=hahn_period / 1,
                                               increment=0,
                                               amp=amp_hh,
                                               freq=self.microwave_frequency,
                                               phase=90)
            HH_Phase.append(pihalf_element)
            for n in range(xy8_order):
                HH_Phase.append(pix_element)
                HH_Phase.append(piy_element)
                HH_Phase.append(pix_element)
                HH_Phase.append(piy_element)
                HH_Phase.append(piy_element)
                HH_Phase.append(pix_element)
                HH_Phase.append(piy_element)
                HH_Phase.append(pix_element)
            HH_Phase.append(pihalf_element)
            HH_Phase.append(laser_element)
            HH_Phase.append(delay_element)
            HH_Phase.append(waiting_element)

            if alternating:
                HH_Phase.append(pi3half_element)
                for n in range(xy8_order):
                    HH_Phase.append(pix_element)
                    HH_Phase.append(piy_element)
                    HH_Phase.append(pix_element)
                    HH_Phase.append(piy_element)
                    HH_Phase.append(piy_element)
                    HH_Phase.append(pix_element)
                    HH_Phase.append(piy_element)
                    HH_Phase.append(pix_element)
                HH_Phase.append(pihalf_element)
                HH_Phase.append(laser_element)
                HH_Phase.append(delay_element)
                HH_Phase.append(waiting_element)
        created_blocks.append(HH_Phase)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((HH_Phase.name, 0))

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

    def generate_HH_Phase_N(self, name='HH_Phase_N', amp_hh=0.05, freq_hahn=0.1e6,
                            num_of_points=50, xy8_order_start=4, order_step=1, alternating=True):
        """
        Continuous dynamical decoupling with XY8 like phase changes, x- axis XY8 - order
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get amplitude array for measurement ticks
        order_array = xy8_order_start + np.arange(num_of_points) * order_step
        hahn_period = 1 / (2 * freq_hahn)

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

        pix_element = self._get_mw_element(length=hahn_period / 1,
                                           increment=0,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=0)
        piy_element = self._get_mw_element(length=hahn_period / 1,
                                           increment=0,
                                           amp=amp_hh,
                                           freq=self.microwave_frequency,
                                           phase=90)

        # Create block and append to created_blocks list
        HH_Phase = PulseBlock(name=name)
        for xy8_order in order_array:
            HH_Phase.append(pihalf_element)
            for n in range(xy8_order):
                HH_Phase.append(pix_element)
                HH_Phase.append(piy_element)
                HH_Phase.append(pix_element)
                HH_Phase.append(piy_element)
                HH_Phase.append(piy_element)
                HH_Phase.append(pix_element)
                HH_Phase.append(piy_element)
                HH_Phase.append(pix_element)
            HH_Phase.append(pihalf_element)
            HH_Phase.append(laser_element)
            HH_Phase.append(delay_element)
            HH_Phase.append(waiting_element)

            HH_Phase.append(pi3half_element)
            if alternating:
                for n in range(xy8_order):
                    HH_Phase.append(pix_element)
                    HH_Phase.append(piy_element)
                    HH_Phase.append(pix_element)
                    HH_Phase.append(piy_element)
                    HH_Phase.append(piy_element)
                    HH_Phase.append(pix_element)
                    HH_Phase.append(piy_element)
                    HH_Phase.append(pix_element)
                HH_Phase.append(pihalf_element)
                HH_Phase.append(laser_element)
                HH_Phase.append(delay_element)
                HH_Phase.append(waiting_element)
        created_blocks.append(HH_Phase)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((HH_Phase.name, 0))

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

    def generate_rot_echo(self, name='rot_echo', amp_hh=0.05, freq_hahn=0.1e6, freq_step=0.01e6,
                          num_of_points=50, order=4, alternating=True):
        """
        Rotary echo - continuous dynamical decoupling with 0/180 phase changes, x-axis is frequency
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get amplitude array for measurement ticks
        freq_array = freq_hahn + np.arange(num_of_points) * freq_step

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

        # Create block and append to created_blocks list
        rot_echo = PulseBlock(name=name)
        for freq_hh in freq_array:
            hahn_period = 1 / (2 * freq_hh)
            pix_element = self._get_mw_element(length=hahn_period / 1,
                                               increment=0,
                                               amp=amp_hh,
                                               freq=self.microwave_frequency,
                                               phase=0)
            piy_element = self._get_mw_element(length=hahn_period / 1,
                                               increment=0,
                                               amp=amp_hh,
                                               freq=self.microwave_frequency,
                                               phase=180)
            rot_echo.append(pihalf_element)
            for n in range(order):
                rot_echo.append(pix_element)
                rot_echo.append(piy_element)
            rot_echo.append(pihalf_element)
            rot_echo.append(laser_element)
            rot_echo.append(delay_element)
            rot_echo.append(waiting_element)

            rot_echo.append(pi3half_element)
            if alternating:
                for n in range(order):
                    rot_echo.append(pix_element)
                    rot_echo.append(piy_element)
                rot_echo.append(pihalf_element)
                rot_echo.append(laser_element)
                rot_echo.append(delay_element)
                rot_echo.append(waiting_element)
        created_blocks.append(rot_echo)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((rot_echo.name, 0))

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

    def generate_rot_echo_tau(self, name='rot_echo_tau', amp_hh=0.05, freq_hahn=0.1e6, order_step=1,
                              num_of_points=50, order_start=4, alternating=True):
        """
        Rotary echo - continuous dynamical decoupling with 0/180 phase changes, x-axis is sequence length
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get amplitude array for measurement ticks
        step_array = order_start + np.arange(num_of_points) * order_step

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

        # Create block and append to created_blocks list
        rot_echo_tau = PulseBlock(name=name)
        for step in step_array:
            hahn_period = 1 / (2 * freq_hahn)
            pix_element = self._get_mw_element(length=hahn_period / 1,
                                               increment=0,
                                               amp=amp_hh,
                                               freq=self.microwave_frequency,
                                               phase=0)
            piy_element = self._get_mw_element(length=hahn_period / 1,
                                               increment=0,
                                               amp=amp_hh,
                                               freq=self.microwave_frequency,
                                               phase=180)
            rot_echo_tau.append(pihalf_element)
            for n in range(step):
                rot_echo_tau.append(pix_element)
                rot_echo_tau.append(piy_element)
            rot_echo_tau.append(pihalf_element)
            rot_echo_tau.append(laser_element)
            rot_echo_tau.append(delay_element)
            rot_echo_tau.append(waiting_element)

            rot_echo_tau.append(pi3half_element)
            if alternating:
                for n in range(step):
                    rot_echo_tau.append(pix_element)
                    rot_echo_tau.append(piy_element)
                rot_echo_tau.append(pihalf_element)
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
        block_ensemble.measurement_information['controlled_variable'] = step_array
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('order', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences
