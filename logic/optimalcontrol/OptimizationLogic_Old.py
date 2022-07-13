"""
This is the logic class for the optimization
"""
from quocspyside2interface.logic.OptimizationBasic import OptimizationBasic
from quocslib.utils.dynamicimport import dynamic_import
from quocslib.communication.AllInOneCommunication import AllInOneCommunication
from logic.generic_logic import GenericLogic
from core.connector import Connector

# from qudi.core.module import LogicBase
# from core.configoption import ConfigOption
# from qudi.core.connector import Connector


class OptimizationLogic(GenericLogic, OptimizationBasic):

    fom_eval_logic = Connector(interface="TestMeasurementLogic")
    # Receive measurement is used by the communication object
    receive_measurement_logic = Connector(interface='ReceiveMeasurement')

    def __init__(self, config, **kwargs):
        """Initialize the base class"""
        super().__init__(config=config, **kwargs)
        return

    def start_optimization(self, opti_comm_dict):
        optimization_dictionary = opti_comm_dict["optimization_dictionary"]
        interface_job_name = optimization_dictionary["optimization_client_name"]
        communication_obj = AllInOneCommunication(
            interface_job_name=interface_job_name, fom_obj=self.receive_measurement_logic(),
            handle_exit_obj=self.handle_exit_obj,
            comm_signals_list=[self.message_label_signal, self.fom_plot_signal, self.controls_update_signal])
        # Get the optimizer attribute
        optimizer_attribute = dynamic_import(
            attribute=optimization_dictionary.setdefault("opti_algorithm_attribute", None),
            module_name=optimization_dictionary.setdefault("opti_algorithm_module", None),
            class_name=optimization_dictionary.setdefault("opti_algorithm_class", None))
        optimizer_obj = optimizer_attribute(optimization_dict=optimization_dictionary,
                                            communication_obj=communication_obj)
        try:
            optimizer_obj.begin()
            optimizer_obj.run()
        except Exception as ex:
            print("Unhandled exception: {}".format(ex.args))
            print("something goes wrong")
        finally:
            optimizer_obj.end()
        self.message_label_signal.emit("The optimization is finished")
        self.is_running_signal.emit(False)

    def on_activate(self):
        self.log.info("Starting the Optimization Logic")
        # Main signal connections between the FoM logic and recevie measurement logic
        # TODO Make a connection with Pulsed measurement
        self.fom_eval_logic().fom_signal.connect(self.receive_measurement_logic().update_FoM)
        self.receive_measurement_logic().send_controls_signal.connect(self.fom_eval_logic().get_measurement)

        # Just a redefinition
        self.rm_obj = self.receive_measurement_logic()
        return

    def on_deactivate(self):
        self.log.info("Close the Optimization logic")
