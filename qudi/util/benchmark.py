from collections import deque
import scipy
import numpy as np
import copy


class BenchmarkTool(object):
    """
    Helper that allows to benchmark a (generic) task. To this end, data of type 'quantity' vs 'time needed'
    can be supplied (by querying the task). Eg. created samples vs the time needed to generate them.
    Based on the gathered data, a speed value [quantity/time] or a time prediction
    for a given quantity is obtained.
    """
    def __init__(self, n_save_datapoints=20):
        self._n_save_datapoints = n_save_datapoints
        # data point: a tuple of (time [s], 'quantity')
        self._datapoints = deque(maxlen=n_save_datapoints)  # fifo-like
        self._datapoints_fixed = list()

    @property
    def n_benchmarks(self):
        return len(self._datapoints) + len(self._datapoints_fixed)

    @property
    def sanity(self):
        a, t0, da = self._get_speed_fit()

        if a + da < 0 or t0 < 0:
            return False

        return True

    def reset(self):
        """
        Reset all gathered data.
        :return:
        """
        self._datapoints_fixed = []
        self._datapoints.clear()

    def add_benchmark(self, time_s, y, is_persistent=False):
        """
        Add a single data point to the benchmark.
        :param time_s: time needed (s)
        :param y: quantity
        :param is_persistent: will not be cleared. If 'False' data is stored in a rolling buffer.
        :return:
        """

        if time_s <= 0.:
            return

        if not is_persistent:
            self._datapoints.append((time_s, y))
        else:
            self._datapoints_fixed.append((time_s, y))

    def estimate_time(self, y, check_sanity=True):
        """
        Estimate the time needed to perform a task of given 'quantity'.
        :param y: quantity
        :param check_sanity: if 'True' will check sanity of the estimation
        :return: time (s) to perform task, -1 if sanity check fails
        """

        a, t0, _ = self._get_speed_fit()

        if self.sanity or not check_sanity:
            return t0 + a * y

        return -1

    def estimate_speed(self, check_sanity=True):
        """
        Estimate the speed value from the gathered data.
        :param check_sanity: if 'True' will check sanity of the estimation
        :return: speed ([quantity] / s), np.nan if sanity check fails
        """
        a, t0, _ = self._get_speed_fit()

        if self.sanity or not check_sanity:
            return 1. / a

        return np.nan

    def save(self, obj=None, value=None):
        # function signature needs to fulfill the StatusVar logic

        save_dict = copy.deepcopy(self.__dict__)
        # make deque serializable
        save_dict['_datapoints'] = copy.deepcopy(list(self._datapoints))

        return save_dict

    def load_from_dict(self, obj=None, saved_dict=None):

        if saved_dict != None:
            saved_dict['_datapoints'] = deque(saved_dict['_datapoints'], maxlen=self._n_save_datapoints)

            self.__dict__.update(saved_dict)

    def _get_speed_fit(self):

        # linear fit t= a*y + t0 over all data with t: time, y: benchmark quantitiy
        all_data = np.asarray(self._datapoints_fixed + list(self._datapoints))

        if len(self._datapoints) > len(self._datapoints_fixed):
            # ensure rolling data has max 50:50 weight
            weighted_data = np.asarray(self._datapoints_fixed + list(self._datapoints)[-len(self._datapoints_fixed):])
        else:
            weighted_data = all_data

        if len(all_data) < 1:
            return np.nan, np.nan, np.nan
        if len(np.unique(all_data[:,1])) == 1:
            # fit needs at least 2 different datapoints in y
            return np.average(all_data[:,0])/all_data[0,1], 0, np.nan
        a, t0, _, _, da = scipy.stats.linregress(weighted_data[:, 1], weighted_data[:, 0])

        return a, t0, da
