from collections import OrderedDict
import numpy as np
import time
import datetime
import matplotlib.pyplot as plt
from core.util import units
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.user_logic import UserGlobals

import logging
logging.basicConfig(filename='logfile.log', filemode='w', level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    pulsedmasterlogic
except NameError:
    manager.startModule('logic', 'pulsedmasterlogic')
try:
    scannerlogic
except NameError:
    manager.startModule('logic', 'scannerlogic')
try:
    optimizerlogic
except NameError:
    manager.startModule('logic', 'optimizerlogic')


############################################ Static hardware parameters ################################################

save_subdir = None
qm_dict_final ={}

setup = OrderedDict()
setup['gated'] = pulsedmeasurementlogic.fastcounter().gated#True
setup['sampling_freq'] = pulsedmasterlogic.pulse_generator_settings['sample_rate']
setup['bin_width'] = 4.0e-9
setup['wait_time'] = 1.0e-6
setup['laser_delay'] = 500e-9  #p7887: 900e-9 # aom delay, N25 setup3: 510e-9
setup['laser_safety'] = 200e-9

if setup['gated']:
    # need a "sync pulse" at the starting edge of every readout laser
    # setting a gate channel pulls up the gate_ch of every laser_gate_element
    setup['sync_channel'] = 'd_ch1'
    setup['gate_channel'] = 'd_ch3'

else:
    setup['sync_channel'] = 'd_ch1'
    setup['gate_channel'] = ''
try:
    pulsedmeasurementlogic.fastcounter().change_sweep_mode(setup['gated'])
    logger.debug("Setting fastcounter to gated: {}".format(setup['gated']))
except Exception as e:
    logger.warning("Couldn't set fast counter sweep mode: {}".format(str(e)))

setup['laser_channel'] = 'd_ch4'
setup['laser_length'] = 3e-6
setup['wait_length'] = 1e-6
setup['trigger_length'] = 20e-9

setup['delay_length'] = setup['laser_delay'] - 30e-9#450e-9

setup['channel_amp'] = 1.0
setup['microwave_channel'] = 'a_ch1'
setup['optimize_channel'] = None #'/Dev1/PFI0'

setup['readout_end'] = 0.3e-6

setup['max_tau'] = 1e-3
setup['max_tau_start'] = 1e-3
setup['max_rabi_period'] = 1e-3
setup['min_microwave_frequency'] = 1
setup['max_microwave_amplitude'] = 0.25

setup['measurement_time'] = 600
setup['optimize_time'] = 300
setup['freq_optimize_time'] = None
setup['analysis_interval'] = 3

logger.info("Logic essentials imported, setup params: {}".format(setup))

#####
# Autoload often used modules
#####

try:
    nicard
except NameError:
    print("Nicard hardware not found, creating dummy interface")
    try:
        manager.loadConfigureModule('hardware', 'nicard')
    except Exception as e:
        logger.error("Auto module loading failed. Defined in config? {}".format(e))
try:
    uglobals
except NameError:
    try:
        manager.loadConfigureModule('logic', 'uglobals')
    except Exception as e:
        logger.error("Auto module loading failed. Defined in config? {}".format(e))
try:
    uglobals.abort.clear()
    uglobals.next.clear()
except NameError:
    pass

try:
    ucmd
except NameError:
    try:
        manager.loadConfigureModule('logic', 'ucmd')
    except Exception as e:
        logger.error("Auto module loading failed. Defined in config? {}".format(e))


def print_welcome_msg():
    print('[{}] Hi, jupyter ready. working dir: {}'.format(time.ctime(), os.getcwd()))


def config_matplotlib_jupyter():
    # is overwritten by qudi save logic
    # does impact local plotting from jupyter (?)
    import matplotlib
    matplotlib.pylab.rcParams['figure.figsize'] = (7.5, 5)

    pass

############################## Standard function for conventional and SSR measurements #################################


def do_experiment(experiment, qm_dict, meas_type, meas_info, generate_new=True, save_tag='',
                  load_tag='', save_subdir=None, sleep_time=0.2, prepare_only=False):
    """
    :param save_tag: different from qudi: if == None, don't save anything.
    :return:
    """
    # purge last mes
    global qm_dict_final
    qm_dict_final = {}
    # add information necessary for measurement type
    logger.debug("Measrument info of type {}".format(str(meas_info)))
    qm_dict = meas_info(experiment, qm_dict)

    # perform sanity checks
    if experiment not in pulsedmasterlogic.generate_methods:
        logger.error('Unknown Experiment {0}'.format(experiment))
        return -1
    if not perform_sanity_check(qm_dict):
        logger.error('Dictionary sanity check failed')
        return -1

    # Stop and save the measurement if one is running
    if pulsedmasterlogic.status_dict['measurement_running']:
        pulsedmasterlogic.toggle_pulsed_measurement(False)
        pulsedmasterlogic.save_measurement_data(save_tag, True)
    if pulsedmeasurementlogic.pulsegenerator().get_status == 1:
        pulsedmasterlogic.toggle_pulse_generator(False)

    logger.debug("do_experiment pulsedMesLogic.n_sweeps / next.is_set / abort.is_set: {}, {}, {}".format(
                pulsedmasterlogic.pulsedmeasurementlogic().elapsed_sweeps, uglobals.next.is_set(),
                uglobals.abort.is_set()))

    user_terminated = False
    if not handle_abort():
        # prepare the measurement by generating and loading the sequence/waveform
        prepare_qm(experiment, qm_dict, generate_new)

        if prepare_only:
            return user_terminated

        # perform measurement
        user_terminated = perform_measurement(qm_dict=qm_dict, meas_type=meas_type, load_tag=load_tag,
                                              save_tag=save_tag, save_subdir=save_subdir)

        # wait for a moment
        time.sleep(sleep_time)

    # if ssr:
    #     # # save the measurement results
    #     save_ssr_final_result(save_tag)

    return user_terminated

def perform_sanity_check(qm_dict):

    ok = True

    if 'tau' in qm_dict and qm_dict['tau']>setup['max_tau']:
        ok = False
    if 'tau_start' in qm_dict and qm_dict['tau_start']>setup['max_tau_start']:
        ok = False
    if 'rabi_period' in qm_dict and qm_dict['rabi_period']>setup['max_rabi_period']:
        ok = False
    if 'microwave_frequency' in qm_dict and qm_dict['microwave_frequency']<setup['min_microwave_frequency']:
        ok = False
    if 'microwave_amplitude' in qm_dict and qm_dict['microwave_amplitude']>setup['max_microwave_amplitude']:
        ok = False
    if 'microwave_amplitude' in qm_dict and qm_dict['microwave_amplitude']>setup['max_microwave_amplitude']:
        ok = False
    if 'rf_duration' in qm_dict and qm_dict['rf_duration']>1:
        ok = False
    if 'freq_start' in qm_dict and qm_dict['freq_start']<5000:
        ok = False

    if not ok:
        logger.warning("Dict sanity check failed. Dict: {}".format(qm_dict))

    return ok


def add_conventional_information(experiment, qm_dict):
    qm_dict['experiment'] = experiment

    if 'gated' not in qm_dict:
        qm_dict['gated'] = False
    if 'sequence_mode' not in qm_dict:
        qm_dict['sequence_mode'] = False
    if 'ctr_single_sweeps' not in qm_dict:
        qm_dict['ctr_single_sweeps'] = False
    if 'ctr_n_sweeps' not in qm_dict:
        qm_dict['ctr_n_sweeps'] = 0
    if 'ctr_n_cycles' not in qm_dict:
        qm_dict['ctr_n_cycles'] = 0


    if 'measurement_time' not in qm_dict:
        qm_dict['measurement_time'] = None
    if 'optimize_time' not in qm_dict:
        qm_dict['optimize_time'] = None
    if 'freq_optimize_time' not in qm_dict:
        qm_dict['freq_optimize_time'] = None
    if 'analysis_interval' not in qm_dict:
        qm_dict['analysis_interval'] = None

    return qm_dict


def add_sequence_mode_info(experiment, qm_dict):
    qm_dict['experiment'] = experiment

    if 'gated' not in qm_dict:
        qm_dict['gated'] = False
    if 'sequence_mode' not in qm_dict:
        qm_dict['sequence_mode'] = True
    if 'ctr_single_sweeps' not in qm_dict:
        qm_dict['ctr_single_sweeps'] = False
    if 'ctr_n_sweeps' not in qm_dict:
        qm_dict['ctr_n_sweeps'] = None
    if 'ctr_n_cycles' not in qm_dict:
        qm_dict['ctr_n_cycles'] = 0

    if 'measurement_time' not in qm_dict:
        qm_dict['measurement_time'] = None
    if 'optimize_time' not in qm_dict:
        qm_dict['optimize_time'] = None
    if 'freq_optimize_time' not in qm_dict:
        qm_dict['freq_optimize_time'] = None
    if 'analysis_interval' not in qm_dict:
        qm_dict['analysis_interval'] = None

    return qm_dict


def lockfile_aquire(filename, timeout_s=0):
        """
        Lockfile is deleted aa soon as lock acquired.
        :param filename:
        :param timeout_s: 0: return immediately, -1: wait infinitely
        :return:
        """
        import os

        t_start = time.perf_counter()
        timeout = False
        success = False

        while not timeout and not success:

            try:
                with open(filename, 'rb') as file:
                    lock = pickle.load(file)
                success = True
                #logger.info("Successfully acquired lock {}".format(filename))
                break
            except Exception as e:
                success = False
                #logger.info("Failed acquiring lock {}: {}".format(filename, str(e)))

            time.sleep(0.1)

            t_now = time.perf_counter()
            if t_now - t_start > timeout_s:
                if not timeout_s < 0:
                    timeout = True

        if success:
            os.remove(filename)

        return success

###################################  Upload and set parameters functionality #######################################


def prepare_qm(experiment, qm_dict, generate_new=True):
    ###### Prepare a quantum measurement by generating the sequence and loading it up to the pulser

    if generate_new:
        generate_sample_upload(experiment, qm_dict)
    else:
        logger.info("Loading stored experiment {} without re-generation.".format(qm_dict))
        load_into_channel(qm_dict['name'], sequence_mode=qm_dict['sequence_mode'])

        """
        # seems weird ?????
        try:
            qm_dict.update(memory_dict[qm_dict['name']])
        except Exception as e:
            pulsedmasterlogic.log.error('Experiment parameters are not known. Needs to be generate newly.')
            raise e
        """

    # todo: this seems to take forever for long sequences on awg8190
    # do we need it at all?
    """
    logger.debug("Getting sequence length...")
    if not qm_dict['sequence_mode']:
        qm_dict['sequence_length'] = \
            pulsedmasterlogic.get_ensemble_info(pulsedmasterlogic.saved_pulse_block_ensembles[qm_dict['name']])[0]
    else:
        qm_dict['sequence_length'] = \
            pulsedmasterlogic.get_sequence_info(pulsedmasterlogic.saved_pulse_sequences[qm_dict['name']])[0]
    """
    set_parameters(qm_dict)

    try:
        memory_dict = {}.update(memory_dict)
    except:
        memory_dict = {}

    logger.debug("Preparing experiment. qm_dict {}, memory_dict {}".format(qm_dict, memory_dict))

    return qm_dict


def customise_setup(dictionary):
    #final_dict = dictionary
    for key in setup.keys():
        if key not in dictionary.keys():
            dictionary[key] = setup[key]
    # get a subdictionary with the generation parameters and set them
    subdict = dict([(key, dictionary.get(key)) for key in pulsedmasterlogic.generation_parameters if key in dictionary])
    pulsedmasterlogic.set_generation_parameters(subdict)

    logger.info("Setting sequence generation params: {}".format(subdict))

    subdict_fc = dict([(key, dictionary.get(key)) for key in pulsedmasterlogic.fast_counter_settings if key in dictionary])
    pulsedmasterlogic.set_fast_counter_settings(subdict)
    logger.info("Setting fastcounter params: {}".format(subdict_fc))


    return dictionary

def generate_sample_upload(experiment, qm_dict):
    qm_dict = customise_setup(qm_dict)
    if not qm_dict['sequence_mode']:
        # make sure a previous ensemble is deleted
        pulsedmasterlogic.delete_block_ensemble(qm_dict['name'])
        try:
            pulsedmasterlogic.generate_predefined_sequence(experiment, qm_dict.copy())
        except Exception as e:
            pulsedmasterlogic.log.error('Generation failed')
            raise e

        time.sleep(0.2)
        # sample the ensemble
        sleep_until_abort("pulsedmasterlogic.status_dict['predefined_generation_busy']")

        not_found = False
        if qm_dict['name'] in pulsedmasterlogic.saved_pulse_block_ensembles:
            pulsedmasterlogic.sample_ensemble(qm_dict['name'], True)
        else:
            if qm_dict['name'] in pulsedmasterlogic.saved_pulse_sequences:
                pulsedmasterlogic.sample_sequence(qm_dict['name'], True)
            else:
                not_found = True

        if not_found:
            raise RuntimeError("Couldn't find experiment {} in saved pulse block ensembles / sequences".format(qm_dict['name']))


    else:
        if 'exchange_parts' not in qm_dict or qm_dict['exchange_parts']=={}:
            # make sure a previous sequence is deleted
            pulsedmasterlogic.delete_sequence(qm_dict['name'])
            # generate the ensemble or sequence
            try:
                pulsedmasterlogic.generate_predefined_sequence(experiment, qm_dict.copy())
            except Exception as e:
                pulsedmasterlogic.log.error('Generation failed: {}'.format(str(e)))
                raise e
            # sample the sequence
            time.sleep(0.2)
            sleep_until_abort("pulsedmasterlogic.status_dict['predefined_generation_busy']")

            if qm_dict['name'] not in pulsedmasterlogic.saved_pulse_sequences:
                pulsedmasterlogic.log.error("Couldn't find sequence {} in pulsedmasterlogic".format(qm_dict['name']))
                raise RuntimeError("Couldn't find sequence {} in pulsedmasterlogic".format(qm_dict['name']))

            pulsedmasterlogic.sample_sequence(qm_dict['name'], True)

        else:
            # get the sequence information
            #sequence = pulsedmasterlogic.saved_pulse_sequences.get(qm_dict['name'])
            # just generate the replacement ensembles
            for name in qm_dict['exchange_parts']:
                #adapt name of ensemble to be exchanged
                tmp_dict = qm_dict['exchange_parts'][name]['qm_dict'].copy()
                tmp_dict['name'] = name
                pulsedmasterlogic.delete_block_ensemble(name)
                try:
                    pulsedmasterlogic.generate_predefined_sequence(qm_dict['exchange_parts'][name]['experiment'],
                                                                   tmp_dict.copy())
                except:
                    pulsedmasterlogic.log.error('Generation failed')
                    return cause_an_error

                sleep_until_abort("pulsedmasterlogic.status_dict['predefined_generation_busy']")

                if name not in pulsedmasterlogic.saved_pulse_block_ensembles: cause_an_error
                pulsedmasterlogic.sample_ensemble(name, True)
                sleep_until_abort("pulsedmasterlogic.status_dict['sampload_busy']")
            # load the sequence
            # generate
            write_sequence(sequence_name=qm_dict['name'], sequence_param_list=None, load=True)

    # wait till sequence is sampled
    sleep_until_abort("pulsedmasterlogic.status_dict['sampload_busy']")

    return

def load_into_channel(name, sequence_mode):

    logger.debug("Loading {} {} from AWG to channel.".format('sequence' if sequence_mode else 'ensemble', name))

    n_trials_awg = 10
    i_trial = 0
    while i_trial < n_trials_awg:
        try:
            sampled_seqs = pulsedmasterlogic.sampled_sequences
            break
        except IOError:
            # sometimes AWG70k isnt't responding, keep trying
            logger.warning("VisaIOError while communicating with pulser. Retrying {}...".format(i_trial))
            time.sleep(0.2)

    # upload ensemble to pulser channel with sanity check
    if sequence_mode:
        if name in sampled_seqs:
            logger.info("Loading sequence {}...".format(name))
            pulsedmasterlogic.load_sequence(name)
        else:
            pulsedmasterlogic.log.error('Sequence {} not found. Cannot load to channel. Sequences: {}'.format(
                                        name, sampled_seqs))
            raise RuntimeError('Sequence {} not found. Cannot load to channel. Sequences: {}'.format(
                                        name, sampled_seqs))
    else:
        if name + '_ch1' in pulsedmasterlogic.sampled_waveforms:
            pulsedmasterlogic.load_ensemble(name)
        else:
            pulsedmasterlogic.log.error('Ensemble not found. Cannot load to channel')

    # wait until ensemble is loaded to channel
    sleep_until_abort("pulsedmasterlogic.status_dict['loading_busy']", dt_s=0.5, timeout_s=100)

    logger.debug("Loading to channel done.")
    return


def set_parameters(qm_dict):

    logger.debug("Setting parameters for asset {}: {}".format(qm_dict['name'], qm_dict))
    try:
        if not qm_dict['sequence_mode']:
            qm_dict['params'] = pulsedmasterlogic.saved_pulse_block_ensembles.get(qm_dict['name']).measurement_information
        else:
            qm_dict['params'] = pulsedmasterlogic.saved_pulse_sequences.get(qm_dict['name']).measurement_information
        pulsedmasterlogic.set_measurement_settings(qm_dict['params'])

    except:
        logger.exception(f"Failed setting pulsed parameters. Is sequence? {qm_dict['sequence_mode']}:")

    return qm_dict



############################### Perform Measurement Methods ############################################################


def perform_measurement(qm_dict, meas_type, load_tag='', save_tag='', save_subdir=None, analysis_interval=None, measurement_time=None,
                        optimize_time=None, freq_optimize_time=None):
    # FIXME: add the possibility to load previous data saved under load_tag
    laser_off(pulser_on=False)
    try:
        pulsedmasterlogic.do_fit('No Fit')
    except BaseException:
        logger.exception("Empty fir failed: ")
    # save parameters into memory_dict
    memory_dict[qm_dict['name']] = qm_dict.copy()

    ###################### Adjust running and refocussing time ##################
    # should be in qm_dict, keep as comment to see whether breaks
    """
    qm_dict['measurement_time'] = measurement_time
    qm_dict['optimize_time'] = optimize_time
    qm_dict['freq_optimize_time'] = freq_optimize_time
    qm_dict['analysis_interval'] = analysis_interval
    """
    user_terminated = False

    ################ Start and perform the measurement #################
    if handle_abort() is 0:
        logger.debug(f"Starting mes of type {meas_type}")
        user_terminated = meas_type(qm_dict)

    ########################## Save data ###############################
    # save and fit depending on abort signals
    if handle_abort() is 2:
        user_terminated = True
        return user_terminated

    # save
    global qm_dict_final
    qm_dict_final = qm_dict

    if save_tag is not None:
        logger.debug("Saving logic essential params to {}/{}".format(save_subdir, save_tag))
        save_parameters(save_tag=save_tag, save_dict=qm_dict, subdir=save_subdir)

    if 'listfile' in qm_dict.keys():
        # listfile .lst is configure before mes, but still .mpa will miss.
        # So change save_mode and save again after mes
        if qm_dict['listfile']:
            data_dir = os.path.abspath(savelogic.get_daily_directory())
            name = f"{qm_dict['savetag']}.mpa"
            myfastcounter.change_save_mode(0)
            myfastcounter.save_data(data_dir + r'\\' + name)
            logger.info(f"Saving .mpa to: {myfastcounter.get_filename()}")
            myfastcounter.change_save_mode(2)

    # if fit desired
    if 'fit_experiment' in qm_dict and qm_dict['fit_experiment'] != 'No fit':
        try:
            fit_data, fit_result = pulsedmeasurementlogic.do_fit(qm_dict['fit_experiment'])
        except BaseException as e:
            logger.exception("Fit failed: ")
    if save_tag is not None:
        pulsedmasterlogic.save_measurement_data(save_tag, with_error=True, subdir=save_subdir)
    time.sleep(1)

    return user_terminated

def handle_abort():
    """
    Stops mes and returns status code.
    Actual stop of mes [pulsedmasterlogic.toggle_pulsed_measurement(False)] must be handled outside!

    :return:
        0: no abort
        1: abort
        2: next measurement.
    """

    retcode = 0

    if uglobals.abort.is_set():
        retcode = 1

    try:
        if pulsedmasterlogic.break_variable is True:  # break_variable: for backward compability
            retcode = 1
    except AttributeError:  # break_variable not defined
        pass

    if uglobals.next.is_set():
        uglobals.next.clear()
        retcode = 2

    if retcode > 0:
        try:
            uglobals.qmeas = {}
        except: pass
        logger.debug("handle_abort() received stop signal, code {}".format(retcode))

    return retcode

def conventional_measurement(qm_dict):


    set_up_conventional_measurement(qm_dict)
    # perform measurement
    logger.info("Issueing Pulser on")
    pulsedmasterlogic.toggle_pulsed_measurement(True)
    logger.info("Pulser on")

    i_wait = 0
    n_wait_max = 200
    while not pulsedmasterlogic.status_dict['measurement_running'] and i_wait < n_wait_max:
        logger.debug("Waiting for mes and fastcounter to start.")
        time.sleep(1)
        i_wait += 1

        user_abort_code = handle_abort()
        if user_abort_code != 0:
            pulsedmasterlogic.toggle_pulsed_measurement(False)
            return True

    if i_wait >= n_wait_max:
        logger.warning("Timed out while starting measurement.")
        user_terminated = False
    else:
        try:
            uglobals.qmeas = qm_dict
        except: pass
        user_terminated = control_measurement(qm_dict, analysis_method=None)


    # Stop measurement
    try:
            uglobals.qmeas = {}
    except: pass

    pulsedmasterlogic.toggle_pulsed_measurement(False)
    i_wait = 0
    n_wait_max = 50
    while pulsedmasterlogic.status_dict['measurement_running'] and i_wait < n_wait_max:
        time.sleep(0.5)
        i_wait += 1

    if i_wait >= n_wait_max:
        logger.warning("Stopping pulsed mes timed out.")

    return user_terminated

def set_gated_counting(qm_dict):
    # not needed to configure fastcounter from script, should be done from pulsedmeasuremenlogic.configure()
    if not setup['gated']:
        qm_dict['ctr_n_cycles'] = 0
    else:
        qm_dict['gated'] = setup['gated']
        qm_dict['ctr_n_cycles'] = qm_dict['params']['number_of_lasers']
    """
    if setup['gated']:
        pulsedmeasurementlogic.fastcounter().change_sweep_mode(setup['gated'],
                                                                cycles=1,
                                                               preset=None)
    """
    return qm_dict

def set_up_conventional_measurement(qm_dict):
    from hardware.fast_counter_dummy import FastCounterDummy

    # configure AWG
    if 'trig_in_pol' in qm_dict:
        try:
            pulsedmasterlogic.pulsedmeasurementlogic().pulsegenerator().set_trig_polarity(qm_dict['trig_in_pol'])
        except Exception as e:
            logger.warning("Couldn't set trigger polarity {}: {}".format(qm_dict['trig_in_pol'], str(e)))
    if 'trig_mode' in qm_dict:
        try:
            pulsedmasterlogic.pulsedmeasurementlogic().pulsegenerator().set_trigger_mode((qm_dict['trig_mode']))
        except Exception as e:
            logger.warning("Couldn't set trigger mode {}: {}".format(qm_dict['trig_mode'], str(e)))

    # configure counting
    #if not isinstance(pulsedmeasurementlogic.fastcounter(), FastCounterDummy):
    logger.info("Setting fastcounter to gated: {}, bin_width {}".format(setup['gated'], qm_dict['bin_width']))



    # need to do after sequence generation, otherwise number_of_lasers not available
    qm_dict = set_gated_counting(qm_dict)

    # might be specific for mfl 2d gated counting (every 2d line is a epoch)
    pulsedmasterlogic.set_fast_counter_settings({'bin_width': qm_dict['bin_width'],
                                                 'record_length': qm_dict['params']['counting_length'],
                                                 'number_of_gates': qm_dict['ctr_n_cycles'] if setup['gated'] else 0})
    time.sleep(0.2)
    # laser pulse extraction
    laser_on = setup['laser_length']

    if not 'extr_method' in qm_dict:
        #extr_method = {'method': 'fixed_time_one_pulse', 't1': 0e-9, 't2': laser_on}  # mfl with gating adjusts for aom delay
        if setup['gated']:
            extr_method = {'method': 'pass_through'}
        else:
            extr_method = {'method': 'gated_conv_deriv', 'delay': setup['laser_delay'], 'safety': setup['laser_safety']}
    else:
        extr_method = qm_dict['extr_method']

    pulsedmasterlogic.set_extraction_settings(extr_method)
    logger.info("Setting laser pulse extraction method: {}".format(extr_method))

    # pulsedmasterlogic.set_extraction_settings({'method': 'conv_deriv', 'conv_std_dev': 20})
    # pulsedmasterlogic.set_extraction_settings({'method': 'threshold', 'count_threshold':20, 'min_laser_length':100e-9, 'threshold_tolerance':10e-9})
    # pulsedmasterlogic.set_extraction_settings({'method': 'gated_conv_deriv', 'delay': setup['laser_delay'],
    #                                            'safety': setup['laser_safety']})
    # pulsedmasterlogic.set_extraction_settings({'method': 'fixed_time_one_pulse', 't1': 560e-9,
    #                                           't2': 1.6e-6})

    #pulsedmasterlogic.set_analysis_settings({'method': 'mean_norm', 'signal_start': 0, 'signal_end': 500e-9,
    #                                         'norm_start': 1.8e-6, 'norm_end': 2.8e-6})

    if 'analysis_method' in qm_dict:
        analy_method = qm_dict['analysis_method']
    else:
        if not setup['gated']:
            if pulsedmasterlogic.generation_parameters['laser_length'] > 1.5e-6:
                analy_method = {'method': 'mean_norm', 'signal_start': 0, 'signal_end': 400e-9,
                                'norm_start': 1.7e-6, 'norm_end': 2.15e-6}
            else:
                analy_method = {'method': 'mean', 'signal_start': 0, 'signal_end': 400e-9,
                                'norm_start': 1.7e-6, 'norm_end': 2.15e-6}
        else:
            #analy_method = {'method': 'mean_norm', 'signal_start': 805e-9, 'signal_end': 805e-9 + 800e-9,
             #                                   'norm_start': 2700e-9, 'norm_end': 2700e-9 + 800e-9}
            analy_method = {'method': 'mean_norm', 'signal_start': 833.684e-9, 'signal_end': 833.684e-9 + 943.158e-9,
                                                'norm_start': 3204e-9, 'norm_end': 3204e-9 + 294.737e-9}
            #analy_method = {'method': 'mean', 'signal_start': 3280-9, 'signal_end': 3280-9 + 500e-9,
            #                                    'norm_start': 740e-9 + 1.7e-6, 'norm_end': 740e-9 + 2.15e-6}

    logger.info("Setting laser pulse analysis method: {}".format(analy_method))
    pulsedmasterlogic.set_analysis_settings(analy_method)

    #if not isinstance(pulsedmeasurementlogic.fastcounter(), FastCounterDummy):
    #logger.debug("Setting delayed start= 0")
    #pulsedmeasurementlogic.fastcounter().set_delay_start(0)

    #pulsedmeasurementlogic.fastcounter().change_save_mode(0)

    # debug: create lst file
    """
    filepath = 'C:/P7887(x64)/DATA/'
    list_name = filepath + '\\' + 'test'
    filepath = list_name + '.lst'
    pulsedmeasurementlogic.fastcounter()._change_filename(filepath)
    pulsedmeasurementlogic.fastcounter().change_save_mode(2)
    """

    if 'timer_interval' not in qm_dict:
        t_loop_mes = 2
    else:
        t_loop_mes = qm_dict['timer_interval']
    logger.debug("Setting mes logic timer interval  to {} s.".format(t_loop_mes))
    pulsedmeasurementlogic.timer_interval = t_loop_mes

    #logger.debug("Final setup: {}".format(setup))

    logger.debug("Finished setup")
    return


def control_measurement(qm_dict, analysis_method=None):
    """
    Main loop while running an experiment
    """
    ################# Set the timer and run the measurement #################
    start_time = time.time()
    optimize_real_time = start_time
    freq_optimize_real_time = start_time
    real_update_time = start_time

    idx_loop = 0
    t_last_save = None
    idx_last_save = 0
    while True:

        time.sleep(0.5)  # 2

        if 'n_sweeps' in qm_dict:
            # stop by sweeps can't be faster than sleep time
            if qm_dict['n_sweeps'] is not None:
                if pulsedmasterlogic.elapsed_sweeps >= qm_dict['n_sweeps']:
                    # repull if data is outdated
                    pulsedmasterlogic.pulsedmeasurementlogic().manually_pull_data()
                    if pulsedmasterlogic.elapsed_sweeps >= qm_dict['n_sweeps']:
                        pulsedmasterlogic.pulsedmeasurementlogic().stop_pulsed_measurement()
                        logger.debug("stopping mes in control loop {} after {}/{} sweeps".format(idx_loop,
                                                                    pulsedmasterlogic.elapsed_sweeps, qm_dict['n_sweeps']))
                        user_terminated = False
                        break

        if qm_dict['measurement_time'] is not None:
            if (time.time() - start_time) > qm_dict['measurement_time']:
                user_terminated = False
                break

        try:
            if qm_dict['lock_file_done'] is not None:
                import os
                file = os.getcwd() + '/' + qm_dict['lock_file_done']
                #logger.debug("Trying acquiring lockfile {}...".format(file))
                if lockfile_aquire(file, 0):
                    logger.debug("Success acquiring lockfile.")
                    user_terminated = False
                    break
        except KeyError:
            #logger.warning("key error, no lock_file_done in qmease")
            pass

        if not pulsedmasterlogic.status_dict['measurement_running']:
            user_terminated = True
            break

        ##################### optimize position #######################
        if qm_dict['optimize_time'] is not None:
            func_toggle = None
            if 'optimize_func_toggle_pause' in qm_dict:
                func_toggle = qm_dict['optimize_func_toggle_pause']
            if time.time() - optimize_real_time > qm_dict['optimize_time']:
                additional_time = optimize_position(func_toggle_pause=func_toggle)
                start_time = start_time + additional_time
                optimize_real_time = time.time()

        ####################### optimize frequency ####################
        if qm_dict['freq_optimize_time'] is not None:
            if time.time() - freq_optimize_real_time > qm_dict['freq_optimize_time']:
                additional_time = optimize_frequency_during_experiment(opt_dict=optimize_freq_dict, qm_dict=qm_dict)
                start_time = start_time + additional_time
                freq_optimize_real_time = time.time()

        ####################### analyze data ######################
        if (analysis_method and qm_dict['update_time']) is not None:
            if time.time() - real_update_time > qm_dict['update_time']:
                analysis_method()
                real_update_time = time.time()

        if 'autosave_s' in qm_dict.keys():
            if t_last_save is None:
                t_last_save = time.time()
            if time.time() - t_last_save > qm_dict['autosave_s'] and qm_dict['autosave_s'] > 0:
                save_tag = f"{qmeas['name']}_i{idx_last_save:04d}"
                pulsedmasterlogic.save_measurement_data(save_tag, True)
                idx_last_save += 1
                t_last_save = time.time()

        if handle_abort():
            user_terminated = True
            break

        idx_loop += 1

        # warning: debuging in this loop seems to slow down gui
        #logger.debug(
        #    "in mes loop: pulsedMesLogic.n_sweeps {}/{}".format(pulsedmasterlogic.pulsedmeasurementlogic().elapsed_sweeps,
        #                                                        qm_dict['n_sweeps']))

    logger.debug("Breaking control mes loop at i= {}".format(idx_loop))
    #time.sleep(0.2)
    return user_terminated


def perform_measurement_on_condition(qm_dict):
    # set up
    set_up_conventional_measurement(qm_dict)
    fit_data, fit_result = control_measurement_on_condition(qm_dict)
    #save_parameters(save_tag='Condition', save_dict=qm_dict)
    #return pulsedmasterlogic.fit_container
    return fit_data, fit_result


def control_measurement_on_condition(qm_dict):
    pulsedmasterlogic.break_var = False
    # FIXME: ADD the Options for optical and microwave optimization
    if ('fit_method' or 'threshold_parameter' or 'fit_threshold') not in qm_dict:
        pulsedmasterlogic.log.error('Not enough parameters specified for measurement on condition!')
        cause_an_error
    pulsedmasterlogic.toggle_pulsed_measurement(True)
    while not pulsedmasterlogic.status_dict['measurement_running']: time.sleep(0.5)
    # before the first fit wait so that there is actually some data
    time.sleep(pulsedmasterlogic.timer_interval * 1.5)
    fit_value = 1e18
    # if the fit_value is below 1e-15, there is something funny
    while fit_value > qm_dict['fit_threshold'] or fit_value < 1e-15:
        if not all(points == 0 for points in pulsedmasterlogic.signal_data[1]):
            time.sleep(pulsedmasterlogic.timer_interval)
            try:
                fit_data, fit_result = pulsedmeasurementlogic.do_fit(qm_dict['fit_method'])
                fit_value = fit_result.result_str_dict[qm_dict['threshold_parameter']]['value']
                if 'normalize_threshold_parameter' in qm_dict and qm_dict['normalize_threshold_parameter']:
                    fit_value = fit_value / np.mean(pulsedmasterlogic.signal_data[1]) ** 2
                    pulsedmasterlogic.log.info(fit_value)
            except: pass
            # user can break it
            if not pulsedmasterlogic.status_dict['measurement_running']: break
    # stop the measurement
    pulsedmasterlogic.toggle_pulsed_measurement(False)
    while pulsedmasterlogic.status_dict['measurement_running']: time.sleep(0.5)
    return fit_data, fit_result


def external_mw_measurement(qm_dict):
    #set up
    set_up_conventional_measurement(qm_dict)
    pulsedmasterlogic.set_extraction_settings({'method': 'threshold'})
    pulsedmasterlogic.set_ext_microwave_settings(frequency=qm_dict['mw_frequency'], power=qm_dict['mw_power'],
                                                 use_ext_microwave=True)
    pulsedmasterlogic.toggle_ext_microwave(True)
    # perform measurement
    pulsedmasterlogic.toggle_pulsed_measurement(True)
    while not pulsedmasterlogic.status_dict['measurement_running']: time.sleep(0.5)
    user_terminated = control_measurement(qm_dict, analysis_method=None)
    pulsedmasterlogic.toggle_pulsed_measurement(False)
    while pulsedmasterlogic.status_dict['measurement_running']: time.sleep(0.5)
    pulsedmasterlogic.toggle_ext_microwave(False)
    return user_terminated



#########################################  Save methods ############################################

def save_parameters(save_tag='', save_dict=None, subdir=None, timestamp=None):

    global save_subdir
    if timestamp is None:
        timestamp = datetime.datetime.now()

    if save_tag is None:
        return  # don't save anything

    if save_dict is None:
        save_dict = OrderedDict()


    if not save_dict['sequence_mode']:
        sequence = pulsedmasterlogic.saved_pulse_block_ensembles.get(save_dict['name'])
    else:
        sequence = pulsedmasterlogic.saved_pulse_sequences.get(save_dict['name'])
    # get measurement information
    meas_info = sequence.measurement_information
    # get sampling information
    samp_info = sequence.sampling_information

    # get fastcounter settings
    fc_dict = pulsedmasterlogic.fast_counter_settings

    final_dict = {'parameters': save_dict, 'measurementinfo': meas_info,
                  'sampling_info': samp_info, 'fastcounter_settings': fc_dict}

    signal_dict = {'dummyData': [-1]}

    try:
        filepath = savelogic.get_path_for_module('PulsedMeasurement')

        if save_subdir is not None:
            filepath = filepath + '/' + save_subdir + '/'
        if subdir is not None:
            filepath = filepath + '/' + subdir + '/'
            if save_subdir is not None:
                logger.warning(f"Overwriting global save subdir {save_subdir} by function param: {subdir}")

        savelogic.save_data(signal_dict, timestamp=timestamp,
                            parameters=final_dict, fmt='%.15e',
                            filepath=filepath,
                            filelabel=save_tag + '_parameters',
                            delimiter='\t', plotfig=None)
    except Exception as e:
        logger.exception("Error while saving logic essential parameters: {}")
    return


# def save_qdyne_measurement(save_tag):
#
#     parameters = qmeas
#     analysis_dict = read_and_analyse_lst_file()
#
#     if not qmeas['show_full']:
#         plt.style.use(savelogic.mpl_qd_style)
#         fig, ax = plt.subplots(1, 1)
#         ax.plot(analysis_dict['ft_freqs'], analysis_dict['ft_result'], 'o', color='blue',
#                 linestyle=':', linewidth=0.5, label='FFT signal')
#         ax.plot(analysis_dict['fit_freqs'], analysis_dict['fit_result'], '-', color='red',
#                 linestyle='-', linewidth=1, label='FFT signal')
#         ax.set_xlabel('freq')
#         ax.set_ylabel('signal')
#         fig.tight_layout()
#
#         parameters['fit parameters see here'] = ''
#         parameters.update(analysis_dict['fit_params'])
#         del analysis_dict['fit_params']
#         savelogic.save_data(analysis_dict, timestamp=qmeas['timestamp'], parameters=parameters, fmt='%.15e',
#                             filepath=savelogic.get_path_for_module('T1_qdyne'), filelabel=save_tag, filetype='npz',
#                             delimiter='\t', plotfig=fig)
#     else:
#         savelogic.save_data(analysis_dict, timestamp=qmeas['timestamp'], parameters=parameters, fmt='%.15e',
#                             filepath=savelogic.get_path_for_module('T1_qdyne'), filelabel=save_tag, filetype='npz',
#                             delimiter='\t', plotfig=None)
#     return






######################################## Position optimize and laser functions #########################################

def sleep_until_abort(condition_str, dt_s=0.2, timeout_s=-1):
    timed_out = False
    user_abort_code = 0

    t_start = time.time()
    while eval(condition_str) and user_abort_code == 0 and not timed_out:
        time.sleep(dt_s)
        if timeout_s >= 0 and t_start - time.time() > timeout_s:
            timed_out = True
            logger.warning("Timed out while waiting for {}".format(condition_str))
        user_abort_code = handle_abort()

def wait_for_cts(min_cts=10e3, timeout_s=2):

    # todo: waiting like this freezes qudi manager

    high_cts = False
    t_start = time.time()

    while time.time() - t_start < timeout_s:
        # will stop on calling .save_data())

        #counterlogic.start_saving()
        timeserieslogic.start_reading()
        time.sleep(0.1)
        logger.debug("Waiting for counts...")
        try:

            #data_array, parameters = counterlogic.save_data(to_file=False)
            #data_array = np.array(data_array)[:, 1]
            data_array = timeserieslogic.trace_data[1].values()
            last_cts = list(data_array)[0][-1]

            if last_cts > min_cts:
                high_cts = True
                logger.debug("Waited {:.2f} s for {}>{} counts".format(time.time() - t_start,
                                                                   last_cts, min_cts))
                break
        except Exception as e:
            logger.warning("Couldn't read from counter: {}".format(str(e)))
            return

    if not high_cts:
        logger.warning("Timed out while waiting for high counts.")

def optimize_position(optimize_ch=''):
    # FIXME: Add the option to pause pulsed measurement during position optimization
    # add: check if counts

    time_start_optimize = time.time()
    try:

        #pulsedmeasurementlogic.fast_counter_pause()
        if optimize_ch is None:
            logger.info(f"Optimization with laser ch: {setup['optimize_channel']}")
            nicard.digital_channel_switch(setup['optimize_channel'], mode=True)
        elif optimize_ch is '':
            logger.debug("No opt_ch optimization")
            pass
        else:
            logger.debug(f"Optimization with laser ch: {optimize_ch}")
            nicard.digital_channel_switch(optimize_ch, mode=True)

        wait_for_cts()

        # perform refocus
        scannerlogic.stop_scanning()
        time.sleep(0.2)
        crosshair_pos = scannerlogic.get_position()
        optimizerlogic.start_refocus(initial_pos=crosshair_pos)

        sleep_until_abort("optimizerlogic.module_state() != 'idle'", timeout_s=10)

        if abs(optimizerlogic.optim_pos_x - crosshair_pos[0])  > 1e-6 or \
            abs(optimizerlogic.optim_pos_y - crosshair_pos[1]) > 1e-6 or \
            abs(optimizerlogic.optim_pos_z - crosshair_pos[2]) > 1e-6:
                optimize_position()
                logger.debug("Repeating optimization")
        else:

            scannerlogic.set_position('optimizer', x=optimizerlogic.optim_pos_x, y=optimizerlogic.optim_pos_y,
                                  z=optimizerlogic.optim_pos_z, a=0.0)
            time.sleep(0.5)
            # switch off laser
            #logger.debug("Laser off")
            #nicard.digital_channel_switch(setup['optimize_channel'], mode=False)
            # pulsedmeasurementlogic.fast_counter_continue()

        time_stop_optimize = time.time()
        additional_time = (time_stop_optimize - time_start_optimize)

        if optimize_ch is not '':
            nicard.digital_channel_switch(setup['optimize_channel'], mode=False)

    except:
        logger.exception(f"Optimization failed: ")

    return additional_time


def optimize_poi(poi, update_shift=False):
    # FIXME: Add the option to pause pulsed measurement during position optimization
    time_start_optimize = time.time()
    #pulsedmeasurementlogic.fast_counter_pause()
    laser_on()
    logger.debug("Laser on, sleeping before count wait")
    time.sleep(1)
    wait_for_cts(min_cts=1e3, timeout_s=10)
    time.sleep(1)
    # perform refocus
    if poi:
        poimanagerlogic.go_to_poi(poi)
    poimanagerlogic.optimise_poi_position(poi, update_roi_position=update_shift)


    logger.debug("Waiting for track to finish")
    sleep_until_abort("optimizerlogic.module_state() != 'idle'", timeout_s=10)
    logger.debug("Done")

    scannerlogic.set_position('optimizer', x=optimizerlogic.optim_pos_x, y=optimizerlogic.optim_pos_y,
                              z=optimizerlogic.optim_pos_z, a=0.0)

    # switch off laser
    logger.debug("Laser off")
    nicard.digital_channel_switch(setup['optimize_channel'], mode=False)
    # pulsedmeasurementlogic.fast_counter_continue()
    time_stop_optimize = time.time()
    additional_time = (time_stop_optimize - time_start_optimize)


    return additional_time



def laser_on(pulser_on=True):

    laser_on_awg()
    # Turns on the laser via nicard. If pulser_on the pulser is not stopped
    #nicard.digital_channel_switch(setup['optimize_channel'], mode=True)
    return

def laser_on_awg():
    # loads a waveform to awg that contionously enables laser marker
    # Caution: stops any waveform currently played!
    # waveform must be already in workspace of awg!
    pg = pulsedmasterlogic.pulsedmeasurementlogic().pulsegenerator()

    logger.debug("Stop pg")
    pulsedmasterlogic.toggle_pulse_generator(False)
    logger.debug("Done. Set active ch.")
    pg.set_active_channels({'a_ch1':True, 'a_ch2':True})
    logger.debug("Done. Load wave.")
    pg.load_waveform({1: 'laser_on_ch1', 2: 'laser_on_ch2'})
    logger.debug("Done. Start pg")
    pulsedmasterlogic.toggle_pulse_generator(True)
    logger.debug("Done.")

def laser_off(pulser_on=False):
    # Switches off the laser trigger from nicard
    pulsedmasterlogic.toggle_pulse_generator(pulser_on)
    #nicard.digital_channel_switch(setup['optimize_channel'], mode=False)
    return


######################################## Microwave frequency optimize functions #########################################


def optimize_frequency_during_experiment(opt_dict, qm_dict):
    # FIXME: Add the moment only working for conventional measurements
    time_start_optimize = time.time()

    if 'freq_optimization_method' not in opt_dict:
        pulsedmasterlogic.log.error('Not frequency optimization method specified. Cannot run optimization')
        return -1

    # stop pulsed measurement and stash raw data
    pulsedmasterlogic.toggle_pulsed_measurement(False, qm_dict['name'])
    #pulsedmasterlogic.toggle_pulsed_measurement(False)
    while pulsedmasterlogic.status_dict['measurement_running']: time.sleep(0.2)
    # set the frequency optimization interval to None
    opt_dict['freq_optimize_time'] = None
    # generate sequence, upload it, set the parameters and run optimization experiment
    do_experiment(experiment=opt_dict['freq_optimization_method'], qm_dict=opt_dict, meas_type=conventional_measurement,
                  meas_info=add_conventional_information,
                  generate_new=opt_dict['generate_new'], save_tag=opt_dict['save_tag'])
    # perform a final fit
    fit_data, fit_result = pulsedmeasurementlogic.do_fit(opt_dict['optimize_fit_method'])
    # update the specified parameters
    for key in opt_dict['parameters2update']:
        qm_dict[opt_dict['parameters2update'][key]] = fit_result.best_values[key]
    # generate, sample and upload the new sequence
    prepare_qm(experiment=qm_dict['experiment'], qm_dict=qm_dict, generate_new=True)
    pulsedmasterlogic.do_fit('No Fit')
    # restart experiment and use stashed data
    pulsedmasterlogic.toggle_pulsed_measurement(True, qm_dict['name'])
    #pulsedmeasurementlogic.toggle_pulsed_measurement(True, qm_dict['name'])
    #pulsedmasterlogic.toggle_pulsed_measurement(True)
    while not pulsedmasterlogic.status_dict['measurement_running']: time.sleep(0.2)
    return time.time()-time_start_optimize


def optimize_frequency(opt_dict):
    # Generate a new dictionary with the measurement parameters
    if 'mw_optimization_method' not in opt_dict:
        pulsedmasterlogic.log.error('Not frequency optimization method specified. Cannot run optimization')
        return -1

    # generate sequence, upload it, set the parameters and run optimization experiment
    do_experiment(experiment=opt_dict['mw_optimization_method'], qm_dict=opt_dict, meas_type=opt_dict['meas_type'],
                  meas_info=add_conventional_information,
                  generate_new=opt_dict['optimize_generate_new'], save_tag = opt_dict['save_tag'])
    # perform a final fit
    fit_data, fit_result = pulsedmeasurementlogic.do_fit(opt_dict['optimize_fit_method'])
    # FIXME:
    # generate, sample and upload the new sequence
    return fit_result


########################################## Qdyne Analysis functions #########################################################

# FIXME:
# def read_and_analyse_lst_file(type='qdyne'):
#     if type == 'qdyne':
#         headerlength = 89
#         read_dict = pulseextractionlogic.ungated_qdyne_conventional(qmeas['full_list_name'], headerlength=headerlength,
#                                                                     read_lines=pulseextractionlogic.read_lines,
#                                                                     lines_to_read=None,
#                                                                     time_trace=pulseextractionlogic.time_trace)
#         pulseextractionlogic.read_lines = read_dict['read_lines']
#         pulseextractionlogic.time_trace = read_dict['time_trace']
#
#         analysis_dict = pulseanalysislogic.analyse_qdyne_fft(time_trace=pulseextractionlogic.time_trace,
#                                                              range_around_peak=40)
#         analysis_dict['time_trace'] = read_dict['time_trace']
#
#     elif type == 'qdyne_ssr':
#         time_trace = extract_ssr_qdyne_time_trace(traceanalysislogic.count_trace)
#         time_trace = time_trace - np.mean(time_trace)
#         analysis_dict = pulseanalysislogic.analyse_qdyne_fft(time_trace=time_trace, range_around_peak=40,
#                                                              meas_type=type)
#         analysis_dict['time_trace'] = time_trace
#
#     if len(analysis_dict['ft_freqs_whole']) > 1:
#         if qmeas['show_full']:
#             qdplotlogic.set_data([analysis_dict['ft_freqs_whole']], [analysis_dict['ft_result_whole']])
#         else:
#             lorentz_fit = fitlogic.make_lorentzian_fit(x_axis=analysis_dict['ft_freqs'], data=analysis_dict['ft_result'],
#                                                        estimator=fitlogic.estimate_lorentzian_peak)
#             model, params = fitlogic.make_lorentzian_model()
#             analysis_dict['fit_freqs'] = np.linspace(np.min(analysis_dict['ft_freqs']), np.max(analysis_dict['ft_freqs']),
#                                                      1000)
#             analysis_dict['fit_result'] = model.eval(x=analysis_dict['fit_freqs'], params=lorentz_fit.params)
#             analysis_dict['fit_params'] = lorentz_fit.best_values
#             qdplotlogic.set_data([analysis_dict['ft_freqs'],analysis_dict['fit_freqs']],
#                                  [analysis_dict['ft_result'],analysis_dict['fit_result']])
#
#     qdplotlogic.set_domain()
#     qdplotlogic.set_range()
#
#     return analysis_dict
#
#
# #FIXME
# def read_and_save_time_trace(save_path, save_path_info=None, start_line=None, lines_to_read=None):
#
#     headerlength = 89
#
#
#     if start_line is None:
#         start_line = 1
#     # read file
#     read_dict = pulseextractionlogic.ungated_qdyne_conventional(qmeas['full_list_name'], headerlength=headerlength,
#                                                                 read_lines=start_line-1,
#                                                                 lines_to_read=lines_to_read)
#
#     # save time trace as .npz file
#     np.savez_compressed(save_path, np.array(read_dict['time_trace']))
#
#     read_lines = read_dict['read_lines']
#     read_whole_file = read_dict['read_whole_file']
#     # save info for the time trace
#     if save_path_info != None:
#         with open(save_path_info, 'a') as infofile:
#             infofile.write(save_path + ': ' + str(read_dict['number_of_sweeps']) + ' sweeps \n')
#             infofile.write('read lines of list file: ' + str(read_lines) + '\n')
#             infofile.write('finished to read whole file ')
#             infofile.write(str(read_whole_file))
#             infofile.write('\n \n')
#
#     return read_whole_file, read_lines







################################## Automized measurements for a list of NV centers #####################################


def do_automized_measurements(qm_dict, autoexp):

    # If there is not list of pois specified, take all pois from the current roi
    if not qm_dict['list_pois']:
        qm_dict['list_pois'] = poimanagerlogic.poi_names
        # remove 'crosshair' and 'sample'
        qm_dict['list_pois'].remove('crosshair')
        qm_dict['list_pois'].remove('sample')

    # check if for the first poi new sequences should be generated
    first_poi = qm_dict['generate_new']
    # loop over all the pois
    for poi in qm_dict['list_pois']:
        if handle_abort() is 1:
            break       # next is handled in inner loop
        # move to current poi and optimize position
        if not poi == "":
            logger.info("Autopilot moving to poi {}".format(poi))
            poi_name = poi
            poimanagerlogic.go_to_poi(poi_name)
        else:
            logger.debug("Skipped moving to poi, setting no_optimize")
            qm_dict['no_optimize'] = True
            poi_name = '<current pos>'

        if not 'no_optimize' in qm_dict.keys():
            qm_dict['no_optimize'] = False
        if not qm_dict['no_optimize']:
            optimize_poi(poi_name)

        # perform all experiments
        for experiment in autoexp:
            logger.info("Starting experiment: {} on {}".format(experiment, poi_name))
            logger.debug("Auto exp settings: {}".format(autoexp[experiment]))
            cur_exp_dict = autoexp[experiment]
            if handle_abort() is 1:
                break
            if handle_abort() is 2:
                continue


            # perform the measurement
            try:
                savetag, save_subdir_nv = "", ""
                try:
                    savetag = cur_exp_dict['savetag'] if cur_exp_dict['savetag'] else ""
                except: pass
                savetag = cur_exp_dict['name'] if not savetag else savetag
                if not poi == "":
                    savetag += "_nv_" + poi
                    save_subdir_nv = "nv_" + poi

                logger.debug(f"Savetag {savetag}, subdir {save_subdir}")

                if first_poi:
                    do_experiment(experiment=cur_exp_dict['type'], qm_dict=cur_exp_dict,
                                  meas_type=cur_exp_dict['meas_type'], meas_info=cur_exp_dict['meas_info'],
                                  generate_new=True, save_tag=savetag, save_subdir=save_subdir_nv)
                else:
                    try:
                        generate_new = cur_exp_dict['generate_new']
                    except: generate_new = True
                    do_experiment(experiment=cur_exp_dict['type'], qm_dict=cur_exp_dict,
                                  meas_type=cur_exp_dict['meas_type'], meas_info=cur_exp_dict['meas_info'],
                                  generate_new=generate_new,
                                  save_tag=savetag, save_subdir=save_subdir_nv)
            except:
                logger.exception("Error during measurement: ")

            # fit and update parameters
            if 'fit_experiment' in cur_exp_dict:
                if cur_exp_dict['fit_experiment'] != '':
                    try:
                        fit_data, fit_result = pulsedmeasurementlogic.do_fit(cur_exp_dict['fit_experiment'])
                        #pulsedmasterlogic.do_fit(cur_exp_dict['fit_experiment'])
                        # while pulsedmasterlogic.status_dict['fitting_busy']: time.sleep(0.2)
                        #time.sleep(1)
                        #fit_dict = pulsedmasterlogic.fit_container.current_fit_result.result_str_dict
                        #fit_para = fit_dict[cur_exp_dict['fit_parameter']]['value']
                        #fit_para = fit_result.best_values[cur_exp_dict['fit_parameter']]

                        fit_para = fit_result.result_str_dict[cur_exp_dict['fit_parameter']]['value']
                    except Exception as e:
                        logger.warning("Couldn't perform fit: {}".format(str(e)))
                        fit_para = None

                    if 'update_parameters' in cur_exp_dict:
                        """
                              example how to update parameters in next experiment:
                              qexp['update_parameters'] 
                                    =   {'Rabi': 'microwave_frequency',
                                         'pODMR_fine': {'target_name': 'freq_start',
                                                    'func': f"_x_ - 0.5*({qexp['freq_step']}*{qexp['num_of_points']})"}
                            }
                                        
                        """
                        try:
                            for key_nextexp in cur_exp_dict['update_parameters']:
                                try:
                                    offset = cur_exp_dict['fit_offset'][key_nextexp]
                                except:  offset = 0
                                try:
                                    fact = cur_exp_dict['fit_factor'][key_nextexp]
                                except: fact = 1
                                try:
                                    fit_para = (fact * fit_para) + offset

                                    update_rule = cur_exp_dict['update_parameters'][key_nextexp]
                                    if type(update_rule) == str:
                                        key_param = update_rule
                                        val = fit_para

                                    elif type(update_rule) == dict:
                                        key_param = update_rule['target_name']
                                        func_str = update_rule['func']
                                        # replace "_x_" (the fit result) with str for eval()
                                        func_str = func_str.replace("_x_", "fit_para")
                                        try:
                                            val = eval(func_str)
                                        except:
                                            logger.exception(f"Failed to evaluate update rule: {func_str}")
                                    else:
                                        logger.warning(f"Didn't understand update rule {update_rule} for exp {key_nextexp}")

                                    autoexp[key_nextexp][key_param] = val
                                    logger.info("Updating {}= {} for exp {}".format(key_param, val, key_nextexp))
                                except Exception as e:
                                    logger.warning("Failed to update next parameter for {}: {}".format(key_nextexp, str(e)))
                        except Exception as e:
                            logger.warning("Couldn't update params: {}".format(str(e)))
                    else:
                        logger.debug("Didn't find any update parameters in {}".format(cur_exp_dict['name']))
            try:
                if handle_abort() != 0:
                    continue
                if qm_dict['optimize_between_experiments']:
                    if 'optimize_on_poi' in qm_dict.keys():
                        opt_poi = qm_dict['optimize_on_poi']
                        logger.info(f"Moving to poi {opt_poi} to optimize for sample shift tracking")
                    else:
                        opt_poi = poi
                    optimize_poi(opt_poi, update_shift=True)
                    if opt_poi != poi:
                        logger.info(f"Back to and optimize on poi {poi}")
                        optimize_poi(poi, update_shift=False)
            except: pass
        first_poi = False

    logger.info("Autopilot has landed.")
    return



################################## Magnet movement #########################################

def get_magnet_pathway(x_range, x_step, y_range, y_step):
    # check if magnet gui and logic are loaded, otherwise load

    position_before = magnet_logic.get_pos()

    # set up pathway and GUI
    pathway, backmap = magnet_logic._create_2d_pathway('x', x_range, x_step, 'y', y_range, y_step, position_before)
    x_start = backmap[0]['x']
    y_start = backmap[0]['y']
    prepared_graph = magnet_logic._prepare_2d_graph(x_start, x_range, x_step, y_start, y_range, y_step)
    magnet_logic._2D_data_matrix, magnet_logic._2D_axis0_data, magnet_logic._2D_axis1_data = prepared_graph
    magnet_logic._2D_add_data_matrix = np.zeros(shape=np.shape(magnet_logic._2D_data_matrix), dtype=object)
    # handle the stupid crosshair
    magnetgui.roi_magnet.setSize([x_range / 10, y_range / 10], True)
    magnetgui.roi_magnet.setPos([position_before['x'], position_before['y']])

    return pathway, backmap, position_before



#################################### arbitrary sequence generation method ##################

def generate_sequence(name, info_dict, rotating_frame = False):
    created_sequences = list()
    element_list = list()
    # generate the indvidual blocks and ensemple and generate sequence
    for block in info_dict:
        #first generate the blocks and ensemples
        pulsedmasterlogic.generate_predefined_sequence(info_dict[block]['method'],info_dict[block]['meas_dict'])
        while info_dict[block]['meas_dict']['name'] not in pulsedmasterlogic.saved_pulse_block_ensembles: time.sleep(0.2)
        # Add the sequence information:
        seq_para = customize_seq_para(info_dict[block]['seq_para'])
        element_list.append([block,seq_para])

    sequence = PulseSequence(name=name, ensemble_list = element_list, rotating_frame = rotating_frame)

    created_sequences.append(sequence)
    return created_sequences



def customize_seq_para(seq_para_dict):
    if 'event_trigger' not in seq_para_dict:
        seq_para_dict['event_trigger'] = 'OFF'
    if 'event_jump_to' not in seq_para_dict:
        seq_para_dict['event_jump_to'] = 0
    if 'wait_for' not in seq_para_dict:
        seq_para_dict['wait_for'] = 'OFF'
    if 'repetitions' not in seq_para_dict:
        seq_para_dict['repetitions'] = 1
    if 'go_to' not in seq_para_dict:
        seq_para_dict['go_to'] = 0
    return seq_para_dict


def write_sequence(sequence_name, sequence_param_list=None, load=True):

    if sequence_param_list is None:
        # get the sequence information if necessary
        sequence_param_list = get_sequence_parameter_list(sequence_name)

    sequencegeneratorlogic.pulsegenerator().write_sequence(sequence_name,
                                    sequence_param_list)
    time.sleep(0.2)
    if load:
        sequencegeneratorlogic.load_sequence(sequence_name)
    return


def get_sequence_parameter_list(sequence_name):
    # get the sequence information
    sequence = sequencegeneratorlogic.get_sequence(sequence_name)
    sequence_param_list = list()
    for step_index, seq_step in enumerate(sequence):
        ensemble_name = sequence.sampling_information['step_waveform_list'][step_index]
        sequence_param_list.append((tuple(ensemble_name), seq_step))
    return sequence_param_list







############################### old method which are currently not used but might be helpful ######################

# def generate_sample_upload(experiment, qmeas_dict):
#     pulsedmasterlogic.generate_predefined_sequence(experiment, qmeas_dict)
#     pulsedmasterlogic.sample_ensemble(qmeas_dict['name'], True)
#     time_tmp = time.time()
#     tries = 0
#     #tries2 = 0
#     while pulsedmasterlogic.status_dict['sampload_busy']:
#         time.sleep(0.1)
#         # unfortunately the software hangs up from time to time. Check if it is already uploaded
#         if time.time() - time_tmp > 10:
#             if qmeas_dict['name'] + '_ch1' in pulsedmasterlogic.sampled_waveforms:
#                 pulsedmasterlogic.status_dict['sampload_busy'] = False
#             time_tmp = time.time()
#             tries = tries + 1
#             # if the upload did not work, try everything again
#             if tries > 2:
#                 tries= 0
#                 pulsedmasterlogic.status_dict['sampload_busy'] = False
#                 generate_sample_upload(experiment, qmeas_dict)
#     return


# #FIXME:
# def set_fastcounter_general(gated, fc_binwidth, length, delay_start=0, save_mode = 0, counts_per_readout=None,
#                                countlength = None, sequences=None, filename=None):
#
#     pulsedmeasurementlogic.fastcounter().change_sweep_mode(gated, countlength, counts_per_readout)
#
#     if gated:
#         # First reduce length to prevent crashes
#         pulsedmasterlogic.set_fast_counter_settings(bin_width=6.4e-9, record_length=100e-9)
#         time.sleep(0.5)
#         # put cycles and preset again. Otherwise for some reason cycles is reset to 1
#
#         singleshotlogic.set_ssr_counter_settings({'countlength': countlength, 'counts_per_readout': counts_per_readout})
#     else:
#         pulsedmasterlogic.set_fast_counter_settings(bin_width=fc_binwidth, record_length=length)
#     time.sleep(0.05)
#
#     pulsedmeasurementlogic.fastcounter().set_delay_start(delay_start)
#     pulsedmeasurementlogic.fastcounter().change_save_mode(save_mode)
#     if filename is not None:
#         pulsedmeasurementlogic.fastcounter().change_filename(filename)
#     return

