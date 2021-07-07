# -*- coding: utf-8 -*-
"""
This file contains the Qudi tools for remote module sharing via rpyc server.

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

__all__ = ('RemoteModulesService', 'QudiNamespaceService')

import rpyc
import weakref

from qudi.util.mutex import Mutex
from qudi.util.models import DictTableModel
from qudi.core.logger import get_logger

logger = get_logger(__name__)


class _SharedModulesModel(DictTableModel):
    """ Derived dict model for GUI display elements
    """
    def __init__(self):
        super().__init__(headers='Shared Module')

    def data(self, index, role):
        """ Get data from model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return QVariant: data for given cell and role
        """
        data = super().data(index, role)
        if data is None:
            return None
        # second column returns weakref.ref object
        if index.column() == 1:
            data = data()
        return data


class RemoteModulesService(rpyc.Service):
    """ An RPyC service that has a module list.
    """
    ALIASES = ['RemoteModules']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = Mutex()
        self.shared_modules = _SharedModulesModel()

    def share_module(self, module):
        with self._thread_lock:
            if module.name in self.shared_modules:
                logger.warning(f'Module "{module.name}" already shared')
                return
            self.shared_modules[module.name] = weakref.ref(module)
            weakref.finalize(module, self.remove_shared_module, module.name)

    def remove_shared_module(self, module):
        with self._thread_lock:
            name = module if isinstance(module, str) else module.name
            self.shared_modules.pop(name, None)

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client connected to remote modules service from [{host}]:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing
        """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client [{host}]:{port:d} disconnected from remote modules service')

    def exposed_get_module_instance(self, name, activate=False):
        """ Return reference to a module in the shared module list.

        @param str name: unique module name

        @return object: reference to the module
        """
        with self._thread_lock:
            try:
                module = self.shared_modules.get(name, None)()
            except TypeError:
                logger.error(f'Client requested a module ("{name}") that is not shared.')
                return None
            if activate:
                if not module.activate():
                    logger.error(f'Unable to share requested module "{name}" with client. Module '
                                 f'can not be activated.')
                    return None
            return module.instance

    def exposed_get_available_module_names(self):
        """ Returns the currently shared module names independent of the current module state.

        @return tuple: Names of the currently shared modules
        """
        with self._thread_lock:
            return tuple(self.shared_modules)

    def exposed_get_loaded_module_names(self):
        """ Returns the currently shared module names for all modules that have been loaded
        (instantiated).

        @return tuple: Names of the currently shared and loaded modules
        """
        with self._thread_lock:
            all_modules = {name: ref() for name, ref in self.shared_modules.items()}
            return tuple(name for name, mod in all_modules.items() if
                         mod is not None and mod.instance is not None)

    def exposed_get_active_module_names(self):
        """ Returns the currently shared module names for all modules that are active.

        @return tuple: Names of the currently shared active modules
        """
        with self._thread_lock:
            all_modules = {name: ref() for name, ref in self.shared_modules.items()}
            return tuple(
                name for name, mod in all_modules.items() if mod is not None and mod.is_active
            )


class QudiNamespaceService(rpyc.Service):
    """ An RPyC service providing a namespace dict containing references to all active qudi module
    instances as well as a reference to the qudi application itself.
    """
    ALIASES = ['QudiNamespace']

    def __init__(self, *args, qudi, **kwargs):
        super().__init__(*args, **kwargs)
        self.__qudi_ref = weakref.ref(qudi)
        self._notifier_callbacks = dict()

    @property
    def _qudi(self):
        qudi = self.__qudi_ref()
        if qudi is None:
            raise RuntimeError('Dead qudi application reference encountered')
        return qudi

    @property
    def _module_manager(self):
        manager = self._qudi.module_manager
        if manager is None:
            raise RuntimeError('No module manager initialized in qudi application')
        return manager

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        try:
            self._notifier_callbacks[conn] = rpyc.async_(conn.root.modules_changed)
        except AttributeError:
            pass
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client connected to local module service from [{host}]:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing
        """
        self._notifier_callbacks.pop(conn, None)
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client [{host}]:{port:d} disconnected from local module service')

    def notify_module_change(self):
        logger.debug('Local module server has detected a module state change and sends async '
                     'notifier signals to all clients')
        for callback in self._notifier_callbacks.values():
            callback()

    def exposed_get_namespace_dict(self):
        """ Returns the instances of the currently active modules as well as a reference to the
        qudi application itself.

        @return dict: Names (keys) and object references (values)
        """
        mods = {name: mod.instance for name, mod in self._module_manager.items() if mod.is_active}
        mods['qudi'] = self._qudi
        return mods

    def exposed_get_numpy_module(self):
        """
        """
        import numpy
        return numpy
