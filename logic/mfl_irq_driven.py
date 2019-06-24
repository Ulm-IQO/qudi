from logic.generic_logic import GenericLogic
from hardware.national_instruments_x_series import NationalInstrumentsXSeries
from core.module import Connector, StatusVar
import time

import imp
mfl_lib = imp.load_source('packages', './jupyter/Timo/own/mfl_sensing_simplelib.py')
import qinfer as qi


ARRAY_SIZE_MAX = 100


class MFL_IRQ_Driven(GenericLogic):

    _modclass = 'mfl_irq_driven'
    _modtype = 'logic'

    # this class requires a NI X Series counter
    counter = Connector(interface='SlowCounterInterface')
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')

    _epoch_done_trig_ch = StatusVar('_epoch_done_trig_ch', 'dev1/port0/line0')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.sequence_name = None
        self.i_epoch = 0
        self.n_epochs = -1
        self.n_sweeps = None
        self.z_thresh = None    # for majority vote of Ramsey result

        self.nolog_callback = False
        self.is_running = False
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

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.nicard = self.counter()
        if not isinstance(self.nicard, NationalInstrumentsXSeries):
            self.log.warning("Config defines not supported counter of type {} for MFL logic, not NI X Series.".format(
                             type(self.nicard)))

        self.serial = PatternJumpAdapter()
        self.serial.init_ni()

    def on_deactivate(self):
        """ """
        self.serial.stop_ni()
        self.end_run()

    def init(self, name, n_sweeps, n_epochs=-1, nolog_callback=False, z_thresh=0.5):
        self.i_epoch = 0
        self.n_epochs = n_epochs
        self.nolog_callback = nolog_callback
        self.sequence_name = name
        self.n_sweeps = n_sweeps
        self.z_thresh = z_thresh

        self.init_arrays(self.n_epochs)
        self.init_mfl_algo()

    def setup_new_run(self, tau_first, tau_first_req):

        # Attention: may not run smoothly in debug mode

        # reset probability distris
        self.init_mfl_algo()

        self.nicard.register_callback_on_change_detection(self._epoch_done_trig_ch,
                                                          self.__cb_func_epoch_done, edges=[True, False])

        mes = self.pulsedmasterlogic().pulsedmeasurementlogic()
        mes.timer_interval = 100  # basically disable analysis loop, pull manually instead

        self.save_estimates_before_first_run(tau_first, tau_first_req)

    def init_arrays(self, n_epochs):

        if n_epochs == -1:
            n_epochs = ARRAY_SIZE_MAX
            self.log.warning("Setting array length for infinite epochs to {}".format())

        self.timestamps = np.zeros((n_epochs, 3))
        # first estimate from flat prior is also in array
        self.taus = np.zeros((n_epochs + 1, 1))
        self.taus_requested = np.zeros((n_epochs + 1, 1))
        self.t_seqs = np.zeros((n_epochs + 1, 1))
        self.bs = np.zeros((n_epochs + 1, 1))
        self.dbs = np.zeros((n_epochs + 1, 1))


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


    def set_jumptable(self, jumptable_dict, tau_list, t_seqs_list):
        """
        self.jumptable format:
        {'name': [], 'idx_seqtable': [], 'jump_address': [], 'tau': [], 't_seq': []}
        """

        jumptable_dict['tau'] = tau_list            # interaction time
        jumptable_dict['t_seq'] = t_seqs_list      # the length of the sequence on the AWG

        self.jumptable = jumptable_dict

    def pull_jumptable(self, seqname, step_name='mfl_ramsey_pjump', jumpseq_name='laser_wait_0'):
        """
        :param seqname: name of the whole sequence in pulser
        :param step_name: common string of all seq elements.
        :param jumpseq_name: common string of all seq elements that can be jumped to.
                             Every jumpseq element belongs to a single sequence step
                             which is typically played right after the jumpseq element.
        :return:
        """
        seq = self.pulsedmasterlogic().sequencegeneratorlogic().saved_pulse_sequences[seqname]
        taus = seq.measurement_information['controlled_variable_virtual']   # needs to be added in generation method
        t_seqs = self.pull_t_seq_list(seq.ensemble_list, step_name)

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

    def pull_t_seq_list(self, active_ensembles, step_name):
        """
        Gets a list of all sequences lengths of block ensembles that share the given step name.
        :param step_name:  common string of all seq elements
        :return:
        """

        sample_rate = self.pulsedmasterlogic().pulse_generator_settings['sample_rate']

        # all ensembles in sequencer logic
        ens_dict = {key: val for key, val in self.pulsedmasterlogic().sequencegeneratorlogic().saved_pulse_block_ensembles.items() if
             step_name in key}

        # ensembles in the active sequence of the AWG
        active_steps = [el.ensemble for el in active_ensembles]

        t_seq_list = []
        for key, ensemble in ens_dict.items():
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
        db_mhz_rad =  np.sqrt(self.mfl_updater.est_covariance_mtx())
        self.dbs[0] = db_mhz_rad / (2*np.pi)

    def save_current_results(self, real_tau_s, requested_tau_s, t_seq_s):

        b_mhz_rad = self.mfl_updater.est_mean()[0]
        db_mhz_rad = np.sqrt(self.mfl_updater.est_covariance_mtx()[0,0])
        if self.mfl_updater.est_covariance_mtx().shape != (1,1):
            raise NotImplementedError("Never thought about >1 dimensional estimation, sorry.")

        self.bs[self._arr_idx(self.i_epoch) + 1, 0] = b_mhz_rad / (2 * np.pi)   # MHz
        self.dbs[self._arr_idx(self.i_epoch) + 1, 0] = db_mhz_rad / (2 * np.pi)
        self.taus[self._arr_idx(self.i_epoch) + 1, 0] = real_tau_s
        self.t_seqs[self._arr_idx(self.i_epoch) + 1, 0] = t_seq_s
        self.taus_requested[self._arr_idx(self.i_epoch) + 1, 0] = requested_tau_s

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
            raise RuntimeError

    def end_run(self):
        self.nicard.register_callback_on_change_detection(self._epoch_done_trig_ch,
                                                          None, edges=[True, False])

        if self.is_running:
            # assumes:
            # - that fast counter gets every single sweep by AWG
            # - constant sweeps in every tau
            tau_total = np.sum(self.taus * self.n_sweeps)
            t_seq_total = np.sum(self.t_seqs * self.n_sweeps)

            b, db, tau, tau_req = self.get_current_results()

            np.set_printoptions(formatter={'float': '{:0.6f}'.format})
            self.log.info("Ending MFL run at epoch {0}/{1}. B= {4:.2f} +- {5:.2f} MHz. Total tau / t_seq: {3:.3f}, {6:.3f} us."
                          " Timestamps: \n (i_epoch, t [s], t-t0 [s]){2}".format(
                self.i_epoch, self.n_epochs, self.timestamps, 1e6*tau_total,
                b, db, 1e6*t_seq_total))
            self.log.info("In MFL run: taus, taus_requested, delta: {}".format(
                [(t, self.taus_requested[i,0], t-self.taus_requested[i,0]) for (i, t) in enumerate(self.taus[:,0])]))
            self.log.info("In MFL run: B, dB (MHz): {}".format(
                [(b, self.dbs[i]) for (i, b) in enumerate(self.bs)]))
            np.set_printoptions()

            self.pulsedmasterlogic().toggle_pulsed_measurement(False)

        self.is_running = False

    def output_jump_pattern(self, jump_address):
        self.serial.output_data(jump_address)

    def iterate_mfl(self):
        self.i_epoch += 1

    def get_ramsey_result(self):
        mes = self.pulsedmasterlogic().pulsedmeasurementlogic()
        # get data at least once, even if timer to analyze not fired yet
        mes.manually_pull_data()

        x = mes.signal_data[0]
        y = mes.signal_data[1]

        return (x, y)

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

    def calc_jump_addr(self, tau, default_addr=1):

        addr = default_addr

        # find closest tau in jumptable
        idx_jumptable, val = self._find_nearest(self.jumptable['tau'], tau)
        addr = self.jumptable['jump_address'][idx_jumptable]
        name_seqstep = self.jumptable['name'][idx_jumptable]
        if not self.nolog_callback:
            self.log.info("Finding closest tau {} ns (req: {}) in {} at jump address {} (0b{:08b})".
                          format(1e9*val,1e9*tau, name_seqstep, addr, addr))

        return idx_jumptable, addr

    def timestamp(self, i_epoch):

        t_now = time.time()

        if i_epoch == 0:
            t0 = t_now
        else:
            t0 = self.timestamps[0][1]
            if i_epoch > self.n_epochs:
                self.log.warning("Potential ringbuffer overflow in timestamps. Treat result with care.")

        t_since_0 = t_now - t0

        self.timestamps[self._arr_idx(i_epoch)][0] = i_epoch
        self.timestamps[self._arr_idx(i_epoch)][1] = t_now
        self.timestamps[self._arr_idx(i_epoch)][2] = t_since_0

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


    def __cb_func_epoch_done(self, taskhandle, signalID, callbackData):

        # done here, because before mes uploaded info not available and mes directly starts after upload atm
        # ugly, because costs time in first epoch
        if self.i_epoch == 0:
            self.pull_jumptable(seqname=self.sequence_name)
            self.is_running = True  # todo: should this be mutexed?

        if self.n_epochs is not -1 and self.i_epoch >= self.n_epochs:
            self.end_run()
            return 0
            # make sure thath i_epoch + 1 is never reached, if i_epoch == n_epochs

        self.timestamp(self.i_epoch)

        # we are after the mes -> prepare for next epoch
        _, z = self.get_ramsey_result()
        #z = 0
        z_binary = self.majority_vote(z, z_thresh=self.z_thresh)

        if not self.nolog_callback:
            self.log.info("MFL callback invoked in epoch {}. z= {} -> {}".format(self.i_epoch, z, z_binary))

        # prior not updated yet
        tau_req = self.calc_tau_from_posterior()    # new tau

        #tau_req = 3500e-9
        idx_jumptable, addr = self.calc_jump_addr(tau_req)
        real_tau, t_seq = self.get_ts(idx_jumptable)
        tau_and_x = self.get_tau_and_x(real_tau)

        self.mfl_updater.update(z_binary, tau_and_x)        # updates prior

        # save result after measuring of this epoch and updating priors
        self.save_current_results(real_tau, tau_req, t_seq)
        self.iterate_mfl()  # iterates i_epoch

        self.output_jump_pattern(addr)      # should directly before return

        # todo:
        # - for some reason first epoch only half the sweeps. comtech not ready yet?
        # - can fastcomtech start recounting while running?
        # - fix readout: gated?
        # - results array indexing really correct?

        return 0

    def _find_nearest(self, array, value):
        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return idx, array[idx]


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

    def __init__(self, data_ch=None, strobe_ch=None):
        super().__init__()
        self.nitask_serial_out = None
        self.nitask_strobe_out = None

    def init_ni(self):
        self.nitask_serial_out = daq.TaskHandle()
        self.nitask_strobe_out = daq.TaskHandle()

        try:
            daq.DAQmxCreateTask('', daq.byref(self.nitask_serial_out))
        except daq.DuplicateTaskError:
            self.recreate_nitask('', self.nitask_serial_out)

        daq.DAQmxCreateDOChan(self.nitask_serial_out, self.data_ch, "", daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxStartTask(self.nitask_serial_out)

        try:
            daq.DAQmxCreateTask('', daq.byref(self.nitask_strobe_out))
        except daq.DuplicateTaskError:
            self.recreate_nitask('', self.nitask_strobe_out)

        daq.DAQmxCreateDOChan(self.nitask_strobe_out, self.strobe_ch, "", daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxStartTask(self.nitask_strobe_out)

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

