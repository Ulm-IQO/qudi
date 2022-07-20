import pickle
import numpy as np
import os
import re
import pandas as pd

import ast
import difflib

qudi_path = "C:/Users/Setup3-PC/Desktop/qudi"
os.chdir(qudi_path)

try:
    from logic.mfl_irq_driven import MFL_IRQ_Driven
    from logic.mfl_xy8_irq_driven import MFL_IRQ_Driven as MFL_XY8_IRQ_Driven
    from logic.mfl_multi_irq_driven import MFL_Multi_IRQ_Driven
except:
    pass
try:
    # if enums should be de-derialized
    from logic.pulsed.predefined_generate_methods.multi_nv_methods import DQTAltModes, TomoRotations, TomoInit
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
    def list_mult_pulsed_mes(path, incl_subdir=True, filter_strs=['pulsed_measurement', '.dat'],
                             excl_filter_str=None, excl_params=['']):
        files = Tk_file.get_dir_items(path, incl_subdir=incl_subdir)
        files_filtered = files
        for filter in filter_strs:
            files_filtered = Tk_string.filter_str(files_filtered, filter, excl_filter_str)

        return files_filtered

    @staticmethod
    def load_pulsed_result(fname):

        data = pd.read_csv(fname, sep="\t", comment='#', names=["tau", "z1", "z2", "std1", "std2"])
        if pd.isnull(data.iloc[0, -1]):
            data = pd.read_csv(fname, sep="\t", comment='#', names=["tau", "z1", "std1"])
        meta = Tk_file.load_pulsed_metadata(fname)

        mes = {'data': data,
               'file': fname}
        mes = {**mes, **meta}

        fname_params = Tk_file.find_param_file(mes)
        mes['file_params'] = fname_params
        exp_params = {'exp_params': Tk_file.load_pulsed_params(mes)}

        mes = {**mes, **exp_params}

        return mes

    @staticmethod
    def load_pulsed_metadata(fname):

        header_lines = Tk_file.read_file_header(fname)
        meta = Tk_file.extract_header(header_lines)

        return meta


    @staticmethod
    def load_param_file(fname):

        if not fname:
            return None
        if not os.path.exists(fname):
            return None

        header_lines = Tk_file.read_file_header(fname)
        header_flat = ' '.join([line for line in header_lines])

        # cut in the right line
        param_str = header_flat.split('parameters: ')[1].replace("OrderedDict(", "")
        # need to cut, because current save format breaks starting from "('params'"
        param_str = param_str.split("('params'")[0][:-2]
        param_str = param_str + "]"

        # make string format parse-able
        param_str = param_str.replace("',", "':")
        param_str = param_str.replace("(", "").replace(")", "")
        param_str = param_str.replace("[", "").replace("]", "")
        # manually parse back to dict-like entries
        # skip entries unreadable to ast
        param_list = param_str.split(",")
        param_dict_accepted = {}

        for entry in param_list:
            try:
                entry_dict = ast.literal_eval("{" + entry + "}")
            except:
                try:
                    el_manual = Tk_string.str_2_dict(entry)
                    val_enum = Tk_string.str_2_enum(el_manual[1])
                    val = el_manual[1] if val_enum is None else val_enum

                    entry_dict = {el_manual[0]: val}
                except:
                    pass
            try:
                param_dict_accepted = {**param_dict_accepted, **entry_dict}
            except:
                pass
                #raise ValueError(f"Error loading entry {entry} in file: {fname}")

        return param_dict_accepted


    @staticmethod
    def find_param_file(p_mes):

        def diff_letters(a, b):
            return sum(a[i] != b[i] for i in range(len(a)))

        # needed, if "Active POI:" property in .dat file is buggy
        path = os.path.normpath(p_mes['file'])
        # offset for erasing automatic "nv_" previx
        p_file = path.split(os.sep)[-1]
        folder = os.path.join(*path.split(os.sep)[:-1])

        param_file = p_file.split('_pulsed')[0]
        # expected file name for parameter file
        param_file = folder + os.sep + param_file + '_parameters.dat'

        # find file that is closest to expected file name
        files_in_folder = Tk_file.list_mult_pulsed_mes(folder, filter_strs=['parameters', '.dat'], incl_subdir=False)
        if not files_in_folder:
            return None

        database = files_in_folder
        search_file = os.path.abspath(param_file)
        candidate_param_file = os.path.abspath(difflib.get_close_matches(search_file, database)[0])

        # logger.debug(f"Searched: {os.path.basename(search_file)}, found: {os.path.basename(candidate_param_file)},\
        #             n_diff: {diff_letters(candidate_param_file, search_file)}")

        # the seconds of the timestamp in the file name may vary,
        # so accept small difference between expect and found file
        if diff_letters(candidate_param_file, search_file) > 2:
            return None
        else:
            param_file = candidate_param_file

        if os.path.exists(param_file):
            return param_file
        else:
            return None

    @staticmethod
    def load_pulsed_params(p_mes):
        fname = Tk_file.find_param_file(p_mes)
        return Tk_file.load_param_file(fname)

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
        date = pd.to_datetime(found, dayfirst=True)

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
                                           and not any(estr.lower() in x.lower() for estr in exclStrList))]

    @staticmethod
    def str_2_enum(enum_str):
        # todo: works only if enum is known to toolkit
        # ATTENTION: dangerous eval, but no better way
        if "<" in enum_str and ">" in enum_str:
            parse_str = re.findall(r'<.+?:', enum_str)[0][1:-1]
            try:
                return eval(parse_str)
            except:
                pass
        return None

    @staticmethod
    def str_2_dict(dict_str):
        if ":" in dict_str:
            key_str = dict_str.split(":", 1)[0][1:-1]
            val_str = dict_str.split(":", 1)[1][1:]

            key_str = key_str.replace("'", "")
            val_str = val_str.replace("'", "")

            return key_str, val_str
        return None

    @staticmethod
    def params_from_str(in_str, keys=['pix']):
        params = {}
        in_str = in_str.lower()

        for key in keys:
            if f"{key}=" in in_str:
                try:
                    substr = in_str.split(f"{key}=", 1)[1]
                    val = Tk_string.find_num_in_str(substr)[0]
                    params[key] = val
                except IndexError:
                    continue

        return params

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

    fname = r"E:\\Data\\2022\\04\\20220414\\PulsedMeasurement\\dummy_tomography_tests\\single_qubit\\20220414-1356-06_tomography_parameters.dat"
    mes = Tk_file.load_param_file(fname)

    inpath = r"E:\Data\2022\04\20220426\PulsedMeasurement\tomography_test_init=00"

    filter_strs = ['pulsed_measurement', '.dat']
    # filter_strs += ['rabi']

    fnames = Tk_file.list_mult_pulsed_mes(inpath, filter_strs=filter_strs, incl_subdir=True)

    p_raw = []
    for f in fnames:
        # p_i = Tk_file.load_pulsed_metadata(f)
        # p_i = {**p_i, **{'file': f, 'data':Tk_file.load_pulsed_result(f)['data']}}
        # p_i = Tk_file.load_pulsed_result(f)
        p_i = Tk_file.load_pulsed_result(f)
        p_raw.append(p_i)
