import struct
from .method import Method
from .method import Header
from .method import Body
from .heartbeat import HeartBeat

_FRAME_HEADER_SIZE = 7
_FRAME_END_SIZE =  1

_FRAME_END = b'\xce'

_FRAME_METHOD = 1
_FRAME_HEADER = 2
_FRAME_BODY = 3
_FRAME_HEARTBEAT = 8


def read_frame(data_in):
    # Extracted from pika's library and slightly adapted
    try:
        (
            frame_type,
            channel_number,
            payload_size,
        ) = struct.unpack('>BHL', data_in[0:7])
    except struct.error:
        print("struct_error")
        return None
    # Get the frame data
    frame_size = _FRAME_HEADER_SIZE + payload_size + _FRAME_END_SIZE

    # We don't have all of the frame yet
    if frame_size > len(data_in):
        print("no enough data", frame_size, len(data_in))
        return None

    # The Frame termination chr is wrong
    if data_in[frame_size - 1:frame_size] != _FRAME_END:
        raise exceptions.InvalidFrameError("Invalid FRAME_END marker")

    # Get the raw frame data
    payload = data_in[_FRAME_HEADER_SIZE:frame_size - 1]

    if frame_type == _FRAME_METHOD:
        # Get the Method ID from the frame data
        method_id = struct.unpack_from('>I', payload)[0]
        print(method_id)
        return Method(
            channel_number,
            frame_size,
            method_id,
            payload,
        )
    if frame_type == _FRAME_HEARTBEAT:
        return HeartBeat(frame_size)

    if frame_type == _FRAME_HEADER:
        print(len(data_in[0:11]))
        (
            class_id,
            _weight,  # unused
            body_size,
            property_flags,
        ) = struct.unpack('>HHQH', data_in[0:14])
        print(hex(class_id))
        return Header(
            channel_number,
            frame_size,
            class_id,
            body_size,
            property_flags,
            payload
        )

    if frame_type == _FRAME_BODY:
        return Body(
            channel_number,
            frame_size,
            payload
        )

    print("frame type:", frame_type)

