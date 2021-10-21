import numpy as np
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
#from interface.pulser_interface import SequenceOrderOption
#from core.module import Connector

OFFSET_TAU_MFL_SEQMODE = 3      # number of sequence elements in front of ramseys
DELTA_TAU_I_MFL_SEQMODE = 2     # separation between different ramseys in sequence
OFFSET_TAU_MFL_LIN_SEQMODE = 1      # number of sequence elements in front of sequence segments
DELTA_TAU_I_MFL_LIN_SEQMODE = 2     # separation between different sequence segments in sequence
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
        self._jumptable['jump_address'].append(self._seqtable_counter)
        # for AWG8190 no seperate jumptable -> jump addresses are seqtable ids
        self._jumptable_address += 1

    def init_seqtable(self):
        self._seqtable = {'blocks': [], 'ensembles': [], 'seq_params': []}
        self._seqtable_counter = 0

    def init_jumptable(self):
        self._jumptable = {'name': [], 'idx_seqtable': [], 'jump_address': []}
        self._jumptable_address = 0

    def _seqtable_to_result(self):
        # as needed from sequencer
        return self._seqtable['blocks'], self._seqtable['ensembles'], self._seqtable['seq_params']

    def _get_current_seqtable_idx(self):
        # only valid while iterating through generation of sequence
        return self._seqtable_counter

    def _get_current_jumptable_address(self):
        # only valid while iterating through generation of sequence
        return self._seqtable_counter

    def generate_ppol_2x_propi(self, name="ppol_2x_propi", n_pol=100, m_read_step=20,
                        tau_ppol=50e-9, order_ppol=1, alternating=True):

        # for linear sequencers like Keysight AWG
        self.init_jumptable()  # jumping not needed, but using code infrastructure
        self.init_seqtable()
        general_params = locals()


        # read polarization has to come first
        # the laser extraction is based on the laser_rising_bins
        # which are counted in the order of the sequence step
        cur_name = 'ppol_read'
        cur_blocks, cur_ensembles, _ = self._create_single_ppol(cur_name, tau_ppol, order_ppol, 'down',
                                                                alternating=alternating)
        cur_seq_params = self._get_default_seq_params({'repetitions': int(m_read_step - 1)})
        self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        # init polarization
        cur_name = 'ppol_init_up'
        cur_blocks, cur_ensembles, _ = self._create_single_ppol(cur_name, tau_ppol, order_ppol, 'up',
                                                                alternating=False, add_gate_ch='')
        cur_seq_params = self._get_default_seq_params({'repetitions': int(n_pol - 1)})
        self._add_to_seqtable(cur_name, cur_blocks, cur_ensembles, cur_seq_params)

        # sync trigger for start readout
        sync_name = 'sync_trig'
        sync_blocks, sync_ensembles, _ = self._create_generic_trigger(sync_name, ['d_ch1'])
        sync_seq_params = self._get_default_seq_params({'repetitions': 0})
        self._add_to_seqtable(sync_name, sync_blocks, sync_ensembles, sync_seq_params)

        all_blocks, all_ensembles, ensemble_list = self._seqtable_to_result()
        sequence = PulseSequence(name=general_params['name'], ensemble_list=ensemble_list, rotating_frame=False)

        # get length of ppol_read ensemble
        idx_read = 0
        fastcounter_count_length = int(m_read_step )*self._get_ensemble_count_length(all_ensembles[idx_read], created_blocks=all_blocks)
        self.log.debug("Setting fastcounter count length to {:.3f} us".format(fastcounter_count_length * 1e6))

        contr_var = np.arange(m_read_step) + 1
        n_lasers = len(contr_var)
        n_lasers = 2*n_lasers if alternating else n_lasers
        n_phys_lasers = n_lasers + n_pol
        laser_ignore = np.arange(n_lasers, n_phys_lasers, 1)

        self._add_metadata_to_settings(sequence, alternating=alternating, created_blocks=list(),
                                       laser_ignore_list=list(laser_ignore),
                                       controlled_variable=contr_var, units=('', ''), labels=('Depol. step', 'Signal'),
                                       number_of_lasers=n_lasers,
                                       counting_length=fastcounter_count_length)

        return all_blocks, all_ensembles, [sequence]

    def _swap_pos(self, arr, pos1, pos2):
        """
        Swap pos between a<->b in 1d or 2d array likes.
        :param array:
        :param pos1: Flattened index a
        :param pos2: Flattened index b
        :return:
        """

        shape_orig = np.asarray(arr).shape
        arr_flat = np.asarray(arr).flatten()
        arr_flat[pos1], arr_flat[pos2] = arr_flat[pos2], arr_flat[pos1]
        arr = arr_flat.reshape(shape_orig)

        return arr

    def _create_init_laser_pulses(self, general_params, name='laser_wait'):
        created_blocks = []
        created_ensembles = []

        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self._create_laser_wait(name=name, laser_length=general_params['laser_length'],
                                    wait_length=general_params['wait_length']
                                    )
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # todo: check if save
        #if general_params['alternating']:
        #    raise NotImplemented("Look into repetitive_readout_methods.py if needed")

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


    def _get_index_of_ramsey(self, tau, tau_array, linear_sequencer=False):
        """
        Ramseys or equivalent (1 parameter) sequences have taus as described by tau_array.
        Get the sequence index of the tau that is closest to given first tau value.
        :param tau:
        :param tau_array:
        :return:
        """
        idx, val = self._find_nearest(tau_array, tau)
        if not linear_sequencer:
            idx_in_sequence = 1 + OFFSET_TAU_MFL_SEQMODE + DELTA_TAU_I_MFL_SEQMODE * idx
        else:
            idx_in_sequence = 1 + OFFSET_TAU_MFL_LIN_SEQMODE + DELTA_TAU_I_MFL_LIN_SEQMODE * idx
        return int(idx_in_sequence), val

    def _get_index_of_xy8(self, tau, n_xy8, tau_n_array, idx_of_seqtable=True, is_linear_sequencer=False):
        """
        XY8 or equivalent (2 parameter) sequences have taus as described by tau_array.
        Get the sequence index of the tau that is closest to given first tau value.
        :param tau: looked for tau
        :param n_xy8: looked for n_xy8
        :param tau_n_array: meshgrid like. tau_n[0][i_t,j_n] -> tau; tau_n[1][i_t,j_n] -> n_xy8
        :return:
        """
        # assumes tau_n_array is well spaced
        idx_t, val_t = self._find_nearest(tau_n_array[0][0,:], tau)
        idx_n, val_n = self._find_nearest(tau_n_array[1][:,0], n_xy8)
        len_t = len(tau_n_array[0][0,:])

        idx = len_t * idx_n + idx_t

        if not is_linear_sequencer:
            idx_in_sequence = 1 + OFFSET_TAU_MFL_SEQMODE + DELTA_TAU_I_MFL_SEQMODE * idx
        else:
            idx_in_sequence = 1 + OFFSET_TAU_MFL_LIN_SEQMODE + DELTA_TAU_I_MFL_LIN_SEQMODE * idx

        if idx_of_seqtable:
            return int(idx_in_sequence), val_t, val_n
        else:
            return int(idx), val_t, val_n

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

    def _create_generic_trigger(self, name='trigger', channels=[]):
        created_blocks = []
        created_ensembles = []
        created_sequences = []

        trig_element =  self._get_trigger_element(length=50e-9, increment=0., channels=channels)
        block = PulseBlock(name=name)
        block.append(trig_element)

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

    def _deg_to_rad(self, angle_deg):
        return angle_deg/360 * 2*np.pi

    def _create_single_ppol(self, name='ppol', tau=0.5e-6, order=1, direction='up', alternating=True,
                            add_gate_ch='d_ch4'):
            """
            based on polarisation_methods (s3 Pol20_polarize)
            """

            created_blocks = list()
            created_ensembles = list()
            created_sequences = list()
            rabi_period = self.rabi_period
            microwave_amplitude = self.microwave_amplitude
            microwave_frequency = self.microwave_frequency

            if tau / 4.0 - rabi_period / 2.0 < 0.0:
                self.log.error('PPol generation failed! Rabi period of {0:.3e} s is too long for start tau '
                               'of {1:.3e} s.'.format(rabi_period, tau))
                return

            # get readout element
            readout_element = self._get_readout_element()
            if add_gate_ch == '':
                readout_element[0].digital_high['d_ch4'] = False


            pihalfx_element = self._get_mw_element(length=rabi_period / 4, increment=0.0,
                                                           amp=microwave_amplitude, freq=microwave_frequency,
                                                           phase=0)
            pihalfminusx_element = self._get_mw_element(length=rabi_period / 4, increment=0.0,
                                                           amp=microwave_amplitude, freq=microwave_frequency,
                                                           phase=180.0)
            pihalfy_element = self._get_mw_element(length=rabi_period / 4,
                                                      increment=0.0,
                                                      amp=microwave_amplitude,
                                                      freq=microwave_frequency,
                                                      phase=90.0)
            pihalfminusy_element = self._get_mw_element(length=rabi_period / 4,
                                                      increment=0.0,
                                                      amp=microwave_amplitude,
                                                      freq=microwave_frequency,
                                                      phase=270.0)
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
            tau_element = self._get_idle_element(length=tau / 4.0 - rabi_period / 2, increment=0)

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
                block.extend(readout_element)

                if alternating:
                    # alternates readout, not pol direction
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

                    block[-1] = pihalfminusy_element
                    block.extend(readout_element)


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

                    block[-1] = pihalfx_element
                    block.extend(readout_element)


            created_blocks.append(block)
            # Create block ensemble
            block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
            block_ensemble.append((block.name, 0))

            # Create and append sync trigger block if needed
            # NO SYNC TRIGGER
            #created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
            # add metadata to invoke settings
            block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                            alternating=False, units=('s', ''),
                                                            labels=('tau', 'Signal'),
                                                            controlled_variable=[tau])
            # append ensemble to created ensembles
            created_ensembles.append(block_ensemble)
            return created_blocks, created_ensembles, created_sequences




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

    def _create_single_xy8(self, name='xy8', tau=500e-9, xy8_order=1,
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
        real_tau = max(0, tau - self.rabi_period / 2)

        tau = self._adjust_to_samplingrate(real_tau, 4)


        # create the elements
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        pihalf_read = self._get_mw_element(length=rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=self._rad_to_deg(phase_readout_rad))

        pix_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=0)
        piy_element = self._get_mw_element(length=rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=90)
        tauhalf_element = self._get_idle_element(length=tau / 2, increment=0)
        tau_element = self._get_idle_element(length=tau, increment=0)

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

        xy8_block = PulseBlock(name=name)
        xy8_block.append(pihalf_element)
        xy8_block.append(tauhalf_element)
        for n in range(xy8_order):
            xy8_block.append(pix_element)
            xy8_block.append(tau_element)
            xy8_block.append(piy_element)
            xy8_block.append(tau_element)
            xy8_block.append(pix_element)
            xy8_block.append(tau_element)
            xy8_block.append(piy_element)
            xy8_block.append(tau_element)
            xy8_block.append(piy_element)
            xy8_block.append(tau_element)
            xy8_block.append(pix_element)
            xy8_block.append(tau_element)
            xy8_block.append(piy_element)
            xy8_block.append(tau_element)
            xy8_block.append(pix_element)
            if n != xy8_order - 1:
                xy8_block.append(tau_element)
        xy8_block.append(tauhalf_element)
        xy8_block.append(pihalf_read)

        if not use_ni_counter:  # normal, fastcounter acquisition
            if self.gate_channel:
                xy8_block.append(laser_gate_element)
            if self.sync_channel:
                xy8_block.append(laser_sync_element)
            xy8_block.append(laser_element)
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
                xy8_block.append(laser_element_1)
                xy8_block.append(laser_gate_element)
                xy8_block.append(laser_element_2) # may cut back laser_gate, st laser length correct
                if ni_gate_length + aom_delay >= laser_length:
                    xy8_block.append(gate_element_after_laser)

        xy8_block.append(delay_element)
        xy8_block.append(waiting_element)

        self._extend_to_min_samples(xy8_block, prepend=True)

        # prepare return vals
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((xy8_block.name, 0))
        created_blocks.append(xy8_block)

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

