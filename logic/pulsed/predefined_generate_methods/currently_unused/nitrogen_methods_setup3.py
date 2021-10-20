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

class SSRPredefinedGeneratorS3(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_nitrogen_rabi_s3(self, qm_dict='None'):
        """
        Do a Rabi on the nitrogen nuclear spins. It can be chosen whether to apply a MW pi-pulse or a RF pi-pulse
        to change the electron or nuclear spin before.
        """

        # get tau array for measurement ticks
        tau_array = qm_dict['tau_start'] + np.arange(num_of_points) * tau_step


        # get waiting element
        waiting_element = self._get_idle_element_s3(100e-6, 0.0)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element_s3(qm_dict['laser_length'], 0.0, qm_dict['delay_length'],
                                                                  qm_dict['channel_amp'], qm_dict['gate'])
        if qm_dict['seq_trig'] != '':
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element_s3(qm_dict['trigger_length'], 0.0, qm_dict['seq_trig'],
                                                           amp=qm_dict['channel_amp'])
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)

        if qm_dict['NV_pi_pulse']:
            mw_pi_element = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0 , qm_dict['mw_channel'],
                                                    mw_amp, mw_freq, 0.0)
            if alternating:
                mw_pi_element2 = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
                                                        mw_amp, mw_freq+qm_dict['hyperfine'], 0.0)
        if qm_dict['nitrogen']=='14' and qm_dict['N0+1_pi_pulse']:
            rf_pi_element = self._get_mw_element_s3(qm_dict['N0+1_rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
                                                    qm_dict['N0+1_rf_amp'], qm_dict['N0+1_rf_freq'], 0.0)

        # Create element list for Rabi PulseBlock
        element_list = []

        for tau in tau_array:

            if qm_dict['NV_pi_pulse']:
                element_list.append(mw_pi_element)
            if qm_dict['nitrogen']=='14' and qm_dict['N0+1_pi_pulse']:
                element_list.append(rf_pi_element)
            # get MW element
            rf_element = self._get_mw_element_s3(tau, 0, qm_dict['mw_channel'],
                                                 qm_dict['rf_amp'], qm_dict['rf_freq'], 0.0)
            element_list.append(rf_element)
            if qm_dict['nitrogen']=='14' and qm_dict['N0+1_pi_pulse']:
                element_list.append(rf_pi_element)
            if qm_dict['NV_pi_pulse']:
                element_list.append(mw_pi_element)
            element_list.extend([laser_element, delay_element, waiting_element])

            if alternating:

                if qm_dict['NV_pi_pulse']:
                    element_list.append(mw_pi_element2)
                if qm_dict['nitrogen']=='14' and qm_dict['N0+1_pi_pulse']:
                    element_list.append(rf_pi_element)
                # get MW element
                rf_element = self._get_mw_element_s3(tau, 0, qm_dict['mw_channel'],
                                                     qm_dict['rf_amp'], qm_dict['rf_freq'], 0.0)
                element_list.append(rf_element)
                if qm_dict['nitrogen']=='14' and qm_dict['N0+1_pi_pulse']:
                    element_list.append(rf_pi_element)
                if qm_dict['NV_pi_pulse']:
                    element_list.append(mw_pi_element2)
                element_list.extend([laser_element, delay_element, waiting_element])

        # Create PulseBlock object
        rabi_block = PulseBlock(name, element_list)
        # save block
        self.save_block(name, rabi_block)

        # Create Block list with repetitions and sequence trigger if needed.
        # remember num_of_points=0 also counts as first round.
        block_list = [(rabi_block, 0)]
        if qm_dict['seq_trig'] != '':
            block_list.insert(0,(seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        # add metadata to invoke settings later on
        block_ensemble = self._invoke_settings(block_ensemble, controlled_vals_array=tau_array, alternating = alternating)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    def generate_nitrogen_odmr_s3(self, qm_dict='None'):
        """
        Sweep RF pi pulse on nuclear spin. At GSLAC, contrast signal is due to flip-flops between nuclear
        spin and NV electron spin. Away from GSLAC the alternating sequence with MW-pi pulses polarises the
        nuclear spin to create contrast
        """

        # get waiting element
        waiting_element = self._get_idle_element_s3(2*qm_dict['nitrogen_rabi_period'], 0.0)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element_s3(qm_dict['laser_length'], 0.0, qm_dict['delay_length'],
                                                                  qm_dict['channel_amp'], qm_dict['gate'])
        if qm_dict['nitrogen'] == '14' and qm_dict['nitrogen_pi_pulse']:
            nitrogen_pi = self._get_mw_element_s3(qm_dict['N0+1_rabi_period'] / 2, 0.0 , qm_dict['mw_channel'],
                                                  qm_dict['rf_amp'], qm_dict['N0+1_freq'], 0.0)

        if qm_dict['NV_pi_pulse']: #Do a pi pulse on NV center to initialise to |1> state
            # get MW element
            mw_element = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0 , qm_dict['mw_channel'],
                                                 mw_amp, mw_freq, 0.0)

            if alternating:
                mw_element2 = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0 , qm_dict['mw_channel'],
                                                 mw_amp, mw_freq+qm_dict['hyperfine'], 0.0)

        if qm_dict['seq_trig'] != '':
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element_s3(qm_dict['trigger_length'], 0.0, qm_dict['seq_trig'], amp=qm_dict['channel_amp'])
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)

        # Create frequency list array
        freq_array = qm_dict['rf_freq_start'] + np.arange(num_of_points) * qm_dict['rf_freq_incr']

        # Create element list for PulsedODMR PulseBlock
        element_list = []
        for rf_freq in freq_array:
            rf_element = self._get_mw_element_s3(qm_dict['nitrogen_rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
                                                 qm_dict['rf_amp'], rf_freq, 0.0)
            if qm_dict['NV_pi_pulse']:
                element_list.append(mw_element)
            if qm_dict['nitrogen'] == '14' and qm_dict['nitrogen_pi_pulse']:
                element_list.append(nitrogen_pi)
            element_list.append(rf_element)
            if qm_dict['nitrogen'] == '14' and qm_dict['nitrogen_pi_pulse']:
                element_list.append(nitrogen_pi)
            if qm_dict['NV_pi_pulse']:
               element_list.append(mw_element)
            element_list.append(laser_element)
            element_list.append(delay_element)
            element_list.append(waiting_element)

            if alternating:

                if qm_dict['NV_pi_pulse']:
                    element_list.append(mw_element2)
                if qm_dict['nitrogen'] == '14' and qm_dict['nitrogen_pi_pulse']:
                    element_list.append(nitrogen_pi)
                element_list.append(rf_element)
                if qm_dict['nitrogen'] == '14' and qm_dict['nitrogen_pi_pulse']:
                    element_list.append(nitrogen_pi)
                if qm_dict['NV_pi_pulse']:
                    element_list.append(mw_element2)
                element_list.append(laser_element)
                element_list.append(delay_element)
                element_list.append(waiting_element)

        # Create PulseBlock object
        pulsedodmr_block = PulseBlock(name, element_list)
        # save block
        self.save_block(name, pulsedodmr_block)

        # Create Block list with repetitions and sequence trigger if needed.
        # remember num_of_points=0 also counts as first round.
        block_list = [(pulsedodmr_block, 0)]
        if qm_dict['seq_trig'] != '':
            block_list.insert(0,(seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        # add metadata to invoke settings later on
        block_ensemble = self._invoke_settings(block_ensemble, controlled_vals_array=freq_array, alternating = alternating)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    def generate_check_rr_number_s3(self, qm_dict='None'):
        """
        # Polarize nucleus with a combination of selective MW and RF pulses and check the decay of polarization
        """

        # get waiting element
        waiting_element = self._get_idle_element_s3(qm_dict['wait_length'], 0.0)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element_s3(qm_dict['laser_length'], 0.0, qm_dict['delay_length'],
                                                                  qm_dict['channel_amp'], qm_dict['gate'])


        mw_element = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0 , qm_dict['mw_channel'],
                                             mw_amp, mw_freq, 0.0)
        mw_element2 = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
                                             mw_amp, mw_freq+3e6, 0.0)

        rf_element = self._get_mw_element_s3(qm_dict['nitrogen_rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
                                             qm_dict['rf_amp'], qm_dict['rf_freq'], 0.0)



        if qm_dict['seq_trig'] != '':
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element_s3(qm_dict['trigger_length'], 0.0, qm_dict['seq_trig'], amp=qm_dict['channel_amp'])
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)



        # Create element list for PulsedODMR PulseBlock
        element_list = []


        for ii in range(qm_dict['number_rr']):

            element_list.append(mw_element2)
            element_list.append(laser_element)
            element_list.append(delay_element)
            element_list.append(waiting_element)

        element_list.append(mw_element)
        element_list.append(rf_element)
        element_list.append(laser_element)
        element_list.append(delay_element)
        element_list.append(waiting_element)


        # Create PulseBlock object
        pulsedodmr_block = PulseBlock(name, element_list)
        # save block
        self.save_block(name, pulsedodmr_block)

        # Create Block list with repetitions and sequence trigger if needed.
        # remember num_of_points=0 also counts as first round.
        block_list = [(pulsedodmr_block, 0)]
        if qm_dict['seq_trig'] != '':
            block_list.insert(0,(seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        # add metadata to invoke settings later on
        block_ensemble = self._invoke_settings(block_ensemble, controlled_vals_array=np.linspace(0,qm_dict['number_rr'],qm_dict['number_rr']+1), alternating = False)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    def generate_nitrogen_T1_s3(self, qm_dict='None'):
        """

        """

        # get waiting element
        waiting_element = self._get_idle_element_s3(qm_dict['wait_length'], 0.0)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element_s3(qm_dict['laser_length'], 0.0, qm_dict['delay_length'],
                                                                  qm_dict['channel_amp'], qm_dict['gate'])

        if qm_dict['initial_pulse'] or alternating:
            # get pi element
            pi_element = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
                                                 mw_amp, mw_freq, 0.0)

            pi_element2 = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
                                                  mw_amp, mw_freq+3.0e6, 0.0)

        if qm_dict['initial_pulse']:
            #Create initial laser PulseBlock
            initial_block = self._get_inital_element(alternating, laser_element, delay_element, waiting_element,
                                                     pi_element)
        if qm_dict['seq_trig'] != '':
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element_s3(qm_dict['trigger_length'], 0.0, qm_dict['seq_trig'],
                                                           amp=qm_dict['channel_amp'])
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)

        if qm_dict['exp_incr']:
            # get tau array for measurement ticks
            if qm_dict['tau_start'] == 0.0:
                tau_array = np.geomspace(1e-9, qm_dict['tau_end'], num_of_points - 1)
                tau_array = np.insert(tau_array, 0, 0.0)
            else:
                tau_array = np.geomspace(qm_dict['tau_start'], qm_dict['tau_end'], num_of_points)

            # Create element list for PulsedODMR PulseBlock
            element_list = []
            for tau in tau_array:
                tau_element = self._get_idle_element_s3(tau, 0.0)

                element_list.append(tau_element)
                element_list.append(laser_element)
                element_list.append(delay_element)
                element_list.append(waiting_element)

                if alternating:

                    element_list.append(pi_element)
                    element_list.append(tau_element)
                    element_list.append(pi_element)
                    element_list.append(laser_element)
                    element_list.append(delay_element)
                    element_list.append(waiting_element)

            # Create PulseBlock object
            T1_block = PulseBlock(name, element_list)
            # save block
            self.save_block(name, T1_block)

            # Create Block list with repetitions and sequence trigger if needed.
            block_list = [(T1_block, 0)]

        else:
            # get tau array for measurement ticks
            tau_array = qm_dict['tau_start'] + np.arange(num_of_points) * tau_step
            # get tau element
            tau_element = self._get_idle_element_s3(qm_dict['tau_start'], tau_step)

            # Create element list for T1 PulseBlock
            element_list = []
            element_list.append(tau_element)
            element_list.append(laser_element)
            element_list.append(delay_element)
            element_list.append(waiting_element)

            if alternating:

                element_list.append(pi_element)
                element_list.append(tau_element)
                element_list.append(pi_element)
                element_list.append(laser_element)
                element_list.append(delay_element)
                element_list.append(waiting_element)

            # Create PulseBlock object
            T1_block = PulseBlock(name, element_list)
            # save block
            self.save_block(name, T1_block)

            # Create Block list with repetitions and sequence trigger if needed.
            # remember num_of_points=0 also counts as first round.
            block_list = [(T1_block, num_of_points - 1)]

        if qm_dict['initial_pulse']:
            block_list.insert(0, (initial_block, 0))
            tau_array = np.insert(tau_array, 0, 0.0)
        if qm_dict['seq_trig'] != '':
            block_list.insert(0,(seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
        # add metadata to invoke settings later on
        block_ensemble = self._invoke_settings(block_ensemble, alternating=alternating, controlled_vals_array=tau_array)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    # def generate_T1_nitrogen_s3(self, qm_dict='None'):
    #     """
    #
    #     """
    #
    #     # get waiting element
    #     waiting_element = self._get_idle_element_s3(qm_dict['wait_length'], 0.0)
    #     # get laser and delay element
    #     laser_element, delay_element = self._get_laser_element_s3(qm_dict['laser_length'], 0.0, qm_dict['delay_length'],
    #                                                            qm_dict['channel_amp'], qm_dict['gate'])
    #
    #     if qm_dict['initial_pulse'] or alternating:
    #         # get pi element
    #         pi_element = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
    #                                              mw_amp, mw_freq, 0.0)
    #
    #         pi_element2 = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
    #                                              mw_amp, mw_freq+3.0e6, 0.0)
    #
    #     if qm_dict['initial_pulse']:
    #         #Create initial laser PulseBlock
    #         initial_block = self._get_inital_element(alternating, laser_element, delay_element, waiting_element, pi_element)
    #     if qm_dict['seq_trig'] != '':
    #         # get sequence trigger element
    #         seqtrig_element = self._get_trigger_element_s3(qm_dict['trigger_length'], 0.0, qm_dict['seq_trig'], amp=qm_dict['channel_amp'])
    #         # Create its own block out of the element
    #         seq_block = PulseBlock('seq_trigger', [seqtrig_element])
    #         # save block
    #         self.save_block('seq_trigger', seq_block)
    #
    #     if qm_dict['exp_incr']:
    #         # get tau array for measurement ticks
    #         if qm_dict['tau_start'] == 0.0:
    #             tau_array = np.geomspace(1e-9, qm_dict['tau_end'], num_of_points - 1)
    #             tau_array = np.insert(tau_array, 0, 0.0)
    #         else:
    #             tau_array = np.geomspace(qm_dict['tau_start'], qm_dict['tau_end'], num_of_points)
    #
    #         # Create element list for PulsedODMR PulseBlock
    #         element_list = []
    #         for tau in tau_array:
    #             tau_element = self._get_idle_element_s3(tau, 0.0)
    #
    #             element_list.append(tau_element)
    #             element_list.append(laser_element)
    #             element_list.append(delay_element)
    #             element_list.append(waiting_element)
    #
    #             if alternating:
    #
    #                 element_list.append(pi_element)
    #                 element_list.append(tau_element)
    #                 element_list.append(pi_element)
    #                 element_list.append(laser_element)
    #                 element_list.append(delay_element)
    #                 element_list.append(waiting_element)
    #
    #         # Create PulseBlock object
    #         T1_block = PulseBlock(name, element_list)
    #         # save block
    #         self.save_block(name, T1_block)
    #
    #         # Create Block list with repetitions and sequence trigger if needed.
    #         block_list = [(T1_block, 0)]
    #
    #     else:
    #         # get tau array for measurement ticks
    #         tau_array = qm_dict['tau_start'] + np.arange(num_of_points) * tau_step
    #         # get tau element
    #         tau_element = self._get_idle_element_s3(qm_dict['tau_start'], tau_step)
    #
    #         # Create element list for T1 PulseBlock
    #         element_list = []
    #         element_list.append(tau_element)
    #         element_list.append(laser_element)
    #         element_list.append(delay_element)
    #         element_list.append(waiting_element)
    #
    #         if alternating:
    #
    #             element_list.append(pi_element)
    #             element_list.append(tau_element)
    #             element_list.append(pi_element)
    #             element_list.append(laser_element)
    #             element_list.append(delay_element)
    #             element_list.append(waiting_element)
    #
    #         # Create PulseBlock object
    #         T1_block = PulseBlock(name, element_list)
    #         # save block
    #         self.save_block(name, T1_block)
    #
    #         # Create Block list with repetitions and sequence trigger if needed.
    #         # remember num_of_points=0 also counts as first round.
    #         block_list = [(T1_block, num_of_points - 1)]
    #
    #     if qm_dict['initial_pulse']:
    #         block_list.insert(0, (initial_block, 0))
    #         tau_array = np.insert(tau_array, 0, 0.0)
    #     if qm_dict['seq_trig'] != '':
    #         block_list.insert(0,(seq_block, 0))
    #
    #     # create ensemble out of the block(s)
    #     block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
    #     # add metadata to invoke settings later on
    #     block_ensemble = self._invoke_settings(block_ensemble, alternating=alternating, controlled_vals_array=tau_array)
    #     # save ensemble
    #     self.save_ensemble(name, block_ensemble)
    #     return block_ensemble


    ########################################################################################################################


    def generate_single_nitrogen_rabi_s3(self, qm_dict='None'):
        """
        Do a Rabi on the nitrogen nuclear spins. It can be chosen whether to apply a MW pi-pulse or a RF pi-pulse
        to change the electron or nuclear spin before.
        """

        ### prevent granularity problems
        tau = self._adjust_to_samplingrate(tau, 4)
        length = tau

        if tau != 0:
            rf_element = self._get_mw_element_s3(tau, 0, qm_dict['mw_channel'], mw_amp, mw_freq, 0.0)

        if qm_dict['NV_pi_pulse']:
            mw_pi_element = self._get_mw_element_s3(qm_dict['rabi_period'] / 2, 0.0 , qm_dict['mw_channel'],
                                                    mw_amp, mw_freq, 0.0)
            length += qm_dict['rabi_period'] / 2
        if qm_dict['nitrogen']=='14' and qm_dict['N0+1_pi_pulse']:
            rf_pi_element = self._get_mw_element_s3(qm_dict['N0+1_rabi_period'] / 2, 0.0, qm_dict['mw_channel'],
                                                    qm_dict['N0+1_rf_amp'], qm_dict['N0+1_rf_freq'], 0.0)
            length += qm_dict['N0+1_rabi_period'] / 2

        if qm_dict['NV_pi_pulse']:
            element_list.append(mw_pi_element)
        if qm_dict['nitrogen']=='14' and qm_dict['N0+1_pi_pulse']:
            element_list.append(rf_pi_element)

        ## Create element list for Rabi PulseBlock
        # In sequence mode there is a minimum waveform length of 4800 sample. If the pulse is too short add an
        # extra idle time before the pulse to take that into account
        if length * self.sample_rate < 4800:
            length_idle = 4800 / self.sample_rate - length
            idle_element = self._get_idle_element_s3(length_idle, 0.0)
            if tau != 0:
                element_list = [idle_element, rf_element]
            else:
                element_list = [idle_element]
        else:
            element_list = [rf_element]

        if qm_dict['nitrogen']=='14' and qm_dict['N0+1_pi_pulse']:
            element_list.append(rf_pi_element)
        if qm_dict['NV_pi_pulse']:
            element_list.append(mw_pi_element)

        # Create PulseBlock object
        rabi_block = PulseBlock(name, element_list)
        # save block
        self.save_block(name, rabi_block)

        # Create Block list with repetitions and sequence trigger if needed.
        # remember num_of_points=0 also counts as first round.
        block_list = [(rabi_block, 0)]
        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        # add metadata to invoke settings later on
        block_ensemble = self._invoke_settings(block_ensemble, controlled_vals_array=tau_array,
                                               alternating = alternating)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    def generate_initialize_NV_s3(self, qm_dict='None'):
        """ Generates initialization sequence for NV center(with 15N). Initializes state |0,up>.

        @param str dict: dictionary containing the parameters for the initialization pulses

        @return object: the generated PulseBlockEnsemble object.
        """
        name = name
        # create the laser element
        laser_element, delay_element = self._get_laser_element_s3(qm_dict['laser_length'], 0.0, qm_dict['delay_length'],
                                                                  qm_dict['channel_amp'], qm_dict['gate'])
        waiting_element = self._get_idle_element_s3(qm_dict['wait_length'], 0.0)

        ### prevent granularity problems
        mw_tau = self._adjust_to_samplingrate(qm_dict['mw_rabi_period']/2, 2)
        mw_element = self._get_mw_element_s3(mw_tau, 0, qm_dict['mw_channel'],
                                             mw_amp, mw_freq, 0.0)

        rf_tau = self._adjust_to_samplingrate(qm_dict['rf_rabi_period'] / 2, 2)
        rf_element = self._get_mw_element_s3(rf_tau, 0, qm_dict['mw_channel'],
                                             qm_dict['rf_amp'], qm_dict['rf_freq'], 0.0)

        # Create the element list
        element_list = [mw_element, rf_element, laser_element, delay_element, waiting_element]
        # create the PulseBlock object.
        block = PulseBlock(name, element_list)
        # save block
        self.save_block(name, block)
        # put block in a list with repetitions
        block_list = [(block, 0)]
        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        # add metadata to invoke settings later on
        block_ensemble = self._invoke_settings(block_ensemble, controlled_vals_array=[0])
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    def generate_laser_readout(self, qm_dict='None'):
        """ Generates Laser pulse and waiting (idle) time.

        @param dict qm_dict: dictionary with the parameters

        @return object: the generated PulseBlockEnsemble object.
        """
        name = name
        # create the laser element
        laser_element, delay_element = self._get_laser_element_s3(qm_dict['laser_length'], 0.0, qm_dict['delay_length'],
                                                                  qm_dict['channel_amp'], qm_dict['gate'])
        waiting_element = self._get_idle_element_s3(qm_dict['wait_length'], 0.0)

        seqtrig_element = self._get_trigger_element_s3(20.0e-9, 0.0, qm_dict['seq_trig'], amp=qm_dict['channel_amp'])
        # Create the element list
        element_list = [seqtrig_element, laser_element, delay_element, waiting_element]
        # create the PulseBlock object.
        block = PulseBlock(name, element_list)
        # save block
        self.save_block(name, block)
        # put block in a list with repetitions
        block_list = [(block, 0)]
        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        # add metadata to invoke settings later on
        block_ensemble = self._invoke_settings(block_ensemble, controlled_vals_array=[0])
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble

