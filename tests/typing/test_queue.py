import pytest
from pygears.typing import Queue, TemplateArgumentsError, Uint


def test_inheritance():
    assert Queue[1].base is Queue


def test_default():
    a = Queue[2]
    assert a.args[1] == 1

    b = Queue[2, 6]
    assert b.args[1] == 6


def test_equality():
    assert Queue[1] == Queue[1]
    assert Queue[1] == Queue[1, 1]
    assert Queue[1, 2] != Queue[1, 3]
    assert Queue[1, 2] == Queue[1, 2]


def test_repr():
    a = Queue['T1', 3]
    assert repr(a) == "Queue['T1', 3]"


def test_str():
    a = Queue['T1', 3]
    assert str(a) == "[T1]^3"


def test_is_specified():
    assert Queue[1].specified is True
    assert Queue['T1'].specified is False
    assert Queue[Uint['T2']].specified is False
    assert Queue[Uint[1]].specified is True


def test_subs():
    a = Queue['T1']
    b = a[1]
    assert b == Queue[1]


def test_multilevel_subs():
    a = Queue[Uint['T1']]
    b = a[1]
    assert b == Queue[Uint[1]]


@pytest.mark.xfail(raises=TemplateArgumentsError)
def test_excessive_subs():
    a = Queue[Uint['T1']]
    a[1, 2]


def test_indexing():
    a = Queue[Uint[10]]
    assert a[0] == Uint[10]
    assert a[1] == Uint[1]

    data, eot = a
    assert data == a[0]
    assert eot == a[1]


def test_queue_of_queues():
    assert Queue[Queue[Uint[2], 2], 3] == Queue[Uint[2], 5]
