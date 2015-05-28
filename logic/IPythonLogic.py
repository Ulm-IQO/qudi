# -*- coding: utf-8 -*-

from logic.GenericLogic import GenericLogic
from core.util.Mutex import Mutex
from collections import OrderedDict
from pyqtgraph.Qt import QtCore

import os
import sys
import zmq
import IPython.kernel.zmq.ipkernel
from IPython.kernel.zmq.ipkernel import Kernel
from IPython.kernel.zmq.heartbeat import Heartbeat
from IPython.kernel.zmq.session import Session
from IPython.kernel import write_connection_file
from IPython.core.interactiveshell import InteractiveShell
from zmq.eventloop.zmqstream import ZMQStream
from zmq.eventloop.ioloop import IOLoop
import atexit
import socket
import logging
import threading

def _on_os_x_10_9():
    import platform
    from distutils.version import LooseVersion as V
    return sys.platform == 'darwin' and V(platform.mac_ver()[0]) >= V('10.9')


class IPythonLogic(GenericLogic):        
    """ Logic module containing an IPython kernel.
    """
    _modclass = 'ipythonlogic'
    _modtype = 'logic'
    sigRunKernel = QtCore.Signal()
        
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
    
    def deactivation(self, e=None):
        # remove connection file
        self.cleanupConnectionFile()
        atexit.unregister(self.cleanupConnectionFile)
        # stop ipython loop
        self.loop.loop.stop()
        # stop heartbeat

        # destroy heartbeat zmq context

        # close and remove zmq streams

        # close and remove zmq sockets


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

    def cleanupConnectionFile(self):
        try:
            if not self.connectionFileClean:
                os.remove(self.connection_file)
                self.connectionFileClean = True
        except (IOError, OSError):
            pass

    def activation(self, e=None):
        self.logMsg('IPython kernel created in thread{0}'.format(threading.get_ident()), msgType='thread')
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

            self.namespace = {'manager': self._manager}
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

            self.logMsg('To connect another client to this IPython kernel, use: ipython console --existing {0}'.format(self.connection_file), msgType='status')
            self.sigRunKernel.connect(self.runloop, QtCore.Qt.QueuedConnection)
        except Exception as e:
            self.logMsg('Exception while initializing IPython ZMQ kernel. {0}'.format(e), msgType='error')
            raise
        self.sigRunKernel.emit()

    def runloop(self):
        self.heartbeat.start()
        self.kernel.start()
        self.loop = IPythonMainLoop()
        self.loop.start()
        self.logMsg('IPython running.', msgType='status')

class IPythonMainLoop(QtCore.QThread):
    def __init__(self):
        super().__init__()
        self.loop = IOLoop.instance()

    def run(self):
        #self.logMsg('IPython kernel running in thread{0}'.format(threading.get_ident()), msgType='thread')
        # start ipython main loop
        self.loop.start()
        # cleanup directly after loop terminates, needs to be in same thread
        InteractiveShell.instance().atexit_operations()
        atexit.unregister(InteractiveShell.instance().atexit_operations)
