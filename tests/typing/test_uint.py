from pygears import Uint


def test_indexing():
    a = Uint[10]
    assert a[:1] == Uint[1]
    assert a[0] == Uint[1]
    assert a[0:2, 7, 8:] == Uint[5]
