import asyncio
from enum import IntEnum
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


    def connection_made(self, transport):
        """Handle new connection """
        self.transport = transport

    def data_received(self, data):
        self.http_parser.receive_data(data)
        print("http data")

        event = None
        while event is not h11.NEED_DATA:
            event = self.http_parser.next_event()
            if (
                self._state == _RequestState.WAITING_HEADERS and
                isinstance(event, h11.Request)
            ):
                method = event.method
                if method == b'GET':
                    self._on_get(event.target)
                    continue
                if method == b'DELETE':
                    self._on_delete(event.target)
                    continue


    def _on_get(self, target):

        if target.startswith(b'/authentification-done-with-success-on/'):
            username = target.split(b'/', maxsplit=2)[2]
            future = asyncio.ensure_future(
                self._global_state.wait_authentication_performed_on(
                    username,
                )
            )
            future.add_done_callback(self._on_get_done)
            return

        self._send_http_response_not_found()

    def _on_delete(self, target):
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
                ],
            )
        )
        body_data = self.http_parser.send(
            h11.Data(data=body)
        )
        self.transport.write(data)
        self.transport.write(body_data)
