# -*- coding: utf-8 -*-
"""
Pulsed experiment task

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from logic.generic_task import InterruptableTask
import time
# from sklearn.model_selection import ParameterGrid
import random
import numpy as np
import copy


class Task(InterruptableTask):
    """ This task is used to acquire a pulsed experiment in a interruptable context

    it needs :
        - 'pulsed_master' : pulsed_measurement_logic
        - 'laser' : laser to control power
        - 'save' : save logic to update additional parameters
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._master = self.ref['pulsed_master']
        self._generator = self.ref['pulsed_master'].sequencegeneratorlogic()
        self._measurement = self.ref['pulsed_master'].pulsedmeasurementlogic()
        self._laser = self.ref['laser']
        self._save = self.ref['save']

    def get_generation_parameter(self, param):
        """ Helper method to get a generation parameter """
        return self._generator.generation_parameters[param]

    def grid(self, dic):
        """ Create an list of dict representing a parameter space

            @param (dict) dic: A dictionarry where each key is a parameter and values the possible values

            @return (list): a list of parameter points dictionnaryies

            This function tries to copy sklearn ParameterGrid object.

            It takes a input {'a': [1, 2], 'b': [True, False]} and output :
                [{'b': True, 'a': 1}, {'b': False, 'a': 1},
                 {'b': True, 'a': 2}, {'b': False, 'a': 2}]
        """
        dic = copy.deepcopy(dic)
        first_key = list(dic.keys())[0]
        if len(dic) == 1:
            return [{first_key: value} for value in dic[first_key]]
        else:
            values = dic.pop(first_key)
            _list = []
            sub_list = self.grid(dic)
            for value in values:
                sub_list = copy.deepcopy(sub_list)
                for l in sub_list:
                    l[first_key] = value
                _list += sub_list
            return _list

    def get_current_predefined_method_parameters(self):
        """ Getter method for the parameters that should be sent to the predefined generation method """
        row = copy.deepcopy(self.get_current_row())
        res = {}
        for key in self.config['predefined_method_parameters'].keys():
            res[key] = row(key)
        return res

    def startTask(self):
        """ Method called when the task is tarted

        1. Check the parameters in config
        2. Create the parameter grid
        """

        self.check_config_key('name', 'pulsed_task')

        self._was_running = self._measurement.module_state() == 'locked'
        self._was_loaded = tuple(self._generator.loaded_asset)
        self._was_power = self._laser.get_power_setpoint()
        if self._was_running:
            self._measurement.stop_pulsed_measurement()
        self._was_invoke_settings = self._measurement.measurement_settings['invoke_settings']

        self.check_config_key('wait_time', [self.get_generation_parameter('wait_time')])
        self.check_config_key('laser_length', [self.get_generation_parameter('laser_length')])
        self.check_config_key('laser_delay', [self.get_generation_parameter('laser_delay')])
        self.check_config_key('power', [self._laser.get_power_setpoint()])
        self.check_config_key('predefined_method_parameters', {})
        parameters = ['wait_time', 'laser_length', 'laser_delay', 'power']
        param_grid = dict([(key, self.config[key]) for key in parameters])
        param_grid.update(self.config['predefined_method_parameters'])

        self._list = self.grid(param_grid)
        self._list_metadata = [{'elapsed_time': 0, 'elapsed_photon_count': 0, 'elapsed_sweeps': 0}]*len(self._list)


        duration_modes = ['same_time', 'same_photon_count', 'same_sweeps']
        self.check_config_key('duration_mode', 'same_time', possible_values=duration_modes)
        self.check_config_key('switch_time', 1*60)

        self.check_config_key('max_time', None)

        self.check_config_key('save_laser_pulses', True)
        self.check_config_key('save_pulsed_measurement', True)
        self.check_config_key('save_figure', True)

        self._start_time = time.time()

        self._time_since_last_swtich = 0
        self._current_row = 0

        self._random_key = random.randint(0, 1e9) # key to prevent collision in pulsed saved data

        self.activate_row()

    def runTaskStep(self):
        """ The main loop of the task

        Check if it's time to switch row or stop task. Else continue
        """
        if self._time_since_last_swtich > self.config['switch_time']:
            self.go_to_next_row()

        self._time_since_last_swtich += 0.1
        time.sleep(0.1)
        if self.config['max_time'] is not None and time.time() - self._start_time > self.config['max_time']:
            return False
        else:
            return True  # continue

    def get_key(self, row_number):
        """ Helper function to get unique key for each row """
        return '{:d}_{:d}'.format(self._random_key, row_number)

    def get_current_row(self):
        """ Helper function to get current row object """
        return self._list[self._current_row]

    def stop_current_row(self):
        """ Method to stop the current row acquisition """
        self._measurement.stop_pulsed_measurement(self.get_key(self._current_row))
        current_meta = self._list_metadata[self._current_row]
        current_meta['elapsed_time'] = self._measurement.elapsed_time
        current_meta['elapsed_sweeps'] = self._measurement.elapsed_sweeps
        current_meta['elapsed_photon_count'] = self._measurement.raw_data.sum()
        self.wait_for_idle()

    def go_to_next_row(self):
        """ Method  to stop current row and start next """
        self.stop_current_row()
        self._time_since_last_swtich = 0

        properties = {'same_time': 'elapsed_time',
                      'same_photon_count': 'elapsed_photon_count',
                      'same_sweeps': 'elapsed_sweeps'}
        array = np.array([row[properties[self.config['duration_mode']]] for row in self._list_metadata])
        self._current_row = np.argmin(array)
        self.activate_row()

    def activate_row(self):
        """ Method to create pulsed sequence for current row and measurement settings """
        self.wait_for_idle()
        self.make_sequence(self.config['name'], **self.get_current_row())
        self._measurement.set_measurement_settings(invoke_settings=True)
        self._laser.set_power(self.get_current_row()['power'])
        self._measurement.start_pulsed_measurement(self.get_key(self._current_row))
        self._save.update_additional_parameters(**self._list[self._current_row])

    def make_sequence(self, name, wait_time, laser_delay, laser_length, **_):
        """ Build, sample and load the current row ensemble """
        self._generator.set_generation_parameters(wait_time=wait_time)
        self._generator.set_generation_parameters(laser_delay=laser_delay)
        self._generator.set_generation_parameters(laser_length=laser_length)
        self._generator.generate_predefined_sequence(predefined_sequence_name=name,
                                                     kwargs_dict=self.get_current_predefined_method_parameters())
        self._generator.sample_pulse_block_ensemble(name)
        self._generator.load_ensemble(name)

    def pauseTask(self):
        """ Pause the acquisition in a way that can be resumed even if user change stuff in pulsed module"""
        pass

    def on_pausing(self, e):
        """ Function that is actually called before other task are started """
        self.stop_current_row()
        self.wait_for_idle()

    def resumeTask(self):
        """ Resume paused measurement """
        if self._measurement.module_state() != 'idle':
            self._measurement.stop_pulsed_measurement()
        self.activate_row()

    def cleanupTask(self):
        """ End of task, let's stop save the stuff.

        We have to start/stop/save every one for now.

        """
        if self._measurement.module_state != 'idle':
            self.stop_current_row()

        for i, row in enumerate(self._list):
            self.wait_for_idle()
            self._current_row = i
            self.activate_row()
            self.stop_current_row()
            self._measurement.save_measurement_data(tag=self.name,
                                                    save_laser_pulses=self.config['save_laser_pulses'],
                                                    save_pulsed_measurement=self.config['save_pulsed_measurement'],
                                                    save_figure=self.config['save_figure'])

        if self._was_loaded[1] == 'PulseBlockEnsemble':
            self.wait_for_idle()
            self._generator.sample_pulse_block_ensemble(self._was_loaded[0])
            self._generator.load_ensemble(self._was_loaded[0])
        self._laser.set_power(self._was_power)
        self._measurement.set_measurement_settings(invoke_settings=self._was_invoke_settings)
        if self._was_running:
            self._measurement.start_pulsed_measurement()

    def wait_for_idle(self, timeout=20):
        """ Function to wait for the measurement to be idle

        @param timeout: the maximum time to wait before causing an error (in seconds)
        """
        counter = 0
        while self._measurement.module_state() != 'idle' and self._master.status_dict['measurement_running'] and\
                counter < timeout:
            time.sleep(0.1)
            counter += 0.1
        if counter >= timeout:
            self.log.warning('Measurement is too long to stop, continuing anyway')

    # def checkExtraStartPrerequisites(self):
    #     """ Check whether anything we need is locked. """
    #     return True
    #
    #
    # def checkExtraPausePrerequisites(self):
    #     """ pausing a refocus is forbidden """
    #     return True
    #
