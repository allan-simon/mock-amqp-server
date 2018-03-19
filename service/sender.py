from struct import pack

from .serialization import dumps

_FRAME_END = b'\xce'

def send_connection_start(transport):

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

    transport.write(
        bytearray(
            [
                1,  # method
                0, 0,  # channel number 0
            ]
        )
    )
    # size of the frame
    # class+method (4 bytes) + bytes len of arguments
    transport.write(pack('>I', 4 + len(arguments) ))

    transport.write(
        bytearray([
            0, 10,  # class connection (10)
            0, 10,  # method start (10)
        ])
    )

    transport.write(arguments)
    transport.write(_FRAME_END)

def send_connection_tune(transport):

    arguments = dumps(
        format='BlB',
        values=[
            0,  # channel max
            131072,  # frame max size
            60,  # heartbeat
        ]
    )

    transport.write(
        bytearray(
            [
                1,  # method
                0, 0,  # channel number 0
            ]
        )
    )
    # size of the frame
    # class+method (4 bytes) + bytes len of arguments
    transport.write(pack('>I', 4 + len(arguments) ))

    transport.write(
        bytearray([
            0, 10,  # class connection (10)
            0, 30,  # method tune (30)
        ])
    )

    transport.write(arguments)
    transport.write(_FRAME_END)

def send_connection_ok(transport):

    arguments = dumps(
        format='s',
        values=[
            '' # known host
        ]
    )

    transport.write(
        bytearray(
            [
                1,  # method
                0, 0,  # channel number 0
            ]
        )
    )
    # size of the frame
    # class+method (4 bytes) + bytes len of arguments
    transport.write(pack('>I', 4 + len(arguments) ))

    transport.write(
        bytearray([
            0, 10,  # class connection (10)
            0, 41,  # method open-ok (41)
        ])
    )

    transport.write(arguments)
    transport.write(_FRAME_END)


def send_channel_open_ok(
    transport,
    channel_number,
    channel_id,
):

    arguments = dumps(
        format='S',
        values=[
            channel_id  # channel id
        ]
    )

    transport.write(
        bytearray(
            [
                1,  # method
                # channel number, same as the one received
                0, channel_number,
            ]
        )
    )
    # size of the frame
    # class+method (4 bytes) + bytes len of arguments
    transport.write(pack('>I', 4 + len(arguments) ))

    transport.write(
        bytearray([
            0, 20,  # class channel (20)
            0, 11,  # method open-ok (11)
        ])
    )

    transport.write(arguments)
    transport.write(_FRAME_END)
