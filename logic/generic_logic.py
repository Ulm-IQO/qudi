# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic module base class.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
from qtpy import QtCore
from core.module import Base
from core.util.mutex import Mutex


class GenericLogic(Base):
    """A generic logic interface class.
    """
    _threaded = True
    model_has_changed = QtCore.Signal(list)

    def __init__(self, **kwargs):
        """ Initialzize a logic module.

          @param dict kwargs: dict of additional arguments
        """
        super().__init__(**kwargs)
        self.taskLock = Mutex()

    @QtCore.Slot(QtCore.QThread)
    def moveToThread(self, thread):
        super().moveToThread(thread)

    def getModuleThread(self):
        """ Get the thread associated to this module.

          @return QThread: thread with qt event loop associated with this module
        """
        return self._manager.tm._threads['mod-logic-' + self._name].thread

    def getTaskRunner(self):
        """ Get a reference to the task runner module registered in the manager.

          @return object: reference to task runner

          If there isno registered task runner, an exception is raised.
        """
        with self._manager.lock:
            if self._manager.tr is not None:
                return self._manager.tr
            else:
                raise Exception('Tried to access task runner without loading one!')
