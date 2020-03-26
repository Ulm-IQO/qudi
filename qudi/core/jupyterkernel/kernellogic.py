# -*- coding: utf-8 -*-
"""
IPython compatible kernel launcher module

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

import time
import numpy as np

from qtpy import QtCore
from qudi.core.module import LogicBase
from qudi.core.configoption import ConfigOption
from qudi.core.util.network import netobtain

from qudi.core.jupyterkernel.qzmqkernel import QZMQKernel


class QudiKernelLogic(LogicBase):
    """ Logic module providing a Jupyer-compatible kernel connected via ZMQ.
    """

    _kernel_shutdown_timeout = ConfigOption(name='kernel_shutdown_timeout', default=5)

    sigStartKernel = QtCore.Signal(str)
    sigStopKernel = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        """ Create logic object
        """
        super().__init__(*args, **kwargs)
        self.kernels = dict()
        self.namespace_modules = set()

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self.kernels = dict()
        self.namespace_modules = set()
        if self._kernel_shutdown_timeout < 1:
            self.log.warning('ConfigOption "kernel_shutdown_timeout" has to be at least 1 second.')
            self._kernel_shutdown_timeout = 1
        self._qudi_main.module_manager.sigManagedModulesChanged.connect(
            self.update_module_namespace)

    def on_deactivate(self):
        """ Deactivate module.
        """
        # Disconnect signals
        try:
            self._qudi_main.module_manager.sigManagedModulesChanged.disconnect(
                self.update_module_namespace)
        except:
            pass

        # Stop kernels and wait for them to shut down
        for k in tuple(self.kernels):
            self.stop_kernel(k, blocking=True)
        # start = time.time()
        # while self.kernels:
        #     if time.time() - start > self._kernel_shutdown_timeout:
        #         self.log.warning('Shutting down all qudi kernels timed out.')
        #         break
        #     # QtCore.QCoreApplication.processEvents()
        #     time.sleep(0.1)

    def start_kernel(self, config, external=None):
        """ Start a qudi inprocess jupyter kernel.

        @param dict config: connection information for kernel
        @param callable external: function to call on exit of kernel

        @return str: uuid of the started kernel
        """
        config = netobtain(config)
        self.log.debug('Starting new kernel with config: {0}'.format(config))
        kernel = QZMQKernel(config)
        if kernel.engine_id in self.kernels:
            self.log.error('Kernel with ID {0} already created in QudiKernelLogic. '
                           'Ignoring call to start_kernel.')
            return
        kernel_thread = self._qudi_main.thread_manager.get_new_thread(
            'kernel-{0}'.format(kernel.engine_id))
        kernel.moveToThread(kernel_thread)
        kernel.user_global_ns.update({'np': np,
                                      'config': self._qudi_main.configuration.config_dict,
                                      'qudi': self._qudi_main})
        kernel.sigShutdownFinished.connect(self.cleanup_kernel, QtCore.Qt.QueuedConnection)
        kernel_thread.start()
        QtCore.QMetaObject.invokeMethod(
            kernel, 'connect_kernel', QtCore.Qt.BlockingQueuedConnection)
        self.kernels[kernel.engine_id] = kernel
        modules = self._qudi_main.module_manager
        module_namespace = {name: modules[name].instance for name in self.namespace_modules}
        self._update_kernel_module_namespace(kernel.engine_id, module_namespace)
        self.log.info('Finished starting Kernel {0}'.format(kernel.engine_id))
        return kernel.engine_id

    def stop_kernel(self, kernel_id, blocking=False):
        """ Tell kernel to close all sockets and stop heartbeat thread.

        @param str kernel_id: uuid of kernel to be stopped
        @param bool blocking: Whether this method should wait until the kernel is stopped or not
        """
        kernel_id = netobtain(kernel_id)
        kernel = self.kernels.get(kernel_id, None)
        if kernel is None:
            self.log.error('No kernel with ID {0} registered.'.format(kernel_id))
            return
        self.log.info('Stopping kernel {0}'.format(kernel_id))
        if blocking:
            kernel.sigShutdownFinished.disconnect(self.cleanup_kernel)
            QtCore.QMetaObject.invokeMethod(kernel, 'shutdown', QtCore.Qt.BlockingQueuedConnection)
            self.cleanup_kernel(kernel_id)
        else:
            QtCore.QMetaObject.invokeMethod(kernel, 'shutdown')

    def cleanup_kernel(self, kernel_id, external=None):
        """Remove kernel reference and tell rpyc client for that kernel to exit.

        @param str kernel_id: uuid of kernel reference to remove
        @param callable external: reference to rpyc client exit function
        """
        self.log.info('Cleaning up kernel {0}'.format(kernel_id))
        self._qudi_main.thread_manager.quit_thread('kernel-{0}'.format(kernel_id))
        self.kernels.pop(kernel_id, None)
        if external is not None:
            try:
                external.exit()
            except:
                self.log.warning('External qudikernel starter did not exit')

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_module_namespace(self, managed_modules=None):
        """ Remove non-existing modules from namespace, add new modules to namespace, update
        reloaded modules

        @param dict managed_modules: configured module names with their respective ManagedModule
                                     instances
        """
        if managed_modules is None:
            managed_modules = self._qudi_main.module_manager.modules

        # Collect all active module instances in a dict with their respective configured names
        new_namespace = {mod_name: mod.instance for mod_name, mod in managed_modules.items() if
                         mod.is_active}
        new_namespace_set = set(new_namespace)
        # Determine modules to discard from namespace
        discard = self.namespace_modules - new_namespace_set
        # iterate through all kernels and update namespace
        for kernel_name in self.kernels:
            self._update_kernel_module_namespace(kernel_name, new_namespace, discard)
        # Remember module names of new namespace
        self.namespace_modules = new_namespace_set

    def _update_kernel_module_namespace(self, kernel_id, new_namespace, discard=None):
        """ Helper method to update the namespace of a single kernel
        """
        if discard is None:
            discard = tuple()
        kernel = self.kernels.get(kernel_id, None)
        if kernel is None:
            self.log.error('No kernel with ID {0} registered.'.format(kernel_id))
            return

        kernel.user_global_ns.update(new_namespace)
        for name in discard:
            kernel.user_global_ns.pop(name, None)
        return
