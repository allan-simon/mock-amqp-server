from enum import IntEnum
from struct import unpack
from .serialization import loads


class MethodIDs(IntEnum):
    START_OK = 0x000A000B
    TUNE_OK = 0x000A001F
    HEART_BEAT = 0x000A001F
    OPEN = 0x000A0028

    CHANNEL_OPEN = 0x0014000A
    CHANNEL_CLOSE = 0x00140028

    BASIC_QOS = 0x003C000A
    BASIC_PUBLISH = 0x003C0028

    EXCHANGE_DECLARE = 0x0028000A

    QUEUE_DECLARE = 0x0032000A

class Method():

    def __init__(
        self,
        channel_number,
        size,
        method_id,
        payload,
    ):
        self.is_header = False
        self.is_body = False
        self.channel_number = channel_number
        self.size = size
        self.method_id = method_id

        print(hex(method_id))
        decode_method = _ID_TO_METHOD[method_id]
        print(decode_method.__name__)
        self.properties = decode_method(payload)


class Header():

    PROPERTIES = [
        ('content_type', 's', 1 << 15),
        ('content_encoding', 's', 1 << 14),
        ('application_headers', 'F', 1 << 13),
        ('delivery_mode', 'B', 1 << 12),
        ('priority', 'B', 1 << 11),
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

    def __init__(
        self,
        channel_number,
        size,
        class_id,
        body_size,
        property_flags,
        payload,
    ):
        self.is_header = True
        self.is_body = False
        self.method_id = None
        self.channel_number = channel_number
        self.size = size
        self.class_id = class_id
        self.body_size = body_size

        # we assume there's no extra flags
        parse_string = ''
        keys = []
        for key, parse_type, mask in self.PROPERTIES:
            if property_flags & mask:
                parse_string += parse_type
                keys.append(key)

        values, _ = loads(
            parse_string,
            payload,
            offset=14,
        )
        self.properties = dict(zip(keys, values))


class Body():
    def __init__(
        self,
        channel_number,
        size,
        payload,
    ):
        self.is_header = False
        self.is_body = True
        self.method_id = None
        self.channel_number = channel_number
        self.size = size
        self.content = payload


def _decode_start_ok(payload):
    values, _ = loads(
        'FsSs',
        payload,
        offset=4,
    )
    properties = {
        'peer-properties': values[0],
        'mechanism': values[1],
        'response': values[2],
        'locale': values[3],
    }
    return properties


def _decode_tune_ok(payload):

    values, _ = loads(
        'BlB',
        payload,
        offset=4,
    )
    return {
        'channel-max': values[0],
        'frame-max': values[1],
        'heartbeat': values[2],
    }


def _decode_open(payload):
    values, _ = loads(
        'ssb',
        payload,
        offset=4,
    )
    return {
        'vhost': values[0],
        'capabilities': values[1],
        'insist': values[2],
    }


def _decode_channel_open(payload):
    values, _ = loads(
        's',
        payload,
        offset=4,
    )
    return {
        'reserved-1': values[0],
    }

def _decode_channel_close(payload):
    values, _ = loads(
        'BsBB',
        payload,
        offset=4,
    )
    return {
        'reply-code': values[0],
        'reply-text': values[1],
        'class-id': values[2],
        'method-id': values[3],
    }


def _decode_basic_qos(payload):

    return {

    }

def _decode_exchange_declare(payload):

    values, _ = loads(
        'BssbbbbbF',
        payload,
        offset=4,
    )
    return {
        'reserved-1': values[0],
        'exchange-name': values[1],
        'type': values[2],
        'passive': values[3],
        'durable': values[4],
        'auto-delete': values[5],
        'internal': values[6],
        'no-wait': values[6],
        'arguments': values[7],
    }

def _decode_basic_publish(payload):

    values, _ = loads(
        'Bssbb',
        payload,
        offset=4,
    )
    return {
        'reserved-1': values[0],
        'exchange-name': values[1],
        'routing-key': values[2],
        'mandatory': values[3],
        'immediate': values[4],
    }

def _decode_queue_declare(payload):

    print(payload)
    values, _ = loads(
        'BsbbbbbF',
        payload,
        offset=4,
    )
    return {
        'reserved-1': values[0],
        'queue-name': values[1],
        'passive': values[2],
        'durable': values[3],
        'exclusive': values[4],
        'auto-delete': values[5],
        'no-wait': values[6],
        'arguments': values[7],
    }


_ID_TO_METHOD = {
    0x000A000B: _decode_start_ok,
    0x000A001F: _decode_tune_ok,
    0x000A0028: _decode_open,

    0x0014000A: _decode_channel_open,
    0x00140028: _decode_channel_close,

    0x003C000A: _decode_basic_qos,
    0x003C0028: _decode_basic_publish,

    0x0028000A: _decode_exchange_declare,
    MethodIDs.QUEUE_DECLARE: _decode_queue_declare,
}
