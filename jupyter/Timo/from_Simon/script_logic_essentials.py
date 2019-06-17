from collections import OrderedDict
import numpy as np
import time
import datetime
import matplotlib.pyplot as plt
from core.util import units
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.user_globals import UserGlobals

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


### dummy hardware for development ###
"""
# can't do this -> load dummy hardware module via config
def build_nidaq_dummy():

    from hardware.nicard_dummy import NicardDummy
    return NicardDummy(manager, 'nidaq')
"""


############################################ Static hardware parameters ################################################

# static hardware parameters:
setup = OrderedDict()
setup['gated'] = False
setup['sampling_freq'] = pulsedmasterlogic.pulse_generator_settings['sample_rate']
setup['bin_width'] = 4.0e-9
setup['wait_time'] = 1.0e-6
setup['laser_delay'] = 510e-9
setup['laser_safety'] = 200e-9

if setup['gated']:
    setup['sync_channel'] = ''
    setup['gate_channel'] = 'd_ch1'
else:
    setup['sync_channel'] = 'd_ch1'
    setup['gate_channel'] = ''

setup['laser_channel'] = 'd_ch2'

setup['laser_length'] = 3e-6
setup['wait_length'] = 1e-6
setup['trigger_length'] = 20e-9

setup['delay_length'] = setup['laser_delay'] - 30e-9#450e-9

setup['channel_amp'] = 1.0
setup['microwave_channel'] = 'a_ch1'
setup['optimize_channel'] = '/Dev1/PFI9'

setup['readout_end'] = 0.5e-6

setup['max_tau'] = 1e-3
setup['max_tau_start'] = 1e-3
setup['max_rabi_period'] = 1e-3
setup['min_microwave_frequency'] = 1
setup['max_microwave_amplitude'] = 0.25

setup['measurement_time'] = 600
setup['optimize_time'] = 300
setup['freq_optimize_time'] = None
setup['analysis_interval'] = 3



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
    userglobals
except NameError:
    try:
        manager.loadConfigureModule('logic', 'userglobals')
    except Exception as e:
        logger.error("Auto module loading failed. Defined in config? {}".format(e))
try:
    userglobals.abort.clear()
    userglobals.next.clear()
except NameError:
    pass


def config_matplotlib_jupyter():
    # is overwritten by qudi save logic
    # does impact local plotting from jupyter (?)
    import matplotlib
    matplotlib.pylab.rcParams['figure.figsize'] = (7.5, 5)

    pass

############################## Standard function for conventional and SSR measurements #################################


def do_experiment(experiment, qm_dict, meas_type, meas_info, generate_new=True, save_tag='',
                  load_tag='', sleep_time = 0.2):
    """
    :param save_tag: different from qudi: if == None, don't save anything.
    :return:
    """
    # add information necessary for measurement type
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

    logger.debug("Debug: do_experiment pulsedMesLogic.n_sweeps / next.is_set / abort.is_set: {}, {}, {}".format(
                pulsedmasterlogic.pulsedmeasurementlogic().elapsed_sweeps, userglobals.next.is_set(),
                userglobals.abort.is_set()))

    user_terminated = False
    if not userglobals.next.is_set() and not userglobals.abort.is_set():
        # prepare the measurement by generating and loading the sequence/waveform
        prepare_qm(experiment, qm_dict, generate_new)
        # perform measurement
        user_terminated = perform_measurement(qm_dict=qm_dict,meas_type=meas_type, load_tag=load_tag, save_tag=save_tag)

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
    qm_dict['gated'] = False
    qm_dict['sequence_mode'] = False
    return qm_dict


###################################  Upload and set parameters functionality #######################################


def prepare_qm(experiment, qm_dict,  generate_new = True):
    ###### Prepare a quantum measurement by generating the sequence and loading it up to the pulser
    if generate_new:
        generate_sample_upload(experiment, qm_dict)
    else:
        load_into_channel(qm_dict['name'], sequence_mode=qm_dict['sequence_mode'])
        try:
            qm_dict.update(memory_dict[qm_dict['name']])
        except:
            pulsedmasterlogic.log.error('Experiment parameters are not known. Needs to be generate newly.')
            return cause_an_error
    if not qm_dict['sequence_mode']:
        qm_dict['sequence_length'] = \
            pulsedmasterlogic.get_ensemble_info(pulsedmasterlogic.saved_pulse_block_ensembles[qm_dict['name']])[0]
    else:
        qm_dict['sequence_length'] = \
            pulsedmasterlogic.get_sequence_info(pulsedmasterlogic.saved_pulse_sequences[qm_dict['name']])[0]
    # Set the parameters
    set_parameters(qm_dict)
    return qm_dict


def customise_setup(dictionary):
    #final_dict = dictionary
    for key in setup.keys():
        if key not in dictionary.keys():
            dictionary[key] = setup[key]
    # get a subdictionary with the generation parameters and set them
    subdict = dict([(key, dictionary.get(key)) for key in pulsedmasterlogic.generation_parameters if key in dictionary])
    pulsedmasterlogic.set_generation_parameters(subdict)
    return dictionary

def generate_sample_upload(experiment, qm_dict):
    qm_dict = customise_setup(qm_dict)
    if not qm_dict['sequence_mode']:
        # make sure a previous ensemble is deleted
        pulsedmasterlogic.delete_block_ensemble(qm_dict['name'])
        try:
            pulsedmasterlogic.generate_predefined_sequence(experiment, qm_dict.copy())
        except:
            pulsedmasterlogic.log.error('Generation failed')
            return cause_an_error
        time.sleep(0.2)
        # sample the ensemble
        while pulsedmasterlogic.status_dict['predefined_generation_busy']: time.sleep(0.2)
        if qm_dict['name'] not in pulsedmasterlogic.saved_pulse_block_ensembles: cause_an_error
        pulsedmasterlogic.sample_ensemble(qm_dict['name'], True)
    else:
        if 'exchange_parts' not in qm_dict or qm_dict['exchange_parts']=={}:
            # make sure a previous sequence is deleted
            pulsedmasterlogic.delete_sequence(qm_dict['name'])
            # generate the ensemble or sequence
            try:
                pulsedmasterlogic.generate_predefined_sequence(experiment, qm_dict.copy())
            except:
                pulsedmasterlogic.log.error('Generation failed')
                return cause_an_error
            # sample the sequence
            time.sleep(0.2)
            while pulsedmasterlogic.status_dict['predefined_generation_busy']: time.sleep(0.2)
            if qm_dict['name'] not in pulsedmasterlogic.saved_pulse_sequences: cause_an_error
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
                while pulsedmasterlogic.status_dict['predefined_generation_busy']: time.sleep(0.2)
                if name not in pulsedmasterlogic.saved_pulse_block_ensembles: cause_an_error
                pulsedmasterlogic.sample_ensemble(name, True)
                while pulsedmasterlogic.status_dict['sampload_busy']: time.sleep(0.2)
            # load the sequence
            # generate
            write_sequence(sequence_name=qm_dict['name'], sequence_param_list=None, load=True)

    # wait till sequence is sampled
    while pulsedmasterlogic.status_dict['sampload_busy']: time.sleep(0.2)
    return


def load_into_channel(name, sequence_mode):
    # upload ensemble to pulser channel with sanity check
    if sequence_mode:
        if name in pulsedmasterlogic.sampled_sequences:
            pulsedmasterlogic.load_sequence(name)
        else:
            pulsedmasterlogic.log.error('Sequence not found. Cannot load to channel')
    else:
        if name + '_ch1' in pulsedmasterlogic.sampled_waveforms:
            pulsedmasterlogic.load_ensemble(name)
        else:
            pulsedmasterlogic.log.error('Ensemble not found. Cannot load to channel')
    # wait until ensemble is loaded to channel
    while pulsedmasterlogic.status_dict['loading_busy']: time.sleep(0.1)
    return


def set_parameters(qm_dict):

    if not qm_dict['sequence_mode']:
        qm_dict['params'] = pulsedmasterlogic.saved_pulse_block_ensembles.get(qm_dict['name']).measurement_information
    else:
        qm_dict['params'] = pulsedmasterlogic.saved_pulse_sequences.get(qm_dict['name']).measurement_information
    pulsedmasterlogic.set_measurement_settings(qm_dict['params'])

    return qm_dict



############################### Perform Measurement Methods ############################################################


def perform_measurement(qm_dict, meas_type, load_tag='', save_tag='', analysis_interval = None, measurement_time=None,
                        optimize_time=None, freq_optimize_time=None):
    # FIXME: add the possibility to load previous data saved under load_tag
    laser_off(pulser_on = False)
    pulsedmasterlogic.do_fit('No Fit')
    # save parameters into memory_dict
    memory_dict[qm_dict['name']] = qm_dict.copy()
    ###################### Adjust running and refocussing time ##################
    if measurement_time is not None:
        qm_dict['measurement_time'] = measurement_time
    if optimize_time is not None:
        qm_dict['optimize_time'] = optimize_time
    if freq_optimize_time is not None:
        qm_dict['freq_optimize_time'] = freq_optimize_time
    if analysis_interval is not None:
        qm_dict['analysis_interval'] = analysis_interval


    ################ Start and perform the measurement #################
    if not userglobals.abort.is_set() and not userglobals.next.is_set():
        user_terminated = meas_type(qm_dict)
    ########################## Save data ###############################

    # save and fit depending on abort signals
    if userglobals.abort.is_set():
        user_terminated = True
        return user_terminated

    save_parameters(save_tag=save_tag, save_dict=qm_dict)
    # if fit desired
    if 'fit_experiment' in qm_dict and qm_dict['fit_experiment']!= 'No fit':
        fit_data, fit_result = pulsedmeasurementlogic.do_fit(qm_dict['fit_experiment'])
    if save_tag is not None:
        pulsedmasterlogic.save_measurement_data(save_tag, True)
    time.sleep(1)
    return user_terminated

def handle_abort():
    """
    Stops mes and returns true if should be aborted by abort or next signal.
    """

    ret = False

    if userglobals.abort.is_set():
        if pulsedmasterlogic is not None:
            #pulsedmasterlogic.toggle_pulsed_measurement(False)
            pass # handled in control loop
        ret = True
    else:
        ret = False

    if userglobals.next.is_set():
        if pulsedmasterlogic is not None:
            #pulsedmasterlogic.toggle_pulsed_measurement(False)
            pass  # handled in control loop
        userglobals.next.clear()
        ret = True

    if ret:
        logger.debug("handle_abort() received stop signal")

    return ret

def conventional_measurement(qm_dict):


    #set up
    set_up_conventional_measurement(qm_dict)
    # perform measurement
    pulsedmasterlogic.toggle_pulsed_measurement(True)
    while not pulsedmasterlogic.status_dict['measurement_running']:
        time.sleep(0.1)
        logger.debug("Wating for mes to start.")

    'threading also freezes gui'
    #import threading
    #thread = threading.Thread(target=control_measurement, kwargs={"analysis_method":None})
    #thread.start()
    #user_terminated = False # thread doesn't return

    user_terminated = control_measurement(qm_dict, analysis_method=None)

    pulsedmasterlogic.toggle_pulsed_measurement(False)
    while pulsedmasterlogic.status_dict['measurement_running']: time.sleep(0.5)
    return user_terminated

def DEBUG_pulsed_with_result_mes(qm_dict):
    set_up_conventional_measurement(qm_dict)
    # perform measurement
    pulsedmasterlogic.toggle_pulsed_measurement(True)
    while not pulsedmasterlogic.status_dict['measurement_running']: time.sleep(0.5)

    user_terminated = control_measurement(qm_dict, analysis_method=None)
    pulsedmasterlogic.toggle_pulsed_measurement(False)
    while pulsedmasterlogic.status_dict['measurement_running']: time.sleep(0.5)

    mes = pulsedmasterlogic.pulsedmeasurementlogic()
    x = mes.signal_data[0]
    y = mes.signal_data[1]

    logger.debug("pulsed result x {} / y {}".format(x,y))

    return user_terminated


def set_up_conventional_measurement(qm_dict):
    from hardware.fast_counter_dummy import FastCounterDummy

    #if not isinstance(pulsedmeasurementlogic.fastcounter(), FastCounterDummy):
    pulsedmeasurementlogic.fastcounter().change_sweep_mode(False)

    pulsedmasterlogic.set_fast_counter_settings({'bin_width': qm_dict['bin_width'],
                                                 'record_length': qm_dict['params']['counting_length']})
    time.sleep(0.2)
    # add sequence length to measurement dictionary
    #pulsedmasterlogic.set_extraction_settings({'method': 'threshold', 'count_threshold':20, 'min_laser_length':100e-9, 'threshold_tolerance':10e-9})
    pulsedmasterlogic.set_extraction_settings({'method': 'gated_conv_deriv', 'delay': setup['laser_delay'],
                                                'safety': setup['laser_safety']})
    pulsedmasterlogic.set_analysis_settings({'method': 'mean_norm', 'signal_start': 0, 'signal_end': 500e-9,
                                             'norm_start': 1.8e-6, 'norm_end': 2.8e-6})

    #if not isinstance(pulsedmeasurementlogic.fastcounter(), FastCounterDummy):
    pulsedmeasurementlogic.fastcounter().set_delay_start(0)
    pulsedmeasurementlogic.fastcounter().change_save_mode(0)

    t_loop_mes = 2 # for stopping fast by software: 0.001 #s
    logger.warning("Setting mes logic timer interval  to {} s.".format(t_loop_mes))
    pulsedmeasurementlogic.timer_interval = t_loop_mes

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
    while True:

        if 'n_sweeps' in qm_dict:
            # stop by sweeps can't be faster than sleep time
            if qm_dict['n_sweeps'] is not None:
                if pulsedmasterlogic.elapsed_sweeps >= qm_dict['n_sweeps']:
                    # hard break already here for debug
                    pulsedmasterlogic.pulsedmeasurementlogic().stop_pulsed_measurement()
                    logger.debug("stopping mes in control loop {} after {}/{} sweeps".format(idx_loop,
                                                                pulsedmasterlogic.elapsed_sweeps, qm_dict['n_sweeps']))
                    user_terminated = False
                    break

        if qm_dict['measurement_time'] is not None:
            if (time.time() - start_time) > qm_dict['measurement_time']:
                user_terminated = False
                break
        if not pulsedmasterlogic.status_dict['measurement_running']:
            user_terminated = True
            break
        ##################### optimize position #######################
        if qm_dict['optimize_time'] is not None:
            if time.time() - optimize_real_time > qm_dict['optimize_time']:
                additional_time = optimize_position()
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

        if handle_abort():
            user_terminated = True
            break

        time.sleep(0.5) #2
        idx_loop += 1

        # warning: debuging in this loop seems to slow down gui
        #logger.debug(
        #    "in mes loop: pulsedMesLogic.n_sweeps {}/{}".format(pulsedmasterlogic.pulsedmeasurementlogic().elapsed_sweeps,
        #                                                        qm_dict['n_sweeps']))

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

def save_parameters(save_tag='', save_dict=None):

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

    # some empty data file
    signal_dict = OrderedDict()
    signal_dict['None'] = np.array([0])

    savelogic.save_data(signal_dict, timestamp=timestamp,
                        parameters=final_dict, fmt='%.15e',
                        filepath=savelogic.get_path_for_module('PulsedMeasurement'),
                        filelabel=save_tag+ '_parameters',
                        delimiter='\t', plotfig=None)
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

def optimize_position():
    # FIXME: Add the option to pause pulsed measurement during position optimization
    time_start_optimize = time.time()
    #pulsedmeasurementlogic.fast_counter_pause()
    nicard.digital_channel_switch(setup['optimize_channel'], mode=True)
    # perform refocus
    scannerlogic.stop_scanning()
    crosshair_pos = scannerlogic.get_position()
    optimizerlogic.start_refocus(initial_pos=crosshair_pos)
    while optimizerlogic.module_state() == 'idle':
        time.sleep(0.2)
    while optimizerlogic.module_state() != 'idle':
        time.sleep(0.2)

    if abs(optimizerlogic.optim_pos_x - crosshair_pos[0])>1e-6 or \
        abs(optimizerlogic.optim_pos_y - crosshair_pos[1])>1e-6 or \
        abs(optimizerlogic.optim_pos_z - crosshair_pos[2])>1e-6:
        optimize_position()
    else:

        scannerlogic.set_position('optimizer', x=optimizerlogic.optim_pos_x, y=optimizerlogic.optim_pos_y,
                              z=optimizerlogic.optim_pos_z, a=0.0)
        time.sleep(0.5)
        # switch off laser
        nicard.digital_channel_switch(setup['optimize_channel'], mode=False)
        # pulsedmeasurementlogic.fast_counter_continue()
        time_stop_optimize = time.time()
        additional_time = (time_stop_optimize - time_start_optimize)

    return additional_time


def optimize_poi(poi):
    # FIXME: Add the option to pause pulsed measurement during position optimization
    time_start_optimize = time.time()
    #pulsedmeasurementlogic.fast_counter_pause()
    nicard.digital_channel_switch(setup['optimize_channel'], mode=True)
    # perform refocus
    poimanagerlogic.optimise_poi(poi)
    while optimizerlogic.module_state() == 'idle':
        time.sleep(0.2)
    while optimizerlogic.module_state() != 'idle':
        time.sleep(0.2)
    scannerlogic.set_position('optimizer', x=optimizerlogic.optim_pos_x, y=optimizerlogic.optim_pos_y,
                              z=optimizerlogic.optim_pos_z, a=0.0)
    time.sleep(0.5)
    # switch off laser
    nicard.digital_channel_switch(setup['optimize_channel'], mode=False)
    # pulsedmeasurementlogic.fast_counter_continue()
    time_stop_optimize = time.time()
    additional_time = (time_stop_optimize - time_start_optimize)

    return additional_time



def laser_on(pulser_on=True):
    # Turns on the laser via nicard. If pulser_on the pulser is not stopped
    pulsedmasterlogic.toggle_pulse_generator(pulser_on)
    nicard.digital_channel_switch(setup['optimize_channel'], mode=True)
    return

def laser_on_awg():
    # loads a waveform to awg that contionously enables laser marker
    # Caution: stops any waveform currently played!
    # waveform must be already in workspace of awg!

    pulsedmasterlogic.pulsedmeasurementlogic().pulsegenerator().load_waveform({1:'laser_on_ch1'})
    pulsedmasterlogic.toggle_pulse_generator(True)

def laser_off(pulser_on=False):
    # Switches off the laser trigger from nicard
    pulsedmasterlogic.toggle_pulse_generator(pulser_on)
    nicard.digital_channel_switch(setup['optimize_channel'], mode=False)
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
                  generate_new=opt_dict['generate_new'], save_tag = opt_dict['save_tag'])
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
        qm_dict['list_pois'] = poimanagerlogic.get_all_pois()
        # remove 'crosshair' and 'sample'
        qm_dict['list_pois'].remove('crosshair')
        qm_dict['list_pois'].remove('sample')

    # make sure there is an option to break the loop
    pulsedmasterlogic.break_variable = False
    # check if for the first poi new sequences should be generated
    first_poi = qm_dict['generate_new']
    # loop over all the pois
    for poi in qm_dict['list_pois']:
        if pulsedmasterlogic.break_variable == True: break
        # move to current poi and optimize position
        poimanagerlogic.go_to_poi(poi)
        optimize_poi(poi)

        # perform all experiments
        for experiment in autoexp:
            if pulsedmasterlogic.break_variable == True: break
            # perform the measurement
            if first_poi:
                do_experiment(experiment=autoexp[experiment]['type'], qm_dict = autoexp[experiment],
                              meas_type=autoexp[experiment]['meas_type'], meas_info=autoexp[experiment]['meas_info'],
                              generate_new=True, save_tag=autoexp[experiment]['name']+poi)
            else:
                do_experiment(experiment=autoexp[experiment]['type'], qm_dict = autoexp[experiment],
                              meas_type=autoexp[experiment]['meas_type'], meas_info=autoexp[experiment]['meas_info'],
                              generate_new=autoexp[experiment]['generate_new'],
                              save_tag=autoexp[experiment]['name']+poi)

            # fit and update parameters
            if 'fit_experiment' in autoexp[experiment]:
                if autoexp[experiment]['fit_experiment'] != '':
                    fit_data, fit_result = pulsedmeasurementlogic.do_fit(autoexp[experiment]['fit_experiment'])
                    #pulsedmasterlogic.do_fit(autoexp[experiment]['fit_experiment'])
                   # while pulsedmasterlogic.status_dict['fitting_busy']: time.sleep(0.2)
                    #time.sleep(1)
                    if 'fit_parameter' in autoexp[experiment]:
                        #fit_dict = pulsedmasterlogic.fit_container.current_fit_result.result_str_dict
                        #fit_para = fit_dict[autoexp[experiment]['fit_parameter']]['value']
                        #fit_para = fit_result.best_values[autoexp[experiment]['fit_parameter']]
                        fit_para = fit_result.result_str_dict[autoexp[experiment]['fit_parameter']]['value']
                        if 'update_parameters' in autoexp[experiment]:
                            for key in autoexp[experiment]['update_parameters']:
                                autoexp[key][autoexp[experiment]['update_parameters'][key]] = fit_para

            if qm_dict['optimize_between_experiments']:
                optimize_poi(poi)
        first_poi = False
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

