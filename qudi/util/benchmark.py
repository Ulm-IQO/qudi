from collections import deque, namedtuple
import scipy
import numpy as np
import copy


class BenchmarkTool(object):

    def __init__(self, n_save_datapoints=20):
        # datapoint: a tuple of (time [s], figure of merit)
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
        self._datapoints_fixed = []
        self._datapoints.clear()

    def add_benchmark(self, time_s, y, is_persistent=False):

        if time_s <= 0.:
            return

        if not is_persistent:
            self._datapoints.append((time_s, y))
        else:
            self._datapoints_fixed.append((time_s, y))

    def estimate_time(self, y, check_sanity=True):

        a, t0, _ = self._get_speed_fit()

        if self.sanity or not check_sanity:
            return t0 + a * y

        return -1

    def estimate_speed(self, check_sanity=True):
        # units: [y] per s
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
            saved_dict['_datapoints'] = deque(saved_dict['_datapoints'])

            self.__dict__.update(saved_dict)

    def _get_speed_fit(self):

        # linear fit t= a*y + t0 over all data with t: time, y: benchmark quantitiy
        all_data = np.asarray(self._datapoints_fixed + list(self._datapoints))

        if len(self._datapoints) > len(self._datapoints_fixed):
            # ensure rolling data has max 50:50 weight
            weighted_data = np.asarray(self._datapoints_fixed + list(self._datapoints[-len(self._datapoints_fixed):]))
        else:
            weighted_data = all_data

        if len(all_data) < 1:
            return np.nan, np.nan, np.nan
        if len(np.unique(all_data[:,1])) == 1:
            # fit needs at least 2 different datapoints in y
            return np.average(all_data[:,0])/all_data[0,1], 0, np.nan
        a, t0, _, _, da = scipy.stats.linregress(weighted_data[:, 1], weighted_data[:, 0])

        return a, t0, da