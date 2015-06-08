# -*- coding: utf-8 -*-

from logic.GenericLogic import GenericLogic
from core.util.Mutex import Mutex
from collections import OrderedDict
from pyqtgraph.Qt import QtCore
import pyqtgraph as pg
import numpy as np
import threading
import atexit
import sys
import os

from IPython.qt.inprocess import QtInProcessKernelManager

##old_register = atexit.register
#old_unregister = atexit.unregister
#
#def debug_register(func, *args, **kargs):
#    print('register', func, *args, **kargs)
#    old_register(func, *args, **kargs)
#
#def debug_unregister(func):
#    print('unregister', func)
#    old_unregister(func)
#
#atexit.register = debug_register
#atexit.unregister = debug_unregister

class IPythonLogic(GenericLogic):        
    """ Logic module containing an IPython kernel.
    """
    _modclass = 'ipythonlogic'
    _modtype = 'logic'
        
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = { 'onactivate': self.activation,
            'ondeactivate': self.deactivation
            }
        super().__init__(manager, name, config, state_actions, **kwargs)
        ## declare connectors    
        self.connector['out']['ipythonlogic'] = OrderedDict()
        self.connector['out']['ipythonlogic']['class'] = 'IPythonLogic'
        #locking for thread safety
        self.lock = Mutex()
        self.modules = set()
 
    def activation(self, e=None):
        self.logMsg('IPy activation in thread {0}'.format(threading.get_ident()), msgType='thread')
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        self.namespace = self.kernel.shell.user_ns
        self.namespace.update({
            'pg': pg,
            'np': np,
            'config': self._manager.tree['defined'],
            'manager': self._manager
            })
        self.updateModuleList()
        self.kernel.gui = 'qt4'
        self.logMsg('IPython has kernel {0}'.format(self.kernel_manager.has_kernel))
        self.logMsg('IPython kernel alive {0}'.format(self.kernel_manager.is_alive()))
        self._manager.sigModulesChanged.connect(self.updateModuleList)

    def deactivation(self, e=None):
        self.logMsg('IPy deactivation'.format(threading.get_ident()), msgType='thread')
        self.kernel_manager.shutdown_kernel()
        #self.kernel_manager.cleanup()

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
        self.namespace.update(newNamespace)
        for module in discard:
            self.namespace.pop(module, None)
        self.modules = currentModules
