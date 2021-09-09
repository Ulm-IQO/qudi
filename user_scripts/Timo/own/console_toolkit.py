import pickle
import numpy as np
import os
import re
import pandas as pd

qudi_path = "C:/Users/Setup3-PC/Desktop/qudi"
os.chdir(qudi_path)

try:
    from logic.mfl_irq_driven import MFL_IRQ_Driven
    from logic.mfl_xy8_irq_driven import MFL_IRQ_Driven as MFL_XY8_IRQ_Driven
    from logic.mfl_multi_irq_driven import MFL_Multi_IRQ_Driven
except:
    pass

from abc import abstractstaticmethod

class Tk_file():

    @staticmethod
    def dump_obj(obj, filename):

        def to_dict(obj):
            mdict = {}
            accept_types = [np.ndarray, str, bool, float, int, list, tuple]

            if type(obj) is dict:
                d = obj
            else:  # convert generic object to dict
                d = obj.__dict__

            for key, var in d.items():
                if type(var) in accept_types:
                    mdict[key] = var
                # clear up subdicts from non accepted types
                if type(var) is dict:
                    mdict[key] = to_dict(var)

            return mdict

        mes = to_dict(obj)

        with open(filename, 'wb') as file:
            pickle.dump(mes, file)

    @staticmethod
    def get_filename_no_extension(filename):
        return os.path.splitext(filename)[0]

    @staticmethod
    def change_extension(filename, new_ext):
        return Tk_file.get_filename_no_extension(filename) + "." + str(new_ext)

    @staticmethod
    def load_pickle(filename=None):
        if filename is None:
            filename = qudi_path + "/temp/mfl_mes_result.pkl"
        with open(filename, 'rb') as file:
            pickle_dict = pickle.load(file)

        return pickle_dict

    @staticmethod
    def load_seperate_thread_results(filename, excl_keys=[]):
        """
        Loads a single result file as created from mfl_logic run as seperate thread.
        :param filename:
        :param excl_keys:
        :return:
        """
        mes_dict = Tk_file.load_pickle(filename)

        if 'mfl_ramsey_pjump' in mes_dict['sequence_name'] in mes_dict['sequence_name'] and mes_dict['bs'].shape[
            1] == 2:
            mes = MFL_Multi_IRQ_Driven(None, no_super=True, manager=None, name=None)
        elif 'xy8' in mes_dict['sequence_name']:
            mes = MFL_XY8_IRQ_Driven(None, no_super=True, manager=None, name=None)
        else:
            mes = MFL_IRQ_Driven(None, no_super=True, manager=None, name=None)

        mes.__dict__.update(mes_dict)

        for ekey in excl_keys:
            try:
                del (mes.__dict__[ekey])
            except:
                pass

        return mes

    @staticmethod
    def load_pulsed_result(fname):

        data = pd.read_csv(fname, sep="\t", comment='#', names=["tau", "z1", "z2", "std1", "std2"])
        meta = Tk_file.load_pulsed_metadata(fname)

        mes = {'data': data,
               'file': fname}
        mes = {**mes, **meta}

        return mes

    @staticmethod
    def load_pulsed_metadata(fname):

        header_lines = Tk_file.read_file_header(fname)
        meta = Tk_file.extract_header(header_lines)

        return meta

    @staticmethod
    def read_file_header(fname, comment_char='#'):
        with open(fname, "r") as fi:
            id = []
            for ln in fi:
                if ln.startswith(comment_char):
                    id.append(ln[1:])
                # id.append(ln.startswith(comment_char))

        return id

    @staticmethod
    def extract_header(header_lines):

        header_flat = ' '.join([line for line in header_lines])
        text = header_flat

        # time of experiment
        m = re.search('on(.+?)\n', text)
        if m:
            found = m.group(1)
        date = pd.to_datetime(found)

        # poi
        m = re.search('POI:(.+?)\n', text)
        if m:
            found = m.group(1)
        poi = found.lstrip()

        meta = {'date': date,
                'poi': poi}
        return meta

    @staticmethod
    def get_dir_items(dir=None, incl_subdir=False):
        # list files in directory
        import os
        from glob import glob

        if dir is None:
            path = '.'
        else:
            path = dir
        files = [path + "/" + f for f in os.listdir(path) if os.path.isfile(path + "/" + f)]

        if incl_subdir:
            files = []
            start_dir = path
            pattern = "*"

            for dir, _, _ in os.walk(start_dir):
                files.extend(glob(os.path.join(dir, pattern)))

        return files

    @staticmethod
    def get_parent_dir(filename):

        from pathlib import Path
        parent_dir_full = Path(filename).parents[0]
        parent_dir_last = parent_dir_full.name

        return parent_dir_last, parent_dir_full

    @staticmethod
    def split_path_to_folder(path):
        # can probably replace by os.path.normpath(fname_list[0]).split(os.path.sep)
        # https://stackoverflow.com/questions/3167154/how-to-split-a-dos-path-into-its-components-in-python
        folders = []
        while 1:
            path, folder = os.path.split(path)

            if folder != "":
                folders.append(folder)
            else:
                if path != "":
                    folders.append(path)

                break

        folders.reverse()
        return folders


class Tk_string():

    @staticmethod
    def find_num_in_str(str):
        import re
        numstrList = re.findall(r"[-+]?\d*\.\d+|\d+", str)
        # don't sort here, order of files important for load_series()
        return numstrList

    @staticmethod
    def filter_str(strList, containStr, exclStrList=[]):

        if containStr:
            containStr = containStr.lower()
        else:
            containStr = ""

        # allow single string input for backward comp
        if isinstance(exclStrList, str):
            exclStrList = [exclStrList]

        if exclStrList is None or not exclStrList:
            return [x for x in strList if containStr in x.lower()]
        else:
            return [x for x in strList if (containStr in x.lower()
                                           and not any(estr in x.lower() for estr in exclStrList))]


class Tk_math():

    @staticmethod
    def find_nearest(array, value):
        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return idx, array[idx]

    @staticmethod
    def mean_y_for_duplicate_x(x, y):
        import pandas as pd

        zipped = sorted(zip(x, y), key=lambda x: x[0])

        data = pd.DataFrame(zipped)
        data = data.groupby(0, as_index=False)[1].mean().values.tolist()

        x = [el[0] for el in data]
        y = [el[1] for el in data]

        return x, y

    @staticmethod
    def running_mean(x, N):
        cumsum = np.cumsum(np.insert(x, 0, 0))
        return (cumsum[N:] - cumsum[:-N]) / float(N)

    def funcspace(start, end, npoints, func, warp_factor=0):
        """
        :param start:
        :param end:
        :param npoints:
        :param func: needs to be defined first, eg. def func(x): return x**2

        :return:
        """
        # https://stackoverflow.com/questions/34017691/numpy-generate-grid-according-to-density-function
        x = np.linspace(start, end, npoints)
        f_x = func(x)

        g = warp_factor

        density = (1 + g * (f_x - 1)) / f_x
        if 0 in f_x:
            raise ZeroDivisionError

        # sum the intervals to get new grid
        x_density = np.cumsum(density)
        # rescale to match old range
        x_density -= x_density.min()
        x_density /= x_density.max()
        x_density *= (end - start)
        x_density += start

        return x_density

    import matplotlib.pyplot as plt

    def two_sym_logspace(start, end, npoints=20):
        mid = (end - start) / 2

        space1 = abs(np.geomspace(-start, -mid, int(npoints) // int(2)))
        print(space1)
        space2 = np.geomspace(mid, end, int(npoints) // int(2))
        print(space2)
        return np.concatenate([space1, space2])

    def func(x, a=15, b=-6, c=2.1, d=-0.34, e=0.018):
        return a + b * x + c * x ** 2 + d * x ** 3 + e * x ** 4

    def func(x, a=10.0, b=-3.64, c=0.36):
        return a + b * x + c * x ** 2

    def func(x, a=0.1, t2star=15, c=0):
        return a * (x - t2star) ** (2) + c


if __name__ == '__main__':
    """
    # warped tau space
    t2star = 15
    tau0 = .025
    tau1 = 40
    n_poinst = 100
    tau_space_warp = (funcspace(tau0, tau1, n_poinst, func, warp_factor=0.99))
    #two_log_space = two_sym_logspace(tau0, tau1, n_poinst)
    linspace = np.linspace(tau0, tau1, n_poinst)

    #plt.hist(tau_space_warp, bins=30)
    plt.figure()
    plt.plot(linspace, func(linspace), 'ok')
    plt.plot(tau_space_warp, func(tau_space_warp), 'or')
    print(tau_space_warp)
    plt.show()
    """

    # file = 'E:/Data/2019/09/20190910/PulsedMeasurement\mfl_n_sweeps=500_B=2.35MHz.23/20190910-1338-41_MFL_irq_driven_mfl_raw.pkl'
    # mes =  Tk_file.load_seperate_thread_results(file)
    # mes.get_total_times()
    # mes.calc_sensitivity()