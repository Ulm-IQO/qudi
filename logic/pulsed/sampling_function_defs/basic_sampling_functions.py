# -*- coding: utf-8 -*-

"""
This file contains the Qudi file with all default sampling functions.

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
from logic.pulsed.sampling_functions import SamplingBase


class Idle(SamplingBase):
    """
    Object representing an idle element (zero voltage)
    """
    def __init__(self):
        pass

    @staticmethod
    def get_samples(time_array):
        samples_arr = np.zeros(len(time_array))
        return samples_arr


class DC(SamplingBase):
    """
    Object representing an DC element (constant voltage)
    """
    params = OrderedDict()
    params['voltage'] = {'unit': 'V', 'init': 0.0, 'min': -np.inf, 'max': +np.inf, 'type': float}

    def __init__(self, voltage=None):
        if voltage is None:
            self.voltage = self.params['voltage']['init']
        else:
            self.voltage = voltage
        return

    @staticmethod
    def _get_dc(time_array, voltage):
        samples_arr = np.zeros(len(time_array)) + voltage
        return samples_arr

    def get_samples(self, time_array):
        samples_arr = self._get_dc(time_array, self.voltage)
        return samples_arr


class Sin(SamplingBase):
    """
    Object representing a sine wave element
    """
    params = OrderedDict()
    params['amplitude'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase'] = {'unit': '°', 'init': 0.0, 'min': -np.inf, 'max': np.inf, 'type': float}

    def __init__(self, amplitude=None, frequency=None, phase=None):
        if amplitude is None:
            self.amplitude = self.params['amplitude']['init']
        else:
            self.amplitude = amplitude
        if frequency is None:
            self.frequency = self.params['frequency']['init']
        else:
            self.frequency = frequency
        if phase is None:
            self.phase = self.params['phase']['init']
        else:
            self.phase = phase
        return

    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def get_samples(self, time_array):
        phase_rad = np.pi * self.phase / 180
        samples_arr = self._get_sine(time_array, self.amplitude, self.frequency, phase_rad)
        return samples_arr


class DoubleSinSum(SamplingBase):
    """
    Object representing a double sine wave element (Superposition of two sine waves; NOT normalized)
    """
    params = OrderedDict()
    params['amplitude_1'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_1'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_1'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['amplitude_2'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_2'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_2'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}

    def __init__(self,
                 amplitude_1=None, frequency_1=None, phase_1=None,
                 amplitude_2=None, frequency_2=None, phase_2=None):
        if amplitude_1 is None:
            self.amplitude_1 = self.params['amplitude_1']['init']
        else:
            self.amplitude_1 = amplitude_1
        if frequency_1 is None:
            self.frequency_1 = self.params['frequency_1']['init']
        else:
            self.frequency_1 = frequency_1
        if phase_1 is None:
            self.phase_1 = self.params['phase_1']['init']
        else:
            self.phase_1 = phase_1

        if amplitude_2 is None:
            self.amplitude_2 = self.params['amplitude_2']['init']
        else:
            self.amplitude_2 = amplitude_2
        if frequency_2 is None:
            self.frequency_2 = self.params['frequency_2']['init']
        else:
            self.frequency_2 = frequency_2
        if phase_2 is None:
            self.phase_2 = self.params['phase_2']['init']
        else:
            self.phase_2 = phase_2
        return

    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def get_samples(self, time_array):
        # First sine wave
        phase_rad = np.pi * self.phase_1 / 180
        samples_arr = self._get_sine(time_array, self.amplitude_1, self.frequency_1, phase_rad)

        # Second sine wave (add on first sine)
        phase_rad = np.pi * self.phase_2 / 180
        samples_arr += self._get_sine(time_array, self.amplitude_2, self.frequency_2, phase_rad)
        return samples_arr


class DoubleSinProduct(SamplingBase):
    """
    Object representing a double sine wave element (Product of two sine waves; NOT normalized)
    """
    params = OrderedDict()
    params['amplitude_1'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_1'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_1'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['amplitude_2'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_2'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_2'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}

    def __init__(self,
                 amplitude_1=None, frequency_1=None, phase_1=None,
                 amplitude_2=None, frequency_2=None, phase_2=None):
        if amplitude_1 is None:
            self.amplitude_1 = self.params['amplitude_1']['init']
        else:
            self.amplitude_1 = amplitude_1
        if frequency_1 is None:
            self.frequency_1 = self.params['frequency_1']['init']
        else:
            self.frequency_1 = frequency_1
        if phase_1 is None:
            self.phase_1 = self.params['phase_1']['init']
        else:
            self.phase_1 = phase_1

        if amplitude_2 is None:
            self.amplitude_2 = self.params['amplitude_2']['init']
        else:
            self.amplitude_2 = amplitude_2
        if frequency_2 is None:
            self.frequency_2 = self.params['frequency_2']['init']
        else:
            self.frequency_2 = frequency_2
        if phase_2 is None:
            self.phase_2 = self.params['phase_2']['init']
        else:
            self.phase_2 = phase_2
        return

    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def get_samples(self, time_array):
        # First sine wave
        phase_rad = np.pi * self.phase_1 / 180
        samples_arr = self._get_sine(time_array, self.amplitude_1, self.frequency_1, phase_rad)

        # Second sine wave (add on first sine)
        phase_rad = np.pi * self.phase_2 / 180
        samples_arr *= self._get_sine(time_array, self.amplitude_2, self.frequency_2, phase_rad)
        return samples_arr


class TripleSinSum(SamplingBase):
    """
    Object representing a linear combination of three sines
    (Superposition of three sine waves; NOT normalized)
    """
    params = OrderedDict()
    params['amplitude_1'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_1'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_1'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['amplitude_2'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_2'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_2'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['amplitude_3'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_3'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_3'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}

    def __init__(self,
                 amplitude_1=None, frequency_1=None, phase_1=None,
                 amplitude_2=None, frequency_2=None, phase_2=None,
                 amplitude_3=None, frequency_3=None, phase_3=None):
        if amplitude_1 is None:
            self.amplitude_1 = self.params['amplitude_1']['init']
        else:
            self.amplitude_1 = amplitude_1
        if frequency_1 is None:
            self.frequency_1 = self.params['frequency_1']['init']
        else:
            self.frequency_1 = frequency_1
        if phase_1 is None:
            self.phase_1 = self.params['phase_1']['init']
        else:
            self.phase_1 = phase_1

        if amplitude_2 is None:
            self.amplitude_2 = self.params['amplitude_2']['init']
        else:
            self.amplitude_2 = amplitude_2
        if frequency_2 is None:
            self.frequency_2 = self.params['frequency_2']['init']
        else:
            self.frequency_2 = frequency_2
        if phase_2 is None:
            self.phase_2 = self.params['phase_2']['init']
        else:
            self.phase_2 = phase_2

        if amplitude_3 is None:
            self.amplitude_3 = self.params['amplitude_3']['init']
        else:
            self.amplitude_3 = amplitude_3
        if frequency_3 is None:
            self.frequency_3 = self.params['frequency_3']['init']
        else:
            self.frequency_3 = frequency_3
        if phase_3 is None:
            self.phase_3 = self.params['phase_3']['init']
        else:
            self.phase_3 = phase_3
        return

    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def get_samples(self, time_array):
        # First sine wave
        phase_rad = np.pi * self.phase_1 / 180
        samples_arr = self._get_sine(time_array, self.amplitude_1, self.frequency_1, phase_rad)

        # Second sine wave (add on first sine)
        phase_rad = np.pi * self.phase_2 / 180
        samples_arr += self._get_sine(time_array, self.amplitude_2, self.frequency_2, phase_rad)

        # Second sine wave (add on sum of first and second)
        phase_rad = np.pi * self.phase_3 / 180
        samples_arr += self._get_sine(time_array, self.amplitude_3, self.frequency_3, phase_rad)
        return samples_arr


class TripleSinProduct(SamplingBase):
    """
    Object representing a wave element composed of the product of three sines
    (Product of three sine waves; NOT normalized)
    """
    params = OrderedDict()
    params['amplitude_1'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_1'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_1'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['amplitude_2'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_2'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_2'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['amplitude_3'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency_3'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase_3'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}

    def __init__(self,
                 amplitude_1=None, frequency_1=None, phase_1=None,
                 amplitude_2=None, frequency_2=None, phase_2=None,
                 amplitude_3=None, frequency_3=None, phase_3=None):
        if amplitude_1 is None:
            self.amplitude_1 = self.params['amplitude_1']['init']
        else:
            self.amplitude_1 = amplitude_1
        if frequency_1 is None:
            self.frequency_1 = self.params['frequency_1']['init']
        else:
            self.frequency_1 = frequency_1
        if phase_1 is None:
            self.phase_1 = self.params['phase_1']['init']
        else:
            self.phase_1 = phase_1

        if amplitude_2 is None:
            self.amplitude_2 = self.params['amplitude_2']['init']
        else:
            self.amplitude_2 = amplitude_2
        if frequency_2 is None:
            self.frequency_2 = self.params['frequency_2']['init']
        else:
            self.frequency_2 = frequency_2
        if phase_2 is None:
            self.phase_2 = self.params['phase_2']['init']
        else:
            self.phase_2 = phase_2

        if amplitude_3 is None:
            self.amplitude_3 = self.params['amplitude_3']['init']
        else:
            self.amplitude_3 = amplitude_3
        if frequency_3 is None:
            self.frequency_3 = self.params['frequency_3']['init']
        else:
            self.frequency_3 = frequency_3
        if phase_3 is None:
            self.phase_3 = self.params['phase_3']['init']
        else:
            self.phase_3 = phase_3
        return

    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def get_samples(self, time_array):
        # First sine wave
        phase_rad = np.pi * self.phase_1 / 180
        samples_arr = self._get_sine(time_array, self.amplitude_1, self.frequency_1, phase_rad)

        # Second sine wave (add on first sine)
        phase_rad = np.pi * self.phase_2 / 180
        samples_arr *= self._get_sine(time_array, self.amplitude_2, self.frequency_2, phase_rad)

        # Second sine wave (add on sum of first and second)
        phase_rad = np.pi * self.phase_3 / 180
        samples_arr *= self._get_sine(time_array, self.amplitude_3, self.frequency_3, phase_rad)
        return samples_arr


class Chirp(SamplingBase):
    """
    Object representing a chirp element
    """
    params = OrderedDict()
    params['amplitude'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['start_freq'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf,
                                 'type': float}
    params['stop_freq'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf,
                                'type': float}

    def __init__(self, amplitude=None, phase=None, start_freq=None, stop_freq=None):
        if amplitude is None:
            self.amplitude = self.params['amplitude']['init']
        else:
            self.amplitude = amplitude
        if phase is None:
            self.phase = self.params['phase']['init']
        else:
            self.phase = phase
        if start_freq is None:
            self.start_freq = self.params['start_freq']['init']
        else:
            self.start_freq = start_freq
        if stop_freq is None:
            self.stop_freq = self.params['stop_freq']['init']
        else:
            self.stop_freq = stop_freq
        return

    def get_samples(self, time_array):
        phase_rad = np.deg2rad(self.phase)
        freq_diff = self.stop_freq - self.start_freq
        time_diff = time_array[-1] - time_array[0]
        samples_arr = self.amplitude * np.sin(2 * np.pi * time_array * (
                    self.start_freq + freq_diff * (
                        time_array - time_array[0]) / time_diff / 2) + phase_rad)
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