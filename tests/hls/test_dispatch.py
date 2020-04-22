from pygears import gear
from functools import singledispatch
from pygears.typing import Uint, Int, Integer
from pygears.typing.uint import UintType, IntType
from pygears.lib import directed, drv
from pygears.sim import sim


@singledispatch
def dispatch_test(val):
    raise TypeError


@dispatch_test.register(Int)
def _(val: Int):
    return val - 1


@dispatch_test.register(Uint)
def _(val: Uint):
    return val + 1


def test_simple_uint(sim_cls):
    @gear(hdl={'compile': True})
    async def test(din: Integer['w']) -> b'din.base[w+1]':
        async with din as d:
            yield dispatch_test(d)

    directed(drv(t=Uint[8], seq=[0, 1, 2]),
             f=test(sim_cls=sim_cls),
             ref=[1, 2, 3])

    sim(timeout=3)


def test_simple_int(sim_cls):
    @gear(hdl={'compile': True})
    async def test(din: Integer['w']) -> b'din.base[w+1]':
        async with din as d:
            yield dispatch_test(d)

    directed(drv(t=Int[8], seq=[0, -1, -2]),
             f=test(sim_cls=sim_cls),
             ref=[-1, -2, -3])

    sim(timeout=3)


@singledispatch
def dispatch_types(t, val):
    raise TypeError


@dispatch_types.register(IntType)
def _(t: IntType, val):
    return t(val - 1)


@dispatch_types.register(UintType)
def _(t: UintType, val):
    return t(val + 1)


def test_type_uint(sim_cls):
    @gear(hdl={'compile': True})
    async def test(din: Integer['w'], *, t) -> b't':
        async with din as d:
            yield dispatch_types(t, d)

    directed(drv(t=Uint[8], seq=[0, 1, 2]),
             f=test(sim_cls=sim_cls, t=Uint[16]),
             ref=[1, 2, 3])

    sim(timeout=3)


def test_type_int(sim_cls):
    @gear(hdl={'compile': True})
    async def test(din: Integer['w'], *, t) -> b't':
        async with din as d:
            yield dispatch_types(t, d)

    directed(drv(t=Uint[8], seq=[0, 1, 2]),
             f=test(sim_cls=sim_cls, t=Int[16]),
             ref=[-1, 0, 1])

    sim(timeout=3)
