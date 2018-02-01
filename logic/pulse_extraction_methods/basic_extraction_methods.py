import numpy as np
from scipy import ndimage


def gated_conv_deriv(self, count_data):
    """
    Detects the rising flank in the gated timetrace data and extracts just the laser pulses.

    @param numpy.ndarray count_data:    2D array, the raw timetrace data from a gated fast counter,
                                        dimensions: 0: gate number, 1: time bin

    @return dict:   The extracted laser pulses of the timetrace as well as the indices for rising
                    and falling flanks.
    """
    if 'conv_std_dev' not in self.extraction_settings:
        self.log.error('Pulse extraction method "gated_conv_dev" will not work. No conv_std_dev '
                       'defined in class PulseExtractionLogic.')
        return np.ndarray([], dtype=int)
    # sum up all gated timetraces to ease flank detection
    timetrace_sum = np.sum(count_data, 0)

    # apply gaussian filter to remove noise and compute the gradient of the timetrace sum
    conv_deriv = self._convolve_derive(timetrace_sum.astype(float), self.extraction_settings['conv_std_dev'])

    # get indices of rising and falling flank
    rising_ind = conv_deriv.argmax()
    falling_ind = conv_deriv.argmin()

    # If gaussian smoothing or derivative failed, the returned array only
    # contains zeros. Check for that and return also only zeros to indicate a
    # failed pulse extraction.
    if len(conv_deriv.nonzero()[0]) == 0:
        laser_arr = np.zeros(count_data.shape, dtype=int)
    else:
        # slice the data array to cut off anything but laser pulses
        laser_arr = count_data[:, rising_ind:falling_ind]

    # Create return dictionary
    return_dict = dict()

    return_dict['laser_counts_arr'] = laser_arr.astype(int)
    return_dict['laser_indices_rising'] = rising_ind
    return_dict['laser_indices_falling'] = falling_ind

    return return_dict


def ungated_conv_deriv(self, count_data):
    """ Detects the laser pulses in the ungated timetrace data and extracts
        them.

    @param numpy.ndarray count_data:    1D array the raw timetrace data from an ungated fast counter

    @return 2D numpy.ndarray:   2D array, the extracted laser pulses of the timetrace.
                                dimensions: 0: laser number, 1: time bin

    Procedure:
        Edge Detection:
        ---------------

        The count_data array with the laser pulses is smoothed with a
        gaussian filter (convolution), which used a defined standard
        deviation of 10 entries (bins). Then the derivation of the convolved
        time trace is taken to obtain the maxima and minima, which
        corresponds to the rising and falling edge of the pulses.

        The convolution with a gaussian removes nasty peaks due to count
        fluctuation within a laser pulse and at the same time ensures a
        clear distinction of the maxima and minima in the derived convolved
        trace.

        The maxima and minima are not found sequentially, pulse by pulse,
        but are rather globally obtained. I.e. the convolved and derived
        array is searched iteratively for a maximum and a minimum, and after
        finding those the array entries within the 4 times
        self.conv_std_dev (2*self.conv_std_dev to the left and
        2*self.conv_std_dev) are set to zero.

        The crucial part is the knowledge of the number of laser pulses and
        the choice of the appropriate std_dev for the gauss filter.

        To ensure a good performance of the edge detection, you have to
        ensure a steep rising and falling edge of the laser pulse! Be also
        careful in choosing a large conv_std_dev value and using a small
        laser pulse (rule of thumb: conv_std_dev < laser_length/10).
    """
    if 'conv_std_dev' not in self.extraction_settings:
        self.log.error('Pulse extraction method "ungated_conv_dev" will not work. No conv_std_dev '
                       'defined in class PulseExtractionLogic.')
        return np.ndarray([], dtype=int)
    if self.number_of_lasers is None:
        self.log.error('Pulse extraction method "ungated_conv_dev" will not work. No '
                       'number_of_lasers defined in class PulseExtractionLogic.')
        return np.ndarray([], dtype=int)
    # apply gaussian filter to remove noise and compute the gradient of the timetrace
    conv_deriv = self._convolve_derive(count_data.astype(float), self.extraction_settings['conv_std_dev'])

    # if gaussian smoothing or derivative failed, the returned array only contains zeros.
    # Check for that and return also only zeros to indicate a failed pulse extraction.
    if len(conv_deriv.nonzero()[0]) == 0:
        laser_arr = np.zeros([self.number_of_lasers, 10], dtype=int)
        return laser_arr

    # use a reference for array, because the exact position of the peaks or dips
    # (i.e. maxima or minima, which are the inflection points in the pulse) are distorted by
    # a large conv_std_dev value.
    conv_deriv_ref = self._convolve_derive(count_data, 10)

    # initialize arrays to contain indices for all rising and falling
    # flanks, respectively
    rising_ind = np.empty([self.number_of_lasers], int)
    falling_ind = np.empty([self.number_of_lasers], int)

    # Find as many rising and falling flanks as there are laser pulses in
    # the trace:
    for i in range(self.number_of_lasers):
        # save the index of the absolute maximum of the derived time trace
        # as rising edge position
        rising_ind[i] = np.argmax(conv_deriv)

        # refine the rising edge detection, by using a small and fixed
        # conv_std_dev parameter to find the inflection point more precise
        start_ind = int(rising_ind[i] - self.extraction_settings['conv_std_dev'])
        if start_ind < 0:
            start_ind = 0

        stop_ind = int(rising_ind[i] + self.extraction_settings['conv_std_dev'])
        if stop_ind > len(conv_deriv):
            stop_ind = len(conv_deriv)

        if start_ind == stop_ind:
            stop_ind = start_ind+1

        rising_ind[i] = start_ind + np.argmax(conv_deriv_ref[start_ind:stop_ind])

        # set this position and the surrounding of the saved edge to 0 to
        # avoid a second detection
        if rising_ind[i] < 2 * self.extraction_settings['conv_std_dev']:
            del_ind_start = 0
        else:
            del_ind_start = rising_ind[i] - int(2 * self.extraction_settings['conv_std_dev'])
        if (conv_deriv.size - rising_ind[i]) < 2 * self.extraction_settings['conv_std_dev']:
            del_ind_stop = conv_deriv.size - 1
        else:
            del_ind_stop = rising_ind[i] + int(2 * self.extraction_settings['conv_std_dev'])
            conv_deriv[del_ind_start:del_ind_stop] = 0

        # save the index of the absolute minimum of the derived time trace
        # as falling edge position
        falling_ind[i] = np.argmin(conv_deriv)

        # refine the falling edge detection, by using a small and fixed
        # conv_std_dev parameter to find the inflection point more precise
        start_ind = int(falling_ind[i] - self.extraction_settings['conv_std_dev'])
        if start_ind < 0:
            start_ind = 0

        stop_ind = int(falling_ind[i] + self.extraction_settings['conv_std_dev'])
        if stop_ind > len(conv_deriv):
            stop_ind = len(conv_deriv)

        if start_ind == stop_ind:
            stop_ind = start_ind+1

        falling_ind[i] = start_ind + np.argmin(conv_deriv_ref[start_ind:stop_ind])

        # set this position and the sourrounding of the saved flank to 0 to
        #  avoid a second detection
        if falling_ind[i] < 2 * self.extraction_settings['conv_std_dev']:
            del_ind_start = 0
        else:
            del_ind_start = falling_ind[i] - int(2 * self.extraction_settings['conv_std_dev'])
        if (conv_deriv.size - falling_ind[i]) < 2 * self.extraction_settings['conv_std_dev']:
            del_ind_stop = conv_deriv.size-1
        else:
            del_ind_stop = falling_ind[i] + int(2 * self.extraction_settings['conv_std_dev'])
        conv_deriv[del_ind_start:del_ind_stop] = 0

    # sort all indices of rising and falling flanks
    rising_ind.sort()
    falling_ind.sort()

    # find the maximum laser length to use as size for the laser array
    laser_length = np.max(falling_ind-rising_ind)

    #Todo: Find better method, here the idea is to take a histogram to find
    # length of pulses
    #diff = (falling_ind-rising_ind)[np.where( falling_ind-rising_ind > 0)]
    #self.histo = np.histogram(diff)
    #laser_length = int(self.histo[1][self.histo[0].argmax()])

    # initialize the empty output array
    laser_arr = np.zeros([self.number_of_lasers, laser_length], dtype=int)
    # slice the detected laser pulses of the timetrace and save them in the
    # output array according to the found rising edge
    for i in range(self.number_of_lasers):
        if (rising_ind[i] + laser_length > count_data.size):
            lenarr = count_data[rising_ind[i]:].size
            laser_arr[i, 0:lenarr] = count_data[rising_ind[i]:]
        else:
            laser_arr[i] = count_data[rising_ind[i]:rising_ind[i] + laser_length]

    # Create return dictionary
    return_dict = dict()
    return_dict['laser_counts_arr'] = laser_arr.astype(int)
    return_dict['laser_indices_rising'] = rising_ind
    return_dict['laser_indices_falling'] = falling_ind
    return return_dict


def ungated_threshold(self, count_data):
    """
    Detects the laser pulses in the ungated timetrace data and extracts them.

    @param numpy.ndarray count_data:    1D array the raw timetrace data from an ungated fast counter

    @return 2D numpy.ndarray:   2D array, the extracted laser pulses of the timetrace.
                                dimensions: 0: laser number, 1: time bin

    Procedure:
        Threshold detection:
        ---------------

        All count data from the time trace is compared to a threshold value.
        Values above the threshold are considered to belong to a laser pulse.
        If the length of a pulse would be below the minimum length the pulse is discarded
        If a number of bins smaller as threshold_tolerance_bins are below the threshold they are still considered to
        belong to a laser pulse
    """
    return_dict = dict()

    if self.number_of_lasers is None:
        self.log.error('Pulse extraction method "ungated_threshold" will not work. No '
                       'number_of_lasers defined in class PulseExtractionLogic.')
        return_dict['laser_indices_rising'] = np.zeros(1, dtype=int)
        return_dict['laser_indices_falling'] = np.zeros(1, dtype=int)
        return_dict['laser_counts_arr'] = np.zeros([1, 3000], dtype=int)
        return return_dict
    else:
        return_dict['laser_indices_rising'] = np.zeros(self.number_of_lasers, dtype=int)
        return_dict['laser_indices_falling'] = np.zeros(self.number_of_lasers, dtype=int)
        return_dict['laser_counts_arr'] = np.zeros([self.number_of_lasers, 3000], dtype=int)

    if 'min_laser_length' not in self.extraction_settings:
        self.log.error('Pulse extraction method "ungated_threshold" will not work. No '
                       'min_laser_length defined in class PulseExtractionLogic.')
        return return_dict
    if 'count_threshold' not in self.extraction_settings:
        self.log.error('Pulse extraction method "ungated_threshold" will not work. No '
                       'count_threshold defined in class PulseExtractionLogic.')
        return return_dict
    if 'threshold_tolerance_bins' not in self.extraction_settings:
        self.log.error('Pulse extraction method "ungated_threshold" will not work. No '
                       'threshold_tolerance_bins defined in class PulseExtractionLogic.')
        return return_dict

    # get all bin indices with counts > threshold value
    bigger_indices = np.where(count_data >= self.extraction_settings['count_threshold'])[0]
    # get all indices with consecutive numbering (bin chains not interrupted by values < threshold
    consecutive_indices_unfiltered = \
        self._find_consecutive_tolerance(np.array(bigger_indices), self.extraction_settings['threshold_tolerance_bins'])
    # sort out all groups shorter than minimum laser length
    consecutive_indices = [item for item in consecutive_indices_unfiltered if len(item) > self.extraction_settings['min_laser_length']]

    # Check if the number of lasers matches the number of remaining index groups
    if self.number_of_lasers != len(consecutive_indices):
        self.log.warning('Pulse extraction method "ungated_threshold" failed. Found number of laser'
                         ' pulses {0:d} does not match the required number of {1:d}'
                         ''.format(len(consecutive_indices), self.number_of_lasers))
        return return_dict

    # determine max length of laser pulse and initialize laser array
    max_laser_length = max([index_array.size for index_array in consecutive_indices])
    return_dict['laser_counts_arr'] = np.zeros([self.number_of_lasers, max_laser_length], dtype=int)
    # fill laser array with slices of raw data array. Also populate the rising/falling index arrays
    for i, index_group in enumerate(consecutive_indices):
        return_dict['laser_indices_rising'][i] = index_group[0]
        return_dict['laser_indices_falling'][i] = index_group[-1]
        return_dict['laser_counts_arr'][i, :index_group.size] = count_data[index_group]

    return return_dict


def _convolve_derive(self, data, std_dev):
    """ Smooth the input data by applying a gaussian filter.

    @param numpy.ndarray data: 1D array, the raw data to be smoothed
                                    and derived
    @param float std_dev: standard deviation of the gaussian filter to be
                          applied for smoothing

    @return numpy.ndarray: 1D array, the smoothed and derived data

    The convolution is applied with specified standard deviation. The
    derivative of the smoothed data is computed afterwards and returned. If
    the input data is some kind of rectangular signal containing high
    frequency noise, the output data will show sharp peaks corresponding to
    the rising and falling flanks of the input signal.
    """
    try:
        conv = ndimage.filters.gaussian_filter1d(data, std_dev)
    except:
        self.log.debug('Convolution of fast counter timetrace failed.\n'
                       'Probably NaN encountered in data array.')
        conv = np.zeros(data.size)
    try:
        conv_deriv = np.gradient(conv)
    except:
        self.log.debug('Derivative of convolution of fast counter timetrace failed.\n'
                       'Probably NaN encountered in data array.')
        conv_deriv = np.zeros(conv.size)
    return conv_deriv


def _find_consecutive(self, data):
    return np.split(data, np.where(np.diff(data) != 1)[0]+1)


def _find_consecutive_tolerance(self, data, tolerance):
    index_list = np.split(data, np.where(np.diff(data) >= tolerance)[0]+1)
    for i, index_group in enumerate(index_list):
        if index_group.size > 0:
            start, end = index_list[i][0], index_list[i][-1]
            index_list[i] = np.arange(start, end + 1)
    return index_list
