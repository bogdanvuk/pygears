import pytest

from pygears.util.test_utils import synth_check
from pygears.typing import Union, Uint
from pygears.common import demux, mux, demux_ctrl
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import drv, directed
from pygears.sim import sim
from pygears import Intf


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


def mux_demux_redux(branches):
    TDin = Union[tuple(Uint[i] for i in range(1, branches + 1))]
    demux_ctrl(Intf(TDin)) | mux


@pytest.mark.parametrize('branches', [2, 3, 27])
@synth_check({'logic luts': 0, 'ffs': 0}, tool='vivado')
def test_mux_demux_redux_vivado(branches):
    mux_demux_redux(branches)


@pytest.mark.parametrize('branches', [2, 3, 27])
@synth_check({'logic luts': 0, 'ffs': 0}, tool='yosys', freduce=True)
def test_mux_demux_redux_yosys(branches):
    mux_demux_redux(branches)
