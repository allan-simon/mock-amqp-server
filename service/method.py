from enum import IntEnum
from .serialization import loads

class MethodIDs(IntEnum):
    START_OK = 0x000A000B
    TUNE_OK = 0x000A001F
    HEART_BEAT = 0x000A001F
    OPEN = 0x000A0028

    CHANNEL_OPEN = 0x0014000A

    BASIC_QOS = 0x003C000A
    BASIC_PUBLISH = 0x003C0028

    EXCHANGE_DECLARE = 0x0028000A


class Method():

    def __init__(
        self,
        channel_number,
        size,
        method_id,
        payload,
    ):
        self.channel_number = channel_number
        self.size = size
        self.method_id = method_id

        print(hex(method_id))
        decode_method = _ID_TO_METHOD[method_id]
        self.properties = decode_method(payload)


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


def _decode_basic_qos(payload):

    return {

    }

def _decode_exchange_declare(payload):

    values, _ = loads(
        'BsBbbbbbF',
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

_ID_TO_METHOD = {
    0x000A000B: _decode_start_ok,
    0x000A001F: _decode_tune_ok,
    0x000A0028: _decode_open,

    0x0014000A: _decode_channel_open,

    0x003C000A: _decode_basic_qos,
    0x003C0028: _decode_basic_publish,

    0x0028000A: _decode_exchange_declare,
}
