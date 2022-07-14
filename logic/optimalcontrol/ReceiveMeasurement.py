"""
FoM class. Here are present all the problem I need for my thesis
"""
import time

from qtpy import QtCore
#from qudi.core.module import LogicBase
from logic.generic_logic import GenericLogic
from quocslib.figureofmeritevaluation.AbstractFom import AbstractFom
#  TODO implement the file update communication part


class ReceiveMeasurement(GenericLogic):
    """

    """
    send_controls_signal = QtCore.Signal(list, list, list)
    is_computed: bool = False
    is_optimization_running = False

    def __init__(self, config, **kwargs):
        """Initialize the base class"""
        super().__init__(config=config, **kwargs)
        self.fom_max = 10**10
        self.fom = self.fom_max
        self.status_code = 0
        return

    def on_activate(self):
        return

    def on_deactivate(self):
        return

    def test(self):
        print("It is just a test")

    @QtCore.Slot(float, int)
    def update_FoM(self, fom, status_code: int = 0) -> None:
        self.fom = fom
        self.statu_code = status_code
        self.is_computed = True

    def update_optimization_status(self, is_running):
        print("Change the status pf the optimization in the receive measurement to: {0}"
              .format(is_running))
        self.is_optimization_running = is_running

    def get_FoM(self, pulses, parameters, timegrids) -> dict:
        """
        Module for figure of merit evaluation

        Returns
        -------

        """
        self.send_controls_signal.emit(pulses, parameters, timegrids)
        while not self.is_computed:
            time.sleep(0.01)
            if not self.is_optimization_running:
                return {"FoM": self.fom_max, "status_code": -1}
        self.is_computed = False
        return {"FoM": self.fom, "status_code": self.status_code}
