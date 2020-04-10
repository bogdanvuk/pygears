import pytest

from pygears.typing import Int, TemplateArgumentsError, Tuple, Uint, Union


def test_inheritance():
    assert Union[Uint[1], Uint[2]].base is Union


def test_equality():
    assert Union[1] == Union[1]
    assert Union[1, 2] != Union[1, 3]
    assert Union[1, 2] != Union[1, 2, 3]


def test_is_specified():
    assert Union[1, 2].specified is True
    assert Union['T1', 2].specified is False
    assert Union[1, Uint['T2']].specified is False


def test_repr():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    assert repr(a) == "Union['T1', 2, 'T2', 3, 'T3', 'T4']"


def test_str():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    assert str(a) == "T1 | 2 | T2 | 3 | T3 | T4"


def test_partial_subs():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    b = a[1, 'T2', 3]
    assert b.specified is False
    assert b == Union[1, 2, 'T2', 3, 3, 'T4']


def test_all_subs():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    b = a[1, 2, 3, 4]
    assert b.specified is True
    assert b == Union[1, 2, 2, 3, 3, 4]


@pytest.mark.xfail(raises=TemplateArgumentsError)
def test_excessive_subs():
    a = Union['T1', 2, 'T2', 3, 'T3', 'T4']
    a[1, 2, 3, 4, 5]


def test_indexing():
    a = Union[Uint[1], Uint[2], Uint[3]]
    assert a[0] == Uint[3]
    assert a[1] == Uint[2]


def test_define_with_tuple():
    assert Union[Uint[1], Uint[2]] == Union[(Uint[1], Uint[2])]
    assert Union[Uint[1]] == Union[(Uint[1], )]
    assert Union[Uint[1], Uint[2], Uint[3]] == Union[tuple(Uint[i] for i in range(1, 4))]


def test_decode_int():
    subt0 = Tuple[Int[8], Int[4]]
    subt1 = Tuple[Int[4], Int[8]]
    dtype = Union[subt0, subt1]

    dtype_tuple0 = Tuple[subt0, Uint[1]]
    dtype_tuple1 = Tuple[subt1, Uint[1]]

    val0 = (-128, -8)
    code0 = int(dtype_tuple0((subt0(val0), 0)))

    val1 = (-8, -128)
    code1 = int(dtype_tuple1((subt1(val1), 1)))

    assert (dtype.decode(code0).data == val0)
    assert (dtype.decode(code1).data == val1)
