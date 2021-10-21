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
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from logic.pulsed.sampling_functions import SamplingFunctions
from logic.pulsed.predefined_generate_methods.helper_methods_setup3 import HelperMethods

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


class BasicPolarisationGenerator(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    ################################################################################################
    #                             Generation methods for waveforms                                 #
    ################################################################################################

    def generate_HHamp_s3(self, name='hh_amp', spinlock_length=20e-6, amp_start=0.05, amp_step=0.01,
                          num_of_points=50, alternating=True):
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
            hhamp_block.append(pihalf_element)
            hhamp_block.append(sl_element)
            hhamp_block.append(pihalf_element)
            hhamp_block.append(laser_element)
            hhamp_block.append(delay_element)
            hhamp_block.append(waiting_element)

            if alternating:
                hhamp_block.append(pi3half_element)
                hhamp_block.append(sl_element)
                hhamp_block.append(pihalf_element)
                hhamp_block.append(laser_element)
                hhamp_block.append(delay_element)
                hhamp_block.append(waiting_element)
        created_blocks.append(hhamp_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((hhamp_block.name, 0))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = amp_array
        block_ensemble.measurement_information['units'] = ('V', '')
        block_ensemble.measurement_information['labels'] = ('MW amplitude', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_HHtau_s3(self, name='hh_tau', spinlock_amp=0.1, tau_start=1e-6, tau_step=1e-6,
                       num_of_points=50, alternating=True):
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
        hhtau_block.append(pihalf_element)
        hhtau_block.append(sl_element)
        hhtau_block.append(pihalf_element)
        hhtau_block.append(laser_element)
        hhtau_block.append(delay_element)
        hhtau_block.append(waiting_element)

        if alternating:
            hhtau_block.append(pi3half_element)
            hhtau_block.append(sl_element)
            hhtau_block.append(pihalf_element)
            hhtau_block.append(laser_element)
            hhtau_block.append(delay_element)
            hhtau_block.append(waiting_element)
        created_blocks.append(hhtau_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((hhtau_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Spinlock time', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_HHrepetitive(self, name='hh_rep', spinlock_amp=0.1, spinlock_length=25e-6,
                              num_of_points=50, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        readout_array = 1+ np.arange(2*num_of_points) if alternating else 1+ np.arange(num_of_points)

        # create the elements
        # get readout element
        readout_element = self._get_trigger_readout_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)

        pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                               increment=0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=180)

        sl_element = self._get_mw_element(length=spinlock_length,
                                          increment=0,
                                          amp=spinlock_amp,
                                          freq=self.microwave_frequency,
                                          phase=90)

        # Create block and append to created_blocks list
        block = PulseBlock(name=name)
        block.append(pihalf_element)
        block.append(sl_element)
        block.append(pihalf_element)
        block.extend(readout_element)

        created_blocks.append(block)
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))
        created_ensembles.append(block_ensemble)
        seq_param = self._customize_seq_para({'repetitions': num_of_points-1})
        hmh_list = [block.name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        element_list.append(hmh_list.copy())

        if alternating:
            block = PulseBlock(name=name+'_alt')
            block.append(pi3half_element)
            block.append(sl_element)
            block.append(pihalf_element)
            block.extend(readout_element)

            created_blocks.append(block)
            block_ensemble = PulseBlockEnsemble(name=name+'_alt', rotating_frame=True)
            block_ensemble.append((block.name, 0))
            created_ensembles.append(block_ensemble)
            seq_param = self._customize_seq_para({'repetitions': num_of_points - 1})
            hmh_alt_list = [block.name, seq_param]
            element_list.append(hmh_alt_list.copy())

        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)

        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False,
                                       laser_ignore_list=list(),
                                       controlled_variable=readout_array, units=('#', 'a.u.'),
                                       labels=('Cycles', 'Signal'),
                                       number_of_lasers=2 * num_of_points if alternating else num_of_points,
                                       counting_length=self.laser_length * 1.4)

        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_Poltau(self, name='PPol_tau', tau_start=0.5e-6, tau_step=0.01e-6,
                        num_of_points=50,
                        order=8, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        microwave_amplitude = self.microwave_amplitude
        microwave_frequency = self.microwave_frequency
        rabi_period = self.rabi_period
        """"
        rabi_period = self._adjust_to_samplingrate(rabi_period, 8)
        start_tau = self._adjust_to_samplingrate(tau_start, 4)
        incr_tau = self._adjust_to_samplingrate(tau_step, 4)
        """
        # get tau array for measurement ticks
        start_tau, incr_tau = tau_start, tau_step
        tau_array = start_tau + np.arange(num_of_points) * incr_tau

        if start_tau / 4.0 - rabi_period / 2.0 < 0.0:
            self.log.error('Pol 2.0 generation failed! Rabi period of {0:.3e} s is too long for start tau '
                           'of {1:.3e} s.'.format(rabi_period, start_tau))
            return

        # get readout element
        readout_element = self._get_readout_element()

        # get -x pihalf element
        pihalfminusx_element = self._get_mw_element(length=rabi_period / 4., increment=0.0,
                                                       amp=microwave_amplitude, freq=microwave_frequency,
                                                       phase=180.0)


        pihalfx_element = self._get_mw_element(length=rabi_period / 4., increment=0.0,
                                                  amp=microwave_amplitude, freq=microwave_frequency,
                                                  phase=0.0)

        # get y pihalf element
        pihalfy_element = self._get_mw_element(length=rabi_period / 4.,
                                                  increment=0.0,
                                                  amp=microwave_amplitude,
                                                  freq=microwave_frequency,
                                                  phase=90.0)
        # get pi elements
        pix_element = self._get_mw_element(length=rabi_period / 2.,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0)
        # get pi elements
        piminusx_element = self._get_mw_element(length=rabi_period / 2.,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=180.0)

        piy_element = self._get_mw_element(length=rabi_period / 2.,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=90.0)
        # get tau/4 element
        tau_element = self._get_idle_element(length=start_tau / 4.0 - rabi_period / 2, increment=incr_tau / 4)

        # create Pol 2.0 block element list
        block = PulseBlock(name=name)
        # actual (Pol 2.0)_2N sequence
        for nn in range(2 * order):
            block.append(pihalfminusx_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pihalfminusx_element)

            block.append(pihalfy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(pihalfy_element)
        block.extend(readout_element)

        if alternating:
            for pp in range(2 * order):
                block.append(pihalfy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pihalfy_element)

                block.append(pihalfminusx_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pihalfminusx_element)

            block[-1] = pihalfx_element
            block.extend(readout_element)

        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating, units=('s', ''),
                                                        labels=('tau', 'Signal'),
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences

    def generate_Poltau2(self, name='PolTau_0.1', tau_start=0.5e-6, tau_step=0.01e-6,
                         num_of_points=50, order=8, alternating=True):
        """

        """

        microwave_amplitude = self.microwave_amplitude
        microwave_frequency = self.microwave_frequency
        rabi_period = self.rabi_period

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        rabi_period = self._adjust_to_samplingrate(rabi_period, 8)
        start_tau = self._adjust_to_samplingrate(tau_start, 4)
        incr_tau = self._adjust_to_samplingrate(tau_step, 4)
        # get tau array for measurement ticks
        tau_array = start_tau + np.arange(num_of_points) * incr_tau

        if start_tau / 4.0 - rabi_period / 2.0 < 0.0:
            self.log.error('Pol 2.0 generation failed! Rabi period of {0:.3e} s is too long for start tau '
                           'of {1:.3e} s.'.format(rabi_period, start_tau))
            return

        # get readout element
        readout_element = self._get_readout_element()

        # get -x pihalf element
        pihalfy_element = self._get_mw_element(length=rabi_period / 4., increment=0.0,
                                                  amp=microwave_amplitude, freq=microwave_frequency,
                                                  phase=90.0)

        pihalfminusy_element = self._get_mw_element(length=rabi_period / 4., increment=0.0,
                                                  amp=microwave_amplitude, freq=microwave_frequency,
                                                  phase=270.0)

        pihalfx_element = self._get_mw_element(length=rabi_period / 4., increment=0.0,
                                                  amp=microwave_amplitude, freq=microwave_frequency,
                                                  phase=0.0)

        # get pi elements
        pix_element = self._get_mw_element(length=rabi_period / 2.,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0)


        piy_element = self._get_mw_element(length=rabi_period / 2.,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=90.0)
        # get tau/4 element
        tau_element = self._get_idle_element(length=start_tau / 4.0 - rabi_period / 2, increment=incr_tau / 4)

        # create Pol 2.0 block element list
        block = PulseBlock(name=name)
        # actual (Pol 2.0)_2N sequence
        # ATTENTION: phases not as in Schwartz paper
        for nn in range(2 * order):
            block.append(pihalfy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(pihalfy_element)

            block.append(pihalfx_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pihalfx_element)
        block.extend(readout_element)

        if alternating:
            # reverse polarization
            for pp in range(2 * order):
                block.append(pihalfx_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pihalfx_element)

                block.append(pihalfy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pihalfy_element)

            block[-1] = pihalfminusy_element  # for nv readout contrast
            block.extend(readout_element)

        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating, units=('s', ''),
                                                        labels=('tau', 'Signal'),
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences


    def generate_Pol20_polarize(self, name='Pol 2.0_down', rabi_period=0.1e-6, tau_start=0.5e-6, tau_step=0.01e-6,
                                num_of_points=50, microwave_amplitude=0.25, microwave_frequency=2.87e9,
                                order=8, direction='down', alternating=True, pulse_function='Sin'):
        """

        """

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        rabi_period = self._adjust_to_samplingrate(rabi_period, 8)
        start_tau = self._adjust_to_samplingrate(tau_start, 4)
        incr_tau = self._adjust_to_samplingrate(tau_step, 4)
        # get tau array for measurement ticks
        tau_array = start_tau + np.arange(num_of_points) * incr_tau

        if start_tau / 4.0 - rabi_period / 2.0 < 0.0:
            self.log.error('Pol 2.0 generation failed! Rabi period of {0:.3e} s is too long for start tau '
                           'of {1:.3e} s.'.format(rabi_period, start_tau))
            return

        # get readout element
        readout_element = self._get_readout_element()

        # get -x pihalf element
        pihalfminusx_element = self._get_mw_element_s3(length=rabi_period / 4, increment=0.0,
                                                       amp=microwave_amplitude, freq=microwave_frequency,
                                                       phase=180.0, pulse_function=pulse_function)

        # get y pihalf element
        pihalfy_element = self._get_mw_element_s3(length=rabi_period / 4,
                                                  increment=0.0,
                                                  amp=microwave_amplitude,
                                                  freq=microwave_frequency,
                                                  phase=90.0,
                                                  pulse_function=pulse_function)
        # get pi elements
        pix_element = self._get_mw_element_s3(length=rabi_period / 2,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0,
                                              pulse_function=pulse_function)

        piy_element = self._get_mw_element_s3(length=rabi_period / 2,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=90.0,
                                              pulse_function=pulse_function)
        # get tau/4 element
        tau_element = self._get_idle_element(length=start_tau / 4.0 - rabi_period / 2, increment=incr_tau / 4)

        block = PulseBlock(name=name)
        # actual (Pol 2.0)_2N sequence
        if direction == 'up':
            for n in range(2 * order):
                block.append(pihalfminusx_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pihalfminusx_element)

                block.append(pihalfy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pihalfy_element)

        if direction == 'down':
            for n in range(2 * order):
                block.append(pihalfy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pihalfy_element)

                block.append(pihalfminusx_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pihalfminusx_element)

        block.extend(readout_element)

        if alternating:
            if direction == 'up':
                for n in range(2 * order):
                    block.append(pihalfminusx_element)
                    block.append(tau_element)
                    block.append(piy_element)
                    block.append(tau_element)
                    block.append(pihalfminusx_element)

                    block.append(pihalfy_element)
                    block.append(tau_element)
                    block.append(pix_element)
                    block.append(tau_element)
                    block.append(pihalfy_element)

            if direction == 'down':
                for n in range(2 * order):
                    block.append(pihalfy_element)
                    block.append(tau_element)
                    block.append(pix_element)
                    block.append(tau_element)
                    block.append(pihalfy_element)

                    block.append(pihalfminusx_element)
                    block.append(tau_element)
                    block.append(piy_element)
                    block.append(tau_element)
                    block.append(pihalfminusx_element)

            block.append(pix_element)
            block.extend(readout_element)

        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating, units=('s', ''),
                                                        labels=('tau', 'Signal'),
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_Pol20_order(self, name='PPol order', n_start=1, n_step=1, num_of_points=50, tau=0.5e-6,
                             alternating = False):
        """

        """

        microwave_amplitude = self.microwave_amplitude
        microwave_frequency = self.microwave_frequency
        rabi_period = self.rabi_period

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get pulse number array for measurement ticks
        n_array = n_start + np.arange(num_of_points) * n_step
        n_array.astype(int)
        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
        tau = self._adjust_to_samplingrate(tau, 2)

        # get readout element
        readout_element = self._get_readout_element()

        # get -x pihalf element
        pihalfminusx_element = self._get_mw_element(length=rabi_period / 4, increment=0.0,
                                                    amp=microwave_amplitude, freq=microwave_frequency,
                                                    phase=180.0)
        pihalfx_element = self._get_mw_element(length=rabi_period / 4, increment=0.0,
                                               amp=microwave_amplitude, freq=microwave_frequency,
                                               phase=0.0)

        # get y pihalf element
        pihalfy_element = self._get_mw_element(length=rabi_period / 4,
                                               increment=0.0,
                                               amp=microwave_amplitude,
                                               freq=microwave_frequency,
                                               phase=90.0)
        # get pi elements
        pix_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=0.0)

        piy_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=microwave_amplitude,
                                           freq=microwave_frequency,
                                           phase=90.0)

        # get tau/4 element
        tau_element = self._get_idle_element(length=tau / 4 - rabi_period / 2.0, increment=0.)

        block = PulseBlock(name=name)
        for order in n_array:
            for nn in range(2 * order):
                block.append(pihalfminusx_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pihalfminusx_element)

                block.append(pihalfy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pihalfy_element)

            block.extend(readout_element)

            for nn in range(2 * order):
                block.append(pihalfy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pihalfy_element)

                block.append(pihalfminusx_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pihalfminusx_element)

            block[-1] = pihalfx_element
            block.extend(readout_element)



        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=True, units=('#', ''),
                                                        labels=('PulsePol order', 'Signal'),
                                                        controlled_variable=n_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences

    def generate_POLrepetitive(self, name='PolRep', rabi_period=0.1e-6, order=10, num_of_points=50,
                               microwave_amplitude=0.25, microwave_frequency=2.8e9, tau=0.5e-6,
                               alternating = True, pulse_function='Sin'):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get pulse number array for measurement ticks
        readout_array = 1+np.arange(2*num_of_points) if alternating else 1+np.arange(num_of_points)

        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
        tau = self._adjust_to_samplingrate(tau, 2)

        # get readout element
        readout_element = self._get_trigger_readout_element()

        # get -x pihalf element
        pihalfminusx_element = self._get_mw_element_s3(length=rabi_period / 4, increment=0.0,
                                                       amp=microwave_amplitude, freq=microwave_frequency,
                                                       phase=180.0)
        pihalfx_element = self._get_mw_element_s3(length=rabi_period / 4, increment=0.0,
                                                  amp=microwave_amplitude, freq=microwave_frequency,
                                                  phase=0.0)

        # get y pihalf element
        pihalfy_element = self._get_mw_element_s3(length=rabi_period / 4,
                                                  increment=0.0,
                                                  amp=microwave_amplitude,
                                                  freq=microwave_frequency,
                                                  phase=90.0,
                                                  pulse_function=pulse_function)
        # get pi elements
        pix_element = self._get_mw_element_s3(length=rabi_period / 2,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0,
                                              pulse_function=pulse_function)

        piy_element = self._get_mw_element_s3(length=rabi_period / 2,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=90.0,
                                              pulse_function=pulse_function)

        # get tau/4 element
        tau_element = self._get_idle_element(length=tau / 4 - rabi_period / 2.0, increment=0.)

        block = PulseBlock(name=name)
        for nn in range(2 * order):
            block.append(pihalfminusx_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pihalfminusx_element)

            block.append(pihalfy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(pihalfy_element)

        block.extend(readout_element)
        created_blocks.append(block)
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))
        created_ensembles.append(block_ensemble)
        seq_param = self._customize_seq_para({'repetitions': num_of_points - 1})
        pol_list = [block.name, seq_param]
        element_list = list()
        element_list.append(pol_list.copy())

        if alternating:
            block = PulseBlock(name=name+'_alt')
            for nn in range(2 * order):
                block.append(pihalfy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pihalfy_element)

                block.append(pihalfminusx_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pihalfminusx_element)

            block[-1] = pihalfx_element
            block.extend(readout_element)

            created_blocks.append(block)
            block_ensemble = PulseBlockEnsemble(name=name + '_alt', rotating_frame=True)
            block_ensemble.append((block.name, 0))
            created_ensembles.append(block_ensemble)
            seq_param = self._customize_seq_para({'repetitions': num_of_points - 1})
            pol_alt_list = [block.name, seq_param]
            element_list.append(pol_alt_list.copy())

        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)

        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False,
                                       laser_ignore_list=list(),
                                       controlled_variable=readout_array, units=('#', 'a.u.'),
                                       labels=('Cycles', 'Signal'),
                                       number_of_lasers=2 * num_of_points if alternating else num_of_points,
                                       counting_length=self.laser_length * 1.4)

        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_Pol20_order2(self, name='Pol 2.0_order', rabi_period=0.1e-6, n_start=1, n_step=1, num_of_points=50,
                              microwave_amplitude=0.25, microwave_frequency=2.8e9, tau=0.5e-6,
                              alternating = False, pulse_function='Sin'):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get pulse number array for measurement ticks
        n_array = n_start + np.arange(num_of_points) * n_step
        n_array.astype(int)
        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
        tau = self._adjust_to_samplingrate(tau, 2)

        # get readout element
        readout_element = self._get_readout_element()

        # get -x pihalf element
        pihalfminusy_element = self._get_mw_element_s3(length=rabi_period / 4, increment=0.0,
                                                       amp=microwave_amplitude, freq=microwave_frequency,
                                                       phase=270.0, pulse_function=pulse_function)
        pihalfx_element = self._get_mw_element_s3(length=rabi_period / 4, increment=0.0,
                                                  amp=microwave_amplitude, freq=microwave_frequency,
                                                  phase=0.0, pulse_function=pulse_function)

        # get y pihalf element
        pihalfy_element = self._get_mw_element_s3(length=rabi_period / 4,
                                                  increment=0.0,
                                                  amp=microwave_amplitude,
                                                  freq=microwave_frequency,
                                                  phase=90.0,
                                                  pulse_function=pulse_function)
        # get pi elements
        pix_element = self._get_mw_element_s3(length=rabi_period / 2,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0,
                                              pulse_function=pulse_function)

        piy_element = self._get_mw_element_s3(length=rabi_period / 2,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=90.0,
                                              pulse_function=pulse_function)

        # get tau/4 element
        tau_element = self._get_idle_element(length=tau / 4 - rabi_period / 2.0, increment=0.)

        block = PulseBlock(name=name)
        for order in n_array:
            for nn in range(2 * order):
                block.append(pihalfy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pihalfy_element)

                block.append(pihalfx_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pihalfx_element)

            block.extend(readout_element)

            for nn in range(2 * order):
                block.append(pihalfx_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pihalfx_element)

                block.append(pihalfy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(pihalfy_element)

            block[-1] = pihalfminusy_element
            block.extend(readout_element)



        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=True, units=('#', ''),
                                                        labels=('PulsePol order', 'Signal'),
                                                        controlled_variable=n_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences

    # def generate_Pol20_order2(self, name='Pol 2.0_order', rabi_period=0.1e-6, n_start=1, n_step=1, num_of_points=50,
    #                           microwave_amplitude=0.25, microwave_frequency=2.8e9, tau=0.5e-6, pulse_function='Sin'):
    #     """
    #
    #     """
    #     created_blocks = list()
    #     created_ensembles = list()
    #     created_sequences = list()
    #
    #     # get pulse number array for measurement ticks
    #     n_array = n_start + np.arange(num_of_points) * n_step
    #     n_array.astype(int)
    #     # change parameters in a way that they fit to the current sampling rate
    #     rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
    #     tau = self._adjust_to_samplingrate(tau, 2)
    #
    #     # get readout element
    #     readout_element = self._get_readout_element()
    #
    #     # get -x pihalf element
    #     pihalfminusx_element = self._get_mw_element_s3(length=rabi_period / 4, increment=0.0,
    #                                                    amp=microwave_amplitude, freq=microwave_frequency,
    #                                                    phase=180.0, pulse_function=pulse_function)
    #
    #     pihalfx_element = self._get_mw_element_s3(length=rabi_period / 4, increment=0.0,
    #                                               amp=microwave_amplitude, freq=microwave_frequency,
    #                                               phase=0.0, pulse_function=pulse_function)
    #     # get y pihalf element
    #     pihalfy_element = self._get_mw_element_s3(length=rabi_period / 4,
    #                                               increment=0.0,
    #                                               amp=microwave_amplitude,
    #                                               freq=microwave_frequency,
    #                                               phase=90.0,
    #                                               pulse_function=pulse_function)
    #     # get pi elements
    #     pix_element = self._get_mw_element_s3(length=rabi_period / 2,
    #                                           increment=0.0,
    #                                           amp=microwave_amplitude,
    #                                           freq=microwave_frequency,
    #                                           phase=0.0,
    #                                           pulse_function=pulse_function)
    #
    #     piy_element = self._get_mw_element_s3(length=rabi_period / 2,
    #                                           increment=0.0,
    #                                           amp=microwave_amplitude,
    #                                           freq=microwave_frequency,
    #                                           phase=90.0,
    #                                           pulse_function=pulse_function)
    #
    #     # get tau/4 element
    #     tau_element = self._get_idle_element(length=tau / 4 - rabi_period / 2.0, increment=0.)
    #
    #     block = PulseBlock(name=name)
    #
    #     for order in n_array:
    #         # adding this pi over 2 to check tau
    #         block.append(pihalfx_element)
    #         block.append(tau_element)
    #         for n in range(2 * order):
    #             block.append(pihalfminusx_element)
    #             block.append(tau_element)
    #             block.append(piy_element)
    #             block.append(tau_element)
    #             block.append(pihalfminusx_element)
    #
    #             block.append(pihalfy_element)
    #             block.append(tau_element)
    #             block.append(pix_element)
    #             block.append(tau_element)
    #             block.append(pihalfy_element)
    #
    #         block.extend(readout_element)
    #
    #         for nn in range(2 * order):
    #             block.append(pihalfy_element)
    #             block.append(tau_element)
    #             block.append(pix_element)
    #             block.append(tau_element)
    #             block.append(pihalfy_element)
    #
    #             block.append(pihalfminusx_element)
    #             block.append(tau_element)
    #             block.append(piy_element)
    #             block.append(tau_element)
    #             block.append(pihalfminusx_element)
    #
    #         block[-1] = pihalfx_element
    #
    #         # adding this pi over 2 to check tau
    #         block.append(tau_element)
    #         block.append(pihalfx_element)  #
    #         block.extend(readout_element)
    #
    #     created_blocks.append(block)
    #     # Create block ensemble
    #     block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
    #     block_ensemble.append((block.name, 0))
    #
    #     # Create and append sync trigger block if needed
    #     created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
    #     # add metadata to invoke settings
    #     block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
    #                                                     alternating=True, units=('#', ''),
    #                                                     labels=('PulsePol order', 'Signal'),
    #                                                     controlled_variable=n_array)
    #     # append ensemble to created ensembles
    #     created_ensembles.append(block_ensemble)
    #
    #     return created_blocks, created_ensembles, created_sequences



############################### Polarised Nuclear Spin Manipulation experiments ##########################################

    def generate_hmh_nuclear_odmr(self, name = 'HHM-Nuc-ODMR', freq_start=1e6 , freq_step=1e3, num_of_points=5,
                                       rf_rabi_period = 100e-6, rf_amp=0.1, hmh_name='HMH', rabi_period=50e-9,
                                       microwave_amplitude=0.1, microwave_frequency=2.8e9, microwave_phase=0,
                                       spinlock_length=25e-6, hmh_amp=0.01, hmh_frequency=2.8e9,  hmh_phase=0.0,
                                       hmh_laser_length=500e-9, hmh_wait_length=1e-6, repeat_pol=1,
                                       laser_name='Laser_wait', laser_length=500e-9, wait_length=1e-6):
        # First polarize a nuclear spin then manipulate it and readout
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        freq_array = freq_start + np.arange(num_of_points) * freq_step
        para_list = list()
        for number, freq in enumerate(freq_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse(name=name_tmp, rf_duration=rf_rabi_period/2, rf_amp=rf_amp, rf_freq=freq,
                                       rf_phase=0.0)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])


        created_blocks, created_ensembles, sequence = \
            self._hmh_polarisation(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=freq_array, units=('Hz', 'a.u.'), number_of_lasers=num_of_points,
                                       labels=('Frequency', 'Norm. Intensity'),
                                       counting_length=hmh_laser_length*1.2)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_hmh_nuclear_rabi(self, name = 'HMH-Nuc-Rabi', tau_start=1e-6 , tau_step=1e-6, num_of_points=5,
                                  rf_freq = 1e6, rf_amp=0.1, hmh_name='HMH', rabi_period=50e-9,
                                  microwave_amplitude=0.1, microwave_frequency=2.8e9, microwave_phase=0.0,
                                  spinlock_length=25e-6, hmh_amp=0.01, hmh_frequency=2.8e9,  hmh_phase=0.0,
                                  hmh_laser_length=500e-9, hmh_wait_length=1e-6, repeat_pol=1,
                                  laser_name='Laser_wait', laser_length=500e-9, wait_length=1e-6):
        # First polarize a nuclear spin then manipulate it and readout
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse2(name=name_tmp, rf_duration=tau, rf_amp=rf_amp, rf_freq=rf_freq,
                                       rf_phase=0.0)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])


        created_blocks, created_ensembles, sequence = \
            self._hmh_polarisation(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', 'a.u.'), number_of_lasers=num_of_points,
                                       labels=('interaction time ', 'Norm. Intensity'),
                                       counting_length=hmh_laser_length*1.2)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences


####################################### PulsePol Polarization ###################################################

    def generate_pp_nuclear_odmr(self, name = 'PP-Nuc-ODMR', freq_start=1e6 , freq_step=1e3, num_of_points=5,
                                 rf_rabi_period = 100e-6, rf_amp=0.1, pp_name='PulsePol', rabi_period=50e-9,
                                 microwave_amplitude=0.1, microwave_frequency=2.8e9, tau=1e-6,
                                 order=20, pp_laser_length=500e-9, pp_wait_length=1e-6, repeat_pol=1, repetitions=1):

        # First polarize a nuclear spin then manipulate it and readout
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        freq_array = freq_start + np.arange(num_of_points) * freq_step
        para_list = list()
        for number, freq in enumerate(freq_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse(name=name_tmp, rf_duration=rf_rabi_period/2, rf_amp=rf_amp, rf_freq=freq,
                                       rf_phase=0.0)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])


        created_blocks, created_ensembles, sequence = \
            self._pp_polarisation(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=freq_array, units=('Hz', 'a.u.'), number_of_lasers=num_of_points,
                                       labels=('Frequency', 'Norm. Intensity'),
                                       counting_length=pp_laser_length*1.2)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_pp_nuclear_rabi(self, name='PP-Nuc-Rabi', tau_start=1e-6, tau_step=1e-6, num_of_points=5,
                                 rf_freq=100e-6, rf_amp=0.1, pp_name='PulsePol', rabi_period=50e-9,
                                 microwave_amplitude=0.1, microwave_frequency=2.8e9, tau=1e-6,
                                 order=20, pp_laser_length=500e-9, pp_wait_length=1e-6, repeat_pol=1, repetitions=1):

        # First polarize a nuclear spin then manipulate it and readout
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse(name=name_tmp, rf_duration=tau, rf_amp=rf_amp, rf_freq=rf_freq,
                                               rf_phase=0.0)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])

        created_blocks, created_ensembles, sequence = \
            self._pp_polarisation(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', 'a.u.'),
                                       number_of_lasers=num_of_points,
                                       labels=('RF duration', 'Norm. Intensity'),
                                       counting_length=pp_laser_length * 1.2)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    ############################################ Sequences with polarized carbon spin #####################################################

    def generate_hmh_phase_calibration(self, name='HMH-Phase-Calibration', phase_start=0.0, phase_step=3.0,
                                       num_of_points=5,
                                       rf_freq=1e6, rf_amp=0.1, rf_rabi_period=10e-6, hmh_name='HMH',
                                       spinlock_length=25e-6, hmh_amp=0.01, hmh_frequency=2.8e9, hmh_phase=0.0,
                                       hmh_laser_length=500e-9, hmh_wait_length=1e-6, repeat_pol=1,
                                       xy8_name='XY8', rabi_period=50e-9, microwave_amplitude=0.1,
                                       microwave_frequency=2.8e9, microwave_phase=0.0, tau=1e-6, xy8N=4,
                                       ylast=False,
                                       readout_name='Laser_wait', laser_length=500e-9, wait_length=1e-6):
        # First polarize a nuclear spin then manipulate it and readout
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        phase_array = phase_start + np.arange(num_of_points) * phase_step
        para_list = list()
        for number, phase in enumerate(phase_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse(name=name_tmp, rf_duration=rf_rabi_period / 4.0, rf_amp=rf_amp,
                                               rf_freq=rf_freq,
                                               rf_phase=phase)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])

        # Add hmh
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_hmh(name=hmh_name,
                                     rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                     microwave_frequency=microwave_frequency, microwave_phase=microwave_phase,
                                     spinlock_length=spinlock_length, hmh_amplitude=hmh_amp,
                                     hmh_frequency=hmh_frequency, hmh_phase=hmh_phase,
                                     hmh_laser_length=hmh_laser_length,
                                     hmh_wait_length=hmh_wait_length, alternating=False, trigger=False)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        hmh_list = [hmh_name, seq_param]

        # ADD XY8
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_xy8_s3(name=xy8_name, rabi_period=rabi_period, tau=tau,
                                        microwave_amplitude=microwave_amplitude,
                                        microwave_frequency=microwave_frequency, xy8N=xy8N, ylast=ylast)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        xy8_list = [xy8_name, seq_param]

        # Add readout element
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_laser_wait(name=readout_name, laser_length=laser_length, wait_length=wait_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        readout_list = [readout_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(num_of_points):
            element_list.append(hmh_list.copy())
            element_list.append(para_list[ii][0].copy())
            element_list.append(para_list[ii][1].copy())
            element_list.append(xy8_list.copy())
            element_list.append(readout_list.copy())

        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=phase_array, units=('°', 'a.u.'),
                                       number_of_lasers=num_of_points,
                                       labels=('RF phase', 'Norm. Intensity'),
                                       counting_length=laser_length * 1.2)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences


    def generate_pp_phase_calibration(self, name='PP-Phase-Calibration', phase_start=0.0, phase_step=3.0,
                                       num_of_points=5,
                                       rf_freq=1e6, rf_amp=0.1, rf_rabi_period=10e-6, pp_name='PulsePol',
                                       pp_tau=25e-6, pp_order=20,
                                       pp_laser_length=500e-9, pp_wait_length=1e-6, repeat_pol=1,
                                       xy8_name='XY8', rabi_period=50e-9, microwave_amplitude=0.1,
                                       microwave_frequency=2.8e9, microwave_phase=0.0, tau=1e-6, xy8N=4,
                                       ylast=True,
                                       readout_name='Laser_wait', laser_length=500e-9, wait_length=1e-6):
        # First polarize a nuclear spin then manipulate it and readout
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        phase_array = phase_start + np.arange(num_of_points) * phase_step
        para_list = list()
        for number, phase in enumerate(phase_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse(name=name_tmp, tau=rf_rabi_period / 4.0, microwave_amplitude=rf_amp,
                                              microwave_frequency=rf_freq, microwave_phase=phase)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])


        # Add hmh
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_pulsepol(name=pp_name,
                                     rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                     microwave_frequency=microwave_frequency, tau=pp_tau,
                                     order=pp_order, pp_laser_length=pp_laser_length,
                                     pp_wait_length=pp_wait_length, trigger=False)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        pp_list = [pp_name, seq_param]

        # ADD XY8
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_xy8_s3(name=xy8_name, rabi_period=rabi_period, tau=tau,
                                        microwave_amplitude=microwave_amplitude,
                                        microwave_frequency=microwave_frequency, xy8N=xy8N, ylast=ylast)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        xy8_list = [xy8_name, seq_param]

        # Add readout element
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_laser_wait(name=readout_name, laser_length=laser_length,
                                             wait_length=wait_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        readout_list = [readout_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(num_of_points):
            element_list.append(pp_list.copy())
            element_list.append(para_list[ii].copy())
            #element_list.append(para_list[ii][1].copy())
            element_list.append(xy8_list.copy())
            element_list.append(readout_list.copy())

        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False,
                                       laser_ignore_list=list(),
                                       controlled_variable=phase_array, units=('°', 'a.u.'),
                                       number_of_lasers=num_of_points,
                                       labels=('RF phase', 'Norm. Intensity'),
                                       counting_length=laser_length * 1.2)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_pp_xy8(self, name='PP-XY8', tau_start=1e-6, tau_step=1e-6, num_of_points=5,
                        rabi_period=50e-9, microwave_amplitude=0.1, microwave_frequency=2.8e9, xy8N=4, ylast=True,
                        rf_name='C13', rf_freq=1e6, rf_amp=0.1, rf_rabi_period=10e-6, rf_phase = 0.0,
                        pp_name='PulsePol', pp_tau=2.5e-6, pp_order=20, pp_laser_length=500e-9, pp_wait_length=1e-6,
                        repeat_pol=1, readout_name='Laser_wait', laser_length=500e-9, wait_length=1e-6):
        # First polarize a nuclear spin then manipulate it and readout
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_xy8_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                                            microwave_amplitude=microwave_amplitude,
                                            microwave_frequency=microwave_frequency, xy8N=xy8N, ylast=ylast)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        # Add PulsePol
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_pulsepol(name=pp_name,
                                          rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                          microwave_frequency=microwave_frequency, tau=pp_tau,
                                          order=pp_order, pp_laser_length=pp_laser_length,
                                          pp_wait_length=pp_wait_length, trigger=False)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        pp_list = [pp_name, seq_param]

        # ADD C13 Rf pulse
        # created_blocks_tmp, created_ensembles_tmp, rf_list1, rf_list2 = \
        #     self.generate_chopped_rf_pulse(name=rf_name, rf_duration=rf_rabi_period / 4.0, rf_amp=rf_amp,
        #                                    rf_freq=rf_freq, rf_phase=rf_phase)
        # created_blocks += created_blocks_tmp
        # created_ensembles += created_ensembles_tmp
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_mw_pulse(name=rf_name, tau=rf_rabi_period / 4.0, microwave_amplitude=rf_amp,
                                          microwave_frequency=rf_freq, microwave_phase=rf_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        rf_list1 = [rf_name, seq_param]

        # Add readout element
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_laser_wait(name=readout_name, laser_length=laser_length,
                                             wait_length=wait_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        readout_list = [readout_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(num_of_points):
            element_list.append(pp_list.copy())
            element_list.append(rf_list1.copy())
            #element_list.append(rf_list2.copy())
            element_list.append(para_list[ii].copy())
            element_list.append(readout_list.copy())

        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False,
                                       laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', 'a.u.'),
                                       number_of_lasers=num_of_points,
                                       labels=('tau', 'Norm. Intensity'),
                                       counting_length=laser_length * 1.2)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_pp_xy8_nsweep(self, name='PP-XY8', n_start=2, n_step=2, num_of_points=5,
                               rabi_period=50e-9, microwave_amplitude=0.1, microwave_frequency=2.8e9, tau=1e-6, ylast=True,
                               rf_name='C13', rf_freq=1e6, rf_amp=0.1, rf_rabi_period=10e-6, rf_phase = 0.0,
                               pp_name='PulsePol', pp_tau=2.5e-6, pp_order=20, pp_laser_length=500e-9, pp_wait_length=1e-6,
                               repeat_pol=1, readout_name='Laser_wait', laser_length=500e-9, wait_length=1e-6):
        # First polarize a nuclear spin then manipulate it and readout
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        n_array = n_start + np.arange(num_of_points) * n_step
        para_list = list()
        for number, xy8N in enumerate(n_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_xy8_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                                            microwave_amplitude=microwave_amplitude,
                                            microwave_frequency=microwave_frequency, xy8N=xy8N, ylast=ylast)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        # Add PulsePol
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_pulsepol(name=pp_name,
                                          rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                          microwave_frequency=microwave_frequency, tau=pp_tau,
                                          order=pp_order, pp_laser_length=pp_laser_length,
                                          pp_wait_length=pp_wait_length, trigger=False)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        pp_list = [pp_name, seq_param]

        # ADD C13 Rf pulse
        created_blocks_tmp, created_ensembles_tmp, rf_list1, rf_list2 = \
            self.generate_chopped_rf_pulse(name=rf_name, rf_duration=rf_rabi_period / 4.0, rf_amp=rf_amp,
                                           rf_freq=rf_freq, rf_phase=rf_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add readout element
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_laser_wait(name=readout_name, laser_length=laser_length,
                                             wait_length=wait_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        readout_list = [readout_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(num_of_points):
            element_list.append(pp_list.copy())
            element_list.append(rf_list1.copy())
            element_list.append(rf_list2.copy())
            element_list.append(para_list[ii].copy())
            element_list.append(readout_list.copy())

        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False,
                                       laser_ignore_list=list(),
                                       controlled_variable=n_array, units=('#', 'a.u.'),
                                       number_of_lasers=num_of_points,
                                       labels=('XY8 order', 'Norm. Intensity'),
                                       counting_length=laser_length * 1.2)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    ###################################### Sequences with polarised nitrogen spin #################################

    def generate_polarised_odmr(self, name='Polarised-ODMR', freq_start=2.8e9, freq_step=1.0e6, num_of_points=5,
                                rabi_period = 1e-6, microwave_amplitude=0.1, laser_length_experiment=1e-6,
                                wait_length_experiment = 1e-6,
                                laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6,
                                rf_cnot_rabi_period=100.0e-6, rf_cnot_amplitude=0.1, rf_cnot_phase=0,
                                rf_cnot_frequency = 2e6, rf_cnot_name='RF-CNOT',
                                mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=20e-6, mw_cnot_amplitude=0.025,
                                mw_cnot_frequency=2.8e9, mw_cnot_phase=0, counts_per_readout=100,repeat_pol=2,
                                alternating=False):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # generate the RF-Rabi pieces
        freq_array = freq_start + np.arange(num_of_points) * freq_step
        para_list=list()
        for number, freq in enumerate(freq_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_mw_trigger_laser_wait(name=name_tmp, laser_length=laser_length_experiment,
                                                    wait_length = wait_length_experiment, mw_length = rabi_period/2.,
                                                    mw_amp=microwave_amplitude, mw_phase=0, mw_freq=freq)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_polarisation(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=freq_array, units=('Hz', ''), labels=('Frequency', 'Signal'),
                                       number_of_lasers=num_of_points,
                                       counting_length=laser_length_experiment * 1.4)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_polarised_hmhamp(self, name='Polarised-HMHamp', rabi_period = 1e-6, microwave_amplitude=0.1,
                                  microwave_frequency = 2.8e9, microwave_phase=0.0,
                                  spinlock_length=25e-6, amp_start=0.05, amp_step=1e-3, num_of_points=5,
                                  hmh_frequency=2.8e9, hmh_phase=0.0,
                                  laser_length_experiment=1e-6, wait_length_experiment = 1e-6,
                                  laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6,
                                  rf_cnot_rabi_period=100.0e-6, rf_cnot_amplitude=0.1, rf_cnot_phase=0,
                                  rf_cnot_frequency = 2e6, rf_cnot_name='RF-CNOT',
                                  mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=20e-6, mw_cnot_amplitude=0.025,
                                  mw_cnot_frequency=2.8e9, mw_cnot_phase=0, counts_per_readout=100,repeat_pol=2,
                                  alternating=True):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        amp_array = amp_start + np.arange(num_of_points) * amp_step
        para_list=list()
        for number, amp in enumerate(amp_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_hmh(name=name_tmp, rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                         microwave_frequency = microwave_frequency, microwave_phase=microwave_phase,
                                         spinlock_length=spinlock_length, hmh_amplitude=amp,
                                         hmh_frequency=hmh_frequency, hmh_phase=hmh_phase,
                                         hmh_laser_length=laser_length_experiment,
                                         hmh_wait_length = wait_length_experiment, alternating=False, trigger = True)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
            para_list.append([name_tmp, seq_param])
        if alternating:
            for number, amp in enumerate(amp_array):
                name_tmp = name + '_alt_' + str(number)
                created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                    self.generate_single_hmh(name=name_tmp, rabi_period=rabi_period,
                                             microwave_amplitude=microwave_amplitude,
                                             microwave_frequency=microwave_frequency, microwave_phase=microwave_phase,
                                             spinlock_length=spinlock_length, hmh_amplitude=amp,
                                             hmh_frequency=hmh_frequency, hmh_phase=hmh_phase,
                                             hmh_laser_length=laser_length_experiment,
                                             hmh_wait_length=wait_length_experiment, alternating=True, trigger = True)
                created_blocks += created_blocks_tmp
                created_ensembles += created_ensembles_tmp
                seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
                para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_polarisation(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=alternating, laser_ignore_list=list(),
                                       controlled_variable=amp_array, units=('V', 'a.u.'), labels=('Amplitude', 'Signal'),
                                       number_of_lasers=2*num_of_points if alternating else num_of_points,
                                       counting_length=laser_length_experiment * 1.4)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_polarised_hmhtau(self, name='Polarised-HMHtau', rabi_period = 1e-6, microwave_amplitude=0.1,
                                  microwave_frequency=2.8e9, microwave_phase=0.0,
                                  amp=0.05, tau_start=1e-6, tau_step=1e-6, num_of_points=5,
                                  hmh_frequency=2.8e9, hmh_phase=0.0,
                                  laser_length_experiment=1e-6, wait_length_experiment = 1e-6,
                                  laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6,
                                  rf_cnot_rabi_period=100.0e-6, rf_cnot_amplitude=0.1, rf_cnot_phase=0,
                                  rf_cnot_frequency = 2e6, rf_cnot_name='RF-CNOT',
                                  mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=20e-6, mw_cnot_amplitude=0.025,
                                  mw_cnot_frequency=2.8e9, mw_cnot_phase=0, counts_per_readout=100,repeat_pol=2,
                                  alternating=True):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list=list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_hmh(name=name_tmp, rabi_period=rabi_period,
                                         microwave_amplitude=microwave_amplitude,
                                         microwave_frequency=microwave_frequency, microwave_phase=0,
                                         spinlock_length=tau, hmh_amplitude=amp,
                                         hmh_frequency=hmh_frequency, hmh_phase=hmh_phase,
                                         hmh_laser_length=laser_length_experiment,
                                         hmh_wait_length=wait_length_experiment, alternating=False, trigger = True)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
            para_list.append([name_tmp, seq_param])
        if alternating:
            for number, tau in enumerate(tau_array):
                name_tmp = name + '_alt_' + str(number)
                created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                    self.generate_single_hmh(name=name_tmp, rabi_period=rabi_period,
                                             microwave_amplitude=microwave_amplitude,
                                             microwave_frequency=microwave_frequency, microwave_phase=0.0,
                                             spinlock_length=tau, hmh_amplitude=amp,
                                             hmh_frequency=hmh_frequency, hmh_phase=hmh_phase,
                                             hmh_laser_length=laser_length_experiment,
                                             hmh_wait_length=wait_length_experiment, alternating=True, trigger = True)
                created_blocks += created_blocks_tmp
                created_ensembles += created_ensembles_tmp
                seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
                para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_polarisation(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=alternating, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', 'a.u.'), labels=('Spin locking', 'Signal'),
                                       number_of_lasers=2*num_of_points if alternating else num_of_points,
                                       counting_length=laser_length_experiment * 1.4)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences




############################################# Standard nuclear manipulstion #####################################

    def _standard_polarisation(self, created_blocks, created_ensembles, para_list, para_dict):

        # generate initialization, and rr_readout)
        created_blocks_tmp, created_ensembles_tmp, laser_wait_list, mw_cnot_list, rf_list1, rf_list2 = \
            self._initialize_polarisation(laser_name=para_dict['laser_name'], laser_length=para_dict['laser_length'],
                                          wait_length=para_dict['wait_length'],
                                          mw_cnot_name=para_dict['mw_cnot_name'],
                                          mw_cnot_rabi_period=para_dict['mw_cnot_rabi_period'],
                                          mw_cnot_amplitude=para_dict['mw_cnot_amplitude'],
                                          mw_cnot_frequency=para_dict['mw_cnot_frequency'],
                                          mw_cnot_phase=para_dict['mw_cnot_phase'],
                                          rf_cnot_name=para_dict['rf_cnot_name'],
                                          rf_cnot_rabi_period=para_dict['rf_cnot_rabi_period'],
                                          rf_cnot_amplitude=para_dict['rf_cnot_amplitude'],
                                          rf_cnot_frequency=para_dict['rf_cnot_frequency'],
                                          rf_cnot_phase=para_dict['rf_cnot_phase'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(para_dict['num_of_points']):
            for nn in range(para_dict['repeat_pol']):
                element_list.append(mw_cnot_list.copy())
                element_list.append(rf_list1.copy())
                element_list.append(rf_list2.copy())
                element_list.append(laser_wait_list.copy())
            element_list.append(para_list[ii].copy())
            if para_dict['alternating']:
                for nn in range(para_dict['repeat_pol']):
                    element_list.append(mw_cnot_list.copy())
                    element_list.append(rf_list1.copy())
                    element_list.append(rf_list2.copy())
                    element_list.append(laser_wait_list.copy())
                element_list.append(para_list[para_dict['num_of_points']+ii].copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)

        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)
        return created_blocks, created_ensembles, sequence


    def _hmh_polarisation(self, created_blocks, created_ensembles, para_list, para_dict):

        # generate initialization, and rr_readout)
        created_blocks_tmp, created_ensembles_tmp, hmh_list, laser_wait_list = \
            self._initialize_hmh_polarisation(hmh_name=para_dict['hmh_name'],
                                              rabi_period=para_dict['rabi_period'],
                                              microwave_amplitude=para_dict['microwave_amplitude'],
                                              microwave_frequency=para_dict['microwave_frequency'],
                                              microwave_phase=para_dict['microwave_phase'],
                                              spinlock_length=para_dict['spinlock_length'],
                                              hmh_amp=para_dict['hmh_amp'],
                                              hmh_frequency=para_dict['hmh_frequency'],
                                              hmh_phase=para_dict['hmh_phase'],
                                              hmh_laser_length=para_dict['hmh_laser_length'],
                                              hmh_wait_length=para_dict['hmh_wait_length'],
                                              laser_name=para_dict['laser_name'],
                                              laser_length=para_dict['laser_length'],
                                              wait_length=para_dict['wait_length'],
                                              repeat_pol=para_dict['repeat_pol'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(para_list[ii][0].copy())
            element_list.append(para_list[ii][1].copy())
            element_list.append(hmh_list.copy())
            #element_list.append(laser_wait_list.copy())

        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)

        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)

        return created_blocks, created_ensembles, sequence

    def _pp_polarisation(self, created_blocks, created_ensembles, para_list, para_dict):

        # Generate pulsepol readout
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_pulsepol(name=para_dict['pp_name'], rabi_period=para_dict['rabi_period'],
                                          microwave_amplitude=para_dict['microwave_amplitude'],
                                          microwave_frequency=para_dict['microwave_frequency'],
                                          tau=para_dict['tau'], order=para_dict['order'],
                                          pp_laser_length=para_dict['pp_laser_length'],
                                          pp_wait_length=para_dict['pp_wait_length'], trigger=True, repetitions=para_dict['repetitions'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': para_dict['repeat_pol'] - 1})
        pp_list = [para_dict['pp_name'], seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(para_list[ii][0].copy())
            element_list.append(para_list[ii][1].copy())
            element_list.append(pp_list.copy())

        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)

        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)

        return created_blocks, created_ensembles, sequence


############################################ Helper methods ##################################################


    def _initialize_polarisation(self, laser_name, laser_length, wait_length, rf_cnot_name, rf_cnot_rabi_period,
                                 rf_cnot_amplitude, rf_cnot_frequency, rf_cnot_phase, mw_cnot_name,
                                 mw_cnot_rabi_period, mw_cnot_amplitude, mw_cnot_frequency, mw_cnot_phase):
        # standard sequence for repetitive readout.

        created_blocks = list()
        created_ensembles = list()

        # Add the laser wait
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_laser_wait(name=laser_name, laser_length=laser_length, wait_length=wait_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        laser_wait_list = [laser_name, seq_param]

        # Add MW-CNOT
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2,
                                             microwave_amplitude=mw_cnot_amplitude,
                                             microwave_frequency=mw_cnot_frequency, microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add RF pulse
        created_blocks_tmp, created_ensembles_tmp, rf_list1, rf_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_rabi_period/2, rf_amp=rf_cnot_amplitude,
                                   rf_freq=rf_cnot_frequency, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        return created_blocks, created_ensembles, laser_wait_list, mw_cnot_list, rf_list1, rf_list2

    def _initialize_hmh_polarisation(self, hmh_name, rabi_period, microwave_amplitude, microwave_frequency,
                                     microwave_phase,
                                     spinlock_length, hmh_amp, hmh_frequency, hmh_phase, hmh_laser_length, 
                                     hmh_wait_length, laser_name, laser_length, wait_length, repeat_pol):
        # standard sequence for repetitive readout.

        created_blocks = list()
        created_ensembles = list()

        # Add hmh
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_hmh(name=hmh_name,
                                     rabi_period = rabi_period, microwave_amplitude=microwave_amplitude,
                                     microwave_frequency=microwave_frequency, microwave_phase=microwave_phase,
                                     spinlock_length=spinlock_length, hmh_amplitude=hmh_amp,
                                     hmh_frequency=hmh_frequency, hmh_phase=hmh_phase, hmh_laser_length=hmh_laser_length,
                                     hmh_wait_length=hmh_wait_length, alternating=False, trigger = True)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol-1})
        hmh_list = [hmh_name, seq_param]

        # Add the laser wait
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_laser_wait(name=laser_name, laser_length=laser_length, wait_length=wait_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        laser_wait_list = [laser_name, seq_param]

        return created_blocks, created_ensembles, hmh_list, laser_wait_list




