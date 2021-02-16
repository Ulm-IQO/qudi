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

import numpy as np
from scipy.ndimage import filters
from scipy.signal.windows import gaussian
from lmfit import Model


class estimator:
    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        # ToDo: Sanity checking for appropriate estimator method. Keep in mind other decorators
        #  (i.e. staticmethod, classmethod etc.)
        #  Do not flag function if it is an invalid estimator.
        func.estimator_name = self.name
        return func


class FitModelMeta(type):
    def __init__(cls, name, bases, attrs):
        estimators = dict()
        for name, method in attrs.items():
            if hasattr(method, 'estimator_name'):
                estimators[method.estimator_name] = name

        @property
        def _estimators(self):
            names = estimators.copy()
            try:
                names.update(super(cls, self)._estimators)
            except AttributeError:
                pass
            return names

        cls._estimators = _estimators


class FitModelBase(Model, metaclass=FitModelMeta):
    """
    """

    def __init__(self, **kwargs):
        kwargs.pop('name', None)
        super().__init__(self._model_function, name=self.__class__.__name__, **kwargs)

    @property
    def estimators(self):
        return {name: getattr(self, attr) for name, attr in self._estimators.items()}


def _search_end_of_dip(direction, data, peak_arg, start_arg, end_arg, sigma_threshold, minimal_threshold):
    """ Data has to be offset leveled such that offset is subtracted
    """
    absolute_min = data[peak_arg]

    if direction == 'left':
        mult = -1
        sigma_arg = start_arg
    elif direction == 'right':
        mult = +1
        sigma_arg = end_arg
    else:
        raise ValueError('No valid direction in search end of dip')

    ii = 0
    # if the minimum is at the end set this as border
    if peak_arg != start_arg and direction == 'left' or peak_arg != end_arg and direction == 'right':
        while True:
            # if no minimum can be found decrease threshold
            if (peak_arg-ii<start_arg and direction == 'left') or (peak_arg+ii>end_arg and direction=='right'):
                sigma_threshold *= 0.9
                ii=0

            #if the dip is always over threshold the end is as
            # set before
            if abs(sigma_threshold/absolute_min)<abs(minimal_threshold):
                break

             #check if value was changed and search is finished
            if ((sigma_arg == start_arg and direction == 'left') or
                (sigma_arg == end_arg   and direction=='right')):
                # check if if value is lower as threshold this is the
                # searched value
                if abs(data[peak_arg+(mult*ii)])<abs(sigma_threshold):
                    # value lower than threshold found - left end found
                    sigma_arg=peak_arg+(mult*ii)
                    break
            ii+=1

    # in this case the value is the last index and should be search set as right argument
    else:
        sigma_arg=peak_arg

    return sigma_threshold, sigma_arg


def _search_double_dip(x_axis, data, threshold_fraction=0.3, minimal_threshold=0.01,
                       sigma_threshold_fraction=0.3):
    """ This method searches for a double dip. There are three values which can be set in order to
    adjust the search. A threshold which defines when a minimum is a dip, this threshold is then
    lowered if no dip can be found until the minimal threshold which sets the absolute border and a
    sigma_threshold_fraction which defines when the

    @param array x_axis: x values
    @param array data: value of each data point corresponding to x values
    @param float threshold_fraction: x values
    @param float minimal_threshold: x values
    @param float sigma_threshold_fraction: x values
    @return int error: error code (0:OK, -1:error)
    @return int sigma0_argleft: index of left side of 1st peak
    @return int dip0_arg: index of max of 1st peak
    @return int sigma0_argright: index of right side of 1st peak
    @return int sigma1_argleft: index of left side of 2nd peak
    @return int dip1_arg: index of max side of 2nd peak
    @return int sigma1_argright: index of right side of 2nd peak
    """
    if sigma_threshold_fraction is None:
        sigma_threshold_fraction = threshold_fraction

    error = 0

    # first search for absolute minimum
    absolute_min = np.min(data)
    absolute_argmin = np.argmin(data)

    # adjust thresholds
    threshold = threshold_fraction*absolute_min
    sigma_threshold=sigma_threshold_fraction*absolute_min

    dip0_arg = absolute_argmin

    # ====== search for the left end of the dip ======

    sigma_threshold, sigma0_argleft = _search_end_of_dip(
                             direction='left',
                             data=data,
                             peak_arg = absolute_argmin,
                             start_arg = 0,
                             end_arg = len(data)-1,
                             sigma_threshold = sigma_threshold,
                             minimal_threshold = minimal_threshold)

    # ====== search for the right end of the dip ======
    # reset sigma_threshold
    sigma_threshold, sigma0_argright = _search_end_of_dip(
                             direction='right',
                             data=data,
                             peak_arg = absolute_argmin,
                             start_arg = 0,
                             end_arg = len(data)-1,
                             sigma_threshold = sigma_threshold_fraction*absolute_min,
                             minimal_threshold = minimal_threshold)

    # ======== search for second lorentzian dip ========
    left_index=int(0)
    right_index=len(x_axis)-1

    mid_index_left=sigma0_argleft
    mid_index_right=sigma0_argright

    # if main first dip covers the whole left side search on the right
    # side only
    if mid_index_left==left_index:
        # if one dip is within the second they have to be set to one
        if mid_index_right==right_index:
            dip1_arg=dip0_arg
        else:
            dip1_arg=data[mid_index_right:right_index].argmin()+mid_index_right

    # if main first dip covers the whole right side search on the left side only
    elif mid_index_right==right_index:
        #if one dip is within the second they have to be set to one
        if mid_index_left==left_index:
            dip1_arg=dip0_arg
        else:
            dip1_arg=data[left_index:mid_index_left].argmin()

    # search for peak left and right of the dip
    else:
        while True:
            # set search area excluding the first dip
            left_min=data[left_index:mid_index_left].min()
            left_argmin=data[left_index:mid_index_left].argmin()
            right_min=data[mid_index_right:right_index].min()
            right_argmin=data[mid_index_right:right_index].argmin()

            if abs(left_min) > abs(threshold) and \
               abs(left_min) > abs(right_min):
                # there is a minimum on the left side which is higher
                # than the minimum on the right side
                dip1_arg = left_argmin+left_index
                break
            elif abs(right_min)>abs(threshold):
                # there is a minimum on the right side which is higher
                # than on left side
                dip1_arg=right_argmin+mid_index_right
                break
            else:
                # no minimum at all over threshold so lowering threshold
                #  and resetting search area
                threshold*=0.9
                left_index=int(0)
                right_index=len(x_axis)-1
                mid_index_left=sigma0_argleft
                mid_index_right=sigma0_argright
                # if no second dip can be found set both to same value
                if abs(threshold/absolute_min)<abs(minimal_threshold):
                    # self.log.warning('Threshold to minimum ratio was too '
                    #         'small to estimate two minima. So both '
                    #         'are set to the same value')
                    error=-1
                    dip1_arg=dip0_arg
                    break

    # if the dip is exactly at one of the boarders that means
    # the dips are most probably overlapping
    if dip1_arg in (sigma0_argleft, sigma0_argright):
        distance_left  = abs(dip0_arg - sigma0_argleft)
        distance_right = abs(dip0_arg - sigma0_argright)
        sigma1_argleft = sigma0_argleft
        sigma1_argright = sigma0_argright
        if distance_left > distance_right:
            dip1_arg = dip0_arg - abs(distance_left-distance_right)
        elif distance_left < distance_right:
            dip1_arg = dip0_arg + abs(distance_left-distance_right)
        else:
            dip1_arg = dip0_arg
    else:
        # if the peaks are not overlapping search for left and right
        # boarder of the dip

        # ====== search for the right end of the dip ======
        sigma_threshold, sigma1_argleft = _search_end_of_dip(
                                 direction='left',
                                 data=data,
                                 peak_arg = dip1_arg,
                                 start_arg = 0,
                                 end_arg = len(data)-1,
                                 sigma_threshold = sigma_threshold_fraction*absolute_min,
                                 minimal_threshold = minimal_threshold)

        # ====== search for the right end of the dip ======
        sigma_threshold, sigma1_argright = _search_end_of_dip(
                                 direction='right',
                                 data=data,
                                 peak_arg = dip1_arg,
                                 start_arg = 0,
                                 end_arg = len(data)-1,
                                 sigma_threshold = sigma_threshold_fraction*absolute_min,
                                 minimal_threshold = minimal_threshold)

    return error, sigma0_argleft, dip0_arg, sigma0_argright, sigma1_argleft, dip1_arg, sigma1_argright


def find_offset_parameter(x_values=None, data=None):
    """ This method convolves the data with a Lorentzian and the finds the offset which is supposed
    to be the most likely valy via a histogram. Additional the smoothed data is returned.

    @param array x_values: x values
    @param array data: value of each data point corresponding to
                        x values
    @return int error: error code (0:OK, -1:error)
    @return float array data_smooth: smoothed data
    @return float offset: estimated offset
    """
    if len(x_values) < 20.:
        len_x = 5
    elif len(x_values) >= 100.:
        len_x = 10
    else:
        len_x = int(len(x_values)/10.)+1

    lorentz = (len_x/4) ** 2 / ((np.linspace(0, len_x, len_x) - len_x/2) ** 2 + (len_x/4) ** 2)
    data_smooth = filters.convolve1d(data, lorentz/lorentz.sum(), mode='constant', cval=max(data))

    # finding most frequent value which is supposed to be the offset
    hist = np.histogram(data_smooth, bins=10)
    offset = (hist[1][hist[0].argmax()]+hist[1][hist[0].argmax()+1])/2.

    return data_smooth, offset
