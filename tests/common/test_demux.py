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


@pytest.mark.parametrize('branches', [2, 3, 7, 13, 17, 27, 127])
@synth_check({'logic luts': 1, 'ffs': 0}, tool='vivado')
def test_mux_demux_redux_vivado(branches):
    mux_demux_redux(branches)


@pytest.mark.parametrize('branches', [2, 3, 7, 13, 17, 27, 127])
@synth_check({'logic luts': 1, 'ffs': 0}, tool='yosys')
def test_mux_demux_redux_yosys(branches=2):
    mux_demux_redux(branches)


# # test_simple_directed('/tools/home/tmp', SimVerilated, 0, 0, 3)

# def test_simple_synth(tmpdir, branches):
#     TDin = Union[tuple(Uint[i] for i in range(1, branches + 1))]
#     # print(TDin)
#     # TDin = Union[Uint[1], Uint[1]]

#     demux_ctrl(Intf(TDin)) | mux
#     # demux_ctrl(Intf(TDin))
#     res = synth('/tools/home/tmp')
#     print(res)

#     # util = vivado_synth('/tools/home/tmp', language='v')
#     # print(util)
#     # assert util['total luts'] == branches

# test_simple_synth(5)

# config['trace/level'] = 1
# sim('/tools/home/tmp')

######## YOSYS #########
# read_verilog /home/bogdan/mux_demux.v
# prep
# dump t:$dff %x:+[Q] t:$dff %d
# connect -set ready_reg 2'h0
# // dump t:$dff %co
# // ls

# sat -tempinduct -prove ready_reg 2'h0
