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
import io
import json
import hmac
import uuid
import errno
import hashlib
import datetime


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
        logging.debug("Notifier: {0!s}".format(self.readnotifier.socket()))
        self.readnotifier.activated.connect(self.checkForMessage)

    def checkForMessage(self, socket):
        """ Check on socket activity if there is a complete ZMQ message.

          @param socket: ZMQ socket
        """
        logging.debug("Check: {0!s}".format(self.readnotifier.socket()))
        self.readnotifier.setEnabled(False)
        check = True
        try:
            while check:
                events = self.socket.get(zmq.EVENTS)
                check = events & zmq.POLLIN
                logging.debug("EVENTS: {0!s}".format(events))
                if check:
                    try:
                        msg = self.socket.recv_multipart(zmq.NOBLOCK)
                    except zmq.ZMQError as e:
                        if e.errno == zmq.EAGAIN:
                            # state changed since poll event
                            pass
                        else:
                            logging.info("RECV Error: {0!s}".format(zmq.strerror(e.errno)))
                    else:
                        logging.debug("MSG: {0!s} {1!s}".format(self.readnotifier.socket(), msg))
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


class NetworkStream(QZMQStream):

    def __init__(self, context, zqm_type, connection, auth, engine_id, port=0):

        self._socket = context.socket(zqm_type)
        self._port = self.bind(self._socket, connection, port)
        super().__init__(self._socket)

        self._auth = auth
        self._engine_id = engine_id

        self.DELIM = b"<IDS|MSG>"
        self._parent_header = dict()

    def close(self):
        super().close()
        self._socket.close()

    @property
    def parent_header(self):
        return self._parent_header.copy()

    @parent_header.setter
    def parent_header(self, value):
        self._parent_header = value.copy()

    @property
    def port(self):
        return self._port

    @staticmethod
    def bind(socket, connection, port):
        if port <= 0:
            return socket.bind_to_random_port(connection)
        else:
            socket.bind("%s:%s" % (connection, port))
        return port

    @staticmethod
    def msg_id():
        """ Return a new uuid for message id """
        return str(uuid.uuid4())

    def sign(self, msg_lst):
        """
        Sign a message with a secure signature.
        """
        h = self._auth.copy()
        for m in msg_lst:
            h.update(m)
        return h.hexdigest().encode('ascii')

    def new_header(self, msg_type):
        """make a new header"""
        return {
            "date": datetime.datetime.now().isoformat(),
            "msg_id": self.msg_id(),
            "username": "kernel",
            "session": self._engine_id,
            "msg_type": msg_type,
            "version": "5.0",
        }

    def send(self, msg_type, content=None, parent_header=None, metadata=None, identities=None):
        header = self.new_header(msg_type)
        if content is None:
            content = dict()
        if parent_header is None:
            parent_header = self._parent_header
        if metadata is None:
            metadata = dict()

        def jencode(msg):
            return json.dumps(msg).encode('ascii')

        msg_lst = [
            jencode(header),
            jencode(parent_header),
            jencode(metadata),
            jencode(content),
        ]
        signature = self.sign(msg_lst)
        parts = [self.DELIM,
                 signature,
                 msg_lst[0],
                 msg_lst[1],
                 msg_lst[2],
                 msg_lst[3]]
        if identities:
            parts = identities + parts
        logging.debug("send parts: %s" % parts)
        self.socket.send_multipart(parts)

    def deserialize_wire_msg(self, wire_msg):
        """split the routing prefix and message frames from a message on the wire"""
        delim_idx = wire_msg.index(self.DELIM)
        identities = wire_msg[:delim_idx]
        m_signature = wire_msg[delim_idx + 1]
        msg_frames = wire_msg[delim_idx + 2:]

        def jdecode(msg):
            return json.loads(msg.decode('ascii'))

        m = {'header': jdecode(msg_frames[0]), 'parent_header': jdecode(msg_frames[1]),
             'metadata': jdecode(msg_frames[2]), 'content': jdecode(msg_frames[3])}
        check_sig = self.sign(msg_frames)
        if check_sig != m_signature:
            raise ValueError("Signatures do not match")

        return identities, m

    def write(self, s):
        content = {
            'name': "stdout",
            'text': s,
        }
        self.send(msg_type='stream', content=content)

    def flush(self):
        pass

    @property
    def readable(self):
        return False

    @property
    def writable(self):
        return True
