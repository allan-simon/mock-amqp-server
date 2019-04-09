"""Convert between bytestreams and higher-level AMQP types.

Adapted from https://github.com/celery/py-amqp/blob/master/amqp/serialization.py

Copyright (c) 2015-2016 Ask Solem & contributors.  All rights reserved.
Copyright (c) 2012-2014 GoPivotal, Inc.  All rights reserved.
Copyright (c) 2009, 2010, 2011, 2012 Ask Solem, and individual contributors.  All rights reserved.
Copyright (C) 2007-2008 Barry Pederson <bp@barryp.org>. All rights reserved.

py-amqp is licensed under The BSD License (3 Clause, also known as
the new BSD license).  The license is an OSI approved Open Source
license and is GPL-compatible(1).

The license text can also be found here:
http://www.opensource.org/licenses/BSD-3-Clause

License
=======

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Ask Solem, nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL Ask Solem OR CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.


Footnotes
=========
(1) A GPL-compatible license makes it possible to
    combine Celery with other software that is released
    under the GPL, it does not mean that we're distributing
    Celery under the GPL license.  The BSD license, unlike the GPL,
    let you distribute a modified version without making your
    changes open source.

"""
# Copyright (C) 2007 Barry Pederson <bp@barryp.org>

import calendar
import sys
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from struct import pack, unpack_from


class FrameSyntaxError(Exception):
    def __init__(self, reply_text):
        Exception.__init__(
            self,
            502,
            reply_text,
        )


def _str_to_bytes(s):
    """Convert str to bytes."""
    if isinstance(s, str):
        return s.encode('utf-8', 'surrogatepass')
    return s


def _bytes_to_str(s):
    """Convert bytes to str."""
    if isinstance(s, bytes):
        return s.decode('utf-8', 'surrogatepass')
    return s


ftype_t = chr if sys.version_info[0] == 3 else None

ILLEGAL_TABLE_TYPE = """\
    Table type {0!r} not handled by amqp.
"""

ILLEGAL_TABLE_TYPE_WITH_KEY = """\
Table type {0!r} for key {1!r} not handled by amqp. [value: {2!r}]
"""

ILLEGAL_TABLE_TYPE_WITH_VALUE = """\
    Table type {0!r} not handled by amqp. [value: {1!r}]
"""


def _read_item(
    buf,
    offset=0,
    unpack_from=unpack_from,
    ftype_t=ftype_t
):
    ftype = ftype_t(buf[offset]) if ftype_t else buf[offset]
    offset += 1

    # 'S': long string
    if ftype == 'S':
        slen, = unpack_from('>I', buf, offset)
        offset += 4
        val = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    # rabbitmq implement 's' not as short string
    # see https://github.com/rabbitmq/rabbitmq-common/issues/261
    # 's': short string
    # elif ftype == 's':
    #     slen, = unpack_from('>B', buf, offset)
    #     offset += 1

    #     val = _bytes_to_str(buf[offset:offset + slen])
    #     offset += slen
    # 'b': short-short int
    elif ftype == 'b':
        val, = unpack_from('>B', buf, offset)
        offset += 1
    # 'B': short-short unsigned int
    elif ftype == 'B':
        val, = unpack_from('>b', buf, offset)
        offset += 1
    # RabbitMQ implement 's' as short int
    # 'U': short int
    elif ftype in ['U', 's']:
        val, = unpack_from('>h', buf, offset)
        offset += 2
    # 'u': short unsigned int
    elif ftype == 'u':
        val, = unpack_from('>H', buf, offset)
        offset += 2
    # 'I': long int
    elif ftype == 'I':
        val, = unpack_from('>i', buf, offset)
        offset += 4
    # 'i': long unsigned int
    elif ftype == 'i':
        val, = unpack_from('>I', buf, offset)
        offset += 4
    # 'L': long long int
    elif ftype == 'L':
        val, = unpack_from('>q', buf, offset)
        offset += 8
    # 'l': long long unsigned int
    elif ftype == 'l':
        val, = unpack_from('>Q', buf, offset)
        offset += 8
    # 'f': float
    elif ftype == 'f':
        val, = unpack_from('>f', buf, offset)
        offset += 4
    # 'd': double
    elif ftype == 'd':
        val, = unpack_from('>d', buf, offset)
        offset += 8
    # 'D': decimal
    elif ftype == 'D':
        d, = unpack_from('>B', buf, offset)
        offset += 1
        n, = unpack_from('>i', buf, offset)
        offset += 4
        val = Decimal(n) / Decimal(10 ** d)
    # 'F': table
    elif ftype == 'F':
        tlen, = unpack_from('>I', buf, offset)
        offset += 4
        limit = offset + tlen
        val = {}
        while offset < limit:
            keylen, = unpack_from('>B', buf, offset)
            offset += 1
            key = _bytes_to_str(buf[offset:offset + keylen])
            offset += keylen
            val[key], offset = _read_item(buf, offset)
    # 'A': array
    elif ftype == 'A':
        alen, = unpack_from('>I', buf, offset)
        offset += 4
        limit = offset + alen
        val = []
        while offset < limit:
            v, offset = _read_item(buf, offset)
            val.append(v)
    # 't' (bool)
    elif ftype == 't':
        val, = unpack_from('>B', buf, offset)
        val = bool(val)
        offset += 1
    # 'T': timestamp
    elif ftype == 'T':
        val, = unpack_from('>Q', buf, offset)
        offset += 8
        val = datetime.utcfromtimestamp(val)
    # 'V': void
    elif ftype == 'V':
        val = None
    else:
        raise FrameSyntaxError(
            'Unknown value in table: {0!r} ({1!r})'.format(
                ftype,
                type(ftype)
            )
        )
    return val, offset


def loads(
    format,
    buf,
    offset=0,
):
    """Deserialize amqp format.

    bit = b
    octet = o
    short = B
    long = l
    long long = L
    float = f
    shortstr = s
    longstr = S
    table = F
    array = A
    timestamp = T
    """
    bitcount = bits = 0

    values = []
    append = values.append
    format = _bytes_to_str(format)

    for p in format:
        if p == 'b':
            if not bitcount:
                bits = ord(buf[offset:offset + 1])
                offset += 1
            bitcount = 8
            val = (bits & 1) == 1
            bits >>= 1
            bitcount -= 1
        elif p == 'o':
            bitcount = bits = 0
            val, = unpack_from('>B', buf, offset)
            offset += 1
        elif p == 'B':
            bitcount = bits = 0
            val, = unpack_from('>H', buf, offset)
            offset += 2
        elif p == 'l':
            bitcount = bits = 0
            val, = unpack_from('>I', buf, offset)
            offset += 4
        elif p == 'L':
            bitcount = bits = 0
            val, = unpack_from('>Q', buf, offset)
            offset += 8
        elif p == 'f':
            bitcount = bits = 0
            val, = unpack_from('>f', buf, offset)
            offset += 4
        elif p == 's':
            bitcount = bits = 0
            slen, = unpack_from('B', buf, offset)
            offset += 1
            val = buf[offset:offset + slen].decode('utf-8', 'surrogatepass')
            offset += slen
        elif p == 'S':
            bitcount = bits = 0
            slen, = unpack_from('>I', buf, offset)
            offset += 4
            val = buf[offset:offset + slen].decode('utf-8', 'surrogatepass')
            offset += slen
        elif p == 'F':
            bitcount = bits = 0
            tlen, = unpack_from('>I', buf, offset)
            offset += 4
            limit = offset + tlen
            val = {}
            while offset < limit:
                keylen, = unpack_from('>B', buf, offset)
                offset += 1
                key = _bytes_to_str(buf[offset:offset + keylen])
                offset += keylen
                val[key], offset = _read_item(buf, offset)
        elif p == 'A':
            bitcount = bits = 0
            alen, = unpack_from('>I', buf, offset)
            offset += 4
            limit = offset + alen
            val = []
            while offset < limit:
                aval, offset = _read_item(buf, offset)
                val.append(aval)
        elif p == 'T':
            bitcount = bits = 0
            val, = unpack_from('>Q', buf, offset)
            offset += 8
            val = datetime.utcfromtimestamp(val)
        else:
            raise FrameSyntaxError(ILLEGAL_TABLE_TYPE.format(p))
        append(val)
    return values, offset


def _flushbits(bits, write, pack=pack):
    if bits:
        write(pack('B' * len(bits), *bits))
        bits[:] = []
    return 0


def dumps(format, values):
    """Serialize AMQP arguments.

    Notes:
        bit = b
        octet = o
        short = B
        long = l
        long long = L
        shortstr = s
        longstr = S
        table = F
        array = A
    """
    bitcount = 0
    bits = []
    out = BytesIO()
    write = out.write

    format = _bytes_to_str(format)

    for i, val in enumerate(values):
        p = format[i]
        if p == 'b':
            val = 1 if val else 0
            shift = bitcount % 8
            if shift == 0:
                bits.append(0)
            bits[-1] |= (val << shift)
            bitcount += 1
        elif p == 'o':
            bitcount = _flushbits(bits, write)
            write(pack('B', val))
        elif p == 'B':
            bitcount = _flushbits(bits, write)
            write(pack('>H', int(val)))
        elif p == 'l':
            bitcount = _flushbits(bits, write)
            write(pack('>I', val))
        elif p == 'L':
            bitcount = _flushbits(bits, write)
            write(pack('>Q', val))
        elif p == 'f':
            bitcount = _flushbits(bits, write)
            write(pack('>f', val))
        elif p == 's':
            val = val or ''
            bitcount = _flushbits(bits, write)
            if isinstance(val, str):
                val = val.encode('utf-8', 'surrogatepass')
            write(pack('B', len(val)))
            write(val)
        elif p == 'S':
            val = val or ''
            bitcount = _flushbits(bits, write)
            if isinstance(val, str):
                val = val.encode('utf-8', 'surrogatepass')
            write(pack('>I', len(val)))
            write(val)
        elif p == 'F':
            bitcount = _flushbits(bits, write)
            _write_table(val or {}, write, bits)
        elif p == 'A':
            bitcount = _flushbits(bits, write)
            _write_array(val or [], write, bits)
        elif p == 'T':
            write(pack('>Q', int(calendar.timegm(val.utctimetuple()))))
    _flushbits(bits, write)

    return out.getvalue()


def _write_table(d, write, bits, pack=pack):
    out = BytesIO()
    twrite = out.write
    for k, v in d.items():
        if isinstance(k, str):
            k = k.encode('utf-8', 'surrogatepass')
        twrite(pack('B', len(k)))
        twrite(k)
        try:
            _write_item(v, twrite, bits)
        except ValueError:
            raise FrameSyntaxError(
                ILLEGAL_TABLE_TYPE_WITH_KEY.format(
                    type(v),
                    k,
                    v
                )
            )
    table_data = out.getvalue()
    write(pack('>I', len(table_data)))
    write(table_data)


def _write_array(l, write, bits, pack=pack):
    out = BytesIO()
    awrite = out.write
    for v in l:
        try:
            _write_item(v, awrite, bits)
        except ValueError:
            raise FrameSyntaxError(
                ILLEGAL_TABLE_TYPE_WITH_VALUE.format(
                    type(v),
                    v,
                )
            )
    array_data = out.getvalue()
    write(pack('>I', len(array_data)))
    write(array_data)


def _write_item(
    v,
    write,
    bits,
):
    if isinstance(v, (str, bytes)):
        if isinstance(v, str):
            v = v.encode('utf-8', 'surrogatepass')
        write(pack('>cI', b'S', len(v)))
        write(v)
    elif isinstance(v, bool):
        write(pack('>cB', b't', int(v)))
    elif isinstance(v, float):
        write(pack('>cd', b'd', v))
    elif isinstance(v, int):
        if v > 2147483647 or v < -2147483647:
            write(pack('>cq', b'L', v))
        else:
            write(pack('>ci', b'I', v))
    elif isinstance(v, Decimal):
        sign, digits, exponent = v.as_tuple()
        v = 0
        for d in digits:
            v = (v * 10) + d
        if sign:
            v = -v
        write(pack('>cBi', b'D', -exponent, v))
    elif isinstance(v, datetime):
        write(
            pack('>cQ', b'T', int(calendar.timegm(v.utctimetuple()))))
    elif isinstance(v, dict):
        write(b'F')
        _write_table(v, write, bits)
    elif isinstance(v, (list, tuple)):
        write(b'A')
        _write_array(v, write, bits)
    elif v is None:
        write(b'V')
    else:
        raise ValueError()


def decode_properties_basic(
    buf,
    offset=0,
):
    """Decode basic properties."""
    properties = {}

    flags, = unpack_from('>H', buf, offset)
    offset += 2

    if flags & 0x8000:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['content_type'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    if flags & 0x4000:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['content_encoding'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    if flags & 0x2000:
        _f, offset = loads('F', buf, offset)
        properties['application_headers'], = _f
    if flags & 0x1000:
        properties['delivery_mode'], = unpack_from('>B', buf, offset)
        offset += 1
    if flags & 0x0800:
        properties['priority'], = unpack_from('>B', buf, offset)
        offset += 1
    if flags & 0x0400:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['correlation_id'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    if flags & 0x0200:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['reply_to'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    if flags & 0x0100:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['expiration'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    if flags & 0x0080:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['message_id'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    if flags & 0x0040:
        properties['timestamp'], = unpack_from('>Q', buf, offset)
        offset += 8
    if flags & 0x0020:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['type'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    if flags & 0x0010:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['user_id'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    if flags & 0x0008:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['app_id'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    if flags & 0x0004:
        slen, = unpack_from('>B', buf, offset)
        offset += 1
        properties['cluster_id'] = _bytes_to_str(buf[offset:offset + slen])
        offset += slen
    return properties, offset


PROPERTY_CLASSES = {
    60: decode_properties_basic,
}


class GenericContent(object):
    """Abstract base class for AMQP content.

    Subclasses should override the PROPERTIES attribute.
    """

    CLASS_ID = None
    PROPERTIES = [('dummy', 's')]

    def __init__(self, frame_method=None, frame_args=None, **props):
        self.frame_method = frame_method
        self.frame_args = frame_args

        self.properties = props
        self._pending_chunks = []
        self.body_received = 0
        self.body_size = 0
        self.ready = False

    def __getattr__(self, name):
        # Look for additional properties in the 'properties'
        # dictionary, and if present - the 'delivery_info' dictionary.
        if name == '__setstate__':
            # Allows pickling/unpickling to work
            raise AttributeError('__setstate__')

        if name in self.properties:
            return self.properties[name]
        raise AttributeError(name)

    def _load_properties(self, class_id, buf, offset=0, classes=PROPERTY_CLASSES, unpack_from=unpack_from):
        """Load AMQP properties.

        Given the raw bytes containing the property-flags and property-list
        from a content-frame-header, parse and insert into a dictionary
        stored in this object as an attribute named 'properties'.
        """
        # Read 16-bit shorts until we get one with a low bit set to zero
        props, offset = classes[class_id](buf, offset)
        self.properties = props
        return offset

    def _serialize_properties(self):
        """Serialize AMQP properties.

        Serialize the 'properties' attribute (a dictionary) into
        the raw bytes making up a set of property flags and a
        property list, suitable for putting into a content frame header.
        """
        shift = 15
        flag_bits = 0
        flags = []
        sformat, svalues = [], []
        props = self.properties
        props.setdefault('content_encoding', 'utf-8')
        for key, proptype in self.PROPERTIES:
            val = props.get(key, None)
            if val is not None:
                if shift == 0:
                    flags.append(flag_bits)
                    flag_bits = 0
                    shift = 15

                flag_bits |= (1 << shift)
                if proptype != 'bit':
                    sformat.append(_str_to_bytes(proptype))
                    svalues.append(val)

            shift -= 1
        flags.append(flag_bits)
        result = BytesIO()
        write = result.write
        for flag_bits in flags:
            write(pack('>H', flag_bits))
        write(dumps(b''.join(sformat), svalues))

        return result.getvalue()

    def inbound_header(self, buf, offset=0):
        class_id, self.body_size = unpack_from('>HxxQ', buf, offset)
        offset += 12
        self._load_properties(class_id, buf, offset)
        if not self.body_size:
            self.ready = True
        return offset

    def inbound_body(self, buf):
        chunks = self._pending_chunks
        self.body_received += len(buf)
        if self.body_received >= self.body_size:
            if chunks:
                chunks.append(buf)
                self.body = bytes().join(chunks)
                chunks[:] = []
            else:
                self.body = buf
            self.ready = True
        else:
            chunks.append(buf)


if __name__ == '__main__':
    data = [
        0x00, 0x00, 0x01,
        0xc7, 0x0c, 0x63, 0x61, 0x70, 0x61, 0x62, 0x69,
        0x6c, 0x69, 0x74, 0x69, 0x65, 0x73, 0x46, 0x00,
        0x00, 0x00, 0xc7, 0x12, 0x70, 0x75, 0x62, 0x6c,
        0x69, 0x73, 0x68, 0x65, 0x72, 0x5f, 0x63, 0x6f,
        0x6e, 0x66, 0x69, 0x72, 0x6d, 0x73, 0x74, 0x01,
        0x1a, 0x65, 0x78, 0x63, 0x68, 0x61, 0x6e, 0x67,
        0x65, 0x5f, 0x65, 0x78, 0x63, 0x68, 0x61, 0x6e,
        0x67, 0x65, 0x5f, 0x62, 0x69, 0x6e, 0x64, 0x69,
        0x6e, 0x67, 0x73, 0x74, 0x01, 0x0a, 0x62, 0x61,
        0x73, 0x69, 0x63, 0x2e, 0x6e, 0x61, 0x63, 0x6b,
        0x74, 0x01, 0x16, 0x63, 0x6f, 0x6e, 0x73, 0x75,
        0x6d, 0x65, 0x72, 0x5f, 0x63, 0x61, 0x6e, 0x63,
        0x65, 0x6c, 0x5f, 0x6e, 0x6f, 0x74, 0x69, 0x66,
        0x79, 0x74, 0x01, 0x12, 0x63, 0x6f, 0x6e, 0x6e,
        0x65, 0x63, 0x74, 0x69, 0x6f, 0x6e, 0x2e, 0x62,
        0x6c, 0x6f, 0x63, 0x6b, 0x65, 0x64, 0x74, 0x01,
        0x13, 0x63, 0x6f, 0x6e, 0x73, 0x75, 0x6d, 0x65,
        0x72, 0x5f, 0x70, 0x72, 0x69, 0x6f, 0x72, 0x69,
        0x74, 0x69, 0x65, 0x73, 0x74, 0x01, 0x1c, 0x61,
        0x75, 0x74, 0x68, 0x65, 0x6e, 0x74, 0x69, 0x63,
        0x61, 0x74, 0x69, 0x6f, 0x6e, 0x5f, 0x66, 0x61,
        0x69, 0x6c, 0x75, 0x72, 0x65, 0x5f, 0x63, 0x6c,
        0x6f, 0x73, 0x65, 0x74, 0x01, 0x10, 0x70, 0x65,
        0x72, 0x5f, 0x63, 0x6f, 0x6e, 0x73, 0x75, 0x6d,
        0x65, 0x72, 0x5f, 0x71, 0x6f, 0x73, 0x74, 0x01,
        0x0f, 0x64, 0x69, 0x72, 0x65, 0x63, 0x74, 0x5f,
        0x72, 0x65, 0x70, 0x6c, 0x79, 0x5f, 0x74, 0x6f,
        0x74, 0x01, 0x0c, 0x63, 0x6c, 0x75, 0x73, 0x74,
        0x65, 0x72, 0x5f, 0x6e, 0x61, 0x6d, 0x65, 0x53,
        0x00, 0x00, 0x00, 0x13, 0x72, 0x61, 0x62, 0x62,
        0x69, 0x74, 0x40, 0x36, 0x30, 0x62, 0x35, 0x38,
        0x34, 0x63, 0x62, 0x34, 0x63, 0x31, 0x62, 0x09,
        0x63, 0x6f, 0x70, 0x79, 0x72, 0x69, 0x67, 0x68,
        0x74, 0x53, 0x00, 0x00, 0x00, 0x2e, 0x43, 0x6f,
        0x70, 0x79, 0x72, 0x69, 0x67, 0x68, 0x74, 0x20,
        0x28, 0x43, 0x29, 0x20, 0x32, 0x30, 0x30, 0x37,
        0x2d, 0x32, 0x30, 0x31, 0x38, 0x20, 0x50, 0x69,
        0x76, 0x6f, 0x74, 0x61, 0x6c, 0x20, 0x53, 0x6f,
        0x66, 0x74, 0x77, 0x61, 0x72, 0x65, 0x2c, 0x20,
        0x49, 0x6e, 0x63, 0x2e, 0x0b, 0x69, 0x6e, 0x66,
        0x6f, 0x72, 0x6d, 0x61, 0x74, 0x69, 0x6f, 0x6e,
        0x53, 0x00, 0x00, 0x00, 0x35, 0x4c, 0x69, 0x63,
        0x65, 0x6e, 0x73, 0x65, 0x64, 0x20, 0x75, 0x6e,
        0x64, 0x65, 0x72, 0x20, 0x74, 0x68, 0x65, 0x20,
        0x4d, 0x50, 0x4c, 0x2e, 0x20, 0x20, 0x53, 0x65,
        0x65, 0x20, 0x68, 0x74, 0x74, 0x70, 0x3a, 0x2f,
        0x2f, 0x77, 0x77, 0x77, 0x2e, 0x72, 0x61, 0x62,
        0x62, 0x69, 0x74, 0x6d, 0x71, 0x2e, 0x63, 0x6f,
        0x6d, 0x2f, 0x08, 0x70, 0x6c, 0x61, 0x74, 0x66,
        0x6f, 0x72, 0x6d, 0x53, 0x00, 0x00, 0x00, 0x11,
        0x45, 0x72, 0x6c, 0x61, 0x6e, 0x67, 0x2f, 0x4f,
        0x54, 0x50, 0x20, 0x32, 0x30, 0x2e, 0x32, 0x2e,
        0x34, 0x07, 0x70, 0x72, 0x6f, 0x64, 0x75, 0x63,
        0x74, 0x53, 0x00, 0x00, 0x00, 0x08, 0x52, 0x61,
        0x62, 0x62, 0x69, 0x74, 0x4d, 0x51, 0x07, 0x76,
        0x65, 0x72, 0x73, 0x69, 0x6f, 0x6e, 0x53, 0x00,
        0x00, 0x00, 0x05, 0x33, 0x2e, 0x37, 0x2e, 0x34,
        0x00, 0x00, 0x00, 0x0e, 0x50, 0x4c, 0x41, 0x49,
        0x4e, 0x20, 0x41, 0x4d, 0x51, 0x50, 0x4c, 0x41,
        0x49, 0x4e, 0x00, 0x00, 0x00, 0x05, 0x65, 0x6e,
        0x5f, 0x55, 0x53, 0xce
    ]

    print(
        loads(
            'FSS',
            bytes(bytearray(data)),
            0,
        )
    )

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
        'information': 'Licensed under the MPL. See http://www.rabbitmq.com/',
        'cluster_name': 'rabbit@60b584cb4c1b',
        'product': 'RabbitMQ', 'version': '3.7.4',
        'copyright': 'Copyright (C) 2007-2018 Pivotal Software, Inc.',
        'platform': 'Erlang/OTP 20.2.4'
    }
    print(
        dumps(
            'ooF',
            [
                0,
                9,
                peer_properties,
            ]
        )
    )
