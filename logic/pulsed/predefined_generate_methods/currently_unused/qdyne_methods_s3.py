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


class QdynePredefinedGeneratorS3(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



    def generate_XY8_Qdyne_s3(self, name='XY8_Qdyne', rabi_period=0.1e-6, mw_freq=2870.0e6, mw_amp=0.1,
                        tau=1e-6, num_of_points=1, xy8_order=4, lasty=False, para_dict='None'):
        """

        """


        # get tau element
        tau_element = self._get_idle_element_s3(tau - rabi_period / 2, 0)

        # get tauhalf element
        tauhalf_element = self._get_idle_element_s3((tau - rabi_period / 2) / 2, 0)

        # get pihalf elements
        pihalfx_element = self._get_mw_element_s3(rabi_period / 4, 0.0, para_dict['mw_channel'], mw_amp, mw_freq,
                                              0.0)

        pihalfy_element = self._get_mw_element_s3(rabi_period / 4, 0.0, para_dict['mw_channel'], mw_amp, mw_freq,
                                              90.0)
        # get pi elements
        pix_element = self._get_mw_element_s3(rabi_period / 2, 0.0, para_dict['mw_channel'], mw_amp, mw_freq,
                                           0.0)
        piy_element = self._get_mw_element_s3(rabi_period / 2, 0.0, para_dict['mw_channel'], mw_amp, mw_freq,
                                           90.0)

        # get waiting element
        waiting_element = self._get_idle_element_s3(1e-6 + para_dict['wait_length'] - para_dict['delay_length'] - rabi_period / 2, 0.0)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element_s3(para_dict['laser_length'], 0.0, para_dict['delay_length'],
                                                               para_dict['channel_amp'], para_dict['gate'])

        if para_dict['seq_trig'] != '':
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element_s3(20.0e-9, 0.0, para_dict['seq_trig'], amp=para_dict['channel_amp'])
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)

        # Create element list for XY8_Qdyne PulseBlock
        element_list = []
        element_list.append(laser_element)
        element_list.append(delay_element)
        element_list.append(waiting_element)
        element_list.append(pihalfx_element)
        element_list.append(tauhalf_element)

        for n in range(xy8_order):
            element_list.append(pix_element)
            element_list.append(tau_element)
            element_list.append(piy_element)
            element_list.append(tau_element)
            element_list.append(pix_element)
            element_list.append(tau_element)
            element_list.append(piy_element)
            element_list.append(tau_element)
            element_list.append(piy_element)
            element_list.append(tau_element)
            element_list.append(pix_element)
            element_list.append(tau_element)
            element_list.append(piy_element)
            element_list.append(tau_element)
            element_list.append(pix_element)
            if n != xy8_order-1:
                element_list.append(tau_element)
        element_list.append(tauhalf_element)
        if lasty:
            element_list.append(pihalfy_element)
        else:
            element_list.append(pihalfx_element)

        # Create PulseBlock object
        XY8_Qdyne_block = PulseBlock(name, element_list)
        # save block
        self.save_block(name, XY8_Qdyne_block)

        # Create Block list with repetitions and sequence trigger if needed.
        # remember num_of_points=0 also counts as first round.
        block_list = [(XY8_Qdyne_block, num_of_points - 1)]
        if para_dict['seq_trig'] != '':
            block_list.insert(0,(seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
        # add metadata to invoke settings later on
        block_ensemble = self._invoke_settings(block_ensemble, controlled_vals_array=tau)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble

    def generate_xy8_qdyne(self, name='XY8_Qdyne', rabi_period=1.0e-8, mw_freq=2870.0e6, mw_amp=0.5, tau=0.5e-6,
                           xy8_order=4, frequency=1.0e6, mw_channel='a_ch1', laser_length=3.0e-7, channel_amp=1.0,
                           delay_length=0.7e-6, wait_time=1.0e-6, seq_trig_channel='d_ch1', gate_count_channel=''):
        """
        """

        # pre-computations

        period = 1 / frequency

        rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
        tau = self._adjust_to_samplingrate(tau, 2)
        laser_length = self._adjust_to_samplingrate(laser_length, 1)
        delay_length = self._adjust_to_samplingrate(delay_length, 1)
        wait_time = self._adjust_to_samplingrate(wait_time, 1)

        # trigger + 8*N tau + 2*pi/2 pulse + 2*tauhalf_excess + laser_length + aom_delay + wait_time
        sequence_length = 20.0e-9 + 8 * xy8_order * tau + rabi_period / 2 + laser_length + delay_length + wait_time
        if (sequence_length % period) == 0:
            extra_time = 0
        else:
            extra_time = period - (sequence_length % period)
        extra_time = self._adjust_to_samplingrate(extra_time, 1)

        # Sanity checks
        if gate_count_channel == '':
            gate_count_channel = None
        if seq_trig_channel == '':
            seq_trig_channel = None
        err_code = self._do_channel_sanity_checks(mw_channel=mw_channel,
                                                  gate_count_channel=gate_count_channel,
                                                  seq_trig_channel=seq_trig_channel)
        if err_code != 0:
            return

        # calculate "real" start length of the waiting times (tau and tauhalf)
        real_start_tau = tau - rabi_period / 2
        real_start_tauhalf = tau / 2 - rabi_period / 4
        if real_start_tau < 0.0 or real_start_tauhalf < 0.0:
            self.log.error('XY8_Qdyne generation failed! Rabi period of {0:.3e} s is too long for start tau '
                           'of {1:.3e} s.'.format(rabi_period, tau))
            return

        # get waiting element
        waiting_element = self._get_idle_element(wait_time + extra_time, 0.0, False)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
                                                               channel_amp, gate_count_channel)
        # get pihalf element
        pihalf_element = self._get_mw_element(rabi_period / 4.0, 0.0, mw_channel, False, mw_amp, mw_freq,
                                              0.0)
        # get -x pihalf (3pihalf) element
        piyhalf_element = self._get_mw_element(rabi_period / 4.0, 0.0, mw_channel, False, mw_amp,
                                               mw_freq, 90.)
        # get pi elements
        pix_element = self._get_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, mw_amp, mw_freq,
                                           0.0)
        piy_element = self._get_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, mw_amp, mw_freq,
                                           90.0)
        # get tauhalf element
        tauhalf_element = self._get_idle_element(real_start_tauhalf, 0, False)
        # get tau element
        tau_element = self._get_idle_element(real_start_tau, 0, False)

        if seq_trig_channel is not None:
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, seq_trig_channel, amp=channel_amp)
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)

        # create XY8-N_qdyne block element list
        block = []

        block.append(laser_element)
        block.append(delay_element)
        block.append(waiting_element)

        # actual Qdyne XY8 sequence
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
        block.append(piyhalf_element)

        # create XY8-N block object
        block = PulseBlock(name, block)
        self.save_block(name, block)

        # create block list and ensemble object
        block_list = [(block, 0)]
        if seq_trig_channel is not None:
            block_list.append((seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
        # add metadata to invoke settings later on
        block_ensemble.sample_rate = self.sample_rate
        block_ensemble.activation_config = self.activation_config
        block_ensemble.amplitude_dict = self.amplitude_dict
        block_ensemble.laser_channel = self.laser_channel
        block_ensemble.alternating = False
        block_ensemble.laser_ignore_list = []
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


################################# T1 Qdyne methods #####################################

    def generate_T1_qdyne_s3(self, qm_dict='None'):
        """
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        # pre-computations
        rabi_period=self._adjust_to_samplingrate(rabi_period,4)
        tau=self._adjust_to_samplingrate(tau,1)

        # get readout element
        readout_element = self._get_readout_element()

        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0.0)

        tau_element = self._get_idle_element(length = tau, increment= 0)


        # create XY8-N_qdyne block element list
        block = PulseBlock(name=name)
        block.extend(readout_element)
        block.append(tau_element)
        block.append(pihalf_element)

        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, alternating=False, created_blocks= created_blocks)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_T1_qdyne_dtg_s3(self, name='T1_Qdyne_DTG', rabi_period=10e-9, tau=1000e-9, seq_trig='d_ch1'):
        """
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        # pre-computations
        rabi_period=self._adjust_to_samplingrate(rabi_period,4)
        tau=self._adjust_to_samplingrate(tau,1)

        # get readout element
        readout_element = self._get_readout_element()
        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0.0)

        tau_element = self._get_trigger_element(length=tau, increment=0, channels=seq_trig)

        block = PulseBlock(name=name)
        # create T1_qdyne block element list
        block.append(tau_element)
        block.extend(readout_element)
        block.append(pihalf_element)

        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))

        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        controlled_variable=[0], counting_length=1.05*self.laser_length)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    # def generate_T1_qdyne_hahn_dtg(self, qm_dict='None'):
    #     """
    #     """
    #
    #     created_blocks = list()
    #     created_ensembles = list()
    #     created_sequences = list()
    #     # pre-computations
    #     rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
    #     tau = self._adjust_to_samplingrate(tau, 1)
    #
    #     # get readout element
    #     readout_element = self._get_readout_element()
    #     # get pihalf element
    #     pihalf_element = self._get_mw_element(length=rabi_period / 4,
    #                                           increment=0,
    #                                           amp=self.microwave_amplitude,
    #                                           freq=self.microwave_frequency,
    #                                           phase=0.0)
    #
    #     tau_element = self._get_trigger_element(length=tau, increment=0, channel=seq_trig)
    #
    #     block = PulseBlock(name=name)
    #
    #     block.extend(readout_element)
    #     block.append(pihalf_element)
    #     block.append(tau_element)
    #     block.append(pihalf_element)
    #     block.append(pihalf_element)
    #     block.append(tau_element)
    #
    #     created_blocks.append(block)
    #
    #     # Create block ensemble
    #     block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
    #     block_ensemble.append((block.name, 0))
    #
    #     # Create and append sync trigger block if needed
    #     created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
    #     # add metadata to invoke settings
    #     block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)
    #     # append ensemble to created ensembles
    #     created_ensembles.append(block_ensemble)
    #     return created_blocks, created_ensembles, created_sequences
    #
    #
    #
    # def generate_T1_qdyne_mollow_dtg(self, qm_dict='None'):
    #     """
    #     """
    #
    #     created_blocks = list()
    #     created_ensembles = list()
    #     created_sequences = list()
    #     # pre-computations
    #     rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
    #     tau = self._adjust_to_samplingrate(tau, 1)
    #
    #     # get readout element
    #     readout_element = self._get_readout_element()
    #     # get pihalf element
    #     pihalf_element = self._get_mw_element(length=rabi_period / 4,
    #                                           increment=0,
    #                                           amp=self.microwave_amplitude,
    #                                           freq=self.microwave_frequency,
    #                                           phase=0.0)
    #     # get pihalf element
    #     pi_element = self._get_mw_element(length=rabi_period / 2,
    #                                       increment=0,
    #                                       amp=self.microwave_amplitude,
    #                                       freq=self.microwave_frequency,
    #                                       phase=0.0)
    #     pi_element2 = self._get_mw_element(length=rabi_period / 2,
    #                                        increment=0,
    #                                        amp=self.microwave_amplitude,
    #                                        freq=self.microwave_frequency,
    #                                        phase=90.0)
    #     pi_element3 = self._get_mw_element(length=rabi_period / 2,
    #                                        increment=0,
    #                                        amp=self.microwave_amplitude,
    #                                        freq=self.microwave_frequency,
    #                                        phase=180.0)
    #
    #     tau_element = self._get_trigger_element(length=tau, increment=0, channel=seq_trig)
    #
    #     block = PulseBlock(name=name)
    #
    #     block.extend(readout_element)
    #     block.append(pihalf_element)
    #     for ii in range(qm_dict['number_pulses']):
    #         block.append(tau_element)
    #         if ii%8==0 or ii%8==3 or ii%8==4 or ii%8==5:
    #         #if ii%2==0:
    #         #if True:
    #             block.append(pi_element)
    #         else:
    #             block.append(pi_element3)
    #         block.append(tau_element)
    #
    #     created_blocks.append(block)
    #
    #     # Create block ensemble
    #     block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
    #     block_ensemble.append((block.name, 0))
    #
    #     # Create and append sync trigger block if needed
    #     created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
    #     # add metadata to invoke settings
    #     block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)
    #     # append ensemble to created ensembles
    #     created_ensembles.append(block_ensemble)
    #     return created_blocks, created_ensembles, created_sequences
    #
    #
    # def generate_T1_qdyne_DCoffset(self, qm_dict='None'):
    #     """
    #     """
    #
    #     created_blocks = list()
    #     created_ensembles = list()
    #     created_sequences = list()
    #     # pre-computations
    #     rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
    #     tau = self._adjust_to_samplingrate(tau, 1)
    #
    #     # get readout element
    #     readout_element = self._get_readout_element()
    #     # get pihalf element
    #     pihalf_element = self._get_mw_element(length=rabi_period / 4,
    #                                           increment=0,
    #                                           amp=self.microwave_amplitude,
    #                                           freq=self.microwave_frequency,
    #                                           phase=0.0)
    #
    #     tau_element = self._get_trigger_element(length=tau, increment=0, channel=seq_trig)
    #
    #     block = PulseBlock(name=name)
    #     block.extend(readout_element)
    #     block.append(tau_element)
    #     block.append(pihalf_element)
    #
    #     created_blocks.append(block)
    #
    #     # Create block ensemble
    #     block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
    #     block_ensemble.append((block.name, 0))
    #
    #     # Create and append sync trigger block if needed
    #     created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
    #     # add metadata to invoke settings
    #     block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)
    #     # append ensemble to created ensembles
    #     created_ensembles.append(block_ensemble)
    #     return created_blocks, created_ensembles, created_sequences
    #
    #
    # def generate_rabi_DTG_hahn(self, qm_dict='None'):
    #     """
    #     """
    #     created_blocks = list()
    #     created_ensembles = list()
    #     created_sequences = list()
    #     rabi_period = self._adjust_to_samplingrate(rabi_period, 4)
    #     tau_array = qm_dict['tau_start'] + np.arange(num_of_points) * qm_dict['tau_step']
    #
    #     # get readout element
    #     readout_element = self._get_readout_element()
    #     # get MW element (here just DC trigger)
    #     mw_element = self._get_trigger_element(length=qm_dict['tau_start'],
    #                                             increment=qm_dict['tau_step'],
    #                                             channels=seq_trig)
    #     # get pi pulse element
    #     pi_element = self._get_mw_element(length=rabi_period / 2,
    #                                              increment=0.0,
    #                                              amp=mw_amp,
    #                                              freq=mw_freq,
    #                                              phase=0.0)
    #
    #     block = PulseBlock(name=name)
    #     block.append(mw_element)
    #     block.append(pi_element)
    #     block.append(mw_element)
    #     block.extend(readout_element)
    #
    #     created_blocks.append(block)
    #     # Create block ensemble
    #     block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
    #     block_ensemble.append((block.name, 0))
    #
    #     # Create and append sync trigger block if needed
    #     created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
    #     # add metadata to invoke settings
    #     block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)
    #     # append ensemble to created ensembles
    #     created_ensembles.append(block_ensemble)
    #     return created_blocks, created_ensembles, created_sequences
    #
    #
    # #FIXME:
    #
    #
    # def generate_rabi_DTG_DD(self, name='rabi_dtg', tau_start=10.0e-9, tau_step=10.0e-9, number_of_taus=50, mw_freq=3e9,
    #                          mw_amp=1.0, mw_length=50e-9, pi_pulse_spacing=100e-9, mw_channel='', laser_length=3.0e-6,
    #                          channel_amp=1.0, delay_length=0.7e-6, wait_time=1.0e-6, sync_trig_channel='',
    #                          gate_count_channel=''):
    #     """
    #
    #     """
    #     # Sanity checks
    #     if gate_count_channel == '':
    #         gate_count_channel = None
    #     if sync_trig_channel == '':
    #         sync_trig_channel = None
    #     err_code = self._do_channel_sanity_checks(gate_count_channel=gate_count_channel,
    #                                               sync_trig_channel=sync_trig_channel)
    #     if err_code != 0:
    #         return
    #
    #     tau_array = tau_start + np.arange(number_of_taus) * tau_step
    #
    #     # get MW element (here just DC trigger)
    #     mw_element = self._get_trigger_element(pi_pulse_spacing / 2, 0, sync_trig_channel, use_as_tick=False,
    #                                            amp=channel_amp)
    #     # get pi pulse element
    #     pi_pulse_element = self._get_trigger_mw_element(mw_length, 0.0, mw_channel, False, sync_trig_channel, mw_amp,
    #                                                     mw_freq, 0.0)
    #     pi_pulse_element2 = self._get_trigger_mw_element(mw_length, 0.0, mw_channel, False, sync_trig_channel, mw_amp,
    #                                                      mw_freq, 180.0)
    #     pi_pulse_element3 = self._get_trigger_mw_element(mw_length, 0.0, mw_channel, False, sync_trig_channel, mw_amp,
    #                                                      mw_freq, 90.0)
    #     # pi_pulse_element2 = self._get_trigger_mw_element(mw_length, 0.0, mw_channel, False, sync_trig_channel, mw_amp,
    #     #                                                  mw_freq, 180.0)
    #     # get waiting element
    #     waiting_element = self._get_idle_element(wait_time, 0.0, False)
    #     # get short idle element
    #     short_idle_element = self._get_idle_element(250.0e-9, 0.0, False)
    #     # get long idle element
    #     long_idle_element = self._get_idle_element(3e-6, 0.0, False)
    #     long_idle_block = PulseBlock('long_idle', [long_idle_element])
    #     self.save_block('long_idle', long_idle_block)
    #     # get laser and delay element
    #     laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
    #                                                            channel_amp, gate_count_channel)
    #     if sync_trig_channel is not None:
    #         # get sequence trigger element
    #         seqtrig_element = self._get_trigger_element(15.0e-9, 0.0, sync_trig_channel,
    #                                                     amp=channel_amp)
    #         # Create its own block out of the element
    #         seq_block = PulseBlock('seq_trigger', [seqtrig_element, short_idle_element])
    #         # save block
    #         self.save_block('seq_trigger', seq_block)
    #
    #     element_list = []
    #
    #     for kk in range(number_of_taus):
    #         number_pi_pulses = int(tau_array[kk] / pi_pulse_spacing)
    #         remainder = tau_array[kk] % pi_pulse_spacing
    #         remainder_element = self._get_trigger_element(remainder / 2, 0, sync_trig_channel, use_as_tick=False,
    #                                                       amp=channel_amp)
    #         element_list.append(remainder_element)
    #         for jj in range(number_pi_pulses):
    #             # Create element list for Rabi PulseBlock
    #             element_list.append(mw_element)
    #             if jj % 4 == 0:
    #                 element_list.append(pi_pulse_element)
    #             elif jj % 4 == 1:
    #                 element_list.append(pi_pulse_element2)
    #             elif jj % 4 == 2:
    #                 element_list.append(pi_pulse_element2)
    #             else:
    #                 element_list.append(pi_pulse_element)
    #             element_list.append(mw_element)
    #         element_list.append(remainder_element)
    #         element_list.append(laser_element)
    #         element_list.append(delay_element)
    #         element_list.append(waiting_element)
    #
    #     # Create PulseBlock object
    #     rabi_block = PulseBlock(name, element_list)
    #     # save block
    #     self.save_block(name, rabi_block)
    #
    #     # Create Block list with repetitions and sequence trigger if needed.
    #     # remember number_of_taus=0 also counts as first round.
    #
    #     if sync_trig_channel is not None:
    #         block_list = [(seq_block, 0)]
    #         block_list.append((rabi_block, 0))
    #     else:
    #         block_list = [(rabi_block, 0)]
    #     block_list.append((long_idle_block, 0))
    #
    #     # create ensemble out of the block(s)
    #     block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
    #     # add metadata to invoke settings later on
    #     block_ensemble.controlled_vals_array = tau_array
    #     block_ensemble.sample_rate = self.sample_rate
    #     block_ensemble.activation_config = self.activation_config
    #     block_ensemble.amplitude_dict = self.amplitude_dict
    #     block_ensemble.laser_channel = self.laser_channel
    #     block_ensemble.alternating = False
    #     block_ensemble.laser_ignore_list = []
    #     # save ensemble
    #     self.save_ensemble(name, block_ensemble)
    #     return block_ensemble
    #
    # def generate_Mollow_rabi_DTG(self, name='mollow_rabi_dtg', mw_freq=3e9, mw_amp=1.0, rabi_period=100e-9,
    #                              tau=100e-9, pulse_start=1, pulse_inc=2, pulse_rep=50, mw_channel='',
    #                              laser_length=3.0e-6,
    #                              channel_amp=1.0, delay_length=0.7e-6, wait_time=1.0e-6, sync_trig_channel='',
    #                              gate_count_channel=''):
    #     """
    #
    #     """
    #     # Sanity checks
    #     if gate_count_channel == '':
    #         gate_count_channel = None
    #     if sync_trig_channel == '':
    #         sync_trig_channel = None
    #     err_code = self._do_channel_sanity_checks(gate_count_channel=gate_count_channel,
    #                                               sync_trig_channel=sync_trig_channel)
    #     if err_code != 0:
    #         return
    #
    #     pulse_array = (pulse_start + np.arange(pulse_rep) * pulse_inc).astype(int)
    #     tau_array = pulse_array * tau
    #
    #     # get MW element (here just DC trigger)
    #     mwhalf_element = self._get_trigger_element((tau - rabi_period / 2.0) / 2.0, 0, sync_trig_channel,
    #                                                use_as_tick=False,
    #                                                amp=channel_amp)
    #     # get MW element (here just DC trigger)
    #     # mw_element = self._get_trigger_element(tau-rabi_period/2, 0, sync_trig_channel, use_as_tick=False, amp=channel_amp)
    #     # get pihalf pulse element
    #     pihalf_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp, mw_freq,
    #                                           0.0)
    #     # get pi pulse element
    #     pi_pulse_element = self._get_trigger_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, sync_trig_channel,
    #                                                     mw_amp, mw_freq, 0.0)
    #     pi_pulse_element2 = self._get_trigger_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, sync_trig_channel,
    #                                                      mw_amp,
    #                                                      mw_freq, 180.0)
    #     pi_pulse_element3 = self._get_trigger_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, sync_trig_channel,
    #                                                      mw_amp,
    #                                                      mw_freq, 90.0)
    #     # pi_pulse_element2 = self._get_trigger_mw_element(mw_length, 0.0, mw_channel, False, sync_trig_channel, mw_amp,
    #     #                                                  mw_freq, 180.0)
    #     # get waiting element
    #     waiting_element = self._get_idle_element(wait_time, 0.0, False)
    #     # get short idle element
    #     short_idle_element = self._get_idle_element(250.0e-9, 0.0, False)
    #     # get long idle element
    #     long_idle_element = self._get_idle_element(3e-6, 0.0, False)
    #     long_idle_block = PulseBlock('long_idle', [long_idle_element])
    #     self.save_block('long_idle', long_idle_block)
    #     # get laser and delay element
    #     laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
    #                                                            channel_amp, gate_count_channel)
    #     if sync_trig_channel is not None:
    #         # get sequence trigger element
    #         seqtrig_element = self._get_trigger_element(15.0e-9, 0.0, sync_trig_channel,
    #                                                     amp=channel_amp)
    #         # Create its own block out of the element
    #         seq_block = PulseBlock('seq_trigger', [seqtrig_element, short_idle_element])
    #         # save block
    #         self.save_block('seq_trigger', seq_block)
    #
    #     element_list = []
    #
    #     for kk in range(len(pulse_array)):
    #         element_list.append(pihalf_element)
    #         for jj in range(pulse_array[kk]):
    #             element_list.append(mwhalf_element)
    #             # if jj%8==0 or jj%8==3 or jj%8==4 or jj%8==5:
    #             if jj % 2 == 0:
    #                 element_list.append(pi_pulse_element2)
    #             else:
    #                 element_list.append(pi_pulse_element)
    #             element_list.append(mwhalf_element)
    #         element_list.append(laser_element)
    #         element_list.append(delay_element)
    #         element_list.append(waiting_element)
    #
    #     # Create PulseBlock object
    #     rabi_block = PulseBlock(name, element_list)
    #     # save block
    #     self.save_block(name, rabi_block)
    #
    #     # Create Block list with repetitions and sequence trigger if needed.
    #     # remember number_of_taus=0 also counts as first round.
    #
    #     if sync_trig_channel is not None:
    #         block_list = [(seq_block, 0)]
    #         block_list.append((rabi_block, 0))
    #     else:
    #         block_list = [(rabi_block, 0)]
    #     block_list.append((long_idle_block, 0))
    #
    #     # create ensemble out of the block(s)
    #     block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
    #     # add metadata to invoke settings later on
    #     block_ensemble.controlled_vals_array = tau_array
    #     block_ensemble.sample_rate = self.sample_rate
    #     block_ensemble.activation_config = self.activation_config
    #     block_ensemble.amplitude_dict = self.amplitude_dict
    #     block_ensemble.laser_channel = self.laser_channel
    #     block_ensemble.alternating = False
    #     block_ensemble.laser_ignore_list = []
    #     # save ensemble
    #     self.save_ensemble(name, block_ensemble)
    #     return block_ensemble
    #
    # def generate_Mollow_rabi_AWG(self, name='mollow_rabi_dtg', mw_freq=3e9, mw_amp=1.0, rabi_period=100e-9,
    #                              tau=100e-9, pulse_start=1, pulse_inc=2, pulse_rep=50, mw_freq2=2e9, mw_amp2=0.01,
    #                              mw_phase2=90, mw_channel='', laser_length=3.0e-6, channel_amp=1.0, delay_length=0.7e-6,
    #                              wait_time=1.0e-6, sync_trig_channel='', gate_count_channel=''):
    #     """
    #
    #     """
    #     # Sanity checks
    #     if gate_count_channel == '':
    #         gate_count_channel = None
    #     if sync_trig_channel == '':
    #         sync_trig_channel = None
    #     err_code = self._do_channel_sanity_checks(gate_count_channel=gate_count_channel,
    #                                               sync_trig_channel=sync_trig_channel)
    #     if err_code != 0:
    #         return
    #
    #     pulse_array = (pulse_start + np.arange(pulse_rep) * pulse_inc).astype(int)
    #     tau_array = pulse_array * tau
    #
    #     # get MW element
    #     mwhalf_element = self._get_mw_element((tau - rabi_period / 2.0) / 2.0, 0, mw_channel, False, mw_amp2, mw_freq2,
    #                                           mw_phase2)
    #     # get MW element (here just DC trigger)
    #     # mw_element = self._get_trigger_element(tau-rabi_period/2, 0, sync_trig_channel, use_as_tick=False, amp=channel_amp)
    #     # get pihalf pulse element
    #     pihalf_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp, mw_freq, 0.0)
    #     # get pi pulse element
    #     pi_pulse_element = self._get_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, mw_amp, mw_freq, 0.0)
    #     pi_pulse_element2 = self._get_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, mw_amp, mw_freq, 180.0)
    #     pi_pulse_element3 = self._get_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, mw_amp, mw_freq, 90.0)
    #     # pi_pulse_element2 = self._get_trigger_mw_element(mw_length, 0.0, mw_channel, False, sync_trig_channel, mw_amp,
    #     #                                                  mw_freq, 180.0)
    #     # get waiting element
    #     waiting_element = self._get_idle_element(wait_time, 0.0, False)
    #     # get short idle element
    #     short_idle_element = self._get_idle_element(250.0e-9, 0.0, False)
    #     # get long idle element
    #     long_idle_element = self._get_idle_element(3e-6, 0.0, False)
    #     long_idle_block = PulseBlock('long_idle', [long_idle_element])
    #     self.save_block('long_idle', long_idle_block)
    #     # get laser and delay element
    #     laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
    #                                                            channel_amp, gate_count_channel)
    #     if sync_trig_channel is not None:
    #         # get sequence trigger element
    #         seqtrig_element = self._get_trigger_element(15.0e-9, 0.0, sync_trig_channel,
    #                                                     amp=channel_amp)
    #         # Create its own block out of the element
    #         seq_block = PulseBlock('seq_trigger', [seqtrig_element, short_idle_element])
    #         # save block
    #         self.save_block('seq_trigger', seq_block)
    #
    #     element_list = []
    #
    #     for kk in range(len(pulse_array)):
    #         element_list.append(pihalf_element)
    #         for jj in range(pulse_array[kk]):
    #             element_list.append(mwhalf_element)
    #             if jj % 8 == 0 or jj % 8 == 3 or jj % 8 == 4 or jj % 8 == 5:
    #                 # if jj % 2 == 0:
    #                 element_list.append(pi_pulse_element)
    #             else:
    #                 element_list.append(pi_pulse_element2)
    #             element_list.append(mwhalf_element)
    #         element_list.append(laser_element)
    #         element_list.append(delay_element)
    #         element_list.append(waiting_element)
    #
    #     # Create PulseBlock object
    #     rabi_block = PulseBlock(name, element_list)
    #     # save block
    #     self.save_block(name, rabi_block)
    #
    #     # Create Block list with repetitions and sequence trigger if needed.
    #     # remember number_of_taus=0 also counts as first round.
    #
    #     if sync_trig_channel is not None:
    #         block_list = [(seq_block, 0)]
    #         block_list.append((rabi_block, 0))
    #     else:
    #         block_list = [(rabi_block, 0)]
    #     block_list.append((long_idle_block, 0))
    #
    #     # create ensemble out of the block(s)
    #     block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
    #     # add metadata to invoke settings later on
    #     block_ensemble.controlled_vals_array = tau_array
    #     block_ensemble.sample_rate = self.sample_rate
    #     block_ensemble.activation_config = self.activation_config
    #     block_ensemble.amplitude_dict = self.amplitude_dict
    #     block_ensemble.laser_channel = self.laser_channel
    #     block_ensemble.alternating = False
    #     block_ensemble.laser_ignore_list = []
    #     # save ensemble
    #     self.save_ensemble(name, block_ensemble)
    #     return block_ensemble
    #
    # def generate_Mollow_pulsedODMR_AWG(self, name='mollow_pulsedODMR_dtg', mw_freq=3e9, mw_amp=1.0, rabi_period=100e-9,
    #                                    tau=100e-9, freq_start=1, freq_inc=2, freq_rep=50, number_pulses=10,
    #                                    mw_amp2=0.01, mw_phase2=90, mw_channel='', laser_length=3.0e-6, channel_amp=1.0,
    #                                    delay_length=0.7e-6, wait_time=1.0e-6, sync_trig_channel='',
    #                                    gate_count_channel=''):
    #     """
    #
    #     """
    #     # Sanity checks
    #     if gate_count_channel == '':
    #         gate_count_channel = None
    #     if sync_trig_channel == '':
    #         sync_trig_channel = None
    #     err_code = self._do_channel_sanity_checks(gate_count_channel=gate_count_channel,
    #                                               sync_trig_channel=sync_trig_channel)
    #     if err_code != 0:
    #         return
    #
    #     freq_array = (freq_start + np.arange(freq_rep) * freq_inc).astype(int)
    #
    #     # get pihalf pulse element
    #     pihalf_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp, mw_freq, 0.0)
    #
    #     # get waiting element
    #     waiting_element = self._get_idle_element(wait_time, 0.0, False)
    #     # get short idle element
    #     short_idle_element = self._get_idle_element(250.0e-9, 0.0, False)
    #     # get long idle element
    #     long_idle_element = self._get_idle_element(3e-6, 0.0, False)
    #     long_idle_block = PulseBlock('long_idle', [long_idle_element])
    #     self.save_block('long_idle', long_idle_block)
    #     # get laser and delay element
    #     laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
    #                                                            channel_amp, gate_count_channel)
    #     if sync_trig_channel is not None:
    #         # get sequence trigger element
    #         seqtrig_element = self._get_trigger_element(15.0e-9, 0.0, sync_trig_channel,
    #                                                     amp=channel_amp)
    #         # Create its own block out of the element
    #         seq_block = PulseBlock('seq_trigger', [seqtrig_element, short_idle_element])
    #         # save block
    #         self.save_block('seq_trigger', seq_block)
    #
    #     element_list = []
    #
    #     for kk in range(len(freq_array)):
    #         element_list.append(pihalf_element)
    #         phase = mw_phase2 + 360 * freq_array[kk] * rabi_period / 4
    #         phase_pi = 360 * mw_freq * rabi_period / 4
    #         for jj in range(number_pulses):
    #             # get MW element
    #             mwhalf_element = self._get_mw_element((tau - rabi_period / 2.0) / 2.0, 0, mw_channel, False, mw_amp2,
    #                                                   freq_array[kk], phase)
    #             element_list.append(mwhalf_element)
    #
    #             phase = phase + 360 * freq_array[kk] * (tau - rabi_period / 2.0) / 2.0
    #             phase_pi = phase_pi + 360 * mw_freq * (tau - rabi_period / 2.0) / 2.0
    #
    #             if jj % 8 == 0 or jj % 8 == 3 or jj % 8 == 4 or jj % 8 == 5:
    #                 # if jj%2==0:
    #                 pi_pulse_element = self._get_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, mw_amp, mw_freq,
    #                                                         0.0 + phase_pi)
    #                 element_list.append(pi_pulse_element)
    #             else:
    #                 pi_pulse_element = self._get_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, mw_amp, mw_freq,
    #                                                         180.0 + phase_pi)
    #                 element_list.append(pi_pulse_element)
    #
    #             phase = phase + 360 * freq_array[kk] * rabi_period / 2.0
    #             phase_pi = phase_pi + 360 * mw_freq * rabi_period / 2.0
    #
    #             mwhalf_element = self._get_mw_element((tau - rabi_period / 2.0) / 2.0, 0, mw_channel, False, mw_amp2,
    #                                                   freq_array[kk], phase)
    #             element_list.append(mwhalf_element)
    #
    #             phase = phase + 360 * freq_array[kk] * (tau - rabi_period / 2.0) / 2.0
    #             phase_pi = phase_pi + 360 * mw_freq * (tau - rabi_period / 2.0) / 2.0
    #
    #         element_list.append(laser_element)
    #         element_list.append(delay_element)
    #         element_list.append(waiting_element)
    #
    #     # Create PulseBlock object
    #     rabi_block = PulseBlock(name, element_list)
    #     # save block
    #     self.save_block(name, rabi_block)
    #
    #     # Create Block list with repetitions and sequence trigger if needed.
    #     # remember number_of_taus=0 also counts as first round.
    #
    #     if sync_trig_channel is not None:
    #         block_list = [(seq_block, 0)]
    #         block_list.append((rabi_block, 0))
    #     else:
    #         block_list = [(rabi_block, 0)]
    #     block_list.append((long_idle_block, 0))
    #
    #     # create ensemble out of the block(s)
    #     block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
    #     # add metadata to invoke settings later on
    #     block_ensemble.controlled_vals_array = freq_array
    #     block_ensemble.sample_rate = self.sample_rate
    #     block_ensemble.activation_config = self.activation_config
    #     block_ensemble.amplitude_dict = self.amplitude_dict
    #     block_ensemble.laser_channel = self.laser_channel
    #     block_ensemble.alternating = False
    #     block_ensemble.laser_ignore_list = []
    #     # save ensemble
    #     self.save_ensemble(name, block_ensemble)
    #     return block_ensemble

    # def generate_pulsedodmr_DCoffset(self, name='pulsedODMR_DCoffset', rabi_period=1.0e-6, mw_freq_start=2870.0e6,
    #                                  mw_freq_incr=0.2e6, num_of_points=50, mw_amp=1.0, mw_channel='a_ch1',
    #                                  laser_length=3.0e-6, channel_amp=1.0, delay_length=0.7e-6, wait_time=1.0e-6,
    #                                  sync_trig_channel='', gate_count_channel=''):
    #     """
    #
    #     """
    #     # Sanity checks
    #     if gate_count_channel == '':
    #         gate_count_channel = None
    #     if sync_trig_channel == '':
    #         sync_trig_channel = None
    #     err_code = self._do_channel_sanity_checks(mw_channel=mw_channel,
    #                                               gate_count_channel=gate_count_channel,
    #                                               sync_trig_channel=sync_trig_channel)
    #     if err_code != 0:
    #         return
    #
    #     # get waiting element
    #     waiting_element = self._get_trigger_element(wait_time, 0.0, sync_trig_channel, amp=channel_amp)
    #     # short idle element
    #     short_idle_element = self._get_idle_element(200e-9, 0.0, False)
    #     short_idle_block = PulseBlock('short_idle', [short_idle_element])
    #     self.save_block('short_idle', short_idle_block)
    #     # long idle element
    #     long_idle_element = self._get_idle_element(2000e-9, 0.0, False)
    #     long_idle_block = PulseBlock('long_idle', [long_idle_element])
    #     self.save_block('long_idle', long_idle_block)
    #     # get laser and delay element
    #     laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
    #                                                            channel_amp, sync_trig_channel)
    #     if sync_trig_channel is not None:
    #         # get sequence trigger element
    #         seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, sync_trig_channel,
    #                                                     amp=channel_amp)
    #         # Create its own block out of the element
    #         seq_block = PulseBlock('seq_trigger', [seqtrig_element])
    #         # save block
    #         self.save_block('seq_trigger', seq_block)
    #
    #     # Create frequency list array
    #     freq_array = mw_freq_start + np.arange(num_of_points) * mw_freq_incr
    #
    #     # Create element list for PulsedODMR PulseBlock
    #     element_list = []
    #     for mw_freq in freq_array:
    #         mw_element = self._get_trigger_mw_element(rabi_period / 2, 0.0, mw_channel, False, sync_trig_channel,
    #                                                   mw_amp, mw_freq, 0.0)
    #
    #         element_list.append(mw_element)
    #         element_list.append(laser_element)
    #         element_list.append(delay_element)
    #         element_list.append(waiting_element)
    #     # Create PulseBlock object
    #     pulsedodmr_block = PulseBlock(name, element_list)
    #     # save block
    #     self.save_block(name, pulsedodmr_block)
    #
    #     # Create Block list with repetitions and sequence trigger if needed.
    #     # remember number_of_taus=0 also counts as first round.
    #     block_list = [(pulsedodmr_block, 0)]
    #     if sync_trig_channel is not None:
    #         block_list.append((seq_block, 0))
    #
    #     if sync_trig_channel is not None:
    #         block_list = [(seq_block, 0)]
    #         block_list.append((short_idle_block, 0))
    #         block_list.append((pulsedodmr_block, 0))
    #     else:
    #         block_list = [(pulsedodmr_block, 0)]
    #     block_list.append((long_idle_block, 0))
    #
    #     # create ensemble out of the block(s)
    #     block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
    #     # add metadata to invoke settings later on
    #     block_ensemble.controlled_vals_array = freq_array
    #     block_ensemble.sample_rate = self.sample_rate
    #     block_ensemble.activation_config = self.activation_config
    #     block_ensemble.amplitude_dict = self.amplitude_dict
    #     block_ensemble.laser_channel = self.laser_channel
    #     block_ensemble.alternating = False
    #     block_ensemble.laser_ignore_list = []
    #     # save ensemble
    #     self.save_ensemble(name, block_ensemble)
    #     return block_ensemble




    def _get_trigger_mw_element(self, length, increment, mw_channel, use_as_tick, channel,
                                mw_amp=None, mw_freq=None, mw_phase=None):
        """

        @param length:
        @param increment:
        @param mw_channel:
        @param use_as_tick:
        @param delay_time:
        @param laser_amp:
        @param mw_amp:
        @param mw_freq:
        @param mw_phase:
        @param gate_count_chnl:
        @return:
        """
        # get channel lists
        digital_channels, analog_channels = self._get_channel_lists()

        # input params for laser/mw element generation
        trigger_mw_params = [{}] * self.analog_channels
        trigger_mw_digital = [False] * self.digital_channels
        trigger_mw_function = ['Idle'] * self.analog_channels

        # Determine analogue or digital laser channel and set parameters accordingly.
        if 'd_ch' in channel:
            trigger_index = digital_channels.index(channel)
            trigger_mw_digital[trigger_index] = True
        elif 'a_ch' in self.laser_channel:
            trigger_index = analog_channels.index(channel)
            trigger_mw_function[trigger_index] = 'DC'
            trigger_mw_params[trigger_index] = {'amplitude1': 1.0}

        # Determine analogue or digital MW channel and set parameters accordingly.
        if 'd_ch' in mw_channel:
            mw_index = digital_channels.index(mw_channel)
            trigger_mw_digital[mw_index] = True
        elif 'a_ch' in mw_channel:
            mw_index = analog_channels.index(mw_channel)
            trigger_mw_function[mw_index] = 'Sin'
            trigger_mw_params[mw_index] = {'amplitude1': mw_amp, 'frequency1': mw_freq,
                                           'phase1': mw_phase}

        # Create laser/mw element
        trigger_mw_element = PulseBlockElement(init_length_s=length, increment_s=increment,
                                               pulse_function=trigger_mw_function,
                                               digital_high=trigger_mw_digital, parameters=trigger_mw_params,
                                               use_as_tick=use_as_tick)

        return trigger_mw_element
