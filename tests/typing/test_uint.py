from pygears.typing import Int, Integer, Uint, Unit


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
