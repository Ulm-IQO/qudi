import os
from scipy.io import savemat
from collections import namedtuple

from core.util import units

from console_toolkit import *
from mfl_analysis_snippets import *

Series2D = namedtuple('Series2D', 'axes data')



import logging



logger = logging.getLogger(__name__)

def series2d_get_x_axis(ser):
    return ser.axes[:, 0, 0]

def series2d_get_y_axis(ser):
    return ser.axes[0, :, 1]


def sort_fname_with_free_var(fname_list, free_var_list):
    # shadows TUM plot_snippets.py

    fname_list_s = [x for y, x in sorted(zip(free_var_list, fname_list), key=lambda x: float(x[0]))]
    free_var_list_s = [y for y, x in sorted(zip(free_var_list, fname_list), key=lambda x: float(x[0]))]

    return fname_list_s, free_var_list_s


def load_mult_mes_freevar(path, varpos_in_str=0, incl_subdir=True, filter_str=None, excl_filter_str=None,
                          parent_dir_level=0):
    """

    :param path:
    :param varpos_in_str:
    :param incl_subdir:
    :param filter_str:
    :param excl_filter_str:
    :param parent_dir_level: # 0: file name, 1: first parent folder
    :return:
    """
    files = Tk_file.get_dir_items(path, incl_subdir=incl_subdir)
    fname_list = Tk_string.filter_str(files, filter_str, excl_filter_str)

    try:
        varList = []
        for f in fname_list:
            mes_id_str = Tk_file.split_path_to_folder(f)[::-1][parent_dir_level]
            varList.append(Tk_string.find_num_in_str(mes_id_str)[varpos_in_str])

    except IndexError:
        raise IndexError("Error while extracting float out of file name. Make sure only data in folder!")

    """
    mes_list = []
    for file in fname_list:
        mes = LoadedMes(Tk_file.load_pulsed_result(file), file)
        mes_list.append(mes)
    logger.info("Loaded files {}".format([mes.filename for mes in mes_list]))
    """
    return sort_fname_with_free_var(fname_list, varList)     # element: (mes, filepath)

def subtract_background(data, background):
    return data-background

def find_extremum(x,y, mode='max'):

    if mode == 'min':
        dip = x[np.argmin(y)]
        val = np.min(y)
    elif mode == 'max':
        dip = x[np.argmax(y)]
        val = np.max(y)
    else:
        raise ValueError

    return dip, val

def normalize(data, mode='default'):

    if type(mode) != type('str'):
        mode = 'default'
    if mode is 'default':
        mode = 'avg'

    if mode is 'avg':
        data = data / np.average(data)
    elif mode is 'max':
        data = data / np.max(data)
    elif mode is 'sub_bg' or mode is 'sub_bg_avg':
        # atm, need to call manually
        pass
    else:
        raise ValueError("Unknown normalization mode {}".format(mode))

    return data

def load_ser_list(flist, varList, x_axis_str='tau', y_axis_str='zs', normalize_rows=False):
    """
    Load data as list of Series2D for multiple y axes (different mes data, same x axis)
    :param varpos_in_str:
    :param dir:
    :return:
    """

    ser_list = []


    try:
        ser_list.append(load_series(flist, varList, x_axis_str=x_axis_str, y_axis_str=y_axis_str, normalize_y=normalize_rows))
    except IndexError:
        # idx not available
        logger.warn("[WARNING]: y index does not exist.")
        pass

    return ser_list

def load_series(fname_list, free_var_list=None, x_axis_str='tau', y_axis_str='z1', normalize_y=True):
    # shaddows TUM plot_snippets.py

    if free_var_list is None:
        free_var_list = range(0, len(fname_list))
    # sort according to free_var_list
    fname_list_s = [x for y, x in sorted(zip(free_var_list, fname_list), key=lambda x: float(x[0]))]
    free_var_list_s = [y for y, x in sorted(zip(free_var_list, fname_list),  key=lambda x: float(x[0]))]
    fname_list = fname_list_s
    free_var_list = free_var_list_s
    #print free_var_list

    # init array
    n_free_var = len(fname_list)
    # load all and look for largest len(taus)
    m_t = max([len(Tk_file.load_pulsed_result(file)[x_axis_str]) for file in fname_list])
    dataArr = np.zeros([m_t, n_free_var])
    axArr = np.zeros([m_t, n_free_var, 2])

    # for bg subtraction
    if normalize_y == 'sub_bg' or normalize_y == 'sub_bg_avg':
        z0 = Tk_file.load_pulsed_result(fname_list[0])[y_axis_str][:]
        z_avg = np.average([Tk_file.load_pulsed_result(fname)[y_axis_str][:] for fname in fname_list], axis=0)

    for i, fname in enumerate(fname_list):

        mes = Tk_file.load_pulsed_result(fname)

        t = mes[x_axis_str]
        if y_axis_str == "z2-z1":
            z = np.asarray(mes["z2"]) - np.asarray(mes["z1"][:])
        else:
            z = mes[y_axis_str][:]   # Only loading 1 zs
        if normalize_y is not False:
            if normalize_y == 'sub_bg':
                z = subtract_background(z, z0)
            if normalize_y == 'sub_bg_avg':
                z = subtract_background(z, z_avg)
            print("[DEBGUG]: normalizing var {}, min {:.2f} @ {}, max {:.2f} @ {}".format(free_var_list[i],
                  find_extremum(t, z, 'min')[1],  find_extremum(t, z, 'min')[0],
                  find_extremum(t, z, 'max')[1], find_extremum(t, z, 'max')[0]))
            z = normalize(z, normalize_y)

        # sort according to taus
        t_s = [y for y, x in sorted(zip(t, z), key=lambda x: float(x[0]))]
        z_s = [x for y, x in sorted(zip(t, z), key=lambda x: float(x[0]))]
        t = t_s
        z = z_s

        # if shorter data line, pad st mes data is in middle
        if len(z) < m_t:
            n_pad = m_t - len(z)
            z = np.lib.pad(z, (int(np.ceil(n_pad/2.)), int(np.floor(n_pad/2.))), 'constant', constant_values=(1,1))
            t = np.lib.pad(t, (int(np.ceil(n_pad / 2.)), int(np.floor(n_pad / 2.))), 'edge')
            print('[WARNING]: Padding axes for file {} to {}'.format(fname, n_pad + m_t))

        dataArr[:, i] = z
        axArr[:, i, 0] = t
        axArr[:, i, 1] = free_var_list[i]

    return Series2D(axArr, dataArr)
    #return axArr, dataArr

def plot_2d(axesArr, dataArr, target_fig=None, interpolation=None, label_xy=('t', None), units_xy=("s", None)):

    if target_fig is None:
        fig = plt.figure()
    else:
        fig = target_fig

    fig.clear()
    # data plot
    axes = fig.add_axes((0.1, 0.2, .65, .7))  # for data plot
    vmin = np.min(dataArr)  # without pre-init zeros
    vmax = np.max(dataArr)
    # axes
    max_val = axesArr[-1, 0, 0]
    scaled_float = units.ScaledFloat(max_val)
    x_axis_prefix = scaled_float.scale
    x_axis_scaled = axesArr/ scaled_float.scale_val

    axis_extent = [x_axis_scaled[0, 0, 0], x_axis_scaled[-1, 0, 0], axesArr[0, 0, 1], axesArr[0, -1, 1]]
    axes.axis(axis_extent)  # xmin, xmax, ymin, ymax
    ax_show = axes.imshow(np.transpose(dataArr), aspect='auto', vmax=vmax,
                          vmin=vmin,
                          extent=axis_extent, origin='lower', interpolation=interpolation)  # .
    # label
    if label_xy[0] is not None:
        xlabel = label_xy[0] + " [" + x_axis_prefix + units_xy[0] + "]"
        axes.set_xlabel(xlabel)
    if label_xy[1] is not None:
        axes.set_ylabel(label_xy[1])

    # colorbar
    axes = fig.add_axes((0.8, 0.2, .05, 0.7))  # for colorbar
    cb = fig.colorbar(ax_show, axes, orientation='vertical')


def plot_ser_2d(dir, fname, ser, interpolation='nearest', label_xy=(None,None)):

    try:
        os.mkdir(dir)
    except WindowsError:
        #print "[WARNING]: /2d/ folder already existing. Abort saving."
        pass

    fig = plt.figure(figsize=(6,4))
    plot_2d(ser.axes, ser.data, fig, interpolation, label_xy=label_xy)
    fig.savefig(dir + "/" + fname)
    plt.close('all')

    saveDict = {}
    saveDict['x'] = series2d_get_x_axis(ser)
    saveDict['y'] = series2d_get_y_axis(ser)
    saveDict['z1'] = ser.data

    savemat(dir + "/" + fname, saveDict)


def create_2d_to_dir(path, varpos_in_str=0, dir=None, label_xy=('t',None),
                     x_axis_str='tau', y_axis_str='z1', normalize_rows=False,
                     parent_dir_level=0):

    flist, varlist = load_mult_mes_freevar(path, varpos_in_str=varpos_in_str, filter_str='pulsed_measurement.dat',
                                           parent_dir_level=parent_dir_level)
    ser_list = load_ser_list(flist, varlist, x_axis_str=x_axis_str, y_axis_str=y_axis_str, normalize_rows=normalize_rows)

    if len(ser_list) != 1:
        raise RuntimeError("Loaded {} y axes instead of 1.", len(ser_list))

    plot_ser_2d(path + "/2d/", y_axis_str, ser_list[0], label_xy=label_xy)



logging.basicConfig()
activate_loggers([__name__], level=logging.DEBUG)


create_2d_to_dir(r"E:\Data\2020\10\20201001\PulsedMeasurement\mfl_calibs_mult_tausweeps.1", varpos_in_str=1, label_xy=('t',"n_pi"),
                 parent_dir_level=1)
create_2d_to_dir(r"E:\Data\2020\10\20201001\PulsedMeasurement\mfl_calibs_mult_tausweeps.1", y_axis_str="z2-z1", label_xy=('t',"n_pi"),
                                                                                varpos_in_str=1, parent_dir_level=1)