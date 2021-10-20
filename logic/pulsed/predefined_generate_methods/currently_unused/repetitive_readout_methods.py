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

class RRPredefinedGeneratorS3(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    non_normalised_safety = 1.4
    normalised_safety = 2.3

    def generate_repetitive_readout(self, name='RR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=0.1,
                                    mw_cnot_frequency=2.8e9, mw_cnot_phase = 0):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()


        ### prevent granularity problems
        rabi_period = self._adjust_to_samplingrate(mw_cnot_rabi_period, 4)


        # get mw pi pulse block
        mw_pi_element = self._get_multiple_mw_element(length=rabi_period/2,
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


        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        controlled_variable = [0],
                                                        counting_length = self.laser_length * 1.4)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences


    def _generate_laser_wait(self, name='laser_wait', laser_length=500e-9, wait_length = 1e-6):
        """ Generates Laser pulse and waiting (idle) time.

        @param str name: Name of the PulseBlockEnsemble
        @param float length: laser duration in seconds
        @param float amp: In case of analogue laser channel this value will be the laser on voltage.

        @return object: the generated PulseBlockEnsemble object.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        # create the laser element
        laser_element = self._get_laser_gate_element(length=laser_length, increment=0)
        waiting_element = self._get_idle_element(length=wait_length, increment=0.0)
        # Create the element list
        block = PulseBlock(name=name)
        block.append(laser_element)
        block.append(waiting_element)
        #block.extend(laser_element, waiting_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False, number_of_lasers=0) # todo: check 0 or 1 laser?
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def _generate_laser_wait_pi_pulse(self, name='laser_wait_pi', tau = 1e-6, laser_length=500e-9, wait_length = 1e-6):
        """ Generates Laser pulse and waiting (idle) time.

        @param str name: Name of the PulseBlockEnsemble
        @param float length: laser duration in seconds
        @param float amp: In case of analogue laser channel this value will be the laser on voltage.

        @return object: the generated PulseBlockEnsemble object.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        # create the laser element
        laser_element = self._get_laser_gate_element(length=laser_length, increment=0)
        waiting_element = self._get_idle_element(length=wait_length, increment=0.0)
        ### prevent granularity problems
        tau = self._adjust_to_samplingrate(tau, 4)
        mw_element = self._get_mw_element(length=tau,
                                          increment=0.0,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0.0)
        # Create the element list
        block = PulseBlock(name=name)
        block.extend([laser_element, waiting_element, mw_element])
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False, number_of_lasers=0)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    def _generate_pi_pulse_trigger_laser_wait(self, name='laser_wait_pi', tau = 1e-6, laser_length=500e-9,
                                             wait_length = 1e-6):
        """ Generates Laser pulse and waiting (idle) time.

        @param str name: Name of the PulseBlockEnsemble
        @param float length: laser duration in seconds
        @param float amp: In case of analogue laser channel this value will be the laser on voltage.

        @return object: the generated PulseBlockEnsemble object.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get readout element
        laser_element = self._get_laser_gate_element(length=laser_length, increment=0)
        waiting_element = self._get_idle_element(length=wait_length, increment=0.0)
        seqtrig_element = self._get_sync_element()

        ### prevent granularity problems
        tau = self._adjust_to_samplingrate(tau, 4)
        mw_element = self._get_mw_element(length=tau,
                                          increment=0.0,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0.0)

        block = PulseBlock(name=name)
        block.extend([mw_element, seqtrig_element, laser_element, waiting_element])
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False, number_of_lasers=0)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_single_mw_pulse_s3(self, name='MW_pulse', tau=1e-6, microwave_amplitude=0.25,
                                    microwave_frequency = 1e6, microwave_phase=0.0):

        # In sequence mode there is a minimum waveform length of 4800 sample. If the pulse is to short add an
        # extra idle time before the pulse to take that into account
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        ### prevent granularity problems
        tau = self._adjust_to_samplingrate(tau, 4)

        mw_element = self._get_mw_element(length=tau,
                                          increment=0.0,
                                          amp=microwave_amplitude,
                                          freq=microwave_frequency,
                                          phase=microwave_phase)

        # Create PulseBlock object
        block = PulseBlock(name=name)
        if tau * self.pulse_generator_settings['sample_rate'] < 4800:
            length_idle = 4800/self.pulse_generator_settings['sample_rate'] -tau
            idle_element = self._get_idle_element(length = length_idle, increment= 0.0)
            block.append(idle_element)

        block.append(mw_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False, number_of_lasers=0)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def _generate_idle(self, name='idle', tau=1e-6):
        """ Generates waiting (idle) time.

        @param str name: Name of the PulseBlockEnsemble
        @param float length_waiting: duration in seconds


        @return object: the generated PulseBlockEnsemble object.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        ### prevent granularity problems
        if tau * self.pulse_generator_settings['sample_rate'] < 4800:
            needed_extra_time = 4800 / self.pulse_generator_settings['sample_rate'] - tau
        else:
            needed_extra_time = 0

        tau = self._adjust_to_samplingrate(tau+needed_extra_time, 4)

        # get the idle element
        idle_element = self._get_idle_element(length=tau, increment=0.0)
        # Create the element list
        block = PulseBlock(name=name)
        block.append(idle_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    def _generate_single_xy8_s3(self, name='XY8', rabi_period = 20e-9, tau=500e-9, microwave_amplitude=0.1,
                               microwave_frequency = 2.8e9, xy8N =1):

        # In sequence mode there is a minimum waveform length of 4800 sample. If the pulse is to short add an
        # extra idle time before the pulse to take that into account
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        ### prevent granularity problems
        rabi_period = self._adjust_to_samplingrate(rabi_period, 8)
        tau = self._adjust_to_samplingrate(tau, 4)

        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0)

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

        tauhalf_element = self._get_idle_element(length = tau/2-rabi_period/4, increment=0.0)
        tau_element = self._get_idle_element(length=tau - rabi_period / 2, increment= 0.0)

        # create XY8-N block element list
        block = PulseBlock(name=name)
        if (tau + xy8N) * self.pulse_generator_settings['sample_rate'] < 4800:
            length_idle = 4800 / self.pulse_generator_settings['sample_rate'] - (tau + xy8N)
            idle_element_extra = self._get_idle_element(length = length_idle, increment = 0.0)
            block.append(idle_element_extra)
        # actual XY8-N sequence
        block.append(pihalf_element)
        block.append(tauhalf_element)
        for n in range(xy8N):
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
            if n != xy8N - 1:
                block.append(tau_element)
        block.append(tauhalf_element)
        block.append(pihalf_element)

        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    def _generate_single_xy8_signal_s3(self, name='XY8', rabi_period = 20e-9, tau=500e-9, xy8N =1,
                                      signal_during_mw = False, lasty=False, signal_amplitude = 1,
                                      signal_frequency=1.0e6, signal_phase = 0.0):

        # In sequence mode there is a minimum waveform length of 4800 sample. If the pulse is to short add an
        # extra idle time before the pulse to take that into account
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        ### prevent granularity problems
        rabi_period = self._adjust_to_samplingrate(rabi_period, 8)
        tau = self._adjust_to_samplingrate(tau, 4)

        if not signal_during_mw:

            # get pihalf element
            pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                                  increment=0.0,
                                                  amp=self.microwave_amplitude,
                                                  freq=self.microwave_frequency,
                                                  phase=0.0)
            if lasty:
                piyhalf_element = self._get_mw_element(length=rabi_period / 4,
                                                       increment=0.0,
                                                       amp=self.microwave_amplitude,
                                                       freq=self.microwave_frequency,
                                                       phase=90.0)

            # get pi elements
            pix_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=0.0)

            piy_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=90.0)

        else:
            # get pihalf element
            pihalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                           increment=0,
                                                           amps=[self.microwave_amplitude, signal_amplitude],
                                                           freqs=[self.microwave_frequency, signal_frequency],
                                                           phases=[0.0, signal_phase])
            if lasty:
                piyhalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                increment=0,
                                                                amps=[self.microwave_amplitude, signal_amplitude],
                                                                freqs=[self.microwave_frequency, signal_frequency],
                                                                phases=[90.0, signal_phase])

            # get pi elements
            pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[self.microwave_amplitude, signal_amplitude],
                                                        freqs=[self.microwave_frequency, signal_frequency],
                                                        phases=[0.0, signal_phase])

            piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[self.microwave_amplitude, signal_amplitude],
                                                        freqs=[self.microwave_frequency, signal_frequency],
                                                        phases=[90.0, signal_phase])

        # get pure interaction elements
        tauhalf_element = self._get_mw_element(length=tau / 2.0 - rabi_period / 4,
                                               increment=0.0,
                                               amp=signal_amplitude,
                                               freq=signal_frequency,
                                               phase=signal_phase)

        tau_element = self._get_mw_element(length=tau - rabi_period / 2,
                                           increment=0.0,
                                           amp=signal_amplitude,
                                           freq=signal_frequency,
                                           phase=signal_phase)

        block = PulseBlock(name=name)
        if (tau + xy8N) * self.pulse_generator_settings['sample_rate'] < 4800:
            length_idle = 4800 / self.pulse_generator_settings['sample_rate'] - (tau + xy8N)
            idle_element_extra = self._get_idle_element(length_idle, 0.0)
            block.append(idle_element_extra)
        # actual XY8-N sequence
        block.append(pihalf_element)
        block.append(tauhalf_element)
        for n in range(xy8N):
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
            if n != xy8N - 1:
                block.append(tau_element)
        block.append(tauhalf_element)
        if lasty:
            block.append(piyhalf_element)
        else:
            block.append(pihalf_element)

        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    def _generate_single_xy4_signal_s3(self, name='XY4', rabi_period = 20e-9, tau=500e-9, xy4N =1,
                                      signal_during_mw = False, lasty=False, signal_amplitude = 1,
                                      signal_frequency=1.0e6, signal_phase = 0.0):

        # In sequence mode there is a minimum waveform length of 4800 sample. If the pulse is to short add an
        # extra idle time before the pulse to take that into account
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        ### prevent granularity problems
        rabi_period = self._adjust_to_samplingrate(rabi_period, 8)
        tau = self._adjust_to_samplingrate(tau, 4)

        if not signal_during_mw:

            pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                                  increment=0.0,
                                                  amp=self.microwave_amplitude,
                                                  freq=self.microwave_frequency,
                                                  phase=0.0)

            if lasty:
                piyhalf_element = self._get_mw_element(length=rabi_period / 4,
                                                       increment=0.0,
                                                       amp=self.microwave_amplitude,
                                                       freq=self.microwave_frequency,
                                                       phase=90.0)

            # get pi elements
            pix_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=0.0)

            piy_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=90.0)

        else:
            pihalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                           increment=0,
                                                           amps=[self.microwave_amplitude, signal_amplitude],
                                                           freqs=[self.microwave_frequency, signal_frequency],
                                                           phases=[0.0, signal_phase])
            if lasty:
                piyhalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                increment=0,
                                                                amps=[self.microwave_amplitude, signal_amplitude],
                                                                freqs=[self.microwave_frequency, signal_frequency],
                                                                phases=[90.0, signal_phase])

            pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[self.microwave_amplitude, signal_amplitude],
                                                        freqs=[self.microwave_frequency, signal_frequency],
                                                        phases=[0.0, signal_phase])

            piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[self.microwave_amplitude, signal_amplitude],
                                                        freqs=[self.microwave_frequency, signal_frequency],
                                                        phases=[90.0, signal_phase])

        # get pure interaction elements
        tauhalf_element = self._get_mw_element(length=tau / 2.0 - rabi_period / 4,
                                               increment=0.0,
                                               amp=signal_amplitude,
                                               freq=signal_frequency,
                                               phase=signal_phase)

        tau_element = self._get_mw_element(length=tau - rabi_period / 2,
                                           increment=0.0,
                                           amp=signal_amplitude,
                                           freq=signal_frequency,
                                           phase=signal_phase)

        block = PulseBlock(name=name)
        if (tau + xy4N) * self.pulse_generator_settings['sample_rate'] < 4800:
            length_idle = 4800 / self.pulse_generator_settings['sample_rate'] - (tau + xy4N)
            idle_element_extra = self._get_idle_element(length_idle, 0.0)
            block.append(idle_element_extra)
        # actual xy4-N sequence
        block.append(pihalf_element)
        block.append(tauhalf_element)
        for n in range(xy4N):
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            if n != xy4N - 1:
                block.append(tau_element)
            block.append(tauhalf_element)
        if lasty:
            block.append(piyhalf_element)
        else:
            block.append(pihalf_element)

        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    def _generate_single_xy4_signal_adapted_readout_s3(self, name='XY4', rabi_period = 20e-9, tau=500e-9, xy4N =1,
                                                      signal_during_mw = False, lasty=False, signal_amplitude = 1,
                                                      signal_frequency=1.0e6, signal_phase = 0.0,
                                                      signal_amplitude_Hz = 1.0e3):

        # In sequence mode there is a minimum waveform length of 4800 sample. If the pulse is to short add an
        # extra idle time before the pulse to take that into account
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        ### prevent granularity problems
        rabi_period = self._adjust_to_samplingrate(rabi_period, 8)
        tau = self._adjust_to_samplingrate(tau, 4)

        # compute the readout_axes:
        detuning = (signal_frequency - 1 / 2 / tau) * 2 * np.pi
        phase = 2 * signal_amplitude_Hz * (1 - np.cos(detuning * tau * 4 * xy4N)) / detuning / 2 / np.pi * 360

        if not signal_during_mw:

            pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                                  increment=0.0,
                                                  amp=self.microwave_amplitude,
                                                  freq=self.microwave_frequency,
                                                  phase=0.0)
            pihalf_readout_element = self._get_mw_element(length=rabi_period / 4,
                                                  increment=0.0,
                                                  amp=self.microwave_amplitude,
                                                  freq=self.microwave_frequency,
                                                  phase=phase)

            pix_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=0.0)

            piy_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=90.0)

        else:
            pihalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                           increment=0,
                                                           amps=[self.microwave_amplitude, signal_amplitude],
                                                           freqs=[self.microwave_frequency, signal_frequency],
                                                           phases=[0.0, signal_phase])

            pihalf_readout_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                           increment=0,
                                                           amps=[self.microwave_amplitude, signal_amplitude],
                                                           freqs=[self.microwave_frequency, signal_frequency],
                                                           phases=[phase, signal_phase])

            pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[self.microwave_amplitude, signal_amplitude],
                                                        freqs=[self.microwave_frequency, signal_frequency],
                                                        phases=[0.0, signal_phase])

            piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[self.microwave_amplitude, signal_amplitude],
                                                        freqs=[self.microwave_frequency, signal_frequency],
                                                        phases=[90.0, signal_phase])

        # get pure interaction elements
        tauhalf_element = self._get_mw_element(length=tau / 2.0 - rabi_period / 4,
                                               increment=0.0,
                                               amp=signal_amplitude,
                                               freq=signal_frequency,
                                               phase=signal_phase)

        tau_element = self._get_mw_element(length=tau - rabi_period / 2,
                                           increment=0.0,
                                           amp=signal_amplitude,
                                           freq=signal_frequency,
                                           phase=signal_phase)

        block = PulseBlock(name=name)
        # additional time to fill up the waveform to 4800 samples if necessary
        if (tau+xy4N) * self.pulse_generator_settings['sample_rate'] < 4800:
            length_idle = 4800/self.pulse_generator_settings['sample_rate'] - (tau+xy4N)
            idle_element_extra = self._get_idle_element(length=length_idle, increment=0.0)
            block.append(idle_element_extra)
        # actual xy4-N sequence
        block.append(pihalf_element)
        block.append(tauhalf_element)
        for n in range(xy4N):
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            block.append(tau_element)
            block.append(pix_element)
            block.append(tau_element)
            block.append(piy_element)
            if n != xy4N - 1:
                block.append(tau_element)
        block.append(tauhalf_element)
        block.append(pihalf_readout_element)

        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    ###########################################################################################################

    def _generate_single_T1_qdyne_s3(self, name='T1_qdyne', rabi_period = 20e-9, tau=1e-6, seq_trig='d_ch1'):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        ### prevent granularity problems
        rabi_period = self._adjust_to_samplingrate(rabi_period, 8)
        tau = self._adjust_to_samplingrate(tau, 4)

        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0.0)
        # get tau element
        tau_element = self._get_trigger_element(length=tau,
                                                increment=0.0,
                                                channels=seq_trig)
        # create single_T1_qdyne block element list
        block = PulseBlock(name=name)
        # block.append(waiting_element)
        block.append(tau_element)
        block.append(pihalf_element)


        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=False,
                                                        controlled_variable=np.array([0]))
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


############################################# SSR experiments ################################################






#######################################     RR #######################################

    def generate_rr_rabi(self, name='RR-Rabi', tau_start=1.0e-9, tau_step=1.0e-9, num_of_points=50,
                         laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6,
                         rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1, rf_cnot_duration=100e-6, rf_cnot_phase=0,
                         mw_cnot_name='MW-CNOT', rr_name='RR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=0.25,
                         mw_cnot_frequency=2.8e9, mw_cnot_phase=0, mw_cnot_amplitude2=1.0, mw_cnot_frequency2=2.8e9,
                         mw_cnot_phase2=0, alternating=True, counts_per_readout=1000):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # generate the Rabi pieces
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list=list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse_s3(name = name_tmp, tau=tau,
                                                 microwave_amplitude=self.microwave_amplitude,
                                                 microwave_frequency=self.microwave_frequency, microwave_phase=0.0)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_rr(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, alternating=alternating, created_blocks=list(), laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', ''), labels=('Tau', 'Signal'),
                                       number_of_lasers=2 * num_of_points if alternating else num_of_points,
                                       counting_length= laser_length * 1.4)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences



    def generate_rr_xy8(self, name='RR-XY8', tau_start=1.0e-9, tau_step=1.0e-9, num_of_points=50, xy8N=1,
                         laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6,
                         rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1, rf_cnot_duration=100e-6, rf_cnot_phase=0,
                         mw_cnot_name='MW-CNOT', rr_name='RR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=0.25,
                        mw_cnot_frequency=2.8e9, mw_cnot_phase=0, mw_cnot_amplitude2=1.0, mw_cnot_frequency2=2.8e9,
                        mw_cnot_phase2=0, alternating=True, counts_per_readout=1000):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # generate the Rabi pieces
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list=list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self._generate_single_xy8_s3(name = name_tmp, tau=tau, microwave_amplitude=self.microwave_amplitude,
                                            microwave_frequency=self.microwave_frequency, xy8N = xy8N)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_rr(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, alternating=alternating, created_blocks=list(), laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', ''), labels=('Tau', 'Signal'),
                                       number_of_lasers=2 * num_of_points if alternating else num_of_points,
                                       counting_length= laser_length * 1.4)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences






    ################################# Generate standard SSR sequence ###########################################

    def _standard_rr(self, created_blocks, created_ensembles, para_list, para_dict):

        created_sequences = list()
        # generate initialization, rf control, and rr_readout)
        created_blocks_tmp, created_ensembles_tmp, laser_wait_list, rf_list1, rf_list2, mw_cnot_list, rr_list, rr_alt_list = \
            self._initalize_rf_rr(laser_name=para_dict['laser_name'], laser_length=para_dict['laser_length'],
                                  wait_length=para_dict['wait_length'], rf_cnot_name=para_dict['rf_cnot_name'],
                                  rf_cnot_duration=para_dict['rf_cnot_duration'], rf_cnot_amp=para_dict['rf_cnot_amp'],
                                  rf_cnot_freq=para_dict['rf_cnot_freq'], rf_cnot_phase=para_dict['rf_cnot_phase'],
                                  mw_cnot_name = para_dict['mw_cnot_name'],
                                  rr_name=para_dict['rr_name'], mw_cnot_rabi_period=para_dict['mw_cnot_rabi_period'],
                                  mw_cnot_amplitude=para_dict['mw_cnot_amplitude'],
                                  mw_cnot_frequency=para_dict['mw_cnot_frequency'],
                                  mw_cnot_phase=para_dict['mw_cnot_phase'],
                                  mw_cnot_amplitude2=para_dict['mw_cnot_amplitude2'],
                                  mw_cnot_frequency2=para_dict['mw_cnot_frequency2'],
                                  mw_cnot_phase2=para_dict['mw_cnot_phase2'],
                                  alternating=para_dict['alternating'],
                                  counts_per_readout=para_dict['counts_per_readout'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(mw_cnot_list.copy())
            element_list.append(rf_list1.copy())
            element_list.append(rf_list2.copy())
            element_list.append(laser_wait_list.copy())
            element_list.append(para_list[ii])
            element_list.append(rf_list1.copy())
            element_list.append(rf_list2.copy())
            element_list.append(laser_wait_list.copy())
            element_list.append(rr_list.copy())
            if para_dict['alternating']:
                element_list.append(mw_cnot_list.copy())
                element_list.append(rf_list1.copy())
                element_list.append(rf_list2.copy())
                element_list.append(laser_wait_list.copy())
                element_list.append(para_list[ii])
                element_list.append(rf_list1.copy())
                element_list.append(rf_list2.copy())
                element_list.append(laser_wait_list.copy())
                element_list.append(rr_alt_list.copy())

        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)

        return created_blocks, created_ensembles, sequence




    #################################### Nuclear control methods ###################################

    def generate_rr_number_sweep(self, name='RR-Number-Sweep', num_of_points=50,
                                  laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6,
                                  rf_cnot_duration=1.0e-6, rf_cnot_amp=0.1, rf_cnot_freq=1.0e6, rf_cnot_phase=0,
                                  mw_cnot_name='MW-CNOT',
                                  rr_name='RR', mw_cnot_rabi_period=20e-6, mw_cnot_amplitude=0.25,
                                  mw_cnot_frequency=2.8e9, mw_cnot_phase=0, mw_cnot_amplitude2=1.0,
                                  mw_cnot_frequency2=2.8e9,  mw_cnot_phase2=0, alternating=False, counts_per_readout=1):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()
        para_dict['counts_per_readout'] = counts_per_readout * num_of_points

        number_array = counts_per_readout/2.0 + np.arange(num_of_points) * counts_per_readout

        # get the RF pulse
        created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
            self.generate_chopped_rf_pulse(name='RF', rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp, rf_freq=rf_cnot_freq,
                                   rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        para_list = list()
        para_list.append([list1, list2])

        created_blocks, created_ensembles, sequence = \
            self._nuclear_manipulation_rr(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=alternating, laser_ignore_list=list(),
                                       controlled_variable=number_array, units=('#', ''), labels=('readouts', 'Signal'),
                                       number_of_lasers=2 * num_of_points if alternating else num_of_points,
                                       counting_length=laser_length * 1.4)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences


    def generate_rr_nuclear_odmr(self, name='Nuclear-ODMR', freq_start=1.0e6, freq_step=1.0e3, num_of_points=5,
                                 laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6,
                                 rf_duration=100.0e-6, rf_amp=0.1, rf_phase=0, mw_cnot_name='MW-CNOT',
                                 rr_name='RR', mw_cnot_rabi_period=20e-6, mw_cnot_amplitude=0.25,
                                 mw_cnot_frequency=2.8e9, mw_cnot_phase=0, mw_cnot_amplitude2=0.1,
                                 mw_cnot_frequency2=2.8e9,  mw_cnot_phase2=0, alternating=True,
                                 counts_per_readout=1):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # generate the RF-Rabi pieces
        freq_array = freq_start + np.arange(num_of_points) * freq_step
        para_list=list()
        for number, freq in enumerate(freq_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse(name=name_tmp, rf_duration=rf_duration, rf_amp=rf_amp, rf_freq=freq, rf_phase=rf_phase)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])

        created_blocks, created_ensembles, sequence = \
            self._nuclear_manipulation_rr(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=alternating, laser_ignore_list=list(),
                                       controlled_variable=freq_array, units=('Hz', ''), labels=('Frequency', 'Signal'),
                                       number_of_lasers=2*num_of_points if alternating else num_of_points,
                                       counting_length=laser_length * 1.4)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences



    def generate_rr_nuclear_rabi(self, name='Nuclear-Rabi', tau_start=1.0e-9, tau_step=1.0e-9, num_of_points=50,
                                  laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6,
                                  rf_freq=1.0e6, rf_amp=0.1, rf_phase=0, mw_cnot_name='MW-CNOT',
                                  rr_name='RR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=0.25,
                                  mw_cnot_frequency=2.8e9, mw_cnot_phase=0, mw_cnot_amplitude2=1.0,
                                  mw_cnot_frequency2=2.8e9, mw_cnot_phase2=0, alternating=True,
                                  counts_per_readout=1):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # generate the RF-Rabi pieces
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list=list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse(name = name_tmp, rf_duration=tau, rf_amp=rf_amp, rf_freq=rf_freq, rf_phase=rf_phase)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])

        created_blocks, created_ensembles, sequence = \
            self._nuclear_manipulation_rr(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating = alternating, laser_ignore_list = list(),
                                       controlled_variable = tau_array, units=('s', ''), labels=('Tau', 'Signal'),
                                       number_of_lasers=2 * num_of_points if alternating else num_of_points,
                                       counting_length= laser_length * 1.4)

        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences




############################################# Standard nuclear manipulstion #####################################

    def _nuclear_manipulation_rr(self, created_blocks, created_ensembles, para_list, para_dict):

        # generate initialization, and rr_readout)
        created_blocks_tmp, created_ensembles_tmp, laser_wait_list, mw_cnot_list, mw_cnot_alt_list, rr_list, rr_alt_list= \
            self._initialize_rr(laser_name=para_dict['laser_name'], laser_length=para_dict['laser_length'],
                                wait_length=para_dict['wait_length'],
                                mw_cnot_name=para_dict['mw_cnot_name'], rr_name=para_dict['rr_name'],
                                mw_cnot_rabi_period=para_dict['mw_cnot_rabi_period'],
                                mw_cnot_amplitude=para_dict['mw_cnot_amplitude'],
                                mw_cnot_frequency=para_dict['mw_cnot_frequency'],
                                mw_cnot_phase=para_dict['mw_cnot_phase'],
                                mw_cnot_amplitude2=para_dict['mw_cnot_amplitude2'],
                                mw_cnot_frequency2=para_dict['mw_cnot_frequency2'],
                                mw_cnot_phase2=para_dict['mw_cnot_phase2'],
                                alternating=para_dict['alternating'],
                                counts_per_readout=para_dict['counts_per_readout'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(mw_cnot_list.copy())
            element_list.append(para_list[ii][0])
            element_list.append(para_list[ii][1])
            element_list.append(rr_list.copy())
            if para_dict['alternating']:
                element_list.append(mw_cnot_alt_list.copy())
                element_list.append(para_list[ii][0])
                element_list.append(para_list[ii][1])
                element_list.append(rr_alt_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)

        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)

        return created_blocks, created_ensembles, sequence


############################################ Helper methods ##################################################


    def _initalize_rf_rr(self, laser_name, laser_length, wait_length, rf_cnot_name, rf_cnot_duration, rf_cnot_amp,
                         rf_cnot_freq, rf_cnot_phase, mw_cnot_name,
                         rr_name, mw_cnot_rabi_period, mw_cnot_amplitude, mw_cnot_frequency, mw_cnot_phase,
                         mw_cnot_amplitude2, mw_cnot_frequency2, mw_cnot_phase2, alternating,
                         counts_per_readout):
        # standard sequence for repetitive readout.

        created_blocks = list()
        created_ensembles = list()

        # Add the laser wait
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self._generate_laser_wait(name=laser_name, laser_length=laser_length, wait_length=wait_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        laser_wait_list = [laser_name, seq_param]

        # Add RF pulse
        created_blocks_tmp, created_ensembles_tmp, rf_list1, rf_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                   rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp


        # Add MW-CNOT
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_mw_pulse_s3(name=mw_cnot_name, tau=mw_cnot_rabi_period/2, microwave_amplitude=mw_cnot_amplitude,
                                             microwave_frequency=mw_cnot_frequency, microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add RR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_repetitive_readout(name=rr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
        rr_list = [rr_name, seq_param]

        if alternating:
            # Add alternating part if required
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_repetitive_readout(name=rr_name + '_alt', mw_cnot_rabi_period=mw_cnot_rabi_period,
                                                 mw_cnot_amplitude=mw_cnot_amplitude2,
                                                 mw_cnot_frequency=mw_cnot_frequency2,
                                                 mw_cnot_phase=mw_cnot_phase2)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
            rr_alt_list = [rr_name + '_alt', seq_param]
        else:
            rr_alt_list = []

        return created_blocks, created_ensembles, laser_wait_list, rf_list1, rf_list2, mw_cnot_list, rr_list, rr_alt_list

    def _initialize_rr(self, laser_name, laser_length, wait_length, mw_cnot_name, rr_name, mw_cnot_rabi_period,
                       mw_cnot_amplitude, mw_cnot_frequency, mw_cnot_phase, mw_cnot_amplitude2, mw_cnot_frequency2,
                       mw_cnot_phase2, alternating, counts_per_readout):

        created_blocks = list()
        created_ensembles = list()

        # Add the laser initialization
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self._generate_laser_wait(name=laser_name, laser_length=laser_length, wait_length=wait_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        laser_wait_list = [laser_name, seq_param]

        # Add MW-CNOT
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_mw_pulse_s3(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2,
                                              microwave_amplitude=mw_cnot_amplitude,
                                              microwave_frequency=mw_cnot_frequency, microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        if alternating:
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse_s3(name=mw_cnot_name+'_alt', tau=mw_cnot_rabi_period / 2,
                                                  microwave_amplitude=mw_cnot_amplitude2,
                                                  microwave_frequency=mw_cnot_frequency2,
                                                  microwave_phase=mw_cnot_phase2)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            mw_cnot_alt_list = [mw_cnot_name+'_alt', seq_param]
        else:
            mw_cnot_alt_list = []

        # Add RR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_repetitive_readout(name=rr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
        rr_list = [rr_name, seq_param]

        if alternating:
            # Add alternating part if required
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_repetitive_readout(name=rr_name + '_alt', mw_cnot_rabi_period=mw_cnot_rabi_period,
                                                 mw_cnot_amplitude=mw_cnot_amplitude2,
                                                 mw_cnot_frequency=mw_cnot_frequency2,
                                                 mw_cnot_phase=mw_cnot_phase2)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
            rr_alt_list = [rr_name+'_alt', seq_param]
        else:
            rr_alt_list = []

        return created_blocks, created_ensembles, laser_wait_list, mw_cnot_list, mw_cnot_alt_list, rr_list, rr_alt_list


    def generate_chopped_rf_pulse(self, name, rf_duration, rf_amp, rf_freq, rf_phase):
        # analyse the rf pulse
        rf_dict = self._analyse_rf_pulse(rf_duration, rf_freq)
        # generate first part of rf pulse
        if rf_dict['number_periods'] > 0:
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse_s3(name=name+'1', tau=rf_dict['period'], microwave_amplitude=rf_amp,
                                                 microwave_frequency=rf_freq, microwave_phase=rf_phase)
        else:
            # If there is not more than 1 period just makes this an idle with minimal length
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self._generate_idle(name=name + '1', tau=4800/self.pulse_generator_settings['sample_rate'])
            # set it to 1 so it is repeated at least once
            rf_dict['number_periods'] = 1
        created_blocks = created_blocks_tmp
        created_ensembles = created_ensembles_tmp
        # add sequence parameters
        seq_param = self._customize_seq_para({'repetitions': rf_dict['number_periods']-1})
        list1 = [name+'1', seq_param]

        # generate second part of rf pulse
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_mw_pulse_s3(name=name+'2', tau=rf_dict['remainder'], microwave_amplitude=rf_amp,
                                             microwave_frequency=rf_freq, microwave_phase=rf_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        # add sequence parameters
        seq_param2 = self._customize_seq_para({})
        list2 = [name+'2', seq_param2]

        return created_blocks, created_ensembles, list1, list2

    def generate_chopped_rf_pulse2(self, name='RF', rf_duration=10e-6, rf_amp=0.01, rf_freq=1.0e6, rf_phase=0.0):
        # Here the difference is that the poeriod is sampled only once, which saves time for example for Rabi
        # analyse the rf pulse
        rf_dict = self._analyse_rf_pulse(rf_duration, rf_freq)
        # generate first part of rf pulse
        if rf_dict['number_periods'] > 0:
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse_s3(name=name[:-2], tau=rf_dict['period'], microwave_amplitude=rf_amp,
                                                 microwave_frequency=rf_freq, microwave_phase=rf_phase)
            created_blocks = created_blocks_tmp
            created_ensembles = created_ensembles_tmp
            # add sequence parameters
            seq_param = self._customize_seq_para({'repetitions': rf_dict['number_periods'] - 1})
            list1 = [name[:-2], seq_param]
        else:
            # If there is not more than 1 period just makes this an idle with minimal length
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self._generate_idle(name=name[:-2], tau=4800/self.pulse_generator_settings['sample_rate'])
            # set it to 1 so it is repeated at least once
            rf_dict['number_periods'] = 1
            created_blocks = created_blocks_tmp
            created_ensembles = created_ensembles_tmp
            # add sequence parameters
            seq_param = self._customize_seq_para({'repetitions': rf_dict['number_periods']-1})
            list1 = [name+'1', seq_param]

        # generate second part of rf pulse
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_mw_pulse_s3(name=name+'2', tau=rf_dict['remainder'], microwave_amplitude=rf_amp,
                                             microwave_frequency=rf_freq, microwave_phase=rf_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        # add sequence parameters
        seq_param2 = self._customize_seq_para({})
        list2 = [name+'2', seq_param2]

        return created_blocks, created_ensembles, list1, list2

    def _analyse_rf_pulse(self, rf_duration, rf_freq):
        rf_dict={'rf_duration': rf_duration}
        rf_dict['rf_freq'] = rf_freq
        period = 1.0/rf_freq
        # multiplicity has to be two to avoid granularity problems  with AWG
        rf_dict['period'] = self._adjust_to_samplingrate(period, 2)
        rf_dict['number_periods'] = int(rf_duration / period) - 1
        if rf_dict['number_periods'] > 0:
            remainder = rf_duration % rf_dict['period']
            remainder = self._adjust_to_samplingrate(remainder + rf_dict['period'], 2)
        else:
            remainder = self._adjust_to_samplingrate(rf_duration, 2)
        # this helps to prevent granularity problems
        rf_dict['remainder'] = remainder + 1e-12
        return rf_dict

    def _customize_seq_para(self, seq_para_dict):
        if 'event_trigger' not in seq_para_dict:
            seq_para_dict['event_trigger'] = 'OFF'
        if 'event_jump_to' not in seq_para_dict:
            seq_para_dict['event_jump_to'] = 0
        if 'wait_for' not in seq_para_dict:
            seq_para_dict['wait_for'] = 'OFF'
        if 'repetitions' not in seq_para_dict:
            seq_para_dict['repetitions'] = 0
        if 'go_to' not in seq_para_dict:
            seq_para_dict['go_to'] = 0
        return seq_para_dict

    def _make_sequence_continous(self, element_list):
        # change the goto key of the last list in element_list to 1
        tmp_dict = dict(element_list[-1][1])
        tmp_dict['go_to'] = 1
        element_list[-1][1] = tmp_dict
        return element_list



##################################### Methods for initalized nuclear spin #########################################################


    def generate_initializedRFrabi(self, name='rabi', tau_start=10.0e-9, tau_step=10.0e-9, num_of_points=50,
                                   rf_frequency = 1.0e6, rf_amplitude= 0.1,
                                   mw_cnot_rabi_period= 100e-9, mw_cnot_frequency = 3.0e9, mw_cnot_amplitude = 0.1,
                                   alternating=False, hyperfine=3.03e6, n1state=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the laser_mw element
        rf_element = self._get_mw_element(length=tau_start,
                                          increment=tau_step,
                                          amp=rf_amplitude,
                                          freq=rf_frequency,
                                          phase=0)
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        mw_cnot_element = self._get_mw_element(length=mw_cnot_rabi_period / 2,
                                               increment=0,
                                               amp=mw_cnot_amplitude,
                                               freq=mw_cnot_frequency,
                                               phase=0)
        if alternating:
            mw_cnot_element2 = self._get_mw_element(length=mw_cnot_rabi_period / 2,
                                                   increment=0,
                                                   amp=mw_cnot_amplitude,
                                                   freq=mw_cnot_frequency+hyperfine,
                                                   phase=0)


        short_wait_element = self._get_idle_element(length=1e-6, increment=0)

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        if n1state:
            rabi_block.append(mw_cnot_element)
        rabi_block.append(short_wait_element)
        rabi_block.append(rf_element)
        rabi_block.append(short_wait_element)
        rabi_block.append(mw_cnot_element)
        rabi_block.append(laser_element)
        rabi_block.append(delay_element)
        rabi_block.append(waiting_element)
        if alternating:
            if n1state:
                rabi_block.append(mw_cnot_element2)
            rabi_block.append(short_wait_element)
            rabi_block.append(rf_element)
            rabi_block.append(short_wait_element)
            rabi_block.append(mw_cnot_element2)
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
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = num_of_points*2 if alternating else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_initializedRFodmr(self, name='RF-ODMR', freq_start=2870.0e3, freq_step=0.2e3,
                                   rf_period=100e-6, rf_amplitude = 0.1, num_of_points=50,
                                   mw_cnot_rabi_period= 100e-9, mw_cnot_frequency= 3.0e9,   mw_cnot_amplitude = 0.1,
                                   alternating = False, hyperfine=3.03e-6, n1state=True):
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

        mw_cnot_element = self._get_mw_element(length=mw_cnot_rabi_period / 2,
                                              increment=0,
                                              amp=mw_cnot_amplitude,
                                              freq=mw_cnot_frequency,
                                              phase=0)
        if alternating:
            mw_cnot_element2 = self._get_mw_element(length=mw_cnot_rabi_period / 2,
                                                   increment=0,
                                                   amp=mw_cnot_amplitude,
                                                   freq=mw_cnot_frequency+hyperfine,
                                                   phase=0)

        short_wait_element = self._get_idle_element(length=1e-6, increment=0)

        # Create block and append to created_blocks list
        pulsedodmr_block = PulseBlock(name=name)
        for rf_freq in freq_array:
            rf_element = self._get_mw_element(length=rf_period / 2,
                                              increment=0,
                                              amp=rf_amplitude,
                                              freq=rf_freq,
                                              phase=0)
            if n1state:
                pulsedodmr_block.append(mw_cnot_element)
            pulsedodmr_block.append(short_wait_element)
            pulsedodmr_block.append(rf_element)
            pulsedodmr_block.append(short_wait_element)
            pulsedodmr_block.append(mw_cnot_element)
            pulsedodmr_block.append(laser_element)
            pulsedodmr_block.append(delay_element)
            pulsedodmr_block.append(waiting_element)
            if alternating:
                if n1state:
                    pulsedodmr_block.append(mw_cnot_element2)
                pulsedodmr_block.append(rf_element)
                pulsedodmr_block.append(short_wait_element)
                pulsedodmr_block.append(mw_cnot_element2)
                pulsedodmr_block.append(laser_element)
                pulsedodmr_block.append(delay_element)
                pulsedodmr_block.append(waiting_element)
        created_blocks.append(pulsedodmr_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((pulsedodmr_block.name, 0))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = num_of_points*2 if alternating else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences