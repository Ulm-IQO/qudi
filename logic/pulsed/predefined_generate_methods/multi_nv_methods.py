import numpy as np
import copy as cp
from enum import Enum, IntEnum
import os

from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from logic.pulsed.sampling_functions import SamplingFunctions, DDMethods
#from logic.pulsed.sampling_function_defs.sampling_functions_nvision import EnvelopeMethods
from logic.pulsed.pulse_objects import PulseEnvelopeType as Evm
from logic.pulsed.pulse_objects import PulseCompositeType as Comp
from core.util.helpers import csv_2_list
from user_scripts.Timo.own.console_toolkit import Tk_file, Tk_string


class DQTAltModes(IntEnum):
    DQT_12_alternating = 1
    DQT_both = 2


class TomoRotations(IntEnum):
    none = 0
    ux90_on_1 = 1
    ux90_on_2 = 2
    uy90_on_1 = 3
    uy90_on_2 = 4
    ux45_on_2 = 5
    ux45min_on_2 = 6
    ux90min_on_1 = 7
    ux90min_on_2 = 8
    uy90min_on_1 = 9
    uy90min_on_2 = 10

    ux180_on_1 = 11
    ux180_on_2 = 12
    uy180_on_1 = 13
    uy180_on_2 = 14
    ux180min_on_1 = 15
    ux180min_on_2 = 16
    uy180min_on_1 = 17
    uy180min_on_2 = 18
    c1not2 = 19
    c2not1 = 20
    c1not2_ux180_on_2 = 21
    c2not1_ux180_on_1 = 22
    c2phase1_dd = 23

    ux90_on_both = 24
    uy90_on_both = 25
    ux90min_on_both = 26
    uy90min_on_both = 27
    ux180_on_both = 28
    uy180_on_both = 29
    ux180min_on_both = 30
    uy180min_on_both = 31

    def __init__(self, *args):
        super().__init__()

        self._native_gate_translation = {
            'ux45min_on_2': {'pulse_area': np.pi / 4, 'phase': 180, 'target': [2]},
            'ux90_on_1': {'pulse_area': np.pi / 2, 'phase': 0, 'target': [1]},
            'ux90_on_2': {'pulse_area': np.pi / 2, 'phase': 0, 'target': [2]},
            'ux90_on_both': {'pulse_area': np.pi / 2, 'phase': 0, 'target': [1, 2]},
            'uy90_on_1': {'pulse_area': np.pi / 2, 'phase': 90, 'target': [1]},
            'uy90_on_2': {'pulse_area': np.pi / 2, 'phase': 90, 'target': [2]},
            'uy90_on_both': {'pulse_area': np.pi / 2, 'phase': 90, 'target': [1, 2]},
            'ux90min_on_1': {'pulse_area': np.pi / 2, 'phase': 180, 'target': [1]},
            'ux90min_on_2': {'pulse_area': np.pi / 2, 'phase': 180, 'target': [2]},
            'ux90min_on_both': {'pulse_area': np.pi / 2, 'phase': 180, 'target': [1, 2]},
            'uy90min_on_1': {'pulse_area': np.pi / 2, 'phase': 270, 'target': [1]},
            'uy90min_on_2': {'pulse_area': np.pi / 2, 'phase': 270, 'target': [2]},
            'uy90min_on_both': {'pulse_area': np.pi / 2, 'phase': 270, 'target': [1, 2]},
            'ux180_on_1': {'pulse_area': np.pi / 1, 'phase': 0, 'target': [1]},
            'ux180_on_2': {'pulse_area': np.pi / 1, 'phase': 0, 'target': [2]},
            'ux180_on_both': {'pulse_area': np.pi / 1, 'phase': 0, 'target': [1, 2]},
            'uy180_on_1': {'pulse_area': np.pi / 1, 'phase': 90, 'target': [1]},
            'uy180_on_2': {'pulse_area': np.pi / 1, 'phase': 90, 'target': [2]},
            'uy180_on_both': {'pulse_area': np.pi / 1, 'phase': 90, 'target': [1, 2]},
            'ux180min_on_1': {'pulse_area': np.pi / 1, 'phase': 180, 'target': [1]},
            'ux180min_on_2': {'pulse_area': np.pi / 1, 'phase': 180, 'target': [2]},
            'ux180min_on_both': {'pulse_area': np.pi / 1, 'phase': 180, 'target': [1, 2]},
            'uy180min_on_1': {'pulse_area': np.pi / 1, 'phase': 270, 'target': [1]},
            'uy180min_on_2': {'pulse_area': np.pi / 1, 'phase': 270, 'target': [2]},
            'uy180min_on_both': {'pulse_area': np.pi / 1, 'phase': 270, 'target': [1, 2]},
            ###
            'c2phase1_dd': {'pulse_area': np.pi / 2, 'phase': np.nan, 'target': [1, 2]},
        }

    @property
    def pulse_parameters(self):
        return self._native_gate_translation[self.name]


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
    cphase_none = 14
    cphase_ux180_on_1 = 15
    cphase_ux180_on_2 = 16
    cphase_ux180_on_both = 17
    cphase_hadamad_1 = 18
    cphase_hadamad_2 = 19
    cphase_hadamd_2_ux180_on_1 = 20


class OptimalControlPulse():
    def __init__(self, on_nv=1, par_with_nvs=None, pi_x=1, file_i=None, file_q=None):
        """
        @param on_nv: int. Specify on which nv pulse is applied
        @param par_with_nvs: None, or [int]. pulse should be run with another parallel pulse on those nvs.
        @param pi_x: pulse length in units of a pi rotation
        @param file_i:
        @param file_q:
        """
        self._on_nv = on_nv
        self._pi_x = pi_x
        self._par_with_nvs = par_with_nvs

        self._file_i = file_i
        self._file_q = file_q

    def equal_target_u(self, other_pulse):
        if self._on_nv==other_pulse._on_nv and self._pi_x == other_pulse._pi_x \
                and self._par_with_nvs==other_pulse._par_with_nvs:
            return True
        return False

    @property
    def file(self):
        """
        If pulse consists out of > 1 file (eg. "p_ampl.txt", "p_ph.txt"),
        reduce to base name "p_".
        :return:
        """

        # without file extension, with folder dir
        fnames = [self._file_i, self._file_q]

        return os.path.commonprefix(fnames)

class MultiNV_Generator(PredefinedGeneratorBase):
    """

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.optimal_control_assets_path = 'C:\Software\qudi_data\optimal_control_assets'
        self._optimal_pulses = []
        self._init_optimal_control()
        self.pulse_envelope = Evm.rectangle


    def _init_optimal_control(self):
        self._optimal_pulses = self.load_optimal_pulses_from_path(self.optimal_control_assets_path)
        # evil setting of private variable
        self._PredefinedGeneratorBase__sequencegeneratorlogic._optimal_pulses = self._optimal_pulses
        self.log.info(f"Loaded optimal pulses from: {[os.path.basename(p._file_i) for p in self._optimal_pulses]}")
        pass

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

    @property
    def optimal_control_assets_path(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['optimal_control_assets_path']
        except KeyError:
            return None

    @optimal_control_assets_path.setter
    def optimal_control_assets_path(self, path):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'optimal_control_assets_path': path})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @property
    def pulse_envelope(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['pulse_envelope']
        except KeyError:
            return None

    @pulse_envelope.setter
    def pulse_envelope(self, envelope):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'pulse_envelope': envelope})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    def oc_params_from_str(self, in_str):

        keys = ['pix', 'on_nv', 'par']

        return Tk_string.params_from_str(in_str, keys=keys)

    def get_oc_pulse(self, on_nv=1, pix=1, par_with_nvs=None):

        ret_pulses = []
        search_pulse = OptimalControlPulse(on_nv=on_nv, pi_x=pix, par_with_nvs=par_with_nvs)

        for pulse in self._optimal_pulses:
            #self.log.debug(
            #    f"Checking pulse1: on={search_pulse._on_nv},pi={search_pulse._pi_x},par={search_pulse._par_with_nvs},"
            #    f"pulse2: on={pulse._on_nv},pi={pulse._pi_x},par={pulse._par_with_nvs} ")
            if pulse.equal_target_u(search_pulse):
                ret_pulses.append(pulse)

        return ret_pulses

    def load_optimal_pulses_from_path(self, path, quadrature_names=['amplitude', 'phase']):

        def find_q_files(i_file, all_files, quadrature_names=['amplitude', 'phase']):
            str_i, str_q = quadrature_names[0], quadrature_names[1]

            file_no_path = os.path.basename(i_file)
            file_no_quad = file_no_path.replace(str_i, "")
            file_no_quad_no_ext = os.path.splitext(file_no_quad)[0]
            file_no_ext = Tk_file.get_filename_no_extension(file_no_path)
            extension = os.path.splitext(file_no_path)[1]
            files_filtered = all_files

            filter_str = [path, file_no_quad_no_ext + quadrature_names[1]]

            self.log.debug(f"Searching q file for {i_file} in {all_files}. Filter: {filter_str}")
            if file_no_ext == str_i:
                # filename exactly = quad_name => filtering against empty string yields all other files
                # instead, we search for the name of the other quadrature
                filter_str.append(str_q + extension)

            for filter in filter_str:
                files_filtered = Tk_string.filter_str(files_filtered, filter, exclStrList=[i_file])
                #self.log.debug(f"Filter {filter}: => {files_filtered}")

            return files_filtered

        fnames = Tk_file.get_dir_items(path, incl_subdir=False)
        str_i = quadrature_names[0]
        loaded_pulses = []

        for file in fnames:

            path = str(Tk_file.get_parent_dir(file)[1])
            file_no_path = os.path.basename(file)

            # for every file which is an i quadrature, look for q quadrature
            if str_i in file_no_path:
                file_i = file
                files_q = find_q_files(file_i, fnames, quadrature_names=quadrature_names)
                if len(files_q) == 1:
                    file_q = files_q[0]
                elif len(files_q) == 0:
                    self.log.warning(
                        f"Found optimal control file {file} for i quadrature, but no corresponding "
                        f"q file. Candidates: {files_q}")
                    continue
                else:
                    self.log.warning(
                        f"Found optimal control file {file} for i quadrature, but multiple corresponding "
                        f"q files. Candidates: {files_q}")
                    continue
            else:
                continue

            oc_params = self.oc_params_from_str(file_i)
            # default to 'pi pulse on nv 1' if params not in filename
            on_nv = oc_params['on_nv'] if 'on_nv' in oc_params.keys() else 1
            par_with_nv = oc_params['par'] if 'par' in oc_params.keys() else None
            # currently, params_from_string only extracts floats, not lists
            par_with_nv = [par_with_nv] if par_with_nv!= None else None
            pix = oc_params['pix'] if 'pix' in oc_params.keys() else 1
            oc_pulse = OptimalControlPulse(on_nv, pi_x=pix, par_with_nvs=par_with_nv,
                                           file_i=file_i, file_q=file_q)
            exist_pulses = self.get_oc_pulse(on_nv, pix=pix, par_with_nvs=par_with_nv)

            if len(exist_pulses) != 0:
                self.log.warning(
                    f"Skipping loaded optimal pulse {file}, because already found {exist_pulses[0]._file_i}"
                    f" with same paremters {oc_params}.")
            else:
                loaded_pulses.append(oc_pulse)

        return loaded_pulses

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

    def generate_tomography_single(self, name='tomography_single_point',
                            rotations="<TomoRotations.none: 0>", init_states="<TomoInit.none: 0>",
                            tau_cnot=0e-9, dd_type_cnot=DDMethods.SE, dd_order=1,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                            alternating=False, pi_on_nv="1,2",
                            init_state_kwargs='', cnot_kwargs=''):
        """
        pulse amplitude/frequency/rabi_period order: [f_nv1, f_dqt_nv1, f_nv2, f_dqt_nv2]
        """
        created_blocks, created_ensembles, created_sequences = list(), list(), list()

        # handle kwargs
        # allow to overwrite generation parameters by kwargs or default to this gen method params
        dd_type_ent = dd_type_cnot if 'dd_type' not in init_state_kwargs else init_state_kwargs['dd_type']
        dd_order_ent = dd_order if 'dd_order' not in init_state_kwargs else init_state_kwargs['dd_order']
        tau_ent = tau_cnot if 'tau_start' not in init_state_kwargs else init_state_kwargs['tau_start']
        rabi_period_mw_2_ent = rabi_period_mw_2 if 'rabi_period_mw_2' not in init_state_kwargs \
            else init_state_kwargs['rabi_period_mw_2']
        init_env_type = Evm.rectangle if 'env_type' not in init_state_kwargs else init_state_kwargs['env_type']
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
        rotations = csv_2_list(rotations, str_2_val=Tk_string.str_2_enum)
        init_states = csv_2_list(init_states, str_2_val=Tk_string.str_2_enum)
        pi_on_nv = csv_2_list(pi_on_nv)

        self.log.debug(f"Tomographic mes, single point  Ampls_both: {amplitudes},"
                       f" ampl_1= {ampls_on_1}, ampl_2= {ampls_on_2}, ampl_2_cnot: {ampl_mw_2_cnot},"
                       f" cnot_kwargs: {cnot_kwargs}")


        # get tau array for measurement ticks
        idx_array = list(range(len(rotations)))
        if alternating:
            # -> rotation, rotation + pi_on1, rotation, rotation + pi_on2
            idx_array = list(range(len(pi_on_nv)*len(rotations)))
        num_of_points = len(idx_array)
        self.log.debug(f"x axis {idx_array}, n_points={ num_of_points}")

        # simple rotations
        pi_on_both_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods)
        pi_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods)
        pi_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods)
        pi_oc_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods, on_nv=1, env_type=Evm.optimal)
        pi_oc_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods, on_nv=2, env_type=Evm.optimal)
        pi_oc_on_both_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods, on_nv=[1,2],
                                                 env_type=Evm.optimal)
        pi2_on_both_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods, pi_x_length=0.5)
        pi2_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods, pi_x_length=0.5)
        pi2_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods, pi_x_length=0.5)
        pi2y_on_1_element = self.get_pi_element(90, mw_freqs, ampls_on_1, rabi_periods, pi_x_length=0.5)
        pi2y_on_2_element = self.get_pi_element(90, mw_freqs, ampls_on_2, rabi_periods, pi_x_length=0.5)

        # 2 qubit gates

        c1not2_element, _, _ = self.generate_c1not2('c1not2', tau_start=tau_cnot, tau_step=0.0e-6, num_of_points=1,
                                                    f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2_cnot,
                                                    rabi_period_mw_2=rabi_period_mw_2_cnot,
                                                    dd_type=dd_type_cnot, dd_order=dd_order, alternating=False,
                                                    no_laser=True,
                                                    kwargs_dict=cnot_kwargs)
        c1not2_element = c1not2_element[0]
        c2not1_element, _, _ = self.generate_c2not1('c2not1', tau_start=tau_cnot, tau_step=0.0e-6, num_of_points=1,
                                                    f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2_cnot,
                                                    rabi_period_mw_2=rabi_period_mw_2_cnot,
                                                    dd_type=dd_type_cnot, dd_order=dd_order, alternating=False,
                                                    no_laser=True,
                                                    kwargs_dict=cnot_kwargs)
        c2not1_element = c2not1_element[0]

        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)

        delay_element = self._get_delay_gate_element()

        if len(rotations) != len(init_states):
            raise ValueError("Unequal length of provided rotations/inits")

        def init_element(init_state):

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
                if init_env_type == Evm.optimal:
                    init_elements = pi_oc_on_1_element
                    self.log.debug(f"Init {init_state.name} with oc pulse")
            elif init_state == TomoInit.ux180_on_2:
                init_elements = pi_on_2_element
                if init_env_type == Evm.optimal:
                    init_elements = pi_oc_on_2_element
                    self.log.debug(f"Init {init_state.name} with oc pulse")
            elif init_state == TomoInit.ux180_on_both:
                # init_elements = pi_on_both_element
                init_elements = cp.deepcopy(pi_on_1_element)
                init_elements.extend(pi_on_2_element)
                if init_env_type == Evm.optimal:
                    init_elements = pi_oc_on_both_element
                    self.log.debug(f"Init {init_state.name} with parallel oc pulse")
            elif init_state == TomoInit.ux90_on_1_uy90_on_2:
                init_elements = cp.deepcopy(pi2_on_1_element)
                init_elements.extend(pi2y_on_2_element)
            elif init_state == TomoInit.ux90_on_1_ux180_on_2:
                init_elements = cp.deepcopy(pi2_on_1_element)
                init_elements.extend(pi_on_2_element)
            else:
                raise ValueError(f"Unknown tomography init state: {init_state.name}")
            return init_elements

        def rotation_element(rotation):

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
                rot_elements = cp.deepcopy(c1not2_element)
                rot_elements.extend(pi_on_2_element)
            elif rotation == TomoRotations.c2not1_ux180_on_1:
                rot_elements = cp.deepcopy(c2not1_element)
                rot_elements.extend(pi_on_1_element)
            else:
                raise ValueError(f"Unknown tomography rotation: {rotation.name}")
            return rot_elements

        rabi_block = PulseBlock(name=name)

        for idx, rotation in enumerate(rotations):
            init_state = init_states[idx]
            # Create block and append to created_blocks list

            pi_end_on = pi_on_nv if alternating else [-1]
            for rabi_on_nv in pi_end_on:
                self.log.debug(f"idx= {idx}, rot= {rotation.name}, init={init_state.name}, pi_on_nv={rabi_on_nv}")
                rabi_block.extend(init_element(init_state))
                rabi_block.extend(rotation_element(rotation))
                rabi_block.append(laser_element)
                rabi_block.append(delay_element)
                rabi_block.append(waiting_element)

                if alternating:
                    pi_read_element = cp.deepcopy(pi_on_1_element) if rabi_on_nv == 1 else cp.deepcopy(pi_on_2_element)
                    rabi_block.extend(init_element(init_state))
                    rabi_block.extend(rotation_element(rotation))
                    rabi_block.extend(pi_read_element)
                    rabi_block.append(laser_element)
                    rabi_block.append(delay_element)
                    rabi_block.append(waiting_element)

        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((rabi_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = idx_array
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('idx', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2*num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

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
        init_env_type = Evm.rectangle if 'env_type' not in init_state_kwargs else \
            init_state_kwargs['env_type']

        # create param arrays
        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), n_nvs=2)
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), n_nvs=2)
        rabi_on_nv = int(rabi_on_nv)
        if type(rotation) != list:
            rotation = [rotation]
        if type(init_state) != list:
            init_state = [init_state]

        self.log.debug(f"Tomographic rabi on {rabi_on_nv}. Ampls_both: {amplitudes},"
                       f" ampl_1= {ampls_on_1}, ampl_2= {ampls_on_2}, ampl_2_cnot: {ampl_mw_2_cnot},"
                       f" cnot_kwargs: {cnot_kwargs}")

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
        #pi_oc_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods, on_nv=1,
        #                                         env_type=Evm.optimal)
        #pi_oc_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods, on_nv=2,
        #                                         env_type=Evm.optimal)

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
        c2phase1_dd_element, _, _ = self.generate_c2phase1_dd('c2phase1_dd', tau_start=tau_cnot, tau_step=0.0e-6, num_of_points=1,
                                                    f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2_cnot,
                                                    rabi_period_mw_2=rabi_period_mw_2_cnot,
                                                    dd_type=dd_type_cnot, dd_order=dd_order, alternating=False,
                                                    no_laser=True,
                                                    kwargs_dict=cnot_kwargs)
        c2phase1_dd_element = c2phase1_dd_element[0]



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

        def init_element(init_state):
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
                if init_env_type == Evm.optimal:
                    init_elements = pi_oc_on_1_element
                    self.log.debug(f"Init {init_state.name} with oc pulse")
            elif init_state == TomoInit.ux180_on_2:
                init_elements = pi_on_2_element
                if init_env_type == Evm.optimal:
                    init_elements = pi_oc_on_2_element
                    self.log.debug(f"Init {init_state.name} with oc pulse")
            elif init_state == TomoInit.ux180_on_both:
                # init_elements = pi_on_both_element
                init_elements = cp.deepcopy(pi_on_1_element)
                init_elements.extend(pi_on_2_element)
                if init_env_type == Evm.optimal:
                    init_elements = cp.deepcopy(pi_oc_on_1_element)
                    init_elements.extend(pi_oc_on_2_element)
                    self.log.debug(f"Init {init_state.name} with sequential oc pulse")
            elif init_state == TomoInit.ux90_on_1_uy90_on_2:
                init_elements = cp.deepcopy(pi2_on_1_element)
                init_elements.extend(pi2y_on_2_element)
            elif init_state == TomoInit.ux90_on_1_ux180_on_2:
                init_elements = cp.deepcopy(pi2_on_1_element)
                init_elements.extend(pi_on_2_element)
            else:
                raise ValueError(f"Unknown tomography init state: {init_state.name}")
            return init_elements

        def rotation_element(rotation):
            if rotation == TomoRotations.none:
                rot_elements = []
            elif rotation == TomoRotations.c1not2:
                rot_elements = c1not2_element
            elif rotation == TomoRotations.c2phase1_dd:
                rot_elements = c2phase1_dd_element
            elif rotation == TomoRotations.c2not1:
                rot_elements = c2not1_element
            elif rotation == TomoRotations.ux180_on_1:
                rot_elements = pi_on_1_element
            elif rotation == TomoRotations.ux180_on_2:
                rot_elements = pi_on_2_element
            elif rotation == TomoRotations.c1not2_ux180_on_2:
                rot_elements = cp.deepcopy(c1not2_element)
                rot_elements.extend(pi_on_2_element)
            elif rotation == TomoRotations.c2not1_ux180_on_1:
                rot_elements = cp.deepcopy(c2not1_element)
                rot_elements.extend(pi_on_1_element)
            else:
                raise ValueError(f"Unknown tomography rotation: {rotation.name}")
            return rot_elements


        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        for init in init_state:
            rabi_block.extend(init_element(init))
        for rot in rotation:
            rabi_block.extend(rotation_element(rot))
        rabi_block.extend(mw_rabi_element)
        rabi_block.append(laser_element)
        rabi_block.append(delay_element)
        rabi_block.append(waiting_element)

        if alternating:
            for init in init_state:
                rabi_block.extend(init_element(init))
            for rot in rotation:
                rabi_block.extend(rotation_element(rot))
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


    def generate_rand_benchmark(self, name='random_benchmark', xticks='',
                            rotations="[[<TomoRotations.none: 0>,];]", read_rots="",
                            tau_cnot=0e-9, dd_type_cnot=DDMethods.SE, dd_order=1, t_idle=0e-9,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", ampl_idle_mult=0., rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                            comp_type=Comp.from_gen_settings,
                            mirror_1q_pulses=False, alternating=False,
                            init_state_kwargs='', cnot_kwargs='', add_gate_ch=''):
        """
        :param rotations: list of list. Each element is a list of gates (given as TomoRotations) and will yield
                                        a single data point.
        pulse amplitude/frequency/rabi_period order: [f_nv1, f_dqt_nv1, f_nv2, f_dqt_nv2]
        """

        def pi_element_function(xphase, on_nv=1, pi_x_length=1., no_amps_2_idle=True, comp_type_pi=None):

            if type(on_nv) != list:
                on_nv = [on_nv]

            if comp_type_pi is None:
                comp_type_pi = comp_type

            # ampls_on_1/2 take care of nv_order already
            if on_nv == [1]:
                ampl_pi = ampls_on_1
                mw_idle_amps = ampls_on_2 * ampl_idle_mult
            elif on_nv == [2]:
                ampl_pi = ampls_on_2
                mw_idle_amps = ampls_on_2 * ampl_idle_mult
            elif set(on_nv) == set([1,2]):
                ampl_pi = amplitudes
                mw_idle_amps = None
            else:
                raise ValueError

            if comp_type_pi == Comp.bb1_cp2 or comp_type_pi == Comp.mw_dd or comp_type_pi == Comp.mw_ddxdd:
                # for composite pulses that act on both NVs
                ampl_pi = amplitudes

            return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                       pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle,
                                       comp_type=comp_type_pi, on_nv=on_nv, mw_idle_amps=mw_idle_amps)

        def rotation_element(rotation):
            # atm, supported (native) gate set is only:
            gate_set = [TomoRotations.ux45_on_2, TomoRotations.ux45min_on_2,
                        TomoRotations.ux90_on_1, TomoRotations.ux90_on_2,
                        TomoRotations.uy90_on_1, TomoRotations.uy90_on_2,
                        TomoRotations.ux90min_on_1, TomoRotations.ux90min_on_2,
                        TomoRotations.uy90min_on_1, TomoRotations.uy90min_on_2,
                        TomoRotations.ux180_on_1, TomoRotations.ux180_on_2,
                        TomoRotations.uy180_on_1, TomoRotations.uy180_on_2,
                        TomoRotations.ux180min_on_1, TomoRotations.ux180min_on_2,
                        TomoRotations.uy180min_on_1, TomoRotations.uy180min_on_2,
                        TomoRotations.c2not1, TomoRotations.c2phase1_dd,
                        TomoRotations.none]
            if rotation not in gate_set:
                raise ValueError(
                    f"Found rotation {rotation.name}, type {type(rotation)} which is not in native gate set {gate_set}")

            if rotation == TomoRotations.none:
                rot_elements = []
            elif rotation not in [TomoRotations.c2not1, TomoRotations.c2phase1_dd]:
                params = rotation.pulse_parameters
                if mirror_1q_pulses:
                    params['target'] = [1, 2]
                rot_elements = pi_element_function(params['phase'], pi_x_length=params['pulse_area']/np.pi,
                                                   on_nv=params['target'])
            elif rotation == TomoRotations.c2not1:
                rot_elements = c2not1_element
                if mirror_1q_pulses:
                    raise ValueError("Can't mirror c2not1 to other qubit.")
            elif rotation == TomoRotations.c2phase1_dd:
                rot_elements = c2phase1_dd_element
                if mirror_1q_pulses:
                    raise NotImplementedError
            else:
                raise ValueError(f"Unknown random benchmarking rotation: {rotation.name}")

            return rot_elements

        created_blocks, created_ensembles, created_sequences = list(), list(), list()

        # handle kwargs
        # allow to overwrite generation parameters by kwargs or default to this gen method params
        dd_type_ent = dd_type_cnot if 'dd_type' not in init_state_kwargs else init_state_kwargs['dd_type']
        dd_order_ent = dd_order if 'dd_order' not in init_state_kwargs else init_state_kwargs['dd_order']
        tau_ent = tau_cnot if 'tau_start' not in init_state_kwargs else init_state_kwargs['tau_start']
        rabi_period_mw_2_ent = rabi_period_mw_2 if 'rabi_period_mw_2' not in init_state_kwargs \
            else init_state_kwargs['rabi_period_mw_2']
        init_env_type = Evm.rectangle if 'env_type' not in init_state_kwargs else init_state_kwargs['env_type']
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

        str_lists = csv_2_list(rotations, str_2_val=str, delimiter=';')  # to list of csv strings
        rotations = [csv_2_list(el, str_2_val=Tk_string.str_2_enum) for el in str_lists]
        read_rots = csv_2_list(read_rots, str_2_val=Tk_string.str_2_enum)

        self.log.debug(f"Rb mes point  Ampls_both: {amplitudes},"
                       f" ampl_1= {ampls_on_1}, ampl_2= {ampls_on_2}, ampl_2_cnot: {ampl_mw_2_cnot},"
                       f" cnot_kwargs: {cnot_kwargs}, read rots {read_rots}")
        if mirror_1q_pulses:
            if len(np.unique(rabi_periods)) != 1:
                self.log.warning(f"Mirroring with non unique rabi_periods: {rabi_periods} will cause idle times.")

        # get tau array for measurement ticks
        idx_array = list(range(len(rotations)))
        xticks = csv_2_list(xticks)
        if xticks:
            # expand xaxis. Multiple random sequences for a single n_cliff are collapsed to same tick
            if len(xticks) < len(idx_array):
                xticks = np.asarray([[x]*int(len(rotations)/len(xticks)) for x in xticks]).flatten()
        num_of_points = len(idx_array)

        # simple rotations
        id_element = self._get_idle_element(t_idle, 0)
        pi_on_1_element = pi_element_function(0, on_nv=1, comp_type_pi=Comp.bare)
        pi_on_2_element = pi_element_function(0, on_nv=2, comp_type_pi=Comp.bare)

        # todo: optimal control not supported atm
        #pi_oc_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods, on_nv=1, env_type=Evm.optimal)
        #pi_oc_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods, on_nv=2, env_type=Evm.optimal)
        #pi_oc_on_both_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods, on_nv=[1,2],
        #                                         env_type=Evm.optimal)


        # 2 qubit gates
        c2not1_element, _, _ = self.generate_c2not1('c2not1', tau_start=tau_cnot, tau_step=0.0e-6, num_of_points=1,
                                                    f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2_cnot,
                                                    rabi_period_mw_2=rabi_period_mw_2_cnot,
                                                    dd_type=dd_type_cnot, dd_order=dd_order, alternating=False,
                                                    no_laser=True,
                                                    kwargs_dict=cnot_kwargs)
        c2not1_element = c2not1_element[0]
        c2phase1_dd_element, _, _ = self.generate_c2phase1_dd('c2phase1_dd', tau_start=tau_cnot, tau_step=0.0e-6, num_of_points=1,
                                                    f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2_cnot,
                                                    rabi_period_mw_2=rabi_period_mw_2_cnot,
                                                    dd_type=dd_type_cnot, dd_order=dd_order, alternating=False,
                                                    no_laser=True,
                                                    kwargs_dict=cnot_kwargs)
        c2phase1_dd_element = c2phase1_dd_element[0]

        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0,
                                                     add_gate_ch=add_gate_ch)
        delay_element = self._get_delay_gate_element(add_gate_ch=add_gate_ch)

        rabi_block = PulseBlock(name=name)

        for idx, gate_list in enumerate(rotations):
            # Create block and append to created_blocks list
            #self.log.debug(f"New rb data point. Gate list: {gate_list}")
            for rotation in gate_list:
                #self.log.debug(f"Adding rot {rotation} of type {type(rotation)}")
                rabi_block.extend(rotation_element(rotation))
                rabi_block.append(id_element)
            for rotation in read_rots:
                rabi_block.extend(rotation_element(rotation))

            rabi_block.append(laser_element)
            rabi_block.append(delay_element)
            rabi_block.append(waiting_element)

            if alternating:

                for rotation in gate_list:
                    rabi_block.extend(rotation_element(rotation))
                    rabi_block.append(id_element)
                # we measure ground state population |00>, so alternating against |11>
                for rotation in read_rots:
                    rabi_block.extend(rotation_element(rotation))

                rabi_block.extend(pi_on_1_element)
                rabi_block.extend(pi_on_2_element)
                rabi_block.append(laser_element)
                rabi_block.append(delay_element)
                rabi_block.append(waiting_element)

        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((rabi_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = idx_array if xticks==[] else xticks
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('idx', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2*num_of_points if alternating else num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_c2phase1_dd(self, name='c2phase1_dd', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                            rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                            dd_type=DDMethods.SE, dd_order=1,
                            read_phase_deg=0, order_nvs="1,2",
                            alternating=False, no_laser=True,
                            # arguments passed to generate methods
                            kwargs_dict=''):

        read_phase = 90 + read_phase_deg   # 90° to deer realizes cnot, additional phase by parameter

        env_type = Evm.from_gen_settings if 'env_type' not in kwargs_dict else kwargs_dict['env_type']
        env_type = self._get_envelope_settings(env_type)
        #order_p = 1 if 'order_P' not in kwargs_dict else kwargs_dict['order_P']
        tau_dd_fix = None if 'tau_dd_fix' not in kwargs_dict else kwargs_dict['tau_dd_fix']
        rabi_period_1 = self.rabi_period if 'rabi_period' not in kwargs_dict else kwargs_dict['rabi_period']
        dd_type_2 = None if 'dd_type_2' not in kwargs_dict else kwargs_dict['dd_type_2']

        if num_of_points==1:
            self.log.debug(f"Generating single cphase (nv_order: {order_nvs}) "
                           f"with tau_1: {tau_dd_fix}, tau_2: {tau_start}, "
                           f"t_rabi_1_shaped: {rabi_period_1}. Envelope: {env_type}")

        if tau_dd_fix is not None:
            return self.generate_deer_dd_tau(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                                             tau1=tau_dd_fix,
                                             f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                                             dd_type=dd_type, dd_type_2=dd_type_2, dd_order=dd_order,
                                             alternating=alternating, no_laser=no_laser,
                                             nv_order=order_nvs,
                                             init_pix_on_1=0, end_pix_on_1=0,
                                             start_pix_on_1=0, end_pix_on_2=1,
                                             env_type_1=env_type, env_type_2=env_type,
                                             read_phase_deg=read_phase)
        else:
            self.log.warning("Untested code!")
            return self.generate_deer_dd_par_tau(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                                 f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                                 dd_type=dd_type, dd_order=dd_order, alternating=alternating, no_laser=no_laser,
                                 nv_order=order_nvs,
                                 init_pix_on_1=0, init_pix_on_2=0, end_pix_on_2=0, end_pix_on_1=0,
                                 read_phase_deg=read_phase)

        """
        DEPRECATED nvision code
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
        """


    def generate_c2not1(self, name='c2not1', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                            rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                            dd_type=DDMethods.SE, dd_order=1,
                            read_phase_deg=0, order_nvs="1,2",
                            alternating=False, no_laser=True,
                            # arguments passed to generate methods
                            kwargs_dict=''):

        read_phase = 90 + read_phase_deg   # 90° to deer realizes cnot, additional phase by parameter

        env_type = Evm.from_gen_settings if 'env_type' not in kwargs_dict else kwargs_dict['env_type']
        env_type = self._get_envelope_settings(env_type)
        #order_p = 1 if 'order_P' not in kwargs_dict else kwargs_dict['order_P']
        tau_dd_fix = None if 'tau_dd_fix' not in kwargs_dict else kwargs_dict['tau_dd_fix']
        rabi_period_1 = self.rabi_period if 'rabi_period' not in kwargs_dict else kwargs_dict['rabi_period']
        dd_type_2 = None if 'dd_type_2' not in kwargs_dict else kwargs_dict['dd_type_2']

        if num_of_points==1:
            self.log.debug(f"Generating single c2not1 (nv_order: {order_nvs}) "
                           f"with tau_1: {tau_dd_fix}, tau_2: {tau_start}, "
                           f"t_rabi_1_shaped: {rabi_period_1}. Envelope: {env_type}")

        if tau_dd_fix is not None:
            return self.generate_deer_dd_tau(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                                             tau1=tau_dd_fix,
                                             f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                                             dd_type=dd_type, dd_type_2=dd_type_2, dd_order=dd_order,
                                             alternating=alternating, no_laser=no_laser,
                                             nv_order=order_nvs, end_pix_on_2=1, env_type_1=env_type, env_type_2=env_type,
                                             read_phase_deg=read_phase)
        else:
            return self.generate_deer_dd_par_tau(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                                 f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                                 dd_type=dd_type, dd_order=dd_order, alternating=alternating, no_laser=no_laser,
                                 nv_order=order_nvs, end_pix_on_2=1,
                                 read_phase_deg=read_phase)

        """
        DEPRECATED nvision code
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
        """

    def generate_c1not2(self, name='c1not2', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                        f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                        rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                        dd_type=DDMethods.SE, dd_order=1,
                        read_phase_deg=0,
                        alternating=False, no_laser=True,
                        # arguments passed to deer method
                        kwargs_dict=''):

        # just change order of nvs to swap control and target qubit
        order_nvs = "2,1"

        return self.generate_c2not1(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                            f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                            rabi_period_mw_2=rabi_period_mw_2,
                            dd_type=dd_type, dd_order=dd_order,
                            read_phase_deg=read_phase_deg, order_nvs=order_nvs,
                            alternating=alternating, no_laser=no_laser,
                            # arguments passed to deer method
                            kwargs_dict=kwargs_dict)


    def generate_c2phase1(self, name='c2phase1',init_state=TomoInit.none ,tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                        f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                        rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                        dd_type=DDMethods.SE, dd_order=1,
                        read_phase_deg=90,nv_order="1,2",
                        alternating=False, no_laser=True,
                        # arguments passed to deer method
                        kwargs_dict=''):
        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), order_nvs=nv_order,
                                                n_nvs=2)

        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), order_nvs=nv_order,
                                              n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2,
                                              order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2,
                                              order_nvs=nv_order)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), order_nvs=nv_order, n_nvs=2)

        # Creation of cphase Gate from cnot with Hadamard on NV1
        c2not1_element, _, _ = self.generate_c2not1(name=name, tau_start=tau_start, tau_step=tau_step,
                                                    num_of_points=num_of_points,
                                                    f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                    rabi_period_mw_2=rabi_period_mw_2,
                                                    dd_type=dd_type, dd_order=dd_order,
                                                    read_phase_deg=read_phase_deg, order_nvs=nv_order,
                                                    alternating=alternating, no_laser=no_laser,
                                                    # arguments passed to deer method
                                                    kwargs_dict=kwargs_dict)
        c2not1_element = c2not1_element[0]

        pihalf_y_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_1,
                                                                         freqs=mw_freqs,
                                                                         phases=[90, 90])

        pihalf_y_on2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_2,
                                                                         freqs=mw_freqs,
                                                                         phases=[90, 90])



        pi_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 2,
                                                                   increments=[0, 0],
                                                                   amps=ampls_on_1,
                                                                   freqs=mw_freqs,
                                                                   phases=[0, 0])

        pi_on_2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 2,
                                                                    increments=[0, 0],
                                                                    amps=ampls_on_2,
                                                                    freqs=mw_freqs,
                                                                    phases=[0, 0])

        # If the optimum controlled pulses are needed ToDo: For later use implementation of optimal controlled pulses
        # pi_oc_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods, on_nv=1, env_type=Evm.optimal)
        #pi_oc_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods, on_nv=2, env_type=Evm.optimal)
        #pi_oc_on_both_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods, on_nv=[1, 2],
                                                #    env_type=Evm.optimal)

        def init_element(init_state):

            if init_state == TomoInit.none:
                init_elements = []
            elif init_state == TomoInit.ux180_on_1:
                init_elements = pi_on_1_element
                #if init_env_type == Evm.optimal:
                 #   init_elements = pi_oc_on_1_element
                  #  self.log.debug(f"Init {init_state.name} with oc pulse")
            elif init_state == TomoInit.ux180_on_2:
                init_elements = pi_on_2_element
                #if init_env_type == Evm.optimal:
                 #   init_elements = pi_oc_on_2_element
                  #  self.log.debug(f"Init {init_state.name} with oc pulse")
            elif init_state == TomoInit.ux180_on_both:
                # init_elements = pi_on_both_element
                init_elements = cp.deepcopy(pi_on_1_element)
                init_elements.extend(pi_on_2_element)
                #if init_env_type == Evm.optimal:
                 #   init_elements = pi_oc_on_both_element
                  #  self.log.debug(f"Init {init_state.name} with parallel oc pulse")
            elif init_state == TomoInit.ux90_on_1_uy90_on_2:
                init_elements = cp.deepcopy(pi2_on_1_element)
                init_elements.extend(pi2y_on_2_element)
            elif init_state == TomoInit.ux90_on_1_ux180_on_2:
                init_elements = cp.deepcopy(pi2_on_1_element)
                init_elements.extend(pi_on_2_element)
            else:
                raise ValueError(f"Unknown tomography init state: {init_state.name}")
            return init_elements


        def had_element(onNV = []):
            hadarmad_block = []
            if onNV == [1]:
                hadarmad_block.extend(pihalf_y_on1_element)
                hadarmad_block.extend(pi_on1_element)
            elif onNV ==[2]:
                hadarmad_block.extend(pihalf_y_on2_element)
                hadarmad_block.extend(pi_on2_element)
            else:
                raise ValueError(f"Wrong type of Input: {onNV}")

            return hadarmad_block

        hadamard_on1_element = had_element([1])


        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        cphase_block = PulseBlock(name=name)
        cphase_block.extend(init_element(init_state))
        cphase_block.extend(hadamard_on1_element)
        cphase_block.extend(c2not1_element)
        cphase_block.extend(hadamard_on1_element)
        if not no_laser:
            cphase_block.append(laser_element)
            cphase_block.append(delay_element)
            cphase_block.append(waiting_element)

        if alternating:
            cphase_block.extend(init_element(init_state))
            cphase_block.extend(hadamard_on1_element)
            cphase_block.extend(c2not1_element)
            cphase_block.extend(hadamard_on1_element)
            cphase_block.extend(pi_on_1_element)
            cphase_block.extend(pi_on_2_element)
            if not no_laser:
                cphase_block.append(laser_element)
                cphase_block.append(delay_element)
                cphase_block.append(waiting_element)




        created_blocks.append(cphase_block)

        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((cphase_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        if not no_laser:
            self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array * dd_order * dd_type.suborder
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('t', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences



    # Verification of the cphase
    def generate_cphase_verif(self, name='cphase_verif',verif_gate=TomoRotations.none,init_state= TomoInit.none,
                              tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                        f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                        rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                        dd_type=DDMethods.SE, dd_order=1,
                        read_phase_deg=0,nv_order="1,2",
                        alternating=False, no_laser=True,
                        # arguments passed to deer method
                        kwargs_dict=''):
        # Variable verif_gate: Any Unitary Gate U to verify if it's diagonal
        # Variable init_state: Initial state |00> prepared with the operators from the Protocoll. A list of preparations



        def init_element(init_state,verif_gate): # Prepare of init states for cphase gate with a gate to verifiy

            # verif_gate: gate to experimentally verify, if it's a cphase gate
            if verif_gate == TomoRotations.cphase:
                verif_element = cphase_element
            elif verif_gate == TomoRotations.none:
                verif_element = []
            else:
                ValueError(f"Unknown gate for Verification: {verif_gate.name}.")

            if init_state == TomoInit.cphase_none:
                # Operators: U
                init_elements = []
                init_elements.extend(verif_element)
                self.log.debug(f"Init state for cphase {init_state.name}")
            elif init_state == TomoInit.cphase_ux180_on_1:
                #Operators: X1*U*X1
                init_elements = pi_on_1_element
                #if init_env_type == Evm.optimal:
                 #   init_elements = pi_oc_on_1_element
                  #  self.log.debug(f"Init {init_state.name} with oc pulse")
                init_elements.extend(verif_element)
                self.log.debug(f"Init state for cphase {init_state.name}")
            elif init_state == TomoInit.cphase_ux180_on_2:
                # Operators: X2*U'X2
                init_elements = pi_on_2_element
                #if init_env_type == Evm.optimal:
                 #   init_elements = pi_oc_on_2_element
                  #  self.log.debug(f"Init {init_state.name} with oc pulse")
                init_elements.extend(verif_element)
                self.log.debug(f"Init state for cphase {init_state.name}")
            elif init_state == TomoInit.cphase_ux180_on_both:
                # Operators: X1*X2*U*X1*X2
                # init_elements = pi_on_both_element
                init_elements = cp.deepcopy(pi_on_1_element)
                init_elements.extend(pi_on_2_element)
                #if init_env_type == Evm.optimal:
                 #   init_elements = pi_oc_on_both_element
                  #  self.log.debug(f"Init {init_state.name} with parallel oc pulse")
                init_elements.extend(verif_element)
                self.log.debug(f"Init state for cphase {init_state.name}")
            elif init_state == TomoInit.cphase_hadamad_1:
                init_elements = hadamard_on1_element
                init_elements.extend(verif_element)
                init_elements.extend(hadamad_on1_element)
            elif init_state == TomoInit.cphase_hadamad_2:
                init_elements = hadamard_on2_element
                init_elements.extend(verif_element)
                init_elements.extend(hadamad_on2_element)
            elif init_state == TomoInit.cphase_hadamd_2_ux180_on_1:
                init_elements = hadamard_on2_element
                init_elements.extend(pi_oc_on_1_element)
                init_elements.extend(verif_element)
                init_elements.extend(hadamad_on2_element)
                init_elements.extend(pi_oc_on_1_element)
            else:
                raise ValueError(f"Unknown init state for cPhase Verification: {init_state.name}")
            return init_elements


        #def meas_element(init_state,meas_state): #ToDo Possible Use of this function or to erase this
         #   if init_state == TomoInit.cphase_none:
          #      if meas_state == TomoRotations.none:
           #         meas_element = []
            #    elif meas_state == TomoRotations.ux90min_on_both#.ux90_on_both: # --
             #       meas_element = cp.depcopy(pihalf_x_on1_element)#other phase
              #      meas_element.extend(pihalf_x_on2_element) # other phase
               # elif meas_state == TomoRotations.uy90min_on_both:
                #    meas_element = cp.depcopy(pihalf_y_on1_element)
                 #   meas_element.extend(pihalf_y_on2_element) # other element
                #elif meas_state == TomoRotations.uy90min_on_1_ux90min_on_2:
                 #   meas_element = []
                  #  meas_element.extend(pihalf_ymin_on1_element)
                   # meas_element.extend(pihalf_xmin_on2_element)
                #elif meas_state == TomoRotations.ux90min_on_1_uy90min_on_2:
                 #   meas_element = []
                  #  meas_element.extend(pihalf_xmin_on1_element)
                   # meas_element.extend(pihalf_ymin_on2_element)
                #else:
                 #   raise ValueError(f"Unknown state for measurement: {meas_state.name}")
            #elif init_state == TomoInit.cphase_ux180_on_1:
             #   if meas_state == TomoRotations.ux90min_on_1
              #      meas_element = []
               # elif meas_state == TomoInit.TomoRotations.ux90min_on_2:
                #    pass
                #elif meas_state == TomoRotations.uy90min_on_1_ux90min_on_2:
                 #   meas_element = []
                  #  meas_element.extend(pihalf_ymin_on1_element)
                   # meas_element.extend(pihalf_xmin_on2_element)
                #else:
                 #   raise ValueError(f"Unknown state for measurement: {meas_state.name}")
            #elif init_state == TomoInit.cphase_ux180_on_2:
             #   if meas_state == TomoInit.none
              #      meas_element = []
               # elif meas_state == TomoInit.
                #    pass
                #elif meas_state == TomoInit.
                 #   pass
                #elif meas_state == TomoInit.
                 #   pass
                #else:
                 #   raise ValueError(f"Unknown state for measurement: {meas_state.name}")
            #elif init_state == TomoInit.cphase_ux180_on_both:
             #   if meas_state == TomoInit.none
              #      meas_element = []
               # elif meas_state == TomoInit.
                #    pass
                #elif meas_state == TomoInit.
                 #   pass
                #elif meas_state == TomoInit.
                 #   pass
                #else:
                 #   raise ValueError(f"Unknown state for measurement: {meas_state.name}")
            #elif init_state == TomoInit.cphase_hadamad_1:
             #   if meas_state == TomoInit.none
              #      meas_element = []
               # elif meas_state == TomoInit.
                #    pass
                #elif meas_state == TomoInit.
                 #   pass
                #elif meas_state == TomoInit.
                 #   pass
                #else:
                 #   raise ValueError(f"Unknown state for measurement: {meas_state.name}")
            #elif init_state == TomoInit.cphase_hadamad_2:
             #   if meas_state == TomoInit.none
              #      meas_element = []
               # elif meas_state == TomoInit.
                #    pass
                #elif meas_state == TomoInit.
                 #   pass
                #elif meas_state == TomoInit.
                 #   pass
                #else:
                 #   raise ValueError(f"Unknown state for measurement: {meas_state.name}")
            #elif init_state == TomoInit.cphase_hadamd_2_ux180_on_1:
             #   if meas_state == TomoInit.none
              #      meas_element = []
               # elif meas_state == TomoInit.
                #    pass
                #elif meas_state == TomoInit.
                 #   pass
                #elif meas_state == TomoInit.
                 #   pass
                #else:
                 #   raise ValueError(f"Unknown state for measurement: {meas_state.name}")
            #else:
             #   raise ValueError(f"Unknown init state for Measuring: {init_state.name}")

            #return meas_element

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()


        # Create other pulse_elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), order_nvs=nv_order,
                                                n_nvs=2)

        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), order_nvs=nv_order,
                                              n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2,
                                              order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2,
                                              order_nvs=nv_order)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), order_nvs=nv_order, n_nvs=2)


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
        pihalf_y_on2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_2,
                                                                         freqs=mw_freqs,
                                                                         phases=[90, 90])

        pihalf_x_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_1,
                                                                         freqs=mw_freqs,
                                                                         phases=[0, 0])
        pihalf_x_on2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_2,
                                                                         freqs=mw_freqs,
                                                                         phases=[0, 0])

        pihalf_ymin_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_1,
                                                                         freqs=mw_freqs,
                                                                         phases=[270, 270])
        pihalf_ymin_on2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_2,
                                                                         freqs=mw_freqs,
                                                                         phases=[270, 270])

        pihalf_xmin_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_1,
                                                                         freqs=mw_freqs,
                                                                         phases=[180, 180])
        pihalf_xmin_on2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_2,
                                                                         freqs=mw_freqs,
                                                                         phases=[180, 180])

        pi_on2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 2,
                                                                   increments=[0, 0],
                                                                   amps=ampls_on_2,
                                                                   freqs=mw_freqs,
                                                                   phases=[0, 0])

        def had_element(onNV = []):
            hadarmad_block = []
            if onNV == [1]:
                hadarmad_block.extend(pihalf_y_on1_element)
                hadarmad_block.extend(pi_on1_element)
            elif onNV ==[2]:
                hadarmad_block.extend(pihalf_y_on2_element)
                hadarmad_block.extend(pi_on2_element)
            else:
                raise ValueError(f"Wrong type of Input: {onNV}")



            return hadarmad_block

        # ToDo Later for optimized pulse shapes
        #pi_oc_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods, on_nv=1, env_type=Evm.optimal)
        #pi_oc_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods, on_nv=2, env_type=Evm.optimal)
        #pi_oc_on_both_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods, on_nv=[1, 2],
         #                                           env_type=Evm.optimal)

        # Create a cphase eement from C2Not1 Element and Hadarmad Element

        cphase_element,_,_ = self.generate_c2phase1(name=name, tau_start=tau_start, tau_step=tau_step, num_of_points=num_of_points,
                            f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                            rabi_period_mw_2=rabi_period_mw_2,
                            dd_type=dd_type, dd_order=dd_order,
                            read_phase_deg=read_phase_deg, nv_order=nv_order,
                            alternating=alternating, no_laser=no_laser,
                            # arguments passed to deer method
                            kwargs_dict=kwargs_dict)

        hadamard_on1_element =  had_element([1])
        hadamard_on2_element = had_element([2])

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        init_state_block = PulseBlock(name = name)

        # The measurement will be given for 7 inital states

        init_state_list = [init_state]
        for i in range(len(init_state_list)):
            init_state_block.extend(init_element(init_state_list[i], verif_gate))
            #init_state_block.append(meas_element(init_state[i],meas_state)) Todo: Possible Inserting measurement states
            if not no_laser:
                init_state_block.append(laser_element)
                init_state_block.append(waiting_element)
                init_state_block.append(delay_element)

            if alternating:
                init_state_block.append(init_element(init_state_list[i], verif_gate))
                #init_state_block.append(meas_element(init_state[i], meas_state)) Todo: Possible Inserting measurement states
                init_state_block.append(pi_on1_element)
                init_state_block.append(pi_on2_element)
                if not no_laser:
                    init_state_block.append(laser_element)
                    init_state_block.append(waiting_element)
                    init_state_block.append(delay_element)

            created_blocks.append(init_state_block)

        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((init_state_block.name, num_of_points - 1))

        # Create and append sync trigger block if needed
        if not no_laser:
            self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        idx_array = list(range(len(init_state))) # Each number is connected to a initial state

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = idx_array if tau_step == 0.0 else tau_array
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('idx', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_deer_dd_tau_nvision(self, name='DEER_DD_tau', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                        f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                        rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                        dd_type=DDMethods.SE, dd_order=1,
                        env_type=Evm.rectangle, order_P=1, tau_dd_fix=100e-9,
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
                                 init_pix_on_2=0, init_pix_on_1=0.5, end_pix_on_1=0.5, end_pix_on_2=0, nv_order="1,2",
                                 read_phase_deg=90,
                                 env_type=Evm.rectangle, no_laser=False):
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
                                                pi_x_length=init_pix_on_1, no_amps_2_idle=True)
        pix_init_on2_element = self.get_pi_element(0, mw_freqs, mw_amps=ampls_on_2, rabi_periods=rabi_periods,
                                                   pi_x_length=init_pix_on_2, no_amps_2_idle=False)
        pix_end_on2_element = self.get_pi_element(0, mw_freqs, mw_amps=ampls_on_2, rabi_periods=rabi_periods,
                                                   pi_x_length=end_pix_on_2, no_amps_2_idle=False)
        pihalf_on1_read_element = self.get_pi_element(read_phase_deg, mw_freqs, mw_amps=ampls_on_1,
                                                      rabi_periods=rabi_periods,
                                                      pi_x_length=end_pix_on_1, no_amps_2_idle=True)
        pihalf_on1_alt_read_element = self.get_pi_element(180+read_phase_deg,
                                                          mw_freqs, mw_amps=ampls_on_1,
                                                          rabi_periods=rabi_periods,
                                                          pi_x_length=end_pix_on_1, no_amps_2_idle=True)

        def pi_element_function(xphase, on_nv=1, pi_x_length=1., no_amps_2_idle=True):

            if on_nv != [1,2]:
                raise NotImplementedError("Swapping order not supports yet")

            if env_type == Evm.optimal:
                return self.get_pi_element(xphase, mw_freqs, amplitudes, rabi_periods,
                                           pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle,
                                           env_type=env_type, on_nv=on_nv)
            else:
                return self.get_pi_element(xphase, mw_freqs, amplitudes, rabi_periods,
                                       pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle)



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
                dd_block.extend(pi_element_function(dd_type.phases[pulse_number], on_nv=[1,2]))
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
                    dd_block.extend(pi_element_function(dd_type.phases[pulse_number], on_nv=[1,2]))
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
                             dd_type=DDMethods.SE, dd_type_2='', dd_order=1,
                             init_pix_on_1=0, init_pix_on_2=0,
                             start_pix_on_1=0.5, end_pix_on_1=0.5, end_pix_on_2=0, read_pix_on_2=0,
                             nv_order="1,2", read_phase_deg=90,
                             add_gate_ch='d_ch4', env_type_1=Evm.from_gen_settings,
                             env_type_2=Evm.from_gen_settings,
                             scale_tau2_first=1, scale_tau2_last=1, floating_last_pi=True,  # will allow only negative tau2!
                             alternating=True, no_laser=False, incl_ref=False):
        """
        Decoupling sequence on both NVs.
        Tau1 is kept constant and the second pi pulse is swept through.
        """


        adapt_pspacing = False   # take into account init pulse before cphase

        def pi_element_function(xphase, on_nv=1, pi_x_length=1., no_amps_2_idle=True):

            on_nv_oc = on_nv
            if on_nv == '2,1':
                on_nv_oc = 1 if on_nv==2 else 2
                self.log.debug(f"Reversing oc pi_element nv_order: {nv_order}")

            # ampls_on_1/2 take care of nv_order already
            if on_nv == 1:
                ampl_pi = ampls_on_1
                env_type = env_type_1
            elif on_nv == 2:
                ampl_pi = ampls_on_2
                env_type = env_type_2
            else:
                raise ValueError

            return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                       pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle,
                                       env_type=env_type)

        def get_deer_pos(i_dd_order, dd_order, i_dd_suborder, dd_type, before_pi_on1):
            first = (i_dd_order == 0 and i_dd_suborder == 0 and before_pi_on1)
            last = (i_dd_order == dd_order - 1 and i_dd_suborder == dd_type.suborder - 1 and not before_pi_on1)
            in_between = not first and not last

            return first, last, in_between

        def tauhalf_element_function(i_dd_order, dd_order, i_dd_suborder, dd_type, before_pi_on1=False,
                                     floating_last_pi=False, before_pi_on2=False):

            first, last, in_between = get_deer_pos(i_dd_order, dd_order, i_dd_suborder, dd_type, before_pi_on1)

            #self.log.debug(f"Generating tauhal el for i_dd {i_dd_order}, i_dd_sub {i_dd_suborder} "
            #               f"=> first {first}, last {last}, bweteen {in_between}")

            if first and last:
                self.log.warning("Not tested for low order DD. May work, but be careful.")

            if last and floating_last_pi:
                if before_pi_on2:
                    return tauhalf_last_1_float_element
                else:
                    return tauhalf_last_2_float_element

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

            raise ValueError


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

        if dd_type_2 == '' or dd_type_2 is None:
            dd_type_2 = dd_type
        self.log.debug(f"deer_dd with ampl1/2= {ampls_on_1}, {ampls_on_2}, t_rabi: {rabi_periods}, f: {mw_freqs}, "
                       f"envelope= {env_type_1}/{env_type_2}, read pulse phase {read_phase_deg},"
                       f"init=({init_pix_on_1, init_pix_on_2}), start={start_pix_on_1}, end={(end_pix_on_1, end_pix_on_2)}")

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0,
                                                     add_gate_ch=add_gate_ch)
        delay_element = self._get_delay_gate_element(add_gate_ch=add_gate_ch)

        pihalf_start_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                                       pi_x_length=start_pix_on_1)
        # elements inside dd come from their own function
        pi_on1_element = pi_element_function(0, on_nv=1, no_amps_2_idle=False)
        pi_on2_element = pi_element_function(0, on_nv=2, no_amps_2_idle=True)
        pix_init_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                                   pi_x_length=init_pix_on_2, no_amps_2_idle=False,
                                                   env_type=env_type_2, on_nv=2)
        pix_init_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                                   pi_x_length=init_pix_on_1, no_amps_2_idle=False,
                                                   env_type=env_type_1, on_nv=1)

        # read phase opposite to canonical DD: 0->0 on no phase evolution

        pihalf_on1_read_element = self.get_pi_element(0+read_phase_deg, mw_freqs, ampls_on_1, rabi_periods,
                                                      pi_x_length=end_pix_on_1)
        pihalf_on1_alt_read_element = self.get_pi_element(180 + read_phase_deg, mw_freqs, ampls_on_1, rabi_periods,
                                                      pi_x_length=end_pix_on_1)
        pix_on2_read_element = self.get_pi_element(0+read_phase_deg, mw_freqs, ampls_on_2, rabi_periods,
                                                      pi_x_length=read_pix_on_2)
        pix_on2_alt_read_element = self.get_pi_element(180 + read_phase_deg, mw_freqs, ampls_on_2, rabi_periods,
                                                      pi_x_length=read_pix_on_2)

        t_pi_on1 = MultiNV_Generator.get_element_length(pi_on1_element)
        t_pi_on2 = MultiNV_Generator.get_element_length(pi_on2_element)

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        if incl_ref:
            dtau = abs(tau_array[-1] - tau_array[0])
            dtau = -1 if dtau == 0 else dtau
            tau_array = np.concatenate([np.ones(1)*(tau_array[0] - 2*dtau), tau_array], axis=None)

        pix_end_on2_element = self.get_pi_element(dd_type.phases[0], mw_freqs, ampls_on_2,
                                                  rabi_periods,
                                                  pi_x_length=end_pix_on_2, no_amps_2_idle=True,
                                                  env_type=env_type_2, on_nv=2)

        start_tau2_pspacing = self.tau_2_pulse_spacing(tau1,
                                                       custom_func=[lambda t:t-t_pi_on1-t_pi_on2,
                                                                    lambda t:t+t_pi_on1+t_pi_on2])

        if adapt_pspacing:
            self.log.warning("Dangerous to adapt pulse spacing. Depends on init/read pi2 pulses.")
            tauhalf_first_pspacing = self.tau_2_pulse_spacing(tau1/2,
                                                     custom_func=[lambda t: t-t_pi_on1/2-t_pi_on1/4,
                                                                  lambda t: t+t_pi_on1/2+t_pi_on1/4])
            tauhalf_last_pspacing = self.tau_2_pulse_spacing(tau1/2,
                                                     custom_func=[lambda t: t-t_pi_on1/2-t_pi_on1/4,
                                                                  lambda t: t+t_pi_on1/2+t_pi_on1/4])
            if end_pix_on_2 != 0:
                tauhalf_last_pspacing -= MultiNV_Generator.get_element_length(pix_end_on2_element)
        else:
            tauhalf_first_pspacing = self.tau_2_pulse_spacing(tau1/2, custom_func=[lambda t:t-t_pi_on1/2,
                                                                                   lambda t:t+t_pi_on1/2])
            tauhalf_last_pspacing = tauhalf_first_pspacing


        # after pi_on_1
        tauhalf_aft_element = self._get_idle_element(length=start_tau2_pspacing/2+tau_start, increment=tau_step)
        # before pi_on_1
        tauhalf_bef_element = self._get_idle_element(length=start_tau2_pspacing/2-tau_start, increment=-tau_step)
        # first and last tauhalf
        tauhalf_first_element = self._get_idle_element(length=scale_tau2_first*tauhalf_first_pspacing, increment=0)
        tauhalf_last_element =  self._get_idle_element(length=scale_tau2_last*tauhalf_last_pspacing, increment=0)

        tauhalf_last_1_float_element = tauhalf_aft_element
        t_pix_end_on2 = MultiNV_Generator.get_element_length(pix_end_on2_element)
        tauhalf_last_2_float_element = self._get_idle_element(length=tauhalf_last_pspacing-(start_tau2_pspacing/2+tau_start)-t_pix_end_on2, increment=-tau_step)
        self.log.debug(f"Length floating last tau2_1: {start_tau2_pspacing/2+tau_start},"
                       f" tau2_2: {tauhalf_last_pspacing-(start_tau2_pspacing/2+tau_start)-t_pix_end_on2}")
        if floating_last_pi and end_pix_on_2 != 1. and end_pix_on_2 != 0.:
            raise ValueError("Floating last pulse must be a pi pulse.")


        tauhalf_bef_min = MultiNV_Generator.get_element_length_max(tauhalf_bef_element, num_of_points)
        tauhalf_aft_min = MultiNV_Generator.get_element_length_max(tauhalf_aft_element, num_of_points)
        tauhalf_last_2_min = MultiNV_Generator.get_element_length_max(tauhalf_last_2_float_element, num_of_points)
        if tauhalf_bef_min < 0 or tauhalf_aft_min < 0:
            # todo: catch negative pspacing and throw datapoints out, instead of raising
            self.log.debug(f"t_pi1= {t_pi_on1}, t_pi2= {t_pi_on2}, start_tau2_ps= {start_tau2_pspacing},"
                           f"tau_start= {tau_start}, tau_step= {tau_step}, tau1= {tau1}")
            raise ValueError(f"Tau1, tau setting yields negative pulse spacing "
                             f"{np.min([tauhalf_bef_min, tauhalf_aft_min])}."
                             f" Increase tau1 or decrease tau. Check debug for pulse times")
        if (tauhalf_last_2_min < 0 and floating_last_pi):
            raise ValueError(f"Tau1, tau setting yields negative pulse spacing on last tau2 "
                             f"{np.min([tauhalf_last_2_min])}.")


        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)

        if incl_ref:
            if not no_laser:
                dd_block.append(laser_element)
                dd_block.append(delay_element)
                dd_block.append(waiting_element)

        if init_pix_on_1 != 0:
            dd_block.extend(pix_init_on1_element)
        if init_pix_on_2 != 0:
            dd_block.extend(pix_init_on2_element)
        if start_pix_on_1 != 0:
            dd_block.extend(pihalf_start_on1_element)
        for n in range(dd_order):
            # create the DD sequence for a single order
            for pulse_number in range(dd_type.suborder):
                dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, True))
                dd_block.extend(pi_element_function(dd_type.phases[pulse_number], on_nv=1))
                first, last, in_between = get_deer_pos(n, dd_order, pulse_number, dd_type, False)

                if last and not floating_last_pi:
                    dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False))
                    if end_pix_on_2 != 0:
                        pix_end_on2_element = self.get_pi_element(dd_type_2.phases[pulse_number], mw_freqs, ampls_on_2,
                                                                  rabi_periods, env_type=env_type_2, on_nv=2,
                                                                  pi_x_length=end_pix_on_2, no_amps_2_idle=True)
                        dd_block.extend(pix_end_on2_element)
                elif last and floating_last_pi:
                    dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False,
                                                             floating_last_pi=True, before_pi_on2=True))
                    if end_pix_on_2 != 0:
                        pix_end_on2_element = self.get_pi_element(dd_type_2.phases[pulse_number], mw_freqs, ampls_on_2,
                                                                  rabi_periods, env_type=env_type_2, on_nv=2,
                                                                  pi_x_length=end_pix_on_2, no_amps_2_idle=True)
                        dd_block.extend(pix_end_on2_element)
                    dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False,
                                                             floating_last_pi=True, before_pi_on2=False))

                else:
                    dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False))
                    dd_block.extend(pi_element_function(dd_type_2.phases[pulse_number], on_nv=2))

        if end_pix_on_1 != 0:
            dd_block.extend(pihalf_on1_read_element)
        if read_pix_on_2 != 0:
            dd_block.extend(pix_on2_read_element)

        if not no_laser:
            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)

        if alternating:
            if incl_ref:
                dd_block.extend(pi_on1_element)
                dd_block.extend(pi_on2_element)

                if not no_laser:
                    dd_block.append(laser_element)
                    dd_block.append(delay_element)
                    dd_block.append(waiting_element)

            if init_pix_on_1 != 0:
                dd_block.extend(pix_init_on1_element)
            if init_pix_on_2 != 0:
                dd_block.extend(pix_init_on2_element)
            if start_pix_on_1 != 0:
                dd_block.extend(pihalf_start_on1_element)
            for n in range(dd_order):
                # create the DD sequence for a single order
                for pulse_number in range(dd_type.suborder):
                    dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, True))
                    dd_block.extend(pi_element_function(dd_type.phases[pulse_number], on_nv=1))
                    first, last, in_between = get_deer_pos(n, dd_order, pulse_number, dd_type, False)

                    if last and not floating_last_pi:
                        dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False))
                        if end_pix_on_2 != 0:
                            pix_end_on2_element = self.get_pi_element(dd_type_2.phases[pulse_number], mw_freqs, ampls_on_2,
                                                    rabi_periods, env_type=env_type_2, on_nv=2,  pi_x_length=end_pix_on_2, no_amps_2_idle=True)
                            dd_block.extend(pix_end_on2_element)
                    elif last and floating_last_pi:
                        dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False,
                                                     floating_last_pi=True, before_pi_on2=True))
                        if end_pix_on_2 != 0:
                            pix_end_on2_element = self.get_pi_element(dd_type_2.phases[pulse_number],  mw_freqs, ampls_on_2,
                                                        rabi_periods, env_type=env_type_2, on_nv=2, pi_x_length=end_pix_on_2, no_amps_2_idle=True)
                            dd_block.extend(pix_end_on2_element)
                        dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False,
                                                     floating_last_pi=True, before_pi_on2=False))

                    else:
                        dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False))
                        dd_block.extend(pi_element_function(dd_type_2.phases[pulse_number], on_nv=2))

            if end_pix_on_1 != 0:
                dd_block.extend(pihalf_on1_alt_read_element)
            if read_pix_on_2 != 0:
                dd_block.extend(pix_on2_alt_read_element)

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
        if incl_ref:
            number_of_lasers = number_of_lasers + 2 if alternating else number_of_lasers + 1
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

    def generate_deer_dd_tau1(self, name='deer_dd_tau', tau2=0e-9, tau_start=0e-6, tau_step=0.01e-6, num_of_points=50,
                             f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                             dd_type=DDMethods.SE, dd_type_2='', dd_order=1,
                             init_pix_on_1=0, init_pix_on_2=0,
                             start_pix_on_1=0.5, end_pix_on_1=0.5, end_pix_on_2=0,
                             nv_order="1,2", read_phase_deg=90,
                             add_gate_ch='d_ch4', env_type_1=Evm.from_gen_settings,
                             env_type_2=Evm.from_gen_settings,
                             alternating=True, no_laser=False):
        """
        Decoupling sequence on both NVs.
        Tau2 is kept constant and the tau1 is swept.
        """

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        dd_block = PulseBlock(name=name)
        for tau1 in tau_array:
            deer_element, _, _ = self.generate_deer_dd_tau(tau1=tau1, tau_start=tau2, tau_step=0, num_of_points=1,
                                      f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                                      dd_type=dd_type, dd_type_2=dd_type_2, dd_order=dd_order,
                                      init_pix_on_1=init_pix_on_1, init_pix_on_2=init_pix_on_2,
                                      start_pix_on_1=start_pix_on_1, end_pix_on_1=end_pix_on_1,
                                      end_pix_on_2=end_pix_on_2, nv_order=nv_order, read_phase_deg=read_phase_deg,
                                      add_gate_ch=add_gate_ch, env_type_1=env_type_1, env_type_2=env_type_2,
                                      alternating=False, no_laser=no_laser)
            deer_element = deer_element[0]
            dd_block.extend(deer_element)

            if alternating:
                deer_alt_element, _, _ = self.generate_deer_dd_tau(tau1=tau1, tau_start=tau2, tau_step=0, num_of_points=1,
                                          f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                          rabi_period_mw_2=rabi_period_mw_2,
                                          dd_type=dd_type, dd_type_2=dd_type_2, dd_order=dd_order,
                                          init_pix_on_1=init_pix_on_1, init_pix_on_2=init_pix_on_2,
                                          start_pix_on_1=start_pix_on_1, end_pix_on_1=end_pix_on_1,
                                          end_pix_on_2=end_pix_on_2, nv_order=nv_order,
                                          read_phase_deg=read_phase_deg+180,
                                          add_gate_ch=add_gate_ch, env_type_1=env_type_1,
                                          env_type_2=env_type_2,
                                          alternating=False, no_laser=no_laser)
                deer_alt_element = deer_alt_element[0]
                dd_block.extend(deer_alt_element)

        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, 0))

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


    def generate_deer_dd_tau_interm(self, name='deer_dd_tau', tau1=0.5e-6, tau2=0e-6,
                             f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                             dd_type=DDMethods.SE, dd_type_2='', dd_order=1,
                             init_pix_on_1=0, init_pix_on_2=0, end_pix_on_2=0,
                             nv_order="1,2", read_phase_deg=90, env_type_1=Evm.rectangle,
                             env_type_2=Evm.rectangle,
                             alternating=True, no_laser=False):
        """
        Decoupling sequence on both NVs.
        Tau1 is kept constant and the second pi pulse is swept through.
        """

        def pi_element_function(xphase, on_nv=1, pi_x_length=1., no_amps_2_idle=True):

            on_nv_oc = on_nv
            if on_nv == '2,1':
                on_nv_oc = 1 if on_nv==2 else 2
                self.log.debug(f"Reversing oc pi_element nv_order: {nv_order}")

            # ampls_on_1/2 take care of nv_order already
            if on_nv == 1:
                ampl_pi = ampls_on_1
                env_type = env_type_1
            elif on_nv == 2:
                ampl_pi = ampls_on_2
                env_type = env_type_2
            else:
                raise ValueError

            if env_type == Evm.optimal:
                return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                           pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle,
                                           env_type=env_type, on_nv=on_nv_oc)
            else:
                return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                       pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle)

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

        if dd_type_2 == '' or dd_type_2 is None:
            dd_type_2 = dd_type
        self.log.debug(f"deer_dd with ampl1/2= {ampls_on_1}, {ampls_on_2}, t_rabi: {rabi_periods}, f: {mw_freqs}, "
                       f"envelope= {env_type_1}/{env_type_2}")

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        pihalf_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,  pi_x_length=0.5)
        # elements inside dd come from their own function
        pi_on1_element = pi_element_function(0, on_nv=1, no_amps_2_idle=False)
        pi_on2_element = pi_element_function(0, on_nv=2, no_amps_2_idle=False)
        pix_init_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                                   pi_x_length=init_pix_on_2, no_amps_2_idle=False,
                                                   env_type=env_type_2, on_nv=2)
        pix_init_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                                   pi_x_length=init_pix_on_1, no_amps_2_idle=False,
                                                   env_type=env_type_1, on_nv=1)
        pix_init_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                                   pi_x_length=init_pix_on_2, no_amps_2_idle=False,
                                                   env_type=Evm.rectangle)
        pix_init_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                                   pi_x_length=init_pix_on_1, no_amps_2_idle=False,
                                                   env_type=Evm.rectangle)

        # read phase opposite to canonical DD: 0->0 on no phase evolution
        pihalf_on1_read_element = self.get_pi_element(180+read_phase_deg, mw_freqs, ampls_on_1, rabi_periods,
                                                      pi_x_length=0.5)
        pihalf_on1_alt_read_element = self.get_pi_element(0 + read_phase_deg, mw_freqs, ampls_on_1, rabi_periods,
                                                      pi_x_length=0.5)

        t_pi_on1 = MultiNV_Generator.get_element_length(pi_on1_element)
        t_pi_on2 = MultiNV_Generator.get_element_length(pi_on2_element)

        # get tau array for measurement ticks
        tau_array = [tau2]
        n_pi = dd_type.suborder*dd_order
        n_pi_array = 2*np.asarray(range(n_pi))+1
        num_of_points = len(n_pi_array)

        tauhalf_first_pspacing = self.tau_2_pulse_spacing(tau1/2,
                                                 custom_func=[lambda t: t-t_pi_on1/2-t_pi_on1/4,
                                                              lambda t: t+t_pi_on1/2+t_pi_on1/4])
        tauhalf_last_pspacing = self.tau_2_pulse_spacing(tau1/2,
                                                 custom_func=[lambda t: t-t_pi_on1/2-t_pi_on1/4,
                                                              lambda t: t+t_pi_on1/2+t_pi_on1/4])
        if end_pix_on_2 != 0:
            pix_end_on2_element = self.get_pi_element(dd_type.phases[0], mw_freqs, ampls_on_2,
                                                      rabi_periods,
                                                      pi_x_length=end_pix_on_2, no_amps_2_idle=True,
                                                      env_type=env_type_2, on_nv=2)
            tauhalf_last_pspacing -= MultiNV_Generator.get_element_length(pix_end_on2_element)


        start_tau2_pspacing = self.tau_2_pulse_spacing(tau1,
                                                       custom_func=[lambda t:t-t_pi_on1-t_pi_on2,
                                                                    lambda t:t+t_pi_on1+t_pi_on2])

        # after pi_on_1
        tauhalf_aft_element = self._get_idle_element(length=start_tau2_pspacing/2+tau2, increment=0)
        # before pi_on_1
        tauhalf_bef_element = self._get_idle_element(length=start_tau2_pspacing/2-tau2, increment=-0)
        # first and last tauhalf
        tauhalf_first_element = self._get_idle_element(length=tauhalf_first_pspacing, increment=0)
        tauhalf_last_element = self._get_idle_element(length=tauhalf_last_pspacing, increment=0)

        tauhalf_bef_min = MultiNV_Generator.get_element_length_max(tauhalf_bef_element, 1)
        tauhalf_aft_min = MultiNV_Generator.get_element_length_max(tauhalf_aft_element, 1)
        if tauhalf_bef_min < 0 or tauhalf_aft_min < 0:
            raise ValueError(f"Tau1, tau setting yields negative pulse spacing "
                             f"{np.min([tauhalf_bef_min, tauhalf_aft_min])}."
                             f" Increase tau1 or decrease tau. Check debug for pulse times")

        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)
        for n_pi in np.asarray(range(n_pi))+1:
            idx_pi = 0
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
                    idx_pi += 1
                    if idx_pi == n_pi:
                        break
                    dd_block.append(tauhalf_element_function(n, dd_order, pulse_number, dd_type, False))
                    first, last, in_between = get_deer_pos(n, dd_order, pulse_number, dd_type, False)
                    if last:
                        if end_pix_on_2 != 0:
                            pix_end_on2_element = self.get_pi_element(dd_type_2.phases[pulse_number], mw_freqs, ampls_on_2,
                                                                      rabi_periods, env_type=env_type_2, on_nv=2,
                                                                      pi_x_length=end_pix_on_2, no_amps_2_idle=True)
                            dd_block.extend(pix_end_on2_element)
                    else:
                        dd_block.extend(pi_element_function(dd_type_2.phases[pulse_number], on_nv=2))
                    idx_pi += 1
                    if idx_pi == n_pi:
                        break
                if idx_pi == n_pi:
                    break

            #dd_block.extend(pihalf_on1_read_element)

            if not no_laser:
                dd_block.append(laser_element)
                dd_block.append(delay_element)
                dd_block.append(waiting_element)







        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, 0))

        # Create and append sync trigger block if needed
        if not no_laser:
            self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = n_pi_array
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('pi idx', 'Signal')
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
                                        kwargs_dict='', use_c2not1=False, reverse_had=False, simple_had=False,
                                        alternating=True, no_laser=False, read_phase_deg=0):
        """
        Similar to ent_create_bell(), but instead of Dolde's sequence uses Hadamard + CNOT (via DEER)
        :return:
        """

        # todo: no laser = False doesn't make sense currently

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
        pihalf_x_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                         increments=[0, 0],
                                                                         amps=ampls_on_1,
                                                                         freqs=mw_freqs,
                                                                         phases=[0, 0])
        pihalf_y_on1_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_1,
                                                                          freqs=mw_freqs,
                                                                          phases=[90, 90])
        pihalf_y_on1_read_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_1,
                                                                          freqs=mw_freqs,
                                                                          phases=[90+read_phase_deg, 90+read_phase_deg])
        pihalf_x_on1_read_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_1,
                                                                          freqs=mw_freqs,
                                                                          phases=[0+read_phase_deg, 0+read_phase_deg])
        pihalf_x_on1_read_alt_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_1,
                                                                          freqs=mw_freqs,
                                                                          phases=[180+read_phase_deg, 180+read_phase_deg])
        pihalf_y_on1_read_alt_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_1,
                                                                          freqs=mw_freqs,
                                                                          phases=[-90+read_phase_deg, -90+read_phase_deg])
        pi_on2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 2,
                                                                    increments=[0, 0],
                                                                    amps=ampls_on_2,
                                                                    freqs=mw_freqs,
                                                                    phases=[0, 0])

        pihalf_y_read_on2_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_2,
                                                                          freqs=mw_freqs,
                                                                          phases=[90+read_phase_deg, 90+read_phase_deg])
        pihalf_y_read_on2_alt_element = self._get_multiple_mw_mult_length_element(lengths=rabi_periods / 4,
                                                                          increments=[0, 0],
                                                                          amps=ampls_on_2,
                                                                          freqs=mw_freqs,
                                                                          phases=[-90+read_phase_deg, -90+read_phase_deg])

        def had_element(reverse=False, use_c2not1=False):
            # Hadarmard = 180_X*90_Y*|Psi>
            had_on1_element = [pihalf_y_on1_element, pi_on1_element] if not simple_had else [pihalf_x_on1_element]
            #had_on2_element = [pihalf_y_on2_element, pi_on1_element] if not simple_had else [pihalf_x_on1_element]

            if not reverse:
                had = []
                # Hadarmard = 180_X*90_Y*|Psi>
                had.extend(pihalf_y_on1_element)
                had.extend(pi_on1_element)
            if reverse and not use_c2not1:
                had = []
                had.extend(pi_on1_element)
                had.extend(pihalf_y_on1_read_element)
            elif reverse_had and use_c2not1:
                had = []
                had.extend(pi_on2_element)
                had.extend(pihalf_y_read_on2_element)
            if simple_had:
                had = []
                had.extend(pihalf_x_on1_element)

            return had

        # TODO: include simple had correctly

        self.log.debug(f"{name}: reverse_had {reverse_had}, use_c2not1 {use_c2not1}. Tau_cnot: {tau_start}")

        # Create block and append to created_blocks list
        dd_block = PulseBlock(name=name)
        created_blocks, created_ensembles, created_sequences = [], [], []
        if not reverse_had:
            # Hadarmard = 180_X*90_Y*|Psi>
            #dd_block.extend(pihalf_y_on1_element)
            #dd_block.extend(pi_on1_element)
            dd_block.extend(pihalf_x_on1_element)
        if not use_c2not1:
            dd_block.extend(c1not2_element)
        else:
            dd_block.extend(c2not1_element)
        if reverse_had and not use_c2not1:
            #dd_block.extend(pi_on1_element)
            #dd_block.extend(pihalf_y_on1_read_element)
            dd_block.extend(pihalf_x_on1_read_element)
        elif reverse_had and use_c2not1:
            dd_block.extend(pi_on2_element)
            dd_block.extend(pihalf_y_read_on2_element)

        if alternating:
            if not reverse_had:
                # Hadarmard = 180_X*90_Y*|Psi>
                # dd_block.extend(pihalf_y_on1_element)
                # dd_block.extend(pi_on1_element)
                dd_block.extend(pihalf_x_on1_element)
            if not use_c2not1:
                dd_block.extend(c1not2_alt_element)
            else:
                dd_block.extend(c2not1_alt_element)
            if reverse_had and not use_c2not1:
                #dd_block.extend(pi_on1_element)
                #dd_block.extend(pihalf_y_on1_read_alt_element)
                dd_block.extend(pihalf_x_on1_read_alt_element)
            elif reverse_had and use_c2not1:
                dd_block.extend(pi_on2_element)
                dd_block.extend(pihalf_y_read_on2_alt_element)

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
                                 tau_cnot=10e-6, f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                                 rabi_period_mw_2="100e-9, 100e-9, 100e-9", assym_disent=False,
                                 dd_type=DDMethods.SE, dd_order=1, cnot_kwargs='', alternating=True):
        """
        Use lists of f_mw_2, ampl_mw_2, rabi_period_m2_2 to a) address second NV b) use double quantum transition
        """

        self.log.debug(f"Bell Ramsey (assym={assym_disent}) tau_cnot= {tau_cnot}, cnot_kwargs={cnot_kwargs}, "
                       f"dd_type={dd_type.name}-{dd_order}")
        bell_blocks, _, _ = self.generate_ent_create_bell_bycnot('ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        alternating=False, no_laser=True,
                                                                        kwargs_dict=cnot_kwargs, reverse_had=False,
                                                                        use_c2not1=False)
        disent_blocks, _, _ = self.generate_ent_create_bell_bycnot('dis-ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        kwargs_dict=cnot_kwargs,
                                                                        alternating=False,no_laser=True, reverse_had=True,
                                                                        use_c2not1=assym_disent)
        disent_alt_blocks, _, _ = self.generate_ent_create_bell_bycnot('dis-ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        kwargs_dict=cnot_kwargs,
                                                                        alternating=False, no_laser=True,reverse_had=True,
                                                                        read_phase_deg=180,
                                                                        use_c2not1=assym_disent)
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()


        bell_blocks, disent_blocks, disent_alt_blocks = bell_blocks[0], disent_blocks[0], disent_alt_blocks[0]

        tau_start_pspacing = tau_start   # pi pulse not subtracted here!
        tau_array = tau_start_pspacing + np.arange(num_of_points) * tau_step
        tau_element = self._get_idle_element(length=tau_start_pspacing, increment=tau_step)

        bell_ramsey_block = PulseBlock(name=name)
        bell_ramsey_block.extend(bell_blocks)
        bell_ramsey_block.append(tau_element)
        bell_ramsey_block.extend(disent_blocks)
        bell_ramsey_block.append(laser_element)
        bell_ramsey_block.append(delay_element)
        bell_ramsey_block.append(waiting_element)

        if alternating:
            bell_ramsey_block.extend(bell_blocks)
            bell_ramsey_block.append(tau_element)
            bell_ramsey_block.extend(disent_alt_blocks)
            bell_ramsey_block.append(laser_element)
            bell_ramsey_block.append(delay_element)
            bell_ramsey_block.append(waiting_element)

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

    def generate_bell_hahnecho(self, name='bell_ramsey', tau_start=0.5e-6, tau_step=0.01e-6, num_of_points=50,
                                 tau_cnot=10e-6, f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0",
                                 rabi_period_mw_2="100e-9, 100e-9, 100e-9", assym_disent=False,
                                 dd_type=DDMethods.SE, dd_order=1, cnot_kwargs='', alternating=True):
        """
        Use lists of f_mw_2, ampl_mw_2, rabi_period_m2_2 to a) address second NV b) use double quantum transition
        """

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2), n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), n_nvs=2)

        self.log.debug(f"Bell Hahn echo (assym={assym_disent}) tau_cnot= {tau_cnot}, cnot_kwargs={cnot_kwargs}, "
                       f"dd_type={dd_type.name}-{dd_order}")
        bell_blocks, _, _ = self.generate_ent_create_bell_bycnot('ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        alternating=False, no_laser=True,
                                                                        kwargs_dict=cnot_kwargs, reverse_had=False,
                                                                        use_c2not1=False)
        disent_blocks, _, _ = self.generate_ent_create_bell_bycnot('dis-ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        kwargs_dict=cnot_kwargs,
                                                                        alternating=False,no_laser=True, reverse_had=True,
                                                                        use_c2not1=assym_disent)
        disent_alt_blocks, _, _ = self.generate_ent_create_bell_bycnot('dis-ent', tau_cnot, tau_step=0, num_of_points=1,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        dd_type=dd_type, dd_order=dd_order,
                                                                        kwargs_dict=cnot_kwargs,
                                                                        alternating=False, no_laser=True,reverse_had=True,
                                                                        read_phase_deg=180,
                                                                        use_c2not1=assym_disent)
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        def pi_element_function(xphase, on_nv=1, pi_x_length=1., no_amps_2_idle=False):

            env_type = Evm.rectangle if 'env_type' not in cnot_kwargs else \
                cnot_kwargs['env_type']

            if on_nv == 1:
                ampl_pi = ampls_on_1
                env_type = env_type
            elif on_nv == 2:
                ampl_pi = ampls_on_2
                env_type = env_type
            else:
                raise ValueError

            self.log.debug(f"Pi element on_nv= {on_nv}, env {env_type}, freq= {mw_freqs}, ampl= {ampl_pi}")

            if env_type == Evm.optimal:
                return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                           pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle,
                                           env_type=env_type, on_nv=on_nv)
            else:
                return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                           pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle)




        bell_blocks, disent_blocks, disent_alt_blocks = bell_blocks[0], disent_blocks[0], disent_alt_blocks[0]

        tau_start_pspacing = tau_start   # pi pulse not subtracted here!
        tau_array = tau_start_pspacing + np.arange(num_of_points) * tau_step
        tau_element = self._get_idle_element(length=tau_start_pspacing, increment=tau_step)

        bell_ramsey_block = PulseBlock(name=name)
        bell_ramsey_block.extend(bell_blocks)
        bell_ramsey_block.append(tau_element)
        bell_ramsey_block.extend(pi_element_function(0, on_nv=1))
        bell_ramsey_block.extend(pi_element_function(0, on_nv=2))
        bell_ramsey_block.append(tau_element)
        bell_ramsey_block.extend(disent_blocks)
        bell_ramsey_block.append(laser_element)
        bell_ramsey_block.append(delay_element)
        bell_ramsey_block.append(waiting_element)

        if alternating:
            bell_ramsey_block.extend(bell_blocks)
            bell_ramsey_block.append(tau_element)
            bell_ramsey_block.extend(pi_element_function(0, on_nv=1))
            bell_ramsey_block.extend(pi_element_function(0, on_nv=2))
            bell_ramsey_block.append(tau_element)
            bell_ramsey_block.extend(disent_alt_blocks)
            bell_ramsey_block.append(laser_element)
            bell_ramsey_block.append(delay_element)
            bell_ramsey_block.append(waiting_element)

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

    def generate_rabi_test(self, name='rabi', tau_start=10.0e-9, tau_step=10.0e-9, num_of_points=50,
                           f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", ampl_idle_mult=0.):
        """
        Double quantum transition, driven in parallel (instead of sequential)
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()


        # create param arrays
        amplitudes = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=0, n_nvs=2)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), idx_nv=1, n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), n_nvs=2)


        tau_array = tau_start + np.arange(num_of_points) * tau_step
        num_of_points = len(tau_array)


        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        for tau in tau_array:
            if tau == 0:
                tau = 1e-9
                self.log.warning(f"Changing mw element of unsupported tau=0 to {tau}")
            rabi_periods = np.ones(amplitudes.shape)*tau
            # todo: debug only
            mw_element = self.get_pi_element(0, mw_freqs, amplitudes, rabi_periods, pi_x_length=2,
                                             mw_idle_amps=ampls_on_2 * ampl_idle_mult)
            #mw_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods, pi_x_length=2,
            #                                      mw_idle_amps=ampls_on_2*ampl_idle_mult)
            rabi_block.extend(mw_element)
            rabi_block.append(laser_element)
            rabi_block.append(delay_element)
            rabi_block.append(waiting_element)


        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((rabi_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2*num_of_points if False else num_of_points
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


    def generate_oc_pi_ampl(self, name='oc_ampl', on_nv=1,
                            ampl_start=0., ampl_step=0.1, num_of_points=20):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        on_nv = csv_2_list(on_nv)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2), n_nvs=2)

        # get tau array for measurement ticks
        ampl_array = ampl_start + np.arange(num_of_points) * ampl_step

        # create the laser_mw element
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        # Create block and append to created_blocks list
        rabi_block = PulseBlock(name=name)
        for ampl in ampl_array:
            mw_element = self._get_pi_oc_element([0], [self.microwave_frequency], on_nv=on_nv,
                                                 scale_ampl=ampl)
            rabi_block.extend(mw_element)
            rabi_block.append(laser_element)
            rabi_block.append(delay_element)
            rabi_block.append(waiting_element)


        else:
            raise ValueError(f"On_nv= {on_nv} has wrong length.")

        created_blocks.append(rabi_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((rabi_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = ampl_array
        block_ensemble.measurement_information['units'] = ('', '')
        block_ensemble.measurement_information['labels'] = ('rel. ampl.', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def _get_mw_gate_dd_element(self, phase, mw_freqs, mw_amps, rabi_periods, pi_x_length=1.,
                            nv_order='1,2', dd_type=DDMethods.SE, dd_order=1, env_type=Evm.from_gen_settings,
                            ):

        exact_mw_tau = True
        mw_freqs_raw, mw_amps_raw, rabi_periods_raw = cp.copy(mw_freqs), cp.copy(mw_amps), cp.copy(rabi_periods)

        ampls_on_1 = self._create_param_array(None, mw_amps, idx_nv=0, n_nvs=2,
                                              order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(None, mw_amps, idx_nv=1, n_nvs=2,
                                               order_nvs=nv_order)
        mw_freqs = self._create_param_array(None, mw_freqs, n_nvs=2, order_nvs=nv_order)
        rabi_periods = self._create_param_array(None, rabi_periods, n_nvs=2, order_nvs=nv_order)

        def pi_element_function(xphase, pi_x_length=1., on_nv=1, no_amps_2_idle=True):

            if on_nv == 1:
                ampl_pi = ampls_on_1
            elif on_nv == 2:
                ampl_pi = ampls_on_2
            else:
                raise ValueError

            return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                   pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle,
                                   env_type=env_type)

        pix_on1_element = pi_element_function(0, pi_x_length=pi_x_length, on_nv=1)
        pi_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                           pi_x_length=1, no_amps_2_idle=False,
                                           env_type=Evm.from_gen_settings)
        pi_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                             pi_x_length=1, no_amps_2_idle=False,
                                             env_type=Evm.from_gen_settings)

        t_pi_on1 = MultiNV_Generator.get_element_length(pi_on1_element)
        t_pi_on2 = MultiNV_Generator.get_element_length(pi_on2_element)
        mw_length = MultiNV_Generator.get_element_length(pix_on1_element)


        gate_block = []

        tau1 = 2*mw_length/2
        # make tau1 longer st. the resulting tau2_ps (in deer_dd_tau) yields tau_pi_1 = 2x (mw_length/2 + t_pi/2)
        t_balance = 0
        if exact_mw_tau:
            t_balance = t_pi_on1/2
            tau1 += t_balance
        self.log.debug(f"For MW {mw_length}, MW/2 {mw_length/2}, => tau1 {tau1}, t_balance {t_balance}")

        ampl_gate = ampls_on_1[0]

        mw_half_el = self._get_multiple_mw_element(mw_length/2, 0, ampl_gate, mw_freqs, [phase]*len(mw_freqs))
        self.log.debug(f"rabi: {rabi_periods}, amppl2 {ampls_on_2}, freqs {mw_freqs}")
        pi_on2_element = self.get_pi_element(dd_type.phases[-1], mw_freqs, ampls_on_2, rabi_periods,
                                             pi_x_length=1)

        no_dd_on2 = False
        save_mw_amp, save_mw_freqs, save_rabi_periods = self.microwave_amplitude, self.microwave_frequency, self.rabi_period
        self.microwave_amplitude, self.microwave_frequency, self.rabi_period = mw_amps_raw[0], mw_freqs_raw[0], \
                                                                               rabi_periods_raw[0]
        save_mw_amp = self.microwave_amplitude
        if no_dd_on2:
            self.log.warning("no_dd_on2 enabled. Won't decouple the other NV!")
            # debug only
            if nv_order == "1,2":
                mw_amps_raw[1] = 0
            elif nv_order == "2,1":
                self.microwave_amplitude = 0
            else:
                raise ValueError


        # deer_dd with tau2=0 decouples dipolar coupling, and both NV1, NV2
        # pass unaltered mw_freqs, mw_amps array that might have been flipped by nv_order already
        dd_element, _, _ = self.generate_deer_dd_tau(name='mw_dd', tau1=tau1, tau_start=0, tau_step=0, num_of_points=1,
                                  f_mw_2=self.list_2_csv(list(mw_freqs_raw[1:])), ampl_mw_2=self.list_2_csv(list(mw_amps_raw[1:])),
                                                     rabi_period_mw_2=self.list_2_csv(list(rabi_periods_raw[1:])),
                                  dd_type=dd_type, dd_type_2=DDMethods.MW_DD_SE8, dd_order=dd_order,
                                  init_pix_on_1=0, init_pix_on_2=0,
                                  start_pix_on_1=0, end_pix_on_1=0, end_pix_on_2=0, read_pix_on_2=0,
                                  scale_tau2_last=0, scale_tau2_first=0, floating_last_pi=False,
                                  nv_order=nv_order,
                                  alternating=False, no_laser=True)

        self.microwave_amplitude, self.microwave_frequency, self.rabi_period = save_mw_amp, save_mw_freqs, save_rabi_periods

        dd_element = dd_element[0]


        gate_block.append(mw_half_el)
        gate_block.extend(dd_element)
        gate_block.append(mw_half_el)
        #gate_block.extend(pi_on2_element)


        return gate_block


    def _get_mw_gate_ddxdd_element(self, phase, mw_freqs, mw_amps, rabi_periods, pi_x_length=1.,
                                   ampl_gate=None,
                                   nv_order='1,2', dd_type=DDMethods.SE, dd_type_2='',
                                   dd_order=1, dd_tau=100e-9, env_type=Evm.from_gen_settings,
                            ):

        exact_mw_tau = True
        force_axy = False

        mw_freqs_raw, mw_amps_raw, rabi_periods_raw = cp.copy(mw_freqs), cp.copy(mw_amps), cp.copy(rabi_periods)

        ampls_on_1 = self._create_param_array(None, mw_amps, idx_nv=0, n_nvs=2,
                                              order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(None, mw_amps, idx_nv=1, n_nvs=2,
                                               order_nvs=nv_order)
        mw_freqs = self._create_param_array(None, mw_freqs, n_nvs=2, order_nvs=nv_order)
        rabi_periods = self._create_param_array(None, rabi_periods, n_nvs=2, order_nvs=nv_order)

        def pi_element_function(xphase, pi_x_length=1., on_nv=1, no_amps_2_idle=True):

            if on_nv == 1:
                ampl_pi = ampls_on_1
            elif on_nv == 2:
                ampl_pi = ampls_on_2
            else:
                raise ValueError

            return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                   pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle,
                                   env_type=env_type)

        pix_on1_element = pi_element_function(0, pi_x_length=pi_x_length, on_nv=1)
        pi_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                           pi_x_length=1, no_amps_2_idle=False,
                                           env_type=Evm.from_gen_settings)
        pi_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                             pi_x_length=1, no_amps_2_idle=False,
                                             env_type=Evm.from_gen_settings)

        t_pi_on1 = MultiNV_Generator.get_element_length(pi_on1_element)
        t_pi_on2 = MultiNV_Generator.get_element_length(pi_on2_element)
        mw_length = MultiNV_Generator.get_element_length(pix_on1_element)

        if dd_type_2 == '':
            dd_type_2 = DDMethods.MW_DD_SE8

        t_balance_last = 1
        tau1 = dd_tau

        if exact_mw_tau:
            t_balance_last = 1 - (mw_length / 2) / ((tau1 - t_pi_on1) / 2)
            if tau1 < t_pi_on2 + t_pi_on1 or t_balance_last < 0:
                self.log.warning(f"Adjusting tau1 to fit t_pi_on2 in: {tau1}"
                                 f"->{1 + abs(t_balance_last) * (t_pi_on2 + t_pi_on1)}")
                tau1 = (1 + abs(t_balance_last)) * (t_pi_on2 + t_pi_on1)

        if ampl_gate is None:
            ampl_gate = ampls_on_1[0]

        mw_el = self._get_multiple_mw_element(mw_length, 0, ampl_gate, mw_freqs, [phase]*len(mw_freqs))
        self.log.debug(f"rabi: {rabi_periods}, amppl2 {ampls_on_2}, freqs {mw_freqs}")
        pi_on2_element = self.get_pi_element(dd_type.phases[-1], mw_freqs, ampls_on_2, rabi_periods,
                                             pi_x_length=1)

        no_dd_on2 = False  # debug only
        save_mw_amp, save_mw_freqs, save_rabi_periods = self.microwave_amplitude, self.microwave_frequency, self.rabi_period
        self.microwave_amplitude, self.microwave_frequency, self.rabi_period = mw_amps_raw[0], mw_freqs_raw[0], rabi_periods_raw[0]
        if no_dd_on2:
            self.log.warning("no_dd_on2 enabled. Won't decouple the other NV!")
            # debug only
            if nv_order == "1,2":
                mw_amps_raw[1] = 0
            elif nv_order == "2,1":
                self.microwave_amplitude = 0
            else:
                raise ValueError

        # deer_dd with tau2=0 decouples dipolar coupling, and both NV1, NV2
        # pass unaltered mw_freqs, mw_amps array that might have been flipped by nv_order already

        # deer_dd with tau2=0 decouples dipolar coupling, and both NV1, NV2
        dd_element_1, _, _ = self.generate_deer_dd_tau(name='mw_dd', tau1=tau1, tau_start=0, num_of_points=1,
                                                       f_mw_2=self.list_2_csv(list(mw_freqs_raw[1:])),
                                                       ampl_mw_2=self.list_2_csv(list(mw_amps_raw[1:])),
                                                       rabi_period_mw_2=self.list_2_csv(list(rabi_periods_raw[1:])),
                                                       dd_type=dd_type, dd_type_2=dd_type_2,
                                                       dd_order=dd_order,
                                                       init_pix_on_1=0, init_pix_on_2=0,
                                                       start_pix_on_1=0, end_pix_on_1=0, end_pix_on_2=0,
                                                       read_pix_on_2=0,
                                                       nv_order=nv_order,
                                                       scale_tau2_first=1, scale_tau2_last=t_balance_last,
                                                       floating_last_pi=False,
                                                       alternating=False, no_laser=True)
        dd_element_2, _, _ = self.generate_deer_dd_tau(name='mw_dd', tau1=tau1, tau_start=0, num_of_points=1,
                                                       f_mw_2=self.list_2_csv(list(mw_freqs_raw[1:])),
                                                       ampl_mw_2=self.list_2_csv(list(mw_amps_raw[1:])),
                                                       rabi_period_mw_2=self.list_2_csv(list(rabi_periods_raw[1:])),
                                                       dd_type=dd_type.dd_after_mwx, dd_type_2=dd_type_2.dd_after_mwx,
                                                       dd_order=dd_order,
                                                       init_pix_on_1=0, init_pix_on_2=0,
                                                       start_pix_on_1=0, end_pix_on_1=0, end_pix_on_2=0,
                                                       read_pix_on_2=0,
                                                       nv_order=nv_order,
                                                       scale_tau2_first=t_balance_last, scale_tau2_last=1,
                                                       floating_last_pi=False,
                                                       alternating=False, no_laser=True)

        if dd_type != dd_type.dd_after_mwx:
            self.log.debug(f"Using decoupling streched over mw x, type {dd_type} -> {dd_type.dd_after_mwx}")
        if dd_type_2 != dd_type_2.dd_after_mwx:
            self.log.debug(f"Using decoupling on2 streched over mw x, type {dd_type_2} -> {dd_type_2.dd_after_mwx}")

        if force_axy:
            axy_element_1, _, _ = self.generate_AXY(name='mw_dd', tau_start=tau1, tau_step=0e-9,
                                                    num_of_points=1,
                                                    f_mw_2=self.list_2_csv(list(mw_freqs_raw[1:])),
                                                    ampl_mw_2=self.list_2_csv(list(mw_amps_raw[1:])),
                                                    rabi_period_mw_2=self.list_2_csv(list(rabi_periods_raw[1:])),
                                                    xy8_order=dd_order,
                                                    no_laser=True, alternating=False,
                                                    f1=0, f2=0, f3=0, f4=0,
                                                    scale_tau2_first=1, scale_tau2_last=t_balance_last,
                                                    init_pix=0)
            axy_element_2, _, _ = self.generate_AXY(name='mw_dd', tau_start=tau1, tau_step=0e-9,
                                                    num_of_points=1,
                                                    f_mw_2=self.list_2_csv(list(mw_freqs_raw[1:])),
                                                    ampl_mw_2=self.list_2_csv(list(mw_amps_raw[1:])),
                                                    rabi_period_mw_2=self.list_2_csv(list(rabi_periods_raw[1:])),
                                                    xy8_order=dd_order,
                                                    no_laser=True, alternating=False,
                                                    f1=0, f2=0, f3=0, f4=0,
                                                    scale_tau2_first=t_balance_last, scale_tau2_last=1,
                                                    init_pix=0)
            dd_element_1, dd_element_2 = axy_element_1, axy_element_2

        dd_element_1, dd_element_2 = dd_element_1[0], dd_element_2[0]
        self.microwave_amplitude, self.microwave_frequency, self.rabi_period = save_mw_amp, save_mw_freqs, save_rabi_periods

        gate_block = []
        gate_block.extend(dd_element_1)
        gate_block.append(mw_el)
        gate_block.extend(dd_element_2)
        #gate_block.extend(pi_on2_element)

        return gate_block


    def generate_mw_gate_dd(self, name='gate_dd', tau_start=100e-9, tau_step=1e-6, num_of_points=10,
                                phase=0, ampl_gate=0.1, n_gate_reps=1,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                            nv_order='1,2',
                            dd_type=DDMethods.SE, dd_type_2='', dd_order=1, alternating=False,
                            ):

        exact_mw_tau = True

        created_blocks, created_ensembles, created_sequences = list(), list(), list()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2),
                                                n_nvs=2, order_nvs=nv_order)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=0, n_nvs=2, order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=1, n_nvs=2, order_nvs=nv_order)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2),
                                            n_nvs=2, order_nvs=nv_order)


        tau_array = tau_start + np.arange(num_of_points) * tau_step

        pi_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                           pi_x_length=1, no_amps_2_idle=False,
                                           env_type=Evm.from_gen_settings)
        pi_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                             pi_x_length=1, no_amps_2_idle=False,
                                             env_type=Evm.from_gen_settings)
        t_pi_on1 = MultiNV_Generator.get_element_length(pi_on1_element)
        t_pi_on2 = MultiNV_Generator.get_element_length(pi_on2_element)

        if dd_type_2 == '':
            dd_type_2 = DDMethods.MW_DD_SE8

        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        gate_block = PulseBlock(name=name)


        # todo: make use of _get_mw_gate_dd_element
        for mw_length in tau_array:

            tau1 = 2*mw_length/2
            # make tau1 longer st. the resulting tau2_ps (in deer_dd_tau) yields pi pulse spacing on NV 1 = 2x mw_length
            # pulse spacing must stay constant for n_rep > 1!
            t_balance = 0
            if exact_mw_tau:
                t_balance = 2*t_pi_on1/2 # tau from pi pulse centers!
                tau1 += t_balance
                if tau1 < t_pi_on2 + t_pi_on1:
                    self.log.warning(f"Adjusting tau1 to fit t_pi_on2 in: {tau1}->{t_pi_on2 + t_pi_on1}")
                    tau1 = t_pi_on2 + t_pi_on1

            self.log.debug(f"For MW/2 {mw_length/2}, => tau1 {tau1}, t_balance {t_balance}")

            mw_half_el = self._get_multiple_mw_element(mw_length/2, 0, ampl_gate, mw_freqs, [phase]*len(mw_freqs))
            self.log.debug(f"rabi: {rabi_periods}, amppl2 {ampls_on_2}, freqs {mw_freqs}")
            pi_on2_element = self.get_pi_element(dd_type.phases[-1], mw_freqs, ampls_on_2, rabi_periods,
                                                 pi_x_length=1)
            # deer_dd with tau2=0 decouples dipolar coupling, and both NV1, NV2
            dd_element, _, _ = self.generate_deer_dd_tau(name='mw_dd', tau1=tau1, tau_start=0, num_of_points=1,
                                      f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2, rabi_period_mw_2=rabi_period_mw_2,
                                      dd_type=dd_type, dd_type_2=dd_type_2, dd_order=dd_order,
                                      init_pix_on_1=0, init_pix_on_2=0,
                                      start_pix_on_1=0, end_pix_on_1=0, end_pix_on_2=0, read_pix_on_2=0,
                                      nv_order = nv_order,
                                      scale_tau2_first=0, scale_tau2_last=0, floating_last_pi=False,
                                      alternating=False, no_laser=True)


            dd_element = dd_element[0]

            for i_gate in range(n_gate_reps):
                gate_block.append(mw_half_el)
                gate_block.extend(dd_element)
                gate_block.append(mw_half_el)
            #gate_block.extend(pi_on2_element)

            gate_block.append(laser_element)
            gate_block.append(delay_element)
            gate_block.append(waiting_element)

            if alternating:
                for i_gate in range(n_gate_reps):
                    gate_block.append(mw_half_el)
                    gate_block.extend(dd_element)
                    gate_block.append(mw_half_el)
                #gate_block.extend(pi_on2_element)
                gate_block.extend(pi_on1_element)

                gate_block.append(laser_element)
                gate_block.append(delay_element)
                gate_block.append(waiting_element)


        created_blocks.append(gate_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((gate_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2*number_of_lasers if alternating else number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_AXY(self, name='axy8', tau_start=0.5e-6, tau_step=10.0e-9, num_of_points=50,
                    f_mw_2="1e9", rabi_period_mw_2='0e-9', ampl_mw_2='0.',
                    xy8_order=4, no_laser=False, alternating=True,
                    f1=1.0, f2=0.0, f3=0.0, f4=0.0,
                    scale_tau2_first=1., scale_tau2_last=1.,
                    init_pix=0):
        """
        based on Philip V. AXY method
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2),
                                                n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=0, n_nvs=2)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=1, n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2),
                                            n_nvs=2)

        # get tau array for measurement ticks
        start_tau_pspacing = self.tau_2_pulse_spacing(tau_start)
        tau_array = start_tau_pspacing + np.arange(num_of_points, dtype='float64') * tau_step

        # check if all pi pulses fit in tau, i.e. if the rabi period is short enough
        if (5 * self.rabi_period / 2) > tau_array.min():
            self.log.error('Unable to create AXY sequence. Rabi period too long for minimum tau.')
            return created_blocks, created_ensembles, created_sequences

        # calculate the relative spacings of the composite pulse.
        spacings = self._get_axy_spacing(f1e=f1, f2e=f2, f3e=f3, f4e=f4)
        # Determine a scale factor for each tau
        tau_factors = np.zeros(6, dtype='float64')
        tau_factors[0] = spacings[0]
        tau_factors[1] = spacings[1] - spacings[0]
        tau_factors[2] = spacings[2] - spacings[1]
        tau_factors[3] = tau_factors[2]
        tau_factors[4] = tau_factors[1]
        tau_factors[5] = tau_factors[0]

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        pihalf_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                              pi_x_length=0.5)
        pix_0_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                              pi_x_length=1)
        pix_30_element = self.get_pi_element(30, mw_freqs, ampls_on_1, rabi_periods,
                                              pi_x_length=1)
        pix_90_element = self.get_pi_element(90, mw_freqs, ampls_on_1, rabi_periods,
                                              pi_x_length=1)
        piy_0_element = self.get_pi_element(90, mw_freqs, ampls_on_1, rabi_periods,
                                              pi_x_length=1)
        piy_30_element = self.get_pi_element(120, mw_freqs, ampls_on_1, rabi_periods,
                                              pi_x_length=1)
        piy_90_element = self.get_pi_element(180, mw_freqs, ampls_on_1, rabi_periods,
                                              pi_x_length=1)


        # Create pihalf block
        dd_block = PulseBlock(name=name)
        if init_pix != 0.:
            dd_block.append(pihalf_element)

        for i, tau in enumerate(tau_array):
            # Create the different tau elements
            first_tau = self._get_idle_element(
                length=scale_tau2_first*tau_factors[0] * 2 * tau - (self.rabi_period / 4), increment=0)
            last_tau = self._get_idle_element(
                length=scale_tau2_last*tau_factors[0] * 2 * tau - (self.rabi_period / 4), increment=0)
            tau1_raw_element = self._get_idle_element(length=tau_factors[0] * 2 * tau, increment=0)
            tau6_raw_element = self._get_idle_element(length=tau_factors[5] * 2 * tau, increment=0)
            tau1_element = self._get_idle_element(
                length=tau_factors[0] * 2 * tau - (self.rabi_period / 2), increment=0)
            tau2_element = self._get_idle_element(
                length=tau_factors[1] * 2 * tau - (self.rabi_period / 2), increment=0)
            tau3_element = self._get_idle_element(
                length=tau_factors[2] * 2 * tau - (self.rabi_period / 2), increment=0)
            tau4_element = self._get_idle_element(
                length=tau_factors[3] * 2 * tau - (self.rabi_period / 2), increment=0)
            tau5_element = self._get_idle_element(
                length=tau_factors[4] * 2 * tau - (self.rabi_period / 2), increment=0)
            tau6_element = self._get_idle_element(
                length=tau_factors[5] * 2 * tau - (self.rabi_period / 2), increment=0)

            # Fill the PulseBlock with elements
            for n in range(xy8_order):
                # X
                if n == 0:
                    dd_block.append(first_tau)
                else:
                    dd_block.append(tau1_element)
                dd_block.extend(pix_30_element)
                dd_block.append(tau2_element)
                dd_block.extend(pix_0_element)
                dd_block.append(tau3_element)
                dd_block.extend(pix_90_element)
                dd_block.append(tau4_element)
                dd_block.extend(pix_0_element)
                dd_block.append(tau5_element)
                dd_block.extend(pix_30_element)
                dd_block.append(tau6_raw_element)
                # Y
                dd_block.append(tau6_element)
                dd_block.extend(piy_30_element)
                dd_block.append(tau5_element)
                dd_block.extend(piy_0_element)
                dd_block.append(tau4_element)
                dd_block.extend(piy_90_element)
                dd_block.append(tau3_element)
                dd_block.extend(piy_0_element)
                dd_block.append(tau2_element)
                dd_block.extend(piy_30_element)
                dd_block.append(tau1_raw_element)
                # X
                dd_block.append(tau1_element)
                dd_block.extend(pix_30_element)
                dd_block.append(tau2_element)
                dd_block.extend(pix_0_element)
                dd_block.append(tau3_element)
                dd_block.extend(pix_90_element)
                dd_block.append(tau4_element)
                dd_block.extend(pix_0_element)
                dd_block.append(tau5_element)
                dd_block.extend(pix_30_element)
                dd_block.append(tau6_raw_element)
                # Y
                dd_block.append(tau6_element)
                dd_block.extend(piy_30_element)
                dd_block.append(tau5_element)
                dd_block.extend(piy_0_element)
                dd_block.append(tau4_element)
                dd_block.extend(piy_90_element)
                dd_block.append(tau3_element)
                dd_block.extend(piy_0_element)
                dd_block.append(tau2_element)
                dd_block.extend(piy_30_element)
                dd_block.append(tau1_raw_element)
                ###############################################
                # Y
                dd_block.append(tau1_element)
                dd_block.extend(piy_30_element)
                dd_block.append(tau2_element)
                dd_block.extend(piy_0_element)
                dd_block.append(tau3_element)
                dd_block.extend(piy_90_element)
                dd_block.append(tau4_element)
                dd_block.extend(piy_0_element)
                dd_block.append(tau5_element)
                dd_block.extend(piy_30_element)
                dd_block.append(tau6_raw_element)
                # X
                dd_block.append(tau6_element)
                dd_block.extend(pix_30_element)
                dd_block.append(tau5_element)
                dd_block.extend(pix_0_element)
                dd_block.append(tau4_element)
                dd_block.extend(pix_90_element)
                dd_block.append(tau3_element)
                dd_block.extend(pix_0_element)
                dd_block.append(tau2_element)
                dd_block.extend(pix_30_element)
                dd_block.append(tau1_raw_element)
                # Y
                dd_block.append(tau1_element)
                dd_block.extend(piy_30_element)
                dd_block.append(tau2_element)
                dd_block.extend(piy_0_element)
                dd_block.append(tau3_element)
                dd_block.extend(piy_90_element)
                dd_block.append(tau4_element)
                dd_block.extend(piy_0_element)
                dd_block.append(tau5_element)
                dd_block.extend(piy_30_element)
                dd_block.append(tau6_raw_element)
                # X
                dd_block.append(tau6_element)
                dd_block.extend(pix_30_element)
                dd_block.append(tau5_element)
                dd_block.extend(pix_0_element)
                dd_block.append(tau4_element)
                dd_block.extend(pix_90_element)
                dd_block.append(tau3_element)
                dd_block.extend(pix_0_element)
                dd_block.append(tau2_element)
                dd_block.extend(pix_30_element)
                if n == (xy8_order - 1):
                    dd_block.append(last_tau)
                else:
                    dd_block.append(tau1_raw_element)

        if alternating:
            raise NotImplementedError

        if init_pix != 0.:
            dd_block.append(pihalf_element)

        if not no_laser:
            dd_block.append(laser_element)
            dd_block.append(delay_element)
            dd_block.append(waiting_element)
            # Create and append sync trigger block if needed
            if self.sync_channel:
                dd_block.append(self._get_sync_element())

        created_blocks.append(dd_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((dd_block.name, 0))

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

    @staticmethod
    def _get_axy_spacing(f1e=1.0, f2e=0.0, f3e=0.0, f4e=0.0):
        import scipy.optimize as optim
        # Initial angles for solver
        x0 = np.array([0.1 * np.pi, 0.3 * np.pi, 0.6 * np.pi, 0.9 * np.pi], dtype='float64')

        # define function to solve
        def kdd5even(x):
            theta1 = x[0]
            theta2 = x[1]
            theta3 = x[2]
            theta4 = x[3]

            theta5 = theta2 + theta4 - (theta1 + theta3) + np.pi / 2

            return_val = np.zeros(4, dtype='float64')
            return_val[0] = f1e - 4 / (1 * np.pi) * (
                        np.sin(1 * theta1) + np.sin(1 * theta3) + np.sin(1 * theta5) - np.sin(1 * theta2) - np.sin(
                    1 * theta4))
            return_val[1] = f2e - 4 / (2 * np.pi) * (
                        np.sin(2 * theta1) + np.sin(2 * theta3) + np.sin(2 * theta5) - np.sin(2 * theta2) - np.sin(
                    2 * theta4))
            return_val[2] = f3e - 4 / (3 * np.pi) * (
                        np.sin(3 * theta1) + np.sin(3 * theta3) + np.sin(3 * theta5) - np.sin(3 * theta2) - np.sin(
                    3 * theta4))
            return_val[3] = f4e - 4 / (4 * np.pi) * (
                        np.sin(4 * theta1) + np.sin(4 * theta3) + np.sin(4 * theta5) - np.sin(4 * theta2) - np.sin(
                    4 * theta4))
            return return_val

        # Solve for kdd5even(x) = 0
        solved_x = optim.fsolve(kdd5even, x0)
        solved_x = np.append(solved_x,
                             solved_x[1] + solved_x[3] - (solved_x[0] + solved_x[2]) + np.pi / 2)
        return solved_x / (2 * np.pi)

    def generate_mw_gate_dd_x_dd(self, name='gate_dd', tau_start=100e-9, tau_step=1e-6, num_of_points=10,
                                 tau1=100e-9, phase=0, ampl_gate=0.1, n_gate_reps=1,
                                 f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                                 nv_order='1,2',
                                 dd_type=DDMethods.SE, dd_type_2='', dd_order=1, alternating=False,
                                 ):

        created_blocks, created_ensembles, created_sequences = list(), list(), list()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2),
                                                n_nvs=2, order_nvs=nv_order)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=0, n_nvs=2, order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=1, n_nvs=2, order_nvs=nv_order)
        mw_amps = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), order_nvs=nv_order,
                                              n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2),
                                            n_nvs=2, order_nvs=nv_order)


        tau_array = tau_start + np.arange(num_of_points) * tau_step

        pi_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                           pi_x_length=1, no_amps_2_idle=False,
                                           env_type=Evm.from_gen_settings)
        pi_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                             pi_x_length=1, no_amps_2_idle=False,
                                             env_type=Evm.from_gen_settings)
        t_pi_on1 = MultiNV_Generator.get_element_length(pi_on1_element)
        t_pi_on2 = MultiNV_Generator.get_element_length(pi_on2_element)

        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        gate_block = PulseBlock(name=name)

        for mw_length in tau_array:
            pi_x_length = mw_length / t_pi_on1

            mw_dd_element = self._get_mw_gate_ddxdd_element(phase, mw_freqs, mw_amps, rabi_periods,
                                                            ampl_gate=ampl_gate,
                                                            pi_x_length=pi_x_length, nv_order=nv_order,
                                                            dd_type=dd_type, dd_type_2=dd_type_2, dd_order=dd_order,
                                                            dd_tau=tau1)

            for idx_gate, i_gate in enumerate(range(n_gate_reps)):
                gate_block.extend(mw_dd_element)

            gate_block.append(laser_element)
            gate_block.append(delay_element)
            gate_block.append(waiting_element)

            if alternating:
                for i_gate in range(n_gate_reps):
                    gate_block.extend(mw_dd_element)

                gate_block.extend(pi_on1_element)

                gate_block.append(laser_element)
                gate_block.append(delay_element)
                gate_block.append(waiting_element)

        created_blocks.append(gate_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((gate_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2*number_of_lasers if alternating else number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def generate_mw_gate_dd_x_dd_ampl(self, name='gate_dd', ampl_start=1e-3, ampl_step=10e-3, num_of_points=10,
                                 tau1=100e-9, phase=0, t_mw_gate='', n_gate_reps=1,
                                 f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                                 nv_order='1,2',
                                 dd_type=DDMethods.SE, dd_type_2='', dd_order=1, alternating=False,
                                 ):

        created_blocks, created_ensembles, created_sequences = list(), list(), list()

        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2),
                                                n_nvs=2, order_nvs=nv_order)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=0, n_nvs=2, order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=1, n_nvs=2, order_nvs=nv_order)
        mw_amps = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2), order_nvs=nv_order,
                                              n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2),
                                            n_nvs=2, order_nvs=nv_order)


        ampl_array = ampl_start + np.arange(num_of_points) * ampl_step

        pi_on1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                           pi_x_length=1, no_amps_2_idle=False,
                                           env_type=Evm.from_gen_settings)
        pi_on2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                             pi_x_length=1, no_amps_2_idle=False,
                                             env_type=Evm.from_gen_settings)
        t_pi_on1 = MultiNV_Generator.get_element_length(pi_on1_element)
        t_pi_on2 = MultiNV_Generator.get_element_length(pi_on2_element)

        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        gate_block = PulseBlock(name=name)

        for ampl_gate in ampl_array:
            if t_mw_gate is '' or t_mw_gate is None:
                pi_x_length = 1
            else:
                pi_x_length = t_mw_gate / t_pi_on1

            mw_dd_element = self._get_mw_gate_ddxdd_element(phase, mw_freqs, mw_amps, rabi_periods,
                                                            ampl_gate=ampl_gate,
                                                            pi_x_length=pi_x_length, nv_order=nv_order,
                                                            dd_type=dd_type, dd_type_2=dd_type_2, dd_order=dd_order,
                                                            dd_tau=tau1)

            for idx_gate, i_gate in enumerate(range(n_gate_reps)):
                gate_block.extend(mw_dd_element)

            gate_block.append(laser_element)
            gate_block.append(delay_element)
            gate_block.append(waiting_element)

            if alternating:
                for i_gate in range(n_gate_reps):
                    gate_block.extend(mw_dd_element)

                gate_block.extend(pi_on1_element)

                gate_block.append(laser_element)
                gate_block.append(delay_element)
                gate_block.append(waiting_element)

        created_blocks.append(gate_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((gate_block.name, 0))

        # Create and append sync trigger block if needed
        self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = ampl_array
        block_ensemble.measurement_information['units'] = ('V', '')
        block_ensemble.measurement_information['labels'] = ('gate_ampl', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = 2*number_of_lasers if alternating else number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences


    def _get_bb1_cp1_element(self, phase, mw_freqs, mw_amps, rabi_periods, pi_x_length=1.,
                             cp_on2=True, no_amps_2_idle_on2=False, env_type=Evm.from_gen_settings,
                             nv_order="1,2"):

        """
        Arb. rotation on 1 via BB1, decoupling on 2 via CP.
        """

        ampls_on_1 = self._create_param_array(None, mw_amps, idx_nv=0, n_nvs=2,
                                              order_nvs=nv_order)
        ampls_on_2 = self._create_param_array(None, mw_amps, idx_nv=1, n_nvs=2,
                                              order_nvs=nv_order)
        mw_freqs = self._create_param_array(None, mw_freqs, n_nvs=2, order_nvs=nv_order)
        rabi_periods = self._create_param_array(None, rabi_periods, n_nvs=2, order_nvs=nv_order)

        def pi_element_function(xphase, pi_x_length=1., on_nv=1, no_amps_2_idle=True):

            if on_nv == 1:
                ampl_pi = ampls_on_1
            elif on_nv == 2:
                ampl_pi = ampls_on_2
            else:
                raise ValueError

            return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                   pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle,
                                   env_type=env_type)

        pix = pi_x_length

        phi = phase
        beta = np.arccos(-pix % 2 * np.pi / (4 * np.pi)) / (2 * np.pi) * 360
        # BB1 composite pulse
        # split first rotation and insert to beginning and end [Rong, Du 2015]
        pix_c0_on1_element = pi_element_function(phi, pi_x_length=pix / 2, on_nv=1)
        pi_c1_on1_element = pi_element_function(phi + beta, on_nv=1)
        twopi_c2_on1_element = pi_element_function(phi + 3 * beta, on_nv=1, pi_x_length=2)
        pi_c3_on1_element = pi_element_function(phi + beta, on_nv=1)
        # decoupling on NV2. If no_amps_2_idle=False and ampl2=0, will yield a standard BB1 pulse
        pi_on2_element = pi_element_function(phi, on_nv=2, no_amps_2_idle=no_amps_2_idle_on2)

        comp_block = []
        comp_block.extend(pix_c0_on1_element)
        comp_block.extend(pi_c1_on1_element)
        if cp_on2:
            comp_block.extend(pi_on2_element)
        comp_block.extend(twopi_c2_on1_element)
        if cp_on2:
            comp_block.extend(pi_on2_element)
        comp_block.extend(pi_c3_on1_element)
        comp_block.extend(pix_c0_on1_element)

        return comp_block

    def generate_mw_gate_bb1_cpon2(self, name='gate_bb1', pix_start=0., pix_step=1/25, num_of_points=50,
                             f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                             phase=0., no_amps_2_idle_on2=False,
                             nv_order="1,2",
                             alternating=True, no_laser=False):
        """
        BB1 composite pulse on NV1. CP like (2x Pi_x pulses) on NV2.
        """

        def pi_element_function(xphase, on_nv=1, pi_x_length=1., no_amps_2_idle=True):

            on_nv_oc = on_nv
            if on_nv == '2,1':
                on_nv_oc = 1 if on_nv==2 else 2
                self.log.debug(f"Reversing oc pi_element nv_order: {nv_order}")

            # ampls_on_1/2 take care of nv_order already
            if on_nv == 1:
                ampl_pi = ampls_on_1
            elif on_nv == 2:
                ampl_pi = ampls_on_2
            else:
                raise ValueError

            return self.get_pi_element(xphase, mw_freqs, ampl_pi, rabi_periods,
                                       pi_x_length=pi_x_length, no_amps_2_idle=no_amps_2_idle,
                                       env_type=Evm.from_gen_settings)


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


        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()

        pi_on1_element = pi_element_function(0, on_nv=1, no_amps_2_idle=False)
        pi_on2_element = pi_element_function(0, on_nv=2, no_amps_2_idle=False)
        #t_pi_on1 = MultiNV_Generator.get_element_length(pi_on1_element)
        #t_pi_on2 = MultiNV_Generator.get_element_length(pi_on2_element)

        # get tau array for measurement ticks
        pix_array = pix_start + np.arange(num_of_points) * pix_step

        comp_block = PulseBlock(name=name)

        for pix in pix_array:

            comp_block.extend(self._get_bb1_cp1_element(phase, mw_freqs, amplitudes, rabi_periods,
                                                        pi_x_length=pix, cp_on2=True, nv_order=nv_order,
                                                        no_amps_2_idle_on2=no_amps_2_idle_on2))

            if not no_laser:
                comp_block.append(laser_element)
                comp_block.append(delay_element)
                comp_block.append(waiting_element)
    
            if alternating:
                comp_block.extend(self._get_bb1_cp1_element(phase, mw_freqs, amplitudes, rabi_periods,
                                                            pi_x_length=pix, cp_on2=True, nv_order=nv_order,
                                                            no_amps_2_idle_on2=no_amps_2_idle_on2))
                
                comp_block.extend(pi_on1_element)

                if not no_laser:
                    comp_block.append(laser_element)
                    comp_block.append(delay_element)
                    comp_block.append(waiting_element)


        created_blocks.append(comp_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((comp_block.name, 0))

        # Create and append sync trigger block if needed
        if not no_laser:
            self._add_trigger(created_blocks=created_blocks, block_ensemble=block_ensemble)

        # add metadata to invoke settings later on
        number_of_lasers = num_of_points * 2 if alternating else num_of_points
        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = pix_array
        block_ensemble.measurement_information['units'] = ('rad pi', '')
        block_ensemble.measurement_information['labels'] = ('Rot. angle', 'Signal')
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

    def _get_pi_oc_element(self, phases, freqs, on_nv=[1], pi_x_length=1, scale_ampl=[1]):

        if isinstance(on_nv, (int, float)):
            on_nv = [on_nv]
        on_nv = np.asarray(on_nv)
        if isinstance(scale_ampl, (int, float)):
            scale_ampl = [scale_ampl]
        if len(scale_ampl) == 1:
            scale_ampl = [scale_ampl]*len(on_nv)

        if not (len(scale_ampl) == len(on_nv)):
            raise ValueError(f"Optimal pulses require same length of on_nv= {on_nv} and scale= {scale_ampl}")

        if not (len(phases) == len(freqs) == len(on_nv)):
            raise ValueError(f"Optimal pulses require same length of phase= {phases}, freq= {freqs},"
                             f" on_nv= {on_nv} arrays.")

        file_i, file_q = [],[]
        for nv in on_nv:

            if len(on_nv) > 1:
                # try finding a pulse that is calculated to run in parallel on multiple nvs
                # if none available, just use pulses for each nv and play them in parallel
                other_nvs = on_nv[on_nv != nv]
                #self.log.debug(f"Searching for parallel= {other_nvs} oc_pulse")
                oc_pulse = self.get_oc_pulse(on_nv=nv, pix=pi_x_length, par_with_nvs=other_nvs)
                if len(oc_pulse) == 0:
                    #self.log.debug("Couldn't find")
                    oc_pulse = self.get_oc_pulse(on_nv=nv, pix=pi_x_length)
            else:
                oc_pulse = self.get_oc_pulse(on_nv=nv, pix=pi_x_length)
            if len(oc_pulse) != 1:
                raise ValueError(f"Couldn't find optimal pulse with params (pix= {pi_x_length},"
                                 f"on_nv= {on_nv})"
                                 f" in {self.optimal_control_assets_path}")
            oc_pulse = oc_pulse[0]

            file_i.append(os.path.basename(oc_pulse._file_i))
            file_q.append(os.path.basename(oc_pulse._file_q))


        generate_method = self._get_generation_method('oc_mw_multi_only')
        oc_blocks, _, _ = generate_method('optimal_pix', mw_freqs=self.list_2_csv(freqs), phases=self.list_2_csv(phases),
                                          filename_i=self.list_2_csv(file_i), filename_q=self.list_2_csv(file_q),
                                          folder_path=self.optimal_control_assets_path,
                                          scale_ampl=self.list_2_csv(scale_ampl))



        return oc_blocks[0]

    def _OLD_get_pi_oc_element(self, xphase, mw_freq, on_nv=1, pi_x_length=1):

        phases = np.unique(xphase)
        freqs = np.unique(mw_freq)

        if len(phases) != 1 or len(freqs) != 1:
            raise NotImplementedError("Optimal pulses are currently only possible with a single MW carrier frequency")

        oc_pulse = self.get_oc_pulse(on_nv=on_nv, pix=pi_x_length)
        if len(oc_pulse) != 1:
            raise ValueError(f"Couldn't find optimal pulse with params (pix= {pi_x_length, }on_nv= {on_nv})"
                             f" in {self.optimal_control_assets_path}")
        oc_pulse = oc_pulse[0]

        generate_method = self._get_generation_method('oc_mw_only')
        file_i_no_path = os.path.basename(oc_pulse._file_i)
        file_q_no_path = os.path.basename(oc_pulse._file_q)

        # optimal_control_methods are for only 1 nv, set global mw_freq for the generation
        self.save_microwave_frequency = self.microwave_frequency
        self.microwave_frequency = freqs[0]

        oc_blocks, _, _ = generate_method('optimal_pix', phase=phases[0],
                                          filename_amplitude=file_i_no_path, filename_phase=file_q_no_path,
                                          folder_path=self.optimal_control_assets_path)

        self.microwave_frequency = self.save_microwave_frequency

        return oc_blocks[0]


    def get_pi_element(self, xphase, mw_freqs, mw_amps, rabi_periods, mw_idle_amps=None,
                       pi_x_length=1., no_amps_2_idle=False, env_type=Evm.from_gen_settings,
                       comp_type=Comp.bare,
                       on_nv=None):
        """
         define a function to create phase shifted pi pulse elements
        :param xphase: phase shift
        :param pi_x_length: multiple of pi pulse. Eg. 0.5 => pi_half pulse
        :param no_amps_2_idle: if True, convert a pulse without any amplitude to waiting/idle. Else silently drop pulse.
        :param mw_idle_amps: if >0 on channels with mw_amps=0, add two pulses with a given amplitude
                             that compensate each other by (pi-) reversed phase.
        :return:
        """

        if no_amps_2_idle and len(mw_amps[mw_amps!=0])==0:
            # todo: may have unintended consequences in creation of pulse partition
            mw_amps = np.asarray([1e-99]*len(mw_amps))
            env_type = Evm.rectangle

        if mw_idle_amps is None:
            mw_idle_amps = np.asarray([0] * len(mw_freqs))
        assert len(mw_freqs) == len(mw_idle_amps)

        if pi_x_length < 0:
            self.log.debug(f"Pi lengths {pi_x_length} <0 transformed to phase shift +180° for {xphase}")
            pi_x_length = abs(pi_x_length)
            xphase = xphase + 180


        n_lines = len(mw_amps[mw_amps!=0]) + len(mw_idle_amps[mw_idle_amps!=0])
        lenghts = (pi_x_length * rabi_periods[mw_amps+mw_idle_amps!=0] / 2)
        phases = [float(xphase)] * n_lines
        amps = mw_amps[(mw_amps+mw_idle_amps)!=0]
        fs = mw_freqs[(mw_amps+mw_idle_amps)!=0]
        if amps.size > 0:
            lenghts[amps == 0] = np.max(lenghts[amps!=0])

        assert len(fs) == len(amps) == len(phases) == len(lenghts), f"Unqueal length of {fs}, {amps}, {phases}, {lenghts}"
        # idle_amps>0 only on channels with amps==0
        assert len(amps[amps!=0]) + len(mw_idle_amps[mw_idle_amps!=0]) == \
               len((mw_amps+mw_idle_amps)[(mw_amps+mw_idle_amps)!=0]) == n_lines

        if pi_x_length == 0.:
            return []

        env_type = self._get_envelope_settings(env_type)

        if comp_type == Comp.from_gen_settings:
            comp_type = Comp.bare

        if type(on_nv) != list:
            on_nv = [on_nv]

        if comp_type != Comp.bare:
            if on_nv is None:
                if comp_type != Comp.bb1:
                    raise ValueError(f"Composite pulse {comp_type.value} needs a on_nv specifier!")
                # bb1 can't be executed in parallel right now (like bare pi pulses can)
                # if no nv explicitly specified, auto infer
                if fs[0] == self.microwave_frequency:
                    on_nv = 1
                elif len(mw_freqs)==2 and fs[0] == mw_freqs[1]:
                    on_nv = 2
                else:
                    raise ValueError

            if on_nv == [1]:
                nv_order = "1,2"
            elif on_nv == [2]:
                nv_order = "2,1"
            else:
                raise ValueError("Parallel composite pulses not supported!")


            if env_type != self._get_envelope_settings(Evm.from_gen_settings):
                raise NotImplementedError("Currently, only support pulse envelope 'from_gen_settings'")

            self.log.debug(f"Composite pulse {comp_type.value}, on_nv={on_nv}")

            if comp_type == Comp.bb1:
                if n_lines != 1:
                    raise NotImplementedError("Currently, only support composite pulses on single frequency")

                # todo: provisional only, add a generic function that can generate different comp pulses
                comp_element = self._get_bb1_cp1_element(phases[0], mw_freqs, mw_amps, rabi_periods,
                                                        pi_x_length=pi_x_length, cp_on2=False, nv_order=nv_order,
                                                        no_amps_2_idle_on2=False)

            elif comp_type == Comp.bb1_cp2:
                comp_element = self._get_bb1_cp1_element(phases[0], mw_freqs, mw_amps, rabi_periods,
                                                        pi_x_length=pi_x_length, cp_on2=True, nv_order=nv_order,
                                                        no_amps_2_idle_on2=False)

            elif comp_type == Comp.mw_dd or comp_type == Comp.mw_ddxdd:
                is_ddxdd = (comp_type == comp_type == Comp.mw_ddxdd)
                dd_order = comp_type.parameters['dd_order']
                dd_type = comp_type.parameters['dd_type']
                dd_type_2 = comp_type.parameters.get('dd_type_2', '')
                dd_ampl_2 = comp_type.parameters.get('dd_ampl_2', None)
                dd_tau = comp_type.parameters.get('dd_tau')
                dd_rabi_period = comp_type.parameters['rabi_period']
                dd_rabi_phase = comp_type.parameters['rabi_phase']
                self.log.debug(f"Mw dd comp pulse (dd={dd_type}) with target rot {pi_x_length} pi, phase {phases[0]}")

                flipped_rabi = False

                if dd_ampl_2 is not None and len(mw_amps) == 2:
                    if nv_order == "1,2":
                        idx = 1
                    elif nv_order == "2,1":
                        idx = 0
                    else:
                        raise RuntimeError
                    # not general (n_lines > 2) preliminary helper to disable MW on NV2
                    amps[idx] = dd_ampl_2

                if comp_type == Comp.mw_dd and dd_order * dd_type.suborder %2 == 1:
                    # uneven dd_order will create a pi flip on NV1, balance by increasing the mw_time
                    flipped_rabi = True
                    pi_x_length += 1

                if dd_rabi_period is not None:
                    # compensate calibration
                    t_length_2pi = dd_rabi_period - ((1/4 - dd_rabi_phase/360)* dd_rabi_period)
                    if flipped_rabi:
                        t_length_2pi = dd_rabi_period - ((1 / 4 + dd_rabi_phase / 360) * dd_rabi_period)

                    common_rabi_period = rabi_periods[0]     # rabi_periods[on_nv[0]-1]
                    pi_x_length = pi_x_length* t_length_2pi/common_rabi_period
                    t_pix = 1/2*pi_x_length*common_rabi_period
                    self.log.debug(f"Compensating pi_x_length= {pi_x_length}/{t_pix} for calibrated rabi_period= {dd_rabi_period}"
                                   f" phase= {dd_rabi_phase}")

                if is_ddxdd:
                    comp_element = self._get_mw_gate_ddxdd_element(phases[0], mw_freqs, amps, rabi_periods,
                                                                pi_x_length=pi_x_length, nv_order=nv_order,
                                                                dd_type=dd_type, dd_type_2=dd_type_2, dd_order=dd_order, dd_tau=dd_tau)

                else:
                    comp_element = self._get_mw_gate_dd_element(phases[0], mw_freqs, amps, rabi_periods,
                                                               pi_x_length=pi_x_length, nv_order=nv_order,
                                                               dd_type=dd_type, dd_order=dd_order)
            else:
                raise ValueError
            return comp_element


        if env_type == Evm.rectangle or env_type == Evm.parabola or env_type == Evm.sin_n:
            if on_nv is not None:
                self.log.debug(f"On_nv= {on_nv} parameter ignored for envelope {env_type.name}")
            if len(mw_idle_amps[mw_idle_amps!=0]) == 0:
                return self._get_multiple_mw_mult_length_element(lengths=lenghts,
                                                                 increments=0,
                                                                 amps=amps,
                                                                 freqs=fs,
                                                                 phases=phases,
                                                                 envelope=env_type)
            else:
                mw_elements = []
                # on amp_idle channel, make pulse with reversed phases in 2nd half -> no net state change
                for idx in range(0,2):
                    for idx_ch, _ in enumerate(fs):
                        phases[idx_ch] = phases[idx_ch]+180 if idx==1 and mw_idle_amps[idx_ch] != 0else phases[idx_ch]

                    el = self._get_multiple_mw_mult_length_element(lengths=lenghts/2,
                                                                 increments=0,
                                                                 amps=amps+mw_idle_amps,
                                                                 freqs=fs,
                                                                 phases=phases,
                                                                 envelope=env_type)
                    mw_elements.extend(el)
                return mw_elements


        elif env_type == Evm.optimal:
            if len(mw_idle_amps) != 0:
                raise NotImplementedError("Ooptimal control pulses support no idle ampl != 0")
            return self._get_pi_oc_element(phases, fs, on_nv=on_nv, pi_x_length=pi_x_length)

        else:
            raise ValueError(f"Envelope type {env_type} not supported.")

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

    def _get_multiple_mw_mult_length_element(self, lengths, increments, amps=None, freqs=None, phases=None,
                                             envelope=Evm.from_gen_settings):
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
                                                        freqs=freqs, phases=phases,
                                                        envelope=envelope))

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

        array = [in_value] if in_value!=None else []
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

    def generate_t1_inits(self, name='T1', tau_start=1.0e-6, tau_step=1.0e-6,
                          f_mw_2="1e9", rabi_period_mw_2='0e-9', ampl_mw_2='0.',
                    num_of_points=50, init=TomoInit.none, alternating=False):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        if type(init) != list:
            init = [init]

        # create param arrays
        rabi_periods = self._create_param_array(self.rabi_period, csv_2_list(rabi_period_mw_2),
                                                n_nvs=2)
        ampls_on_1 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=0, n_nvs=2)
        ampls_on_2 = self._create_param_array(self.microwave_amplitude, csv_2_list(ampl_mw_2),
                                              idx_nv=1, n_nvs=2)
        mw_freqs = self._create_param_array(self.microwave_frequency, csv_2_list(f_mw_2),
                                            n_nvs=2)

        # get tau array for measurement ticks
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the elements
        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        pi_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                              mw_idle_amps=ampls_on_2)
        pi_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                              mw_idle_amps=ampls_on_1 )
        piy_on_1_element = self.get_pi_element(90, mw_freqs, ampls_on_1, rabi_periods,
                                               mw_idle_amps=ampls_on_2 )
        piy_on_2_element = self.get_pi_element(90, mw_freqs, ampls_on_2, rabi_periods,
                                               mw_idle_amps=ampls_on_1 )
        pi2_on_1_element = self.get_pi_element(0, mw_freqs, ampls_on_1, rabi_periods,
                                               pi_x_length=0.5,
                                               mw_idle_amps=ampls_on_2)
        pi2_on_2_element = self.get_pi_element(0, mw_freqs, ampls_on_2, rabi_periods,
                                               pi_x_length=0.5,
                                               mw_idle_amps=ampls_on_1)
        pi2y_on_1_element = self.get_pi_element(90, mw_freqs, ampls_on_1, rabi_periods,
                                                pi_x_length=0.5, mw_idle_amps=ampls_on_2)
        pi2y_on_2_element = self.get_pi_element(90, mw_freqs, ampls_on_2, rabi_periods,
                                                pi_x_length=0.5,
                                                mw_idle_amps=ampls_on_1)

        def init_element(init_state):
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
                # init_elements = pi_on_both_element
                init_elements = cp.deepcopy(pi_on_1_element)
                init_elements.extend(pi_on_2_element)
            elif init_state == TomoInit.ux90_on_1_uy90_on_2:
                init_elements = cp.deepcopy(pi2_on_1_element)
                init_elements.extend(pi2y_on_2_element)
            elif init_state == TomoInit.ux90_on_1_ux180_on_2:
                init_elements = cp.deepcopy(pi2_on_1_element)
                init_elements.extend(pi_on_2_element)
            else:
                raise ValueError(f"Unknown tomography init state: {init_state.name}")
            return init_elements


        tau_element = self._get_idle_element(length=tau_start, increment=tau_step)
        t1_block = PulseBlock(name=name)
        for init_el in init:
            t1_block.extend(init_element(init_el))
        t1_block.append(tau_element)
        t1_block.append(laser_element)
        t1_block.append(delay_element)
        t1_block.append(waiting_element)
        if alternating:
            for init_el in init:
                t1_block.extend(init_element(init_el))
            t1_block.append(pi_on_1_element)
            t1_block.append(tau_element)
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



