from pygears.lib import regmap, trigreg, directed, drv, delay_gen
from pygears.typing import Maybe, Tuple, Uint
from pygears.sim import sim, cosim


def test_none():
    directed(drv(t=Maybe[Uint[8]], seq=[None]), f=trigreg, ref=[])
    cosim('/trigreg', 'verilator')
    sim()


def test_two():
    directed(
        drv(t=Maybe[Uint[8]], seq=[2, None]) | delay_gen(f=iter([0, 1])),
        f=trigreg,
        ref=[2, 2],
    )
    cosim('/trigreg', 'verilator')
    sim()


def test_three():
    directed(
        drv(t=Maybe[Uint[8]], seq=[2, None, 3, None])
        | delay_gen(f=iter([0, 1, 0, 0])),
        f=trigreg,
        ref=[2, 2, 3],
    )
    cosim('/trigreg', 'verilator')
    sim()


def test_regmap():

    t_addr = Uint[2]
    t_data = Uint[8]

    directed(
        drv(t=Tuple[t_addr, t_data], seq=[(0, 0), (3, 1), (0, 2), (0, 3)]),
        f=regmap(addrmap={
            0: 0,
            3: 1
        }, initmap={1: 9}),
        ref=[[0, 0, 2, 3, 3], [9, 9, 1, 1, 1, 1]])

    cosim('/regmap', 'verilator')
    sim(timeout=6)
