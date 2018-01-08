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

import abc
import numpy as np
from collections import OrderedDict


class PulseBlockElement(object, metaclass=abc.ABCMeta):
    """
    Base class representing the atomic element of a pulse block.
    """
    params = OrderedDict()
    params['length'] = {'unit': 's', 'init': 0.0, 'min': 0.0, 'max': +np.inf, 'type': float}
    params['increment'] = {'unit': 's', 'init': 0.0, 'min': -np.inf, 'max': +np.inf, 'type': float}

    def __init__(self, **kwargs):
        if 'length' in kwargs:
            self.length_s = kwargs['length_s']
        if 'increment' in kwargs:
            self.increment_s = kwargs['increment_s']
        return

    @abc.abstractmethod
    def get_samples(self, time_array):
        pass


class Idle(PulseBlockElement):
    """
    Object representing an idle element (zero voltage)
    """

    def __init__(self):
        return

    def get_samples(self, time_array):
        samples_arr = np.zeros(len(time_array))
        return samples_arr


class DC(PulseBlockElement):
    """
    Object representing an DC element (constant voltage)
    """

    def __init__(self, voltage):
        self.params['voltage'] = {'unit': 'V', 'init': 0.0, 'min': -np.inf, 'max': +np.inf, 'type': float}
        self.voltage = voltage
        return

    def get_samples(self, time_array):
        samples_arr = np.zeros(len(time_array)) + self.voltage
        return samples_arr


class Sin(PulseBlockElement):
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

    def get_samples(self, time_array):
        phase_rad = np.pi * self.phase / 180
        amp_conv = 2 * self.amplitude  # conversion for AWG to actually output the specified voltage
        samples_arr = amp_conv * np.sin(2 * np.pi * self.frequency * time_array + phase_rad)
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

    def get_samples(self, time_array):
        # First sine wave
        phase_rad = np.pi * self.phase[0] / 180
        amp_conv = 2 * self.amplitude[0]  # conversion for AWG to actually output the specified voltage
        samples_arr = amp_conv * np.sin(2 * np.pi * self.frequency[0] * time_array + phase_rad)

        # Second sine wave (add on first sine)
        phase_rad = np.pi * self.phase[1] / 180
        amp_conv = 2 * self.amplitude[1]  # conversion for AWG to actually output the specified voltage
        samples_arr += amp_conv * np.sin(2 * np.pi * self.frequency[1] * time_array + phase_rad)
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

    def get_samples(self, time_array):
        # First sine wave
        phase_rad = np.pi * self.phase[0] / 180
        amp_conv = 2 * self.amplitude[0]  # conversion for AWG to actually output the specified voltage
        samples_arr = amp_conv * np.sin(2 * np.pi * self.frequency[0] * time_array + phase_rad)

        # Second sine wave (add on first sine)
        phase_rad = np.pi * self.phase[1] / 180
        amp_conv = 2 * self.amplitude[1]  # conversion for AWG to actually output the specified voltage
        samples_arr += amp_conv * np.sin(2 * np.pi * self.frequency[1] * time_array + phase_rad)

        # Second sine wave (add on sum of first and second)
        phase_rad = np.pi * self.phase[2] / 180
        amp_conv = 2 * self.amplitude[2]  # conversion for AWG to actually output the specified voltage
        samples_arr += amp_conv * np.sin(2 * np.pi * self.frequency[2] * time_array + phase_rad)
        return samples_arr
