"""Launch the service to listen to Trackers.

It also route message from/to tackers and the other services.
"""
import traceback
import asyncio

from .protocol import TrackerProtocol


def _exception_handler(loop, context):

    exception = context['exception']
    # see https://stackoverflow.com/questions/9555133
    traceback_list = traceback.format_exception(
        None,  # <- type(e) by docs, but ignored
        exception,
        exception.__traceback__,
    )
    print(traceback_list)


def _main():

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_exception_handler)

    coroutine = loop.create_server(
        lambda: TrackerProtocol(
        ),
        '0.0.0.0',
        '5672',
    )
    server = loop.run_until_complete(coroutine)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    server.close()
    loop.run_until_complete(server.wait_closed())

    loop.close()


if __name__ == "__main__":
    _main()
