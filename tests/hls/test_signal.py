from pygears import gear

from pygears.sim import sim, cosim
from pygears.core.gear import InSig, OutSig
from pygears import module
from pygears.typing import Bool
from pygears.lib import drv


def test_outsig(lang):
    @gear(signals=[InSig('clk', 1),
                   InSig('rst', 1),
                   OutSig('flush', 1)])
    async def local_rst(din):
        sig = module().signals['flush']
        sig.write(0)
        async with din as d:
            if d:
                sig.write(1)
            else:
                sig.write(0)

    @gear
    def hier(din: Bool):
        din | local_rst

    drv(t=Bool, seq=[False, True]) | hier
    cosim('/hier', 'verilator', lang=lang)
    sim()
