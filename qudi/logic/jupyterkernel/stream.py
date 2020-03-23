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
import json
import uuid
import errno
import datetime
from io import StringIO
import threading
from threading import Thread, Lock, Event
import time
from core.util.mutex import Mutex


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
        self.name = None
        self.socket = zmqsocket
        self.readnotifier = QtCore.QSocketNotifier(
            self.socket.get(zmq.FD),
            QtCore.QSocketNotifier.Read)
        logging.debug("Notifier: {0!s} at filenumber {1!s} with socket {2!s} of class {3!s}".format(self.readnotifier.socket(),
                                                                                                    self.socket.get(zmq.FD),
                                                                                                    self.socket,
                                                                                                    self.name))
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
                            logging.debug("state changed since poll event")
                            # state changed since poll event
                            pass
                        else:
                            logging.info("RECV Error: {0!s}".format(zmq.strerror(e.errno)))
                    else:
                        logging.debug("MSG: {0!s} {1!s}".format(self.readnotifier.socket(), msg))
                        self.sigMsgRecvd.emit(msg)
        except:
            logging.debug("Exception in QZMQStream::checkForMessages")
            pass
        else:
            self.readnotifier.setEnabled(True)

    def close(self):
        """ Remove all notifiers from socket.
        """
        self.readnotifier.setEnabled(False)
        self.readnotifier.activated.disconnect()
        self.sigMsgRecvd.disconnect()


class QZMQHeartbeat(QtCore.QObject):
    """ Echo Messages on a ZMQ stream. """

    def __init__(self, stream):
        super().__init__()
        self.stream = stream
        self.stream.sigMsgRecvd.connect(self.beat)

    @QtCore.Slot(bytes)
    def beat(self, msg):
        """ Send a message back.

          @param msg: message to be sent back
        """
        logging.debug("HB: {}".format(msg))
        if len(msg) > 0:
            retmsg = msg[0]
            try:
                self.stream.socket.send(retmsg)
            except zmq.ZMQError as e:
                if e.errno != errno.EINTR:
                    raise


class NetworkStream(QZMQStream):

    def __init__(self, context, zqm_type, connection, auth, engine_id, name=None, port=0):
        self.name = name if name is not None else self.msg_id()
        self._socket = context.socket(zqm_type)
        self._port = self.bind(self._socket, connection, port)
        super().__init__(self._socket)

        self._auth = auth
        self._engine_id = engine_id

        self.DELIM = b"<IDS|MSG>"
        self._parent_header = dict()
        self._threadlock = Mutex()

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
        with self._threadlock:
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
            logging.debug('{0!s} send parts: {1!s}'.format(self.name, parts))
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


class IOStdoutNetworkStream(StringIO):
    """
    This class extends the StringIO to redirect the data via network stream.
    It uses a thread (not Qt but a normal python thread) to regularly query the buffer and send it off.
    By using locks thread safety should be guaranteed for the write operation.
    """

    def __init__(self, network_stream, old_stdout, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._output_channel = 'stdout'
        self._network_stream = network_stream
        self._old_stdout = old_stdout

        self._lock = Lock()
        self._stop = Event()
        self._stop.clear()
        # initialize the thread for the hardware query
        self._network_thread = Thread(target=self._run_network_loop, name='redirect ' + self._output_channel)

        # start the threads
        self._network_thread.start()

    def write(self, s):
        self._lock.acquire()
        if hasattr(threading.current_thread(), 'notebook_thread'):
            super().write(s)
        else:
            self._old_stdout.write(s)
        self._lock.release()

    def _run_network_loop(self):
        while not self._stop.is_set():
            self._dump_stream_to_network()
            # one query every 10 ms should be more than enough
            time.sleep(0.1)

        # clean up the buffer
        self._dump_stream_to_network()
        super().close()

    def _dump_stream_to_network(self):
        if self.tell() > 0:
            # get the data and reset the stream
            self._lock.acquire()
            s = self.getvalue()
            self.truncate(0)
            self.seek(0)
            self._lock.release()

            # send off the data
            content = {
                'name': self._output_channel,
                'text': s,
            }
            self._network_stream.send(msg_type='stream', content=content)

    def close(self):
        self._dump_stream_to_network()
        self._stop.set()


class IOStderrNetworkStream(IOStdoutNetworkStream):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._output_channel = 'stderr'
