from pygears import Intf, gear, reg
from pygears.lib.verif import directed
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.sim.modules import SimVerilated
from pygears.typing import Uint, Tuple
from pygears.lib import add, fmap, decouple
from functools import partial


@gear
def dualcycle(din0, din1) -> (b'din0[0]', b'din1[0]'):
    return din0[0], din1[0]


@gear
def dualcycle_wrap_thin(din) -> b'din[0][0]':
    middle = Intf(din.dtype[0])

    return dualcycle(
        din, middle, intfs={'dout0': middle}, sim_cls=partial(SimVerilated, timeout=1))


@gear
def dualcycle_wrap_comb_middle(din) -> b'din[0][0]':
    middle = Intf(din.dtype[0])

    middle_back = (middle | fmap(f=(add(0), add(0)))) >> din.dtype[0]

    return dualcycle(
        din,
        middle_back,
        intfs={'dout0': middle},
        sim_cls=partial(SimVerilated, timeout=1))


@gear
def dualcycle_wrap_decouple_middle(din) -> b'din[0][0]':
    middle = Intf(din.dtype[0])

    middle_back = middle | decouple

    return dualcycle(
        din,
        middle_back,
        intfs={'dout0': middle},
        sim_cls=partial(SimVerilated, timeout=1))


def multicycle_test_gen(func, latency):
    data_num = 10

    data = [((i, 1), 2) for i in range(data_num)]

    directed(
        drv(t=Tuple[Tuple[Uint[8], Uint[8]], Uint[8]], seq=data),
        f=func,
        ref=list(range(data_num)))

    sim()

    assert reg['sim/timestep'] == (data_num + latency - 1)


def test_multicycle_thin():
    # One additional cycle is needed for Verilator timeout set above
    multicycle_test_gen(dualcycle_wrap_thin, latency=2)


def test_multicycle_comb_middle():
    # One additional cycle is needed for Verilator timeout set above
    multicycle_test_gen(dualcycle_wrap_comb_middle, latency=2)


def test_multicycle_decouple_middle():
    # One additional cycle is needed for Verilator timeout set above
    multicycle_test_gen(dualcycle_wrap_decouple_middle, latency=4)
