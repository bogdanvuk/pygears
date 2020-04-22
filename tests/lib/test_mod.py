from pygears import Intf
from pygears.lib import mod
from pygears.lib.verif import verif
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.typing import Tuple, Uint
from pygears.util.test_utils import formal_check, synth_check


def test_unsigned_cosim(cosim_cls):
    seq = [(0x6, 0x2), (0x5, 0x2), (0x4, 0x3)]

    verif(drv(t=Tuple[Uint[4], Uint[2]], seq=seq),
          f=mod(sim_cls=cosim_cls),
          ref=mod(name='ref_model'))

    sim()


@formal_check()
def test_unsigned_formal():
    mod(Intf(Tuple[Uint[10], Uint[4]]))


@synth_check({'logic luts': 54, 'ffs': 0}, tool='vivado')
def test_unsigned_synth_vivado():
    mod(Intf(Tuple[Uint[10], Uint[4]]))


# @synth_check({'logic luts': 487, 'ffs': 0}, tool='yosys')
# def test_unsigned_synth_yosys():
#     mod(Intf(Tuple[Uint[10], Uint[4]]))
