"""
This is the logic class for the optimization
"""
# QuOCS imports
from quocslib.utils.dynamicimport import dynamic_import
from quocslib.communication.AllInOneCommunication import AllInOneCommunication
from quocslib.utils.BestDump import BestDump
from quocspyside2interface.logic.OptimizationBasic import OptimizationBasic

from logic.optimalcontrol.HandleExit import HandleExitLogic
from logic.generic_logic import GenericLogic as LogicBase
from core.connector import Connector
from core.util.mutex import Mutex

import time

# Qudi new core imports
# from qudi.core.module import LogicBase
# from core.configoption import ConfigOption
# from qudi.core.connector import Connector
from qtpy import QtCore
from logic.optimalcontrol.fom_signal import FomSignal

class OptimizationLogic(LogicBase, OptimizationBasic):

    fom_logic = Connector(interface="WorkerFom")
    controls_logic = Connector(interface="WorkerControls")
    # Signal from outside
    load_optimization_dictionary_signal = QtCore.Signal(dict)
    send_controls_signal = QtCore.Signal(list, list, list)
    wait_fom_signal = QtCore.Signal(str)



    def __init__(self, config, **kwargs):
        """Initialize the base class"""
        super().__init__(config=config, **kwargs)

        self.opti_comm_dict = {}
        # Overwrite the previous handle exit variable
        self.handle_exit_obj = HandleExitLogic()
        self.is_fom_computed = False
        self.fom_max = 10 ** 10
        self.fom = 10**10
        self.std = 0.0
        self.status_code = 0
        # self._mutex = QtCore.QMutex()
        self._threadlock = Mutex()
        self._running = True
        self.optimizer_obj = None
        return

    def on_activate(self):
        """ Activation """
        self.log.info("Starting the Optimization Logic")
        # Creation of the figure of merit class to be use in the optimization dictionary to allow the transmissions
        # between the figure of merit logic and optimization logic
        self.send_controls_signal.connect(self.controls_logic().update_controls)
        # Very important here: Use the Direct Connection instead the default one, otherwise the signal will never reach
        # the slot
        self.fom_logic().send_fom_signal.connect(self.update_FoM, type=QtCore.Qt.DirectConnection)
        self.fom_obj = FomSignal(self.get_FoM)
        # Handle exit signals
        self.handle_exit_obj.is_optimization_running_fom_signal.connect(
            self.fom_logic().update_optimization_status)
        self.handle_exit_obj.is_optimization_running_controls_signal.connect(
            self.controls_logic().update_optimization_status
        )
        self.wait_fom_signal.connect(self.fom_logic().wait_for_fom)
        self.is_running_signal.connect(self.handle_exit_obj.set_is_user_running)
        # Set the timer part
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)

    def update_FoM(self, fom_dict):
        """ Update the figure of merit from the fom logic """
        self.status_code = fom_dict.setdefault("status_code", 0)
        self.std = fom_dict.setdefault("std", 0.0)
        self.fom = fom_dict["FoM"]
        self.is_fom_computed = True

    def is_computed(self):
        """ Check if the figure of is updated """
        return self.is_fom_computed

    def get_FoM(self, pulses, parameters, timegrids):
        """ Send the controls to the worker controls and wait the figure of merit from the worker fom """
        # Send the control to the worker controls
        if self.handle_exit_obj.is_user_running:
            self.send_controls(pulses, parameters, timegrids)
        else:
            return {"FoM": self.fom_max, "status_code": -1}
        # Send a signal to enable the waiting of the figure of merit
        self.wait_fom_signal.emit("Start to wait for figure of merit")
        while not self.is_computed():
            time.sleep(0.1)
            if not self.handle_exit_obj.is_user_running:
                time.sleep(5.0)
                return {"FoM": self.fom_max, "status_code": -1}
        self.is_fom_computed = False
        return {"FoM": self.fom, "std": self.std, "status_code": self.status_code}

    def load_opti_comm_dict(self, opti_comm_dict):
        """ Load the opti communication dictionary and send it to the GUI """
        self.opti_comm_dict = opti_comm_dict
        self.load_optimization_dictionary_signal.emit(opti_comm_dict)

    def start_optimization(self, opti_comm_dict):
        if self.optimizer_obj is not None:
            del self.optimizer_obj
        if self.handle_exit_obj.is_user_running:
            self.log.warning("An optimization is still running. I will wait 5 seconds and then try to abort it")
            time.sleep(5.0)
            self.is_running_signal.emit(False)

        # Activate the optimization logic, fom logic, and controls logic
        self.is_running_signal.emit(True)
        self.log.info("Waiting few seconds before the optimization starts")
        time.sleep(5.0)
        # Creation of the basic objects for the optimizer
        optimization_dictionary = opti_comm_dict["optimization_dictionary"]
        interface_job_name = optimization_dictionary["optimization_client_name"]
        communication_obj = AllInOneCommunication(
            interface_job_name=interface_job_name, fom_obj=self.fom_obj, dump_attribute=BestDump,
            handle_exit_obj=self.handle_exit_obj,
            comm_signals_list=[self.message_label_signal,
                               self.fom_plot_signal,
                               self.controls_update_signal])
        # Get the optimizer attribute
        print(optimization_dictionary)
        optimizer_attribute = dynamic_import(
            attribute=optimization_dictionary.setdefault("opti_algorithm_attribute", None),
            module_name=optimization_dictionary.setdefault("opti_algorithm_module", None),
            class_name=optimization_dictionary.setdefault("opti_algorithm_class", None))
        optimizer_obj = optimizer_attribute(optimization_dict=optimization_dictionary,
                                            communication_obj=communication_obj)
        # Start the optimizer procedure
        try:
            optimizer_obj.begin()
            optimizer_obj.run()
        except Exception as ex:
            self.log.error("Unhandled exception: {}".format(ex.args))
            self.log.error("Something went wrong during the optimization process")
        finally:
            optimizer_obj.end()
        self.message_label_signal.emit("The optimization is finished")
        # Send a signal to conclude the optimization
        self.is_running_signal.emit(False)
        # Save the optimizer obj for further analysis in the jupyter notebook
        self.optimizer_obj = optimizer_obj
        return

    def send_controls(self, pulses_list, parameters_list, timegrids_list):
        """ Send the controls to the worker controls """
        self.log.debug("Sending controls to the worker controls")
        self.send_controls_signal.emit(pulses_list, parameters_list, timegrids_list)
        return

    def on_deactivate(self):
        """ FUnction called during the deactivation """
        # TODO Deactivate all the signals here
        self.log.info("Close the Optimization logic")
