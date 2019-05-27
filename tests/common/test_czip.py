import pytest
from pygears import Intf
from pygears.typing import Queue, Tuple, Uint
from pygears.common import czip

from pygears.sim import sim
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import drv, verif


def test_general():
    iout = czip(Intf(Uint[1]), Intf(Queue[Uint[2], 1]),
                Intf(Queue[Uint[3], 3]), Intf(Queue[Uint[4], 5]))

    assert iout.dtype == Queue[Tuple[Uint[1], Uint[2], Uint[3], Uint[4]], 5]


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    verif(drv(t=Uint[8], seq=list(range(10)))
          | delay_rng(din_delay, din_delay),
          drv(t=Queue[Uint[8]], seq=[list(range(10))])
          | delay_rng(din_delay, din_delay),
          f=czip(sim_cls=cosim_cls),
          ref=czip(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)
