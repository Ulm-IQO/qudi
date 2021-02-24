# -*- coding: utf-8 -*-

"""
This file contains helper methods to find and estimate multiple peaks/dips for fit models.

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
from scipy.signal import find_peaks as _find_peaks
from scipy.signal import peak_widths as _peak_widths

__all__ = ('find_highest_peaks', 'estimate_double_peaks', 'estimate_triple_peaks')


def find_highest_peaks(data, peak_count, allow_borders=True, **kwargs):
    """ Find peaks using scipy.signal.find_peaks().
    ToDo: Document
    """
    peak_count = int(peak_count)
    assert peak_count > 0, 'Parameter "peak_count" must be integer >= 1'
    assert len(data) >= 5, 'Data must contain at least 5 data points'

    # Return early if all elements are the same
    if min(data) == max(data):
        return list(), list(), list()

    # Find all peaks
    peaks, properties = _find_peaks(data, **kwargs)
    if len(peaks) == 0:
        # ToDo: warn
        return list(), list(), list()

    # Sort found peaks by increasing peak height
    sorted_args = np.argsort(data[peaks])
    peaks = peaks[sorted_args]

    # Only keep requested number of highest peaks
    peaks = peaks[-peak_count:]
    peak_heights = data[peaks]
    peak_widths = _peak_widths(data, peaks, rel_height=0.5)[0]  # full-width at half-maximum

    # Check if data borders are more promising as peak locations and replace found peaks
    if allow_borders:
        width = max(2, int(round(max(peak_widths))))
        left_mean = np.mean(data[:width])
        right_mean = np.mean(data[-width:])
        if 2 * min(peak_heights) < left_mean and min(peaks) > 2 * width:
            min_arg = np.argmin(peak_heights)
            peaks[min_arg] = np.argmax(data[:width])
            peak_heights[min_arg] = data[peaks[min_arg]]
        if 2 * min(peak_heights) < 2 * right_mean and max(peaks) < len(data) - 1 - 2 * width:
            min_arg = np.argmin(peak_heights)
            peaks[min_arg] = np.argmax(data[-width:])
            peak_heights[min_arg] = data[peaks[min_arg]]
        # Check if some peaks are missing and manually add borders if they look promising
        if len(peaks) < peak_count:
            threshold = max(data) / 2
            no_left_peak = min(peaks) > 2 * width
            no_right_peak = max(peaks) < len(data) - 1 - 2 * width
            if no_left_peak and left_mean > threshold:
                peaks = np.append(peaks, np.argmax(data[:width]))
                peak_heights = np.append(peak_heights, data[peaks[-1]])
                peak_widths = np.append(peak_widths, width)
            if no_right_peak and right_mean > threshold:
                peaks = np.append(peaks, np.argmax(data[-width:]))
                peak_heights = np.append(peak_heights, data[peaks[-1]])
                peak_widths = np.append(peak_widths, width)

    return peaks, peak_heights, peak_widths


def estimate_double_peaks(data, x, minimum_distance=None):
    # Find peaks along with width and amplitude estimation
    peak_indices, peak_heights, peak_widths = find_highest_peaks(data,
                                                                 peak_count=2,
                                                                 width=minimum_distance,
                                                                 height=0.05 * max(data))

    x_spacing = min(abs(np.ediff1d(x)))
    x_span = abs(x[-1] - x[0])
    data_span = abs(max(data) - min(data))

    # Replace missing peaks with sensible default value
    if len(peak_indices) == 1:
        # If just one peak was found, assume it is two peaks overlapping and split it into two
        left_peak_index = max(0, int(round(peak_indices[0] - peak_widths[0] / 2)))
        right_peak_index = min(len(x) - 1, int(round(peak_indices[0] + peak_widths[0] / 2)))
        peak_indices = (left_peak_index, right_peak_index)
        peak_heights = (peak_heights[0] / 2, peak_heights[0] / 2)
        peak_widths = (peak_widths[0] / 2, peak_widths[0] / 2)
    elif len(peak_indices) == 0:
        # If no peaks have been found, just make a wild guess
        peak_indices = (len(x) // 3, 2 * len(x) // 3)
        peak_heights = (data_span, data_span)
        peak_widths = (x_spacing * 10, x_spacing * 10)

    estimate = {'height': np.asarray(peak_heights),
                'fwhm'  : np.asarray(peak_widths) * x_spacing,
                'center': np.asarray(x[np.asarray(peak_indices)])}
    limits = {'height': ((0, 2 * data_span),) * 2,
              'fwhm'  : ((x_spacing, x_span),) * 2,
              'center': ((min(x) - x_span / 2, max(x) + x_span / 2),) * 2}
    return estimate, limits


def estimate_triple_peaks(data, x, minimum_distance=None):
    # Find peaks along with width and amplitude estimation
    peak_indices, peak_heights, peak_widths = find_highest_peaks(data,
                                                                 peak_count=3,
                                                                 width=minimum_distance,
                                                                 height=0.05 * max(data))

    x_spacing = min(abs(np.ediff1d(x)))
    x_span = abs(x[-1] - x[0])
    data_span = abs(max(data) - min(data))

    # Replace missing peaks with sensible default value
    if len(peak_indices) == 2:
        # If just two peaks were found, assume it is three peaks overlapping and put one in the
        # middle
        middle_peak_index = abs(peak_indices[0] - peak_indices[1]) // 2
        middle_peak_width = np.mean(peak_widths)
        middle_peak_height = np.mean(peak_heights)
        peak_indices = (peak_indices[0], middle_peak_index, peak_indices[1])
        peak_heights = (peak_heights[0], middle_peak_height, peak_heights[1])
        peak_widths = (peak_widths[0], middle_peak_width, peak_widths[1])
    elif len(peak_indices) == 1:
        # If just one peak was found, assume it is three peaks overlapping and split it
        left_peak_index = max(0, int(round(peak_indices[0] - peak_widths[0] / 2)))
        right_peak_index = min(len(x) - 1, int(round(peak_indices[0] + peak_widths[0] / 2)))
        peak_indices = (left_peak_index, peak_indices[0], right_peak_index)
        peak_heights = (peak_heights[0] / 2, peak_heights[0] / 2, peak_heights[0] / 2)
        peak_widths = (peak_widths[0] / 2, peak_widths[0] / 2, peak_widths[0] / 2)
    elif len(peak_indices) == 0:
        # If no peaks have been found, just make a wild guess
        peak_indices = (len(x) // 4, len(x) // 2, 3 * len(x) // 4)
        peak_heights = (data_span, data_span, data_span)
        peak_widths = (x_spacing * 10, x_spacing * 10, x_spacing * 10)

    estimate = {'height': np.asarray(peak_heights),
                'fwhm'  : np.asarray(peak_widths) * x_spacing,
                'center': np.asarray(x[np.asarray(peak_indices)])}
    limits = {'height': ((0, 2 * data_span),) * 3,
              'fwhm'  : ((x_spacing, x_span),) * 3,
              'center': ((min(x) - x_span / 2, max(x) + x_span / 2),) * 3}
    return estimate, limits
