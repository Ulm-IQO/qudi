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
from scipy import interpolate

class OC_RedCrab(SamplingBase):
    """
    Object representing an IQ modulated sine wave (I*sin + Q*cos).
    For consistency with old code, quadratures are called 'amplitude' (I) and 'phase' (Q)
    """
    params = OrderedDict()
    params['amplitude_scaling'] = {'unit': '', 'init': 1.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['frequency'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase'] = {'unit': '°', 'init': 0.0, 'min': -np.inf, 'max': np.inf, 'type': float}
    params['filename_amplitude'] = {'unit': '', 'init': 'amplitude_file', 'type': str}
    params['filename_phase'] = {'unit': '', 'init': 'phase_file', 'type': str}
    params['folder_path'] = {'unit': '', 'init': r'C:\Users\Mesoscopic\Desktop\Redcrab_data',
                             'type': str}

    def __init__(self, amplitude_scaling=None, frequency=None, phase=None, filename_amplitude=None,
                 filename_phase=None, folder_path=None):
        if amplitude_scaling is None:
            self.amplitude_scaling = self.params['amplitude_scaling']['init']
        else:
            self.amplitude_scaling = amplitude_scaling
        if frequency is None:
            self.frequency = self.params['frequency']['init']
        else:
            self.frequency = frequency
        if phase is None:
            self.phase = self.params['phase']['init']
        else:
            self.phase = phase
        if filename_amplitude is None:
            self.filename_amplitude = self.params['filename_amplitude']['init']
        else:
            self.filename_amplitude = filename_amplitude
        if filename_phase is None:
            self.filename_phase = self.params['filename_phase']['init']
        else:
            self.filename_phase = filename_phase
        if folder_path is None:
            self.folder_path = self.params['folder_path']['init']
        else:
            self.folder_path = folder_path
        return

    @staticmethod
    # waveform if the data matches the sampling rate
    def _get_sine(time_array, amplitude_opt, frequency, phase_rad, phase_opt):
        samples_arr = amplitude_opt * np.sin(2 * np.pi * frequency * time_array + phase_rad + phase_opt)
        return samples_arr

    # waveform if the data is interpolated
    # def _get_sine_func(self, time_array, amplitude_func, frequency, phase_rad, phase_func):
    #     samples_arr = amplitude_func(time_array - time_array[0]) * np.sin(2 * np.pi * frequency * time_array
    #                                                                       + phase_rad + phase_func(time_array
    #                                                                                                - time_array[0]))
    #     return samples_arr

    def _get_sine_func(self, time_array, amplitude_func, frequency, phase_rad, phase_func):
        samples_arr = amplitude_func(time_array - time_array[0]) * np.sin(2*np.pi * frequency * time_array + phase_rad) \
                      + phase_func(time_array - time_array[0]) * np.cos(2*np.pi * frequency * time_array + phase_rad)

        return samples_arr

    # generate the samples for the awg
    def get_samples(self, time_array):

        # make sure the time_array starts at 0: for interpolation
        # time_array = time_array - time_array[0]

        # convert the phase to rad
        phase_rad = np.pi * self.phase / 180

        # get the full file path to load the file
        file_path_amplitude = self.folder_path + r'/' + self.filename_amplitude
        file_path_phase = self.folder_path + r'/' + self.filename_phase

        # try to load the file
        try:
            timegrid, amplitude_opt = np.loadtxt(file_path_amplitude, usecols=(0, 1), unpack=True)
            timegrid, phase_opt = np.loadtxt(file_path_phase, usecols=(0, 1), unpack=True)

            self.log.debug(f"Loading oc to samplnig func from: {file_path_amplitude}")
        except IOError:
            timegrid = [0, 1]
            amplitude_opt = [0, 0]
            phase_opt = [0, 0]
            self.log.error('The pulse file does not exist! '
                           '\nDefault parameters loaded')

        #self.log.warning('Time grid does not match the sampling rate of the AWG! '
                         #'\nInterpolating the recieved data!')

        amplitude_func = interpolate.interp1d(timegrid, amplitude_opt)
        phase_func = interpolate.interp1d(timegrid, phase_opt)

        # calculate the samples
        samples_arr = self._get_sine_func(time_array, amplitude_func, self.frequency, phase_rad, phase_func)

        # change the amplitude of the pulse (e.g. to simulate amplitude detuning)
        samples_arr = self.amplitude_scaling * samples_arr

        # avoid re-scaling by the pg, todo: think of better way
        import scipy
        if max(abs(samples_arr)) > 0.25:
            biggest_val = max([abs(np.min(samples_arr)), np.max(samples_arr)])
            self.log.warning(
                f"Resampling in OC sampling function, because ampl value {biggest_val} exceeds limit")
            mapper = scipy.interpolate.interp1d([-biggest_val, biggest_val], [-0.25, 0.25])
            samples_arr = mapper(samples_arr)

        return samples_arr