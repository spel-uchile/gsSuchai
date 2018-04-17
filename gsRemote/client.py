# -*- coding: latin-1 -*-

#                          Part of SERIAL COMMANDER
#                A simple serial interface to send commands
#
#      Copyright 2013, Carlos Gonzalez Cortes, carlgonz@ug.uchile.cl
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from PyQt4.QtCore import QObject, pyqtSignal
from threading import Thread
import zmq


class Client(QObject):

    new_message = pyqtSignal(str)

    def __init__(self, server="localhost", send_port="5557", recv_port="5556", dbg_port="5558"):
        """
        Creates a ZMQ Client object capable to send messages using ZMQ.PUSH in
        send_port and receive any message using ZMQ.SUB in recv_port and
        dbg_port
        :param server: Str. remote publisher address
        :param send_port: Str. remote receiver port
        :param recv_port: Str. port to receive messages
        :param dbg_port: Str. port to receive dbg messages.
        """
        QObject.__init__(self)
        self._run = True
        self.context = zmq.Context()

        # Sender socket using PULL-PUSH pattern
        self.sender_socket = self.context.socket(zmq.PUSH)
        self.sender_socket.connect("tcp://{0}:{1}".format(server, send_port))

        # Start receiver thread
        args = (self.context, server, recv_port)
        self.recv_thread = Thread(target=self.receive, args=args)
        self.recv_thread.start()
        
        # Start debug receiver thread
        dargs = (self.context, server, dbg_port)
        self.rdbg_thread = Thread(target=self.receive, args=dargs)
        self.rdbg_thread.start()

    def close(self):
        """
        Stop the client, join receiver threads and close zmq connections.
        :return: None
        """
        self._run = False
        self.recv_thread.join(10)
        self.rdbg_thread.join(10)
        self.sender_socket.close(1)
        self.context.destroy(1)

    def send(self, message):
        """
        Send a message
        :param message: Str. Message to send
        :return: None
        """
        self.sender_socket.send(message.encode())

    def receive(self, context, server, port):
        """
        Thread to receive messages. Message are sent to GUI using a signal.
        :param context: zmq context
        :param server: Str. remote publisher address
        :param port: Str. remote publisher port
        :return: None
        """
        # Receiver socket using SUB_PUB pattern
        receiver_socket = context.socket(zmq.SUB)
        receiver_socket.connect("tcp://{0}:{1}".format(server, port))
        receiver_socket.setsockopt(zmq.SUBSCRIBE, b"")
        poller = zmq.Poller()
        poller.register(receiver_socket, zmq.POLLIN)

        while self._run:
            # Get the publisher's message
            socks = dict(poller.poll(500))
            if receiver_socket in socks and socks[receiver_socket] == zmq.POLLIN:
                message = receiver_socket.recv()
                try:
                    message = message.decode("utf-8")
                except UnicodeDecodeError:
                    # Fix receiving invalids messages from GNU radio ZMQ sink
                    message = message[3:].decode("utf-8")
                self.new_message.emit(message)

        receiver_socket.close(1)
