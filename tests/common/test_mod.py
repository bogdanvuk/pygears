from pygears.cookbook.verif import verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Tuple, Uint
from pygears.common import mod


def test_unsigned_cosim(tmpdir, sim_cls):
    seq = [(0x6, 0x2), (0x5, 0x2), (0x4, 0x3)]

    verif(
        drv(t=Tuple[Uint[4], Uint[2]], seq=seq),
        f=mod(sim_cls=sim_cls),
        ref=mod(name='ref_model'))

    sim(outdir=tmpdir)
