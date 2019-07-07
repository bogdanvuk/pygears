from pygears import registry, Intf
from pygears.lib import factor
from pygears.typing import Queue, Tuple, Union, Uint
from pygears.typing.base import param_subs
from pygears.typing.factor import factor as factor_type


# Tests for out type resolve function
def test_factor_union_queue():
    a = Union[Queue[1, 6], Queue[2, 6]]
    b = factor_type(a)

    assert b == Queue[Union[1, 2], 6]


def test_factor_tuple_queue():
    a = Tuple[Queue[1], Queue[2]]
    b = factor_type(a)

    assert b == Queue[Tuple[1, 2]]


def test_factor_union_queue_str_subs():
    a = param_subs('factor(Union[Queue[1, 6], Queue[2, 6]])', {},
                   registry('gear/type_arith'))

    assert a == Queue[Union[1, 2], 6]


# Tests for gear
def test_gear_factor_union_queue():
    a = Union[Queue[Uint[16]], Queue[Uint[16]]]
    iout = factor(Intf(a))

    assert iout.dtype == factor_type(a)


def test_gear_factor_tuple_queue():
    a = Tuple[Queue[Uint[4]], Queue[Uint[8]]]
    iout = factor(Intf(a))

    assert iout.dtype == factor_type(a)
