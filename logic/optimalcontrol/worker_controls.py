"""
Worker controls class
"""

#from qudi.core.module import LogicBase
from logic.generic_logic import GenericLogic
from qtpy import QtCore

import time


class WorkerControls(GenericLogic):

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.log.info("Worker Controls initialization")
        self.fom_max = 10**10
        self.fom = 10**10
        self.status_code = 0
        self.max_time = 30.0
        self.previous_time = time.time()
        self.is_optimization_running = False
        self.are_pulses_calculated = False
        self.is_active = False
        self.is_fom_computed = False
        # The controls
        self.pulses, self.parameters, self.timegrids = None, None, None
        return

    def on_activate(self):
        self.log.info("Starting the Worker FoM")
        return

    def on_deactivate(self):
        self.log.info("Closing the Worker FoM")
        return

    def set_max_time(self, max_time: float):
        """ Set the maximum time for waiting the controls """
        self.max_time = max_time

    @QtCore.Slot(list, list, list)
    def update_controls(self, pulses, parameters, timegrids):
        """ Update the controls with the ones provided by the optimization algorithm """
        if not self.is_optimization_running:
            self.log.warning("The optimization is stopped. QuOCS will not provide any controls anymore.")
            self.pulses, self.parameters, self.timegrids = None, None, None
            time.sleep(1.0)
            return
        self.pulses, self.parameters, self.timegrids = pulses, parameters, timegrids
        self.are_pulses_calculated = True
        return

    @QtCore.Slot(bool)
    def update_optimization_status(self, is_running):
        self.log.debug("Change the status of the optimization in the controlslogic to: {0}".format(is_running))
        self.is_optimization_running = is_running
        return
