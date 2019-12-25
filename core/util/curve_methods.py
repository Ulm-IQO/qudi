# -*- coding: utf-8 -*-
"""
This file contains Qudi methods for data curve manipulation, either just Y, (X, Y) or (X, [Y1, Y2, ... YN]

---

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


def rebin(y, ratio, do_average=False):
    """ Rebin a 1D array the good old way.

    @param (1d array) y : The Y vector to rebin
    @param (int) ratio: The number of old bin per new bin
    @param (bool) do_average: Optional parameter to take the average instead of the sum in the process

    @return (1d numpy array) : The array rebinned

    This rebbining method does not use any dangerous smoothing method. It just simply adds bin.

    The last values will be dropped if the sizes do not match
    """
    y = np.array(y)
    ratio = int(ratio)
    length = (len(y) // ratio) * ratio
    y = y[0:length]
    y = y.reshape(length//ratio, ratio)
    if do_average:
        return y.mean(axis=1)
    else:
        return y.sum(axis=1)


def decimate(y, ratio):
    """ Decimate a 1D array . This means some value are dropped, not averaged

    @param (1d array) y : The Y vector to decimate
    @param (int) ratio: The number of old value per new value

    @return (1d numpy array) : The array decimated
    """
    y = np.array(y)
    ratio = int(ratio)
    length = (len(y) // ratio) * ratio
    return y[:length:ratio]


def rebin_xy(x, y,  ratio, do_average=True):
    """ Helper method to decimate x and rebin y, with do_average True as default

    @param (1d array) x : The X vector to decimate
    @param (1d array) y : The Y vector to rebin
    @param (int) ratio: The number of old bin per new bin
    @param (bool) do_average: Optional parameter to take the average instead of the sum in the process

    @return (1d numpy array) : The array rebinned

    This rebbining method does not use any dangerous smoothing method. It just simply adds bin.

    do_average is True by default, because this function can be used in notebooks and one generally prefers having
    true as default.

    The last values will be dropped if the sizes do not match
    """
    return decimate(x, ratio), rebin(y, ratio, do_average)


def get_window(x, y, a, b):
    """ Very useful method to get just a window [a, b] of a signal (x,y)

    @param (1d array) x : The X vector to decimate
    @param (1d array) y : The Y vector to rebin
    @param (float) a : Inferior bound
    @param (float) b : Superior bound

    This function removes (xi, yi) points of the (X,Y) curve the xi is out of the [a, b] window.
    X is not assumed to be sorted
    """
    x, y = np.array(x), np.array(y)
    mask_1 = a < x
    mask_2 = x < b
    mask = np.logical_and(mask_1, mask_2)
    x = x[mask]
    y = y[mask]
    return x, y
