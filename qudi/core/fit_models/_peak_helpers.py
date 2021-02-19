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

import copy
import numpy as np
from scipy.signal import find_peaks as _find_peaks
from scipy.signal import peak_widths as _peak_widths
from scipy.ndimage.filters import gaussian_filter1d as _gaussian_filter
from ._general import correct_offset_histogram

__all__ = (
    'find_highest_peaks', 'estimate_double_peaks', 'estimate_double_dips', 'estimate_triple_peaks',
    'estimate_triple_dips'
)


def find_highest_peaks(data, peak_count, **kwargs):
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


def estimate_double_peaks(default_params, data, x):
    # check if input x-axis is ordered and increasing
    if not np.all(val > 0 for val in np.ediff1d(x)):
        x = x[np.argsort(x)]
        data = data[np.argsort(x)]

    # Smooth data
    filter_width = max(1, int(round(len(x) / 100)))
    data_smoothed = _gaussian_filter(data, sigma=filter_width)

    # determine offset from histogram
    data_smoothed, offset = correct_offset_histogram(data_smoothed, bin_width=filter_width)

    # Find peaks along with width and amplitude estimation
    peak_indices, peak_heights, peak_widths = find_highest_peaks(
        data_smoothed,
        peak_count=2,
        width=filter_width,
        height=0.05 * max(data_smoothed)
    )

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

    estimate = copy.deepcopy(default_params)
    estimate['amplitude_1'].set(value=peak_heights[0], min=0, max=2 * data_span)
    estimate['amplitude_2'].set(value=peak_heights[1], min=0, max=2 * data_span)
    estimate['sigma_1'].set(value=peak_widths[0] * x_spacing / 2.3548,
                            min=x_spacing,
                            max=x_span)
    estimate['sigma_2'].set(value=peak_widths[1] * x_spacing / 2.3548,
                            min=x_spacing,
                            max=x_span)
    estimate['center_1'].set(value=x[peak_indices[0]],
                             min=min(x) - x_span / 2,
                             max=max(x) + x_span / 2)
    estimate['center_2'].set(value=x[peak_indices[1]],
                             min=min(x) - x_span / 2,
                             max=max(x) + x_span / 2)
    estimate['offset'].set(value=offset,
                           min=min(data) - data_span / 2,
                           max=max(data) + data_span / 2)
    return estimate


def estimate_double_dips(default_params, data, x):
    estimate = estimate_double_peaks(default_params, -data, x)
    estimate['offset'].set(value=-estimate['offset'].value,
                           min=-estimate['offset'].max,
                           max=-estimate['offset'].min)
    estimate['amplitude_1'].set(value=-estimate['amplitude_1'].value,
                                min=-estimate['amplitude_1'].max,
                                max=-estimate['amplitude_1'].min)
    estimate['amplitude_2'].set(value=-estimate['amplitude_2'].value,
                                min=-estimate['amplitude_2'].max,
                                max=-estimate['amplitude_2'].min)
    return estimate


def estimate_triple_peaks(default_params, data, x):
    # check if input x-axis is ordered and increasing
    if not np.all(val > 0 for val in np.ediff1d(x)):
        x = x[np.argsort(x)]
        data = data[np.argsort(x)]

    # Smooth data
    filter_width = max(1, int(round(len(x) / 100)))
    data_smoothed = _gaussian_filter(data, sigma=filter_width)

    # determine offset from histogram
    data_smoothed, offset = correct_offset_histogram(data_smoothed, bin_width=filter_width)

    # Find peaks along with width and amplitude estimation
    peak_indices, peak_heights, peak_widths = find_highest_peaks(
        data_smoothed,
        peak_count=3,
        width=filter_width,
        height=0.05 * max(data_smoothed)
    )

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

    estimate = copy.deepcopy(default_params)
    estimate['amplitude_1'].set(value=peak_heights[0], min=0, max=2 * data_span)
    estimate['amplitude_2'].set(value=peak_heights[1], min=0, max=2 * data_span)
    estimate['amplitude_3'].set(value=peak_heights[2], min=0, max=2 * data_span)
    estimate['sigma_1'].set(value=peak_widths[0] * x_spacing / 2.3548,
                            min=x_spacing,
                            max=x_span)
    estimate['sigma_2'].set(value=peak_widths[1] * x_spacing / 2.3548,
                            min=x_spacing,
                            max=x_span)
    estimate['sigma_3'].set(value=peak_widths[2] * x_spacing / 2.3548,
                            min=x_spacing,
                            max=x_span)
    estimate['center_1'].set(value=x[peak_indices[0]],
                             min=min(x) - x_span / 2,
                             max=max(x) + x_span / 2)
    estimate['center_2'].set(value=x[peak_indices[1]],
                             min=min(x) - x_span / 2,
                             max=max(x) + x_span / 2)
    estimate['center_3'].set(value=x[peak_indices[2]],
                             min=min(x) - x_span / 2,
                             max=max(x) + x_span / 2)
    estimate['offset'].set(value=offset,
                           min=min(data) - data_span / 2,
                           max=max(data) + data_span / 2)
    return estimate


def estimate_triple_dips(default_params, data, x):
    estimate = estimate_triple_peaks(default_params, -data, x)
    estimate['offset'].set(value=-estimate['offset'].value,
                           min=-estimate['offset'].max,
                           max=-estimate['offset'].min)
    estimate['amplitude_1'].set(value=-estimate['amplitude_1'].value,
                                min=-estimate['amplitude_1'].max,
                                max=-estimate['amplitude_1'].min)
    estimate['amplitude_2'].set(value=-estimate['amplitude_2'].value,
                                min=-estimate['amplitude_2'].max,
                                max=-estimate['amplitude_2'].min)
    estimate['amplitude_3'].set(value=-estimate['amplitude_3'].value,
                                min=-estimate['amplitude_3'].max,
                                max=-estimate['amplitude_3'].min)
    return estimate
