"""
Test Problems for Optimal Control Suite
"""

#from qudi.core.module import LogicBase
from logic.generic_logic import GenericLogic
# from quocslib.optimalcontrolproblems.OneQubitProblem import OneQubit
# from quocslib.optimalcontrolproblems.RosenbrockProblem import Rosenbrock
from qtpy import QtCore
from core.connector import Connector

import time


class TestMeasurementLogic(GenericLogic):

    # fom_signal = QtCore.Signal(float, int)


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        print("Figure of merit logic initialization")
        self.fom_max = 10**10
        self.fom = 10**10
        self.status_code = 0
        self.max_time = 30.0
        self.previous_time = time.time()
        self.is_optimization_running = False
        self.are_pulses_calculated = False
        self.is_active = False
        self.is_fom_computed = False

        # self.control_problem = OneQubit()
        return

    def on_activate(self):
        self.log.info("Starting the TestMeasurement Logic")
        return 0

    def on_deactivate(self):
        self.log.info("Close the TestMeasurement logic")
        return 0

    @QtCore.Slot(bool)
    def set_is_active(self, is_active):
        if is_active:
            self.log.info("The setup is activated")
        else:
            self.log.info("The setup is deactivated")
        self.is_active = is_active
        return

    def set_fom_signal(self, fom_signal):
        self.fom_signal = fom_signal

    def update_optimization_status(self, is_running):
        print("Change the status of the optimization in the testmeasurementlogic to: {0}"
              .format(is_running))
        self.is_optimization_running = is_running
        return

    def update_pulses(self, pulses, parameters, timegrids):
        """ Update the controls with the ones provided by the optimization algorithm """
        # print("Pulses Updated")
        self.pulses, self.parameters, self.timegrids = pulses, parameters, timegrids
        self.are_pulses_calculated = True
        return

    def update_FoM(self, fom: float, status_code: int = 0):
        """ Update the figure of merit value from the Jupyter notebook"""
        # print("FoM Updated")
        self.fom = fom
        self.status_code = status_code
        self.is_fom_computed = True
        return

    @QtCore.Slot(list, list, list)
    def get_measurement(self, pulses, parameters, timegrids):
        """ """
        print("I am in the testmeasurementlogic, get_measurement")
        curr_time = time.time()
        # Just a flag to active the measurement
        if not self.is_active:
            self.log.warn("Activate the experimental logic wih testmeasurementlogic.set_is_active(True)")
        while not self.is_active:
            time.sleep(0.5)
        # Update the pulses
        self.update_pulses(pulses, parameters, timegrids)
        print("Waiting fom is computed in testmeasurementlogic")
        while not self.is_fom_computed:
            # If the optimization is not running anymore, return the maximum fidelity to stop the optimization
            diff_time = self.max_time - curr_time
            if not self.is_optimization_running or (diff_time > self.max_time):
                print("Exceed maximum time. Exit")
                self.fom_signal.emit(self.fom_max, self.status_code)
                return
            time.sleep(0.1)
        print("Fom is computed !")
        # Update the previous time variable with the current time
        self.previous_time = time.time()
        self.is_fom_computed = False
        # self.are_pulses_calculated = False
        print("I am in the testmeasurementlogic, emitting the signal back to the optimization logic")
        print("Fom: {0}, Status code: {1}".format(self.fom, self.status_code))
        self.fom_signal.emit(self.fom, self.status_code)
        return
