import pytest

from pygears.util.test_utils import synth_check
from pygears.typing import Union, Uint
from pygears.common import demux, mux, demux_ctrl
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import drv, directed
from pygears.sim import sim
from pygears.sim.modules import SimVerilated
from pygears import config, Intf
from pygears.util.test_utils import vivado_synth


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
@pytest.mark.parametrize('branches', list(range(2, 10)))
def test_simple_directed(tmpdir, sim_cls, din_delay, dout_delay, branches):

    seq = [(i, i) for i in range(branches)]
    TDin = Union[tuple(Uint[i] for i in range(1, branches + 1))]

    directed(
        drv(t=TDin, seq=seq) | delay_rng(din_delay, din_delay),
        f=demux(sim_cls=sim_cls),
        delays=[delay_rng(dout_delay, dout_delay) for _ in range(branches)],
        ref=[[i] for i in range(branches)])

    sim(outdir=tmpdir)


# @pytest.mark.parametrize('branches', list(range(2, 10)))
# @pytest.mark.parametrize('branches', [3])
# @synth_check({'logic luts': 33, 'ffs': 0})

# 3 -> 3, 10 -> 9, 11 -> 10

def test_simple_synth(branches):
    # TDin = Union[tuple(Uint[i] for i in range(1, branches + 1))]
    TDin = Union[Uint[1], Uint[1]]

    demux_ctrl(Intf(TDin)) | mux

    # util = vivado_synth('/tools/home/tmp', language='sv')
    # print(util)
    # assert util['total luts'] == branches


# # test_simple_directed('/tools/home/tmp', SimVerilated, 0, 0, 3)
test_simple_synth(2)

# config['trace/level'] = 1
# sim('/tools/home/tmp')
