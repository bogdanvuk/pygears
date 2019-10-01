from pygears.conf.utils import intercept_arguments
from pygears.conf.registry import inject, Inject


@intercept_arguments
def mix_no_args(x, a=1, y=2, **b):
    return (x, a, y, b)


def test_mix_no_args():
    assert mix_no_args(11) == (11, 1, 2, {})
    assert mix_no_args(x=11, y=12, a=13) == (11, 13, 12, {})
    assert mix_no_args(3, 4, 5) == (3, 4, 5, {})
    assert mix_no_args(
        3, 4, 5, m=6, z=7, k=8, j=9) == (3, 4, 5, {
            'm': 6,
            'z': 7,
            'k': 8,
            'j': 9
        })


@intercept_arguments
def mix_no_kwds(x, a=1, y=2, *b):
    return (x, a, y, b)


def test_mix_no_kwds():
    assert mix_no_kwds(11) == (11, 1, 2, ())
    assert mix_no_kwds(x=11, y=12, a=13) == (11, 13, 12, ())
    assert mix_no_kwds(3, 4, 5) == (3, 4, 5, ())
    assert mix_no_kwds(3, 4, 5, 6, 7, 8, 9) == (3, 4, 5, (6, 7, 8, 9))


@intercept_arguments
def args_kwargs(*a, **k):
    return (a, k)


def test_args_kwargs():
    assert args_kwargs(3, x=2, y=1) == ((3, ), {'x': 2, 'y': 1})
    assert args_kwargs(
        3, 4, x=2, y=1) == ((
            3,
            4,
        ), {
            'x': 2,
            'y': 1
        })


@intercept_arguments
def named(a, b, x, c):
    return (a, b, x, c)


def test_named():
    assert named(3, 4, 5, 6) == (3, 4, 5, 6)
    assert named(a=3, b=4, x=5, c=6) == (3, 4, 5, 6)


@intercept_arguments
def named_dflt(a, b, x=3, c=2):
    return (a, b, x, c)


def test_named_dflt():
    assert named_dflt(3, 4, 5, 6) == (3, 4, 5, 6)
    assert named_dflt(1, 2, 9) == (1, 2, 9, 2)
    assert named_dflt(a=1, b=2) == (1, 2, 3, 2)


@inject
def get_from_reg(x=5, sim_lvl=Inject('logger/sim/level')):
    return (x, sim_lvl)


def test_registry():
    assert get_from_reg() == (5, 20)
    assert get_from_reg(1, 2) == (1, 2)
