"""Launch the service to listen to Trackers.

It also route message from/to tackers and the other services.
"""
import traceback
import asyncio

from .protocol import TrackerProtocol
from .http_protocol import HTTPProtocol
from .state import State


def _exception_handler(loop, context):

    exception = context['exception']
    # see https://stackoverflow.com/questions/9555133
    traceback_list = traceback.format_exception(
        None,  # <- type(e) by docs, but ignored
        exception,
        exception.__traceback__,
    )
    for line in traceback_list:
        print(line, end='')


def _main():
    global_state = State()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_exception_handler)

    coroutine = loop.create_server(
        lambda: TrackerProtocol(
            global_state,
        ),
        '0.0.0.0',
        '5672',
    )
    http_coroutine = loop.create_server(
        lambda: HTTPProtocol(
            global_state,
        ),
        '0.0.0.0',
        '8080',
    )
    server = loop.run_until_complete(coroutine)
    http_server = loop.run_until_complete(http_coroutine)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    server.close()
    http_server.close()
    loop.run_until_complete(server.wait_closed())
    loop.run_until_complete(http_server.wait_closed())

    loop.close()


if __name__ == "__main__":
    _main()
