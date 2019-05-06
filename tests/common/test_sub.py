from pygears.sim import sim
from pygears.cookbook.verif import drv, directed, verif
from pygears.typing import Tuple, Uint, Int
from pygears.common import sub
from pygears import gear


def test_unsigned_overflow_cosim(tmpdir, cosim_cls):
    seq = [(0x1, 0x2), (0x1, 0x1), (0xf, 0x1)]

    verif(
        drv(t=Tuple[Uint[4], Uint[2]], seq=seq),
        f=sub(sim_cls=cosim_cls),
        ref=sub(name='ref_model'))

    sim(outdir=tmpdir)


def test_signed_unsigned_cosim(tmpdir, cosim_cls):
    seq = [(0x1, 0xf), (-0x2, 0xf), (0x1, 0x0), (-0x2, 0x0)]

    verif(
        drv(t=Tuple[Int[2], Uint[4]], seq=seq),
        f=sub(sim_cls=cosim_cls),
        ref=sub(name='ref_model'))

    sim(outdir=tmpdir)


def test_unsigned_signed_cosim(tmpdir, cosim_cls):
    seq = [(0x1, 0x7), (0x1, -0x8), (0x2, 0x7), (0x2, -0x8)]

    verif(
        drv(t=Tuple[Uint[2], Int[4]], seq=seq),
        f=sub(sim_cls=cosim_cls),
        ref=sub(name='ref_model'))

    sim(outdir=tmpdir)


def test_signed_cosim(tmpdir, cosim_cls):
    seq = [(0x1, 0x7), (-0x2, 0x7), (0x1, -0x8), (-0x2, -0x8)]

    verif(
        drv(t=Tuple[Int[2], Int[4]], seq=seq),
        f=sub(sim_cls=cosim_cls),
        ref=sub(name='ref_model'))

    sim(outdir=tmpdir)


def test_hier(tmpdir, cosim_cls):
    @gear
    def const_sub(din):
        return din - 1

    directed(
        drv(t=Uint[4], seq=[1, 2, 3]),
        f=const_sub(sim_cls=cosim_cls),
        ref=[0, 1, 2])

    sim(outdir=tmpdir)
