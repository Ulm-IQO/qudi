import numpy as np
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase



class T4PredefinedGeneratorS3(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_xy8_signal(self, qm_dict='None'):
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

            # get pi elements
            pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[mw_amp, qm_dict['amp_signal']],
                                                        freqs=[mw_freq, qm_dict['freq_signal']],
                                                        phases=[0.0, qm_dict['signal_phase']])

            piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[mw_amp, qm_dict['amp_signal']],
                                                        freqs=[mw_freq, qm_dict['freq_signal']],
                                                        phases=[90.0, qm_dict['signal_phase']])

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
            # get pi elements
            pix_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=mw_amp,
                                               freq=mw_freq,
                                               phase=0.0)

            piy_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=mw_amp,
                                               freq=mw_freq,
                                               phase=90.0)

        block = PulseBlock(name=name)
        for ii in range(num_of_points):
            # get pure interaction elements
            tauhalf_element = self._get_mw_element(length=tau_array[ii]/2.0 - rabi_period/4,
                                                   increment=0.0,
                                                   amp=qm_dict['amp_signal'],
                                                   freq=qm_dict['freq_signal'],
                                                   phase=qm_dict['signal_phase'])
            tau_element = self._get_mw_element(length=tau_array[ii]- rabi_period / 2,
                                                   increment=0.0,
                                                   amp=qm_dict['amp_signal'],
                                                   freq=qm_dict['freq_signal'],
                                                   phase=qm_dict['signal_phase'])
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


    def generate_xy8_Nsweep_signal(self, qm_dict='None'):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        # get pulse number array for measurement ticks
        xy8N_array = qm_dict['start_xy8N'] + np.arange(num_of_points) * qm_dict['incr_xy8N']
        xy8N_array.astype(int)

        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(qm_dict['rabi_period'], 4)
        tau = self._adjust_to_samplingrate(tau, 2)


        # the idea is to increment the waiting time in a way that the phase of a continous signal would be the same phase
        # for every block
        period = 1.0/qm_dict['freq_signal']
        waiting_length = np.zeros(num_of_points)
        for kk in range(num_of_points):
            length_of_block = qm_dict['laser_length'] + 8 * xy8N_array[kk] * (tau) + rabi_period /2.0
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

            # get pi elements
            pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[mw_amp, qm_dict['amp_signal']],
                                                        freqs=[mw_freq, qm_dict['freq_signal']],
                                                        phases=[0.0, qm_dict['signal_phase']])

            piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[mw_amp, qm_dict['amp_signal']],
                                                        freqs=[mw_freq, qm_dict['freq_signal']],
                                                        phases=[90.0, qm_dict['signal_phase']])

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
            # get pi elements
            pix_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=mw_amp,
                                               freq=mw_freq,
                                               phase=0.0)

            piy_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=mw_amp,
                                               freq=mw_freq,
                                               phase=90.0)

        # get pure interaction elements
        tauhalf_element = self._get_mw_element(length=tau / 2.0 - rabi_period / 4,
                                               increment=0.0,
                                               amp=qm_dict['amp_signal'],
                                               freq=qm_dict['freq_signal'],
                                               phase=qm_dict['signal_phase'])

        tau_element = self._get_mw_element(length=tau - rabi_period / 2,
                                           increment=0.0,
                                           amp=qm_dict['amp_signal'],
                                           freq=qm_dict['freq_signal'],
                                           phase=qm_dict['signal_phase'])

        block = PulseBlock(name=name)
        for ii in range(num_of_points):
            block.append(pihalf_element)

            for nn in range(xy8N_array[ii]):
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
                waiting_element = self._get_mw_element(length=waiting_length[ii],
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
                for nn in range(xy8N_array[ii]):
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
                                                        controlled_variable=xy8N_array * 8 * tau)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences





    def generate_xy8_PhiSweep(self, qm_dict='None'):
        """

        """
        # get Phase array
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        phi_array = qm_dict['start_phi'] + np.arange(num_of_points) * qm_dict['incr_phi']

        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(qm_dict['rabi_period'], 4)
        tau = self._adjust_to_samplingrate(tau, 2)

        # the idea is to increment the waiting time in a way that the phase of a continous signal would be the expected phase
        # for every block
        period = 1.0/qm_dict['freq_signal']
        length_of_sequence = qm_dict['laser_length'] + 8 * (qm_dict['xy8N']) * (tau) + rabi_period /2.0
        remainder = np.around(length_of_sequence % period, decimals=12)
        waiting_length = np.around((period - remainder) + qm_dict['incr_phi'] / 360 * period, decimals=12)
        while waiting_length < 1e-6:
            waiting_length = waiting_length + period

        if alternating:
            ## if alternating the waiting length should be just one perid
            waiting_length_alt = np.around((period - remainder), decimals=12)
            while waiting_length_alt < 1e-6:
                waiting_length_alt = waiting_length_alt + period


        # create XY8_signal block element list
        if qm_dict['signal_during_mw']:
            # get laser, delay and waiting element
            laser_element = self._get_mw_laser_element(length=qm_dict['laser_length'],
                                                       increment=0.0,
                                                       amp=qm_dict['amp_signal'],
                                                       freq=qm_dict['freq_signal'],
                                                       phase=qm_dict['signal_phase'])

            waiting_element = self._get_mw_element(length=waiting_length,
                                                  increment=0.0,
                                                  amp=qm_dict['amp_signal'],
                                                  freq=qm_dict['freq_signal'],
                                                  phase=qm_dict['start_phi'])
            # get pihalf element
            pihalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                           increment=0,
                                                           amps=[mw_amp, qm_dict['amp_signal']],
                                                           freqs=[mw_freq, qm_dict['freq_signal']],
                                                           phases=[0.0, qm_dict['start_phi']])
            if qm_dict['lasty']:
                pihalf_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                               increment=0,
                                                               amps=[mw_amp, qm_dict['amp_signal']],
                                                               freqs=[mw_freq, qm_dict['freq_signal']],
                                                               phases=[90.0, qm_dict['start_phi']])
            if alternating:
                pi3half_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                               increment=0,
                                                               amps=[mw_amp, qm_dict['amp_signal']],
                                                               freqs=[mw_freq, qm_dict['freq_signal']],
                                                               phases=[180.0, qm_dict['start_phi']])
                waiting_element_alt = self._get_mw_element(length=waiting_length_alt,
                                                       increment=0.0,
                                                       amp=qm_dict['amp_signal'],
                                                       freq=qm_dict['freq_signal'],
                                                       phase=qm_dict['start_phi'])
                if qm_dict['lasty']:
                    piy3half_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                   increment=0,
                                                                   amps=[mw_amp, qm_dict['amp_signal']],
                                                                   freqs=[mw_freq, qm_dict['freq_signal']],
                                                                   phases=[270.0, qm_dict['start_phi']])
            # get pi elements
            pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[mw_amp, qm_dict['amp_signal']],
                                                        freqs=[mw_freq, qm_dict['freq_signal']],
                                                        phases=[0.0, qm_dict['start_phi']])
            piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[mw_amp, qm_dict['amp_signal']],
                                                        freqs=[mw_freq, qm_dict['freq_signal']],
                                                        phases=[90.0, qm_dict['start_phi']])

        else:
            # get waiting element
            waiting_element = self._get_idle_element(length = waiting_length,
                                                     increment = 0.0)
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
            # get pi elements
            pix_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=mw_amp,
                                               freq=mw_freq,
                                               phase=0.0)

            piy_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=mw_amp,
                                               freq=mw_freq,
                                               phase=90.0)

        # get pure interaction elements
        tauhalf_element = self._get_mw_element_s3(tau/2.0-rabi_period/4, 0, qm_dict['mw_channel'], qm_dict['amp_signal'],
                                                  qm_dict['freq_signal'], qm_dict['start_phi'])
        tau_element = self._get_mw_element_s3(tau-rabi_period/2, 0, qm_dict['mw_channel'], qm_dict['amp_signal'],
                                                  qm_dict['freq_signal'], qm_dict['start_phi'])

        block = PulseBlock(name=name)
        for ii in range(num_of_points):
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
                block.append(piyhalf_element)
            else:
                block.append(pihalf_element)
            block.append(laser_element)
            if alternating:
                block.append(waiting_element_alt)
            else:
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
                                                        controlled_variable=phi_array)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    ############################################# XY8-4 methods #####################################################



    def generate_xy4_Nsweep_signal(self, qm_dict='None'):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        # get pulse number array for measurement ticks
        xy4N_array = qm_dict['start_xy4N'] + np.arange(num_of_points) * qm_dict['incr_xy4N']
        xy4N_array.astype(int)

        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(qm_dict['rabi_period'], 4)
        tau = self._adjust_to_samplingrate(tau, 2)


        # the idea is to increment the waiting time in a way that the phase of a continous signal would be the same phase
        # for every block
        period = 1.0/qm_dict['freq_signal']
        waiting_length = np.zeros(num_of_points)
        for kk in range(num_of_points):
            length_of_block = qm_dict['laser_length'] + 4 * xy4N_array[kk] * (tau) + rabi_period /2.0
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
            pihalf_element = self._get_multiple_mw_element(length = rabi_period / 4,
                                                              increment = 0,
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

            # get pi elements
            pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[mw_amp, qm_dict['amp_signal']],
                                                        freqs=[mw_freq, qm_dict['freq_signal']],
                                                        phases=[0.0, qm_dict['signal_phase']])

            piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                        increment=0,
                                                        amps=[mw_amp, qm_dict['amp_signal']],
                                                        freqs=[mw_freq, qm_dict['freq_signal']],
                                                        phases=[90.0, qm_dict['signal_phase']])

        else:
            # get laser and delay element
            laser_element = self._get_laser_gate_element(length=self.laser_length,
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
            # get pi elements
            pix_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=mw_amp,
                                               freq=mw_freq,
                                               phase=0.0)

            piy_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=mw_amp,
                                               freq=mw_freq,
                                               phase=90.0)

        # get pure interaction elements
        tauhalf_element = self._get_mw_element(length=tau / 2.0 - rabi_period / 4,
                                               increment=0.0,
                                               amp=qm_dict['amp_signal'],
                                               freq=qm_dict['freq_signal'],
                                               phase=qm_dict['signal_phase'])

        tau_element = self._get_mw_element(length=tau - rabi_period / 2,
                                           increment=0.0,
                                           amp=qm_dict['amp_signal'],
                                           freq=qm_dict['freq_signal'],
                                           phase=qm_dict['signal_phase'])

        block = PulseBlock(name=name)
        for ii in range(num_of_points):
            block.append(pihalf_element)

            for nn in range(xy4N_array[ii]):
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
                waiting_element = self._get_mw_element(length=waiting_length[ii],
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
                for nn in range(xy4N_array[ii]):
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
                                                        controlled_variable=xy4N_array * 4 * tau)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences




    def generate_xy4_Nsweep_signal_adapted_readout_s3(self, qm_dict='None'):
        """

        """

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get pulse number array for measurement ticks
        xy4N_array = qm_dict['start_xy4N'] + np.arange(num_of_points) * qm_dict['incr_xy4N']
        xy4N_array.astype(int)

        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(qm_dict['rabi_period'], 4)
        tau = self._adjust_to_samplingrate(tau, 2)

        # compute the readout_axes:
        detuning = (qm_dict['freq_signal'] - 1/2/tau) * 2 * np.pi
        phases = 2 * qm_dict['signal_ampl_Hz'] * (1-np.cos(detuning*tau*4*xy4N_array))/detuning /2/np.pi * 360

        # the idea is to increment the waiting time in a way that the phase of a continous signal would be the same phase
        # for every block
        period = 1.0/qm_dict['freq_signal']
        waiting_length = np.zeros(num_of_points)
        for kk in range(num_of_points):
            length_of_block = qm_dict['laser_length'] + 4 * xy4N_array[kk] * (tau) + rabi_period /2.0
            remainder = np.around(length_of_block % period, decimals=12)
            waiting_length[kk] = np.around((period - remainder), decimals=12)
            while waiting_length[kk] < 1e-6:
                waiting_length[kk] = waiting_length[kk] + period



        # create XY8_signal block element list

        if qm_dict['signal_during_mw']:
            # get laser, delay and waiting element
            laser_element = self._get_mw_laser_element(length=self.laser_length,
                                                       increment=0.0,
                                                       amp=qm_dict['amp_signal'],
                                                       freq=qm_dict['freq_signal'],
                                                       phase=qm_dict['signal_phase'])


            # get pihalf element
            pihalf_element = self._get_multiple_mw_element(length = rabi_period / 4,
                                                              increment = 0,
                                                              amps=[mw_amp, qm_dict['amp_signal']],
                                                              freqs=[mw_freq, qm_dict['freq_signal']],
                                                              phases=[0.0, qm_dict['signal_phase']])

            pix_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                              increment=0,
                                                              amps=[mw_amp, qm_dict['amp_signal']],
                                                              freqs=[mw_freq, qm_dict['freq_signal']],
                                                              phases=[0.0, qm_dict['signal_phase']])

            piy_element = self._get_multiple_mw_element(length=rabi_period / 2,
                                                           increment=0,
                                                           amps=[mw_amp, qm_dict['amp_signal']],
                                                           freqs=[mw_freq, qm_dict['freq_signal']],
                                                           phases=[90.0, qm_dict['signal_phase']])

        else:
            # get laser and delay element
            laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                         increment=0)
            # get pihalf element
            pihalf_element = self._get_mw_element(length = rabi_period / 4,
                                                     increment = 0.0,
                                                     amp = mw_amp,
                                                     freq= mw_freq,
                                                     phase = 0.0)
            # get pi elements
            pix_element = self._get_mw_element(length=rabi_period / 2,
                                                     increment=0.0,
                                                     amp=mw_amp,
                                                     freq=mw_freq,
                                                     phase=0.0)

            piy_element = self._get_mw_element(length=rabi_period / 2,
                                               increment=0.0,
                                               amp=mw_amp,
                                               freq=mw_freq,
                                               phase=90.0)

        # get pure interaction elements
        tauhalf_element = self._get_mw_element(length=tau/2.0-rabi_period/4,
                                               increment=0.0,
                                               amp=qm_dict['amp_signal'],
                                               freq=qm_dict['freq_signal'],
                                               phase=qm_dict['signal_phase'])

        tau_element = self._get_mw_element(length=tau - rabi_period / 2,
                                               increment=0.0,
                                               amp=qm_dict['amp_signal'],
                                               freq=qm_dict['freq_signal'],
                                               phase=qm_dict['signal_phase'])


        block = PulseBlock(name=name)
        for ii in range(num_of_points):
            block.append(pihalf_element)
            for nn in range(xy4N_array[ii]):
                block.append(tauhalf_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tau_element)
                block.append(pix_element)
                block.append(tau_element)
                block.append(piy_element)
                block.append(tauhalf_element)

            if qm_dict['signal_during_mw']:

                pi_readout_half_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                        increment=0,
                                                                        amps=[mw_amp, qm_dict['amp_signal']],
                                                                        freqs=[mw_freq, qm_dict['freq_signal']],
                                                                        phases=[phases[ii], qm_dict['signal_phase']])

            else:
                pi_readout_half_element = self._get_mw_element(length=rabi_period / 4,
                                                               increment=0.0,
                                                               amp=mw_amp,
                                                               freq=mw_freq,
                                                               phase=phases[ii])

            block.append(pi_readout_half_element)
            block.append(laser_element)
            # get current waiting element
            if qm_dict['signal_during_mw']:
                waiting_element = self._get_mw_element(length=waiting_length[ii],
                                                       increment=0.0,
                                                       amp=qm_dict['amp_signal'],
                                                       freq=qm_dict['freq_signal'],
                                                       phase=qm_dict['signal_phase'])
            else:
                waiting_element = self._get_idle_element(length = waiting_length[ii],
                                                         increment = 0.0)

            block.append(waiting_element)
            # add alternating sequence
            if alternating:
                block.append(pihalf_element)
                for nn in range(xy4N_array[ii]):
                    block.append(tauhalf_element)
                    block.append(pix_element)
                    block.append(tau_element)
                    block.append(piy_element)
                    block.append(tau_element)
                    block.append(pix_element)
                    block.append(tau_element)
                    block.append(piy_element)
                    block.append(tauhalf_element)

                if qm_dict['signal_during_mw']:

                    pi_readout_half_element = self._get_multiple_mw_element(length=rabi_period / 4,
                                                                            increment=0,
                                                                            amps=[mw_amp, qm_dict['amp_signal']],
                                                                            freqs=[mw_freq, qm_dict['freq_signal']],
                                                                            phases=[phases[ii]+180, qm_dict['signal_phase']])

                else:
                    pi_readout_half_element = self._get_mw_element(length=rabi_period / 4,
                                                                   increment=0.0,
                                                                   amp=mw_amp,
                                                                   freq=mw_freq,
                                                                   phase=phases[ii]+180)
                block.append(pi_readout_half_element)
                block.append(laser_element)
                block.append(waiting_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=alternating,
                                                        controlled_variable=xy4N_array * 4 * tau)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

