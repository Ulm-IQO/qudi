# -*- coding: utf-8 -*-
"""
Exposure timer for X Series National Instruments card.

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

from core.module import Base, ConfigOption
#from interface.exposure_controller import ExposureControllerInterface
import nidaqmx
import nidaqmx.constants as cnx


class NIExposureTimer(Base): #, ExposureControllerInterface):
    """
    This module implements communication with Picoamperemeter.

    This module is untested and very likely broken.
    """
    _modclass = 'niexposure'
    _modtype = 'hardware'

    # config options
    _device = ConfigOption('device', missing='error')
    _counter = ConfigOption('counter', missing='error')

    def on_activate(self):
        """ Activate module
        """
        self.idle_level = cnx.Level.HIGH
        self.timebase = '80MHzTimebase'
        self._timebase_hz = 80e6
        self.counter_task = None
        self.hardware_triggered = False
        self.pause_ticks = 2
        self.expose_ticks = 2

    def on_deactivate(self):
        """ Deactivate module
        """
        self.stop_exposure()

    def prepare_exposure(self):
        if self.counter_task is not None:
            return -1

        self.counter_task = nidaqmx.Task('ExposureCounterTask')
        self.counter_task.co_channels.add_co_pulse_chan_ticks(
            '/' + self._device + '/' + self._counter,
            '/' + self._device + '/' + self.timebase,
            idle_state=self.idle_level,
            low_ticks=int(round(self.pause_ticks)),
            high_ticks=int(round(self.expose_ticks))
            )
        if self.hardware_triggered:
            self.counter_task.triggers.start_trigger.trig_type = cnx.TriggerType.DIGITAL_EDGE
            self.counter_task.triggers.start_trigger.dig_edge_edge = cnx.Edge.RISING
            self.counter_task.triggers.start_trigger.dig_edge_src = '/' + self._device + '/' + self._trg_source
        return 0

    def start_exposure(self):
        self.counter_task.start()
        return 0

    def stop_exposure(self):
        if self.counter_task is not None:
            self.counter_task.stop()
            return 0
        return -1

    def configure_exposure(self, low_time, high_time, idle_level=False):
        self.pause_ticks = int(round(self._timebase_hz * low_time))
        self.expose_ticks = int(round(self._timebase_hz * high_time))

        if idle_level:
            self.idle_level = cnx.Level.HIGH
        else:
            self.idle_level = cnx.Level.LOW

    def get_status(self):
        if self.counter_task is None:
            return -1

        return self.counter_task.is_task_done()
