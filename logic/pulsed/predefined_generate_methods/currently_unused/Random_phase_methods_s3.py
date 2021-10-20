import numpy as np
import random
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase



class RandomPhasePredefinedGeneratorS3(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def generate_xy8_random_phase_spectroscopy_signal(self, qm_dict='None'):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(qm_dict['rabi_period'], 4)
        start_tau = self._adjust_to_samplingrate(tau_start, 2)
        tau_step = self._adjust_to_samplingrate(qm_dict['tau_step'], 2)

        # get tau array for measurement ticks
        tau_array = start_tau + np.arange(num_of_points) * tau_step


        # the idea is to adapt the waiting time in a way that the phase of a continous signal would be the same phase
        # for every block
        period = 1.0/qm_dict['freq_signal']
        waiting_length = np.zeros(num_of_points)
        for kk in range(num_of_points):
            length_of_block = qm_dict['laser_length'] + 8 * qm_dict['xy8N'] * tau_array[kk] + rabi_period /2.0
            remainder = np.around(length_of_block % period, decimals=12)
            waiting_length[kk] = np.around((period - remainder), decimals=12)
            while waiting_length[kk] < 1e-6:
                waiting_length[kk] = waiting_length[kk] + period


        # create XY8_signal block element list
        if qm_dict['signal_during_mw']:
            # get laser, delay and waiting element
            laser_element = self._get_mw_laser_element(length=qm_dict['laser_length'],
                                                       increment=0.0,
                                                       amp=qm_dict['amp_signal'],
                                                       freq=qm_dict['freq_signal'],
                                                       phase=qm_dict['signal_phase'])

            # get pihalf element
            pihalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                           increment=0,
                                                           amps=[mw_amp, qm_dict['amp_signal']],
                                                           freqs=[mw_freq, qm_dict['freq_signal']],
                                                           phases=[0.0, qm_dict['signal_phase']])
            if qm_dict['lasty']:
                piyhalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                increment=0,
                                                                amps=[mw_amp, qm_dict['amp_signal']],
                                                                freqs=[mw_freq, qm_dict['freq_signal']],
                                                                phases=[90.0, qm_dict['signal_phase']])
            if alternating:
                pi3half_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                increment=0,
                                                                amps=[mw_amp, qm_dict['amp_signal']],
                                                                freqs=[mw_freq, qm_dict['freq_signal']],
                                                                phases=[180.0, qm_dict['signal_phase']])
                if qm_dict['lasty']:
                    piy3half_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                     increment=0,
                                                                     amps=[mw_amp, qm_dict['amp_signal']],
                                                                     freqs=[mw_freq, qm_dict['freq_signal']],
                                                                     phases=[270.0, qm_dict['signal_phase']])

        else:
            # get laser and delay element
            laser_element = self._get_laser_gate_element(length=qm_dict['laser_length'],
                                                         increment=0)
            # get pihalf element
            pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                                  increment=0.0,
                                                  amp=mw_amp,
                                                  freq=mw_freq,
                                                  phase=0.0)
            if qm_dict['lasty']:
                piyhalf_element = self._get_mw_element(length=rabi_period / 4,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=90.0)
            if alternating:
                # get -x pihalf (3pihalf) element
                pi3half_element = self._get_mw_element(length=rabi_period / 4,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=180.0)
                if qm_dict['lasty']:
                    pi3yhalf_element = self._get_mw_element(length=rabi_period / 4,
                                                            increment=0.0,
                                                            amp=mw_amp,
                                                            freq=mw_freq,
                                                            phase=270.0)

        block = PulseBlock(name=name)
        for ii in range(num_of_points):
            # get pure interaction elements
            tauhalf_element = self._get_mw_element(length=tau_array[ii] / 2.0 - rabi_period / 4,
                                                   increment=0.0,
                                                   amp=qm_dict['amp_signal'],
                                                   freq=qm_dict['freq_signal'],
                                                   phase=qm_dict['signal_phase'])
            tau_element = self._get_mw_element(length=tau_array[ii] - rabi_period / 2,
                                               increment=0.0,
                                               amp=qm_dict['amp_signal'],
                                               freq=qm_dict['freq_signal'],
                                               phase=qm_dict['signal_phase'])
            block.append(pihalf_element)

            for nn in range(qm_dict['xy8N']):

                if randomize:
                    random_phase = random.uniform(0, 360)
                else:
                    random_phase = 0

                # get pi elements
                if qm_dict['signal_during_mw']:
                    # get pi elements
                    pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                                increment=0,
                                                                amps=[mw_amp, qm_dict['amp_signal']],
                                                                freqs=[mw_freq, qm_dict['freq_signal']],
                                                                phases=[random_phase, qm_dict['signal_phase']])

                    piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                                increment=0,
                                                                amps=[mw_amp, qm_dict['amp_signal']],
                                                                freqs=[mw_freq, qm_dict['freq_signal']],
                                                                phases=[90.0+random_phase, qm_dict['signal_phase']])
                else:
                    pix_element = self._get_mw_element(length=rabi_period / 2,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=random_phase)

                    piy_element = self._get_mw_element(length=rabi_period / 2,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=90.0+random_phase)


                block.append(tauhalf_element)
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
                block.append(tauhalf_element)
            if qm_dict['lasty']:
                block.append(piyhalf_element)
            else:
                block.append(pihalf_element)
            block.append(laser_element)
            # get current waiting element
            if qm_dict['signal_during_mw']:
                waiting_element = self._get_mw_element(waiting_length[ii],
                                                       increment=0.0,
                                                       amp=qm_dict['amp_signal'],
                                                       freq=qm_dict['freq_signal'],
                                                       phase=qm_dict['signal_phase'])
            else:
                waiting_element = self._get_idle_element(length=waiting_length[ii],
                                                         increment=0.0)

            block.append(waiting_element)
            # add alternating sequence
            if alternating:
                block.append(pihalf_element)
                for nn in range(qm_dict['xy8N']):
                    block.append(tauhalf_element)
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
                    block.append(tauhalf_element)

                if qm_dict['lasty']:
                    block.append(piy3half_element)
                else:
                    block.append(pi3half_element)
                block.append(laser_element)
                block.append(waiting_element)

        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating,
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_xy8_random_phase_2d(self, qm_dict=''):
        """
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get x_axis for measurement ticks
        x_axis = np.linspace(1,qm_dict['number_rabi']*qm_dict['number_freq'],qm_dict['number_rabi']*qm_dict['number_freq'])
        # get rabi_period parameters
        rabi_array = qm_dict['rabi_freq_start'] + np.arange(qm_dict['number_rabi']) * qm_dict['rabi_freq_incr']
        # get frequency parameters
        freq_array = qm_dict['mw_freq_start'] + np.arange(qm_dict['number_freq']) * qm_dict['mw_freq_incr']
        # get random phases
        random_phase = [0] * xy8_order
        if randomize:
            for ii in range(xy8_order):
                random_phase[ii] = random.uniform(0, 360)

        time_trace = 0

        # get readout element
        readout_element = self._get_readout_element()

        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=mw_amp,
                                              freq=qm_dict['resonant_frequency'],
                                              phase=0.0)


        # create XY8-N block element list
        block = PulseBlock(name=name)
        for rabi_freq in rabi_array:
            rabi_period = self._adjust_to_samplingrate(1/rabi_freq, 8)
            tau = self._adjust_to_samplingrate(tau-rabi_period/2, 2)
            # get tauhalf element
            tauhalf_element = self._get_idle_element(length=tau/2, increment=0)
            # get tau element
            tau_element = self._get_idle_element(length=tau, increment=0)

            for freq in freq_array:
                # actual XY8-N sequence
                block.append(pihalf_element)

                time_trace = time_trace + tau/2
                for nn in range(xy8_order):
                    block.append(tauhalf_element)
                    # get pi elements
                    phase_correction = time_trace * (freq - qm_dict['resonant_frequency']) * 360
                    pix_element = self._get_mw_element(length=rabi_period / 2,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=(random_phase[nn] - phase_correction) % 360)
                    # get pi elements
                    piy_element = self._get_mw_element(length=rabi_period / 2,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=(random_phase[nn] + 90 - phase_correction) % 360)


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
                    block.append(tauhalf_element)

                    time_trace = time_trace + 8 * rabi_period / 2 + 7 * tau


                block.append(tauhalf_element)
                phase_correction2 = ((freq - qm_dict['resonant_frequency']) * (8 * xy8_order * tau ) * 360) % 360
                #self.log.warning('phasecorrection2:' + str(phase_correction2))
                pihalf_element_final = self._get_mw_element(length=rabi_period / 4,
                                                      increment=0.0,
                                                      amp=mw_amp,
                                                      freq=qm_dict['resonant_frequency'],
                                                      phase=phase_correction2)
                block.append(pihalf_element_final)
                block.extend(readout_element)
                time_trace = time_trace + tau/2 + rabi_period / 4 + qm_dict['laser_length'] + \
                             qm_dict['delay_length'] + qm_dict['waiting_time']

        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating,
                                                        controlled_variable=x_axis)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    # FIXME:


    def generate_xy8_random_phase3(self, name='xy8_rp3', rabi_freq_start=30e6, rabi_freq_incr=1.0e6, number_rabi=10,
                                   mw_freq_start=2870.0e6, mw_freq_incr=1.0e6, number_freq=10, mw_amp=0.1,
                                   tau=0.5e-6, xy8_order=4, randomize=True, phase_error=0,
                                   resonant_rabi_period=20e-9, resonant_frequency=3.0e9,
                                   mw_channel='a_ch1', laser_length=3.0e-6, channel_amp=1.0, delay_length=0.7e-6,
                                   wait_time=1.0e-6, sync_trig_channel='', gate_count_channel='', alternating=True):
        """

        """
        # Sanity checks
        if gate_count_channel == '':
            gate_count_channel = None
        if sync_trig_channel == '':
            sync_trig_channel = None
        err_code = self._do_channel_sanity_checks(mw_channel=mw_channel,
                                                  gate_count_channel=gate_count_channel,
                                                  sync_trig_channel=sync_trig_channel)
        if err_code != 0:
            return

        # get x_axis for measurement ticks
        x_axis = np.linspace(1, number_rabi * number_freq, number_rabi * number_freq)
        # get rabi_period parameters
        rabi_array = rabi_freq_start + np.arange(number_rabi) * rabi_freq_incr
        # get frequency parameters
        freq_array = mw_freq_start + np.arange(number_freq) * mw_freq_incr
        # get random phases
        random_phase = [0] * xy8_order
        if randomize:
            for ii in range(xy8_order):
                random_phase[ii] = random.uniform(0, 360)

        # get waiting element
        waiting_element = self._get_idle_element(wait_time, 0.0, False)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
                                                               channel_amp, gate_count_channel)

        # get pihalf element
        length_pi_2 = self._adjust_to_samplingrate(resonant_rabi_period / 4, 1)
        pihalf_element = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp, resonant_frequency, 0.0)
        # get -x pihalf (3pihalf) element
        pi3half_element = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp, resonant_frequency, 180.)

        if sync_trig_channel is not None:
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, sync_trig_channel,
                                                        amp=channel_amp)
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)

        # create XY8-N block element list
        block = []

        for rabi_freq in rabi_array:
            period = self._adjust_to_samplingrate(1 / rabi_freq, 8)
            # calculate "real" tau length of the waiting times (tau and tauhalf)
            real_tau = tau - period / 2
            real_tauhalf = tau / 2 - 3 * period / 8
            real_tauhalf = self._adjust_to_samplingrate(real_tauhalf, 1)
            # self.log.warning('Real tau half:' + str(real_tauhalf))
            if real_tau < 0.0 or real_tauhalf < 0.0:
                self.log.error('XY8 generation failed! Rabi period of {0:.3e} s is too long for start tau '
                               'of {1:.3e} s.'.format(period, tau))
                return

            # get tauhalf element
            tauhalf_element = self._get_idle_element(real_tauhalf, 0, False)
            # get tau element
            tau_element = self._get_idle_element(real_tau, 0, False)

            for freq in freq_array:

                # get pihalf element
                # pihalf_element = self._get_mw_element(resonant_rabi_period / 4, 0.0, mw_channel, False, mw_amp,
                #                                     freq, 0.0)
                # get -x pihalf (3pihalf) element
                # pi3half_element = self._get_mw_element(resonant_rabi_period / 4, 0.0, mw_channel, False, mw_amp,
                #                                      freq, 180.)


                # actual XY8-N sequence
                block.append(pihalf_element)
                phase_extra = (resonant_frequency * length_pi_2 * 360)%360
                block.append(tauhalf_element)
                time_trace = real_tauhalf
                for n in range(xy8_order):

                    # get pi elements
                    phase_correction = (time_trace * freq * 360 + phase_extra)%360

                    pix_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + phase_correction) % 360)

                    block.append(pix_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)


                    block.append(piy_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    pix_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + phase_error + phase_correction) % 360)

                    block.append(pix_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                    block.append(piy_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                    block.append(piy_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    pix_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + phase_error + phase_correction) % 360)

                    block.append(pix_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                    block.append(piy_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    pix_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + phase_error + phase_correction) % 360)

                    block.append(pix_element)

                    time_trace = time_trace + period / 2

                    if n != xy8_order - 1:
                        block.append(tau_element)
                        time_trace = time_trace + real_tau

                block.append(tauhalf_element)
                time_trace = time_trace + real_tauhalf
                phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                self.log.warning('phasecorrection:' + str(phase_correction))
                pihalf_element_final = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp, resonant_frequency,
                                                            phase_correction)
                block.append(pihalf_element_final)
                block.append(laser_element)
                block.append(delay_element)
                block.append(waiting_element)

                #time_trace = time_trace + real_tauhalf + length_pi_2 + laser_length + delay_length + wait_time

                if alternating:
                    block.append(pihalf_element)
                    block.append(tauhalf_element)
                    for n in range(xy8_order):

                        pix_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           random_phase[n])
                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           random_phase[n] + 90.0 + phase_error)
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
                    block.append(pi3half_element)
                    block.append(laser_element)
                    block.append(delay_element)
                    block.append(waiting_element)

        # create XY8-N block object
        xy8_block = PulseBlock(name, block)
        self.save_block(name, xy8_block)

        # create block list and ensemble object
        block_list = [(xy8_block, 0)]
        if sync_trig_channel is not None:
            block_list.append((seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        # add metadata to invoke settings later on
        block_ensemble.sample_rate = self.sample_rate
        block_ensemble.activation_config = self.activation_config
        block_ensemble.amplitude_dict = self.amplitude_dict
        block_ensemble.laser_channel = self.laser_channel
        block_ensemble.alternating = alternating
        block_ensemble.laser_ignore_list = []
        block_ensemble.controlled_vals_array = x_axis
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    def generate_yy8_random_phase1(self, name='yy8_rp1', rabi_period=1.0e-6, mw_freq=2870.0e6, mw_amp=0.1,
                         start_tau=0.5e-6, tau_step=0.01e-6, num_of_points=50, yy8_order=4, randomize = True,
                                  phase_error = 0,
                         mw_channel='a_ch1', laser_length=3.0e-6, channel_amp=1.0, delay_length=0.7e-6,
                         wait_time=1.0e-6, sync_trig_channel='', gate_count_channel='', alternating=True):
        """

        """
        # Sanity checks
        if gate_count_channel == '':
            gate_count_channel = None
        if sync_trig_channel == '':
            sync_trig_channel = None
        err_code = self._do_channel_sanity_checks(mw_channel=mw_channel,
                                                  gate_count_channel=gate_count_channel,
                                                  sync_trig_channel=sync_trig_channel)
        if err_code != 0:
            return

        # get tau array for measurement ticks
        tau_array = start_tau + np.arange(num_of_points) * tau_step
        # calculate "real" start length of the waiting times (tau and tauhalf)
        real_start_tau = start_tau - rabi_period / 2
        real_start_tauhalf = start_tau / 2 - 3 * rabi_period / 8
        if real_start_tau < 0.0 or real_start_tauhalf < 0.0:
            self.log.error('YY8 generation failed! Rabi period of {0:.3e} s is too long for start tau '
                           'of {1:.3e} s.'.format(rabi_period, start_tau))
            return

        # get waiting element
        waiting_element = self._get_idle_element(wait_time, 0.0, False)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
                                                               channel_amp, gate_count_channel)
        # get pihalf element
        pihalf_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp, mw_freq,
                                              0.0)
        # get -x pihalf (3pihalf) element
        pi3half_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp,
                                               mw_freq, 180.)
        # get tauhalf element
        tauhalf_element = self._get_idle_element(real_start_tauhalf, tau_step / 2, False)
        # get tau element
        tau_element = self._get_idle_element(real_start_tau, tau_step, False)

        if sync_trig_channel is not None:
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, sync_trig_channel,
                                                        amp=channel_amp)
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)

        # create XY8-N block element list
        yy8_elem_list = []
        # actual XY8-N sequence
        yy8_elem_list.append(pihalf_element)
        yy8_elem_list.append(tauhalf_element)
        for n in range(yy8_order):

            # get pi elements
            if randomize:
                random_phase = random.uniform(0, 360)
            else:
                random_phase = 0
            piy1_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq, random_phase-90)
            piy2_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq, random_phase+90.0+phase_error)

            if n==0:
                yy8_elem_list.append( self._get_mw_element(rabi_period / 2, 0.0, mw_channel, True,
                                                            mw_amp, mw_freq,random_phase-90))
                yy8_elem_list.append(self._get_idle_element(real_start_tau, tau_step, True))
            else:
                yy8_elem_list.append(piy1_element)
                yy8_elem_list.append(tau_element)
            yy8_elem_list.append(piy2_element)
            yy8_elem_list.append(tau_element)
            yy8_elem_list.append(piy2_element)
            yy8_elem_list.append(tau_element)
            yy8_elem_list.append(piy1_element)
            yy8_elem_list.append(tau_element)
            yy8_elem_list.append(piy1_element)
            yy8_elem_list.append(tau_element)
            yy8_elem_list.append(piy1_element)
            yy8_elem_list.append(tau_element)
            yy8_elem_list.append(piy2_element)
            yy8_elem_list.append(tau_element)
            yy8_elem_list.append(piy2_element)
            if n != yy8_order-1:
                yy8_elem_list.append(tau_element)
        yy8_elem_list.append(tauhalf_element)
        yy8_elem_list.append(pihalf_element)
        yy8_elem_list.append(laser_element)
        yy8_elem_list.append(delay_element)
        yy8_elem_list.append(waiting_element)

        if alternating:
            yy8_elem_list.append(pihalf_element)
            yy8_elem_list.append(tauhalf_element)
            for n in range(yy8_order):
                if randomize:
                    random_phase = random.uniform(0, 360)
                else:
                    random_phase = 0
                piy1_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq, random_phase + 90)
                piy2_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq,random_phase - 90.0+phase_error)
                yy8_elem_list.append(piy2_element)
                yy8_elem_list.append(tau_element)
                yy8_elem_list.append(piy1_element)
                yy8_elem_list.append(tau_element)
                yy8_elem_list.append(piy1_element)
                yy8_elem_list.append(tau_element)
                yy8_elem_list.append(piy2_element)
                yy8_elem_list.append(tau_element)
                yy8_elem_list.append(piy2_element)
                yy8_elem_list.append(tau_element)
                yy8_elem_list.append(piy2_element)
                yy8_elem_list.append(tau_element)
                yy8_elem_list.append(piy1_element)
                yy8_elem_list.append(tau_element)
                yy8_elem_list.append(piy1_element)
                if n != yy8_order - 1:
                    yy8_elem_list.append(tau_element)
            yy8_elem_list.append(tauhalf_element)
            yy8_elem_list.append(pi3half_element)
            yy8_elem_list.append(laser_element)
            yy8_elem_list.append(delay_element)
            yy8_elem_list.append(waiting_element)

        # create XY8-N block object
        yy8_block = PulseBlock(name, yy8_elem_list)
        self.save_block(name, yy8_block)

        # create block list and ensemble object
        block_list = [(yy8_block, num_of_points - 1)]
        if sync_trig_channel is not None:
            block_list.append((seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
        # add metadata to invoke settings later on
        block_ensemble.sample_rate = self.sample_rate
        block_ensemble.activation_config = self.activation_config
        block_ensemble.amplitude_dict = self.amplitude_dict
        block_ensemble.laser_channel = self.laser_channel
        block_ensemble.alternating = alternating
        block_ensemble.laser_ignore_list = []
        block_ensemble.controlled_vals_array = tau_array
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    def generate_yy8_random_phase(self, name='xy8_rp3', rabi_freq_start=30e6, rabi_freq_incr=1.0e6, number_rabi=10,
                                   mw_freq_start=2870.0e6, mw_freq_incr=1.0e6, number_freq=10, mw_amp=0.1,
                                   tau=0.5e-6, xy8_order=4, randomize=True, phase_error=0,
                                   resonant_rabi_period=20e-9, resonant_frequency=3.0e9, add_phase = 0,
                                   mw_channel='a_ch1', laser_length=3.0e-6, channel_amp=1.0, delay_length=0.7e-6,
                                   wait_time=1.0e-6, sync_trig_channel='', gate_count_channel='', alternating=True):
        """

        """
        # Sanity checks
        if gate_count_channel == '':
            gate_count_channel = None
        if sync_trig_channel == '':
            sync_trig_channel = None
        err_code = self._do_channel_sanity_checks(mw_channel=mw_channel,
                                                  gate_count_channel=gate_count_channel,
                                                  sync_trig_channel=sync_trig_channel)
        if err_code != 0:
            return

        # get x_axis for measurement ticks
        x_axis = np.linspace(1, number_rabi * number_freq, number_rabi * number_freq)
        # get rabi_period parameters
        rabi_array = rabi_freq_start + np.arange(number_rabi) * rabi_freq_incr
        # get frequency parameters
        freq_array = mw_freq_start + np.arange(number_freq) * mw_freq_incr
        # get random phases
        random_phase = [0] * xy8_order
        if randomize:
            for ii in range(xy8_order):
                random_phase[ii] = random.uniform(0, 360)

        # get waiting element
        waiting_element = self._get_idle_element(wait_time, 0.0, False)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
                                                               channel_amp, gate_count_channel)

        # get pihalf element
        length_pi_2 = self._adjust_to_samplingrate(resonant_rabi_period / 4, 1)
        pihalf_element = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp, resonant_frequency, 0.0)
        # get -x pihalf (3pihalf) element
        pi3half_element = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp, resonant_frequency, 180.)

        if sync_trig_channel is not None:
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, sync_trig_channel,
                                                        amp=channel_amp)
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)

        # create XY8-N block element list
        yy8_elem_list = []

        for rabi_freq in rabi_array:
            period = self._adjust_to_samplingrate(1 / rabi_freq, 8)
            # calculate "real" tau length of the waiting times (tau and tauhalf)
            real_tau = tau - period / 2
            real_tauhalf = tau / 2 - 3 * period / 8
            real_tauhalf = self._adjust_to_samplingrate(real_tauhalf, 1)
            # self.log.warning('Real tau half:' + str(real_tauhalf))
            if real_tau < 0.0 or real_tauhalf < 0.0:
                self.log.error('XY8 generation failed! Rabi period of {0:.3e} s is too long for start tau '
                               'of {1:.3e} s.'.format(period, tau))
                return

            # get tauhalf element
            tauhalf_element = self._get_idle_element(real_tauhalf, 0, False)
            # get tau element
            tau_element = self._get_idle_element(real_tau, 0, False)

            for freq in freq_array:

                # get pihalf element
                # pihalf_element = self._get_mw_element(resonant_rabi_period / 4, 0.0, mw_channel, False, mw_amp,
                #                                     freq, 0.0)
                # get -x pihalf (3pihalf) element
                # pi3half_element = self._get_mw_element(resonant_rabi_period / 4, 0.0, mw_channel, False, mw_amp,
                #                                      freq, 180.)


                # actual XY8-N sequence
                yy8_elem_list.append(pihalf_element)
                phase_extra = (resonant_frequency * length_pi_2 * 360  + add_phase)%360
                yy8_elem_list.append(tauhalf_element)
                time_trace = real_tauhalf
                for n in range(xy8_order):

                    # get pi elements
                    phase_correction = (time_trace * freq * 360 + phase_extra)%360

                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] - 90.0 + phase_correction) % 360)

                    yy8_elem_list.append(piy_element)
                    yy8_elem_list.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)


                    yy8_elem_list.append(piy_element)
                    yy8_elem_list.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                    yy8_elem_list.append(piy_element)
                    yy8_elem_list.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] - 90.0 + phase_error + phase_correction) % 360)

                    yy8_elem_list.append(piy_element)
                    yy8_elem_list.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] - 90.0 + phase_error + phase_correction) % 360)

                    yy8_elem_list.append(piy_element)
                    yy8_elem_list.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] - 90.0 + phase_error + phase_correction) % 360)

                    yy8_elem_list.append(piy_element)
                    yy8_elem_list.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                    yy8_elem_list.append(piy_element)
                    yy8_elem_list.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                    yy8_elem_list.append(piy_element)

                    time_trace = time_trace + period / 2

                    if n != xy8_order - 1:
                        yy8_elem_list.append(tau_element)
                        time_trace = time_trace + real_tau

                yy8_elem_list.append(tauhalf_element)
                time_trace = time_trace + real_tauhalf
                phase_correction = (time_trace * freq * 360 + phase_extra-add_phase+180) % 360
                #self.log.warning('phasecorrection:' + str(phase_correction))
                pihalf_element_final = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp, resonant_frequency,
                                                            phase_correction)
                yy8_elem_list.append(pihalf_element_final)
                yy8_elem_list.append(laser_element)
                yy8_elem_list.append(delay_element)
                yy8_elem_list.append(waiting_element)

                #time_trace = time_trace + real_tauhalf + length_pi_2 + laser_length + delay_length + wait_time

                if alternating:
                    yy8_elem_list.append(pihalf_element)
                    phase_extra = (resonant_frequency * length_pi_2 * 360 + add_phase) % 360
                    yy8_elem_list.append(tauhalf_element)
                    time_trace = real_tauhalf

                    for n in range(xy8_order):

                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360

                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           (random_phase[n] - 90.0 + phase_correction) % 360)


                        yy8_elem_list.append(piy_element)
                        yy8_elem_list.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                        yy8_elem_list.append(piy_element)
                        yy8_elem_list.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                        yy8_elem_list.append(piy_element)
                        yy8_elem_list.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           (random_phase[n] - 90.0 + phase_error + phase_correction) % 360)

                        yy8_elem_list.append(piy_element)
                        yy8_elem_list.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           (random_phase[n] - 90.0 + phase_error + phase_correction) % 360)

                        yy8_elem_list.append(piy_element)
                        yy8_elem_list.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           (random_phase[n] - 90.0 + phase_error + phase_correction) % 360)

                        yy8_elem_list.append(piy_element)
                        yy8_elem_list.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)
                        yy8_elem_list.append(piy_element)
                        yy8_elem_list.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                        yy8_elem_list.append(piy_element)
                        time_trace = time_trace + period / 2

                        if n != xy8_order - 1:
                            yy8_elem_list.append(tau_element)
                            time_trace = time_trace + real_tau

                    yy8_elem_list.append(tauhalf_element)
                    time_trace = time_trace + real_tauhalf
                    phase_correction = (time_trace * freq * 360 + phase_extra - add_phase) % 360
                    #self.log.warning('phasecorrection:' + str(phase_correction))
                    pihalf_element_final = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp,
                                                                resonant_frequency,
                                                                phase_correction)
                    yy8_elem_list.append(pihalf_element_final)
                    yy8_elem_list.append(laser_element)
                    yy8_elem_list.append(delay_element)
                    yy8_elem_list.append(waiting_element)

        # create XY8-N block object
        yy8_block = PulseBlock(name, yy8_elem_list)
        self.save_block(name, yy8_block)

        # create block list and ensemble object
        block_list = [(yy8_block, 0)]
        if sync_trig_channel is not None:
            block_list.append((seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        # add metadata to invoke settings later on
        block_ensemble.sample_rate = self.sample_rate
        block_ensemble.activation_config = self.activation_config
        block_ensemble.amplitude_dict = self.amplitude_dict
        block_ensemble.laser_channel = self.laser_channel
        block_ensemble.alternating = alternating
        block_ensemble.laser_ignore_list = []
        block_ensemble.controlled_vals_array = x_axis
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    def generate_kdd_random_phase(self, name='kdd', rabi_freq_start=30e6, rabi_freq_incr=1.0e6, number_rabi=10,
                                  mw_freq_start=2870.0e6, mw_freq_incr=1.0e6, number_freq=10, mw_amp=0.1,
                                  tau=0.5e-6, kdd_order=4, randomize=True, phase_error=0,
                                  resonant_rabi_period=20e-9, resonant_frequency=3.0e9, add_phase=0,
                                  mw_channel='a_ch1', laser_length=3.0e-6, channel_amp=1.0, delay_length=0.7e-6,
                                  wait_time=1.0e-6, sync_trig_channel='', gate_count_channel='', alternating=True):
        """

        """
        # Sanity checks
        if gate_count_channel == '':
            gate_count_channel = None
        if sync_trig_channel == '':
            sync_trig_channel = None
        err_code = self._do_channel_sanity_checks(mw_channel=mw_channel,
                                                  gate_count_channel=gate_count_channel,
                                                  sync_trig_channel=sync_trig_channel)
        if err_code != 0:
            return

        # get x_axis for measurement ticks
        x_axis = np.linspace(1, number_rabi * number_freq, number_rabi * number_freq)
        # get rabi_period parameters
        rabi_array = rabi_freq_start + np.arange(number_rabi) * rabi_freq_incr
        # get frequency parameters
        freq_array = mw_freq_start + np.arange(number_freq) * mw_freq_incr
        # get random phases
        random_phase = [0] * kdd_order
        if randomize:
            for ii in range(kdd_order):
                random_phase[ii] = random.uniform(0, 360)
        self.log.warning(random_phase)

        # get waiting element
        waiting_element = self._get_idle_element(wait_time, 0.0, False)
        # get laser and delay element
        laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
                                                               channel_amp, gate_count_channel)

        # get pihalf element
        length_pi_2 = self._adjust_to_samplingrate(resonant_rabi_period / 4, 1)
        pihalf_element = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp, resonant_frequency, 0.0)
        # get -x pihalf (3pihalf) element
        pi3half_element = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp, resonant_frequency, 180.)

        if sync_trig_channel is not None:
            # get sequence trigger element
            seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, sync_trig_channel,
                                                        amp=channel_amp)
            # Create its own block out of the element
            seq_block = PulseBlock('seq_trigger', [seqtrig_element])
            # save block
            self.save_block('seq_trigger', seq_block)

        # create KDD-N block element list
        block = []
        phase_extra = (resonant_frequency * length_pi_2 * 360 + add_phase) % 360

        for rabi_freq in rabi_array:
            period = self._adjust_to_samplingrate(1 / rabi_freq, 8)
            # calculate "real" tau length of the waiting times (tau and tauhalf)
            real_tau = tau - period / 2
            real_tauhalf = tau / 2 - 3 * period / 8
            real_tauhalf = self._adjust_to_samplingrate(real_tauhalf, 1)
            # self.log.warning('Real tau half:' + str(real_tauhalf))
            if real_tau < 0.0 or real_tauhalf < 0.0:
                self.log.error('KDD generation failed! Rabi period of {0:.3e} s is too long for start tau '
                               'of {1:.3e} s.'.format(period, tau))
                return

            # get tauhalf element
            tauhalf_element = self._get_idle_element(real_tauhalf, 0, False)
            # get tau element
            tau_element = self._get_idle_element(real_tau, 0, False)

            for freq in freq_array:


                # actual kdd-N sequence
                block.append(pihalf_element)
                block.append(tauhalf_element)
                time_trace = real_tauhalf
                for n in range(kdd_order):

                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360

                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 30.0 + phase_correction) % 360)

                    block.append(mw_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 0.0 + phase_error + phase_correction) % 360)

                    block.append(mw_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                    block.append(mw_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n]  + 0.0 + phase_error + phase_correction) % 360)

                    block.append(mw_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 30.0 + phase_error + phase_correction) % 360)

                    block.append(mw_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 120.0 + phase_error + phase_correction) % 360)

                    block.append(mw_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                      (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                    block.append(mw_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                      (random_phase[n] + 180.0 + phase_error + phase_correction) % 360)

                    block.append(mw_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                    block.append(mw_element)
                    block.append(tau_element)

                    time_trace = time_trace + period / 2 + real_tau
                    phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                    mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                       (random_phase[n] + 120.0 + phase_error + phase_correction) % 360)

                    block.append(mw_element)

                    time_trace = time_trace + period / 2

                    if n != kdd_order - 1:
                        block.append(tau_element)
                        time_trace = time_trace + real_tau

                block.append(tauhalf_element)
                time_trace = time_trace + real_tauhalf
                phase_correction = (time_trace * freq * 360 + phase_extra - add_phase + 180) % 360
                self.log.warning('phasecorrection:' + str(phase_correction))
                pihalf_element_final = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp, resonant_frequency,
                                                            phase_correction)
                block.append(pihalf_element_final)
                block.append(laser_element)
                block.append(delay_element)
                block.append(waiting_element)

                # time_trace = time_trace + real_tauhalf + length_pi_2 + laser_length + delay_length + wait_time

                if alternating:
                    block.append(pihalf_element)
                    phase_extra = (resonant_frequency * length_pi_2 * 360 + add_phase) % 360
                    block.append(tauhalf_element)
                    time_trace = real_tauhalf
                    for n in range(kdd_order):

                        # get pi elements
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360

                        mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                          (random_phase[n] + 30.0 + phase_correction) % 360)

                        block.append(mw_element)
                        block.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                          (random_phase[n] + phase_error + phase_correction) % 360)

                        block.append(mw_element)
                        block.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                          (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                        block.append(mw_element)
                        block.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                          (random_phase[n] + phase_error + phase_correction) % 360)

                        block.append(mw_element)
                        block.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                          (random_phase[n] + 30.0 + phase_error + phase_correction) % 360)

                        block.append(mw_element)
                        block.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                          (random_phase[n] + 120.0 + phase_error + phase_correction) % 360)

                        block.append(mw_element)
                        block.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                          (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                        block.append(mw_element)
                        block.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                          (random_phase[n] + 180.0 + phase_error + phase_correction) % 360)

                        block.append(mw_element)
                        block.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        mw_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                          (random_phase[n] + 90.0 + phase_error + phase_correction) % 360)

                        block.append(mw_element)
                        block.append(tau_element)

                        time_trace = time_trace + period / 2 + real_tau
                        phase_correction = (time_trace * freq * 360 + phase_extra) % 360
                        piy_element = self._get_mw_element(period / 2, 0.0, mw_channel, False, mw_amp, freq,
                                                           (random_phase[n] + 120.0 + phase_error + phase_correction) % 360)

                        block.append(piy_element)

                        time_trace = time_trace + period / 2

                        if n != kdd_order - 1:
                            block.append(tau_element)
                            time_trace = time_trace + real_tau

                    block.append(tauhalf_element)
                    time_trace = time_trace + real_tauhalf
                    phase_correction = (time_trace * freq * 360 + phase_extra - add_phase) % 360
                    self.log.warning('phasecorrection:' + str(phase_correction))
                    pihalf_element_final = self._get_mw_element(length_pi_2, 0.0, mw_channel, False, mw_amp,
                                                                resonant_frequency,
                                                                phase_correction)
                    block.append(pihalf_element_final)
                    block.append(laser_element)
                    block.append(delay_element)
                    block.append(waiting_element)

        # create XY8-N block object
        kdd_block = PulseBlock(name, block)
        self.save_block(name, kdd_block)

        # create block list and ensemble object
        block_list = [(kdd_block, 0)]
        if sync_trig_channel is not None:
            block_list.append((seq_block, 0))

        # create ensemble out of the block(s)
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        # add metadata to invoke settings later on
        block_ensemble.sample_rate = self.sample_rate
        block_ensemble.activation_config = self.activation_config
        block_ensemble.amplitude_dict = self.amplitude_dict
        block_ensemble.laser_channel = self.laser_channel
        block_ensemble.alternating = alternating
        block_ensemble.laser_ignore_list = []
        block_ensemble.controlled_vals_array = x_axis
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        return block_ensemble


    def generate_xy4_random_phase_spectroscopy_signal(self, qm_dict='None'):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(qm_dict['rabi_period'], 4)
        start_tau = self._adjust_to_samplingrate(tau_start, 2)
        tau_step = self._adjust_to_samplingrate(qm_dict['tau_step'], 2)

        # get tau array for measurement ticks
        tau_array = start_tau + np.arange(num_of_points) * tau_step


        # the idea is to adapt the waiting time in a way that the phase of a continous signal would be the same phase
        # for every block
        period = 1.0/qm_dict['freq_signal']
        waiting_length = np.zeros(num_of_points)
        for kk in range(num_of_points):
            length_of_block = qm_dict['laser_length'] + 8 * qm_dict['xy8N'] * tau_array[kk] + rabi_period /2.0
            remainder = np.around(length_of_block % period, decimals=12)
            waiting_length[kk] = np.around((period - remainder), decimals=12)
            while waiting_length[kk] < 1e-6:
                waiting_length[kk] = waiting_length[kk] + period


        # create XY4_signal block element list

        if qm_dict['signal_during_mw']:
            # get laser, delay and waiting element
            laser_element = self._get_mw_laser_element(length=qm_dict['laser_length'],
                                                       increment=0.0,
                                                       amp=qm_dict['amp_signal'],
                                                       freq=qm_dict['freq_signal'],
                                                       phase=qm_dict['signal_phase'])

            # get pihalf element
            pihalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                           increment=0,
                                                           amps=[mw_amp, qm_dict['amp_signal']],
                                                           freqs=[mw_freq, qm_dict['freq_signal']],
                                                           phases=[0.0, qm_dict['signal_phase']])
            if qm_dict['lasty']:
                piyhalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                increment=0,
                                                                amps=[mw_amp, qm_dict['amp_signal']],
                                                                freqs=[mw_freq, qm_dict['freq_signal']],
                                                                phases=[90.0, qm_dict['signal_phase']])
            if alternating:
                pi3half_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                increment=0,
                                                                amps=[mw_amp, qm_dict['amp_signal']],
                                                                freqs=[mw_freq, qm_dict['freq_signal']],
                                                                phases=[180.0, qm_dict['signal_phase']])
                if qm_dict['lasty']:
                    piy3half_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                     increment=0,
                                                                     amps=[mw_amp, qm_dict['amp_signal']],
                                                                     freqs=[mw_freq, qm_dict['freq_signal']],
                                                                     phases=[270.0, qm_dict['signal_phase']])

        else:
            # get laser and delay element
            laser_element = self._get_laser_gate_element(length=qm_dict['laser_length'],
                                                         increment=0)
            # get pihalf element
            pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                                  increment=0.0,
                                                  amp=mw_amp,
                                                  freq=mw_freq,
                                                  phase=0.0)
            if qm_dict['lasty']:
                piyhalf_element = self._get_mw_element(length=rabi_period / 4,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=90.0)
            if alternating:
                # get -x pihalf (3pihalf) element
                pi3half_element = self._get_mw_element(length=rabi_period / 4,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=180.0)
                if qm_dict['lasty']:
                    pi3yhalf_element = self._get_mw_element(length=rabi_period / 4,
                                                            increment=0.0,
                                                            amp=mw_amp,
                                                            freq=mw_freq,
                                                            phase=270.0)

        block = PulseBlock(name=name)
        for ii in range(num_of_points):
            # get pure interaction elements
            tauhalf_element = self._get_mw_element(length=tau_array[ii] / 2.0 - rabi_period / 4,
                                                   increment=0.0,
                                                   amp=qm_dict['amp_signal'],
                                                   freq=qm_dict['freq_signal'],
                                                   phase=qm_dict['signal_phase'])
            tau_element = self._get_mw_element(length=tau_array[ii] - rabi_period / 2,
                                               increment=0.0,
                                               amp=qm_dict['amp_signal'],
                                               freq=qm_dict['freq_signal'],
                                               phase=qm_dict['signal_phase'])
            block.append(pihalf_element)

            for nn in range(qm_dict['xy8N']):

                if randomize:
                    random_phase = random.uniform(0, 360)
                else:
                    random_phase = 0

                # get pi elements
                if qm_dict['signal_during_mw']:
                    # get pi elements
                    pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                                increment=0,
                                                                amps=[mw_amp, qm_dict['amp_signal']],
                                                                freqs=[mw_freq, qm_dict['freq_signal']],
                                                                phases=[random_phase, qm_dict['signal_phase']])

                    piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                                increment=0,
                                                                amps=[mw_amp, qm_dict['amp_signal']],
                                                                freqs=[mw_freq, qm_dict['freq_signal']],
                                                                phases=[90.0 + random_phase,
                                                                        qm_dict['signal_phase']])
                else:
                    pix_element = self._get_mw_element(length=rabi_period / 2,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=random_phase)

                    piy_element = self._get_mw_element(length=rabi_period / 2,
                                                       increment=0.0,
                                                       amp=mw_amp,
                                                       freq=mw_freq,
                                                       phase=90.0 + random_phase)


                block.append(tauhalf_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tauhalf_element)
            if qm_dict['lasty']:
                block.append(piyhalf_element)
            else:
                block.append(pihalf_element)
            block.append(laser_element)
            # get current waiting element
            if qm_dict['signal_during_mw']:
                waiting_element = self._get_mw_element(waiting_length[ii],
                                                       increment=0.0,
                                                       amp=qm_dict['amp_signal'],
                                                       freq=qm_dict['freq_signal'],
                                                       phase=qm_dict['signal_phase'])
            else:
                waiting_element = self._get_idle_element(length=waiting_length[ii],
                                                         increment=0.0)

            block.append(waiting_element)
            # add alternating sequence
            if alternating:
                block.append(pihalf_element)
                for nn in range(qm_dict['xy8N']):
                    block.append(tauhalf_element)
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
                    block.append(tauhalf_element)

                if qm_dict['lasty']:
                    block.append(piy3half_element)
                else:
                    block.append(pi3half_element)
                block.append(laser_element)
                block.append(waiting_element)

        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating,
                                                        controlled_variable=tau_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences