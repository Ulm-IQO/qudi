# -*- coding: utf-8 -*-

"""
This file contains the Qudi Hardware module NICard class.

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

import os
import time
import datetime
import numpy as np

from logic.generic_logic import GenericLogic
from logic.pulsed.pulse_objects import SequenceStep
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from core.connector import Connector


class Awg70kNiXSeriesSuperresScanner(GenericLogic):
    """

    """

    _mw_channel = ConfigOption(name='mw_channel', default='a_ch1', missing='warn')
    _laser_channel = ConfigOption(name='laser_channel', default='d_ch1', missing='warn')

    awg_connector = Connector(name='awg_connector', interface='PulserInterface')
    nicard_connector = Connector(name='nicard_connector', interface='NiXSeriesAnalogScanner')

    __sequence_name = 'superres'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._awg = None
        self._nicard = None
        self.current_estimated_time = 0.0
        self._current_scan_params = dict()
        self._current_scan_timestamp = None

    def on_activate(self):
        self._awg = self.awg_connector()
        self._nicard = self.nicard_connector()
        self.current_estimated_time = 0.0
        self._current_scan_params = dict()
        self._current_scan_timestamp = None

    def on_deactivate(self):
        self._awg = None
        self._nicard = None

    def set_up_scan(self, size, extent, axes, sample_frequency, mw_frequencies, mw_amplitudes):
        new_size = (size[0] * 3, size[1])
        if len(mw_frequencies) != 3 or len(mw_amplitudes) != 3:
            self.log.error('mw_frequencies and mw_amplitudes must be iterables of len 3')
            return True
        # TODO: Move to start position
        self._nicard.set_up_image_scan(self, new_size, extent, axes, sample_frequency)
        self.current_estimated_time = self._nicard.estimated_scan_time
        if self.create_superres_sequence(mw_frequencies, mw_amplitudes):
            return True
        self._awg.load_sequence(self.__sequence_name)
        self._awg.pulser_on()
        self._awg.pulser_off()
        self._current_scan_params['size'] = tuple(size)
        self._current_scan_params['extent'] = tuple(extent)
        self._current_scan_params['axes'] = tuple(axes)
        self._current_scan_params['sample_frequency'] = float(sample_frequency)
        self._current_scan_params['mw_frequencies'] = tuple(mw_frequencies)
        self._current_scan_params['mw_amplitudes'] = tuple(mw_amplitudes)
        return False

    def scan_image(self):
        self._current_scan_timestamp = datetime.datetime.now()
        self._awg.pulser_on()
        time.sleep(0.1)
        if self._nicard.start_image_scan():
            return True

        err_flag = False
        timeout = 1.5 * self.current_estimated_time
        start = time.time()
        while self._nicard.module_state() != 'idle':
            if time.time() - start > timeout:
                self.log.error('Image scan timed out...')
                err_flag = True
                break
            time.sleep(1.0)
        self._awg.pulser_off()
        time.sleep(0.1)
        return err_flag

    def get_scan_images(self):
        return self._nicard.get_scan_data(), self._nicard.get_backscan_data()

    def save_scan(self, save_dir):
        if not os.path.exists(save_dir):
            self.log.error('Save directory "{0}" non-existent.'.format(save_dir))
            return True
        timestamp = self._current_scan_timestamp.strftime('%Y%m%d_%Hh%Mm%Ss')
        header = '{0}\n'.format(timestamp)
        header += '\n'.join(
            ['{0}: {1}'.format(key, value) for key, value in self._current_scan_params.items()])

        for channel, image in self._nicard.get_scan_data().items():
            filename = 'superres_scan_{0}_{1}.dat'.format(channel, timestamp)
            np.savetxt(os.path.join(save_dir, filename), image, header=header)
        for channel, image in self._nicard.get_backscan_data().items():
            filename = 'superres_backscan_{0}_{1}.dat'.format(channel, timestamp)
            np.savetxt(os.path.join(save_dir, filename), image, header=header)
        return False

    def create_superres_sequence(self, mw_frequencies, mw_amplitudes):
        self._awg.pulser_off()
        wfm_names = ('mw0_{0}'.format(self.__sequence_name),
                     'mw1_{0}'.format(self.__sequence_name),
                     'mw2_{0}'.format(self.__sequence_name))
        # Delete old waveforms
        self._awg.delete_waveform(wfm_names)
        # query currently active channels
        active_channels = tuple(ch for ch, on in self._awg.get_active_channels().items() if on)
        digital_channels = tuple(ch for ch in active_channels if ch.startswith('d'))
        analog_channels = tuple(ch for ch in active_channels if ch.startswith('a'))
        # query current sample rate
        sample_rate = self._awg.get_sample_rate()
        # query current peak-to-peak voltages
        pp_voltages, _ = self._awg.get_analog_level(amplitude=analog_channels, offset=())
        # Check necessary channel activity
        if self._mw_channel not in analog_channels:
            self.log.error('MW channel specified as ConfigOption not present in currently active '
                           'analog channels.')
            return True
        if self._laser_channel not in digital_channels:
            self.log.error('Laser trigger channel specified as ConfigOption not present in '
                           'currently active digital channels.')
            return True

        # Create waveforms
        created_waveforms = list()
        for ii, mw_freq in enumerate(mw_frequencies):
            wfm_name = wfm_names[ii]
            analog_samples = dict()
            digital_sampels = dict()
            wfm_length = int(round(sample_rate * 100 / mw_freq))
            for ch in analog_channels:
                if ch == self._mw_channel:
                    amp = 2 * mw_amplitudes[ii] / pp_voltages[ch]
                    analog_samples[ch] = amp * np.sin(
                        2 * np.pi * mw_freq * np.arange(wfm_length, dtype=np.float32) / sample_rate)
                else:
                    analog_samples[ch] = np.zeros(wfm_length, dtype=np.float32)
            for ch in digital_channels:
                if ch == self._laser_channel:
                    digital_sampels[ch] = np.ones(wfm_length, dtype=bool)
                else:
                    digital_sampels[ch] = np.zeros(wfm_length, dtype=bool)
            written_samples, wfm_list = self._awg.write_waveform(name=wfm_name,
                                                                 analog_samples=analog_samples,
                                                                 digital_samples=digital_sampels,
                                                                 is_first_chunk=True,
                                                                 is_last_chunk=True,
                                                                 total_number_of_samples=wfm_length)
            if written_samples != wfm_length:
                self.log.error('Number of written samples ({0:d}) != desired waveform length({1:d})'
                               ''.format(written_samples, wfm_length))
                return True
            created_waveforms.append(tuple(wfm_list))
        print('waveforms in AWG memory:', self._awg.get_waveform_names())
        print('created waveforms:', created_waveforms)

        # Create sequence
        sequence_params = list()
        # First step is special
        step_params = SequenceStep(ensemble=wfm_names[0],
                                   repetitions=-1,
                                   go_to=3,
                                   event_jump_to=3,
                                   event_trigger='A',
                                   wait_for='A')
        sequence_params.append((created_waveforms[0], step_params))
        for ii, wfm_name in enumerate(wfm_names):
            wfm_tuple = created_waveforms[ii]
            goto = 2 if ii == (len(wfm_names) - 1) else -1
            step_params = SequenceStep(ensemble=wfm_name,
                                       repetitions=-1,
                                       go_to=goto,
                                       event_jump_to=goto,
                                       event_trigger='A')
            sequence_params.append((wfm_tuple, step_params))
        steps_written = self._awg.write_sequence(self.__sequence_name, sequence_params)
        if steps_written != len(wfm_names) + 1:
            self.log.error('Unexpected number of written sequence steps ({0:d}). Expected 4 steps.'
                           ''.format(steps_written))
            return True
        return False
