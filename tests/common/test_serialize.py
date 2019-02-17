import pytest

from pygears.common.serialize import TDin, serialize
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Array, Uint


def test_directed(tmpdir, sim_cls):
    brick_size = 4
    seq_list = [1, 2, 3, 4]

    directed(
        drv(t=Array[Uint[16], brick_size],
            seq=[(i, ) * brick_size for i in seq_list]),
        f=serialize(sim_cls=sim_cls),
        ref=sorted(seq_list * brick_size))

    sim(outdir=tmpdir)


def test_directed_active(tmpdir, sim_cls):
    no = 4
    directed(
        drv(t=TDin[Uint[8], no, 4],
            seq=[((8, ) * no, 3), ((2, ) * no, 4), ((1, ) * no, 1)]),
        f=serialize(sim_cls=sim_cls),
        ref=[[8] * 3, [2] * 4, [1]])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
    brick_size = 4
    seq_list = [1, 2, 3, 4]
    verif(
        drv(t=Array[Uint[16], brick_size],
            seq=[(i, ) * brick_size
                 for i in seq_list]) | delay_rng(din_delay, din_delay),
        f=serialize(sim_cls=cosim_cls),
        ref=serialize(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_cosim_active(tmpdir, cosim_cls, din_delay, dout_delay):
    no = 4
    verif(
        drv(t=TDin[Uint[8], no, 4],
            seq=[((8, ) * no, 3), ((2, ) * no, 4),
                 ((1, ) * no, 1)]) | delay_rng(din_delay, din_delay),
        f=serialize(sim_cls=cosim_cls),
        ref=serialize(name='ref_model'),
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)
