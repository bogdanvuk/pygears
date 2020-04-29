import pytest
from pygears import gear, config
from pygears.typing import Bool, Uint, code, Queue, Tuple, bitw
from pygears.lib.delay import delay_rng
from pygears.sim import sim, cosim
from pygears.lib import drv, shred, directed
from pygears.lib.rng import qrange
from pygears.lib.mux import mux
from pygears.lib.union import select


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_intf_vararg_fix_index(lang, din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(*din: Uint) -> b'din[0]':
        async with din[0] as d:
            yield d

    directed(
        drv(t=Uint[4], seq=list(range(4)))
        | delay_rng(din_delay, din_delay),
        drv(t=Uint[4], seq=list(range(4, 8)))
        | delay_rng(din_delay, din_delay),
        f=test,
        delays=[delay_rng(dout_delay, dout_delay)],
        ref=list(range(4)))

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_intf_vararg_mux(sim_cls, din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(*din: Uint) -> b'din[0]':
        async with mux(0, *din) as d:
            yield code(d[0], Uint[4])

    directed(
        drv(t=Uint[4], seq=list(range(4)))
        | delay_rng(din_delay, din_delay),
        drv(t=Uint[4], seq=list(range(4, 8)))
        | delay_rng(din_delay, din_delay),
        f=test(sim_cls=sim_cls),
        delays=[delay_rng(dout_delay, dout_delay)],
        ref=list(range(4)))

    sim(check_activity=False)


def test_loop_select_intfs(lang):
    @gear(hdl={'compile': True})
    async def test(*din: Uint) -> b'din[0]':
        dsel: Uint[4]
        for i in range(len(din)):
            async with select(i, *din) as d:
                yield d

    directed(
        drv(t=Uint[4], seq=list(range(4))),
        drv(t=Uint[4], seq=list(range(4, 8))),
        f=test,
        ref=[0, 4, 1, 5, 2, 6, 3, 7])

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_loop_intfs(lang, din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(*din: Uint) -> b'din[0]':
        for d in din:
            async with d as data:
                yield data

    directed(
        drv(t=Uint[4], seq=list(range(4)))
        | delay_rng(din_delay, din_delay),
        drv(t=Uint[4], seq=list(range(4, 8)))
        | delay_rng(din_delay, din_delay),
        f=test,
        delays=[delay_rng(dout_delay, dout_delay)],
        ref=[0, 4, 1, 5, 2, 6, 3, 7])

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_enum_intfs(lang, din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(*din: Uint) -> b'din[0]':
        for i, d in enumerate(din):
            async with d as data:
                yield data

    directed(
        drv(t=Uint[4], seq=list(range(4)))
        | delay_rng(din_delay, din_delay),
        drv(t=Uint[4], seq=list(range(4, 8)))
        | delay_rng(din_delay, din_delay),
        f=test,
        delays=[delay_rng(dout_delay, dout_delay)],
        ref=[0, 4, 1, 5, 2, 6, 3, 7])

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_enum_intfs_single(lang, din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(*din: Uint) -> b'din[0]':
        for i, d in enumerate(din):
            async with d as data:
                yield data

    directed(
        drv(t=Uint[4], seq=list(range(4)))
        | delay_rng(din_delay, din_delay),
        f=test,
        delays=[delay_rng(dout_delay, dout_delay)],
        ref=list(range(4)))

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_enum_intfs_use_i(lang, din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(*din: Uint) -> Tuple['din[0]', Uint['bitw(len(din))']]:
        for i, d in enumerate(din):
            async with d as data:
                yield data, i

    directed(
        drv(t=Uint[4], seq=list(range(4)))
        | delay_rng(din_delay, din_delay),
        drv(t=Uint[4], seq=list(range(4, 8)))
        | delay_rng(din_delay, din_delay),
        f=test,
        delays=[delay_rng(dout_delay, dout_delay)],
        ref=[(0, 0), (4, 1), (1, 0), (5, 1), (2, 0), (6, 1), (3, 0), (7, 1)])

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_loop_queue_intfs(lang, din_delay, dout_delay):
    @gear(hdl={'compile': True})
    async def test(*din: Queue) -> b'din[0].data':
        for i, d in enumerate(din):
            async for (data, last) in d:
                yield data

    directed(
        drv(t=Queue[Uint[4]], seq=[list(range(4))])
        | delay_rng(din_delay, din_delay),
        drv(t=Queue[Uint[4]], seq=[list(range(4, 8))])
        | delay_rng(din_delay, din_delay),
        f=test,
        delays=[delay_rng(dout_delay, dout_delay)],
        ref=list(range(4)) + list(range(4, 8)))

    cosim('/test', 'verilator', lang=lang)
    sim(check_activity=False)
