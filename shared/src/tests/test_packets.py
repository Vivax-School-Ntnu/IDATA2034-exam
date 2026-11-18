import io
from collections.abc import Buffer

import hypothesis
import pytest
from hypothesis import strategies as st
from pydantic import ValidationError

import shared


@hypothesis.given(st.builds(shared.BasePacket))
def test_round_trip(payload: shared.BasePacket):
    buffer = io.BytesIO()
    shared.write_frame(buffer, payload)

    buffer.seek(0)
    read_back = shared.read_frame(buffer)

    assert read_back == payload


@hypothesis.given(st.lists(st.builds(shared.BasePacket)))
def test_multiple_packets(packets: list[shared.BasePacket]):
    buffer = io.BytesIO()
    for packet in packets:
        shared.write_frame(buffer, packet)

    buffer.seek(0)
    for packet in packets:
        assert shared.read_frame(buffer) == packet


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


@hypothesis.given(st.builds(shared.BasePacket))
def test_split_packet(payload: shared.BasePacket):
    buffer = io.BytesIO()
    shared.write_frame(buffer, payload)

    buffer.seek(0)
    buffer = ChunkedReader(buffer, 5)
    read_back = shared.read_frame(buffer)

    assert read_back == payload


def test_eof():
    buffer = io.BytesIO()
    buffer.write(b"\x00\x00\x00\x00\x00\x00\x00\x08")
    buffer.write(b"\x00\x00\x00")

    buffer.seek(0)

    with pytest.raises(EOFError):
        shared.read_frame(buffer)


@pytest.mark.parametrize(
    "payload", [b"{not json", b"\xff\xfe", b"[1, 2, 3]", b'{"request_id": "r1"}']
)
def test_invalid_packet(payload: bytes) -> None:
    buffer = io.BytesIO(len(payload).to_bytes(8, "big") + payload)
    with pytest.raises(ValidationError):
        shared.read_frame(buffer)
