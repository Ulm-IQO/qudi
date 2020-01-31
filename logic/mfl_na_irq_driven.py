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

class MFL_NonAdapt_IRQ_Driven(MFL_IRQ_Driven):

    _modclass = 'mfl_nonadapt_irq_driven'
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
        t2star_s = kwargs.get('t2star_s', None)
        freq_max_mhz = kwargs.get('freq_max_mhz', 10)
        eta_assym = kwargs.get('eta_assym', 1)
        resample_a = kwargs.get('resample_a', 0.98)
        resample_thresh = kwargs.get('resample_thresh', 0.5)
        mfl_na_g = kwargs.get('na_g', 1)
        mfl_na_f = kwargs.get('na_f', 0)
        mfl_n_taus = kwargs.get('na_n_taus', 10)
        mfl_opt_phase = kwargs.get('na_opt_phase', False)
        mfl_na_tau_short_to_long = kwargs.get('tau_short_to_long', True)

        n_particles = 1000
        freq_min = 0        # for BKnown model
        freq_max = 2 * np.pi * freq_max_mhz  # MHz rad
        # the expected T2, when 0 this is the ideal case
        if t2star_s is None:
            inv_T2 = 0
        else:
            inv_T2 = 1. / (t2star_s * 1e6)
            self.log.debug("t2= {} us, inv_t2= {} MHz".format(t2star_s * 1e6, inv_T2))

        # to save for dumping
        self.mfl_n_particles = n_particles
        self.mfl_frq_min_mhz = 0
        self.mfl_frq_max_mhz = freq_max_mhz
        self.mfl_t2star_s = t2star_s
        self.mfl_resample_a = resample_a
        self.mfl_resample_thresh = resample_thresh
        self.mfl_na_g = mfl_na_g
        self.mfl_na_f = mfl_na_f
        self.mfl_n_taus = mfl_n_taus
        self.mfl_opt_phase = mfl_opt_phase
        self.mfl_na_tau_short_to_long = mfl_na_tau_short_to_long

        # extra counter for non adaptive
        self.m_phase = 0
        self.i_tau = 0

        self.mfl_prior = qi.UniformDistribution([freq_min, freq_max])

        self.mfl_model = mfl_lib.ExpDecoKnownPrecessionModel(min_freq=freq_min, invT2=inv_T2, eta_assym=eta_assym)
        self.mfl_updater = mfl_lib.basic_SMCUpdater(self.mfl_model, n_particles, self.mfl_prior, resample_a=resample_a,
                                                    resample_thresh=resample_thresh)
        self.mfl_updater.reset()

        self.mfl_tau_0 = 1/(2*self.mfl_frq_max_mhz*1e6)   # as in Bonato (2015)
        self.mfl_tau_from_heuristic = mfl_lib.NonAdaptive_PGH(self.mfl_updater, inv_field='w_',
                                                              tau_0=self.mfl_tau_0, n_taus=self.mfl_n_taus,
                                                              fix_readout_phase_rad=0 if not self.mfl_opt_phase else None,
                                                              tau_short_to_long=mfl_na_tau_short_to_long
                                                              )

    def _reset_epoch_counters(self):
        self.i_epoch = 0
        self.m_phase = 0

    def generate_tau_and_phase(self):

        i_epoch_temp = self.i_tau
        m_phase_temp = self.m_phase

        self._reset_epoch_counters()
        tau_list, phase_list = [], []
        for i in range(0, 999):
            # iterate i_tau, m_phase inside _calc_tau_and_phase
            tau_list.append(self._calc_tau_and_phase(hold_phase=True, hold_tau=True)[0])
            phase_list.append(self._calc_tau_and_phase(hold_phase=False, hold_tau=False)[1])
            if self.i_tau >= self.mfl_n_taus:
                break
        if i >= 999:
            self.log.warning("Maximum iterations reached.")

        self.i_tau = i_epoch_temp
        self.m_phase = m_phase_temp

        return tau_list, phase_list

    def calc_tau_from_posterior(self):
        # as calc_phase_from_posterior is always called after, iterate there
        return self._calc_tau_and_phase(hold_phase=True, hold_tau=True)[0]

    def calc_phase_from_posterior(self):
        # called in irq directly after calc_tau_from_posterior
        return self._calc_tau_and_phase()[1]

    def get_should_end_run(self):

        end = False

        if self.i_tau >= self.mfl_n_taus:
            #end = True
            end = False
        if self.i_epoch >= self.n_epochs:
            end = True
            self.log.warning("Ending run by reaching n_epoch= {} limit. "
                             "n_taus= {} might not be reached yet.".format(self.n_epochs, self.mfl_n_taus))

        return end

    def _calc_tau_and_phase(self, hold_tau=False, hold_phase=False):

        if (self.mfl_n_taus - (self.i_tau+1)) < 0:
            # repeat tau when hitting n_tau limit
            i_tau_limited = self.mfl_n_taus - 1
        else:
            i_tau_limited = self.i_tau

        # many phases at short tau
        if not self.mfl_na_tau_short_to_long:
            m_total_phases = self.mfl_na_g + self.mfl_na_f * i_tau_limited
        else:
            m_total_phases = self.mfl_na_g + self.mfl_na_f * (self.mfl_n_taus - (i_tau_limited + 1))
        m_phase = self.m_phase

        next_tau_s, next_phase_rad = self.mfl_tau_from_heuristic(self.i_tau, m_phase,
                                                                m_total_phases)

        # reset if maximum phases per tau reached
        if m_phase + 1 >= m_total_phases:
            if not hold_phase:
                m_phase = 0
            if not hold_tau:
                self.i_tau += 1
        else:
            if not hold_phase:
                m_phase += 1
        self.m_phase = m_phase

        return next_tau_s, next_phase_rad



if __name__ == '__main__':
    from logic.user_logic import UserCommands as ucmd
    import logging
    import PyDAQmx as daq
    import os

    os.chdir('../')
    print("Running mfl_na_irq_diven.py. Working dir: {}".format(os.getcwd()))

    logging.basicConfig(level=logging.DEBUG)
    #logging.basicConfig(filename='logfile.log', filemode='w', level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    mfl_logic = MFL_NonAdapt_IRQ_Driven(None, no_super=True)
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

    def setup_mfl_seperate_thread(n_sweeps, n_epochs, z_thresh, t2star_s=None, calibmode_lintau=False, freq_max_mhz=10,
                                  meta_dict=None, nowait_callback=False, eta_assym=1, na_g=None, na_f=None,
                                  na_n_taus=None, na_opt_phase=None, tau_short_to_long=False):

        nolog = not calibmode_lintau
        #logger.warning("Logger in callback activated for debug")
        #nolog = False

        # dummy init for first tau
        mfl_logic.init('mfl_ramsey_pjump', n_sweeps, n_epochs=n_epochs, nolog_callback=nolog, z_thresh=z_thresh,
                       calibmode_lintau=calibmode_lintau, nowait_callback=nowait_callback)
        mfl_logic.meta_dict = meta_dict

        mfl_logic.save_priors = True     # OK if callback slow
        # todo: in dummy init, this will irgnore any later deployed tau_short_to_long value
        tau_first_req = mfl_logic.get_first_tau()
        # can pull here, since waiting for lock makes sure that seqtable is available as temp file
        mfl_logic.pull_jumptable(seqname=mfl_logic.sequence_name, load_vars_metafile=mfl_logic.qudi_vars_metafile)

        idx_jumptable_first, _ = mfl_logic.find_nearest_tau(tau_first_req)
        tau_first, t_seq_first = mfl_logic.get_ts(idx_jumptable_first)
        # shortest tau mfl algo may choose, problem: shorter than tau_first causes rounding issues

        logger.info("Setting up NA mfl (g={}, f={}) started at {}. n_sweeps= {}, n_epochs={}, z_thresh={}, t2star= {} us. First tau from flat prior {} ns, freq_max= {} Mhz, eta_assym= {}, Meta: {}".format(
                na_g, na_f,
                meta['t_start'], n_sweeps, n_epochs, z_thresh, t2star_s*1e6 if t2star_s is not None else None,
                1e9*tau_first, freq_max_mhz, eta_assym, meta_dict))

        mfl_logic.setup_new_run(tau_first, tau_first_req, t_first_seq=t_seq_first, t2star_s=t2star_s,
                                freq_max_mhz=freq_max_mhz, eta_assym=eta_assym,
                                na_g=na_g, na_f=na_f,
                                na_n_taus=na_n_taus, na_opt_phase=na_opt_phase, tau_short_to_long=tau_short_to_long,
                                )

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

        #print(mfl_logic.generate_tau_and_phase())

        _wait_for_start()
        logger.info("MFL thread done")



    """
    Run in sepearte thread
    """
    #"""
    logger.info("Setting up non-adaptive mfl irq driven in own thread.")
    logger.info("Waiting for new mes params. Now start mfl from qudi/jupyter notebook.")
    wait_for_correct_metafile(mfl_logic.qudi_vars_metafile)
    params, _, meta = import_mfl_params(mfl_logic.qudi_vars_metafile)
    # DEBUG
    #params = {'n_epochs':1, 'n_sweeps':2, 'z_thresh':0.1, 't2star':1e-6, 'calibmode_lintau': False,
    #          'freq_max_mhz': 1, 'eta_assym': 0, 'nowait_callback': False}
    #meta = {'t_start':0}
    try:
        setup_mfl_seperate_thread(n_epochs=params['n_epochs'], n_sweeps=params['n_sweeps'], z_thresh=params['z_thresh'],
                                  t2star_s=params['t2star'], calibmode_lintau=params['calibmode_lintau'],
                                  freq_max_mhz=params['freq_max_mhz'], eta_assym=params['eta_assym'],
                                  na_g=params['na_g'], na_f=params['na_f'],
                                  na_n_taus=params['na_n_taus'], na_opt_phase=params['na_opt_phase'],
                                  meta_dict=meta, nowait_callback=params['nowait_callback'],
                                  tau_short_to_long=params['tau_short_to_long']
                                  )
    except KeyError as e:
        logger.error("Error: {} in params dict {}".format(str(e), params))
    join_mfl_seperate_thread()

    exit(0)

