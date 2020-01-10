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
    """ A generic logic module class.
    """
    _threaded = True

    def __init__(self, *args, **kwargs):
        """
        Initialize a logic module.
        """
        super().__init__(*args, **kwargs)
        self.taskLock = Mutex()  # FIXME: What's this? Is it needed?

    @QtCore.Slot(QtCore.QThread)
    def moveToThread(self, thread):
        super().moveToThread(thread)

    @property
    def module_thread(self):
        return QtCore.QObject.thread(self)

    # FIXME: exposing this seems like a great opportunity to shoot yourself in the foot.
    #  Is it really needed? If the reference to task_runner is really needed and must be protected
    #  by a Mutex, then the manager should handle safe access. (maybe a manager property?)
    def get_task_runner(self):
        """
        Get a reference to the task runner module registered in the manager.
        If there is no registered task runner, an exception is raised.

        @return object: reference to task runner
        """
        with self._manager.lock:
            if self._manager.task_runner is not None:
                return self._manager.task_runner
            else:
                raise Exception('Tried to access task runner without loading one!')
