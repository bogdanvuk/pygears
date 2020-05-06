from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv, verif
from pygears import Intf, sim
from pygears.lib import decouple
from pygears.typing import Uint
from pygears.util.test_utils import synth_check


@synth_check({'logic luts': 4, 'ffs': 4, 'lutrams': 2}, tool='vivado')
def test_synth_u1_vivado():
    decouple(Intf(Uint[1]))


@synth_check({'logic luts': 12, 'ffs': 7}, tool='yosys')
def test_synth_u1_yosys():
    decouple(Intf(Uint[1]))


@synth_check({'logic luts': 4, 'ffs': 4, 'lutrams': 44}, tool='vivado')
def test_synth_u64_vivado():
    decouple(Intf(Uint[64]))


@synth_check({'logic luts': 7, 'ffs': 15}, tool='yosys')
def test_synth_u64_yosys():
    decouple(Intf(Uint[64]))


def test_cosim(cosim_cls):
    seq = list(range(1, 10))
    directed(drv(t=Uint[16], seq=seq) | delay_rng(0, 2),
             f=decouple(sim_cls=cosim_cls),
             ref=seq,
             delays=[delay_rng(0, 2)])

    sim()
