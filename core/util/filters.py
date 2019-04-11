# -*- coding: utf-8 -*-
"""
This file contains Qudi methods for data filtering.

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
from scipy.ndimage import minimum_filter1d, maximum_filter1d

import logging
logger = logging.getLogger(__name__)


def scan_blink_correction(image, axis=1):
    """
    This filter can be used to filter out impulsive noise from a 2D array along a single axis.
    As filter we apply a sequence of two filters. First a min-filter and then a max-filter.
    This composite non-linear filter technique is also called opening filter.

    This filter will completely remove single-pixel (along given axis) brightness spikes from the
    image but will cause the image to be more "blocky"/less smooth.
    Of course you need to ensure that the image features of interest are larger than

    @param numpy.ndarray image: A 2D numpy array to be filtered (e.g. image data)
    @param int axis: The axis along which to apply the 1D filter
    @return numpy.ndarray: The filtered image. Same dimensions as input image
    """

    if not isinstance(image, np.ndarray):
        logger.error('Image must be 2D numpy array.')
        return image
    if image.ndim != 2:
        logger.error('Image must be 2D numpy array.')
        return image
    if axis != 0 and axis != 1:
        logger.error('Optional axis parameter must be either 0 or 1.')
        return image

    # Calculate median value of the image. This value is used for padding image boundaries during
    # filtering.
    median = np.median(image)
    # Apply a minimum filter along the chosen axis.
    filt_img = minimum_filter1d(image, size=2, axis=axis, mode='constant', cval=median)
    # Apply a maximum filter along the chosen axis. Flip the previous filter result to avoid
    # translation of image features.
    filt_img = maximum_filter1d(
        np.flip(filt_img, axis), size=2, axis=axis, mode='constant', cval=median)
    # Flip back the image to obtain original orientation and return result.
    return np.flip(filt_img, axis)
