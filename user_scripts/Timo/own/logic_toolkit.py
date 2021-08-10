import time, os
import numpy as np

def print_welcome_msg():
    print('[{}] Hi, jupyter ready. working dir: {}'.format(time.ctime(), os.getcwd()))

def set_pulsed_gui_settigns(with_error=True):
    gui = pulsedmeasurementgui
    gui.toggle_error_bars(with_error)


def update_pulsed_gui(mes):
    gui = pulsedmeasurementgui
    mes.sigMeasurementDataUpdated.emit()

def get_current_pulsed_mes():
    mes = pulsedmasterlogic.pulsedmeasurementlogic()
    return mes

def get_current_pulsed_mes_running():
    return pulsedmasterlogic.status_dict['measurement_running']

def purge_current_mes():
    mes = get_current_pulsed_mes()
    mes._controlled_variable = [None]
    mes._number_of_lasers = 1   # = len(_controlled_variable)
    mes._laser_ignore_list = []
    mes._alternating = False

def inject_data_to_current_mes(x, y, y2=None, dy=None, dy2=None, labels_xy=None, units_xy=None):
    mes = get_current_pulsed_mes()
    purge_current_mes()

    signal_dim = 2
    if y2 is not None:
        signal_dim = 3

    mes.signal_data = np.zeros((signal_dim, len(x)))

    mes.signal_data[0] = x
    mes.signal_data[1] = y
    if y2 is not None:
        mes.signal_data[2] = y2


    # mes.signal_alt_data = np.zeros((2, len(x)))+2 # second plot
    mes._alternative_data_type = 'None'

    # error bar
    if dy is not None or dy2 is not None:
        mes.measurement_error = np.zeros((signal_dim, len(x)))
        if dy is not None:
            mes.measurement_error[1] = dy
        if dy2 is not None:
            mes.measurement_error[2] = dy2

    # labels, units, ...

    settings = {'invoke_settings': False}
    if labels_xy is not None:
        settings['labels'] = [labels_xy[0], labels_xy[1]]
    if units_xy is not None:
        settings['units'] = [units_xy[0], units_xy[1]]
    if y2 is not None:
        settings['alternating'] = True

    get_current_pulsed_mes().set_measurement_settings(settings)

    update_pulsed_gui(mes)

# inject_data_to_current_mes([0,1],[0,2], [0.1,0.2])