from nose.tools import raises

from pygears.typing import Array, Uint, Unit, TemplateArgumentsError


def test_inheritance():
    assert Array[Uint[1]].base is Array


def test_equality():
    assert Array[Uint[1], 2] != Array[Uint[1], 3]
    assert Array[Uint[1], 2] == Array[Uint[1], 2]
    assert Array[Uint[2], 2] != Array[Uint[1], 2]


def test_repr():
    a = Array['{T1}', 3]
    assert repr(a) == "Array['{T1}', 3]"


def test_str():
    a = Array['{T1}', 3]
    assert str(a) == "Array[{T1}, 3]"


def test_is_specified():
    assert Array[Uint[1], 2].is_specified() is True
    assert Array['{T1}', 3].is_specified() is False
    assert Array[Uint['{T2}'], 2].is_specified() is False


def test_subs():
    a = Array['{T1}', 2]
    b = a[Uint[1]]
    assert b == Array[Uint[1], 2]


def test_disolve():
    assert Array[Unit, 4] == Unit
    assert Array[Uint[2], 0] == Unit
    assert Array[Uint[4], 1] == Uint[4]


def test_multilevel_subs():
    a = Array[Uint['{T1}'], 2]
    b = a[1]
    assert b == Array[Uint[1], 2]


@raises(TemplateArgumentsError)
def test_excessive_subs():
    a = Array[Uint['{T1}']]
    a[1, 2]


def test_indexing():
    a = Array[Uint[1], 6]
    assert a[0] == Uint[1]
    assert a[5] == Uint[1]
    assert a[1:4] == Array[Uint[1], 3]
    assert a[:5] == Array[Uint[1], 5]
    assert a[:-1] == Array[Uint[1], 5]
    assert a[2:] == Array[Uint[1], 4]


@raises(IndexError)
def test_index_error():
    a = Array[Uint[1], 6]
    a[6]


def test_size():
    a = Array[Uint[6], 6]
    assert int(a) == 36
