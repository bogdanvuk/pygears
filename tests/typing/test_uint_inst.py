from pygears.typing import Int, Uint


def test_abs():
    res = abs(Uint[2].max)
    assert isinstance(res, Uint[2])
    assert res == 3

    res = abs(Int[2].min)
    assert isinstance(res, Int[3])
    assert res == 2

    res = abs(Int[2].max)
    assert isinstance(res, Int[3])
    assert res == 1


def test_add():
    res = Uint[2].max + Uint[5].max
    assert isinstance(res, Uint[6])
    assert res == 34
    res = Uint[5].max + Uint[5].max
    assert isinstance(res, Uint[6])
    assert res == 62

    res = Int[2].min + Int[5].min
    assert isinstance(res, Int[6])
    assert res == -18
    res = Int[5].min + Int[5].min
    assert isinstance(res, Int[6])
    assert res == -32

    res = Uint[2].max + Int[5].max
    assert isinstance(res, Int[6])
    assert res == 18
    res = Uint[5].max + Int[2].max
    assert isinstance(res, Int[7])
    assert res == 32
    res = Uint[5].max + Int[5].max
    assert isinstance(res, Int[7])
    assert res == 46
