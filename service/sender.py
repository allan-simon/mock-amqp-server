from struct import pack

from .serialization import dumps

_FRAME_END = b'\xce'

PROPERTIES = [
    ('content_type', 's', 1 << 15),
    ('content_encoding', 's', 1 << 14),
    ('application_headers', 'F', 1 << 13),
    ('delivery_mode', 'o', 1 << 12),
    ('priority', 'o', 1 << 11),
    ('correlation_id', 's', 1 << 10),
    ('reply_to', 's', 1 << 9),
    ('expiration', 's', 1 << 8),
    ('message_id', 's', 1 << 7),
    ('timestamp', 'L', 1 << 6),
    ('type', 's', 1 << 5),
    ('user_id', 's', 1 << 4),
    ('app_id', 's', 1 << 3),
    ('cluster_id', 's', 1 << 2)
]


def send_heartbeat(transport):

    transport.write(
        bytearray(
            [
                8,  # heartbeat
                # channel number, must be 0 for heartbeat
                0, 0,
            ]
        )
    )
    # size of the frame (0)
    transport.write(pack('>I', 0))
    transport.write(_FRAME_END)


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
    transport.write(pack('>I', 4 + len(arguments)))

    transport.write(
        bytearray([
            0, 10,  # class connection (10)
            0, 10,  # method start (10)
        ])
    )

    transport.write(arguments)
    transport.write(_FRAME_END)

def send_connection_close_ok(transport):

    transport.write(
        bytearray(
            [
                1,  # method
                0, 0,  # channel number 0
            ]
        )
    )

    # size of the frame
    # class+method (4 bytes)
    transport.write(pack('>I', 4))

    transport.write(
        bytearray([
            0, 10,  # class connection (10)
            0, 51,  # method close-ok (51)
        ])
    )
    transport.write(_FRAME_END)


def send_basic_cancel_ok(
    transport,
    channel_number,
    consumer_tag,
):

    arguments = dumps(
        format='s',
        values=[
            consumer_tag,
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
    transport.write(pack('>I', 4 + len(arguments)))

    transport.write(
        bytearray([
            0, 60,  # class basic (60)
            0, 31,  # method cancel-ok (31)
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
            10,  # heartbeat
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
    transport.write(pack('>I', 4 + len(arguments)))

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
            ''  # known host
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
    transport.write(pack('>I', 4 + len(arguments)))

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
    transport.write(pack('>I', 4 + len(arguments)))

    transport.write(
        bytearray([
            0, 20,  # class channel (20)
            0, 11,  # method open-ok (11)
        ])
    )

    transport.write(arguments)
    transport.write(_FRAME_END)


def send_channel_close_ok(
    transport,
    channel_number,
):

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
    # class+method (4 bytes)
    transport.write(pack('>I', 4))

    transport.write(
        bytearray([
            0, 20,  # class channel (20)
            0, 41,  # method close-ok (41)
        ])
    )

    transport.write(_FRAME_END)


def send_exchange_declare_ok(
    transport,
    channel_number,
):

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
    # class+method (4 bytes)
    transport.write(pack('>I', 4))

    transport.write(
        bytearray([
            0, 40,  # class exchange (40)
            0, 11,  # method declare-ok (11)
        ])
    )

    transport.write(_FRAME_END)


def send_queue_declare_ok(
    transport,
    channel_number,
    queue_name,
    message_count,
    consumer_count,
):

    arguments = dumps(
        format='sll',
        values=[
            queue_name,
            message_count,
            consumer_count,
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
    transport.write(pack('>I', 4 + len(arguments)))

    transport.write(
        bytearray([
            0, 50,  # class queue (50)
            0, 11,  # method declare-ok (11)
        ])
    )

    transport.write(arguments)

    transport.write(_FRAME_END)


def send_queue_bind_ok(
    transport,
    channel_number,
):

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
    # class+method (4 bytes)
    transport.write(pack('>I', 4))

    transport.write(
        bytearray([
            0, 50,  # class queue (50)
            0, 21,  # method bind-ok (21)
        ])
    )

    transport.write(_FRAME_END)


def send_basic_qos_ok(
    transport,
    channel_number,
):

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
    # class+method (4 bytes)
    transport.write(pack('>I', 4))

    transport.write(
        bytearray([
            0, 60,  # class basic (60)
            0, 11,  # method qos-ok (11)
        ])
    )

    transport.write(_FRAME_END)


def send_basic_consume_ok(
    transport,
    channel_number,
    consumer_tag,
):

    arguments = dumps(
        format='s',
        values=[
            consumer_tag,
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
    transport.write(pack('>I', 4 + len(arguments)))

    transport.write(
        bytearray([
            0, 60,  # class basic (60)
            0, 21,  # method consume-ok (21)
        ])
    )

    transport.write(arguments)

    transport.write(_FRAME_END)


def send_basic_deliver(
    transport,
    channel_number,
    consumer_tag,
    delivery_tag,
    redelivered,
    exchange_name,
    routing_key,
):

    arguments = dumps(
        format='sLbss',
        values=[
            consumer_tag,
            delivery_tag,
            redelivered,
            exchange_name,
            routing_key,
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
    transport.write(pack('>I', 4 + len(arguments)))

    transport.write(
        bytearray([
            0, 60,  # class basic (60)
            0, 60,  # method deliver (21)
        ])
    )

    transport.write(arguments)

    transport.write(_FRAME_END)


def send_content_header(
    transport,
    channel_number,
    properties,
    body_size,
):

    transport.write(
        bytearray(
            [
                2,  # header
                # channel number, same as the one received
                0, channel_number,
            ]
        )
    )

    property_flags = 0
    formats = ''
    property_values = []
    for name, format, bit in PROPERTIES:
        if name not in properties:
            continue
        property_flags += bit
        formats += format
        property_values.append(properties[name])

    arguments = dumps(
        format='BBLB' + formats,
        values=[
            60,  # class basic
            0,  # weight
            body_size,
            property_flags,
        ] + property_values,
    )
    print(arguments)

    # size of the frame
    transport.write(pack('>I', len(arguments)))
    transport.write(arguments)

    transport.write(_FRAME_END)


def send_content_body(
    transport,
    channel_number,
    body,
):

    transport.write(
        bytearray(
            [
                3,  # body
                # channel number, same as the one received
                0, channel_number,
            ]
        )
    )

    # size of the frame
    transport.write(pack('>I', len(body)))
    transport.write(body)

    transport.write(_FRAME_END)

