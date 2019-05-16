import pytest

from pygears.common import ccat
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, drv, verif
from pygears.sim import sim
from pygears.typing import Queue, Uint


@pytest.mark.parametrize('din_delay', [(0, 0, 0), (1, 5, 3)])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_uint_3(tmpdir, cosim_cls, din_delay, dout_delay):

    directed(
        drv(t=Uint[2], seq=[0, 1, 2, 3])
        | delay_rng(din_delay[0], din_delay[0]),
        drv(t=Uint[3], seq=[4, 5, 6, 7])
        | delay_rng(din_delay[1], din_delay[1]),
        drv(t=Uint[8], seq=[8, 9, 10, 11])
        | delay_rng(din_delay[2], din_delay[2]),
        f=ccat(sim_cls=cosim_cls),
        ref=[(0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [(0, 0, 0), (1, 5, 3)])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_queue_3(tmpdir, cosim_cls, din_delay, dout_delay):

    verif(
        drv(t=Queue[Uint[2]], seq=[[0, 1], [2, 3]])
        | delay_rng(din_delay[0], din_delay[0]),
        drv(t=Queue[Uint[3]], seq=[[4, 5], [6, 7]])
        | delay_rng(din_delay[1], din_delay[1]),
        drv(t=Queue[Uint[8]], seq=[[8, 9], [10, 11]])
        | delay_rng(din_delay[2], din_delay[2]),
        f=ccat(sim_cls=cosim_cls),
        ref=ccat(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)
