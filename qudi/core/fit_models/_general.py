# -*- coding: utf-8 -*-

"""
This file contains base and meta class for data fit model classes for qudi based on the lmfit
package. Also contains an estimator decorator for fit models to name estimator methods.

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

import inspect
import numpy as np
from scipy.signal import find_peaks as _find_peaks
from scipy.signal import peak_widths as _peak_widths
from abc import ABCMeta, abstractmethod
from lmfit import Model, CompositeModel

__all__ = (
    'correct_offset_histogram', 'find_highest_peaks', 'estimator', 'FitCompositeModelBase',
    'FitCompositeModelMeta', 'FitModelBase', 'FitModelMeta'
)


def estimator(name):
    assert isinstance(name, str) and name, 'estimator name must be non-empty str'

    def _decorator(func):
        assert callable(func), 'estimator must be callable'
        params = tuple(inspect.signature(func).parameters)
        assert len(params) == 3, \
            'estimator must be bound method with 2 positional parameters. First parameter is the ' \
            'y data array to use and second parameter is the corresponding independent variable.'
        func._estimator_name = name
        func._estimator_independent_var = params[2]
        return func

    return _decorator


class FitModelMeta(ABCMeta):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

        # collect marked estimator methods in a dict "_estimators" and attach it to created class
        estimators = dict()
        for attr_name in [a for a in dir(cls) if not a.startswith('__')]:
            attr = getattr(cls, attr_name)
            name = getattr(attr, '_estimator_name', None)
            if isinstance(name, str):
                estimators[name] = attr
        cls._estimators = estimators

        # The following is just performed on lmfit.Model subclasses, NOT CompositeModel subclasses
        if not issubclass(cls, CompositeModel):
            # inspect static _model_function and perform sanity checks
            model_func = inspect.getattr_static(cls, '_model_function', None)
            assert isinstance(model_func, staticmethod), '"_model_function" must be staticmethod'
            params = tuple(inspect.signature(cls._model_function).parameters)
            assert len(params) > 0, '"_model_function" must accept at least 1 positional argument' \
                                    ' representing the independent variable'
            indep_var_name = params[0]

            for estimator_name, estimator in estimators.items():
                assert getattr(estimator, '_estimator_independent_var', '') == indep_var_name, \
                    f'estimator "{estimator_name}" second argument must have the same name as the' \
                    f' independent variable of "_model_function"'


class FitCompositeModelMeta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

        # collect marked estimator methods in a dict "_estimators" and attach it to created class.
        # The main difference to FitModelMeta.__init__ is the fact that we just collect estimators
        # in cls.__dict__ here (not from possible base classes)
        cls._estimators = {attr._estimator_name: attr for attr in attrs.values() if
                           hasattr(attr, '_estimator_name')}
        independent_vars = {e._estimator_independent_var for e in cls._estimators.values()}
        assert len(independent_vars) < 2, \
            'More than one independent variable name encountered in estimators. Use only the ' \
            'independent variable name that has been used in the Models "_model_function".'


class FitModelBase(Model, metaclass=FitModelMeta):
    """ ToDo: Document
    """

    def __init__(self, **kwargs):
        kwargs['name'] = self.__class__.__name__
        super().__init__(self._model_function, **kwargs)
        assert len(self.independent_vars) == 1, \
            'Qudi fit models must contain exactly 1 independent variable.'
        # Shadow FitModelBase._estimators with a similar dict containing the bound method objects.
        # This instance-level dict has read-only access via property "estimators"
        self._estimators = {name: getattr(self, e.__name__) for name, e in self._estimators.items()}

    @property
    def estimators(self):
        """ Read-only dict property holding available estimator names as keys and the corresponding
        estimator methods as values.

        @return dict: Available estimator methods (values) with corresponding names (keys)
        """
        return self._estimators.copy()

    @staticmethod
    @abstractmethod
    def _model_function(x):
        """ ToDo: Document
        """
        raise NotImplementedError('FitModel object must implement staticmethod "_model_function".')


class FitCompositeModelBase(CompositeModel, metaclass=FitCompositeModelMeta):
    """ ToDo: Document
    """

    def __init__(self, *args, **kwargs):
        kwargs['name'] = self.__class__.__name__
        super().__init__(*args, **kwargs)
        assert len(self.independent_vars) == 1, \
            'Qudi fit models must contain exactly 1 independent variable.'
        # Shadow FitCompositeModelBase._estimators with a similar dict containing the bound method
        # objects. This instance-level dict has read-only access via property "estimators"
        self._estimators = {name: getattr(self, e.__name__) for name, e in self._estimators.items()}

    @property
    def estimators(self):
        """ Read-only dict property holding available estimator names as keys and the corresponding
        estimator methods as values.

        @return dict: Available estimator methods (values) with corresponding names (keys)
        """
        return self._estimators.copy()


def correct_offset_histogram(data, bin_width=None):
    """ Subtracts a constant offset from a copy of given data array and returns it.
    The offset is assumed to be the most common value in data. This value is determined by creating
    a histogram of <data> with bin width <bin_width> and taking the value with most occurrences.
    If no bin width has been specified, assume bin width of 1/50th of data length (min. 1).

    For best results, make sure to filter noisy data beforehand. The used smoothing filter width
    is a good estimate for optimal bin_width.

    @param iterable data: Peak data to correct offset for. Must be convertible using numpy.asarray.
    @param int bin_width: optional, bin width in samples to use for histogram creation.

    @return numpy.ndarray, float: New array with offset-corrected data, the offset value
    """
    data = np.asarray(data)
    if bin_width is None:
        bin_width = max(1, data.size // 50)
    elif not isinstance(bin_width, int):
        bin_width = max(1, int(round(bin_width)))
    hist = np.histogram(data, bins=bin_width)
    offset = (hist[1][hist[0].argmax()] + hist[1][hist[0].argmax() + 1]) / 2
    return data - offset, offset


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
