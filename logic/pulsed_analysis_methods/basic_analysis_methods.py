import numpy as np


def analyse_mean_norm(self, laser_data):
    """

    @param laser_data:
    @return:
    """
    num_of_lasers = laser_data.shape[0]

    # Initialize the signal and normalization mean data arrays
    reference_mean = np.zeros(num_of_lasers, dtype=float)
    signal_mean = np.zeros(num_of_lasers, dtype=float)
    signal_area = np.zeros(num_of_lasers, dtype=float)
    reference_area = np.zeros(num_of_lasers, dtype=float)
    measuring_error = np.zeros(num_of_lasers, dtype=float)
    # initialize data arrays
    signal_data = np.empty(num_of_lasers, dtype=float)

    # loop over all laser pulses and analyze them
    for ii in range(num_of_lasers):
        # calculate the mean of the data in the normalization window
        norm_tmp_data = laser_data[ii][self.norm_start_bin:self.norm_end_bin]
        if np.sum(norm_tmp_data) < 1:
            reference_mean[ii] = 0.0
        else:
            reference_mean[ii] = norm_tmp_data.mean()
        # calculate the mean of the data in the signal window
        signal_tmp_data = laser_data[ii][self.signal_start_bin:self.signal_end_bin]
        if np.sum(signal_tmp_data) < 1:
            signal_mean[ii] = 0.0
        else:
            signal_mean[ii] = signal_tmp_data.mean() - reference_mean[ii]
        # update the signal plot y-data
        if reference_mean[ii] == 0.0:
            signal_data[ii] = 0.0
        else:
            signal_data[ii] = 1. + (signal_mean[ii] / reference_mean[ii])

    # Compute the measuring error
    for jj in range(num_of_lasers):
        signal_area[jj] = laser_data[jj][self.signal_start_bin:self.signal_end_bin].sum()
        reference_area[jj] = laser_data[jj][self.norm_start_bin:self.norm_end_bin].sum()
        if reference_area[jj] == 0.:
            measuring_error[jj] = 0.
        elif signal_area[jj] == 0.:
            measuring_error[jj] = 0.
        else:
            # with respect to gaußian error 'evolution'
            measuring_error[jj] = signal_data[jj] * np.sqrt(
                1 / signal_area[jj] + 1 / reference_area[jj])
    return signal_data, measuring_error


def analyse_mean(self, laser_data):
    """

    @param laser_data:
    @return:
    """
    num_of_lasers = laser_data.shape[0]

    # Initialize the signal and normalization mean data arrays
    signal_mean = np.zeros(num_of_lasers, dtype=float)
    measuring_error = np.zeros(num_of_lasers, dtype=float)

    # loop over all laser pulses and analyze them
    for ii in range(num_of_lasers):
        # calculate the mean of the data in the signal window
        signal_tmp_data = laser_data[ii][self.signal_start_bin:self.signal_end_bin]
        if np.sum(signal_tmp_data) < 1:
            signal_mean[ii] = 0.0
            measuring_error[ii] = 0.
        else:
            signal_mean[ii] = signal_tmp_data.mean()
            measuring_error[ii] = np.sqrt(signal_tmp_data.sum())/(self.signal_end_bin-self.signal_start_bin)

    return signal_mean, measuring_error