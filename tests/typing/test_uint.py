import pytest
from pygears.typing import Bool, Int, Integer, Uint, Unit


def test_autowidth():
    assert type(Uint(7)) == Uint[3]
    assert type(Uint(8)) == Uint[4]

    assert type(Int(-7)) == Int[4]
    assert type(Int(7)) == Int[4]

    # TODO: check this?
    # assert type(Int(-8)) == Int[4]


def test_indexing():
    a = Uint[10]
    assert a[:1] == Uint[1]
    assert a[0] == Uint[1]
    assert a[0:2, 7, 8:] == Uint[5]
    assert a[0:0] == Unit
    assert a[:0] == Unit


def type_hierarchy():
    a = Uint[10]
    b = Int[10]

    assert issubclass(a, Uint)
    assert issubclass(a, Integer)
    assert not issubclass(a, Int)

    assert issubclass(b, Int)
    assert issubclass(b, Integer)
    assert not issubclass(b, Uint)


def test_concat():
    assert Uint[2](0x1) @ Uint[4](0xf) == Uint[6](0x1f)


def test_bool():
    assert Bool(2) == Uint[1](1)
    assert Bool(0) == Uint[1](0)
    assert type(Bool(0)) == Uint[1]


def test_wrong_param():
    with pytest.raises(TypeError, match="Uint type parameter must be an integer, not '1.2'"):
        Uint[1.2]

    with pytest.raises(TypeError, match="Uint type parameter must be a positive integer, not '-1'"):
        Uint[-1]


def test_abs():
    assert abs(Uint[2]) == Uint[2]
    assert abs(Int[2]) == Int[3]


def test_add_type():
    assert Uint[2] + Uint[5] == Uint[6]
    assert Uint[5] + Uint[5] == Uint[6]

    assert Int[2] + Int[5] == Int[6]
    assert Int[5] + Int[5] == Int[6]

    assert Uint[2] + Int[5] == Int[6]
    assert Uint[5] + Int[2] == Int[7]
    assert Uint[5] + Int[5] == Int[7]


def test_sub_type():
    assert Uint[2] - Uint[5] == Int[6]
    assert Uint[5] - Uint[2] == Int[6]

    assert Int[2] - Int[5] == Int[6]
    assert Int[5] - Int[2] == Int[6]

    assert Uint[2] - Int[5] == Int[6]
    assert Uint[5] - Int[2] == Int[7]
    assert Uint[5] - Int[5] == Int[7]

    assert Int[2] - Uint[5] == Int[7]
    assert Int[5] - Uint[2] == Int[6]
    assert Int[5] - Uint[5] == Int[7]


def test_sub_val():
    res = Uint[2].min - Uint[5].max
    assert isinstance(res, Int[6])
    assert res == -31

    res = Uint[5].max - Uint[2].min
    assert isinstance(res, Int[6])
    assert res == 31

    res = Int[2].min - Int[5].max
    assert isinstance(res, Int[6])
    assert res == -17

    res = Int[5].min - Int[2].max
    assert isinstance(res, Int[6])
    assert res == -17

    res = Uint[2].max - Int[5].min
    assert isinstance(res, Int[6])
    assert res == 19

    res = Uint[5].max - Int[2].min
    assert isinstance(res, Int[7])
    assert res == 33

    res = Uint[5].max - Int[5].min
    assert isinstance(res, Int[7])
    assert res == 47

    res = Int[2].min - Uint[5].max
    assert isinstance(res, Int[7])
    assert res == -33
    res = Int[5].min - Uint[2].max
    assert isinstance(res, Int[6])
    assert res == -19
    res = Int[5].min - Uint[5].max
    assert isinstance(res, Int[7])
    assert res == -47


def test_mul_val():
    res = Uint[2].max * Uint[5].max
    assert isinstance(res, Uint[7])
    assert res == 93

    res = Uint[5].max * Uint[2].max
    assert isinstance(res, Uint[7])
    assert res == 93

    res = Int[2].max * Int[5].max
    assert isinstance(res, Int[7])
    assert res == 15

    res = Int[5].max * Int[2].max
    assert isinstance(res, Int[7])
    assert res == 15

    res = Int[2].min * Int[5].min
    assert isinstance(res, Int[7])
    assert res == 32

    res = Int[5].min * Int[2].min
    assert isinstance(res, Int[7])
    assert res == 32

    res = Int[2].min * Int[5].max
    assert isinstance(res, Int[7])
    assert res == -30

    res = Int[5].max * Int[2].min
    assert isinstance(res, Int[7])
    assert res == -30

    res = Int[2].max * Int[5].min
    assert isinstance(res, Int[7])
    assert res == -16

    res = Int[5].min * Int[2].max
    assert isinstance(res, Int[7])
    assert res == -16


def test_mul_type():
    assert Uint[2] * Uint[5] == Uint[7]
    assert Uint[5] * Uint[2] == Uint[7]

    assert Int[2] * Int[5] == Int[7]
    assert Int[5] * Int[2] == Int[7]

    assert Int[2] * Uint[5] == Int[7]
    assert Uint[5] * Int[2] == Int[7]

    assert Uint[2] * Int[5] == Int[7]
    assert Int[5] * Uint[2] == Int[7]


def test_mul_int():
    res = Uint[2].max * 2
    assert isinstance(res, Uint[4])
    assert res == 6

    res = 2 * Uint[2].max
    assert isinstance(res, Uint[4])
    assert res == 6

    res = Int[2].max * 2
    assert isinstance(res, Int[4])
    assert res == 2

    res = 2 * Int[2].max
    assert isinstance(res, Int[4])
    assert res == 2

    res = Int[2].min * 2
    assert isinstance(res, Int[4])
    assert res == -4

    res = 2 * Int[2].min
    assert isinstance(res, Int[4])
    assert res == -4


# print(Uint[2].max * 2)
