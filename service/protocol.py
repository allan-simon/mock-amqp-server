import traceback
from typing import Callable, Any
from enum import IntEnum
from struct import pack
import asyncio
from collections import deque

from .serialization import dumps

PROTOCOL_HEADER = [i for i in b'AMQP\x00\x00\x09\x01']
CE_END_FRAME = b'\xce'


class _ParserState(IntEnum):
    """State of the parsing state machine."""

    WAITING_PROTOCOL_HEADER = 1
    WAITING_CONNECTION_START_OK = 2


class TrackerProtocol(asyncio.protocols.Protocol):
    """Handle connection and bytes parsing."""

    def __init__(
        self,
    ) -> None:
        """Create a new instance.

        And set the external callback that will be responsible
        to treat the message. (put it into a Queue for example)
        As well as the callback used to associate an IMEI to a connection
        so that we can send back message to the trackers, and the callback
        when the connection is lost.
        """
        self.transport = None  # type: asyncio.transports.Transport
        self._buffer = deque()
        self._parser_state = _ParserState.WAITING_PROTOCOL_HEADER

    def connection_made(self, transport):
        """Handle new connection """
        self.transport = transport

    def connection_lost(self, exception):

        if self.imei is not None:
            self.on_connection_lost(self.imei)

        if exception is None:
            return

        # see https://stackoverflow.com/questions/9555133
        traceback_list = traceback.format_exception(
            None,  # <- type(e) by docs, but ignored
            exception,
            exception.__traceback__,
        )
        print(traceback_list)

    def data_received(self, data):
        """Treat incoming bytes and handle the state machine.

        State transitions in normal case:

        """
        self._buffer.extend(data)
        print(data)
        if self._parser_state == _ParserState.WAITING_PROTOCOL_HEADER:
            self._check_protocol_header()
            return

    def _check_protocol_header(self):
        if len(self._buffer) < len(PROTOCOL_HEADER):
            # underflow
            return
        header = [
            self._buffer.popleft()
            for _i in range(len(PROTOCOL_HEADER))
        ]
        if header != PROTOCOL_HEADER:
            self.transport.close()
            return
        self._send_connection_start()
        self._parser_state = _ParserState.WAITING_CONNECTION_START_OK
        print("sent")

    def _send_connection_start(self):

        # dumped from the peer-properties sent by a RabbitMQ 3.7.4
        # server
        peer_properties = {
            'capabilities': {
                'authentication_failure_close': True,
                'consumer_priorities': True,
                'exchange_exchange_bindings': True,
                'direct_reply_to': True,
                'per_consumer_qos': True,
                'basic.nack': True,
                'publisher_confirms': True,
                'consumer_cancel_notify': True,
                'connection.blocked': True
            },
            'information': 'Licensed under the MPL.  See http://www.rabbitmq.com/',
            'cluster_name': 'rabbit@60b584cb4c1b',
            'product': 'RabbitMQ', 'version': '3.7.4',
            'copyright': 'Copyright (C) 2007-2018 Pivotal Software, Inc.',
            'platform': 'Erlang/OTP 20.2.4'
        }
        mechanisms = 'PLAIN AMQPLAIN'
        locales = 'en_US'

        arguments = dumps(
            format='ooFSS',
            values=[
                0,
                9,
                peer_properties,
                mechanisms,
                locales,
            ]
        )

        self.transport.write(
            bytearray(
                [
                    1,  # method
                    0, 0,  # channel number 0
                ]
            )
        )
        # size of the frame
        # class+method (4 bytes) + bytes len of arguments
        self.transport.write(pack('>I', 4 + len(arguments) ))

        self.transport.write(
            bytearray([
                0, 10,  # class connection (10)
                0, 10,  # method start (10)
            ])
        )

        self.transport.write(arguments)
        self.transport.write(CE_END_FRAME)
