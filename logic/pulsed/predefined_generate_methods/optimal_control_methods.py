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
from logic.pulsed.sampling_functions import SamplingFunctions, DDMethods
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

    def _get_mw_element_oc_multi(self, length, amplitude_scaling, freqs, phases, fnames_i,
                                   fnames_q, folder_path):
        """
        Creates an OC MW pulse PulseBlockElement with multiple carriers. Provided oc files must have same length.
        """

        n_carriers = min(len(freqs), len(phases))
        if not (len(phases) == len(freqs) == len(fnames_i) == len(fnames_q)):
            raise ValueError("Input arrays must be of same length.")

        if not length:
            lengthes = []
            for file in fnames_i:
                lengthes.append(self._get_oc_pulse_length(file, folder_path))
            if len(np.unique(lengthes)) != 1:
                raise ValueError(f"Provided oc pulses not of same length, but {lengthes}")
            length = lengthes[0]

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

            if n_carriers == 1:
                mw_oc_element_RedCrab.pulse_function[self.microwave_channel] = SamplingFunctions.OC_RedCrab(
                    amplitude_scaling=amplitude_scaling[0],
                    frequency=freqs[0],
                    phase=phases[0],
                    filename_amplitude=fnames_i[0],
                    filename_phase=fnames_q[0],
                    folder_path=folder_path
                )
            elif n_carriers == 2:
                mw_oc_element_RedCrab.pulse_function[self.microwave_channel] = SamplingFunctions.OC_DoubleCarrierSum(
                    amplitude_scaling_1=amplitude_scaling[0],
                    amplitude_scaling_2=amplitude_scaling[1],
                    frequency_1=freqs[0],
                    phase_1=phases[0],
                    frequency_2=freqs[1],
                    phase_2=phases[1],
                    filename_i_1=fnames_i[0],
                    filename_q_1=fnames_q[0],
                    filename_i_2=fnames_i[1],
                    filename_q_2=fnames_q[1],
                    folder_path=folder_path
                )
            else:
                raise NotImplementedError

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

    def generate_oc_mw_multi_only(self, name='optimal_mw_pulse',  mw_freqs='1e9', phases='0',
                            filename_i='amplitude.txt', filename_q='phase.txt', scale_ampl='1',
                        folder_path=r'C:\Software\qudi_data\optimal_control_assets'):

        """
        wrapper to make _get_mw_element_oc_RedCrab available to sequence methods in other generate method files
        """

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        mw_freqs = csv_2_list(mw_freqs)
        phases = csv_2_list(phases)
        ampl_scales = csv_2_list(scale_ampl)
        filename_i = [f.strip('\'') for f in csv_2_list(filename_i, str_2_val=str, delimiter=";")]
        filename_q = [f.strip('\'') for f in csv_2_list(filename_q, str_2_val=str, delimiter=";")]

        # create the optimized mw element
        oc_mw_element = self._get_mw_element_oc_multi(length=None,
                                                      amplitude_scaling=ampl_scales,
                                                      freqs=mw_freqs, phases=phases,
                                                      fnames_i=filename_i,
                                                      fnames_q=filename_q,
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
                        t_gap=0e-9, phases='0', init_end_pix=0., init_end_phases_deg='0',
                        dd_type=DDMethods.SE,
                        vs_rect_pulse=True, symmetric_tgap=False,
                        alternating=True, alternating_end_phase=False):
        """
        @param name:
        @param n_start:
        @param n_step:
        @param num_of_points:
        @param filename_amplitude:
        @param filename_phase:
        @param folder_path:
        @param t_gap:
        @param phases: string of list of oc phase. Must provide init_end_phases_deg of same length.
                       Repeat each datapoint with every element.
        @param init_end_pix:
        @param init_end_phases_deg:
        @param dd_type: Add dd phase cycling within a n_rep.
        @param vs_rect_pulse:
        @param symmetric_tgap:
        @param alternating:
        @return:
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        assert not (alternating and alternating_end_phase)

        phases = csv_2_list(phases)
        init_end_phases_deg = csv_2_list(init_end_phases_deg)
        if len(phases) != len(init_end_phases_deg):
            raise ValueError(f"OC phases {phases} and init_end phases {init_end_phases_deg} "
                             f"must have same length!")

        n_array = n_start + np.arange(num_of_points) * n_step
        # combine each n_pi with all phases
        n_array = np.asarray([val for val in n_array for _ in range(len(phases))])

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)


        gap_element = self._get_idle_element(length=t_gap,
                                                 increment=0)
        gap2_element = self._get_idle_element(length=t_gap/2,
                                             increment=0)
        def pi_element(pix=1., phase=0, is_oc=False):
            pi_rect_element = self._get_mw_element(length=pix * self.rabi_period / 2,
                                                    increment=0,
                                                    amp=self.microwave_amplitude,
                                                    freq=self.microwave_frequency,
                                                    phase=phase)


            # create the optimized mw element
            oc_mw_element = self._get_mw_element_oc_RedCrab(length=None,
                                                            amplitude_scaling=1,
                                                            frequency=self.microwave_frequency,
                                                            phase=phase,
                                                            filename_amplitude=filename_amplitude,
                                                            filename_phase=filename_phase,
                                                            folder_path=folder_path)

            if is_oc:
                return oc_mw_element
            return pi_rect_element


        # Create block and append to created_blocks list
        qst_block = PulseBlock(name=name)
        for idx, n_pulses in enumerate(n_array):
            phase = phases[idx % len(phases)]
            phase_init_end = init_end_phases_deg[idx % len(phases)]

            self.log.debug(f"Generating oc_nrep ({dd_type.name}) with n_pi= {n_pulses} oc phase= {phase} deg, "
                           f"init_end_phase= {phase_init_end} deg")

            if init_end_pix != 0:
                qst_block.append(pi_element(pix=init_end_pix, phase=phase_init_end))
            if symmetric_tgap:
                for idx_per_laser in range(n_pulses):
                    phi_i = phase + dd_type.phases[idx_per_laser % len(dd_type.phases)]
                    self.log.debug(f"For sequence n_pulses= {n_pulses}, idx= {idx_per_laser}, phase= {phi_i}")
                    qst_block.extend([gap2_element, pi_element(phase=phi_i, is_oc=True), gap2_element])
            else:
                for idx_per_laser in range(n_pulses):
                    phi_i = phase + dd_type.phases[idx_per_laser % len(dd_type.phases)]
                    qst_block.extend([pi_element(phase=phi_i, is_oc=True), gap_element])
            if init_end_pix != 0:
                # rect init/end pulses are not ideal. Make them X,-X for some pulse error correction
                qst_block.append(pi_element(pix=init_end_pix, phase=phase_init_end + 180))
            elif init_end_pix == 0:
                qst_block.append(pi_element(pix=1, phase=0))
            qst_block.append(laser_element)
            qst_block.append(waiting_element)

            if alternating:
                qst_block.append(laser_element)
                qst_block.append(waiting_element)
            if alternating_end_phase:
                if init_end_pix != 0:
                    qst_block.append(pi_element(pix=init_end_pix, phase=phase_init_end))
                if symmetric_tgap:
                    for idx_per_laser in range(n_pulses):
                        phi_i = phase + dd_type.phases[idx_per_laser % len(dd_type.phases)]
                        qst_block.extend([gap2_element, pi_element(phase=phi_i, is_oc=True), gap2_element])
                else:
                    for idx_per_laser in range(n_pulses):
                        phi_i = phase + dd_type.phases[idx_per_laser % len(dd_type.phases)]
                        qst_block.extend([pi_element(phase=phi_i, is_oc=True), gap_element])
                if init_end_pix != 0:
                    # no X, -X pulse eerror correction possible for alternating_end_phase
                    qst_block.append(pi_element(pix=init_end_pix, phase=phase_init_end + 180 + 180))
                elif init_end_pix == 0:
                    qst_block.append(pi_element(pix=1, phase=0))
                if init_end_pix != 0 and init_end_pix != 0.5:
                    self.log.warning(f"Alternating end_phase only well defined for init_end_pix=0/0.5, not {init_end_pix}.")

            qst_block.append(laser_element)
            qst_block.append(waiting_element)


        # compare against rect pulses (negative x axis)
        for idx, n_pulses in enumerate(n_array):
            phase = phases[idx % len(phases)]
            phase_init_end = init_end_phases_deg[idx % len(phases)]

            if vs_rect_pulse:
                if init_end_pix != 0:
                    qst_block.append(pi_element(pix=init_end_pix, phase=phase_init_end))
                    for idx_per_laser in range(n_pulses):
                        phi_i = phase + dd_type.phases[idx_per_laser % len(dd_type.phases)]
                        qst_block.extend(
                            [gap2_element, pi_element(phase=phi_i, is_oc=False), gap2_element])
                else:
                    for idx_per_laser in range(n_pulses):
                        phi_i = phase + dd_type.phases[idx_per_laser % len(dd_type.phases)]
                        qst_block.extend([pi_element(phase=phi_i, is_oc=False), gap_element])
                if init_end_pix != 0:
                    # rect init/end pulses are not ideal. Make them X,-X for some pulse error correction
                    qst_block.append(pi_element(pix=init_end_pix, phase=phase_init_end + 180))
                qst_block.append(laser_element)
                qst_block.append(waiting_element)

                if alternating:
                    qst_block.append(laser_element)
                    qst_block.append(waiting_element)
                if alternating_end_phase:
                    if init_end_pix != 0:
                        qst_block.append(pi_element(pix=init_end_pix, phase=phase_init_end))
                        for idx_per_laser in range(n_pulses):
                            phi_i = phase + dd_type.phases[idx_per_laser % len(dd_type.phases)]
                            qst_block.extend(
                                [gap2_element, pi_element(phase=phi_i, is_oc=False), gap2_element])
                    else:
                        for idx_per_laser in range(n_pulses):
                            phi_i = phase + dd_type.phases[idx_per_laser % len(dd_type.phases)]
                            qst_block.extend([pi_element(phase=phi_i, is_oc=False), gap_element])
                    if init_end_pix != 0:
                        # no X, -X pulse eerror correction possible for alternating_end_phase
                        qst_block.append(pi_element(pix=init_end_pix, phase=phase_init_end + 180 + 180))
                    elif init_end_pix == 0:
                        qst_block.append(pi_element(pix=1, phase=0))
                    else:
                        pass
                    qst_block.append(laser_element)
                    qst_block.append(waiting_element)


        created_blocks.append(qst_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((qst_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        n_lasers = len(n_array)
        n_lasers = 2*n_lasers if (alternating or alternating_end_phase) else n_lasers
        n_lasers = 2*n_lasers if vs_rect_pulse else n_lasers
        # rect pulses have negative repetition number n
        x_axis = list(n_array)
        x_axis = list(n_array) + list(-n_array) if vs_rect_pulse else x_axis
        block_ensemble.measurement_information['alternating'] = (alternating or alternating_end_phase)
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = x_axis
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('repetitions / #pi', 'Signal')
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