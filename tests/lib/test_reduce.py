import pytest
from pygears.util.test_utils import get_decoupled_dut
from functools import reduce as freduce
from pygears.lib import reduce, directed, drv, verif, delay_rng, accum, saturate as saturate_gear, qmax
from pygears.typing import Uint, Queue, Bool, saturate, trunc, Int
from pygears.sim import sim
from pygears.util.test_utils import synth_check
from pygears import Intf, gear


def test_uint_directed(sim_cls):
    init = [7, 45]
    seq = [list(range(0, 100, 10)), list(range(2))]

    def add(x, y):
        return saturate(x + y, Uint[8])

    directed(drv(t=Queue[Uint[8]], seq=seq),
             drv(t=Uint[8], seq=init),
             f=reduce(f=add, sim_cls=sim_cls),
             ref=[freduce(add, s, i) for s, i in zip(seq, init)])
    sim()


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_delay(cosim_cls, din_delay, dout_delay):
    def bitfield(n):
        return [int(digit) for digit in bin(n)[2:]]

    seq = [bitfield(0x73), bitfield(0x00)]
    init = [1, 0]

    dut = get_decoupled_dut(dout_delay, reduce(f=lambda x, y: x ^ y))
    verif(drv(t=Queue[Bool], seq=seq) | delay_rng(din_delay, din_delay),
          drv(t=Uint[8], seq=init),
          f=dut(sim_cls=cosim_cls),
          ref=reduce(name='ref_model', f=lambda x, y: x ^ y),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim()


def accum_test(accum_gear, reduce_func):
    init = [7, 45]
    seq = [list(range(0, 100, 10)), list(range(2))]

    directed(drv(t=Queue[Uint[8]], seq=seq),
             drv(t=Uint[8], seq=init),
             f=accum_gear,
             ref=[freduce(reduce_func, s, i) for s, i in zip(seq, init)])

    sim()


def test_accum_dflt_directed(sim_cls):
    def add(x, y):
        return saturate(x + y, Uint[8])

    accum_test(accum(sim_cls=sim_cls), add)


def test_accum_trunc_directed(sim_cls):
    def add(x, y):
        return trunc(x + y, Uint[8])

    accum_test(accum(sim_cls=sim_cls, cast=trunc), add)


def test_accum_saturate_gear_directed(cosim_cls):
    def add(x, y):
        return saturate(x + y, Uint[8])

    @gear
    async def add_gear(x, y) -> Uint[8]:
        async with x as dx, y as dy:
            yield saturate(dx + dy, t=Uint[8])

    accum_test(reduce(f=add_gear, sim_cls=cosim_cls), add)


def test_qmax(sim_cls):
    seq = [list(range(-20, 24, 4))]

    directed(drv(t=Queue[Int[8]], seq=seq), f=qmax, ref=[max(s) for s in seq])

    sim()
