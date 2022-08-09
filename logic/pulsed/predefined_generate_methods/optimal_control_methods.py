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
from core.util.helpers import csv_2_list

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


class BasicPredefinedGenerator(PredefinedGeneratorBase):
    """

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    ################################################################################################
    #                         Generation methods for new pulse objects                             #
    ################################################################################################

    def _get_mw_element_oc_RedCrab(self, length, amplitude_scaling, frequency, phase, filename_amplitude,
                                   filename_phase, folder_path):
        """
        Creates a MW pulse PulseBlockElement for a given optimal control pulse file

        @param float length: MW pulse duration
        @param float amplitude_scaling: scaling factor for the amplitude of the MW pulse
        @param float frequency: frequency of the MW pulse
        @param float phase: phase of the MW pulse (additional to the optimized one)
        @param str filename: filename of the optimized pulse
        @param str folder_path: folder path in which the optimized pulse file is located

        @return: PulseBlockElement, the generated MW element
        """

        if not length:
            length = self._get_oc_pulse_length(filename_amplitude, folder_path)

        if self.microwave_channel.startswith('d'):
            self.log.error('Please choose a analog output! The optimized pulse cannot be generated for a digital '
                           'channel!'
                           '\n Returning a idle element instead!')

            mw_oc_element_RedCrab = self._get_idle_element(
                length=length,
                increment=0)

        else:
            mw_oc_element_RedCrab = self._get_idle_element(
                length=length,
                increment=0)

            mw_oc_element_RedCrab.pulse_function[self.microwave_channel] = SamplingFunctions.OC_RedCrab(
                amplitude_scaling=amplitude_scaling,
                frequency=frequency,
                phase=phase,
                filename_amplitude=filename_amplitude,
                filename_phase=filename_phase,
                folder_path=folder_path
            )

        return mw_oc_element_RedCrab

    ####################################################################################################################
    # State to State Transfer
    ####################################################################################################################

    # todo: think about idle extension
    def _get_oc_pulse_length(self, filename_amplitude, folder_path, idle_extension=-1e-9):
        time, ampl = np.loadtxt(folder_path + "/" + filename_amplitude, usecols=(0, 1), unpack=True)
        return time[-1] + idle_extension

    def generate_oc_mw_only(self, name='optimal_mw_pulse',  phase=0,
                            filename_amplitude='amplitude.txt', filename_phase='phase.txt',
                        folder_path=r'C:\Software\qudi_data\optimal_control_assets'):

        """
        wrapper to make _get_mw_element_oc_RedCrab available to sequence methods in other generate method files
        """

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the optimized mw element
        oc_mw_element = self._get_mw_element_oc_RedCrab(length=None,
                                                        amplitude_scaling=1,
                                                        frequency=self.microwave_frequency,
                                                        phase=phase,
                                                        filename_amplitude=filename_amplitude,
                                                        filename_phase=filename_phase,
                                                        folder_path=folder_path)

        # Create block and append to created_blocks list
        qst_block = PulseBlock(name=name)
        qst_block.append(oc_mw_element)
        created_blocks.append(qst_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((qst_block.name, 0))

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = np.arange(1)
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 0
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_sts_oc(self, name='stsoc', length=99e-9, filename_amplitude='amplitude.txt', filename_phase='phase.txt',
                        folder_path=r'C:\Software\qudi_data\optimal_control_assets'):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)

        pix_element = self._get_mw_element(length=self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=0)

        pihalfx_element = self._get_mw_element(length=self.rabi_period / 4,
                                               increment=0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=0)

        pihalfy_element = self._get_mw_element(length=self.rabi_period / 4,
                                               increment=0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=90)

        # create the optimized mw element
        oc_mw_element = self._get_mw_element_oc_RedCrab(length=length,
                                                        amplitude_scaling=1,
                                                        frequency=self.microwave_frequency,
                                                        phase=0,
                                                        filename_amplitude=filename_amplitude,
                                                        filename_phase=filename_phase,
                                                        folder_path=folder_path)

        # Create block and append to created_blocks list
        qst_block = PulseBlock(name=name)

        qst_block.append(laser_element)
        qst_block.append(waiting_element)

        qst_block.append(oc_mw_element)

        qst_block.append(laser_element)
        qst_block.append(waiting_element)

        created_blocks.append(qst_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((qst_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = np.arange(2)
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_sts_rec(self, name='stsrec', length=99e-9, amplitude=0.5):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)

        # create the optimized mw element
        oc_mw_element = self._get_mw_element(length=length,
                                             increment=0,
                                             amp=amplitude,
                                             freq=self.microwave_frequency,
                                             phase=0)

        # Create block and append to created_blocks list
        qst_block = PulseBlock(name=name)

        qst_block.append(laser_element)
        qst_block.append(waiting_element)

        qst_block.append(oc_mw_element)

        qst_block.append(laser_element)
        qst_block.append(waiting_element)

        created_blocks.append(qst_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((qst_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = np.arange(2)
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_oc_nrep(self, name='oc_nrep_sweep', n_start=1, n_step=1, num_of_points=10,
                        filename_amplitude='amplitude.txt', filename_phase='phase.txt',
                        folder_path=r'C:\Software\qudi_data\optimal_control_assets',
                        t_gap=0e-9, phase=0, init_end_pix=0, init_end_phase_deg=0,
                        vs_rect_pulse=True, alternating=True):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        n_array = n_start + np.arange(num_of_points) * n_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)

        pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=0)
        gap_element = self._get_idle_element(length=t_gap,
                                                 increment=0)
        # rect init/end pulses are not ideal. Make them X,-X for some pulse error correction
        pix_init_element = self._get_mw_element(length=init_end_pix*self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=init_end_phase_deg)

        pix_end_element = self._get_mw_element(length=-init_end_pix*self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=init_end_phase_deg)

        # create the optimized mw element
        oc_mw_element = self._get_mw_element_oc_RedCrab(length=None,
                                                        amplitude_scaling=1,
                                                        frequency=self.microwave_frequency,
                                                        phase=phase,
                                                        filename_amplitude=filename_amplitude,
                                                        filename_phase=filename_phase,
                                                        folder_path=folder_path)

        # Create block and append to created_blocks list
        qst_block = PulseBlock(name=name)
        for n_pulses in n_array:
            if init_end_pix != 0:
                qst_block.append(pix_init_element)
            qst_block.extend([oc_mw_element, gap_element]*n_pulses)
            if init_end_pix != 0:
                qst_block.append(pix_end_element)
            qst_block.append(laser_element)
            qst_block.append(waiting_element)

            if alternating:
                qst_block.append(laser_element)
                qst_block.append(waiting_element)

        # compare against rect pulses (negative x axis)
        for n_pulses in n_array:
            if vs_rect_pulse:
                if init_end_pix != 0:
                    qst_block.append(pix_init_element)
                qst_block.extend([pi_element, gap_element]*n_pulses)
                if init_end_pix != 0:
                    qst_block.append(pix_end_element)
                qst_block.append(laser_element)
                qst_block.append(waiting_element)

                if alternating:
                    qst_block.append(laser_element)
                    qst_block.append(waiting_element)

        created_blocks.append(qst_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((qst_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        n_lasers = num_of_points
        n_lasers = 2*n_lasers if alternating else n_lasers
        n_lasers = 2*n_lasers if vs_rect_pulse else n_lasers
        # rect pulses have negative repetition number n
        x_axis = list(n_array)
        x_axis = list(n_array) + list(-n_array) if vs_rect_pulse else x_axis
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = x_axis
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = n_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_oc_podmr(self, name='oc_podmr', freq_start=2870.0e6, freq_step=0.2e6,
                        num_of_points=50,
                        filename_amplitude='amplitude.txt', filename_phase='phase.txt',
                        folder_path=r'C:\Software\qudi_data\optimal_control_assets',
                        ):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        freq_array = freq_start + np.arange(num_of_points) * freq_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)


        # Create block and append to created_blocks list
        qst_block = PulseBlock(name=name)

        for mw_freq in freq_array:
            oc_mw_element = self._get_mw_element_oc_RedCrab(length=None,
                                                            amplitude_scaling=1,
                                                            frequency=mw_freq,
                                                            phase=0,
                                                            filename_amplitude=filename_amplitude,
                                                            filename_phase=filename_phase,
                                                            folder_path=folder_path)
            qst_block.append(oc_mw_element)
            qst_block.append(laser_element)
            qst_block.append(waiting_element)



        created_blocks.append(qst_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((qst_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        n_lasers = num_of_points
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = n_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences