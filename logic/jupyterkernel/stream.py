# -*- coding: utf-8 -*-
"""
Qt-based ZMQ stream

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
import zmq
from qtpy import QtCore
import logging

class QZMQStream(QtCore.QObject):
    """ Qt based ZMQ stream.
        QSignal based notifications about arriving ZMQ messages.
    """
    sigMsgRecvd = QtCore.Signal(object)

    def __init__(self, zmqsocket):
        """ Make a stream from a socket.

        @param zmqsocket: ZMQ socket
        """
        super().__init__()
        self.socket = zmqsocket
        self.readnotifier = QtCore.QSocketNotifier(
            self.socket.get(zmq.FD),
            QtCore.QSocketNotifier.Read)
        logging.debug( "Notifier: {0!s}".format(self.readnotifier.socket()))
        self.readnotifier.activated.connect(self.checkForMessage)

    def checkForMessage(self, socket):
        """ Check on socket activity if there is a complete ZMQ message.

          @param socket: ZMQ socket
        """
        logging.debug( "Check: {0!s}".format(self.readnotifier.socket()))
        self.readnotifier.setEnabled(False)
        check = True
        try:
            while check:
                events = self.socket.get(zmq.EVENTS)
                check = events & zmq.POLLIN
                logging.debug( "EVENTS: {0!s}".format(events))
                if check:
                    try:
                        msg = self.socket.recv_multipart(zmq.NOBLOCK)
                    except zmq.ZMQError as e:
                        if e.errno == zmq.EAGAIN:
                            # state changed since poll event
                            pass
                        else:
                            logging.info( "RECV Error: {0!s}".format(zmq.strerror(e.errno)))
                    else:
                        logging.debug( "MSG: {0!s} {1!s}".format(self.readnotifier.socket(), msg))
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


