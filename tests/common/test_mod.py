from pygears.util.test_utils import skip_ifndef
from pygears.cookbook.verif import verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Tuple, Uint
from pygears.sim.modules.verilator import SimVerilated
from pygears.common import mod


def test_unsigned_cosim(tmpdir):
    skip_ifndef('VERILATOR_ROOT')
    seq = [(0x6, 0x2), (0x5, 0x2), (0x4, 0x3)]

    verif(
        drv(t=Tuple[Uint[4], Uint[2]], seq=seq),
        f=mod(sim_cls=SimVerilated),
        ref=mod(name='ref_model'))

    sim(outdir=tmpdir)
