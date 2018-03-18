import traceback
from typing import Callable, Any
from enum import IntEnum
import asyncio

from .frame import read_frame
from .sender import (
    send_connection_start,
    send_connection_tune,
)
from .heartbeat import HeartBeat
from .method import MethodIDs

PROTOCOL_HEADER = b'AMQP\x00\x00\x09\x01'
CE_END_FRAME = b'\xce'


class _ParserState(IntEnum):
    """State of the parsing state machine."""

    WAITING_PROTOCOL_HEADER = 1
    WAITING_CONNECTION_START_OK = 2
    WAITING_CONNECTION_TUNE_OK = 3
    WAITING_CONNECTION_OPEN = 4


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
        self._buffer = b''
        self._parser_state = _ParserState.WAITING_PROTOCOL_HEADER

    def connection_made(self, transport):
        """Handle new connection """
        self.transport = transport

    def connection_lost(self, exception):

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
        self._buffer += data

        if self._parser_state == _ParserState.WAITING_PROTOCOL_HEADER:
            protocol_ok = self._check_protocol_header()
            if not protocol_ok:
                return

            send_connection_start(self.transport)
            self._parser_state = _ParserState.WAITING_CONNECTION_START_OK
            return

        print("data")
        while len(self._buffer) > 0:
            frame_value = read_frame(self._buffer)
            if not frame_value:
                print("no frame :(")
                # no more complete frame available
                # => wait for next data
                return
            print("frame")
            print(frame_value)
            self._buffer = self._buffer[frame_value.size:]

            if isinstance(frame_value, HeartBeat):
                continue

            if self._parser_state == _ParserState.WAITING_CONNECTION_START_OK:
                correct_credentials = self._check_start_ok(frame_value)

                if not correct_credentials:
                    # TODO: we're supposed to send a connection.close method
                    # https://www.rabbitmq.com/auth-notification.html
                    self.transport.close()
                    return

                send_connection_tune(self.transport)
                self._parser_state = _ParserState.WAITING_CONNECTION_TUNE_OK
                return

            if self._parser_state == _ParserState.WAITING_CONNECTION_TUNE_OK:
                if frame_value.method_id != MethodIDs.TUNE_OK:
                    self.transport.close()
                    return
                self._parser_state = _ParserState.WAITING_CONNECTION_OPEN
                continue

            if self._parser_state == _ParserState.WAITING_CONNECTION_OPEN:
                if frame_value.method_id != MethodIDs.OPEN:
                    self.transport.close()
                    return
                self._check_open(frame_value)
                continue

    def _check_protocol_header(self):
        if len(self._buffer) < len(PROTOCOL_HEADER):
            # underflow
            return False

        if self._buffer != PROTOCOL_HEADER:
            self.transport.close()
            self._buffer = b''
            return False

        self._buffer = b''
        return True
        print("sent")

    def _check_start_ok(self, method):
        if method.properties['mechanism'] != "PLAIN":
            return False
        # TODO: use callback to check username/password correctness
        _ , username, password = method.properties['response'].split('\x00', 3)
        return True;

    def _check_open(self, method):
        # TODO: use callback to check user has access to vhost etc.
        return True
