from pygears import gear
from pygears.lib import xor
from pygears.lib.verif import drv, verif
from pygears.sim import sim
from pygears.typing import Uint


def test_basic(tmpdir, cosim_cls):

    seq_op1 = [1, 2, 3]
    seq_op2 = [2, 2, 2]

    @gear
    def xor_wrap(op1, op2):
        return op1 ^ op2

    verif(
        drv(t=Uint[4], seq=seq_op1),
        drv(t=Uint[4], seq=seq_op2),
        f=xor_wrap(sim_cls=cosim_cls),
        ref=xor(name='ref_model'))

    sim(outdir=tmpdir)
