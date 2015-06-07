# -*- coding: utf-8 -*-

from logic.GenericLogic import GenericLogic
from core.util.Mutex import Mutex
from collections import OrderedDict
from pyqtgraph.Qt import QtCore

import os
import sys
#import zmq
#import IPython.kernel.zmq.ipkernel
#from IPython.kernel.zmq.ipkernel import Kernel
#from IPython.kernel.zmq.heartbeat import Heartbeat
#from IPython.kernel.zmq.session import Session
#from IPython.kernel import write_connection_file
#from IPython.core.interactiveshell import InteractiveShell
#from zmq.eventloop.zmqstream import ZMQStream
#from zmq.eventloop.ioloop import IOLoop
import atexit
import socket
import logging
import threading

from IPython.qt.inprocess import QtInProcessKernelManager

def _on_os_x_10_9():
    import platform
    from distutils.version import LooseVersion as V
    return sys.platform == 'darwin' and V(platform.mac_ver()[0]) >= V('10.9')

old_register = atexit.register
old_unregister = atexit.unregister

def debug_register(func, *args, **kargs):
    print('register', func, *args, **kargs)
    old_register(func, *args, **kargs)

def debug_unregister(func):
    print('unregister', func)
    old_unregister(func)

atexit.register = debug_register
atexit.unregister = debug_unregister

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
        self.connectionFileClean = True
 
    def activation(self, e=None):
        self.logMsg('IPy activation in thread {0}'.format(threading.get_ident()), msgType='thread')
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        self.kernel.gui = 'qt4'
        self.logMsg('IPython has kernel {0}'.format(self.kernel_manager.has_kernel))
        self.logMsg('IPython kernel alive {0}'.format(self.kernel_manager.is_alive()))
        #self.ipythread = QtCore.QThread()
        #self.ipykernel = IPythonKernel(self)
        #self.ipykernel.moveToThread(self.ipythread)
        #self.ipythread.started.connect(self.ipykernel.prepare)
        #self.ipythread.start()

    def deactivation(self, e=None):
        self.logMsg('IPy deactivation'.format(threading.get_ident()), msgType='thread')
        self.kernel_manager.shutdown_kernel()
        #self.ipykernel.loop.stop()
        #self.ipythread.quit()
        #self.ipythread.wait()

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

class IPythonKernel(QtCore.QObject):
    sigRunKernel = QtCore.Signal()

    def __init__(self, ipylogic):
        super().__init__()
        self.ipylogic = ipylogic

    def prepare(self):
        self.ipylogic.logMsg('IPython kernel created in thread {0}'.format(threading.get_ident()), msgType='thread')
        # You can remotely connect to this kernel. See the output on stdout.
        IPython.kernel.zmq.ipkernel.signal = lambda sig, f: None  # Overwrite.
        # Do in mainthread to avoid history sqlite DB errors at exit.
        # https://github.com/ipython/ipython/issues/680
        try:
            self.connection_file = 'kernel-{0}.json'.format(os.getpid())
            atexit.register(self.cleanupConnectionFile)

            self.logger = logging.Logger('IPython')
            self.logger.addHandler(logging.NullHandler())
            self.session = Session(username='kernel')

            self.context = zmq.Context.instance()
            self.ip = socket.gethostbyname(socket.gethostname())
            self.transport = 'tcp'
            self.addr = '{0}://{1}'.format(self.transport, self.ip)
            self.shell_socket = self.context.socket(zmq.ROUTER)
            self.shell_port = self.shell_socket.bind_to_random_port(self.addr)
            self.iopub_socket = self.context.socket(zmq.PUB)
            self.iopub_port = self.iopub_socket.bind_to_random_port(self.addr)
            self.control_socket = self.context.socket(zmq.ROUTER)
            self.control_port = self.control_socket.bind_to_random_port(self.addr)

            self.hb_ctx = zmq.Context()
            self.heartbeat = Heartbeat(self.hb_ctx, (self.transport, self.ip, 0))
            self.hb_port = self.heartbeat.port

            self.shell_stream = ZMQStream(self.shell_socket)
            self.control_stream = ZMQStream(self.control_socket)

            self.namespace = {'manager': self.ipylogic._manager}
            self.kernel = Kernel(
                    session = self.session,
                    user_ns = self.namespace,
                    shell_streams = [self.shell_stream, self.control_stream],
                    iopub_socket = self.iopub_socket,
                    log = self.logger)

            if _on_os_x_10_9() and self.kernel._darwin_app_nap:
                from IPython.external.appnope import nope_scope as context
            else:
                from IPython.core.interactiveshell import NoOpContext as context
    
            self.connectionFileClean = False
            write_connection_file(
                    self.connection_file,
                    shell_port = self.shell_port,
                    iopub_port = self.iopub_port,
                    control_port = self.control_port,
                    hb_port = self.hb_port,
                    ip = self.ip)

            self.ipylogic.logMsg('To connect another client to this IPython kernel, use: ipython console --existing {0}'.format(self.connection_file), msgType='status')
        except Exception as e:
            self.ipylogic.logMsg('Exception while initializing IPython ZMQ kernel. {0}'.format(e), msgType='error')
            raise
        self.sigRunKernel.connect(self.runKernel)
        self.sigRunKernel.emit()

    def cleanupConnectionFile(self):
        try:
            if not self.connectionFileClean:
                os.remove(self.connection_file)
                self.connectionFileClean = True
        except (IOError, OSError):
            pass

    def runKernel(self):
        self.heartbeat.start()
        self.kernel.start()
        self.ipylogic.logMsg('IPython running.', msgType='status')
        self.ipylogic.logMsg('IPython kernel started in thread {0}'.format(threading.get_ident()), msgType='thread')
        self.loop = IOLoop.instance()
        self.ipylogic.logMsg('IPython kernel running in thread {0}'.format(threading.get_ident()), msgType='thread')
        # start ipython main loop
        self.loop.start()
        self.ipylogic.logMsg('IPython kernel stopped in thread {0}'.format(threading.get_ident()), msgType='thread')

        # remove connection file
        self.cleanupConnectionFile()
        atexit.unregister(self.cleanupConnectionFile)
        # stop ipython loop
        # cleanup directly after loop terminates, needs to be in same thread
        self.kernel.shell.atexit_operations()
        atexit.unregister(self.kernel.shell.atexit_operations)
        #print(self.kernel.shell.magics_manager.registry)
        if 'ScriptMagics' in self.kernel.shell.magics_manager.registry:
             self.kernel.shell.magics_manager.registry['ScriptMagics'].kill_bg_processes()
             atexit.unregister(self.kernel.shell.magics_manager.registry['ScriptMagics'].kill_bg_processes)
        self.kernel.shell.history_manager.save_thread.stop()
        atexit.unregister(self.kernel.shell.history_manager.save_thread.stop)
        # stop heartbeat
        # destroy heartbeat zmq context
        # close and remove zmq streams
        # close and remove zmq sockets
        self.control_socket.close()
        self.iopub_socket.close()
        self.shell_socket.close()
        #stop session

