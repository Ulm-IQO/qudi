import numpy as np
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from logic.pulsed.sampling_functions import SamplingFunctions


class PentaceneMethods(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    ############ pentacene methodes

    def generate_podmr_pentacene(self, name='podmr_pen', freq_start=1430.0e6, freq_step=2e6, wait_2_time=50e-6,
                            num_of_points=20, alternating_no_mw=False):
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
        waiting_afterMW_element = self._get_idle_element(length=wait_2_time,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        pulsedodmr_block = PulseBlock(name=name)

        for mw_freq in freq_array:
            pulsedodmr_block.append(waiting_element)

            mw_element = self._get_mw_element(length=self.rabi_period / 2,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=mw_freq,
                                              phase=0)
            pulsedodmr_block.append(mw_element)
            pulsedodmr_block.append(waiting_afterMW_element)
            pulsedodmr_block.append(laser_element)
            pulsedodmr_block.append(delay_element)
            if alternating_no_mw:
                pulsedodmr_block.append(waiting_element)
                no_mw_element = self._get_mw_element(length=self.rabi_period / 2,
                                                  increment=0,
                                                  amp=0,
                                                  freq=mw_freq/2.,
                                                  phase=0)
                pulsedodmr_block.append(no_mw_element)
                pulsedodmr_block.append(waiting_afterMW_element)
                pulsedodmr_block.append(laser_element)
                pulsedodmr_block.append(delay_element)
        created_blocks.append(pulsedodmr_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((pulsedodmr_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating_no_mw
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_fakecwodmr_pentacene(self, name='fake_cw_odmr_pen', freq_start=1430.0e6, freq_step=2e6, t_single=50e-6,
                                 num_of_points=20, alternating_no_mw=False):
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
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        pulsedodmr_block = PulseBlock(name=name)

        for mw_freq in freq_array:

            mw_element = self._get_mw_laser_element(length=t_single,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=mw_freq,
                                              phase=0)
            pulsedodmr_block.append(mw_element)
            pulsedodmr_block.append(delay_element)
            pulsedodmr_block.append(waiting_element)

            if alternating_no_mw:
                no_mw_element = self._get_mw_laser_element(length=t_single,
                                                     increment=0,
                                                     amp=0,
                                                     freq=mw_freq / 2.,
                                                     phase=0)
                pulsedodmr_block.append(no_mw_element)
                pulsedodmr_block.append(delay_element)
                pulsedodmr_block.append(waiting_element)

        created_blocks.append(pulsedodmr_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((pulsedodmr_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating_no_mw
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] =  2 * num_of_points if alternating_no_mw else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_rabi_pentacene(self, name='rabi_pen', tau_start=10.0e-9, tau_step=10.0e-9, num_of_points=50,
                                wait_2_time=50e-6, alternating_no_mw=False):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the laser_mw element
        mw_element = self._get_mw_element(length=tau_start,
                                          increment=tau_step,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0)
        noMw_element = self._get_mw_element(length=tau_start,
                                          increment=tau_step,
                                          amp=0,
                                          freq=self.microwave_frequency/2,
                                          phase=0)

        waiting_element = self._get_idle_element(length=self.wait_time,
                                                         increment=0)
        waiting_element_after_mw = self._get_idle_element(length=wait_2_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        rabi_block.append(waiting_element)
        rabi_block.append(mw_element)
        rabi_block.append(waiting_element_after_mw)
        rabi_block.append(laser_element)
        rabi_block.append(delay_element)
        if alternating_no_mw:
            rabi_block.append(waiting_element)
            rabi_block.append(noMw_element)
            rabi_block.append(waiting_element_after_mw)
            rabi_block.append(laser_element)
            rabi_block.append(delay_element)

        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((rabi_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating_no_mw
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2 * num_of_points if alternating_no_mw else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    ############# NV methods

    def generate_laser_strob(self, name='laser_strob', t_laser_read=3e-6,
                                  t_laser_init=10e-6, t_wait_between=0e-9, laser_read_ch='', add_gate_ch='',
                                  t_aom_safety=250e-9):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        laser_init_element = self._get_laser_gate_element(length=t_laser_init,
                                                          increment=0,
                                                          add_gate_ch='')
        # additional gate channel, independent on the one from pulsed gui
        laser_red_element = self._get_laser_gate_element(length=t_laser_read-t_aom_safety,
                                                         increment=0,
                                                         add_gate_ch=add_gate_ch)
        # close gap between aom init laser pulse and instant red pulse
        laser_red_balanceaom_element = self._get_laser_gate_element(length=t_aom_safety,
                                                                    increment=0,
                                                                    add_gate_ch=add_gate_ch)
        if laser_read_ch:
            laser_red_element.digital_high[self.laser_channel] = False
            laser_red_element.digital_high[laser_read_ch] = True
            if t_laser_init > t_aom_safety:
                laser_red_balanceaom_element.digital_high[self.laser_channel] = True
            else:
                laser_red_balanceaom_element.digital_high[self.laser_channel] = False
            laser_red_balanceaom_element.digital_high[laser_read_ch] = True


        idle_between_lasers_element = self._get_idle_element(length=t_wait_between,
                                                             increment=0)

        delay_element = self._get_delay_gate_element()
        safety_element = self._get_idle_element(length=t_aom_safety,
                                                increment=0)

        # Create block and append to created_blocks list
        strob_block = PulseBlock(name=name)
        strob_block.append(laser_red_element)
        strob_block.append(laser_red_balanceaom_element)
        strob_block.append(idle_between_lasers_element)
        strob_block.append(laser_init_element)
        # Is considerable fraction of time, not needed in confocal scanning as m_s state unchanged
        #strob_block.append(delay_element)
        # ~ aom delay, but more aggressive timing. Avoid overlapping of green (aom) and red (instant)
        strob_block.append(safety_element)


        created_blocks.append(strob_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((strob_block.name, 1 - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = [-1]
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 1
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_rabi_nv_red_read(self, name='rabi_red', tau_start=10.0e-9, tau_step=10.0e-9, num_of_points=50,
                                 t_laser_init=10e-6, t_wait_between=10e-9, laser_read_ch='', add_gate_ch=''):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the laser_mw element
        mw_element = self._get_mw_element(length=tau_start,
                                          increment=tau_step,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0)
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_red_element = self._get_laser_gate_element(length=self.laser_length,
                                                         increment=0,
                                                         add_gate_ch=add_gate_ch)
        if laser_read_ch:
            laser_red_element.digital_high[self.laser_channel] = False
            laser_red_element.digital_high[laser_read_ch] = True

        idle_between_lasers_element = self._get_idle_element(length=t_wait_between,
                                                             increment=0)
        laser_init_element = self._get_laser_gate_element(length=t_laser_init,
                                                          increment=0,
                                                          add_gate_ch='')
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        rabi_block.append(mw_element)
        rabi_block.append(laser_red_element)
        rabi_block.append(idle_between_lasers_element)
        rabi_block.append(laser_init_element)
        rabi_block.append(delay_element)
        rabi_block.append(waiting_element)
        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((rabi_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_hahn_nv_red_read(self, name='hahn_red', tau_start=10.0e-9, tau_step=10.0e-9, num_of_points=50,
                                 t_laser_init=10e-6, t_wait_between=10e-9, laser_read_ch='', add_gate_ch='',
                                  alternating=False):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                          increment=0,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0)
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)

        tau_element = self._get_idle_element(length=tau_start, increment=tau_step)
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_red_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        if laser_read_ch:
            laser_red_element.digital_high[self.laser_channel] = False
            laser_red_element.digital_high[laser_read_ch] = True

        # additional gate channel, independent on the one from pulsed gui
        if add_gate_ch:
            laser_red_element.digital_high[add_gate_ch] = True

        idle_between_lasers_element = self._get_idle_element(length=t_wait_between,
                                                 increment=0)
        laser_init_element = self._get_laser_gate_element(length=t_laser_init,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        hahn_block = PulseBlock(name=name)
        hahn_block.append(pihalf_element)
        hahn_block.append(tau_element)
        hahn_block.append(pi_element)
        hahn_block.append(tau_element)
        hahn_block.append(pihalf_element)
        hahn_block.append(laser_red_element)
        hahn_block.append(idle_between_lasers_element)
        hahn_block.append(laser_init_element)
        hahn_block.append(delay_element)
        hahn_block.append(waiting_element)

        if alternating:
            hahn_block.append(pihalf_element)
            hahn_block.append(tau_element)
            hahn_block.append(pi_element)
            hahn_block.append(tau_element)
            hahn_block.append(pi3half_element)
            hahn_block.append(laser_red_element)
            hahn_block.append(idle_between_lasers_element)
            hahn_block.append(laser_init_element)
            hahn_block.append(delay_element)
            hahn_block.append(waiting_element)

        created_blocks.append(hahn_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((hahn_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_xy8_tau_nv_red(self, name='xy8_tau_red', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                                xy8_order=4,
                                t_laser_init=10e-6, t_wait_between=10e-9, laser_read_ch='', add_gate_ch='',
                                alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        # calculate "real" start length of tau due to finite pi-pulse length
        real_start_tau = max(0, tau_start - self.rabi_period / 2)

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        laser_red_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)

        if laser_read_ch:
            laser_red_element.digital_high[self.laser_channel] = False
            laser_red_element.digital_high[laser_read_ch] = True

        # additional gate channel, independent on the one from pulsed gui
        if add_gate_ch:
            laser_red_element.digital_high[add_gate_ch] = True

        idle_between_lasers_element = self._get_idle_element(length=t_wait_between,
                                                 increment=0)
        laser_init_element = self._get_laser_gate_element(length=t_laser_init,
                                                     increment=0)

        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
        pix_element = self._get_mw_element(length=self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=0)
        piy_element = self._get_mw_element(length=self.rabi_period / 2,
                                           increment=0,
                                           amp=self.microwave_amplitude,
                                           freq=self.microwave_frequency,
                                           phase=90)
        tauhalf_element = self._get_idle_element(length=real_start_tau / 2, increment=tau_step / 2)
        tau_element = self._get_idle_element(length=real_start_tau, increment=tau_step)

        # Create block and append to created_blocks list
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
        xy8_block.append(pihalf_element)
        xy8_block.append(laser_red_element)
        xy8_block.append(idle_between_lasers_element)
        xy8_block.append(laser_init_element)
        xy8_block.append(delay_element)
        xy8_block.append(waiting_element)
        if alternating:
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
            xy8_block.append(pi3half_element)
            xy8_block.append(laser_red_element)
            xy8_block.append(idle_between_lasers_element)
            xy8_block.append(laser_init_element)
            xy8_block.append(delay_element)
            xy8_block.append(waiting_element)
        created_blocks.append(xy8_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((xy8_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_xy8_nsweep_nv_red(self, name='XY8_n_red', tau=1.0e-6, xy8_start=1, xy8_step=1,
                                   t_laser_init=10e-6, t_wait_between=10e-9, laser_read_ch='', add_gate_ch='',
                                num_of_points=50, alternating = True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get pulse number array for measurement ticks
        xy8_array = xy8_start + np.arange(num_of_points) * xy8_step
        xy8_array.astype(int)
        # change parameters in a way that they fit to the current sampling rate
        rabi_period = self._adjust_to_samplingrate(self.rabi_period, 4)
        tau = self._adjust_to_samplingrate(tau, 2)
        real_tau = max(0, tau - rabi_period / 2)

        # get readout element
        readout_element = self._get_readout_element()
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        delay_element = self._get_delay_gate_element()
        laser_red_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        if laser_read_ch:
            laser_red_element.digital_high[self.laser_channel] = False
            laser_red_element.digital_high[laser_read_ch] = True

        # additional gate channel, independent on the one from pulsed gui
        if add_gate_ch:
            laser_red_element.digital_high[add_gate_ch] = True

        idle_between_lasers_element = self._get_idle_element(length=t_wait_between,
                                                 increment=0)
        laser_init_element = self._get_laser_gate_element(length=t_laser_init,
                                                     increment=0)



        # get pihalf element
        pihalf_element = self._get_mw_element(length=rabi_period / 4,
                                              increment=0.0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0.0)

        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
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

        # get tau elements
        tau_element = self._get_idle_element(length=real_tau, increment=0)
        tauhalf_element = self._get_idle_element(length=real_tau / 2, increment=0)
        #self.log.warning(locals())



        # create XY8-N block element list
        xy8_block = PulseBlock(name=name)
        for ii in range(num_of_points):
            xy8_block.append(pihalf_element)
            xy8_block.append(tauhalf_element)
            xy8_order = xy8_array[ii]
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
            xy8_block.append(pihalf_element)
            xy8_block.append(laser_red_element)
            xy8_block.append(idle_between_lasers_element)
            xy8_block.append(laser_init_element)
            xy8_block.append(delay_element)
            xy8_block.append(waiting_element)
            if alternating:
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
                xy8_block.append(pi3half_element)
                xy8_block.append(laser_red_element)
                xy8_block.append(idle_between_lasers_element)
                xy8_block.append(laser_init_element)
                xy8_block.append(delay_element)
                xy8_block.append(waiting_element)

        created_blocks.append(xy8_block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((xy8_block.name, 0))

        # Create and append sync trigger block if needed
        created_blocks, block_ensemble = self._add_trigger(created_blocks, block_ensemble)
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks,
                                                        alternating=alternating,
                                                        controlled_variable= 8 * xy8_array * tau)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences





    def generate_t1_pentacene(self, name='T1_pen', tau_start=1.0e-6, tau_step=1.0e-6,
                    num_of_points=50, alternating=False, wait_2_time=50e-6):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        waiting_element_after_mw = self._get_idle_element(length=wait_2_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()
        if alternating:  # get pi element
            pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)

        tau_element = self._get_idle_element(length=tau_start, increment=tau_step)
        t1_block = PulseBlock(name=name)
        t1_block.append(tau_element)
        t1_block.append(waiting_element_after_mw)
        t1_block.append(laser_element)
        t1_block.append(delay_element)
        t1_block.append(waiting_element)
        if alternating:
            t1_block.append(pi_element)
            t1_block.append(tau_element)
            t1_block.append(waiting_element_after_mw)
            t1_block.append(laser_element)
            t1_block.append(delay_element)
            t1_block.append(waiting_element)
        created_blocks.append(t1_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((t1_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_laser_on_jump(self, name='laser_on_jump_off', length=10.0e-3, jump_channel='d_ch4'):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the laser element
        laser_element = self._get_laser_element(length=length, increment=0)

        # create the laser element with "jump" signal
        laser_element_jump = self._get_laser_element(length=length, increment=0)
        laser_element_jump.digital_high[jump_channel] = True

        waiting_element = self._get_idle_element(length=length/2.,
                                                increment=0)

        # Create block and append to created_blocks list
        laser_block = PulseBlock(name=name)
        laser_block.append(waiting_element)
        laser_block.append(laser_element)
        laser_block.append(laser_element_jump)
        laser_block.append(laser_element)
        laser_block.append(waiting_element)

        created_blocks.append(laser_block)

        # Create block ensemble and append to created_ensembles list
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((laser_block.name, 0))


        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        number_of_lasers = 1
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = [0]
        block_ensemble.measurement_information['units'] = ('a.u.', '')
        block_ensemble.measurement_information['labels'] = ('data point', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    def generate_pol_ise_pentacene(self, name='pol_pen', t_laser=1e-6, t_mw_ramp=100e-9, f_mw_sweep=10e6,
                                   jump_channel='d_ch4'):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the laser element
        """
        laser_element = self._get_laser_element(length=t_laser, increment=0)

        # create the laser element with "jump" signal
        laser_element_jump = self._get_laser_element(length=t_laser, increment=0)
        laser_element_jump.digital_high[jump_channel] = True
        """
        # create n mw chirps
        n_mw_chirps = int(t_laser/t_mw_ramp)
        if t_laser % t_mw_ramp != 0.:
            self.log.warning("Laser not dividable by t_mw. Extending to: {} us".
                             format(n_mw_chirps*t_mw_ramp))
        mw_freq_center = self.microwave_frequency
        freq_range = f_mw_sweep
        mw_freq_start = mw_freq_center - freq_range / 2.
        mw_freq_end = mw_freq_center + freq_range / 2

        mw_sweep_element = self.self._get_mw_element_linearchirp(length=t_mw_ramp,
                                                          increment=0,
                                                          amplitude=self.microwave_amplitude,
                                                          start_freq=mw_freq_start,
                                                          stop_freq=mw_freq_end,
                                                          phase=0)
        mw_sweep_element.digital_high[self.laser_channel] = True
        mw_sweep_element.digital_high[jump_channel] = True

        # Create block and append to created_blocks list
        laser_block = PulseBlock(name=name)
        #laser_block.append(laser_element_jump)
        for i in range(n_mw_chirps):
            laser_block.append(mw_sweep_element)

        created_blocks.append(laser_block)

        # Create block ensemble and append to created_ensembles list
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((laser_block.name, 0))


        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        number_of_lasers = 1
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = [0]
        block_ensemble.measurement_information['units'] = ('a.u.', '')
        block_ensemble.measurement_information['labels'] = ('data point', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_deer_ramsey(self, name='deer_ramsey', f_mw_penta=1.4e9, t_rabi_penta=100e-9,
                             tau_start=1.0e-6, tau_step=1.0e-6, num_of_points=50, alternating_mode='pentacene_pi_off'):


        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = (tau_start + np.arange(num_of_points) * tau_step) + t_rabi_penta / 2

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        pi_pentacene_element = self._get_mw_element(length=t_rabi_penta / 2,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=f_mw_penta,
                                              phase=0)
        idle_pentacene_element = self._get_idle_element(length=t_rabi_penta / 2,
                                                        increment=0)

        # Use a 180 deg phase shiftet pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)
        tau_element = self._get_idle_element(length=tau_start, increment=tau_step)

        # Create block and append to created_blocks list
        ramsey_block = PulseBlock(name=name)
        ramsey_block.append(pihalf_element)
        ramsey_block.append(pi_pentacene_element)
        ramsey_block.append(tau_element)
        ramsey_block.append(pihalf_element)
        ramsey_block.append(laser_element)
        ramsey_block.append(delay_element)
        ramsey_block.append(waiting_element)

        alternating = False
        if alternating_mode == 'nv_pi_3_2':
            ramsey_block.append(pihalf_element)
            ramsey_block.append(tau_element)
            ramsey_block.append(pi3half_element)
            ramsey_block.append(laser_element)
            ramsey_block.append(delay_element)
            ramsey_block.append(waiting_element)
            alternating = True
        elif alternating_mode == 'pentacene_pi_off':
            ramsey_block.append(pihalf_element)
            ramsey_block.append(tau_element)
            ramsey_block.append(idle_pentacene_element)
            ramsey_block.append(pihalf_element)
            ramsey_block.append(laser_element)
            ramsey_block.append(delay_element)
            ramsey_block.append(waiting_element)
            alternating = True

        created_blocks.append(ramsey_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((ramsey_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_DEER(self, name='DEER', tau_start=1e-6, tau_step=1e-6, num_of_points=50,
                      hahn_echo_tau=50e-6, second_rabi_period=20e-9,
                      second_mw_amplitude=0.0, second_mw_frequency=2.87e9, two_deer_pi=True, alternating=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks.
        # Calculate boundaries for second pi_pulse length to avoid pulse overlap.
        min_tau = self.rabi_period / 8 + second_rabi_period / 4
        max_tau = hahn_echo_tau - self.rabi_period / 4 - second_rabi_period / 4
        if tau_start < min_tau:
            tau_start = min_tau
        # Reduce number of points to stay within tau boundaries
        while (tau_start + (num_of_points-1) * tau_step - max_tau) > 0:
            num_of_points -= 1
        if num_of_points < 1:
            raise Exception('Number of points for DEER measurement is smaller than 1. This can '
                            'happen if you entered a wrong number or if the hahn_echo_tau interval '
                            'is too small to fit tau_step witout overlapping pulses.')
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                          increment=0,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0)
        second_pi_element = self._get_mw_element(length=second_rabi_period / 2,
                                                 increment=0,
                                                 amp=second_mw_amplitude,
                                                 freq=second_mw_frequency,
                                                 phase=0)
        # Use a 180 deg phase shifted pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=180)
        else:
            pi3half_element = self._get_mw_element(length=3 * self.rabi_period / 4,
                                                   increment=0,
                                                   amp=self.microwave_amplitude,
                                                   freq=self.microwave_frequency,
                                                   phase=0)

        # Hahn echo tau compensated for finite pulse length
        real_hahn_tau = hahn_echo_tau - self.rabi_period / 8 - self.rabi_period / 4
        real_tau_start = tau_start - self.rabi_period / 8 - second_rabi_period / 4
        real_remainder_start = real_hahn_tau - real_tau_start - self.rabi_period / 4 - second_rabi_period / 4

        # total mw free times in first and second half of hahn echo
        if two_deer_pi:
            real_hahn_tau_1 = real_hahn_tau - second_rabi_period / 2
            mw_first_free_1 = real_hahn_tau_1 + second_rabi_period / 2
        else:
            real_hahn_tau_1 = real_hahn_tau
            mw_first_free_1 = real_hahn_tau_1

        real_hahn_tau_2 = real_tau_start + real_remainder_start
        mw_first_free_2 = real_hahn_tau_2 + second_rabi_period / 2

        self.log.debug(f"MW-free free evolution: real tau_1: {real_hahn_tau_1}"
                       f" real tau_2: {real_hahn_tau_2} "
                       f"1st-electron-MW-free free evolution: real tau_1: {mw_first_free_1} "
                       f"real tau_2: {mw_first_free_2}")

        while (real_remainder_start - (num_of_points-1) * tau_step) < 0:
            num_of_points -= 1
            if num_of_points < 1:
                raise Exception('Number of points for DEER measurement is smaller than 1. This can '
                                'happen if you entered a wrong number or if the hahn_echo_tau '
                                'interval is too small to fit tau_step witout overlapping pulses.')
            tau_array = tau_array[:-1]

        hahn_tau_element = self._get_idle_element(length=real_hahn_tau, increment=0)
        if two_deer_pi:
            hahn_tau_element = self._get_idle_element(length=real_hahn_tau_1, increment=0)

        hahn_remainder_element = self._get_idle_element(length=real_remainder_start, increment=-tau_step)
        tau_element = self._get_idle_element(length=real_tau_start, increment=tau_step)

        # Create block and append to created_blocks list
        hahn_block = PulseBlock(name=name)
        hahn_block.append(pihalf_element)
        if two_deer_pi:
            hahn_block.append(second_pi_element)
            hahn_block.append(hahn_tau_element)
        else:
            hahn_block.append(hahn_tau_element)
        hahn_block.append(pi_element)

        hahn_block.append(hahn_remainder_element)
        hahn_block.append(second_pi_element)
        hahn_block.append(tau_element)

        hahn_block.append(pihalf_element)
        hahn_block.append(laser_element)
        hahn_block.append(delay_element)
        hahn_block.append(waiting_element)
        if alternating:
            hahn_block.append(pihalf_element)
            if two_deer_pi:
                hahn_block.append(second_pi_element)
                hahn_block.append(hahn_tau_element)
            else:
                hahn_block.append(hahn_tau_element)
            hahn_block.append(pi_element)

            hahn_block.append(hahn_remainder_element)
            hahn_block.append(second_pi_element)
            hahn_block.append(tau_element)

            hahn_block.append(pi3half_element)
            hahn_block.append(laser_element)
            hahn_block.append(delay_element)
            hahn_block.append(waiting_element)
        created_blocks.append(hahn_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((hahn_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_deer_spectrum(self, name='DEERspect', freq_start=2870.0e6, freq_step=0.2e6, deer_amp=0.001, pi_len=20.0e-9,
                           tau = 200.0e-9, num_of_points=50, two_deer_pi=False, alternating=False):
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

        # Create block and append to created_blocks list
        pulsedodmr_block = PulseBlock(name=name)
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                          increment=0,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0)
        pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=180)
        pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        tau1_element = self._get_idle_element(length=tau,
                                                 increment=0)
        tau2_element = self._get_idle_element(length=tau-pi_len,
                                             increment=0)

        for mw_freq in freq_array:

            mw_element = self._get_mw_element(length=pi_len,
                                              increment=0,
                                              amp=deer_amp,
                                              freq=mw_freq,
                                              phase=0)
            pulsedodmr_block.append(pihalf_element)
            if two_deer_pi:
                pulsedodmr_block.append(mw_element)
            pulsedodmr_block.append(tau1_element)
            pulsedodmr_block.append(pi_element)
            pulsedodmr_block.append(mw_element)
            pulsedodmr_block.append(tau2_element)
            pulsedodmr_block.append(pihalf_element)
            pulsedodmr_block.append(laser_element)
            pulsedodmr_block.append(waiting_element)

            if alternating:
                pulsedodmr_block.append(pihalf_element)
                if two_deer_pi:
                    pulsedodmr_block.append(mw_element)
                pulsedodmr_block.append(tau1_element)
                pulsedodmr_block.append(pi_element)
                pulsedodmr_block.append(mw_element)
                pulsedodmr_block.append(tau2_element)
                pulsedodmr_block.append(pi3half_element)
                pulsedodmr_block.append(laser_element)
                pulsedodmr_block.append(waiting_element)

        created_blocks.append(pulsedodmr_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((pulsedodmr_block.name, 0))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))

        # add metadata to invoke settings later on
        number_of_lasers = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_deer_rabi(self, name='DEERrabi', tau_fixed=200.0e-9, deer_freq=2870.0e6, deer_amp=0.001,
                          tau_start=2.0e-9, tau_step=2.0e-9, num_of_taus=50, two_deer_pi=False, alternating=False):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # Create frequency array
        tau_array = tau_start + np.arange(num_of_taus) * tau_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        deerrabi_block = PulseBlock(name=name)
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=0)
        pi3half_element = self._get_mw_element(length=self.rabi_period / 4,
                                               increment=0,
                                               amp=self.microwave_amplitude,
                                               freq=self.microwave_frequency,
                                               phase=180)
        tau1_element = self._get_idle_element(length=tau_fixed,
                                              increment=0)
        tau2_element = self._get_idle_element(length=tau_fixed - tau_start,
                                              increment=-tau_step)

        pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                          increment=0,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=0)
        mw_element = self._get_mw_element(length=tau_start,
                                          increment=tau_step,
                                          amp=deer_amp,
                                          freq=deer_freq,
                                          phase=0)

        deerrabi_block.append(pihalf_element)
        if two_deer_pi:
            deerrabi_block.append(mw_element)
            deerrabi_block.append(tau2_element)
        else:
            deerrabi_block.append(tau1_element)
        deerrabi_block.append(pi_element)

        deerrabi_block.append(mw_element)
        deerrabi_block.append(tau2_element)
        deerrabi_block.append(pihalf_element)

        deerrabi_block.append(laser_element)
        deerrabi_block.append(waiting_element)
        if alternating:
            deerrabi_block.append(pihalf_element)
            if two_deer_pi:
                deerrabi_block.append(mw_element)
            deerrabi_block.append(tau1_element)
            deerrabi_block.append(pi_element)
            deerrabi_block.append(mw_element)
            deerrabi_block.append(tau2_element)
            deerrabi_block.append(pi3half_element)
            deerrabi_block.append(laser_element)
            deerrabi_block.append(waiting_element)
        created_blocks.append(deerrabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((deerrabi_block.name, num_of_taus - 1))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))

        # add metadata to invoke settings later on
        number_of_lasers = 2 * num_of_taus if alternating else num_of_taus
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences