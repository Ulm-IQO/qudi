import numpy as np
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.pulsed.pulse_objects import PredefinedGeneratorBase

#from logic.pulsed.sampling_function_defs.sampling_functions_nvision import EnvelopeMethods
from logic.pulsed.pulse_objects import PulseEnvelopeType as Evm
from logic.pulsed.predefined_generate_methods.basic_methods_polarization_nvision import NVisionPolarizationGenerator
from logic.pulsed.predefined_generate_methods.multi_nv_methods import DQTAltModes, TomoRotations, TomoInit

from logic.pulsed.sampling_functions import DDMethods
from core.util.helpers import csv_2_list

from user_scripts.Timo.own.console_toolkit import Tk_file, Tk_string



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
        self._init_custom_generation_params()

        self.gen_nvision = NVisionPolarizationGenerator(*args, **kwargs)

    def _init_custom_generation_params(self):

        self.t_laser_fci_red = 2.5e-6
        self.t_laser_fci_green = 0.5e-6
        self.t_wait_fci = 1e-6
        self.t_safety_fci = 1e-6
        self.laser_read_red_ch = 'd_ch3'
        self.done_fci_ch = 'd_ch1'
        self.add_gate_ch = 'd_ch4'   # additional gate channel to open APD switch

    def _get_generation_method(self, method_name):
        # evil access to all loaded generation methods. Use carefully.
        return self._PredefinedGeneratorBase__sequencegeneratorlogic.generate_methods[method_name]

    @property
    def t_laser_fci_red(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['t_laser_fci_red']
        except KeyError:
            return None

    @t_laser_fci_red.setter
    def t_laser_fci_red(self, t_laser):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'t_laser_fci_red': t_laser})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @property
    def t_laser_fci_green(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['t_laser_fci_green']
        except KeyError:
            return None

    @t_laser_fci_green.setter
    def t_laser_fci_green(self, t_laser):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'t_laser_fci_green': t_laser})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @property
    def t_wait_fci(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['t_wait_fci']
        except KeyError:
            return None

    @t_wait_fci.setter
    def t_wait_fci(self, t_laser):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'t_wait_fci': t_laser})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @property
    def t_safety_fci(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['t_safety_fci']
        except KeyError:
            return None

    @t_safety_fci.setter
    def t_safety_fci(self, t_laser):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'t_safety_fci': t_laser})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @property
    def laser_read_red_ch(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['laser_read_red_ch']
        except KeyError:
            return None

    @laser_read_red_ch.setter
    def laser_read_red_ch(self, laser_ch):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'laser_read_red_ch': laser_ch})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @property
    def done_fci_ch(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['done_fci_ch']
        except KeyError:
            return None

    @done_fci_ch.setter
    def done_fci_ch(self, laser_ch):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'done_fci_ch': laser_ch})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

    @property
    def add_gate_ch(self):
        try:
            gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
            return gen_params['add_gate_ch']
        except KeyError:
            return None

    @add_gate_ch.setter
    def add_gate_ch(self, laser_ch):
        gen_params = self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters
        gen_params.update({'add_gate_ch': laser_ch})
        self._PredefinedGeneratorBase__sequencegeneratorlogic.generation_parameters = gen_params

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

    def _add_ensemble_to_seqtable(self, blocks, ensemble, name, seq_params=None):
        cur_seq_params = self._get_default_seq_params(seq_params)
        self._add_to_seqtable(name, blocks, ensemble, cur_seq_params)

    def generate_rabi_fci(self, name='rabi_fci', tau_start=10.0e-9, tau_step=10.0e-9, num_of_points=50,
                          t_cinit_green=500e-9, t_cinit_red=10e-6,
                          t_wait_between=1e-6, t_aom_safety=750e-9,
                          laser_red_ch='d_ch3', add_gate_ch='', done_ch='d_ch1'
                          ):

        """
        Sequence for charge readout. Init charge with fast charge readout as in Hopper (2020).
        Analysis of the data requires listmode acquisition to create a photon number histogram.
        """

        total_name = name

        generate_method = self._get_generation_method('rabi')
        single_mw_name = 'rabi'

        tau_array = tau_start + np.arange(num_of_points) * tau_step
        for idx, tau in enumerate(tau_array):
            # mw method must have green laser at end!
            cur_name = f"{single_mw_name}_{idx}"

            single_mw_blocks, single_mw_ensembles, _ = generate_method(name=cur_name, tau_start=tau,
                                                                       tau_step=0, num_of_points=1,
                                                                       # suppress fci counting during normal readout
                                                                       add_gate_ch=f"{add_gate_ch},{done_ch}",
                                                                       #short_laser=idx/len(tau_array)*10)
                                                                       )
            # single generic method creates most of the mes info, only set multiple tau here
            single_mw_ensembles[0].measurement_information['controlled_variable'] = tau_array
            single_mw_ensembles[0].measurement_information['number_of_lasers'] = len(tau_array)

            blocks, enembles, sequences = self.generic_nv_minus_init(total_name=total_name, generic_name=cur_name,
                                                                     generic_blocks=single_mw_blocks, generic_ensemble=single_mw_ensembles,
                                                                     t_init=t_cinit_green, t_read=t_cinit_red,
                                                                     laser_read_ch=laser_red_ch,
                                                                     ch_trigger_done=done_ch, add_gate_ch=add_gate_ch,
                                                                     t_aom_safety=t_aom_safety, t_wait_between=t_wait_between,
                                                                     continue_seqtable=(idx!=0))

        return blocks, enembles, sequences


    def generate_deer_dd_tau_fci(self, name='deer_dd_tau_fci', tau1=0.5e-6, tau_start=0e-6, tau_step=0.01e-6, num_of_points=50,
                                 f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="10e-9, 10e-9, 10e-9",
                                 dd_type=DDMethods.SE, dd_type_2='', dd_order=1,
                                 init_pix_on_1=0, init_pix_on_2=0,
                                 start_pix_on_1=0.5, end_pix_on_1=0.5, end_pix_on_2=0, read_pix_on_2=0,
                                 nv_order="1,2", read_phase_deg=90, env_type_1=Evm.from_gen_settings,
                                 env_type_2=Evm.from_gen_settings,
                                 alternating=True, no_laser=False,
                                 t_cinit_green=500e-9, t_cinit_red=10e-6,
                                 t_wait_between=1e-6, t_aom_safety=750e-9,
                                 laser_red_ch='d_ch3', add_gate_ch='', done_ch='d_ch1'
                                 ):
        """
        Sequence for charge readout. Init charge with fast charge readout as in Hopper (2020).
        Analysis of the data requires listmode acquisition to create a photon number histogram.
        """
        total_name = name

        generate_method = self._get_generation_method('deer_dd_tau')
        single_mw_name = 'deer_dd_tau'

        tau_array = tau_start + np.arange(num_of_points) * tau_step
        for idx, tau in enumerate(tau_array):
            # mw method must have green laser at end!
            cur_name = f"{single_mw_name}_{idx}"

            single_mw_blocks, single_mw_ensembles, _ = generate_method(name=cur_name, tau_start=tau,
                                                                       tau_step=0, num_of_points=1,
                                                                       tau1=tau1, f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                       rabi_period_mw_2=rabi_period_mw_2, dd_type=dd_type,
                                                                       dd_type_2=dd_type_2, dd_order=dd_order,
                                                                       init_pix_on_1=init_pix_on_1, init_pix_on_2=init_pix_on_2,
                                                                       start_pix_on_1=start_pix_on_1, end_pix_on_1=end_pix_on_1,
                                                                       end_pix_on_2=end_pix_on_2, read_pix_on_2=read_pix_on_2,
                                                                       nv_order=nv_order, read_phase_deg=read_phase_deg,
                                                                       env_type_1=env_type_1, env_type_2=env_type_2,
                                                                       alternating=False, no_laser=no_laser,
                                                                       # suppress fci counting during normal readout
                                                                       add_gate_ch=f"{add_gate_ch},{done_ch}")
            # single generic method creates most of the mes info, only set multiple tau here
            single_mw_ensembles[0].measurement_information['controlled_variable'] = tau_array
            single_mw_ensembles[0].measurement_information['number_of_lasers'] = 2*len(tau_array) if alternating else len(tau_array)
            single_mw_ensembles[0].measurement_information['alternating'] = alternating

            blocks, enembles, sequences = self.generic_nv_minus_init(total_name=total_name, generic_name=cur_name,
                                                                     generic_blocks=single_mw_blocks, generic_ensemble=single_mw_ensembles,
                                                                     t_init=t_cinit_green, t_read=t_cinit_red,
                                                                     laser_read_ch=laser_red_ch,
                                                                     ch_trigger_done=done_ch, add_gate_ch=add_gate_ch,
                                                                     t_aom_safety=t_aom_safety, t_wait_between=t_wait_between,
                                                                     continue_seqtable=(idx!=0))

            if alternating:
                cur_name = f"{single_mw_name}_{idx}_alt"

                single_mw_blocks, single_mw_ensembles, _ = generate_method(name=cur_name, tau_start=tau,
                                                                           tau_step=0, num_of_points=1,
                                                                           tau1=tau1, f_mw_2=f_mw_2,
                                                                           ampl_mw_2=ampl_mw_2,
                                                                           rabi_period_mw_2=rabi_period_mw_2,
                                                                           dd_type=dd_type,
                                                                           dd_type_2=dd_type_2, dd_order=dd_order,
                                                                           init_pix_on_1=init_pix_on_1, init_pix_on_2=init_pix_on_2,
                                                                           start_pix_on_1=start_pix_on_1, end_pix_on_1=end_pix_on_1,
                                                                           end_pix_on_2=end_pix_on_2, read_pix_on_2=read_pix_on_2,
                                                                           nv_order=nv_order,
                                                                           read_phase_deg=180+read_phase_deg,
                                                                           env_type_1=env_type_1, env_type_2=env_type_2,
                                                                           alternating=False, no_laser=no_laser,
                                                                           # suppress fci counting during normal readout
                                                                           add_gate_ch=f"{add_gate_ch},{done_ch}",
                                                                           )
                # single generic method creates most of the mes info, only set multiple tau here
                single_mw_ensembles[0].measurement_information['controlled_variable'] = tau_array
                single_mw_ensembles[0].measurement_information['number_of_lasers'] = 2*len(tau_array) if alternating else len(tau_array)
                single_mw_ensembles[0].measurement_information['alternating'] = alternating

                blocks, enembles, sequences = self.generic_nv_minus_init(total_name=total_name, generic_name=cur_name,
                                                                         generic_blocks=single_mw_blocks,
                                                                         generic_ensemble=single_mw_ensembles,
                                                                         t_init=t_cinit_green, t_read=t_cinit_red,
                                                                         laser_read_ch=laser_red_ch,
                                                                         ch_trigger_done=done_ch,
                                                                         add_gate_ch=add_gate_ch,
                                                                         t_aom_safety=t_aom_safety,
                                                                         t_wait_between=t_wait_between,
                                                                         continue_seqtable=True)

        return blocks, enembles, sequences

    def generate_charge_read_fci(self, name='charge_read_fci', t_cinit_green=500e-9, t_cinit_red=10e-6,
                                 t_cread_red=50e-6,  t_wait_between=1e-6, t_aom_safety=750e-9,
                                 laser_red_ch='d_ch3', add_gate_ch='', done_ch='d_ch1'
                                 ):

        """
        Sequence for charge readout. Init charge with fast charge readout as in Hopper (2020).
        Analysis of the data requires listmode acquisition to create a photon number histogram.
        """

        total_name = name

        generate_method = self._get_generation_method('laser_strob')
        cur_name = 'charge_read'
        cur_blocks, cur_ensembles, _ = generate_method(name=cur_name, t_laser_read=t_cread_red,
                                                       t_laser_init=0, t_wait_between=0, laser_read_ch=laser_red_ch,
                                                       # suppress fci counting during (long) charge read by const reset
                                                       add_gate_ch=f"{add_gate_ch},{done_ch}",
                                                       t_aom_safety=t_aom_safety)

        blocks, enembles, sequences = self.generic_nv_minus_init(total_name=total_name, generic_name=cur_name,
                                                                 generic_blocks=cur_blocks, generic_ensemble=cur_ensembles,
                                                                 t_init=t_cinit_green, t_read=t_cinit_red,
                                                                 laser_read_ch=laser_red_ch,
                                                                 ch_trigger_done=done_ch, add_gate_ch=add_gate_ch,
                                                                 t_aom_safety=t_aom_safety, t_wait_between=t_wait_between)

        return blocks, enembles, sequences


    def generate_rand_benchmark_fci(self, name='random_benchmark_fci', xticks='',
                            rotations="[[<TomoRotations.none: 0>,];]",
                            tau_cnot=0e-9, dd_type_cnot=DDMethods.SE, dd_order=1, t_idle=0e-9,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                            alternating=False,
                            init_state_kwargs='', cnot_kwargs=''):
        """
        Init charge with fast charge readout as in Hopper (2020).
        Analysis of the data requires listmode acquisition to create a photon number histogram.
        """
        total_name = name

        generate_method = self._get_generation_method('rand_benchmark')
        single_mw_name = 'rand_benchmark'

        str_lists = csv_2_list(rotations, str_2_val=str, delimiter=';')  # to list of csv strings
        rotations_list = [csv_2_list(el, str_2_val=Tk_string.str_2_enum) for el in str_lists]
        # get tau array for measurement ticks
        idx_array = list(range(len(rotations_list)))
        xticks_list = csv_2_list(xticks)
        if xticks_list:
            # expand xaxis. Multiple random sequences for a single n_cliff are collapsed to same tick
            if len(xticks_list) < len(idx_array):
                xticks_list = np.asarray([[x]*int(len(rotations_list)/len(xticks_list)) for x in xticks_list]).flatten()
        num_of_points = len(idx_array)

        mw_readout_gate_ch = f"{self.add_gate_ch},{self.done_fci_ch}"
        self.log.debug(f"idx_array {idx_array}, xticks: {xticks_list}, num {num_of_points}, gate_read_ch= {mw_readout_gate_ch}")

        for idx, rotation in enumerate(rotations_list):
            # mw method must have green laser at end!
            cur_name = f"{single_mw_name}_{idx}"
            self.log.debug(f"Generating rot {rotation}")
            single_mw_blocks, single_mw_ensembles, _ = generate_method(name=cur_name, xticks='',
                                                                        rotations=self.list_2_csv(rotation),  # todo: double check no read rot
                                                                        tau_cnot=tau_cnot, dd_type_cnot=dd_type_cnot,
                                                                        dd_order=dd_order, t_idle=t_idle,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        alternating=False,
                                                                        init_state_kwargs=init_state_kwargs,
                                                                        cnot_kwargs=cnot_kwargs,
                                                                       # suppress fci counting during normal readout
                                                                       add_gate_ch=mw_readout_gate_ch,
                                                                       )
            # single generic method creates most of the mes info, only set multiple tau here
            single_mw_ensembles[0].measurement_information['controlled_variable'] = idx_array if xticks_list==[] else xticks_list
            single_mw_ensembles[0].measurement_information['number_of_lasers'] = 2*num_of_points if alternating else num_of_points
            single_mw_ensembles[0].measurement_information['alternating'] = alternating

            blocks, enembles, sequences = self.generic_nv_minus_init(total_name=total_name, generic_name=cur_name,
                                                                     generic_blocks=single_mw_blocks, generic_ensemble=single_mw_ensembles,
                                                                     t_init=self.t_laser_fci_green, t_read=self.t_laser_fci_red,
                                                                     laser_read_ch=self.laser_read_red_ch,
                                                                     ch_trigger_done=self.done_fci_ch, add_gate_ch=self.add_gate_ch,
                                                                     t_aom_safety=self.t_safety_fci, t_wait_between=self.t_wait_fci,
                                                                     continue_seqtable=(idx!=0))

            if alternating:
                cur_name = f"{single_mw_name}_{idx}_alt"
                read_rotations = [TomoRotations.ux180_on_1, TomoRotations.ux180_on_2]

                single_mw_blocks, single_mw_ensembles, _ = generate_method(name=cur_name, xticks='',
                                                                        rotations=self.list_2_csv(rotation),
                                                                        read_rots=read_rotations,
                                                                        tau_cnot=tau_cnot, dd_type_cnot=dd_type_cnot,
                                                                        dd_order=dd_order, t_idle=t_idle,
                                                                        f_mw_2=f_mw_2, ampl_mw_2=ampl_mw_2,
                                                                        rabi_period_mw_2=rabi_period_mw_2,
                                                                        alternating=False,
                                                                        init_state_kwargs=init_state_kwargs,
                                                                        cnot_kwargs=cnot_kwargs,
                                                                       # suppress fci counting during normal readout
                                                                       add_gate_ch=mw_readout_gate_ch,
                                                                       )
                # single generic method creates most of the mes info, only set multiple tau here
                single_mw_ensembles[0].measurement_information[
                    'controlled_variable'] = idx_array if xticks_list == [] else xticks_list
                single_mw_ensembles[0].measurement_information[
                    'number_of_lasers'] = 2 * num_of_points if alternating else num_of_points
                single_mw_ensembles[0].measurement_information['alternating'] = alternating

                blocks, enembles, sequences = self.generic_nv_minus_init(total_name=total_name, generic_name=cur_name,
                                                                         generic_blocks=single_mw_blocks,
                                                                         generic_ensemble=single_mw_ensembles,
                                                                         t_init=self.t_laser_fci_green,
                                                                         t_read=self.t_laser_fci_red,
                                                                         laser_read_ch=self.laser_read_red_ch,
                                                                         ch_trigger_done=self.done_fci_ch,
                                                                         add_gate_ch=self.add_gate_ch,
                                                                         t_aom_safety=self.t_safety_fci,
                                                                         t_wait_between=self.t_wait_fci,
                                                                         continue_seqtable=True)



        return blocks, enembles, sequences


    def generate_tomogphry_fci(self, name='tomography', tau_start=10.0e-9, tau_step=10.0e-9,
                            rabi_on_nv=1, rabi_phase_deg=0, rotation=TomoRotations.none, init_state=TomoInit.none,
                            num_of_points=50,
                            tau_cnot=0e-9, dd_type_cnot=DDMethods.SE, dd_order=1,
                            f_mw_2="1e9,1e9,1e9", ampl_mw_2="0.125, 0, 0", rabi_period_mw_2="100e-9, 100e-9, 100e-9",
                            alternating=False, init_state_kwargs='', cnot_kwargs=''):
        pass


    def generic_nv_minus_init(self, total_name='generic_nvinit', generic_name="generic_method",
                              t_init=3e-6, t_read=10e-6, t_aom_safety=750e-9, t_wait_between=1e-6,
                              generic_blocks=None, generic_ensemble=None,
                              ch_trigger_done='d_ch1', laser_read_ch='d_ch3', add_gate_ch='',
                              alternating=False, continue_seqtable=False):
        """
        Prepends a deterministic (Hopper) readout to some generic predefined method.
        This version is meant to be used with a linear sequencer, as Keysight M8190A.
        """
        # for linear sequencers like Keysight AWG
        # self.init_jumptable()  # jumping currently not needed
        if not continue_seqtable:
            self.init_seqtable()
        general_params = locals()

        # charge init by repeating (green, res) until a photon threshold is signaled by ext hw
        # repeat init indefintely is done by segment advance mode==conditional + trigger mode==contiunous

        # epoch done trigger for signaling finished sequence and reset of external hw
        # to reset counter with every green-red combination, add epoch_done into the laser_strob segment
        done_name = 'epoch_done'
        done_blocks, done_ensembles, _ = self._create_generic_trigger(done_name, ch_trigger_done)
        self._add_to_jumptable(done_name)
        self._add_ensemble_to_seqtable(done_blocks, done_ensembles, done_name,
                                       seq_params={'repetitions': int(0)})



        init_name = 'nvmin_init'
        generate_method = self._get_generation_method('laser_strob')
        init_seq_params = self._get_default_seq_params({'repetitons': 0,
                                                       'segment_advance_mode': 'conditional'})
        init_blocks, init_ensembles, _ = generate_method(name=init_name, t_laser_read=t_read,
                             t_laser_init=t_init, t_wait_between=t_wait_between, laser_read_ch=laser_read_ch,
                             add_gate_ch=add_gate_ch, read_no_fc_gate=True, epoch_done_ch=ch_trigger_done,
                             t_aom_safety=t_aom_safety, init_laser_first=True)

        self._add_to_jumptable(init_name)
        self._add_ensemble_to_seqtable(init_blocks, init_ensembles, init_name,
                                       seq_params=init_seq_params)
                                       #seq_params = {'repetitions': int(5)})


        # add generic method after init
        if generic_blocks and generic_ensemble:
            cur_seq_params = self._get_default_seq_params({'repetitons': 0})
            self._add_to_jumptable(generic_name)
            self._add_ensemble_to_seqtable(generic_blocks, generic_ensemble, generic_name,
                                           seq_params=cur_seq_params)




        all_blocks, all_ensembles, ensemble_list = self._seqtable_to_result()
        sequence = PulseSequence(name=total_name, ensemble_list=ensemble_list, rotating_frame=False)

        # take measurement info for sequence from generic_method ensemble
        idx_read = 2
        ensemble_info = all_ensembles[idx_read].measurement_information
        sequence.measurement_information = ensemble_info
        #fastcounter_count_length = self._get_ensemble_count_length(all_ensembles[idx_read],
        #                                                           created_blocks=all_blocks)



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
            seq_para_dict['go_to'] = -1
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

        idle_element = self._get_idle_element(1e-9, increment=0)
        trig_element =  self._get_trigger_element(length=10e-9, increment=0., channels=channels)  # todo: length of trigger element?
        block = PulseBlock(name=name)
        #block.append(idle_element) # todo: remove idle, only for debug
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

