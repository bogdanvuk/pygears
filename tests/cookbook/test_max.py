from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Tuple, Uint, Int
from pygears.cookbook import max2


def test_unsigned_overflow(tmpdir, sim_cls):
    seq = [(0x1, 0xf), (0x2, 0xe), (0x3, 0xd)]

    directed(
        drv(t=Tuple[Uint[2], Uint[4]], seq=seq),
        f=max2(sim_cls=sim_cls),
        ref=[0xf, 0xe, 0xd])

    sim(outdir=tmpdir)


def test_signed_unsigned(tmpdir, sim_cls):
    seq = [(0x1, 0xf), (-0x2, 0xf), (0x1, 0x0), (-0x2, 0x0)]

    directed(
        drv(t=Tuple[Int[2], Uint[4]], seq=seq),
        f=max2(sim_cls=sim_cls),
        ref=[0xf, 0xf, 0x1, 0x0])

    sim(outdir=tmpdir)


def test_unsigned_signed_cosim(tmpdir, sim_cls):
    seq = [(0x1, 0x7), (0x1, -0x8), (0x2, 0x7), (0x2, -0x8)]

    directed(
        drv(t=Tuple[Uint[2], Int[4]], seq=seq),
        f=max2(sim_cls=sim_cls),
        ref=[0x7, 0x1, 0x7, 0x2])

    sim(outdir=tmpdir)


def test_signed_cosim(tmpdir, sim_cls):
    seq = [(0x1, 0x7), (-0x2, 0x7), (0x1, -0x8), (-0x2, -0x8)]

    directed(
        drv(t=Tuple[Int[2], Int[4]], seq=seq),
        f=max2(sim_cls=sim_cls),
        ref=[0x7, 0x7, 0x1, -0x2])

    sim(outdir=tmpdir)
