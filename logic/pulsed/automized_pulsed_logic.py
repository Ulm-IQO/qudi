# -*- coding: utf-8 -*-
"""
Master logic to combine sequence_generator_logic and pulsed_measurement_logic to be
used with a single GUI.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from core.module import Connector
from logic.generic_logic import GenericLogic
import time


class AutomizedPulsedLogic(GenericLogic):
    """
    This logic module allows to perform automized measurements. It is possible to perform multiple measurements on the
    same spot, the same measurement on different spots and both.

    This logic module has no GUI at the moment, thus can only be accessed directly or via script
    """
    _modclass = 'automizedpulsedlogic'
    _modtype = 'logic'

    # declare connectors
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')
    poimanagerlogic = Connector(interface='PoimanagerLogic')


    def __init__(self, config, **kwargs):
        """ Create PulsedMasterLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        return

    def on_deactivate(self):
        """
        @return:
        """
        return

    def do_experiment(self, experiment, qm_dict, generate_new=True, save_tag='', load_tag=''):
        """
        Performs a pulsedmeasurement on its own

        @param string experiment: name of the generate method
        @param dict qm_dict: Dictionary with measurement parameters
        @param bool generate_new: should be a new ensembled generated
        @param string save_tag: save_name of the measurement
        @param string load_tag: load_tag

        @return bool user_terminated: Did the user dertimate the measurement
        """
        # perform sanity checks
        if experiment not in self.pulsedmasterlogic().generate_methods:
            self.log.error('Unknown Experiment {0}'.format(experiment))
            return -1
        # prepare the measurement by generating and loading the sequence/waveform
        self.prepare_qm(experiment, qm_dict, generate_new)
        # perform measurement
        user_terminated = self.perform_measurement(qm_dict=qm_dict, load_tag=load_tag, save_tag=save_tag)

        return user_terminated

    def prepare_qm(self, experiment, qm_dict, generate_new=True):
        ###### Prepare a quantum measurement by generating the sequence and loading it up to the pulser
        if generate_new:
            #set the generation parameters
            subdict = dict(
                [(key, qm_dict.get(key)) for key in self.pulsedmasterlogic().generation_parameters if key in qm_dict])
            self.pulsedmasterlogic().set_generation_parameters(subdict)
            self.generate_sample_upload(experiment, qm_dict)
        else:
            self.load_into_channel(qm_dict['name'])
        self.set_parameters(qm_dict)

        return qm_dict

    def generate_sample_upload(self, experiment, qm_dict):

        # make sure a previous ensemble or sequence is deleted
        self.pulsedmasterlogic().delete_block_ensemble(qm_dict['name'])
        # generate the ensemble or sequence
        try:
            self.pulsedmasterlogic().generate_predefined_sequence(experiment, qm_dict.copy())
        except:
            self.log.error('Generation failed')
            return -1
        # sample the ensemble or sequence
        while qm_dict['name'] not in self.pulsedmasterlogic().saved_pulse_block_ensembles: time.sleep(0.2)
        self.pulsedmasterlogic().sample_ensemble(qm_dict['name'], True)
        # wait till sequence is sampled
        while self.pulsedmasterlogic().status_dict['sampload_busy']: time.sleep(0.2)
        return

    def load_into_channel(self, name):
        # upload ensemble to pulser channel with sanity check
        if name + '_ch1' in self.pulsedmasterlogic().sampled_waveforms:
            self.pulsedmasterlogic().load_ensemble(name)
        else:
            self.pulsedmasterlogic().log.error('Ensemble not found. Cannot load to channel')
        # wait until ensemble is loaded to channel
        while self.pulsedmasterlogic().status_dict['loading_busy']: time.sleep(0.1)
        return

    def set_parameters(self, qm_dict):

        qm_dict['params'] = self.pulsedmasterlogic().saved_pulse_block_ensembles.get(
            qm_dict['name']).measurement_information
        self.pulsedmasterlogic().set_measurement_settings(qm_dict['params'])
        self.pulsedmasterlogic().set_fast_counter_settings({'record_length': qm_dict['params']['counting_length']})
        time.sleep(0.3)
        qm_dict['current_poi'] = self.poimanagerlogic().active_poi.get_key()
        return qm_dict

    ############################### Perform Measurement Methods ############################################################


    def perform_measurement(self, qm_dict, load_tag='', save_tag=''):
        #remove fit
        self.pulsedmasterlogic().do_fit('No Fit')
        ################ Start and perform the measurement #################
        user_terminated = self.conventional_measurement(qm_dict, load_tag)
        ########################## Save data ###############################
        self.pulsedmasterlogic().save_measurement_data(save_tag, True)
        time.sleep(1)
        return user_terminated


    def conventional_measurement(self, qm_dict, load_tag):
        # perform measurement
        self.pulsedmasterlogic().toggle_pulsed_measurement(True, load_tag)
        while not self.pulsedmasterlogic().status_dict['measurement_running']: time.sleep(0.5)
        user_terminated = self.control_measurement(qm_dict)
        self.pulsedmasterlogic().toggle_pulsed_measurement(False)
        while self.pulsedmasterlogic().status_dict['measurement_running']: time.sleep(0.5)
        return user_terminated

    def control_measurement(self, qm_dict, analysis_method=None):
        ################# Set the timer and run the measurement #################
        start_time = time.time()
        optimize_real_time = start_time

        while True:
            time.sleep(2)
            if qm_dict['measurement_time'] is not None:
                if (time.time() - start_time) > qm_dict['measurement_time']:
                    user_terminated = False
                    break
            if not self.pulsedmasterlogic().status_dict['measurement_running']:
                user_terminated = True
                break
            ##################### optimize position #######################
            if qm_dict['optimize_time'] is not None:
                if time.time() - optimize_real_time > qm_dict['optimize_time']:
                    additional_time = self.optimize_position(qm_dict['current_poi'])
                    start_time = start_time + additional_time
                    optimize_real_time = time.time()
        time.sleep(0.2)
        return user_terminated


############################################### Optimize position method ####################################

    def optimize_position(self, poi_key):
        time_start_optimize = time.time()
        # switch on laser
        # FIXME: Here add method to turn on laser
        # perform refocus
        self.poimanagerlogic().optimise_poi(poi_key)
        time.sleep(0.5)
        # switch off laser
        #FIXME: Here add method to turn off laser and reload sequence
        # pulsedmeasurementlogic.fast_counter_continue()
        time_stop_optimize = time.time()
        additional_time = (time_stop_optimize - time_start_optimize)
        return additional_time



    def do_automized_measurements(self, qm_dict, autoexp):

        # If there is not list of pois specified, take all pois from the current roi
        if not qm_dict['list_pois']:
            qm_dict['list_pois'] = self.poimanagerlogic().get_all_pois()
            # remove 'crosshair' and 'sample'
            qm_dict['list_pois'].remove('crosshair')
            qm_dict['list_pois'].remove('sample')

        # variable to break out of the loop/ an be changed in manager
        self.break_variable = False

        first_poi = True
        # loop over all the pois
        for poi in qm_dict['list_pois']:
            if self.break_variable == True: break
            # move to current poi and optimize position
            self.poimanagerlogic().go_to_poi(poi)
            self.optimize_position(poi)

            # perform all experiments
            for experiment in autoexp:
                if self.break_variable == True: break
                # perform the measurement
                if first_poi:
                    self.do_experiment(experiment=autoexp[experiment]['type'], qm_dict=autoexp[experiment],
                                  generate_new=True, save_tag=autoexp[experiment]['name'] + poi)
                else:
                    self.do_experiment(experiment=autoexp[experiment]['type'], qm_dict=autoexp[experiment],
                                  generate_new=autoexp[experiment]['generate_new'],
                                  save_tag=autoexp[experiment]['name'] + poi)
                first_poi = False

                # fit and update parameters
                if 'fit_experiment' in autoexp[experiment]:
                    if autoexp[experiment]['fit_experiment'] != '':
                        self.pulsedmasterlogic().do_fit(autoexp[experiment]['fit_experiment'])
                        #while self.pulsedmasterlogic().status_dict['fitting_busy']: time.sleep(0.2)
                        time.sleep(1)
                        if 'fit_parameter' in autoexp[experiment]:
                            fit_dict = self.pulsedmasterlogic().fit_container.current_fit_result.result_str_dict
                            fit_para = fit_dict[autoexp[experiment]['fit_parameter']]['value']
                            if 'update_parameters' in autoexp[experiment]:
                                for key in autoexp[experiment]['update_parameters']:
                                    autoexp[key][autoexp[experiment]['update_parameters'][key]] = fit_para

                if 'optimize_between_experiments' in qm_dict and qm_dict['optimize_between_experiments']:
                    self.optimize_position(poi)
        return


