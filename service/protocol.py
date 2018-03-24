import traceback
from typing import Callable, Any
from enum import IntEnum
import asyncio

from .frame import read_frame
from .sender import (
    send_connection_start,
    send_connection_tune,
    send_connection_ok,
    send_heartbeat,
    send_channel_open_ok,
    send_channel_close_ok,
    send_exchange_declare_ok,
    send_queue_declare_ok,
    send_queue_bind_ok,
    send_basic_qos_ok,
    send_basic_consume_ok,
)
from .heartbeat import HeartBeat
from .method import MethodIDs
from .message import Message
from .serialization import loads

PROTOCOL_HEADER = b'AMQP\x00\x00\x09\x01'
CE_END_FRAME = b'\xce'


class _ConnectionState(IntEnum):
    """State of the parsing state machine."""

    WAITING_PROTOCOL_HEADER = 1
    WAITING_START_OK = 2
    WAITING_TUNE_OK = 3
    WAITING_OPEN = 4
    OPENED = 5

    WAITING_OTHER = 999

class _ChannelState(IntEnum):
    WAITING_OPEN = 1
    OPENED = 2
    WAITING_HEADER = 3
    WAITING_BODY = 4


class TrackerProtocol(asyncio.protocols.Protocol):
    """Handle connection and bytes parsing."""

    def __init__(
        self,
        global_state,
    ) -> None:
        """Create a new instance.
        """
        self.transport = None  # type: asyncio.transports.Transport
        self._global_state = global_state

        self._buffer = b''
        self._parser_state = _ConnectionState.WAITING_PROTOCOL_HEADER
        self._channels = {}

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

        if self._parser_state == _ConnectionState.WAITING_PROTOCOL_HEADER:
            protocol_ok = self._check_protocol_header()
            if not protocol_ok:
                return

            send_connection_start(self.transport)
            self._parser_state = _ConnectionState.WAITING_START_OK
            return

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
                send_heartbeat(self.transport)
                print("send hearbeat")
                continue

            if frame_value.channel_number != 0:
                self._upsert_channel(frame_value.channel_number)
                self._treat_channel_frame(frame_value)
                continue

            if self._parser_state == _ConnectionState.WAITING_START_OK:
                correct_credentials = self._check_start_ok(frame_value)

                if not correct_credentials:
                    # TODO: we're supposed to send a connection.close method
                    # https://www.rabbitmq.com/auth-notification.html
                    self.transport.close()
                    return

                send_connection_tune(self.transport)
                self._parser_state = _ConnectionState.WAITING_TUNE_OK
                return

            if self._parser_state == _ConnectionState.WAITING_TUNE_OK:
                if frame_value.method_id != MethodIDs.TUNE_OK:
                    self.transport.close()
                    return
                self._parser_state = _ConnectionState.WAITING_OPEN
                continue

            if self._parser_state == _ConnectionState.WAITING_OPEN:
                if frame_value.method_id != MethodIDs.OPEN:
                    self.transport.close()
                    return

                open_is_ok = self._check_open(frame_value)
                if not open_is_ok:
                    self.transport.close()
                    return

                send_connection_ok(self.transport)
                self._parser_state = _ConnectionState.OPENED
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
        if method.properties['mechanism'] not in ["PLAIN", "AMQPLAIN"]:
            return False

        # TODO: use callback to check username/password correctness
        if method.properties['mechanism'] == "PLAIN":
            _ , username, password = method.properties['response'].split('\x00', 3)

        if method.properties['mechanism'] == "AMQPLAIN":
            _, _, username, _, _, password = loads(
                'soSsoS',
                method.properties['response'].encode('utf-8')
            )[0]  # [0] decoded values, [1] => length decoded

        accepted = self._global_state.check_credentials(
            username,
            password
        );

        return accepted;

    def _check_open(self, method):
        # TODO: use callback to check user has access to vhost etc.
        return True

    def _check_channel_open(self, method):
        return True

    def _upsert_channel(self, channel_number):
        if channel_number not in self._channels:
            print("new channel", channel_number)
            self._channels[channel_number] = {
                'state': _ChannelState.WAITING_OPEN,
                'number': channel_number,
            }

    def _treat_channel_frame(self, frame_value):
        channel = self._channels[frame_value.channel_number]
        channel_number = frame_value.channel_number

        if channel['state'] == _ChannelState.WAITING_OPEN:
            if frame_value.method_id != MethodIDs.CHANNEL_OPEN:
                self.transport.close()
                return

            open_is_ok = self._check_channel_open(frame_value)
            if not open_is_ok:
                self.transport.close()
                return

            send_channel_open_ok(
                self.transport,
                channel_id='42',
                channel_number=channel['number'],
            )
            print("send_channel open ok")
            channel['state'] = _ChannelState.OPENED
            return

        if frame_value.method_id == MethodIDs.CHANNEL_CLOSE:
            del self._channels[channel_number]
            send_channel_close_ok(self.transport, channel_number)
            print("closed")
            self.transport.close()
            return

        if channel['state'] == _ChannelState.OPENED:

            if frame_value.method_id == MethodIDs.EXCHANGE_DECLARE:
                # TODO add exchange declare callback
                send_exchange_declare_ok(
                    self.transport,
                    channel_number,
                )
                print("exchange ok")
                return

            if frame_value.method_id == MethodIDs.QUEUE_DECLARE:
                # TODO add queue declare callback
                # and get message_count / consumer_count
                send_queue_declare_ok(
                    self.transport,
                    channel_number,
                    frame_value.properties['queue-name'],
                    message_count=0,
                    consumer_count=0,
                )
                print("queue ok")
                return

            if frame_value.method_id == MethodIDs.QUEUE_BIND:
                # TODO add queue bind callback
                send_queue_bind_ok(
                    self.transport,
                    channel_number,
                )
                print("queue bind")
                return

            if frame_value.method_id == MethodIDs.BASIC_QOS:
                # TODO add basic qos callback
                send_basic_qos_ok(
                    self.transport,
                    channel_number,
                )
                print("basic qos")
                return

            if frame_value.method_id == MethodIDs.BASIC_PUBLISH:
                print("message published started")
                channel['state'] = _ChannelState.WAITING_HEADER
                channel['exchange'] = frame_value.properties['exchange-name']
                channel['routing_key'] = frame_value.properties['exchange-name']
                return

            if frame_value.method_id == MethodIDs.BASIC_CONSUME:

                # TODO add basic qos callback
                send_basic_consume_ok(
                    self.transport,
                    channel_number,
                    frame_value.properties['consumer-tag']
                )
                print("basic consume")
                return

            return

        if channel['state'] == _ChannelState.WAITING_HEADER:
            if not frame_value.is_header:
                return

            channel['on_going_message'] = Message(header=frame_value)
            channel['state'] = _ChannelState.WAITING_BODY

        if channel['state'] == _ChannelState.WAITING_BODY:
            if not frame_value.is_body:
                return

            message = channel['on_going_message']
            message.add_content(frame_value.content)
            if not message.is_complete():
                return

            # TODO callback message

            channel['state'] = _ChannelState.OPENED
