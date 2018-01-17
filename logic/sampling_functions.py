# -*- coding: utf-8 -*-

"""
This file contains the Qudi file with all available sampling functions.

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

import numpy as np
from collections import OrderedDict
# Specify here all classes that are actually sampling functions
__all__ = ['Idle', 'DC', 'Sin', 'DoubleSin', 'TripleSin']


class Idle(object):
    """
    Object representing an idle element (zero voltage)
    """
    params = OrderedDict()

    def __init__(self):
        return

    @staticmethod
    def get_samples(time_array):
        samples_arr = np.zeros(len(time_array))
        return samples_arr


class DC(object):
    """
    Object representing an DC element (constant voltage)
    """
    params = OrderedDict()
    params['voltage'] = {'unit': 'V', 'init': 0.0, 'min': -np.inf, 'max': +np.inf, 'type': float}

    def __init__(self, voltage):
        self.voltage = voltage
        return

    @staticmethod
    def _get_dc(time_array, voltage):
        samples_arr = np.zeros(len(time_array)) + voltage
        return samples_arr

    def get_samples(self, time_array):
        samples_arr = self._get_dc(time_array, self.voltage)
        return samples_arr


class Sin(object):
    """
    Object representing a sine wave element
    """
    params = OrderedDict()
    params['amplitude'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase'] = {'unit': '°', 'init': 0.0, 'min': 0.0, 'max': 2*np.pi, 'type': float}

    def __init__(self, amplitude, frequency, phase):
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase
        return

    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def get_samples(self, time_array):
        phase_rad = np.pi * self.phase / 180
        # conversion for AWG to actually output the specified voltage
        amp_conv = 2 * self.amplitude
        samples_arr = self._get_sine(time_array, amp_conv, self.frequency, phase_rad)
        return samples_arr


class DoubleSin(object):
    """
    Object representing a double sine wave element (Superposition of two sine waves; NOT normalized)
    """
    params = OrderedDict()
    params['amplitude_1'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_1'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_1'] = {'unit': '°', 'init': 0.0, 'min': 0.0, 'max': 2 * np.pi, 'type': float}
    params['amplitude_2'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_2'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_2'] = {'unit': '°', 'init': 0.0, 'min': 0.0, 'max': 2*np.pi, 'type': float}

    def __init__(self, amplitude_1, frequency_1, phase_1, amplitude_2, frequency_2, phase_2):
        self.amplitude = [amplitude_1, amplitude_2]
        self.frequency = [frequency_1, frequency_2]
        self.phase = [phase_1, phase_2]
        return

    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def get_samples(self, time_array):
        # First sine wave
        phase_rad = np.pi * self.phase[0] / 180
        # conversion for AWG to actually output the specified voltage
        amp_conv = 2 * self.amplitude[0]
        samples_arr = self._get_sine(time_array, amp_conv, self.frequency[0], phase_rad)

        # Second sine wave (add on first sine)
        phase_rad = np.pi * self.phase[1] / 180
        # conversion for AWG to actually output the specified voltage
        amp_conv = 2 * self.amplitude[1]
        samples_arr += self._get_sine(time_array, amp_conv, self.frequency[1], phase_rad)
        return samples_arr


class TripleSin(object):
    """
    Object representing a triple sine wave element
    (Superposition of three sine waves; NOT normalized)
    """
    params = OrderedDict()
    params['amplitude_1'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_1'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_1'] = {'unit': '°', 'init': 0.0, 'min': 0.0, 'max': 2 * np.pi, 'type': float}
    params['amplitude_2'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_2'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_2'] = {'unit': '°', 'init': 0.0, 'min': 0.0, 'max': 2*np.pi, 'type': float}
    params['amplitude_3'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_3'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_3'] = {'unit': '°', 'init': 0.0, 'min': 0.0, 'max': 2 * np.pi, 'type': float}

    def __init__(self, amplitude_1, frequency_1, phase_1, amplitude_2, frequency_2, phase_2,
                 amplitude_3, frequency_3, phase_3):
        self.amplitude = [amplitude_1, amplitude_2, amplitude_3]
        self.frequency = [frequency_1, frequency_2, frequency_3]
        self.phase = [phase_1, phase_2, phase_3]
        return

    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def get_samples(self, time_array):
        # First sine wave
        phase_rad = np.pi * self.phase[0] / 180
        # conversion for AWG to actually output the specified voltage
        amp_conv = 2 * self.amplitude[0]
        samples_arr = self._get_sine(time_array, amp_conv, self.frequency[0], phase_rad)

        # Second sine wave (add on first sine)
        phase_rad = np.pi * self.phase[1] / 180
        # conversion for AWG to actually output the specified voltage
        amp_conv = 2 * self.amplitude[1]
        samples_arr += self._get_sine(time_array, amp_conv, self.frequency[1], phase_rad)

        # Second sine wave (add on sum of first and second)
        phase_rad = np.pi * self.phase[2] / 180
        # conversion for AWG to actually output the specified voltage
        amp_conv = 2 * self.amplitude[2]
        samples_arr += self._get_sine(time_array, amp_conv, self.frequency[2], phase_rad)
        return samples_arr


# FIXME: Not implemented yet!
# class ImportedSamples(object):
#     """
#     Object representing an element of a pre-sampled waveform from file (as for optimal control).
#     """
#     params = OrderedDict()
#     params['import_path'] = {'unit': '', 'init': '', 'min': '', 'max': '', 'type': str}
#
#     def __init__(self, importpath):
#         self.importpath = importpath
#
#     def get_samples(self, time_array):
#         # TODO: Import samples from file
#         imported_samples = np.zeros(len(time_array))
#         samples_arr = imported_samples[:len(time_array)]
