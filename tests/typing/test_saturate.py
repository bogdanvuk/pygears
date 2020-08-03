from pygears.typing import saturate, Uint


def test_uint_type():
    saturate(Uint[8], Uint[7]) == Uint[7]
