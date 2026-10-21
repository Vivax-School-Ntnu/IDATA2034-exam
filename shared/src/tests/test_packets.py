import io
from collections.abc import Buffer

import hypothesis
import pytest
from hypothesis import strategies as st

import shared

json_scalars = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text()
)

json_values = st.recursive(
    json_scalars,
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=50,
)


@hypothesis.example({"type": "sensor", "value": 10})
@hypothesis.given(json_values)
def test_round_trip(payload: object):
    buffer = io.BytesIO()
    shared.write_frame(buffer, payload)

    buffer.seek(0)
    read_back = shared.read_frame(buffer)

    assert read_back == payload


@hypothesis.example(["hello", {"test": 123}, "cool"])
@hypothesis.given(st.lists(json_values))
def test_multiple_packets(packets: list[object]):
    buffer = io.BytesIO()
    for packet in packets:
        shared.write_frame(buffer, packet)

    buffer.seek(0)
    for packet in packets:
        assert shared.read_frame(buffer) == packet


def test_eof():
    buffer = io.BytesIO()
    buffer.write(b"\x00\x00\x00\x00\x00\x00\x00\x08")
    buffer.write(b"\x00\x00\x00")

    buffer.seek(0)

    with pytest.raises(EOFError):
        shared.read_frame(buffer)


class ChunkedReader(io.RawIOBase):
    def __init__(self, data: io.BytesIO, chunk_size: int):
        self.data = data
        self.chunk_size = chunk_size

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Buffer, /) -> int:
        view = memoryview(buffer).cast("B")
        read_length = min(len(view), self.chunk_size)
        chunk = self.data.read(read_length)
        view[: len(chunk)] = chunk
        return len(chunk)


@hypothesis.example({"type": "sensor", "value": 10})
@hypothesis.given(json_values)
def test_split_packet(payload: object):
    buffer = io.BytesIO()
    shared.write_frame(buffer, payload)

    buffer.seek(0)
    buffer = ChunkedReader(buffer, 5)
    read_back = shared.read_frame(buffer)

    assert read_back == payload
