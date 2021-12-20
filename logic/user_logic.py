from logic.generic_logic import GenericLogic
from core.module import Connector
import threading

class UserGlobals(GenericLogic):
    """
    This class defines some usefull global variables.
    After loading the module via the config file, the qudi console
    and every module importing this file can access these variables.

    eg. in config.cfg:
    uglobals:
        module.Class: 'user_logic.UserGlobals'

    access in console:
        uglobals.<varname>
    access in module:
        from from logic.user_logic import UserGlobals as uglobals
        uglobals.<varname>

    """

    _modclass = 'uglobals'
    _modtype = 'logic'

    # experiment control flow
    abort = threading.Event()
    abort.clear()
    next = threading.Event()
    next.clear()

    # current mes dict
    qmeas = {}


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ """
        pass


class UserCommands(GenericLogic):

    _modclass = 'usercommands'
    _modtype = 'logic'

    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')
    poimanagerlogic = Connector(interface='poimanagerlogic')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ """
        pass

    def send_ttl_pulse(self, channel_name='/dev1/PFI9', n=1, t_wait=0.02):
        import PyDAQmx as daq
        import time
        import numpy as np

        # setup DO for sending interrupt
        val = False
        digital_read = daq.c_int32()
        digital_samples_channel = daq.c_int32(1)
        digital_out_task = daq.TaskHandle()
        daq.DAQmxCreateTask('DigitalOut', daq.byref(digital_out_task))

        try:
            for i in range(0, int(n * 2)):
                val = not val

                # shadow of digital_write function
                if val:
                    digital_data = daq.c_uint32(0xffffffff)
                else:
                    digital_data = daq.c_uint32(0x0)

                if i is 0:
                    daq.DAQmxCreateDOChan(digital_out_task, channel_name, "", daq.DAQmx_Val_ChanForAllLines)
                    daq.DAQmxStartTask(digital_out_task)
                daq.DAQmxWriteDigitalU32(digital_out_task, digital_samples_channel, True,
                                         0, daq.DAQmx_Val_GroupByChannel,
                                         np.array(digital_data), digital_read, None)

                #print("i {}: {}".format(i, val))
                time.sleep(t_wait)
                i += 1

        except Exception as e:

            daq.DAQmxStopTask(digital_out_task)
            daq.DAQmxClearTask(digital_out_task)
            print("Error occured: {}".format(e.message))
            return

        daq.DAQmxStopTask(digital_out_task)
        daq.DAQmxClearTask(digital_out_task)

    def reset_pulsedgui(self):
        # after fancy stuff from jupyter, invoking loads settings from predefined methods
        self.pulsedmasterlogic().pulsedmeasurementlogic().measurement_settings = {'invoke_settings': True}
        self.pulsedmasterlogic().pulsedmeasurementlogic().timer_interval = 2

    def reset_poi_history(self):
        n_hist =  len(self.poimanagerlogic()._roi._pos_history)

        for i in range(0, n_hist):
            self.poimanagerlogic().delete_history_entry()