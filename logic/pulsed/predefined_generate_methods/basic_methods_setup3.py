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
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase


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


class BasicPredefinedGeneratorS3(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_ramsey_from_list_s3(self, name='ramsey', tau_list='[1e-6, 2e-6]', alternating = True):
        """

        """

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = [n.strip() for n in tau_list]

        # get readout element
        readout_element = self._get_readout_element()

        # get pihalf element
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0.0)

        if alternating:
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
        block = PulseBlock(name=name)
        for tau in tau_array:
            block.append(pihalf_element)
            tau_element = self._get_idle_element(length=tau, increment=0)
            block.append(tau_element)
            block.append(tau_element)
            block.append(pihalf_element)
            block.extend(readout_element)

            if alternating:
                block.append(pihalf_element)
                block.append(tau_element)
                block.append(pi3half_element)
                block.extend(readout_element)

        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=alternating,
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_t1_s3(self, name='T1', tau_start=1.0e-6, tau_step=1.0e-6,
                    num_of_points=50, alternating = False):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # get readout element
        readout_element = self._get_readout_element()

        if alternating: # get pi element
            pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)

        tau_element = self._get_idle_element(length=tau_start, increment=tau_step)
        block = PulseBlock(name=name)
        block.append(tau_element)
        block.extend(readout_element)
        if alternating:
            block.append(pi_element)
            block.append(tau_element)
            block.extend(readout_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=alternating,
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_t1_exponential_s3(self, name='T1_exp', tau_start=1.0e-6, tau_end=1.0e-6,
                    num_of_points=50, alternating=False):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        if tau_start == 0.0:
            tau_array = np.geomspace(1e-9, tau_end, num_of_points - 1)
            tau_array = np.insert(tau_array, 0, 0.0)
        else:
            tau_array = np.geomspace(tau_start, tau_end, num_of_points)

        # get readout element
        readout_element = self._get_readout_element()

        if alternating:  # get pi element
            pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        block = PulseBlock(name=name)
        for tau in tau_array:
            tau_element = self._get_idle_element(length=tau, increment=0.0)
            block.append(tau_element)
            block.extend(readout_element)
            if alternating:
                block.append(pi_element)
                block.append(tau_element)
                block.extend(readout_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=alternating,
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_hahnecho_exp_s3(self, name='hahn_echo', tau_start=1.0e-6, tau_end=10.0e-6,
                          num_of_points=50, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        if tau_start == 0.0:
            tau_array = np.geomspace(1e-9, tau_end, num_of_points - 1)
            tau_array = np.insert(tau_array, 0, 0.0)
        else:
            tau_array = np.geomspace(tau_start, tau_end, num_of_points)

        # get readout element
        readout_element = self._get_readout_element()

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


        # Create block and append to created_blocks list
        block = PulseBlock(name=name)
        for tau in tau_array:
            tau_element = self._get_idle_element(length=tau, increment=0.0)
            block.append(pihalf_element)
            block.append(tau_element)
            block.append(pi_element)
            block.append(tau_element)
            block.append(pihalf_element)
            block.extend(readout_element)
            if alternating:
                block.append(pihalf_element)
                block.append(tau_element)
                block.append(pi_element)
                block.append(tau_element)
                block.append(pi3half_element)
                block.extend(readout_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=alternating,
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    def generate_hahnecho_s3(self, name='hahn_echo', tau_start=1.0e-6, tau_step=1.0e-6,
                          num_of_points=50, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # get readout element
        readout_element = self._get_readout_element()

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
        block = PulseBlock(name=name)
        block.append(pihalf_element)
        block.append(tau_element)
        block.append(pi_element)
        block.append(tau_element)
        block.append(pihalf_element)
        block.extend(readout_element)
        if alternating:
            block.append(pihalf_element)
            block.append(tau_element)
            block.append(pi_element)
            block.append(tau_element)
            block.append(pi3half_element)
            block.extend(readout_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=alternating,
                                                        controlled_variable=tau_array)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    def generate_xy8_tau_s3(self, name='xy8_tau', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
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

        # get readout element
        readout_element = self._get_readout_element()
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
        block = PulseBlock(name=name)
        block.append(pihalf_element)
        block.append(tauhalf_element)
        for n in range(xy8_order):
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pix_element)
            if n != xy8_order - 1:
                block.append(tau_element)
        block.append(tauhalf_element)
        block.append(pihalf_element)
        block.extend(readout_element)
        if alternating:
            block.append(pihalf_element)
            block.append(tauhalf_element)
            for n in range(xy8_order):
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pix_element)
                if n != xy8_order - 1:
                    block.append(tau_element)
            block.append(tauhalf_element)
            block.append(pi3half_element)
            block.extend(readout_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=alternating,
                                                        controlled_variable=tau_array)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences




    def generate_rabi_DTG(self, name='Rabi_dtg', tau_start=1e-9, tau_step=1e-9, num_of_points=50,
                          seq_trig='d_ch1', shorten_record=300e-9):
        """
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # get MW element (here just DC trigger)
        mw_element = self._get_trigger_element(length=tau_start, increment=tau_step,  channels=seq_trig)
        # get readout element
        readout_element = self._get_readout_element()
        block = PulseBlock(name=name)
        # Create element list for Rabi PulseBlock
        block.append(mw_element)
        block.extend(readout_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, num_of_points-1))

        # add metadata to invoke settings
        sequence_length = self._get_ensemble_count_length(ensemble=block_ensemble, created_blocks=created_blocks)
        block_ensemble = \
            self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False,
                                                        controlled_variable=tau_array,
                                                        counting_length=sequence_length-shorten_record)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_rabi_alternating(self, name='rabi', tau_start=10.0e-9, tau_step=10.0e-9, num_of_points=50):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the laser_mw element
        mw_element = self._get_mw_element(length=tau_start,
                                          increment=tau_step,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0)
        mw_element_strong = self._get_mw_element(length=42e-9/2,
                                          increment=0,
                                          amp=0.25,
                                          freq=4.1262e9+3.03e6/2,
                                          phase=0)
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        rabi_block.append(mw_element_strong)
        rabi_block.append(mw_element)
        rabi_block.append(laser_element)
        rabi_block.append(delay_element)
        rabi_block.append(waiting_element)



        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((rabi_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = True
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences













