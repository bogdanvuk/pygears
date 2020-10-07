from pygears.lib import repack, drv, directed
from pygears.typing import Uint, Tuple
from pygears import sim
from pygears.sim import cosim


def test_basic(tmpdir, sim_cls):
    tin = Tuple['a':Uint[1], 'b':Uint[2], 'c':Uint[3], 'd':Uint[4]]

    tout = Tuple['a':Uint[1], 'c':Uint[3]]

    directed(drv(t=tin, seq=[(1, 2, 3, 4)] * 3),
             f=repack(t=tout, sim_cls=sim_cls),
             ref=[(1, 3)] * 3)

    sim(tmpdir)


def test_name_map(tmpdir, sim_cls):
    tin = Tuple['a':Uint[1], 'b':Uint[2], 'c':Uint[3], 'd':Uint[4]]

    tout = Tuple['f':Uint[1], 'g':Uint[3]]

    directed(drv(t=tin, seq=[(1, 2, 3, 4)] * 3),
             f=repack(t=tout, sim_cls=sim_cls, name_map={
                 'f': 'a',
                 'g': 'c'
             }),
             ref=[(1, 3)] * 3)

    sim(tmpdir)


def test_val_map(tmpdir, sim_cls):
    tin = Tuple['a':Uint[1], 'b':Uint[2], 'c':Uint[3], 'd':Uint[4]]

    tout = Tuple['f':Uint[1], 'g':Uint[3]]

    directed(drv(t=tin, seq=[(1, 2, 3, 4)] * 3),
             f=repack(t=tout, sim_cls=sim_cls, name_map={
                 'f': 'a',
                 'g': 'c'
             }, val_map={'g': 2}),
             ref=[(1, 2)] * 3)

    sim(tmpdir)


# from pygears.sim.modules import SimVerilated
# from functools import partial
# test_name_map('/tools/home/tmp/test_name_map', partial(SimVerilated, lang='v'))

