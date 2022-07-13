# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#  Copyright 2021-  QuOCS Team
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
from qtpy import QtCore
# from quocslib.figureofmeritevaluation.AbstractFom import AbstractFom
# from logic.generic_logic import GenericLogic
import time


# class SignalFom(GenericLogic):
class SignalFom:

    # controls_signal = QtCore.Signal(list, list, list)

    # def __init__(self, config, max_waiting_time: float = 100, **kwargs):
        # super().__init__(config=config, **kwargs)
    def __init__(self, controls_signal, fom_pack, max_waiting_time: float = 100):
        self.max_waiting_time = max_waiting_time
        self.fom_max = 10**10
        self.is_fom_computed = False
        self.status_code = 0
        # Define a big previous time for the first iteration
        self.previous_time = 10**3
        self.controls_signal = controls_signal
        # self.fom_pack_list = [fom, status_code, is_calculated]
        self.fom_pack = fom_pack

    # @QtCore.Slot(float, int)
    # def update_FoM(self, fom, status_code):
    #     """Update the status code"""
    #     print("SignalFom, updating FoM")
    #     self.fom = fom
    #     self.status_code = status_code
    #     self.is_fom_computed = True

    # def on_activate(self):
    #     self.log.info("Starting the SignalFom Logic")
    #     return 0
    #
    # def on_deactivate(self):
    #     self.log.info("Close the SignalFom logic")
    #     return 0


    def get_FoM(self, pulses, parameters, timegrids) -> dict:
        """Send a signal to the qudi logic for the evaluation of the figure of merit and return it to the quocs """
        print("SignalFom, send controls to fomlogic")
        self.controls_signal.emit(pulses, parameters, timegrids)
        # Wait until the fom is computed by FomLogic
        # self.fom_pack_list = [fom, status_code, is_calculated]
        while not self.fom_pack.is_fom_computed:
            time.sleep(0.1)
            # curr_time = time.time()
            # diff_time = curr_time - self.previous_time
            # if diff_time > self.max_waiting_time:
            #     print("SignalFom: exceed the time for fom computation: {0}. Return code -1 ".format(diff_time))
            #     fom = self.fom_max
            #     status_code = -1
            #     return {"FoM": fom, "status_code": status_code}
        # Update the time
        self.previous_time = time.time()
        # The fom was computed then return to the main programme
        self.fom_pack.is_fom_computed = False
        return {"FoM": self.fom_pack.fom, "status_code": self.fom_pack.status_code}


