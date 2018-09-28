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


class SSRPredefinedGenerator(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def generate_singleshot_readout(self, name='SSR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=0.1,
                                    mw_cnot_frequency=2.8e9, mw_cnot_phase = 0, mw_cnot_amplitude2=0.1,
                                    mw_cnot_frequency2=2.8e9, mw_cnot_phase2=0, ssr_normalise=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        ### prevent granularity problems
        mw_cnot_rabi_period = self._adjust_to_samplingrate(mw_cnot_rabi_period, 4)


        # get mw pi pulse block
        mw_pi_element = self._get_multiple_mw_element(length=mw_cnot_rabi_period/2,
                                                      increment=0.0,
                                                      amps=mw_cnot_amplitude,
                                                      freqs=mw_cnot_frequency,
                                                      phases=mw_cnot_phase)

        trigger_element = self._get_sync_element()

        readout_element = self._get_readout_element()
        block = PulseBlock(name=name)
        block.append(mw_pi_element)
        block.append(trigger_element)
        block.extend(readout_element)


        if ssr_normalise:
            time_between_trigger = self.laser_length + self.wait_time + self.laser_delay
            if time_between_trigger > self.laser_length * 1.4:
                wait = time_between_trigger - self.laser_length * 2.3
                extra_waiting_element = self._get_idle_element(length=wait*1.2, increment=0)
            mw_pi_element2 = self._get_multiple_mw_element(length=mw_cnot_rabi_period/2,
                                                           increment=0.0,
                                                           amps=mw_cnot_amplitude2,
                                                           freqs=mw_cnot_frequency2,
                                                           phases=mw_cnot_phase2)
            waiting_element = self._get_idle_element(length=self.laser_length + 200e-9, increment=0)

            if time_between_trigger > self.laser_length * 1.4:
                block.append(extra_waiting_element)
#
            block.append(mw_pi_element2)
            block.append(trigger_element)
            block.append(waiting_element)
            block.extend(readout_element)
        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=list(), controlled_variable = [0],
                                        counting_length = self.laser_length * 2.3 if ssr_normalise
                                                         else self.laser_length * 1.4)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences
