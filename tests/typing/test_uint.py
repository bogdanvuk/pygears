from pygears.typing import Uint, Integer, typeof, Int


def test_indexing():
    a = Uint[10]
    assert a[:1] == Uint[1]
    assert a[0] == Uint[1]
    assert a[0:2, 7, 8:] == Uint[5]


def type_hierarchy():
    a = Uint[10]
    b = Int[10]

    assert issubclass(a, Uint)
    assert issubclass(a, Integer)
    assert not issubclass(a, Int)

    assert issubclass(b, Int)
    assert issubclass(b, Integer)
    assert not issubclass(b, Uint)
