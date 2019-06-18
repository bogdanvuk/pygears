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


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
@pytest.mark.parametrize('branches', list(range(2, 10)))
def test_mapped_directed(tmpdir, sim_cls, din_delay, dout_delay, branches):

    seq = [(i, i) for i in range(branches)]
    TDin = Union[tuple(Uint[i] for i in range(1, branches + 1))]

    mapping = {}
    for i in range(branches):
        mapping[i] = (i + 1) if (i + 1) < branches else 0

    ref = [[(i - 1) if (i - 1) >= 0 else (branches - 1)]
           for i in range(branches)]

    print(mapping)
    print(seq)
    print(ref)

    directed(
        drv(t=TDin, seq=seq) | delay_rng(din_delay, din_delay),
        f=demux(mapping=mapping, sim_cls=sim_cls),
        delays=[delay_rng(dout_delay, dout_delay) for _ in range(branches)],
        ref=ref)

    sim(outdir=tmpdir)


def mux_demux_redux(branches):
    TDin = Union[tuple(Uint[i] for i in range(1, branches + 1))]
    demux_ctrl(Intf(TDin)) | mux


@pytest.mark.parametrize('language', ['v'])
@pytest.mark.parametrize('branches', [2, 4])
@synth_check({'logic luts': 0, 'ffs': 0}, tool='vivado')
def test_mux_demux_redux_power_two_vivado(branches):
    mux_demux_redux(branches)


@pytest.mark.parametrize('language', ['v'])
@pytest.mark.parametrize('branches', [3])
@synth_check({'logic luts': 1, 'ffs': 0}, tool='vivado')
def test_mux_demux_redux_odd_vivado(branches):
    mux_demux_redux(branches)


@pytest.mark.parametrize('branches', [2, 3, 27])
@synth_check({'logic luts': 0, 'ffs': 0}, tool='yosys', freduce=True)
def test_mux_demux_redux_yosys(branches):
    mux_demux_redux(branches)


@pytest.mark.parametrize('branches', [3, 27])
@synth_check({'logic luts': 2, 'ffs': 0}, tool='yosys')
def test_mux_demux_redux_no_freduce_yosys(branches):
    mux_demux_redux(branches)
