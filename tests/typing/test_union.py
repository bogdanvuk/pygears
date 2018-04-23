from nose.tools import raises

from pygears.typing import TemplateArgumentsError, Uint, Union, Unit


def test_inheritance():
    assert Union[Uint[1], Uint[2]].base is Union


def test_equality():
    assert Union[1] == Union[1]
    assert Union[1] == 1
    assert Union[1, 2] != Union[1, 3]
    assert Union[1, 2] != Union[1, 2, 3]


def test_union_collapse():
    assert Union[Union[1]] == 1
    assert Union[1, Union[2, 3]] == Union[1, 2, 3]
    assert Union[Union[1, 2, 3], Union[4, 5, 6]] == Union[1, 2, 3, 4, 5, 6]
    assert Union[Union[1, 2, 3], Union[Union[4, 5], 6]] == Union[1, 2, 3, 4, 5,
                                                                 6]


def test_is_specified():
    assert Union[1, 2].is_specified() is True
    assert Union['T1', 2].is_specified() is False
    assert Union[1, Uint['T2']].is_specified() is False


def test_repr():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    assert repr(a) == "Union['T1', 2, 'T2', 3, 'T3', 'T4']"


def test_str():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    assert str(a) == "T1 | 2 | T2 | 3 | T3 | T4"


def test_partial_subs():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    b = a[1, 'T2', 3]
    assert b.is_specified() is False
    assert b == Union[1, 2, 'T2', 3, 3, 'T4']


def test_all_subs():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    b = a[1, 2, 3, 4]
    assert b.is_specified() is True
    assert b == Union[1, 2, 2, 3, 3, 4]


@raises(TemplateArgumentsError)
def test_excessive_subs():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    a[1, 2, 3, 4, 5]


def test_indexing():
    a = Union[Uint[1], Uint[2], Uint[3]]
    assert a[0] == Uint[3]
    assert a[1] == Uint[2]


def test_unit():
    a = Union[Unit]
    assert a == Unit
