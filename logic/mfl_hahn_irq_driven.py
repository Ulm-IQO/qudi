from logic.mfl_irq_driven import MFL_IRQ_Driven
from core.module import Connector, StatusVar, Base

import numpy as np
import time
import pickle
import qinfer as qi

import imp
qudi_dir = 'C:/Users/Setup3-PC/Desktop/qudi/'
path_mfl_lib = qudi_dir + '/jupyter/Timo/own/mfl_sensing_simplelib.py'
if __name__ == '__main__':  # for debugging
    path_mfl_lib = '../jupyter/Timo/own/mfl_sensing_simplelib.py'

mfl_lib = imp.load_source('packages', path_mfl_lib)

ARRAY_SIZE_MAX = 5000
GAMMA_NV_HZ_GAUSS = 2.8e6  # Hz per Gauss
GAMMA_C_HZ_GAUSS = 1.07084e3

class MFL_Hahn_IRQ_Driven(MFL_IRQ_Driven):

    _modclass = 'mfl_hahn_irq_driven'
    _modtype = 'logic'

    # this class requires a NI X Series counter
    counter = Connector(interface='SlowCounterInterface')
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')

    _epoch_done_trig_ch = StatusVar('_epoch_done_trig_ch', 'dev1/port0/line0')

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)

    def on_activate(self, logger_override=None, force_no_qudi=False):
        super().on_activate(logger_override=logger_override, force_no_qudi=True)

    def init_mfl_algo(self, **kwargs):

        # for dummy init, default values must be set
        b0_gauss = kwargs.get('b0_gauss', 10)   # default needs to be a reasonable value, as used in first_tau
        freq_max_mhz = kwargs.get('freq_max_mhz', 10)
        phi_max = kwargs.get('phi_max', np.pi)
        c_scale_2 = kwargs.get('c_scale', 1)
        resample_a = kwargs.get('resample_a', 0.98)
        resample_thresh = kwargs.get('resample_thresh', 0.5)
        a_parallel_mhz = kwargs.get('a_parallel_mhz', -1)
        t2 = kwargs.get('t2_s', 1)

        n_particles = 1000
        freq_min = 2 * np.pi * a_parallel_mhz  # for AparrKnown model
        freq_min = 0        # for BKnown model
        freq_max = 2 * np.pi * freq_max_mhz  # MHz rad
        if freq_max <= freq_min:
            self.log.warning("Mfl prior freq_max= {} MHz rad <= freq_min= {} MHz rad".format(
                freq_max, freq_min
            ))

        # to save for dumping
        self.mfl_n_particles = n_particles
        self.mfl_frq_min_mhz = 0
        self.mfl_frq_max_mhz = freq_max_mhz
        self.mfl_t2_s = t2
        self.mfl_resample_a = resample_a
        self.mfl_resample_thresh = resample_thresh
        self.mfl_b0_gauss = b0_gauss
        self.mfl_phi_max = phi_max
        self.mfl_c_scale_2 = c_scale_2
        self.mfl_a_parallel_mhz = a_parallel_mhz

        self.mfl_prior = qi.UniformDistribution([freq_min, freq_max])

        # ATTENTION: search for Aparr in this file beofre activating again!
        #self.mfl_model = mfl_lib.AparrKnownHahnModel(b0_gauss, 1e6* 2*np.pi * a_parallel_mhz,
        #                                             min_freq=2*np.pi * a_parallel_mhz, c_scale_2=c_scale_2)

        self.mfl_model = mfl_lib.BKnownHahnModel(b0_gauss, min_freq=0, c_scale_2=c_scale_2)

        self.mfl_updater = mfl_lib.basic_SMCUpdater(self.mfl_model, n_particles, self.mfl_prior,
                                                    resample_a=resample_a, resample_thresh=resample_thresh)
        self.mfl_updater.reset()
        #self.mfl_tau_from_heuristic = mfl_lib.T2_Thresh_MultiHahnPGH(self.mfl_updater, b0_gauss,
        #                                                             inv_field=['w_'], tau_thresh_us=t2*1e6)
        self.mfl_tau_from_heuristic = mfl_lib.T2RandPenalty_MultiHahnPGH(self.mfl_updater, b0_gauss,
                                                                         tau_thresh_rescale=t2 / 4, scale_f=4,
                                                                         inv_field=['w_'])

    def update_mfl(self, z_bin):
        # update posterior = prior * likelihood
        last_tau = self.taus[self.i_epoch, 0]  # get tau of experiment
        tau_and_x = self.get_tau_and_x(last_tau)
        try:
            self.mfl_updater.update(z_bin, tau_and_x)  # updates prior
        except RuntimeError as e:
            self.log.error("Updating mfl failed in epoch {}: {}".format(self.i_epoch, str(e)))

        #self.prior_erase_f1()

    def prior_erase_f1(self):
        # particles = [updater.particle_locations, updater.particle_weights]

        f1 = self.mfl_b0_gauss * GAMMA_C_HZ_GAUSS

        df = 10e3

        if self.n_est_ws == 1:
            self.mfl_updater.particle_weights[
                 np.logical_and(1e-6 * 2*np.pi* (f1 - df) < self.mfl_updater.particle_locations[:,0],
                                self.mfl_updater.particle_locations[:,0] < 1e-6 * 2*np.pi* (f1 + df))] = 0
        else:
            raise NotImplementedError

if __name__ == '__main__':
    from logic.user_logic import UserCommands as ucmd
    import logging
    import PyDAQmx as daq
    import os

    os.chdir('../')
    print("Running mfl_hahn_irq_diven.py. Working dir: {}".format(os.getcwd()))

    logging.basicConfig(level=logging.DEBUG)
    #logging.basicConfig(filename='logfile.log', filemode='w', level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    mfl_logic = MFL_Hahn_IRQ_Driven(None, no_super=True)
    mfl_logic.on_activate(logger_override=logger)

    def import_mfl_params(meta_filename):
        with open(meta_filename, 'rb') as file:
            meta = pickle.load(file)

        params = meta['mfl_params']
        t_start_str = meta['t_start']
        lock = meta['lock_file']

        return params, lock, meta

    def lockfile_aquire(filename, timeout_s=0):
        """
        Lockfile is deleted aa soon as mes starts.
        -> Don't start mes from old meta file.
        :param filename:
        :param timeout_s: 0: return immediately, -1: wait infinitely
        :return:
        """
        t_start = time.time()
        timeout = False
        success = False

        while not timeout and not success:

            try:
                with open(filename, 'rb') as file:
                    lock = pickle.load(file)
                success = True
                logger.info("Successfully acquired lock {}".format(filename))
                break
            except Exception as e:
                success = False

            t_now = time.time()
            if t_now - t_start > timeout_s:
                if not timeout_s < 0:
                    timeout = True

        if success:
            os.remove(filename)

        return success

    def wait_for_correct_metafile(meta_filename, timeout_s=-1):
        """
        Continously load metafile. Could be old, not belonging to current mes.
        So wait until correct lock to be obtained.
        """
        t_start = time.perf_counter()
        timeout = False
        success = False

        while not timeout and not success:
            t_now = time.perf_counter()
            if t_now - t_start > timeout_s:
                if not timeout_s < 0:
                    timeout = True

            _, lock, _ = import_mfl_params(meta_filename)
            success = lockfile_aquire(lock, 1)

        time.sleep(0.1)     # wait until all files are written

        return success

    def setup_mfl_seperate_thread(n_sweeps, n_epochs, z_thresh, t2_s=None, calibmode_lintau=False, meta_dict=None, nowait_callback=False,
                                  freq_max_mhz=10, phi_max=np.pi, a_parallel_mhz=None, c_scale=1, b0_gauss=None):

        nolog = not calibmode_lintau

        mfl_logic.init('mfl_hahn_pjump', n_sweeps, n_epochs=n_epochs, nolog_callback=nolog, z_thresh=z_thresh,
                       calibmode_lintau=calibmode_lintau, nowait_callback=nowait_callback)
        mfl_logic.meta_dict = meta_dict

        mfl_logic.save_priors = True     # OK if callback slow
        tau_first_req = mfl_logic.get_first_tau()
        # can pull here, since waiting for lock makes sure that seqtable is available as temp file
        mfl_logic.pull_jumptable(seqname=mfl_logic.sequence_name, step_name='mfl_hahn_pjump',
                                 load_vars_metafile=mfl_logic.qudi_vars_metafile)

        idx_jumptable_first, _ = mfl_logic.find_nearest_tau(tau_first_req)
        tau_first, t_seq_first = mfl_logic.get_ts(idx_jumptable_first)
        # shortest tau mfl algo may choose, problem: shorter than tau_first causes rounding issues

        logger.info("Setting up mfl started at {}. n_sweeps= {}, n_epochs={}, z_thresh={}, t2 {} us. First tau from flat prior {} ns, freq_max= {} Mhz, Meta: {}".format(
                meta['t_start'], n_sweeps, n_epochs, z_thresh, t2_s*1e6 if t2_s is not None else None,
                1e9*tau_first, freq_max_mhz, meta_dict))

        mfl_logic.setup_new_run(tau_first, tau_first_req, t_first_seq=t_seq_first, t2_s=t2_s,
                                freq_max_mhz=freq_max_mhz, phi_max=phi_max, a_parallel_mhz=a_parallel_mhz,
                                c_scale=c_scale, b0_gauss=b0_gauss)

        if mfl_logic._cur_pull_data_method is 'gated_2d':
            mfl_logic.fastcounter.change_sweep_mode(gated=True, is_single_sweeps=False,
                                                    n_sweeps_preset=int(n_sweeps))


    def _wait_for_start():
        # here: callback must be installed,
        # -> ready to react on mes run by qudi / from jupyter notebook

        mfl_logic.wait_for_start_lock.acquire()
        logger.info("Waiting for mes to start...")
        # will be released in first IRQ callback invocation
        mfl_logic.wait_for_start_lock.acquire()

        logger.info("Started. Waiting for all epochs done...")
        # will be released in end_run()
        mfl_logic.is_running_lock.acquire()
        mfl_logic.is_running_lock.release()  # needed? also released in end_run()

    def join_mfl_seperate_thread():
        # prio of this thread
        prio = 5    # 2: normal 5: real time
        prio_new = mfl_logic._setpriority_win(pid=None, priority=prio)
        if prio != prio_new:
            logger.warning("Couldn't set process priority to {} (is {}). Run as admin?".format(prio, prio_new))

        _wait_for_start()
        logger.info("MFL thread done")


    """
    Run in sepearte thread
    """
    #"""
    logger.info("Setting up mfl hahn irq driven in own thread.")
    logger.info("Waiting for new mes params. Now start mfl from qudi/jupyter notebook.")
    wait_for_correct_metafile(mfl_logic.qudi_vars_metafile)
    params, _, meta = import_mfl_params(mfl_logic.qudi_vars_metafile)
    # DEBUG
    #params = {'n_epochs':1, 'n_sweeps':2, 'z_thresh':0.1, 't2star':1e-6, 'calibmode_lintau': False,
    #          'freq_max_mhz': 1, 'eta_assym': 0, 'nowait_callback': False}
    #meta = {'t_start':0}

    setup_mfl_seperate_thread(n_epochs=params['n_epochs'], n_sweeps=params['n_sweeps'], z_thresh=params['z_thresh'],
                              t2_s=params['t2'], calibmode_lintau=params['calibmode_lintau'],
                              meta_dict=meta, nowait_callback=params['nowait_callback'],
                              freq_max_mhz=params['freq_max_mhz'], phi_max=params['phi_max'],
                              a_parallel_mhz=params['a_parallel_mhz'], c_scale=params['c_scale'],
                              b0_gauss=params['b0_gauss']
                              )
    join_mfl_seperate_thread()

    exit(0)

