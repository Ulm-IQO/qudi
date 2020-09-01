# -*- coding: utf-8 -*-
"""
This file contains the Qudi Manager class.

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

# import os
# import PySide2
# dirname = os.path.dirname(PySide2.__file__)
# plugin_path = os.path.join(dirname, 'plugins', 'platforms')
# os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
# os.environ['QT_API'] = 'pyside2'

from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.core.connector import Connector
from qudi.core.module import Base, LogicBase, GuiBase
from qudi.core.logger import get_logger
from PySide2.QtCore import Slot
import functools as __functools


def qudi_slot(*args, **kwargs):
    """ Decorator to be used as drop-in replacement for PySide2.QtCore.Slot().
    Wraps decorated function with a try/except statement to pass any exceptions to the qudi logging
    facility.
    This is necessary because PySide2 Slots silently ignore Python exceptions raised in non-main
    threads by default if they get invoked by Qt Signals (with QueuedConnection).
    The "common" approach to install a custom sys.excepthook does not work in this case.

    See PySide2.QtCore.Slot for decorator documentation.
    """
    if len(args) == 0 or callable(args[0]):
        args = []
    qt_decorator = Slot(*args, **kwargs)  # default decorator

    def slot_decorator(func):
        log = get_logger('{0}.{1}'.format(func.__module__, func.__qualname__.split('.', 1)[0]))

        @__functools.wraps(func)
        def wrapper(*_args, **_kwargs):
            try:
                return func(*_args, **_kwargs)
            except:
                log.exception('Error while invoking Qt Slot. This must never happen.')
        return qt_decorator(wrapper)
    return slot_decorator
