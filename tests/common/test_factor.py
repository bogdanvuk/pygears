from pygears import registry
from pygears.typing import Queue, Tuple, Union
from pygears.typing.base import param_subs
from pygears.typing_common.factor import factor


def test_factor_union_queue():
    a = Union[Queue[1, 6], Queue[2, 6]]
    b = factor(a)

    assert b == Queue[Union[1, 2], 6]


def test_factor_tuple_queue():
    a = Tuple[Queue[1], Queue[2]]
    b = factor(a)

    assert b == Queue[Tuple[1, 2]]


def test_factor_union_queue_str_subs():
    a = param_subs('factor(Union[Queue[1, 6], Queue[2, 6]])', {},
                   registry('TypeArithNamespace'))

    assert a == Queue[Union[1, 2], 6]
