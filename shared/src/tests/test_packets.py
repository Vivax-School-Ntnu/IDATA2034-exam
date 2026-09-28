import io

import hypothesis
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
