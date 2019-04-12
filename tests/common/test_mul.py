from pygears import Intf
from pygears.common import mul
from pygears.cookbook.verif import verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Int, Tuple, Uint
from pygears.util.test_utils import synth_check


def test_unsigned_overflow_cosim(tmpdir, cosim_cls):
    seq = [(0x1, 0xf), (0x2, 0xe), (0x3, 0xd)]

    verif(
        drv(t=Tuple[Uint[2], Uint[4]], seq=seq),
        f=mul(sim_cls=cosim_cls),
        ref=mul(name='ref_model'))

    sim(outdir=tmpdir)


def test_signed_unsigned_cosim(tmpdir, cosim_cls):
    seq = [(0x1, 0xf), (-0x2, 0xf), (0x1, 0x0), (-0x2, 0x0)]

    verif(
        drv(t=Tuple[Int[2], Uint[4]], seq=seq),
        f=mul(sim_cls=cosim_cls),
        ref=mul(name='ref_model'))

    sim(outdir=tmpdir)


def test_unsigned_signed_cosim(tmpdir, cosim_cls):
    seq = [(0x1, 0x7), (0x1, -0x8), (0x2, 0x7), (0x2, -0x8)]

    verif(
        drv(t=Tuple[Uint[2], Int[4]], seq=seq),
        f=mul(sim_cls=cosim_cls),
        ref=mul(name='ref_model'))

    sim(outdir=tmpdir)


def test_signed_cosim(tmpdir, cosim_cls):
    seq = [(0x1, 0x7), (-0x2, 0x7), (0x1, -0x8), (-0x2, -0x8)]

    verif(
        drv(t=Tuple[Int[2], Int[4]], seq=seq),
        f=mul(sim_cls=cosim_cls),
        ref=mul(name='ref_model'))

    sim(outdir=tmpdir)


@synth_check({
    'logic luts': 43,
    'ffs': 0,
    'path delay': lambda delay: delay < 8.0
})
def test_unsigned_synth():
    mul(Intf(Tuple[Uint[10], Uint[4]]))
