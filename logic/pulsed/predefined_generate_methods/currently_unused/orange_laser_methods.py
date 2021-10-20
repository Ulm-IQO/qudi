import numpy as np
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
#from logic.pulsed.pulse_objects import PredefinedGeneratorBase
from logic.pulsed.predefined_generate_methods.helper_methods_setup3 import HelperMethods



class OrangeLaserGeneratorS3(HelperMethods):
    """

    """

    # simplyfy the call of the imported functions
    # hm =  HelperMethods(PredefinedGeneratorBase)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def generate_orange_distribution(self, name='Orange', length_orange=1e-6, counts_per_readout=1000, idle_end=1e-6):
        """
        """


        # get the laser ensemble
        created_blocks, created_ensembles, created_sequences = \
            self.generate_trigger(name='orange', tau=length_orange, digital_channel=self.sync_channel)
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
        laser_list = ['orange', seq_param]
        # get the idle element
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name='Idle', tau=idle_end)
        seq_param =  self._customize_seq_para({})
        idle_list = ['Idle', seq_param]
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        #  bring the individual blocks in the correct order
        element_list = list([laser_list.copy(), idle_list.copy()])
        # make sequence continousbetween
        element_list = self._make_sequence_continous(element_list)

        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=[0], units=('au', 'au'),
                                       number_of_lasers=1,
                                       labels=('nothing', 'nothing'),
                                       counting_length=length_orange*1.002)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences


    def generate_orange_distribution2(self, name='Orange', length_orange=3e-6, idle_orange=0.5e-6):
        """
        Without sequence mode
        """
        created_blocks = list()
        created_ensembles = list()


        ### fill up to minimum length of 4800 if necessary
        if (length_orange+idle_orange) * self.pulse_generator_settings['sample_rate'] < 4800:
            idle_orange = self._adjust_to_samplingrate(4800 / self.pulse_generator_settings['sample_rate']-length_orange, 2)
            self.log.warning('Idle duration adusted to minimum sequence length of {0} for samplingrate '
                             '{1}'.format(idle_orange, self.pulse_generator_settings['sample_rate']))
        else:
            # prevent granularity problems
            idle_orange = self._adjust_to_samplingrate(length_orange + idle_orange, 2) - length_orange

        # get the elements
        laser_element = self._get_trigger_element(length=length_orange, increment=0.0, channels=self.sync_channel)
        idle_element = self._get_idle_element(length=idle_orange, increment=0.0)

        block = PulseBlock(name=name)
        block.append(laser_element)
        block.append(idle_element)
        created_blocks.append(block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((block.name, 0))
        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=[0], units=('au', 'au'),
                                       number_of_lasers=1,
                                       labels=('nothing', 'nothing'),
                                       counting_length=length_orange*1.002)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, list()




    def generate_green_distribution(self, name='Green', length_green = 500e-9, repetitions_green = 1,
                                    idle_between = 500e-9, length_orange=1e-6, idle_orange=1e-6,
                                    counts_per_readout=1000, idle_end=1e-6):
        """
        """

        # get the green laser ensemble
        created_blocks, created_ensembles, created_sequences = \
            self.generate_laser(name='green_laser', tau=length_green)
        seq_param = self._customize_seq_para({'repetitions': repetitions_green-1})
        green_laser_list = ['green_laser', seq_param]

        # get the orange laser element
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name='orange_laser', trigger_length=length_orange/counts_per_readout,
                                       wait_length=idle_orange, digital_channel=self.sync_channel)
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
        orange_laser_list = ['orange_laser', seq_param]
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # get the idle elements
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name='Idle_between', tau=idle_between)
        seq_param =  self._customize_seq_para({})
        idle_between_list = ['Idle_between', seq_param]
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name='Idle_end', tau=idle_end)
        seq_param =  self._customize_seq_para({})
        idle_end_list = ['Idle_end', seq_param]
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        #  bring the individual blocks in the correct order
        element_list = list([green_laser_list.copy(), idle_between_list.copy(),
                             orange_laser_list.copy(),idle_end_list.copy()])
        # make sequence continous
        element_list = self._make_sequence_continous(element_list)

        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=[0], units=('au', 'au'),
                                       number_of_lasers=1,
                                       labels=('nothing', 'nothing'),
                                       counting_length=length_orange/counts_per_readout*1.025)

        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences


##################################### Combined with SSR experiments #############################



    def generate_orange_ssr_contrast_mapping(self, name='Orange_SSR-Contrast', rabi_period=1.0e-7, include_pi2=False,
                                             orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                 #laser_name='laser_wait',
                                             laser_length=1e-6, wait_length=1e-6,
                                             rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                             rf_cnot_duration=100e-6, rf_cnot_phase=0,
                                             ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=20e-9,
                                             mw_cnot_amplitude=1.0, mw_cnot_frequency=2.8e9,
                                             mw_cnot_phase=0, mw_cnot_rabi_period2=20e-9,
                                             mw_cnot_amplitude2=1.0, mw_cnot_frequency2=2.8e9,
                                             mw_cnot_phase2=0, ssr_normalise=True, counts_per_readout=1000,
                                             idle_step_name='IDLE', idle_step_length=2e-6):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()


        # generate the Rabi pieces
        if include_pi2:
            tau_array = np.array([0, rabi_period / 4.0, rabi_period / 2.0])
        else:
            tau_array = np.array([0,rabi_period/2.0])
        #self.log.warning(locals())
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse(name=name_tmp, tau=tau,
                                              microwave_amplitude=self.microwave_amplitude,
                                              microwave_frequency=self.microwave_frequency, microwave_phase=0.0)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_ssr_mapping_orange(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', ''), number_of_lasers=len(tau_array),
                                       labels=('Tau', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences

    def generate_orange_ssr_rabi_mapping(self, name='Orange_SSR-Rabi', tau_start=1.0e-9, tau_step=1.0e-9, num_of_points=50,
                                         orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                         #        laser_name='laser_wait',
                                         laser_length=1e-6, wait_length=1e-6,
                                         rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                         rf_cnot_duration=100e-6, rf_cnot_phase=0,
                                         ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=20e-9,
                                         mw_cnot_amplitude=1.0, mw_cnot_frequency=2.8e9,
                                         mw_cnot_phase=0, mw_cnot_rabi_period2=20e-9,mw_cnot_amplitude2=1.0, mw_cnot_frequency2=2.8e9,
                                         mw_cnot_phase2=0, ssr_normalise=True, counts_per_readout=1000,
                                         idle_step_name='IDLE', idle_step_length=2e-6):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # generate the Rabi pieces
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse(name=name_tmp, tau=tau,
                                              microwave_amplitude=self.microwave_amplitude,
                                              microwave_frequency=self.microwave_frequency, microwave_phase=0.0)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_ssr_mapping_orange(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', ''), number_of_lasers=num_of_points,
                                       labels=('Tau', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences


    def generate_orange_ssr_xy8_mapping(self, name='Orange_SSR-XY8', rabi_period=1e-7, tau_start=1.0e-6, tau_step=1.0e-6,
                                        num_of_points=50, xy8_order=4,
                                        orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                 #laser_name='laser_wait',
                                        laser_length=1e-6, wait_length=1e-6,
                                        rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1, rf_cnot_duration=100e-6,
                                        rf_cnot_phase=0,
                                        ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=20e-9,
                                        mw_cnot_amplitude=1.0, mw_cnot_frequency=2.8e9,
                                        mw_cnot_phase=0,mw_cnot_rabi_period2=20e-9, mw_cnot_amplitude2=1.0, mw_cnot_frequency2=2.8e9,
                                        mw_cnot_phase2=0, ssr_normalise=True, counts_per_readout=1000,
                                        idle_step_name='IDLE', idle_step_length=2e-6):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # make sure the taus correspond to the sampling rate
        tau_start = self._adjust_to_samplingrate(tau_start, 2)
        tau_step = self._adjust_to_samplingrate(tau_step, 2)
        tau_array = tau_start + np.arange(num_of_points) * tau_step


        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_xy8_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                                              microwave_amplitude=self.microwave_amplitude,
                                              microwave_frequency=self.microwave_frequency, xy8N=xy8_order)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_ssr_mapping_orange(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', ''), number_of_lasers=num_of_points,
                                       labels=('Tau', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences


    def generate_orange_ssr_xy8N_sweep_mapping(self, name='Orange_SSR-XY8', rabi_period=1e-6, n_start=1,
                                               n_step=1, num_of_points=50, tau=400e-9,
                                               orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                 #laser_name='laser_wait',
                                               laser_length=1e-6, wait_length=1e-6,
                                               rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                               rf_cnot_duration=100e-6, rf_cnot_phase=0,
                                               ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=20e-9,
                                               mw_cnot_amplitude=1.0, mw_cnot_frequency=2.8e9,
                                               mw_cnot_phase=0, mw_cnot_rabi_period2=20e-9,
                                               mw_cnot_amplitude2=1.0, mw_cnot_frequency2=2.8e9,
                                               mw_cnot_phase2=0, ssr_normalise=True, counts_per_readout=1000,
                                               idle_step_name='IDLE', idle_step_length=2e-6):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # make sure the taus correspond to the sampling rate
        n_array = (n_start + np.arange(num_of_points) * n_step).astype(int)


        para_list = list()
        for number, xy8N in enumerate(n_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_xy8_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                                              microwave_amplitude=self.microwave_amplitude,
                                              microwave_frequency=self.microwave_frequency, xy8N=xy8N)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_ssr_mapping_orange(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=n_array*tau, units=('s', ''), number_of_lasers=num_of_points,
                                       labels=('Tau', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences



###################################### Full experiment with all parts ####################################

    def generate_hmh_c13_orange_xy8Nsweep_mapping_ssr(self, name='Total_Nsweep', n_start=1, n_step=1, num_of_points=5,
                                                      tau=1000e-9, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                                      microwave_frequency=2.8e9, microwave_phase=0.0, ylast=False,
                                                      hmh_name='HMH', spinlock_length=25e-6, hmh_amp=0.01,
                                                      hmh_frequency=2.8e9, hmh_phase=0.0, hmh_laser_length=500e-9,
                                                      hmh_wait_length=1e-6, repeat_pol=1, c13_name='C13_',
                                                      c13_rabi_period=100e-6, c13_amp=0.05, c13_freq=1e6, c13_phase=0.0,
                                                      orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                                      #laser_name='laser_wait',
                                                      laser_length=1e-6, wait_length=1e-6,
                                                      rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                                      rf_cnot_duration=100e-6, rf_cnot_phase=0,
                                                      ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                                      mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                                      mw_cnot_phase=0, mw_cnot_rabi_period2=2000e-9,
                                                      mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                                      mw_cnot_phase2=0, ssr_normalise=True, counts_per_readout=1000,
                                                      idle_step_name='IDLE', idle_step_length=2e-6):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # make sure the taus correspond to the sampling rate
        n_array = (n_start + np.arange(num_of_points) * n_step).astype(int)


        para_list = list()
        for number, xy8N in enumerate(n_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_xy8_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                                              microwave_amplitude=self.microwave_amplitude,
                                              microwave_frequency=self.microwave_frequency, xy8N=xy8N, ylast=ylast)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_hmh_c13_orange_mapping_ssr(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=n_array*tau, units=('s', ''), number_of_lasers=num_of_points,
                                       labels=('Tau', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences

    def generate_hmh_c13_orange_xy8_mapping_ssr(self, name='Total_XY8', tau_start=1000e-9, tau_step=1000e-9,
                                                num_of_points=5, xy8N=4, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                                microwave_frequency=2.8e9, microwave_phase=0.0, ylast=False,
                                                hmh_name='HMH', spinlock_length=25e-6, hmh_amp=0.01,
                                                hmh_frequency=2.8e9, hmh_phase=0.0, hmh_laser_length=500e-9,
                                                hmh_wait_length=1e-6, repeat_pol=1, c13_name='C13_',
                                                c13_rabi_period=100e-6, c13_amp=0.05, c13_freq=1e6, c13_phase=0.0,
                                                orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                                #laser_name='laser_wait',
                                                laser_length=1e-6, wait_length=1e-6,
                                                rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                                rf_cnot_duration=100e-6, rf_cnot_phase=0.0,
                                                ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                                mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                                mw_cnot_phase=0.0, mw_cnot_rabi_period2=20e-9,
                                                mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                                mw_cnot_phase2=0.0, ssr_normalise=True, counts_per_readout=1000,
                                                idle_step_name='IDLE', idle_step_length=2e-6):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # make sure the taus correspond to the sampling rate
        tau_start = self._adjust_to_samplingrate(tau_start, 2)
        tau_step = self._adjust_to_samplingrate(tau_step, 2)
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_xy8_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                                            microwave_amplitude=self.microwave_amplitude,
                                            microwave_frequency=self.microwave_frequency, xy8N=xy8N, ylast=ylast)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_hmh_c13_orange_mapping_ssr(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', ''), number_of_lasers=num_of_points,
                                       labels=('Tau', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences


    def generate_pp_orange_c13_xy8Nsweep_mapping_ssr(self, name='Total_Nsweep', n_start=1, n_step=1, num_of_points=5,
                                                      tau=1000e-9, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                                      microwave_frequency=2.8e9, microwave_phase=0.0, ylast=False,
                                                      pp_name='PulsePol', pp_tau=2.5e-6, pp_order=20,
                                                     pp_laser_length=500e-9, pp_wait_length=1e-6, repeat_pol=1,
                                                     c13_name='C13_', c13_rabi_period=100e-6, c13_amp=0.05, c13_freq=1e6, c13_phase=0.0,
                                                      orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                                      #laser_name='laser_wait',
                                                      laser_length=1e-6, wait_length=1e-6,
                                                      rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                                      rf_cnot_duration=100e-6, rf_cnot_phase=0,
                                                      ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                                      mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                                      mw_cnot_phase=0, mw_cnot_rabi_period2=20e-9,
                                                     mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                                      mw_cnot_phase2=0, ssr_normalise=True, counts_per_readout=1000,
                                                      idle_step_name='IDLE', idle_step_length=2e-6):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # make sure the taus correspond to the sampling rate
        n_array = (n_start + np.arange(num_of_points) * n_step).astype(int)


        para_list = list()
        for number, xy8N in enumerate(n_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_xy8_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                                              microwave_amplitude=microwave_amplitude,
                                              microwave_frequency=microwave_frequency, xy8N=xy8N, ylast=ylast)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_pp_orange_c13_mapping_ssr(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=n_array*tau, units=('s', ''), number_of_lasers=num_of_points,
                                       labels=('Tau', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences

    def generate_pp_orange_c13_xy8_mapping_ssr(self, name='Total_XY8', tau_start=1000e-9, tau_step=1000e-9,
                                                num_of_points=5, xy8N=4, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                                microwave_frequency=2.8e9, microwave_phase=0.0, ylast=False, idle_beginning=0e-9,
                                                pp_name='PulsePol', pp_tau=2.5e-6, pp_order=20,
                                                pp_laser_length=500e-9, pp_wait_length=1e-6, repeat_pol=1,
                                                c13_name='C13_', c13_rabi_period=100e-6, c13_amp=0.05, c13_freq=1e6, c13_phase=0.0,
                                                orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                                #laser_name='laser_wait',
                                                laser_length=1e-6, wait_length=1e-6,
                                                rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                                rf_cnot_duration=100e-6, rf_cnot_phase=0.0,
                                                ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                                mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                                mw_cnot_phase=0.0,  mw_cnot_rabi_period2=2000e-9, mw_cnot_amplitude2=0.001,
                                               mw_cnot_frequency2=2.8e9,
                                               mw_cnot_phase2=0.0, ssr_normalise=True, counts_per_readout=1000,
                                               idle_step_name='IDLE', idle_step_length=2e-6):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # make sure the taus correspond to the sampling rate
        tau_start = self._adjust_to_samplingrate(tau_start, 2)
        tau_step = self._adjust_to_samplingrate(tau_step, 2)
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_xy8_mwcnot_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                                            microwave_amplitude=self.microwave_amplitude,
                                            microwave_frequency=self.microwave_frequency, xy8N=xy8N, ylast=ylast,
                                            idle_beginning=idle_beginning,
                                            mw_not_rabi_period=mw_cnot_rabi_period,
                                            mw_not_freq=mw_cnot_frequency,
                                            mw_not_amp=mw_cnot_amplitude,
                                            mw_not_phase=mw_cnot_phase)
                # self.generate_single_xy8_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                #                             microwave_amplitude=self.microwave_amplitude,
                #                             microwave_frequency=self.microwave_frequency, xy8N=xy8N, ylast=ylast,
                #                             idle_beginning = idle_beginning)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_pp_orange_c13_mapping_ssr(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', ''), number_of_lasers=num_of_points,
                                       labels=('Tau', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences

    def generate_pp_orange_c13_xy8_mapping_ssr2(self, name='Total-xy8', tau_start=0.0, tau_step=3.0, num_of_points=5,
                                        xy8N=4, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                        microwave_frequency=2.8e9, ylast=False,
                                        pp_name='PulsePol', pp_tau=2.5e-6, pp_order=20,
                                        pp_laser_length=500e-9, pp_wait_length=1e-6, repeat_pol=1,
                                        orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                        laser_length=1e-6, c13_name='C13', c13_phase=0.0,
                                                c13_rabi_period=100e-6, c13_amp=0.05, c13_freq=1e6,
                                        rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                        rf_cnot_duration=100e-6, rf_cnot_phase=0.0,
                                        ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                        mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                        mw_cnot_phase=0.0, mw_cnot_rabi_period2=2000e-9,
                                        mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                        mw_cnot_phase2=0.0, ssr_normalise=True, counts_per_readout=1000,
                                        idle_step_name='IDLE', idle_step_length=2e-6):
        # find the phase of the C13 pulse
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # Add C13 rf pulses with specified phase
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_xy8_s3(name=name_tmp, rabi_period=rabi_period, tau=tau,
                                            microwave_amplitude=microwave_amplitude,
                                            microwave_frequency=microwave_frequency, xy8N=xy8N, ylast=ylast)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])


        # Add pulsepol
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_pulsepol(name=pp_name,
                                          rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                          microwave_frequency=microwave_frequency,
                                          tau=pp_tau, order=pp_order, pp_laser_length=pp_laser_length,
                                          pp_wait_length=pp_wait_length, trigger=False, repetitions=1)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        pp_list = [pp_name, seq_param]

        # Add the orange laser
        if ssr_normalise:
            factor = 2
        else:
            factor = 1
        individual_orange_length = orange_length / counts_per_readout / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout * factor - 1})
        orange_list = [orange_name, seq_param]

        # Add C13
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_mw_pulse(name=c13_name, tau=c13_rabi_period / 4.0, microwave_amplitude=c13_amp,
                                          microwave_frequency=c13_freq, microwave_phase=c13_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        c13_list = [c13_name, seq_param]


        # Add MW CNOT gate
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_multiple_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2.0,
                                            microwave_amplitude=mw_cnot_amplitude,
                                            microwave_frequency=mw_cnot_frequency,
                                            microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_cnot_list1, rf_cnot_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                           rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(pp_list.copy())
            element_list.append(orange_list.copy())
            element_list.append(c13_list)
            element_list.append(para_list[ii].copy())
            element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('ns', ''), number_of_lasers=num_of_points,
                                       labels=('tau spacing', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences


######################################### Nuclear experiments ####################################################

    def generate_orange_ssr_contrast(self, name='SSR-contrast',
                                  orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                  laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6, initial_pi_pulse=False,
                                  rf_cnot_duration=100e-6, rf_cnot_freq=1.0e6, rf_cnot_amp=0.1, rf_cnot_phase=0,
                                  ssr_name='SSR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=1.0,
                                  mw_cnot_frequency=2.8e9, mw_cnot_phase=0, mw_cnot_rabi_period2=20e-9, mw_cnot_amplitude2=1.0,
                                  mw_cnot_frequency2=2.8e9, mw_cnot_phase2=0, ssr_normalise=True,
                                  counts_per_readout=1000, idle_step_name='IDLE', idle_step_length=2e-6):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict=locals()

        # generate the RF-Rabi pieces
        tau_array = [0, rf_cnot_duration]
        para_list=list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse(name = name_tmp, rf_duration=tau, rf_amp=rf_cnot_amp,
                                       rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])

        created_blocks, created_ensembles, sequence = \
            self._nuclear_manipulation_orange(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', ''), number_of_lasers=2,
                                       counting_length=count_length)

        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_orange_nuclear_odmr(self, name='Orange-Nuclear-ODMR', freq_start=1.0e6, freq_step=1.0e3, num_of_points=50,
                                     orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                     laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6, initial_pi_pulse=False,
                                     rf_duration=1.0e6, rf_amp=0.1, rf_phase=0,
                                     ssr_name='SSR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=1.0,
                                     mw_cnot_frequency=2.8e9, mw_cnot_phase=0, mw_cnot_rabi_period2=20e-9,
                                     mw_cnot_amplitude2=1.0,
                                     mw_cnot_frequency2=2.8e9,  mw_cnot_phase2=0, ssr_normalise=True,
                                     counts_per_readout=1000,idle_step_name='IDLE', idle_step_length=2e-6):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # generate the RF-Rabi pieces
        freq_array = freq_start + np.arange(num_of_points) * freq_step
        para_list=list()
        for number, freq in enumerate(freq_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse(name = name_tmp, rf_duration=rf_duration, rf_amp=rf_amp,
                                       rf_freq=freq, rf_phase=rf_phase)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])

        created_blocks, created_ensembles, sequence = \
            self._nuclear_manipulation_orange(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=freq_array, units=('Hz', ''), number_of_lasers=num_of_points,
                                       labels = ('Frequency', 'Spin flip probability'),
                                       counting_length=self.laser_length * 1.4)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences


    def generate_orange_nuclear_rabi(self, name='Orange-Nuclear-Rabi', tau_start=1.0e-9, tau_step=1.0e-9, num_of_points=50,
                                     orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                     laser_name='laser_wait', laser_length=1e-6, wait_length=1e-6, initial_pi_pulse=False,
                                     rf_freq=1.0e6, rf_amp=0.1, rf_phase=0,
                                     ssr_name='SSR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=1.0,
                                     mw_cnot_frequency=2.8e9, mw_cnot_phase=0, mw_cnot_rabi_period2=20e-9,
                                     mw_cnot_amplitude2=1.0,
                                     mw_cnot_frequency2=2.8e9, mw_cnot_phase2=0, ssr_normalise=True,
                                     counts_per_readout=1000, idle_step_name='IDLE', idle_step_length=2e-6):

        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # generate the RF-Rabi pieces
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list=list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
                self.generate_chopped_rf_pulse(name = name_tmp, rf_duration=tau, rf_amp=rf_amp,
                                       rf_freq=rf_freq, rf_phase=rf_phase)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            para_list.append([list1, list2])

        created_blocks, created_ensembles, sequence = \
            self._nuclear_manipulation_orange(created_blocks, created_ensembles, para_list, para_dict)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating = False, laser_ignore_list = list(),
                                    controlled_variable = tau_array, units=('s', ''), number_of_lasers = num_of_points,
                                    counting_length=self.laser_length * 1.4)

        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

###############################################  Helper methods ####################################################

    def _nuclear_manipulation_orange(self, created_blocks, created_ensembles, para_list, para_dict):

        # generate initialization, rf control, and ssr_readout)
        created_blocks_tmp, created_ensembles_tmp, orange_list, ssr_list = \
            self._initialize_ssr_orange(orange_name=para_dict['orange_name'], orange_length=para_dict['orange_length'],
                                        orange_wait=para_dict['orange_wait'],
                                        #laser_name=para_dict['laser_name'], laser_length=para_dict['laser_length'],
                                        #wait_length=para_dict['wait_length'],
                                        initial_pi_pulse=para_dict['initial_pi_pulse'],
                                        ssr_name=para_dict['ssr_name'],
                                        mw_cnot_rabi_period=para_dict['mw_cnot_rabi_period'],
                                        mw_cnot_amplitude=para_dict['mw_cnot_amplitude'],
                                        mw_cnot_frequency=para_dict['mw_cnot_frequency'],
                                        mw_cnot_phase=para_dict['mw_cnot_phase'],
                                        mw_cnot_rabi_period2=para_dict['mw_cnot_rabi_period2'],
                                        mw_cnot_amplitude2=para_dict['mw_cnot_amplitude2'],
                                        mw_cnot_frequency2=para_dict['mw_cnot_frequency2'],
                                        mw_cnot_phase2=para_dict['mw_cnot_phase2'],
                                        ssr_normalise=para_dict['ssr_normalise'],
                                        counts_per_readout=para_dict['counts_per_readout'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(orange_list.copy())
            #element_list.append(laser_wait_list.copy())
            element_list.append(para_list[ii][0])
            element_list.append(para_list[ii][1])
            element_list.append(ssr_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        # # make sequence continous+
        # element_list = self._make_sequence_continous(element_list)

        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)

        return created_blocks, created_ensembles, sequence


    def _standard_ssr_orange(self, created_blocks, created_ensembles, para_list, para_dict):
        created_sequences = list()
        # generate initialization, rf control, and ssr_readout)
        created_blocks_tmp, created_ensembles_tmp, orange_list, rf_list1, rf_list2, ssr_list, idle_step_list = \
            self._initalize_rf_ssr_orange(orange_name=para_dict['orange_name'], orange_length=para_dict['orange_wait'],
                                          orange_wait=para_dict['orange_wait'],
                                          #laser_name=para_dict['laser_name'], laser_length=para_dict['laser_length'],
                                          #wait_length=para_dict['wait_length'],
                                          rf_cnot_name=para_dict['rf_cnot_name'],
                                          rf_cnot_duration=para_dict['rf_cnot_duration'],
                                          rf_cnot_amp=para_dict['rf_cnot_amp'],
                                          rf_cnot_freq=para_dict['rf_cnot_freq'],
                                          rf_cnot_phase=para_dict['rf_cnot_phase'],
                                          ssr_name=para_dict['ssr_name'],
                                          mw_cnot_rabi_period=para_dict['mw_cnot_rabi_period'],
                                          mw_cnot_amplitude=para_dict['mw_cnot_amplitude'],
                                          mw_cnot_frequency=para_dict['mw_cnot_frequency'],
                                          mw_cnot_phase=para_dict['mw_cnot_phase'],
                                          mw_cnot_rabi_period2=para_dict['mw_cnot_rabi_period2'],
                                          mw_cnot_amplitude2=para_dict['mw_cnot_amplitude2'],
                                          mw_cnot_frequency2=para_dict['mw_cnot_frequency2'],
                                          mw_cnot_phase2=para_dict['mw_cnot_phase2'],
                                          ssr_normalise=para_dict['ssr_normalise'],
                                          counts_per_readout=para_dict['counts_per_readout'],
                                          idle_step_name=para_dict['idle_step_name'],
                                          idle_step_length=para_dict['idle_step_length'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(orange_list.copy())
            #element_list.append(laser_wait_list.copy())
            element_list.append(para_list[ii])
            element_list.append(rf_list1.copy())
            element_list.append(rf_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)

        return created_blocks, created_ensembles, sequence



    def _standard_ssr_mapping_orange(self, created_blocks, created_ensembles, para_list, para_dict):
        created_sequences = list()
        # generate initialization, rf control, and ssr_readout)
        created_blocks_tmp, created_ensembles_tmp, orange_list, mw_cnot_list, \
        rf_list1, rf_list2, ssr_list, idle_step_list = \
            self._initalize_rf_ssr_mapping_orange(orange_name=para_dict['orange_name'],
                                                  orange_length=para_dict['orange_length'],
                                                  orange_wait=para_dict['orange_wait'],
                                                  #laser_name=para_dict['laser_name'], laser_length=para_dict['laser_length'],
                                                  #wait_length=para_dict['wait_length'],
                                                  rf_cnot_name=para_dict['rf_cnot_name'],
                                                  rf_cnot_duration=para_dict['rf_cnot_duration'],
                                                  rf_cnot_amp=para_dict['rf_cnot_amp'],
                                                  rf_cnot_freq=para_dict['rf_cnot_freq'],
                                                  rf_cnot_phase=para_dict['rf_cnot_phase'],
                                                  ssr_name=para_dict['ssr_name'],
                                                  mw_cnot_name=para_dict['mw_cnot_name'],
                                                  mw_cnot_rabi_period=para_dict['mw_cnot_rabi_period'],
                                                  mw_cnot_amplitude=para_dict['mw_cnot_amplitude'],
                                                  mw_cnot_frequency=para_dict['mw_cnot_frequency'],
                                                  mw_cnot_phase=para_dict['mw_cnot_phase'],
                                                  mw_cnot_rabi_period2=para_dict['mw_cnot_rabi_period2'],
                                                  mw_cnot_amplitude2=para_dict['mw_cnot_amplitude2'],
                                                  mw_cnot_frequency2=para_dict['mw_cnot_frequency2'],
                                                  mw_cnot_phase2=para_dict['mw_cnot_phase2'],
                                                  ssr_normalise=para_dict['ssr_normalise'],
                                                  counts_per_readout=para_dict['counts_per_readout'],
                                                  idle_step_name=para_dict['idle_step_name'],
                                                  idle_step_length=para_dict['idle_step_length'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(orange_list.copy())
            #element_list.append(laser_wait_list.copy())
            element_list.append(para_list[ii])
            element_list.append(mw_cnot_list)
            element_list.append(rf_list1.copy())
            element_list.append(rf_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)

        return created_blocks, created_ensembles, sequence

    def _standard_hmh_c13_orange_mapping_ssr(self, created_blocks, created_ensembles, para_list, para_dict):

        # generate hmh polarisation, c13 manipulation, cahrge state selection, mapping to nitrogen and SSR)
        created_blocks_tmp, created_ensembles_tmp, hmh_list, c13_list1, c13_list2, orange_list, mw_cnot_list, \
        rf_cnot_list1, rf_cnot_list2, ssr_list, idle_step_list = \
            self._initialize_hmh_c13_orange_mapping_ssr(hmh_name=para_dict['hmh_name'],
                                                        rabi_period=para_dict['rabi_period'],
                                                        microwave_amplitude=para_dict['microwave_amplitude'],
                                                        microwave_frequency=para_dict['microwave_frequency'],
                                                        microwave_phase=para_dict['microwave_phase'],
                                                        spinlock_length=para_dict['spinlock_length'],
                                                        hmh_amp=para_dict['hmh_amp'],
                                                        hmh_frequency=para_dict['hmh_frequency'],
                                                        hmh_phase=para_dict['hmh_phase'],
                                                        hmh_laser_length=para_dict['hmh_laser_length'],
                                                        hmh_wait_length=para_dict['hmh_wait_length'],
                                                        repeat_pol=para_dict['repeat_pol'],
                                                        c13_name=para_dict['c13_name'],
                                                        c13_rabi_period=para_dict['c13_rabi_period'],
                                                        c13_amp=para_dict['c13_amp'],
                                                        c13_freq=para_dict['c13_freq'],
                                                        c13_phase=para_dict['c13_phase'],
                                                        orange_name=para_dict['orange_name'],
                                                        orange_length=para_dict['orange_length'],
                                                        orange_wait=para_dict['orange_wait'],
                                                        rf_cnot_name=para_dict['rf_cnot_name'],
                                                        rf_cnot_duration=para_dict['rf_cnot_duration'],
                                                        rf_cnot_amp=para_dict['rf_cnot_amp'],
                                                        rf_cnot_freq=para_dict['rf_cnot_freq'],
                                                        rf_cnot_phase=para_dict['rf_cnot_phase'],
                                                        ssr_name=para_dict['ssr_name'],
                                                        mw_cnot_name=para_dict['mw_cnot_name'],
                                                        mw_cnot_rabi_period=para_dict['mw_cnot_rabi_period'],
                                                        mw_cnot_amplitude=para_dict['mw_cnot_amplitude'],
                                                        mw_cnot_frequency=para_dict['mw_cnot_frequency'],
                                                        mw_cnot_phase=para_dict['mw_cnot_phase'],
                                                        mw_cnot_rabi_period2=para_dict['mw_cnot_rabi_period2'],
                                                        mw_cnot_amplitude2=para_dict['mw_cnot_amplitude2'],
                                                        mw_cnot_frequency2=para_dict['mw_cnot_frequency2'],
                                                        mw_cnot_phase2=para_dict['mw_cnot_phase2'],
                                                        ssr_normalise=para_dict['ssr_normalise'],
                                                        counts_per_readout=para_dict['counts_per_readout'],
                                                        idle_step_name=para_dict['idle_step_name'],
                                                        idle_step_length=para_dict['idle_step_length'])

        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(hmh_list.copy())
            element_list.append(orange_list.copy())
            element_list.append(c13_list1.copy())
            element_list.append(c13_list2.copy())
            element_list.append(para_list[ii])
            element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)

        return created_blocks, created_ensembles, sequence

    def _standard_pp_orange_c13_mapping_ssr(self, created_blocks, created_ensembles, para_list, para_dict):

        # Add PulsePol
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_pulsepol(name=para_dict['pp_name'],
                                          rabi_period=para_dict['rabi_period'], microwave_amplitude=para_dict['microwave_amplitude'],
                                          microwave_frequency=para_dict['microwave_frequency'],
                                          tau=para_dict['pp_tau'], order=para_dict['pp_order'], pp_laser_length=para_dict['pp_laser_length'],
                                          pp_wait_length=para_dict['pp_wait_length'], trigger=False, repetitions=1)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': para_dict['repeat_pol'] - 1})
        pp_list = [para_dict['pp_name'], seq_param]

        # Add 13C manipulation
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_mw_pulse(name=para_dict['c13_name'], tau=para_dict['c13_rabi_period'] / 4.0,
                                          microwave_amplitude=para_dict['c13_amp'],
                                          microwave_frequency=para_dict['c13_freq'], microwave_phase=para_dict['c13_phase'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        c13_list1 = [para_dict['c13_name'], seq_param]

        # Add the orange laser
        if para_dict['ssr_normalise']:
            factor = 2
        else:
            factor = 1
        individual_orange_length = para_dict['orange_length'] / para_dict['counts_per_readout'] / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=para_dict['orange_name'], trigger_length=individual_orange_length,
                                       wait_length=para_dict['orange_wait'], digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': para_dict['counts_per_readout'] * factor - 1})
        orange_list = [para_dict['orange_name'], seq_param]

        # # Add MW CNOT gate
        # created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
        #     self.generate_multiple_mw_pulse(name=para_dict['mw_cnot_name'], tau=para_dict['mw_cnot_rabi_period'] / 2.0,
        #                                     microwave_amplitude=para_dict['mw_cnot_amplitude'],
        #                                     microwave_frequency=para_dict['mw_cnot_frequency'],
        #                                     microwave_phase=para_dict['mw_cnot_phase'])
        # created_blocks += created_blocks_tmp
        # created_ensembles += created_ensembles_tmp
        # seq_param = self._customize_seq_para({})
        # mw_cnot_list = [para_dict['mw_cnot_name'], seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_cnot_list1, rf_cnot_list2 = \
            self.generate_chopped_rf_pulse(name=para_dict['rf_cnot_name'], rf_duration=para_dict['rf_cnot_duration'],
                                           rf_amp=para_dict['rf_cnot_amp'],
                                           rf_freq=para_dict['rf_cnot_freq'], rf_phase=para_dict['rf_cnot_phase'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=para_dict['ssr_name'], mw_cnot_rabi_period=para_dict['mw_cnot_rabi_period'],
                                             mw_cnot_amplitude=para_dict['mw_cnot_amplitude'],
                                             mw_cnot_frequency=para_dict['mw_cnot_frequency'],
                                             mw_cnot_phase=para_dict['mw_cnot_phase'],
                                             mw_cnot_rabi_period2=para_dict['mw_cnot_rabi_period2'],
                                             mw_cnot_amplitude2=para_dict['mw_cnot_amplitude2'],
                                             mw_cnot_frequency2=para_dict['mw_cnot_frequency2'],
                                             mw_cnot_phase2=para_dict['mw_cnot_phase2'],
                                             ssr_normalise=para_dict['ssr_normalise'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': para_dict['counts_per_readout'] - 1})
        ssr_list = [para_dict['ssr_name'], seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=para_dict['idle_step_name'], tau=para_dict['idle_step_length'])
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [para_dict['idle_step_name'], seq_param]


        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(pp_list.copy())
            element_list.append(orange_list.copy())
            element_list.append(c13_list1.copy())
            #element_list.append(c13_list2.copy())
            element_list.append(para_list[ii])
            #element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=para_dict['name'], ensemble_list=element_list, rotating_frame=False)

        return created_blocks, created_ensembles, sequence


############################################ Initialize methods #######################################################

    def _initialize_ssr_orange(self, orange_name, orange_length, orange_wait,
                               initial_pi_pulse, ssr_name, mw_cnot_rabi_period, mw_cnot_amplitude, mw_cnot_frequency,
                               mw_cnot_phase, mw_cnot_rabi_period2, mw_cnot_amplitude2, mw_cnot_frequency2,
                               mw_cnot_phase2, ssr_normalise, counts_per_readout):

        created_blocks = list()
        created_ensembles = list()

        # Add the orange laser
        individual_orange_length = orange_length / counts_per_readout
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        orange_list = [orange_name, seq_param]

        # # Add the laser initialization
        #
        # if not initial_pi_pulse:
        #     # Add just laser initialization
        #     created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
        #         self.generate_laser_wait(name=laser_name, laser_length=laser_length, wait_length=wait_length)
        # else:
        #     # Add an additional MW pi-pulse to initalize the NV into -1 or +1
        #     created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
        #         self.generate_laser_wait_pipulse(name=laser_name, laser_length=laser_length,  wait_length=wait_length)
        #
        # created_blocks += created_blocks_tmp
        # created_ensembles += created_ensembles_tmp
        # seq_param = self._customize_seq_para({})
        # laser_wait_list = [laser_name, seq_param]


        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
        ssr_list = [ssr_name, seq_param]

        return created_blocks, created_ensembles, orange_list, ssr_list

    def _initalize_rf_ssr_orange(self, orange_name, orange_length, orange_wait,
                                 rf_cnot_name, rf_cnot_duration, rf_cnot_amp, rf_cnot_freq, rf_cnot_phase, ssr_name,
                                 mw_cnot_rabi_period, mw_cnot_amplitude, mw_cnot_frequency, mw_cnot_phase,
                                 mw_cnot_rabi_period2, mw_cnot_amplitude2, mw_cnot_frequency2, mw_cnot_phase2,
                                 ssr_normalise,counts_per_readout, idle_step_name, idle_step_length):

        created_blocks = list()
        created_ensembles = list()

        # Add the orange laser
        individual_orange_length = orange_length/counts_per_readout
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel = self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
        orange_list = [orange_name, seq_param]

        # # Add the laser initialization
        # created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
        #     self.generate_laser_wait(name=laser_name, laser_length=laser_length, wait_length=wait_length)
        # created_blocks += created_blocks_tmp
        # created_ensembles += created_ensembles_tmp
        # seq_param = self._customize_seq_para({})
        # laser_wait_list = [laser_name, seq_param]

        # Add RF pulse
        created_blocks_tmp, created_ensembles_tmp, rf_list1, rf_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                   rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout-1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        return created_blocks, created_ensembles, orange_list, rf_list1, rf_list2, ssr_list, idle_step_list

    def _initalize_rf_ssr_mapping_orange(self, orange_name, orange_length, orange_wait,
                                 rf_cnot_name, rf_cnot_duration, rf_cnot_amp, rf_cnot_freq, rf_cnot_phase,
                                 ssr_name, mw_cnot_name,
                                 mw_cnot_rabi_period, mw_cnot_amplitude, mw_cnot_frequency, mw_cnot_phase,
                                 mw_cnot_rabi_period2, mw_cnot_amplitude2, mw_cnot_frequency2, mw_cnot_phase2,
                                         ssr_normalise, counts_per_readout, idle_step_name, idle_step_length):
        created_blocks = list()
        created_ensembles = list()

        # Add the orange laser
        if ssr_normalise:
            factor = 2
        else:
            factor = 1
        individual_orange_length = orange_length / counts_per_readout / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout * factor  - 1})
        orange_list = [orange_name, seq_param]

        # Add MW CNOT gate
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_multiple_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2.0,
                                            microwave_amplitude=mw_cnot_amplitude,
                                            microwave_frequency=mw_cnot_frequency,
                                            microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_list1, rf_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                   rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        return created_blocks, created_ensembles, orange_list, mw_cnot_list, rf_list1, rf_list2, ssr_list, idle_step_list

    def _initialize_hmh_c13_orange_mapping_ssr(self, hmh_name, rabi_period, microwave_amplitude, microwave_frequency,
                                               microwave_phase, spinlock_length, hmh_amp, hmh_frequency, hmh_phase,
                                               hmh_laser_length, hmh_wait_length, repeat_pol,
                                               c13_name, c13_rabi_period, c13_amp, c13_freq, c13_phase,
                                               orange_name, orange_length, orange_wait,
                                               rf_cnot_name, rf_cnot_duration, rf_cnot_amp, rf_cnot_freq, rf_cnot_phase,
                                               ssr_name, mw_cnot_name, mw_cnot_rabi_period, mw_cnot_amplitude,
                                               mw_cnot_frequency, mw_cnot_phase, mw_cnot_amplitude2, mw_cnot_frequency2,
                                               mw_cnot_phase2, ssr_normalise, counts_per_readout, idle_step_name,
                                               idle_step_length):
        created_blocks = list()
        created_ensembles = list()

        # Add hmh
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_hmh(name=hmh_name,
                                     rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                     microwave_frequency=microwave_frequency, microwave_phase=microwave_phase,
                                     spinlock_length=spinlock_length, hmh_amplitude=hmh_amp,
                                     hmh_frequency=hmh_frequency, hmh_phase=hmh_phase,
                                     hmh_laser_length=hmh_laser_length,
                                     hmh_wait_length=hmh_wait_length, alternating=False, trigger=False)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        hmh_list = [hmh_name, seq_param]

        # Add 13C manipulation
        created_blocks_tmp, created_ensembles_tmp, c13_list1, c13_list2 = \
            self.generate_chopped_rf_pulse(name=c13_name, rf_duration=c13_rabi_period/4.0, rf_amp=c13_amp,
                                   rf_freq=c13_freq, rf_phase=c13_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add the orange laser
        if ssr_normalise:
            factor = 2
        else:
            factor = 1
        individual_orange_length = orange_length / counts_per_readout / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout * factor  - 1})
        orange_list = [orange_name, seq_param]

        # Add MW CNOT gate
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_multiple_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2.0,
                                            microwave_amplitude=mw_cnot_amplitude,
                                            microwave_frequency=mw_cnot_frequency,
                                            microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_cnot_list1, rf_cnot_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                           rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        return created_blocks, created_ensembles, hmh_list, c13_list1, c13_list2, orange_list, \
               mw_cnot_list, rf_cnot_list1, rf_cnot_list2, ssr_list, idle_step_list



############################## To move to helper methods #######################################


    def compute_count_length(self, orange_length, laser_length, ssr_normalise, counts_per_readout):

        if ssr_normalise:
            if orange_length/counts_per_readout/2 * 1.0 > laser_length * 1.8:
                count_length = orange_length/counts_per_readout/2 * 1.0
            else:
                count_length = laser_length * 1.8
        else:
            if orange_length/counts_per_readout* 1.0 > laser_length * 1.4:
                count_length = orange_length/counts_per_readout * 1.0
            else:
                count_length = laser_length * 1.4
        return count_length


#     def generate_singleshot_readout(self, name='SSR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=0.1,
#                                     mw_cnot_frequency=2.8e9, mw_cnot_phase = 0, mw_cnot_amplitude2=0.1,
#                                     mw_cnot_frequency2=2.8e9, mw_cnot_phase2=0, ssr_normalise=True):
#         """
#
#         """
#         created_blocks = list()
#         created_ensembles = list()
#         created_sequences = list()
#
#         ### prevent granularity problems
#         mw_cnot_rabi_period = self._adjust_to_samplingrate(mw_cnot_rabi_period, 4)
#
#
#         # get mw pi pulse block
#         mw_pi_element = self._get_multiple_mw_element(length=mw_cnot_rabi_period/2,
#                                                       increment=0.0,
#                                                       amps=mw_cnot_amplitude,
#                                                       freqs=mw_cnot_frequency,
#                                                       phases=mw_cnot_phase)
#
#         trigger_element = self._get_sync_element()
#
#         readout_element = self._get_readout_element()
#         block = PulseBlock(name=name)
#         block.append(mw_pi_element)
#         block.append(trigger_element)
#         block.extend(readout_element)
#
#
#         if ssr_normalise:
#             time_between_trigger = self.laser_length + self.wait_time + self.laser_delay
#             if time_between_trigger > self.laser_length * 1.4:
#                 wait = time_between_trigger - self.laser_length * 1.4
#                 extra_waiting_element = self._get_idle_element(length=wait*1.2, increment=0)
#             mw_pi_element2 = self._get_multiple_mw_element(length=mw_cnot_rabi_period/2,
#                                                            increment=0.0,
#                                                            amps=mw_cnot_amplitude2,
#                                                            freqs=mw_cnot_frequency2,
#                                                            phases=mw_cnot_phase2)
#             waiting_element = self._get_idle_element(length=self.laser_length + 200e-9, increment=0)
#
#             if self.laser_length + self.wait_time + self.laser_delay > self.laser_length * 1.4:
#                 block.append(extra_waiting_element)
# #
#             block.append(mw_pi_element2)
#             block.append(trigger_element)
#             block.append(waiting_element)
#             block.extend(readout_element)
#         created_blocks.append(block)
#         # Create block ensemble
#         block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
#         block_ensemble.append((block.name, 0))
#         # add metadata to invoke settings
#         block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=list(), controlled_variable = [0],
#                                         counting_length = self.laser_length * 1.8 if ssr_normalise
#                                                          else self.laser_length * 1.4)
#         # append ensemble to created ensembles
#         created_ensembles.append(block_ensemble)
#
#         return created_blocks, created_ensembles, created_sequences

##################################### Methods based on flip probability #############################

    def generate_orange_ssr_rabi(self, name='Orange_SSR-Rabi', tau_start=1.0e-9, tau_step=1.0e-9, num_of_points=50,
                                 orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                 #laser_name='laser_wait',
                                 laser_length=1e-6, wait_length=1e-6,
                                 rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1, rf_cnot_duration=100e-6,
                                 rf_cnot_phase=0,
                                 ssr_name='SSR', mw_cnot_rabi_period=20e-9, mw_cnot_amplitude=1.0,
                                 mw_cnot_frequency=2.8e9, mw_cnot_rabi_period2=20e-9,
                                 mw_cnot_phase=0, mw_cnot_amplitude2=1.0, mw_cnot_frequency2=2.8e9,
                                 mw_cnot_phase2=0, ssr_normalise=True, counts_per_readout=1000,
                                 idle_step_name='IDLE', idle_step_length=2e-6):
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        para_dict = locals()

        # generate the Rabi pieces
        tau_array = tau_start + np.arange(num_of_points) * tau_step
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse(name=name_tmp, tau=tau,
                                              microwave_amplitude=self.microwave_amplitude,
                                              microwave_frequency=self.microwave_frequency, microwave_phase=0.0)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        created_blocks, created_ensembles, sequence = \
            self._standard_ssr_orange(created_blocks, created_ensembles, para_list, para_dict)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('s', ''), number_of_lasers=num_of_points,
                                       labels=('Tau', 'Spin flip probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)

        return created_blocks, created_ensembles, created_sequences

    ############################################## Calibration methods ########################################

    def generate_calibrate_C13_phase(self, name='C13_phase', c13_phase_start=0.0, c13_phase_step=3.0, num_of_points=5,
                                     c13_rabi_period=100e-6, c13_amp=0.05, c13_freq=1e6,
                                     xy8_name='XY8', tau=1000e-9, xy8N=4, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                     microwave_frequency=2.8e9, microwave_phase=0.0, ylast=False,
                                     hmh_name='HMH', spinlock_length=25e-6, hmh_amp=0.01,
                                     hmh_frequency=2.8e9, hmh_phase=0.0, hmh_laser_length=500e-9,
                                     hmh_wait_length=1e-6, repeat_pol=1,
                                     orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                     laser_length=1e-6, wait_length=1e-6,
                                     rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                     rf_cnot_duration=100e-6, rf_cnot_phase=0.0,
                                     ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                     mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                     mw_cnot_phase=0.0, mw_cnot_rabi_period2=2000e-9,
                                     mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                     mw_cnot_phase2=0.0, ssr_normalise=True, counts_per_readout=1000,
                                     idle_step_name='IDLE', idle_step_length=2e-6):
        # find the phase of the C13 pulse
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        phase_array = c13_phase_start + np.arange(num_of_points) * c13_phase_step

        # Add C13 rf pulses with specified phase
        para_list = list()
        for number, phase in enumerate(phase_array):
            name_tmp = name + '_' + str(number)
            # created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
            #     self.generate_chopped_rf_pulse(name=name_tmp, rf_duration=c13_rabi_period/4.0, rf_amp=c13_amp,
            #                                    rf_freq=c13_freq, rf_phase=phase)
            #
            # created_blocks += created_blocks_tmp
            # created_ensembles += created_ensembles_tmp
            # para_list.append([list1, list2])
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse(name=name_tmp, tau=c13_rabi_period/4.0, microwave_amplitude=c13_amp,
                                              microwave_frequency=c13_freq, microwave_phase=phase)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        # Add hmh
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_hmh(name=hmh_name,
                                     rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                     microwave_frequency=microwave_frequency, microwave_phase=microwave_phase,
                                     spinlock_length=spinlock_length, hmh_amplitude=hmh_amp,
                                     hmh_frequency=hmh_frequency, hmh_phase=hmh_phase,
                                     hmh_laser_length=hmh_laser_length,
                                     hmh_wait_length=hmh_wait_length, alternating=False, trigger=False)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        hmh_list = [hmh_name, seq_param]

        # Add the orange laser
        if ssr_normalise:
            factor = 2
        else:
            factor = 1
        individual_orange_length = orange_length / counts_per_readout / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout * factor - 1})
        orange_list = [orange_name, seq_param]

        # ADD XY8
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_xy8_s3(name=xy8_name, rabi_period=rabi_period, tau=tau,
                                        microwave_amplitude=microwave_amplitude,
                                        microwave_frequency=microwave_frequency, xy8N=xy8N, ylast=ylast)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        xy8_list =[xy8_name, seq_param]

        # Add MW CNOT gate
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_multiple_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2.0,
                                            microwave_amplitude=mw_cnot_amplitude,
                                            microwave_frequency=mw_cnot_frequency,
                                            microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_cnot_list1, rf_cnot_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                           rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(hmh_list.copy())
            element_list.append(orange_list.copy())
            element_list.append(para_list[ii].copy())
            # element_list.append(para_list[ii][0].copy())
            # element_list.append(para_list[ii][1].copy())
            element_list.append(xy8_list)
            element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=phase_array, units=('°', ''), number_of_lasers=num_of_points,
                                       labels=('C13 phase', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_calibrate_C13_phase_pp(self, name='C13_phase', c13_phase_start=0.0, c13_phase_step=3.0, num_of_points=5,
                                        c13_rabi_period=100e-6, c13_amp=0.05, c13_freq=1e6,
                                        xy8_name='XY8', tau=1000e-9, xy8N=4, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                        microwave_frequency=2.8e9, microwave_phase=0.0, ylast=False,
                                        pp_name='PulsePol', pp_tau=2.5e-6, pp_order=20,
                                        pp_laser_length=500e-9, pp_wait_length=1e-6, repeat_pol=1,
                                        orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                        laser_length=1e-6, wait_length=1e-6,
                                        rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                        rf_cnot_duration=100e-6, rf_cnot_phase=0.0,
                                        ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                        mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                        mw_cnot_phase=0.0, mw_cnot_rabi_period2=2000e-9,
                                        mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                        mw_cnot_phase2=0.0, ssr_normalise=True, counts_per_readout=1000,
                                        idle_step_name='IDLE', idle_step_length=2e-6):
        # find the phase of the C13 pulse
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        phase_array = c13_phase_start + np.arange(num_of_points) * c13_phase_step

        # Add C13 rf pulses with specified phase
        para_list = list()
        for number, phase in enumerate(phase_array):
            name_tmp = name + '_' + str(number)
            # created_blocks_tmp, created_ensembles_tmp, list1, list2 = \
            #     self.generate_chopped_rf_pulse(name=name_tmp, rf_duration=c13_rabi_period/4.0, rf_amp=c13_amp,
            #                                    rf_freq=c13_freq, rf_phase=phase)
            #
            # created_blocks += created_blocks_tmp
            # created_ensembles += created_ensembles_tmp
            # para_list.append([list1, list2])
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_mw_pulse(name=name_tmp, tau=c13_rabi_period/4.0, microwave_amplitude=c13_amp,
                                              microwave_frequency=c13_freq, microwave_phase=phase)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            para_list.append([name_tmp, seq_param])

        # Add pulsepol
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_pulsepol(name=pp_name,
                                          rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                          microwave_frequency=microwave_frequency,
                                          tau=pp_tau, order=pp_order, pp_laser_length=pp_laser_length,
                                          pp_wait_length=pp_wait_length, trigger=False, repetitions=1)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        pp_list = [pp_name, seq_param]

        # Add the orange laser
        if ssr_normalise:
            factor = 2
        else:
            factor = 1
        individual_orange_length = orange_length / counts_per_readout / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout * factor - 1})
        orange_list = [orange_name, seq_param]

        # ADD XY8
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_xy8_s3(name=xy8_name, rabi_period=rabi_period, tau=tau,
                                        microwave_amplitude=microwave_amplitude,
                                        microwave_frequency=microwave_frequency, xy8N=xy8N, ylast=ylast)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        xy8_list =[xy8_name, seq_param]

        # Add MW CNOT gate
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_multiple_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2.0,
                                            microwave_amplitude=mw_cnot_amplitude,
                                            microwave_frequency=mw_cnot_frequency,
                                            microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_cnot_list1, rf_cnot_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                           rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(pp_list.copy())
            element_list.append(orange_list.copy())
            element_list.append(para_list[ii].copy())
            # element_list.append(para_list[ii][0].copy())
            # element_list.append(para_list[ii][1].copy())
            element_list.append(xy8_list)
            element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=phase_array, units=('°', ''), number_of_lasers=num_of_points,
                                       labels=('C13 phase', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_calibrate_pp(self, name='PulsePol', tau_start=500e-9, tau_step=10e-9, num_of_points=5,
                                        order=4, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                        microwave_frequency=2.8e9,
                                        orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                        laser_length=1e-6, pp_tau=500e-9, pp_order=10, pp_laser_length=500e-9,
                              pp_wait_length=1e-6, repeat_pol =3,
                                        rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                        rf_cnot_duration=100e-6, rf_cnot_phase=0.0,
                                        ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                        mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                        mw_cnot_phase=0.0, mw_cnot_rabi_period2=2000e-9,
                                        mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                        mw_cnot_phase2=0.0, ssr_normalise=True, counts_per_readout=1000,
                                        idle_step_name='IDLE', idle_step_length=2e-6):
        # find the phase of the C13 pulse
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # Add Pulsepol
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol2(name=name_tmp, tau=tau, rabi_period=rabi_period,
                                               microwave_amplitude=microwave_amplitude,
                                               microwave_frequency=microwave_frequency, order=order, alternating=False)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})
            name_tmp_alt = name_tmp + '_alt'
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol2(name=name_tmp_alt, tau=tau, rabi_period=rabi_period,
                                               microwave_amplitude=microwave_amplitude,
                                               microwave_frequency=microwave_frequency, order=order, alternating=True)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param2 = self._customize_seq_para({})
            para_list.append([[name_tmp, seq_param],[name_tmp_alt, seq_param2]])

        # Add the orange laser
        if ssr_normalise:
            factor = 2
        else:
            factor = 1
        individual_orange_length = orange_length / counts_per_readout / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout * factor - 1})
        orange_list = [orange_name, seq_param]

        # Add pulsepol
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_pulsepol(name='PulsePol',
                                          rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                          microwave_frequency=microwave_frequency,
                                          tau=pp_tau, order=pp_order, pp_laser_length=pp_laser_length,
                                          pp_wait_length=pp_wait_length, trigger=False, repetitions=1,
                                          alternating=True)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        pp_list = ['PulsePol', seq_param]

        # Add pulsepol alt
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_single_pulsepol(name='PulsePol_alt',
                                          rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                          microwave_frequency=microwave_frequency,
                                          tau=pp_tau, order=pp_order, pp_laser_length=pp_laser_length,
                                          pp_wait_length=pp_wait_length, trigger=False, repetitions=1,
                                          alternating=False)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': repeat_pol - 1})
        pp_list_alt = ['PulsePol_alt', seq_param]

        # Add MW CNOT gate
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_multiple_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2.0,
                                            microwave_amplitude=mw_cnot_amplitude,
                                            microwave_frequency=mw_cnot_frequency,
                                            microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_cnot_list1, rf_cnot_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                           rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(orange_list.copy())
            element_list.append(pp_list.copy())
            element_list.append(para_list[ii][0].copy())
            element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
            element_list.append(orange_list.copy())
            element_list.append(pp_list_alt.copy())
            element_list.append(para_list[ii][1].copy())
            element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('ns', ''), number_of_lasers=num_of_points,
                                       labels=('tau spacing', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_calibrate_pp2(self, name='PulsePol', tau_start=500e-9, tau_step=10e-9, num_of_points=5,
                                        order=4, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                        microwave_frequency=2.8e9,
                                        orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                        laser_length=1e-6, pp_tau=500e-9, pp_order=10, pp_laser_length=500e-9,
                              pp_wait_length=1e-6, repeat_pol =3, alternating = False,
                                        rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                        rf_cnot_duration=100e-6, rf_cnot_phase=0.0,
                                        ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                        mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                        mw_cnot_phase=0.0, mw_cnot_rabi_period2=2000e-9,
                                        mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                        mw_cnot_phase2=0.0, ssr_normalise=True, counts_per_readout=1000,
                                        idle_step_name='IDLE', idle_step_length=2e-6):
        # find the phase of the C13 pulse
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # Add Pulsepol
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol2(name=name_tmp, tau=tau, rabi_period=rabi_period,
                                               microwave_amplitude=microwave_amplitude,
                                               microwave_frequency=microwave_frequency, order=order,
                                               alternating=alternating)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})

            name_tmp_pol = name_tmp + '_pol'
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol(name=name_tmp_pol,
                                              rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                              microwave_frequency=microwave_frequency,
                                              tau=tau, order=order, pp_laser_length=pp_laser_length,
                                              pp_wait_length=pp_wait_length, trigger=False, repetitions=1,
                                              alternating=not alternating )
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param_pol = self._customize_seq_para({'repetitions': repeat_pol - 1})

            para_list.append([[name_tmp, seq_param],[name_tmp_pol, seq_param_pol]])

        # Add the orange laser
        if ssr_normalise:
            factor = 2
        else:
            factor = 1
        individual_orange_length = orange_length / counts_per_readout / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout * factor - 1})
        orange_list = [orange_name, seq_param]



        # Add MW CNOT gate
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_multiple_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2.0,
                                            microwave_amplitude=mw_cnot_amplitude,
                                            microwave_frequency=mw_cnot_frequency,
                                            microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_cnot_list1, rf_cnot_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                           rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(orange_list.copy())
            element_list.append(para_list[ii][1].copy())
            element_list.append(para_list[ii][0].copy())
            element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=tau_array, units=('ns', ''), number_of_lasers=num_of_points,
                                       labels=('tau spacing', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_calibrate_pp3(self, name='PulsePol', tau_start=500e-9, tau_step=10e-9, num_of_points=5,
                                        order=4, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                        microwave_frequency=2.8e9,
                                        orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                        laser_length=1e-6, pp_tau=500e-9, pp_order=10, pp_laser_length=500e-9,
                              pp_wait_length=1e-6, repeat_pol =3, alternating = False,
                                        rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                        rf_cnot_duration=100e-6, rf_cnot_phase=0.0,
                                        ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                        mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                        mw_cnot_phase=0.0, mw_cnot_rabi_period2=2000e-9,
                                        mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                        mw_cnot_phase2=0.0, ssr_normalise=True, counts_per_readout=1000,
                                        idle_step_name='IDLE', idle_step_length=2e-6):
        # find the phase of the C13 pulse
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # Add Pulsepol
        para_list = list()
        for number, tau in enumerate(tau_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol2(name=name_tmp, tau=tau, rabi_period=rabi_period,
                                               microwave_amplitude=microwave_amplitude,
                                               microwave_frequency=microwave_frequency, order=order,
                                               alternating=alternating)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})

            name_tmp_pol = name_tmp + '_pol'
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol(name=name_tmp_pol,
                                              rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                              microwave_frequency=microwave_frequency,
                                              tau=tau, order=order, pp_laser_length=pp_laser_length,
                                              pp_wait_length=pp_wait_length, trigger=False, repetitions=1,
                                              alternating=not alternating )
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param_pol = self._customize_seq_para({'repetitions': repeat_pol - 1})

            para_list.append([[name_tmp, seq_param],[name_tmp_pol, seq_param_pol]])

            name_tmp = name + '_' + str(number) + '_alt'
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol2(name=name_tmp, tau=tau, rabi_period=rabi_period,
                                               microwave_amplitude=microwave_amplitude,
                                               microwave_frequency=microwave_frequency, order=order,
                                               alternating=not alternating)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})

            name_tmp_pol = name_tmp + '_pol'
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol(name=name_tmp_pol,
                                              rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                              microwave_frequency=microwave_frequency,
                                              tau=tau, order=order, pp_laser_length=pp_laser_length,
                                              pp_wait_length=pp_wait_length, trigger=False, repetitions=1,
                                              alternating=alternating)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param_pol = self._customize_seq_para({'repetitions': repeat_pol - 1})

            para_list.append([[name_tmp, seq_param], [name_tmp_pol, seq_param_pol]])

        # Add the orange laser
        if ssr_normalise:
            factor = 2
        else:
            factor = 1
        individual_orange_length = orange_length / counts_per_readout / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout * factor - 1})
        orange_list = [orange_name, seq_param]

        # Add MW CNOT gate
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_multiple_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2.0,
                                            microwave_amplitude=mw_cnot_amplitude,
                                            microwave_frequency=mw_cnot_frequency,
                                            microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_cnot_list1, rf_cnot_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                           rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(orange_list.copy())
            element_list.append(para_list[ii][1].copy())
            #element_list.append(orange_list.copy())
            element_list.append(para_list[ii][0].copy())
            element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            #element_list.append(orange_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=True, laser_ignore_list=list(),
                                       #controlled_variable=sorted(np.concatenate([tau_array,tau_array])),
                                       controlled_variable=tau_array,
                                       units=('ns', ''), number_of_lasers=len(para_list),
                                       labels=('tau spacing', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences

    def generate_calibrate_pp4(self, name='PulsePol', order_start=1, order_step=1, num_of_points=5,
                                        tau=500e-9, rabi_period=0.1e-6, microwave_amplitude=0.1,
                                        microwave_frequency=2.8e9,
                                        orange_name='orange', orange_length=1e-3, orange_wait=1.2e-6,
                                        laser_length=1e-6, pp_tau=500e-9, pp_order=10, pp_laser_length=500e-9,
                              pp_wait_length=1e-6, repeat_pol =3, alternating = False,
                                        rf_cnot_name='RF', rf_cnot_freq=1.0e6, rf_cnot_amp=0.1,
                                        rf_cnot_duration=100e-6, rf_cnot_phase=0.0,
                                        ssr_name='SSR', mw_cnot_name='MW-CNOT', mw_cnot_rabi_period=2000e-9,
                                        mw_cnot_amplitude=0.001, mw_cnot_frequency=2.8e9,
                                        mw_cnot_phase=0.0, mw_cnot_rabi_period2=2000e-9,
                                        mw_cnot_amplitude2=0.001, mw_cnot_frequency2=2.8e9,
                                        mw_cnot_phase2=0.0, ssr_normalise=True, counts_per_readout=1000,
                                        idle_step_name='IDLE', idle_step_length=2e-6):
        # find the phase of the C13 pulse
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        order_array = order_start + np.arange(num_of_points) * order_step

        # Add Pulsepol
        para_list = list()
        for number, order in enumerate(order_array):
            name_tmp = name + '_' + str(number)
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol2(name=name_tmp, tau=tau, rabi_period=rabi_period,
                                               microwave_amplitude=microwave_amplitude,
                                               microwave_frequency=microwave_frequency, order=order,
                                               alternating=alternating)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})

            name_tmp_pol = name_tmp + '_pol'
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol(name=name_tmp_pol,
                                              rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                              microwave_frequency=microwave_frequency,
                                              tau=tau, order=order, pp_laser_length=pp_laser_length,
                                              pp_wait_length=pp_wait_length, trigger=False, repetitions=1,
                                              alternating=not alternating )
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param_pol = self._customize_seq_para({'repetitions': repeat_pol - 1})

            para_list.append([[name_tmp, seq_param],[name_tmp_pol, seq_param_pol]])

            name_tmp = name + '_' + str(number) + '_alt'
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol2(name=name_tmp, tau=tau, rabi_period=rabi_period,
                                               microwave_amplitude=microwave_amplitude,
                                               microwave_frequency=microwave_frequency, order=order,
                                               alternating=not alternating)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param = self._customize_seq_para({})

            name_tmp_pol = name_tmp + '_pol'
            created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
                self.generate_single_pulsepol(name=name_tmp_pol,
                                              rabi_period=rabi_period, microwave_amplitude=microwave_amplitude,
                                              microwave_frequency=microwave_frequency,
                                              tau=tau, order=order, pp_laser_length=pp_laser_length,
                                              pp_wait_length=pp_wait_length, trigger=False, repetitions=1,
                                              alternating=alternating)
            created_blocks += created_blocks_tmp
            created_ensembles += created_ensembles_tmp
            seq_param_pol = self._customize_seq_para({'repetitions': repeat_pol - 1})

            para_list.append([[name_tmp, seq_param], [name_tmp_pol, seq_param_pol]])

        # Add the orange laser
        if ssr_normalise:
            factor = 2
        else:
            factor = 1
        individual_orange_length = orange_length / counts_per_readout / factor
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_trigger_wait(name=orange_name, trigger_length=individual_orange_length,
                                       wait_length=orange_wait, digital_channel=self.sync_channel)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout * factor - 1})
        orange_list = [orange_name, seq_param]

        # Add MW CNOT gate
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_multiple_mw_pulse(name=mw_cnot_name, tau=mw_cnot_rabi_period / 2.0,
                                            microwave_amplitude=mw_cnot_amplitude,
                                            microwave_frequency=mw_cnot_frequency,
                                            microwave_phase=mw_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({})
        mw_cnot_list = [mw_cnot_name, seq_param]

        # Add Nitrogen manipulation
        created_blocks_tmp, created_ensembles_tmp, rf_cnot_list1, rf_cnot_list2 = \
            self.generate_chopped_rf_pulse(name=rf_cnot_name, rf_duration=rf_cnot_duration, rf_amp=rf_cnot_amp,
                                           rf_freq=rf_cnot_freq, rf_phase=rf_cnot_phase)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp

        # Add SSR
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_singleshot_readout(name=ssr_name, mw_cnot_rabi_period=mw_cnot_rabi_period,
                                             mw_cnot_amplitude=mw_cnot_amplitude,
                                             mw_cnot_frequency=mw_cnot_frequency,
                                             mw_cnot_phase=mw_cnot_phase,
                                             mw_cnot_rabi_period2=mw_cnot_rabi_period2,
                                             mw_cnot_amplitude2=mw_cnot_amplitude2,
                                             mw_cnot_frequency2=mw_cnot_frequency2,
                                             mw_cnot_phase2=mw_cnot_phase2,
                                             ssr_normalise=ssr_normalise)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': counts_per_readout - 1})
        ssr_list = [ssr_name, seq_param]

        # Add idle step
        created_blocks_tmp, created_ensembles_tmp, created_sequences_tmp = \
            self.generate_idle_s3(name=idle_step_name, tau=idle_step_length)
        created_blocks += created_blocks_tmp
        created_ensembles += created_ensembles_tmp
        seq_param = self._customize_seq_para({'repetitions': 0})
        idle_step_list = [idle_step_name, seq_param]

        # bring the individual blocks in the correct order
        element_list = list()
        for ii in range(len(para_list)):
            element_list.append(orange_list.copy())
            element_list.append(para_list[ii][1].copy())
            #element_list.append(orange_list.copy())
            element_list.append(para_list[ii][0].copy())
            element_list.append(mw_cnot_list)
            element_list.append(rf_cnot_list1.copy())
            element_list.append(rf_cnot_list2.copy())
            element_list.append(ssr_list.copy())
            #element_list.append(orange_list.copy())
            element_list.append(idle_step_list.copy())
        # make sequence continous+
        element_list = self._make_sequence_continous(element_list)
        sequence = PulseSequence(name=name, ensemble_list=element_list, rotating_frame=False)

        count_length = self.compute_count_length(orange_length=orange_length, laser_length=laser_length,
                                                 ssr_normalise=ssr_normalise, counts_per_readout=counts_per_readout)

        self._add_metadata_to_settings(sequence, created_blocks=list(), alternating=False, laser_ignore_list=list(),
                                       controlled_variable=sorted(np.concatenate([order_array,order_array])),
                                       #controlled_variable=order_array,
                                       units=('ns', ''), number_of_lasers=len(para_list),
                                       labels=('tau spacing', 'Mapping probability'),
                                       counting_length=count_length)
        created_sequences.append(sequence)
        return created_blocks, created_ensembles, created_sequences


    def generate_single_pulsepol2(self, name='PulsePol', rabi_period=0.1e-6, tau=0.5e-6, microwave_amplitude=0.1,
                                 microwave_frequency=2870.0e6, order=8, pulse_function='Sin', alternating=False):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()
        # sanity check
        if tau / 4.0 - rabi_period / 2.0 < 0.0:
            self.log.error('Pol 2.0 generation failed! Rabi period of {0:.3e} s is too long for start tau '
                           'of {1:.3e} s.'.format(rabi_period, tau))
            return

        # get -x pihalf element
        pihalfminusx_element = self._get_mw_element_s3(length=rabi_period / 4., increment=0.0,
                                                       amp=microwave_amplitude, freq=microwave_frequency,
                                                       phase=180.0, pulse_function=pulse_function)

        pihalfx_element = self._get_mw_element_s3(length=rabi_period / 4., increment=0.0,
                                                  amp=microwave_amplitude, freq=microwave_frequency,
                                                  phase=0.0, pulse_function=pulse_function)

        # get y pihalf element
        pihalfy_element = self._get_mw_element_s3(length=rabi_period / 4.,
                                                  increment=0.0,
                                                  amp=microwave_amplitude,
                                                  freq=microwave_frequency,
                                                  phase=90.0,
                                                  pulse_function=pulse_function)
        # get pi elements
        pix_element = self._get_mw_element_s3(length=rabi_period / 2.,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=0.0,
                                              pulse_function=pulse_function)
        # get pi elements
        piminusx_element = self._get_mw_element_s3(length=rabi_period / 2.,
                                                   increment=0.0,
                                                   amp=microwave_amplitude,
                                                   freq=microwave_frequency,
                                                   phase=180.0,
                                                   pulse_function=pulse_function)

        piy_element = self._get_mw_element_s3(length=rabi_period / 2.,
                                              increment=0.0,
                                              amp=microwave_amplitude,
                                              freq=microwave_frequency,
                                              phase=90.0,
                                              pulse_function=pulse_function)
        # get tau/4 element
        tau_element = self._get_idle_element(length=tau / 4.0 - rabi_period / 2, increment=0)

        # create Pol 2.0 block element list
        block = PulseBlock(name=name)
        # actual (Pol 2.0)_2N sequence
        if not alternating:
            for nn in range(2 * order):
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
        else:
            for nn in range(2 * order):
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


        created_blocks.append(block)
        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=True)
        block_ensemble.append((block.name, 0))

        # add metadata to invoke settings
        block_ensemble = self._add_metadata_to_settings(block_ensemble, created_blocks=created_blocks, alternating=False)
        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)

        return created_blocks, created_ensembles, created_sequences