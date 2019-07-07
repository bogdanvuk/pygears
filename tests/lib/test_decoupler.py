from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv, verif
from pygears import Intf, sim
from pygears.lib import decoupler
from pygears.typing import Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 4, 'ffs': 4, 'lutrams': 2}, tool='vivado')
def test_synth_u1_vivado():
    decoupler(Intf(Uint[1]))


@synth_check({'logic luts': 11, 'ffs': 6}, tool='yosys')
def test_synth_u1_yosys():
    decoupler(Intf(Uint[1]))


@synth_check({'logic luts': 4, 'ffs': 4, 'lutrams': 44}, tool='vivado')
def test_synth_u64_vivado():
    decoupler(Intf(Uint[64]))


@synth_check({'logic luts': 8, 'ffs': 4, 'lutrams': 64}, tool='yosys')
def test_synth_u64_yosys():
    decoupler(Intf(Uint[64]))


def test_cosim(tmpdir, cosim_cls):
    seq = list(range(1, 10))
    directed(drv(t=Uint[16], seq=seq) | delay_rng(0, 2),
             f=decoupler(sim_cls=cosim_cls),
             ref=seq,
             delays=[delay_rng(0, 2)])

    sim(outdir=tmpdir)


# from pygears.sim.modules import SimVerilated
# from functools import partial
# test_cosim('/tools/home/tmp', partial(SimVerilated, language='v'))
