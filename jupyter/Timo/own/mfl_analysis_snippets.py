import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import logging
from collections import namedtuple
import copy as cp

from console_toolkit import *
from logic.fit_logic import *


logger = logging.getLogger(__name__)

# manual init of fitlogic
kwargs = {'manager': None, 'name': None}
config = {}
fitlogic = FitLogic(**kwargs, config=config)

import imp
qudi_dir = 'C:/Users/Setup3-PC/Desktop/qudi/'
path_mfl_lib = qudi_dir + '/jupyter/Timo/own/mfl_sensing_simplelib.py'


mfl_lib = imp.load_source('packages', path_mfl_lib)

#### Type defs ####

LoadedMes = namedtuple('Mes', 'mes filename')
GAMMA_NV_HZ_GAUSS = 2.8e6  # Hz per Gauss


##### Basics #####

def activate_loggers(active_logs=[], level=logging.DEBUG):
    # deactivate all loggers (set to low level):
    for loggerStr in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(loggerStr)
        logger.propagate = False

    # activate needed loggers at loglevel
    for lg in active_logs:
        logging.getLogger(lg).propagate = True
        logging.getLogger(lg).setLevel(level)

def load_mult_mes(path, incl_subdir=True, filter_str=None, excl_filter_str=None, excl_params=['priors']):
    files = Tk_file.get_dir_items(path, incl_subdir=incl_subdir)
    files_filter_pkl = Tk_string.filter_str(files, filter_str, excl_filter_str)

    mes_list = []
    for file in files_filter_pkl:
        mes = LoadedMes(Tk_file.load_seperate_thread_results(file, excl_keys=excl_params), file)
        mes_list.append(mes)
    try:
        mes_list = sorted(mes_list, key=lambda x: x[0].meta_dict['t_start'])  # according to starttime
    except:
        logger.warning("Couln't sort measurements")

    logger.info("Loaded files {}".format([el.filename for el in mes_list]))
    return mes_list     # element: (mes, filepath)


def load_mult_pkl(path, incl_subdir=True, filter_str=None, excl_filter_str=None, excl_params=['priors']):
    files = Tk_file.get_dir_items(path, incl_subdir=incl_subdir)
    files_filter_pkl = Tk_string.filter_str(files, filter_str, excl_filter_str)

    mes_list = []
    for file in files_filter_pkl:
        mes = Tk_file.load_pickle(file)
        mes_list.append(mes)

    logger.info("Loaded files {}".format(files_filter_pkl))
    return mes_list     # element: (mes, filepath)


def calc_rolling_mean(x, y, rolling_window=None, subsampling_fraction=20):

    # to pandas for a time series (data is unevenly spaced!)
    data_zip = zip(x, y)
    data_zip = sorted(data_zip, key = lambda x: x[0])

    eta_series = pd.DataFrame(data_zip, columns=['x', 'y'])
    eta_series.set_index(pd.DatetimeIndex(eta_series['x']))

    eta_series['date'] = pd.to_datetime(eta_series['x'], unit='s')
    eta_series.set_index('date', inplace=True)
    #print(eta_series[-10:])
    dt_window = rolling_window
    eta_mean = eta_series.rolling(dt_window, min_periods=1).median()
    eta_std_dev = eta_series.rolling(dt_window, min_periods=1).std()#

    # subsampling on right 3/4 of data
    if len(eta_mean) > 10e3:
        n_skip = int(len(eta_mean) / 10e3)
        n_split = int(len(eta_mean) / subsampling_fraction)
        eta_mean = pd.concat([eta_mean[0:n_split], eta_mean[n_split::n_skip]])
        eta_std_dev = pd.concat([eta_std_dev[0:n_split], eta_std_dev[n_split::n_skip]])

    x = np.asarray(eta_mean['x'].tolist())
    y = np.asarray(eta_mean['y'].tolist())
    dy = np.asarray(eta_std_dev['y'].tolist())
    #print(dy[-10:])

    return x, y, dy


##### Plotting #####

def plot_eta_vs_t(mes_list, eta_mode='all', rolling_window=None, savepath=None, no_scatter=False):

    t_total_list = []
    eta_total_lsti = []
    try:
        n_params = mes_list[0][0].dbs.shape[1]
    except IndexError:
        n_params = 1
    if n_params > 1:
        n_params += 1

    plt.figure(figsize=(6,4*n_params))
    plt.subplot(n_params, 1, 1)

    num_colors = len(plt.rcParams['axes.prop_cycle'].by_key()['color'])

    for i, el in enumerate(mes_list):
        mes = el.mes
        file = el.filename
        parent_dir, _ = Tk_file.get_parent_dir(file)
        try:
            t_total_phase, t_total_seq, t_total = mes.get_total_times()
            eta_phase_total, eta_seq_total, eta_total = mes.calc_sensitivity(use_total_time=True)
        except Exception as e:
            logger.error("Unknown error in file {}".format(file))
            raise e

        if eta_mode is 'all':
            t = t_total
            eta = 1e9 * eta_total
        elif eta_mode is 'phase':
            t = t_total_phase
            eta = 1e9 * eta_phase_total
        elif eta_mode is 'seq':
            t = t_total_seq
            eta = 1e9 * eta_seq_total
        else:
            raise ValueError("Unknown mode: {}".format(eta_mode))

        t_total_list.extend(t)
        eta_total_lsti.extend(eta)

        # plot single trace
        if not no_scatter:
            label = parent_dir.replace("n_sweeps=500_", "")
            for i_param in range(0, n_params):
                if i_param == n_params -1:
                    break # no scatter for average plot
                plt.subplot(n_params, 1, i_param+1)
                plt.scatter(t, eta[:,i_param],
                            label="{}".format(label), color='C{}'.format(i%num_colors), s=1, alpha=0.5)

    if n_params > 1:
        eta_avg = np.average(eta_total_lsti, axis=1)
        eta_total_lsti = np.append(eta_total_lsti, eta_avg[:, np.newaxis], axis=1)

    save_dict = {'rolling_window': str(rolling_window)}

    for i_param in range(0, n_params):
        plt.subplot(n_params, 1, i_param + 1)
        plt.ylabel("$\eta (nT/\sqrt{Hz})$")
        plt.xlabel("$t_{total} (s)$")
        axes = plt.gca()
        axes.set_xscale('log')
        axes.set_yscale('log')
        # axes.set_xlim([10e-3, 10])
        axes.set_ylim([10, 10e4])

        # plot rolling mean
        if rolling_window is not None:
            t_roll_ms = _window_str_2_ms(rolling_window)

            x, y, dy = calc_rolling_mean(t_total_list, eta_total_lsti[:,i_param], rolling_window=rolling_window)
            save_dict.update({'t_tot_{:d}'.format(i_param): x,
                              'eta_nT_sqrt(Hz)_{:d}'.format(i_param): y,
                              'std_eta_sqrt(Hz)_{:d}'.format(i_param): dy})

            axes.plot(x, y, label='median, window= {}'.format(rolling_window), linewidth=5)

            if not np.isnan(t_roll_ms):
                idx_end_roll, _ = Tk_math.find_nearest(x, x[-1] - 1*t_roll_ms*1e-3)
                idx_start_avg, _ = Tk_math.find_nearest(x, x[-1] - 5*t_roll_ms*1e-3)
                eta_min = np.min(y[idx_start_avg:idx_end_roll])
            else:
                eta_min = np.median(y[-10:])
            #eta_min = np.nanmin(y)

            plt.axhline(eta_min, label="min= {:.1f} nT".format(eta_min))
            plt.fill_between(x, y - dy, y + dy,
                             alpha=0.2, edgecolor='#1B2ACC', facecolor='#089FFF', antialiased=True)
            #plt.plot(x, dy)

        plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")

    fname_noext = Tk_file.get_filename_no_extension(savepath) + "_" + eta_mode
    if rolling_window is not None:
        dump_filename = fname_noext + ".pkl"
        Tk_file.dump_obj(save_dict, dump_filename)
        save_fig(fname_noext)
#    plt.show()

def plot_db_vs_epochs(mes_list, eta_mode='all', rolling_window=None, savepath=None):
    x_total_list = []
    y_total_list = []

    eta_total_lsti = []
    try:
        n_params = mes_list[0][0].dbs.shape[1]
    except IndexError:
        n_params = 1

    plt.figure(figsize=(6,4*n_params))
    plt.subplot(n_params, 1, 1)
    num_colors = len(plt.rcParams['axes.prop_cycle'].by_key()['color'])

    for i, el in enumerate(mes_list):
        mes = el.mes
        file = el.filename
        parent_dir, _ = Tk_file.get_parent_dir(file)

        try:
            t_total_phase, t_total_seq, t_total = mes.get_total_times()
            y = mes.dbs
        except Exception as e:
            logger.error("Unknown error in file {}".format(file))
            raise e

        if eta_mode is 'all':
            t = t_total
        elif eta_mode is 'phase':
            t = t_total_phase
        elif eta_mode is 'seq':
            t = t_total_seq
        else:
            raise ValueError("Unknown mode: {}".format(eta_mode))


        y_total_list.extend(y)
        n_epochs = len(y)
        x = np.arange(0, n_epochs, 1)
        x_total_list.extend(x)


        # plot single trace
        label = parent_dir

        for i_param in range(0, n_params):
            plt.subplot(n_params, 1, i_param+1)
            plt.scatter(x, y[:, i_param],
                        label="{}".format(label), color='C{}'.format(i % num_colors), s=1, alpha=0.5)




    y_total_list = np.asarray(y_total_list)


    save_dict = {'rolling_window': str(rolling_window)}  # {'x1_nT': x1, ...}
    # plot rolling mean
    if rolling_window is not None:
        for i_param in range(0, n_params):
            plt.subplot(n_params, 1, i_param + 1)
            plt.ylabel("$dB \mathrm{(MHz)}$")
            plt.xlabel("$epoch $")
            axes = plt.gca()
            axes.set_xscale('log')
            axes.set_yscale('log')
            # axes.set_xlim([10e-3, 10])
            # axes.set_ylim([10, 10e4])

            x, y, dy = calc_rolling_mean(x_total_list, y_total_list[:,i_param], rolling_window=rolling_window)
            save_dict.update({'epoch': x,
                              'dB_MHz_{:d}'.format(i_param): y,
                              'std_MHz_nT_{:d}'.format(i_param): dy})

            axes.plot(x, y, label='median, window= {}'.format(rolling_window), linewidth=5)

            eta_min = np.nanmin(y)
            plt.axhline(eta_min, label="min= {:f} MHz".format(eta_min))
            plt.fill_between(x, y - dy, y + dy,
                             alpha=0.2, edgecolor='#1B2ACC', facecolor='#089FFF', antialiased=True)
            #plt.plot(x, dy)
            plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")


    fname_noext = Tk_file.get_filename_no_extension(savepath) + "_" + eta_mode
    if savepath is not None:
        dump_filename = fname_noext + ".pkl"
        Tk_file.dump_obj(save_dict, dump_filename)
        save_fig(dump_filename)

def plot_db_vs_t(mes_list, eta_mode='all', rolling_window=None, savepath=None):

    t_total_list = []
    y_total_list = []

    eta_total_lsti = []
    try:
        n_params = mes_list[0][0].dbs.shape[1]
    except IndexError:
        n_params = 1

    plt.figure(figsize=(6,4*n_params))
    plt.subplot(n_params, 1, 1)
    num_colors = len(plt.rcParams['axes.prop_cycle'].by_key()['color'])

    for i, el in enumerate(mes_list):
        mes = el.mes
        file = el.filename
        parent_dir, _ = Tk_file.get_parent_dir(file)

        try:
            t_total_phase, t_total_seq, t_total = mes.get_total_times()
            y = mes.dbs
        except Exception as e:
            logger.error("Unknown error in file {}".format(file))
            raise e

        if eta_mode is 'all':
            t = t_total
        elif eta_mode is 'phase':
            t = t_total_phase
        elif eta_mode is 'seq':
            t = t_total_seq
        else:
            raise ValueError("Unknown mode: {}".format(eta_mode))

        t_total_list.extend(t)
        y_total_list.extend(y)
        n_epochs = len(y)
        x = np.arange(0, n_epochs, 1)


        # plot single trace
        label = parent_dir

        for i_param in range(0, n_params):
            plt.subplot(n_params, 1, i_param+1)
            plt.scatter(t, y[:,i_param],
                        label="{}".format(label), color='C{}'.format(i%num_colors), s=1, alpha=0.5)



    y_total_list = np.asarray(y_total_list)


    save_dict = {'rolling_window': str(rolling_window)}  # {'x1_nT': x1, ...}
    # plot rolling mean
    if rolling_window is not None:
        for i_param in range(0, n_params):
            plt.subplot(n_params, 1, i_param + 1)
            plt.ylabel("$dB \mathrm{(MHz)}$")
            plt.xlabel("$t_{total} (s)$")
            axes = plt.gca()
            axes.set_xscale('log')
            axes.set_yscale('log')
            # axes.set_xlim([10e-3, 10])
            # axes.set_ylim([10, 10e4])

            x, y, dy = calc_rolling_mean(t_total_list, y_total_list[:,i_param], rolling_window=rolling_window)
            save_dict.update({  't_tot_{:d}'.format(i_param): x,
                                'dB_MHz_{:d}'.format(i_param): y,
                                'std_MHz_nT_{:d}'.format(i_param): dy})


            axes.plot(x, y, label='median, window= {}'.format(rolling_window), linewidth=5)

            eta_min = np.nanmin(y)
            plt.axhline(eta_min, label="min= {:f} MHz".format(eta_min))
            plt.fill_between(x, y - dy, y + dy,
                             alpha=0.2, edgecolor='#1B2ACC', facecolor='#089FFF', antialiased=True)
            #plt.plot(x, dy)
            plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")


    fname_noext = Tk_file.get_filename_no_extension(savepath) + "_" + eta_mode
    if rolling_window is not None:
        dump_filename = fname_noext + ".pkl"
        Tk_file.dump_obj(save_dict, dump_filename)
        save_fig(dump_filename)

def plot_b_vs_epoch(mes_list, savepath=None, is_unit_ut=True):

    plt.figure(figsize=(6, 4))
    fig, axs = plt.subplots(1,1)
    num_colors = len(plt.rcParams['axes.prop_cycle'].by_key()['color'])

    for i, el in enumerate(mes_list):
        mes = el.mes
        file = el.filename
        parent_dir, _ = Tk_file.get_parent_dir(file)

        """
        buggy for mes with covariance matrices
        try:
            x_epochs = 1 + np.asarray(range(len(mes.taus) + 1))  # plot "before first epoch", start from x=1
            b_mhz = np.concatenate([mes.data_before_first_epoch['b_mhz'][np.newaxis,:],     mes.bs[:,:]])  # 2nd index: all params
            db_mhz = np.concatenate([mes.data_before_first_epoch['db_mhz'],   mes.dbs[:,:]])
        except KeyError:
        """
        x_epochs = 1 + np.asarray(range(len(mes.taus)))
        b_mhz =  mes.bs[:,:]
        db_mhz = mes.dbs[:,:]


        #b_khz = mes.bs[:,:]*1e3  # 2nd index: all params
        #db_khz = mes.dbs[:,:]*1e3
        b_ut = b_mhz / 2.8 * 100
        db_ut = db_mhz / 2.8 * 100
        if is_unit_ut:
            b = b_ut
            db = db_ut
        else:
            b = b_mhz
            db = db_mhz

        # plot single trace
        label = parent_dir
        """
        plt.plot(x_epochs, b_mhz,
                    label="{}".format(label), color='C{}'.format(i % num_colors))

        plt.fill_between(x_epochs, b_mhz - db_mhz, b_mhz + db_mhz,
                         alpha=0.1, edgecolor=None, facecolor='C{}'.format(i % num_colors), antialiased=True)
        """
        #"""
        n_params = len(b_mhz[0,:])

        for j in range(0, n_params):
            plt.plot(x_epochs, b[:,j],
                        label="{}".format(label), color='C{}'.format((i+j) % num_colors))

            plt.fill_between(x_epochs, b[:,j] - db[:,j], b[:,j] + db[:,j],
                             alpha=0.2, edgecolor=None, facecolor='C{}'.format((i+j) % num_colors), antialiased=True)
        #"""
    plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    #fig.legend(loc=7)
    #fig.tight_layout()
    #fig.subplots_adjust(right=0.75)

    #plt.tight_layout()
    plt.xlabel("$epoch$")
    plt.ylabel("$\gamma B / 2 \pi $  $(\mathrm{MHz}) $")
    if is_unit_ut:
        plt.ylabel(r'$B\ (\mathrm{ μ T})$')          # mathrm forces upright
    axes = plt.gca()
    axes.set_xscale('log')
    #axes.set_yscale('log')
    axes.set_xlim([x_epochs[0], x_epochs[-1]*1.5])
    #axes.set_ylim([10, 10e4])

    # number of ticks
    plt.locator_params(axis='y', nbins=4)

    save_fig(savepath)

   # plt.show()

def plot_hist_taus(mes_list, savepath=None):


    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    num_colors = len(plt.rcParams['axes.prop_cycle'].by_key()['color'])

    taus = []
    for i, el in enumerate(mes_list):
        mes = el.mes
        file = el.filename
        parent_dir, _ = Tk_file.get_parent_dir(file)
        taus.append(mes.taus)

    x_epochs = range(0, len(taus[0]))
    t2_star = mes_list[0].mes.mfl_t2star_s

    taus_all = (np.asarray(taus)).flatten()
    tau_min = np.min(taus_all)
    tau_max = np.max(taus_all)
    tau_median = np.median(taus_all)
    tau_avg = np.average(taus_all)

    # plot vs epochs

    plt.subplot(121)
    for rep_row in taus:
        plt.scatter(x_epochs, (np.asarray(rep_row)).flatten()*1e6, color='blue', s=3)

    axes = plt.gca()
    axes.set_yscale('log')

    plt.axhline(y=t2_star * 1e6, label='T2*= {} us'.format(t2_star * 1e6), color='red')
    plt.axhline(y=tau_median * 1e6, label='median= {:.1f} us'.format(tau_median * 1e6), color='green')
    plt.legend()
    plt.ylabel("tau (us)")
    plt.xlabel("epoch")
    plt.title("In total {} taus in {} runs of {} epochs".format(len(taus_all), len(mes_list), mes_list[0].mes.n_epochs))

    # plot histo
    n_bins = len(mes_list) if len(mes_list) < 100 else 100
    bin_list = 1e6*np.linspace(tau_min, tau_max, n_bins)
    plt.subplot(122)

    hist_fail, _, _ = plt.hist(taus_all*1e6, label='avg= {:.1f}, max= {:.1f}'.format(
                                1e6*tau_avg, 1e6*tau_max),
                               bins=bin_list)

    plt.axvline(x=t2_star * 1e6, color='red')
    plt.axvline(x=tau_median * 1e6, color='green')
    plt.legend()


   #plt.ylim([0, ymax])
    axes = plt.gca()
    axes.set_yscale('log')
    plt.ylabel("hits")
    plt.xlabel("tau (us)")

    #axes.set_xscale('log')

    save_fig(savepath)


def plot_eta_vs_B(mes_list, eta_mode='all', savepath=None):

    b_mhz_list = []
    eta_total_lsti = []

    try:
        n_params = mes_list[0][0].dbs.shape[1]
    except IndexError:
        n_params = 1

    plt.figure(figsize=(6,4*n_params))

    num_colors = len(plt.rcParams['axes.prop_cycle'].by_key()['color'])

    for i, el in enumerate(mes_list):
        mes = el.mes
        file = el.filename
        parent_dir, _ = Tk_file.get_parent_dir(file)
        try:
            t_total_phase, t_total_seq, t_total = mes.get_total_times()
            eta_phase_total, eta_seq_total, eta_total = mes.calc_sensitivity(use_total_time=True)
        except Exception as e:
            logger.error("Unknown error in file {}".format(file))
            raise e

        if eta_mode is 'all':
            eta = 1e9 * eta_total
        elif eta_mode is 'phase':
            eta = 1e9 * eta_phase_total
        elif eta_mode is 'seq':
            eta = 1e9 * eta_seq_total
        else:
            raise ValueError("Unknown mode: {}".format(eta_mode))

        b_mhz_list.append(mes.bs[-1,:])
        eta_total_lsti.append(eta[-1])

    b_mhz_list = np.asarray(b_mhz_list)
    eta_total_lsti = np.asarray(eta_total_lsti)

    # plot single trace
    label = parent_dir.replace("n_sweeps=500_", "")
    for i in range(0, n_params):
        plt.subplot(n_params, 1, i + 1)
        plt.scatter(b_mhz_list[:,i], eta_total_lsti[:,i],
                    label="{}".format(label), s=1, alpha=1)
        eta_median = np.median(eta_total_lsti[:,i])
        plt.axhline(eta_median,  label="median= {:.3f} MHz".format(eta_median))

        plt.ylabel("eta (nT/sqrt(Hz))")
        plt.xlabel("est(B) (MHz)")
        axes = plt.gca()
        axes.set_xscale('log')
        #axes.set_yscale('log')
        #axes.set_xlim([10e-3, 10])
        axes.set_ylim([10, 500])
        plt.legend()

    fname_noext = Tk_file.get_filename_no_extension(savepath) + "_" + eta_mode
    save_fig(fname_noext)
#    plt.show()


def plot_b_vs_runs(mes_list, taxis=False, savepath=None):

    import datetime

    b_mhz_runs = []
    db_mhz_runs = []
    t_s = []


    for i, el in enumerate(mes_list):
        mes = el.mes
        file = el.filename
        parent_dir, _ = Tk_file.get_parent_dir(file)

        b_mhz_runs.append(mes.bs[-1,:])    # all estimated params, one run, end of all epochs
        db_mhz_runs.append(mes.dbs[-1,:])

        t_start = datetime.datetime.strptime(mes.meta_dict['t_start'], '%Y%m%d-%H%M-%S')
        if i == 0:
            t_start_0_s = (t_start - datetime.datetime(2019, 1, 1)).total_seconds()
            t_start_s = 0
        else:
            t_start_s = (t_start - datetime.datetime(2019, 1, 1)).total_seconds() - t_start_0_s
        t_s.append(t_start_s)

    # plot single trace
    b_mhz_runs = np.asarray(b_mhz_runs)
    db_mhz_runs = np.asarray(db_mhz_runs)
    b_mhz_runs = np.asarray(b_mhz_runs)*1e3  # khz!
    db_mhz_runs = np.asarray(db_mhz_runs)*1e3 # khz!
    #b_mhz_runs = np.asarray(b_mhz_runs)[:,0,np.newaxis]   # only first param
    #db_mhz_runs = np.asarray(db_mhz_runs)[:,0,np.newaxis]
    n_params = len(b_mhz_runs[0,:])
    x_runs = range(0, len(b_mhz_runs[:,0]))
    x = x_runs if not taxis else t_s


    #print("Debug: b_mhz_last: {}".format(b_mhz_runs))

    label = parent_dir.replace("n_sweeps=500_", "")
    n_plots = 1 if n_params == 1 else n_params+1
    # for only dif plot
    #n_plots = 1
    fig, axs = plt.subplots(n_plots,1, figsize=(6, 3.5*n_plots))
    num_colors = len(plt.rcParams['axes.prop_cycle'].by_key()['color'])

    # plot all estimated Bs
    for i, param in enumerate(b_mhz_runs[0, :]):
        #break
        plt.subplot(n_plots, 1, i+1)
        plt.plot(x, b_mhz_runs[:,i],
                    color='C{}'.format(i % num_colors), marker='o')
        y_median = np.median(b_mhz_runs[:,i])
        plt.axhline(y_median, color='C{}'.format(i % num_colors), label="median= {:.3f} kHz".format(y_median))
        plt.fill_between(x, b_mhz_runs[:,i] - db_mhz_runs[:,i], b_mhz_runs[:,i] + db_mhz_runs[:,i],
                         alpha=0.3, edgecolor=None, facecolor='C{}'.format(i % num_colors), antialiased=True)
        plt.ylabel(r"$B_{}$".format(i) + "$\mathrm{(kHz)}$")
        plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")

    # plot diff
    if n_params > 1:
        n_params = 0
        plt.subplot(n_plots, 1, i+2)
        b_diff = abs(b_mhz_runs[:, 1]-b_mhz_runs[:, 0])
        db_diff =  np.sqrt(db_mhz_runs[:, 0]**2 + db_mhz_runs[:, 1]**2)
        plt.plot(x, b_diff,
                 color='C{}'.format(i + 1 % num_colors))
        y_median = np.median(b_diff)
        dy_std = np.std(b_diff)
        plt.axhline(y_median, color='C{}'.format(i+1 % num_colors), label="median= {:.5f} +- std= {:.5f} MHz".format(y_median, dy_std))
        #plt.axhline(y_median - dy_std, color='C{}'.format(i + 1 % num_colors), label="mean(db)= {:.5f} MHz".format(np.mean(db_diff)))
        #plt.axhline(y_median + dy_std, color='C{}'.format(i + 1 % num_colors))
        plt.fill_between(x, b_diff - db_diff, b_diff + db_diff,
                         alpha=0.3, edgecolor=None, facecolor='C{}'.format(i+1 % num_colors), antialiased=True,
                         )
        plt.ylabel("$\Delta B_{0,1}$ $\mathrm{(kHz)}$")


    plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    #fig.legend(loc=7)
    #fig.tight_layout()
    #fig.subplots_adjust(right=0.75)

    #plt.tight_layout()
    xlabel = "run" if not taxis else "$time$ $since$ $start$ $(s)$"
    plt.xlabel(xlabel)
    #plt.ylabel("B (uT)")
    axes = plt.gca()
    #axes.set_xscale('log')
    #axes.set_yscale('log')
    # axes.set_xlim([10e-3, 10])
    #axes.set_ylim([np.min(b_mhz_runs.flatten()), np.max(b_mhz_runs.flatten())])

    save_fig(savepath)

def plot_b_hist(mes_list, savepath=None, filter_str_success='combine'):

    b_mhz_runs = []
    db_mhz_runs = []
    b_mhz_runs_fail = []
    db_mhz_runs_fail = []


    for i, el in enumerate(mes_list):
        mes = el.mes
        file = el.filename
        parent_dir, full_dir = Tk_file.get_parent_dir(file)

        if filter_str_success in str(full_dir):
            b_mhz_runs.append(mes.bs[-1,:])    # all estimated params, one run, end of all epochs
            db_mhz_runs.append(mes.dbs[-1,:])
        else:
            b_mhz_runs_fail.append(mes.bs[-1, :])
            db_mhz_runs_fail.append(mes.dbs[-1, :])

    b_arr = np.zeros((len(b_mhz_runs), mes.n_est_ws))
    db_arr = np.zeros((len(b_mhz_runs), mes.n_est_ws))
    b_fail_arr = np.zeros((len(b_mhz_runs_fail), mes.n_est_ws))
    db_fail_arr = np.zeros((len(b_mhz_runs_fail), mes.n_est_ws))
    b_arr[:,:] = b_mhz_runs
    db_arr[:,:] = db_mhz_runs
    try:
        b_fail_arr[:,:] = b_mhz_runs_fail
        db_fail_arr[:,:] = db_mhz_runs_fail
    except:
        pass

    b_min_1 = np.min(np.concatenate([b_arr[:,0], b_fail_arr[:,0]]))
    b_max_1 = np.max(np.concatenate([b_arr[:,0], b_fail_arr[:,0]]))
    b_min_2 = np.min(np.concatenate([b_arr[:,1], b_fail_arr[:,1]]))
    b_max_2 = np.max(np.concatenate([b_arr[:,1], b_fail_arr[:,1]]))

    n_bins = len(mes_list) if len(mes_list) < 100 else 100
    bin_list_1 = np.linspace(b_min_1, b_max_1, n_bins)
    bin_list_2 = np.linspace(b_min_2, b_max_2, n_bins)
    bins_list = [bin_list_1, bin_list_2]

    n_rows = mes.n_est_ws
    if mes.n_est_ws == 2:
        n_rows += 1
    n_cols = 1
    plt.figure(figsize=(6, 4*n_rows))

    for i_fig in range(mes.n_est_ws):
        plt.subplot(n_rows, n_cols, i_fig + 1)
        hist, _, _ = plt.hist(b_arr[:,i_fig], label='in combine ({:d} / {:.1f})'.format(
                              len(b_mhz_runs), 100* len(b_mhz_runs)/(len(b_mhz_runs) + len(b_mhz_runs_fail))),
                              bins=bins_list[i_fig])
        hist_fail, _, _ = plt.hist(b_fail_arr[:,i_fig], label='fail ({:d})'.format(len(b_mhz_runs_fail)),
                                   bins=bins_list[i_fig])
        plt.legend()
        axes = plt.gca()
        axes.set_yscale('log')
        plt.ylabel("hits")
        plt.xlabel(r"est($B_{}$) (MHz)".format(i_fig))
        # axes.set_xscale('log')

    if mes.n_est_ws == 2:
        i_fig += 1
        plt.subplot(n_rows, n_cols, i_fig + 1)

        b_all_1 = np.concatenate([b_arr[:, 0], b_fail_arr[:, 0]])
        b_all_2 = np.concatenate([b_arr[:, 1], b_fail_arr[:, 1]])
        plt.hist2d(b_all_1, b_all_2, bins=n_bins//2)
        plt.xlabel("$B_0$ (MHz)")
        plt.ylabel("$B_1$ (MHz)")

    """
    hist_all = np.concatenate([hist, hist_fail])
    ymax = 4*np.median(hist_all[hist_all > 0])
    #plt.ylim([0, ymax])
    """


    save_fig(savepath)


def _get_prior_plotsize(epochs_idx=[], always_show_err=False):
    # shaddows jupyter notebook code

    plot_all = False
    if not list(epochs_idx):
        plot_all = True

    epochs_error = []  # not known in experiments
    n_plots = len(track_priors) if plot_all else len(epochs_idx)
    n_plots += 2 * len(epochs_error)
    n_col = 4 if n_plots >= 4 else n_plots
    n_rows = np.ceil(n_plots / n_col)

    return int(n_rows), int(n_col)

def plot_prior_2d(loaded_mes, epochs_idx=[], n_bins=50, savepath=None, tick_label_digits=3):
        # shaddows jupyter notebbok code

        # load data
        priors = loaded_mes.mes.priors


        n_rows, n_col = _get_prior_plotsize(epochs_idx, always_show_err=False)
        fig, axs = plt.subplots(n_rows, n_col, figsize=(6 * n_col, 3.5 * n_rows))
        try:
            axs.flatten()
        except AttributeError:
            # only one plot -> manually create array
            arr = np.zeros([1,1], dtype=object)
            arr[0, 0] = axs
            axs = arr

        idx_plot = 0
        for i, p in enumerate(priors):
            epoch = i
            if epoch in epochs_idx:
                particle_locations = priors[epoch]

                h, xedge, yedge, img = axs.flatten()[idx_plot].hist2d(particle_locations[:, 0],
                                                      particle_locations[:, 1],
                                                      normed=True, bins=n_bins)

                ax_cur = axs.flatten()[idx_plot]
                label = 'Prior {}'.format(epoch)
                ax_cur.set_title(label)
                ax_cur.set_xlabel("$\gamma B_1 / 2 \pi \ \mathrm{(MHz)}$")
                ax_cur.set_ylabel("$\gamma B_2 / 2 \pi \ \mathrm{(MHz)}$")
                ax_cur.set_ylabel("")

                # disable left tick label (shared left prior, likelihood)
                #ax_cur.tick_params(labelleft=False)

                # only 2 ticks each axis
                ax_cur.set_xticks([np.min(xedge), np.max(xedge)])
                ax_cur.set_yticks([np.min(yedge), np.max(yedge)])
                from matplotlib.ticker import FormatStrFormatter
                ax_cur.yaxis.set_major_formatter(FormatStrFormatter('%.{}f'.format(int(tick_label_digits))))
                ax_cur.xaxis.set_major_formatter(FormatStrFormatter('%.{}f'.format(int(tick_label_digits))))

                #ax_cur.set_xticks([0, 5])
                #ax_cur.set_yticks([0., 5])
                ax_cur.set_xticks([0.536, 0.568])
                ax_cur.set_yticks([0.604, 0.633])
                #fig.colorbar(img)

                idx_plot += 1

        #plt.tight_layout()
        plt.legend()
        #plt.locator_params(nbins=2)  # 4 ticks only, not working

        save_fig(savepath)


def plot_likelihood_2d(loaded_mes, epochs_idx=[], savepath=None, tick_label_digits=3, omega_mhz=[]):
    # shaddows jupyter notebbok code

    # load data
    priors = loaded_mes.mes.priors

    n_rows, n_col = _get_prior_plotsize(epochs_idx, always_show_err=False)
    fig, axs = plt.subplots(n_rows, n_col, figsize=(6 * n_col, 3.5 * n_rows))
    try:
        axs.flatten()
    except AttributeError:
        # only one plot -> manually create array
        arr = np.zeros([1, 1], dtype=object)
        arr[0, 0] = axs
        axs = arr

    idx_plot = 0
    for i, p in enumerate(priors):
        epoch = i
        if epoch in epochs_idx:
            particle_locations = priors[epoch]  # MHz

            if not list(omega_mhz):
                omega_1 = np.linspace(min(particle_locations[:, 0]), max(particle_locations[:, 0]), 100)  # MHz
                omega_2 = np.linspace(min(particle_locations[:, 1]), max(particle_locations[:, 1]), 100)
            else:
                omega_1 = omega_mhz[0]  # MHz
                omega_2 = omega_mhz[1]


            x_grid, y_grid = np.meshgrid(omega_1, omega_2)

            z_bin = 1
            # models don't get saved /serialized, so recreate:
            loaded_mes.mes.mfl_model = mfl_lib.MultimodePrecModel(min_freq=0)
            x, y = loaded_mes.mes.get_likelihood([2*np.pi*x_grid.flatten(), 2*np.pi*y_grid.flatten()],
                                                  idx_epoch=epoch, exp_outcome=z_bin)
            y_2d = y.reshape(len(omega_1), len(omega_2))

            plt.subplot(n_rows, n_col, idx_plot + 1)
            plt.imshow(y_2d, vmin=0, extent=[omega_1[0], omega_1[-1],
                                             omega_2[0], omega_2[-1]],
                       cmap='plasma', aspect='auto', origin='lower')

            # plt.colorbar()

            ax_cur = plt.gca()
            # disable left tick label (shared with prior)
            ax_cur.tick_params(labelleft=False)



            plt.title(r"$L({:.0f}|B,\tau)$".format(z_bin))
            #plt.title(r"$L({:.0f}|B,\tau) {}$".format(z_bin, epoch))
            ax_cur.set_xlabel("$\gamma B_1 / 2 \pi \ \mathrm{(MHz)}$")
            ax_cur.set_ylabel("$\gamma B_2 / 2 \pi \ \mathrm{(MHz)}$")
            ax_cur.set_ylabel("")
            # only 2 ticks each axis
            ax_cur.set_xticks([omega_1[0], omega_1[-1] ])
            ax_cur.set_yticks([omega_2[0], omega_2[-1] ])
            from matplotlib.ticker import FormatStrFormatter
            ax_cur.yaxis.set_major_formatter(FormatStrFormatter('%.{}f'.format(int(tick_label_digits))))
            ax_cur.xaxis.set_major_formatter(FormatStrFormatter('%.{}f'.format(int(tick_label_digits))))

            # ax_cur.set_xticks([0, 5])
            # ax_cur.set_yticks([0., 5])
            # ax_cur.set_xticks([0.536, 0.567])
            # ax_cur.set_yticks([0.604, 0.632])
            # fig.colorbar(img)

            idx_plot += 1

    # plt.tight_layout()
    plt.legend()
    # plt.locator_params(nbins=2)  # 4 ticks only, not working

    save_fig(savepath)


def plot_z_vs_tau(mes, t_phase_max=None, fit_params={}, savepath=None, fig_handle=None, subplot_specifier=None):
    t_total_phase, t_total_seq, t_total = mes.get_total_times()
    if t_phase_max:
        idx_end, t_phase = Tk_math.find_nearest(t_total_phase, t_phase_max)
        t_all = t_total[idx_end]
        zs = mes.zs[:idx_end].flatten()
        tau = mes.taus[:idx_end].flatten()
    else:
        zs = mes.zs.flatten()
        tau = mes.taus.flatten()
        t_phase = t_total_phase
        t_all = t_total

    no_plot = (True if savepath is None and fig_handle is None else False)

    z_vs_t = list(zip(tau, zs))
    z_mean = np.asarray(pd.DataFrame(z_vs_t).groupby(0, as_index=False)[1].mean().values.tolist())

    if not no_plot:
        if fig_handle:
            plt.figure(fig_handle.number)
            if subplot_specifier:
                plt.subplot(subplot_specifier)
        else:
            fig, axs = plt.subplots(1,1, figsize=(6, 3.5))
        plt.plot(z_mean[:,0], z_mean[:,1], 'o')

    # fit
    #fit_params = {'lifetime':{'vary': False, 'value': 10e-6},
    #              'frequency': {'min': 450e3}}

    sinedecay_fit = fitlogic.make_sineexponentialdecay_fit(x_axis=z_mean[:,0],
                                                           data=z_mean[:,1],
                                                           add_params=fit_params,
                                                           estimator=fitlogic.estimate_sineexponentialdecay)
    if not sinedecay_fit.errorbars:
        logger.warning("Fit failed to give errorbars")

    model, params = fitlogic.make_sineexponentialdecay_model()
    analysis_dict = {}
    n_sample = 500
    x_res = np.linspace(min(z_mean[:, 0]), max(z_mean[:, 0]), n_sample)
    analysis_dict['fit_result'] = model.eval(x=x_res, params=sinedecay_fit.params)
    analysis_dict['fit_params'] = sinedecay_fit.best_values
    analysis_dict['fit_params_err'] = {}
    for key, val in sinedecay_fit.params.items():
        analysis_dict['fit_params_err'].update({key: val.stderr})

    if not no_plot:
        plt.plot(x_res, analysis_dict['fit_result'])

    save_dict = {}
    save_dict.update({'tau': z_mean[:,0],
                      'z_mean': z_mean[:,0],
                      'fit_dict': analysis_dict})

    return save_dict, t_phase, t_all

def _get_plotsize(epochs_idx=[], data_list=[]):
    plot_all = not epochs_idx

    n_plots = len(data_list) if plot_all else len(epochs_idx)
    n_col = 4
    n_rows = np.ceil(n_plots / n_col)

    return int(n_rows), int(n_col)

def plot_fit_params_vs_tphase(loaded_mes, savepath=None, fit_params=None, aggregate_data_factor=1, omit_epoch_factor=1):

    # leave out data points
    if omit_epoch_factor > 1:
        # reload file to avoid failing deepcopy
        mes_mod = Tk_file.load_seperate_thread_results(loaded_mes.filename)
        for key, val in mes_mod.__dict__.items():
            if isinstance(val, np.ndarray) or isinstance(val, list):
                if len(val) == mes_mod.n_epochs:
                    mes_mod.__dict__[key] = val[::omit_epoch_factor]
    else:
        mes_mod = loaded_mes.mes



    t_total_phase, t_total_seq, t_total = mes_mod.get_total_times()
    m_complete_tau_sweeps = int(mes_mod.n_epochs /mes_mod.mfl_n_taus)/aggregate_data_factor
    t_granuality = t_total_phase[-1] / float(m_complete_tau_sweeps)

    t_phases_req = np.linspace(t_granuality, m_complete_tau_sweeps * t_granuality, m_complete_tau_sweeps)
    f_fit = []
    df_fit = []
    t2star_fit = []
    dt2star_fit = []
    t_phase = []
    t_allov = []

    n_plots = 30
    delta_i = int(m_complete_tau_sweeps / n_plots)
    draw_full_epochs_idxs = list(np.arange(0, m_complete_tau_sweeps, delta_i))
    n_rows, n_cols = _get_plotsize(draw_full_epochs_idxs, t_phases_req)

    fig, axs = plt.subplots(n_rows, n_cols, figsize=(12, n_rows * 3.5))
    i_fig = 0

    for i, t in enumerate(t_phases_req):
        if i in draw_full_epochs_idxs:
            #subplot = int("{}{}{}".format(n_rows, n_cols, i_fig+1))
            plt.subplot(n_rows, n_cols, i_fig+1)
            res_dict, t_phase_real, t_all_real = plot_z_vs_tau(mes_mod, t_phase_max=t, fit_params=fit_params,
                                                               fig_handle=fig)#, subplot_specifier=subplot)
            i_fig += 1
        else:
            res_dict, t_phase_real, t_all_real = plot_z_vs_tau(mes_mod, t_phase_max=t, fit_params=fit_params)
        f_fit.append(res_dict['fit_dict']['fit_params']['frequency'])
        df_fit.append(res_dict['fit_dict']['fit_params_err']['frequency'])
        t2star_fit.append(res_dict['fit_dict']['fit_params']['lifetime'])
        dt2star_fit.append(res_dict['fit_dict']['fit_params_err']['lifetime'])

        t_phase.append(t_phase_real)
        t_allov.append(t_all_real)

    if savepath is not None:
        fname_noext = Tk_file.get_filename_no_extension(savepath)
        if omit_epoch_factor > 1:
            fname_noext += "_omit_epoch={}".format(omit_epoch_factor)
        if aggregate_data_factor > 1:
            fname_noext += "_aggregate_epoch={}".format(aggregate_data_factor)
        fname_noext += "_fits"
        dump_filename = fname_noext + ".pkl"
        save_fig(dump_filename)

    t_phase = np.asarray(t_phase)
    t_allov = np.asarray(t_allov)
    f_fit = np.asarray(f_fit)
    df_fit = np.asarray(df_fit)
    t2star_fit = np.asarray(t2star_fit)
    dt2star_fit = np.asarray(dt2star_fit)
    dB_tesla = df_fit / (1e6*GAMMA_NV_HZ_GAUSS * 1e-2)
    eta_T = dB_tesla*np.sqrt(t_phase)
    eta_T_all = dB_tesla*np.sqrt(t_allov)


    fig, axs = plt.subplots(3, 2, figsize=(2*6, 2*3.5))

    # f
    plt.subplot(321)
    plt.plot(t_phase, f_fit/1e6, 'o')
    axes = plt.gca()
    plt.ylabel("$B_{fit} \mathrm{(MHz)}$")
    plt.xlabel("$t_{phase} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    # axes.set_ylim([np.min(df_fit), np.median(sorted(df_fit)[-10:-1])])
    #axes.set_ylim([1e3, 10e6])

    # df
    plt.subplot(322)
    plt.plot(t_phase, df_fit/1e3, 'o')
    axes = plt.gca()
    plt.ylabel("$dB_{fit} \mathrm{(kHz)}$")
    plt.xlabel("$t_{phase} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    #axes.set_ylim([np.min(df_fit), np.median(sorted(df_fit)[-10:-1])])
    #axes.set_ylim([1e3, 10e6])

    # t2star
    plt.subplot(323)
    plt.plot(t_phase, t2star_fit*1e6, 'o')
    axes = plt.gca()
    plt.ylabel("${T_2^*}_{fit} \mathrm{(us)}$")
    plt.xlabel("$t_{phase} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    #axes.set_ylim([1e-6, 50e-6])
    #axes.set_ylim([np.min(t2star_fit), np.median(sorted(t2star_fit)[-10:-1])])

    # eta
    plt.subplot(324)
    plt.plot(t_phase, eta_T*1e9, 'o')
    axes = plt.gca()
    plt.ylabel("$\eta_{fit} \mathrm{(nT/sqrt(Hz))}$")
    plt.xlabel("$t_{phase} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    # axes.set_ylim([np.min(df_fit), np.median(sorted(df_fit)[-10:-1])])
    #axes.set_ylim([1e-9, 10e3*1e-9])

    # eta
    plt.subplot(325)
    plt.plot(t_allov, eta_T_all*1e9, 'o')
    axes = plt.gca()
    plt.ylabel("$\eta_{fit} \mathrm{(nT/sqrt(Hz))}$")
    plt.xlabel("$t_{all} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    # axes.set_ylim([np.min(df_fit), np.median(sorted(df_fit)[-10:-1])])
    #axes.set_ylim([1e-9, 10e3*1e-9])
    plt.tight_layout()

    save_dict = {}
    save_dict.update({'t_tot_phase_s': t_phase,
                      'B_fit_Hz': f_fit,
                      'dB_fit_Hz': df_fit,
                      't2_fit_s': t2star_fit,
                      'dt2_fit_s': dt2star_fit,
                      'eta_fit_T_sqrtHz': eta_T})

    # save
    if savepath is not None:
        fname_noext = Tk_file.get_filename_no_extension(savepath)
        if aggregate_data_factor > 1:
            fname_noext += "_aggregate_epoch={}".format(aggregate_data_factor)
        if omit_epoch_factor > 1:
            fname_noext += "_omit_epoch={}".format(omit_epoch_factor)

        dump_filename = fname_noext + ".pkl"
        Tk_file.dump_obj(save_dict, dump_filename)
        save_fig(dump_filename)

def reshuffle_taus_single_taus_at_once(mes_mod):
    # reshufle mes
    # https://stackoverflow.com/questions/19931975/sort-multiple-lists-simultaneously
    mes_info_zip = zip(mes_mod.taus, mes_mod.taus_requested, mes_mod.t_seqs,
                       [el[0] for el in mes_mod.timestamps[1::2]],  # need here, to keep taus ordered in time
                       mes_mod.zs, mes_mod.read_phases, mes_mod.read_phases_requested)
    mes_resorted = zip(*sorted(mes_info_zip))
    mes_mod.taus, mes_mod.taus_requested, mes_mod.t_seqs, _, mes_mod.zs, \
    mes_mod.read_phases, mes_mod.read_phases_requested = map(list, mes_resorted)
    mes_mod.taus, mes_mod.taus_requested, mes_mod.t_seqs, mes_mod.zs, mes_mod.read_phases, \
    mes_mod.read_phases_requested = np.asarray(mes_mod.taus), \
                                    np.asarray(mes_mod.taus_requested), np.asarray(mes_mod.t_seqs), \
                                    np.asarray(mes_mod.zs), np.asarray(mes_mod.read_phases), \
                                    np.asarray(mes_mod.read_phases_requested)

    # loose every meaning
    mes_mod.bs = []
    mes_mod.dbs = []
    mes_mod.likelihoods = []
    mes_mod.priors = []
    # unable to reshuffle t_since_0 atm
    for stamp_list in mes_mod.timestamps:
        stamp_list[2] = 0

    return mes_mod

def plot_fit_params_vs_tphase_single_taus_at_once(loaded_mes, savepath=None, fit_params=None, aggregate_data_factor=1, omit_epoch_factor=1):

    # leave out data points
    if omit_epoch_factor > 1:
        # reload file to avoid failing deepcopy
        mes_mod = Tk_file.load_seperate_thread_results(loaded_mes.filename)
        for key, val in mes_mod.__dict__.items():
            if isinstance(val, np.ndarray) or isinstance(val, list):
                if len(val) == mes_mod.n_epochs:
                    mes_mod.__dict__[key] = val[::omit_epoch_factor]
    else:
        mes_mod = loaded_mes.mes

    # calculate total phase time up to epoch_i
    n_rep_per_tau = mes_mod.n_epochs / mes_mod.mfl_n_taus
    t_phases_req = [mes_mod.taus[i]*n_rep_per_tau*mes_mod.n_sweeps for i in range(1, mes_mod.mfl_n_taus + 1)]
    t_phases_total_req = np.zeros(len(t_phases_req))
    for i, val in enumerate(t_phases_req):
        t_phases_total_req[i] = np.sum(t_phases_req[0:i + 1])

    reshuffle_taus_single_taus_at_once(mes_mod)
    t_total_phase, t_total_seq, t_total = mes_mod.get_total_times()



    f_fit = []
    df_fit = []
    t2star_fit = []
    dt2star_fit = []
    t_phase = []
    t_allov = []

    n_plots = 30

    n_rows =  mes_mod.mfl_n_taus
    fig, axs = plt.subplots(n_rows, 1, figsize=(12,  n_rows * 3.5))
    i_fig = 0
    for i, t in enumerate(t_phases_total_req):
        if i == 0 or i == 1 or i==2 or i==3:
            continue  # few point fit breaks
        plt.subplot(n_rows, 1, i_fig + 1)
        res_dict, t_phase_real, t_all_real = plot_z_vs_tau(mes_mod, t_phase_max=t, fit_params=fit_params,
                                                           fig_handle=fig)  # , subplot_specifier=subplot)
        i_fig += 1

        f_fit.append(res_dict['fit_dict']['fit_params']['frequency'])
        df_fit.append(res_dict['fit_dict']['fit_params_err']['frequency'])
        t2star_fit.append(res_dict['fit_dict']['fit_params']['lifetime'])
        dt2star_fit.append(res_dict['fit_dict']['fit_params_err']['lifetime'])

        t_phase.append(t_phase_real)
        t_allov.append(t_all_real)

    if savepath is not None:
        fname_noext = Tk_file.get_filename_no_extension(savepath)
        if omit_epoch_factor > 1:
            fname_noext += "_omit_epoch={}".format(omit_epoch_factor)
        if aggregate_data_factor > 1:
            fname_noext += "_aggregate_epoch={}".format(aggregate_data_factor)
        fname_noext += "_fits"
        dump_filename = fname_noext + ".pkl"
        save_fig(dump_filename)

    t_phase = np.asarray(t_phase)
    t_allov = np.asarray(t_allov)
    f_fit = np.asarray(f_fit)
    df_fit = np.asarray(df_fit)
    t2star_fit = np.asarray(t2star_fit)
    dt2star_fit = np.asarray(dt2star_fit)
    dB_tesla = df_fit / (1e6*GAMMA_NV_HZ_GAUSS * 1e-2)
    eta_T = dB_tesla*np.sqrt(t_phase)
    eta_T_all = dB_tesla*np.sqrt(t_allov)


    fig, axs = plt.subplots(3, 2, figsize=(2*6, 2*3.5))

    # f
    plt.subplot(321)
    plt.plot(t_phase, f_fit/1e6, 'o')
    axes = plt.gca()
    plt.ylabel("$B_{fit} \mathrm{(MHz)}$")
    plt.xlabel("$t_{phase} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    # axes.set_ylim([np.min(df_fit), np.median(sorted(df_fit)[-10:-1])])
    #axes.set_ylim([1e3, 10e6])

    # df
    plt.subplot(322)
    plt.plot(t_phase, df_fit/1e3, 'o')
    axes = plt.gca()
    plt.ylabel("$dB_{fit} \mathrm{(kHz)}$")
    plt.xlabel("$t_{phase} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    #axes.set_ylim([np.min(df_fit), np.median(sorted(df_fit)[-10:-1])])
    #axes.set_ylim([1e3, 10e6])

    # t2star
    plt.subplot(323)
    plt.plot(t_phase, t2star_fit*1e6, 'o')
    axes = plt.gca()
    plt.ylabel("${T_2^*}_{fit} \mathrm{(us)}$")
    plt.xlabel("$t_{phase} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    #axes.set_ylim([1e-6, 50e-6])
    #axes.set_ylim([np.min(t2star_fit), np.median(sorted(t2star_fit)[-10:-1])])

    # eta
    plt.subplot(324)
    plt.plot(t_phase, eta_T*1e9, 'o')
    axes = plt.gca()
    plt.ylabel("$\eta_{fit} \mathrm{(nT/sqrt(Hz))}$")
    plt.xlabel("$t_{phase} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    # axes.set_ylim([np.min(df_fit), np.median(sorted(df_fit)[-10:-1])])
    #axes.set_ylim([1e-9, 10e3*1e-9])

    # eta
    plt.subplot(325)
    plt.plot(t_allov, eta_T_all*1e9, 'o')
    axes = plt.gca()
    plt.ylabel("$\eta_{fit} \mathrm{(nT/sqrt(Hz))}$")
    plt.xlabel("$t_{all} (s) $")
    axes.set_xscale('log')
    axes.set_yscale('log')
    # axes.set_ylim([np.min(df_fit), np.median(sorted(df_fit)[-10:-1])])
    #axes.set_ylim([1e-9, 10e3*1e-9])
    plt.tight_layout()

    save_dict = {}
    save_dict.update({'t_tot_phase_s': t_phase,
                      'B_fit_Hz': f_fit,
                      'dB_fit_Hz': df_fit,
                      't2_fit_s': t2star_fit,
                      'dt2_fit_s': dt2star_fit,
                      'eta_fit_T_sqrtHz': eta_T})

    # save
    if savepath is not None:
        fname_noext = Tk_file.get_filename_no_extension(savepath)
        if aggregate_data_factor > 1:
            fname_noext += "_aggregate_epoch={}".format(aggregate_data_factor)
        if omit_epoch_factor > 1:
            fname_noext += "_omit_epoch={}".format(omit_epoch_factor)

        dump_filename = fname_noext + ".pkl"
        Tk_file.dump_obj(save_dict, dump_filename)
        save_fig(dump_filename)

def plot_median_fit_params(path, name_pkl, rolling_window=None, savepath=None, t_col_name = 't_tot_phase_s'):

        num_colors = len(plt.rcParams['axes.prop_cycle'].by_key()['color'])

        # load several pkl and make median
        pkl_list = load_mult_pkl(path, filter_str=name_pkl, excl_filter_str=['mfl_irq','excl'])
        table_list = [pd.DataFrame(pkl) for pkl in pkl_list]
        n_params = len(table_list[0].columns) - 1

        # plot each dataset
        fig, axs = plt.subplots(n_params, 1, figsize=(6, 3.5 * n_params))

        for i_t, table in enumerate(table_list):
            i_param = 1
            for col in table:
                if col == t_col_name:
                    continue
                plt.subplot(n_params, 1, i_param)
                plt.scatter(table[t_col_name], table[col],
                            color='C{}'.format(i_t % num_colors), s=1, alpha=0.5,
                            label=None)
                i_param += 1

        mes_table_concat = pd.concat(table_list)
        t = mes_table_concat[t_col_name]

        # calc and plot median
        save_dict = {}
        i_param = 1
        for col in mes_table_concat.columns:
            if col == t_col_name:
                continue
            y = mes_table_concat[col]
            if rolling_window is not None:
                x_med, y_med, _ = calc_rolling_mean(t, y, rolling_window=rolling_window)
                save_dict[t_col_name+'_median'] = x_med
                save_dict.update({'{}_median'.format(col): y_med})

            plt.subplot(n_params, 1, i_param)

            plt.plot(x_med, y_med,
                    label='median, window= {}'.format(rolling_window), linewidth=5,
                     color='C{}'.format(i_param-1 % num_colors))
            plt.ylabel("{}_median".format(col))
            plt.xlabel("{}".format(t_col_name))
            axes = plt.gca()
            axes.set_xscale('log')
            axes.set_yscale('log')
            plt.legend()
            i_param += 1


        plt.tight_layout()

        if savepath is not None:
            fname_noext = Tk_file.get_filename_no_extension(savepath)
            dump_filename = fname_noext + ".pkl"
            Tk_file.dump_obj(save_dict, dump_filename)
            save_fig(fname_noext)

def plot_overhead_times(loaded_mes, savepath=None):
    fig, axs = plt.subplots(figsize=(6, 3.5))

    fname_no_ext = Tk_file.get_filename_no_extension(savepath)
    mes = loaded_mes.mes
    epochs = np.arange(0, len(mes.taus), 1)

    n_sweeps = mes.n_sweeps
    t_phase_s, t_seq_s, t_epoch_s = mes.get_times()
    t_phase_rel = t_phase_s / t_epoch_s
    t_laser_rel = (t_seq_s - t_phase_s) / t_epoch_s
    t_comp_rel = (t_epoch_s - t_seq_s) / t_epoch_s

    t_phase_tot_s, t_seq_tot_s, t_epoch_tot_s =  mes.get_total_times()
    t_phase_tot_rel = t_phase_tot_s / t_epoch_tot_s
    t_laser_tot_rel = (t_seq_tot_s - t_phase_tot_s) / t_epoch_tot_s
    t_comp_tot_rel = (t_epoch_tot_s - t_seq_tot_s) / t_epoch_tot_s

    plt.bar(epochs, t_phase_rel, width =1, label="phase")
    plt.bar(epochs, t_laser_rel, width =1, bottom=t_phase_rel, label="laser")
    plt.bar(epochs, t_comp_rel,  width =1, bottom=t_phase_rel+t_laser_rel, label="comp")
    #plt.bar(epochs, t_phase_rel + t_laser_rel + t_comp_rel, label="rel sum")

    #plt.title("per epoch")
    plt.xlabel("$epoch$")
    plt.ylabel("$rel. time$")
    plt.legend()

    save_fig(fname_no_ext + "_per_epoch" + ".png")

    fig, axs = plt.subplots(figsize=(6, 3.5))
    plt.bar(epochs, t_phase_tot_rel, width =1, label="phase")
    plt.bar(epochs, t_laser_tot_rel, width =1, bottom=t_phase_tot_rel, label="laser")
    plt.bar(epochs, t_comp_tot_rel,  width =1, bottom=t_phase_tot_rel+t_laser_tot_rel, label="comp")

    plt.title("Final: t_ph= {:.3f}, t_l={:.3f}, t_ov = {:.3f}".format(t_phase_tot_rel[-1],
                                                                      t_laser_tot_rel[-1],
                                                                      t_comp_tot_rel[-1]))
    #plt.title("accumulated")
    plt.xlabel("$epoch$")
    plt.ylabel("$rel. time$")
    plt.legend()

    save_fig(fname_no_ext + "_accumuluated" + ".png")

#### Misc ####

def load_from_dir(path, excl_params=['priors'], load_fails=True):

    mes_list = load_mult_mes(path, filter_str='.pkl', excl_filter_str=['median', 'excl'], excl_params=excl_params)
    parent_folders = set([str(Tk_file.get_parent_dir(Tk_file.get_parent_dir(el.filename)[1])[1]) for el in mes_list])
    logger.info("Successfull runs from: {}".format(parent_folders))
    try:
        if load_fails:
            path_all = str(Tk_file.get_parent_dir(path)[1])
            mes_list_fail = load_mult_mes(path_all, filter_str='.pkl', excl_filter_str=['median','combine', 'excl'])
        else:
            mes_list_fail = []
    except:
        logger.warning("Could not find dir with fail data.")
        mes_list_fail = []
    parent_folders = set(
        [str(Tk_file.get_parent_dir(Tk_file.get_parent_dir(el.filename)[1])[1]) for el in mes_list_fail])
    logger.info("Failed runs from: {}".format(parent_folders))

    mes_list_all = mes_list + mes_list_fail
    logger.info("Success in {}/{} mes ({:.1f} %)".format(len(mes_list), len(mes_list_all),
                                                         100 * len(mes_list) / len(mes_list_all)))

    return mes_list, mes_list_fail, mes_list_all

def _window_str_2_ms(window_str):

    if not isinstance(window_str, str):
        return float(np.NAN)

    import re
    vals = re.findall(r"[-+]?\d*\.\d+|\d+", window_str)

    if len(vals) != 1:
        raise ValueError("Found != 1 value in str: {}".format(window_str))

    #if 'ms' not in str:
    #    raise ValueError("Expected unit ms in str: {}".format(str))

    return float(vals[0])

def move_mes_pngs(dir, new_subdir_name):

    import os.path
    import shutil

    mes_list = load_mult_mes(dir, filter_str='.pkl')
    dirs_all_mes = [os.path.dirname(mes.filename) for mes in mes_list]

    # move all pngs into new dir

    for dir in dirs_all_mes:
        all_files = Tk_file.get_dir_items(dir, incl_subdir=False)
        png_files = Tk_string.filter_str(all_files, '.png')

        if not png_files:
            continue

        new_dir = dir + '/' + new_subdir_name
        if not os.path.exists(new_dir):
            os.mkdir(new_dir)
        for png in png_files:
            filename_base = os.path.basename(png)
            new_path = new_dir + '/' + filename_base
            shutil.move(png, new_path)

        logger.info("moved {} pngs to dir: {}".format(len(png_files), new_dir))


def save_fig(fname):

    global save_svg

    ax = plt.gca()
    if disable_legend:
        try:
            ax.get_legend().remove()
        except:
            pass
    # bar ticks
    plt.tick_params(which='both', direction='in',                   # tick direction (major and minor)
                    labeltop=False, labelright=False,               # labels only x,y axis
                    bottom=True, top=True, left=True, right=True)   # ticks at all sides

    try:
        plt.gcf().set_size_inches(overwrite_figsize[0], overwrite_figsize[1])
    except: pass

    if fname is not None:
        fname_noext = Tk_file.get_filename_no_extension(fname)

        plt.savefig(fname_noext + '.png', dpi=300, bbox_inches="tight")
        if save_svg:
            plt.savefig(fname_noext + '.svg', dpi=300, bbox_inches="tight")

##### Scripts #####

if __name__ == '__main__':

    logging.basicConfig()
    activate_loggers([__name__], level=logging.DEBUG)

    # global plotting params
    from matplotlib import rc
    # font in text mode
    rc('font',**{'family':'sans-serif','sans-serif':['Helvetica'], 'size': 11.5})
    # for inset figures
    rc('font',**{'family':'sans-serif','sans-serif':['Helvetica'], 'size': 7})
    # font in math mode: computer modern
    plt.rcParams["mathtext.fontset"] = "cm"



    # drawing a lot of points...
    plt.rcParams['agg.path.chunksize'] = 10000

    #rc('text', usetex=True) # use external miktex renderer
    #rc('text.latex', preamble=','.join(r'\usepackage{txfonts}\usepackage{lmodern}'.split()))

    save_svg = False
    disable_legend = False
    # for puplicattions
    figsize_cm = [8.6, 3/4*8.6]                 # single fig
    #figsize_cm = [1/2*8.6, 1/2*3/4*8.6]        # inset
    #figsize_cm = [1/4*3/4*8.6, 1/4*3/4*8.6]     # quadtatic small inset
    #figsize_cm = [8.6, 4]                      # wide screen
    #overwrite_figsize = np.asarray(figsize_cm)*0.394  # in inches


    # basic plotting of combined mfl data
    #"""
    path = r"E:/Data/2019/11/20191118/PulsedMeasurement/mfl_n_sweeps=200_longT_2/combine"
    path = r"E:/Data/2019/11/20191119/PulsedMeasurement/combine"
    path = r"E:/Data/2020/01/20200124/PulsedMeasurement/na_g_f_vary_2/g=4_f=3/combine"
    #path = "E:/Data/2019/11/20191104/PulsedMeasurement/_2d_mfl_M6.3/combine"


    #paths = [r"E:\Data\2019\11\20191104\PulsedMeasurement\_2d_mfl_M6.3\combine",]
    paths = [r"E:\Data\2020\10\20201007\PulsedMeasurement\combine"]

    rolling_windows = '100ms'
    rolling_windows = '1000ms'  # only [ms] allowed!
    # rolling_windows = 1

    for path in paths:
        path = path.replace("\\","/")

        mes_list, mes_list_fail, mes_list_all = load_from_dir(path, load_fails=True, excl_params=[])
        #mes_list, mes_list_fail, mes_list_all = load_from_dir(path, excl_params=['priors','likelihoods'], load_fails=True)

        # SINGLE MES
        #####################

        #"""
        fit_params = {'lifetime':{'value': 10e-6, 'min': 5e-6, 'max': 20e-6},
                        'frequency': {'value': 400e3, 'min': 550e3, 'max': 800e3},
                        'amplitude': {'value': 0.015, 'min': 0.005}}
        #plot_fit_params_vs_tphase_single_taus_at_once(mes_list[0], savepath=path + '/' + 'fit_params_vs_t_phase_single_taus.png',
        #                                              fit_params=fit_params)
        #plot_fit_params_vs_tphase(mes_list[0], savepath=path + '/' + 'fit_params_vs_t_phase_2.png', fit_params=fit_params,
        #                          aggregate_data_factor=4, omit_epoch_factor=1)
        #plot_fit_params_vs_tphase(mes_list[0], savepath=path + '/' + 'fit_params_vs_t_phase_2.png', fit_params=fit_params,
        #                          aggregate_data_factor=4, omit_epoch_factor=4)
        #continue
        """
        # priors
        idx_epoch_plots = np.arange(0,500,4)
        #plot_prior_2d(mes_list[0], epochs_idx=[0], n_bins=50, savepath=path + '/' + 'priors_0.png', tick_label_digits=1)
        plot_prior_2d(mes_list[1], epochs_idx=[500], n_bins=50, savepath=path + '/' + 'priors_500.png')
        #plot_prior_2d(mes_list[0], epochs_idx=idx_epoch_plots, savepath=path + '/' + 'prior.png', n_bins=50,
        #             )

        plot_likelihood_2d(mes_list[0], epochs_idx=idx_epoch_plots, savepath=path + '/' + 'likelihoods.png')
        #plot_likelihood_2d(mes_list[0], epochs_idx=idx_epoch_plots, savepath=path + '/' + 'likelihoods.png',
        #                    omega_mhz=[omega_1, omega_1])

        # paper
        omega_1 = np.linspace(0, 5, 100)
        plot_likelihood_2d(mes_list[0], epochs_idx=[16], savepath=path + '/' + 'likelihoods_0.png',
                            omega_mhz=[omega_1, omega_1], tick_label_digits=1)
        omega_1 = np.linspace(0.536, 0.568, 100)
        omega_2 = np.linspace(0.603, 0.633, 100)
        plot_likelihood_2d(mes_list[0], epochs_idx=[496], savepath=path + '/' + 'likelihoods_500.png',
                           omega_mhz=[omega_1, omega_2], tick_label_digits=3)
        exit(0)
        """
        # overhead times
        plot_overhead_times(mes_list[0], savepath=path + '/' + 'overhead.png')

        # MEDIAN OF MES LIST
        ######################


        # eta and db
        #"""
        plot_eta_vs_t(mes_list, rolling_window=rolling_windows, savepath=path + '/' + 'median_eta.png', eta_mode='all', no_scatter=False)
        plot_eta_vs_t(mes_list, rolling_window=rolling_windows, savepath=path + '/' + 'median_eta.png', eta_mode='phase', no_scatter=False)
        plot_db_vs_t(mes_list, rolling_window=rolling_windows, savepath=path + '/' + 'median_db.png', eta_mode='phase')
        plot_db_vs_t(mes_list, rolling_window=rolling_windows, savepath=path + '/' + 'median_db.png', eta_mode='all')
        plot_db_vs_t(mes_list, rolling_window=rolling_windows, savepath=path + '/' + 'median_db.png', eta_mode='seq')

        plot_db_vs_epochs(mes_list, rolling_window=rolling_windows, savepath=path + '/' + 'median_db_epoch.png', eta_mode='phase')

        #"""
        # b
        plot_b_hist(mes_list_all, savepath=path + '/' + 'B_hist.png')
        #"""
        plot_b_vs_epoch(mes_list, savepath=path + '/' + 'B_vs_epochs.png', is_unit_ut=False)
        plot_b_vs_runs(mes_list, savepath=path + '/' + 'B_vs_runs.png', taxis=False)
        plot_b_vs_runs(mes_list, savepath=path + '/' + 'B_vs_t_run.png', taxis=True)


        #plot_eta_vs_B(mes_list, savepath=path + '/' + 'eta_vs_B.png')
        #"""

        # taus
        #plot_hist_taus(mes_list, savepath=path + '/' + 'hist_taus.png')


        # File handling & batch processing
        ###############################
        """
        path = "E:/Data/2019/09/20190913/PulsedMeasurement/combine"
        path = "E:/Data/2019/09/20190913/"
        move_mes_pngs(path, "eta_calc_corrupted")
        """

        # save pkl data to csv
        """
        import pandas
        mes_list = load_mult_mes(path, filter_str='.pkl', excl_filter_str=['excl'])
        for mes, fname in mes_list:
            if "median_" in fname or "fit_params" in fname:
                path_save = fname.replace("pkl", "csv")
                mes = Tk_file.load_pickle(fname)
                mes_table = pandas.DataFrame(mes)
                mes_table.to_csv(path_save, sep=';', encoding='utf-8', float_format="%E", decimal=",")
        """



        #plot_median_fit_params(path, 'fit_params_vs_t_phase_single_taus.pkl', rolling_window=rolling_windows, savepath=path + "/" + 'median_fit_params.pkl')

    print("Done.")