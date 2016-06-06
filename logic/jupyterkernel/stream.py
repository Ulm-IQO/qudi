# -*- coding: utf-8 -*-
import zmq
from pyqtgraph.Qt import QtCore
QtCore.Signal = QtCore.pyqtSignal
import logging

class QZMQStream(QtCore.QObject):
    sigMsgRecvd = QtCore.Signal(object)

    def __init__(self, zmqsocket):
        super().__init__()
        self.socket = zmqsocket
        self.readnotifier = QtCore.QSocketNotifier(
            self.socket.get(zmq.FD),
            QtCore.QSocketNotifier.Read)
        logging.debug( "Notifier: %s" % self.readnotifier.socket())
        self.readnotifier.activated.connect(self.checkForMessage)

    def checkForMessage(self, socket):
        logging.debug( "Check: %s" % self.readnotifier.socket())
        self.readnotifier.setEnabled(False)
        check = True
        try:
            while check:
                events = self.socket.get(zmq.EVENTS)
                check = events & zmq.POLLIN
                logging.debug( "EVENTS: %s" % events)
                if check:
                    try:
                        msg = self.socket.recv_multipart(zmq.NOBLOCK)
                    except zmq.ZMQError as e:
                        if e.errno == zmq.EAGAIN:
                            # state changed since poll event
                            pass
                        else:
                            logging.info( "RECV Error: %s" % zmq.strerror(e.errno))
                    else:
                        logging.debug( "MSG: %s %s" % (self.readnotifier.socket(), msg))
                        self.sigMsgRecvd.emit(msg)
        except:
            pass
        else:
            self.readnotifier.setEnabled(True)

    def close(self):
        self.readnotifier.setEnabled(False)
        self.readnotifier.activated.disconnect()
        self.sigMsgRecvd.disconnect()


