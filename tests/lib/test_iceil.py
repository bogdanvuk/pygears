import math
import pytest

from pygears.lib import iceil
from pygears.lib.verif import directed
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.typing import Uint


@pytest.mark.parametrize('div', [1, 2, 4, 8])
def test_directed(tmpdir, sim_cls, div):
    seq = list(range(256 - div))
    ref = [math.ceil(x / div) for x in seq]
    directed(
        drv(t=Uint[8], seq=seq), f=iceil(sim_cls=sim_cls, div=div), ref=ref)
    sim(outdir=tmpdir)
