# -*- coding: utf-8 -*-
"""
Qt-based ZMQ stream

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
import zmq
from pyqtgraph.Qt import QtCore
QtCore.Signal = QtCore.pyqtSignal
import logging

class QZMQStream(QtCore.QObject):
    """ Qt based ZMQ stream.
        QSignal based notifications about arriving ZMQ messages.
    """
    sigMsgRecvd = QtCore.Signal(object)

    def __init__(self, zmqsocket):
        """ Make a stream from a socket.
        
        @param socket: ZMQ socket
        """
        super().__init__()
        self.socket = zmqsocket
        self.readnotifier = QtCore.QSocketNotifier(
            self.socket.get(zmq.FD),
            QtCore.QSocketNotifier.Read)
        logging.debug( "Notifier: %s" % self.readnotifier.socket())
        self.readnotifier.activated.connect(self.checkForMessage)

    def checkForMessage(self, socket):
        """ Check on socket activity if there is a complete ZMQ message.

          @param socket: ZMQ socket
        """
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
        """ Remove all notifiers from socket.
        """
        self.readnotifier.setEnabled(False)
        self.readnotifier.activated.disconnect()
        self.sigMsgRecvd.disconnect()


