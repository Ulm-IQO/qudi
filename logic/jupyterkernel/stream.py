# -*- coding: utf-8 -*-
"""
Qt-based IPython/jupyter kernel

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

Copyright (C) 2016 Jan M. Binder jan.binder@uni-ulm.de
"""
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


