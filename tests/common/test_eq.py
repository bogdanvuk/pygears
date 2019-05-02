from pygears import gear
from pygears.cookbook.verif import verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Uint
from pygears.common import eq


def test_basic(tmpdir, cosim_cls):

    seq_op1 = [1, 2, 3]
    seq_op2 = [2, 2, 2]

    @gear
    def eq_wrap(op1, op2):
        return op1 == op2

    verif(
        drv(t=Uint[4], seq=seq_op1),
        drv(t=Uint[4], seq=seq_op2),
        f=eq_wrap(sim_cls=cosim_cls),
        ref=eq(name='ref_model'))

    sim(outdir=tmpdir)
