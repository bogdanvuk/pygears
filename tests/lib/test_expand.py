from pygears import Intf
from pygears import reg
from pygears.typing import Queue, Tuple, Union, Uint
from pygears.typing.base import param_subs
from pygears.typing.expand import expand as expand_type
from pygears.lib import expand


# Tests for out type resolve function
def test_expand_queue_union():
    a = Queue[Union[1, 2], 6]
    b = expand_type(a)

    assert b == Union[Queue[1, 6], Queue[2, 6]]


def test_expand_tuple_union():
    a = Tuple[Union[1, 2], Union[3, 4]]
    b = expand_type(a)

    assert b == Union[Tuple[1, 3], Tuple[2, 3], Tuple[1, 4], Tuple[2, 4]]


def test_expand_queue_tuple():
    a = Queue[Tuple[1, 2]]
    b = expand_type(a)

    assert b == Tuple[Queue[1], Queue[2]]


def test_expand_queue_union_str_subs():
    a = param_subs('expand(Queue[Union[1, 2], 6])', {},
                   reg['gear/type_arith'])

    assert a == Union[Queue[1, 6], Queue[2, 6]]


# Tests for gear
def test_gear_expand_queue_union():
    a = Queue[Union[Uint[3], Uint[3]]]
    iout = expand(Intf(a))

    assert iout.dtype == expand_type(a)


def test_gear_expand_tuple_union():
    a = Tuple[Union[Uint[2], Uint[2]], Union[Uint[4], Uint[4]]]
    iout = expand(Intf(a))

    assert iout.dtype == expand_type(a)


def test_gear_expand_tuple_union_tuple():
    a = Tuple[Union[Uint[2], Uint[2]],
              Tuple[Uint[3], Uint[3]],
              Union[Uint[4], Uint[4]]]
    iout = expand(Intf(a))

    assert iout.dtype == expand_type(a)


def test_gear_expand_tuple_union_complex():
    a = Tuple[Union[Uint[2], Uint[3]],
              Union[Uint[10], Uint[11], Uint[12]],
              Tuple[Uint[8], Uint[8]],
              Union[Uint[7], Uint[8]]]
    iout = expand(Intf(a))

    assert iout.dtype == expand_type(a)


def test_gear_expand_tuple_three_union():
    a = Tuple[Union[Uint[2], Uint[2]], Union[Uint[4], Uint[4]],
              Union[Uint[8], Uint[8]]]
    iout = expand(Intf(a))

    assert iout.dtype == expand_type(a)


def test_gear_expand_queue_tuple():
    a = Queue[Tuple[Uint[4], Uint[6]]]
    iout = expand(Intf(a))

    assert iout.dtype == expand_type(a)
