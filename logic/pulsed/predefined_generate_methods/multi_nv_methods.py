import numpy as np
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from logic.pulsed.sampling_functions import SamplingFunctions, DDMethods

from enum import Enum

class DQTAltModes(Enum):
    DQT_12_alternating = 1
    DQT_both = 2

class MultiNV_Generator(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_ent_create_bell(self, name='ent_create_bell', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                             f_mw_2=1e9, ampl_mw_2=0.125, rabi_period_mw_2=100e-9,
                             dd_type=DDMethods.SE, dd_order=1, alternating=True):
        """
        Decoupling sequence on both NVs. Initialization with Hadarmard instead of pi2.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        rabi_periods = np.asarray([self.rabi_period, rabi_period_mw_2])
        amplitudes =  np.asarray([self.microwave_amplitude, ampl_mw_2])
        mw_freqs =  np.asarray([self.microwave_frequency, f_mw_2])

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        # calculate "real" start length of tau due to finite pi-pulse length
        real_start_tau = max(0, tau_start - self.rabi_period / 2)
        start_tau_pspacing = self.tau_2_pulse_spacing(tau_start)
        # self.log.debug("So far tau_start: {}, new: {}".format(real_start_tau, start_tau_pspacing))

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_both_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods/4,
                                              increments=[0,0],
                                              amps=amplitudes,
                                              freqs=mw_freqs,
                                              phases=[0,0])
        pi_both_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods/2,
                                              increments=[0,0],
                                              amps=amplitudes,
                                              freqs=mw_freqs,
                                              phases=[0,0])
        pihalf_y_both_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods/4,
                                              increments=[0,0],
                                              amps=amplitudes,
                                              freqs=mw_freqs,
                                              phases=[90,90])

        # define a function to create phase shifted pi pulse elements
        def pi_element_function(xphase):
            return self._get_multiple_mw_mult_length_element(lengths=rabi_periods/2,
                                              increments=[0,0],
                                              amps=amplitudes,
                                              freqs=mw_freqs,
                                              phases=[xphase,xphase])


        # Use a 180 deg phase shifted pulse as 3pihalf pulse if microwave channel is analog
        if self.microwave_channel.startswith('a'):
            pi3half_both_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods/4,
                                              increments=[0,0],
                                              amps=amplitudes,
                                              freqs=mw_freqs,
                                              phases=[180,180])
            pi3half_y_both_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods/4,
                                              increments=[0,0],
                                              amps=amplitudes,
                                              freqs=mw_freqs,
                                              phases=[90+180,90+180])
        else:
            raise ValueError("Can't create Hadarmard gate with digital pulse generator")

        tauhalf_element = self._get_idle_element(length=start_tau_pspacing / 2, increment=tau_step / 2)
        tau_element = self._get_idle_element(length=start_tau_pspacing, increment=tau_step)

        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)
        # Hadarmard = 180_X*90_Y*|Psi>
        dd_block.extend(pihalf_y_both_element)
        dd_block.extend(pi_both_element)
        for n in range(dd_order):
            # create the DD sequence for a single order
            for pulse_number in range(dd_type.suborder):
                dd_block.append(tauhalf_element)
                dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                dd_block.append(tauhalf_element)
        dd_block.extend(pi_both_element)
        dd_block.extend(pihalf_y_both_element)


        dd_block.append(laser_element)
        dd_block.append(delay_element)
        dd_block.append(waiting_element)
        if alternating:
            dd_block.extend(pihalf_y_both_element)
            dd_block.extend(pi_both_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element)
                    dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                    dd_block.append(tauhalf_element)
            dd_block.extend(pi_both_element)
            dd_block.extend(pi3half_y_both_element)

            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)
        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, num_of_points - 1))

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

    def generate_rabi_dqt_p(self, name='rabi_dqt-p', tau_start=10.0e-9, tau_step=10.0e-9,
                      num_of_points=50, f_mw_2=1e9, ampl_mw_2=0.125, alternating_mode=DQTAltModes.DQT_12_alternating):
        """
        Double quantum transition, driven in parallel (instead of sequential)
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        alternating = True if alternating_mode == DQTAltModes.DQT_12_alternating else False
        amplitudes_both = np.asarray([self.microwave_amplitude, ampl_mw_2])
        amplitudes_1 = np.asarray([self.microwave_amplitude, 0])
        amplitudes_2 = np.asarray([0, ampl_mw_2])
        mw_freqs = np.asarray([self.microwave_frequency, f_mw_2])

        tau_array = tau_start + np.arange(num_of_points) * tau_step
        num_of_points = len(tau_array)

        if alternating_mode == DQTAltModes.DQT_both:
            mw_element = self._get_multiple_mw_element(length=tau_start,
                                              increment=tau_step,
                                              amps=amplitudes_both,
                                              freqs=mw_freqs,
                                              phases=[0,0])
            mw_alt_element = None
        elif alternating_mode == DQTAltModes.DQT_12_alternating:
            mw_element = self._get_multiple_mw_element(length=tau_start,
                                                       increment=tau_step,
                                                       amps=amplitudes_1,
                                                       freqs=mw_freqs,
                                                       phases=[0, 0])
            mw_alt_element = self._get_multiple_mw_element(length=tau_start,
                                              increment=tau_step,
                                              amps=amplitudes_2,
                                              freqs=mw_freqs,
                                              phases=[0,0])
        else:
            raise ValueError(f"Unknown DQT mode: {alternating_mode}")

        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        rabi_block.append(mw_element)
        rabi_block.append(laser_element)
        rabi_block.append(delay_element)
        rabi_block.append(waiting_element)

        if alternating:
            rabi_block.append(mw_alt_element)
            rabi_block.append(laser_element)
            rabi_block.append(delay_element)
            rabi_block.append(waiting_element)

        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((rabi_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2*num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_dd_dqt_tau_scan(self, name='dd_tau_scan', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                             dd_type=DDMethods.XY8, dd_order=1, dqt_amp2=0, dqt_t_rabi2=100e-9, dqt_f2=1e9, alternating=True):
        """
        shadows and extends iqo-sequences::generate_dd_tau_scan
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        start_tau_pspacing = self.tau_2_pulse_spacing(tau_start)

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        def pi_element_function(xphase, pi_x_length=1.):
            """
             define a function to create phase shifted pi pulse elements
            :param xphase: phase sift
            :param pi_x_length: multiple of pi pulse. Eg. 0.5 => pi_half pulse
            :return:
            """

            lenghts = [pi_x * self.rabi_period / 2, pi_x_length * dqt_t_rabi2 / 2]
            phases = [xphase, xphase]
            amps = [self.microwave_amplitude, dqt_amp2]
            fs = [self.microwave_frequency, dqt_f2]

            if dqt_amp2 == 0:
                lenghts = lenghts[0:1]
                amps = amps[0:1]
                fs = fs[0:1]
                phases = xphase[0:1]

            """
            legacy: delete after testing
            if dqt_amp2 == 0:
                return self._get_mw_element(length=self.rabi_period / 2,
                                            increment=0,
                                            amp=self.microwave_amplitude,
                                            freq=self.microwave_frequency,
                                            phase=xphase)
            """
            return self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                             amps=amps,
                                                             freqs=fs,
                                                             phases=phases)

        def pi3half_element_function():

            # Use a 180 deg phase shifted pulse as 3pihalf pulse if microwave channel is analog
            if self.microwave_channel.startswith('a'):
                lenghts = [self.rabi_period / 2, dqt_t_rabi2 / 2]
                xphase = 180
                phases = [xphase, xphase]
            else:
                lenghts = [3*self.rabi_period / 4, 3*dqt_t_rabi2 / 4]
                xphase = 0
                phases = [xphase, xphase]

            amps = [self.microwave_amplitude, dqt_amp2]
            fs = [self.microwave_frequency, dqt_f2]

            if dqt_amp2 == 0:
                lenghts = lenghts[0:1]
                amps = amps[0:1]
                fs = fs[0:1]
                phases = xphase[0:1]

            pi3half_element = self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                   increments=0,
                                                   amps=amps,
                                                   freqs=fs,
                                                   phases=phases)

            return pi3half_element

        pihalf_element = pi_element_function(0, pi_x_length=1/2.)
        pi3half_element = pi3half_element_function()
        tauhalf_element = self._get_idle_element(length=start_tau_pspacing / 2, increment=tau_step / 2)
        tau_element = self._get_idle_element(length=start_tau_pspacing, increment=tau_step)

        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)
        dd_block.append(pihalf_element)
        for n in range(dd_order):
            # create the DD sequence for a single order
            for pulse_number in range(dd_type.suborder):
                dd_block.append(tauhalf_element)
                dd_block.append(pi_element_function(dd_type.phases[pulse_number]))
                dd_block.append(tauhalf_element)
        dd_block.append(pihalf_element)
        dd_block.append(laser_element)
        dd_block.append(delay_element)
        dd_block.append(waiting_element)
        if alternating:
            dd_block.append(pihalf_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element)
                    dd_block.append(pi_element_function(dd_type.phases[pulse_number]))
                    dd_block.append(tauhalf_element)
            dd_block.append(pi3half_element)
            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)
        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, num_of_points - 1))

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

    def _get_multiple_mw_mult_length_element(self, lengths, increments, amps=None, freqs=None, phases=None):
        """
        Creates single, double sine mw element.

        @param float lengths: MW pulse duration in seconds
        @param float increments: MW pulse duration increment in seconds
        @param amps: list containing the amplitudes
        @param freqs: list containing the frequencies
        @param phases: list containing the phases
        @return: list of PulseBlockElement, the generated MW element
        """

        if isinstance(lengths, (int, float)):
            lengths = [lengths]
        if isinstance(increments, (int, float)):
            increments = [increments]
        if isinstance(amps, (int, float)):
            amps = [amps]
        if isinstance(freqs, (int, float)):
            freqs = [freqs]
        if isinstance(phases, (int, float)):
            phases = [phases]

        if len(np.unique(increments)) > 1:
            raise NotImplementedError("Currently, can only create multi mw elements with equal increments.")
        if len(lengths) > 2:
            raise NotImplementedError
        if len(amps) != len(lengths):
            raise ValueError

        def create_pulse_partition(lengths, amps):
            """
            The partition for the pulse blocks that realize the (possibly different) 'lengths'.
            If lengths are not equal, one pulse must idle while the other is still active.
            :param lengths:
            :return: [partition_mw1, partition_mw2], specifies length (partition_x[1]) and
                     amplitude (partition_x[0]) of output
            """
            blocks_mw1, blocks_mw2 = [], []
            amp_mw1 = amps[0]
            amp_mw2 = amps[1]

            if len(np.unique(lengths)) == 1:
                blocks_mw1 = [(amp_mw1, lengths[0])]
                blocks_mw2 = [(amp_mw2, lengths[0])]
            elif len(lengths) == 2:
                if lengths[0] > lengths[1]:
                    blocks_mw1 = [(amp_mw1, lengths[1]),
                                  (amp_mw1, lengths[0] - lengths[1])]
                    blocks_mw2 = [(amp_mw2, lengths[1]),
                                  (0, lengths[0] - lengths[1])]
                else:
                    blocks_mw1 = [(amp_mw1, lengths[0]),
                                  (0, lengths[1] - lengths[0])]
                    blocks_mw2 = [(amp_mw2, lengths[0]),
                                  (amp_mw2, lengths[1] - lengths[0])]
            else:
                raise NotImplementedError

            return blocks_mw1, blocks_mw2

        parts_mw1, parts_mw2 = create_pulse_partition(lengths, amps)
        blocks = []

        for idx, p_mw1 in enumerate(parts_mw1):
            p_mw2 = parts_mw2[idx]

            # partition guarantees that all steps have same length (but different ampl)
            assert p_mw1[1] == p_mw2[1]
            lenght = p_mw1[1]
            amp_mw1 = p_mw1[0]
            amp_mw2 = p_mw2[0]
            increment = increments[0] if idx == 0 else 0

            blocks.append(self._get_multiple_mw_element(lenght, increment, [amp_mw1, amp_mw2],
                                                        freqs=freqs, phases=phases))

        return blocks