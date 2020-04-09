from pygears import gear

from pygears.sim import sim, cosim
from pygears.core.gear import InSig, OutSig
from pygears import module
from pygears.typing import Bool
from pygears.lib import drv, shred


# def test_outsig(tmpdir):
#     @gear(signals=[InSig('clk', 1),
#                    InSig('rst', 1),
#                    OutSig('flush', 1)],
#           hdl={'compile': True})
#     async def local_rst(din):
#         flush = module().signals['flush']
#         flush.write(0)
#         async with din as d:
#             if d:
#                 flush.write(1)
#             else:
#                 flush.write(0)

#     @gear
#     def hier(din: Bool):
#         din | local_rst

#     drv(t=Bool, seq=[False, True]) | hier
#     cosim('/hier', 'verilator')
#     sim(tmpdir)
