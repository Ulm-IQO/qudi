import numpy as np
import copy as cp
from enum import Enum, IntEnum

from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from logic.pulsed.sampling_functions import SamplingFunctions, DDMethods
from core.util.helpers import csv_2_list



class DQTAltModes(IntEnum):
    DQT_12_alternating = 1
    DQT_both = 2

class TomoRotations(IntEnum):
    none = 0
    ux90_on_1 = 1   # not strictly needed
    ux90_on_2 = 2   # not strictly needed
    ux180_on_1 = 3
    ux180_on_2 = 4
    c1not2 = 5
    c2not1 = 6  # not strictly needed
    c1not2_ux180_on_2 = 7
    c2not1_ux180_on_1 = 8


class MultiNV_Generator(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_pi2_rabi(self, name='pi2_then_rabi', tau_start = 10.0e-9, tau_step = 10.0e-9,
                                pi2_phase_deg=0, num_of_points = 50, alternating = False):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        num_of_points = len(tau_array)

        # create the laser_mw element
        mw_element = self._get_mw_element(length=tau_start,
                                    increment = tau_step,
                                    amp = self.microwave_amplitude,
                                    freq = self.microwave_frequency,
                                    phase = 0)
        pi_element = self._get_mw_element(length=self.rabi_period / 2,
                                    increment = 0,
                                    amp = self.microwave_amplitude,
                                    freq = self.microwave_frequency,
                                    phase = 0)
        pihalf_element = self._get_mw_element(length=self.rabi_period / 4,
                                              increment=0,
                                              amp=self.microwave_amplitude,
                                              freq=self.microwave_frequency,
                                              phase=pi2_phase_deg)

        waiting_element = self._get_idle_element(length=self.wait_time,
                                    increment = 0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                    increment = 0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        rabi_block.append(pihalf_element)
        rabi_block.append(mw_element)
        rabi_block.append(laser_element)
        rabi_block.append(delay_element)
        rabi_block.append(waiting_element)

        if alternating:
            rabi_block.append(pihalf_element)
            rabi_block.append(mw_element)
            rabi_block.append(pi_element)
            rabi_block.append(laser_element)
            rabi_block.append(delay_element)
            rabi_block.append(waiting_element)

        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((rabi_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(

        ensemble = block_ensemble, created_blocks = created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_tomography(self, name='tomography', tau_start=10.0e-9, tau_step=10.0e-9,
                            rabi_on_nv=1, rabi_phase_deg=0, rotation='', num_of_points=50,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                            alternating=False):
        """

        """
        created_blocks, created_ensembles, created_sequences = list(), list(), list()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2))
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2))
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2))
        rabi_on_nv = int(rabi_on_nv)

        if rabi_on_nv != 1 and rabi_on_nv != 2:
            raise ValueError(f"Can drive Rabi on subsystem NV 1 or 2, not {rabi_on_nv}.")

        if len(mw_freqs) != 4:
            raise ValueError("Expected four mw frequencies: [f_nv1, f_dqt_nv1, f_nv2, f_dqt_nv2]. "
                             "Set respective amplitude to zero, if you want omit certain frequencies")

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        num_of_points = len(tau_array)

        # pulse amplitude order as defined in ValueError above
        ampls_on_1, ampls_on_2 = cp.deepcopy(amplitudes), cp.deepcopy(amplitudes)
        ampls_on_2[2:] = 0
        ampls_on_1[:2] = 0

        # define pulses on the subsystems or both
        mw_on_1_element = self.get_mult_mw_element(rabi_phase_deg, tau_start, mw_freqs, ampls_on_1, tau_step)
        mw_on_2_element = self.get_mult_mw_element(rabi_phase_deg, tau_start, mw_freqs, ampls_on_2, tau_step)
        mw_rabi_element = mw_on_1_element if rabi_on_nv == 1 else mw_on_2_element

        self._get_mw_element(length=tau_start,
                                          increment=tau_step,
                                          amp=self.microwave_amplitude,
                                          freq=self.microwave_frequency,
                                          phase=rabi_phase_deg)

        pi_on_all_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods)
        pi_on_1_element = self.get_pi_element(0, mw_freqs,
                                              ampls_on_1,
                                              rabi_periods)
        pi_on_2_element = self.get_pi_element(0, mw_freqs,
                                              ampls_on_2,
                                              rabi_periods)
        pi_rabi_element = pi_on_1_element if rabi_on_nv else pi_on_2_element

        rot_elements = []
        if rotation:
            if rotation == TomoRotations.none:
                rot_elements = []
            elif rotation == TomoRotations.c1not2:
                rot_elements = [] # TODO: get cnot
            elif rotation == TomoRotations.ux180_on_2:
                rot_elements = [pi_on_2_element]
            elif rotation == TomoRotations.c1not2_ux180_on_2:
                rot_elements = [] # todo: get cnot
            elif rotation == TomoRotations.c2not1_ux180_on_1:
                rot_elements = []  # TODO: get cno
            elif rotation == TomoRotations.ux180_on_1:
                rot_elements = [pi_on_1_element]
            else:
                raise ValueError(f"Unknown rotation: {rotation}")

        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        rabi_block.extend(rot_elements)
        rabi_block.append(mw_rabi_element)
        rabi_block.append(laser_element)
        rabi_block.append(delay_element)
        rabi_block.append(waiting_element)

        if alternating:
            rabi_block.extend(rot_elements)
            rabi_block.append(mw_rabi_element)
            rabi_block.append(pi_rabi_element)
            rabi_block.append(laser_element)
            rabi_block.append(delay_element)
            rabi_block.append(waiting_element)

        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((rabi_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2 * num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(

            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_ent_create_bell(self, name='ent_create_bell', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                             f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                             dd_type=DDMethods.SE, dd_order=1, alternating=True, read_phase_deg=90, no_laser=False):
        """
        Decoupling sequence on both NVs. Initialization with Hadarmard instead of pi2.
        Use lists of f_mw_2, ampl_mw_2, rabi_period_m2_2 to a) address second NV b) use double quantum transition
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2))
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2))
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2))

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
                                              phases=[read_phase_deg,read_phase_deg])

        def pi_element_function(xphase, pi_x_length=1.):

            return self.get_pi_element(xphase, mw_freqs, amplitudes, rabi_periods, pi_x_length=pi_x_length)

            """
            
            return self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                             increments=0,
                                                             amps=amps,
                                                             freqs=fs,
                                                             phases=phases)
            """

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
                                              phases=[read_phase_deg+180,read_phase_deg+180])
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
        if not no_laser:
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
            if not no_laser:
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

    def generate_bell_ramsey(self, name='bell_ramsey', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                                 tau_cnot=100e-9, f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                                 rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                                 dd_type=DDMethods.SE, dd_order=1, alternating=True):
        """
        Use lists of f_mw_2, ampl_mw_2, rabi_period_m2_2 to a) address second NV b) use double quantum transition
        """
        bell_blocks, _, _ = self.generate_ent_create_bell('ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        alternating=False, no_laser=True)
        disent_blocks, _, _ = self.generate_ent_create_bell('dis-ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        alternating=False, read_phase_deg=90)
        disent_alt_blocks, _, _ = self.generate_ent_create_bell('dis-ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        alternating=False, read_phase_deg=-90)


        bell_blocks, disent_blocks, disent_alt_blocks = bell_blocks[0], disent_blocks[0], disent_alt_blocks[0]

        tau_start_pspacing = tau_start
        tau_array = tau_start_pspacing + np.arange(num_of_points) * tau_step
        tau_element = self._get_idle_element(length=tau_start_pspacing, increment=tau_step)

        bell_ramsey_block = PulseBlock(name=name)
        bell_ramsey_block.extend(bell_blocks)
        bell_ramsey_block.append(tau_element)
        bell_ramsey_block.extend(disent_blocks)
        if alternating:
            bell_ramsey_block.extend(bell_blocks)
            bell_ramsey_block.append(tau_element)
            bell_ramsey_block.extend(disent_alt_blocks)

        created_blocks = []
        created_blocks.append(bell_ramsey_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((bell_ramsey_block.name, num_of_points - 1))

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
        created_ensembles, created_sequences = [], []
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_rabi_dqt_p(self, name='rabi_dqt-p', tau_start=10.0e-9, tau_step=10.0e-9,
                      num_of_points=50, f_mw_1_add="", f_mw_2="1e9", ampl_mw_2=0.125,
                            alternating_mode=DQTAltModes.DQT_both):
        """
        Double quantum transition, driven in parallel (instead of sequential)
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        alternating = True if alternating_mode == DQTAltModes.DQT_12_alternating else False
        mw_freqs_1 = np.asarray([self.microwave_frequency] + csv_2_list(f_mw_1_add))
        mw_freqs_2 = np.asarray(csv_2_list(f_mw_2))
        mw_freqs_both = np.concatenate([mw_freqs_1, mw_freqs_2])
        amplitudes_both = np.asarray([self.microwave_amplitude]*len(mw_freqs_1) + [ampl_mw_2]*len(mw_freqs_2)).flatten()
        amplitudes_1 = np.asarray([self.microwave_amplitude]*len(mw_freqs_1) + [0]*len(mw_freqs_2)).flatten()
        amplitudes_1_solo = np.asarray([self.microwave_amplitude] * len(mw_freqs_1)).flatten()
        amplitudes_2 = np.asarray([0]*len(mw_freqs_1) + [ampl_mw_2]*len(mw_freqs_2)).flatten()
        amplitudes_2_solo = np.asarray([ampl_mw_2] * len(mw_freqs_2)).flatten()
        n_lines = len(mw_freqs_both)
        n_lines_1 = len(mw_freqs_1)
        n_lines_2 = len(mw_freqs_2)

        tau_array = tau_start + np.arange(num_of_points) * tau_step
        num_of_points = len(tau_array)

        # don't know why simple eqaulity between enums fails
        if int(alternating_mode) == int(DQTAltModes.DQT_both):
            mw_element = self._get_multiple_mw_element(length=tau_start,
                                              increment=tau_step,
                                              amps=amplitudes_both,
                                              freqs=mw_freqs_both,
                                              phases=[0]*n_lines)
            mw_alt_element = None
        elif int(alternating_mode) == int(DQTAltModes.DQT_12_alternating):
            mw_element = self._get_multiple_mw_element(length=tau_start,
                                                       increment=tau_step,
                                                       amps=amplitudes_1_solo,
                                                       freqs=mw_freqs_1,
                                                       phases=[0]*n_lines_1)
            mw_alt_element = self._get_multiple_mw_element(length=tau_start,
                                              increment=tau_step,
                                              amps=amplitudes_2_solo,
                                              freqs=mw_freqs_2,
                                              phases=[0]*n_lines_2)
        else:
            raise ValueError(f"Unknown DQT mode: {alternating_mode} of type {type(alternating_mode)}")

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
                             dd_type=DDMethods.XY8, dd_order=1, dqt_amp2=0e-3, dqt_t_rabi2=100e-9, dqt_f2=1e9,
                             alternating=True):
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

            # just renaming of the needed parameters for get_pi_element()

            rabi_periods = [self.rabi_period / 2, dqt_t_rabi2 / 2]
            amps = [self.microwave_amplitude, dqt_amp2]
            fs = [self.microwave_frequency, dqt_f2]

            if dqt_amp2 == 0:
                rabi_periods = rabi_periods[0:1]
                amps = amps[0:1]
                fs = fs[0:1]
                phases = phases[0:1]

            return self.get_pi_element(xphase, fs, amps, rabi_periods, pi_x_length=pi_x_length)

            """
            legacy: delete after testing
            if dqt_amp2 == 0:
                return self._get_mw_element(length=self.rabi_period / 2,
                                            increment=0,
                                            amp=self.microwave_amplitude,
                                            freq=self.microwave_frequency,
                                            phase=xphase)

            return self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                             increments=0,
                                                             amps=amps,
                                                             freqs=fs,
                                                             phases=phases)
            """

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
                phases = phases[0:1]

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
        dd_block.extend(pihalf_element)
        for n in range(dd_order):
            # create the DD sequence for a single order
            for pulse_number in range(dd_type.suborder):
                dd_block.append(tauhalf_element)
                dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                dd_block.append(tauhalf_element)
        dd_block.extend(pihalf_element)
        dd_block.append(laser_element)
        dd_block.append(delay_element)
        dd_block.append(waiting_element)
        if alternating:
            dd_block.extend(pihalf_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element)
                    dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                    dd_block.append(tauhalf_element)
            dd_block.extend(pi3half_element)
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

    def generate_dd_dqt_sigamp(self, name='dd_sigamp', tau=0.5e-6, amp_start=0e-3, amp_step=0.01e-3,
                                    num_of_points=50, dd_type=DDMethods.XY8, dd_order=1, ampl_mw2=0e-3,
                                    t_rabi_mw2=0, f_mw2="1e9", f_mw1_add="",
                                    alternating=True):
        
        #todo: not working in tests

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        t_rabi_mw2 = self.rabi_period if t_rabi_mw2 == 0 else t_rabi_mw2

        rabi_periods = np.asarray([self.rabi_period, t_rabi_mw2])
        mw_freqs_1 = np.asarray([self.microwave_frequency] + csv_2_list(f_mw1_add))
        mw_freqs_2 = np.asarray(csv_2_list(f_mw2))
        fs = np.concatenate([mw_freqs_1, mw_freqs_2])
        amps = np.asarray([self.microwave_amplitude]*len(mw_freqs_1) + [ampl_mw2]*len(mw_freqs_2)).flatten()

        # get tau array for measurement ticks
        # todo: considers only pi pulse length of 1 drive (self.rabi_period)
        tau_pspacing = self.tau_2_pulse_spacing(tau)
        sig_amp_array = (amp_start + np.arange(num_of_points) * amp_step)[::-1]

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
            nonlocal rabi_periods, amps, fs

            return self.get_pi_element(xphase, fs, amps, rabi_periods, pi_x_length=pi_x_length)

            """
            legacy: delete after testing
            if dqt_amp2 == 0:
                return self._get_mw_element(length=self.rabi_period / 2,
                                            increment=0,
                                            amp=self.microwave_amplitude,
                                            freq=self.microwave_frequency,
                                            phase=xphase)
           
            return self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                             increments=0,
                                                             amps=amps,
                                                             freqs=fs,
                                                             phases=phases)
             """

        def pi3half_element_function():

            nonlocal  fs, amps, rabi_periods

            # Use a 180 deg phase shifted pulse as 3pihalf pulse if microwave channel is analog
            if self.microwave_channel.startswith('a'):
                lenghts = rabi_periods/2
                xphase = 180
                phases = [xphase, xphase]
            else:
                lenghts = 3*rabi_periods/4
                xphase = 0
                phases = [xphase, xphase]


            pi3half_element = self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                   increments=0,
                                                   amps=amps,
                                                   freqs=fs,
                                                   phases=phases)

            return pi3half_element

        pihalf_element = pi_element_function(0, pi_x_length=1/2.)
        pi3half_element = pi3half_element_function()

        dd_block = PulseBlock(name=name)

        for amp_sig in sig_amp_array:
            tauhalf_element = self._get_mw_element(length=tau_pspacing/2,
                                            increment=0,
                                            amp=amp_sig,
                                            freq=1/(2*tau),
                                            phase=90)

            # Create block and append to created_blocks list
            dd_block.extend(pihalf_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element)
                    dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                    dd_block.append(tauhalf_element)
            dd_block.extend(pihalf_element)
            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)
            if alternating:
                dd_block.extend(pihalf_element)
                for n in range(dd_order):
                    # create the DD sequence for a single order
                    for pulse_number in range(dd_type.suborder):
                        dd_block.append(tauhalf_element)
                        dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                        dd_block.append(tauhalf_element)
                dd_block.extend(pi3half_element)
                dd_block.append(laser_element)
                dd_block.append(delay_element)
                dd_block.append(waiting_element)

        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = sig_amp_array
        block_ensemble.measurement_information['units'] = ('V', '')
        block_ensemble.measurement_information['labels'] = ('Signal ampl.', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def get_mult_mw_element(self, phase, length, mw_freqs, mw_amps, increment=0):
        """
        Mw element on multiple lines (freqs) with same length on every of these.
        :param phase:
        :param length:
        :param mw_freqs:
        :param mw_amps:
        :param increment:
        :return:
        """
        assert len(mw_freqs) == len(mw_amps)
        n_lines = len(mw_freqs)

        lenghts = [length] * n_lines
        phases = [phase] * n_lines
        increments = [increment] * n_lines
        amps = mw_amps
        fs = mw_freqs

        return self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                         increments=increments,
                                                         amps=amps,
                                                         freqs=fs,
                                                         phases=phases)

    def get_pi_element(self, xphase, mw_freqs, mw_amps, rabi_periods,
                       pi_x_length=1.):
        """
         define a function to create phase shifted pi pulse elements
        :param xphase: phase sift
        :param pi_x_length: multiple of pi pulse. Eg. 0.5 => pi_half pulse
        :return:
        """

        assert len(mw_freqs) == len(mw_amps) == len(rabi_periods)
        n_lines = len(mw_freqs)

        lenghts = pi_x_length * rabi_periods / 2
        phases = [float(xphase)] * n_lines
        amps = mw_amps
        fs = mw_freqs

        return self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                         increments=0,
                                                         amps=amps,
                                                         freqs=fs,
                                                         phases=phases)

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
        if len(amps) != len(lengths):
            raise ValueError

        def create_pulse_partition(lengths, amps):
            """
            The partition for the pulse blocks that realize the (possibly different) 'lengths'.
            If lengths are not equal, one pulse must idle while the others are still active.
            :param lengths:
            :return: list with elements (length, amps=[amp0, amp1, ..]], each a block of the partition
            """

            partition_blocks = []

            # if pulses are ordered in ascending length
            # and idx_part are subpulses to the right, idx_ch channels downwards
            # the lower triangle of the matrix are subpulses with non-zero amplitude
            n_ch = len(lengths)
            length_amps = sorted(zip(lengths, amps, range(n_ch)), key=lambda x: x[0])

            for idx_part, _ in enumerate(length_amps):
                amps_part = np.zeros((n_ch))

                t_so_far = np.sum([p[0] for p in partition_blocks])
                lenght_part = length_amps[idx_part][0] - t_so_far

                for idx_ch in range(0, n_ch):
                    if idx_part <= idx_ch:
                        ch = length_amps[idx_ch][2]
                        amp_i = amps[ch]
                        # keep original order of channels
                        i = np.where(np.asarray(amps) == amp_i)[0]
                        amps_part[i] = amps[ch]

                if lenght_part > 0:
                    partition_blocks.append([lenght_part, amps_part])

            return partition_blocks

        part_blocks = create_pulse_partition(lengths, amps)
        blocks = []

        for idx, block in enumerate(part_blocks):

            increment = increments[0] if idx == 0 else 0
            amps = block[1]
            length = block[0]

            blocks.append(self._get_multiple_mw_element(length, increment, amps,
                                                        freqs=freqs, phases=phases))

        return blocks

    @staticmethod
    def _create_param_array(in_value, in_list):
        array = [in_value]
        array.extend(in_list)
        return np.asarray(array)
