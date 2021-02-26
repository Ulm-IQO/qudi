# -*- coding: utf-8 -*-

"""
ToDo: Document

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

from qudi.util.mutex import RecursiveMutex
from qudi.core.module import LogicBase
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.interface.microwave_interface import MicrowaveMode, TriggerEdge

class OdmrNicardScannerInterfuse(LogicBase):
    """ ToDo: Document
    """
    # _threaded = False

    _microwave = Connector(name='microwave', interface='MicrowaveInterface')
    _nicard = Connector(name='nicard', interface='FiniteSamplingDummy')

    _sampling_mode = ConfigOption(name='sampling_mode',
                                  missing='error',
                                  converter=lambda x: MicrowaveMode[x.upper()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = RecursiveMutex()

    def on_activate(self):
        mw = self._microwave()
        ni = self._nicard()
        assert self._sampling_mode in (MicrowaveMode.LIST, MicrowaveMode.SWEEP), \
            'No valid frequency sampling mode defined in config'
        assert mw.constraints.mode_supported(self._sampling_mode), \
            'Chosen frequency sampling mode not supported by microwave hardware'

        # Assemble combined constraints
        ni_points_limits = ni.constraints['acquisition_length_limits']
        if self._sampling_mode == MicrowaveMode.LIST:
            mw_points_limits = mw.constraints.list_points_limits
        else:
            mw_points_limits = mw.constraints.sweep_points_limits
        points_limits = (max(ni_points_limits[0], mw_points_limits[0]),
                         min(ni_points_limits[1], mw_points_limits[1]))

        if self._sampling_mode == MicrowaveMode.LIST:
            step_limits = mw.constraints.list_step_limits
        else:
            step_limits = mw.constraints.sweep_step_limits

        ni_rate_limits = ni.constraints['sample_rate_limits']
        mw_rate_limits = mw.constraints.trigger_rate_limits
        sample_rate_limits = (max(ni_rate_limits[0], mw_rate_limits[0]),
                              min(ni_rate_limits[1], mw_rate_limits[1]))

        self._constraints = {
            'multiple_ranges_available': self._sampling_mode == MicrowaveMode.LIST,
            'cw_output_available'      : mw.constraints.mode_supported(MicrowaveMode.CW),
            'frequency_limits'         : mw.constraints.frequency_limits,
            'power_limits'             : mw.constraints.power_limits,
            'sample_rate_limits'       : sample_rate_limits,
            'points_limits'            : points_limits,
            'step_limits'              : step_limits
        }

        # Determine trigger edge
        if mw.constraints.trigger_edge_supported(TriggerEdge.RISING):
            self._trigger_edge = TriggerEdge.RISING
        else:
            self._trigger_edge = TriggerEdge.FALLING

        # unify shared settings upon activation
        mw_sample_rate = mw.trigger_parameters[1]
        ni_sample_rate = ni.sample_rate
        if mw_sample_rate != ni_sample_rate:
            if sample_rate_limits[0] <= ni_sample_rate <= sample_rate_limits[1]:
                sample_rate = ni_sample_rate
            elif sample_rate_limits[0] <= mw_sample_rate <= sample_rate_limits[1]:
                sample_rate = mw_sample_rate
            else:
                sample_rate = sample_rate_limits[1]
            self.set_sample_rate(sample_rate)

        # process parameters
        self._frequency_ranges = None

    def on_deactivate(self):
        pass

    @property
    def constraints(self):
        return self._constraints.copy()

    @property
    def sample_rate(self):
        with self._thread_lock:
            ni_sample_rate = self._nicard().sample_rate
            mw_sample_rate = self._microwave().trigger_parameters[1]
            if ni_sample_rate != mw_sample_rate:
                self.log.warning('NIcard and microwave sample rates have diverged.')
            return ni_sample_rate

    @property
    def frequency_ranges(self):
        return self._frequency_ranges.copy()

    @property
    def cw_parameters(self):
        return self._microwave().cw_parameters

    @property
    def channel_units(self):
        return self._nicard().channel_units

    def set_sample_rate(self, rate):
        with self._thread_lock:
            ni = self._nicard()
            mw = self._microwave()

            mw.set_trigger(self._trigger_edge, rate)
            old_mw_rate = mw.trigger_parameters[1]
            try:
                ni.set_sample_rate(rate)
            except:
                mw.set_trigger(self._trigger_edge, old_mw_rate)
                raise

    def set_frequency_ranges(self, ranges):
        with self._thread_lock:
            assert len(ranges) == 1 or self._constraints['multiple_ranges_available'], \
                'Multiple frequency ranges not supported by hardware or chosen sampling mode'
            if self._sampling_mode == MicrowaveMode.LIST:
                frequencies = list()
                for start, stop, points in ranges:
                    frequencies.extend(np.linspace(start, stop, points))
                self._microwave().set_list(frequencies=frequencies)
            else:
                start, stop, points = ranges[0]
                self._microwave().set_sweep(start=start, stop=stop, points=points)
            self._frequency_ranges = ranges.copy() if isinstance(ranges, list) else list(ranges)

    def set_cw_parameters(self, frequency=None, power=None):
        self._microwave().set_cw(frequency=frequency, power=power)

    def reset_frequency_scan(self):
        if self._sampling_mode == MicrowaveMode.LIST:
            self._microwave().reset_list()
        else:
            self._microwave().reset_sweep()

    def off(self):
        with self._thread_lock:
            try:
                self._microwave().off()
                self._nicard().stop_buffered_acquisition()
            finally:
                if self.module_state() == 'locked':
                    self.module_state.unlock()

    def start_scan(self):
        with self._thread_lock:
            assert self.module_state() == 'idle', 'Unable to start scan. Module is already locked.'
            mw = self._microwave()
            self.module_state.lock()
            try:
                if self._sampling_mode == MicrowaveMode.LIST:
                    mw.list_on()
                else:
                    mw.sweep_on()
            except:
                mw.off()
                self.module_state.unlock()
                raise

    def cw_on(self):
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to start CW output. Module is already locked.'
            mw = self._microwave()
            self.module_state.lock()
            try:
                mw.cw_on()
            except:
                mw.off()
                self.module_state.unlock()
                raise

    def get_single_scan(self):
        with self._thread_lock:
            return self._nicard().acquire_samples()
