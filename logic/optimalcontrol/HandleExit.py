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

import logging

from qtpy import QtCore

from quocspyside2interface.logic.HandleExitBasic import HandleExitBasic as HE


class HandleExitLogic(HE):
    """This class check and update the current optimization status and notify the Client Interface and the Optimization
    code about it"""

    logger = logging.getLogger("oc_logger")

    # Signals for the others logic components
    is_optimization_running_fom_signal = QtCore.Signal(bool)
    is_optimization_running_controls_signal = QtCore.Signal(bool)

    def __init__(self):
        super().__init__()
        self.is_user_running = False

    @QtCore.Slot(bool)
    def set_is_user_running(self, is_running: bool):
        """
        Module connected with the Client Interface GUI. Stop the communication when the user presses to the Stop button
        and start the optimization
        :param bool is_running:
        :return:
        """
        self.is_user_running = is_running
        self.logger.info("The optimization is running: {0}".format(is_running))
        # Notify the other logic components
        self.is_optimization_running_fom_signal.emit(is_running)
        self.is_optimization_running_controls_signal.emit(is_running)
