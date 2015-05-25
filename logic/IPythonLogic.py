# -*- coding: utf-8 -*-

from logic.GenericLogic import GenericLogic
from core.util.Mutex import Mutex
from collections import OrderedDict

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
        
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {
            'on_activate': self.activation,
            'on_deactivate': self.deactivation
            }
        super.__init__(self, manager, name, config, state_actions, **kwargs)
    
        ## declare connectors    
        self.connector['out']['ipythonlogic'] = OrderedDict()
        self.connector['out']['ipythonlogic']['class'] = 'IPythonLogic'
            
        #locking for thread safety
        self.lock = Mutex()
    
    def activation(self, e=None):
        pass

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

    def initIPythonKernel():
        # You can remotely connect to this kernel. See the output on stdout.
        try:
            IPython.kernel.zmq.ipkernel.signal = lambda sig, f: None  # Overwrite.
        except ImportError, e:
            print "IPython import error, cannot start IPython kernel. %s" % e
            return
        # Do in mainthread to avoid history sqlite DB errors at exit.
        # https://github.com/ipython/ipython/issues/680
        try:
            connection_file = "kernel-%s.json" % os.getpid()
            def cleanup_connection_file():
                try:
                    os.remove(connection_file)
                except (IOError, OSError):
                    pass
            atexit.register(cleanup_connection_file)

            logger = logging.Logger("IPython")
            logger.addHandler(logging.NullHandler())
            session = Session(username='kernel')

            context = zmq.Context.instance()
            ip = socket.gethostbyname(socket.gethostname())
            transport = "tcp"
            addr = "%s://%s" % (transport, ip)
            shell_socket = context.socket(zmq.ROUTER)
            shell_port = shell_socket.bind_to_random_port(addr)
            iopub_socket = context.socket(zmq.PUB)
            iopub_port = iopub_socket.bind_to_random_port(addr)
            control_socket = context.socket(zmq.ROUTER)
            control_port = control_socket.bind_to_random_port(addr)

            hb_ctx = zmq.Context()
            heartbeat = Heartbeat(hb_ctx, (transport, ip, 0))
            hb_port = heartbeat.port
            heartbeat.start()

            shell_stream = ZMQStream(shell_socket)
            control_stream = ZMQStream(control_socket)

            kernel = Kernel(
                    session = session,
                    shell_streams = [shell_stream, control_stream],
                    iopub_socket = iopub_socket,
                    log = logger)

            write_connection_file(
                    connection_file,
                    shell_port = shell_port,
                    iopub_port = iopub_port,
                    control_port = control_port,
                    hb_port = hb_port,
                    ip = ip)

            print('To connect another client to this IPython kernel, use:',
                'ipython console --existing {0}'.format(connection_file) )
        except Exception, e:
            print('Exception while initializing IPython ZMQ kernel. {0}'.format(e))
            return

        def ipython_thread():
            kernel.start()
            try:
                ioloop.IOLoop.instance().start()
            except KeyboardInterrupt:
                pass
