from pygears.typing import Maybe, Uint


def test_instantiation():
    t = Maybe[Uint[2]]

    assert t(None)[0] == 0
    assert t(None)[1] == 0

    assert t(2)[0] == Uint[2](2)
    assert t(2)[1] == 1
