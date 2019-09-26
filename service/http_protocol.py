import asyncio
from enum import IntEnum
import json
from wsgiref.handlers import format_date_time

import h11

from .state import WaitTimeout


class _RequestState(IntEnum):
    WAITING_HEADERS = 1
    WAITING_BODY = 2


class HTTPProtocol(asyncio.protocols.Protocol):
    """Handle connection and bytes parsing."""

    def __init__(
        self,
        global_state,
    ) -> None:
        self.transport = None  # type: asyncio.transports.Transport
        self._global_state = global_state

        self.http_parser = h11.Connection(h11.SERVER)
        self._state = _RequestState.WAITING_HEADERS
        self._method = None
        self._target = None
        self._headers = None

    def connection_made(self, transport):
        """Handle new connection """
        self.transport = transport

    def data_received(self, data):
        try:
            self._data_received(data)
        except Exception as e:
            self._send_http_internal_server_error()
            self.transport.close()
            raise e

    def _data_received(self, data):
        self.http_parser.receive_data(data)

        event = None
        while event is not h11.NEED_DATA:
            event = self.http_parser.next_event()
            if (
                self._state == _RequestState.WAITING_HEADERS and
                isinstance(event, h11.Request)
            ):
                self._method = event.method
                self._target = event.target
                self._headers = event.headers
                if self._method == b'MOCK_FLUSH':
                    self._global_state.reset()
                    self._send_http_response_no_content()
                    continue

                if self._method == b'GET':
                    self._on_get(event.target, self._headers)
                    continue
                if self._method == b'DELETE':
                    self._on_delete(event.target, self._headers)
                    continue
                if self._method in [b'POST', b'PUT']:
                    self._state = _RequestState.WAITING_BODY

            if (
                self._state == _RequestState.WAITING_BODY and
                isinstance(event, h11.Data)
            ):
                if self._method == b'POST':
                    self._on_post(self._target, event.data, self._headers)
                    continue
                if self._method == b'PUT':
                    self._on_put(self._target, event.data, self._headers)
                    continue

            if isinstance(event, h11.EndOfMessage):
                self._state = _RequestState.WAITING_HEADERS
                self._method = None
                self._target = None
                self._headers = None
                continue

    def _on_get(self, target, headers=None):


        print('GET ', target)


        ###
        # debug view, when you don't know what you are looking for
        ###
        if target == b'/':
            self._send_http_response_with_json_body(
                status_code=200,
                body=self._global_state.to_json().encode('utf-8')
            )
            return

        ###
        # Check if there was a successful authentication made by a client
        ###
        if target.startswith(b'/authentification-done-with-success-on/'):
            username = target.split(b'/', maxsplit=2)[2]
            future = asyncio.ensure_future(
                self._global_state.wait_authentication_performed_on(
                    username,
                )
            )
            future.add_done_callback(self._on_get_done)
            return

        ###
        # Wait for a message identified by a delivery_tag to be ack
        # by the consumer or timeout
        ###
        if target.startswith(b'/messages-acknowledged/'):
            delivery_tag = target.split(b'/', maxsplit=2)[2]
            future = asyncio.ensure_future(
                self._global_state.wait_message_acknowledged(
                    int(delivery_tag.decode('utf-8')),
                )
            )
            future.add_done_callback(self._on_get_done)
            return

        ###
        # Wait for a message identified by a delivery_tag to be nack
        # by the consumer or timeout
        ###
        if target.startswith(b'/messages-not-acknowledged/'):
            delivery_tag = target.split(b'/', maxsplit=2)[2]
            future = asyncio.ensure_future(
                self._global_state.wait_message_not_acknowledged(
                    int(delivery_tag.decode('utf-8')),
                )
            )
            future.add_done_callback(self._on_get_done)
            return

        ###
        # Wait for a message identified by a delivery_tag to be nack and requeued
        # by the consumer or timeout
        ###
        if target.startswith(b'/messages-requeued/'):
            delivery_tag = target.split(b'/', maxsplit=2)[2]
            future = asyncio.ensure_future(
                self._global_state.wait_message_requeued(
                    int(delivery_tag.decode('utf-8')),
                )
            )
            future.add_done_callback(self._on_get_done)
            return

        ###
        # Inspect the content of a queue where the program we test
        # publish messages.
        # Does not wait.
        ###
        if target.startswith(b'/messages-in-queue/'):
            queue_name = target.split(b'/', maxsplit=2)[2]
            messages = self._global_state.get_messages_of_queue(
                queue_name.decode('utf-8')
            )
            # queue not found
            if messages is None:
                self._send_http_response_not_found()
                return
            self._send_http_response_ok(
                body=json.dumps(messages).encode('utf-8')
            )
            return

        ###
        # Inspect the content of a exchange where the program we test
        # publish messages.
        # Does not wait.
        ###
        if target.startswith(b'/messages-in-exchange/'):
            exchange_name = target.split(b'/', maxsplit=2)[2]
            messages = self._global_state.get_messages_of_exchange(
                exchange_name.decode('utf-8')
            )
            # exchange not found
            if messages is None:
                self._send_http_response_not_found()
                return
            self._send_http_response_ok(
                body=json.dumps(messages).encode('utf-8')
            )
            return

        ###
        # Wait until a given queue is bound to a given exchange
        # or timeout
        ###
        if target.startswith(b'/queue-bound-to-exchange/'):
            _, _, queue, exchange = target.split(b'/', maxsplit=3)
            future = asyncio.ensure_future(
                self._global_state.wait_queue_bound(
                    queue.decode('utf-8'),
                    exchange.decode('utf-8'),
                )
            )
            future.add_done_callback(self._on_get_done)
            return

        self._send_http_response_not_found()

    def _build_message(self, data, headers):
        has_octet_stream = False
        kept_headers = {}
        for (type, value) in headers:
            if type == b'content-type' and value == b'application/octet-stream':
                has_octet_stream = True
            elif type.startswith(b'amqp_header_'):
                kept_headers[type.replace(b'amqp_header_', b'').decode('utf-8')] = value.decode('utf-8')
        if has_octet_stream:
            return {
                'body': data,
                'headers': kept_headers,
                'binary': True,
            }
        return json.loads(data.decode('utf-8'))

    def _on_post(self, target, data, headers=None):
        print('POST ', target)
        if target.startswith(b'/add-message-on/'):
            exchange = target.split(b'/', maxsplit=2)[2]
            full_message = self._build_message(data, headers)
            delivery_tag = self._global_state.publish_message(
                exchange.decode('utf-8'),
                full_message['headers'],
                full_message['body'],
                'binary' in full_message and full_message['binary'],
            )
            if delivery_tag is None:
                self._send_http_response_not_found()
                return
            self._send_http_response_ok(
                body=str(delivery_tag).encode('utf-8')
            )
            return

        if target.startswith(b'/add-message-in-queue/'):
            queue = target.split(b'/', maxsplit=2)[2]
            full_message = self._build_message(data, headers)
            delivery_tag = self._global_state.publish_message_in_queue(
                queue.decode('utf-8'),
                full_message['headers'],
                full_message['body'],
                'binary' in full_message and full_message['binary'],
            )
            if delivery_tag is None:
                self._send_http_response_not_found()
                return
            self._send_http_response_ok(
                body=str(delivery_tag).encode('utf-8')
            )
            return

        if target.startswith(b'/create-exchange/'):
            exchange_name = target.split(b'/', maxsplit=3)[2]
            exchange_type = target.split(b'/', maxsplit=3)[3]
            self._global_state.declare_exchange(
                exchange_name.decode('utf-8'),
                exchange_type.decode('utf-8'),
            )
            self._send_http_response_ok(
                body=b'ok',
            )
            return

        if target.startswith(b'/create-queue/'):
            queue_name = target.split(b'/', maxsplit=2)[2]
            self._global_state.declare_queue(
                queue_name.decode('utf-8'),
            )
            self._send_http_response_ok(
                body=b'ok',
            )
            return

        self._send_http_response_not_found()

    def _on_delete(self, target, headers=None):
        print('DELETE ', target)
        if target.startswith(b'/messages-in-queue/'):
            queue_name = target.split(b'/', maxsplit=2)[2]
            self._global_state.delete_messages_of_queue(
                queue_name.decode('utf-8')
            )
            self._send_http_response_no_content()
            return
        if target.startswith(b'/messages-in-exchange/'):
            queue_name = target.split(b'/', maxsplit=2)[2]
            self._global_state.delete_messages_of_exchange(
                queue_name.decode('utf-8')
            )
            self._send_http_response_no_content()
            return

        self._send_http_response_not_found()

    def _on_put(self, target, data, headers=None):
        print('PUT ', target)
        self._send_http_response_not_found()

    def _on_get_done(self, future):
        try:
            success = future.result()
            if not success:
                self._send_http_response_forbidden()
                return

            self._send_http_response_no_content()

        except WaitTimeout:
            self._send_http_response_timeout()

    def _send_http_response_no_content(self):
        data = self.http_parser.send(
            h11.Response(
                status_code=204,
                headers=[
                    ("Date", format_date_time(None).encode("ascii")),
                    ("Server", b"whatever"),
                    ('Content-Length', b'0'),
                    ('Connection', b'close'),
                ],
            )
        )
        self.transport.write(data)

    def _send_http_response_forbidden(self):
        self._send_http_response_with_body(
            status_code=403,
            body=b"forbidden\n",
        )

    def _send_http_response_timeout(self):
        self._send_http_response_with_body(
            status_code=504,
            body=b"timeout\n",
        )

    def _send_http_response_not_found(self):
        self._send_http_response_with_body(
            status_code=404,
            body=b"not found\n",
        )

    def _send_http_response_ok(self, body):
        self._send_http_response_with_body(
            status_code=200,
            body=body + b'\n',
        )

    def _send_http_response_with_json_body(
        self,
        status_code,
        body,
    ):
        data = self.http_parser.send(
            h11.Response(
                status_code=status_code,
                headers=[
                    ("Date", format_date_time(None).encode("ascii")),
                    ("Server", b"whatever"),
                    ('Content-Length', str(len(body))),
                    ('Content-Type', 'application/json'),
                    ('Connection', b'close'),
                ],
            )
        )
        body_data = self.http_parser.send(
            h11.Data(data=body)
        )
        self.transport.write(data)
        self.transport.write(body_data)



    def _send_http_response_with_body(
        self,
        status_code,
        body,
    ):
        data = self.http_parser.send(
            h11.Response(
                status_code=status_code,
                headers=[
                    ("Date", format_date_time(None).encode("ascii")),
                    ("Server", b"whatever"),
                    ('Content-Length', str(len(body))),
                    ('Connection', b'close'),
                ],
            )
        )
        body_data = self.http_parser.send(
            h11.Data(data=body)
        )
        self.transport.write(data)
        self.transport.write(body_data)

    def _send_http_internal_server_error(self):
        self._send_http_response_with_body(
            status_code=500,
            body=b'internal server error\n',
        )
