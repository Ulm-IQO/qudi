from logic.generic_logic import GenericLogic
from core.module import Connector, StatusVar, Base
from threading import Lock
import time
import pickle

import imp
path_mfl_lib = './jupyter/Timo/own/mfl_sensing_simplelib.py'
if __name__ == '__main__':  # for debugging
    path_mfl_lib = '../jupyter/Timo/own/mfl_sensing_simplelib.py'

mfl_lib = imp.load_source('packages', path_mfl_lib)
import qinfer as qi

import line_profiler
profile = line_profiler.LineProfiler()

ARRAY_SIZE_MAX = 100


from enum import IntEnum
class TimestampEvent(IntEnum):
    irq_start = 1
    irq_end = 2

class MFL_IRQ_Driven(GenericLogic):

    _modclass = 'mfl_irq_driven'
    _modtype = 'logic'

    # this class requires a NI X Series counter
    counter = Connector(interface='SlowCounterInterface')
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')

    _epoch_done_trig_ch = StatusVar('_epoch_done_trig_ch', 'dev1/port0/line0')

    def __init__(self, config, **kwargs):
        if not __name__ == '__main__':
            super().__init__(config=config, **kwargs)

        self.sequence_name = None
        self.i_epoch = 0
        self.n_epochs = -1
        self.n_sweeps = None
        self.z_thresh = None    # for majority vote of Ramsey result

        self.nolog_callback = False
        self.save_priors = False
        self.is_running = False
        self.is_running_lock = Lock()       # released when all epochs done
        self.wait_for_start_lock = Lock()
        self.is_calibmode_lintau = False    # calibration mode
        self.is_no_qudi = False             # run in own thread, avoid all calls to qudi

        self.jumptable = None

        # handles to hw
        self.nicard = None
        self.serial = None

        # mfl algo
        self.mfl_tau_from_heuristic = None  # function handle
        self.mfl_updater = None
        self.mfl_prior = None
        self.mfl_model = None

        # arrays (instead of lists for performance) to track results
        self.timestamps = None      # [(i_epoch, timestamp, [s] since epoch 0)]
        self.taus = None
        self.taus_requested = None
        self.bs = None
        self.dbs = None

        # how to get data from fastcounter
        # in ungated mode: normal 1d array with counts
        # in gated mode: 2d array, 2nd axis: epochs
        self._pull_data_methods = {'gated_and_ungated_plogic': self.pull_data_gated_and_ungated_plogic,
                                   'gated_2d': self.pull_data_gated,
                                   'ungated_sum_up_cts': self.pull_data_ungated_sum_up_cts,
                                   'ungated_sum_up_cts_nicard': self.pull_data_ungated_sum_up_cts_nicard}
        self._cur_pull_data_method = 'ungated_sum_up_cts_nicard'
        self.log.info("Setting pull data method to '{}'".format(self._cur_pull_data_method))

    def on_activate(self, logger_override=None):
        """ Initialisation performed during activation of the module.
        """

        from hardware.national_instruments_x_series import NationalInstrumentsXSeries

        if logger_override is not None:
            self.log = logger_override

        if not __name__ == '__main__':
            self.nicard = self.counter()
            self.fastcounter = self.pulsedmasterlogic().pulsedmeasurementlogic().fastcounter()
        else:
            # for debugging and profiling, qudi might not be available
            from hardware.fastcomtec.fastcomtecp7887 import FastComtec

            self.is_no_qudi = True

            try:
                kwarg = {'manager': None, 'name': None}
                config = {'photon_sources': '', 'clock_channel': '', 'counter_channels': '',
                          'scanner_ao_channels': '', 'scanner_voltage_ranges': '', 'scanner_position_ranges': '',
                          'odmr_trigger_channel': '', 'gate_in_channel': ''}
                self.nicard = NationalInstrumentsXSeries(**kwarg, config=config)
                self.nicard.on_activate()
            except Exception as e:
                raise ImportError("Couldn't manually instantiate NI card. Remove inheritance from base. Error: {}".format(str(e)))
            try:
                kwarg = {'manager': None, 'name': None}
                self.fastcounter = FastComtec(None, **kwarg)
                self.fastcounter.on_activate()
            except Exception as e:
                raise ImportError("Couldn't manually instantiate fastcomtec. Error: {}".format(str(e)))

        if not isinstance(self.nicard, NationalInstrumentsXSeries):
            self.log.warning("Config defines not supported counter of type {} for MFL logic, not NI X Series.".format(
                             type(self.nicard)))

        self.serial = PatternJumpAdapter()
        self.serial.init_ni()

    def on_deactivate(self):
        """ """
        self.pulsedmasterlogic().pulsedmeasurementlogic().timer_interval = 1    # s, reset to normal value
        self.serial.stop_ni()
        self.end_run()

    @property
    def log(self):
        """
        Allows to override base logger in case not called from qudi.
        """
        import logging
        return logging.getLogger("{0}.{1}".format(
            self.__module__, self.__class__.__name__))

    @log.setter
    def log(self, logger):
        self.__log = logger

    def dump(self, filename):

        def to_dict(obj):
            mdict = {}
            accept_types = [np.ndarray, str, bool, float, int, list, tuple]
            for key, var in obj.__dict__.items():
                if type(var) in accept_types:
                    mdict[key] = var

            return mdict

        with open(filename, 'wb') as file:
            pickle.dump(to_dict(self), file)

    def init(self, name, n_sweeps, n_epochs=-1, nolog_callback=False, z_thresh=0.5, calibmode_lintau=False):
        self.i_epoch = 0
        self.is_running = False
        self.is_calibmode_lintau = calibmode_lintau
        self.n_epochs = n_epochs
        self.nolog_callback = nolog_callback
        self.sequence_name = name
        self.n_sweeps = n_sweeps
        self.z_thresh = z_thresh

        self.init_arrays(self.n_epochs)
        self.init_mfl_algo()

    def setup_new_run(self, tau_first, tau_first_req, cb_epoch_done=None):

        # Attention: may not run smoothly in debug mode

        if cb_epoch_done is None:
            cb_epoch_done = self.__cb_func_epoch_done

        # reset probability distris
        self.init_mfl_algo()

        self.nicard.register_callback_on_change_detection(self.get_epoch_done_trig_ch(),
                                                          cb_epoch_done, edges=[True, False])

        if self._cur_pull_data_method is 'ungated_sum_up_cts_nicard':
            self.nicard.set_up_single_edge_counter('dev1/ctr1')

        self.save_estimates_before_first_run(tau_first, tau_first_req)

        if not self.is_no_qudi:
            mes = self.pulsedmasterlogic().pulsedmeasurementlogic()
            mes.timer_interval = 100  # basically disable analysis loop, pull manually instead

    #@deprecated
    def setup_new_run_no_qudi(self):
        self.init_mfl_algo()

        # run without qudi, so StatusVar not available
        self.nicard.register_callback_on_change_detection('dev1/port0/line0',
                                                          self.__cb_func_profile_algo_only, edges=[True, False])
        self.save_estimates_before_first_run(100e-9, 101e-9)



    def init_arrays(self, n_epochs):

        if n_epochs == -1:
            n_epochs = ARRAY_SIZE_MAX
            self.log.warning("Setting array length for infinite epochs to {}".format(n_epochs))

        self.timestamps = np.zeros((2*n_epochs, 4))
        self._idx_timestamps = 0
        # first estimate from flat prior is also in array
        self.taus = np.zeros((n_epochs + 1, 1))
        self.taus_requested = np.zeros((n_epochs + 1, 1))
        self.t_seqs = np.zeros((n_epochs + 1, 1))
        self.bs = np.zeros((n_epochs + 1, 1))   # MHz
        self.dbs = np.zeros((n_epochs + 1, 1))
        self.zs = np.zeros((n_epochs + 1, 1))
        self.priors = []


    def init_mfl_algo(self):
        n_particles = 1000
        freq_min = 0
        freq_max = 2 * np.pi * 10  # MHz
        # the expected T2, when 0 this is the ideal case
        inv_T2 = 0

        self.mfl_prior = qi.UniformDistribution([freq_min, freq_max])
        self.mfl_model = mfl_lib.ExpDecoKnownPrecessionModel(min_freq=freq_min, invT2=inv_T2)

        # resetting updater&heuristic for ease of multiple calls to this cell
        self.mfl_updater = mfl_lib.basic_SMCUpdater(self.mfl_model, n_particles, self.mfl_prior, resample_a=0.98, resample_thresh=0.5)
        self.mfl_updater.reset()
        self.mfl_tau_from_heuristic = mfl_lib.stdPGH(self.mfl_updater, inv_field='w_')

    def get_epoch_done_trig_ch(self):
        # qudi StatusVar is not available if not run as a qudi module
        if self.is_no_qudi:
            return 'dev1/port0/line0'       # todo: avoid hard coding
        else:
            return self._epoch_done_trig_ch

    def set_jumptable(self, jumptable_dict, tau_list, t_seqs_list):
        """
        self.jumptable format:
        {'name': [], 'idx_seqtable': [], 'jump_address': [], 'tau': [], 't_seq': []}
        """

        jumptable_dict['tau'] = tau_list            # interaction time
        jumptable_dict['t_seq'] = t_seqs_list      # the length of the sequence on the AWG

        self.jumptable = jumptable_dict

    def load_qudi_vars_for_jumptable(self, meta_file):
        """
        Corresponding variable names are defined in jupyter notebook.
        :param meta_file:
        :return:
        """
        loaded_dict = {}

        with open(meta_file, 'rb') as file:
            meta_file = pickle.load(file)

        filenames_dict = meta_file['files']
        vars = [key for key, el in filenames_dict.items()]

        for var_name in vars:

            filename = filenames_dict[var_name]
            with open(filename, 'rb') as file:
                loaded_dict[var_name] = pickle.load(file)

        self.log.debug("Loaded qudi vars from {}: {}".format(filenames_dict, loaded_dict.keys()))

        return loaded_dict

    def pull_jumptable(self, seqname, step_name='mfl_ramsey_pjump', jumpseq_name='laser_wait_0', load_vars_metafile=None):
        """
        :param seqname: name of the whole sequence in pulser
        :param step_name: common string of all seq elements.
        :param jumpseq_name: common string of all seq elements that can be jumped to.
                             Every jumpseq element belongs to a single sequence step
                             which is typically played right after the jumpseq element.
        :return:
        """
        if load_vars_metafile is None:
            seq = self.pulsedmasterlogic().sequencegeneratorlogic().saved_pulse_sequences[seqname]
            ens = {key: val for key, val in self.pulsedmasterlogic().sequencegeneratorlogic().saved_pulse_block_ensembles.items() if
                 step_name in key}
            pg_settting = self.pulsedmasterlogic().pulse_generator_settings
        else:
            loaded_qudi_vars = self.load_qudi_vars_for_jumptable(load_vars_metafile)
            seq = loaded_qudi_vars['pulse_sequence']
            ens = loaded_qudi_vars['pulse_ensembles']
            pg_settting = loaded_qudi_vars['pulse_generator_settings']

        taus = seq.measurement_information['controlled_variable_virtual']   # needs to be added in generation method
        t_seqs = self.pull_t_seq_list(ens, seq.ensemble_list, pg_settting)

        # get all sequence steps that correspond to a tau
        seqsteps = [(i, el) for (i, el) in enumerate(seq.ensemble_list) if jumpseq_name in el['ensemble']]

        if len(taus) != len(seqsteps) or len(taus) != len(t_seqs):
            self.log.error("Couldn't pull jump address table.")
            return

        # prepare output
        jumptable = {'name': [], 'jump_address': [], 'idx_seqtable': []}
        jumptable['name'] = [el['ensemble'] for (i, el) in seqsteps]
        jumptable['jump_address'] = [el['pattern_jump_address'] for (i, el) in seqsteps]
        jumptable['idx_seqtable'] = [i for (i, el) in seqsteps]

        self.set_jumptable(jumptable, taus, t_seqs)

    def pull_t_seq_list(self, ens_dict_all, active_ensembles, pulse_generator_settings):
        """
        Gets a list of all sequences lengths of block ensembles that share the given step name.
        :param step_name:  common string of all seq elements
        :return:
        """

        sample_rate = pulse_generator_settings['sample_rate']

        # ensembles in the active sequence of the AWG
        active_steps = [el.ensemble for el in active_ensembles]

        t_seq_list = []
        for key, ensemble in ens_dict_all.items():
            if key in active_steps:
                t_seq_list.append(ensemble.sampling_information['number_of_samples'] / sample_rate)

        return t_seq_list

    def _get_ensemble_count_length(self, ensemble, created_blocks):
        """

        @param ensemble:
        @param created_blocks:
        @return:
        """

        blocks = {block.name: block for block in created_blocks}
        length = 0.0
        for block_name, reps in ensemble.block_list:
            length += blocks[block_name].init_length_s * (reps + 1)
            length += blocks[block_name].increment_s * ((reps ** 2 + reps) / 2)
        return length


    def get_jump_address(self, idx_epoch):
        adr = self.jumptable['jump_address'][idx_epoch]
        name = self.jumptable['name'][idx_epoch]
        self.log.debug("Resolving jump address {} to segment{} for epooh {}.".format(adr, name, idx_epoch))

        return adr

    def save_estimates_before_first_run(self, tau_first_real, tau_first_req):
        self.taus_requested[0] = tau_first_req
        self.taus[0] = tau_first_real
        self.t_seqs[0] = 0

        b_mhz_rad = self.mfl_updater.est_mean()
        self.bs[0] = b_mhz_rad / (2*np.pi)
        db_mhz_rad = np.sqrt(self.mfl_updater.est_covariance_mtx())
        self.dbs[0] = db_mhz_rad / (2*np.pi)

        if self.save_priors:
            self.priors.append(self.mfl_updater.sample(n=self.mfl_updater.n_particles)/(2*np.pi))

    def save_current_results(self, real_tau_s, requested_tau_s, t_seq_s, z):

        b_mhz_rad = self.mfl_updater.est_mean()[0]
        db_mhz_rad = np.sqrt(self.mfl_updater.est_covariance_mtx()[0,0])
        if self.mfl_updater.est_covariance_mtx().shape != (1,1):
            raise NotImplementedError("Never thought about >1 dimensional estimation, sorry.")

        self.bs[self._arr_idx(self.i_epoch) + 1, 0] = b_mhz_rad / (2 * np.pi)   # MHz
        self.dbs[self._arr_idx(self.i_epoch) + 1, 0] = db_mhz_rad / (2 * np.pi)
        self.taus[self._arr_idx(self.i_epoch) + 1, 0] = real_tau_s
        self.t_seqs[self._arr_idx(self.i_epoch) + 1, 0] = t_seq_s
        self.taus_requested[self._arr_idx(self.i_epoch) + 1, 0] = requested_tau_s
        self.zs[self._arr_idx(self.i_epoch) + 1, 0] = z

        if self.save_priors:
            self.priors.append(self.mfl_updater.sample(n=self.mfl_updater.n_particles) / (2 * np.pi))

    def get_current_results(self):
        b = self.bs[self._arr_idx(self.i_epoch), 0]  # MHz
        db = self.dbs[self._arr_idx(self.i_epoch), 0]
        tau = self.taus[self._arr_idx(self.i_epoch), 0] # s
        tau_req = self.taus_requested[self._arr_idx(self.i_epoch), 0]

        return b, db, tau, tau_req

    def get_first_tau(self):
        """
        calcs from initialized prior a requested first tau
        :return:
        """
        if self.i_epoch == 0 and not self.is_running:
            return self.calc_tau_from_posterior()
        else:
            self.log.error("Can't get first tau if mfl already started.")
            raise RuntimeError("Can't get first tau if mfl already started.")

    def end_run(self):
        self.nicard.register_callback_on_change_detection(self.get_epoch_done_trig_ch(),
                                                          None, edges=[True, False])

        if self.is_running:
            if not self.is_no_qudi:

                self.pulsedmasterlogic().toggle_pulsed_measurement(False)
                time.sleep(0.5)

            if self._cur_pull_data_method is 'ungated_sum_up_cts_nicard':
                cts = self.nicard.get_edge_counters()[0]
                self.nicard.close_edge_counters()
                if self.i_epoch > 0:
                    self.log.info("summed_up_cts from nicard: {} per epoch / {} total from {} epochs".format(
                        float(cts) / self.i_epoch, float(cts), self.i_epoch))

            fastcounter = self.fastcounter
            sweeps_done = fastcounter.get_current_sweeps()
            if sweeps_done != self.i_epoch * self.n_sweeps:
                self.log.warning("Counted {} / {} expected sweeps. Did we miss some?".format(
                            sweeps_done, self.i_epoch * self.n_sweeps))

            # assumes:
            # - that fast counter gets every single sweep by AWG
            # - constant sweeps in every tau
            tau_total = np.sum(self.taus * self.n_sweeps)
            t_seq_total = np.sum(self.t_seqs * self.n_sweeps)

            b, db, tau, tau_req = self.get_current_results()

            # log output
            np.set_printoptions(formatter={'float': '{:0.6f}'.format})
            self.log.info("Ending MFL run at epoch {0}/{1}. B= {3:.2f} +- {4:.2f} MHz. Total tau / t_seq: {2:.3f}, {5:.3f} us."
                            .format(self.i_epoch, self.n_epochs, 1e6*tau_total,
                            b, db, 1e6*t_seq_total))

            timestamps_pretty = []
            delta_list = []
            for i, line in enumerate(self.timestamps):
                # todo: get last irq_start event, instead relying on order (-1)
                is_valid = True
                is_t_end = False
                try:
                    is_t_end = TimestampEvent(int(line[3])) is TimestampEvent.irq_end
                except ValueError:
                    is_valid = False
                if is_valid:
                    if i == 0 or not is_t_end:
                        t_delta = 0
                    else:
                        t_delta = line[2] - self.timestamps[i-1][2]
                        delta_list.append(t_delta)
                    timestamps_pretty.append([int(line[0]), TimestampEvent(int(line[3])).name, line[2], t_delta])

            self.log.info("Timestamps (i_epoch, EventType, t-t0[s], t_irqend - t irqstart[s]): {}".format(timestamps_pretty))
            self.log.info("IRQ Timing: avg: {} +- {} ms from {} events. Deltas: {}".format(
                        np.mean(delta_list)*1e3, np.var(delta_list)*1e3, len(delta_list), (np.asarray(delta_list)*1e3).tolist()))
            self.log.info("In MFL run: taus, taus_requested, delta (ns): {}".format(
                [(1e9*t, 1e9*self.taus_requested[i,0], 1e9*(t-self.taus_requested[i,0])) for (i, t) in enumerate(self.taus[:,0])]))
            self.log.info("In MFL run: B, dB (MHz): {}".format(
                [(b[0], self.dbs[i,0]) for (i, b) in enumerate(self.bs)]))
            np.set_printoptions()

            # save
            self.dump('temp/mfl_mes_result.pkl')
            # save to qudi pulsed mes?

            self.is_running = False
            self.is_running_lock.release()


    def output_jump_pattern(self, jump_address):
        try:
            self.serial.output_data(jump_address)
        except Exception as e:
            self.log.error("Couln't output jump pattern: {}".format(str(e)))

    def iterate_mfl(self):
        self.i_epoch += 1

    def get_ramsey_result(self):

        wait_for_data = True
        timeout_cyc = 25
        wait_s = 0.001      # initial wait time, is increased
        wait_total_s = 0
        i_wait = 0

        #time.sleep(1000e-3)

        while wait_for_data and i_wait < timeout_cyc:

            x, y, sweeps = self._pull_data_methods[self._cur_pull_data_method]()

            #if sweeps < (self.i_epoch + 1) * self.n_sweeps:   # sweeps seems to be incremented after counts!
            if abs(y) < 1e-6:
                #self.log.warning("Zeros received from fastcounter.")
                time.sleep(wait_s)
                wait_total_s += wait_s
                i_wait += 1
                if i_wait > 10:
                    wait_s = wait_s*1.5
                if not self.nolog_callback:
                    self.log.debug("Zero data looks like: {}".format(y))
            else:
                wait_for_data = False

            #y = 0 # DEBUG only

        if i_wait > 0:
            self.log.warning("Waited for data from fastcounter for {} ms in epoch {}".format(
                wait_total_s*1e3, self.i_epoch))
            if wait_for_data:
                self.log.warning("Timed out while waiting for data.")

        return (x, y)


    def pull_data_gated_and_ungated_plogic(self):
        """
        uses qudi pulsedmeasurement logic
        :return:
        """
        mes = self.pulsedmasterlogic().pulsedmeasurementlogic()
        mes.manually_pull_data()
        mes._extract_laser_pulses()

        x = mes.signal_data[0]
        y = mes.signal_data[1]

        # in gated mode we get results from the whole epoch array
        if len(x) > 1:
            x = x[self.i_epoch]
            y = y[self.i_epoch]

        return x, y, mes.elapsed_sweeps

    def pull_data_gated(self):

        fc_data, info = self.fastcounter.get_data_trace()
        sweeps = info['elapsed_sweeps']
        cts = fc_data

        x = None  # mes.signal_data[0]
        y = np.sum(cts[self.i_epoch])

        return x, y, sweeps

    def pull_data_ungated_sum_up_cts(self):

        fc_data, info = self.fastcounter.get_data_trace()
        sweeps = info['elapsed_sweeps']
        cts = np.sum(fc_data)

        if self.i_epoch == 0:
            y = cts
            self._sum_cts = cts     # must create variable in first run
        else:
            y = cts - self._sum_cts

        y = float(y)/self.n_sweeps

        if not self.nolog_callback:
            self.log.debug("Epoch {}, sweeps {}. pull_data_ungated_sum_up_cts. y= {}, cts= {}, sum= {} \n array= {}".format(
                            self.i_epoch, sweeps, y, cts, self._sum_cts, fc_data))

        self._sum_cts = cts
        x = None #mes.signal_data[0]

        return x, y, sweeps

    def pull_data_ungated_sum_up_cts_nicard(self):

        cts = self.nicard.get_edge_counters()[0]

        if self.i_epoch == 0:
            y = cts
            self._sum_cts = cts     # must create variable in first run
        else:
            y = cts - self._sum_cts

        y = float(y)/self.n_sweeps

        if not self.nolog_callback:
            self.log.debug("Epoch {}. pull_data_ungated_sum_up_cts_nicard. y= {}, cts= {}, sum= {}".format(
                            self.i_epoch, y, cts, self._sum_cts))

        self._sum_cts = cts
        x = None #mes.signal_data[0]

        return x, y, -1


    def calc_tau_from_posterior(self):

        tau_and_x = self.mfl_tau_from_heuristic()
        tau = tau_and_x['t']    # us
        tau = tau[0] * 1e-6

        #tau = 3500e-9   # DEBUG

        return tau

    def get_tau_and_x(self, tau_s):
        """
        outputs an array as expected from mfl_lib. tau in us, x set to dummy value.
        """
        tau_and_x = np.array([tau_s * 1e6, -1])
        tau_and_x.dtype = ([('t', '<f8'), ('w_', '<f8')])

        return tau_and_x

    def get_ts(self, idx_jumptable):
        tau_real = self.jumptable['tau'][idx_jumptable]
        t_seq = self.jumptable['t_seq'][idx_jumptable]

        return tau_real, t_seq

    def calc_jump_addr(self, tau, last_tau=None):

        # normal mode: find closest tau in jumptable
        idx_jumptable, val = self._find_nearest(self.jumptable['tau'], tau)
        if self.is_calibmode_lintau:
            # calibration mode: play taus linear after each other
            idx_jumptable, val = self._find_next_greatest(self.jumptable['tau'], last_tau)
            if idx_jumptable is -1:
                self.log.warning("No next greatest tau. Repeating last tau.")
                idx_jumptable, val = self._find_nearest(self.jumptable['tau'], last_tau)

        addr = self.jumptable['jump_address'][idx_jumptable]
        name_seqstep = self.jumptable['name'][idx_jumptable]
        if not self.nolog_callback:
            self.log.info("Finding next tau {} ns (req: {}) in {} at jump address {} (0b{:08b})".
                          format(1e9*val,1e9*tau, name_seqstep, addr, addr))

        return idx_jumptable, addr

    def timestamp(self, i_epoch, event_type):

        t_now = time.perf_counter()

        if i_epoch == 0:
            t0 = t_now
        else:
            t0 = self.timestamps[0][1]
            if i_epoch > self.n_epochs:
                self.log.warning("Potential ringbuffer overflow in timestamps. Treat result with care.")

        t_since_0 = t_now - t0

        self.timestamps[self._idx_timestamps][0] = i_epoch
        self.timestamps[self._idx_timestamps][1] = t_now
        self.timestamps[self._idx_timestamps][2] = t_since_0
        self.timestamps[self._idx_timestamps][3] = float(event_type)

        self._idx_timestamps += 1

    def majority_vote(self, z, z_thresh=0.5):
        if z > z_thresh:
            return 1
        else:
            return 0

    def _arr_idx(self, i_epoch, mode='ringbuffer'):

        if self.n_epochs < ARRAY_SIZE_MAX:
            return self.i_epoch

        if mode == 'ringbuffer':
            return i_epoch % ARRAY_SIZE_MAX
        else:
            raise NotImplemented


    def _find_nearest(self, array, value):
        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return idx, array[idx]

    def _find_next_greatest(self, array, value):

        dif = np.asarray(array, dtype=float) - value
        dif[dif <= 0] = np.inf
        idx = np.argmin(dif)
        val = array[idx]

        if dif[idx] == np.inf:
            idx = -1
            val = -1

        return idx, val

    def __cb_func_epoch_done(self, taskhandle, signalID, callbackData):

        # todo:
        # - The fastcomtec has a minimum range, need to check that the fastcounterlength is not less than this


        # done here, because before mes uploaded info not available and mes directly starts after upload atm
        # ugly, because costs time in first epoch
        if self.i_epoch == 0:
            self.is_running = True  # todo: should this be mutexed?
            self.is_running_lock.acquire()

            self.pull_jumptable(seqname=self.sequence_name)
            self.taus[0,0] = self._find_nearest(self.jumptable['tau'], self.taus[0,0])[1]   # todo: ugly. problem: atm, we don't now before first run started

        self.timestamp(self.i_epoch, TimestampEvent.irq_start)

        # we are after the mes -> prepare for next epoch
        _, z = self.get_ramsey_result()
        #z = 0  # DEBUG
        z_binary = self.majority_vote(z, z_thresh=self.z_thresh)

        if not self.nolog_callback:
            self.log.info("MFL callback invoked in epoch {}. z= {} -> {}".format(self.i_epoch, z, z_binary))

        last_tau = self.taus[self.i_epoch, 0]
        tau_and_x = self.get_tau_and_x(last_tau)
        self.mfl_updater.update(z_binary, tau_and_x)        # updates prior

        # new tau
        tau_req = self.calc_tau_from_posterior()    # new tau

        #tau_req = 3500e-9
        idx_jumptable, addr = self.calc_jump_addr(tau_req, last_tau)
        real_tau, t_seq = self.get_ts(idx_jumptable)

        # save result after measuring of this epoch and updating priors
        self.save_current_results(real_tau, tau_req, t_seq, z)
        self.iterate_mfl()  # iterates i_epoch

        if self.n_epochs is not -1 and self.i_epoch >= self.n_epochs:
            self.end_run()
            return 0
            # make sure thath i_epoch + 1 is never reached, if i_epoch == n_epochs

        self.timestamp(self.i_epoch - 1, TimestampEvent.irq_end)
        self.output_jump_pattern(addr)      # should directly before return

        return 0

    def _cb_func_profile_algo_only(self, taskhandle, signalID, callbackData):
        if self.i_epoch == 0:
            self.is_running = True  # todo: should this be mutexed?
      #
        self.timestamp(self.i_epoch)

        z = 0  # DEBUG
        z_binary = self.majority_vote(z, z_thresh=self.z_thresh)

        if not self.nolog_callback:
            self.log.info("MFL callback invoked in epoch {}. z= {} -> {}".format(self.i_epoch, z, z_binary))

        last_tau = self.taus[self.i_epoch, 0]
        tau_and_x = self.get_tau_and_x(last_tau)
        self.mfl_updater.update(z_binary, tau_and_x)  # updates prior

        # new tau
        tau_req = self.calc_tau_from_posterior()  # new tau

        # tau_req = 3500e-9
        #idx_jumptable, addr = self.calc_jump_addr(tau_req)
        real_tau, t_seq = 0, 0

        # save result after measuring of this epoch and updating priors
        self.save_current_results(real_tau, tau_req, t_seq, z)
        self.iterate_mfl()  # iterates i_epoch

        if self.n_epochs is not -1 and self.i_epoch >= self.n_epochs:
            self.end_run()
            return 0
            # make sure thath i_epoch + 1 is never reached, if i_epoch == n_epochs

        #time.sleep(0.01)
        #ucmd.send_ttl_pulse(None, channel_name='/dev1/PFI9', t_wait=0.01)

        #print("{}".format(self.i_epoch))

        return 0

    def _cb_func_profile_no_qudi(self, taskhandle, signalID, callbackData):

        # done here, because before mes uploaded info not available and mes directly starts after upload atm
        # ugly, because costs time in first epoch
        if self.i_epoch == 0:
            self.is_running = True  # todo: should this be mutexed?
            self.is_running_lock.acquire()
            self.wait_for_start_lock.release()

            time.sleep(1)

            self.pull_jumptable(seqname=self.sequence_name, load_vars_metafile='temp/mfl_meta.pkl')
            self.taus[0,0] = self._find_nearest(self.jumptable['tau'], self.taus[0,0])[1]   # todo: ugly. problem: atm, we don't now before first run started

        self.timestamp(self.i_epoch, TimestampEvent.irq_start)

        # we are after the mes -> prepare for next epoch

        _, z = self.get_ramsey_result()
        #z = 0  # DEBUG
        z_binary = self.majority_vote(z, z_thresh=self.z_thresh)

        if not self.nolog_callback:
            self.log.info("MFL callback invoked in epoch {}. z= {} -> {}".format(self.i_epoch, z, z_binary))

        last_tau = self.taus[self.i_epoch, 0]
        tau_and_x = self.get_tau_and_x(last_tau)
        self.mfl_updater.update(z_binary, tau_and_x)        # updates prior

        # new tau
        tau_req = self.calc_tau_from_posterior()    # new tau

        #tau_req = 3500e-9
        idx_jumptable, addr = self.calc_jump_addr(tau_req, last_tau)
        real_tau, t_seq = self.get_ts(idx_jumptable)
        #idx_jumptable, addr = 4, 1     # DEBUG, deterministically jump to first tau
        #real_tau, t_seq = -1, -1

        # save result after measuring of this epoch and updating priors
        self.save_current_results(real_tau, tau_req, t_seq, z)
        self.iterate_mfl()  # iterates i_epoch

        if self.n_epochs is not -1 and self.i_epoch >= self.n_epochs:
            self.end_run()
            return 0
            # make sure thath i_epoch + 1 is never reached, if i_epoch == n_epochs

        self.timestamp(self.i_epoch - 1, TimestampEvent.irq_end)
        self.output_jump_pattern(addr)      # should directly before return

        return 0

    def _setpriority_win(self, pid=None, priority=1):
        """ Set The Priority of a Windows Process.  Priority is a value between 0-5 where
            2 is normal priority.  Default sets the priority of the current
            python process but can take any valid process ID. """

        import win32api, win32process, win32con

        priorityclasses = [win32process.IDLE_PRIORITY_CLASS,
                           win32process.BELOW_NORMAL_PRIORITY_CLASS,
                           win32process.NORMAL_PRIORITY_CLASS,
                           win32process.ABOVE_NORMAL_PRIORITY_CLASS,
                           win32process.HIGH_PRIORITY_CLASS,
                           win32process.REALTIME_PRIORITY_CLASS]
        if pid == None:
            pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        win32process.SetPriorityClass(handle, priorityclasses[priority])

        prio_new = win32process.GetPriorityClass(handle)

        # https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getpriorityclass
        prio_switcher = {0x00008000: 3, # ABOVE_NORMAL_PRIORITY_CLASS
                    0x00004000: 1, # BELOW_NORMAL_PRIORITY_CLASS
                    0x00000080: 4, # HIGH_PRIORITY_CLASS
                    0x00000040: 0, # IDLE_PRIORITY_CLASS
                    0x00000020: 2, # NORMAL_PRIORITY_CLASS
                    0x00000100: 5} # REALTIME_PRIORITY_CLASS

        return prio_switcher.get(prio_new, 'invalid prio')


import abc
from core.util.interfaces import InterfaceMetaclass
class SerialInterface(metaclass=InterfaceMetaclass):
    """defines a device that can output bit patterns via a serial line"""
    _modtype = 'SerialInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def output_data(self, data):
        pass

import PyDAQmx as daq
import numpy as np
class PatternJumpAdapter(SerialInterface):
    """
    Adapter for realising serial output of 8 data bits + 1 strobe bit
    via NI PCIe 6323.
    uint32 written to NI. Translation to 8 bits:
    Lowest numbered bit on data ch is LSB, highest bit is MSB.
    Eg. line17: MSB, line23: LSB.
    data_in         line17... 23
                    |          |
    data = 1    =>  100...     0
    data = 128  =>  000...     1
    """
    strobe_ch = '/dev1/port0/line25'
    data_ch = '/dev1/port0/line17:24'

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.nitask_serial_out = None
        self.nitask_strobe_out = None

    def init_ni(self):
        self.nitask_serial_out = daq.TaskHandle()
        self.nitask_strobe_out = daq.TaskHandle()

        try:
            daq.DAQmxCreateTask('d_serial_out', daq.byref(self.nitask_serial_out))
        except daq.DuplicateTaskError:
            self.recreate_nitask('d_serial_out', self.nitask_serial_out)

        daq.DAQmxCreateDOChan(self.nitask_serial_out, self.data_ch, "", daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxStartTask(self.nitask_serial_out)

        try:
            daq.DAQmxCreateTask('d_strobe_out', daq.byref(self.nitask_strobe_out))
        except daq.DuplicateTaskError:
            self.recreate_nitask('d_strobe_out', self.nitask_strobe_out)

        daq.DAQmxCreateDOChan(self.nitask_strobe_out, self.strobe_ch, "", daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxStartTask(self.nitask_strobe_out)

        #self.log.debug("Created ni tasks for outputting jump patterns.")

    def recreate_nitask(self, name, task):
        daq.DAQmxClearTask(task)
        daq.DAQmxCreateTask(name, daq.byref(task))

    def stop_ni(self):
        daq.DAQmxClearTask(self.nitask_serial_out)
        daq.DAQmxClearTask(self.nitask_strobe_out)

    def output_data(self, data):
        digital_data = daq.c_uint32(data << 17)
        digital_read = daq.c_int32()    # dummy to feed to function
        n_samples = daq.c_int32(1)

        # value stays active at ouput
        daq.DAQmxWriteDigitalU32(self.nitask_serial_out, n_samples, True,
                                 0, daq.DAQmx_Val_GroupByChannel,
                                 np.array(digital_data), digital_read, None)

        self.output_strobe()

    def output_bit(self, idx_bit, high=True):
        """
        :param idx_bit: counted from 0 from low to high. idx_bit=0 -> line17, idx_bit=7 -> line 24
        :param high:
        :return:
        """
        digital_data = daq.c_uint32(0x1 << idx_bit + 17)
        digital_low = daq.c_uint32(0x0)
        digital_read = daq.c_int32()  # dummy to feed to function
        n_samples = daq.c_int32(1)

        if high:
            daq.DAQmxWriteDigitalU32(self.nitask_serial_out, n_samples, True,
                                     0, daq.DAQmx_Val_GroupByChannel,
                                     np.array(digital_data), digital_read, None)
        else:
            daq.DAQmxWriteDigitalU32(self.nitask_serial_out, n_samples, True,
                                     0, daq.DAQmx_Val_GroupByChannel,
                                     np.array(digital_low), digital_read, None)

    def output_strobe(self):
        digital_strobe = daq.c_uint32(0xffffffff)
        digital_low = daq.c_uint32(0x0)
        digital_read = daq.c_int32()  # dummy to feed to function
        n_samples = daq.c_int32(1)

        daq.DAQmxWriteDigitalU32(self.nitask_strobe_out, n_samples, True,
                                 0, daq.DAQmx_Val_GroupByChannel,
                                 np.array(digital_strobe), digital_read, None)
        daq.DAQmxWriteDigitalU32(self.nitask_strobe_out, n_samples, True,
                                 0, daq.DAQmx_Val_GroupByChannel,
                                 np.array(digital_low), digital_read, None)


if __name__ == '__main__':
    from logic.user_logic import UserCommands as ucmd
    import logging
    import PyDAQmx as daq
    import os

    os.chdir('../')
    print("Running mfl_irq_diven.py. Working dir: {}".format(os.getcwd()))

    logging.basicConfig(level=logging.DEBUG)
    #logging.basicConfig(filename='logfile.log', filemode='w', level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    mfl_logic = MFL_IRQ_Driven(None)
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

    def setup_mfl_seperate_thread():

        # todo:
        # parse setup params from file written by jupyter notebook
        n_sweeps = 1e4
        n_epochs = 20
        z_thresh = 0.7

        logger.info("Setting up mfl irq driven in own thread. Start mes from qudi. Will wait until all epochs done.")

        mfl_logic.init('mfl_ramsey_pjump', n_sweeps, n_epochs=n_epochs, nolog_callback=True, z_thresh=z_thresh)
        tau_first_req = mfl_logic.get_first_tau()
        # tau_first_req = 3500e-9 # DEBUG
        tau_first = tau_first_req  # PROBLEM would like to get from seqtable, but only created after run started
        # shortest tau mfl algo may choose, problem: shorter than tau_first causes rounding issues
        tau_start = 25e-9
        logger.info("First tau from flat prior {} ns".format(1e9 * tau_first))

        mfl_logic.setup_new_run(tau_first, tau_first_req, cb_epoch_done=mfl_logic._cb_func_profile_no_qudi)

        if mfl_logic._cur_pull_data_method is 'gated_2d':
            mfl_logic.fastcounter.change_sweep_mode(gated=True, is_single_sweeps=False,
                                                    n_sweeps_preset=int(n_sweeps))


    def join_mfl_seperate_thread():
        # prio of this thread
        prio = 5    # 2: normal 5: real time
        prio_new = mfl_logic._setpriority_win(pid=None, priority=prio)
        if prio != prio_new:
            logger.warning("Couldn't set process priority to {} (is {}). Run as admin?".format(prio, prio_new))

        mfl_logic.wait_for_start_lock.acquire()

        # here: callback installed, ready to react on mes run by qudi / from jupyter notebook

        #run_ramsey_pj(qmeas), called from jupyter scipt
        # wait until start
        logger.info("Waiting for mes to start...")
        mfl_logic.wait_for_start_lock.acquire()
        logger.info("Started. Waiting for all epochs done...")


        # wait until all epochs done
        mfl_logic.is_running_lock.acquire()
        mfl_logic.is_running_lock.release()

        logger.info("MFL thread done")

    """
    Profile callback
    """
    """
    daq.DAQmxResetDevice('dev1')
    #profile_mfl_pj()
    lp = line_profiler.LineProfiler()
    lp.add_function(mfl_logic._cb_func_profile_algo_only)
    lp.add_function(mfl_logic.save_current_results)

    lp_wrapper = lp(profile_mfl_pj)

    lp_wrapper()
    lp.print_stats()
    """

    """
    Profile fastcomtech read
    """
    """
    lp = line_profiler.LineProfiler()
    lp_wrapper = lp(profile_fastcounter_pull_data)

    lp_wrapper()
    lp.print_stats()
    """

    """
    Run in sepearte thread
    """

    #setup_mfl_seperate_thread()
    #mfl_logic.dump("temp/mfl_mes.pkl")
    #join_mfl_seperate_thread()


    """
    Test counting with ni counter
    """
    def setup_ni_counter():
        mfl_logic.nicard.set_up_single_edge_counter('dev1/ctr1')    # PFI 3 on breakout


    def test_edge_counter():
        t0 = time.perf_counter()
        for i in range(0, 10):
            t0_read = time.perf_counter()
            cts = mfl_logic.nicard.get_edge_counters()[0]
            t1_read = time.perf_counter()
            time.sleep(0.2)
            t1 = time.perf_counter()

            logger.info("Counted {}, in {} s -> {} kHz. Count took {} ms".format(
                cts, t1 - t0, float(cts) / (1e3*(t1 - t0)), (t1_read - t0_read)*1e3))

        for i in range(0, 10):
            t0 = time.perf_counter()
            cts = mfl_logic.nicard.get_edge_counters()[0]
            mfl_logic.nicard.close_edge_counters()
            setup_ni_counter()
            t1 = time.perf_counter()

            logger.info("Counted {}. Count & Reset took {} ms -> {} kHz".format(cts, (t1 - t0)*1e3, 1e-3 / (t1 - t0)))

        mfl_logic.nicard.close_edge_counters()


    setup_ni_counter()
    test_edge_counter()

