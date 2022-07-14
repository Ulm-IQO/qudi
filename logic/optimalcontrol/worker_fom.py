""" """
import time
import logging


from qtpy import QtCore
#from qudi.core.module import LogicBase
from logic.generic_logic import GenericLogic as LogicBase


class WorkerFom(LogicBase):
    """ """
    send_fom_signal = QtCore.Signal(dict)
    test_message_signal = QtCore.Signal(str)

    def __init__(self, config, **kwargs):
        """Initialize the base class"""
        super().__init__(config=config, **kwargs)
        self.fom_max = 10**10
        self.fom = self.fom_max
        self.std = 0.0
        self.status_code = 0
        self.is_optimization_running = False
        self.is_fom_computed = False
        self.max_time = 30.0
        return

    def on_activate(self):
        """ Module called during the activation """
        return

    def on_deactivate(self):
        """ Module called during the deactivation"""
        return

    def set_max_time(self, max_time: float):
        """ Set the maximum time for the calculation of the figure of merit """
        self.max_time = max_time

    def update_fom(self, fom: float, std: float = 0.0, status_code: int = 0):
        self.fom = fom
        self.std = std
        self.status_code = status_code
        self.is_fom_computed = True

    def send_fom(self):
        """ Send the dictionary containing the figure of merit  and the status code to the optimization logic """
        # Check if the worker is still active
        if not self.is_optimization_running:
            self.log.info("The worker fom is not running")
            time.sleep(1.0)
            return
        # Wait for the figure of merit calculation
        curr_time = time.time()
        while not self.is_fom_computed:
            time.sleep(0.1)
            diff_time = self.max_time - curr_time
            if diff_time > self.max_time:
                status_code = -1
                self.log.warning("Exceed maximum time for the figure of merit evaluation")
                self.send_fom_signal.emit({"FoM": self.fom_max, "status_code": status_code})
                time.sleep(1.0)
                return
        self.is_fom_computed = False
        self.send_fom_signal.emit({"FoM": self.fom, "std": self.std, "status_code": self.status_code})

    def update_optimization_status(self, is_running):
        self.log.debug("Change the status of the optimization in the worker fom to: {0}".format(is_running))
        self.is_optimization_running = is_running

    def wait_for_fom(self, message):
        """ Activate the waiting function for the figure of merit"""
        self.log.debug(message)
        self.send_fom()
