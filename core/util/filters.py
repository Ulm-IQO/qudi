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
    if not isinstance(image, np.ndarray):
        logger.error('Image must be 2D numpy array.')
        return image
    if image.ndim != 2:
        logger.error('Image must be 2D numpy array.')
        return image
    if axis != 0 and axis != 1:
        logger.error('Optional axis parameter must be either 0 or 1.')
        return image

    median = np.median(image)
    filt_img = minimum_filter1d(image, size=2, axis=axis, mode='constant', cval=median)
    filt_img = maximum_filter1d(
        np.flip(filt_img, axis), size=2, axis=axis, mode='constant', cval=median)
    return np.flip(filt_img, axis)
