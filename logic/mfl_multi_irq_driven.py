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
GAMMA_NV_MHZ_GAUSS = 2.8e6  # Hz per Gauss

class MFL_Multi_IRQ_Driven(MFL_IRQ_Driven):

    _modclass = 'mfl_mulri_irq_driven'
    _modtype = 'logic'

    # this class requires a NI X Series counter
    counter = Connector(interface='SlowCounterInterface')
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')

    _epoch_done_trig_ch = StatusVar('_epoch_done_trig_ch', 'dev1/port0/line0')

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.n_est_ws = 2

    def on_activate(self, logger_override=None, force_no_qudi=False):
        super().on_activate(logger_override=logger_override, force_no_qudi=True)

    def init_mfl_algo(self, t2star_s=None, freq_max_mhz=10, resample_a=0.98, resample_thresh=0.5, eta_assym=1):
        n_particles = 2000
        freq_min = 0
        freq_max = 2 * np.pi * freq_max_mhz  # MHz rad
        # the expected T2, when 0 this is the ideal case
        if t2star_s is None:
            inv_T2 = 0
        else:
            inv_T2 = 1./(t2star_s * 1e6)
            self.log.debug("t2= {} us, inv_t2= {} MHz".format(t2star_s*1e6, inv_T2))

        # to save for dumping
        self.mfl_frq_min_mhz = 0
        self.mfl_frq_max_mhz = freq_max_mhz
        self.mfl_t2star_s = t2star_s
        self.mfl_resample_a = resample_a
        self.mfl_resample_thresh = resample_thresh
        self.mfl_eta_assym = eta_assym
        if eta_assym != 1.0:
            raise NotImplementedError("eta_assym currently only in 1d mfl")


        self.mfl_prior = qi.UniformDistribution(np.asarray([[freq_min, freq_max],[freq_min, freq_max]]))

        if t2star_s is not None:
            self.mfl_model = mfl_lib.ExpDecoKnownMultimodePrecModel(min_freq=0, inv_T2=inv_T2)
        else:
            self.mfl_model = mfl_lib.MultimodePrecModel(min_freq=0)

        self.mfl_updater = qi.SMCUpdater(self.mfl_model, n_particles, self.mfl_prior)
        self.mfl_updater.reset()

        if t2star_s is not None:
            self.mfl_tau_from_heuristic = mfl_lib.T2RandPenalty_MultiPGH(self.mfl_updater, tau_thresh_rescale=t2star_s/4, scale_f=4, inv_field=['w1','w2'])
        else:
            self.mfl_tau_from_heuristic = mfl_lib.MultiPGH(self.mfl_updater, inv_field=['w1','w2'])



    def init_arrays(self, n_epochs):

        if n_epochs == -1:
            n_epochs = ARRAY_SIZE_MAX
            self.log.warning("Setting array length for infinite epochs to {}".format(n_epochs))
        if n_epochs > ARRAY_SIZE_MAX:
            n_epochs = ARRAY_SIZE_MAX
            self.log.warning("Setting array length for too many epochs to {}".format(n_epochs))

        self.timestamps = np.zeros((2*n_epochs, 4))
        self._idx_timestamps = 0
        # first estimate from flat prior stored in self.data_before_first_epcoh
        self.taus = np.zeros((n_epochs, 1))
        self.taus_requested = np.zeros((n_epochs, 1))
        self.t_seqs = np.zeros((n_epochs, 1))
        self.bs = np.zeros((n_epochs,  self.n_est_ws))  # MHz
        self.dbs = np.zeros((n_epochs,  self.n_est_ws))
        self.dbs_cov = np.array([np.zeros((2,2), dtype=float)] *n_epochs, dtype=object) # elements are 2x2 ndarrays
        self.zs = np.zeros((n_epochs, 1))
        self.priors = []

    def save_estimates_before_first_run(self, tau_first_real, tau_first_req, t_first_seq=None):

        # taus needed for first epoch
        self.taus_requested[0] = tau_first_req
        self.taus[0] = tau_first_real
        if t_first_seq is None:
            self.t_seqs[0] = 0   # this is not correct, but might be unknown at time of setup
        else:
            self.t_seqs[0] = t_first_seq

        b_mhz_rad = self.mfl_updater.est_mean()  # [b1, b2]
        b_mhz_0 = b_mhz_rad / (2*np.pi)
        db_mhz_rad = np.sqrt(self.mfl_updater.est_covariance_mtx())  # 2x2 matrix
        db_mhz_0 = db_mhz_rad / (2*np.pi)

        self.data_before_first_epoch = {'b_1_mhz': b_mhz_0[0], 'db_1_mhz': db_mhz_0[0][0],
                                        'b_2_mhz': b_mhz_0[1], 'db_2_mhz': db_mhz_0[1][1]}

    def update_mfl(self, z_bin):
        # update posterior = prior * likelihood
        last_tau = self.taus[self.i_epoch, 0]  # get tau of experiment
        tau_and_x = self.get_tau_and_x(last_tau)
        try:
            self.mfl_updater.update(z_bin, tau_and_x)  # updates prior
        except RuntimeError as e:
            self.log.error("Updating mfl failed in epoch {}: {}".format(self.i_epoch, str(e)))

        self.prior_erase_beyond_sampling()
        # for 2d estimation
        self.prior_erase_mirrored()


    def prior_erase_mirrored(self):
        # particles = [updater.particle_locations, updater.particle_weights]
        # by definition w2 > w1
        self.mfl_updater.particle_weights[self.mfl_updater.particle_locations[:, 1] < self.mfl_updater.particle_locations[:, 0]] = 0


if __name__ == '__main__':
    from logic.user_logic import UserCommands as ucmd
    import logging
    import PyDAQmx as daq
    import os

    os.chdir('../')
    print("Running mfl_multi_irq_diven.py. Working dir: {}".format(os.getcwd()))

    logging.basicConfig(level=logging.DEBUG)
    #logging.basicConfig(filename='logfile.log', filemode='w', level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    mfl_logic = MFL_Multi_IRQ_Driven(None, no_super=True)
    mfl_logic.on_activate(logger_override=logger)

    def profile_mfl_pj(n_epochs=1000):
        """start this function with profiler
           Must connect PFI9 to IRQ input!
        """

        n_sweeps = 10e3
        z_thresh = 0.0

        mfl_logic.init('mfl_ramsey_pjump', n_sweeps, n_epochs=n_epochs, nolog_callback=True, z_thresh=z_thresh)

        mfl_logic.save_priors = False

        for i in range(0, n_epochs):
            mfl_logic._cb_func_profile_algo_only(None, None, None)

        # using IRQ logic, not possible to profile atm
        """
        mfl_logic.setup_new_run_no_qudi()

        # send first interrupt
        ucmd.send_ttl_pulse(None, channel_name='/dev1/PFI9')

        timeout_cyc = 10000
        i_wait = 0
        while mfl_logic.is_running and i_wait < timeout_cyc:
            time.sleep(0.1)
            i_wait += 1

        print("Run MFL {} / {} epochs".format(mfl_logic.i_epoch, mfl_logic.n_epochs))

        # should end itself, but if user abort:
        mfl_logic.end_run()
        """

    def profile_fastcounter_pull_data(n_reps=1e3):
        mfl_logic.i_epoch = 0
        mfl_logic.n_epochs = 1
        mfl_logic.n_sweeps = 1

        for i in range(0, int(n_reps)):
            _, z = mfl_logic._pull_data_methods['ungated_sum_up_cts']()

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

    def setup_multi_mfl_seperate_thread(n_sweeps, n_epochs, z_thresh, t2star_s=None, calibmode_lintau=False, freq_max_mhz=10
                                  , meta_dict=None, nowait_callback=False):

        nolog = not calibmode_lintau

        mfl_logic.init('mfl_ramsey_pjump', n_sweeps, n_epochs=n_epochs, nolog_callback=nolog, z_thresh=z_thresh,
                       calibmode_lintau=calibmode_lintau, nowait_callback=nowait_callback)
        mfl_logic.meta_dict = meta_dict

        mfl_logic.save_priors = True     # OK if callback slow
        tau_first_req = mfl_logic.get_first_tau()
        # can pull here, since waiting for lock makes sure that seqtable is available as temp file
        mfl_logic.pull_jumptable(seqname=mfl_logic.sequence_name, load_vars_metafile=mfl_logic.qudi_vars_metafile)

        idx_jumptable_first, _ = mfl_logic.find_nearest_tau(tau_first_req)
        tau_first, t_seq_first = mfl_logic.get_ts(idx_jumptable_first)
        # shortest tau mfl algo may choose, problem: shorter than tau_first causes rounding issues

        logger.info("Setting up multi mfl started at {}. n_sweeps= {}, n_epochs={}, z_thresh={}, t2star= {} us. First tau from flat prior {} ns, freq_max= {} Mhz, Meta: {}".format(
                meta['t_start'], n_sweeps, n_epochs, z_thresh, t2star_s*1e6 if t2star_s is not None else None, 1e9*tau_first, freq_max_mhz, meta_dict))

        mfl_logic.setup_new_run(tau_first, tau_first_req, t_first_seq=t_seq_first, t2star_s=t2star_s, freq_max_mhz=freq_max_mhz)

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

    logger.info("Setting up multi mfl irq driven in own thread.")
    logger.info("Waiting for new mes params. Now start mfl from qudi/jupyter notebook.")
    wait_for_correct_metafile(mfl_logic.qudi_vars_metafile)
    params, _, meta = import_mfl_params(mfl_logic.qudi_vars_metafile)

    setup_multi_mfl_seperate_thread(n_epochs=params['n_epochs'], n_sweeps=params['n_sweeps'], z_thresh=params['z_thresh'],
                              t2star_s=params['t2star'], calibmode_lintau=params['calibmode_lintau'],
                              freq_max_mhz=params['freq_max_mhz'], meta_dict=meta, nowait_callback=params['nowait_callback'])
    join_mfl_seperate_thread()

    exit(0)

    """
    Test counting with ni counter
    """
    def setup_ni_counter():
        mfl_logic.nicard.set_up_single_edge_counter('dev1/ctr1')    # PFI 3 on breakout

