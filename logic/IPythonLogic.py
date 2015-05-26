# -*- coding: utf-8 -*-

from logic.GenericLogic import GenericLogic
from core.util.Mutex import Mutex
from collections import OrderedDict
from pyqtgraph.Qt import QtCore

import os
import zmq
import IPython.kernel.zmq.ipkernel
from IPython.kernel.zmq.ipkernel import Kernel
from IPython.kernel.zmq.heartbeat import Heartbeat
from IPython.kernel.zmq.session import Session
from IPython.kernel import write_connection_file
from zmq.eventloop import ioloop
from zmq.eventloop.zmqstream import ZMQStream
import atexit
import socket
import logging

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
    
    def deactivation(self, e=None):
        pass

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

    def cleanup_connection_file(self):
        try:
            os.remove(self.connection_file)
        except (IOError, OSError):
            pass

    def activation(self, e=None):
        # You can remotely connect to this kernel. See the output on stdout.
        IPython.kernel.zmq.ipkernel.signal = lambda sig, f: None  # Overwrite.
        # Do in mainthread to avoid history sqlite DB errors at exit.
        # https://github.com/ipython/ipython/issues/680
        try:
            self.connection_file = 'kernel-{0}.json'.format(os.getpid())
            atexit.register(self.cleanup_connection_file)

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
            self.heartbeat.start()

            self.shell_stream = ZMQStream(self.shell_socket)
            self.control_stream = ZMQStream(self.control_socket)

            self.kernel = Kernel(
                    session = self.session,
                    shell_streams = [self.shell_stream, self.control_stream],
                    iopub_socket = self.iopub_socket,
                    log = self.logger)

            write_connection_file(
                    self.connection_file,
                    shell_port = self.shell_port,
                    iopub_port = self.iopub_port,
                    control_port = self.control_port,
                    hb_port = self.hb_port,
                    ip = self.ip)

            self.logMsg('To connect another client to this IPython kernel, use: ipython console --existing {0}'.format(self.connection_file), msgType='status')
            self.sigRunKernel.connect(self.runloop, QtCore.Qt.QueuedConnection)
            self.sigRunKernel.emit()

        except Exception as e:
            self.logMsg('Exception while initializing IPython ZMQ kernel. {0}'.format(e), msgType='error')
            raise

    def runloop(self):
        self.kernel.start()
        try:
            ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            pass
