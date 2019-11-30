import pytest
from pygears.util.test_utils import get_decoupled_dut
from pygears.lib import reduce, directed, drv, verif, delay_rng, accum
from pygears.typing import Uint, Queue, Bool
from pygears.sim import sim
from pygears.util.test_utils import synth_check
from pygears import Intf


def test_uint_directed(tmpdir, sim_cls):
    init = [7, 45]
    seq = [list(range(10)), list(range(2))]

    def add(x, y):
        return x + y

    directed(drv(t=Queue[Uint[8]], seq=seq),
             drv(t=Uint[8], seq=init),
             f=reduce(f=add, sim_cls=sim_cls, t=Uint[8]),
             ref=[sum(s, i) for s, i in zip(seq, init)])
    sim(resdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 1, 10])
@pytest.mark.parametrize('dout_delay', [0, 1, 10])
def test_delay(tmpdir, cosim_cls, din_delay, dout_delay):
    def bitfield(n):
        return [int(digit) for digit in bin(n)[2:]]

    seq = [bitfield(0x73), bitfield(0x00)]
    init = [1, 0]

    dut = get_decoupled_dut(dout_delay, reduce(f=lambda x, y: x ^ y, t=Uint[8]))
    verif(drv(t=Queue[Bool], seq=seq) | delay_rng(din_delay, din_delay),
          drv(t=Uint[8], seq=init),
          f=dut(sim_cls=cosim_cls),
          ref=reduce(name='ref_model', f=lambda x, y: x ^ y, t=Uint[8]),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim(resdir=tmpdir)
