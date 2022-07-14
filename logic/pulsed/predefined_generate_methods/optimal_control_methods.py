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

    def generate_sts_oc(self, name='stsoc', length=99e-9, filename_amplitude='amplitude', filename_phase='phase',
                        folder_path=r'C:\Users\Mesoscopic\Desktop\Redcrab_data'):
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
