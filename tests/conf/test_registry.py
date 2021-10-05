from pygears import reg, clear
from dataclasses import dataclass
from typing import Any, Callable


def test_basic():
    clear()

    reg['a/b'] = 1

    reg['a/c'] = 3
    reg['a/b'] = 2

    reg['d'] = 4

    assert reg['a/b'] == 2
    assert reg['a/c'] == 3
    assert reg['d'] == 4


def test_conf_getter():
    clear()

    def get_b(var):
        return var.path

    reg.confdef('a/b', getter=get_b)

    assert reg['a/b'] == 'a/b'


def test_conf_setter():
    clear()

    values = []

    def set_b(var, val):
        if val is None:
            return

        values.append(val)

    reg.confdef('a/b', setter=set_b)

    reg['a/b'] = 1
    reg['a/b'] = 2

    assert values == [1, 2]

def test_subreg():
    clear()

    reg.subreg('a')

    a = reg['a']

    a['b'] = 1
    a['c/d'] = 2

    assert reg['a/b'] == 1
    assert reg['a/c/d'] == 2
