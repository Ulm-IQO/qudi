import numpy as np
import copy as cp
from enum import Enum, IntEnum

from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from logic.pulsed.sampling_functions import SamplingFunctions, DDMethods
from logic.pulsed.sampling_function_defs.sampling_functions_nvision import EnvelopeMethods
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

class TomoInit(IntEnum):
    none = 0
    ux90_on_1 = 1
    ux90_on_2 = 2
    ux90_on_both = 3
    uy90_on_1 = 4
    uy90_on_2 = 5
    uy90_on_both = 6
    ux180_on_1 = 7
    ux180_on_2 = 8
    ux180_on_both = 9
    ent_create_bell = 10
    ent_create_bell_bycnot = 11
    ux90_on_1_uy90_on_2 = 12
    ux90_on_1_ux180_on_2 = 13


class MultiNV_Generator(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_generation_method(self, method_name):
        # evil access to all loaded generation methods. Use carefully.
        return self._PredefinedGeneratorBase__sequencegeneratorlogic.generate_methods[method_name]

    # evil setters for comomon generation settings, use with care. Typically, restore after changing in generation method.
    @PredefinedGeneratorBase.rabi_period.setter
    def rabi_period(self, t_rabi):

        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'rabi_period': t_rabi})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @PredefinedGeneratorBase.microwave_amplitude.setter
    def microwave_amplitude(self, ampl):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'microwave_amplitude': ampl})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @PredefinedGeneratorBase.microwave_frequency.setter
    def microwave_frequency(self, freq):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'microwave_frequency': freq})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params


    def generate_pi2_rabi(self, name='pi2_then_rabi', tau_start = 10.0e-9, tau_step = 10.0e-9,
                                pi2_phase_deg=0, num_of_points = 50, alternating=False):
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
                            rabi_on_nv=1, rabi_phase_deg=0, rotation=TomoRotations.none, init_state=TomoInit.none,
                            num_of_points=50,
                            tau_cnot=0e-9, dd_type_cnot=DDMethods.SE, dd_order=1,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                            alternating=False, init_state_kwargs='', cnot_kwargs=''):
        """
        pulse amplitude/frequency/rabi_period order: [f_nv1, f_dqt_nv1, f_nv2, f_dqt_nv2]
        """
        created_blocks, created_ensembles, created_sequences = list(), list(), list()

        # handle kwargs
        # allow to overwrite generation parameters by kwargs or default to this gen method params
        dd_type_ent = dd_type_cnot if 'dd_type' not in init_state_kwargs else init_state_kwargs['dd_type']
        dd_order_ent = dd_order if 'dd_order' not in init_state_kwargs else init_state_kwargs['dd_order']
        tau_ent = tau_cnot if 'tau_start' not in init_state_kwargs else init_state_kwargs['tau_start']
        rabi_period_mw_2_ent = rabi_period_mw_2 if 'rabi_period_mw_2' not in init_state_kwargs\
                               else init_state_kwargs['rabi_period_mw_2']
        rabi_period_mw_2_cnot = rabi_period_mw_2 if 'rabi_period_mw_2' not in cnot_kwargs else \
                                cnot_kwargs['rabi_period_mw_2']
        ampl_mw_2_cnot = ampl_mw_2 if 'ampl_mw_2' not in cnot_kwargs else \
                                cnot_kwargs['ampl_mw_2']

        # create param arrays
        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), n_nvs=2)
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), n_nvs=2)
        rabi_on_nv = int(rabi_on_nv)


        self.log.debug(f"Tomographic rabi on {rabi_on_nv}. Ampls_both: {amplitudes},"
                       f" ampl_1= {ampls_on_1}, ampl_2= {ampls_on_2}, ampl_2_cnot: {ampl_mw_2_cnot}")



        if rabi_on_nv != 1 and rabi_on_nv != 2:
            raise ValueError(f"Can drive Rabi on subsystem NV 1 or 2, not {rabi_on_nv}.")

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        num_of_points = len(tau_array)


        # define pulses on the subsystems or both
        mw_on_1_element = self.get_mult_mw_element(rabi_phase_deg, tau_start, mw_freqs, ampls_on_1, increment=tau_step)
        mw_on_2_element = self.get_mult_mw_element(rabi_phase_deg, tau_start, mw_freqs, ampls_on_2, increment=tau_step)
        mw_rabi_element = mw_on_1_element if rabi_on_nv == 1 else mw_on_2_element

        # simple rotations
        pi_on_both_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods)
        pi_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods)
        pi_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods)
        pi2_on_both_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods, pi_x_length=0.5)
        pi2_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods, pi_x_length=0.5)
        pi2_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods, pi_x_length=0.5)
        pi2y_on_1_element = self.get_pi_element(90, mw_freqs, ampls_on_1, rabi_periods, pi_x_length=0.5)
        pi2y_on_2_element = self.get_pi_element(90, mw_freqs, ampls_on_2, rabi_periods, pi_x_length=0.5)

        pi_read_element = cp.deepcopy(pi_on_1_element) if rabi_on_nv==1 else cp.deepcopy(pi_on_2_element)
        self.log.debug(f"Read element on nv {rabi_on_nv}: {pi_on_1_element}")

        # 2 qubit gates

        c1not2_element, _, _ = self.generate_c1not2('c1not2', tau_start=tau_cnot, tau_step=0.0e-6, num_of_points=1,
                                                  f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2_cnot, rabi_period_mw_2=rabi_period_mw_2_cnot,
                                                  dd_type=dd_type_cnot, dd_order=dd_order, alternating=False,
                                                  no_laser=True,
                                                  kwargs_dict=cnot_kwargs)
        c1not2_element = c1not2_element[0]
        c2not1_element, _, _ = self.generate_c2not1('c2not1', tau_start=tau_cnot, tau_step=0.0e-6, num_of_points=1,
                                                  f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2_cnot, rabi_period_mw_2=rabi_period_mw_2_cnot,
                                                  dd_type=dd_type_cnot, dd_order=dd_order, alternating=False,
                                                  no_laser=True,
                                                  kwargs_dict=cnot_kwargs)
        c2not1_element = c2not1_element[0]



        """
        ent_create_element, _, _, = self.generate_ent_create_bell(tau_start=tau_ent, tau_step=0, num_of_points=1,
                             f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                             dd_type=dd_type_ent, dd_order=dd_order_ent, alternating=False, read_phase_deg=90,
                             no_laser=True)
        # todo: currently untested
       
        ent_create_element = []
        """
        ent_create_bycnot_element, _, _, = self.generate_ent_create_bell_bycnot(tau_start=tau_ent, tau_step=0, num_of_points=1,
                                                                  f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                  rabi_period_mw_2=rabi_period_mw_2_ent,
                                                                  dd_type=dd_type_ent, dd_order=dd_order_ent,
                                                                  kwargs_dict=cnot_kwargs,
                                                                  alternating=False, no_laser=True)
        ent_create_bycnot_element = ent_create_bycnot_element[0]

        init_elements, rot_elements = [], []
        if init_state:
            if init_state == TomoInit.none:
                init_elements = []
            elif init_state == TomoInit.ux90_on_1:
                init_elements = pi2_on_1_element
            elif init_state == TomoInit.ux90_on_2:
                init_elements = pi2_on_2_element
            elif init_state == TomoInit.ux90_on_both:
                init_elements = pi2_on_both_element
            elif init_state == TomoInit.uy90_on_1:
                init_elements = pi2y_on_1_element
            elif init_state == TomoInit.uy90_on_2:
                init_elements = pi2y_on_2_element
            elif init_state == TomoInit.ux180_on_1:
                init_elements = pi_on_1_element
            elif init_state == TomoInit.ux180_on_2:
                init_elements = pi_on_2_element
            elif init_state == TomoInit.ux180_on_both:
                #init_elements = pi_on_both_element
                init_elements = pi_on_1_element
                init_elements.extend(pi_on_2_element)
            elif init_state == TomoInit.ux90_on_1_uy90_on_2:
                init_elements = pi2_on_1_element
                init_elements.extend(pi2y_on_2_element)
            elif init_state == TomoInit.ux90_on_1_ux180_on_2:
                init_elements = pi2_on_1_element
                init_elements.extend(pi_on_2_element)
            elif init_state == TomoInit.ent_create_bell:
                init_elements = ent_create_element
            elif init_state == TomoInit.ent_create_bell_bycnot:
                init_elements = ent_create_bycnot_element
            else:
                raise ValueError(f"Unknown tomography init state: {init_state.name}")
        if rotation:
            if rotation == TomoRotations.none:
                rot_elements = []
            elif rotation == TomoRotations.c1not2:
                rot_elements = c1not2_element
            elif rotation == TomoRotations.c2not1:
                rot_elements = c2not1_element
            elif rotation == TomoRotations.ux180_on_1:
                rot_elements = pi_on_1_element
            elif rotation == TomoRotations.ux180_on_2:
                rot_elements = pi_on_2_element
            elif rotation == TomoRotations.c1not2_ux180_on_2:
                rot_elements = c1not2_element
                rot_elements.extend(pi_on_2_element)
            elif rotation == TomoRotations.c2not1_ux180_on_1:
                rot_elements = c2not1_element
                rot_elements.extend(pi_on_1_element)
            else:
                raise ValueError(f"Unknown tomography rotation: {rotation.name}")

        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        rabi_block.extend(init_elements)
        rabi_block.extend(rot_elements)
        rabi_block.extend(mw_rabi_element)
        rabi_block.append(laser_element)
        rabi_block.append(delay_element)
        rabi_block.append(waiting_element)

        if alternating:
            rabi_block.extend(init_elements)
            rabi_block.extend(rot_elements)
            rabi_block.extend(mw_rabi_element)
            rabi_block.extend(pi_read_element)
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

    def generate_c2not1(self, name='c2not1', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                            rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                            dd_type=DDMethods.SE, dd_order=1,
                            read_phase_deg=0, order_nvs="1,2",
                            alternating=False, no_laser=True,
                            # arguments passed to generate methods
                            kwargs_dict=''):

        read_phase = 90 + read_phase_deg   # 90° to deer realizes cnot, additional phase by parameter

        env_type = EnvelopeMethods.rectangle if 'env_type' not in kwargs_dict else kwargs_dict['env_type']
        order_p = 1 if 'order_P' not in kwargs_dict else kwargs_dict['order_P']
        tau_dd_fix = None if 'tau_dd_fix' not in kwargs_dict else kwargs_dict['tau_dd_fix']
        rabi_period_1 = self.rabi_period if 'rabi_period' not in kwargs_dict else kwargs_dict['rabi_period']

        if env_type == EnvelopeMethods.rectangle:
            if tau_dd_fix is not None:
                return self.generate_deer_dd_tau(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                                                 tau1=tau_dd_fix,
                                                 f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                                                 dd_type=dd_type, dd_order=dd_order, alternating=alternating, no_laser=no_laser,
                                                 nv_order=order_nvs, end_pix_on_2=1,
                                                 read_phase_deg=read_phase)
            else:
                return self.generate_deer_dd_par_tau(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                                     f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                                     dd_type=dd_type, dd_order=dd_order, alternating=alternating, no_laser=no_laser,
                                     nv_order=order_nvs, end_pix_on_2=1,
                                     read_phase_deg=read_phase)

        else:

            # may provide newy rabi_period in kwargs that overwrites common settings
            # atm, no support for changed mw_ampl or mw_f
            self.save_rabi_period, self.save_microwave_amplitude, self.save_microwave_frequency = \
                self.rabi_period, self.microwave_amplitude, self.microwave_frequency
            self.rabi_period = rabi_period_1

            d_blocks, d_ensembles, d_sequences = self.generate_deer_dd_tau_nvision(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                                             f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                                             dd_type=dd_type, dd_order=dd_order, alternating=alternating, no_laser=no_laser,
                                             nv_order=order_nvs,
                                             read_phase_deg=read_phase, end_pix_on_2=1,
                                             env_type=env_type, order_P=order_p, tau_dd_fix=tau_dd_fix)

            self.rabi_period = self.save_rabi_period
            #self.microwave_amplitude = self.save_microwave_amplitude
            #self.microwave_frequency = self.save_microwave_frequency

            return d_blocks, d_ensembles, d_sequences

    def generate_c1not2(self, name='c1not2', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                        f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                        rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                        dd_type=DDMethods.SE, dd_order=1,
                        read_phase_deg=0,
                        alternating=False, no_laser=True,
                        # arguments passed to nvision method
                        kwargs_dict=''):

        # just change order of nvs to swap control and target qubit
        order_nvs = "2,1"

        return self.generate_c2not1(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                            f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                            rabi_period_mw_2=rabi_period_mw_2,
                            dd_type=dd_type, dd_order=dd_order,
                            read_phase_deg=read_phase_deg, order_nvs=order_nvs,
                            alternating=alternating, no_laser=no_laser,
                            # arguments passed to nvision method
                            kwargs_dict=kwargs_dict)


    def generate_deer_dd_tau_nvision(self, name='DEER_DD_tau', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                        f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                        rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                        dd_type=DDMethods.SE, dd_order=1,
                        env_type=EnvelopeMethods.rectangle, order_P=1, tau_dd_fix=100e-9,
                        nv_order="1,2", read_phase_deg=90, init_pix_on_2=0, end_pix_on_2=0,
                        alternating=True, no_laser=False):

        self.log.info("Using Nvision generate method 'DEER_DD_tau'.")
        generate_method = self._get_generation_method('DEER_DD_tau')
        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), order_nvs=nv_order,
                                                n_nvs=2)
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), order_nvs=nv_order,
                                              n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), order_nvs=nv_order, n_nvs=2)
        if len(rabi_periods) != 2 or len(amplitudes) != 2 or len(mw_freqs) != 2:
            raise ValueError("Nvision method only supports two drive frequenices")

        rabi_period_2 = rabi_periods[1]
        mq_freq_2 = mw_freqs[1]
        mw_ampl_2 = amplitudes[1]

        # nvision code expects non-zero tau_step for 1 point
        if tau_step == 0. and num_of_points == 1:
            tau_step = 1e-10
            #tau_start = -tau_start

        d_blocks, d_ensembles, d_sequences = generate_method(name=name,
                                                             rabi_period2=rabi_period_2,
                                                             mw_freq2=mq_freq_2, mw_amp2=mw_ampl_2,
                                                             tau=tau_dd_fix, tau2_start=tau_start,
                                                             tau2_incr=tau_step,
                                                             num_of_points=num_of_points,
                                                             order=dd_order,
                                                             env_type=env_type, order_P=order_P,
                                                             DD_type=dd_type, alternating=alternating,
                                                             normalization=0, tau2_rel_to_pi1=False,
                                                             no_laser=no_laser,
                                                             read_phase=read_phase_deg,
                                                             init_pix_on_2=init_pix_on_2, end_pix_on_2=end_pix_on_2)


        return d_blocks, d_ensembles, d_sequences

    def generate_deer_dd_par_tau(self, name='deer_dd_par_tau', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                                 f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                                 dd_type=DDMethods.SE, dd_order=1, alternating=True,
                                 init_pix_on_2=0, end_pix_on_2=0, nv_order="1,2", read_phase_deg=90, no_laser=False):
        """
        Decoupling sequence on both NVs.
        In contrast to 'normal' DEER, the position of the pi on NV2 is not swept. Instead, the pi pulses on NV1 & NV2
        are varied in parallel
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), order_nvs=nv_order, n_nvs=2)
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), order_nvs=nv_order, n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2, order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2, order_nvs=nv_order)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), order_nvs=nv_order, n_nvs=2)

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        start_tau_pspacing = self.tau_2_pulse_spacing(tau_start)  # todo: considers only t_rabi of NV1


        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_on1_element = self.get_pi_element(0, mw_freqs, mw_amps=ampls_on_1, rabi_periods=rabi_periods,
                                                pi_x_length=1/2, no_amps_2_idle=True)
        pix_init_on2_element = self.get_pi_element(0, mw_freqs, mw_amps=ampls_on_2, rabi_periods=rabi_periods,
                                                   pi_x_length=init_pix_on_2, no_amps_2_idle=False)
        pix_end_on2_element = self.get_pi_element(0, mw_freqs, mw_amps=ampls_on_2, rabi_periods=rabi_periods,
                                                   pi_x_length=end_pix_on_2, no_amps_2_idle=False)
        pihalf_on1_read_element = self.get_pi_element(read_phase_deg, mw_freqs, mw_amps=ampls_on_1,
                                                      rabi_periods=rabi_periods,
                                                      pi_x_length=1/2, no_amps_2_idle=True)
        pihalf_on1_alt_read_element = self.get_pi_element(180+read_phase_deg,
                                                          mw_freqs, mw_amps=ampls_on_1,
                                                          rabi_periods=rabi_periods,
                                                          pi_x_length=1/2, no_amps_2_idle=True)

        def pi_element_function(xphase, pi_x_length=1.):

            return self.get_pi_element(xphase, mw_freqs, amplitudes, rabi_periods, pi_x_length=pi_x_length)

        tauhalf_element = self._get_idle_element(length=start_tau_pspacing / 2, increment=tau_step / 2)
        tau_element = self._get_idle_element(length=start_tau_pspacing, increment=tau_step)

        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)
        dd_block.extend(pix_init_on2_element)
        dd_block.extend(pihalf_on1_element)
        for n in range(dd_order):
            # create the DD sequence for a single order
            for pulse_number in range(dd_type.suborder):
                dd_block.append(tauhalf_element)
                dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                dd_block.append(tauhalf_element)
        dd_block.extend(pihalf_on1_read_element)
        dd_block.extend(pix_end_on2_element)
        if not no_laser:
            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)

        if alternating:
            dd_block.extend(pix_init_on2_element)
            dd_block.extend(pihalf_on1_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element)
                    dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                    dd_block.append(tauhalf_element)
            dd_block.extend(pihalf_on1_alt_read_element)
            dd_block.extend(pix_end_on2_element)
            if not no_laser:
                dd_block.append(laser_element)
                dd_block.append(delay_element)
                dd_block.append(waiting_element)
        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        if not no_laser:
            self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array * dd_order * dd_type.suborder
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('t_evol', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_deer_dd_tau(self, name='deer_dd_tau', tau1=0.5e-6, tau_start=0e-6, tau_step=0.01e-6, num_of_points=50,
                                 f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                                 dd_type=DDMethods.SE, dd_order=1, dd_phase_slip_w=0, alternating=True,
                                 init_pix_on_1=0, init_pix_on_2=0, end_pix_on_2=0,
                                 nv_order="1,2", read_phase_deg=90, no_laser=False):
        """
        Decoupling sequence on both NVs.
        Tau1 is kept constant and the second pi pulse is swept through.
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), order_nvs=nv_order,
                                                n_nvs=2)
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), order_nvs=nv_order,
                                              n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2,
                                              order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2,
                                              order_nvs=nv_order)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), order_nvs=nv_order, n_nvs=2)

        self.log.debug(f"deer_dd with ampl1/2= {ampls_on_1}, {ampls_on_2}, t_rabi: {rabi_periods}, f: {mw_freqs}")

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        pihalf_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,  pi_x_length=0.5)
        pi_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,  pi_x_length=1,
                                             no_amps_2_idle=False)
        pi_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,  pi_x_length=1,
                                             no_amps_2_idle=False)
        pix_init_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                                   pi_x_length=init_pix_on_2, no_amps_2_idle=False)
        pix_init_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                                   pi_x_length=init_pix_on_1, no_amps_2_idle=False)

        # read phase opposite to canonical DD: 0->0 on no phase evolution
        pihalf_on1_read_element = self.get_pi_element(180+read_phase_deg, mw_freqs, ampls_on_1, rabi_periods,
                                                      pi_x_length=0.5)
        pihalf_on1_alt_read_element = self.get_pi_element(0 + read_phase_deg, mw_freqs, ampls_on_1, rabi_periods,
                                                      pi_x_length=0.5)

        def pi_element_function(xphase, on_nv=1, pi_x_length=1.):

            if on_nv == 1:
                ampl_pi = ampls_on_1
            elif on_nv == 2:
                ampl_pi = ampls_on_2
            else:
                raise ValueError

            return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                       pi_x_length=pi_x_length, no_amps_2_idle=True)

        def get_deer_pos(i_dd_order, dd_order, i_dd_suborder, dd_type, before_pi_on1):
            first = (i_dd_order == 0 and i_dd_suborder == 0 and before_pi_on1)
            last = (i_dd_order == dd_order - 1 and i_dd_suborder == dd_type.suborder - 1 and not before_pi_on1)
            in_between = not first and not last

            return first, last, in_between

        def tauhalf_element_function(i_dd_order, dd_order, i_dd_suborder, dd_type, before_pi_on1=False):

            first, last, in_between = get_deer_pos(i_dd_order, dd_order, i_dd_suborder, dd_type, before_pi_on1)

            if first and last:
                self.log.warning("Not tested for low order DD. May work, but be careful.")

            if first:
                if before_pi_on1:
                    return tauhalf_first_element
                else:
                    return tauhalf_bef_element
            if last:
                if before_pi_on1:
                    return tauhalf_aft_element
                else:
                    return tauhalf_last_element

            if in_between:
                if before_pi_on1:
                    return tauhalf_bef_element
                else:
                    return tauhalf_aft_element

        t_pi_on1 = MultiNV_Generator.get_element_length(pi_on1_element)
        t_pi_on2 = MultiNV_Generator.get_element_length(pi_on2_element)

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        tauhalf_first_pspacing = self.tau_2_pulse_spacing(tau1/2,
                                                 custom_func=[lambda t: t-t_pi_on1/2-t_pi_on1/4,
                                                              lambda t: t+t_pi_on1/2+t_pi_on1/4])
        tauhalf_last_pspacing = self.tau_2_pulse_spacing(tau1/2,
                                                 custom_func=[lambda t: t-t_pi_on1/2-t_pi_on1/4,
                                                              lambda t: t+t_pi_on1/2+t_pi_on1/4])
        if end_pix_on_2 != 0:
            pix_end_on2_element = self.get_pi_element(dd_type.phases[0], mw_freqs, ampls_on_2,
                                                      rabi_periods,
                                                      pi_x_length=end_pix_on_2, no_amps_2_idle=True)
            tauhalf_last_pspacing -= MultiNV_Generator.get_element_length(pix_end_on2_element)


        start_tau2_pspacing = self.tau_2_pulse_spacing(tau1,
                                                       custom_func=[lambda t:t-t_pi_on1-t_pi_on2,
                                                                    lambda t:t+t_pi_on1+t_pi_on2])

        # after pi_on_1
        tauhalf_aft_element = self._get_idle_element(length=start_tau2_pspacing/2+tau_start, increment=tau_step)
        # before pi_on_1
        tauhalf_bef_element = self._get_idle_element(length=start_tau2_pspacing/2-tau_start, increment=-tau_step)
        # first and last tauhalf
        tauhalf_first_element = self._get_idle_element(length=tauhalf_first_pspacing, increment=0)
        tauhalf_last_element = self._get_idle_element(length=tauhalf_last_pspacing, increment=0)

        tauhalf_bef_min = MultiNV_Generator.get_element_length_max(tauhalf_bef_element, num_of_points)
        tauhalf_aft_min = MultiNV_Generator.get_element_length_max(tauhalf_aft_element, num_of_points)
        if tauhalf_bef_min < 0 or tauhalf_aft_min < 0:
            # todo: catch negative pspacing and throw datapoints out, instead of raising
            self.log.debug(f"t_pi1= {t_pi_on1}, t_pi2= {t_pi_on2}, start_tau2_ps= {start_tau2_pspacing},"
                           f"tau_start= {tau_start}, tau_step= {tau_step}, tau1= {tau1}")
            raise ValueError(f"Tau1, tau setting yields negative pulse spacing "
                             f"{np.min([tauhalf_bef_min, tauhalf_aft_min])}."
                             f" Increase tau1 or decrease tau. Check debug for pulse times")

        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)
        if init_pix_on_2 != 0:
            # # todo: consider phase on this one?
            # todo: double check that timing auf pis on 1 is kept correctly with init pulse
            dd_block.extend(pix_init_on2_element)
        if init_pix_on_1 != 0:
            dd_block.extend(pix_init_on1_element)
        dd_block.extend(pihalf_on1_element)
        for n in range(dd_order):
            # create the DD sequence for a single order
            for pulse_number in range(dd_type.suborder):
                dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, True))
                dd_block.extend(pi_element_function(dd_type.phases[pulse_number], on_nv=1))
                dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False))
                first, last, in_between = get_deer_pos(n, dd_order, pulse_number, dd_type, False)
                if last:
                    if end_pix_on_2 != 0:
                        pix_end_on2_element = self.get_pi_element(dd_type.phases[pulse_number], mw_freqs, ampls_on_2,
                                                                  rabi_periods,
                                                                  pi_x_length=end_pix_on_2, no_amps_2_idle=True)
                        dd_block.extend(pix_end_on2_element)
                else:
                    dd_block.extend(pi_element_function(dd_type.phases[pulse_number], on_nv=2))
        dd_block.extend(pihalf_on1_read_element)

        if not no_laser:
            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)


        if alternating:
            if init_pix_on_2 != 0:
                # # todo: consider phase on this one?
                dd_block.extend(pix_init_on2_element)
            if init_pix_on_1 != 0:
                dd_block.extend(pix_init_on1_element)
            dd_block.extend(pihalf_on1_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, True))
                    dd_block.extend(pi_element_function(dd_type.phases[pulse_number], on_nv=1))
                    dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False))
                    first, last, in_between = get_deer_pos(n, dd_order, pulse_number, dd_type, False)
                    if last:
                        if end_pix_on_2 != 0:
                            pix_end_on2_element = self.get_pi_element(dd_type.phases[pulse_number], mw_freqs,
                                                                      ampls_on_2,
                                                                      rabi_periods,
                                                                      pi_x_length=end_pix_on_2, no_amps_2_idle=True)
                            dd_block.extend(pix_end_on2_element)
                    else:
                        dd_block.extend(pi_element_function(dd_type.phases[pulse_number], on_nv=2))
            dd_block.extend(pihalf_on1_alt_read_element)

            if not no_laser:
                dd_block.append(laser_element)
                dd_block.append(delay_element)
                dd_block.append(waiting_element)


        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        if not no_laser:
            self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_ramsey_crosstalk(self, name='ramsey_ct', tau_start=1.0e-6, tau_step=1.0e-6, num_of_points=50,
                        f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", alternating_ct=True):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), n_nvs=2)
        n_drives = len(mw_freqs)

        # get tau array for measurement ticks
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

        tau_ct_element = self._get_multiple_mw_mult_length_element(lengths=[tau_start]*n_drives,
                                                                        increments=[tau_step]*n_drives,
                                                                        amps=[0]*n_drives,
                                                                        freqs=mw_freqs,
                                                                        phases=[0]*n_drives)
        tau_ct_alt_element = self._get_multiple_mw_mult_length_element(lengths=[tau_start]*n_drives,
                                                                        increments=[tau_step]*n_drives,
                                                                        amps=ampls_on_2,
                                                                        freqs=mw_freqs,
                                                                        phases=[0]*n_drives)

        # Create block and append to created_blocks list
        ramsey_block = PulseBlock(name=name)
        ramsey_block.append(pihalf_element)
        ramsey_block.extend(tau_ct_element)
        ramsey_block.append(pihalf_element)
        ramsey_block.append(laser_element)
        ramsey_block.append(delay_element)
        ramsey_block.append(waiting_element)
        if alternating_ct:
            ramsey_block.append(pihalf_element)
            ramsey_block.extend(tau_ct_alt_element)
            ramsey_block.append(pi3half_element)
            ramsey_block.append(laser_element)
            ramsey_block.append(delay_element)
            ramsey_block.append(waiting_element)
        created_blocks.append(ramsey_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((ramsey_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = 2 * num_of_points if alternating_ct else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating_ct
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

    def generate_deer_dd_f(self, name='deer_dd_f', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                                 f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                                 dd_type=DDMethods.SE, dd_order=1, alternating=True,
                                 init_pix_on_2=0, nv_order="1,2", read_phase_deg=90, no_laser=False):
        """
        Decoupling sequence on both NVs.
        In contrast to 'normal' DEER, the position of the pi on NV2 is not swept. Instead, the pi pulses on NV1 & NV2
        are varied in parallel
        Order in f_mw2 / ampl_mw_2:
        """
        # todo: finish, this is a stub copy of deer_dd_tau
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), order_nvs=nv_order, n_nvs=2)
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), order_nvs=nv_order, n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2, order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2, order_nvs=nv_order)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), order_nvs=nv_order, n_nvs=2)

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        start_tau_pspacing = self.tau_2_pulse_spacing(tau_start)  # todo: considers only t_rabi of NV1
        # self.log.debug("So far tau_start: {}, new: {}".format(real_start_tau, start_tau_pspacing))

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        pihalf_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                        increments=[0, 0],
                                                                        amps=ampls_on_1,
                                                                        freqs=mw_freqs,
                                                                        phases=[0, 0])
        pi_both_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 2,
                                                                    increments=[0, 0],
                                                                    amps=amplitudes,
                                                                    freqs=mw_freqs,
                                                                    phases=[0, 0])
        pix_on2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 2*init_pix_on_2,
                                                                    increments=[0, 0],
                                                                    amps=ampls_on_2,
                                                                    freqs=mw_freqs,
                                                                    phases=[0, 0])

        pihalf_on1_read_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_1,
                                                                          freqs=mw_freqs,
                                                                          phases=[read_phase_deg, read_phase_deg])
        pihalf_on1_alt_read_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_1,
                                                                          freqs=mw_freqs,
                                                                          phases=[180+read_phase_deg, 180+read_phase_deg])

        def pi_element_function(xphase, pi_x_length=1.):

            return self.get_pi_element(xphase, mw_freqs, amplitudes, rabi_periods, pi_x_length=pi_x_length)

        tauhalf_element = self._get_idle_element(length=start_tau_pspacing / 2, increment=tau_step / 2)
        tau_element = self._get_idle_element(length=start_tau_pspacing, increment=tau_step)

        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)
        if init_pix_on_2 != 0:
            dd_block.extend(pix_on2_element)
        dd_block.extend(pihalf_on1_element)
        for n in range(dd_order):
            # create the DD sequence for a single order
            for pulse_number in range(dd_type.suborder):
                dd_block.append(tauhalf_element)
                dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                dd_block.append(tauhalf_element)
        dd_block.extend(pihalf_on1_read_element)
        if not no_laser:
            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)
        if alternating:
            if init_pix_on_2 != 0:
                dd_block.extend(pix_on2_element)
            dd_block.extend(pihalf_on1_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element)
                    dd_block.extend(pi_element_function(dd_type.phases[pulse_number]))
                    dd_block.append(tauhalf_element)
            dd_block.extend(pihalf_on1_alt_read_element)
            if not no_laser:
                dd_block.append(laser_element)
                dd_block.append(delay_element)
                dd_block.append(waiting_element)
        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        if not no_laser:
            self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array * dd_order * dd_type.suborder
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('t_evol', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
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
                                              phases=[90,90])
        pihalf_y_both_read_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=amplitudes,
                                                                          freqs=mw_freqs,
                                                                          phases=[read_phase_deg, read_phase_deg])

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
            pi3half_y_both_read_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods/4,
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
        dd_block.extend(pihalf_y_both_read_element)
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
            dd_block.extend(pi3half_y_both_read_element)
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
        block_ensemble.measurement_information['controlled_variable'] = tau_array*dd_order*dd_type.suborder
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('t_evol', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_ent_create_bell_bycnot(self, name='ent_create_bell_bycnot', tau_start=10e-9, tau_step=10e-9,
                                        num_of_points=50,
                                        f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                                        rabi_period_mw_2="100e-9, 100e-9, 100e-9", dd_type=DDMethods.SE, dd_order=1,
                                        kwargs_dict='', use_c2not1=False,
                                        alternating=True, no_laser=False, read_phase_deg=0):
        """
        Similar to ent_create_bell(), but instead of Dolde's sequence uses Hadamard + CNOT (via DEER)
        :return:
        """

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), n_nvs=2)
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), n_nvs=2)

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        c1not2_element, _, _ = self.generate_c1not2('c1not2', tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                             f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                             kwargs_dict=kwargs_dict,  read_phase_deg=read_phase_deg,
                             dd_type=dd_type, dd_order=dd_order, alternating=False, no_laser=no_laser)
        c1not2_element = c1not2_element[0]
        c1not2_alt_element, _, _ = self.generate_c1not2('c1not2', tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                             f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                             kwargs_dict=kwargs_dict, read_phase_deg=read_phase_deg+180,
                             dd_type=dd_type, dd_order=dd_order, alternating=False, no_laser=no_laser)
        c1not2_alt_element = c1not2_alt_element[0]
        c2not1_element, _, _ = self.generate_c2not1('c2not1', tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                             f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                             kwargs_dict=kwargs_dict, read_phase_deg=read_phase_deg,
                             dd_type=dd_type, dd_order=dd_order, alternating=False, no_laser=no_laser)
        c2not1_element = c2not1_element[0]
        c2not1_alt_element, _, _ = self.generate_c2not1('c2not1', tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                             f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                             kwargs_dict=kwargs_dict, read_phase_deg=read_phase_deg+180,
                             dd_type=dd_type, dd_order=dd_order, alternating=False, no_laser=no_laser)
        c2not1_alt_element = c2not1_alt_element[0]

        pi_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 2,
                                                                    increments=[0, 0],
                                                                    amps=ampls_on_1,
                                                                    freqs=mw_freqs,
                                                                    phases=[0, 0])

        pihalf_y_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_1,
                                                                          freqs=mw_freqs,
                                                                          phases=[90, 90])


        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)
        created_blocks, created_ensembles, created_sequences = [], [], []
        # Hadarmard = 180_X*90_Y*|Psi>
        dd_block.extend(pihalf_y_on1_element)
        dd_block.extend(pi_on1_element)
        if not use_c2not1:
            dd_block.extend(c1not2_element)  # cnot element includes laser for readout
        else:
            dd_block.extend(c2not1_element)

        if alternating:
            dd_block.extend(pihalf_y_on1_element)
            dd_block.extend(pi_on1_element)
            if not use_c2not1:
                dd_block.extend(c1not2_alt_element)  # cnot element includes laser for readout
            else:
                dd_block.extend(c2not1_alt_element)

        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, num_of_points - 1))

        if not no_laser:
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


    def generate_bell_ramsey(self, name='bell_ramsey', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                                 t_rabi_bell=10e-6, f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                                 rabi_period_mw_2="100e-9, 100e-9, 100e-9", assym_disent=False,
                                 dd_type=DDMethods.SE, dd_order=1, alternating=True):
        """
        Use lists of f_mw_2, ampl_mw_2, rabi_period_m2_2 to a) address second NV b) use double quantum transition
        """

        tau_cnot = t_rabi_bell/(4*dd_order*dd_type.suborder)
        bell_blocks, _, _ = self.generate_ent_create_bell_bycnot('ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        alternating=False, no_laser=True,
                                                                        use_c2not1=False)
        disent_blocks, _, _ = self.generate_ent_create_bell_bycnot('dis-ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        alternating=False,
                                                                        use_c2not1=assym_disent)
        disent_alt_blocks, _, _ = self.generate_ent_create_bell_bycnot('dis-ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        alternating=False, read_phase_deg=180,
                                                                        use_c2not1=assym_disent)



        bell_blocks, disent_blocks, disent_alt_blocks = bell_blocks[0], disent_blocks[0], disent_alt_blocks[0]

        tau_start_pspacing = tau_start   # pi pulse not subtracted here!
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
                phases = xphase

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

        # set freq to zero where ampl=0
        n_lines = len(mw_amps[mw_amps != 0])

        lenghts = [length] * n_lines
        phases = [phase] * n_lines
        increments = [increment] * n_lines
        amps = mw_amps[mw_amps != 0]
        fs = mw_freqs[mw_amps != 0]

        assert len(amps) == len(fs)

        return self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                         increments=increments,
                                                         amps=amps,
                                                         freqs=fs,
                                                         phases=phases)

    def get_pi_element(self, xphase, mw_freqs, mw_amps, rabi_periods,
                       pi_x_length=1., no_amps_2_idle=False):
        """
         define a function to create phase shifted pi pulse elements
        :param xphase: phase sift
        :param pi_x_length: multiple of pi pulse. Eg. 0.5 => pi_half pulse
        :param no_amps_2_idle: if True, convert a pulse without any amplitude to waiting/idle. Else silently drop pulse.
        :return:
        """

        if no_amps_2_idle and len(mw_amps[mw_amps!=0])==0:
            # todo: may have unintended consequences in creation of pulse partition
            mw_amps = np.asarray([1e-99]*len(mw_amps))

        n_lines = len(mw_amps[mw_amps!=0])

        lenghts = (pi_x_length * rabi_periods / 2)[mw_amps !=0]
        phases = [float(xphase)] * n_lines
        amps = mw_amps[mw_amps !=0]
        fs = mw_freqs[mw_amps !=0]

        assert len(fs) == len(amps) == len(phases) == len(lenghts)

        return self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                         increments=0,
                                                         amps=amps,
                                                         freqs=fs,
                                                         phases=phases)

    @staticmethod
    def get_element_length(el_list):
        """
        Easily calculate length, if pulse elements contain more than one block.
        (Eg. pulse created by _get_multiple_mw_mult_length_element)
        :param el_list:
        :return:
        """

        if not isinstance(el_list, list):
            el_list = [el_list]

        incrs = np.sum([el.increment_s for el in el_list])
        if incrs != 0:
            # not saying it's not possible, but not for all cases
            raise ValueError("Can't yield a unique length if increment != 0.")

        return np.sum([el.init_length_s for el in el_list])

    @staticmethod
    def get_element_length_max(el_list, n_tau=1):

        # todo: mary with get_element_length
        if not isinstance(el_list, list):
            el_list = [el_list]

        len_no_incr = np.sum([el.init_length_s for el in el_list])
        incrs = (n_tau-1) * np.sum([el.increment_s for el in el_list])

        return len_no_incr + incrs

    def _get_multiple_mw_mult_length_element(self, lengths, increments, amps=None, freqs=None, phases=None):
        """
        Creates single, double sine mw element.

        :param float lengths: MW pulse duration in seconds
        :param float increments: MW pulse duration increment in seconds
        :param amps: list containing the amplitudes
        :param freqs: list containing the frequencies
        :param phases: list containing the phases
        :return: list of PulseBlockElement, the generated MW element
        """

        if isinstance(lengths, (int, float)):
            lengths = [lengths]
        if isinstance(increments, (int, float)):
            if increments == 0:
                n_lines = len(lengths)
                increments = [increments]*n_lines

        if isinstance(amps, (int, float)):
            amps = [amps]
        if isinstance(freqs, (int, float)):
            freqs = [freqs]
        if isinstance(phases, (int, float)):
            phases = [phases]

        if len(np.unique(increments)) > 1:
            raise NotImplementedError("Currently, can only create multi mw elements with equal increments.")
        if len(np.unique([len(ar) for ar in [lengths, increments, amps, freqs, phases]])) > 1:
            raise ValueError("Parameters must be arrays of same length.")

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
                chs_part = np.zeros((n_ch))

                t_so_far = np.sum([p[0] for p in partition_blocks])
                lenght_part = length_amps[idx_part][0] - t_so_far

                for idx_ch in range(0, n_ch):
                    ch = length_amps[idx_ch][2]
                    chs_part[idx_ch] = ch
                    if idx_part <= idx_ch:
                        amp_i = amps[ch]
                        amps_part[idx_ch] = amp_i

                # restore original ch order (instead of sorted by length)
                amps_part = np.asarray([amp for amp, _ in sorted(zip(amps_part, chs_part), key=lambda x:x[1])])

                if lenght_part > 0:
                    partition_blocks.append([lenght_part, amps_part])

            return partition_blocks

        def sanitize_lengths(lengths, increments):

            # pulse partition eliminates pulse blocks of zero length
            # this is unwanted, if an increment should be applied to a pulse
            if len(lengths) != 0:
                for idx, len_i in enumerate(lengths):
                    if len_i==0. and increments[idx] != 0.:
                        lengths[idx] = 1e-15

        def nan_phase_2_zero_ampl(phases, amps):
            # pulses with phases marked as nan will be set to zero amplitude
            for idx, phi in enumerate(phases):
                if np.isnan(phi):
                    amps[idx] = 0

        nan_phase_2_zero_ampl(phases, amps)
        sanitize_lengths(lengths, increments)

        part_blocks = create_pulse_partition(lengths, amps)
        #debug_1 = create_pulse_partition([100, 10, 10], [0.1, 0.2, 0.3])
        #debug_2 = create_pulse_partition([10, 100, 80], [0.1, 0.2, 0.3])
        #debug_3 = create_pulse_partition([10, 80, 100], [0.1, 0.1, 0.1])
        blocks = []

        for idx, block in enumerate(part_blocks):

            increment = increments[0] if idx == 0 else 0
            amps = block[1]
            length = block[0]

            blocks.append(self._get_multiple_mw_element(length, increment, amps,
                                                        freqs=freqs, phases=phases))

        return blocks

    @staticmethod
    def _create_param_array(in_value, in_list, n_nvs=None, idx_nv=None, order_nvs=None):
        """
        Generate params list that can be supplied to self.get_pi_element() in order
        to generate pulses on all or a single specified NV.
        To this end, other components of the param array will be set to 0.
        Automatically handles if driving a single NV includes mw on multiple transitions.
        By definition order is eg. [f1_nv1, f2_nv1, f1_nv2, f2_nv2, ,...]
        :param in_value:
        :param in_list:
        :param n_nvs:
        :param idx_nv:
        :return:
        """
        def sublists(inlist, n):
            """
            Divides a list/np.array into sublists of len n.
            """
            return [inlist[i:i+int(n)] for i in range(0,len(inlist),int(n))]

        array = [in_value]
        array.extend(in_list)
        all_nv_params = np.asarray(array)

        # re-order paraams, if nv order != [1,2, ...]
        if order_nvs != None:
            order_nvs = csv_2_list(order_nvs)
            parama_per_nv = sublists(all_nv_params, int(len(all_nv_params)/n_nvs))
            parama_per_nv = [p for p, i in sorted(zip(parama_per_nv, order_nvs), key=lambda tup: tup[1])]
            all_nv_params = [item for sublist in parama_per_nv for item in sublist] # flatten per nv list again


        # pick a single NV and set all others to zero ampl
        if n_nvs != None and idx_nv != None:
            if idx_nv >= n_nvs:
                raise ValueError(f"Index of NV {idx_nv} outside range 0..{n_nvs-1}")
            else:
                len_single_nv = int(len(all_nv_params)/n_nvs)
                i_start = idx_nv*len_single_nv
                i_end = i_start + len_single_nv
                single_nv_params = np.zeros((len(all_nv_params)))
                single_nv_params[i_start:i_end] = all_nv_params[i_start:i_end]

            nv_params = single_nv_params
        else:
            nv_params = all_nv_params

        return np.asarray(nv_params)

