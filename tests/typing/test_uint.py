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
    with pytest.raises(
            TypeError,
            match="Uint type parameter must be an integer, not '1.2'"):
        Uint[1.2]

    with pytest.raises(
            TypeError,
            match="Uint type parameter must be a positive integer, not '-1'"):
        Uint[-1]


def test_add_type():
    assert Uint[2] + Uint[5] == Uint[6]
    assert Uint[5] + Uint[5] == Uint[6]

    assert Int[2] + Int[5] == Int[6]
    assert Int[5] + Int[5] == Int[6]

    assert Uint[2] + Int[5] == Int[6]
    assert Uint[5] + Int[2] == Int[7]
    assert Uint[5] + Int[5] == Int[7]


def test_add_val():
    assert Uint[2].max + Uint[5].max == Uint[6](34)
    assert Uint[5].max + Uint[5].max == Uint[6](62)

    assert Int[2].min + Int[5].min == Int[6](-18)
    assert Int[5].min + Int[5].min == Int[6](-32)

    assert Uint[2].max + Int[5].max == Int[6](18)
    assert Uint[5].max + Int[2].max == Int[7](32)
    assert Uint[5].max + Int[5].max == Int[7](46)


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
    assert Uint[2].min - Uint[5].max == Int[6](-31)
    assert Uint[5].max - Uint[2].min == Int[6](31)

    assert Int[2].min - Int[5].max == Int[6](-17)
    assert Int[5].min - Int[2].max == Int[6](-17)

    assert Uint[2].max - Int[5].min == Int[6](19)
    assert Uint[5].max - Int[2].min == Int[7](33)
    assert Uint[5].max - Int[5].min == Int[7](47)

    assert Int[2].min - Uint[5].max == Int[7](-33)
    assert Int[5].min - Uint[2].max == Int[6](-19)
    assert Int[5].min - Uint[5].max == Int[7](-47)
