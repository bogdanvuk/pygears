from pygears.common.expand import type_expand as expand
from pygears import Queue, Union, registry, Tuple
from pygears.typing.base import param_subs


def test_expand_queue_union():
    a = Queue[Union[1, 2], 6]
    b = expand(a)

    assert b == Union[Queue[1, 6], Queue[2, 6]]


def test_expand_tuple_union():
    a = Tuple[Union[1, 2], Union[3, 4]]
    b = expand(a)

    assert b == Union[Tuple[1, 3], Tuple[2, 3], Tuple[1, 4], Tuple[2, 4]]


def test_expand_queue_union_str_subs():
    a = param_subs('expand(Queue[Union[1, 2], 6])', {},
                   registry('TypeArithNamespace'))

    assert a == Union[Queue[1, 6], Queue[2, 6]]
