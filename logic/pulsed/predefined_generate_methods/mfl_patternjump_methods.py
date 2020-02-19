import numpy as np
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from core.module import Connector

OFFSET_TAU_MFL_SEQMODE = 3      # number of sequence elements in front of ramseys
DELTA_TAU_I_MFL_SEQMODE = 2     # separation between different ramseys in sequence
SEG_I_IDLE_SEQMODE = 2          # idx of idle segment
SEG_I_EPOCH_DONE_SEQMODE = 3    # idx of epoch done segment


class MFLPatternJump_Generator(PredefinedGeneratorBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # holds description while generating all sequence elements
        # NOT the actual seqtable written to the AWG
        self._seqtable = None
        self._seqtable_counter = 0
        self._jumptable = None
        self._jumptable_address = 1 # all low (0000 0000) shouldn't be a valid address
        self.init_seqtable()
        self.init_jumptable()

    def _add_to_seqtable(self, name, blocks, ensembles, seq_params):
        self._seqtable['blocks'] += blocks
        self._seqtable['ensembles'] += ensembles
        self._seqtable['seq_params'].append([name, seq_params])
        self._seqtable_counter += 1

    def _add_to_jumptable(self, name):
        """ Call BEFORE _add_to_seqtable, as this will iterate _seqtable_counter """
        self._jumptable['name'].append(name)
        self._jumptable['idx_seqtable'].append(self._seqtable_counter)
        self._jumptable['jump_address'].append(self._jumptable_address)
        self._jumptable_address += 1

    def init_seqtable(self):
        self._seqtable = {'blocks': [], 'ensembles': [], 'seq_params': []}
        self._seqtable_counter = 0

    def init_jumptable(self):
        self._jumptable = {'name': [], 'idx_seqtable': [], 'jump_address': []}
        self._jumptable_address = 1

    def _seqtable_to_result(self):
        # as needed from sequencer
        return self._seqtable['blocks'], self._seqtable['ensembles'], self._seqtable['seq_params']

    def _get_current_seqtable_idx(self):
        # only valid while iterating through generation of sequence
        return self._seqtable_counter

    def _get_current_jumptable_address(self):
        # only valid while iterating through generation of sequence
        return self._jumptable_address

    def generate_mfl_ramsey_pjump(self, name="mfl_ramsey_pjump", n_seq_sweeps=1000, tau_start=10e-9, tau_step=10e-9,
                            num_of_points=10, tau_first=50e-9, n_epochs=15, tau_list=False, phase_list=False,
                            laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6, ni_gate_length=-1e-9, alternating=False):

        self.init_jumptable()
        self.init_seqtable()

        if not tau_list:
            tau_array = tau_start + np.arange(num_of_points) * tau_step
        else:
            tau_array = tau_list
        if phase_list:
            if len(phase_list) != len(tau_array):
                raise ValueError("Length of tau_list= {} not equal length of phase_list= {}".format(
                                    len(tau_array), len(tau_list)))

        general_params = locals()
        is_gated = self.gate_channel is not None

        # generate special blocks for flow control of mfl
        cur_name = 'START'
        seg_idx_0, real_tau = self._get_index_of_ramsey(tau_first, tau_array)    # points to laser_0 before first ramsey
        if tau_first != real_tau:
            self.log.warning("Sequence start chosen to be tau= {} ns, instead of requested {} ns".format(
                            real_tau, tau_first))
        cur_blocks, cur_ensembles, _ = self._create_generic_idle(name=cur_name)
        cur_seq_params = self._get_default_seq_params({'go_to': seg_idx_0})
        self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        cur_name = 'idle'
        cur_blocks, cur_ensembles, _ = self._create_generic_idle(name=cur_name)
        cur_seq_params = self._get_default_seq_params({'go_to': SEG_I_IDLE_SEQMODE, 'repetitions': -1})
        self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        # epoch_done trigger by AWG (rear panel) sequence marker
        cur_name = 'epoch_done'
        # repetitions > 0: too see on osci. irq triggers on rising edge, so doesn't matter performance wise
        cur_blocks, cur_ensembles, _ = self._create_generic_idle(name=cur_name)
        cur_seq_params = self._get_default_seq_params({'go_to': SEG_I_IDLE_SEQMODE, 'repetitions': 1000, 'flag_high': ['A']})
        self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        # generate ramseys for every tau
        for i, tau in enumerate(tau_array):
            if phase_list:
                read_phase = phase_list[i]
            else:
                read_phase = 0

            # laser init before first MW in every epoch. No readout!
            cur_name = 'laser_wait_0_' + str(i)
            cur_blocks, cur_ensembles = self._create_init_laser_pulses(general_params, name=cur_name)
            cur_seq_params = self._get_default_seq_params({'go_to': 0, 'repetitions': 0,
                                                           'pattern_jump_address': self._get_current_jumptable_address()})
            self._add_to_jumptable(cur_name)
            self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

            # MW with laser after each Ramsey
            cur_name = name + '_' + str(i)
            cur_blocks, cur_ensembles, _ = self._create_single_ramsey(name=cur_name, tau=tau,
                                                mw_phase=0.0, laser_length=laser_length, wait_length=wait_length,
                                                ni_gate_length=ni_gate_length, phase_readout_rad=read_phase)

            cur_seq_params = self._get_default_seq_params({'go_to': SEG_I_EPOCH_DONE_SEQMODE, 'repetitions': n_seq_sweeps-1})
            self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        all_blocks, all_ensembles, ensemble_list = self._seqtable_to_result()

        sequence = PulseSequence(name=general_params['name'], ensemble_list=ensemble_list, rotating_frame=False)

        if not is_gated:
            # new: in non gated mode works like gated -> sync pulse with aom.
            # works, since only a single tau
            fastcounter_count_length = self.laser_length + 100e-9
            # attention: relies on fact that last ramsey in list is longest!
            #fastcounter_count_length = 1.1 * self._get_ensemble_count_length(all_ensembles[-1], created_blocks=all_blocks)
        else:
            fastcounter_count_length = self.laser_length + 100e-9

        self.log.info("Setting fastcounter count length to {} us".format(fastcounter_count_length * 1e6))

        # every epoch of mfl has only single tau
        # however, we need all taus sometimes somewhere else
        sequence.measurement_information['controlled_variable_virtual'] = tau_array
        if phase_list:
            sequence.measurement_information['read_phases'] = phase_list

        if not is_gated:
            contr_var = [0]
            n_lasers = 1
        else:
            contr_var = np.arange(n_epochs)
            n_lasers = len(contr_var)

        self._add_metadata_to_settings(sequence, alternating=alternating, created_blocks=list(),
                                       laser_ignore_list=list(),
                                       controlled_variable=contr_var, units=('', ''), labels=('Epoch', 'Signal'),
                                       number_of_lasers=2 * n_lasers if alternating else n_lasers,
                                       counting_length=fastcounter_count_length)


        return all_blocks, all_ensembles, [sequence]

    def generate_mfl_hahn_pjump(self, name="mfl_hahn_pjump", n_seq_sweeps=1000, tau_start=10e-9, tau_step=10e-9,
                            num_of_points=10, tau_first=50e-9, n_epochs=15, tau_list=False,
                            laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6, ni_gate_length=-1e-9, alternating=False):

        self.init_jumptable()
        self.init_seqtable()

        if not tau_list:
            tau_array = tau_start + np.arange(num_of_points) * tau_step
        else:
            tau_array = tau_list

        general_params = locals()
        is_gated = self.gate_channel is not None

        # generate special blocks for flow control of mfl
        cur_name = 'START'
        seg_idx_0, real_tau = self._get_index_of_ramsey(tau_first, tau_array)    # points to laser_0 before first ramsey
        if tau_first != real_tau:
            self.log.warning("Sequence start chosen to be tau= {} ns, instead of requested {} ns".format(
                            real_tau, tau_first))
        cur_blocks, cur_ensembles, _ = self._create_generic_idle(name=cur_name)
        cur_seq_params = self._get_default_seq_params({'go_to': seg_idx_0})
        self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        cur_name = 'idle'
        cur_blocks, cur_ensembles, _ = self._create_generic_idle(name=cur_name)
        cur_seq_params = self._get_default_seq_params({'go_to': SEG_I_IDLE_SEQMODE, 'repetitions': -1})
        self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        # epoch_done trigger by AWG (rear panel) sequence marker
        cur_name = 'epoch_done'
        # repetitions > 0: too see on osci. irq triggers on rising edge, so doesn't matter performance wise
        cur_blocks, cur_ensembles, _ = self._create_generic_idle(name=cur_name)
        cur_seq_params = self._get_default_seq_params({'go_to': SEG_I_IDLE_SEQMODE, 'repetitions': 1000, 'flag_high': ['A']})
        self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        # generate ramseys for every tau
        for i, tau in enumerate(tau_array):
            # laser init before first MW in every epoch. No readout!
            cur_name = 'laser_wait_0_' + str(i)
            cur_blocks, cur_ensembles = self._create_init_laser_pulses(general_params, name=cur_name)
            cur_seq_params = self._get_default_seq_params({'go_to': 0, 'repetitions': 0,
                                                           'pattern_jump_address': self._get_current_jumptable_address()})
            self._add_to_jumptable(cur_name)
            self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

            # MW with laser after each Hahn
            cur_name = name + '_' + str(i)
            cur_blocks, cur_ensembles, _ = self._create_single_hahn(name=cur_name, tau=tau,
                                                mw_phase=0.0, laser_length=laser_length, wait_length=wait_length,
                                                ni_gate_length=ni_gate_length)

            cur_seq_params = self._get_default_seq_params({'go_to': SEG_I_EPOCH_DONE_SEQMODE, 'repetitions': n_seq_sweeps-1})
            self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        all_blocks, all_ensembles, ensemble_list = self._seqtable_to_result()

        sequence = PulseSequence(name=general_params['name'], ensemble_list=ensemble_list, rotating_frame=False)

        if not is_gated:
            # new: in non gated mode works like gated -> sync pulse with aom.
            # works, since only a single tau
            fastcounter_count_length = self.laser_length + 100e-9
            # attention: relies on fact that last ramsey in list is longest!
            #fastcounter_count_length = 1.1 * self._get_ensemble_count_length(all_ensembles[-1], created_blocks=all_blocks)
        else:
            fastcounter_count_length = self.laser_length + 100e-9

        self.log.info("Setting fastcounter count length to {} us".format(fastcounter_count_length * 1e6))

        # every epoch of mfl has only single tau
        # however, we need all taus sometimes somewhere else
        sequence.measurement_information['controlled_variable_virtual'] = tau_array
        if not is_gated:
            contr_var = [0]
            n_lasers = 1
        else:
            contr_var = np.arange(n_epochs)
            n_lasers = len(contr_var)

        self._add_metadata_to_settings(sequence, alternating=alternating, created_blocks=list(),
                                       laser_ignore_list=list(),
                                       controlled_variable=contr_var, units=('', ''), labels=('Epoch', 'Signal'),
                                       number_of_lasers=2 * n_lasers if alternating else n_lasers,
                                       counting_length=fastcounter_count_length)


        return all_blocks, all_ensembles, [sequence]



    def _create_init_laser_pulses(self, general_params, name='laser_wait'):
        created_blocks = []
        created_ensembles = []

        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self._create_laser_wait(name=name, laser_length=general_params['laser_length'],
                                    wait_length=general_params['wait_length']
                                    )
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        if general_params['alternating']:
            raise NotImplemented("Look into repetitive_readout_methods.py if needed")

        return created_blocks, created_ensembles

    # todo: inherit shared methods
    def _create_laser_wait(self, name='laser_wait', laser_length=500e-9, wait_length=1e-6):
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


    def _get_index_of_ramsey(self, first_tau, tau_array):
        """
        Ramseys have taus as described by tau_array.
        Get the sequence index of the tau that is closest to given first tau value.
        :param tau:
        :param tau_array:
        :return:
        """
        idx, val = self._find_nearest(tau_array, first_tau)

        idx_in_sequence = 1 + OFFSET_TAU_MFL_SEQMODE + DELTA_TAU_I_MFL_SEQMODE * idx
        return int(idx_in_sequence), val

    def _find_nearest(self, array, value):
        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return idx, array[idx]

    def _get_default_seq_params(self, overwrite_param_dict=None):
        """
        default params for a sequence segement for MFL
        see pulse_objects.py::PulseSequence() for explanation of params
        :param seq_para_dict:
        :return:
        """

        if overwrite_param_dict is None:
            seq_para_dict = {}
        else:
            seq_para_dict = overwrite_param_dict

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

    def _create_generic_idle(self, name='idle'):
        created_blocks = []
        created_ensembles = []
        created_sequences = []

        idle_element = self._get_idle_element(length=1e-9, increment=0.0)
        block = PulseBlock(name=name)
        block.append(idle_element)

        self._extend_to_min_samples(block)

        # prepare return vals
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))
        created_blocks.append(block)
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=False, number_of_lasers=0)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences

    def _rad_to_deg(self, angle_rad):
        return angle_rad/(2*np.pi)*360

    def _create_single_ramsey(self, name='ramsey', tau=500e-9, mw_phase=0.0,
                              laser_length=1500e-9, wait_length=1000e-9, ni_gate_length=-1e-9,
                              phase_readout_rad=0):

        use_ni_counter = False
        if ni_gate_length > 0.:
            use_ni_counter = True
            if self.gate_channel:
                self.logger.warning("Gated mode sensible with fastcounter, but found nicard counting enabled.")

        created_blocks = []
        created_ensembles = []
        created_sequences = []

        # prevent granularity problems
        rabi_period = self._adjust_to_samplingrate(self.rabi_period, 8)  # s
        tau = self._adjust_to_samplingrate(tau, 4)

        pi2_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0.0)
        pi2_element_read = self._get_mw_element(length=rabi_period / 4,
                                           increment=0.0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=self._rad_to_deg(phase_readout_rad))
        tau_element = self._get_idle_element(length=tau, increment=0.0)

        # laser readout after MW
        aom_delay = self.laser_delay

        # note: fastcomtec triggers only on falling edge
        laser_gate_element = self._get_laser_gate_element(length=aom_delay - 20e-9, increment=0)
        laser_element = self._get_laser_element(length=laser_length - aom_delay + 20e-9, increment=0)
        delay_element = self._get_idle_element(length=aom_delay, increment=0)
        waiting_element = self._get_idle_element(length=wait_length, increment=0.0)

        # only a single tau, so we can operate sync_channel just like in gating mode
        if self.sync_channel:
            laser_gate_channels = [self.sync_channel, self.laser_channel]
            laser_sync_element = self._get_trigger_element(length=aom_delay - 20e-9, increment=0, channels=laser_gate_channels)

        block = PulseBlock(name=name)
        block.append(pi2_element)
        block.append(tau_element)
        block.append(pi2_element_read)
        if not use_ni_counter:  # normal, fastcounter acquisition
            if self.gate_channel:
                block.append(laser_gate_element)
            if self.sync_channel:
                block.append(laser_sync_element)

            block.append(laser_element)
        else:   # use nicard counter and gate away dark counts
            laser_element_1 = self._get_laser_element(length=aom_delay - 10e-9, increment=0)
            laser_gate_channels = [self.sync_channel, self.laser_channel]
            laser_gate_element = self._get_trigger_element(length=ni_gate_length + 20e-9, increment=0, channels=laser_gate_channels)
            gate_after_length = ni_gate_length + aom_delay - laser_length

            # makes sure that whole laser pulse is in ni gate
            # NOT wanted
            #if aom_delay > gate_after_length:
            #    gate_after_length = aom_delay
            gate_element_after_laser = self._get_trigger_element(length=gate_after_length, increment=0, channels=[self.sync_channel])
            # negative length values allowed: cut back laser_gate_element
            laser_element_2 = self._get_laser_element(length=laser_length - ni_gate_length - aom_delay - 10e-9, increment=0)

            if self.sync_channel:
                block.append(laser_element_1)
                block.append(laser_gate_element)
                block.append(laser_element_2) # may cut back laser_gate, st laser length correct
                if ni_gate_length + aom_delay >= laser_length:
                    block.append(gate_element_after_laser)


        block.append(delay_element)
        block.append(waiting_element)


        self._extend_to_min_samples(block, prepend=True)

        # prepare return vals
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))
        created_blocks.append(block)
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=False, number_of_lasers=1)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences

    def _create_single_hahn(self, name='hahn', tau=500e-9, mw_phase=0.0,
                              laser_length=1500e-9, wait_length=1000e-9, ni_gate_length=-1e-9):

        use_ni_counter = False
        if ni_gate_length > 0.:
            use_ni_counter = True
            if self.gate_channel:
                self.logger.warning("Gated mode sensible with fastcounter, but found nicard counting enabled.")

        created_blocks = []
        created_ensembles = []
        created_sequences = []

        # prevent granularity problems
        rabi_period = self._adjust_to_samplingrate(self.rabi_period, 8)  # s
        tau = self._adjust_to_samplingrate(tau, 4)

        pi2_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0.0)
        pi_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0.0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=0.0)
        tau_element = self._get_idle_element(length=tau, increment=0.0)

        # laser readout after MW
        aom_delay = self.laser_delay

        # note: fastcomtec triggers only on falling edge
        laser_gate_element = self._get_laser_gate_element(length=aom_delay - 20e-9, increment=0)
        laser_element = self._get_laser_element(length=laser_length - aom_delay + 20e-9, increment=0)
        delay_element = self._get_idle_element(length=aom_delay, increment=0)
        waiting_element = self._get_idle_element(length=wait_length, increment=0.0)

        # only a single tau, so we can operate sync_channel just like in gating mode
        if self.sync_channel:
            laser_gate_channels = [self.sync_channel, self.laser_channel]
            laser_sync_element = self._get_trigger_element(length=aom_delay - 20e-9, increment=0, channels=laser_gate_channels)

        block = PulseBlock(name=name)
        block.append(pi2_element)
        block.append(tau_element)
        block.append(pi_element)
        block.append(tau_element)
        block.append(pi2_element)

        if not use_ni_counter:  # normal, fastcounter acquisition
            if self.gate_channel:
                block.append(laser_gate_element)
            if self.sync_channel:
                block.append(laser_sync_element)

            block.append(laser_element)
        else:   # use nicard counter and gate away dark counts
            laser_element_1 = self._get_laser_element(length=aom_delay - 10e-9, increment=0)
            laser_gate_channels = [self.sync_channel, self.laser_channel]
            laser_gate_element = self._get_trigger_element(length=ni_gate_length + 20e-9, increment=0, channels=laser_gate_channels)
            gate_after_length = ni_gate_length + aom_delay - laser_length

            # makes sure that whole laser pulse is in ni gate
            # NOT wanted
            #if aom_delay > gate_after_length:
            #    gate_after_length = aom_delay
            gate_element_after_laser = self._get_trigger_element(length=gate_after_length, increment=0, channels=[self.sync_channel])
            # negative length values allowed: cut back laser_gate_element
            laser_element_2 = self._get_laser_element(length=laser_length - ni_gate_length - aom_delay - 10e-9, increment=0)

            if self.sync_channel:
                block.append(laser_element_1)
                block.append(laser_gate_element)
                block.append(laser_element_2) # may cut back laser_gate, st laser length correct
                if ni_gate_length + aom_delay >= laser_length:
                    block.append(gate_element_after_laser)


        block.append(delay_element)
        block.append(waiting_element)

        self._extend_to_min_samples(block, prepend=True)

        # prepare return vals
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))
        created_blocks.append(block)
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=False, number_of_lasers=1)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences


    def _extend_to_min_samples(self, pulse_block, prepend=True):

        min_samples = self.pulse_generator_constraints.waveform_length.min

        if self.get_pulseblock_duration(pulse_block) * self.pulse_generator_settings['sample_rate'] < min_samples:
            length_idle = min_samples / self.pulse_generator_settings['sample_rate'] - self.get_pulseblock_duration(pulse_block)
            idle_element_extra = self._get_idle_element(length=length_idle, increment=0.0)

            if prepend:
                pulse_block.insert(0, idle_element_extra)
            else:
                pulse_block.append(idle_element_extra)

    def get_pulseblock_duration(self, pulse_block):
        # keep here, not general enough to merge into pulse_objects.py
        if pulse_block.increment_s != 0:
            self.log.error("Can't determine length of a PulseBlockElement with increment!")
            return -1

        return pulse_block.init_length_s

