# -*- coding: utf-8 -*-
"""
Optimizer refocus task with laser on.

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


class Task(InterruptableTask):
    """ This task pauses pulsed measurement, run laser_on, does a poi refocus then goes back to the pulsed acquisition.

    It uses poi manager refocus duration as input.

    Example:
        tasks:
            pulsed_refocus:
                module: 'pulsed_refocus'
                needsmodules:
                    poi_manager: 'poimanagerlogic'
                    optimizer_logic: 'optimizerlogic'
                    pulsed_master: 'pulsedmasterlogic'
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._poi_manager = self.ref['poi_manager']
        self._optimizer_logic = self.ref['optimizer_logic']
        # self._laser = self.ref['laser']
        self._master = self.ref['pulsed_master']
        self._generator = self.ref['pulsed_master'].sequencegeneratorlogic()
        self._measurement = self.ref['pulsed_master'].pulsedmeasurementlogic()
        self._was_invoke_settings = None
        self._was_running = None
        self._was_loaded = None
        # self._was_power = None
        # self.check_config_key('power', 300e-6)
        # self._power = self.config['power']

    def startTask(self):
        """ Stop pulsed with backup , start laser_on, do refocus """

        self._was_running = self._measurement.module_state() == 'locked'
        if self._was_running:
            self._measurement.stop_pulsed_measurement('refocus')
        self._was_loaded = tuple(self._generator.loaded_asset)
        # self._was_power = self._laser.get_power_setpoint()
        self._was_invoke_settings = self._measurement.measurement_settings['invoke_settings']

        # self._laser.set_power(self._power)
        self.wait_for_idle()
        self._generator.generate_predefined_sequence(predefined_sequence_name='laser_on', kwargs_dict={})
        self._generator.sample_pulse_block_ensemble('laser_on')
        self._generator.load_ensemble('laser_on')
        self._measurement.set_measurement_settings(invoke_settings=False)
        self._measurement.start_pulsed_measurement()
        self._poi_manager.optimise_poi_position()

    def runTaskStep(self):
        """ Wait for refocus to finish. """
        time.sleep(0.1)
        return self._optimizer_logic.module_state() != 'idle'

    def pauseTask(self):
        """ pausing a refocus is forbidden """
        pass

    def resumeTask(self):
        """ pausing a refocus is forbidden """
        pass

    def cleanupTask(self):
        """ go back to pulsed acquisition from backup """
        self._measurement.stop_pulsed_measurement()
        self.wait_for_idle()
        if self._was_loaded[1] == 'PulseBlockEnsemble':
            self._generator.sample_pulse_block_ensemble(self._was_loaded[0])
            self._generator.load_ensemble(self._was_loaded[0])
        # self._laser.set_power(self._was_power)
        if self._was_invoke_settings:
            self._measurement.set_measurement_settings(invoke_settings=True)
        if self._was_running:
            self._measurement.start_pulsed_measurement('refocus')

    def checkExtraStartPrerequisites(self):
        """ Check whether anything we need is locked. """
        return self._optimizer_logic.module_state() == 'idle'

    def checkExtraPausePrerequisites(self):
        """ pausing a refocus is forbidden """
        return False

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
