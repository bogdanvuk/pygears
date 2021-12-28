import pytest
from pygears import gear
from pygears.typing import Uint, Bool, Tuple
from pygears.lib.delay import delay_rng
from pygears.sim import sim, cosim
from pygears.lib import directed, drv


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_bare(lang, din_delay, dout_delay):
    @gear
    async def test(din: Uint) -> b'din':
        async with din as d:
            yield d

    directed(drv(t=Uint[4], seq=list(range(4)))
             | delay_rng(din_delay, din_delay),
             f=test,
             ref=list(range(4)))

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_cond_out(lang, din_delay, dout_delay):
    @gear
    async def test(din: Uint) -> Uint['din.width+2']:
        async with din as d:
            if d < 4:
                yield d
            elif d > 6:
                yield d * 2

    directed(drv(t=Uint[4], seq=list(range(8)))
             | delay_rng(din_delay, din_delay),
             f=test,
             ref=[0, 1, 2, 3, 14])

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_bare_two_inputs(lang, din_delay, dout_delay):
    @gear
    async def test(din0: Uint, din1: Uint) -> Uint['din0.width+1']:
        async with din0 as d0:
            async with din1 as d1:
                yield d0 + d1

    directed(drv(t=Uint[4], seq=list(range(8)))
             | delay_rng(din_delay, din_delay),
             drv(t=Uint[4], seq=list(range(8)))
             | delay_rng(din_delay, din_delay),
             f=test,
             ref=[2 * x for x in range(8)])

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_async_over_if_over_async(lang, din_delay, dout_delay):
    @gear
    async def test(sel: Bool, din0: Uint, din1: Uint) -> b'max(din0, din1)':
        async with sel as s:
            if s:
                async with din1 as d1:
                    yield d1
            else:
                async with din0 as d0:
                    yield d0

    directed(drv(t=Bool, seq=[0, 1, 0, 1, 0, 1, 0, 1]),
             drv(t=Uint[4], seq=list(range(4)))
             | delay_rng(din_delay, din_delay),
             drv(t=Uint[4], seq=list(range(4, 8)))
             | delay_rng(din_delay, din_delay),
             f=test,
             ref=[0, 4, 1, 5, 2, 6, 3, 7])

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_async_over_if_over_async_over_if(lang, din_delay, dout_delay):
    @gear
    async def test(sel: Bool, din0: Uint,
                   din1: Uint) -> b'max(din0, din1) * Uint[2]':
        async with sel as s:
            if s:
                async with din1 as d1:
                    if d1 > 4:
                        yield d1
            else:
                async with din0 as d0:
                    if d0 < 2:
                        yield d0
                    elif d0 > 0:
                        yield d0 * 2

    directed(drv(t=Bool, seq=[0, 1, 0, 1, 0, 1, 0, 1]),
             drv(t=Uint[4], seq=list(range(4)))
             | delay_rng(din_delay, din_delay),
             drv(t=Uint[4], seq=list(range(4, 8)))
             | delay_rng(din_delay, din_delay),
             f=test,
             ref=[0, 1, 5, 4, 6, 6, 7])

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


def test_unpack(lang):
    @gear
    async def test(din: Tuple) -> b'din[0] + din[1]':
        async with din as (d1, d2):
            yield d1 + d2

    directed(drv(t=Tuple[Uint[4], Uint[4]], seq=[(i, i+4) for i in range(4)]),
             f=test,
             ref=[2*i+4 for i in range(4)])

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)
