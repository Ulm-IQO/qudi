# -*- coding: utf-8 -*-
"""
IPython compatible kernel launcher module

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
from logic.generic_logic import GenericLogic
import core.logger as logger
from core.util.mutex import Mutex
from collections import OrderedDict
from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
import numpy as np

from .qzmqkernel import QZMQKernel
from core.util.network import netobtain
import logging
#-----------------------------------------------------------------------------
# The QuDi logic module
#-----------------------------------------------------------------------------

class QudiKernelLogic(GenericLogic):
    """ Logic module providing a Jupyer-compatible kernel connected via ZMQ."""
    _modclass = 'QudiKernelLogic'
    _modtype = 'logic'
    _out = {'kernel': 'QudiKernelLogic'}

    sigStartKernel = QtCore.Signal(str)
    sigStopKernel = QtCore.Signal(int)
    def __init__(self, manager, name, config, **kwargs):
        """ Create logic object

          @param object manager: reference to module Manager
          @param str name: unique module name
          @param dict config: configuration in a dict
          @param dict kwargs: additional parameters as a dict
        """
        ## declare actions for state transitions
        state_actions = { 'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)
        self.kernellist = dict()
        self.modules = set()

    def activation(self, e):
        """ Prepare logic module for work.

          @param object e: Fysom state change notification
        """
        logging.basicConfig(
            format='%(asctime)s %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %I:%M:%S %p',
            level=logging.DEBUG)

        self.kernellist = dict()
        self.modules = set()
        self._manager.sigModulesChanged.connect(self.updateModuleList)
        self.sigStartKernel.connect(self.updateModuleList, QtCore.Qt.QueuedConnection)

    def deactivation(self, e):
        """ Deactivate module.

          @param object e: Fysom state change notification
        """
        for kernel in self.kernellist:
            self.stopKernel(kernel)

    def startKernel(self, config, external=None):
        """Start a qudi inprocess jupyter kernel.
          @param dict config: connection information for kernel
          @param callable external: function to call on exit of kernel

          @return str: uuid of the started kernel
        """
        realconfig = netobtain(config)
        logger.info('Start {}'.format(realconfig))
        mythread = self.getModuleThread()
        kernel = QZMQKernel(realconfig)
        kernel.moveToThread(mythread)
        kernel.user_global_ns.update({
            'pg': pg,
            'np': np,
            'config': self._manager.tree['defined'],
            'manager': self._manager
            })
        kernel.sigShutdownFinished.connect(self.cleanupKernel)
        logger.info('Kernel is {}'.format(kernel.engine_id))
        QtCore.QMetaObject.invokeMethod(kernel, 'connect_kernel')
        self.kernellist[kernel.engine_id] = kernel
        logger.info('Finished starting Kernel {}'.format(kernel.engine_id))
        self.sigStartKernel.emit(kernel.engine_id)
        return kernel.engine_id

    def stopKernel(self, kernelid):
        """Tell kernel to close all sockets and stop hearteat thread.
          @param str kernelid: uuid of kernel to be stopped
        """
        realkernelid = netobtain(kernelid)
        logger.info('Stopping {}'.format(realkernelid))
        kernel = self.kernellist[realkernelid]
        QtCore.QMetaObject.invokeMethod(kernel, 'shutdown')

    def cleanupKernel(self, kernelid, external=None):
        """Remove kernel reference and tell rpyc client for that kernel to exit.

          @param str kernelid: uuid of kernel reference to remove
          @param callable external: reference to rpyc client exit function
        """
        logger.info('Cleanup kernel {}'.format(kernelid))
        del self.kernellist[kernelid]
        if external is not None:
            try:
                external.exit()
            except:
                logger.warning('External qudikernel starter did not exit')

    def updateModuleList(self):
        """Remove non-existing modules from namespace,
            add new modules to namespace, update reloaded modules
        """
        currentModules = set()
        newNamespace = dict()
        for base in ['hardware', 'logic', 'gui']:
            for module in self._manager.tree['loaded'][base]:
                currentModules.add(module)
                newNamespace[module] = self._manager.tree['loaded'][base][module]
        discard = self.modules - currentModules
        for kernel in self.kernellist:
            self.kernellist[kernel].user_global_ns.update(newNamespace)
        for module in discard:
            for kernel in self.kernellist:
                self.kernellist[kernel].user_global_ns.pop(module, None)
        self.modules = currentModules
